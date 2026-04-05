# Story 4.4: Record Stock Adjustment with Reason Codes

**Status:** done

**Story ID:** 4.4

---

## Story

As a warehouse staff,
I want to record stock adjustments with reason codes,
So that we maintain accurate inventory records with audit trail.

---

## Acceptance Criteria

**✓ AC1:** Adjustment form with reason codes
**Given** I'm on the stock adjustment screen
**When** I enter adjustment details (product, warehouse, quantity change)
**Then** I must select a reason code: received, damaged, returned, correction, other

**✓ AC2:** Quantity validation
**Given** a product has 50 units in stock
**When** I attempt to remove 60 units
**Then** the system rejects with error "Insufficient stock: 50 units available"

**✓ AC3:** Immediate stock update
**Given** I record a stock adjustment
**When** the adjustment is saved
**Then** stock levels update immediately in the system

**✓ AC4:** Audit trail logging
**Given** a stock adjustment is made
**When** the record is saved
**Then** audit_log records: timestamp, actor_id, product_id, adjustment_type, qty_change, reason_code

**✓ AC5:** Adjustment history
**Given** adjustments have been made to a product
**When** I view product details
**Then** I see complete adjustment history with date, actor, reason, quantity change

**✓ AC6:** Reason code persistence
**Given** reason codes are predefined
**When** any staff member adjusts stock
**Then** they select from the same set of predefined reason codes

**✓ AC7:** System-generated reason codes are reserved
**Given** stock is updated by supplier receipt or warehouse transfer workflows
**When** the system records the adjustment
**Then** it uses reserved system reason codes and those values are not manually selectable in the warehouse UI

---

## Tasks / Subtasks

- [ ] **Task 1: Reason Code Configuration** (AC1, AC6, AC7)
  - [ ] Define user-selectable reason codes: RECEIVED, DAMAGED, RETURNED, CORRECTION, OTHER
  - [ ] Define system-only reason codes: SUPPLIER_DELIVERY, TRANSFER_OUT, TRANSFER_IN
  - [ ] Store reason codes in configuration or enum with metadata for `selectable_by_user`
  - [ ] Make reason codes retrievable via API endpoint GET `/api/v1/inventory/reason-codes`

- [ ] **Task 2: Stock Adjustment Data Model** (AC1-AC5)
  - [ ] Create Alembic migration for `stock_adjustment` table: (id, tenant_id, product_id, warehouse_id, quantity_change, reason_code, actor_id, notes, created_at)
  - [ ] Create `stock_adjustment_history` view: shows all adjustments with actor_name, product_name

- [ ] **Task 3: Backend Adjustment Endpoint** (AC2-AC5)
  - [ ] Create POST `/api/v1/inventory/adjustments` endpoint
  - [ ] Input: product_id, warehouse_id, quantity_change, reason_code, notes (optional)
  - [ ] Load the target `inventory_stock` row with `SELECT ... FOR UPDATE`, scoped by `tenant_id`, before validating and mutating stock
  - [ ] Validate quantity doesn't exceed available stock
  - [ ] Atomically: update inventory_stock, insert stock_adjustment, create audit_log entry, and create/resolve reorder_alert when the new stock crosses the warehouse reorder point (per Story 4.3)
  - [ ] Return: adjustment_id, updated_stock_level, timestamp
  - [ ] Use `AsyncSession` from `common.database.get_db` so the shared engine settings, including `statement_cache_size=0`, are inherited automatically

- [ ] **Task 4: Frontend Adjustment Form** (AC1-AC2)
  - [ ] Create StockAdjustmentForm component (React)
  - [ ] Input: product selector, warehouse selector, quantity input, reason dropdown
  - [ ] Validate quantity against current stock in real-time
  - [ ] Show confirmation dialog before submitting

- [ ] **Task 5: Audit Trail Integration** (AC4-AC5)
  - [ ] Record all adjustments in audit_log
  - [ ] Include actor_type, action, before_state, after_state
  - [ ] Make audit_log immutable (append-only; no updates/deletes)

- [ ] **Task 6: Testing** (AC1-AC6)
  - [ ] Unit tests: reason code validation, quantity validation
  - [ ] Integration tests: atomic transaction (inventory + audit log + history)
  - [ ] E2E test: full adjustment workflow from form submission to history view

---

## Dev Notes

### Architecture Compliance

- **Audit Log:** All adjustments recorded in audit_log table [Source: arch#4.3]
- **Transaction:** Stock adjustment must be atomic: update inventory + log history + log audit
- **Immutability:** Audit log entries cannot be modified/deleted
- **Tenant Isolation:** All records include tenant_id for multi-tenant support

### Project Structure

**Backend:**
- Model: `backend/common/models/stock_adjustment.py`
- Route: `backend/domains/inventory/routes.py` — POST /adjustments
- Service: `backend/domains/inventory/services.py` — create_stock_adjustment()
- Schema: `backend/domains/inventory/schemas.py` — StockAdjustmentRequest, ReasonCode enum

**Frontend:**
- Component: `src/domain/inventory/components/StockAdjustmentForm.tsx`
- Hook: `src/domain/inventory/hooks/useStockAdjustment.ts`
- API: `src/lib/api/inventory.ts` — submitAdjustment()

**Database:**
- `stock_adjustment` table: (id, tenant_id, product_id, warehouse_id, quantity_change, reason_code, actor_id, notes, created_at)
- `stock_adjustment_history` view: JOIN stock_adjustment with users and products for display
- `audit_log` table: populated by application logic on stock_adjustment INSERT; append-only enforced by database trigger

### Transaction Pattern

```python
# Backend: Atomic adjustment transaction
async with session.begin():
    # 1. Validate stock
  inventory = await get_inventory_stock_for_update(
    session, tenant_id, product_id, warehouse_id
  )
    if inventory.quantity + adjustment.quantity_change < 0:
        raise InsufficientStockError()

  new_stock = inventory.quantity + adjustment.quantity_change

    # 2. Update inventory
  await update_inventory_stock(
    session, tenant_id, product_id, warehouse_id, adjustment.quantity_change
  )

    # 3. Log adjustment
  await create_stock_adjustment_record(session, tenant_id, adjustment)

    # 4. Audit log
    await create_audit_log_entry(actor_id, "stock_adjust", before_stock, after_stock)

  # 5. Check reorder alerts (Story 4.3 contract)
    if new_stock < reorder_point:
    await create_reorder_alert(session, tenant_id, product_id, warehouse_id, new_stock)
  else:
    await resolve_reorder_alert(session, tenant_id, product_id, warehouse_id)
```

### Reason Code Reference

Define as enum or config constant:

```python
class ReasonCode(str, Enum):
    RECEIVED = "received"                  # Manual warehouse receipt
    DAMAGED = "damaged"            # Items damaged/spoiled
    RETURNED = "returned"          # Customer return
    CORRECTION = "correction"      # Manual count correction
    OTHER = "other"                # Other reason
    SUPPLIER_DELIVERY = "supplier_delivery"  # System-only supplier receipt
    TRANSFER_OUT = "transfer_out"            # System-only source warehouse transfer
    TRANSFER_IN = "transfer_in"              # System-only destination warehouse transfer
```

User-facing forms should expose only the user-selectable reason codes. System-only codes are reserved for Stories 4.5 and 4.6.

---

## Dependencies & Related Stories

- **Depends on:** Story 4.2 (View Stock Level) — stock displayed after adjustment
- **Triggers:** Story 4.3 (Reorder Alerts) — alerts may be created by adjustment
- **Related to:** Story 4.5 (Supplier Orders) — received state linked to supplier orders

---

## Technology Stack

| Tech | Version | Purpose |
|------|---------|---------|
| PostgreSQL | 18+ | Transactional adjustments |
| SQLAlchemy | 2.0+ | Async transaction management |
| FastAPI | 0.135+ | Adjustment endpoint |
| React | 19 | Form component |
| Zod/Pydantic | latest | Input validation |

---

## References

- [Story 4.2: View Stock Level](4-2-view-stock-level.md)
- [Story 4.3: Reorder Alerts](4-3-reorder-alerts.md)
- [Story 4.5: Supplier Orders](4-5-supplier-orders.md)
- [Architecture: Audit Log Pattern](../../docs/superpowers/specs/2026-03-30-erp-architecture-design-v2.md#audit-log)

---

## Dev Agent Record

**Status:** done
**Last Updated:** 2026-04-01

### File List

- `backend/common/models/stock_adjustment.py`
- `backend/domains/inventory/routes.py`
- `backend/domains/inventory/services.py`
- `src/domain/inventory/components/StockAdjustmentForm.tsx`
- `src/domain/inventory/hooks/useStockAdjustment.ts`
