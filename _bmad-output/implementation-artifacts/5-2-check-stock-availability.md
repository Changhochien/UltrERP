# Story 5.2: Check Stock Availability for Order

**Status:** ready-for-dev

**Story ID:** 5.2

---

## Story

As a system,
I want to check and display stock availability for all order line items,
So that sales reps know what's in stock before confirming orders.

---

## Acceptance Criteria

**AC1:** Real-time stock display
**Given** I'm creating an order with line items
**When** I add a product to the order
**Then** the system displays available stock for that product across all warehouses (or the selected warehouse)

**AC2:** Insufficient stock warning
**Given** a product has less stock than the requested quantity
**When** I view the line item
**Then** it shows "Insufficient stock: {available} units available"

**AC3:** Backorder allowance
**Given** stock is insufficient for a line item
**When** I create the order anyway
**Then** the order is created successfully with a backorder_note on the affected line(s)
**And** the available_stock_snapshot captures stock level at order time

**AC4:** Stock check endpoint
**Given** I need to check stock for a product
**When** I call the stock availability API
**Then** it returns available quantity per warehouse for the given product

**AC5:** Stock snapshot on order line
**Given** I create an order with line items
**When** the order is saved
**Then** each line stores `available_stock_snapshot` (total across warehouses at creation time)
**And** if quantity exceeds available, `backorder_note` is populated automatically

---

## Tasks / Subtasks

- [ ] **Task 1: Stock Check API Endpoint** (AC1, AC4)
  - [ ] Add `GET /api/v1/orders/check-stock?product_id={id}` to orders routes
  - [ ] Service function `check_stock_availability(session, tenant_id, product_id)` that queries `inventory_stock` table
  - [ ] Returns: `{ product_id, warehouses: [{ warehouse_id, warehouse_name, available: int }], total_available: int }`
  - [ ] Reuse existing `InventoryStock` and `Warehouse` models from `common.models`

- [ ] **Task 2: Integrate Stock Check into Order Creation** (AC3, AC5)
  - [ ] In `create_order()` service (from Story 5.1), after validating line items:
    - [ ] For each line item, query total available stock across all warehouses
    - [ ] Set `available_stock_snapshot` on each OrderLine
    - [ ] If `quantity > total_available`, set `backorder_note = f"Backorder: {quantity - total_available} units"`
  - [ ] Stock check is READ-ONLY — do NOT reduce or reserve inventory

- [ ] **Task 3: Frontend — Stock Availability Display** (AC1, AC2)
  - [ ] In OrderForm.tsx (from Story 5.1), when a product is selected for a line item:
    - [ ] Call `checkStock(productId)` API
    - [ ] Display available quantity next to the line item
    - [ ] If quantity entered > available, show warning badge: "Insufficient stock: {available} units available"
    - [ ] Use debounced fetch (same pattern as `useProductSearch` in inventory)
  - [ ] Create `src/domain/orders/hooks/useStockCheck.ts` hook

- [ ] **Task 4: Backend Tests** (AC1-AC5)
  - [ ] `backend/tests/test_order_stock_check.py`:
    - [ ] Test stock check endpoint returns correct totals per warehouse
    - [ ] Test stock check for product with no inventory returns 0
    - [ ] Test order creation populates available_stock_snapshot
    - [ ] Test order creation with insufficient stock sets backorder_note
    - [ ] Test order creation with sufficient stock leaves backorder_note null

- [ ] **Task 5: Frontend Tests** (AC1, AC2)
  - [ ] In `src/domain/orders/__tests__/OrderForm.test.tsx`:
    - [ ] Test stock availability display when product selected
    - [ ] Test insufficient stock warning message

---

## Dev Notes

### Architecture Compliance

- **Read-Only Stock Check:** Orders do NOT reserve or reduce inventory. Stock check is purely informational [Source: arch design — "Stock Independence"]
- **No Inventory Mutation:** This story must NOT modify inventory_stock, stock_adjustment, or any inventory tables
- **Existing Models:** Reuse `InventoryStock` and `Warehouse` models from `backend/common/models/` — do NOT create new models

### Implementation Details

- **Stock Query Pattern:** Use the same query pattern as `get_product_detail()` in `domains/inventory/services.py` which already fetches `InventoryStock` per warehouse
- **No Warehouse Selection on Orders (MVP):** Stock check returns totals across ALL warehouses. Future enhancement could add warehouse-scoped orders
- **Snapshot Purpose:** `available_stock_snapshot` is a point-in-time record for reconciliation — it does not affect any business logic

### Dependencies

- **Depends on Story 5.1:** Order model with `available_stock_snapshot` and `backorder_note` fields on OrderLine must exist
- **Reuses from Epic 4:** InventoryStock, Warehouse, Product models already exist in `backend/common/models/`

### Key Conventions

- Tab indentation, `from __future__ import annotations`
- FakeAsyncSession test pattern
- HTTPException for errors (inventory pattern)
- Debounced hooks pattern: see `src/domain/inventory/hooks/useProductSearch.ts`

### Project Structure Notes

**Backend (new files):**
- `backend/tests/test_order_stock_check.py`

**Backend (modified files from 5.1):**
- `backend/domains/orders/services.py` — add `check_stock_availability()`
- `backend/domains/orders/routes.py` — add GET /check-stock endpoint
- `backend/domains/orders/schemas.py` — add StockCheckResponse, WarehouseStockInfo schemas

**Frontend (new files):**
- `src/domain/orders/hooks/useStockCheck.ts`

**Frontend (modified files from 5.1):**
- `src/domain/orders/components/OrderForm.tsx` — integrate stock display into line items

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Epic 5, Story 5.2]
- [Source: backend/domains/inventory/services.py — get_product_detail() for stock query pattern]
- [Source: backend/common/models/inventory_stock.py — InventoryStock model]
- [Source: src/domain/inventory/hooks/useProductSearch.ts — debounced hook pattern]

---

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
