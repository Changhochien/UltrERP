# Story 15.26: Scoped Incremental Canonical Import

Status: ready-for-dev

## Story

As a platform engineer,
I want canonical import to consume the incremental entity scope instead of rescanning an implicit full batch,
so that delta runs update only the impacted canonical records while preserving deterministic lineage.

## Problem Statement

Even after Story 15.25 narrows staging and normalization, the current canonical import contract is still shaped like a full historical batch. It walks customers, suppliers, products, warehouses, inventory, sales, and purchase imports as one monolithic pass, which means a delta batch would still behave like a broad rewrite unless canonical import becomes domain-aware and entity-aware.

The efficient-refresh architecture doc is explicit that this refactor is mandatory. The existing `canonical.py` module, source-resolution work, and mapping-review workflow are strong anchors, but Epic 15 still needs a story file that makes the scoped canonical contract concrete.

## Solution

Refactor canonical import so it:

- accepts `selected_domains`, `entity_scope`, and `batch_mode=incremental`
- upserts only the impacted masters, inventory tuples, and full document families named by the manifest
- preserves deterministic IDs, lineage, and source-resolution semantics for scoped reruns
- limits review-required and unresolved-mapping work to newly observed in-scope issues instead of replaying old unrelated debt every run

This keeps canonical import authoritative while still making incremental execution materially smaller.

## Acceptance Criteria

1. Given canonical import receives `selected_domains`, `entity_scope`, and `batch_mode=incremental`, when it runs, then it upserts only the impacted masters, inventory tuples, and full sales or purchase document families rather than rescanning unrelated domains.
2. Given a sales or purchase document is in scope, when canonical import replays it, then the full header and line family plus lineage records are rebuilt deterministically for that document without touching unrelated documents.
3. Given unresolved product mapping or source-resolution issues exist only outside the current delta scope, when the current batch runs, then they do not make the new batch review-required; only newly observed in-scope unresolved issues surface for operator action.
4. Given the same manifest scope is replayed, when canonical import reruns, then canonical ids, lineage, and source-resolution transitions remain idempotent.
5. Given a dependent master entity is required by an in-scope document or inventory tuple, when canonical import resolves references, then it uses the scoped handoff and prior trusted state deterministically rather than widening the batch implicitly.

## Tasks / Subtasks

- [ ] Task 1: Refactor the canonical-import surface for incremental scope. (AC: 1, 2, 5)
  - [ ] Add `selected_domains`, `entity_scope`, and `batch_mode` inputs to the shared canonical-import entry point.
  - [ ] Split the monolithic pass into domain-aware execution blocks that can be invoked for only the impacted domains.
  - [ ] Preserve full document-family replay for sales and purchase-invoice slices.
- [ ] Task 2: Preserve deterministic lineage and source-resolution behavior for scoped reruns. (AC: 2, 4, 5)
  - [ ] Keep deterministic ids and lineage keys stable when the same delta scope reruns.
  - [ ] Ensure source-resolution state transitions remain lossless and replay-safe under incremental scope.
  - [ ] Avoid implicit widening when dependent masters are already available from prior trusted state.
- [ ] Task 3: Scope mapping review and unresolved-issue surfacing. (AC: 3)
  - [ ] Limit review-required outcomes to new unresolved product codes or source-resolution issues seen in the current delta scope.
  - [ ] Reuse previously approved mappings and previously resolved source identities without forcing repeated operator work.
  - [ ] Preserve operator-facing evidence for newly observed unresolved items.
- [ ] Task 4: Keep canonical summaries and validation inputs incremental-aware. (AC: 1-5)
  - [ ] Emit domain-aware counts for the scoped canonical run.
  - [ ] Preserve the distinction between impacted domains and untouched domains in the canonical summary payload.
  - [ ] Ensure downstream validation receives enough metadata to assess only the intended scope.
- [ ] Task 5: Add focused tests and implementation notes. (AC: 1-5)
  - [ ] Add or extend tests for scoped master upserts, document-family reruns, review-required scoping, and deterministic rerun behavior.
  - [ ] Document the interaction between incremental canonical scope, source-resolution state, and prior trusted carryforward data.

## Dev Notes

### Context

- `docs/legacy/efficient-refresh-architecture.md` calls out canonical import as not yet domain-scope-aware or entity-scope-aware.
- `backend/domains/legacy_import/canonical.py` remains the authoritative import surface and must stay so even after scope is narrowed.
- Story 15.21 moved hold and drain state out of sentinel lineage rows, which gives incremental canonical reruns a cleaner state model to build on.

### Architecture Compliance

- Canonical import must stay authoritative and explicit even when the batch is scoped down.
- Full document families remain the unit of correctness for sales and purchase documents.
- Incremental canonical scope must not introduce a second lineage model or a second source-resolution state surface.

### Implementation Guidance

- Primary backend anchors:
  - `backend/domains/legacy_import/canonical.py`
  - `backend/domains/legacy_import/source_resolution.py`
  - `backend/domains/legacy_import/mapping.py`
  - `backend/scripts/run_legacy_refresh.py`
  - `backend/scripts/run_incremental_legacy_refresh.py`
- Reuse the manifest-derived `entity_scope` rather than re-querying raw source to decide scope.
- Treat dependent master resolution as a deterministic lookup against scoped current data plus prior trusted state, not as permission to widen the run silently.

### Testing Requirements

- Add focused tests for scoped document replay, deterministic reruns, review-required scoping, and dependency handling.
- Ensure unchanged unresolved issues outside the current scope do not repeatedly block fresh incremental batches.
- Preserve full-batch behavior when `batch_mode=full` and no scope is provided.

### References

- `../planning-artifacts/epic-15.md`
- `../implementation-artifacts/15-21-canonical-source-resolution-state-model-refactor.md`
- `../implementation-artifacts/15-25-scoped-incremental-staging-and-normalization.md`
- `docs/legacy/efficient-refresh-architecture.md`
- `backend/domains/legacy_import/canonical.py`
- `backend/domains/legacy_import/source_resolution.py`
- `backend/domains/legacy_import/mapping.py`
- `backend/scripts/run_incremental_legacy_refresh.py`
- `backend/scripts/run_legacy_refresh.py`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- Story draft only; implementation and validation commands not run yet.

### Completion Notes List

- 2026-04-24: Drafted Story 15.26 to formalize scoped canonical import, deterministic rerun behavior, and incremental review-required boundaries.

### File List

- `_bmad-output/implementation-artifacts/15-26-scoped-incremental-canonical-import.md`