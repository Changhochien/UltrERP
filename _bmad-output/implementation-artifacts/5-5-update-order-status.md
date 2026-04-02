# Story 5.5: Update Order Status

**Status:** ready-for-dev

**Story ID:** 5.5

---

## Story

As a sales rep,
I want to update order status through the lifecycle,
So that we track orders from pending to fulfillment.

---

## Acceptance Criteria

**AC1:** Valid status transitions
**Given** an order exists
**When** I update the status
**Then** only valid transitions are allowed:
  - pending → confirmed (handled by Story 5.4 with invoice generation)
  - confirmed → shipped
  - shipped → fulfilled
**And** invalid transitions return 409 Conflict

**AC2:** Status transition logging
**Given** I update an order's status
**When** the transition commits
**Then** an audit_log entry is created with:
  - action: "ORDER_STATUS_CHANGED"
  - before_state: `{ "status": "{old_status}" }`
  - after_state: `{ "status": "{new_status}" }`
  - actor_id, correlation_id

**AC3:** Cancel pending order
**Given** an order has status "pending"
**When** I cancel the order
**Then** the status changes to "cancelled"
**And** cancelled is a terminal state (no further transitions allowed)

**AC4:** Cancellation guard
**Given** an order has status other than "pending"
**When** I try to cancel
**Then** the system returns 409 Conflict — only pending orders can be cancelled

**AC5:** Status-specific timestamps
**Given** an order transitions to "confirmed"
**When** the transition completes
**Then** `confirmed_at` is set (already handled in Story 5.4)

**AC6:** Order status in list view
**Given** orders exist with various statuses
**When** I view the order list
**Then** each order displays its current status with a color-coded badge
**And** I can filter by status

**AC7:** Status update UI
**Given** I view an order detail
**When** I see the current status
**Then** only valid next-status options are shown as action buttons
**And** a confirmation dialog appears before each transition

---

## Tasks / Subtasks

- [ ] **Task 1: Status State Machine** (AC1, AC3, AC4)
  - [ ] In `backend/domains/orders/schemas.py`, define `OrderStatus` enum:
    ```python
    class OrderStatus(str, Enum):
        PENDING = "pending"
        CONFIRMED = "confirmed"
        SHIPPED = "shipped"
        FULFILLED = "fulfilled"
        CANCELLED = "cancelled"
    ```
  - [ ] Define `ALLOWED_TRANSITIONS` as frozenset for immutability:
    ```python
    ALLOWED_TRANSITIONS: dict[OrderStatus, frozenset[OrderStatus]] = {
        OrderStatus.PENDING: frozenset({OrderStatus.CONFIRMED, OrderStatus.CANCELLED}),
        OrderStatus.CONFIRMED: frozenset({OrderStatus.SHIPPED}),
        OrderStatus.SHIPPED: frozenset({OrderStatus.FULFILLED}),
        OrderStatus.FULFILLED: frozenset(),    # terminal
        OrderStatus.CANCELLED: frozenset(),    # terminal
    }
    ```
  - [ ] Implement `update_order_status(session, tenant_id, order_id, new_status, actor_id)`:
    - [ ] Fetch order with `with_for_update()` for locking
    - [ ] Validate new_status is in ALLOWED_TRANSITIONS[current_status]
    - [ ] If transitioning to "confirmed", delegate to `confirm_order()` from Story 5.4 (which handles invoice creation and its own transaction — do NOT wrap in another session.begin())
    - [ ] For other transitions (shipped, fulfilled, cancelled): update status directly within `async with session.begin():`
    - [ ] Create audit_log entry (for actor_id, use `str(actor_id)` since AuditLog.actor_id is String(100))
    - [ ] Update `order.updated_at`
    - [ ] Note: For "confirmed" transition, confirm_order() manages its own session.begin() via _create_invoice_core(). For all other transitions, use `async with session.begin():`

- [ ] **Task 2: Delete/Cancel Route** (AC3, AC4)
  - [ ] Add `DELETE /api/v1/orders/{order_id}` to routes — cancels pending orders (returns 409 if not pending)
  - [ ] Internally calls `update_order_status()` with new_status="cancelled"
  - [ ] Returns the order with status="cancelled"

- [ ] **Task 3: Status Transition Route Enhancement** (AC1, AC2)
  - [ ] The `PATCH /api/v1/orders/{order_id}/status` endpoint from Story 5.4 handles ALL transitions
  - [ ] Validate `new_status` is one of: confirmed, shipped, fulfilled, cancelled
  - [ ] Route confirmed → confirm_order() (Story 5.4), other transitions → update_order_status()

- [ ] **Task 4: Frontend — Status Actions** (AC6, AC7)
  - [ ] In OrderDetail.tsx:
    - [ ] Show current status with color-coded badge (pending=yellow, confirmed=blue, shipped=purple, fulfilled=green, cancelled=red)
    - [ ] Show action buttons for valid next statuses only
    - [ ] "Confirm Order" button (pending → confirmed) — already from Story 5.4
    - [ ] "Mark Shipped" button (confirmed → shipped)
    - [ ] "Mark Fulfilled" button (shipped → fulfilled)
    - [ ] "Cancel Order" button (pending only)
    - [ ] Each action shows a confirmation dialog before proceeding
  - [ ] In OrderList.tsx:
    - [ ] Add status filter dropdown
    - [ ] Color-coded status badges on each row
  - [ ] Create `src/domain/orders/hooks/useOrderStatus.ts` with:
    - [ ] `statusLabel(status)` and `statusColor(status)` helpers (same pattern as supplier orders)
    - [ ] `allowedTransitions(currentStatus)` helper

- [ ] **Task 5: Backend Tests** (AC1-AC4)
  - [ ] `backend/tests/test_order_status.py`:
    - [ ] Test valid transitions: confirmed→shipped, shipped→fulfilled
    - [ ] Test invalid transitions: pending→shipped (409), confirmed→fulfilled (409), fulfilled→anything (409)
    - [ ] Test cancel pending order succeeds
    - [ ] Test cancel non-pending order returns 409
    - [ ] Test audit log created for each transition
    - [ ] Test FOR UPDATE locking prevents concurrent status updates
    - [ ] Test confirmed transition delegates to confirm_order (invoice created)

- [ ] **Task 6: Frontend Tests** (AC6, AC7)
  - [ ] `src/domain/orders/__tests__/OrderDetail.test.tsx`:
    - [ ] Test correct action buttons shown per status
    - [ ] Test confirmation dialog for status changes
    - [ ] Test status badge colors
  - [ ] `src/domain/orders/__tests__/OrderList.test.tsx`:
    - [ ] Test status filter

---

## Dev Notes

### Architecture Compliance

- **State Machine Pattern:** Use local `ALLOWED_TRANSITIONS` dict inside function (same pattern as `update_supplier_order_status()` in inventory services — NOT module-level constant) [Source: inventory services.py]
- **FOR UPDATE Locking:** Lock order row before transition to prevent concurrent updates [Source: arch — row-level locking pattern]
- **Delegation Pattern:** "pending → confirmed" transition MUST delegate to `confirm_order()` which handles invoice auto-generation. Do NOT duplicate invoice creation in this story
- **Cancel as Status:** Cancellation is modeled as a status transition ("cancelled"), not a DELETE that removes the record. The DELETE route is syntactic sugar that internally triggers the cancel transition

### OrderStatus Enum

- Define as `class OrderStatus(str, Enum)` in `backend/domains/orders/schemas.py`:
  ```
  PENDING = "pending"
  CONFIRMED = "confirmed"
  SHIPPED = "shipped"
  FULFILLED = "fulfilled"
  CANCELLED = "cancelled"
  ```
- Used for validation in route handlers and state machine
- Import and use this enum in services.py for ALLOWED_TRANSITIONS
- Audit log: `actor_id` is `String(100)`, so use `ACTOR_ID = str(DEFAULT_TENANT_ID)` (not UUID)
- Audit log fields: entity_type="order", entity_id=str(order.id), action="ORDER_STATUS_CHANGED"

### Notification Hook (Future)

- Stories mention "status change triggers appropriate notifications" — this is NOT in scope for Epic 5
- LINE notifications are Epic 8+ scope
- For now, the audit_log serves as the notification record
- Domain events can be emitted but no listeners need to be wired

### Dependencies

- **Depends on Story 5.1:** Order model, base routes
- **Depends on Story 5.4:** confirm_order() function for pending→confirmed transition
- **Extends Story 5.4:** The PATCH /status endpoint is created in 5.4 — this story adds shipped/fulfilled/cancelled transitions and the full state machine
- **Frontend reuses:** Status badge and filter patterns from SupplierOrderList/SupplierOrderDetail in inventory domain

### Key Conventions

- Tab indentation, `from __future__ import annotations`
- 409 Conflict for invalid state transitions
- `async with session.begin():` for atomic transactions
- `with_for_update()` for row-level locking
- Audit log: action="ORDER_STATUS_CHANGED", before_state/after_state as JSON dicts

### Project Structure Notes

**Backend (new files):**
- `backend/tests/test_order_status.py`

**Backend (modified files):**
- `backend/domains/orders/services.py` — add update_order_status(), ALLOWED_TRANSITIONS
- `backend/domains/orders/routes.py` — add DELETE endpoint, enhance PATCH /status
- `backend/domains/orders/schemas.py` — add OrderStatus enum, OrderStatusUpdate schema

**Frontend (modified files):**
- `src/domain/orders/components/OrderDetail.tsx` — status actions, badges, dialogs
- `src/domain/orders/components/OrderList.tsx` — status filter, badges
- `src/domain/orders/hooks/useOrderStatus.ts` — status helpers, transition logic
- `src/domain/orders/types.ts` — OrderStatus type

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Epic 5, Story 5.5]
- [Source: backend/domains/inventory/services.py — update_supplier_order_status() for state machine pattern]
- [Source: backend/domains/inventory/services.py — ALLOWED_TRANSITIONS local dict pattern]
- [Source: src/domain/inventory/hooks/useSupplierOrders.ts — statusLabel/statusColor helpers]
- [Source: src/domain/inventory/components/SupplierOrderDetail.tsx — status action UI pattern]

---

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
