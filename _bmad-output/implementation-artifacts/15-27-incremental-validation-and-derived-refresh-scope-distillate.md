---
type: bmad-distillate
sources:
  - "_bmad-output/implementation-artifacts/15-27-incremental-validation-and-derived-refresh-scope.md"
downstream_consumer: "code-review"
created: "2026-04-24"
token_estimate: 850
parts: 1
---

## Story Identity
- Story 15.27: Incremental Validation And Derived Refresh Scope
- Role: Platform engineer; wants scoped batch contract honored for delta runs
- Problem: Current refresh flow assumes broad validation/repair; delta runs must not advance watermarks on discovery alone

## Acceptance Criteria

### AC1: Incremental Validation Scope
- Verifies stage-to-normalized and canonical evidence ONLY for affected domains/entities
- Emits incremental validation artifacts
- Untouched domains NOT treated as failures
- Same promotion-policy semantics reused

### AC2: Target-Aware Derived Refreshes
- Post-import hooks refresh ONLY affected purchase receipts, invoice unit costs, sales reservations, inventory tuples
- NOT broad rebaseline windows
- Narrow to current manifest scope

### AC3: Safe Watermark Advancement
- Only impacted domain watermarks advance after scoped success
- Lane-state records: batch_mode, affected_domains, summary_valid, watermark_advanced, batch pointers
- Requires: scoped batch validates cleanly + shared promotion policy satisfied

### AC4: Blocked No-Advance
- If validation blocks, root step fails, or summary invalid → NO watermark advances
- Lane-state records: root_failed_step, root_error_message, rebaseline_reason
- Explicit, not implicit operator interpretation

### AC5: Freshness vs Promotion Distinction
- Latest successful shadow batch distinct from promoted working batch
- Freshness success and promotion eligibility visible as SEPARATE concepts
- NOT conflated

## Tasks

### Task 1: Scoped Validation Refactor (AC1,4,5)
- Teach validation surfaces to accept incremental scope
- Report only on affected domains/entities
- Preserve gate semantics: unresolved mappings, canonical failures, reconciliation blockers, summary integrity
- Emit machine-readable artifacts distinguishing freshness evidence from promotion readiness

### Task 2: Target-Aware Derived Refreshes (AC2)
- Narrow purchase-receipt, invoice-unit-cost, sales-reservation refreshes to manifest scope
- Preserve full-window repair for full rebaseline runs
- Inventory tuple refreshes aligned to manifest closure rules

### Task 3: Safe Watermark Advancement (AC3,4)
- Advance per-domain watermarks ONLY after validation + post-import steps succeed for affected scope
- Leave prior successful watermark state untouched on blocked/failed batches
- Record when rebaseline required vs ambiguous partial advance

### Task 4: Operator Observability (AC3-5)
- Add/emphasize summary and lane-state fields:
  - root_failed_step, root_error_message, summary_valid, batch_mode, affected_domains, watermark_advanced, rebaseline_reason
- Preserve distinction: latest-run vs latest-success vs latest-promoted (incremental lanes)
- Reuse shared promotion-policy contract (not incremental-only)

### Task 5: Tests + Documentation (AC1-5)
- Cover: scoped validation artifacts, target-aware derived refreshes, blocked no-advance behavior, required-rebaseline outcomes
- Document when to force full rebaseline vs routine incremental

## Backend Anchors
- backend/domains/legacy_import/validation.py
- backend/scripts/run_legacy_refresh.py
- backend/scripts/run_incremental_legacy_refresh.py
- backend/scripts/legacy_refresh_state.py
- backend/scripts/backfill_purchase_receipts.py
- backend/scripts/backfill_invoice_unit_cost.py
- backend/scripts/backfill_sales_reservations.py

## Architecture Constraints
- Watermarks advance ONLY from durable scoped success (never discovery alone)
- Promotion eligibility shared across full and incremental paths
- Freshness success ≠ promotion success (distinct)
- Full rebaseline = correctness backstop for scoped validation failures or drift

## State Files
- latest-run.json
- latest-success.json
- latest-promoted.json
- Lane-state model preserved

## References
- epic-15.md
- 15-18-automated-promotion-gate-policy.md
- 15-26-scoped-incremental-canonical-import.md
- docs/legacy/efficient-refresh-architecture.md
- docs/legacy/migration-plan.md
