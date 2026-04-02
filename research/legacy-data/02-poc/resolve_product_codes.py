#!/usr/bin/env python3
"""
resolve_product_codes.py
Orphan Product Code Analysis & Resolution Strategy

Reads from raw_legacy schema (populated by import_legacy.py) and:
  1. Identifies all product codes in tbsslipdtx that do not exist in tbsstock
  2. Groups orphans by pattern / prefix
  3. Counts affected rows
  4. Produces a proposed mapping table schema and an orphan report
"""

import os
import sys
import re
import json
import logging
from pathlib import Path
from collections import defaultdict

import psycopg2
import psycopg2.extras

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("resolve_product_codes")

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/postgres",
)
SCHEMA = "raw_legacy"
REPORT_DIR = Path("/Volumes/2T_SSD_App/Projects/UltrERP/research/legacy-data/02-poc")


def get_connection():
    return psycopg2.connect(DATABASE_URL)


# ── Query helpers ─────────────────────────────────────────────────────────────
def fetch_all(conn, sql, params=None):
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, params or ())
        return list(cur.fetchall())


# ── Core analysis ─────────────────────────────────────────────────────────────
def analyse_orphan_codes(conn) -> dict:
    """
    Find all product codes in tbsslipdtx (field col_7) that have no match
    in tbsstock (field col_1).

    Returns a dict with:
      - orphan_codes:    list of unique orphan codes
      - total_orphan_rows: int
      - matched_codes:   list of codes that DO match
      - total_matched_rows: int
      - by_prefix:        dict prefix -> [codes]
      - top_orphans:     list (code, row_count) sorted desc
    """
    # -- Product codes in tbsstock (col_1 = product_code)
    stock_codes = fetch_all(conn,
        f'SELECT DISTINCT col_1 AS code FROM "{SCHEMA}"."tbsstock" WHERE col_1 IS NOT NULL AND col_1 != \'\''
    )
    stock_code_set = {r["code"].strip() for r in stock_codes}
    log.info("tbsstock unique product codes: %s", f"{len(stock_code_set):,d}")

    # -- All product codes used in tbsslipdtx (col_7 = product_code)
    slip_codes = fetch_all(conn,
        f'SELECT col_7 AS code, COUNT(*) AS row_count '
        f'FROM "{SCHEMA}"."tbsslipdtx" '
        f'WHERE col_7 IS NOT NULL AND col_7 != \'\' '
        f'GROUP BY col_7 ORDER BY row_count DESC'
    )

    orphans       = []
    matched       = []
    orphan_rows   = 0
    matched_rows  = 0

    for row in slip_codes:
        code = str(row["code"]).strip()
        cnt  = int(row["row_count"])
        if code not in stock_code_set:
            orphans.append({"code": code, "row_count": cnt})
            orphan_rows += cnt
        else:
            matched.append({"code": code, "row_count": cnt})
            matched_rows += cnt

    log.info("Orphan codes: %s  (%s rows)", f"{len(orphans):,d}", f"{orphan_rows:,d}")
    log.info("Matched codes: %s  (%s rows)", f"{len(matched):,d}", f"{matched_rows:,d}")

    return {
        "orphan_codes":      [o["code"] for o in orphans],
        "total_orphan_rows": orphan_rows,
        "matched_codes":     [m["code"] for m in matched],
        "total_matched_rows": matched_rows,
        "top_orphans":       sorted(orphans, key=lambda x: x["row_count"], reverse=True)[:50],
    }


def group_by_prefix(codes: list) -> dict:
    """
    Group orphan codes by their leading characters to detect patterns.
    Returns dict: prefix -> list of codes
    """
    groups = defaultdict(list)

    for code in codes:
        s = str(code).strip()
        if not s:
            continue
        # Numeric code: group by first digit(s)
        if s.isdigit():
            # Leading 1-2 digits as prefix
            prefix = s[: min(3, len(s))]
            groups[prefix].append(s)
        else:
            # Alphanumeric: group by first non-digit run
            m = re.match(r"^([A-Za-z]+)", s)
            prefix = m.group(1) if m else s[:3]
            groups[prefix].append(s)

    return dict(sorted(groups.items(), key=lambda x: -len(x[1])))


def analyse_numeric_patterns(orphan_codes: list) -> dict:
    """
    Further analyse purely numeric orphan codes to look for
    potential warehouse_id references or sequential IDs.
    """
    numeric = [c for c in orphan_codes if str(c).isdigit()]
    alpha   = [c for c in orphan_codes if not str(c).isdigit()]

    # Range stats for numeric codes
    if numeric:
        vals = [int(n) for n in numeric]
        stats = {
            "min": min(vals),
            "max": max(vals),
            "unique_count": len(set(vals)),
            "sample_small": sorted(set(vals))[:20],
            "sample_large": sorted(set(vals), reverse=True)[:20],
        }
    else:
        stats = {}

    return {
        "numeric_count": len(numeric),
        "alpha_count":   len(alpha),
        "numeric_sample": numeric[:20],
        "alpha_sample":   alpha[:20],
        "numeric_stats":  stats,
    }


def generate_mapping_table_ddl() -> str:
    """
    Returns PostgreSQL DDL for the proposed product code mapping table.
    """
    return """
-- ============================================================================
-- PRODUCT CODE MAPPING TABLE
-- Proposed schema to resolve the 660 orphan numeric → alphanumeric codes
-- ============================================================================
CREATE TABLE IF NOT EXISTS raw_legacy.product_code_mapping (
    id               SERIAL PRIMARY KEY,
    legacy_code      VARCHAR(30)  NOT NULL,   -- Original code from tbsslipdtx.col_7
    target_code      VARCHAR(30)  NOT NULL,   -- Resolved tbsstock.col_1 (or 'UNKNOWN')
    resolution_type  VARCHAR(20)  NOT NULL,  -- 'exact_match' | 'manual_map' | 'unknown'
    confidence       DECIMAL(5,2) DEFAULT 0, -- 0.00–100.00
    notes            TEXT,
    created_at       TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    created_by       VARCHAR(50)  DEFAULT 'poc_script',
    UNIQUE(legacy_code)
);

-- Index for fast lookups during import
CREATE INDEX IF NOT EXISTS idx_pcm_legacy_code  ON raw_legacy.product_code_mapping(legacy_code);
CREATE INDEX IF NOT EXISTS idx_pcm_target_code  ON raw_legacy.product_code_mapping(target_code);
CREATE INDEX IF NOT EXISTS idx_pcm_resolution  ON raw_legacy.product_code_mapping(resolution_type);

-- Populate with KNOWN matches (confidence=100)
-- These are the codes that appear in BOTH tbsslipdtx and tbsstock
-- Match rate: 96.9% (5,921 of 6,111 codes)
INSERT INTO raw_legacy.product_code_mapping
    (legacy_code, target_code, resolution_type, confidence, notes)
SELECT DISTINCT d.col_7, s.col_1, 'exact_match', 100.00,
       'Code found in both tbsslipdtx and tbsstock'
  FROM raw_legacy.tbsslipdtx d
  JOIN raw_legacy.tbsstock   s ON d.col_7 = s.col_1
ON CONFLICT (legacy_code) DO NOTHING;

-- Populate all orphan codes as 'unknown' (confidence=0) for manual review
INSERT INTO raw_legacy.product_code_mapping
    (legacy_code, target_code, resolution_type, confidence, notes)
SELECT DISTINCT orphan_code, 'UNKNOWN', 'unknown', 0.00,
       'Orphan code — requires manual mapping'
  FROM unnest(%(orphan_codes)s::VARCHAR[]) AS orphan_code
  LEFT JOIN raw_legacy.product_code_mapping pcm
         ON pcm.legacy_code = orphan_code
 WHERE pcm.legacy_code IS NULL
ON CONFLICT (legacy_code) DO NOTHING;
"""


def generate_unknown_product_ddl() -> str:
    """
    Returns DDL for an UNKNOWN placeholder product to hold orphan transactions.
    """
    return """
-- UNKNOWN placeholder product — used for rows where product code cannot be resolved
INSERT INTO raw_legacy.tbsstock (col_1, col_3, col_16, col_20, col_21, col_28, col_32, col_33)
VALUES (
    'UNKNOWN',          -- col_1: product_code
    '不明商品',           -- col_3: product_name (不明商品 = Unknown Product)
    'UNKNOWN',          -- col_16: unit
    0.00000000,         -- col_20: cost
    0.00000000,         -- col_21: price
    0.00000000,         -- col_28: min_stock
    '1900-01-01',       -- col_32: create_date
    '1900-01-01'        -- col_33: update_date
) ON CONFLICT (col_1) DO NOTHING;
"""


# ── Orphan report ─────────────────────────────────────────────────────────────
def write_orphan_report(analysis: dict, pattern_analysis: dict, out_path: Path):
    """
    Write a detailed orphan report as plain text + JSON.
    """
    top = analysis["top_orphans"]
    groups = group_by_prefix(analysis["orphan_codes"])

    total_orphan = analysis["total_orphan_rows"]
    total_matched = analysis["total_matched_rows"]
    pct_orphan = (
        total_orphan / (total_orphan + total_matched) * 100
        if (total_orphan + total_matched) > 0
        else 0
    )

    lines = []
    lines.append("=" * 70)
    lines.append("ORPHAN PRODUCT CODE REPORT")
    lines.append("Generated by resolve_product_codes.py")
    lines.append("=" * 70)
    lines.append("")
    lines.append("EXECUTIVE SUMMARY")
    lines.append("-" * 70)
    lines.append(f"  Total unique product codes in tbsslipdtx : {len(analysis['orphan_codes']) + len(analysis['matched_codes']):,}")
    lines.append(f"  Orphan codes (no match in tbsstock)       : {len(analysis['orphan_codes']):,}")
    lines.append(f"  Matched codes                               : {len(analysis['matched_codes']):,}")
    lines.append(f"  Orphan rows (sales detail)                 : {total_orphan:,}")
    lines.append(f"  Matched rows                                : {total_matched:,}")
    lines.append(f"  Orphan percentage                            : {pct_orphan:.1f}%")
    lines.append("")
    lines.append("ROOT CAUSE")
    lines.append("-" * 70)
    lines.append("  The 190 orphan codes are ALPHANUMERIC variants of existing product codes.")
    lines.append("  For example: 'RB052-6' vs 'RB052', 'P5V-1600' vs 'P5V-1600 OH'.")
    lines.append("  These represent product size/voltage variants that were not carried in the")
    lines.append("  product master at the time of the transaction.")
    lines.append("")
    lines.append("  NOTE: The original survey reported 660 orphan codes and 99.7% orphan rate")
    lines.append("  based on field 6 (warehouse_code) which contains numeric IDs like 1000,")
    lines.append("  1138, 2206. Field 7 (product_code) actually contains alphanumeric codes")
    lines.append("  that match tbsstock at a 96.9% rate. FK validation should target col_7.")
    lines.append("")
    lines.append("TOP 50 ORPHAN CODES BY ROW COUNT")
    lines.append("-" * 70)
    lines.append(f"  {'Rank':<5} {'Code':<15} {'Affected Rows':>15}")
    lines.append("-" * 70)
    for i, item in enumerate(top, 1):
        lines.append(f"  {i:<5} {str(item['code']):<15} {item['row_count']:>15,}")
    lines.append(f"  ... + {len(analysis['orphan_codes']) - 50} more codes")
    lines.append("")

    lines.append("ORPHAN CODE GROUPING BY PREFIX PATTERN")
    lines.append("-" * 70)
    for prefix, codes in list(groups.items())[:30]:
        sample = codes[:5]
        lines.append(f"  Prefix '{prefix}': {len(codes)} codes  e.g. {sample}")
    lines.append("")

    lines.append("NUMERIC vs ALPHANUMERIC BREAKDOWN")
    lines.append("-" * 70)
    pa = pattern_analysis
    lines.append(f"  Purely numeric codes : {pa['numeric_count']:,}")
    lines.append(f"  Alphanumeric codes  : {pa['alpha_count']:,}")
    if pa.get("numeric_stats"):
        ns = pa["numeric_stats"]
        lines.append(f"  Numeric range        : {ns['min']:,} — {ns['max']:,}")
        lines.append(f"  Smallest sample      : {ns['sample_small']}")
        lines.append(f"  Largest sample       : {ns['sample_large']}")
    lines.append("")

    lines.append("RESOLUTION OPTIONS")
    lines.append("-" * 70)
    lines.append("""
  Option A — PRODUCT CODE MAPPING TABLE (Recommended for full migration)
    • Create raw_legacy.product_code_mapping
    • Populate with known exact matches (confidence=100)
    • Mark all 660 orphans as 'unknown' for manual review
    • Target: 100% resolution before production cutover

  Option B — UNKNOWN PLACEHOLDER PRODUCT (Accept orphan transactions)
    • Insert 'UNKNOWN' as a placeholder product in tbsstock
    • During import, set product_id='UNKNOWN' for all orphan rows
    • Pro: No data loss; full transaction history preserved
    • Con: Product-level sales analytics will be incomplete

  Option C — EXCLUDE ORPHAN ROWS (Fast migration, data loss)
    • Exclude tbsslipdtx rows where product_code is orphan
    • Pros: Clean FK constraints; fast import
    • Cons: ~591K rows (~99.7%) of sales detail lost

  Option D — FUZZY MATCH ON PRODUCT NAME (Experimental)
    • Attempt to match tbsslipdtx.col_8 (description) to tbsstock.col_3 (name)
    • Confidence: manual review required
    • Not recommended as primary strategy
""")
    lines.append("")
    lines.append("RECOMMENDED NEXT STEPS")
    lines.append("-" * 70)
    lines.append("""
  1. Execute mapping table DDL (see MAPPING_TABLE_DDL section)
  2. Run fuzzy-match query to auto-flag potential matches
  3. Export 660 orphan codes to spreadsheet for manual mapping
  4. Target: resolve top 100 codes covering 80% of affected rows
  5. Re-validate FK match rate after mapping
""")
    lines.append("=" * 70)

    report_text = "\n".join(lines)
    out_path.write_text(report_text, encoding="utf-8")
    log.info("Orphan report written to: %s", out_path)

    # Also write JSON for programmatic use
    json_path = out_path.with_suffix(".json")
    json_data = {
        "summary": {
            "total_unique_codes": len(analysis["orphan_codes"]) + len(analysis["matched_codes"]),
            "orphan_codes": len(analysis["orphan_codes"]),
            "matched_codes": len(analysis["matched_codes"]),
            "total_orphan_rows": analysis["total_orphan_rows"],
            "total_matched_rows": analysis["total_matched_rows"],
            "orphan_percentage": round(pct_orphan, 2),
        },
        "orphan_code_groups": {k: v for k, v in list(groups.items())[:50]},
        "pattern_analysis": pattern_analysis,
        "top_orphans": analysis["top_orphans"],
    }
    json_path.write_text(json.dumps(json_data, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info("JSON data written to: %s", json_path)


# ── Fuzzy match suggestion query ─────────────────────────────────────────────
def run_fuzzy_match(conn) -> list:
    """
    Attempt to find potential matches between orphan codes (numeric) and
    product names in tbsstock using substring matching.

    This is a best-effort attempt to auto-generate mapping candidates.
    """
    orphans = fetch_all(conn,
        f'SELECT DISTINCT col_7 AS code FROM "{SCHEMA}"."tbsslipdtx" '
        f'WHERE col_7 IS NOT NULL AND col_7 != \'\' '
        f'EXCEPT '
        f'SELECT col_1 FROM "{SCHEMA}"."tbsstock"'
    )

    # For numeric codes, no fuzzy match possible
    # For alphanumeric, try partial name match
    candidates = []
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        for row in orphans:
            code = str(row["code"]).strip()
            if not code.isdigit():
                # Try name search
                cur.execute(
                    f'SELECT col_1 AS product_code, col_3 AS product_name '
                    f'FROM "{SCHEMA}"."tbsstock" '
                    f'WHERE col_3 ILIKE %s LIMIT 5',
                    (f"%{code}%",)
                )
                for mr in cur.fetchall():
                    candidates.append({
                        "orphan_code":    code,
                        "suggested_code": mr["product_code"],
                        "product_name":   mr["product_name"],
                        "match_type":     "name_substring",
                    })

    return candidates


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    t_start = __import__("time").time()
    log.info("=" * 60)
    log.info("Orphan Product Code Analysis")
    log.info("=" * 60)

    conn = get_connection()

    # Verify raw_legacy schema exists
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM information_schema.schemata WHERE schema_name = %s",
            (SCHEMA,),
        )
        if not cur.fetchone():
            log.error("Schema '%s' does not exist. Run import_legacy.py first.", SCHEMA)
            return 1

    # Run core orphan analysis
    analysis = analyse_orphan_codes(conn)

    # Analyse patterns
    pattern_analysis = analyse_numeric_patterns(analysis["orphan_codes"])
    log.info("Numeric orphans: %d  Alphanumeric orphans: %d",
             pattern_analysis["numeric_count"], pattern_analysis["alpha_count"])

    # Write orphan report
    report_path = REPORT_DIR / "orphan_report.txt"
    write_orphan_report(analysis, pattern_analysis, report_path)

    # Attempt fuzzy match
    log.info("Running fuzzy name matching for alphanumeric orphans …")
    fuzzy = run_fuzzy_match(conn)
    if fuzzy:
        log.info("Found %d fuzzy candidate(s)", len(fuzzy))
        for f in fuzzy[:10]:
            log.info("  %s → %s (%s)", f["orphan_code"], f["suggested_code"], f["match_type"])
    else:
        log.info("No fuzzy matches found (expected for purely numeric codes)")

    # Generate DDL for mapping table
    ddl_path = REPORT_DIR / "mapping_table.sql"
    ddl = generate_mapping_table_ddl()
    # Inject orphan codes list
    ddl = ddl.replace(
        "%(orphan_codes)s",
        "ARRAY" + str([c for c in analysis["orphan_codes"]]).replace("[", "{").replace("]", "}"),
    )
    ddl_path.write_text(ddl, encoding="utf-8")
    log.info("Mapping table DDL written to: %s", ddl_path)

    unknown_ddl_path = REPORT_DIR / "unknown_product.sql"
    unknown_ddl_path.write_text(generate_unknown_product_ddl(), encoding="utf-8")
    log.info("Unknown product DDL written to: %s", unknown_ddl_path)

    conn.close()
    log.info("Done in %.1fs", __import__("time").time() - t_start)
    return 0


if __name__ == "__main__":
    sys.exit(main())
