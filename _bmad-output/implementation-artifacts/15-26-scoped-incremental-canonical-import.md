---
type: bmad-distillate
sources:
  - "_bmad-output/implementation-artifacts/15-26-scoped-incremental-canonical-import.md"
downstream_consumer: "story development record"
created: "2026-04-24"
token_estimate: 750
parts: 1
---

## Story Overview
- Story 15.26: Scoped Incremental Canonical Import
- Status: review
- Purpose: canonical import consumes incremental entity scope instead of rescanning implicit full batch; delta runs update only impacted canonical records while preserving deterministic lineage

## Problem
- Current canonical import contract shaped like full historical batch; walks customers, suppliers, products, warehouses, inventory, sales, purchase imports as monolithic pass
- Delta batch behaves like broad rewrite unless canonical import becomes domain-aware and entity-aware
- Efficient-refresh architecture doc mandates this refactor

## Solution
- Accept `selected_domains`, `entity_scope`, and `batch_mode=incremental`
- Upsert only impacted masters, inventory tuples, and full document families named by manifest
- Preserve deterministic IDs, lineage, and source-resolution semantics for scoped reruns
- Limit review-required and unresolved-mapping work to newly observed in-scope issues (not replaying old unrelated debt)

## Acceptance Criteria
- AC1: Given `selected_domains`, `entity_scope`, `batch_mode=incremental` → upserts only impacted masters, inventory tuples, sales/purchase document families (not rescanning unrelated domains)
- AC2: Given sales/purchase document in scope → full header+line family plus lineage records rebuilt deterministically without touching unrelated documents
- AC3: Given unresolved mapping/source-resolution issues exist only outside delta scope → do NOT make new batch review-required; only newly observed in-scope unresolved issues surface
- AC4: Given same manifest scope replayed → canonical IDs, lineage, source-resolution transitions remain idempotent
- AC5: Given dependent master entity required by in-scope document/inventory tuple → use scoped handoff and prior trusted state deterministically (not widening batch implicitly)

## Tasks

### Task 1: Refactor canonical-import surface for incremental scope (AC: 1, 2, 5)
- Add `selected_domains`, `entity_scope`, `batch_mode` inputs to shared canonical-import entry point
- Split monolithic pass into domain-aware execution blocks invocable for impacted domains only
- Preserve full document-family replay for sales/purchase-invoice slices

### Task 2: Preserve deterministic lineage and source-resolution for scoped reruns (AC: 2, 4, 5)
- Keep deterministic IDs and lineage keys stable when same delta scope reruns
- Ensure source-resolution state transitions remain lossless and replay-safe under incremental scope
- Avoid implicit widening when dependent masters available from prior trusted state

### Task 3: Scope mapping review and unresolved-issue surfacing (AC: 3)
- Limit review-required outcomes to new unresolved product codes or source-resolution issues seen in current delta scope
- Reuse previously approved mappings and resolved source identities without forcing repeated operator work
- Preserve operator-facing evidence for newly observed unresolved items

### Task 4: Keep canonical summaries and validation inputs incremental-aware (AC: 1-5)
- Emit domain-aware counts for scoped canonical run
- Preserve distinction between impacted vs untouched domains in canonical summary payload
- Ensure downstream validation receives enough metadata to assess only intended scope

### Task 5: Add focused tests and implementation notes (AC: 1-5)
- Add/extend tests for scoped master upserts, document-family reruns, review-required scoping, deterministic rerun behavior
- Document interaction between incremental canonical scope, source-resolution state, prior trusted carryforward data

## Architecture Constraints
- Canonical import must stay authoritative and explicit even when batch scoped down
- Full document families remain unit of correctness for sales/purchase documents
- Incremental canonical scope must NOT introduce second lineage model or second source-resolution state surface
- Story 15.21 moved hold/drain state out of sentinel lineage rows → cleaner state model for incremental reruns

## Implementation Anchors (Primary Backend)
- `backend/domains/legacy_import/canonical.py`
- `backend/domains/legacy_import/source_resolution.py`
- `backend/domains/legacy_import/mapping.py`
- `backend/scripts/run_legacy_refresh.py`
- `backend/scripts/run_incremental_legacy_refresh.py`

## Implementation Guidance
- Reuse manifest-derived `entity_scope` rather than re-querying raw source to decide scope
- Treat dependent master resolution as deterministic lookup against scoped current data plus prior trusted state (not permission to widen run silently)
- Preserve full-batch behavior when `batch_mode=full` and no scope provided

## References
- Epic 15: `../planning-artifacts/epic-15.md`
- Related stories: 15-21 (canonical source-resolution state model refactor), 15-25 (scoped incremental staging/normalization)
- Architecture: `docs/legacy/efficient-refresh-architecture.md`
- Backend modules: canonical.py, source_resolution.py, mapping.py
- Scripts: run_incremental_legacy_refresh.py, run_legacy_refresh.py

## Dev Agent Record
- Agent model: GPT-5.4
- 2026-04-24: Drafted Story 15.26 to formalize scoped canonical import, deterministic rerun behavior, incremental review-required boundaries
