# Story 4.5: Track Supplier Orders and Auto-Update Stock

**Status:** done

**Story ID:** 4.5

---

## Story

As a system,
I want to track supplier orders and auto-update stock when goods arrive,
So that inventory stays accurate without manual intervention.

---

## Acceptance Criteria

**✓ AC1:** Supplier order creation
**Given** I need to reorder products
**When** I create a supplier order with products, receiving warehouses, and quantities
**Then** the order is saved with status "pending" and assigned an order number

**✓ AC2:** Order status tracking
**Given** a supplier order exists
**When** I view the order
**Then** I see status: pending, confirmed, shipped, partially_received, received, cancelled

**✓ AC3:** Auto-update stock on receipt
**Given** a supplier order is marked as "received"
**When** I confirm receipt
**Then** stock levels automatically increase by the newly received quantity per product
**And** adjustment reason is recorded as "supplier_delivery"

**✓ AC4:** Reorder alert clearing
**Given** a product had a reorder alert
**When** supplier order for that product is received and stock restored
**Then** the reorder alert is automatically resolved

**✓ AC5:** Supplier order history
**Given** supplier orders exist
**When** I view product details
**Then** I see recent supplier orders linked to this product

**✓ AC6:** Bulk order creation from alerts
**Given** multiple products have reorder alerts
**When** I select products from the alert list and create supplier order
**Then** a supplier order is created with all selected products pre-populated

**✓ AC7:** Partial receipts are supported
**Given** a supplier ships only part of an order
**When** I record the receipt
**Then** each order line stores `quantity_received`
**And** the order remains `partially_received` until all lines are fully received or cancelled

**✓ AC8:** Receiving is idempotent
**Given** an order line has already been fully received
**When** I try to receive it again
**Then** stock is not incremented a second time
**And** the API returns the existing order state without duplicating adjustments

---

## Tasks / Subtasks

- [ ] **Task 1: Supplier Order Data Model** (AC1-AC3, AC7, AC8)
  - [ ] Create Alembic migration for `supplier_order` table: (id, tenant_id, supplier_id, order_number, status, order_date, expected_arrival_date, received_date, created_by, created_at)
  - [ ] Create Alembic migration for `supplier_order_line` table: (id, order_id, product_id, warehouse_id, quantity_ordered, quantity_received, notes)
  - [ ] Default status: "pending"

- [ ] **Task 2: Supplier Master Data** (AC1)
  - [ ] Create Alembic migration for `supplier` table: (id, tenant_id, name, contact_email, phone, address, default_lead_time_days, is_active)
  - [ ] Create GET `/api/v1/suppliers` endpoint to list suppliers
  - [ ] Treat supplier create/update flows as migration/admin scope for now; this story only needs list/select behavior

- [ ] **Task 3: Supplier Order API** (AC1-AC5)
  - [ ] POST `/api/v1/inventory/supplier-orders` — create order
  - [ ] GET `/api/v1/inventory/supplier-orders` — list orders with filtering
  - [ ] GET `/api/v1/inventory/supplier-orders/{order_id}` — order details
  - [ ] PUT `/api/v1/inventory/supplier-orders/{order_id}/status` — update status
  - [ ] PUT `/api/v1/inventory/supplier-orders/{order_id}/receive` — mark as received
  - [ ] Define request/response schemas for status and receive actions, including per-line received quantities and an optional idempotency key

- [ ] **Task 4: Auto-Update Stock on Receipt** (AC3-AC4, AC7, AC8)
  - [ ] When a receipt is posted for a supplier order, atomically:
    - [ ] Lock the supplier order row and affected `inventory_stock` rows inside `async with session.begin():` before checking remaining quantity
    - [ ] Update inventory_stock by the newly received quantity for each line item
    - [ ] Create stock_adjustment records with system reason `supplier_delivery`
    - [ ] Create audit_log entries
    - [ ] Resolve reorder_alert if stock now above the warehouse-specific reorder point
    - [ ] Prevent double-receipt by checking order status and remaining quantity before any stock mutation
    - [ ] Use `AsyncSession` from `common.database.get_db` so the shared engine settings, including `statement_cache_size=0`, are inherited automatically

- [ ] **Task 5: Bulk Creation from Alerts** (AC6)
  - [ ] Extend StockAdjustment/ReorderAlerts component with bulk select
  - [ ] Add "Create Supplier Order" button (creates pre-populated Supplier Order form)
  - [ ] Supplier Order form: supplier selector, products pre-filled from alerts
  - [ ] Carry source reorder_alert IDs through the draft order so alerts remain pending until receipt restores stock

- [ ] **Task 6: Frontend Supplier Order UI** (AC1-AC6)
  - [ ] Create SupplierOrderForm component (create new order)
  - [ ] Create SupplierOrderList component (list, filter by status)
  - [ ] Create SupplierOrderDetail component (view, update status, mark received)
  - [ ] Link from product detail to recent supplier orders

- [ ] **Task 7: Testing** (AC1-AC8)
  - [ ] Unit tests: stock auto-update logic on receipt status
  - [ ] Integration tests: atomic transaction (inventory + adjustment + alert clearing)
  - [ ] Integration tests: partial receipt updates quantities without closing the order prematurely
  - [ ] Integration tests: receiving the same order twice is idempotent
  - [ ] E2E tests: create supplier order → receive → verify stock update + alert cleared

---

## Dev Notes

### Architecture Compliance

- **Transaction Pattern:** Stock update, adjustment record, audit log, alert clearing all in single atomic transaction [Source: arch#4.3]
- **Idempotency:** Receiving an order twice should not double-update stock (use status check)
- **Warehouse Routing:** Stock updates to correct warehouse_id from order line items

### Supplier Scope

- Supplier master records are assumed to come from migration/admin configuration in MVP.
- Story 4.5 covers list/select, ordering, receiving, and history, not full supplier CRUD.

### Project Structure

**Backend:**
- Model: `backend/common/models/supplier_order.py`, `backend/common/models/supplier.py`
- Route: `backend/domains/inventory/routes.py` — /supplier-orders endpoints
- Service: `backend/domains/inventory/services.py` — create_supplier_order(), receive_supplier_order()
- Schema: `backend/domains/inventory/schemas.py` — SupplierOrderRequest, SupplierOrderResponse

**Frontend:**
- Component: `src/domain/inventory/components/SupplierOrderForm.tsx`
- Component: `src/domain/inventory/components/SupplierOrderList.tsx`
- Component: `src/domain/inventory/components/SupplierOrderDetail.tsx`
- Hook: `src/domain/inventory/hooks/useSupplierOrders.ts`

**Database:**
- `supplier` table: (id, tenant_id, name, contact_email, phone, address, created_at)
- `supplier_order` table: (id, tenant_id, supplier_id, order_number, status, expected_arrival_date, received_date, created_by, created_at, updated_at)
- `supplier_order_line` table: (id, order_id, product_id, warehouse_id, quantity_ordered, quantity_received, notes)
- Index: `supplier_order_idx_status_date` on (status, created_at DESC)

### Supplier Order Status Flow

```
pending → confirmed → shipped → partially_received → received → [end]
       ↓
     cancelled
```

### Receiving Logic

When status changes to "received":

```python
async def receive_supplier_order(
  session: AsyncSession,
  tenant_id: str,
  order_id: str,
  received_date: date,
  received_quantities: dict[str, int],
):
  async with session.begin():
    order = await get_supplier_order_for_update(session, tenant_id, order_id)
    if order.status == "received":
      return order

        for line in order.lines:
      remaining_qty = line.quantity_ordered - line.quantity_received
      receive_qty = received_quantities.get(str(line.id), remaining_qty)
      if receive_qty <= 0:
        continue
      if receive_qty > remaining_qty:
        raise ValueError("Cannot receive more than remaining quantity")

            # 1. Update inventory
      inventory = await get_inventory_stock_for_update(
        session, tenant_id, line.product_id, line.warehouse_id
      )
      new_stock = await update_inventory_stock(
        session,
        tenant_id,
                line.product_id,
                line.warehouse_id,
        receive_qty
            )

            # 2. Log adjustment
            await create_stock_adjustment({
              "tenant_id": tenant_id,
        "product_id": line.product_id,
        "warehouse_id": line.warehouse_id,
        "quantity_change": receive_qty,
        "reason_code": ReasonCode.SUPPLIER_DELIVERY,
        "notes": f"From supplier order {order.order_number}",
            })

      line.quantity_received += receive_qty
            await save(session, line)

            # 3. Check and clear alerts
      reorder_point = await get_reorder_point(
        session, tenant_id, line.product_id, line.warehouse_id
      )
      if new_stock >= reorder_point:
        await resolve_reorder_alert(
          session, tenant_id, line.product_id, line.warehouse_id
        )

        # 4. Update order status
    if all(line.quantity_received >= line.quantity_ordered for line in order.lines):
      order.status = "received"
      order.received_date = received_date
    else:
      order.status = "partially_received"
            await save(session, order)
```

---

## Dependencies & Related Stories

- **Depends on:** Story 4.4 (Stock Adjustment) — stock update uses same logic
- **Depends on:** Story 4.3 (Reorder Alerts) — alerts resolved on receipt
- **Related to:** Story 4.6 (Warehouses) — stock updates to specific warehouse

---

## Technology Stack

| Tech | Version | Purpose |
|------|---------|---------|
| PostgreSQL | 18+ | Transactional order management |
| SQLAlchemy | 2.0+ | ORM models for orders |
| FastAPI | 0.135+ | Order API endpoints |
| React | 19 | Order management UI |

---

## References

- [Story 4.3: Reorder Alerts](4-3-reorder-alerts.md)
- [Story 4.4: Stock Adjustment](4-4-record-stock-adjustment.md)
- [Story 4.6: Multiple Warehouses](4-6-multiple-warehouse-support.md)

---

## Dev Agent Record

**Status:** ready-for-dev
**Last Updated:** 2026-04-01

### File List

- `backend/common/models/supplier_order.py`
- `backend/common/models/supplier.py`
- `backend/domains/inventory/routes.py`
- `src/domain/inventory/components/SupplierOrderForm.tsx`
- `src/domain/inventory/components/SupplierOrderList.tsx`
- `src/domain/inventory/components/SupplierOrderDetail.tsx`
