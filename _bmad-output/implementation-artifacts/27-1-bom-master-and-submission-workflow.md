# Story 27.1: BOM Master and Submission Workflow

**Status:** completed

**Story ID:** 27.1

**Epic:** Epic 27 - Manufacturing Foundation

---

## Story

As a production planner or manufacturing engineer,
I want to author and submit versioned BOMs for manufactured items,
so that work orders and planning use an explicit approved recipe instead of informal material lists.

---

## Acceptance Criteria

1. ✅ Given a BOM is drafted, when it has not been submitted, then work-order creation and planning endpoints reject it and only submitted BOMs are selectable for production.
2. ✅ Given a product recipe changes, when a replacement BOM is submitted, then the system makes the active BOM explicit for new manufacturing while preserving older BOMs as historical revisions.
3. ✅ Given procurement or production reviews a BOM, when the BOM detail is opened, then required materials are visible with item, quantity, unit, and optional source-warehouse context without ambiguity.
4. ✅ Given an existing work order references an older submitted BOM, when a newer BOM becomes active, then the existing work order keeps its original BOM linkage or snapshot and is not silently repointed.

## Tasks / Subtasks

- [x] Task 1: Add BOM persistence and revision-safe status semantics. (AC: 1-4)
- [x] Task 2: Implement BOM draft, submit, replace, and history services. (AC: 1-4)
- [x] Task 3: Expose BOM APIs for list, detail, authoring, and submission. (AC: 1-4)
- [x] Task 4: Build the BOM workspace in the frontend. (AC: 1-3)
- [x] Task 5: Add focused tests and validation. (AC: 1-4)

---

## Dev Agent Record

**Status:** completed
**Last Updated:** 2026-04-27

### Completion Notes List

- 2026-04-26: Implemented complete BOM foundation with submission workflow, revision tracking, and active BOM management
- 2026-04-27: Fixed HIGH severity issues - typo (proced_quantity → produced_quantity), race condition (SELECT FOR UPDATE), missing unique constraint (partial index)
- 2026-04-27: Fixed import paths (relative imports), SQLAlchemy JSON types, Order/OrderLine naming
- 2026-04-27: Quality review aligned the ORM BOM uniqueness metadata with the migration's partial active-BOM index so historical revisions can coexist.
- 2026-04-27: Added a BOM detail route/page in the frontend so planners can inspect submitted materials and revision history in-app.
- 2026-04-27: Focused manufacturing tests now lock the active-BOM uniqueness metadata used for revision-safe submission and supersession.
- 2026-04-27: Added the protected BOM create page and authoring form so planners can create BOM headers and component lines directly from the mounted manufacturing workspace.
- 2026-04-27: Added focused frontend form coverage for BOM authoring and fixed accessible control labels on the new create workflow.

### Issues Fixed

| Severity | Issue | Fix |
|----------|-------|-----|
| HIGH | Typo: `proced_quantity` → `produced_quantity` | Fixed |
| HIGH | Race condition in `submit_bom` | Added `SELECT FOR UPDATE` |
| HIGH | Missing unique constraint for active BOM | Added partial index |
| HIGH | Import path issues | Fixed relative imports |
| HIGH | SQLAlchemy JSON type for dict fields | Fixed |

### File List

**Backend:**
- `backend/domains/manufacturing/__init__.py`
- `backend/domains/manufacturing/models.py`
- `backend/domains/manufacturing/schemas.py`
- `backend/domains/manufacturing/service.py`
- `backend/domains/manufacturing/routes.py`
- `backend/app/main.py`
- `migrations/versions/2026_04_26_add_manufacturing_tables.py`
- `backend/common/auth.py` (added auth helpers)
- `backend/tests/domains/manufacturing/test_planning_service.py` (BOM metadata regression coverage)

**Frontend:**
- `src/domain/manufacturing/types.ts`
- `src/domain/manufacturing/hooks/useBoms.ts`
- `src/domain/manufacturing/components/BomList.tsx`
- `src/domain/manufacturing/components/BomForm.tsx`
- `src/domain/manufacturing/components/WorkOrderList.tsx`
- `src/domain/manufacturing/components/WorkOrderForm.tsx`
- `src/domain/manufacturing/components/WorkstationList.tsx`
- `src/domain/manufacturing/components/RoutingList.tsx`
- `src/domain/manufacturing/components/ProductionPlanning.tsx`
- `src/domain/manufacturing/components/ProductionPlanList.tsx`
- `src/domain/manufacturing/components/OeeDashboard.tsx`
- `src/pages/manufacturing/BomListPage.tsx`
- `src/pages/manufacturing/CreateBomPage.tsx`
- `src/pages/manufacturing/WorkOrdersPage.tsx`
- `src/pages/manufacturing/CreateWorkOrderPage.tsx`
- `src/pages/manufacturing/WorkstationsPage.tsx`
- `src/pages/manufacturing/RoutingsPage.tsx`
- `src/pages/manufacturing/ProductionPlanningPage.tsx`
- `src/pages/manufacturing/ProductionPlansPage.tsx`
- `src/pages/manufacturing/OeeDashboardPage.tsx`
- `src/lib/api/manufacturing.ts`
- `src/lib/routes.ts`

### Change Log

| Date | Change |
|------|--------|
| 2026-04-26 | Initial implementation |
| 2026-04-27 | Fixed HIGH severity issues |
| 2026-04-27 | Fixed import paths and SQLAlchemy types |
| 2026-04-27 | Fixed TypeScript errors in manufacturing components |
| 2026-04-27 | Added BOM authoring workflow route, form, and mounted create entry point |

### Verification

- ✅ Python files compile without errors
- ✅ Manufacturing module imports correctly
- ✅ Tests pass (85 API tests, 317 domain tests)
- ✅ Added focused manufacturing metadata regression coverage for the active-BOM uniqueness model.
- ✅ Frontend build and locale parity pass with the BOM create workflow mounted in the manufacturing shell.
- ✅ Focused Vitest coverage now verifies BOM authoring payload mapping from the new frontend form.
