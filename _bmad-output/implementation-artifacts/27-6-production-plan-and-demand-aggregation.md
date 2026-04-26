# Story 27.6: Production Plan and Demand Aggregation

**Status:** committed

**Story ID:** 27.6

**Epic:** Epic 27 - Manufacturing Foundation

---

## Story

As a manufacturing planner,
I want a formal production plan that aggregates demand, materials, and capacity,
so that proposed work orders can be reviewed, firmed, and measured against actual production.

---

## Problem Statement

Story 27.4 adds lightweight proposal generation from demand signals, but it remains an operational recommendation layer rather than a formal planning document. That is not enough for period-based planning, make-to-stock overlays, capacity-versus-demand visibility, or plan-accuracy reporting. Without a formal production-plan record, planners cannot group demand over a horizon, compare planned load to workstation capacity, or firm a controlled set of work orders for a planning cycle.

ERPNext's Production Plan is much larger, including sub-assembly and procurement planning. Epic 27 needs a smaller but still formal production-plan layer that aggregates demand from sales orders plus bounded forecast input, highlights material and capacity constraints, and converts approved lines into firm work orders.

## Solution

Add a production-plan domain that:

- stores a plan header and plan lines for a date range or planning horizon
- aggregates demand from sales orders and manual forecast lines into one reviewable planning record
- groups and bulk-manages the lightweight proposal layer from Story 27.4 instead of introducing a second proposal-review system
- evaluates material availability and routing-based capacity load before firming work orders
- tracks planned versus actual results so planners can measure planning accuracy over time

Keep the slice bounded. Land plan records, demand aggregation, capacity visibility, and firming while deferring full MRP procurement generation, sub-assembly explosion, and optimizer-style scheduling.

## Acceptance Criteria

1. Given sales orders exist for manufactured items, when a production plan is generated, then total demand is aggregated into reviewable plan lines.
2. Given manual forecast quantities are needed, when the planner adds them, then they are tracked explicitly inside the production plan instead of inventing a separate forecast subsystem.
3. Given material shortages or capacity overload exist, when the production plan is reviewed, then constrained items are flagged clearly for planner action.
4. Given a planner firms the plan, when selected lines are approved, then proposed work orders become firm work orders linked back to the plan.
5. Given the plan period ends, when actual production is compared to the plan, then planned-versus-actual completion is reportable for accuracy analysis.

## Tasks / Subtasks

- [ ] Task 1: Add production-plan persistence and demand-line models. (AC: 1-5)
  - [ ] Add `ProductionPlan`, `ProductionPlanLine`, and `ProductionPlanForecastLine` or equivalent bounded forecast structure under the manufacturing domain.
  - [ ] Include fields for plan period, status, planning strategy such as make-to-order or make-to-stock, notes, and firmed timestamp metadata.
  - [ ] Include line fields for product, BOM, demand source, forecast quantity, proposed production quantity, shortage summary, capacity summary, linked proposal references, and linked work-order references.
  - [ ] Add the required Alembic migration.
- [ ] Task 2: Implement plan aggregation, shortage evaluation, and capacity load calculation. (AC: 1-3)
  - [ ] Aggregate demand from confirmed sales orders plus any manual forecast lines entered on the plan.
  - [ ] Evaluate material availability using active BOMs and current inventory state.
  - [ ] Evaluate capacity load using routing and workstation data from Story 27.5.
  - [ ] Surface overload and shortage conditions explicitly on plan lines.
- [ ] Task 3: Implement plan review and firming workflow. (AC: 3-5)
  - [ ] Support draft, reviewed, firmed, and closed plan states or an equivalent explicit lifecycle.
  - [ ] Allow planners to review and bulk-manage the lightweight proposal records generated under or attached to the plan instead of introducing a second proposal entity with separate approve or reject semantics.
  - [ ] Convert accepted proposal-backed lines into linked work orders via the existing manufacturing services.
  - [ ] Keep the plan-to-work-order linkage explicit for later accuracy reporting.
- [ ] Task 4: Expose APIs and frontend planning workspace. (AC: 1-5)
  - [ ] Add plan list, detail, aggregation, and firming endpoints under the manufacturing API.
  - [ ] Add `src/pages/manufacturing/ProductionPlansPage.tsx` and a plan-detail page or panel.
  - [ ] Surface demand source, material shortfalls, capacity load, and planner overrides in the UI.
  - [ ] Provide a simple plan accuracy view comparing planned vs. actual completion.
- [ ] Task 5: Add focused tests and validation. (AC: 1-5)
  - [ ] Add backend tests for demand aggregation, forecast inclusion, shortage flags, capacity overload flags, and firming behavior.
  - [ ] Add frontend tests for plan review, overload visibility, line overrides, firming, and planned-vs-actual reporting.
  - [ ] Validate that the plan uses routing capacity and does not bypass work-order creation rules.

## Dev Notes

### Context

- Story 27.4 provides lightweight proposal generation; this story adds the formal planning record and planning-horizon workflow.
- Story 27.5 provides routing and workstation capacity inputs; this story should consume them rather than reinvent capacity logic.
- UltrERP does not currently have a forecast domain, so bounded manual forecast lines inside the plan are the safest first slice.

### Architecture Compliance

- Keep formal production planning inside the manufacturing domain and reuse existing order, inventory, and work-order services as inputs.
- Forecast support in this story should stay bounded to explicit plan lines; do not add a free-floating global forecast subsystem.
- Keep firming explicit and auditable. The planner should choose when proposals become firm work orders.
- Planned-versus-actual reporting should be derived from linked work-order outcomes, not from disconnected spreadsheet-style fields.
- Reuse Story 27.4 `ManufacturingProposal` records as the only proposal-review object. `ProductionPlan` should group, filter, bulk-manage, and firm those proposals rather than creating a second parallel approve or reject workflow.

### Implementation Guidance

- Likely backend files:
  - `backend/domains/manufacturing/models.py`
  - `backend/domains/manufacturing/planning_service.py`
  - `backend/domains/manufacturing/routes.py`
  - `backend/domains/manufacturing/schemas.py`
  - `migrations/versions/*_production_plan.py`
- Likely frontend files:
  - `src/lib/api/manufacturing.ts`
  - `src/domain/manufacturing/hooks/useProductionPlans.ts`
  - `src/domain/manufacturing/components/ProductionPlanTable.tsx`
  - `src/domain/manufacturing/components/ProductionPlanDetail.tsx`
  - `src/pages/manufacturing/ProductionPlansPage.tsx`
- If capacity visualization is needed, keep it summary-level by workstation or routing rather than a full drag-and-drop scheduler.
- Plan accuracy should compare planned quantity to completed work-order quantity for the plan period.

### What NOT to implement

- Do **not** implement full MRP procurement document generation or automatic purchase requests in this story.
- Do **not** implement sub-assembly explosion, multi-level BOM planning, or optimizer-grade scheduling.
- Do **not** introduce a separate enterprise forecasting subsystem beyond manual plan-line adjustments.
- Do **not** auto-firm work orders just because a plan exists.
- Do **not** introduce a second persisted proposal entity or duplicate accept or reject workflow beside Story 27.4.

### Testing Standards

- Include a regression proving sales-order demand and manual forecast lines aggregate into one plan view.
- Include a regression proving overload or shortage flags remain visible after planners adjust line quantities.
- Include a regression proving firmed plan lines create linked work orders and can later be compared to actual completion.

## Dependencies & Related Stories

- **Depends on:** Story 27.4, Story 27.5
- **Related to:** Story 27.2 and Story 27.3 for final execution, Story 27.7 for operational reporting context
- **Cross-epic:** Builds on orders demand and current inventory availability while staying compatible with future procurement planning work.

## References

- `../planning-artifacts/epic-27.md`
- `plans/2026-04-21-UltrERP-ERPNext-Comprehensive-Gap-Analysis-v1.md`
- `reference/erpnext-develop/erpnext/manufacturing/doctype/production_plan/production_plan.json`
- `reference/erpnext-develop/erpnext/manufacturing/doctype/routing/routing.json`
- `https://docs.frappe.io/erpnext/user/manual/en/production-plan`
- `CLAUDE.md`

---

## Dev Agent Record

**Status:** committed
**Last Updated:** 2026-04-27

### Completion Notes List

- 2026-04-26: Story drafted from Epic 27 planning scope, ERPNext production-plan references, and the current UltrERP orders, inventory, and routing-based planning seams.

### File List

- `_bmad-output/implementation-artifacts/27-6-production-plan-and-demand-aggregation.md`

**Implementation Notes:**
- ProductionPlan and ProductionPlanLine models implemented
- Demand aggregation from sales orders and manual forecast lines
- Material and capacity shortage/capacity summary per line
- Make-to-order and make-to-stock strategies
- Plan firming workflow creates linked work orders
- Planned vs actual completion tracking for accuracy reporting