# Efficient Legacy Refresh Architecture

## Why The Current Refresh Feels Slow

The current scheduled refresh path is intentionally a full rebaseline path, not a delta-update path.

Today the control flow is:

1. `scripts.run_scheduled_legacy_shadow_refresh` calls `scripts.run_legacy_refresh`
2. `run_legacy_refresh` performs `live-stage`, `normalize`, `map-products`, `canonical-import`, validation, stock backfills, and reconciliation
3. `--lookback-days` only scopes the stock backfill scripts after validation; it does not reduce how much source data is staged, normalized, or canonically imported

This means a run that is operationally described as an update still behaves like a full refresh for the main import pipeline.

That is why a two-day expectation and the current runtime shape do not match.

## Current Architectural Constraints

The current implementation surfaces make a date-filter patch unsafe as the primary fix.

### Full-Refresh Wrapper

- `backend/scripts/run_scheduled_legacy_shadow_refresh.py` directly invokes `run_legacy_refresh(...)`
- It does not execute a separate incremental runner
- It reseeds incremental state after an eligible full refresh, but it does not consume incremental state to perform delta work

### Live Stage

- `backend/domains/legacy_import/staging.py` stages all discovered source tables when no explicit table subset is supplied
- The current reviewed path is oriented around a full source snapshot for the selected schema

### Normalization

- `backend/domains/legacy_import/normalization.py::run_normalization(...)` is batch-aware, but still assumes the staged batch contains the full required table slices for the batch
- It currently expects the product and party foundations to be present before dependent slices can normalize safely

### Canonical Import

- `backend/domains/legacy_import/canonical.py::run_canonical_import(...)` is attempt-aware and batch-aware, but not yet domain-scope-aware or entity-scope-aware
- It walks customers, suppliers, products, warehouses, inventory, sales, and purchase imports as one full batch pipeline

### Incremental Contract

- `backend/domains/legacy_import/incremental_state.py` and `backend/domains/legacy_import/incremental_refresh.py` define the reviewed watermark and replay contract
- That contract is not yet backed by a real executor that stages only changed rows, closes parent-child document families, normalizes only impacted slices, and canonically applies only affected entities

## Core Architecture Decision

The correct fix is to split refresh into two explicitly different operating modes:

1. `Full rebaseline`
   - A correctness backstop
   - Used for bootstrap, drift recovery, schema changes, mapping-rule changes, and periodic trust resets

2. `Incremental update`
   - The normal daily path
   - Stages and processes only changed source slices plus the minimal dependency closure required for correctness

Do not try to make the current full-refresh scheduler behave incrementally through `--lookback-days` or a broad source-date filter. That would leave the pipeline pretending to be delta-aware while normalization and canonical import still assume full-batch semantics.

## Answer To The Rebaseline Question

If the source data truly does not change, we should not re-import unchanged rows on every run.

But a periodic rebaseline still matters until the system can prove all of the following for every supported domain:

- the source exposes a trustworthy mutation cursor or replayable business cursor
- late-arriving corrections are captured by the replay window
- mapping-rule changes and code-resolution changes can be replayed deterministically
- validation and reconciliation remain clean after incremental-only operation

So the architecture should change from `full refresh every update` to `incremental by default, full rebaseline by policy`.

For the current repo state, the practical recommendation is:

- Daily incremental updates
- Weekly full rebaseline at first
- Later reduce the full rebaseline cadence only after incremental runs demonstrate stable validation and reconciliation over time

## Target Architecture

### 1. Separate Command Surfaces

Keep the current full runner, and add a true incremental runner.

Proposed command surfaces:

- `uv run python -m scripts.run_legacy_refresh ...`
  - Full rebaseline only
- `uv run python -m scripts.run_scheduled_legacy_shadow_refresh ...`
  - Scheduler for full rebaseline cadence only
- `uv run python -m scripts.run_incremental_legacy_refresh ...`
  - New daily delta-update runner
- `uv run python -m scripts.run_scheduled_incremental_legacy_refresh ...`
  - Optional scheduler for daily incremental cadence

The scheduled full wrapper should stop being the operational path for routine small updates.

### 2. Delta Planning Layer

Promote the existing reviewed planner contract into an executable plan.

The new incremental runner should:

1. Load lane state from `_bmad-output/operations/legacy-refresh/state/.../incremental-state.json`
2. Build the plan via `build_incremental_refresh_plan(...)`
3. For each supported domain, resolve:
   - changed source rows since the last successful watermark
   - replay-window rows needed for safety
   - parent-child closure rows needed for correctness
4. Materialize one `delta manifest` artifact per run before any canonical writes happen

That manifest becomes the auditable contract between discovery and execution.

### 3. Delta-Aware Source Adapters

Add reviewed source adapters that can fetch only the affected slices.

Required behavior:

- master domains with a real change timestamp use a watermark cursor
- document domains use business cursors plus replay windows
- when any header or line row changes, the entire document family is included in the delta batch
- inventory deltas operate on `(warehouse_code, product_code)` pairs, not raw table rows in isolation

This should produce changed-key worksets rather than restaging whole tables.

### 4. Batch Model: Full Batch vs Delta Batch

Introduce an explicit batch mode into refresh summaries and state.

Suggested batch metadata fields:

- `batch_mode`: `full` or `incremental`
- `planned_domains`
- `changed_entity_counts`
- `replay_window`
- `watermark_inputs`
- `watermark_outputs`
- `requires_rebaseline`

This prevents operators from confusing a delta update with a full refresh.

### 5. Normalization Refactor

Refactor normalization to accept execution scope instead of assuming one monolithic full batch.

Suggested API direction:

- add `selected_domains`
- add `entity_scope`
- add `batch_mode`

Normalization must support these rules:

- normalize only the domains in scope
- preserve dependency ordering internally
- allow a delta batch to reuse previously trusted master data when the current batch does not include unchanged rows
- regenerate normalized rows only for affected entities or document families

This is the first place where performance gains become real.

### 6. Canonical Import Refactor

Refactor canonical import to work from impacted entities, not only from an implicit full normalized batch.

Suggested API direction:

- add `selected_domains`
- add `entity_scope`
- add `batch_mode`

Canonical behavior should become:

- upsert only impacted customers, suppliers, products, warehouses, inventory tuples, sales documents, and purchase documents
- preserve deterministic IDs and lineage
- reapply full document families for changed sales and purchase documents
- avoid rescanning and rewriting unaffected domains on every daily run

The current `default_discount_percent` incident is a good example of why canonical import needs to remain authoritative and explicit even when scoped down.

### 7. Mapping And Review Scope

Product mapping review should become incremental too.

The delta path should:

- seed or review only newly observed unresolved product codes
- keep previously approved mappings cached and reusable
- mark a batch as review-required only when new unresolved codes appear in the current delta scope

This prevents old unresolved mappings from forcing repeated work on every update.

### 8. Validation And Reconciliation Scope

Validation policy should remain shared, but execution can be narrowed.

Incremental validation should verify:

- delta stage-to-normalized counts for the scoped entities
- unresolved mapping totals for new delta rows
- canonical import failures for the scoped domains
- replay metadata and watermark advancement eligibility

Reconciliation should support two levels:

- `incremental reconciliation` on the affected entities for routine daily updates
- `full reconciliation` during periodic rebaseline runs

Promotion eligibility remains shared across both paths.

### 9. Downstream Derived Data Refresh

Stock backfills and derived repair steps should become target-aware.

Instead of running broad backfill windows after every update, the incremental path should refresh only:

- affected purchase documents
- affected sales documents
- affected `(product_id, warehouse_id)` inventory tuples

Keep the existing full-window backfills for the rebaseline path.

### 10. State And Observability

The state model should tell operators what really failed.

Add or emphasize:

- `root_failed_step`
- `root_error_message`
- `summary_valid`
- `batch_mode`
- `affected_domains`
- `watermark_advanced`
- `rebaseline_reason`

The scheduler should not let `invalid-summary-artifact` become the primary operator-visible diagnosis when a real upstream step already failed.

## When Full Rebaseline Should Still Run

Under the updated architecture, full rebaseline should run when any of these are true:

- first bootstrap for a lane
- schema change in legacy or canonical surfaces
- mapping logic or normalization rules changed
- canonical import logic changed
- watermark state is missing, inconsistent, or stale
- validation or reconciliation drift crosses threshold
- document domains rely on replay heuristics that need a trust reset
- an operator explicitly requests a backstop rebuild

That means full rebaseline stays available and important, but no longer serves as the default answer to every routine update.

## Phased Implementation Plan

### Phase 1: Stop Using The Full Scheduler For Routine Updates

Goal: operational separation.

- keep `run_scheduled_legacy_shadow_refresh` as the full rebaseline scheduler
- document it as rebaseline-only
- add a new incremental runner skeleton that consumes the existing incremental plan/state contract
- add batch-mode fields to summary and state artifacts

### Phase 2: Implement Delta Discovery And Manifests

Goal: cheap source-side change detection.

- add source adapters for changed-row discovery per supported domain
- implement replay-window logic from the existing contract
- materialize a delta manifest artifact per run
- add focused tests for cursor advancement, replay closure, and parent-child expansion

### Phase 3: Make Normalization Delta-Aware

Goal: remove the full-batch assumption.

- add scoped normalization entry points
- reuse existing normalized tables but operate only on affected entities
- prove that unchanged trusted master data does not need to be restaged every run

### Phase 4: Make Canonical Import Delta-Aware

Goal: remove the full import cost.

- add scoped canonical execution per domain
- preserve lineage and attempt accounting
- add targeted retry tests around customer, product, inventory, sales, and purchase slices

### Phase 5: Add Targeted Validation And Derived Refresh

Goal: keep safety while shrinking runtime.

- add incremental validation summaries
- add targeted backfill hooks for affected documents and inventory tuples
- preserve full validation and reconciliation for rebaseline runs

### Phase 6: Tune Rebaseline Policy

Goal: reduce unnecessary full imports without weakening trust.

- start with weekly full rebaseline
- monitor incremental drift and blocked-batch frequency
- only then consider moving the full rebaseline to a less frequent cadence for stable domains

## Recommended Immediate Repo Changes

The next implementation slice should be:

1. Add a new incremental runner instead of modifying `run_scheduled_legacy_shadow_refresh` to pretend it is incremental
2. Extend refresh summaries and lane state with `batch_mode`, affected-domain scope, and root-failure fields
3. Refactor normalization and canonical import signatures to accept scope inputs, even before all domain executors are fully optimized
4. Leave full refresh in place as a separate explicit rebaseline path

This is the smallest architecture change that moves the system toward efficient updates without breaking the reviewed safety model.

## Decision Summary

- Do not keep using the full refresh scheduler for routine daily updates
- Do not treat `lookback-days` as an import-scope control; it is only a backfill-window control in the current design
- Introduce a true incremental runner that consumes the existing watermark contract
- Refactor normalization and canonical import to become scope-aware
- Keep full rebaseline capability, but move it to a policy-driven backstop instead of the default daily path
