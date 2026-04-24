# Story 15.28: Admin Legacy Refresh Control Plane

Status: reviewed and validated

## Story

As an admin operator,
I want a reviewed API and admin UI for launching and observing legacy refresh jobs,
so that we can keep data fresh during the coexistence period without driving heavy refresh commands manually from the backend shell.

## Problem Statement

Epic 15 now has a credible full rebaseline path and an incremental execution path, but there is still no control plane for humans who need to operate both systems during the transition period. The current repo has no legacy-import admin routes, no refresh-specific admin client, and no admin UI section that exposes lane state, recent runs, or job launch controls.

The earlier architecture investigation also established an important constraint: this is a long-running, one-way progress workflow, so FastAPI `BackgroundTasks` is the wrong long-term execution model. The control plane needs an admin-authenticated API, a durable worker boundary, and a UI that starts with polling rather than over-engineering real-time transport on day one.

## Solution

Add a long-term legacy-refresh control plane that:

- exposes admin-authenticated trigger and status endpoints under `/api/v1/admin/...`
- launches full rebaseline and incremental jobs through a durable worker boundary rather than request-thread execution or `BackgroundTasks`
- publishes lane state, recent run summaries, manifest and summary paths, batch pointers, and policy outcomes through a typed admin API
- adds an admin page section for trigger controls, recent-run visibility, and blocked-run diagnostics using polling first, with SSE left as an optional later enhancement

This story turns the reviewed refresh pipeline into something operators can actually use while both systems run in parallel.

## Acceptance Criteria

1. Given an authenticated admin wants to keep legacy data fresh, when they use the control plane, then they can trigger either an incremental refresh or a full rebaseline for a selected lane with explicit mode, dry-run, and source-schema options.
2. Given a refresh job is queued, running, completed, blocked, or failed, when the admin status API is queried, then it returns lane state, current and previous batch pointers, `batch_mode`, affected domains, promotion-policy outcome, root failure details, and artifact paths needed for diagnosis.
3. Given another refresh is already in progress for the same lane, when a new trigger request arrives, then the system reuses the reviewed lane-lock semantics and returns a deterministic blocked or conflict response rather than launching overlapping work.
4. Given the admin UI needs progress visibility, when it polls the status surface, then it shows the latest run, latest successful shadow batch, latest promoted batch, and blocked-run reasons without requiring a full page reload.
5. Given refresh execution is long-running and potentially resource-intensive, when the API launches a job, then it hands work to a durable worker or supervised subprocess boundary rather than FastAPI `BackgroundTasks`.

## Tasks / Subtasks

- [x] Task 1: Add admin-authenticated legacy-refresh API routes and schemas. (AC: 1-4)
  - [x] Backend routes trigger refresh jobs, list lane status, and read recent run details under the admin namespace.
  - [x] The existing admin auth pattern from users and audit-log routes is reused.
  - [x] Typed payloads are returned for `latest-run`, `latest-success`, `latest-promoted`, recent job results, and conflict states.
- [x] Task 2: Introduce a durable execution boundary for refresh jobs. (AC: 1, 3, 5)
  - [x] Refresh work launches through the reviewed durable async boundary rather than the request thread or FastAPI `BackgroundTasks`.
  - [x] Existing lane lock and lane-state publication semantics are reused so API-triggered jobs do not create a second concurrency model.
  - [x] Job launch metadata remains auditable and tied to the operator action.
- [x] Task 3: Add a typed frontend admin client and UI surface. (AC: 1, 2, 4)
  - [x] The admin API client includes refresh trigger and status methods.
  - [x] The admin page exposes a legacy refresh section for trigger controls, lane status, and recent runs.
  - [x] Polling remains the initial deterministic transport; SSE stays a later enhancement.
- [x] Task 4: Surface operator-safe diagnostics and history. (AC: 2-4)
  - [x] The UI shows batch ids, mode, affected domains, lock conflicts, promotion-policy classification, and root failure details.
  - [x] Summary and incremental-state artifact paths are surfaced for operator diagnosis.
  - [x] Freshness success, promotion eligibility, and the promoted working batch remain visibly distinct.
- [x] Task 5: Add focused tests and control-plane docs. (AC: 1-5)
  - [x] Backend tests cover admin auth, trigger conflicts, status serialization, and durable launch boundaries.
  - [x] Frontend tests cover lane diagnostics rendering on the admin page.
  - [x] The story record now documents the polling-first transport and the deliberate avoidance of `BackgroundTasks`.

## Dev Notes

### Context

- `backend/app/main.py` already mounts admin route groups under `/api/v1/admin/...`, but there is no legacy-refresh admin surface yet.
- `src/lib/api/admin.ts` and `src/pages/AdminPage.tsx` are the existing typed client and admin UI anchors to extend.
- `backend/pyproject.toml` already includes Redis in the dependency set, which keeps a durable worker boundary feasible without inventing an unrelated stack first.

### Architecture Compliance

- Reuse the existing admin-route dependency pattern from users and audit logs.
- Prefer polling first for one-way status updates; treat SSE as a later enhancement only if the API contract proves stable and the product truly needs live streaming.
- Do not use FastAPI `BackgroundTasks` for the heavy refresh pipeline; keep execution off the request thread and durable enough to survive operator workflows.

### Implementation Guidance

- Primary backend anchors:
  - `backend/app/main.py`
  - `backend/domains/users/routes.py`
  - `backend/domains/audit/routes.py`
  - `backend/scripts/run_incremental_legacy_refresh.py`
  - `backend/scripts/run_scheduled_legacy_shadow_refresh.py`
  - `backend/scripts/legacy_refresh_state.py`
  - `backend/pyproject.toml`
- Primary frontend anchors:
  - `src/lib/api/admin.ts`
  - `src/pages/AdminPage.tsx`
- Status responses should expose enough data for operators to reason about lane health without shell access.
- The control plane should launch the reviewed CLI and script surfaces rather than re-implementing the refresh logic inside HTTP route handlers.

### Testing Requirements

- Cover admin auth, conflict responses, durable job launch, and lane-state serialization on the backend.
- Cover polling, status rendering, and trigger feedback on the frontend.
- If new admin copy or labels are added, keep locale files synchronized.

### References

- `../planning-artifacts/epic-15.md`
- `../implementation-artifacts/15-23-incremental-legacy-refresh-runner-surface.md`
- `../implementation-artifacts/15-27-incremental-validation-and-derived-refresh-scope.md`
- `backend/app/main.py`
- `backend/domains/users/routes.py`
- `backend/domains/audit/routes.py`
- `backend/pyproject.toml`
- `backend/scripts/run_incremental_legacy_refresh.py`
- `backend/scripts/run_scheduled_legacy_shadow_refresh.py`
- `backend/scripts/legacy_refresh_state.py`
- `src/lib/api/admin.ts`
- `src/pages/AdminPage.tsx`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- Review pass on 2026-04-24: `cd backend && source .venv/bin/activate && python -m pytest tests/test_legacy_refresh_control_plane.py -q` (20 passed)
- Review pass on 2026-04-24: `pnpm exec vitest run src/pages/AdminPage.test.tsx` (2 passed)

### Completion Notes List

- 2026-04-24 review pass: `_load_lane_status(...)` now surfaces `batch_mode`, `affected_domains`, `rebaseline_reason`, and detailed root-failure metadata from persisted lane-state records instead of dropping them.
- 2026-04-24 review pass: the admin page now renders current mode, affected domains, latest summary path, and incremental-state path for each lane, and blocked diagnostics stay visible during polling.
- 2026-04-24 review pass: disposition badges now treat lowercase backend statuses such as `completed` and `validation-blocked` correctly.

### File List

- `backend/domains/legacy_import/routes.py`
- `backend/tests/test_legacy_refresh_control_plane.py`
- `src/pages/AdminPage.tsx`
- `src/pages/AdminPage.test.tsx`
- `public/locales/en/common.json`
- `public/locales/zh-Hant/common.json`
- `_bmad-output/implementation-artifacts/15-28-admin-legacy-refresh-control-plane.md`