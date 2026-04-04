# Story 6.1: Record Payment Against Invoice

Status: ready-for-dev

## Story

As a finance clerk,
I want to record payments against invoices,
So that we track what's been paid and reduce outstanding balances.

## Acceptance Criteria

**AC1:** Record payment with required fields
**Given** an invoice exists with an outstanding balance > 0
**When** I record a payment providing: amount, payment_method, payment_date, and optionally reference_number and notes
**Then** the payment is saved and linked to the invoice
**And** the payment gets a unique auto-generated payment reference (format: `PAY-YYYYMMDD-NNNN`)
**And** the response includes the payment details and updated invoice balance

**AC2:** Reduce invoice outstanding balance
**Given** a payment is recorded against an invoice
**When** the payment is saved
**Then** the invoice's computed outstanding balance = `total_amount - SUM(all payment amounts for this invoice)`
**And** if outstanding balance reaches 0, invoice status transitions from "issued" to "paid"
**And** partial payments leave the invoice status as "issued"

**AC3:** Overpayment prevention
**Given** an invoice has outstanding balance X
**When** I attempt to record payment with amount > X
**Then** the system returns 422 Unprocessable Entity with message "Payment amount exceeds outstanding balance"
**And** no payment is created

**AC4:** Voided invoice guard
**Given** an invoice has status "voided"
**When** I attempt to record a payment
**Then** the system returns 409 Conflict with message "Cannot record payment against voided invoice"

**AC5:** Already-paid invoice guard
**Given** an invoice has outstanding balance = 0 (already fully paid)
**When** I attempt to record a payment
**Then** the system returns 409 Conflict with message "Invoice is already fully paid"

**AC6:** Audit logging
**Given** a payment is recorded
**When** the transaction commits
**Then** an audit_log entry is created with:
  - action: "PAYMENT_RECORDED"
  - entity_type: "payment"
  - entity_id: payment.id
  - after_state: `{ "amount": X, "method": "...", "invoice_id": "..." }`
  - actor_id, correlation_id

**AC7:** List payments for an invoice
**Given** payments exist for an invoice
**When** I request the payments list for that invoice
**Then** I see all payments sorted by payment_date descending
**And** each shows: reference, amount, method, date, created_by

**AC8:** List all payments with pagination
**Given** payments exist in the system
**When** I request the payments list (with optional customer_id or date range filters)
**Then** I see paginated results with total count
**And** results are sorted by payment_date descending

**AC9:** Payment recording UI
**Given** I view an invoice detail with outstanding balance > 0
**When** I click "Record Payment"
**Then** a form appears with: amount (pre-filled with outstanding), method dropdown, date (default today), reference number, notes
**And** after submission, the invoice detail refreshes showing updated balance

**AC10:** Payment methods
**Given** I record a payment
**When** I select a payment method
**Then** available methods are: CASH, BANK_TRANSFER, CHECK, CREDIT_CARD, OTHER

## Tasks / Subtasks

- [ ] **Task 1: Alembic Migration — Payments Table** (AC1, AC10)
  - [ ] Create migration `kk111mm11n43_create_payments_table.py` chaining from `jj000ll00m32`
  - [ ] Create `payments` table:
    ```sql
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid()
    tenant_id       UUID NOT NULL (indexed)
    invoice_id      UUID FK → invoices.id ON DELETE RESTRICT  -- NULLABLE: NULL for unmatched payments (Story 6.2)
    customer_id     UUID NOT NULL FK → customers.id ON DELETE RESTRICT
    payment_ref     VARCHAR(20) NOT NULL
    amount          NUMERIC(20,2) NOT NULL
    payment_method  VARCHAR(20) NOT NULL
    payment_date    DATE NOT NULL
    reference_number VARCHAR(100)   -- bank ref, check number, etc.
    notes           TEXT
    created_by      VARCHAR(100) NOT NULL
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
    ```
  - [ ] Add indexes:
    - `uq_payments_tenant_payment_ref` UNIQUE (tenant_id, payment_ref)
    - `ix_payments_tenant_invoice` (tenant_id, invoice_id)
    - `ix_payments_tenant_customer` (tenant_id, customer_id)
    - `ix_payments_tenant_date` (tenant_id, payment_date)

- [ ] **Task 2: Payment Domain — Model** (AC1)
  - [ ] Create `backend/domains/payments/__init__.py`
  - [ ] Create `backend/domains/payments/models.py` with `Payment` ORM model
  - [ ] Follow existing patterns from `domains/invoices/models.py` and `domains/customers/models.py`:
    - Use `Uuid` from `sqlalchemy` for id columns (NOT `UUID(as_uuid=True)` — that's only in `common/models/`; domain models use `Uuid`)
    - Import: `from sqlalchemy import ... Uuid`
    - Use `server_default=func.now()` for timestamps
    - Use `mapped_column` with explicit types
    - Include `tenant_id` with index
  - [ ] Add relationship: `invoice: Mapped[Invoice] = relationship()` (lazy load)
  - [ ] Add relationship: `customer: Mapped[Customer] = relationship()` (lazy load)

- [ ] **Task 3: Payment Domain — Schemas** (AC1, AC7, AC8, AC10)
  - [ ] Create `backend/domains/payments/schemas.py`
  - [ ] Define `PaymentMethod(str, enum.Enum)`: CASH, BANK_TRANSFER, CHECK, CREDIT_CARD, OTHER
  - [ ] Define `PaymentCreate(BaseModel)`:
    - invoice_id: uuid.UUID
    - amount: Decimal (gt=0)
    - payment_method: PaymentMethod
    - payment_date: date | None = None (defaults to today)
    - reference_number: str | None = Field(default=None, max_length=100)
    - notes: str | None = Field(default=None, max_length=500)
  - [ ] Define `PaymentResponse(BaseModel)` with `ConfigDict(from_attributes=True)`:
    - id, tenant_id, invoice_id, customer_id, payment_ref, amount, payment_method, payment_date, reference_number, notes, created_by, created_at, updated_at
  - [ ] Define `PaymentListItem(BaseModel)` — lighter version for list view
  - [ ] Define `PaymentListResponse(BaseModel)`: items, total, page, page_size

- [ ] **Task 4: Payment Domain — Service** (AC1-AC6)
  - [ ] Create `backend/domains/payments/services.py`
  - [ ] Implement `record_payment(session, tenant_id, data: PaymentCreate, actor_id: str) -> Payment`:
    - Call `await set_tenant(session, tid)` first
    - Within `async with session.begin():`
    - Fetch invoice with `with_for_update()` for locking
    - Validate invoice exists and belongs to tenant
    - Validate invoice status != "voided" (AC4)
    - Compute current outstanding: `invoice.total_amount - SUM(existing payments)`
      - Query: `select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.invoice_id == invoice.id, Payment.tenant_id == tid)`
    - Validate outstanding > 0 (AC5)
    - Validate data.amount <= outstanding (AC3)
    - Generate payment_ref: `PAY-{date.today():%Y%m%d}-{sequential}`
      - Sequential: query max payment_ref for tenant+date, increment
    - Create Payment record
    - If new outstanding == 0: update invoice.status = "paid", invoice.updated_at
    - Create AuditLog entry (AC6)
    - Return payment
  - [ ] Implement `list_payments(session, tenant_id, invoice_id=None, customer_id=None, page=1, page_size=20) -> tuple[list[Payment], int]`:
    - Call `await set_tenant(session, tid)` first
    - Build query with optional filters
    - Return paginated results + total count
  - [ ] Implement `get_payment(session, tenant_id, payment_id) -> Payment | None`

- [ ] **Task 5: Payment Domain — Routes** (AC1, AC7, AC8)
  - [ ] Create `backend/domains/payments/routes.py`
  - [ ] Create sub-app with `router = APIRouter()`
  - [ ] POST `/` — record_payment endpoint
    - Accept `PaymentCreate` body
    - actor_id from request context (hardcode "system" for MVP)
    - Return `PaymentResponse` with status 201
  - [ ] GET `/` — list_payments endpoint
    - Query params: invoice_id, customer_id, page, page_size
    - Return `PaymentListResponse`
  - [ ] GET `/{payment_id}` — get_payment endpoint
    - Return `PaymentResponse` or 404
  - [ ] Mount in `backend/app/main.py` inside `create_app()`:
    ```python
    from domains.payments.routes import router as payments_router
    # Add alongside other include_router calls on api_v1:
    api_v1.include_router(payments_router, prefix="/payments", tags=["payments"])
    ```
    **NOTE:** Project uses `api_v1 = APIRouter(prefix="/api/v1")` then `api_v1.include_router(...)` with domain prefix only (e.g. `"/payments"`, NOT `"/api/v1/payments"`). Final: `app.include_router(api_v1)` adds the `/api/v1` prefix. Follow the exact pattern of customers, invoices, orders routers.

- [ ] **Task 6: Frontend — Types & API** (AC9, AC10)
  - [ ] Create `src/domain/payments/types.ts`:
    - `PaymentMethod` enum: CASH, BANK_TRANSFER, CHECK, CREDIT_CARD, OTHER
    - `Payment` interface matching `PaymentResponse`
    - `PaymentListResponse` interface
    - `PaymentCreate` interface
  - [ ] Create `src/lib/api/payments.ts`:
    - `fetchPayments(params)` — GET with filters
    - `fetchPaymentsByInvoice(invoiceId)` — GET filtered by invoice_id
    - `createPayment(data: PaymentCreate)` — POST
  - [ ] Create `src/domain/payments/hooks/usePayments.ts`:
    - `usePayments(filters)` — list hook with pagination
    - `useCreatePayment()` — mutation hook with optimistic update

- [ ] **Task 7: Frontend — Record Payment Form** (AC9, AC10)
  - [ ] Create `src/domain/payments/components/RecordPaymentForm.tsx`:
    - Props: `invoiceId, outstandingBalance, onSuccess, onCancel`
    - Amount field pre-filled with outstanding balance
    - PaymentMethod dropdown
    - Date picker defaulting to today
    - Reference number (optional text)
    - Notes (optional textarea)
    - Submit button with loading state
    - Validation: amount > 0, amount <= outstanding
  - [ ] Integrate into invoice detail view:
    - Add "Record Payment" button when outstanding > 0
    - Show modal/dialog with RecordPaymentForm
    - Refresh invoice detail on success

- [ ] **Task 8: Frontend — Payment History** (AC7)
  - [ ] Create `src/domain/payments/components/PaymentHistory.tsx`:
    - Props: `invoiceId`
    - Displays payment table: ref, amount, method, date, created_by
    - Sorted by date descending
  - [ ] Embed in invoice detail view below invoice lines

- [ ] **Task 9: Backend Tests** (AC1-AC6)
  - [ ] Create `backend/tests/domains/payments/test_payments_api.py`
  - [ ] Follow existing test patterns from `test_orders_api.py`:
    - Use `FakeAsyncSession` with `queue_scalar` / `queue_result`
    - Queue `set_tenant` scalar(None) before each service call
    - Test: record payment happy path
    - Test: partial payment (amount < outstanding)
    - Test: full payment marks invoice as "paid"
    - Test: overpayment returns 422
    - Test: payment against voided invoice returns 409
    - Test: payment against fully paid invoice returns 409
    - Test: list payments with filters
    - Test: list payments for specific invoice
    - Test: get payment by ID / 404

- [ ] **Task 10: Frontend Tests** (AC9)
  - [ ] Create `src/domain/payments/__tests__/RecordPaymentForm.test.tsx`
  - [ ] Create `src/domain/payments/__tests__/PaymentHistory.test.tsx`
  - [ ] Test: form renders with pre-filled amount
  - [ ] Test: form validates amount > 0 and <= outstanding
  - [ ] Test: form submits and calls createPayment API
  - [ ] Test: payment history displays list correctly

## Dev Notes

### Architecture Compliance

- **Domain structure:** `backend/domains/payments/` with `__init__.py`, `models.py`, `schemas.py`, `services.py`, `routes.py` — matches architecture §3 pattern
- **API mount:** Uses `api_v1.include_router(payments_router, prefix="/payments", tags=["payments"])` inside `create_app()` — matches all other domain routers (customers, invoices, orders, inventory)
- **tenant_id:** All payment records include tenant_id; `set_tenant(session, tid)` called at start of every service function
- **Transaction pattern:** `async with session.begin():` wrapping all writes; `with_for_update()` locking on invoice read
- **Audit log:** Use `AuditLog` model from `common.models.audit_log` — action="PAYMENT_RECORDED", entity_type="payment"
- **Enum pattern:** `PaymentMethod(str, enum.Enum)` matches `OrderStatus(str, enum.Enum)` pattern
- **Error handling:** Use `from common.errors import ValidationError` for domain validation; HTTP exceptions in routes only

### Invoice Status Transition

- Invoice statuses: "issued", "voided", "paid" (add "paid" as valid status)
- When all payments cover total_amount → auto-transition to "paid"
- "paid" status means outstanding_balance == 0
- Do NOT modify the existing Invoice model directly — compute outstanding balance on the fly from payments
- Consider adding a `status` check in invoice service to handle "paid" status

### Payment Reference Generation

- Format: `PAY-20260401-0001` (PAY-YYYYMMDD-NNNN)
- Daily sequential counter per tenant
- Query: `SELECT MAX(payment_ref) FROM payments WHERE tenant_id = :tid AND payment_ref LIKE 'PAY-{date}-%'`
- If no existing: start at 0001; else parse last 4 digits and increment
- Use `with_for_update()` or appropriate locking to prevent race conditions

### Critical Warnings

- **UUID column type:** Domain models (`domains/*/models.py`) use `Uuid` from `sqlalchemy` (customers, invoices). Common models (`common/models/*.py`) use `UUID(as_uuid=True)` from `sqlalchemy.dialects.postgresql` (orders, stock_adjustment). Since Payment lives in `domains/payments/models.py`, use `Uuid` to match the domain model convention. Import: `from sqlalchemy import ... Uuid`.
- **Do NOT nest `session.begin()` calls** — learned from Story 5.4; if calling another service's function, use the `_core` variant without its own begin
- **invoice_id is NULLABLE in DB** — although Story 6.1 always provides an invoice_id, the column is nullable to support Story 6.2's unmatched payment flow. Enforce `invoice_id` as required in `PaymentCreate` schema (Story 6.1), but make the DB column nullable. Story 6.2 adds `PaymentCreateUnmatched` schema that omits invoice_id.
- **Do NOT create a `payments` domain model in `common/models/`** — only Order and AuditLog are in common/models; domain-specific models go in `backend/domains/{domain}/models.py`. Invoice model is in `domains/invoices/models.py`
- **set_tenant() must be called BEFORE any query** — not inside session.begin() but before begin if no other transaction is active, or at the start of the begin block. Follow the pattern in `domains/orders/services.py`
- **Invoice locking required** — use `with_for_update()` when fetching invoice for payment recording to prevent concurrent overpayment
- **Amount computation precision** — use `Decimal` throughout, `Numeric(20,2)` in DB. Sum query must use `func.coalesce(func.sum(...), Decimal('0'))`

### Project Structure Notes

- Backend: `backend/domains/payments/` — new domain directory to create
- Frontend: `src/domain/payments/` — new domain directory to create
  - `src/domain/payments/types.ts`
  - `src/domain/payments/hooks/usePayments.ts`
  - `src/domain/payments/components/RecordPaymentForm.tsx`
  - `src/domain/payments/components/PaymentHistory.tsx`
  - `src/lib/api/payments.ts`
- Tests backend: `backend/tests/domains/payments/test_payments_api.py`
- Tests frontend: `src/domain/payments/__tests__/`
- Migration: `migrations/versions/kk111mm11n43_create_payments_table.py`

### Previous Story Intelligence (Epic 5)

- **set_tenant pattern:** Every service function calls `await set_tenant(session, tid)` as first line. Tests must queue `session.queue_scalar(None)` for each set_tenant call.
- **Route pattern:** Routes use dependency injection for session via `Depends(get_db)`. Actor_id is hardcoded as "system" in MVP.
- **Test pattern:** Uses `FakeAsyncSession` with deterministic result queuing. Each `session.execute()` or `session.scalar()` call must have a corresponding queued result.
- **Frontend pattern:** Hooks use `useState` + `useEffect` for data fetching; mutation hooks return `{ mutate, isLoading, error }` pattern.
- **Enum consistency:** Use enum values consistently between backend and frontend. Backend `PaymentMethod.CASH.value` → "CASH", frontend `PaymentMethod.CASH` = "CASH".

### References

- [Source: docs/superpowers/specs/2026-03-30-erp-architecture-design-v2.md#5.1] Payment entity: amount, method, reconcile_invoice_id
- [Source: docs/superpowers/specs/2026-03-30-erp-architecture-design-v2.md#6.5] MCP tools: payments.list, payments.get, payments.create, payments.reconcile
- [Source: docs/superpowers/specs/2026-03-30-erp-architecture-design-v2.md#4.4] Domain event: PaymentReceived → Reconcile invoice
- [Source: _bmad-output/planning-artifacts/prd.md#Payments] FR13: Finance clerk can record payments against invoices
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 6] Epic goal and acceptance criteria
- [Source: _bmad-output/planning-artifacts/prd.md#RBAC] Finance role: CRUD on Payments
- [Source: backend/common/models/audit_log.py] AuditLog model fields and patterns
- [Source: backend/domains/orders/services.py] set_tenant, session.begin(), with_for_update() patterns
- [Source: backend/common/models/order.py] UUID(as_uuid=True) column type pattern
- [Source: backend/domains/invoices/models.py] Invoice model with total_amount, status fields

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (via GitHub Copilot)

### Completion Notes List

- Story created with exhaustive architectural analysis and codebase pattern verification
- Web research conducted on ERP payment recording best practices and database schema design
- Context7 library docs consulted for SQLAlchemy async patterns
- Cross-referenced with all Epic 5 story learnings (set_tenant, enum consistency, session.begin() nesting)
