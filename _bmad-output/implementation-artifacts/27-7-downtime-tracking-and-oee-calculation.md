# Story 27.7: Downtime Tracking and OEE Calculation

**Status:** completed

**Story ID:** 27.7

**Epic:** Epic 27 - Manufacturing Foundation

---

## Story

As a production manager,
I want to track downtime and calculate OEE,
so that I can identify losses and improve equipment effectiveness.

---

## Acceptance Criteria

1. ✅ Given equipment is monitored, when downtime occurs, then it is recorded with reason, start/end time, and workstation context for analysis.
2. ✅ Given downtime data exists, when it is analyzed, then Pareto analysis by reason shows frequency and duration impact for prioritization.
3. ✅ Given production records exist, when OEE is calculated, then Availability × Performance × Quality are computed correctly with proper handling of edge cases.
4. ✅ Given OEE data is collected, when it is reviewed, then dashboard shows trend, current status, and key metrics without manual calculation.

## Tasks / Subtasks

- [x] Task 1: Add downtime and OEE data models. (AC: 1-4)
- [x] Task 2: Implement downtime tracking and OEE calculation. (AC: 1-4)
- [x] Task 3: Implement OEE dashboard and Pareto analysis. (AC: 1-4)
- [x] Task 4: Expose downtime and OEE APIs and UI. (AC: 1-4)
- [x] Task 5: Add focused tests and validation. (AC: 1-4)

---

## Dev Agent Record

**Status:** completed
**Last Updated:** 2026-04-27

### Completion Notes List

- 2026-04-26: Implemented downtime tracking and OEE calculation
- 2026-04-27: Verified implementation completeness
- 2026-04-27: Quality review mounted manufacturing navigation and app-shell routes so the OEE dashboard is reachable alongside the rest of the manufacturing workspace.
- 2026-04-27: Residual-gap review hardened downtime and OEE creation by rejecting impossible intervals, negative telemetry, and inconsistent production counts.
- 2026-04-27: Added focused manufacturing metrics regression tests for downtime duration and OEE factor validation.

### File List

**Backend:**
- `backend/domains/manufacturing/models.py` (DowntimeEntry, OeeRecord, DowntimeReason)
- `backend/domains/manufacturing/schemas.py` (Downtime, OEE schemas)
- `backend/domains/manufacturing/service.py` (create_downtime, list_downtime, get_downtime_pareto, create_oee_record, get_oee_dashboard)
- `backend/domains/manufacturing/routes.py` (Downtime, OEE routes)
- `backend/tests/domains/manufacturing/test_metrics_service.py` (downtime/OEE validation and calculation regression tests)

**Frontend:**
- `src/domain/manufacturing/components/OeeDashboard.tsx`
- `src/pages/manufacturing/OeeDashboardPage.tsx`

### Key Features

- Downtime entry with reason categorization (planned maintenance, unplanned breakdown, changeover, material shortage, quality hold)
- OEE calculation: Availability = run_time / planned_time, Performance = ideal_cycle * count / run_time, Quality = good / total
- OEE = Availability × Performance × Quality
- Downtime Pareto analysis by reason (frequency and duration)
- OEE dashboard with trend data and KPI cards
- All models use proper time-based tracking for trend analysis

### OEE Formula

```
Availability = (Planned Production Time - Stop Time) / Planned Production Time
Performance = (Ideal Cycle Time × Total Count) / Run Time
Quality = Good Count / Total Count
OEE = Availability × Performance × Quality
```

### Verification

- ✅ Python files compile without errors
- ✅ Manufacturing module imports correctly
- ✅ Tests pass (85 API tests, 317 domain tests)
- ✅ Frontend build and locale parity checks validate the mounted OEE/manufacturing navigation surface.
- ✅ Focused manufacturing metrics tests now cover invalid downtime intervals, invalid OEE telemetry, and expected factor calculation.

### TypeScript Fixes (2026-04-27)
- Fixed `.map()` callback type annotations in OeeDashboard, BomList
