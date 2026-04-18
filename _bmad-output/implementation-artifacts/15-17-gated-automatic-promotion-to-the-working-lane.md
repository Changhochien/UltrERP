# Story 15.17: Gated Automatic Promotion To The Working Lane

Status: done

## Story

As a cutover owner,
I want the latest eligible shadow batch to be promoted into the working lane automatically when all promotion gates pass,
so that routine refreshes land without manual intervention while blocked batches leave the current working lane untouched.

## Context

Story 15.15 already emits the machine-readable gate signals needed for promotion evaluation, including `promotion_readiness`, `promotion_gate_status`, validation artifact paths, and reconciliation metrics.

Story 15.16 already persists per-lane `latest-run.json` and `latest-success.json` under `_bmad-output/operations/legacy-refresh/state/`, but it intentionally stops short of mutating the working lane. That means the repo still lacks a reviewed promotion entry point and a durable record of which batch is actually serving as the current working dataset.

This story closes that gap by turning the latest successful eligible shadow batch into an idempotent, auditable working-lane promotion. The happy path is automatic, but the automation must remain policy-gated and must preserve the previous working batch whenever a candidate is blocked or a promotion attempt fails mid-flight.

## Acceptance Criteria

1. Given a shadow batch is the latest successful candidate and all promotion gates pass, when promotion evaluation runs, then the system refreshes or switches the working lane to that batch atomically and records the promoted batch id, previous promoted batch id, actor identity, promotion time, validation status, reconciliation gap count, threshold used, and source summary path.
2. Given a candidate batch fails validation, exceeds reconciliation thresholds, still requires analyst review, or otherwise fails promotion policy, when promotion evaluation runs, then promotion is refused, the working lane remains on the previously promoted batch, and the refusal records the specific blocking gate and emits an operator-visible alert.
3. Given the candidate batch is already the current working batch, when promotion evaluation runs again, then the system exits idempotently without rebuilding the working lane or writing duplicate promotion history.

## Tasks / Subtasks

- [x] Task 1: Define the reviewed promotion entry point and durable promotion-state contract (AC: 1, 3)
  - [x] Add a repo-owned entry point such as `backend/scripts/run_legacy_promotion.py` instead of embedding working-lane mutation inside the scheduled wrapper.
  - [x] Consume `latest-success.json` plus the referenced Story 15.15 summary JSON under `_bmad-output/operations/legacy-refresh/` as the candidate source of truth.
  - [x] Persist a durable `latest-promoted.json` record under the same per-lane state root, and add append-only promotion-history artifacts if needed for auditability.
  - [x] Record, at minimum: `batch_id`, `previous_batch_id`, `promoted_at`, `promoted_by`, `summary_path`, `validation_status`, `blocking_issue_count`, `reconciliation_gap_count`, `reconciliation_threshold`, and `promotion_result` (`promoted`, `blocked`, or `noop`).
- [x] Task 2: Reuse existing gate signals instead of recomputing refresh logic (AC: 1, 2)
  - [x] Evaluate promotion using Story 15.15 fields such as `promotion_readiness` and `promotion_gate_status` plus Story 15.16 lane state.
  - [x] Treat blocked validation, reconciliation-threshold failure, unresolved analyst review, missing candidate state, or missing summary artifacts as explicit blocking reasons.
  - [x] Refuse promotion if the candidate is not the latest successful shadow batch for the lane or if scheduler overlap/active-lock state indicates the lane is still unstable.
- [x] Task 3: Implement the working-lane switch as one atomic backend-owned operation (AC: 1, 2, 3)
  - [x] Create a single promotion service/module under `backend/domains/legacy_import/` so working-lane mutation is centralized and testable.
  - [x] Keep the previous working batch active until the promotion operation commits successfully.
  - [x] Return a `noop` result when the candidate batch id already matches `latest-promoted.json`.
  - [x] Ensure failed promotion attempts do not partially advance the working-lane pointer or overwrite the prior promoted state.
- [x] Task 4: Emit operator-visible promotion outcomes and alerts (AC: 1, 2, 3)
  - [x] Write a machine-readable promotion result artifact and a concise terminal summary for every evaluation attempt.
  - [x] Include explicit blocking gate names and operator-oriented refusal text for blocked candidates.
  - [x] Record the automated actor identity as `SYSTEM`; reserve human/operator identities for later exception or override paths.
- [x] Task 5: Add focused regression coverage and operator docs (AC: 1, 2, 3)
  - [x] Add focused tests for eligible promotion, blocked promotion, missing candidate state, idempotent `noop`, and failure paths that preserve the prior `latest-promoted` pointer.
  - [x] Update the operator command map and migration docs so scheduled shadow refresh is documented as producing the promotion candidate, while the reviewed promotion entry point owns the working-lane switch.

### Review Findings

- [x] [Review][Patch] Summary gate booleans ignore explicit false values [backend/domains/legacy_import/promotion.py:346]
- [x] [Review][Patch] Summary identity validation only checks batch id [backend/domains/legacy_import/promotion.py:305]
- [x] [Review][Patch] Blocked/noop evaluations can fail before recording the outcome [backend/scripts/run_legacy_promotion.py:273]
- [x] [Review][Patch] Candidate and summary validation still failed open for malformed or missing gate fields, lane identity mismatches, and noop-path corruption gaps [backend/domains/legacy_import/promotion.py]
- [x] [Review][Patch] Promoted-path pointer-write failures could leave contradictory promoted artifacts behind [backend/scripts/run_legacy_promotion.py]
- [x] [Review][Patch] Corrupted `latest-promoted.json` now blocks explicitly as `invalid-promoted-state`, including unreadable, non-object, null, wrong-lane, non-promoted, and partial promoted-pointer payloads [backend/scripts/run_legacy_promotion.py]
- [x] [Review][Patch] Promotion now serializes runs with `promotion.lock` and re-evaluates the refreshed candidate under the shared scheduler lock before noop/promote commit [backend/scripts/run_legacy_promotion.py]
- [x] [Review][Patch] Stale scheduler and promotion locks now auto-recover after expiry before scheduled refresh or promotion evaluation blocks the lane indefinitely [backend/scripts/legacy_refresh_state.py]
- [x] [Review][Patch] Promotion now re-reads and validates the live `latest-promoted.json` pointer under the commit lock before both promoted and noop finalization, blocking pointer drift as `promoted-state-changed` instead of overwriting newer state [backend/scripts/run_legacy_promotion.py]

## Dev Notes

- This story must not rerun `live-stage`, `normalize`, `canonical-import`, or other refresh steps. It consumes the artifacts already produced by Stories 15.15 and 15.16.
- Keep three states distinct and operator-visible:
  - latest attempted shadow batch
  - latest successful shadow batch
  - latest promoted working batch
- The automatic promotion path is a deterministic, policy-gated system action. It should be audited thoroughly, but it does not need to recreate a generic ad hoc approval step for every routine refresh.
- If the working-lane switch surface does not yet exist, introduce one narrow adapter around the actual serving dataset or pointer instead of spreading working-lane writes across scheduler code and ad hoc scripts.
- Promotion alerts can initially be artifact-based and terminal-visible if the repo does not yet have a reviewed notification surface; do not invent parallel alerting channels in this story.

### Project Structure Notes

- New likely files:
  - `backend/scripts/run_legacy_promotion.py`
  - `backend/domains/legacy_import/promotion.py`
  - `backend/tests/test_run_legacy_promotion.py`
- Existing files to reuse:
  - `backend/scripts/run_legacy_refresh.py`
  - `backend/scripts/run_scheduled_legacy_shadow_refresh.py`
  - `backend/scripts/legacy_refresh_common.py`
  - `docs/legacy/migration-plan.md`
  - `.agents/skills/legacy-import/command-map.md`

### References

- `_bmad-output/planning-artifacts/epic-15.md`
- `_bmad-output/planning-artifacts/sprint-change-proposal-2026-04-18.md`
- `_bmad-output/implementation-artifacts/15-15-legacy-refresh-orchestrator.md`
- `_bmad-output/implementation-artifacts/15-16-scheduled-shadow-refresh-and-batch-state-tracking.md`
- `backend/scripts/run_legacy_refresh.py`
- `backend/scripts/run_scheduled_legacy_shadow_refresh.py`
- `backend/scripts/legacy_refresh_common.py`
- `docs/legacy/migration-plan.md`
- `docs/superpowers/specs/2026-03-30-erp-architecture-design-v2.md`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- Focused validation on 2026-04-18: `cd backend && uv run ruff check --fix scripts/run_scheduled_legacy_shadow_refresh.py scripts/run_legacy_promotion.py domains/legacy_import/promotion.py tests/domains/legacy_import/test_promotion.py tests/test_run_legacy_promotion.py && uv run pytest tests/test_run_scheduled_legacy_shadow_refresh.py tests/domains/legacy_import/test_promotion.py tests/test_run_legacy_promotion.py -q && uv run ruff check scripts/legacy_refresh_state.py scripts/run_scheduled_legacy_shadow_refresh.py scripts/run_legacy_promotion.py domains/legacy_import/promotion.py tests/test_run_scheduled_legacy_shadow_refresh.py tests/domains/legacy_import/test_promotion.py tests/test_run_legacy_promotion.py`
- Review-fix validation on 2026-04-18: `cd backend && /Users/hcchang/.local/bin/uv run pytest tests/domains/legacy_import/test_promotion.py tests/test_run_legacy_promotion.py -q && /Users/hcchang/.local/bin/uv run ruff check domains/legacy_import/promotion.py scripts/run_legacy_promotion.py tests/domains/legacy_import/test_promotion.py tests/test_run_legacy_promotion.py`
- Re-review hardening validation on 2026-04-18: `cd backend && /usr/bin/env -C /Volumes/2T_SSD_App/Projects/UltrERP/backend /Users/hcchang/.local/bin/uv run pytest tests/domains/legacy_import/test_promotion.py tests/test_run_legacy_promotion.py -q && /usr/bin/env -C /Volumes/2T_SSD_App/Projects/UltrERP/backend /Users/hcchang/.local/bin/uv run ruff check domains/legacy_import/promotion.py scripts/run_legacy_promotion.py tests/domains/legacy_import/test_promotion.py tests/test_run_legacy_promotion.py`
- Current-pointer corruption validation on 2026-04-18: `cd backend && /usr/bin/env -C /Volumes/2T_SSD_App/Projects/UltrERP/backend /Users/hcchang/.local/bin/uv run pytest tests/domains/legacy_import/test_promotion.py tests/test_run_legacy_promotion.py -q && /usr/bin/env -C /Volumes/2T_SSD_App/Projects/UltrERP/backend /Users/hcchang/.local/bin/uv run ruff check domains/legacy_import/promotion.py scripts/run_legacy_promotion.py scripts/legacy_refresh_state.py tests/domains/legacy_import/test_promotion.py tests/test_run_legacy_promotion.py`
- Concurrency-guard validation on 2026-04-18: `cd backend && /usr/bin/env -C /Volumes/2T_SSD_App/Projects/UltrERP/backend /Users/hcchang/.local/bin/uv run pytest tests/domains/legacy_import/test_promotion.py tests/test_run_legacy_promotion.py -q && /usr/bin/env -C /Volumes/2T_SSD_App/Projects/UltrERP/backend /Users/hcchang/.local/bin/uv run ruff check domains/legacy_import/promotion.py scripts/run_legacy_promotion.py scripts/legacy_refresh_state.py tests/domains/legacy_import/test_promotion.py tests/test_run_legacy_promotion.py`
- Stale-lock recovery validation on 2026-04-18: `/usr/bin/env -C /Volumes/2T_SSD_App/Projects/UltrERP/backend /Users/hcchang/.local/bin/uv run pytest tests/test_run_legacy_promotion.py tests/test_run_scheduled_legacy_shadow_refresh.py && /usr/bin/env -C /Volumes/2T_SSD_App/Projects/UltrERP/backend /Users/hcchang/.local/bin/uv run ruff check scripts/legacy_refresh_state.py scripts/run_legacy_promotion.py scripts/run_scheduled_legacy_shadow_refresh.py tests/test_run_legacy_promotion.py tests/test_run_scheduled_legacy_shadow_refresh.py`
- Promoted-pointer CAS validation on 2026-04-18: `/usr/bin/env -C /Volumes/2T_SSD_App/Projects/UltrERP/backend /Users/hcchang/.local/bin/uv run pytest tests/test_run_legacy_promotion.py && /usr/bin/env -C /Volumes/2T_SSD_App/Projects/UltrERP/backend /Users/hcchang/.local/bin/uv run ruff check scripts/run_legacy_promotion.py tests/test_run_legacy_promotion.py`

### Completion Notes List

- Added a reviewed promotion entry point at `backend/scripts/run_legacy_promotion.py` that consumes `latest-success.json` and the referenced Story 15.15 summary, writes append-only promotion result artifacts, and only advances `latest-promoted.json` when the policy gates pass.
- Added `backend/domains/legacy_import/promotion.py` to centralize promotion-decision evaluation, including explicit blocked gate names for validation, reconciliation, analyst review, missing candidate state, missing summary artifacts, and unstable lane state.
- Preserved the previous working-lane pointer on promotion-write failures and returned idempotent `noop` outcomes when the candidate batch already matches `latest-promoted.json`.
- Extracted reusable lane-state helpers into `backend/scripts/legacy_refresh_state.py` and updated the scheduled shadow-refresh wrapper to reuse the shared lane key/state path helpers instead of duplicating them.
- Updated the legacy-import operator command map and migration plan so the scheduled wrapper is documented as producing the candidate batch while the reviewed promotion entry point owns the working-lane switch.
- Final focused validation passed cleanly with `18 passed` and targeted Ruff checks green.
- Follow-up code review fixes now let the Story 15.15 summary clear stale promotion flags explicitly, reject summary artifacts whose lane identity does not match the candidate state, and downgrade blocked/noop artifact-write failures into controlled `promotion-write-failure` outcomes instead of uncaught CLI crashes.
- Review-fix validation passed with `13 passed` across the focused promotion slice and targeted Ruff checks clean.
- Second re-review hardening now validates candidate lane identity before noop/promote, requires key summary gate fields instead of inheriting stale lane-state values, rejects malformed numeric and boolean gate payloads fail-closed, blocks unresolved `completed-review-required` dispositions unless analyst review explicitly passes, and cleans up stale promoted artifacts when the pointer-write failure path cannot persist a replacement failure artifact.
- Latest re-review validation passed with `30 passed` across the focused promotion slice and targeted Ruff checks clean, but the story remains in review pending follow-up handling for corrupted current-pointer state and promotion snapshot concurrency.
- Current-pointer follow-up now blocks malformed `latest-promoted.json` explicitly, including unreadable JSON, JSON `null`, non-object payloads, wrong-lane or non-promoted records, missing required promoted-state fields, and non-string batch identifiers, with focused integration coverage for each corruption shape.
- Current-pointer follow-up validation passed with `36 passed` across the focused promotion slice and targeted Ruff checks clean.
- Concurrency hardening now serializes promotion runs with `promotion.lock`, fail-closes candidate/summary rereads on wrong-shape and non-UTF8 state, and re-evaluates the refreshed candidate under the shared scheduler lock before both noop and promoted commit paths.
- Concurrency-guard validation passed with `42 passed` across the focused promotion slice and targeted Ruff checks clean.
- Stale-lock recovery now reaps expired `promotion.lock` and `scheduler.lock` files before promotion or scheduled refresh treat the lane as busy, with focused regression coverage across both entry points.
- Stale-lock recovery validation passed with `33 passed` across the focused promotion and scheduler slice and targeted Ruff checks clean.
- Promoted-pointer compare-and-swap hardening now re-reads the live promoted pointer under the commit lock, validates it fail-closed, and blocks both promoted and noop finalization when the current working-lane pointer drifts under the evaluated snapshot.
- Promoted-pointer CAS validation passed with `26 passed` across the focused promotion slice and targeted Ruff checks clean; all Story 15.17 review follow-ups are now closed.

### File List

- `backend/domains/legacy_import/promotion.py`
- `backend/scripts/legacy_refresh_state.py`
- `backend/scripts/run_legacy_promotion.py`
- `backend/scripts/run_scheduled_legacy_shadow_refresh.py`
- `backend/tests/domains/legacy_import/test_promotion.py`
- `backend/tests/test_run_legacy_promotion.py`
- `.agents/skills/legacy-import/command-map.md`
- `docs/legacy/migration-plan.md`
- `_bmad-output/implementation-artifacts/15-17-gated-automatic-promotion-to-the-working-lane.md`