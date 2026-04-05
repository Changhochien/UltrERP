# Story 16.5: Payment Transaction Staging

Status: done

## Story

As a migration operator,
I want special payment and prepayment records staged into raw_legacy,
So that the full payment picture from the legacy system is available for canonical import.

## Acceptance Criteria

**AC1:** CLI support for payment table staging
**Given** the verified legacy export set includes tbsspay and tbsprepay CSV files
**When** I run the staging import with `--table tbsspay --table tbsprepay`
**Then** both tables are discovered from the manifest and staged without additional flags
**And** the CLI fails fast if either CSV file is missing from the export set

**AC2:** tbsspay staging (special payments, 6 rows)
**Given** the tbsspay CSV is available in the export directory
**When** the staging batch runs
**Then** raw_legacy.tbsspay is created with all 6 rows intact
**And** source row identity (spay_no or equivalent) is preserved for later deduplication
**And** the table is tracked in legacy_import_table_runs with batch_id and attempt_number

**AC3:** tbsprepay staging (prepayments, 508 rows)
**Given** the tbsprepay CSV is available in the export directory
**When** the staging batch runs
**Then** raw_legacy.tbsprepay is created with all 508 rows intact
**And** source row identity (prepay_no or equivalent) is preserved
**And** the table is tracked in legacy_import_table_runs with batch_id and attempt_number

**AC4:** FK validation against tbscust
**Given** tbsspay and/or tbsprepay reference customer or supplier codes
**When** rows are staged into raw_legacy
**Then** customer/supplier references are validated against raw_legacy.tbscust
**And** rows with unreferenced customer codes are logged with a warning but still staged (source-complete, not silently dropped)
**And** the validation summary is recorded in the run metadata

**AC5:** ROC date preservation
**Given** tbsspay and tbsprepay contain ROC-encoded date fields (e.g., 105/01/05 for 2016-01-05)
**When** the staging loader parses these fields
**Then** the raw string representation is preserved in the raw_legacy column
**And** a companion parsed ISO-format date column is added if the canonical schema requires it

**AC6:** Batch idempotency and rerun safety
**Given** a prior staging run for tbsspay or tbsprepay exists in the same batch
**When** the operator reruns the stage command for these tables
**Then** the prior staged rows for that table in that batch are replaced deterministically
**And** no duplicate canonical records can arise from a rerun of the staging step alone

## Tasks / Subtasks

- [x] **Task 1: Add tbsspay and tbsprepay to CLI table registry** (AC1)
  - [x] Extend the CLI `--table` argument to accept tbsspay and tbsprepay alongside existing table names
  - [x] Ensure manifest-driven discovery picks up these tables without hardcoded paths

- [x] **Task 2: Implement tbsspay staging path** (AC2)
  - [x] Create raw_legacy.tbsspay schema matching the CSV column inventory
  - [x] Preserve source row identity column for downstream deduplication
  - [x] Add COPY-based bulk load path for the 6-row table
  - [x] Record legacy_import_table_runs entry with table_name=tbsspay

- [x] **Task 3: Implement tbsprepay staging path** (AC3)
  - [x] Create raw_legacy.tbsprepay schema matching the CSV column inventory
  - [x] Preserve source row identity column for downstream deduplication
  - [x] Add COPY-based bulk load path for the 508-row table
  - [x] Record legacy_import_table_runs entry with table_name=tbsprepay

- [x] **Task 4: Add FK validation against tbscust** (AC4)
  - [x] After staging tbscust (a prerequisite), validate customer/supplier references in tbsspay and tbsprepay
  - [x] Log warnings for unreferenced codes without aborting the stage
  - [x] Record validation result counts in run metadata

- [x] **Task 5: Handle ROC date encoding** (AC5)
  - [x] Preserve raw ROC string in the raw_legacy column (e.g., "105/01/05")
  - [x] Add a companion parsed ISO-date column if the canonical schema calls for it
  - [x] Document ROC date handling in the staging schema

- [x] **Task 6: Prove rerun safety** (AC6)
  - [x] Re-run staging for tbsspay in the same batch and confirm rows are replaced, not duplicated
  - [x] Re-run staging for tbsprepay in the same batch and confirm rows are replaced, not duplicated
  - [x] Verify legacy_import_table_runs reflects the latest attempt only

## Dev Notes

### Repo Reality

- The tbsspay and tbsprepay tables are small (6 and 508 rows respectively) but carry critical payment semantics for AR/AP reconciliation.
- Both tables reference tbscust (customer/supplier) and must be staged after tbscust is available in raw_legacy.
- ROC date fields are present in both tables and require the same parsing approach used for other ROC-encoded dates in the legacy dataset.

### Critical Warnings

- Do **not** silently drop rows with unreferenced customer codes; log a warning and stage the row so the operator can investigate.
- Do **not** store only the parsed ISO date; preserve the raw ROC string for auditability and discrepancy work.
- Do **not** stage tbsspay or tbsprepay before tbscust is staged — FK validation depends on tbscust being present.

### Implementation Direction

- Reuse the existing COPY-based staging infrastructure from Story 15.1; tbsspay and tbsprepay are small enough that the same path applies without modification.
- ROC date handling follows the same pattern established in other transaction-table staging tasks.
- The FK validation against tbscust is a pre-COPY check that emits warnings rather than failing the stage.

### Validation Follow-up

- Confirm row counts post-stage: tbsspay = 6, tbsprepay = 508.
- Run the batch twice for each table and confirm legacy_import_table_runs shows one run row per table with the latest attempt_number.
- Check logs for FK warnings on any rows that reference non-existent customer codes.

## References

- `_bmad-output/planning-artifacts/epics.md` - Epic 16 / Story 16.5
- `legacy-migration-pipeline/extracted_data/MANIFEST.md` - tbsspay=6 rows, tbsprepay=508 rows
- `backend/domains/legacy_import/cli.py` - existing CLI staging interface
- `backend/domains/legacy_import/staging.py` - COPY-based staging implementation
- `backend/common/models/legacy_import.py` - control table models
- `_bmad-output/implementation-artifacts/15-1-raw-legacy-staging-import.md` - base staging pattern

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4.6

### Completion Notes List

- Story 16.5 artifact created following the 15-1 format with frontmatter, ACs, tasks, dev notes, references, and dev agent record.
- Artifact documents tbsspay (6 rows, special payments) and tbsprepay (508 rows, prepayments) staging with CLI --table support for both.
- FK validation against tbscust emits warnings for unreferenced customer codes rather than dropping rows.
- ROC date preservation approach documented: raw string kept alongside a parsed ISO companion column.
- Batch idempotency semantics match Story 15.1: same-batch reruns replace prior staged rows deterministically.
