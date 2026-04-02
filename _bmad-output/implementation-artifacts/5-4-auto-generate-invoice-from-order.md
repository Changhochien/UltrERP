# Story 5.4: Auto-Generate Invoice from Confirmed Order

**Status:** ready-for-dev

**Story ID:** 5.4

---

## Story

As a system,
I want to auto-generate an invoice when an order is confirmed,
So that billing happens automatically without manual intervention.

---

## Acceptance Criteria

**AC1:** Invoice auto-creation on confirmation
**Given** a sales rep confirms an order (status changes from "pending" to "confirmed")
**When** the status transition is committed
**Then** an invoice is automatically created with:
  - All line items copied from order (product, qty, unit_price, tax_type, tax_rate, amounts)
  - customer_id from the order
  - invoice_date = today
  - status = "issued"
  - Correct subtotal, tax_amount, total_amount

**AC2:** Invoice-order linkage
**Given** an invoice is auto-generated from an order
**When** the creation completes
**Then** the order's `invoice_id` field is set to the new invoice's ID
**And** the invoice has an `order_id` field pointing back to the order

**AC3:** Tax calculation consistency
**Given** order line items have tax_type and tax_rate
**When** the invoice is generated
**Then** tax is calculated using the same `domains.invoices.tax` engine as manual invoice creation
**And** invoice totals match order totals exactly (rounding consistency)

**AC4:** Atomic transaction
**Given** the order confirmation triggers invoice creation
**When** either the status update OR invoice creation fails
**Then** the entire transaction rolls back — order stays "pending", no orphaned invoice

**AC5:** Validation before confirmation
**Given** an order is being confirmed
**When** validation runs
**Then** the order must have ≥1 line item
**And** the order must NOT already have an invoice_id (prevent duplicate invoices)
**And** the customer must still exist and be active

**AC6:** Confirmation response
**Given** the order is confirmed and invoice created
**When** the API responds
**Then** the response includes the order with updated status and the invoice_id
**And** a confirmation message or indicator is available

**AC7:** Audit logging
**Given** a confirmation occurs
**When** the transaction commits
**Then** audit_log entries are created for both:
  - Order status change (ORDER_STATUS_CHANGED: pending → confirmed)
  - Invoice creation (INVOICE_CREATED with order_id reference)

---

## Tasks / Subtasks

- [ ] **Task 1: Alembic Migration — Invoice order_id Column** (AC2)
  - [ ] Create migration `jj000ll00m32_add_invoice_order_id.py` chaining from orders migration
  - [ ] Add `order_id` (UUID, nullable, FK → orders.id ON DELETE SET NULL) to `invoices` table
  - [ ] Add index `ix_invoices_order_id` on (order_id)
  - [ ] This is a backward-compatible column addition — existing invoices get NULL order_id

- [ ] **Task 2: Update Invoice Model** (AC2)
  - [ ] Add `order_id: Mapped[uuid.UUID | None]` to Invoice model in `backend/domains/invoices/models.py`
  - [ ] Add FK constraint to orders table
  - [ ] No back_populates needed for MVP (avoid circular imports)

- [ ] **Task 3: Order Confirmation Service** (AC1, AC3-AC5, AC7)
  - [ ] In `backend/domains/orders/services.py`, implement `confirm_order(session, tenant_id, order_id, actor_id)`:
    - [ ] Fetch order with `selectinload(Order.lines)` and `with_for_update()` for locking
    - [ ] Validate status == "pending" (else 409 Conflict)
    - [ ] Validate order has ≥1 line
    - [ ] Validate order has no existing invoice_id (prevent duplicate)
    - [ ] Validate customer exists and is active (fetch with selectinload to get normalized_business_number for invoice buyer_identifier)
    - [ ] Create invoice by calling the existing `domains.invoices.service.create_invoice()` function directly:
      - **CRITICAL — Transaction Management:** `create_invoice()` uses `async with session.begin():` internally. You CANNOT nest another `session.begin()` around it (SQLAlchemy 2.0 raises on nested begin). Two options:
        - **Option A (recommended):** Extract `_create_invoice_core(session, data, tenant_id)` from `create_invoice()` that contains all logic WITHOUT `session.begin()`. Then `create_invoice()` becomes a thin wrapper: `async with session.begin(): return await _create_invoice_core(...)`. `confirm_order()` calls `_create_invoice_core()` within its own single `session.begin()` scope for atomicity.
        - **Option B:** Call `create_invoice()` without wrapping in `session.begin()` — but then order update and invoice creation are NOT atomic (risk of partial commit).
      - Map OrderLine fields → InvoiceCreateLine fields
      - Pass customer_id, invoice_date=today, buyer_type from customer
      - Let the invoice service handle number allocation, tax calculation, and totals
    - [ ] Set `order.invoice_id = new_invoice.id`
    - [ ] Set `new_invoice.order_id = order.id` (if model updated)
    - [ ] Set `order.status = "confirmed"`, `order.confirmed_at = now()`
    - [ ] Create audit_log entries for both events
    - [ ] All within `async with session.begin():` for atomicity (using `_create_invoice_core()` per Option A above — do NOT nest `create_invoice()`'s own `session.begin()`)

- [ ] **Task 4: Confirm Order Route** (AC1, AC6)
  - [ ] Add `PATCH /api/v1/orders/{order_id}/status` to orders routes
  - [ ] Accept body: `{ "new_status": "confirmed" }` (this handles Story 5.5's other transitions too)
  - [ ] For "confirmed" transition specifically, call `confirm_order()` which handles invoice creation
  - [ ] Return order response with invoice_id populated

- [ ] **Task 5: Frontend — Confirm Action** (AC6)
  - [ ] In OrderDetail.tsx, add "Confirm Order" button (only visible when status == "pending")
  - [ ] Show confirmation dialog: "Confirming this order will auto-generate an invoice. Continue?"
  - [ ] On success, display new invoice ID and updated status
  - [ ] Create `src/domain/orders/hooks/useOrderStatus.ts` — useConfirmOrder(), useUpdateOrderStatus()

- [ ] **Task 6: Backend Tests** (AC1-AC7)
  - [ ] `backend/tests/test_order_confirmation.py`:
    - [ ] Test confirm order creates invoice with correct line items and amounts
    - [ ] Test confirm order sets invoice_id on order and order_id on invoice
    - [ ] Test confirm order atomic — if invoice creation fails, order remains pending
    - [ ] Test confirm order with no line items returns 409
    - [ ] Test confirm order with existing invoice_id returns 409 (idempotency guard)
    - [ ] Test confirm non-pending order returns 409
    - [ ] Test audit log entries created for both order and invoice
    - [ ] Test tax amounts match between order and invoice

- [ ] **Task 7: Frontend Tests** (AC6)
  - [ ] In `src/domain/orders/__tests__/OrderDetail.test.tsx`:
    - [ ] Test confirm button shows only for pending orders
    - [ ] Test confirmation dialog appears on click
    - [ ] Test successful confirmation updates display

---

## Dev Notes

### Architecture Compliance

- **Cross-Domain Service Call:** This story calls `domains.invoices.service.create_invoice()` from within `domains.orders.services`. This is acceptable in the modular monolith pattern — domains can call each other's service functions directly (intra-process, not HTTP) [Source: arch AR6]
- **Invoice Service Reuse:** DO NOT duplicate invoice creation logic. The existing `create_invoice()` handles: invoice number allocation from ranges, tax calculation, line amount computation, audit logging. Reuse it entirely
- **Transaction Refactoring Required:** `create_invoice()` currently wraps all logic in `async with session.begin():`. To enable atomic confirm_order, extract a `_create_invoice_core(session, data, tenant_id)` function that contains all logic WITHOUT transaction management. Then update `create_invoice()` to: `async with session.begin(): return await _create_invoice_core(...)`. This lets `confirm_order()` call `_create_invoice_core()` within its own single transaction scope. Existing invoice routes are unaffected since they still call `create_invoice()`
- **FOR UPDATE Locking:** Lock the order row before confirmation to prevent concurrent confirmation attempts [Source: arch — same pattern as supplier order receipt]
- **Immutability:** Once confirmed with an invoice, the order cannot be "un-confirmed" — this is by design

### Critical Implementation Detail — Invoice Creation Call

The existing `create_invoice()` in `domains/invoices/service.py` expects an `InvoiceCreate` Pydantic schema. The exact schema fields are:

```python
from domains.invoices.schemas import InvoiceCreate, InvoiceCreateLine
from domains.invoices.enums import BuyerType
from domains.invoices.tax import TaxPolicyCode

# InvoiceCreateLine fields: product_id (UUID|None), product_code (str|None),
#   description (str), quantity (Decimal), unit_price (Decimal), tax_policy_code (TaxPolicyCode)
# InvoiceCreate fields: customer_id (UUID), buyer_type (BuyerType), buyer_identifier (str|None),
#   invoice_date (date|None), currency_code (str, default="TWD"), lines (list[InvoiceCreateLine])

invoice_input = InvoiceCreate(
    customer_id=order.customer_id,
    invoice_date=date.today(),
    buyer_type=BuyerType.B2B,
    buyer_identifier=customer.normalized_business_number,  # Taiwan business number from Customer
    lines=[
        InvoiceCreateLine(
            product_id=line.product_id,
            description=line.description,
            quantity=line.quantity,
            unit_price=line.unit_price,
            tax_policy_code=TaxPolicyCode(line.tax_policy_code),
        )
        for line in order.lines
    ],
)
```

The invoice service will recalculate tax via `calculate_line_amounts()` internally — the amounts should match the order line amounts since the same policy_code and inputs are used.

### Invoice Model Change

- Adding `order_id` to Invoice is a backward-compatible change
- Existing invoices (created without orders) will have `order_id = NULL`
- Use `TYPE_CHECKING` import for Order model in Invoice to avoid circular imports (same pattern as Invoice ↔ Customer)

### Dependencies

- **Depends on Story 5.1:** Order model, services, routes must exist
- **Modifies invoices domain:** Adds order_id to Invoice model + new migration
- **Reuses:** `domains.invoices.service.create_invoice()`, `domains.invoices.tax.*`

### Key Conventions

- Tab indentation, `from __future__ import annotations`
- `async with session.begin():` for atomic transactions
- `with_for_update()` for row locking
- Audit log pattern: `AuditLog(tenant_id=..., actor_id=str(actor_id), action="ORDER_STATUS_CHANGED", entity_type="order", entity_id=str(order.id), ...)` — note actor_id is String(100), not UUID
- 409 Conflict for state violations, 422 for validation errors, 404 for not found

### Project Structure Notes

**Backend (new files):**
- `migrations/versions/jj000ll00m32_add_invoice_order_id.py`
- `backend/tests/test_order_confirmation.py`

**Backend (modified files):**
- `backend/domains/invoices/models.py` — add order_id field
- `backend/domains/orders/services.py` — add confirm_order()
- `backend/domains/orders/routes.py` — add PATCH /status endpoint
- `backend/domains/orders/schemas.py` — add OrderStatusUpdate schema

**Frontend (new files):**
- `src/domain/orders/hooks/useOrderStatus.ts`

**Frontend (modified files):**
- `src/domain/orders/components/OrderDetail.tsx` — confirm button + dialog

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Epic 5, Story 5.4]
- [Source: backend/domains/invoices/service.py — create_invoice() function]
- [Source: backend/domains/invoices/schemas.py — InvoiceCreate, InvoiceCreateLine schemas]
- [Source: backend/domains/invoices/models.py — Invoice model for order_id addition]
- [Source: backend/domains/inventory/services.py — receive_supplier_order() for atomic transaction + FOR UPDATE pattern]

---

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
