# Story 15.3: Product Variant Mapping Workflow

Status: ready-for-dev

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

- [ ] **Task 1: Create production mapping tables and seed path** (AC1, AC2)
  - [ ] Add Alembic-managed mapping tables and supporting indexes for legacy product resolution
  - [ ] Seed exact matches from the verified product-code field
  - [ ] Persist analyst-facing metadata such as `resolution_type`, `confidence`, and notes

- [ ] **Task 2: Encode UNKNOWN fallback behavior** (AC3)
  - [ ] Add the documented `UNKNOWN` placeholder product to the canonical import flow
  - [ ] Ensure unresolved product variants use the fallback intentionally rather than failing FK checks or disappearing
  - [ ] Preserve lineage so unresolved transactions can still be reviewed later

- [ ] **Task 3: Add an analyst review loop** (AC2, AC4)
  - [ ] Expose a reviewed CLI command for exporting/importing mapping-review candidates so a future skill can call it safely
  - [ ] Provide a repeatable import/export path for analyst-reviewed mappings
  - [ ] Seed fuzzy candidates as proposals only, not auto-approved mappings
  - [ ] Record approval source and timestamp when a candidate becomes authoritative

- [ ] **Task 4: Add regression coverage for the legacy field confusion** (AC1, AC3, AC4)
  - [ ] Add a test proving the workflow targets the real product-code field and not the historical warehouse-code mistake
  - [ ] Add tests for exact match, analyst-approved variant map, and unresolved fallback cases
  - [ ] Add a regression protecting the corrected 190-code / 523-row baseline from being overwritten by obsolete PoC comments

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
