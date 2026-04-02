# Story 5.1: Create Order Linked to Customer

**Status:** ready-for-dev

**Story ID:** 5.1

---

## Story

As a sales rep,
I want to create an order linked to an existing customer,
So that I can track sales and generate invoices.

---

## Acceptance Criteria

**AC1:** Order creation with customer link
**Given** a customer exists in the system
**When** I create a new order and select the customer
**Then** the order is saved with the customer_id FK
**And** the order status defaults to "pending"

**AC2:** Unique order number generation
**Given** I create a new order
**When** the order is saved
**Then** the system assigns a unique order number formatted as `ORD-{YYYYMMDD}-{hex}` (same pattern as supplier orders: `PO-{date}-{hex}`)
**And** the order number is unique per tenant

**AC3:** Payment terms defaulting
**Given** the selected customer exists
**When** I create the order without specifying payment terms
**Then** payment terms default to "NET_30" (MVP hardcoded default, customer-level defaults deferred)

**AC4:** Payment terms override
**Given** I'm creating an order
**When** I specify payment terms (NET_30, NET_60, COD)
**Then** the specified terms are recorded on the order

**AC5:** Order with line items
**Given** I'm creating an order
**When** I add line items with product_id, quantity, unit_price, and tax_policy_code
**Then** each line's tax is calculated by calling `calculate_line_amounts(quantity=, unit_price=, policy_code=)` from `domains.invoices.tax`
**And** the returned tax_type, tax_rate, tax_amount, subtotal, and total are stored on each OrderLine
**And** order-level subtotal_amount, tax_amount, and total_amount are aggregated from all lines

**AC6:** Validation rules
**Given** I submit an order creation request
**When** customer_id is missing or invalid, or line items are empty
**Then** the system returns 422 with field-level validation errors

**AC7:** Order list and detail
**Given** orders exist
**When** I request the order list with optional filters (status, customer_id)
**Then** paginated results are returned
**And** I can fetch a single order by ID with full line items

**AC8:** Audit logging
**Given** an order is created
**When** the transaction commits
**Then** an audit_log entry is created with action "ORDER_CREATED", after_state containing order data

---

## Tasks / Subtasks

- [ ] **Task 1: Alembic Migration — Orders Tables** (AC1-AC2, AC5)
  - [ ] Create migration `ii999kk99l21_create_orders_tables.py` with revision chain `hh888jj88k10` → new
  - [ ] `orders` table: id (UUID PK), tenant_id (UUID, NOT NULL, indexed), customer_id (UUID FK → customers.id ON DELETE RESTRICT), order_number (String(50), NOT NULL), status (String(20), NOT NULL, default "pending"), payment_terms_code (String(20), NOT NULL, default "NET_30"), payment_terms_days (Integer, NOT NULL, default 30), subtotal_amount (Numeric(20,2)), tax_amount (Numeric(20,2)), total_amount (Numeric(20,2)), invoice_id (UUID FK → invoices.id, nullable), notes (Text, nullable), created_by (String(100), NOT NULL — matches SupplierOrder/AuditLog pattern), created_at (DateTime(tz), NOT NULL), updated_at (DateTime(tz), NOT NULL), confirmed_at (DateTime(tz), nullable)
  - [ ] `order_lines` table: id (UUID PK), tenant_id (UUID, NOT NULL), order_id (UUID FK → orders.id ON DELETE CASCADE), product_id (UUID FK → product.id ON DELETE RESTRICT), line_number (Integer, NOT NULL), quantity (Numeric(18,3), NOT NULL, CHECK > 0), unit_price (Numeric(20,2), NOT NULL, CHECK >= 0), tax_policy_code (String(20), NOT NULL — stored for reference, one of: standard/zero/exempt/special), tax_type (Integer, NOT NULL — computed from policy), tax_rate (Numeric(6,4), NOT NULL — computed from policy), tax_amount (Numeric(20,2), NOT NULL — computed from policy), subtotal_amount (Numeric(20,2), NOT NULL — qty * unit_price), total_amount (Numeric(20,2), NOT NULL — subtotal + tax), description (String(500), NOT NULL), available_stock_snapshot (Integer, nullable), backorder_note (String(255), nullable), created_at (DateTime(tz), NOT NULL)
  - [ ] Unique constraint: `uq_orders_tenant_order_number` on (tenant_id, order_number)
  - [ ] Unique constraint: `uq_orders_tenant_invoice_id` on (tenant_id, invoice_id) WHERE invoice_id IS NOT NULL — each invoice links to at most one order per tenant
  - [ ] Indexes: ix_orders_tenant_created (tenant_id, created_at DESC), ix_orders_tenant_status (tenant_id, status), ix_orders_customer_id (customer_id), ix_order_lines_order_id (order_id)
  - [ ] Use `UUID(as_uuid=True)` for tenant_id to match gg777 migration pattern (NOT String(50))

- [ ] **Task 2: Order & OrderLine Models** (AC1-AC2, AC5)
  - [ ] Create `backend/common/models/order.py` with Order model
  - [ ] Create `backend/common/models/order_line.py` with OrderLine model
  - [ ] Follow Product model pattern: `UUID(as_uuid=True)` for UUIDs, `DateTime(timezone=True)` for timestamps
  - [ ] Order → OrderLine relationship with cascade="all, delete-orphan", order_by="OrderLine.line_number"
  - [ ] Order → Customer relationship (lazy load, no back_populates needed for MVP)
  - [ ] Register models in `backend/common/models/__init__.py`

- [ ] **Task 3: Orders Domain Structure** (AC1-AC8)
  - [ ] Create `backend/domains/orders/__init__.py`
  - [ ] Create `backend/domains/orders/schemas.py` — OrderCreate, OrderCreateLine, OrderResponse, OrderLineResponse, OrderListResponse, PaymentTermsCode enum (NET_30, NET_60, COD)
  - [ ] Create `backend/domains/orders/services.py` — create_order(), list_orders(), get_order()
  - [ ] Create `backend/domains/orders/routes.py` — POST /api/v1/orders, GET /api/v1/orders, GET /api/v1/orders/{order_id}
  - [ ] Register router in `backend/app/main.py`

- [ ] **Task 4: Order Service Implementation** (AC1-AC6, AC8)
  - [ ] `create_order()`: validate customer exists, validate line items (≥1, qty > 0, unit_price ≥ 0), generate order number (`ORD-{date}-{8-HEX}`), calculate tax per line using `calculate_line_amounts(quantity=line.quantity, unit_price=line.unit_price, policy_code=line.tax_policy_code)` from `domains.invoices.tax` — store returned tax_type, tax_rate, tax_amount, subtotal, total on each OrderLine, aggregate totals on Order, create audit_log entry
  - [ ] Use `async with session.begin():` for atomic transaction
- Hardcode `TENANT_ID = DEFAULT_TENANT_ID` for MVP. For actor_id, use `ACTOR_ID = str(DEFAULT_TENANT_ID)` since AuditLog.actor_id is String(100)
  - [ ] `list_orders()`: paginated query with optional status/customer_id filters, ordered by created_at DESC
  - [ ] `get_order()`: fetch with selectinload(Order.lines), selectinload(Order.customer), raise 404 if not found

- [ ] **Task 5: Frontend — Order Creation Form** (AC1-AC5)
  - [ ] Create `src/domain/orders/` directory structure matching inventory pattern
  - [ ] `src/domain/orders/types.ts` — Order, OrderLine, OrderCreate, PaymentTermsCode interfaces
  - [ ] `src/domain/orders/api/orders.ts` — createOrder(), listOrders(), getOrder() API functions
  - [ ] `src/domain/orders/hooks/useOrders.ts` — useOrders() hook for list, useCreateOrder() for creation
  - [ ] `src/domain/orders/components/OrderForm.tsx` — customer selector (reuse customer search), line item rows with product search, payment terms dropdown, quantity/price inputs, running total display
  - [ ] `src/domain/orders/components/OrderList.tsx` — paginated list with status filter, link to detail
  - [ ] `src/domain/orders/components/OrderDetail.tsx` — read-only view with line items, customer info, status badge

- [ ] **Task 6: Backend Tests** (AC1-AC8)
  - [ ] `backend/tests/test_orders_api.py` — test order creation (happy path, missing customer, empty lines, invalid quantities), list with filters, detail view, order number uniqueness, audit log creation
  - [ ] Follow existing FakeAsyncSession pattern from inventory tests
  - [ ] Test validation error responses (422 with field-level errors)

- [ ] **Task 7: Frontend Tests** (AC1, AC5, AC7)
  - [ ] `src/domain/orders/__tests__/OrderForm.test.tsx` — renders form, submits order, shows validation errors
  - [ ] `src/domain/orders/__tests__/OrderList.test.tsx` — renders list, applies filters

---

## Dev Notes

### Architecture Compliance

- **Domain Pattern:** Follow existing modular monolith — orders is a new domain under `backend/domains/orders/` with its own routes, services, schemas [Source: arch AR6]
- **Models in common/models/:** Order and OrderLine models go in `backend/common/models/` following Product, Warehouse, Supplier pattern — NOT in domains/orders/models.py
- **Tax Calculation:** REUSE `domains.invoices.tax.calculate_line_amounts()` — DO NOT reinvent tax logic. The function signature is `calculate_line_amounts(*, quantity: Decimal, unit_price: Decimal, policy_code: TaxPolicyCode) -> InvoiceLineAmounts`. It returns a dataclass with: subtotal, tax_amount, total_amount, tax_type (int), tax_rate (Decimal), zero_tax_rate_reason. TaxPolicyCode is a StrEnum: standard, zero, exempt, special
- **Invoice Model:** Currently has NO order_id field. Story 5.4 will add it via separate migration. DO NOT modify Invoice model in this story
- **Audit Log:** Use existing `common.models.audit_log.AuditLog` model — same pattern as inventory services. Note: `actor_id` is `String(100)`, so cast UUID to string: `actor_id=str(actor_id)`. Fields: entity_type (String(100)), entity_id (String(100) — use `str(order.id)`), action (String(100)), before_state/after_state (JSON dict), correlation_id (String(100), optional)
- **Error Pattern:** Use `HTTPException` (not JSONResponse) for error responses — matching inventory routes pattern (Epic 4), NOT customers pattern (Epic 3)
- **Tenant ID:** Use `UUID(as_uuid=True)` for tenant_id columns — the gg777 migration standardized all tenant_ids to UUID. Do NOT use String(50)

### Key Conventions

- Tab indentation (enforced by ruff)
- `from __future__ import annotations` at top of every Python file
- `DEFAULT_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")` hardcoded for MVP
- Decimal fields: `Numeric(20, 2)` for amounts, `Numeric(18, 3)` for quantities, `Numeric(6, 4)` for tax rates
- Pydantic schemas use `model_config = ConfigDict(from_attributes=True)`
- Test files use `@pytest.fixture` with `FakeAsyncSession` for unit tests

### Payment Terms — MVP Scope

- Hardcode 3 payment terms: NET_30 (30 days), NET_60 (60 days), COD (0 days)
- Use Python Enum, no lookup table needed for MVP
- Default to NET_30 if not specified on order creation
- Customer model has `credit_limit` field but no `default_payment_terms` — do NOT add it in this story

### Order Number Generation

- Format: `ORD-{YYYYMMDD}-{8-CHAR-HEX}` (uppercase) — e.g., `ORD-20260401-A3F1B9C2`
- Same pattern as supplier order: `PO-{date}-{hex}` in `domains.inventory.services.create_supplier_order()` which uses `uuid.uuid4().hex[:8].upper()`
- Generate hex from `uuid.uuid4().hex[:8].upper()`
- Unique constraint + retry on collision (extremely unlikely with 4 billion combinations per day)

### Product Price Note

- Product model has NO sale_price field — unit_price must be provided per order line item
- This matches InvoiceLine pattern where unit_price is per-line

### Project Structure Notes

**Backend (new files):**
- `backend/common/models/order.py`
- `backend/common/models/order_line.py`
- `backend/domains/orders/__init__.py`
- `backend/domains/orders/schemas.py`
- `backend/domains/orders/services.py`
- `backend/domains/orders/routes.py`
- `backend/tests/test_orders_api.py`
- `migrations/versions/ii999kk99l21_create_orders_tables.py`

**Frontend (new files):**
- `src/domain/orders/types.ts`
- `src/domain/orders/api/orders.ts`
- `src/domain/orders/hooks/useOrders.ts`
- `src/domain/orders/components/OrderForm.tsx`
- `src/domain/orders/components/OrderList.tsx`
- `src/domain/orders/components/OrderDetail.tsx`
- `src/domain/orders/__tests__/OrderForm.test.tsx`
- `src/domain/orders/__tests__/OrderList.test.tsx`

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Epic 5, Story 5.1]
- [Source: backend/domains/inventory/services.py — create_supplier_order() for order number pattern]
- [Source: backend/domains/invoices/tax.py — calculate_line_amounts() for tax reuse]
- [Source: backend/common/models/product.py — Product model pattern]
- [Source: backend/domains/invoices/models.py — Invoice/InvoiceLine model pattern]
- [Source: migrations/versions/gg777ii77j09 — tenant_id UUID standardization]

---

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
