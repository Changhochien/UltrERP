# Story 4.6: Multiple Warehouse Support

**Status:** done

**Story ID:** 4.6

---

## Story

As a warehouse staff,
I want to see and manage stock across multiple warehouse locations,
So that I can allocate inventory properly.

---

## Acceptance Criteria

**✓ AC1:** Warehouse master data
**Given** multiple warehouses exist
**When** I access the system
**Then** all warehouses are available for selection in inventory operations

**✓ AC2:** Per-warehouse stock visibility
**Given** a product has stock in multiple warehouses
**When** I view the product
**Then** I see stock levels per warehouse location

**✓ AC3:** Warehouse filtering
**Given** multiple warehouses exist
**When** I view inventory list or search results
**Then** I can filter by warehouse location

**✓ AC4:** Inter-warehouse transfers
**Given** I have stock in Warehouse A
**When** I initiate a transfer to Warehouse B
**Then** stock is transferred atomically with audit trail
**And** adjustment records created in both warehouses (outbound, inbound)

**✓ AC5:** Warehouse-scoped reorder points
**Given** a product has different reorder points per warehouse
**When** stock adjustment occurs
**Then** reorder alerts generated per warehouse's reorder point

**✓ AC6:** Warehouse assignment in orders & invoices
**Given** I'm creating a supplier order or picking for a sales order
**When** I select products
**Then** I specify which warehouse to pull stock from (or receive to)

**✓ AC7:** Warehouse context persistence
**Given** I select a current warehouse in the inventory module
**When** I navigate between inventory screens
**Then** that warehouse context persists for the session until I explicitly change it
**And** individual requests can still override the session warehouse when a cross-warehouse view is needed

---

## Tasks / Subtasks

- [ ] **Task 1: Warehouse Data Model** (AC1-AC3)
  - [ ] Create Alembic migration for `warehouse` table: (id, tenant_id, name, location, address, contact_email, code, is_active, created_at)
  - [ ] Create GET `/api/v1/warehouses` endpoint to list warehouses
  - [ ] Create GET `/api/v1/warehouses/{warehouse_id}` for details

- [ ] **Task 2: Warehouse-Scoped Inventory** (AC2-AC3)
  - [ ] Ensure `inventory_stock` table has warehouse_id foreign key
  - [ ] Extend `stock_adjustment` table with warehouse_id
  - [ ] Extend `reorder_alert` table with warehouse_id (unique: tenant_id, product_id, warehouse_id)
  - [ ] Update product search/detail to include warehouse parameter

- [ ] **Task 3: Warehouse Filtering** (AC3)
  - [ ] Add `warehouse_id` parameter to GET `/api/v1/inventory/products/search`
  - [ ] Add `warehouse_id` parameter to GET `/api/v1/inventory/products/{id}`
  - [ ] ProductDetail component: add warehouse selector dropdown

- [ ] **Task 4: Stock Transfer Functionality** (AC4)
  - [ ] Create POST `/api/v1/inventory/transfers` endpoint
  - [ ] Input: from_warehouse_id, to_warehouse_id, product_id, quantity, notes
  - [ ] Atomic transaction:
    - [ ] Validate `from_warehouse_id != to_warehouse_id` and `quantity > 0` before opening the transfer
    - [ ] Lock the source inventory row with `SELECT ... FOR UPDATE`, scoped by `tenant_id`, before validating stock
    - [ ] Validate source warehouse has sufficient stock
    - [ ] Decrement source warehouse stock (adjustment reason: `ReasonCode.TRANSFER_OUT`)
    - [ ] Increment target warehouse stock (adjustment reason: `ReasonCode.TRANSFER_IN`)
    - [ ] Create audit log entry with transfer_id reference
    - [ ] Record transfer_history entry
    - [ ] Use `AsyncSession` from `common.database.get_db` so the shared engine settings, including `statement_cache_size=0`, are inherited automatically

- [ ] **Task 5: Transfer UI Component** (AC4)
  - [ ] Create StockTransferForm component
  - [ ] Warehouse selector (from/to dropdowns)
  - [ ] Product selector, quantity input
  - [ ] Confirmation dialog before submission

- [ ] **Task 6: Warehouse-Aware Reorder Points** (AC5)
  - [ ] Allow setting reorder_point per (product, warehouse) combination
  - [ ] Update reorder alert logic to check warehouse-specific reorder point
  - [ ] Update reorder alert list to show warehouse context

- [ ] **Task 7: Supplier Orders with Warehouse** (AC6)
  - [ ] Supplier order lines include warehouse_id (for receiving location)
  - [ ] When marking received, stock goes to specified warehouse

- [ ] **Task 8: Frontend Warehouse Context** (AC1-AC7)
  - [ ] Add warehouse selector to global nav (or context)
  - [ ] Display current warehouse in inventory screens
  - [ ] Allow switching warehouse for multi-location operations
  - [ ] Persist selected warehouse for the active session and allow per-request override where workflows require cross-warehouse visibility

- [ ] **Task 9: Testing** (AC1-AC7)
  - [ ] Unit tests: transfer validation, per-warehouse reorder calculations
  - [ ] Integration tests: atomic transfer transactions
  - [ ] E2E tests: transfer workflow, warehouse-filtered views

---

## Dev Notes

### Architecture Compliance

- **Multi-Tenancy:** tenant_id in all tables [Source: arch#3.2 Data Architecture]
- **Atomic Transactions:** Transfer = 2 inventory updates + 2 adjustment records + 1 audit log, all in one transaction
- **Tenant Isolation:** User can only see/transfer within same tenant warehouses

### Project Structure

**Backend:**
- Model: `backend/common/models/warehouse.py`
- Model: `backend/common/models/stock_transfer.py` (or add to stock_adjustment with type discrimination)
- Route: `backend/domains/inventory/routes.py` — /warehouses, /transfers endpoints
- Service: `backend/domains/inventory/services.py` — transfer_stock(), get_warehouse_inventory()

**Frontend:**
- Component: `src/domain/inventory/components/WarehouseSelector.tsx` (global or scoped)
- Component: `src/domain/inventory/components/StockTransferForm.tsx`
- Hook: `src/domain/inventory/hooks/useWarehouses.ts`
- Context: `src/domain/inventory/context/WarehouseContext.tsx` for persisted session-level warehouse selection

**Database:**
- `warehouse` table: PK (id), UNIQUE (tenant_id, code)
- `inventory_stock` table: UNQ (tenant_id, product_id, warehouse_id)
- `stock_adjustment` table: includes warehouse_id
- `stock_transfer_history` table: (id, tenant_id, product_id, from_warehouse_id, to_warehouse_id, quantity, actor_id, created_at)
- Index: `inventory_stock_idx_warehouse_product` on (warehouse_id, product_id)

### Multi-Warehouse Inventory Aggregation

Some views may need total stock across all warehouses:

```python
# Total stock for a product (all warehouses)
SELECT SUM(quantity) FROM inventory_stock WHERE product_id = ? AND tenant_id = ?

# By warehouse
SELECT warehouse_id, quantity FROM inventory_stock WHERE product_id = ? AND tenant_id = ? ORDER BY warehouse_id
```

### Transfer Transaction Pattern

```python
async def transfer_stock(
  session: AsyncSession,
  tenant_id: str,
    from_warehouse_id: str,
    to_warehouse_id: str,
    product_id: str,
    quantity: int,
    actor_id: str,
) -> str:
  if from_warehouse_id == to_warehouse_id:
    raise ValueError("Cannot transfer to the same warehouse")

  async with session.begin():
        # 1. Validate source stock
    source = await get_inventory_stock_for_update(
      session, tenant_id, product_id, from_warehouse_id
    )
    if source is None:
      raise InsufficientStockError("Product not found in source warehouse")
        if source.quantity < quantity:
            raise InsufficientStockError()

        # 2. Update inventories
    await update_inventory_stock(session, tenant_id, product_id, from_warehouse_id, -quantity)
    await update_inventory_stock(session, tenant_id, product_id, to_warehouse_id, +quantity)

        # 3. Create adjustment records
        transfer_id = generate_uuid()
        await create_stock_adjustment({
      "tenant_id": tenant_id,
      "product_id": product_id,
      "warehouse_id": from_warehouse_id,
      "quantity_change": -quantity,
      "reason_code": ReasonCode.TRANSFER_OUT,
      "transfer_id": transfer_id,
        })
        await create_stock_adjustment({
      "tenant_id": tenant_id,
      "product_id": product_id,
      "warehouse_id": to_warehouse_id,
      "quantity_change": quantity,
      "reason_code": ReasonCode.TRANSFER_IN,
      "transfer_id": transfer_id,
        })

        # 4. Audit log
        await create_audit_log_entry(actor_id, "stock_transfer", transfer_details)

        # 5. Check reorder alerts for both warehouses
        source_after = await get_inventory_stock(session, tenant_id, product_id, from_warehouse_id)
        if source_after.quantity < reorder_point:
          await create_reorder_alert(session, tenant_id, product_id, from_warehouse_id)
        # etc.

        return transfer_id
```

---

## Dependencies & Related Stories

- **Impacts:** Story 4.1 (Search) — add warehouse filtering
- **Impacts:** Story 4.2 (Stock Detail) — show per-warehouse stock
- **Impacts:** Story 4.3 (Alerts) — warehouse-scoped alerts
- **Depends on:** Story 4.4 (Adjustments) — transfer flows reuse the shared `ReasonCode` enum and transaction pattern
- **Impacts:** Story 4.5 (Supplier Orders) — receive to specific warehouse
- **Related:** Story 5 (Orders) — pick from specific warehouse

---

## Technology Stack

| Tech | Version | Purpose |
|------|---------|---------|
| PostgreSQL | 17+ | Multi-warehouse schema |
| SQLAlchemy | 2.0+ | Async transaction management |
| FastAPI | 0.115+ | Warehouse & transfer API |
| React | 19 | Warehouse-aware UI |

---

## References

- [Story 4.1: Search Products](4-1-search-products.md)
- [Story 4.2: View Stock Level](4-2-view-stock-level.md)
- [Story 4.3: Reorder Alerts](4-3-reorder-alerts.md)
- [Story 4.4: Stock Adjustment](4-4-record-stock-adjustment.md)
- [Story 4.5: Supplier Orders](4-5-supplier-orders.md)
- [Architecture: Multi-Tenancy](../../docs/superpowers/specs/2026-03-30-erp-architecture-design-v2.md#data-architecture)

---

## Dev Agent Record

**Status:** done
**Last Updated:** 2026-04-01

### File List

- `backend/common/models/warehouse.py`
- `backend/domains/inventory/routes.py`
- `backend/domains/inventory/services.py`
- `src/domain/inventory/components/WarehouseSelector.tsx`
- `src/domain/inventory/components/StockTransferForm.tsx`
- `src/domain/inventory/hooks/useWarehouses.ts`
