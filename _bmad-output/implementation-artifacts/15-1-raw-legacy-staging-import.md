# Story 15.1: Raw Legacy Staging Import

Status: review

## Story

As a migration operator,
I want extracted legacy CSVs loaded into a read-only staging schema,
So that every migration run starts from a reproducible source snapshot inside PostgreSQL.

## Acceptance Criteria

**AC1:** Manifest-driven staging discovery  
**Given** a verified legacy export set is available  
**When** I run the staging import command  
**Then** the pipeline exposes a stable CLI command surface for staging work  
**And** discovers tables from configured export metadata rather than hardcoded absolute paths  
**And** fails fast if required core tables or expected files are missing  
**And** never mutates the source export files

**AC2:** Read-only raw staging with lineage  
**Given** a staging batch starts  
**When** `raw_legacy` tables are created or refreshed  
**Then** the pipeline records source table, source row identity, and batch/run metadata for staged rows  
**And** preserves import status at table and batch scope

**AC3:** Bulk-load path is production-grade  
**Given** the legacy dataset contains 1.1M+ rows  
**When** large tables are imported  
**Then** the loader uses PostgreSQL-native bulk loading or equivalent batch-safe ingestion  
**And** does not ship the PoC's row-by-row insert strategy as the production implementation

**AC4:** Batch reruns are deterministic  
**Given** the same import batch is run again  
**When** the operator reruns the stage command  
**Then** the batch either replaces or versions the staged scope deterministically  
**And** a stage rerun alone cannot create duplicate canonical records

## Tasks / Subtasks

- [x] **Task 1: Establish the production import surface** (AC1, AC2)
  - [x] Create a dedicated `backend/domains/legacy_import/` package instead of extending the research scripts in place
  - [x] Add operator-facing settings in `backend/common/config.py` for export path, batch ID, and optional cutoff scope
  - [x] Introduce a narrow CLI entry point such as `uv run python -m domains.legacy_import.cli stage ...`
  - [x] Treat the CLI subcommands as the stable automation interface for both humans and agent skills

- [x] **Task 2: Add staging-run metadata and schema helpers** (AC2, AC4)
  - [x] Create Alembic-managed import-run metadata tables for batch status, started/completed timestamps, and table-level row counts
  - [x] Add helpers to create or refresh the PostgreSQL `raw_legacy` schema without writing back to the source system
  - [x] Persist lineage fields needed later for replay and discrepancy work

- [x] **Task 3: Implement manifest-aware CSV ingestion** (AC1, AC3)
  - [x] Reuse the PoC's non-standard CSV parsing knowledge, but remove hardcoded absolute paths from the production code path
  - [x] Read file inventory from migration metadata and/or manifest inputs rather than from an inline `IMPORT_TABLES` dict only
  - [x] Support large-table ingestion through PostgreSQL-native bulk loading or a measured equivalent

- [x] **Task 4: Prove safe reruns and failure behavior** (AC4)
  - [x] Add failure handling for missing files, malformed rows, and batch restarts
  - [x] Ensure the same batch scope can be rerun without leaving partial stage state behind
  - [x] Record operator-readable error output for incomplete runs

- [x] **Task 5: Add focused test coverage** (AC1, AC2, AC3, AC4)
  - [x] Add `backend/tests/domains/legacy_import/` coverage for malformed legacy rows, missing required tables, and rerun behavior
  - [x] Add a fixture slice that exercises the weird legacy quoting format
  - [x] Add a measured smoke test proving the production path does not regress to row-by-row PoC inserts

## Dev Notes

### Repo Reality

- There is currently no import domain under `backend/domains/`; the only import logic lives in `research/legacy-data/02-poc/import_legacy.py`.
- The PoC script hardcodes absolute filesystem paths and uses `psycopg2` with `executemany`; that is acceptable as reference material but not as the production design.
- The approved backend stack already includes Alembic, SQLAlchemy 2.x, and `asyncpg`; introduce new database dependencies only if a measured gap remains.

### Critical Warnings

- Do **not** ship hardcoded workstation paths from the research script.
- Do **not** expose raw legacy staging as a public FastAPI route; this is an operator workflow, not an end-user API.
- Do **not** mutate or rewrite the legacy export set during parsing.

### Implementation Direction

- Keep staging orchestration in a dedicated import package and entry point.
- Make the CLI the durable automation boundary; future skills should call the CLI rather than reimplement import steps in markdown.
- Use Alembic for control tables and schema setup; do not rely on ad hoc schema creation alone.
- Treat `raw_legacy` as an internal source-of-truth snapshot for later normalization stories.

### Validation Follow-up

- Add manifest row-count reconciliation at stage time, not only after canonical import.
- Include explicit tests for rerun safety and partial-run cleanup.

### References

- `_bmad-output/planning-artifacts/epics.md` - Epic 15 / Story 15.1 / FR56 / FR61
- `docs/legacy/migration-plan.md` - staging strategy and rollback posture
- `research/legacy-data/02-poc/import_legacy.py` - PoC parser behavior and hardcoded-path anti-patterns
- `legacy-migration-pipeline/extracted_data/MANIFEST.md` - export inventory baseline
- `backend/common/config.py` - operator settings surface
- `backend/common/database.py` - current PostgreSQL / SQLAlchemy integration point
- `migrations/` - Alembic-managed schema changes

## Dev Agent Record

### Agent Model Used

GitHub Copilot (GPT-5.4)

### Completion Notes List

- Story grounded in the current repo reality: research PoC exists, production import surface does not.
- Story intentionally rejects hardcoded paths and row-by-row PoC inserts as production behavior.
- Story now makes the CLI the stable import interface that later skill automation will wrap.
- Added Alembic-managed control tables for import runs plus table-level staging status.
- Implemented a COPY-based raw staging path with manifest-aware discovery and deterministic same-batch replacement.
- Validated the live CLI against `tbscust` and `tbsstock`, then reran the same batch and confirmed control-table replacement semantics (`runs=1`, `table_runs=2`).
- Review follow-up hardened `--tenant-id` parsing so invalid UUID input now exits with an argparse usage error instead of a Python traceback.
- Review follow-up deduplicated repeated `--table` selections before discovery and run metadata persistence so operator retries cannot stage the same table twice in one batch.
- Review follow-up narrowed the Alembic downgrade to drop only the story-owned control tables and only remove `raw_legacy` if the schema is empty, avoiding `DROP SCHEMA ... CASCADE` collateral damage.
- Review redesign moved staging COPY onto the active `AsyncSession` transaction via the underlying asyncpg driver connection, so raw-table DDL, bulk load, and control-table metadata now share one rollback boundary.
- Review redesign versions same-batch reruns with `attempt_number`, preserving the prior committed snapshot on rollback while still recording failed attempts for operators.
- Focused backend validation after the redesign: `.venv/bin/pytest tests/domains/legacy_import/test_cli.py tests/domains/legacy_import/test_staging.py` -> 17 passed, plus a live same-transaction COPY probe through the session-owned asyncpg driver connection.

### File List

- backend/common/config.py
- backend/common/models/__init__.py
- backend/common/models/legacy_import.py
- backend/domains/legacy_import/__init__.py
- backend/domains/legacy_import/cli.py
- backend/domains/legacy_import/staging.py
- backend/tests/domains/legacy_import/__init__.py
- backend/tests/domains/legacy_import/test_cli.py
- backend/tests/domains/legacy_import/test_staging.py
- migrations/versions/ss999uu99v21_create_legacy_import_control_tables.py

### Review Findings

- [ ] [Review][Patch] source_row_number nil → 0 collision on blank doc_number [backend/domains/legacy_import/canonical.py:1484] — fixed: used `row_identity = source_row_number or line_number`
- [x] [Review][Defer] Date parsing loses day second digit for 8-digit all-digit dates [backend/domains/legacy_import/normalization.py:216-217] — deferred, outside this diff's scope
- [x] [Review][Defer] Silent fallback swallowing ValueError with no counter/metric — deferred, pre-existing
- [x] [Review][Defer] Holding rows have no visible drain/recovery path — deferred, pre-existing design concern
- [x] [Review][Defer] "tbsslipdtj" hardcoded literal is opaque — deferred, pre-existing
- [x] [Review][Defer] No per-row error isolation for holding upsert — deferred, pre-existing
- [x] [Review][Defer] receipt_date→invoice_date fallback not flagged as data issue — deferred, pre-existing
- [x] [Review][Defer] No test coverage changes for blank-doc_number routing — deferred, test file not in diff
- [x] [Review][Defer] AC4 batch rerun idempotency not addressed by this fix — deferred, scope question for later story
- [x] [Review][Defer] AC2 lineage only captured in holding path, not main staging — deferred, existing code concern

### Change Log

- 2026-04-05: Implemented Story 15.1 raw legacy staging foundation with CLI entry point, control tables, COPY-based staging, focused tests, and live rerun validation.
- 2026-04-05: Completed BMAD review follow-up for Story 15.1 by hardening CLI UUID validation, deduplicating repeated table selections, tightening downgrade safety, and documenting remaining redesign-level risks.
- 2026-04-05: Completed the long-term redesign for Story 15.1 by moving COPY staging into the `AsyncSession` transaction, versioning rerun attempts, and preserving prior committed state on failed replacements.
