# Story 15.15: Legacy Refresh Orchestrator

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a migration operator,
I want one reviewed command to run the full live refresh workflow in the correct order,
so that shadow refreshes are repeatable and do not depend on manual step sequencing.

## Acceptance Criteria

1. Given `LEGACY_DB_*`, tenant, and schema settings are configured, when I run the refresh orchestrator with a batch id, then it executes the reviewed workflow in this exact order: `live-stage`, `normalize`, `map-products`, optional `export-product-review`, optional `import-product-review`, `canonical-import`, `validate-import`, `backfill_purchase_receipts`, `backfill_sales_reservations`, and `verify_reconciliation`.
2. Given the basic shadow-refresh path does not include an approved analyst review import, when `map-products` leaves unresolved mappings, then the orchestrator exports the review CSV to a deterministic artifact path, records that review is still required, continues the shadow refresh using the existing `UNKNOWN` fallback behavior, and marks the batch as not promotion-ready.
3. Given `canonical-import` runs, when the orchestrator writes its structured summary, then the summary includes at minimum: `batch_id`, `tenant_id`, `schema_name`, `source_schema`, orchestrator run id, started/completed timestamps, ordered per-step results, `canonical_attempt_number`, validation JSON/Markdown paths, `reconciliation_gap_count`, `reconciliation_threshold_used`, analyst-review gate flags, `promotion_readiness`, a `promotion_gate_status` block, `correction_proposals_path` (nullable), final disposition, exit code, `failed_step` (nullable), and `last_completed_step`.
4. Given any step before reconciliation fails, when the orchestrator aborts, then it exits non-zero immediately, preserves the partial imported state for investigation instead of attempting a global rollback, records the partial-failure shape in the summary artifact, and does not promote the batch automatically.
5. Given `validate-import` returns a blocked batch, when that result is observed, then the orchestrator stops before stock-history follow-up steps, records `promotion_readiness=false`, and exits non-zero with validation as the blocking gate.
6. Given the stock follow-up steps run, when `verify_reconciliation` reports more flagged `(product_id, warehouse_id)` gaps than the configured reconciliation threshold, then the orchestrator completes the remaining post-import evidence capture, records `reconciliation-blocked` status in the summary, and exits non-zero without promoting the batch.
7. Given the same `--batch-id` is rerun, when the orchestrator executes again, then it relies on the existing batch-scoped idempotent import/backfill behavior, writes a new summary artifact for the new orchestrator run instead of overwriting the previous one, and does not create duplicate promotion metadata.
8. Given this story delivers a reviewed operator command, when docs and tests are inspected, then the command is documented alongside the existing legacy-import workflow and focused automated coverage proves step ordering, summary generation, stop-on-failure behavior, and same-batch rerun reporting.

## Tasks / Subtasks

- [x] Task 1: Define the orchestrator command contract and step sequence (AC: 1, 3)
  - [x] Add a new backend-owned command at `backend/scripts/run_legacy_refresh.py`.
  - [x] Define explicit CLI arguments at minimum for `--batch-id`, `--tenant-id`, `--schema`, `--source-schema`, `--lookback-days`, and `--reconciliation-threshold`.
  - [x] Define `--lookback-days` as the value passed through to the stock follow-up scripts; default it to `10000` so the reviewed default behaves like a full-history shadow refresh instead of silently using each script's `180`-day local default.
  - [x] Define `--reconciliation-threshold` as a non-negative integer count of flagged `(product_id, warehouse_id)` reconciliation gaps returned by `verify_reconciliation.py`; default it to `0` for strict gating, with operator override allowed.
  - [x] Keep batch promotion, scheduling, and incremental watermark logic out of this story; this story stops at refresh + evidence generation.

- [x] Task 2: Reuse the existing live import pipeline instead of reimplementing it (AC: 1, 4)
  - [x] Reuse the existing backend import entry points already backing the CLI:
    - `run_live_stage_import`
    - `run_normalization`
    - `run_product_mapping_seed`
    - `run_canonical_import`
    - `validate_import_batch`
  - [x] Make the mapping/review sequence explicit:
    - `map-products` always runs
    - `export-product-review` runs when unresolved mappings exist and no approved import file was supplied
    - `import-product-review` runs only when an approved review CSV path was supplied
  - [x] For the basic shadow-refresh path, continue with the existing `UNKNOWN` fallback if review is still pending, but set review gate flags and `promotion_readiness=false`.
  - [x] Preserve the current live-source semantics from Story 15.12 and the validation boundary from Story 15.5.

- [x] Task 3: Integrate the stock-history follow-up scripts required for a usable shadow dataset (AC: 1, 2, 3)
  - [x] Reuse the existing backfill surfaces only after `validate-import` returns a non-blocked result:
    - `backend/scripts/backfill_sales_reservations.py`
    - `backend/scripts/backfill_purchase_receipts.py`
  - [x] Reuse the read-only reconciliation reporter:
    - `backend/scripts/verify_reconciliation.py`
  - [x] Capture the reconciliation gap count in the orchestrator summary and fail the run when the configured threshold is exceeded.
  - [x] Make the fail behavior explicit: pre-reconciliation failures are fail-fast; reconciliation threshold failure occurs after post-import evidence capture and returns a non-zero final disposition.
  - [x] Explicitly exclude correction proposal generation and correction application from this story's automatic flow.

- [x] Task 4: Emit one structured run summary artifact per orchestrator execution (AC: 2, 3)
  - [x] Write a machine-readable summary artifact under a durable repo path such as `_bmad-output/operations/legacy-refresh/` or another approved operations artifact directory.
  - [x] Include, at minimum:
    - `batch_id`
    - `tenant_id`
    - `schema_name`
    - `source_schema`
    - orchestrator run id
    - start and end timestamps
    - ordered per-step status
    - `failed_step` and `last_completed_step`
    - validation JSON/Markdown artifact paths
    - `canonical_attempt_number`
    - reconciliation gap count
    - `reconciliation_threshold_used`
    - analyst-review gate flags
    - `promotion_readiness`
    - `promotion_gate_status`
    - `correction_proposals_path` (nullable)
    - final disposition and exit code
  - [x] Write each summary to a unique path per orchestrator run, even for the same `batch_id`, so reruns preserve history instead of overwriting the prior summary artifact.
  - [x] Keep the summary stable enough for Stories 15.16, 15.17, and 15.18 to consume later without re-parsing terminal prose.

- [x] Task 5: Add focused operator and regression coverage (AC: 3, 4)
  - [x] Add focused tests for:
    - happy-path step ordering
    - stop-on-failure behavior
    - blocked validation stops before stock follow-up
    - reconciliation-threshold failure behavior
    - partial-failure summary shape
    - summary artifact generation
    - same-batch rerun writes a new summary artifact and preserves prior run evidence
    - no promotion side effect
  - [x] Prefer narrow unit/integration tests around the new orchestrator module rather than trying to exercise full live imports in one test.
  - [x] Document any unrelated pre-existing test failures separately instead of weakening this story's focused coverage.

- [x] Task 6: Document the reviewed command in the operator workflow (AC: 4)
  - [x] Update the legacy-import command map and any relevant skill/operator docs to include the new end-to-end refresh command.
  - [x] Document that this command builds a shadow-ready batch but does not schedule runs, perform the downstream working-lane switch, or auto-apply corrections.

## Dev Notes

### Story Intent

- This story creates the single reviewed entry point for a full live refresh.
- It should reduce operator error, not replace the import pipeline.
- It is the bridge between Story 15.12's live DB ingress and later stories for scheduled shadow refresh and gated downstream promotion.

### Scope Boundaries

- In scope:
  - one end-to-end refresh command
  - sequencing the existing import and follow-up steps
  - structured run summary artifacts
  - threshold-based failure handling
- Out of scope:
  - scheduled automation or recurring jobs (`15.16`)
  - promotion into the working lane (`15.17`)
  - threshold policy design and correction approval workflow changes (`15.18`)
  - incremental or watermark-based live sync (`15.19`)
  - retirement of dump-era legacy surfaces (`15.20`)

### Implementation Direction

- Do **not** reimplement legacy-import business logic in the new script.
- Prefer function-level reuse of the backend surfaces already used by the CLI instead of spawning nested `uv` subprocesses from inside Python.
- Keep operator-visible output aligned with the command map semantics so each step remains explainable in familiar terms.
- Use explicit step boundaries so failure handling is deterministic and summary artifacts remain trustworthy.
- Treat `validate-import` and reconciliation as separate gates:
  - validation is the import-integrity gate and runs immediately after canonical import
  - reconciliation is the shadow-dataset usability gate and runs only after non-blocked validation plus stock follow-up
- Partial state is expected when a later step fails. The orchestrator must report that state clearly instead of attempting an unsafe cross-step rollback.
- Same-batch reruns are supported, but each orchestrator invocation must emit a distinct summary artifact and preserve a trustworthy audit trail of rerun history.

### Existing Repo Constraints

- Story 15.12 already established `live-stage` as the supported direct-from-legacy entry point.
- Story 15.5 already established machine-readable validation artifacts and replay metadata under `_bmad-output/validation/legacy-import/`.
- Story 18.2 showed that a shadow-usable dataset still needs sales and purchase stock backfills plus reconciliation reporting after canonical import.
- Current local evidence on `2026-04-18` still shows non-zero reconciliation drift, so the orchestrator must record and gate on reconciliation rather than assuming success.

### Critical Warnings

- Do **not** embed scheduling logic in this story. A local operator command is the deliverable.
- Do **not** auto-promote a refreshed batch into the working lane.
- Do **not** auto-apply reconciliation corrections from `apply_reconciliation_corrections.py`.
- Do **not** bypass validation or convert validation warnings into silent success.
- Do **not** route operators back to the dump-era `legacy-migration-pipeline/` as the default path now that live staging exists.

### Suggested Command Shape

An acceptable operator command shape is:

```bash
cd backend && uv run python -m scripts.run_legacy_refresh \
  --batch-id legacy-shadow-YYYYMMDD \
  --tenant-id <tenant-uuid> \
  --schema raw_legacy \
  --source-schema public \
  --lookback-days 10000 \
  --reconciliation-threshold 0
```

The final argument surface can expand modestly for lookback and threshold settings, but it should stay operator-friendly and avoid turning this script into a second generic import CLI.

### Testing Notes

- Add new focused tests near the other backend script tests, for example `backend/tests/test_run_legacy_refresh.py`.
- Reuse monkeypatch-driven orchestration tests similar to the CLI tests instead of depending on live DB access.
- Keep assertions focused on:
  - ordered calls
  - summary payload shape
  - threshold gating
  - non-zero exit on failure
- Note the existing broader backend test caveat already documented in recent legacy-import stories:
  - `uv run pytest -q` still has unrelated collection failures outside this slice
  - repo-wide `ruff check` still has unrelated violations outside targeted files

### Project Structure Notes

- Primary implementation surface:
  - `backend/scripts/run_legacy_refresh.py`
- Likely supporting test surface:
  - `backend/tests/test_run_legacy_refresh.py`
- Existing code to reuse:
  - `backend/domains/legacy_import/cli.py`
  - `backend/domains/legacy_import/staging.py`
  - `backend/domains/legacy_import/normalization.py`
  - `backend/domains/legacy_import/mapping.py`
  - `backend/domains/legacy_import/canonical.py`
  - `backend/domains/legacy_import/validation.py`
  - `backend/scripts/backfill_sales_reservations.py`
  - `backend/scripts/backfill_purchase_receipts.py`
  - `backend/scripts/verify_reconciliation.py`
- Documentation updates belong with the established operator docs and skill docs rather than in a one-off note.

## References

- `_bmad-output/planning-artifacts/epic-15.md` - Story 15.15 definition and adjacent Epic 15 sequencing
- `_bmad-output/implementation-artifacts/15-12-live-legacy-db-stage-cli.md` - live-stage operator contract and current live ingress path
- `_bmad-output/implementation-artifacts/15-5-migration-validation-and-replay-safety.md` - validation artifact contract and Epic 13 handoff boundary
- `_bmad-output/implementation-artifacts/18-2-legacy-sales-adjustment-backfill.md` - stock backfill and reconciliation requirements for usable historical shadow data
- `.agents/skills/legacy-import/command-map.md` - reviewed step ordering and stable invocation path
- `docs/legacy/migration-plan.md` - shadow-mode intent, severity policy, and cutover boundary
- `docs/superpowers/specs/2026-03-30-erp-architecture-design-v2.md` - Section 4.5 shadow-mode outputs and Section 7.4 human-in-the-loop approval rules
- `backend/domains/legacy_import/cli.py` - current CLI-backed entry points and summary behavior
- `backend/scripts/backfill_sales_reservations.py`
- `backend/scripts/backfill_purchase_receipts.py`
- `backend/scripts/verify_reconciliation.py`
- `backend/scripts/apply_reconciliation_corrections.py`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- Read Epic 15 planning context in `_bmad-output/planning-artifacts/epic-15.md`
- Read prior implementation context from:
  - `_bmad-output/implementation-artifacts/15-12-live-legacy-db-stage-cli.md`
  - `_bmad-output/implementation-artifacts/15-5-migration-validation-and-replay-safety.md`
  - `_bmad-output/implementation-artifacts/18-2-legacy-sales-adjustment-backfill.md`
- Read operator workflow docs:
  - `.agents/skills/legacy-import/command-map.md`
  - `docs/legacy/migration-plan.md`
- Read supporting code:
  - `backend/scripts/apply_reconciliation_corrections.py`
  - `backend/tests/domains/legacy_import/test_cli.py`
- Grounded the CLI and test approach with official Python `argparse` guidance and pytest `tmp_path`/`monkeypatch` documentation.
- Validation commands:
  - `cd backend && uv run pytest tests/test_run_legacy_refresh.py -q`
  - `cd backend && uv run ruff check scripts/run_legacy_refresh.py scripts/backfill_sales_reservations.py scripts/backfill_purchase_receipts.py scripts/verify_reconciliation.py tests/test_run_legacy_refresh.py`
  - `cd backend && uv run pytest tests/domains/legacy_import tests/test_legacy_stock_backfill_scripts.py tests/test_run_legacy_refresh.py -q`

### Completion Notes List

- Implemented `scripts.run_legacy_refresh` as the reviewed operator entry point that reuses the live-stage, normalization, mapping, canonical import, validation, stock backfill, and reconciliation functions directly instead of spawning nested CLI subprocesses.
- Added stable JSON run summaries under `_bmad-output/operations/legacy-refresh/` with unique per-run paths, ordered step results, gate flags, validation artifact paths, reconciliation thresholds, rerun-safe audit history, and partial-failure reporting.
- Preserved the `UNKNOWN` fallback path for unresolved mappings while exporting a deterministic review CSV and marking the batch not promotion-ready when analyst review is still outstanding.
- Threaded `tenant_id` through the reused stock backfill and reconciliation helpers so the orchestrator does not silently fall back to the default tenant.
- Added focused orchestrator tests covering step ordering, validation blocking, reconciliation blocking, partial-failure summaries, and same-batch rerun evidence; broader legacy-import plus stock-backfill regression passed in this slice.
- Documented the reviewed refresh command in the legacy-import operator command map and migration plan, explicitly excluding scheduling, promotion, and automatic correction application.
- Repo-wide backend `pytest -q` and repo-wide `ruff check` still have unrelated pre-existing failures already noted in the story's testing notes; validation here stayed scoped to the touched legacy-import slice.

### File List

- `.agents/skills/legacy-import/command-map.md`
- `backend/scripts/backfill_purchase_receipts.py`
- `backend/scripts/backfill_sales_reservations.py`
- `backend/scripts/run_legacy_refresh.py`
- `backend/scripts/verify_reconciliation.py`
- `backend/tests/test_run_legacy_refresh.py`
- `docs/legacy/migration-plan.md`
- `_bmad-output/implementation-artifacts/15-15-legacy-refresh-orchestrator.md`

### Change Log

- 2026-04-18: Added the reviewed `run_legacy_refresh` backend command with stable per-run JSON summaries, validation/reconciliation gating, deterministic review export handling, and same-batch rerun history preservation.
- 2026-04-18: Added focused orchestrator regression coverage plus tenant-aware stock backfill/reconciliation helper reuse, and documented the operator command boundaries in legacy-import docs.
