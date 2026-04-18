# Story 15.16: Scheduled Shadow Refresh And Batch State Tracking

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a cutover owner,
I want the live refresh workflow to run on a schedule against a shadow lane,
so that the team can monitor freshness and migration quality without disturbing the working database.

## Acceptance Criteria

1. Given the reviewed refresh orchestrator from Story 15.15 exists, when a scheduled shadow-refresh entry point runs, then it generates an immutable shadow batch id using a UTC timestamped pattern, invokes `run_legacy_refresh` with the configured shadow-lane tenant/schema settings, and writes its outputs under the existing legacy-refresh operations artifact tree instead of inventing a parallel storage location.
2. Given a scheduled shadow refresh finishes, when durable batch state is inspected, then the job writes a machine-readable `latest-run` state record and a `latest-success` state record under a stable operations path, and each record includes at minimum: scheduler run id, generated batch id, summary path, final disposition, exit code, completion time, validation status, blocking issue count, reconciliation gap count, reconciliation threshold, analyst-review-required flag, and `promotion_readiness`.
3. Given a scheduled shadow refresh ends in `completed` or `completed-review-required`, when state is updated, then `latest-success` advances to that batch even if analyst review is still required for promotion, because shadow freshness tracking and promotion readiness are separate concepts.
4. Given a scheduled shadow refresh ends in `failed`, `validation-blocked`, or `reconciliation-blocked`, when state is updated, then `latest-run` records the failed attempt, `latest-success` remains pointed at the prior successful shadow batch, and the job emits a compact operator summary with the current batch id, validation status, blocker count, reconciliation gap count, and summary artifact path.
5. Given a previous scheduled run is still active or a stale scheduler lock is unresolved, when another scheduled run starts, then the entry point refuses to launch a second refresh for the same shadow lane, records an explicit overlap outcome, and leaves the previous durable success state untouched.
6. Given the scheduled shadow refresh story is implemented, when lane-affecting surfaces are inspected, then the wrapper mutates only shadow-lane artifacts and scheduler state directly
  and any later working-lane change happens through downstream promotion gate evaluation rather than inside this wrapper.
7. Given docs and automated coverage are inspected, when the scheduled refresh workflow is reviewed, then the repo documents the cron-safe invocation plus state-file semantics and focused tests prove immutable batch-id generation, state transitions for success and failure, overlap handling, and no direct working-lane mutation inside the wrapper.

## Tasks / Subtasks

- [x] Task 1: Define the scheduled shadow-refresh command contract on top of Story 15.15 (AC: 1, 4, 5)
  - [x] Add a backend-owned scheduled entry point such as `backend/scripts/run_scheduled_legacy_shadow_refresh.py`.
  - [x] Reuse `scripts.run_legacy_refresh.run_legacy_refresh()` directly instead of shelling out to nested `uv` subprocesses from Python.
  - [x] Define explicit CLI arguments at minimum for `--tenant-id`, `--schema`, `--source-schema`, `--lookback-days`, `--reconciliation-threshold`, and a batch-id prefix such as `--batch-prefix`.
  - [x] Generate an immutable UTC batch id for each scheduled run, for example `legacy-shadow-YYYYMMDDTHHMMSSZ`.
  - [x] Keep analyst review import, the working-lane switch itself, and incremental watermark arguments out of this story's scheduled path so unattended runs stay in the safe shadow-refresh lane and feed downstream promotion evaluation rather than owning it.

- [x] Task 2: Persist durable shadow batch state for downstream stories and operators (AC: 2, 3, 4)
  - [x] Add a durable state directory under the existing operations tree, for example `_bmad-output/operations/legacy-refresh/state/`.
  - [x] Write `latest-run.json` for every scheduled invocation.
  - [x] Write `latest-success.json` only for dispositions that count as successful shadow refreshes: `completed` and `completed-review-required`.
  - [x] Define the state payload so later stories can consume it without scraping prose, including at minimum:
    - scheduler run id
    - batch id
    - summary artifact path
    - started and completed timestamps
    - final disposition
    - exit code
    - validation status
    - blocking issue count
    - reconciliation gap count
    - reconciliation threshold
    - analyst-review-required flag
    - `promotion_readiness`
  - [x] Keep state file updates atomic enough that interrupted writes do not leave malformed JSON as the only source of truth.

- [x] Task 3: Add overlap protection and shadow-lane-only safety boundaries (AC: 4, 5, 6)
  - [x] Add a scheduler lock or equivalent guard under the same operations state root so overlapping scheduled runs for the same shadow lane are refused deterministically.
  - [x] Define the overlap outcome clearly in the durable state and terminal summary, including whether the skipped run exits non-zero or uses another explicit operator-visible status.
  - [x] Preserve the previous `latest-success` state when an overlap or failed run occurs.
  - [x] Explicitly avoid performing the working-lane switch or writing approval-request side effects in this story; those belong to the downstream promotion story.

- [x] Task 4: Emit a compact scheduled-run operator summary without replacing the detailed orchestrator summary (AC: 2, 4)
  - [x] Print a concise terminal summary that includes:
    - scheduler run id
    - generated batch id
    - final disposition
    - validation status
    - blocking issue count
    - reconciliation gap count
    - summary artifact path
    - state file paths updated
  - [x] Keep the detailed per-step evidence in the existing Story 15.15 summary JSON and avoid duplicating the full payload into a second verbose report.

- [x] Task 5: Add focused regression coverage for scheduled state tracking (AC: 3, 4, 5, 7)
  - [x] Add focused tests for:
    - immutable batch id generation
    - success updates both `latest-run` and `latest-success`
    - `completed-review-required` still counts as a successful shadow refresh
    - blocked or failed runs update `latest-run` but do not replace `latest-success`
    - overlap protection leaves the previous success state untouched
    - no direct working-lane mutation inside the wrapper
  - [x] Prefer monkeypatch-driven tests around the scheduled wrapper and temporary artifact directories instead of running full live imports.
  - [x] Document any unrelated repo-wide test failures separately rather than weakening this story's assertions.

- [x] Task 6: Document the scheduled shadow-refresh operating model (AC: 7)
  - [x] Update the legacy-import operator docs and migration plan to show the reviewed scheduled entry point, sample cron invocation, and durable state file meanings.
  - [x] Document that scheduled shadow refreshes produce the candidate batch and durable state consumed by Story 15.17; approved corrections remain Story 15.18.

## Dev Notes

### Story Intent

- This story turns the reviewed refresh orchestrator into a repeatable scheduled shadow-refresh job.
- The deliverable is a cron-safe repo entry point plus durable shadow batch state, not the promotion evaluator itself.
- It should make nightly or other approved cadence runs observable and audit-friendly without inventing incremental sync behavior.

### Dependency Context

- Story 15.15 already provides:
  - the reviewed `run_legacy_refresh` execution path
  - stable per-run JSON summaries under `_bmad-output/operations/legacy-refresh/`
  - `promotion_readiness`, validation, and reconciliation gate fields that this story should reuse rather than recompute
- Story 15.17 will depend on this story's durable state to know which shadow batch is the latest reviewed candidate for gated automatic promotion.
- Story 15.18 will depend on the persisted validation and reconciliation fields to classify batches against explicit gate policy.

### Implementation Direction

- Prefer a thin scheduled wrapper around `run_legacy_refresh()` over a second orchestrator implementation.
- Keep all state under the same `_bmad-output/operations/legacy-refresh/` tree so operators have one place to inspect summaries, review exports, and scheduler state.
- Distinguish:
  - shadow refresh success
  - promotion readiness
  - actual working-lane promotion
  These are not the same. A batch may be the latest successful shadow batch while still having `promotion_readiness=false`.
- Treat overlap protection as part of the core operator safety contract. A scheduled job that silently launches two overlapping refreshes would undermine batch/state trust.
- Use immutable batch ids for scheduled runs. Do not reuse the same scheduled batch id across nights.
- Keep actual OS scheduling external to the Python script. The story should provide a cron-safe command surface and repo docs, not a platform-specific daemon or background service.

### Scope Boundaries

- In scope:
  - one scheduled shadow-refresh wrapper command
  - immutable scheduled batch ids
  - durable `latest-run` and `latest-success` state records
  - overlap protection
  - compact operator summaries
- Out of scope:
  - the working-lane promotion evaluator itself (`15.17`)
  - threshold policy redesign or correction proposal workflows (`15.18`)
  - watermark or near-live incremental sync (`15.19`)
  - retirement of dump-era surfaces (`15.20`)

### Existing Repo Constraints

- `backend/scripts/run_legacy_refresh.py` is already the approved full refresh entry point and should remain the only place that owns step sequencing.
- The detailed orchestrator summary already captures:
  - `promotion_readiness`
  - `promotion_gate_status`
  - validation artifact paths
  - reconciliation metrics
  That data should be referenced into scheduler state, not duplicated by recomputation.
- `docs/legacy/migration-plan.md` already states that scheduling is outside Story 15.15, so this story is the right place to introduce the reviewed scheduled wrapper.
- Current local evidence on `2026-04-18` still shows non-zero reconciliation drift, so scheduled runs must preserve failure and blocked states clearly instead of pretending every night is promotion-ready.

### Critical Warnings

- Do **not** mutate the working lane directly in this story.
- Do **not** create approval-request side effects in this story.
- Do **not** treat `completed-review-required` as a failed shadow refresh; it is a successful shadow data refresh with a separate promotion gate still open.
- Do **not** let failed or overlapping runs overwrite the prior `latest-success` pointer.
- Do **not** add platform-specific scheduling services to the repo when a documented cron-safe command is sufficient for this story.

### Suggested Command Shape

An acceptable scheduled entry point shape is:

```bash
cd backend && uv run python -m scripts.run_scheduled_legacy_shadow_refresh \
  --tenant-id <tenant-uuid> \
  --schema raw_legacy \
  --source-schema public \
  --batch-prefix legacy-shadow \
  --lookback-days 10000 \
  --reconciliation-threshold 0
```

An acceptable documented cron example is:

```bash
0 2 * * * cd /path/to/UltrERP/backend && uv run python -m scripts.run_scheduled_legacy_shadow_refresh --tenant-id <tenant-uuid> --schema raw_legacy --source-schema public --batch-prefix legacy-shadow --lookback-days 10000 --reconciliation-threshold 0
```

The exact invocation may vary slightly, but it should stay operator-friendly and reuse the reviewed refresh contract from Story 15.15.

### Testing Notes

- Add focused tests near the other backend script tests, for example `backend/tests/test_run_scheduled_legacy_shadow_refresh.py`.
- Reuse `tmp_path` and monkeypatch-driven summary/state assertions rather than depending on cron or live DB access.
- Keep assertions focused on:
  - batch id format and uniqueness
  - durable state payload shape
  - success versus failure state transitions
  - overlap protection
  - no promotion side effect
- Note the existing broader backend test caveat already documented in recent legacy-import stories:
  - `uv run pytest -q` still has unrelated collection failures outside this slice
  - repo-wide `ruff check` still has unrelated violations outside targeted files

### Project Structure Notes

- Primary implementation surface:
  - `backend/scripts/run_scheduled_legacy_shadow_refresh.py`
- Existing code to reuse:
  - `backend/scripts/run_legacy_refresh.py`
- Likely supporting test surface:
  - `backend/tests/test_run_scheduled_legacy_shadow_refresh.py`
- Likely documentation touch points:
  - `.agents/skills/legacy-import/command-map.md`
  - `docs/legacy/migration-plan.md`
- Durable scheduler state should stay with the existing operations artifacts, not in a new database table, unless a later story explicitly changes that contract.

## References

- `_bmad-output/planning-artifacts/epic-15.md` - Story 15.16 definition and adjacent Epic 15 sequencing
- `_bmad-output/implementation-artifacts/15-15-legacy-refresh-orchestrator.md` - reviewed refresh orchestration contract and summary fields this story must reuse
- `_bmad-output/implementation-artifacts/15-12-live-legacy-db-stage-cli.md` - supported direct-from-legacy ingress path that still underpins scheduled shadow refreshes
- `backend/scripts/run_legacy_refresh.py` - current reviewed refresh entry point and JSON summary contract
- `.agents/skills/legacy-import/command-map.md` - operator command map that should document the scheduled wrapper next
- `docs/legacy/migration-plan.md` - shadow-mode intent, reviewed refresh boundaries, and cutover separation
- `docs/superpowers/specs/2026-03-30-erp-architecture-design-v2.md` - general approval and audit rules; the scheduled wrapper remains promotion-neutral while downstream gate evaluation owns working-lane changes

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- Read Epic 15 planning context in `_bmad-output/planning-artifacts/epic-15.md`
- Read prior implementation context from:
  - `_bmad-output/implementation-artifacts/15-15-legacy-refresh-orchestrator.md`
  - `_bmad-output/implementation-artifacts/15-12-live-legacy-db-stage-cli.md`
- Read operator workflow docs:
  - `.agents/skills/legacy-import/command-map.md`
  - `docs/legacy/migration-plan.md`
- Read supporting code:
  - `backend/scripts/run_legacy_refresh.py`
- Grounded the lock and atomic state-write approach with Python `os.replace()` and
  `tempfile.mkstemp()` documentation; the Context7 library-doc resolve tool was
  unavailable in this environment because it is user-disabled.
- Validation commands:
  - `cd backend && uv run pytest tests/test_run_scheduled_legacy_shadow_refresh.py -q`

### Completion Notes List

- Added `scripts.run_scheduled_legacy_shadow_refresh` as the cron-safe shadow wrapper
  that generates immutable UTC batch ids, reuses `run_legacy_refresh()`, and keeps
  unattended runs inside the shadow lane.
- Persisted per-lane `latest-run.json` and `latest-success.json` state under the
  existing legacy-refresh operations tree with atomic write-then-replace updates and
  explicit overlap-blocked handling via `scheduler.lock`.
- Kept `completed-review-required` eligible for `latest-success` advancement while
  leaving failed, blocked, and overlap runs unable to replace the prior durable
  success pointer.
- Added focused scheduled-wrapper regression coverage for batch-id generation,
  success/failure transitions, overlap protection, and shadow-only write boundaries;
  `cd backend && uv run pytest tests/test_run_scheduled_legacy_shadow_refresh.py -q`
  passed with 8 tests.
- Documented the scheduled entry point, cron example, durable state semantics, and
  stale-lock/operator expectations in the legacy-import command map and migration
  plan.

### File List

- `.agents/skills/legacy-import/command-map.md`
- `backend/scripts/run_scheduled_legacy_shadow_refresh.py`
- `backend/tests/test_run_scheduled_legacy_shadow_refresh.py`
- `docs/legacy/migration-plan.md`
- `_bmad-output/implementation-artifacts/15-16-scheduled-shadow-refresh-and-batch-state-tracking.md`

### Change Log

- 2026-04-18: Added the scheduled shadow-refresh wrapper with immutable UTC batch ids,
  per-lane durable state files, explicit overlap blocking, and compact operator
  summaries layered on top of the existing legacy refresh orchestrator.
- 2026-04-18: Added focused scheduled-wrapper regression coverage and documented the
  cron-safe command plus state-file semantics in the legacy-import operator docs.
