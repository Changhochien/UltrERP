# Story 15.18: Automated Promotion Gate Policy And Approved Corrections

Status: done

## Story

As a cutover owner,
I want explicit automated promotion thresholds and a manual exception policy,
so that routine refreshes can auto-promote when drift is acceptable while out-of-policy batches pause for operator review.

## Context

Stories 15.15 and 15.16 already expose validation status, reconciliation counts, analyst-review requirements, and promotion-readiness signals. Story 15.17 introduces the working-lane promotion evaluator, but that evaluator still needs one shared policy contract so the scheduler, promotion step, alerting, and operator summaries all classify batches the same way.

The repo also already contains manual correction surfaces: `propose_reconciliation_corrections.py` generates candidate corrections, and `apply_reconciliation_corrections.py` applies only explicitly approved actionable rows. This story must preserve that manual control while formalizing when a batch is `eligible`, `blocked`, or `exception-required` for promotion.

## Acceptance Criteria

1. Given validation and reconciliation artifacts exist for a shadow batch, when promotion policy is evaluated, then the system classifies the batch into explicit outcomes such as `eligible`, `blocked`, or `exception-required`, and the same policy is reused by scheduled refreshes, promotion evaluation, alerts, and operator summaries.
2. Given reconciliation output reports gaps within the configured threshold and no other blocking gate is open, when policy is evaluated, then the batch is eligible for automatic promotion.
3. Given reconciliation output exceeds the configured threshold or another gate fails, when policy is evaluated, then the batch is blocked from automatic promotion and the system records which threshold or gate failed.
4. Given correction proposals are generated, when operators decide to apply them, then only explicitly approved correction rows may be applied and automated refresh jobs never auto-apply reconciliation corrections.

## Tasks / Subtasks

- [x] Task 1: Define one shared promotion-policy evaluator contract (AC: 1, 2, 3)
  - [x] Add a backend-owned policy module such as `backend/domains/legacy_import/promotion_policy.py`.
  - [x] Define policy inputs from existing artifacts and state, including validation status, blocking issue count, reconciliation gap count, reconciliation threshold, analyst-review-required flag, overlap state, and summary disposition.
  - [x] Return a structured result containing classification, reason codes, machine-readable gate details, and concise operator-facing text.
- [x] Task 2: Centralize threshold and gate evaluation so all callers agree (AC: 1, 2, 3)
  - [x] Ensure the scheduled wrapper, promotion evaluator, alerts, and any operator summaries reuse the same policy module instead of duplicating threshold logic.
  - [x] Keep threshold configuration in one reviewed location rather than hard-coding different values in multiple scripts.
  - [x] Preserve explicit outcomes `eligible`, `blocked`, and `exception-required`; do not collapse exception cases into silent success.
- [x] Task 3: Keep reconciliation corrections explicit and approved-only (AC: 4)
  - [x] Reuse `backend/scripts/propose_reconciliation_corrections.py` as the proposal-generation surface.
  - [x] Reuse `backend/scripts/apply_reconciliation_corrections.py` and preserve its `approval_action=apply` requirement for actionable rows only.
  - [x] Ensure scheduled refreshes and automated promotion never call correction-application logic automatically.
  - [x] Preserve review-only categories as manual/operator work rather than hidden automation.
- [x] Task 4: Add the manual exception and override record (AC: 1, 4)
  - [x] If operator overrides are allowed for `exception-required` cases, require a durable override record containing batch id, actor identity, rationale, scope, and timestamp.
  - [x] Distinguish override-driven advancement from automatic eligibility in promotion artifacts, alerts, and operator summaries.
- [x] Task 5: Add focused policy coverage and docs (AC: 1, 2, 3, 4)
  - [x] Add tests for threshold boundaries, blocked-gate classification, review-only correction categories, override recording, and callers sharing the same policy outcome.
  - [x] Update the migration plan and command docs to explain the policy outcomes and to state explicitly that correction application remains manual.

### Review Findings

- [x] [Review][Patch] Exception override can bypass reconciliation blockers [backend/domains/legacy_import/promotion_policy.py:654]
- [x] [Review][Patch] Override approvals accept blank operator identities [backend/scripts/run_legacy_promotion.py:514]
- [x] [Review][Patch] Override record can outlive failed promotion commit [backend/scripts/run_legacy_promotion.py:985]
- [x] [Review][Defer] Stale-lock recovery can unlock an active long-running refresh [backend/scripts/legacy_refresh_state.py:16] — deferred, pre-existing
- [x] [Review][Defer] Two backfill failures can leave the refresh step ledger inconsistent [backend/scripts/run_legacy_refresh.py:660] — deferred, pre-existing
- [x] [Review][Defer] Scheduled refresh publication of latest-run and latest-success is non-atomic [backend/scripts/run_scheduled_legacy_shadow_refresh.py:344] — deferred, pre-existing
- [x] [Review][Defer] Second-level scheduled batch ids can collide for rapid successive runs [backend/scripts/run_scheduled_legacy_shadow_refresh.py:92] — deferred, pre-existing
- [x] [Review][Defer] Promotion trusts unvalidated summary paths from latest-success state [backend/scripts/run_legacy_promotion.py:651] — deferred, pre-existing
- [x] [Review][Defer] Approved review imports allow whitespace-only reviewer identities [backend/scripts/run_legacy_refresh.py:382] — deferred, pre-existing

## Dev Notes

- Reuse the existing `RefreshGateStatus` and `RefreshDisposition` enums where they fit, but do not overload them if the policy contract needs a separate `eligible` / `blocked` / `exception-required` layer.
- The policy evaluator should operate on structured artifacts and state whenever possible. Avoid coupling policy classification directly to fresh database scans unless a gate truly requires live data.
- `exception-required` is not a successful automatic outcome. It is an operator decision point that must remain visible in state and alerts.
- `propose_reconciliation_corrections.py` already classifies some categories as review-only. Do not erase that operator safety boundary.
- This story is where the repo should decide whether policy thresholds belong in config, in a checked-in policy file, or in a reviewed CLI/config surface. Pick one reviewed home and reuse it.

### Project Structure Notes

- New likely files:
  - `backend/domains/legacy_import/promotion_policy.py`
  - `backend/tests/domains/legacy_import/test_promotion_policy.py`
- Existing files likely touched:
  - `backend/scripts/run_legacy_promotion.py`
  - `backend/scripts/run_scheduled_legacy_shadow_refresh.py`
  - `backend/scripts/propose_reconciliation_corrections.py`
  - `backend/scripts/apply_reconciliation_corrections.py`
  - `docs/legacy/migration-plan.md`
  - `.agents/skills/legacy-import/command-map.md`

### References

- `_bmad-output/planning-artifacts/epic-15.md`
- `_bmad-output/planning-artifacts/sprint-change-proposal-2026-04-18.md`
- `_bmad-output/implementation-artifacts/15-15-legacy-refresh-orchestrator.md`
- `_bmad-output/implementation-artifacts/15-16-scheduled-shadow-refresh-and-batch-state-tracking.md`
- `backend/scripts/propose_reconciliation_corrections.py`
- `backend/scripts/apply_reconciliation_corrections.py`
- `backend/scripts/run_scheduled_legacy_shadow_refresh.py`
- `backend/scripts/legacy_refresh_common.py`
- `docs/legacy/migration-plan.md`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- Story 15.18 validation on 2026-04-18: `/usr/bin/env -C /Volumes/2T_SSD_App/Projects/UltrERP/backend /Users/hcchang/.local/bin/uv run pytest tests/domains/legacy_import/test_promotion_policy.py tests/test_run_legacy_refresh.py tests/test_run_scheduled_legacy_shadow_refresh.py tests/test_run_legacy_promotion.py && /usr/bin/env -C /Volumes/2T_SSD_App/Projects/UltrERP/backend /Users/hcchang/.local/bin/uv run ruff check domains/legacy_import/promotion.py domains/legacy_import/promotion_policy.py scripts/run_legacy_refresh.py scripts/run_scheduled_legacy_shadow_refresh.py scripts/run_legacy_promotion.py tests/domains/legacy_import/test_promotion_policy.py tests/test_run_legacy_refresh.py tests/test_run_scheduled_legacy_shadow_refresh.py tests/test_run_legacy_promotion.py`
- Story 15.18 review-fix validation on 2026-04-18: `cd /Volumes/2T_SSD_App/Projects/UltrERP/backend && /Users/hcchang/.local/bin/uv run pytest tests/domains/legacy_import/test_promotion_policy.py tests/test_run_legacy_refresh.py tests/test_run_scheduled_legacy_shadow_refresh.py tests/test_run_legacy_promotion.py -q && /Users/hcchang/.local/bin/uv run ruff check domains/legacy_import/promotion_policy.py scripts/run_legacy_promotion.py tests/domains/legacy_import/test_promotion_policy.py tests/test_run_legacy_promotion.py`

### Completion Notes List

- Added `backend/domains/legacy_import/promotion_policy.py` as the shared policy evaluator for `eligible`, `blocked`, and `exception-required` outcomes with structured reason codes and gate details.
- `backend/scripts/run_legacy_refresh.py` now stamps every refresh summary with the shared `promotion_policy` payload, and `backend/scripts/run_scheduled_legacy_shadow_refresh.py` copies that policy into lane state and prints it in the operator summary.
- `backend/domains/legacy_import/promotion.py` now reuses the shared policy contract instead of duplicating gate classification logic, while preserving promoted-state validation and noop semantics.
- `backend/scripts/run_legacy_promotion.py` now records policy classification in promotion artifacts, supports audited exception overrides for analyst-review cases, and writes durable override records under `promotion-overrides/` with actor, rationale, scope, and timestamp.
- Manual correction safety remains explicit: the reviewed docs now document `propose_reconciliation_corrections.py` and `apply_reconciliation_corrections.py` as operator-driven surfaces, and automation does not call the apply step.
- Focused Story 15.18 validation passed with `47 passed` across the policy, refresh, scheduler, and promotion slices plus targeted Ruff checks clean.
- Review-fix follow-up now keeps reconciliation-blocked batches blocked even when analyst review is also outstanding, rejects blank or reserved override actor identities, and removes override artifacts when a promoted result cannot commit successfully.
- Story 15.18 review-fix validation passed with `57 passed` across the focused policy, refresh, scheduler, and promotion slice plus targeted Ruff checks clean.

### File List

- `backend/domains/legacy_import/promotion.py`
- `backend/domains/legacy_import/promotion_policy.py`
- `backend/scripts/legacy_refresh_state.py`
- `backend/scripts/run_legacy_refresh.py`
- `backend/scripts/run_scheduled_legacy_shadow_refresh.py`
- `backend/scripts/run_legacy_promotion.py`
- `backend/tests/domains/legacy_import/test_promotion_policy.py`
- `backend/tests/test_run_legacy_refresh.py`
- `backend/tests/test_run_scheduled_legacy_shadow_refresh.py`
- `backend/tests/test_run_legacy_promotion.py`
- `docs/legacy/migration-plan.md`
- `.agents/skills/legacy-import/command-map.md`