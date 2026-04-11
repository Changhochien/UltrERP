# Story 4.3: Reorder Alerts

**Status:** done

**Story ID:** 4.3

---

## Story

As a system,
I want to generate reorder alerts when stock falls below reorder point,
So that warehouse staff can proactively reorder.

---

## Acceptance Criteria

**✓ AC1:** Alert generation on stock adjustment
**Given** a product's stock falls below its reorder point
**When** a stock adjustment is made
**Then** an alert is generated in the system

**✓ AC2:** Alert visibility in inventory module
**Given** reorder alerts exist
**When** I view the inventory module
**Then** I see a list of products needing reorder with: product name, current stock, reorder point, warehouse

**✓ AC3:** Dashboard integration
**Given** reorder alerts exist
**When** I view the business dashboard
**Then** I see low-stock alerts section (Epic 7, Story 7.3)

**✓ AC4:** Alert lifecycle controls
**Given** a reorder alert is displayed
**When** I acknowledge, snooze, or dismiss the alert
**Then** the alert status changes to "acknowledged", "snoozed", or "dismissed" respectively

**✓ AC5:** Alert persistence
**Given** a product stock is still below reorder point
**When** I log out and log back in
**Then** the alert persists until stock is restored above reorder point

**✓ AC6:** Bulk reorder workflow
**Given** multiple products have reorder alerts
**When** I select products from the alert list
**Then** I can bulk-create supplier orders (integration with Story 4.5)

**✓ AC7:** Atomic alert updates
**Given** a stock adjustment would create or resolve a reorder alert
**When** the adjustment transaction fails at any step
**Then** neither the stock change nor the alert state change is committed

---

## Tasks / Subtasks

- [ ] **Task 1: Alert Data Model & Transactional Logic** (AC1-AC2)
  - [ ] Create Alembic migration for `reorder_alert` table: (id, tenant_id, product_id, warehouse_id, current_stock, reorder_point, status, created_at, acknowledged_at, acknowledged_by, snoozed_until, snoozed_by, dismissed_at, dismissed_by)
  - [ ] Add UNIQUE constraint: `UNIQUE(tenant_id, product_id, warehouse_id)` — prevents duplicate active alerts
  - [ ] **CRITICAL:** Alert creation uses TRANSACTIONAL pattern (NOT PostgreSQL triggers)
  - [ ] Alert logic implemented within stock adjustment transaction (see Story 4.4 Task 3 pattern)
  - [ ] Lock the affected `inventory_stock` row inside the parent stock-adjustment transaction before computing alert transitions
  - [ ] When stock adjustment completes in StockAdjustmentService:
    1. Update inventory_stock
    2. Check if new_stock < reorder_point for this product/warehouse
    3. If below reorder_point: `UPSERT reorder_alert` while preserving `acknowledged` status unless the alert was already resolved
    4. If above reorder_point: `UPDATE reorder_alert SET status='resolved'`
    5. Create audit_log entry for the adjustment (not the alert creation)
  - [ ] All operations within single `async with session.begin():` block to ensure atomicity
  - [ ] Status enum values: pending, acknowledged, snoozed, dismissed, resolved

- [ ] **Task 2: Backend Alert API** (AC1-AC3)
  - [ ] Create GET `/api/v1/inventory/alerts/reorder` endpoint
  - [ ] Return: product_id, product_name, current_stock, reorder_point, warehouse_name, severity, status, created_at, snoozed_until, dismissed_at
  - [ ] Support filtering: status (pending, acknowledged, snoozed, dismissed, resolved), warehouse_id, date_range
  - [ ] Sort by created_at DESC (newest first) or by urgency (most below reorder point first)
  - [ ] Add HTTP error codes: 200 OK, 400 Bad Request, 404 Not Found, 422 Unprocessable Entity
  - [ ] Include tenant_id filter to ensure multi-tenancy isolation

- [ ] **Task 3: Reorder Lifecycle Endpoints** (AC4)
  - [ ] Create PUT `/api/v1/inventory/alerts/reorder/{alert_id}/acknowledge` endpoint
  - [ ] Update alert status to "acknowledged", record timestamp & actor
  - [ ] Create PUT `/api/v1/inventory/alerts/reorder/{alert_id}/snooze` endpoint
  - [ ] Update alert status to "snoozed", record snooze deadline & actor
  - [ ] Create PUT `/api/v1/inventory/alerts/reorder/{alert_id}/dismiss` endpoint
  - [ ] Update alert status to "dismissed", record timestamp & actor
  - [ ] Scope acknowledge updates by `tenant_id` so one tenant cannot acknowledge another tenant's alert

- [ ] **Task 4: Frontend Alert Display** (AC2-AC6)
  - [ ] Create ReorderAlerts component (table view with sorting, filtering)
  - [ ] Show alert count badge in navigation
  - [ ] Implement checkbox selection for bulk actions
  - [ ] Add "Create Supplier Order" button (linked to Story 4.5)

- [ ] **Task 5: Dashboard Widget** (AC3)
  - [ ] Create low-stock alert widget for dashboard
  - [ ] Display top 5 alerts by reorder urgency
  - [ ] Expose compact payload contract for Story 7.3: alert_count, top_alerts[], last_updated_at
  - [ ] Link to full alert list

- [ ] **Task 6: Testing** (AC1-AC7)
  - [ ] Unit tests: alert trigger logic on stock adjustment
  - [ ] Integration tests: alerts persist correctly after logout/login
  - [ ] Integration tests: acknowledged alerts remain acknowledged when stock changes but stays below reorder point
  - [ ] Integration tests: failed alert UPSERT/resolve rolls back the parent stock adjustment transaction
  - [ ] E2E tests: acknowledge alert, dismiss alert, bulk select workflow

---

## Dev Notes

### Architecture Compliance

- **Database:** Reorder alerts are created or resolved inside the stock adjustment transaction; audit_log captures the originating inventory mutation and alert acknowledgments
- **Real-time:** Stock adjustments immediately trigger alert logic (no async delay)
- **Caching:** Alert list cached with 1-minute TTL (Redis)

### Post-Implementation Notes

- 2026-04-11: Aligned the reorder-alert severity contract with the low-stock investigation. Backend `_compute_severity()` now treats stockout or stock below 25% of ROP as `CRITICAL`, stock below ROP as `WARNING`, and exact-threshold alerts as `INFO`.
- 2026-04-11: The backend/API is now the single source of truth for alert severity. Downstream clients should render `severity` from the alert payload instead of recomputing urgency from `current_stock` and `reorder_point`.
- 2026-04-11: Extended the alert lifecycle beyond acknowledge-only handling. Reorder alerts now support `snoozed` and `dismissed` states with explicit endpoints, persisted actor/timestamp metadata, and list filtering for the new states.
- 2026-04-11: Dismissed alerts stay suppressed for the current breach cycle, but reopen automatically after stock genuinely recovers above ROP and drops again. Expired snoozes surface as `pending` in the alert list so the UI does not strand overdue alerts.

### Project Structure

**Backend:**
- Model: `backend/common/models/reorder_alert.py`
- Route: `backend/domains/inventory/routes.py` — /alerts/reorder endpoints
- Service: `backend/domains/inventory/services.py` — create_reorder_alert(), acknowledge_alert()

**Frontend:**
- Component: `src/domain/inventory/components/ReorderAlerts.tsx`
- Hook: `src/domain/inventory/hooks/useReorderAlerts.ts`
- Widget: `src/domain/dashboard/components/LowStockWidget.tsx`

**Database:**
- `reorder_alert` table: PK (id), UNQ (tenant_id, product_id, warehouse_id) — only one active alert per product/warehouse
- Application-side UPSERT/resolve logic in `StockAdjustmentService` updates alerts within the same transaction as inventory changes

#### Alert Status Flow

```
pending → (user acknowledges) → acknowledged
  ├→ (user snoozes) → snoozed → (snooze expires) → pending
  ├→ (user dismisses) → dismissed
  └→ (stock restored) → resolved
```

### ⚠️ CRITICAL: Transactional Alert Pattern (NOT Triggers)

**ARCHITECTURE REQUIREMENT:** All operations must be atomic with audit_log in same transaction [Source: arch v2#4.3]

**Correct Pattern (use this):**
```python
# In StockAdjustmentService.record_adjustment()
async with session.begin():
    # 1. Update inventory
  inventory = await get_inventory_stock_for_update(
    session, tenant_id, product_id, warehouse_id
  )
  new_stock = inventory.quantity + qty_change
  await update_inventory_stock(session, tenant_id, product_id, warehouse_id, qty_change)

    # 2. Create adjustment record
    await create_stock_adjustment({
    "tenant_id": tenant_id,
    "product_id": product_id,
    "warehouse_id": warehouse_id,
    "quantity_change": qty_change,
    "reason_code": reason_code,
    "actor_id": actor_id,
    "notes": notes,
    })

    # 3. Create audit_log entry
    await create_audit_log_entry(actor_id, "stock_adjust", {...})

    # 4. Check and create/update reorder alert (SAME TRANSACTION)
  reorder_pt = await get_product_reorder_point(session, tenant_id, product_id, warehouse_id)
  if new_stock < reorder_pt:
        # UPSERT reorder_alert (create if not exists, update if exists)
    await session.execute(
            """
            INSERT INTO reorder_alert (tenant_id, product_id, warehouse_id,
                                       current_stock, reorder_point, status, created_at)
            VALUES (:tenant_id, :product_id, :warehouse_id, :current_stock,
                    :reorder_point, 'pending', NOW())
            ON CONFLICT (tenant_id, product_id, warehouse_id)
      DO UPDATE SET
        current_stock=:current_stock,
        reorder_point=:reorder_point,
        status=CASE
          WHEN reorder_alert.status = 'acknowledged' THEN reorder_alert.status
          ELSE 'pending'
        END
            """
        )
    else:
        # Stock restored above reorder point
    await session.execute(
            "UPDATE reorder_alert SET status='resolved' "
            "WHERE tenant_id=:tenant_id AND product_id=:product_id "
            "AND warehouse_id=:warehouse_id"
        )
```

**Why NOT triggers:**
- PostgreSQL triggers cannot easily participate in application-side audit_log transaction
- Trigger would run AFTER UPDATE, but audit_log needs to be in same transaction
- Application-side logic allows atomic: inventory + adjustment + audit + alert all together
- Ensures consistency: if any part fails, entire transaction rolls back

### Bulk Reorder Integration

Alert selection feeds into Story 4.5 (Supplier Orders) for bulk order creation from reorder alerts.

---

## Dependencies & Related Stories

- **Depends on:** Story 4.2 (View Stock Level) — reorder point defined here
- **Depends on:** Story 4.4 (Stock Adjustment) — alerts triggered by adjustments
- **Related to:** Story 4.5 (Supplier Orders) — bulk select to create orders
- **Related to:** Story 7.3 (Dashboard Low-Stock) — alerts displayed on dashboard

---

## Technology Stack

| Tech | Version | Purpose |
|------|---------|---------|
| PostgreSQL | 18+ | reorder_alert table & transactional UPSERT flow |
| Redis | 7+ | Cache alert list (1-min TTL) |
| FastAPI | 0.135+ | Alert API endpoints |
| React | 19 | Alert table component |

---

## References

- [Story 4.2: View Stock Level](4-2-view-stock-level.md)
- [Story 4.4: Stock Adjustment](4-4-record-stock-adjustment.md)
- [Story 7.3: Dashboard Low-Stock](../epics.md#story-73-low-stock-alerts)
- [Architecture: Audit Log Pattern](../../docs/superpowers/specs/2026-03-30-erp-architecture-design-v2.md)

---

## Dev Agent Record

**Status:** done
**Last Updated:** 2026-04-01

### File List

- `backend/common/models/reorder_alert.py`
- `backend/domains/inventory/routes.py`
- `src/domain/inventory/components/ReorderAlerts.tsx`
- `src/domain/dashboard/components/LowStockWidget.tsx`

### Completion Notes List

- 2026-04-04 follow-up: `backend/common/models/reorder_alert.py` now supplies SQLAlchemy `Enum(..., values_callable=...)` so PostgreSQL `alert_status_enum` receives lowercase values (`pending`, `acknowledged`, `resolved`) instead of Python member names.
- This fixed the runtime PostgreSQL enum failure that was breaking reorder-alert queries in both inventory workflows and the dashboard low-stock widget.
