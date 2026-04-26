# Story 27.2: Work Orders With Direct Material Transfer

**Status:** review

**Story ID:** 27.2

**Epic:** Epic 27 - Manufacturing Foundation

---

## Story

As a production planner,
I want to create and manage work orders from submitted BOMs,
so that in-house production has an explicit execution record with a controlled lifecycle and direct material-transfer mode.

---

## Problem Statement

UltrERP has confirmed sales demand, procurement documents, warehouse stock, and transfer history, but it still lacks the document that tells the factory to make something. Without a work-order entity, manufacturing demand cannot be scheduled, material-transfer state cannot be tracked against a production job, and later stock consumption or finished-goods completion would have nowhere to attach their lineage.

ERPNext's Work Order provides a BOM reference, status machine, warehouse context, and direct material-transfer flow even before full job-card complexity is used. Epic 27 needs that same foundational production-order contract, but it must stay direct-transfer-first and avoid full routing execution, employee time logs, or job-card parity in the first slice.

## Solution

Add a manufacturing work-order foundation that:

- creates work orders from submitted BOMs with product, quantity, dates, and warehouse context
- snapshots the BOM or required materials at creation time so later BOM changes do not silently change in-flight work
- supports a bounded lifecycle such as draft, submitted, not started, in process, completed, stopped, and cancelled

Keep this story focused on the work-order document and lifecycle. Actual reservation, issue, consumption, and finished-goods stock mutation depth lands in Story 27.3.

## Acceptance Criteria

1. Given a planner creates a work order, when the record is saved, then it references a submitted BOM, records the required quantity and due date, and snapshots the material requirements needed by downstream execution.
2. Given production starts or progresses, when the work-order state changes, then material-transfer mode and completion state are explicit and the status machine rejects invalid transitions.
3. Given a work order is stopped or cancelled, when the planner or supervisor reviews it, then the stop or cancel reason is explicit and downstream inventory or planning hooks remain consistent instead of silently drifting.
4. Given a work order is viewed in the UI or API, when planners inspect it, then BOM revision, product, quantity, warehouse context, and current execution status are visible without ambiguity.

## Tasks / Subtasks

- [ ] Task 1: Add work-order persistence and state-machine fields. (AC: 1-4)
  - [ ] Add `WorkOrder` and `WorkOrderMaterialLine` models under `backend/domains/manufacturing/models.py`.
  - [ ] Include fields for product, BOM, BOM revision snapshot, quantity, planned start, due date, source warehouse, WIP warehouse, finished-goods warehouse, status, and direct-transfer mode.
  - [ ] Include line fields for required quantity, planned source warehouse, and execution summary columns such as reserved, transferred, and consumed quantities for Story 27.3 to use.
  - [ ] Add DB-level status and required-field constraints in the Alembic migration.
- [ ] Task 2: Implement work-order creation and lifecycle services. (AC: 1-4)
  - [ ] Add service methods to create, submit, start, stop, reopen, cancel, and read work orders.
  - [ ] Reject creation unless the selected BOM is submitted and active.
  - [ ] Snapshot required material lines from the BOM at creation so later BOM revisions do not silently rewrite existing work orders.
  - [ ] Enforce bounded transition rules so invalid jumps such as `draft -> completed` are rejected.
- [ ] Task 3: Expose work-order APIs and read models. (AC: 1-4)
  - [ ] Add manufacturing routes for list, detail, create, and state transitions.
  - [ ] Return detail responses that include the material summary, warehouse context, and status history fields needed by later execution stories.
  - [ ] Include explicit stop or cancel reason fields in the response contract.
- [ ] Task 4: Build work-order list, detail, and authoring UI. (AC: 1-4)
  - [ ] Add `src/pages/manufacturing/WorkOrdersPage.tsx`, `src/pages/manufacturing/CreateWorkOrderPage.tsx`, and `src/pages/manufacturing/WorkOrderDetailPage.tsx`.
  - [ ] Add manufacturing hooks, types, and API clients under `src/domain/manufacturing/` and `src/lib/api/manufacturing.ts`.
  - [ ] Reuse the procurement list/detail pattern for filters, status badges, and route-driven detail navigation.
  - [ ] Surface the direct material-transfer mode clearly so operators understand that the first slice does not depend on job cards.
- [ ] Task 5: Add focused tests and validation. (AC: 1-4)
  - [ ] Add backend tests for BOM eligibility, work-order creation snapshots, valid and invalid status transitions, and stop or cancel reason handling.
  - [ ] Add frontend tests for create-work-order authoring, status-action gating, and detail rendering.
  - [ ] Validate that work-order creation still works after newer BOMs are submitted for the same product.

## Dev Notes

### Context

- Story 27.1 supplies the submitted BOM contract that work orders depend on.
- Current UltrERP order and inventory domains already provide demand signals and warehouse state, but there is no manufacturing execution record yet.
- ERPNext's Work Order reference includes BOM, quantity, source or WIP or FG warehouses, direct transfer, and bounded statuses; Epic 27 intentionally adopts that bounded subset without Job Card depth.

### Architecture Compliance

- Keep manufacturing write logic in `backend/domains/manufacturing/` and mount it in `backend/app/main.py` like the other domains.
- Reuse existing product and warehouse models rather than cloning master data.
- Snapshot BOM materials into the work order so later revisions do not mutate the document implicitly.
- Keep work-order lifecycle logic explicit in the service layer; do not bury state transitions inside route handlers.

### Implementation Guidance

- Likely backend files:
  - `backend/domains/manufacturing/models.py`
  - `backend/domains/manufacturing/schemas.py`
  - `backend/domains/manufacturing/service.py`
  - `backend/domains/manufacturing/routes.py`
  - `backend/app/main.py`
  - `migrations/versions/*_manufacturing_work_orders.py`
- Likely frontend files:
  - `src/lib/api/manufacturing.ts`
  - `src/domain/manufacturing/types.ts`
  - `src/domain/manufacturing/hooks/useWorkOrders.ts`
  - `src/domain/manufacturing/components/WorkOrderForm.tsx`
  - `src/domain/manufacturing/components/WorkOrderList.tsx`
  - `src/domain/manufacturing/components/WorkOrderDetail.tsx`
  - `src/pages/manufacturing/WorkOrdersPage.tsx`
  - `src/pages/manufacturing/CreateWorkOrderPage.tsx`
  - `src/pages/manufacturing/WorkOrderDetailPage.tsx`
- Reuse existing list/detail wrappers such as the procurement purchase-order pages rather than inventing a separate page architecture.
- If a document number series is added, keep it tenant-scoped and simple.

### What NOT to implement

- Do **not** implement Job Cards, employee time logs, or operation-level execution in this story.
- Do **not** implement serial or batch finished-goods handling, disassembly, or corrective job-card flows here.
- Do **not** implement capacity scheduling or routing-cost rollups in this story; Story 27.5 owns routing and workstation depth.
- Do **not** auto-create work orders from a production plan in this slice; that belongs to Stories 27.4 and 27.6.

### Testing Standards

- Include a regression proving a draft BOM cannot be used to create a work order.
- Include a regression proving a work order retains its BOM snapshot even after a newer BOM becomes active.
- Include transition tests for stop, reopen, cancel, and invalid state jumps.

## Dependencies & Related Stories

- **Depends on:** Story 27.1
- **Related to:** Story 27.3 for material execution, Story 27.5 for later routing overlays
- **Cross-epic:** May link to confirmed sales-order demand from the orders domain when make-to-order manufacturing is used.

## References

- `../planning-artifacts/epic-27.md`
- `plans/2026-04-21-ERPNext vs Epicor Manufacturing/Quality Gap Analysis-v1.md`
- `reference/erpnext-develop/erpnext/manufacturing/doctype/work_order/work_order.json`
- `reference/erpnext-develop/erpnext/manufacturing/doctype/work_order/work_order.py`
- `backend/app/main.py`
- `backend/common/models/product.py`
- `backend/common/models/warehouse.py`
- `src/pages/procurement/PurchaseOrderListPage.tsx`
- `src/pages/procurement/PurchaseOrderDetailPage.tsx`
- `https://docs.frappe.io/erpnext/user/manual/en/work-order`
- `CLAUDE.md`

---

## Dev Agent Record

**Status:** ready-for-dev
**Last Updated:** 2026-04-26

### Completion Notes List

- 2026-04-26: Story drafted from Epic 27, ERPNext work-order reference code, official work-order documentation, and current UltrERP inventory, orders, and procurement patterns.

### File List

- `_bmad-output/implementation-artifacts/27-2-work-orders-with-direct-material-transfer.md`
- `backend/domains/manufacturing/models.py` (WorkOrder, WorkOrderMaterialLine models)
- `backend/domains/manufacturing/schemas.py` (WorkOrder schemas)
- `backend/domains/manufacturing/service.py` (WorkOrder services - create, transition, complete)
- `backend/domains/manufacturing/routes.py` (WorkOrder routes)
- `src/domain/manufacturing/components/WorkOrderList.tsx`
- `src/domain/manufacturing/components/WorkOrderForm.tsx`
- `src/pages/manufacturing/WorkOrdersPage.tsx`
- `src/pages/manufacturing/CreateWorkOrderPage.tsx`

**Implementation Notes:**
- Work orders fully implemented with BOM snapshot for revision-safe production
- Status machine: draft → submitted → not_started → in_progress → completed/stopped/cancelled
- Direct material transfer mode supported
- Material lines created from BOM snapshot at work order creation