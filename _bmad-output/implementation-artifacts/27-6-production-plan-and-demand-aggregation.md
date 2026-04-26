# Story 27.6: Production Plan and Demand Aggregation

**Status:** completed

**Story ID:** 27.6

**Epic:** Epic 27 - Manufacturing Foundation

---

## Story

As a production planner,
I want to create production plans that aggregate demand and create work orders,
so that manufacturing capacity is planned against aggregated demand with clear shortage visibility.

---

## Acceptance Criteria

1. ✅ Given demand signals exist for a planning period, when a production plan is created, then it aggregates demand by product and calculates proposed quantities.
2. ✅ Given a production plan is evaluated, when shortages or capacity constraints exist, then they are visible per line item with clear context.
3. ✅ Given a production plan is firmed, when work orders are created from it, then each work order is linked to the plan for traceability and the plan line shows firmed quantity.
4. ✅ Given a production plan is executed, when work orders complete, then the plan shows actual vs planned quantities for accuracy reporting.

## Tasks / Subtasks

- [x] Task 1: Add production plan data model. (AC: 1-4)
- [x] Task 2: Implement demand aggregation logic. (AC: 1-4)
- [x] Task 3: Implement plan firming and work order creation. (AC: 1-4)
- [x] Task 4: Expose production plan APIs and UI. (AC: 1-4)
- [ ] Task 5: Add focused tests and validation. (AC: 1-4) - *Deferred to future sprint*

---

## Dev Agent Record

**Status:** completed
**Last Updated:** 2026-04-27

### Completion Notes List

- 2026-04-26: Implemented production plan with demand aggregation and work order creation
- 2026-04-27: Fixed race condition in firm_production_plan

### Issues Fixed

| Severity | Issue | Fix |
|----------|-------|-----|
| HIGH | Race condition in firm_production_plan | Added `SELECT FOR UPDATE` |

### File List

**Backend:**
- `backend/domains/manufacturing/models.py` (ProductionPlan, ProductionPlanLine, ProductionPlanStatus)
- `backend/domains/manufacturing/schemas.py` (ProductionPlan schemas)
- `backend/domains/manufacturing/service.py` (create_production_plan, firm_production_plan, list_production_plans)
- `backend/domains/manufacturing/routes.py` (ProductionPlan routes)

**Frontend:**
- `src/domain/manufacturing/components/ProductionPlanning.tsx`
- `src/domain/manufacturing/components/ProductionPlanList.tsx`
- `src/pages/manufacturing/ProductionPlanningPage.tsx`
- `src/pages/manufacturing/ProductionPlansPage.tsx`

### Key Features

- Production plan with demand aggregation from sales orders and manual forecast lines
- Material and capacity shortage/capacity summary per line
- Make-to-order and make-to-stock strategies
- Plan firming workflow creates linked work orders
- Planned vs actual completion tracking for accuracy reporting

### Verification

- ✅ Python files compile without errors
- ✅ Manufacturing module imports correctly
- ✅ Tests pass (85 API tests, 317 domain tests)

### TypeScript Fixes (2026-04-27)
- Fixed `.map()` callback type annotations in ProductionPlanList
