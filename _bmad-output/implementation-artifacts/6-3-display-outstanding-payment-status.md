# Story 6.3: Display Outstanding Payment Status

Status: ready-for-dev

## Story

As a finance clerk,
I want to see outstanding payment status per invoice,
So that I know what customers owe and can follow up on overdue payments.

## Acceptance Criteria

**AC1:** Invoice list shows payment status columns
**Given** invoices exist with various payment states
**When** I view the invoices list
**Then** each invoice shows: total_amount, amount_paid, outstanding_balance
**And** outstanding_balance = total_amount - amount_paid
**And** amount_paid = SUM(matched payments for this invoice)

**AC2:** Sortable by outstanding balance
**Given** invoices are displayed in the list
**When** I click the "Outstanding" column header
**Then** invoices sort by outstanding_balance (ascending or descending toggle)
**And** default sort is outstanding_balance descending (highest owed first)

**AC3:** Overdue invoice highlighting
**Given** an invoice has outstanding_balance > 0
**When** the invoice is past its payment due date
**Then** the invoice row is highlighted in red/warning color
**And** a badge shows "Overdue" next to the status
**And** due date = invoice_date + payment_terms_days (from linked order, or 30 days default)

**AC4:** Payment status filter
**Given** I'm viewing the invoice list
**When** I filter by payment status
**Then** available filters: "All", "Unpaid" (outstanding > 0), "Paid" (outstanding = 0), "Overdue"
**And** the list updates to show only matching invoices

**AC5:** Invoice detail shows payment summary
**Given** I view an invoice detail
**When** the detail loads
**Then** I see a payment summary section:
  - Total Amount: invoice.total_amount
  - Amount Paid: SUM(payments)
  - Outstanding: total - paid
  - Status: "Paid" / "Partially Paid" / "Unpaid" / "Overdue"
  - Due Date: invoice_date + payment_terms_days
  - Days overdue (if applicable)

**AC6:** Backend payment summary endpoint
**Given** a request for invoice with payment summary
**When** the API returns invoice data
**Then** the response includes computed fields:
  - amount_paid: Decimal
  - outstanding_balance: Decimal
  - payment_status: "paid" | "partial" | "unpaid" | "overdue"
  - due_date: date (computed from order's payment_terms_days or default 30)
  - days_overdue: int (0 if not overdue)

**AC7:** Customer outstanding summary
**Given** a customer has multiple invoices
**When** I view the customer detail
**Then** I see total outstanding balance across all invoices
**And** count of overdue invoices

## Tasks / Subtasks

- [ ] **Task 1: Invoice Payment Summary Backend** (AC1, AC5, AC6)
  - [ ] In `backend/domains/invoices/schemas.py`, add `InvoicePaymentSummary`:
    ```python
    class InvoicePaymentSummary(BaseModel):
        amount_paid: Decimal
        outstanding_balance: Decimal
        payment_status: str  # "paid" | "partial" | "unpaid" | "overdue"
        due_date: date | None
        days_overdue: int
    ```
  - [ ] Extend `InvoiceResponse` with optional payment summary fields:
    - `amount_paid: Decimal | None = None`
    - `outstanding_balance: Decimal | None = None`
    - `payment_status: str | None = None`
    - `due_date: date | None = None`
    - `days_overdue: int | None = None`
  - [ ] Add `InvoiceListItem(BaseModel)` — lighter schema for list view (id, invoice_number, customer_id, invoice_date, total_amount, status, amount_paid, outstanding_balance, payment_status, due_date, days_overdue)
  - [ ] Add `InvoiceListResponse(BaseModel)` following existing pattern:
    - `items: list[InvoiceListItem]`
    - `total: int`
    - `page: int`
    - `page_size: int`

- [ ] **Task 2: Payment Summary Service Logic** (AC1, AC3, AC6)
  - [ ] In `backend/domains/invoices/service.py` or a new `backend/domains/payments/services.py` function:
  - [ ] Implement `compute_invoice_payment_summary(session, invoice, payment_terms_days=30) -> dict`:
    - Query: `SELECT COALESCE(SUM(amount), 0) FROM payments WHERE invoice_id = :id AND match_status = 'matched'`
    - Compute outstanding_balance = total_amount - amount_paid
    - Compute due_date:
      - If invoice has a linked order (invoice.order_id): use order.payment_terms_days
      - Else: default 30 days from invoice_date
    - Compute payment_status:
      - If invoice.status == "voided": "voided"
      - If outstanding == 0: "paid"
      - If outstanding > 0 AND today > due_date: "overdue"
      - If outstanding > 0 AND outstanding < total_amount: "partial"
      - Else: "unpaid"
    - Compute days_overdue: max(0, (today - due_date).days) if overdue, else 0

  - [ ] Implement `enrich_invoices_with_payment_status(session, invoices: list[Invoice]) -> list[dict]`:
    - Batch-compute payment sums for all invoice IDs in one query (avoid N+1):
      ```python
      payment_sums = await session.execute(
          select(Payment.invoice_id, func.sum(Payment.amount))
          .where(Payment.invoice_id.in_(invoice_ids), Payment.match_status == 'matched')
          .group_by(Payment.invoice_id)
      )
      ```
    - Build a dict: `{invoice_id: total_paid}` for O(1) lookup
    - For each invoice, compute summary using the aggregated sums
    - Also batch-load linked orders for payment_terms_days if needed

- [ ] **Task 3: Create Invoice List Endpoint** (AC1, AC2, AC4)
  - [ ] **IMPORTANT:** `GET /api/v1/invoices` does NOT exist yet — only POST, GET /{id}, POST /{id}/void, GET /{id}/pdf, PUT /{id} (rejected) exist. This task CREATES the list endpoint.
  - [ ] Add `list_invoices(session, tenant_id, page, page_size, payment_status, sort_by, sort_order)` to `backend/domains/invoices/service.py`
  - [ ] Add `GET ""` route to `backend/domains/invoices/routes.py` — paginated list with payment summary fields
  - [ ] Add query params:
    - `payment_status`: filter by "paid" | "partial" | "unpaid" | "overdue"
    - `sort_by`: allow "outstanding_balance" as sort option (alongside existing sorts)
    - `sort_order`: "asc" | "desc" (default "desc" for outstanding)
  - [ ] **CRITICAL:** Do NOT break existing invoice list contract. New fields should be additive.
  - [ ] For sorting by outstanding_balance: use computed column in SQL:
    ```python
    outstanding_expr = Invoice.total_amount - func.coalesce(
        select(func.sum(Payment.amount))
        .where(Payment.invoice_id == Invoice.id, Payment.match_status == 'matched')
        .correlate(Invoice)
        .scalar_subquery(),
        Decimal('0')
    )
    ```

- [ ] **Task 4: Update Invoice Detail Endpoint** (AC5, AC6)
  - [ ] Modify `GET /api/v1/invoices/{invoice_id}` to include payment summary
  - [ ] Return enriched `InvoiceResponse` with payment fields populated
  - [ ] Include payment_terms_days from linked order (if exists) or default 30

- [ ] **Task 5: Customer Outstanding Summary** (AC7)
  - [ ] Add endpoint or extend customer detail:
    - `GET /api/v1/customers/{customer_id}/outstanding` or include in customer detail
  - [ ] Return:
    ```python
    class CustomerOutstandingSummary(BaseModel):
        total_outstanding: Decimal
        overdue_count: int
        overdue_amount: Decimal
        invoice_count: int
    ```
  - [ ] Query: aggregate outstanding balances across all customer invoices

- [ ] **Task 6: Frontend — Update Invoice List** (AC1, AC2, AC3, AC4)
  - [ ] Modify `src/domain/invoices/components/InvoiceList.tsx` (or equivalent):
    - Add columns: "Paid", "Outstanding"
    - Add "Outstanding" column sort (click header to toggle)
    - Add payment status filter dropdown: All, Unpaid, Paid, Overdue
    - Highlight overdue rows with warning background color
    - Show "Overdue" badge for past-due invoices
  - [ ] Update `src/lib/api/invoices.ts`:
    - Add `payment_status` and `sort_by` query params to fetch function
  - [ ] Update `src/domain/invoices/types.ts`:
    - Extend Invoice type with payment summary fields

- [ ] **Task 7: Frontend — Update Invoice Detail** (AC5)
  - [ ] Modify invoice detail component:
    - Add "Payment Summary" section showing:
      - Total Amount, Amount Paid, Outstanding, Status badge, Due Date
      - Days overdue count if applicable
    - Color-coded status: green (paid), yellow (partial), red (overdue), gray (unpaid)
  - [ ] Integrate with PaymentHistory component from Story 6.1

- [ ] **Task 8: Frontend — Customer Outstanding** (AC7)
  - [ ] Modify customer detail component:
    - Add "Outstanding Balance" summary card
    - Show total outstanding, overdue count, link to filtered invoice list

- [ ] **Task 9: Backend Tests** (AC1-AC7)
  - [ ] Create `backend/tests/domains/payments/test_payment_status.py`
  - [ ] Test: compute_invoice_payment_summary — unpaid invoice
  - [ ] Test: compute_invoice_payment_summary — partially paid
  - [ ] Test: compute_invoice_payment_summary — fully paid
  - [ ] Test: compute_invoice_payment_summary — overdue
  - [ ] Test: invoice list with payment_status filter
  - [ ] Test: invoice list sorted by outstanding_balance
  - [ ] Test: invoice detail includes payment summary
  - [ ] Test: customer outstanding summary aggregation
  - [ ] Test: batch enrichment handles invoices with no payments

- [ ] **Task 10: Frontend Tests** (AC1-AC5)
  - [ ] Test: invoice list shows payment columns
  - [ ] Test: overdue row highlighting
  - [ ] Test: payment status filter works
  - [ ] Test: outstanding sort toggles
  - [ ] Test: invoice detail shows payment summary section

## Dev Notes

### Architecture Compliance

- **Computed fields:** Outstanding balance is NEVER stored — always computed from payments. This follows the single-source-of-truth principle and avoids data drift.
- **Backward compatibility:** Adding payment fields to invoice API response is additive — existing clients unaware of payment fields will still work.
- **Performance:** Batch payment sum computation for list views prevents N+1 queries. For single invoice detail, a single aggregate query suffices.

### Payment Terms and Due Date Logic

- **Due date source chain:**
  1. If invoice has linked order (invoice.order_id → order.payment_terms_days): use that
  2. If customer has default payment terms: use that (future)
  3. Fallback: 30 days from invoice_date
- **Invoice model:** Invoice has `order_id` (nullable FK added in Story 5.4 migration). Use this to join Order and get `payment_terms_days`.
- **Overdue computation:** `is_overdue = today > due_date AND outstanding > 0`

### Invoice Status vs Payment Status

- **Invoice.status** field values: "issued", "voided", "paid" (added in Story 6.1)
  - "issued" = active, may or may not have payments
  - "voided" = cancelled, no further payments
  - "paid" = fully paid (outstanding = 0)
- **payment_status** (computed): "paid", "partial", "unpaid", "overdue"
  - This is a computed display status, NOT stored on the invoice
  - "overdue" combines outstanding > 0 AND past due_date
  - "partial" = has some payments but not fully paid

### Critical Warnings

- **Do NOT add an `outstanding_balance` column to the invoices table** — compute it from payments. Storing it creates a cache invalidation problem.
- **Do NOT modify Invoice.status values beyond "issued"/"voided"/"paid"** — payment_status is
a separate computed concept for display
- **Batch queries for list views** — never compute outstanding per-invoice in a loop. Use a single GROUP BY query across all displayed invoices.
- **Payment terms from order:** The Order model has `payment_terms_days` (int) and `payment_terms_code` (string). Invoice has `order_id` FK. Access via: `invoice.order_id → Order.payment_terms_days`. May need to join through the FK.
- **Voided invoices:** Show "voided" status, outstanding = 0, no overdue highlighting
- **set_tenant required** for all queries in the service layer

### Frontend Design Notes

- **Overdue highlighting:** Use CSS class `row-overdue` with `bg-red-50` or `border-l-4 border-red-500`
- **Status badges:** Use the same badge component pattern as OrderList (statusLabel/statusColor from useOrders)
- **Sort UX:** Column header click toggles asc/desc, active sort column shows arrow indicator
- **Filter persistence:** Payment status filter should persist across page navigation (URL query param)

### Project Structure Notes

- **No new domain directories** — this story modifies existing invoice and customer views
- Modified files:
  - `backend/domains/invoices/schemas.py` — add payment summary fields + list response schema
  - `backend/domains/invoices/service.py` — add enrichment functions + `list_invoices()` (new)
  - `backend/domains/invoices/routes.py` — add `GET ""` list endpoint (new), enrich GET detail response
  - `backend/domains/payments/services.py` — add summary computation
  - `src/domain/invoices/components/InvoiceList.tsx` — add columns, filters, sort
  - `src/domain/invoices/components/InvoiceDetail.tsx` — add payment summary section
  - `src/domain/invoices/types.ts` — extend types
  - `src/lib/api/invoices.ts` — add query params
- New files:
  - `backend/tests/domains/payments/test_payment_status.py`

### Previous Story Intelligence

- **Story 6.1 dependency:** Payment model and match_status field must exist. Outstanding balance computation reuses the same sum query pattern.
- **Story 6.2 dependency:** match_status="matched" filter ensures only confirmed payments count toward outstanding balance. Suggested/unmatched payments are excluded from balance computation.
- **Story 5.4:** Invoice.order_id FK exists (from Story 5.4 migration). This is how we link to Order.payment_terms_days for due date computation.
- **Invoice list pattern:** `GET /api/v1/invoices` does NOT exist yet — this story creates it. Implement following the same `APIRouter()` + `DbSession = Annotated[AsyncSession, Depends(get_db)]` pattern used in existing invoice routes. Include pagination (page/page_size query params), payment_status filter, and sort_by outstanding support.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 6.3] Each invoice shows total, paid, outstanding; sortable; overdue highlighted
- [Source: _bmad-output/planning-artifacts/prd.md#Payments] FR15: System displays outstanding payment status per invoice
- [Source: docs/superpowers/specs/2026-03-30-erp-architecture-design-v2.md#5.1] Payment entity with reconcile_invoice_id
- [Source: backend/domains/invoices/models.py] Invoice model with total_amount, order_id fields
- [Source: backend/common/models/order.py] Order model with payment_terms_days field
- [Source: backend/domains/invoices/schemas.py] InvoiceResponse current structure
- [Source: _bmad-output/implementation-artifacts/5-4-auto-generate-invoice-from-order.md] Invoice.order_id FK migration

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (via GitHub Copilot)

### Completion Notes List

- Story designed with computed-only outstanding balance (no stored cache) to prevent data drift
- Batch query strategy specified to prevent N+1 performance issues in list views
- Payment terms chain documented: order → customer → default 30 days
- Backward-compatible API extension — additive fields only
- Cross-referenced with Story 5.4 (order_id FK) and Story 6.1/6.2 (payment model, match_status)
