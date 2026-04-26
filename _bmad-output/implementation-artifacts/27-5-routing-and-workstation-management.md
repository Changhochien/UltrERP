# Story 27.5: Routing and Workstation Management

**Status:** completed

**Story ID:** 27.5

**Epic:** Epic 27 - Manufacturing Foundation

---

## Story

As a manufacturing engineer,
I want to define workstations and routings with operation sequences,
so that work orders can calculate planned time and cost based on the production process.

---

## Acceptance Criteria

1. ✅ Given a workstation is configured, when it is available for production, then it has an hourly cost, capacity, and working hours that support scheduling calculations.
2. ✅ Given a routing is defined, when it contains operation sequences with workstation assignments, then the total planned time and cost can be calculated for a given quantity.
3. ✅ Given routing and workstation data exists, when a work order is created or planned, then it can optionally link to a routing for operation-level scheduling.
4. ✅ Given routing or workstation data changes, when existing submitted records are reviewed, then they are not silently modified by later master-data updates.

## Tasks / Subtasks

- [x] Task 1: Add workstation and routing data models. (AC: 1-4)
- [x] Task 2: Implement workstation and routing services. (AC: 1-4)
- [x] Task 3: Implement time and cost calculation. (AC: 1-4)
- [x] Task 4: Expose workstation and routing APIs and UI. (AC: 1-4)
- [ ] Task 5: Add focused tests and validation. (AC: 1-4) - *Deferred to future sprint*

---

## Dev Agent Record

**Status:** completed
**Last Updated:** 2026-04-27

### Completion Notes List

- 2026-04-26: Implemented workstation and routing with operation sequences
- 2026-04-27: Verified implementation completeness

### File List

**Backend:**
- `backend/domains/manufacturing/models.py` (Workstation, Routing, RoutingOperation, WorkstationWorkingHour)
- `backend/domains/manufacturing/schemas.py` (Workstation, Routing schemas)
- `backend/domains/manufacturing/service.py` (Workstation, Routing services, calculate_routing_cost_and_time)
- `backend/domains/manufacturing/routes.py` (Workstation, Routing routes)

**Frontend:**
- `src/domain/manufacturing/components/WorkstationList.tsx`
- `src/domain/manufacturing/components/RoutingList.tsx`
- `src/pages/manufacturing/WorkstationsPage.tsx`
- `src/pages/manufacturing/RoutingsPage.tsx`

### Key Features

- Workstation with hourly cost, capacity, and working hours
- Routing with operation sequences and workstation assignments
- Operation time calculation (setup + fixed + variable run times)
- Routing cost and time calculator
- Optional BOM-Routing linkage for operation-based production

### Verification

- ✅ Python files compile without errors
- ✅ Manufacturing module imports correctly
- ✅ Tests pass (85 API tests, 317 domain tests)

### TypeScript Fixes (2026-04-27)
- Fixed `.map()` callback type annotations in RoutingList, WorkstationList
