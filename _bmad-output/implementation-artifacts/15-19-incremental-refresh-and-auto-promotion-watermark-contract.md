# Story 15.19: Incremental Refresh And Auto-Promotion Watermark Contract

Status: in-progress

## Story

As a platform engineer,
I want a reviewed watermark and replay contract for incremental legacy refreshes that feed the same promotion gates as nightly batches,
so that we can move toward near-live updates without bypassing the automated safety model.

## Context

The repo now has a reviewed full refresh orchestrator and a cron-safe scheduled shadow wrapper, but both are still full-batch oriented. Nothing in the current implementation defines how a sub-daily refresh should identify new legacy source rows, persist resumable watermarks, or recover safely from partial failure while preserving the same promotion semantics used by nightly shadow batches.

This story is a contract story, not the full rollout of near-live sync. Its job is to define the durable watermark state, per-domain replay semantics, and the boundary between incremental shadow updates and downstream promotion so later implementation does not invent unsafe delta behavior.

## Acceptance Criteria

1. Given the team wants refreshes more often than nightly, when the incremental sync design is implemented, then each supported domain defines its watermark source, replay semantics, correction handling, and promotion-eligibility boundary explicitly, and sync state persists the last successful watermark, shadow batch metadata, and last promoted batch metadata for resumable reruns.
2. Given incremental sync is active, when a run fails mid-stream or produces a blocked batch, then the next run can resume safely from the last successful watermark and the working lane remains on the previously promoted batch until a later eligible batch is produced.
3. Given incremental sync remains lower confidence than the nightly baseline, when the system operates over time, then a nightly full rebaseline remains available as the correctness backstop.

## Tasks / Subtasks

- [ ] Task 1: Define the reviewed per-domain watermark contract (AC: 1)
  - [ ] Create a reviewed contract surface that lists each supported domain, the legacy source tables it depends on, the watermark field or cursor source, replay window behavior, and any late-arriving correction rules.
  - [ ] Limit the first contract version to domains already supported by the reviewed refresh pipeline; do not silently include unfinished legacy slices.
  - [ ] Make batch membership and replay rules explicit for domains whose source data arrives in parent/child table pairs.
- [ ] Task 2: Add durable incremental state models under the legacy-refresh state root (AC: 1, 2)
  - [ ] Persist, at minimum, the last successful watermark per supported domain, the current shadow candidate batch metadata, the latest promoted working batch metadata, and the last nightly full rebaseline reference.
  - [ ] Keep incremental state under the same `_bmad-output/operations/legacy-refresh/state/` tree so operators can reason about nightly and incremental flows together.
  - [ ] Ensure failed or blocked incremental runs do not advance the promoted pointer or replace the last successful watermark.
- [ ] Task 3: Define the resumable incremental runner boundary (AC: 1, 2)
  - [ ] Introduce a reviewed planner/helper surface for incremental runs, such as `backend/domains/legacy_import/incremental_refresh.py` or equivalent.
  - [ ] Keep promotion evaluation separate and reuse the Story 15.17 and 15.18 promotion/policy surfaces rather than inventing a second deployment model for incremental batches.
  - [ ] Define how a partially processed run resumes from the last successful watermark without duplicating canonical writes.
- [ ] Task 4: Preserve the nightly full-refresh rebaseline path (AC: 3)
  - [ ] Document a nightly or periodic full shadow refresh as the correctness backstop for incremental mode.
  - [ ] Ensure incremental state can be reseeded from a successful full refresh without manual state surgery.
  - [ ] Define when operators should force a full rebaseline after drift, schema change, or suspicious watermark behavior.
- [ ] Task 5: Add focused state and replay coverage (AC: 1, 2, 3)
  - [ ] Add tests for watermark serialization, resume-after-failure behavior, blocked-batch no-advance behavior, and rebaseline reset semantics.
  - [ ] Add a reviewed doc or contract artifact for operators and developers describing the watermark state shape and rerun rules.

## Dev Notes

- This story should define the contract and shared helpers first. It should not attempt to ship every per-domain incremental import implementation in one pass.
- Watermarks must advance from successful, durable processing positions, not from merely attempted reads.
- Keep the last promoted batch distinct from the last successful shadow batch and the last successful watermark. All three states matter during failure recovery.
- Incremental mode inherits the same promotion policy as nightly full refreshes. A faster cadence must not become a second, weaker path into the working lane.
- The nightly full rebaseline is a deliberate correctness backstop, not a temporary hack. Preserve it explicitly.

### Project Structure Notes

- New likely files:
  - `backend/domains/legacy_import/incremental_refresh.py`
  - `backend/domains/legacy_import/incremental_state.py`
  - `backend/tests/domains/legacy_import/test_incremental_refresh.py`
- Existing files likely touched:
  - `backend/scripts/run_scheduled_legacy_shadow_refresh.py`
  - `backend/scripts/run_legacy_promotion.py`
  - `docs/legacy/migration-plan.md`
  - `.agents/skills/legacy-import/command-map.md`

### References

- `_bmad-output/planning-artifacts/epic-15.md`
- `_bmad-output/planning-artifacts/sprint-change-proposal-2026-04-18.md`
- `_bmad-output/implementation-artifacts/15-16-scheduled-shadow-refresh-and-batch-state-tracking.md`
- `_bmad-output/implementation-artifacts/15-17-gated-automatic-promotion-to-the-working-lane.md`
- `_bmad-output/implementation-artifacts/15-18-automated-promotion-gate-policy-and-approved-corrections.md`
- `backend/scripts/run_legacy_refresh.py`
- `backend/scripts/run_scheduled_legacy_shadow_refresh.py`
- `backend/scripts/legacy_refresh_common.py`
- `docs/legacy/migration-plan.md`
- `docs/superpowers/specs/2026-03-30-erp-architecture-design-v2.md`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

### Completion Notes List

### File List