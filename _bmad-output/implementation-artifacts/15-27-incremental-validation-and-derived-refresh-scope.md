# Story 15.27: Incremental Validation And Derived Refresh Scope

Status: review

## Story

As a platform engineer,
I want incremental validation, derived refreshes, and watermark advancement to honor the scoped batch contract,
so that routine delta runs remain trustworthy without paying full-batch repair costs on every update.

## Problem Statement

After Story 15.26 narrows canonical import, the batch is still not production-safe until validation, downstream backfills, and final watermark advancement learn the same scope. The current refresh flow still assumes broad validation and broad post-import repair windows, and a delta run must not advance watermarks simply because discovery or a partial import succeeded.

The efficient-refresh architecture explicitly calls for scoped validation, targeted derived refreshes, and explicit observability fields such as `root_failed_step`, `summary_valid`, `watermark_advanced`, and `rebaseline_reason`. This story closes that contract.

## Solution

Refactor the post-import portion of the pipeline so it:

- validates only the affected domains and entities while reusing the same reviewed promotion-policy semantics
- runs target-aware downstream repair and derived-refresh steps instead of broad lookback windows
- advances watermarks only after the scoped batch produces durable, policy-compatible results
- records incremental-specific observability in lane state and run summaries so operators can distinguish freshness failures from promotion failures

This is the story that turns a scoped incremental batch into an operator-safe lifecycle.

## Acceptance Criteria

1. Given an incremental batch completes scoped import, when validation runs, then it verifies stage-to-normalized and canonical evidence only for the affected domains and entities and emits incremental validation artifacts without treating untouched domains as failures.
2. Given derived refreshes are required after an incremental run, when post-import hooks execute, then they refresh only the affected purchase receipts, invoice unit costs, sales reservations, and inventory tuples rather than broad rebaseline windows.
3. Given the scoped batch validates cleanly and the shared promotion policy remains satisfied, when finalization runs, then only the impacted domain watermarks advance and lane-state artifacts record `batch_mode`, `affected_domains`, `summary_valid`, `watermark_advanced`, and the relevant batch pointers.
4. Given validation blocks, a root step fails, or a summary artifact is invalid, when finalization runs, then no watermark advances and the operator-visible state records `root_failed_step`, `root_error_message`, and `rebaseline_reason` clearly.
5. Given the latest successful shadow batch is still distinct from the promoted working batch, when operators inspect incremental state, then freshness success and promotion eligibility remain visible as separate concepts rather than being conflated.

## Tasks / Subtasks

- [ ] Task 1: Refactor validation for scoped incremental batches. (AC: 1, 4, 5)
  - [ ] Teach validation surfaces to accept incremental scope and report only on the affected domains and entities.
  - [ ] Preserve the same reviewed gate semantics for unresolved mappings, canonical failures, reconciliation blockers, and summary integrity.
  - [ ] Emit machine-readable artifacts that distinguish freshness evidence from promotion readiness.
- [ ] Task 2: Make derived refreshes and repair hooks target-aware. (AC: 2)
  - [ ] Narrow purchase-receipt, invoice-unit-cost, sales-reservation, and related derived refreshes to the current manifest scope.
  - [ ] Preserve full-window repair behavior for full rebaseline runs.
  - [ ] Keep inventory tuple refreshes aligned to the same manifest closure rules used upstream.
- [ ] Task 3: Advance watermarks only after durable scoped success. (AC: 3, 4)
  - [ ] Advance per-domain watermarks only after validation and post-import steps succeed for the affected scope.
  - [ ] Leave prior successful watermark state untouched on blocked or failed batches.
  - [ ] Record when a rebaseline is required instead of allowing an ambiguous partial advance.
- [ ] Task 4: Improve operator observability for incremental runs. (AC: 3-5)
  - [ ] Add or emphasize summary and lane-state fields such as `root_failed_step`, `root_error_message`, `summary_valid`, `batch_mode`, `affected_domains`, `watermark_advanced`, and `rebaseline_reason`.
  - [ ] Preserve the distinction between `latest-run`, `latest-success`, and `latest-promoted` for incremental lanes.
  - [ ] Reuse the shared promotion-policy contract rather than inventing an incremental-only policy.
- [ ] Task 5: Add focused tests and operator documentation. (AC: 1-5)
  - [ ] Cover scoped validation artifacts, target-aware derived refreshes, blocked no-advance behavior, and required-rebaseline outcomes.
  - [ ] Document when operators should force a full rebaseline even though routine updates normally use the incremental path.

## Dev Notes

### Context

- `docs/legacy/efficient-refresh-architecture.md` explicitly separates incremental reconciliation from periodic full reconciliation.
- `backend/scripts/run_legacy_refresh.py` already carries much of the current validation and derived-refresh orchestration that this story must narrow.
- Existing backfill scripts already exist as separate surfaces, which makes them natural targets for scope-aware refactors.

### Architecture Compliance

- Watermarks advance only from durable scoped success, never from discovery alone.
- Promotion eligibility remains shared across full and incremental paths, but freshness success and promotion success stay distinct.
- Full rebaseline remains the correctness backstop when scoped validation or drift says trust must be reset.

### Implementation Guidance

- Primary backend anchors:
  - `backend/domains/legacy_import/validation.py`
  - `backend/scripts/run_legacy_refresh.py`
  - `backend/scripts/run_incremental_legacy_refresh.py`
  - `backend/scripts/legacy_refresh_state.py`
  - `backend/scripts/backfill_purchase_receipts.py`
  - `backend/scripts/backfill_invoice_unit_cost.py`
  - `backend/scripts/backfill_sales_reservations.py`
- Prefer explicit `requires_rebaseline` and `rebaseline_reason` outputs over implicit operator interpretation.
- Keep lane-state publication aligned with the existing `latest-run.json`, `latest-success.json`, and `latest-promoted.json` model.

### Testing Requirements

- Add focused tests for scoped validation, targeted backfills, and blocked no-advance behavior.
- Verify the lane state clearly distinguishes the latest successful shadow batch from the latest promoted working batch.
- Preserve full-batch validation behavior for the nightly rebaseline path.

### References

- `../planning-artifacts/epic-15.md`
- `../implementation-artifacts/15-18-automated-promotion-gate-policy-and-approved-corrections.md`
- `../implementation-artifacts/15-26-scoped-incremental-canonical-import.md`
- `docs/legacy/efficient-refresh-architecture.md`
- `docs/legacy/migration-plan.md`
- `backend/domains/legacy_import/validation.py`
- `backend/scripts/run_legacy_refresh.py`
- `backend/scripts/run_incremental_legacy_refresh.py`
- `backend/scripts/legacy_refresh_state.py`
- `backend/scripts/backfill_purchase_receipts.py`
- `backend/scripts/backfill_invoice_unit_cost.py`
- `backend/scripts/backfill_sales_reservations.py`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- Story draft only; implementation and validation commands not run yet.

### Completion Notes List

- 2026-04-24: Drafted Story 15.27 to close the scoped validation, targeted derived-refresh, and safe watermark-advancement contract for incremental batches.

### File List

- `_bmad-output/implementation-artifacts/15-27-incremental-validation-and-derived-refresh-scope.md`