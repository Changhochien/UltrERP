# Story 16.3: Raw Purchase Order Staging

Status: implemented

## Story

As a migration operator,
I want extracted purchase order headers loaded into the raw_legacy staging schema,
So that purchase orders are available for canonical import.

## Acceptance Criteria

**AC1:** Manifest-driven staging discovery for tbsslipo
**Given** a verified legacy export set is available
**When** I run the staging import command with `--table tbsslipo`
**Then** the pipeline discovers tbsslipo.csv from the configured export metadata
**And** fails fast if tbsslipo.csv is missing from the manifest inventory
**And** never mutates the source export files

**AC2:** Raw staging with lineage for purchase orders
**Given** a staging batch for tbsslipo starts
**When** raw_legacy.tbsslipo is created or refreshed
**Then** the pipeline records source table, source row identity (order_number, field 2), and batch/run metadata for every staged row
**And** preserves ROC-encoded dates during staging without AD conversion
**And** records import status at table and batch scope

**AC3:** FK validation against supplier master
**Given** tbsslipo rows are being staged
**When** supplier_code (field 5) is encountered
**Then** the loader validates each supplier_code exists in tbscust.customer_code where type='1'
**And** rows with invalid supplier_code are flagged in the staging status but do not abort the batch
**And** a summary of FK failures is recorded for operator review

**AC4:** Batch reruns are deterministic
**Given** the same import batch is run again
**When** the operator reruns the stage command for tbsslipo
**Then** the existing tbsslipo rows for that batch are replaced atomically
**And** a stage rerun alone cannot create duplicate canonical records

## Tasks / Subtasks

- [x] **Task 1: Stage tbsslipo with CLI surface** (AC1, AC2)
  - [x] Extend `backend/domains/legacy_import/cli.py` to support `--table tbsslipo` targeting the purchase order header CSV
  - [x] Read tbsslipo.csv from the manifest-discovered export directory
  - [x] Bulk-load into raw_legacy.tbsslipo using the same COPY-based path proven in Story 15.1
  - [x] Record source key (order_number, field 2), batch_id, run_id, and import status for every staged row

- [x] **Task 2: Preserve ROC dates at staging time** (AC2)
  - [x] Ensure date fields in tbsslipo are loaded as-is (ROC format: YYY/MM/DD) without transformation
  - [x] Document the ROC date fields in tbsslipo for downstream normalization in Story 16.4

- [x] **Task 3: Validate FK to supplier master** (AC3)
  - [x] After bulk-loading tbsslipo, run a FK validation pass against raw_legacy.tbscust checking customer_code where type='1'
  - [x] Flag rows with unmatched supplier_code in the import_run table_runs status
  - [x] Provide operator-readable output summarizing FK failures

- [x] **Task 4: Prove safe reruns for tbsslipo** (AC4)
  - [x] Reuse the same-transaction COPY pattern from Story 15.1 so same-batch reruns replace atomically
  - [x] Record attempt_number for the batch; preserve prior committed snapshot on rollback

## Dev Notes

### tbsslipo Field Layout

Based on MANIFEST.md and Epic 16 ACs:
- **Field 2**: order_number — primary key, source identity
- **Field 5**: supplier_code — FK to tbscust.customer_code where type='1'
- **ROC date fields**: preserved as-is during staging (converted to AD in Story 16.4 normalization)

### CLI Usage

```bash
uv run python -m domains.legacy_import.cli stage \
  --batch-id <id> \
  --source-dir <dir> \
  --schema raw_legacy \
  --tenant-id <id> \
  --table tbsslipo
```

- `--source-dir` defaults to the configured `LEGACY_EXPORT_DIR` from `backend/common/config.py`
- `--batch-id` is required; use a UUID or human-readable string (e.g., `po-2026-q1`)
- `--tenant-id` is required; must be a valid UUID
- `--table` may be specified multiple times; omitting it stages all tables in the manifest

### Expected Row Count

- **tbsslipo**: 270 rows (Other slip type O — purchase order headers)

### FK Validation Rule

tbsslipo.supplier_code (field 5) must match tbscust.customer_code where tbscust.type='1'. This mirrors the supplier pattern established in Story 15.2 (purchase invoice staging) and Epic 15 normalization.

### Atomic Replace on Re-run

Same-batch reruns of tbsslipo use the same attempt_number versioning mechanism proven in Story 15.1:
1. Begin transaction
2. DELETE existing raw_legacy.tbsslipo rows for this batch_id
3. COPY new rows from tbsslipo.csv
4. Update control tables (table_runs, runs)
5. Commit

If the COPY fails, the transaction rolls back and the prior committed snapshot is preserved.

### References

- `_bmad-output/planning-artifacts/epics.md` - Epic 16 / Story 16.3 / FR63
- `_bmad-output/implementation-artifacts/15-1-raw-legacy-staging-import.md` - Story 15.1 (same staging pattern, COPY-based, atomic reruns)
- `legacy-migration-pipeline/extracted_data/MANIFEST.md` - tbsslipo rows=270, field positions
- `backend/domains/legacy_import/cli.py` - CLI entry point extended for tbsslipo
- `backend/domains/legacy_import/staging.py` - COPY-based staging implementation
- `backend/common/models/legacy_import.py` - control table models

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4.6

### Completion Notes List

- Story 16.3 follows the same COPY-based staging pattern proven in Story 15.1.
- CLI supports `--table tbsslipo` for isolated purchase order staging.
- FK validation against tbscust.customer_code (type='1') mirrors the supplier pattern from Epic 15.
- ROC dates are preserved at staging time; AD conversion is deferred to Story 16.4 normalization.
- Atomic same-batch replace uses the attempt_number versioning mechanism.
- Expected row count: 270 (verified against MANIFEST.md).

### File List

- backend/domains/legacy_import/cli.py (updated for tbsslipo)
- backend/domains/legacy_import/staging.py (no changes needed; tbsslipo uses same COPY path)

### Change Log

- 2026-04-05: Implemented Story 16.3 raw purchase order staging for tbsslipo with CLI surface, FK validation, ROC date preservation, and atomic same-batch replace.
