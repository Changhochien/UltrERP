# Story 15.24: Delta Discovery And Manifest Contract

Status: ready-for-dev

## Story

As a platform engineer,
I want a pure delta-discovery layer that records an append-only manifest before any canonical writes happen,
so that incremental runs are auditable, replayable, and safe to scope downstream execution from.

## Problem Statement

Once Story 15.23 can launch an incremental run, the system still needs a reviewed way to decide what actually changed. The planner contract from Story 15.19 tells the runner where to resume, but it does not itself discover changed source rows, expand parent-child closures, or materialize the executable workset.

Without an explicit discovery and manifest layer, later staging, normalization, canonical import, and validation stories would each be tempted to rediscover source changes independently. That would risk inconsistent scope, hidden replay drift, and accidental watermark advancement from a read-only planning step.

## Solution

Add a source-side discovery layer that:

- projects changed source rows per supported domain through a caller-supplied source projection callable
- applies the reviewed replay-window and late-arriving-correction rules from the incremental contract
- expands changed rows into closure keys for document families and inventory tuples
- writes one append-only delta manifest per run before any stage, normalize, or canonical write occurs

The manifest becomes the source of truth for later scoped execution and must be consumed downstream rather than recomputed.

## Acceptance Criteria

1. Given an incremental plan exists, when discovery runs, then each supported domain projects changed source rows using the reviewed cursor and replay-window contract without advancing any watermark.
2. Given an inventory or document domain changes, when discovery expands the workset, then the manifest carries full closure keys for `(warehouse_code, product_code)` tuples or whole document families rather than raw row fragments.
3. Given discovery finishes, when the manifest is recorded, then the append-only JSON includes `batch_mode`, planned, active, and no-op domains, per-domain changed-key and closure counts, `watermark_in`, and proposed `watermark_out` values.
4. Given a domain has zero changed rows after replay expansion, when the manifest is built, then that domain is marked `no-op` so downstream stories skip it rather than falling back to a full-schema batch.
5. Given the same source projection is replayed in tests, when discovery reruns, then the manifest is deterministic and remains pure except for the explicit write of the manifest artifact itself.

## Tasks / Subtasks

- [ ] Task 1: Add the pure delta-discovery core. (AC: 1, 2, 5)
  - [ ] Introduce a pure `discover_delta(...)` surface that accepts the reviewed plan and a caller-supplied `source_projection` callable.
  - [ ] Support the reviewed master-domain, inventory, and document closure rules from the incremental contract.
  - [ ] Keep discovery read-only: it may propose watermark outputs, but it must not advance them.
- [ ] Task 2: Implement live source projections behind the pure discovery seam. (AC: 1, 2)
  - [ ] Add reviewed live-source projection helpers that query only rows beyond the lane watermark or nightly bootstrap anchor.
  - [ ] Preserve a test-friendly projection seam so unit tests and dry-runs stay pure and deterministic.
  - [ ] Ensure document domains close on whole documents and inventory domains close on warehouse-product tuples.
- [ ] Task 3: Record one append-only manifest per incremental run. (AC: 3, 4, 5)
  - [ ] Materialize a manifest JSON before downstream writes begin.
  - [ ] Include per-domain status, resume mode, parent-child rule, replay window, changed keys, closure keys, and watermark inputs and proposals.
  - [ ] Persist the manifest under the lane state root or run artifact root where later stages can consume it directly.
- [ ] Task 4: Integrate the manifest into runner output and dry-run behavior. (AC: 3, 4)
  - [ ] Ensure `--dry-run` surfaces the manifest contract without invoking stage, normalize, or canonical steps.
  - [ ] Thread the manifest path into the incremental runner summary.
  - [ ] Keep `active_domains` and `no_op_domains` distinct for operator diagnosis.
- [ ] Task 5: Add focused tests and contract documentation. (AC: 1-5)
  - [ ] Cover master-domain cursor handling, document-family closure, inventory tuple closure, bootstrap mode, no-op domains, and deterministic watermark proposals.
  - [ ] Document that downstream stories must consume the manifest rather than rediscovering from raw source.

## Dev Notes

### Context

- `backend/domains/legacy_import/delta_discovery.py` already contains the intended pure discovery and manifest surface.
- `backend/domains/legacy_import/live_delta_projection.py` is the natural anchor for real source queries and nightly bootstrap behavior.
- `docs/legacy/efficient-refresh-architecture.md` explicitly calls the delta manifest the auditable contract between discovery and execution.

### Architecture Compliance

- Keep source discovery pure except for writing the manifest artifact.
- Treat the manifest as the single source of truth for later staging, normalization, canonical import, validation, and backfill scope.
- Do not let discovery silently advance watermarks or rewrite lane state.

### Implementation Guidance

- Primary backend anchors:
  - `backend/domains/legacy_import/delta_discovery.py`
  - `backend/domains/legacy_import/live_delta_projection.py`
  - `backend/scripts/run_incremental_legacy_refresh.py`
  - `backend/domains/legacy_import/incremental_state.py`
- The manifest schema should stay append-only and operator-readable; avoid hiding critical scope metadata behind derived counters alone.
- Preserve the source projection seam so tests can inject `explicit_no_delta_projection` or other synthetic projections without opening a live source connection.

### Testing Requirements

- Add focused tests for master, inventory, sales, and purchase-invoice discovery behavior.
- Verify bootstrap-from-nightly-rebaseline behavior and deterministic `watermark_out_proposed` values.
- Ensure domains with empty projections become `no-op` rather than implicitly active.

### References

- `../planning-artifacts/epic-15.md`
- `../implementation-artifacts/15-19-incremental-refresh-and-auto-promotion-watermark-contract.md`
- `../implementation-artifacts/15-23-incremental-legacy-refresh-runner-surface.md`
- `docs/legacy/efficient-refresh-architecture.md`
- `backend/domains/legacy_import/delta_discovery.py`
- `backend/domains/legacy_import/live_delta_projection.py`
- `backend/domains/legacy_import/incremental_state.py`
- `backend/scripts/run_incremental_legacy_refresh.py`
- `backend/tests/test_run_incremental_legacy_refresh.py`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- Story draft only; implementation and validation commands not run yet.

### Completion Notes List

- 2026-04-24: Drafted Story 15.24 to formalize the pure discovery and delta-manifest contract already referenced by the incremental runner and the efficient-refresh architecture.

### File List

- `_bmad-output/implementation-artifacts/15-24-delta-discovery-and-manifest-contract.md`