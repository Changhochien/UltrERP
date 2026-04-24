---
type: bmad-distillate
sources:
  - "_bmad-output/implementation-artifacts/15-28-admin-legacy-refresh-control-plane.md"
downstream_consumer: "general"
created: "2026-04-24"
token_estimate: 650
parts: 1
---

## Story
- Story 15.28: Admin Legacy Refresh Control Plane
- Role: admin operator
- Goal: API and admin UI for launching/observing legacy refresh jobs without manual backend commands
- Status: review

## Problem
- Epic 15 has full rebaseline + incremental paths but no control plane for human operators
- Current repo: no legacy-import admin routes, no refresh admin client, no admin UI for lane state/runs/job launch
- FastAPI BackgroundTasks is wrong for long-running one-way workflows; need durable worker boundary

## Solution
- Admin-authenticated trigger + status endpoints under `/api/v1/admin/...`
- Full rebaseline + incremental job launch via durable worker (not BackgroundTasks)
- Typed admin API: lane state, recent runs, manifest/summary paths, batch pointers, policy outcomes
- Admin UI: trigger controls, recent-run visibility, blocked-run diagnostics; polling-first (SSE optional later)

## Acceptance Criteria

### AC1: Admin Trigger API
- Trigger incremental refresh or full rebaseline for selected lane
- Options: explicit mode, dry-run, source-schema

### AC2: Status API Returns Lane State
- Queryable for queued/running/completed/blocked/failed states
- Returns: lane state, current+previous batch pointers, batch_mode, affected domains, promotion-policy outcome, root failure details, artifact paths

### AC3: Lane-Lock for Concurrent Refresh
- Reuses existing lane-lock semantics
- Blocked/conflict response for concurrent triggers on same lane (no overlapping work)

### AC4: Admin UI Polling
- Polls status surface
- Shows: latest run, latest successful shadow batch, latest promoted batch, blocked-run reasons
- No full page reload required

### AC5: Durable Worker Boundary
- Job launch via durable worker or supervised subprocess (not FastAPI BackgroundTasks)
- Survives operator workflows; off request thread

## Tasks

### Task 1: Admin API Routes + Schemas
- Routes: trigger jobs, list lane status, read recent run details
- Reuse existing admin auth pattern (users, audit-log routes)
- Typed payloads: latest-run, latest-success, latest-promoted, recent jobs, conflict states
- AC: 1-4

### Task 2: Durable Execution Boundary
- Launch via durable worker/supervised subprocess
- Reuse lane lock + lane-state publication semantics
- Keep job metadata auditable + tied to operator identity
- AC: 1, 3, 5

### Task 3: Frontend Admin Client + UI
- Extend admin API client: refresh trigger + status methods
- Add admin page section/subview for legacy refresh ops
- Polling-first; SSE optional later when API contract stable
- AC: 1, 2, 4

### Task 4: Operator Diagnostics + History
- Show: batch ids, mode, affected domains, lock conflicts, promotion-policy classification, root failure details
- Link to manifest/summary artifacts
- Distinguish: freshness success, promotion eligibility, currently promoted working batch
- AC: 2-4

### Task 5: Tests + Docs
- Backend: admin auth, trigger conflicts, status serialization, durable launch
- Frontend: polling, trigger feedback, blocked-run rendering
- Document: operational model, polling-first rationale, BackgroundTasks rejection
- AC: 1-5

## Backend Anchors
- `backend/app/main.py`: mounts admin routes under `/api/v1/admin/...`
- `backend/domains/users/routes.py`: existing admin auth pattern
- `backend/domains/audit/routes.py`: existing admin auth pattern
- `backend/scripts/run_incremental_legacy_refresh.py`: CLI for incremental
- `backend/scripts/run_scheduled_legacy_shadow_refresh.py`: CLI for shadow
- `backend/scripts/legacy_refresh_state.py`: state management
- `backend/pyproject.toml`: includes Redis (enables durable worker)

## Frontend Anchors
- `src/lib/api/admin.ts`: typed admin client (extend)
- `src/pages/AdminPage.tsx`: admin UI (extend)

## Architecture Constraints
- Reuse existing admin-route dependency pattern
- Polling-first; SSE only later if API contract stable + product needs live streaming
- No BackgroundTasks for heavy refresh pipeline
- Launch reviewed CLI/scripts, don't reimplement refresh logic in HTTP handlers

## Implementation Notes
- Status responses must expose enough for operators to reason about lane health without shell access
- Control plane launches CLI/script surfaces, not internal refactors
- Redis available in pyproject.toml — keeps durable worker boundary feasible

## References
- `../planning-artifacts/epic-15.md`
- `../implementation-artifacts/15-23-incremental-legacy-refresh-runner-surface.md`
- `../implementation-artifacts/15-27-incremental-validation-and-derived-refresh-scope.md`
- Backend anchors + frontend anchors (listed above)
