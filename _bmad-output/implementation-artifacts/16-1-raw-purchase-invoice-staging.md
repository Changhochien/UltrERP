# Story 16.1: Raw Purchase Invoice Staging

Status: draft

## Story

As a migration operator,
I want extracted purchase invoice headers and line items loaded into the raw_legacy staging schema,
So that the purchase transaction data is available for normalization and canonical import alongside the sales data already staged in Epic 15.

## Acceptance Criteria

**AC1:** Purchase invoice tables are staged from verified CSVs
**Given** the verified legacy export set includes tbsslipj and tbsslipdtj CSV files
**When** I run the staging import command with `--table tbsslipj --table tbsslipdtj`
**Then** the pipeline creates or refreshes `raw_legacy.tbsslipj` and `raw_legacy.tbsslipdtj` tables for the configured batch
**And** loads source files with PostgreSQL-native bulk loading (COPY)
**And** records source table, source key, batch/run identifier, and import status for every staged row
**And** tbsslipj.supplier_code (field 7) is validated as a FK to tbscust.customer_code where type='1' (supplier)
**And** ROC-encoded dates in tbsslipj and tbsslipdtj are preserved as-is during staging for later normalization

**AC2:** Same-batch reruns replace atomically
**Given** the staging job completes for a batch that already has tbsslipj/tbsslipdtj staged
**When** I re-run the staging command for the same batch
**Then** the existing rows for those tables are replaced atomically without affecting other already-staged tables in the batch

## CLI Command

```bash
# Stage purchase invoice headers and line items (full purchase invoice scope)
uv run python -m domains.legacy_import.cli stage \
  --batch-id <batch-id> \
  --tenant-id <tenant-uuid> \
  --table tbsslipj \
  --table tbsslipdtj

# Stage only headers
uv run python -m domains.legacy_import.cli stage \
  --batch-id <batch-id> \
  --tenant-id <tenant-uuid> \
  --table tbsslipj

# Stage only line items
uv run python -m domains.legacy_import.cli stage \
  --batch-id <batch-id> \
  --tenant-id <tenant-uuid> \
  --table tbsslipdtj
```

## Staging Table Structures

### raw_legacy.tbsslipj — Purchase Invoice Header

Sourced from: `tbsslipj.csv` (9,250 rows per MANIFEST.md)

| # | Field Name | Type | Notes |
|---|-----------|------|-------|
| 1 | slip_type | VARCHAR(10) | Constant '4' in exported data |
| 2 | doc_number | VARCHAR(20) | **Source key**; YYYYMMDD999 format (e.g., 1130827001) |
| 3 | date | DATE | AD date string (e.g., '2024-08-27'); ROC value preserved in field 75 |
| 4 | doc_number_alias | VARCHAR(20) | Usually same as doc_number |
| 5 | doc_number_format | VARCHAR(20) | e.g., 'YYYMMDD999' |
| 6 | blank1 | VARCHAR(10) | Empty in observed rows |
| 7 | supplier_code | VARCHAR(20) | **FK → tbscust.customer_code WHERE type='1'** |
| 8 | supplier_name | VARCHAR(100) | Supplier short name |
| 9 | supplier_address | VARCHAR(200) | Full supplier address |
| 10 | warehouse_code | VARCHAR(20) | e.g., '0001' |
| 11 | currency | VARCHAR(20) | e.g., '新臺幣' |
| 12 | exchange_rate | DECIMAL(15,8) | e.g., 1.00000000 |
| 13 | supplier_code_alias | VARCHAR(20) | Duplicate of field 7 |
| 14–17 | blank | VARCHAR | Empty |
| 18 | net_amount | DECIMAL(15,4) | Net invoice amount |
| 19 | tax_rate_code | VARCHAR(10) | e.g., '3' |
| 20 | tax_amount | DECIMAL(15,4) | Tax amount |
| 21 | quantity | DECIMAL(15,4) | Total quantity |
| 22–30 | blank/amount_fields | DECIMAL | Various zeroed amounts |
| 31 | blank | VARCHAR | |
| 32 | tax_type | VARCHAR(10) | e.g., '0' |
| 33 | blank | VARCHAR | |
| 34 | batch_code | VARCHAR(20) | e.g., '11308' |
| 35 | operator | VARCHAR(100) | e.g., '系統管理員' |
| 36 | blank | VARCHAR | |
| 37 | status | VARCHAR(10) | e.g., '1' |
| 38 | record_status | INTEGER | e.g., 1 |
| 39–73 | various | MIXED | Address, contact, phone, tax computation, GL references |
| 74 | roc_date | VARCHAR(20) | **ROC-encoded date** (e.g., '1130827001'); preserved as-is |
| 75 | roc_date2 | VARCHAR(20) | Duplicate ROC date; preserved as-is |
| 76 | record_status2 | VARCHAR(10) | e.g., 'A' |
| 77 | total_amount | DECIMAL(15,8) | Full invoice total with tax |
| 78 | status2 | VARCHAR(10) | e.g., 'A' |
| 79 | blank | VARCHAR | |
| 80 | total_amount2 | DECIMAL(15,8) | Secondary total |
| 81 | tax_rate2 | DECIMAL(15,8) | e.g., 0.05000000 |
| 82–98 | blank | VARCHAR | Empty |

**Source key:** `doc_number` (field 2)
**Primary staging key:** `batch_id + doc_number`

### raw_legacy.tbsslipdtj — Purchase Invoice Line Item

Sourced from: `tbsslipdtj.csv` (61,728 rows per MANIFEST.md)

| # | Field Name | Type | Notes |
|---|-----------|------|-------|
| 1 | slip_type | VARCHAR(10) | Constant '4' |
| 2 | doc_number | VARCHAR(20) | **FK → tbsslipj.doc_number** |
| 3 | line_no | INTEGER | **Part of source key**; line sequence number |
| 4 | date | DATE | AD date string (same as header) |
| 5 | supplier_code | VARCHAR(20) | Supplier code (mirrors header) |
| 6 | product_code | VARCHAR(50) | Product/service code; may be non-stock (e.g., '0013' = freight expense) |
| 7 | product_name | VARCHAR(200) | Line item description |
| 8–10 | blank | VARCHAR | Empty |
| 11 | quantity | DECIMAL(15,4) | Invoice quantity |
| 12 | unit | VARCHAR(10) | Unit of measure |
| 13 | blank | VARCHAR | |
| 14 | line_status | INTEGER | e.g., 0 |
| 15–18 | blank/warehouse | VARCHAR | |
| 19 | warehouse_name | VARCHAR(100) | e.g., '總倉' (main warehouse) |
| 20 | warehouse_action | VARCHAR(10) | e.g., '條' |
| 21 | unit_price | DECIMAL(15,6) | Unit price |
| 22 | tax_rate | DECIMAL(15,4) | e.g., 3.00000000 |
| 23 | amount | DECIMAL(15,4) | Line amount (qty × unit_price) |
| 24 | quantity2 | DECIMAL(15,4) | Secondary quantity |
| 25 | blank | VARCHAR | |
| 26 | free_flag | VARCHAR(10) | e.g., 'N' |
| 27 | conversion_ratio | DECIMAL(15,4) | e.g., 1.00000000 |
| 28 | inventory_free_flag | VARCHAR(10) | e.g., 'Y' |
| 29 | inventory_amount | DECIMAL(15,4) | Inventory-tracked amount |
| 30–34 | blank/amounts | DECIMAL | Various zeroed amounts |
| 35 | blank | VARCHAR | |
| 36 | line_seq | INTEGER | e.g., 3 |
| 37 | blank | INTEGER | |
| 38 | line_no2 | INTEGER | Secondary line number |
| 39 | blank/amount | DECIMAL | e.g., 0.00000000 |
| 40 | blank | VARCHAR | |
| 41 | roc_date | VARCHAR(20) | **ROC-encoded date**; preserved as-is |
| 42 | inventory_indicator | VARCHAR(10) | e.g., '1' |
| 43 | blank | VARCHAR | |
| 44 | line_amount2 | DECIMAL(15,4) | Secondary line amount |
| 45–60 | blank/various | MIXED | Empty and zeroed fields |
| 61 | line_amount3 | DECIMAL(15,4) | e.g., 80.00000000 |
| 62 | line_amount4 | DECIMAL(15,4) | e.g., 80.00000000 |
| 63 | line_amount5 | DECIMAL(15,4) | e.g., 80.00000000 |
| 64–79 | blank | VARCHAR | Empty |

**Source key:** `doc_number + line_no` (fields 2 + 3)
**Primary staging key:** `batch_id + doc_number + line_no`

## Source Key Mapping

| Staging Table | Source Key Fields | Staging Composite Key |
|---------------|-------------------|-----------------------|
| raw_legacy.tbsslipj | doc_number (fld 2) | tenant_id + batch_id + doc_number |
| raw_legacy.tbsslipdtj | doc_number + line_no (fld 2 + 3) | tenant_id + batch_id + doc_number + line_no |

## Foreign Key Validation

**FK: tbsslipj.supplier_code → tbscust.customer_code (type='1')**

During COPY staging of tbsslipj, after the batch completes the pipeline validates:
```sql
SELECT DISTINCT supplier_code
FROM raw_legacy.tbsslipj
WHERE batch_id = :batch_id
  AND supplier_code NOT IN (
    SELECT customer_code FROM raw_legacy.tbscust WHERE type = '1'
  );
```
If any unmatched supplier_codes are found, the stage run is marked `failed` with a descriptive error listing the orphan supplier codes. This check is recorded in `legacy_import_table_runs.error_message`.

**FK: tbsslipdtj.doc_number → tbsslipj.doc_number**

After staging tbsslipdtj, the pipeline validates:
```sql
SELECT DISTINCT doc_number
FROM raw_legacy.tbsslipdtj
WHERE batch_id = :batch_id
  AND doc_number NOT IN (
    SELECT doc_number FROM raw_legacy.tbsslipj WHERE batch_id = :batch_id
  );
```
Orphan detail doc_numbers indicate a source-file inconsistency and cause the same failure semantics.

## ROC Date Handling

ROC-encoded dates appear in two forms in these tables:

| Format | Example | Conversion |
|--------|---------|------------|
| YYYMMDD999 (ROC year + doc seq) | `1130827001` | ROC year = 1911 + 113 = **2024**; day = Aug 27, seq = 001 |
| AD date string (field 3, 4) | `2024-08-27` | Already AD; preserved as-is |

During staging, both the raw ROC string (field 74 in tbsslipj, field 41 in tbsslipdtj) and the AD date string are stored verbatim in the staging table. No ROC→AD conversion is performed at this stage. Normalization (Story 16.2) will apply the conversion.

## Batch Idempotency (Atomic Replace on Re-run)

The same atomic-replace semantics established in Story 15.1 apply:

1. Staging runs inside a single PostgreSQL transaction.
2. Before inserting, the run deletes any existing rows for the same `batch_id + table_name` combination.
3. On success, the transaction commits atomically.
4. On failure, the entire transaction rolls back; prior committed state is preserved.
5. A failed run records `attempt_number + 1` in `legacy_import_table_runs`; the prior committed snapshot is retained.
6. Re-running the same batch after a failure replaces the prior failed (or successful) rows.

## Validator Checks

The following checks are enforced during staging:

| Check | Condition | Result |
|-------|-----------|--------|
| Required source file | `tbsslipj.csv` or `tbsslipdtj.csv` missing | Stage run fails with `source_file_missing` |
| Supplier FK (tbsslipj) | `supplier_code` not in `tbscust` WHERE `type='1'` | Table run fails with `fk_violation: supplier_code` |
| Detail FK (tbsslipdtj) | `doc_number` not in staged `tbsslipj` for same batch | Table run fails with `fk_violation: doc_number` |
| Non-empty table | Staged row count = 0 | Table run marked `warning` (empty source), not failed |
| Rerun same-batch | Any prior rows for same `batch_id + table_name` | Prior rows deleted before new COPY |

## File List

- `backend/domains/legacy_import/staging.py` — extended to handle tbsslipj and tbsslipdtj
- `backend/domains/legacy_import/cli.py` — `--table tbsslipj` / `--table tbsslipdtj` flags (already supported generically)
- `backend/domains/legacy_import/validation.py` — FK validation queries for supplier_code and doc_number
- `backend/tests/domains/legacy_import/test_staging.py` — coverage for purchase invoice staging
- `migrations/versions/<new_migration>.py` — if new column handling is required

## Dev Notes

### Repo Reality

- The staging infrastructure from Story 15.1 already supports arbitrary table names via `--table` flags; no new CLI flags are needed for AC1.
- The COPY-based ingestion path in `staging.py` handles any CSV with the same quote-escaping format used in the purchase invoice exports.
- FK validation for `tbsslipj.supplier_code` requires `tbscust` to already be staged (same batch). If `tbscust` has not been staged, the FK check is skipped with a warning logged to `legacy_import_table_runs.error_message`.
- The MANIFEST.md records 9,250 tbsslipj rows and 61,728 tbsslipdtj rows — comfortably within the COPY-based bulk loading path.
- ROC dates in tbsslipdtj appear on every row (not just header), so the normalization step in Story 16.2 will need to handle per-line ROC values.

### Critical Warnings

- Do **not** convert ROC dates during staging — preserve the raw values for Story 16.2 normalization to handle.
- Do **not** skip the supplier FK validation; tbsslipj rows with invalid supplier_code indicate data quality issues in the source export.
- Product codes in tbsslipdtj may reference non-stock items (e.g., '0013' = freight expense). Do not assume all product_code values reference tbsstock — validate against the product mapping table during Story 16.2 normalization, not here.
- The `roc_date` field (field 74 in tbsslipj, field 41 in tbsslipdtj) is the authoritative ROC-encoded date; the AD `date` field (field 3) appears to already be converted in the exported CSVs and should not be trusted as the sole date source.

### Implementation Direction

- Reuse the existing `--table` flag pattern; no new CLI subcommands needed.
- Add FK validation as a post-COPY check in `staging.py` (or a new `validate_stage_fk` helper), run within the same transaction so rollback applies.
- Log the FK orphan list to `legacy_import_table_runs.error_message` in the same format used by other validation failures.
- The existing `StageBatchResult` and `StageTableResult` dataclasses in `staging.py` are sufficient; no new result types needed.

### Validation Follow-up

- Stage tbscust first (as in Epic 15), then stage tbsslipj and tbsslipdtj in the same batch to enable FK validation.
- After staging, manually verify: `SELECT supplier_code, COUNT(*) FROM raw_legacy.tbsslipj GROUP BY supplier_code HAVING COUNT(*) > 1;` to confirm multi-line invoices are captured.
- Confirm that tbsslipdtj rows with non-stock product codes (e.g., '0013') are staged without error — these are expected and will be resolved in Story 16.2 normalization via the product mapping table.

## Dev Agent Record

### Agent Model Used

(claude-sonnet-4-6 — worker-2)

### Completion Notes List

- 2026-04-05: Created Story 16.1 implementation artifact following 15-1-raw-legacy-staging-import.md structure, adapted for tbsslipj (9,250 rows) and tbsslipdtj (61,728 rows) purchase invoice tables.
- Documented the actual CSV field layout for both tables based on MANIFEST.md, RELATIONSHIPS.md, and live CSV inspection (tbsslipj: doc_number as source key, supplier_code FK to tbscust(type='1'); tbsslipdtj: composite doc_number+line_no key, FK to tbsslipj.doc_number).
- Specified ROC date fields (field 74 in header, field 41 in detail) to be preserved verbatim during staging per AC1.
- Specified FK validation checks as post-COPY queries within the same transaction boundary.
- Specified atomic replace on same-batch rerun using the same pattern as Story 15.1.
- Flagged that product_code in tbsslipdtj may reference non-stock items (expenses) — validation deferred to Story 16.2 normalization.
