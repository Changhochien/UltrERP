---
type: bmad-distillate
sources:
  - "_bmad-output/implementation-artifacts/15-24-delta-discovery-and-manifest-contract.md"
downstream_consumer: "story development record"
created: "2026-04-24"
token_estimate: 1340
parts: 1
---

## Story
- ID: 15.24
- Role: platform engineer
- Want: pure delta-discovery layer with append-only manifest before canonical writes
- Need: incremental runs are auditable, replayable, scoped downstream execution

## Problem
- Story 15.23 launches incremental runs; system lacks reviewed way to decide what changed
- Planner contract (15.19) tells runner where to resume but doesn't discover changed rows, expand closures, materialize workset
- Without explicit discovery layer: inconsistent scope, hidden replay drift, accidental watermark advancement from read-only planning

## Solution
- Source-side discovery layer that:
  - Projects changed source rows per domain through caller-supplied source_projection callable
  - Applies reviewed replay-window and late-arriving-correction rules from incremental contract
  - Expands changed rows into closure keys for document families and inventory tuples
  - Writes one append-only delta manifest per run before any stage, normalize, or canonical write
- Manifest = source of truth for scoped execution; must be consumed downstream not recomputed

## Acceptance Criteria
1. Incremental plan exists + discovery runs → each domain projects changed rows using reviewed cursor and replay-window contract; no watermark advancement
2. Inventory/document domain changes → discovery expands workset; manifest carries full closure keys for (warehouse_code, product_code) tuples or whole document families, not raw row fragments
3. Discovery finishes → append-only JSON includes batch_mode, planned/active/no-op domains, per-domain changed-key and closure counts, watermark_in, proposed watermark_out
4. Domain has zero changed rows after replay expansion → manifest marks domain no-op; downstream stories skip it
5. Same source projection replayed in tests → manifest deterministic; discovery pure except explicit manifest artifact write

## Tasks / Status
- [x] Task 1: Pure delta-discovery core (AC: 1, 2, 5)
  - Pure discover_delta(...) surface accepting reviewed plan + caller-supplied source_projection callable
  - Master-domain, inventory, document closure rules from incremental contract
  - Discovery read-only; proposes watermark outputs but never advances them
- [x] Task 2: Live source projections behind pure discovery seam (AC: 1, 2)
  - Live-source projection helpers querying only rows beyond lane watermark or nightly bootstrap anchor
  - Test-friendly projection seam for pure deterministic unit tests/dry-runs
  - Document domains close on whole documents; inventory domains close on warehouse-product tuples
- [x] Task 3: Append-only manifest per incremental run (AC: 3, 4, 5)
  - Manifest JSON materialized before downstream writes
  - Includes per-domain status, resume mode, parent-child rule, replay window, changed keys, closure keys, watermark inputs/proposals
  - Persisted under lane state root or run artifact root for later stage consumption
- [x] Task 4: Integrate manifest into runner output and dry-run (AC: 3, 4)
  - --dry-run surfaces manifest contract without invoking stage, normalize, canonical steps
  - Manifest path threaded into incremental runner summary
  - active_domains and no_op_domains kept distinct for operator diagnosis
- [x] Task 5: Focused tests and contract documentation (AC: 1-5)
  - Master-domain cursor handling, document-family closure, inventory tuple closure, bootstrap mode, no-op domains, deterministic watermark proposals
  - Downstream stories must consume manifest not rediscover from raw source

## Architecture Compliance
- Source discovery pure except manifest artifact write
- Manifest = single source of truth for staging, normalization, canonical import, validation, backfill scope
- Discovery must NOT silently advance watermarks or rewrite lane state

## Implementation Anchors
- `backend/domains/legacy_import/delta_discovery.py`: pure discovery and manifest surface
- `backend/domains/legacy_import/live_delta_projection.py`: real source queries, nightly bootstrap
- `backend/domains/legacy_import/incremental_state.py`: state management
- `backend/scripts/run_incremental_legacy_refresh.py`: runner integration
- Manifest schema: append-only, operator-readable; critical scope metadata not hidden behind derived counters

## Testing
- Master, inventory, sales, purchase-invoice discovery behavior
- Bootstrap-from-nightly-rebaseline
- Deterministic watermark_out_proposed values
- Empty projections → no-op not implicitly active

## References
- Epic 15: `../planning-artifacts/epic-15.md`
- Watermark contract (15.19): `../implementation-artifacts/15-19-incremental-refresh-and-auto-promotion-watermark-contract.md`
- Runner surface (15.23): `../implementation-artifacts/15-23-incremental-legacy-refresh-runner-surface.md`
- Architecture: `docs/legacy/efficient-refresh-architecture.md`

## Dev Record
- Model: GPT-5.4
- Status: reviewed and validated
- Tests added: 4 (test_discover_delta_does_not_mutate_plan, test_discover_delta_applies_header_and_line_closure_for_purchase_invoices, test_manifest_includes_parent_child_batch_rule_and_replay_window, test_discover_delta_is_deterministic_on_rerun)
- Review fix: tightened `discover_delta(...)` so projected rows missing required cursor or closure fields fail closed instead of emitting malformed manifest `closure_keys`
- Regression added: `test_discover_delta_rejects_rows_missing_required_closure_fields`
- Validation: `cd backend && source .venv/bin/activate && python -m pytest tests/domains/legacy_import/test_delta_discovery.py -q` (13 passed)
