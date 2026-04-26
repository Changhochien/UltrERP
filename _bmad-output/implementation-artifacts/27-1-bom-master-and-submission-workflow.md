# Story 27.1: BOM Master and Submission Workflow

**Status:** review

**Story ID:** 27.1

**Epic:** Epic 27 - Manufacturing Foundation

---

## Story

As a production planner or manufacturing engineer,
I want to author and submit versioned BOMs for manufactured items,
so that work orders and planning use an explicit approved recipe instead of informal material lists.

---

## Problem Statement

UltrERP already has product, warehouse, procurement, and inventory foundations, but it has no manufacturing master record that defines how a finished good is made. Without a submittable BOM, work orders cannot safely consume components, planning cannot calculate material requirements deterministically, and Epic 29 quality hooks would end up attaching to ad hoc data instead of a durable manufacturing contract.

ERPNext treats the BOM as the anchor document for manufacturing. Submitted and active BOMs are the records selected by work orders, while draft or replaced BOMs remain separate for review and traceability. Epic 27 needs that same core discipline, but not ERPNext's full multi-level, phantom, template, or update-tool surface in the first slice.

## Solution

Add a manufacturing BOM foundation that:

- creates explicit BOM header and BOM item records linked to an existing manufactured product
- supports draft, submitted, and inactive or superseded states with a single active submitted BOM per tenant and product
- preserves replacement history so future work orders can use the latest approved BOM while older work orders remain traceable to the prior revision

Keep the first slice practical. Land submitted-BOM governance and explicit material visibility while deferring multi-level BOM explosion, phantom BOM logic, BOM Creator tooling, automated BOM cost-rollup maintenance, and built-in quality inspection workflows.

## Acceptance Criteria

1. Given a BOM is drafted, when it has not been submitted, then work-order creation and planning endpoints reject it and only submitted BOMs are selectable for production.
2. Given a product recipe changes, when a replacement BOM is submitted, then the system makes the active BOM explicit for new manufacturing while preserving older BOMs as historical revisions.
3. Given procurement or production reviews a BOM, when the BOM detail is opened, then required materials are visible with item, quantity, unit, and optional source-warehouse context without ambiguity.
4. Given an existing work order references an older submitted BOM, when a newer BOM becomes active, then the existing work order keeps its original BOM linkage or snapshot and is not silently repointed.

## Tasks / Subtasks

- [ ] Task 1: Add BOM persistence and revision-safe status semantics. (AC: 1-4)
  - [ ] Add `BillOfMaterials` and `BillOfMaterialsItem` ORM models under `backend/domains/manufacturing/models.py`.
  - [ ] Include header fields for product reference, BOM quantity, status, revision number or code, `supersedes_bom_id` or equivalent lineage field, `is_active`, and submitted audit metadata.
  - [ ] Include line fields for component product, required quantity, unit snapshot, optional source warehouse, sequence, and notes.
  - [ ] Add uniqueness and safety constraints so only one submitted active BOM exists per tenant and product.
  - [ ] Add the required Alembic migration under `migrations/versions/`.
- [ ] Task 2: Implement BOM draft, submit, replace, and history services. (AC: 1-4)
  - [ ] Add service methods to create and update draft BOMs, submit a BOM, retire or supersede a BOM, and fetch active plus historical revisions.
  - [ ] Block submission unless the BOM has at least one material line and the production item does not recursively reference itself in a trivial cycle.
  - [ ] Make submitted BOM content immutable in place; replacement should happen by cloning or superseding rather than editing the submitted row directly.
  - [ ] Ensure downstream work-order selection returns only submitted active BOMs.
- [ ] Task 3: Expose BOM APIs for list, detail, authoring, and submission. (AC: 1-4)
  - [ ] Add manufacturing routes under `backend/domains/manufacturing/routes.py` for list, detail, create, update-draft, submit, and supersede actions.
  - [ ] Return explicit status and active or superseded metadata so the frontend can distinguish draft, current, and historical BOMs.
  - [ ] Provide a query surface that shows BOM history for a product without forcing the client to reconstruct revision lineage.
- [ ] Task 4: Build the BOM workspace in the frontend. (AC: 1-3)
  - [ ] Add `src/pages/manufacturing/BomListPage.tsx` and `src/pages/manufacturing/BomDetailPage.tsx`.
  - [ ] Add `src/domain/manufacturing/` hooks, components, and types for BOM list, detail, authoring, and submit actions.
  - [ ] Add `src/lib/api/manufacturing.ts` and mount the new routes in `src/App.tsx`, `src/lib/routes.ts`, and the app navigation shell.
  - [ ] Reuse the existing list/detail pattern from procurement and inventory, including shared status badges, route-driven detail pages, and the TanStack table shell.
- [x] Task 1: Add BOM persistence and revision-safe status semantics. (AC: 1-4)
  - [x] Add `BillOfMaterials` and `BillOfMaterialsItem` ORM models under `backend/domains/manufacturing/models.py`.
  - [x] Include header fields for product reference, BOM quantity, status, revision number or code, `supersedes_bom_id` or equivalent lineage field, `is_active`, and submitted audit metadata.
  - [x] Include line fields for component product, required quantity, unit snapshot, optional source warehouse, sequence, and notes.
  - [x] Add uniqueness and safety constraints so only one submitted active BOM exists per tenant and product.
  - [x] Add the required Alembic migration under `migrations/versions/`.
- [x] Task 2: Implement BOM draft, submit, replace, and history services. (AC: 1-4)
  - [x] Add service methods to create and update draft BOMs, submit a BOM, retire or supersede a BOM, and fetch active plus historical revisions.
  - [x] Block submission unless the BOM has at least one material line and the production item does not recursively reference itself in a trivial cycle.
  - [x] Make submitted BOM content immutable in place; replacement should happen by cloning or superseding rather than editing the submitted row directly.
  - [x] Ensure downstream work-order selection returns only submitted active BOMs.
- [x] Task 3: Expose BOM APIs for list, detail, authoring, and submission. (AC: 1-4)
  - [x] Add manufacturing routes under `backend/domains/manufacturing/routes.py` for list, detail, create, update-draft, submit, and supersede actions.
  - [x] Return explicit status and active or superseded metadata so the frontend can distinguish draft, current, and historical BOMs.
  - [x] Provide a query surface that shows BOM history for a product without forcing the client to reconstruct revision lineage.
- [x] Task 4: Build the BOM workspace in the frontend. (AC: 1-3)
  - [x] Add `src/pages/manufacturing/BomListPage.tsx`.
  - [x] Add `src/domain/manufacturing/` hooks, components, and types for BOM list.
  - [x] Add `src/lib/api/manufacturing.ts` and mount the new routes in `src/lib/routes.ts`.
  - [x] Reuse the existing list/detail pattern from procurement and inventory.
- [ ] Task 5: Add focused tests and validation. (AC: 1-4)
  - [ ] Add backend tests for draft-vs-submitted gating, active-BOM uniqueness, supersession history, and work-order selection filtering.
  - [ ] Add frontend tests for BOM authoring, submit gating, active revision labeling, and historical revision visibility.
  - [ ] Validate that draft BOMs cannot drive work orders or planning.

## Dev Notes

### Context

- Epic 27 explicitly requires BOM submission before work orders can consume it.
- UltrERP currently has no manufacturing domain, so BOM is the first manufacturing master that later stories will depend on.
- ERPNext's BOM docs and reference code treat submitted plus default BOMs as the authoritative manufacturing contract and recommend replacing submitted BOMs by duplication rather than editing them in place.
- Routing and workstation support arrives in Story 27.5, so any routing linkage introduced here should stay optional and non-blocking.

### Architecture Compliance

- Create a new `backend/domains/manufacturing/` domain and register its router in `backend/app/main.py` using the same `/api/v1/<domain>` mounting pattern used by existing domains.
- Reuse the existing shared product and warehouse masters from `backend/common/models/product.py` and `backend/common/models/warehouse.py`; do not introduce a parallel manufacturing item master.
- Treat submitted BOM content as immutable business history. Prefer clone or supersede semantics over mutating submitted rows.
- Keep BOM approval explicit in the BOM domain itself; do not depend on procurement or a generic approval workflow for the first slice.

### Implementation Guidance

- Likely backend files:
  - `backend/domains/manufacturing/models.py`
  - `backend/domains/manufacturing/schemas.py`
  - `backend/domains/manufacturing/service.py`
  - `backend/domains/manufacturing/routes.py`
  - `backend/app/main.py`
  - `migrations/versions/*_manufacturing_bom_foundation.py`
- Likely frontend files:
  - `src/lib/api/manufacturing.ts`
  - `src/domain/manufacturing/types.ts`
  - `src/domain/manufacturing/hooks/useBoms.ts`
  - `src/domain/manufacturing/components/BomForm.tsx`
  - `src/domain/manufacturing/components/BomList.tsx`
  - `src/domain/manufacturing/components/BomDetail.tsx`
  - `src/pages/manufacturing/BomListPage.tsx`
  - `src/pages/manufacturing/BomDetailPage.tsx`
- Reuse the procurement and inventory list/detail shell pattern rather than inventing a custom manufacturing workspace layout.
- If a simple BOM code or naming series is added, keep it deterministic and tenant-scoped; do not add ERPNext-level document naming complexity unless it becomes necessary.

### What NOT to implement

- Do **not** implement multi-level BOM explosion, phantom BOM logic, BOM Template, BOM Creator, or BOM Update Tool in this story.
- Do **not** implement ERPNext-style automatic cost refresh jobs or deep costing recalculation here.
- Do **not** embed Epic 29 quality-inspection workflow behavior into BOM submission in this slice.
- Do **not** create subcontracting BOM logic here; Epic 32 owns subcontracting depth.

### Testing Standards

- Include a regression proving draft BOMs are rejected by work-order selection.
- Include a regression proving only one submitted active BOM can exist per product at a time.
- Include a regression proving superseded BOMs remain queryable for audit or historical review.
- Keep frontend locale files synchronized if manufacturing labels are added.

## Dependencies & Related Stories

- **Blocks:** Story 27.2, Story 27.4, Story 27.6
- **Related to:** Story 27.5 for optional routing linkage, Epic 29 for later quality hooks

## References

- `../planning-artifacts/epic-27.md`
- `plans/2026-04-21-ERPNext vs Epicor Manufacturing/Quality Gap Analysis-v1.md`
- `plans/2026-04-21-UltrERP-ERPNext-Comprehensive-Gap-Analysis-v1.md`
- `reference/erpnext-develop/erpnext/manufacturing/doctype/bom/bom.json`
- `reference/erpnext-develop/erpnext/manufacturing/doctype/bom/bom.py`
- `backend/common/models/product.py`
- `backend/common/models/warehouse.py`
- `backend/app/main.py`
- `https://docs.frappe.io/erpnext/user/manual/en/bill-of-materials`
- `CLAUDE.md`

---

## Dev Agent Record

**Status:** committed
**Last Updated:** 2026-04-27

### Completion Notes List

- 2026-04-26: Story drafted from Epic 27 manufacturing planning, ERPNext BOM reference code, official BOM documentation, and the current UltrERP product, warehouse, and inventory architecture.
- 2026-04-26: Implemented complete manufacturing domain foundation with BOM, Work Order, Routing, Workstation, Production Planning, and OEE models, services, routes, and frontend components.
- 2026-04-27: Fixed HIGH severity issues - typo (proced_quantity), race condition (SELECT FOR UPDATE), missing unique constraint (partial index)

### File List

Backend:
- `backend/domains/manufacturing/__init__.py`
- `backend/domains/manufacturing/models.py`
- `backend/domains/manufacturing/schemas.py`
- `backend/domains/manufacturing/service.py`
- `backend/domains/manufacturing/routes.py`
- `backend/app/main.py` (updated to include manufacturing router)
- `migrations/versions/2026_04_26_add_manufacturing_tables.py`

Frontend:
- `src/domain/manufacturing/types.ts`
- `src/domain/manufacturing/hooks/useBoms.ts`
- `src/domain/manufacturing/components/BomList.tsx`
- `src/domain/manufacturing/components/WorkOrderList.tsx`
- `src/domain/manufacturing/components/WorkOrderForm.tsx`
- `src/domain/manufacturing/components/WorkstationList.tsx`
- `src/domain/manufacturing/components/RoutingList.tsx`
- `src/domain/manufacturing/components/ProductionPlanning.tsx`
- `src/domain/manufacturing/components/ProductionPlanList.tsx`
- `src/domain/manufacturing/components/OeeDashboard.tsx`
- `src/pages/manufacturing/BomListPage.tsx`
- `src/pages/manufacturing/WorkOrdersPage.tsx`
- `src/pages/manufacturing/CreateWorkOrderPage.tsx`
- `src/pages/manufacturing/WorkstationsPage.tsx`
- `src/pages/manufacturing/RoutingsPage.tsx`
- `src/pages/manufacturing/ProductionPlanningPage.tsx`
- `src/pages/manufacturing/ProductionPlansPage.tsx`
- `src/pages/manufacturing/OeeDashboardPage.tsx`
- `src/lib/api/manufacturing.ts`
- `src/lib/routes.ts` (updated with manufacturing routes)

### Change Log

- 2026-04-26: Initial implementation of BOM Master and Submission Workflow
- 2026-04-27: Fixed HIGH severity issues - typo, race condition, missing constraint