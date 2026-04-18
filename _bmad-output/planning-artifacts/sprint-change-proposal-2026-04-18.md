# Sprint Change Proposal: Epic 15 Auto-Promotion Realignment

Date: 2026-04-18
Project: UltrERP
Author: GitHub Copilot

## 1. Issue Summary

Epic 15 currently assumes a shadow-first workflow where scheduled refreshes stop after evidence generation and a human later approves promotion into the working lane.

That assumption no longer matches the intended operating model for routine imports. The routine path should be unattended when the batch is clean, while failures should leave the working lane unchanged and notify operators with enough detail to investigate.

The current implementation already produces most of the gate signals needed for automation:

- `run_legacy_refresh` emits `promotion_readiness` and structured `promotion_gate_status`
- the scheduled wrapper persists `latest-run.json` and `latest-success.json`
- validation and reconciliation already produce explicit machine-readable status

The mismatch is therefore not in the refresh pipeline itself. The mismatch is in the later story slice and surrounding docs, which still treat manual approval as the only allowed promotion path.

## 2. Impact Analysis

### Recommended approach

Adopt **Shadow + Conditional Auto-Promote** for the current Epic 15 plan.

This means:

- keep the existing shadow-lane refresh architecture from Stories 15.15 and 15.16
- remove manual approval from the happy path
- auto-promote only when all gates pass
- keep human involvement only for exception handling, correction approval, or policy overrides

### Why this is the right scope

This keeps the change set mostly inside Stories 15.17 to 15.20 and avoids reopening completed implementation work in Stories 15.15 and 15.16.

If the team instead wants **direct import with no shadow lane**, then Stories 15.15 and 15.16 must also be rewritten and parts of the already implemented scheduler/state model should be re-scoped. That is a larger epic-level replan, not just a Story 15.17 to 15.20 adjustment.

### Directly affected artifacts

- `_bmad-output/planning-artifacts/epic-15.md`
- `_bmad-output/implementation-artifacts/15-16-scheduled-shadow-refresh-and-batch-state-tracking.md`
- `docs/legacy/migration-plan.md`

### Potentially affected technical surfaces after story approval

- `backend/scripts/run_scheduled_legacy_shadow_refresh.py`
- a new promotion surface, likely under `backend/domains/legacy_import/` plus a repo-owned script entry point
- durable promotion state, for example `latest-promoted.json` or equivalent

### Architecture notes

No general change is required to the platform-wide human-in-the-loop rule in `docs/superpowers/specs/2026-03-30-erp-architecture-design-v2.md`.

This legacy refresh path should be classified as a deterministic, policy-gated system action, not as an open-ended AI action that always requires ad hoc human approval.

## 3. Recommended Approach

### Decision

Rewrite Stories 15.17 to 15.20 around these rules:

1. Scheduled refresh continues to build a shadow batch and capture evidence.
2. Promotion eligibility is decided by explicit machine-readable gates.
3. The happy path is automatic.
4. Failures do not mutate the working lane.
5. Exception handling and correction application remain manual.

### Gate model

At minimum, automatic promotion should require all of the following:

- validation gate passed
- reconciliation gap count at or below threshold
- no unresolved analyst-review gate if that gate remains part of the workflow
- no overlapping active scheduler state

### State model addition

The current scheduler state tracks the latest attempted and latest successful shadow batches. The automated architecture also needs a durable record of the currently promoted working batch.

Add a promotion state record containing at minimum:

- `batch_id`
- `promoted_at`
- `promoted_by` (`SYSTEM` for automated promotion, operator id for manual override)
- `previous_batch_id`
- `validation_status`
- `blocking_issue_count`
- `reconciliation_gap_count`
- `reconciliation_threshold`
- `summary_path`
- `promotion_result` (`promoted`, `blocked`, `noop`)

## 4. Detailed Change Proposals

### Story 15.17

**Current title**

`Approved Promotion To The Working Lane`

**Proposed title**

`Gated Automatic Promotion To The Working Lane`

**Current story**

As an operator,
I want validated shadow batches to be promoted into the working database only through an approval step,
So that the team works from fresh data without turning every refresh into an uncontrolled production event.

**Proposed story**

As a cutover owner,
I want the latest eligible shadow batch to be promoted into the working lane automatically when all promotion gates pass,
So that routine refreshes land without manual intervention while blocked batches leave the current working lane untouched.

**Replace acceptance criteria with**

1. **Given** a shadow batch is the latest successful candidate and all promotion gates pass
   **When** the promotion evaluation runs
   **Then** the system refreshes or switches the working lane to that batch atomically
   **And** records the promoted batch id, previous promoted batch id, actor identity, promotion time, validation status, reconciliation gap count, threshold used, and source summary path.

2. **Given** a candidate batch fails validation, exceeds reconciliation thresholds, still requires analyst review, or otherwise fails promotion policy
   **When** promotion evaluation runs
   **Then** promotion is refused
   **And** the working lane remains on the previously promoted batch
   **And** the refusal records the specific blocking gate and emits an operator-visible alert.

3. **Given** the candidate batch is already the current working batch
   **When** promotion evaluation runs again
   **Then** the system exits idempotently without rebuilding the working lane or writing duplicate promotion history.

**Rationale**

This removes human approval from the happy path without removing auditability or safety.

### Story 15.18

**Current title**

`Reconciliation Gate Policy And Approved Corrections`

**Proposed title**

`Automated Promotion Gate Policy And Approved Corrections`

**Current story**

As a cutover owner,
I want explicit reconciliation thresholds and an approval-based correction policy,
So that routine refreshes can distinguish acceptable known drift from cutover-blocking problems.

**Proposed story**

As a cutover owner,
I want explicit automated promotion thresholds and a manual exception policy,
So that routine refreshes can auto-promote when drift is acceptable while out-of-policy batches pause for operator review.

**Replace acceptance criteria with**

1. **Given** validation and reconciliation artifacts exist for a shadow batch
   **When** promotion policy is evaluated
   **Then** the system classifies the batch into explicit outcomes such as `eligible`, `blocked`, or `exception-required`
   **And** the same policy is reused by scheduled refreshes, promotion evaluation, alerts, and operator summaries.

2. **Given** reconciliation output reports gaps within the configured threshold and no other blocking gate is open
   **When** policy is evaluated
   **Then** the batch is eligible for automatic promotion.

3. **Given** reconciliation output exceeds the configured threshold or another gate fails
   **When** policy is evaluated
   **Then** the batch is blocked from automatic promotion
   **And** the system records which threshold or gate failed.

4. **Given** correction proposals or exception decisions are needed
   **When** operators act on them
   **Then** only explicitly approved corrections or overrides may be applied
   **And** scheduled jobs never auto-apply reconciliation corrections.

**Rationale**

The manual step moves from “approve every promotion” to “approve only exceptions or corrective actions.”

### Story 15.19

**Current title**

`Incremental Live Sync Watermark Contract`

**Proposed title**

`Incremental Refresh And Auto-Promotion Watermark Contract`

**Current story**

As a platform engineer,
I want a reviewed watermark and replay contract for sub-daily legacy refreshes,
So that we can evolve from nightly full shadow batches toward near-live shadow sync without inventing unsafe delta behavior.

**Proposed story**

As a platform engineer,
I want a reviewed watermark and replay contract for incremental legacy refreshes that feed the same promotion gates as nightly batches,
So that we can move toward near-live updates without bypassing the automated safety model.

**Replace acceptance criteria with**

1. **Given** the team wants refreshes more often than nightly
   **When** the incremental sync design is implemented
   **Then** each supported domain defines its watermark source, replay semantics, correction handling, and promotion-eligibility boundary explicitly
   **And** sync state persists the last successful watermark, shadow batch metadata, and last promoted batch metadata for resumable reruns.

2. **Given** incremental sync is active
   **When** a run fails mid-stream or produces a blocked batch
   **Then** the next run can resume safely from the last successful watermark
   **And** the working lane remains on the previously promoted batch until a later eligible batch is produced.

3. **Given** incremental sync remains lower confidence than the nightly baseline
   **When** the system operates over time
   **Then** a nightly full rebaseline remains available as the correctness backstop.

**Rationale**

Incremental sync must inherit the same promotion contract instead of inventing a second deployment policy.

### Story 15.20

**Current title**

`Legacy Dump Surface Deprecation And Retirement`

**Proposed title**

`Legacy Dump And Manual-Promotion Surface Retirement`

**Current story**

As a platform maintainer,
I want obsolete dump-era migration surfaces retired behind explicit stability gates,
So that the repo defaults to the live legacy path and no longer carries duplicated legacy code once it is no longer needed.

**Proposed story**

As a platform maintainer,
I want obsolete dump-era and manual-promotion legacy surfaces retired behind explicit stability gates,
So that the repo defaults to the live gated refresh path and no longer carries duplicate operational workflows.

**Replace acceptance criteria with**

1. **Given** the live refresh plus automatic promotion path has met agreed stability gates
   **When** the retirement story executes
   **Then** the repository stops defaulting operators to dump-era sources or manual approval-driven promotion steps
   **And** docs, skills, and commands point to the live gated refresh workflow as the default path.

2. **Given** dump-era imports, manual promotion notes, or transitional remediation scripts still exist
   **When** cleanup is evaluated
   **Then** a surface may only be removed after its logic is absorbed into the standard refresh, promotion, alerting, or exception workflow
   **And** the cleanup records which fallback surfaces intentionally remain.

3. **Given** archived CSV extracts or raw dumps still need retention for audit
   **When** active repo cleanup happens
   **Then** those artifacts are archived outside the working repo before deletion from default developer workflows.

**Rationale**

Once promotion is automated, the old manual cutover surface becomes part of the legacy workflow that should eventually be retired.

## 5. Adjacent Artifact Changes Needed

These changes are outside Stories 15.17 to 15.20 themselves but should be updated with the same proposal.

### Story 15.16 implementation artifact

Update the narrative and scope notes that currently state scheduled refreshes never mutate the working lane.

Recommended adjustment:

- keep Story 15.16 itself as shadow-refresh state tracking
- clarify that Story 15.16 remains promotion-neutral on its own, but its state becomes the input to automated promotion in Story 15.17
- remove any wording in living docs that implies manual approval is the only allowed downstream path

### Legacy migration docs

Update `docs/legacy/migration-plan.md` so it no longer states that scheduled refreshes categorically do not promote. Replace that with language that says scheduled refresh produces the promotion candidate, and downstream promotion is automatic when gates pass.

### Operator-facing state semantics

Add a durable distinction between:

- latest attempted shadow batch
- latest successful shadow batch
- latest promoted working batch

Without that third state, operators cannot tell whether freshness and production-equivalent visibility are aligned.

## 6. Scope Classification And Handoff

### Scope

Moderate.

This is not a full architecture reset, but it does cross planning, operator docs, scheduler state semantics, and downstream implementation.

### Handoff

- Product/Planning: update Epic 15 story text and any story implementation artifacts that are treated as living planning documents
- Architecture/Engineering: define the working-lane promotion mechanism and promotion state record
- Developer: implement Story 15.17 and related docs after story text is approved

### Success criteria

- routine scheduled refreshes can promote automatically when gates pass
- blocked batches leave the working lane unchanged
- operators can see both the latest successful shadow batch and the latest promoted working batch
- correction application remains explicit and manual
- incremental sync and dump retirement stories align with the same promotion contract