# Story 15.3: Product Variant Mapping Workflow

Status: done

## Story

As a data analyst,
I want unresolved legacy product variants managed through an explicit mapping workflow,
So that transaction history is preserved without claiming false product certainty.

## Acceptance Criteria

**AC1:** Correct orphan detection uses the verified product field  
**Given** staged sales-detail rows are analyzed for missing product matches  
**When** the mapping workflow computes orphans  
**Then** it compares the verified product-code field rather than the warehouse-code field  
**And** uses the corrected orphan profile as the production baseline, not the obsolete 660-code claim

**AC2:** Mapping records are auditable  
**Given** a legacy product code is exact-matched, analyst-approved, or unresolved  
**When** the mapping phase or review command updates the mapping table  
**Then** the resolution type, confidence, and review notes are stored explicitly  
**And** later imports can trace why a legacy code resolved the way it did

**AC3:** Unresolved variants preserve transaction history  
**Given** a product code remains unresolved after analyst review  
**When** historical transactions are imported  
**Then** the row is assigned to the documented `UNKNOWN` fallback product  
**And** the transaction is preserved for reconciliation  
**And** the fallback remains visibly non-authoritative for product analytics

**AC4:** Analyst review does not auto-approve fuzzy guesses  
**Given** fuzzy-match candidates are available  
**When** the workflow seeds them for review  
**Then** they remain analyst-review candidates until explicitly approved  
**And** the system does not silently collapse variants into base SKUs without provenance

## Tasks / Subtasks

- [x] **Task 1: Create production mapping tables and seed path** (AC1, AC2)
  - [x] Add Alembic-managed mapping tables and supporting indexes for legacy product resolution
  - [x] Seed exact matches from the verified product-code field
  - [x] Persist analyst-facing metadata such as `resolution_type`, `confidence`, and notes

- [x] **Task 2: Encode UNKNOWN fallback behavior** (AC3)
  - [x] Add the documented `UNKNOWN` placeholder product to the canonical import flow
  - [x] Ensure unresolved product variants use the fallback intentionally rather than failing FK checks or disappearing
  - [x] Preserve lineage so unresolved transactions can still be reviewed later

- [x] **Task 3: Add an analyst review loop** (AC2, AC4)
  - [x] Expose a reviewed CLI command for exporting/importing mapping-review candidates so a future skill can call it safely
  - [x] Provide a repeatable import/export path for analyst-reviewed mappings
  - [x] Seed fuzzy candidates as proposals only, not auto-approved mappings
  - [x] Record approval source and timestamp when a candidate becomes authoritative

- [x] **Task 4: Add regression coverage for the legacy field confusion** (AC1, AC3, AC4)
  - [x] Add a test proving the workflow targets the real product-code field and not the historical warehouse-code mistake
  - [x] Add tests for exact match, analyst-approved variant map, and unresolved fallback cases
  - [x] Add a regression protecting the corrected 190-code / 523-row baseline from being overwritten by obsolete PoC comments

### Review Findings

- [x] [Review][Patch] Make analyst review imports atomic and keep the `UNKNOWN` placeholder materialized during review imports [backend/domains/legacy_import/mapping.py]
- [x] [Review][Patch] Reject batch-mismatched or duplicate analyst review rows before applying any mapping changes [backend/domains/legacy_import/mapping.py]
- [x] [Review][Defer] Partial selected-table reruns can drop unrelated staged tables [backend/domains/legacy_import/staging.py] — deferred, pre-existing 15.1 staging semantics

## Dev Notes

### Repo Reality

- The PoC analysis is useful, but parts of the research scripts and SQL still contain the superseded 660-orphan narrative.
- Production code must treat `docs/legacy/migration-plan.md` and `research/legacy-data/03-findings.md` as the authoritative source for orphan logic.

### Critical Warnings

- Do **not** compare `warehouse_code` to the product master again.
- Do **not** auto-accept fuzzy matches; that would fabricate data certainty.
- Do **not** drop unresolved transactions just to satisfy foreign keys.

### Implementation Direction

- Keep resolution policy explicit and operator-reviewable.
- Route mapping refresh and review export/import through stable CLI subcommands instead of one-off SQL snippets.
- Prefer one authoritative mapping path shared by all downstream imports rather than per-import heuristics.
- Preserve unresolved rows via `UNKNOWN` plus lineage so Epic 13 reconciliation can still flag them appropriately.

### Validation Follow-up

- Include at least one regression fixture that would have failed under the old field-confusion logic.
- Validate exact-match seeding and unresolved fallback counts independently from full transaction import.

### References

- `_bmad-output/planning-artifacts/epics.md` - Epic 15 / Story 15.3 / FR58
- `docs/legacy/migration-plan.md` - product-code resolution strategy
- `research/legacy-data/03-findings.md` - corrected orphan profile and fuzzy-match context
- `research/legacy-data/02-poc/resolve_product_codes.py` - analysis approach and obsolete-comment pitfalls
- `research/legacy-data/02-poc/mapping_table.sql` - reference DDL to adapt, not copy verbatim
- `research/legacy-data/02-poc/unknown_product.sql` - fallback-product reference

## Dev Agent Record

### Agent Model Used

GitHub Copilot (GPT-5.4)

### Completion Notes List

- Story explicitly guards against the legacy field-confusion mistake.
- Story keeps analyst approval and `UNKNOWN` fallback auditable instead of heuristic-only.
- Added `raw_legacy.product_code_mapping` and `raw_legacy.product_code_mapping_candidates` plus CLI commands for mapping seed, review export, and review import.
- Exact matches now seed only from `tbsslipdtx.col_7`; fuzzy proposals remain analyst-review candidates, and unresolved codes deliberately land on `UNKNOWN` with lineage preserved.
- Live validation on batch `batch-153-live-20260405` staged `tbscust`, `tbsstock`, `tbsstkhouse`, and `tbsslipdtx`, then normalized `1022` parties, `6611` products, `1` warehouse, and `6588` inventory rows before mapping `6111` product codes with `100` review candidates and the corrected `190` orphan codes / `523` orphan rows baseline.
- Live analyst-review validation exported the real review CSV, imported one approved candidate, and verified `raw_legacy.product_code_mapping` persisted `legacy_code=000`, `target_code=0000`, `resolution_type=analyst_review`, `approval_source=review-import`, and `approved_by=live-analyst-check`.
- Runtime hardening for the live `tbsslipdtx` path removed COPY timeout failures, batched large COPY work, and added forward migrations to reconcile `legacy_import_runs` attempt-number and uniqueness drift on already-created databases.
- Code-review follow-up wrapped `import_product_mapping_review()` in an asyncpg transaction, re-materializes `UNKNOWN` during review imports, and rejects batch-mismatched or duplicate decision rows before any upsert runs.
- Post-review validation passed with `uv run pytest tests/domains/legacy_import` (`41 passed`), `uv run ruff check domains/legacy_import/mapping.py tests/domains/legacy_import/test_mapping.py`, and a second live review import/query showing `approved_by=live-analyst-check-2` on the persisted analyst-reviewed mapping.

### File List

- backend/domains/legacy_import/__init__.py
- backend/domains/legacy_import/cli.py
- backend/domains/legacy_import/mapping.py
- backend/domains/legacy_import/staging.py
- backend/tests/domains/legacy_import/test_cli.py
- backend/tests/domains/legacy_import/test_mapping.py
- backend/tests/domains/legacy_import/test_staging.py
- migrations/versions/ss999uu99v21_create_legacy_import_control_tables.py
- migrations/versions/tt111vv11w32_create_legacy_product_mapping_tables.py
- migrations/versions/uu222ww22x43_backfill_legacy_import_attempt_number.py
- migrations/versions/vv333xx33y54_fix_legacy_import_run_unique_constraint.py

### Change Log

- 2026-04-05: Implemented Story 15.3 with auditable legacy product mapping tables, exact-match seeding from `tbsslipdtx.col_7`, `UNKNOWN` fallback handling, and CLI review export/import commands.
- 2026-04-05: Completed Story 15.3 live validation by hardening large-table COPY behavior, repairing `legacy_import_runs` schema drift on existing databases, and proving analyst review import/export against real legacy data.
- 2026-04-05: Completed Story 15.3 code-review follow-up by making analyst review imports atomic, validating review CSV batch/duplicate semantics, and recording the inherited partial-rerun staging issue as deferred work.
