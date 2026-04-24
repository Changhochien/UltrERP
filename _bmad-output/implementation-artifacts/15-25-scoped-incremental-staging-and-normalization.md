# Story 15.25: Scoped Incremental Staging And Normalization

Status: ready-for-dev

## Story

As a platform engineer,
I want incremental runs to stage and normalize only the entities named in the delta manifest,
so that routine freshness updates stop restaging and renormalizing the entire legacy lane.

## Problem Statement

After Story 15.24 records a delta manifest, the main performance win still does not exist until staging and normalization honor that scope. The reviewed live-stage path is still oriented around a full source snapshot, and normalization historically assumed the staged batch contained the complete foundation for every supported domain.

The repo already contains strong anchors for the intended solution in `incremental_stage_adapter.py`, the incremental normalization tests, and runner-side `entity_scope` handoff tests, but Epic 15 still lacks a story artifact that makes the scope contract explicit.

## Solution

Add a manifest-driven staging and normalization slice that:

- narrows live-stage discovery to the source tables touched by the selected domains
- filters source rows by manifest `closure_keys` and fails closed when scope is empty or malformed
- teaches normalization to accept `selected_domains`, `entity_scope`, `batch_mode=incremental`, and prior-batch carryforward inputs
- preserves dependency ordering while reusing previously trusted rows for unchanged foundations

This story is where delta execution becomes materially faster without relaxing correctness.

## Acceptance Criteria

1. Given a delta manifest selects domains and closure keys, when incremental live staging runs, then only rows from the scoped source tables and matching closure keys are staged and the adapter fails rather than falling back to a full-schema projection.
2. Given incremental normalization receives `selected_domains`, `entity_scope`, and `batch_mode=incremental`, when it runs, then it regenerates only the impacted domains while preserving internal dependency ordering.
3. Given unchanged trusted master data is required by the scoped batch, when normalization needs that context, then it carries forward the required rows from the last successful eligible batch ids instead of forcing a full restage.
4. Given the runner hands off the manifest to downstream execution, when `run_legacy_refresh(...)` is invoked, then `entity_scope` and `last_successful_batch_ids` are threaded through the incremental path so scoped staging and normalization can use them deterministically.
5. Given the current scope is empty or malformed for a requested domain, when incremental staging or normalization is invoked, then the run fails loudly with actionable diagnostics instead of silently widening scope.

## Tasks / Subtasks

- [ ] Task 1: Add the manifest-driven live-stage adapter. (AC: 1, 5)
  - [ ] Introduce an incremental stage adapter that narrows discovered tables to the selected domains' source tables.
  - [ ] Filter rows by manifest closure keys and preserve the shared live-stage parsing and encoding path.
  - [ ] Fail loudly when `selected_domains` is empty, a domain lacks closure keys, or a required column mapping is missing.
- [ ] Task 2: Thread manifest scope from the runner into shared refresh execution. (AC: 1, 4)
  - [ ] Build `entity_scope` directly from the delta manifest rather than rediscovering scope later.
  - [ ] Pass `last_successful_batch_ids` for the scoped domains and their required master-data dependencies.
  - [ ] Keep the incremental runner summary explicit about which domains were actually scoped into execution.
- [ ] Task 3: Refactor normalization for scoped incremental batches. (AC: 2, 3, 5)
  - [ ] Add `selected_domains`, `entity_scope`, and `batch_mode` inputs to normalization.
  - [ ] Preserve dependency ordering so scoped inventory, sales, and purchase-invoice slices still see the required upstream entities.
  - [ ] Add carryforward logic that reuses previously trusted normalized rows when the current batch does not restage unchanged data.
- [ ] Task 4: Keep scope handling deterministic and operator-visible. (AC: 1-5)
  - [ ] Record which domains used carryforward and which domains staged fresh source rows.
  - [ ] Preserve the distinction between `planned_domains`, `affected_domains`, and actual staged tables.
  - [ ] Ensure malformed scope remains an explicit failure rather than a soft warning.
- [ ] Task 5: Add focused tests and contract docs. (AC: 1-5)
  - [ ] Add or extend tests for empty-scope rejection, single-domain scope, dependent-master carryforward, and runner handoff of `entity_scope` plus `last_successful_batch_ids`.
  - [ ] Document the positional column mapping contract used to match manifest closure keys to scoped live-source rows.

## Dev Notes

### Context

- `backend/domains/legacy_import/incremental_stage_adapter.py` already describes the intended fail-closed scoped staging behavior.
- `backend/tests/domains/legacy_import/test_incremental_normalization.py` captures the intended normalization contract for `batch_mode=incremental`.
- `backend/tests/test_run_incremental_legacy_refresh.py` already verifies the runner handoff of `entity_scope` and dependent prior-batch ids.

### Architecture Compliance

- The manifest, not raw source rediscovery, must define scope.
- Shared live-stage parsing must remain the only parsing path; the incremental adapter should compose the existing live adapter rather than fork it.
- Normalization must remain dependency-aware even when scoped.

### Implementation Guidance

- Primary backend anchors:
  - `backend/domains/legacy_import/incremental_stage_adapter.py`
  - `backend/domains/legacy_import/normalization.py`
  - `backend/scripts/run_incremental_legacy_refresh.py`
  - `backend/tests/domains/legacy_import/test_incremental_normalization.py`
  - `backend/tests/test_run_incremental_legacy_refresh.py`
- Treat carryforward as a correctness mechanism, not an optimization shortcut; only reuse rows from the last successful eligible batch ids.
- Keep the mapping between manifest closure keys and staged-source positional columns centralized so scoped staging and normalization agree on the same source-row identity contract.

### Testing Requirements

- Cover empty-scope rejection, scoped table selection, dependent master-data carryforward, and scoped normalization domain ordering.
- Verify that out-of-scope domains do not leak stale prior-batch ids into the incremental handoff.
- Ensure incremental normalization rejects incompatible full-batch arguments and vice versa.

### References

- `../planning-artifacts/epic-15.md`
- `../implementation-artifacts/15-24-delta-discovery-and-manifest-contract.md`
- `docs/legacy/efficient-refresh-architecture.md`
- `backend/domains/legacy_import/incremental_stage_adapter.py`
- `backend/domains/legacy_import/normalization.py`
- `backend/scripts/run_incremental_legacy_refresh.py`
- `backend/tests/domains/legacy_import/test_incremental_normalization.py`
- `backend/tests/test_run_incremental_legacy_refresh.py`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- Story draft only; implementation and validation commands not run yet.

### Completion Notes List

- 2026-04-24: Drafted Story 15.25 to bind the manifest contract to fail-closed scoped staging, incremental normalization, and prior-batch carryforward.

### File List

- `_bmad-output/implementation-artifacts/15-25-scoped-incremental-staging-and-normalization.md`