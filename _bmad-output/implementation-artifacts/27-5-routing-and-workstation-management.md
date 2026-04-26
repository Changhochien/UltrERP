# Story 27.5: Routing and Workstation Management

**Status:** review

**Story ID:** 27.5

**Epic:** Epic 27 - Manufacturing Foundation

---

## Story

As a manufacturing planner,
I want reusable routing templates and workstation masters,
so that work orders can estimate time, labor cost, and basic operation sequencing before execution begins.

---

## Problem Statement

Stories 27.1 through 27.3 provide BOMs, work orders, and stock execution, but they still treat manufacturing as a single opaque step. Without routings and workstations, planners cannot model operation sequences, estimate labor or machine cost, or preview how long a work order should take. That leaves Epic 27 with production records but no manufacturable process definition.

ERPNext separates Routing and Workstation so one operation sequence can be reused across items and work orders can inherit operation timing and workstation context. Epic 27 should adopt that core pattern while stopping short of full job-card execution, employee time logs, holiday-aware optimization, or a full plant-floor board.

## Solution

Add routing and workstation masters that:

- define workstations with cost, basic capacity, and working-hour availability
- define routings as reusable operation sequences with workstation, setup time, and fixed or variable run-time inputs
- let BOMs or work orders inherit routings so planned production time and operation cost can be estimated before work starts

Keep the first slice focused on planning and costing. Land reusable routing templates, workstation availability, and simple operation schedules while deferring job-card execution, employee assignment, and full scheduling optimization.

## Acceptance Criteria

1. Given a workstation is configured with hourly cost and basic capacity, when a work order uses operations on that workstation, then the planned operation labor or machine cost is calculated correctly.
2. Given a routing is defined for a product, when a work order is created from a BOM that uses that routing, then the operation sequence and time estimates are inherited into the work order.
3. Given a work order uses multiple operations, when planned time is calculated, then setup plus fixed and variable run-time inputs produce a clear planned duration and operation-cost estimate.
4. Given a work order is scheduled, when the planner reviews the detail, then the system can display a basic operation timeline derived from workstation availability, sequence order, and any explicitly modeled overlap rules.
5. Given production requires specific workstations, when the routing is configured, then operation assignments remain explicit and auditable.

## Tasks / Subtasks

- [ ] Task 1: Add workstation and routing persistence. (AC: 1-5)
  - [ ] Add `Workstation`, `WorkstationWorkingHour`, `Routing`, and `RoutingOperation` models under the manufacturing domain.
  - [ ] Include workstation fields for name, description, status, hourly cost, job capacity, disabled flag, and working-hour windows.
  - [ ] Include routing fields for name, disabled flag, and operation rows.
  - [ ] Include routing-operation fields for operation name, workstation, sequence, setup minutes, fixed run minutes, variable run minutes per unit or batch, batch size, and optional overlap metadata.
- [ ] Task 2: Implement routing inheritance and planning calculators. (AC: 1-4)
  - [ ] Add services to create and update routings and workstations.
  - [ ] Allow a BOM to reference a routing and snapshot routing operations onto a work order when appropriate.
  - [ ] Calculate planned minutes and planned operating cost for each operation and for the whole work order.
  - [ ] Keep overlap support explicit and simple, such as overlap lag minutes or overlap percentage, rather than a full scheduling engine.
- [ ] Task 3: Implement workstation availability and basic timeline scheduling. (AC: 1-4)
  - [ ] Use workstation working-hour windows and capacity to compute a basic planned start and end window for each operation.
  - [ ] Respect routing sequence order when building the operation timeline.
  - [ ] Surface overload or unavailable-workstation situations clearly instead of silently dropping operations.
- [ ] Task 4: Expose APIs and frontend management UI. (AC: 1-5)
  - [ ] Add list, detail, and create or update endpoints for workstations and routings.
  - [ ] Add `src/pages/manufacturing/WorkstationsPage.tsx` and `src/pages/manufacturing/RoutingsPage.tsx` plus any detail or edit pages needed.
  - [ ] Add routing and workstation forms, tables, and timeline visualizations under `src/domain/manufacturing/`.
  - [ ] Surface inherited routing operations on work-order detail screens.
- [ ] Task 5: Add focused tests and validation. (AC: 1-5)
  - [ ] Add backend tests for workstation cost calculations, routing inheritance, sequence ordering, and simple availability scheduling.
  - [ ] Add frontend tests for workstation authoring, routing authoring, inherited operation display, and timeline rendering.
  - [ ] Validate that the first slice remains planning-oriented and does not introduce job-card execution depth.

## Dev Notes

### Context

- Epic 27 originally stopped short of full routing parity, but the gap analysis explicitly recommended adding Routing, Workstation, and Downtime coverage to Epic 27.
- ERPNext stores routings as reusable operation templates and workstations as cost and capacity resources.
- Story 27.2 and Story 27.3 provide the work-order document that routing will enrich; this story should not replace that workflow with a job-card-first model.
- Story 27.1 is the BOM foundation where routing linkage will be stored or resolved for manufactured products.

### Architecture Compliance

- Keep workstation and routing masters in the manufacturing domain; do not hide them under settings just because they are master data.
- Snapshot routing operations onto work orders when planning starts so later routing edits do not silently rewrite existing work-order plans.
- Model workstation availability simply and explicitly. A clear basic schedule is better than an implied optimizer.
- Use route and page patterns already established in procurement and accounting for new manufacturing management pages.

### Implementation Guidance

- Likely backend files:
  - `backend/domains/manufacturing/models.py`
  - `backend/domains/manufacturing/service.py`
  - `backend/domains/manufacturing/routes.py`
  - `backend/domains/manufacturing/schemas.py`
  - `migrations/versions/*_manufacturing_routing_workstations.py`
- Likely frontend files:
  - `src/lib/api/manufacturing.ts`
  - `src/domain/manufacturing/hooks/useRoutings.ts`
  - `src/domain/manufacturing/hooks/useWorkstations.ts`
  - `src/domain/manufacturing/components/RoutingForm.tsx`
  - `src/domain/manufacturing/components/WorkstationForm.tsx`
  - `src/domain/manufacturing/components/OperationTimeline.tsx`
  - `src/pages/manufacturing/RoutingsPage.tsx`
  - `src/pages/manufacturing/WorkstationsPage.tsx`
- If routing linkage is stored on BOM, keep it optional so Story 27.1 can land without routing support first.
- If workstation working hours are introduced, keep them simple daily windows for the first slice.

### What NOT to implement

- Do **not** implement Job Cards, employee assignment, time logs, or operation completion tracking in this story.
- Do **not** implement holiday-list, overtime, or plant-floor optimization depth beyond basic availability windows.
- Do **not** implement a full finite-capacity scheduler or critical-path optimizer.
- Do **not** make routing mandatory for every BOM or work order in the first slice.

### Testing Standards

- Include a regression proving workstation hourly cost flows into planned operation cost.
- Include a regression proving routing edits do not silently rewrite already-created work orders.
- Include a regression proving unavailable workstations or capacity overload are surfaced explicitly.

## Dependencies & Related Stories

- **Depends on:** Story 27.1, Story 27.2
- **Related to:** Story 27.1 for optional BOM linkage, Story 27.6 for later capacity-based planning, Story 27.7 for downtime and OEE metrics

## References

- `../planning-artifacts/epic-27.md`
- `plans/2026-04-21-UltrERP-ERPNext-Comprehensive-Gap-Analysis-v1.md`
- `reference/erpnext-develop/erpnext/manufacturing/doctype/routing/routing.json`
- `reference/erpnext-develop/erpnext/manufacturing/doctype/workstation/workstation.json`
- `https://docs.frappe.io/erpnext/user/manual/en/routing`
- `https://docs.frappe.io/erpnext/user/manual/en/workstation`
- `CLAUDE.md`

---

## Dev Agent Record

**Status:** ready-for-dev
**Last Updated:** 2026-04-26

### Completion Notes List

- 2026-04-26: Story drafted from Epic 27 routing additions, ERPNext routing and workstation reference code, official docs, and current UltrERP work-order planning seams.

### File List

- `_bmad-output/implementation-artifacts/27-5-routing-and-workstation-management.md`

**Implementation Notes:**
- Workstation and Routing models fully implemented
- Workstation includes hourly cost, capacity, and working hours
- Routing includes operation sequences with workstation assignments
- Operation time calculation (setup + fixed + variable run times)
- Routing cost and time calculator service implemented
- Optional BOM-Routing linkage for operation-based production