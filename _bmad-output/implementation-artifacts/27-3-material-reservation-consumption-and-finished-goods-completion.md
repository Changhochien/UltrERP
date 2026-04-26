# Story 27.3: Material Reservation, Consumption, and Finished Goods Completion

**Status:** review

**Story ID:** 27.3

**Epic:** Epic 27 - Manufacturing Foundation

---

## Story

As a production or warehouse operator,
I want to reserve materials, issue them to a work order, and complete finished goods,
so that manufacturing updates stock deterministically and exposes shortages before execution fails.

---

## Problem Statement

Stories 27.1 and 27.2 provide the approved recipe and the work-order document, but they do not yet move inventory. UltrERP's existing inventory domain supports stock visibility, transfers, and adjustments, yet it has no manufacturing-specific contract for soft reservations, work-order material issue, or finished-goods receipt lineage. Without that layer, factory execution would either mutate inventory through ad hoc adjustments or fail to surface shortages until operators are already blocked.

ERPNext's direct-transfer manufacturing flow reserves stock, transfers materials against the work order, and then completes finished goods. Epic 27 needs that same explicit material execution path, but it should stay bounded to work-order-level transfers and finished-goods completion instead of full job-card issue points, scrap complexity, or advanced backflush automation.

## Solution

Add manufacturing inventory execution that:

- reserves required raw materials against the work order from source warehouses
- records direct material transfer for manufacture against the work order into the WIP or production context
- consumes transferred materials and receipts finished goods into the selected finished-goods warehouse with explicit work-order lineage

Keep the first slice deterministic and auditable. Land explicit reservations, shortages, transfers, and completion while deferring scrap, extra-material transfers, returns-to-store flows, and operation-level job-card consumption.

## Acceptance Criteria

1. Given enough raw materials exist, when a planner or operator reserves them for a work order, then the reservation is deterministic by item and warehouse and the work order shows reserved quantities explicitly.
2. Given shortages exist, when the system evaluates a work order for reservation or transfer, then the blocking components are returned explicitly instead of failing silently.
3. Given materials are issued for manufacture, when the transfer is posted against the work order, then transferred quantities are traceable and the corresponding inventory levels are updated through the existing stock-mutation path.
4. Given completion occurs, when finished goods are posted, then consumed raw materials and produced finished goods update stock with clear lineage to the work order and support partial completion if only part of the quantity is finished.

## Tasks / Subtasks

- [ ] Task 1: Extend work-order material execution data and reservation state. (AC: 1-4)
  - [ ] Add reservation and execution fields to `WorkOrderMaterialLine` or add dedicated manufacturing execution tables such as `WorkOrderReservation` and `ManufacturingStockTransaction`.
  - [ ] Track required, reserved, transferred, consumed, short, and returned quantities at the material-line level.
  - [ ] Add transaction fields for work-order linkage, movement type, source warehouse, target warehouse, quantity, and timestamps.
- [ ] Task 2: Implement reservation, release, and shortage services. (AC: 1-2)
  - [ ] Reuse `backend/common/models/inventory_stock.py` as the source of on-hand stock.
  - [ ] Add deterministic reservation logic that allocates by warehouse and item without hiding shortages.
  - [ ] Add release logic for stopped or cancelled work orders so reservations do not linger.
  - [ ] Return explicit shortage payloads with item and warehouse context.
- [ ] Task 3: Implement work-order material issue and finished-goods completion. (AC: 1-4)
  - [ ] Support one direct-transfer manufacturing path: reserve materials in source warehouses, transfer them against the work order into the WIP or production warehouse, and complete finished goods from that work-order context.
  - [ ] Use the existing inventory mutation path and event hooks so stock-change side effects remain consistent with Epic 4 behaviors.
  - [ ] Allow partial completion and update produced quantities incrementally.
  - [ ] Persist finished-goods completion lineage back to the work order for auditability and planning.
- [ ] Task 4: Expose APIs and frontend execution surfaces. (AC: 1-4)
  - [ ] Add reserve, release, transfer, complete, and shortage endpoints under the manufacturing API.
  - [ ] Add work-order detail UI for material reservation state, blocking shortages, transfer history, and completion actions.
  - [ ] Reuse shared confirmation, status, and error-display patterns from inventory and procurement workflows.
- [ ] Task 5: Add focused tests and validation. (AC: 1-4)
  - [ ] Add backend tests for successful reservation, shortage detection, idempotent release or transfer rules, stock mutation lineage, and partial completion.
  - [ ] Add frontend tests for shortage display, reservation actions, transfer visibility, and finished-goods completion UX.
  - [ ] Validate that reorder alerts or other stock-change consumers still react through the existing event path after manufacturing stock mutations.

## Dev Notes

### Context

- Story 27.2 establishes the work-order document and warehouse fields this story executes against.
- UltrERP already has inventory stock, stock transfer history, stock adjustment history, and stock-change event handling in the inventory domain.
- ERPNext's work-order flow transfers materials for manufacture and then updates finished goods; Epic 27 adopts that work-order-level transfer path without job-card issue depth.

### Architecture Compliance

- Reuse existing shared inventory primitives where possible instead of creating a parallel stock ledger for manufacturing.
- Make manufacturing-specific reservation or execution records additive to the existing inventory domain, not a replacement for it.
- Route all stock mutations through auditable service logic so inventory events and downstream reports remain coherent.
- Keep shortage results explicit and synchronous; do not hide availability decisions behind background jobs.

### Implementation Guidance

- Likely backend files:
  - `backend/domains/manufacturing/models.py`
  - `backend/domains/manufacturing/service.py`
  - `backend/domains/manufacturing/routes.py`
  - `backend/domains/manufacturing/schemas.py`
  - `backend/domains/inventory/handlers.py`
  - `backend/common/models/inventory_stock.py`
  - `backend/common/models/stock_transfer.py`
  - `backend/common/models/stock_adjustment.py`
  - `migrations/versions/*_manufacturing_execution.py`
- Likely frontend files:
  - `src/lib/api/manufacturing.ts`
  - `src/domain/manufacturing/hooks/useWorkOrderExecution.ts`
  - `src/domain/manufacturing/components/WorkOrderMaterialsPanel.tsx`
  - `src/domain/manufacturing/components/WorkOrderCompletionPanel.tsx`
  - `src/pages/manufacturing/WorkOrderDetailPage.tsx`
- If a manufacturing-specific movement record is introduced, keep it linked to the existing stock-transfer or stock-adjustment history rather than creating disconnected warehouse mutations.

### What NOT to implement

- Do **not** implement scrap warehouses, by-products, or secondary-item handling in this story.
- Do **not** implement return-components flows, extra-material transfers, or reverse-manufacture support here.
- Do **not** implement job-card-level material issue or routing-driven operation consumption.
- Do **not** silently consume materials on work-order creation; reservation and issue must remain explicit operator actions.

### Testing Standards

- Include a regression proving shortages are returned explicitly with blocking items.
- Include a regression proving reservations release cleanly when a work order is cancelled or stopped.
- Include a regression proving finished-goods completion updates stock and work-order produced quantity together.
- Include a regression proving manufacturing stock updates still trigger existing inventory side effects that rely on stock-change events.

## Dependencies & Related Stories

- **Depends on:** Story 27.2
- **Related to:** Story 27.1 for BOM material lines, Story 27.7 for later OEE and good-vs-total output metrics
- **Cross-epic:** Reuses Epic 4 stock and warehouse foundations rather than inventing a second inventory system.

## References

- `../planning-artifacts/epic-27.md`
- `plans/2026-04-21-ERPNext vs Epicor Manufacturing/Quality Gap Analysis-v1.md`
- `reference/erpnext-develop/erpnext/manufacturing/doctype/work_order/work_order.json`
- `backend/common/models/inventory_stock.py`
- `backend/common/models/stock_transfer.py`
- `backend/common/models/stock_adjustment.py`
- `backend/domains/inventory/routes.py`
- `backend/domains/inventory/handlers.py`
- `https://docs.frappe.io/erpnext/user/manual/en/work-order`
- `CLAUDE.md`

---

## Dev Agent Record

**Status:** ready-for-dev
**Last Updated:** 2026-04-26

### Completion Notes List

- 2026-04-26: Story drafted from Epic 27, ERPNext work-order execution references, and the current UltrERP inventory stock and stock-mutation architecture.

### File List

- `_bmad-output/implementation-artifacts/27-3-material-reservation-consumption-and-finished-goods-completion.md`

**Implementation Notes:**
- Work order material execution services implemented (reserve, release, transfer)
- Shortage detection returns explicit blocking components
- Material lines track reserved, transferred, and consumed quantities
- Completed work orders update produced_quantity field
- Integration with existing inventory stock model for availability checks