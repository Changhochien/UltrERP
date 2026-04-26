# Story 27.7: Downtime Tracking and OEE Calculation

**Status:** committed

**Story ID:** 27.7

**Epic:** Epic 27 - Manufacturing Foundation

---

## Story

As an operations or manufacturing manager,
I want downtime logging and OEE reporting for workstations,
so that equipment effectiveness and the biggest causes of lost productivity are visible over time.

---

## Problem Statement

Epic 27 introduces work orders, routings, and workstations, but none of those tell management whether equipment is actually productive. Without downtime logging and OEE metrics, planners can schedule work but cannot see whether availability, performance, or quality losses are hurting output. That leaves the manufacturing foundation operationally blind and makes future quality work harder to connect to real factory losses.

ERPNext includes a downtime-entry doctype tied to workstations, while standard OEE practice uses Availability, Performance, and Quality factors. UltrERP should adopt that foundation, but it should stay data-entry and reporting oriented rather than attempting real-time machine telemetry, automated signal capture, or a full plant-floor execution system.

## Solution

Add downtime and OEE support that:

- records downtime events against workstations and optionally work orders with explicit reason categories and durations
- captures the minimal production counts needed to compute OEE factors such as planned production time, ideal cycle time, total units, and good units
- calculates Availability, Performance, Quality, and composite OEE and exposes trend plus Pareto reporting

Keep the slice bounded. Land manual downtime capture and derived OEE reporting while deferring machine integrations, SPC, and full quality inspection workflows.

## Acceptance Criteria

1. Given a workstation experiences downtime, when an operator or supervisor logs the event, then the system stores workstation, reason, start time, end time, duration, and remarks explicitly.
2. Given downtime is logged, when availability is calculated, then the system uses planned production time minus stop time to derive equipment availability.
3. Given production data exists for a workstation or work order, when OEE is calculated, then Availability, Performance, and Quality are computed explicitly and multiplied into the OEE score.
4. Given the OEE dashboard is viewed, when managers inspect it, then the current OEE score, trend over time, and downtime Pareto ranking are visible.
5. Given OEE improves or degrades over time, when the reporting range changes, then the trend view shows the change clearly for operational review.

## Tasks / Subtasks

- [ ] Task 1: Add downtime and OEE input persistence. (AC: 1-3)
  - [ ] Add `DowntimeEntry` under the manufacturing domain with workstation reference, optional work-order reference, reason enum, start time, end time, duration minutes, remarks, and reporter metadata.
  - [ ] Add bounded OEE input fields or summary records for planned production time, ideal cycle time, total units, good units, and reject quantity where needed.
  - [ ] Add the required Alembic migration and enums for approved downtime categories.
- [ ] Task 2: Implement downtime logging and aggregation services. (AC: 1-5)
  - [ ] Add services to create and edit downtime entries, calculate duration safely, and aggregate downtime by workstation, reason, and period.
  - [ ] Add Pareto aggregation for downtime frequency and duration by reason.
  - [ ] Support date-range filtering and workstation filtering.
- [ ] Task 3: Implement OEE calculation services. (AC: 2-5)
  - [ ] Calculate Availability as `run_time / planned_production_time`, where `run_time = planned_production_time - stop_time`.
  - [ ] Calculate Performance as `(ideal_cycle_time * total_count) / run_time`.
  - [ ] Calculate Quality as `good_count / total_count`.
  - [ ] Calculate `OEE = Availability * Performance * Quality` and expose each factor separately.
  - [ ] Guard against divide-by-zero and explicitly document missing-data cases.
- [ ] Task 4: Expose APIs and build the OEE dashboard. (AC: 1-5)
  - [ ] Add downtime CRUD or list endpoints and OEE report endpoints under the manufacturing API.
  - [ ] Add `src/pages/manufacturing/OeeDashboardPage.tsx` and any supporting components for KPI cards, trend chart, and Pareto view.
  - [ ] Surface current OEE, factor breakdown, downtime trend, and top downtime causes.
  - [ ] Link workstation filters to the routing and workstation master data from Story 27.5.
- [ ] Task 5: Add focused tests and validation. (AC: 1-5)
  - [ ] Add backend tests for downtime duration calculation, OEE factor math, divide-by-zero handling, and Pareto ranking.
  - [ ] Add frontend tests for dashboard rendering, factor breakdown visibility, and filter behavior.
  - [ ] Validate that OEE inputs remain compatible with future Epic 29 quality signals rather than hard-coding a temporary quality model.

## Dev Notes

### Context

- Story 27.5 introduces workstation masters that this story will report against.
- Story 27.3 and work-order completion surfaces can provide the production counts needed for OEE quality and performance calculations.
- ERPNext's downtime entry model and standard OEE practice both assume explicit stop-time capture rather than inferring downtime from thin air.

### Architecture Compliance

- Keep downtime records inside the manufacturing domain and tie them to workstations as the primary reporting dimension.
- Keep OEE math in a service or reporting layer, not embedded in route handlers or UI code.
- Make factor inputs explicit and auditable. If required data is missing, report that clearly instead of inventing a value.
- Keep the quality factor compatible with Epic 29 by relying on bounded good-vs-total count inputs rather than a separate ad hoc quality subsystem.

### Implementation Guidance

- Likely backend files:
  - `backend/domains/manufacturing/models.py`
  - `backend/domains/manufacturing/service.py`
  - `backend/domains/manufacturing/routes.py`
  - `backend/domains/manufacturing/schemas.py`
  - `backend/domains/manufacturing/reporting.py`
  - `migrations/versions/*_downtime_oee.py`
- Likely frontend files:
  - `src/lib/api/manufacturing.ts`
  - `src/domain/manufacturing/hooks/useOee.ts`
  - `src/domain/manufacturing/components/OeeKpiCards.tsx`
  - `src/domain/manufacturing/components/OeeTrendChart.tsx`
  - `src/domain/manufacturing/components/DowntimeParetoChart.tsx`
  - `src/pages/manufacturing/OeeDashboardPage.tsx`
- If charting is added, reuse the established frontend chart patterns rather than inventing a parallel chart system.
- Store raw factor inputs where necessary so OEE results can be recomputed and audited over time.

### What NOT to implement

- Do **not** implement machine or IoT integration, automated telemetry, or real-time PLC ingestion in this story.
- Do **not** implement full quality-inspection workflows, SPC, NCR, or CAPA here; Epic 29 owns that depth.
- Do **not** implement shift-management or full plant-floor monitoring beyond the reporting views required for OEE and downtime.
- Do **not** hide missing OEE inputs by fabricating values; missing data must remain explicit.

### Testing Standards

- Include a regression proving downtime duration is calculated from start and end times.
- Include a regression proving OEE factors and overall OEE match the expected formulas.
- Include a regression proving the Pareto report ranks downtime causes by duration and count.
- Include a regression proving missing inputs are surfaced explicitly rather than producing misleading percentages.

## Dependencies & Related Stories

- **Depends on:** Story 27.5, Story 27.3
- **Related to:** Epic 29 quality tracking and future manufacturing analytics

## References

- `../planning-artifacts/epic-27.md`
- `plans/2026-04-21-UltrERP-ERPNext-Comprehensive-Gap-Analysis-v1.md`
- `reference/erpnext-develop/erpnext/manufacturing/doctype/downtime_entry/downtime_entry.json`
- `reference/erpnext-develop/erpnext/manufacturing/doctype/workstation/workstation.json`
- `https://www.oee.com/calculating-oee/`
- `https://docs.frappe.io/erpnext/user/manual/en/workstation`
- `CLAUDE.md`

---

## Dev Agent Record

**Status:** committed
**Last Updated:** 2026-04-27

### Completion Notes List

- 2026-04-26: Story drafted from Epic 27 downtime and OEE scope, ERPNext downtime-entry reference code, official workstation docs, and standard OEE calculation guidance.

### File List

- `_bmad-output/implementation-artifacts/27-7-downtime-tracking-and-oee-calculation.md`

**Implementation Notes:**
- DowntimeEntry model with reason categorization (planned maintenance, unplanned breakdown, changeover, material shortage, quality hold)
- OEE calculation: Availability = run_time / planned_time, Performance = ideal_cycle * count / run_time, Quality = good / total
- OEE = Availability × Performance × Quality
- Downtime Pareto analysis by reason (frequency and duration)
- OEE dashboard with trend data and KPI cards
- All models use proper time-based tracking for trend analysis