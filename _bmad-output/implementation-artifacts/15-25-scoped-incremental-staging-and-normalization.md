---
type: bmad-distillate
sources:
  - "_bmad-output/implementation-artifacts/15-25-scoped-incremental-staging-and-normalization.md"
downstream_consumer: "story development record"
created: "2026-04-24"
token_estimate: 424
parts: 1
---

## Story Identity
- Story ID: 15.25
- Title: Scoped Incremental Staging And Normalization
- Status: review (from "draft")
- Role: platform engineer
- Value: routine freshness updates stop restaging/renormalizing entire legacy lane

## Problem
- After Story 15.24 delta manifest recorded, main performance win missing until staging/normalization honor scope
- Reviewed live-stage path oriented around full source snapshot
- Normalization historically assumed staged batch contained complete foundation for every domain

## Solution
Manifest-driven staging/normalization slice that:
- Narrows live-stage discovery to source tables touched by selected domains
- Filters source rows by manifest `closure_keys`; fails closed on empty/malformed scope
- Teaches normalization to accept `selected_domains`, `entity_scope`, `batch_mode=incremental`, prior-batch carryforward inputs
- Preserves dependency ordering while reusing previously trusted rows for unchanged foundations

## Acceptance Criteria
- AC1: Delta manifest + scoped domains → incremental staging stages only matching rows; fails closed instead of full-schema fallback
- AC2: Normalization receives `selected_domains`, `entity_scope`, `batch_mode=incremental` → regenerates only impacted domains with internal dependency ordering preserved
- AC3: Required unchanged master data → carryforward from last successful eligible batch ids; no forced full restage
- AC4: `run_legacy_refresh(...)` → threads `entity_scope` and `last_successful_batch_ids` through incremental path deterministically
- AC5: Empty/malformed scope → explicit failure with actionable diagnostics; not silent scope widening

## Tasks
- Task 1: Manifest-driven live-stage adapter (AC1, AC5)
  - Incremental stage adapter narrows discovered tables to selected domains' source tables
  - Filter rows by manifest closure keys; preserve shared live-stage parsing/encoding path
  - Fail loudly when `selected_domains` empty, domain lacks closure keys, or column mapping missing
- Task 2: Thread manifest scope from runner (AC1, AC4)
  - Build `entity_scope` from delta manifest (not late rediscovery)
  - Pass `last_successful_batch_ids` for scoped domains + master-data dependencies
  - Incremental runner summary explicitly lists scoped domains
- Task 3: Refactor normalization for scoped incremental batches (AC2, AC3, AC5)
  - Add `selected_domains`, `entity_scope`, `batch_mode` inputs
  - Preserve dependency ordering for scoped inventory/sales/purchase-invoice slices
  - Add carryforward logic for normalized rows not restaged in current batch
- Task 4: Deterministic scope handling (AC1-5)
  - Record which domains used carryforward vs staged fresh
  - Distinguish `planned_domains`, `affected_domains`, actual staged tables
  - Malformed scope = explicit failure, not soft warning
- Task 5: Tests and contract docs (AC1-5)
  - Empty-scope rejection, single-domain scope, dependent-master carryforward, runner handoff tests
  - Document positional column mapping contract (manifest closure keys → scoped live-source rows)

## Architecture Compliance
- Manifest, not raw source rediscovery, defines scope
- Shared live-stage parsing remains only parsing path; incremental adapter composes existing adapter (no fork)
- Normalization remains dependency-aware even when scoped

## Implementation Anchors
- `backend/domains/legacy_import/incremental_stage_adapter.py`
- `backend/domains/legacy_import/normalization.py`
- `backend/scripts/run_incremental_legacy_refresh.py`
- `backend/tests/domains/legacy_import/test_incremental_normalization.py`
- `backend/tests/test_run_incremental_legacy_refresh.py`
- Carryforward: correctness mechanism; reuse rows from last successful eligible batch ids only
- Mapping between manifest closure keys and staged-source positional columns: centralized (scoped staging + normalization agree on same source-row identity contract)

## Testing Requirements
- Empty-scope rejection
- Scoped table selection
- Dependent master-data carryforward
- Scoped normalization domain ordering
- Out-of-scope domains do not leak stale prior-batch ids
- Incremental normalization rejects incompatible full-batch arguments (and vice versa)

## References
- `../planning-artifacts/epic-15.md`
- `../implementation-artifacts/15-24-delta-discovery-and-manifest-contract.md`
- `docs/legacy/efficient-refresh-architecture.md`

## Dev Agent Record
- Model: GPT-5.4
- Implementation date: 2026-04-24
- Status: implemented and validated

## Validation Results (from completion notes)
- `test_incremental_normalization.py`: 12/12 tests pass
- `test_run_incremental_legacy_refresh.py`: 12/12 tests pass
- `test_normalization.py`: 28/28 tests pass (backward compatibility)
- AC coverage: AC1-AC5 all covered
- Files changed: normalization.py, run_legacy_refresh.py, test_incremental_normalization.py, story artifact
