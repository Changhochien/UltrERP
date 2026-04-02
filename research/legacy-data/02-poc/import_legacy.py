#!/usr/bin/env python3
"""
import_legacy.py
Legacy ERP CSV Import Pipeline PoC

Connects to PostgreSQL, creates raw_legacy schema, and imports
key CSV files from extracted_data/ with ROC date parsing.
"""

import os
import sys
import re
import io
import time
import csv
import logging
from datetime import date, datetime
from pathlib import Path

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("import_legacy")

# ── Env / Paths ───────────────────────────────────────────────────────────────
DATA_DIR = Path("/Volumes/2T_SSD_App/Projects/UltrERP/legacy-migration-pipeline/extracted_data")
WORK_DIR = Path("/Volumes/2T_SSD_App/Projects/UltrERP/research/legacy-data/02-poc")

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/postgres",
)

# ── CSV that will be imported ─────────────────────────────────────────────────
IMPORT_TABLES = {
    "tbscust":   {"fname": "tbscust.csv",   "row_estimate": 1_022},
    "tbsstock":  {"fname": "tbsstock.csv",  "row_estimate": 6_611},
    "tbsslipx":  {"fname": "tbsslipx.csv",   "row_estimate": 133_419},
    # PoC scope: 3 CSVs required; tbsslipdtx is too large for quick PoC
}

# ── ROC Date helpers ─────────────────────────────────────────────────────────
# ROC year in source data: Year + 1911 = AD
# Invoice number: 1130826001 → ROC 113, month 08, day 26, seq 001
# Some date fields are already YYYY-MM-DD (AD). Others are ROC string.
# The sentinel 1900-01-01 indicates an empty/null date in the legacy system.

ROC_SENTINEL = date(1900, 1, 1)


def parse_roc_date(value: str) -> date:
    """
    Parse a date value that may be in ROC format or AD format.

    ROC format observed: '1130826001' → 2024-08-26 (ROC year 113 = AD 2024)
    AD format observed: '2024-08-26'  → 2024-08-26
    Sentinel:           '1900-01-01'  → returns ROC_SENTINEL (1900-01-01)

    Raises ValueError if the date cannot be parsed.
    """
    if not value or value.strip() in ("", "0"):
        return ROC_SENTINEL

    s = str(value).strip()

    # Already AD format (YYYY-MM-DD)
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        try:
            dt = datetime.strptime(s, "%Y-%m-%d").date()
            if dt == ROC_SENTINEL:
                return ROC_SENTINEL  # explicit sentinel
            # If year is pre-1911 it cannot be a valid AD date in this dataset
            if dt.year < 1911 and dt != ROC_SENTINEL:
                log.warning("Date %s looks like ROC but has no leading digit; treating as-is", s)
            return dt
        except ValueError:
            pass

    # ROC encoded invoice number: 1130826001 → 2024-08-26
    if re.match(r"^\d{10}$", s):
        try:
            roc_year = int(s[0:3])
            month    = int(s[3:5])
            day      = int(s[5:7])
            ad_year  = roc_year + 1911
            return date(ad_year, month, day)
        except (ValueError, IndexError) as e:
            raise ValueError(f"Cannot parse ROC number {s}: {e}")

    # 8-digit ROC date (older format: YYMMDDNN or similar)
    if re.match(r"^\d{8}$", s):
        try:
            roc_year = int(s[0:2])
            month    = int(s[2:4])
            day      = int(s[4:6])
            ad_year  = roc_year + 1911
            return date(ad_year, month, day)
        except ValueError:
            raise ValueError(f"Cannot parse 8-digit date {s}")

    raise ValueError(f"Unrecognised date format: {s!r}")


# ── CSV Parser ────────────────────────────────────────────────────────────────
def parse_row(line: str) -> list:
    """
    Parse a single CSV row from the legacy export format.

    Rows look like:
      " '1149', '2', '昌弘五金實業有限公司', ..."

    The separator is "', '" (single-quote, comma, space, single-quote).
    We strip the leading/trailing wrapper quotes and split on the delimiter.
    Fields are returned stripped of their surrounding quotes.
    """
    # Remove outer double-quote wrapper
    line = line.strip()
    if line.startswith('"') and line.endswith('"'):
        line = line[1:-1]

    # Un-escape any double-escaped quotes within the row
    line = line.replace('\\"', '"')

    # Split on the field delimiter
    fields = line.split("', '")

    # Strip leading/trailing single quotes from each field
    cleaned = []
    for f in fields:
        f = f.strip()
        if f.startswith("'") and f.endswith("'"):
            f = f[1:-1]
        elif f.startswith("'"):
            f = f[1:]
        elif f.endswith("'"):
            f = f[:-1]
        cleaned.append(f)

    return cleaned


# ── PostgreSQL helpers ───────────────────────────────────────────────────────
def get_connection():
    import psycopg2
    return psycopg2.connect(DATABASE_URL)


def schema_exists(conn, schema: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM information_schema.schemata WHERE schema_name = %s",
            (schema,),
        )
        return cur.fetchone() is not None


def create_schema(conn, schema: str):
    with conn.cursor() as cur:
        cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
    conn.commit()
    log.info("Schema '%s' created/verified", schema)


def drop_table(conn, schema: str, table: str):
    with conn.cursor() as cur:
        cur.execute(f'DROP TABLE IF EXISTS "{schema}"."{table}" CASCADE')
    conn.commit()


def create_table(conn, schema: str, table: str, num_cols: int):
    """Create a staging table with num_cols TEXT columns (handles any length)."""
    cols_def = ",".join([f'"col_{i+1}" TEXT' for i in range(num_cols)])
    with conn.cursor() as cur:
        cur.execute(f'CREATE TABLE "{schema}"."{table}" ({cols_def})')
    conn.commit()


def import_csv(conn, schema: str, table: str, csv_path: Path) -> int:
    """
    Load a headerless CSV into raw_legacy.<table>.
    Determines column count from first row, creates table, then bulk-inserts.
    Returns the number of rows inserted.
    """
    drop_table(conn, schema, table)

    rows_inserted = 0
    t0 = time.time()

    # Pass 1: read all rows
    # The CSV has an outer double-quote wrapper; inside, fields are separated
    # by comma and may be single-quoted.  We strip the wrapper and use
    # Python's csv.reader (which handles single-quote text qualification).
    all_rows = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line:
                continue
            # Remove outer double-quote wrapper if present
            if line.startswith('"') and line.endswith('"'):
                line = line[1:-1]
            # Parse with csv.reader (handles quoted fields correctly)
            try:
                rows = list(csv.reader(io.StringIO(line)))
                if rows:
                    row = [field.strip().strip("'") for field in rows[0]]
                    if any(r for r in row):
                        all_rows.append(row)
            except Exception:
                # Fallback: split on "', '" delimiter
                fields = line.split("', '")
                row = [f.strip().strip("'") for f in fields]
                if any(r for r in row):
                    all_rows.append(row)

    if not all_rows:
        log.warning("No data rows found in %s", csv_path)
        return 0

    # Determine column count from longest row
    num_cols = max(len(r) for r in all_rows)
    create_table(conn, schema, table, num_cols)
    log.info("Created table %s.%s with %d columns", schema, table, num_cols)

    # Batch insert
    cols = [f"col_{i+1}" for i in range(num_cols)]
    placeholders = ",".join(["%s"] * num_cols)
    col_names    = ",".join([f'"{c}"' for c in cols])
    insert_sql   = f'INSERT INTO "{schema}"."{table}" ({col_names}) VALUES ({placeholders})'

    # Pad short rows with None
    padded = [row + [None] * (num_cols - len(row)) for row in all_rows]

    with conn.cursor() as cur:
        for batch_start in range(0, len(padded), 10_000):
            batch = padded[batch_start : batch_start + 10_000]
            cur.executemany(insert_sql, batch)
            conn.commit()

    rows_inserted = len(padded)
    elapsed = time.time() - t0
    rate = rows_inserted / elapsed if elapsed > 0 else 0
    log.info(
        "IMPORTED %s: %s rows in %.1fs (%.0f rows/sec)",
        table, f"{rows_inserted:,d}", elapsed, rate,
    )
    return rows_inserted


def add_staging_columns(conn, schema: str, table: str):
    """Add audit / lineage columns to every raw table."""
    with conn.cursor() as cur:
        cur.execute(
            f'SET search_path TO "{schema}"'
        )
        # Add columns only if they don't exist
        for col, col_type in [
            ("_import_status",   "VARCHAR(20) DEFAULT 'loaded'"),
            ("_legacy_pk",       "VARCHAR(100)"),
            ("_fk_violation",    "BOOLEAN DEFAULT FALSE"),
        ]:
            try:
                cur.execute(
                    f'ALTER TABLE "{table}" ADD COLUMN {col} {col_type}'
                )
            except Exception:
                pass  # column already exists
    conn.commit()


# ── ROC date parser (SQL-based for performance) ───────────────────────────────
ROC_SENTINEL_SQL = "DATE '1900-01-01'"


def _roc_case_sql(value_col: str) -> str:
    """
    Return a PostgreSQL CASE expression that parses a ROC date value.
    Handles:
      - 10-digit ROC invoice number: 1130826001 → 2024-08-26
      - 8-digit ROC compact:           88032642 → 1999-03-26
      - Standard YYYY-MM-DD AD:         passed through
      - '1900-01-01' sentinel:         kept as sentinel
    """
    v = value_col
    return f"""
        CASE
        WHEN {v} IS NULL OR {v} = '' THEN {ROC_SENTINEL_SQL}
        WHEN {v} = '1900-01-01' THEN {ROC_SENTINEL_SQL}
        WHEN {v} ~ '^[0-9]{{10}}$' THEN
            MAKE_DATE(
                SUBSTRING({v}, 1, 3)::INT + 1911,
                SUBSTRING({v}, 4, 2)::INT,
                SUBSTRING({v}, 6, 2)::INT
            )
        WHEN {v} ~ '^[0-9]{{8}}$' THEN
            MAKE_DATE(
                SUBSTRING({v}, 1, 2)::INT + 1911,
                SUBSTRING({v}, 3, 2)::INT,
                SUBSTRING({v}, 5, 2)::INT
            )
        WHEN {v} ~ '^[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}$' THEN
            {v}::DATE
        ELSE {ROC_SENTINEL_SQL}
        END
    """


def normalise_slipx_dates(conn, schema: str):
    """
    Parse ROC dates in tbsslipx col_3 (order_date) and col_23 (create_date)
    using SQL-native parsing for performance.
    """
    with conn.cursor() as cur:
        try:
            cur.execute(
                f'ALTER TABLE "{schema}"."tbsslipx" '
                f'ADD COLUMN _order_date_ad DATE'
            )
        except Exception:
            pass
        try:
            cur.execute(
                f'ALTER TABLE "{schema}"."tbsslipx" '
                f'ADD COLUMN _create_date_ad DATE'
            )
        except Exception:
            pass

    order_sql  = _roc_case_sql("col_3")
    create_sql = _roc_case_sql("col_23")

    with conn.cursor() as cur:
        cur.execute(
            f'UPDATE "{schema}"."tbsslipx" '
            f'SET _order_date_ad  = ({order_sql}), '
            f'    _create_date_ad = ({create_sql})'
        )
    conn.commit()
    log.info("Normalised dates in tbsslipx")


# ── Field-level date normalisation for tbsslipdtx ────────────────────────────
# col_2  = doc_number
# col_4  = line_date  (format varies: ROC string or 'YYYY-MM-DD')
# col_56 = delivery_date (often '1900-01-01' sentinel)
def normalise_slipdtx_dates(conn, schema: str):
    """
    Parse dates in tbsslipdtx col_4 using SQL-native parsing.
    For performance, processes in batches of 100K rows.
    """
    with conn.cursor() as cur:
        try:
            cur.execute(
                f'ALTER TABLE "{schema}"."tbsslipdtx" ADD COLUMN _line_date_ad DATE'
            )
        except Exception:
            pass

    line_sql = _roc_case_sql("col_4")

    # Process in batches using a CTE with LIMIT (PostgreSQL 9.5+)
    with conn.cursor() as cur:
        batch = 0
        while True:
            cur.execute(
                f'''
                WITH target AS (
                    SELECT col_1, col_2, col_3
                    FROM "{schema}"."tbsslipdtx"
                    WHERE _line_date_ad IS NULL
                    LIMIT 100000
                )
                UPDATE "{schema}"."tbsslipdtx" AS t
                SET _line_date_ad = ({line_sql})
                FROM target
                WHERE t.col_1 = target.col_1
                  AND t.col_2 = target.col_2
                  AND t.col_3 = target.col_3
                '''
            )
            conn.commit()
            batch += 1
            if cur.rowcount == 0:
                break
            log.info("tbsslipdtx: batch %d — %d rows updated", batch, cur.rowcount)
            if batch >= 20:  # safety cap
                log.warning("tbsslipdtx: hit batch cap — some rows may not be processed")
                break

    log.info("Normalised dates in tbsslipdtx")


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    t_start = time.time()

    log.info("=" * 60)
    log.info("Legacy ERP Import Pipeline — PoC")
    log.info("Database: %s", DATABASE_URL)
    log.info("Data dir: %s", DATA_DIR)
    log.info("=" * 60)

    conn = get_connection()

    # 1. Create schema
    SCHEMA = "raw_legacy"
    if schema_exists(conn, SCHEMA):
        log.info("Schema '%s' already exists — dropping and recreating", SCHEMA)
        with conn.cursor() as cur:
            cur.execute(f"DROP SCHEMA {SCHEMA} CASCADE")
        conn.commit()

    create_schema(conn, SCHEMA)

    # 2. Import CSVs
    results = {}
    for table_name, cfg in IMPORT_TABLES.items():
        csv_path = DATA_DIR / cfg["fname"]
        if not csv_path.exists():
            log.error("CSV not found: %s — skipping", csv_path)
            results[table_name] = 0
            continue

        log.info("Importing %s from %s …", table_name, cfg["fname"])
        rows = import_csv(conn, SCHEMA, table_name, csv_path)
        add_staging_columns(conn, SCHEMA, table_name)
        results[table_name] = rows

    # 3. Import tbsslipdtx separately (larger file, different treatment)
    slipdtx_path = DATA_DIR / "tbsslipdtx.csv"
    if slipdtx_path.exists():
        log.info("Importing tbsslipdtx (%s rows) — this may take a few minutes …",
                 f"{593_017:,d}")
        t0 = time.time()
        rows = import_csv(conn, SCHEMA, "tbsslipdtx", slipdtx_path)
        add_staging_columns(conn, SCHEMA, "tbsslipdtx")
        log.info("tbsslipdtx: %s rows in %.1fs", f"{rows:,d}", time.time() - t0)
        results["tbsslipdtx"] = rows
    else:
        log.warning("tbsslipdtx.csv not found — skipping")

    # 4. Normalise ROC dates
    if "tbsslipx" in results and results["tbsslipx"] > 0:
        try:
            normalise_slipx_dates(conn, SCHEMA)
        except Exception as e:
            log.error("Date normalisation for tbsslipx failed: %s", e)

    if "tbsslipdtx" in results and results["tbsslipdtx"] > 0:
        try:
            normalise_slipdtx_dates(conn, SCHEMA)
        except Exception as e:
            log.error("Date normalisation for tbsslipdtx failed: %s", e)

    conn.close()

    # Summary
    total = sum(results.values())
    log.info("=" * 60)
    log.info("IMPORT SUMMARY")
    log.info("=" * 60)
    for tbl, cnt in results.items():
        log.info("  %-15s  %s rows", tbl, f"{cnt:,d}")
    log.info("  %-15s  %s total", "TOTAL", f"{total:,d}")
    log.info("Total time: %.1fs", time.time() - t_start)
    log.info("=" * 60)
    log.info("Done. Schema 'raw_legacy' ready for analysis.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
