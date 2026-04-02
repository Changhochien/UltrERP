# Story 5.4 Validation Report

**Story:** Auto-Generate Invoice from Confirmed Order
**Story ID:** 5.4
**Iteration:** 4-pass complete
**Date:** 2026-04-01

---

## CRITICAL ISSUES (will break implementation)

### C1: Nested `session.begin()` — Transaction Conflict

**Location:** Task 3, `confirm_order()` service function

**Problem:** `create_invoice()` in `domains/invoices/service.py:125` uses `async with session.begin():` internally. The story specifies `confirm_order()` should wrap ALL operations including the `create_invoice()` call within `async with session.begin():` (Task 3, line "All within `async with session.begin():` for atomicity").

This creates a nested transaction scenario. SQLAlchemy 2.0's `AsyncSession` does not support nested `begin()` calls — calling `session.begin()` when already inside a transaction raises `InvalidRequestError: A transaction is already begun on this Session`.

**Evidence:**
- `create_invoice()` at `backend/domains/invoices/service.py:125`: `async with session.begin():`
- Story Task 3 step 11: "All within `async with session.begin():` for atomicity"
- `receive_supplier_order()` at `backend/domains/inventory/services.py:960-1118` does NOT use `session.begin()` wrapper — it runs without an outer transaction context, relying on the route handler to manage the session

**Fix Required:** The `confirm_order()` function should NOT wrap its operations in `async with session.begin():`. Instead, the route handler that calls `confirm_order()` should manage the transaction. Alternatively, refactor `create_invoice()` to accept an optional `auto_commit=False` parameter and not call `session.begin()` internally when called from within an existing transaction.

**Web Search Finding:** SQLAlchemy 2.0 removed subtransaction behavior. Calling `session.begin()` inside an existing transaction raises `InvalidRequestError`. The correct pattern is to use `session.begin_nested()` for savepoints when nesting is needed, or to have only the outermost caller use `session.begin()`.

---

### C2: Orders Domain Does Not Exist

**Location:** Story dependencies, Task 3

**Problem:** The story references `backend/domains/orders/services.py`, `backend/domains/orders/routes.py`, and `backend/domains/orders/schemas.py` as existing files, but the `backend/domains/orders/` directory does not exist. Story 5.1 (which creates the orders domain) is marked "ready-for-dev" but is not yet implemented.

The `Order` and `OrderLine` models do not exist in `backend/common/models/`. Story 5.1's migration (`ii999kk99l21_create_orders_tables.py`) has not been created.

**Impact:** `confirm_order()` cannot be implemented until Story 5.1 is complete. This story is not independently implementable.

**Fix:** Story 5.1 must be completed first.

---

### C3: Invoice Model Missing `order_id` Field

**Location:** Task 2, Invoice model

**Problem:** The story says "Add `order_id: Mapped[uuid.UUID | None]` to Invoice model in `backend/domains/invoices/models.py`" as Task 2. The current `Invoice` model at `backend/domains/invoices/models.py` does NOT have an `order_id` field. This field must be added by this story's migration.

This is expected — the story is responsible for adding it. However, the Dev Notes (line 174-176) state "Adding `order_id` to Invoice is a backward-compatible change" and "Use `TYPE_CHECKING` import for Order model in Invoice to avoid circular imports". These are accurate guidance IF the Order model existed.

**Status:** Field will be added by this story's migration. Not a blocking issue — the story correctly identifies the change needed.

---

### C4: `buyer_type` Mapping from Customer — Field Does Not Exist

**Location:** Dev Notes, Critical Implementation Detail section

**Problem:** The story's code example shows:
```python
buyer_type=BuyerType.B2B,  # BuyerType from customer
buyer_identifier=customer.normalized_business_number,
```

The comment says "BuyerType from customer" but the `Customer` model (`backend/domains/customers/models.py`) has NO `buyer_type` field. The Customer model only has: `company_name`, `normalized_business_number`, `billing_address`, `contact_name`, `contact_phone`, `contact_email`, `credit_limit`, `status`.

**Fix:** The story should default `buyer_type=BuyerType.B2B` hardcoded (Taiwan B2B invoices require business number), OR the Customer model needs a `buyer_type` field added (separate story). The current story cannot correctly map `customer.buyer_type` because that field does not exist.

---

## WARNINGS (potential issues)

### W1: Story 5.1 `invoice_id` on Order vs Story 5.4 `order_id` on Invoice — Dual FK Direction

**Location:** AC2, Story 5.1 Task 1 migration spec

**Observation:** Story 5.1 migration spec (line 70) defines `orders` table with `invoice_id (UUID FK → invoices.id, nullable)`. Story 5.4 adds `order_id (UUID FK → orders.id)` to the `invoices` table. This creates a bidirectional FK relationship.

The unique constraint in Story 5.1: `uq_orders_tenant_invoice_id on (tenant_id, invoice_id) WHERE invoice_id IS NOT NULL` ensures each invoice links to at most one order per tenant.

This is architecturally valid but requires careful migration ordering (orders table must exist before invoices can FK to it). No actual conflict.

---

### W2: `async with session.begin():` in Story 5.1 vs Story 5.4

**Location:** Story 5.1 Task 4, Story 5.4 Task 3

**Observation:** Story 5.1 specifies `create_order()` uses `async with session.begin():` (Story 5.1, Task 4). Story 5.4 specifies `confirm_order()` also uses `async with session.begin():`.

When the PATCH `/orders/{order_id}/status` route is called for "confirmed" transition:
1. It calls `confirm_order()` which has its own `async with session.begin():`
2. `confirm_order()` calls `create_invoice()` which ALSO has `async with session.begin():`
3. This is the nested transaction issue (C1 above)

The correct pattern (as seen in `receive_supplier_order()`) is for the service function to NOT use `session.begin()` — the route handler uses `async with session.begin():` as the outermost wrapper.

**Fix:** Story 5.4 Task 3 should follow the `receive_supplier_order()` pattern: service function has NO outer `session.begin()`, the route handler provides the transaction boundary.

---

### W3: `TaxPolicyCode` Construction from OrderLine String

**Location:** Dev Notes, line 163

**Observation:** Story 5.1 stores `tax_policy_code` on `OrderLine` as `String(20)` (the actual string value like "standard", not the enum). Story 5.4 maps `TaxPolicyCode(line.tax_policy_code)`.

`TaxPolicyCode` is a `StrEnum` with values `STANDARD = "standard"`, `ZERO = "zero"`, etc. Constructing via `TaxPolicyCode("standard")` works due to StrEnum semantics.

**Status:** Confirmed functional. No change needed.

---

### W4: Frontend Files Not Created Yet

**Location:** Tasks 5, 7

**Observation:** The story references `src/domain/orders/components/OrderDetail.tsx`, `src/domain/orders/hooks/useOrderStatus.ts`, and `src/domain/orders/__tests__/OrderDetail.test.tsx`. The `src/domain/orders/` directory does not exist. Story 5.1 creates this directory structure.

**Status:** Expected — both stories depend on the same frontend scaffold. No conflict.

---

### W5: `Actor_id` Type in AuditLog

**Observation:** Story 5.4 Audit Log spec uses `actor_id=str(actor_id)`. The `AuditLog` model has `actor_id: Mapped[str] = mapped_column(String(100), nullable=False)`. The story is correct to cast UUID to string. The Dev Notes (line 189) correctly note this.

**Status:** Confirmed correct.

---

## CONFIRMED VALID

### V1: `create_invoice()` Function Exists and Signature Confirmed

**Location:** `backend/domains/invoices/service.py:107-203`

```python
async def create_invoice(
    session: AsyncSession,
    data: InvoiceCreate,
    tenant_id: uuid.UUID | None = None,
) -> Invoice:
```

**Verification:** Function exists with exact signature. Handles invoice number allocation, tax calculation via `calculate_line_amounts()`, line amount computation, audit logging internally, and returns `Invoice` with `domain_events = [DomainEvent(name="InvoiceIssued")]`.

---

### V2: `InvoiceCreate` Schema Confirmed

**Location:** `backend/domains/invoices/schemas.py:24-30`

```python
class InvoiceCreate(BaseModel):
    customer_id: uuid.UUID
    buyer_type: BuyerType
    buyer_identifier: str | None = Field(default=None, max_length=20)
    invoice_date: date | None = None
    currency_code: str = Field(default="TWD", min_length=3, max_length=3)
    lines: list[InvoiceCreateLine]
```

**Verification:** All fields match story's usage. `buyer_type` accepts `BuyerType` enum (which is a `StrEnum`). `invoice_date` defaults to None (service fills with today).

---

### V3: `InvoiceCreateLine` Schema Confirmed

**Location:** `backend/domains/invoices/schemas.py:15-21`

```python
class InvoiceCreateLine(BaseModel):
    product_id: uuid.UUID | None = None
    product_code: str | None = Field(default=None, max_length=100)
    description: str = Field(..., min_length=1, max_length=500)
    quantity: Decimal
    unit_price: Decimal
    tax_policy_code: TaxPolicyCode
```

**Verification:** All fields match story's mapping. `tax_policy_code: TaxPolicyCode` accepts the StrEnum.

---

### V4: `BuyerType` Enum Confirmed

**Location:** `backend/domains/invoices/enums.py:8-10`

```python
class BuyerType(StrEnum):
    B2B = "b2b"
    B2C = "b2c"
```

**Verification:** Exists with `B2B` and `B2C` values. `StrEnum` allows construction from lowercase string values.

---

### V5: `TaxPolicyCode` Enum Confirmed

**Location:** `backend/domains/invoices/tax.py:18-22`

```python
class TaxPolicyCode(StrEnum):
    STANDARD = "standard"
    ZERO = "zero"
    EXEMPT = "exempt"
    SPECIAL = "special"
```

**Verification:** Exists with all four values used in the system. `StrEnum` allows construction from matching strings.

---

### V6: `TaxPolicyCode` Tax Calculation Confirmed

**Location:** `backend/domains/invoices/tax.py:77-95`

`calculate_line_amounts(quantity=, unit_price=, policy_code=)` returns `InvoiceLineAmounts` dataclass with `subtotal`, `tax_amount`, `total_amount`, `tax_type`, `tax_rate`, `zero_tax_rate_reason`.

**Verification:** Confirmed reusable. Story 5.1 also uses this same function for order line tax calculation.

---

### V7: `with_for_update()` Pattern Confirmed

**Location:** `backend/domains/inventory/services.py:993` (`receive_supplier_order`)

```python
order_stmt = (
    select(SupplierOrder)
    .options(selectinload(SupplierOrder.lines))
    .where(...)
    .with_for_update()
)
```

**Verification:** Pattern is well-established. Story 5.4's use of `with_for_update()` for `confirm_order()` matches this pattern exactly.

---

### V8: `selectinload(Order.lines)` Pattern Confirmed

**Observation:** `receive_supplier_order()` uses `.options(selectinload(SupplierOrder.lines))`. The story's `confirm_order()` specification uses `selectinload(Order.lines)`. This is a standard SQLAlchemy eager loading pattern.

**Verification:** Pattern is correct for the intended use.

---

### V9: `AuditLog` Model Confirmed

**Location:** `backend/common/models/audit_log.py`

```python
class AuditLog(Base):
    tenant_id: Mapped[uuid.UUID]
    actor_id: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[str]
    entity_type: Mapped[str]
    entity_id: Mapped[str]
    before_state: Mapped[dict | None] = mapped_column(JSON)
    after_state: Mapped[dict | None] = mapped_column(JSON)
    correlation_id: Mapped[str | None]
    notes: Mapped[str | None]
```

**Verification:** All fields used in the story's audit log spec exist with correct types. `actor_id` is `String(100)` as noted in the story.

---

### V10: `customer.normalized_business_number` Confirmed

**Location:** `backend/domains/customers/models.py:24`

```python
normalized_business_number: Mapped[str] = mapped_column(String(8), nullable=False)
```

**Verification:** Field exists with correct type.

---

### V11: Migration ID `jj000ll00m32` — No Conflict

**Observation:** Existing migrations use format `aa111dd11c43`, `bb222ee22d54`, `cc333ff33e65`, `dd444ff44f76`, `ee555gg55h87`, `ee5b6cc6d7e8`, `ff666hh66i98`, `gg777ii77j09`, `hh888jj88k10`. The proposed ID `jj000ll00m32` follows the same alphanumeric pattern and does not conflict with any existing migration ID. The story correctly chains from `hh888jj88k10` (the last existing migration). Story 5.1 chains from the same base with ID `ii999kk99l21`.

**Verification:** No conflict. `jj000ll00m32` > `ii999kk99l21` in sort order.

---

### V12: `receive_supplier_order()` as Reference Pattern

**Location:** `backend/domains/inventory/services.py:960-1118`

The story cites this as the reference pattern for atomic transaction + FOR UPDATE. Key observations:
- Does NOT use `async with session.begin()` wrapper — the route handler manages the session
- Uses `with_for_update()` for locking
- Performs multiple operations atomically (locks, stock updates, adjustments, audit logs, status updates)
- Uses `selectinload()` for eager loading lines

**Verification:** This is the correct architectural pattern. The story's `confirm_order()` should follow the same approach (no `session.begin()` in the service, route handler provides the transaction boundary).

---

### V13: Story 5.5 Depends on Story 5.4

**Observation:** Story 5.5 specifies that the "pending → confirmed" transition "MUST delegate to `confirm_order()`" from Story 5.4. Story 5.4's Task 4 creates `PATCH /api/v1/orders/{order_id}/status` which Story 5.5 extends. The stories are correctly sequenced.

---

## WEB SEARCH FINDINGS

### Order-to-Invoice Automation Best Practices

**Source:** Industry best practices for Order-to-Cash (O2C) automation

1. **Atomicity is critical**: Order confirmation and invoice creation must be atomic — a failure in invoice generation should roll back the order confirmation. This matches AC4 (atomic transaction with rollback).

2. **Idempotency guards**: Prevents duplicate invoice creation from retried confirmations. The story's AC5 check for existing `invoice_id` implements this correctly.

3. **Tax calculation consistency**: Using the same tax engine for both order and invoice ensures totals match. The story correctly reuses `domains.invoices.tax` for this.

4. **Cross-domain service composition**: In modular monoliths, direct service-to-service calls (not HTTP) are the standard pattern for atomic cross-domain operations. The story's approach of calling `create_invoice()` directly from `confirm_order()` is architecturally correct for this pattern.

### SQLAlchemy Nested Transaction Issue

**Source:** SQLAlchemy GitHub Discussions, SQLAlchemy 2.0 Documentation

**Key Finding:** SQLAlchemy 2.0 removed subtransaction behavior. Calling `session.begin()` when already inside a transaction raises `InvalidRequestError`. This directly impacts Story 5.4's design.

**Recommended Pattern:**
- Service functions should NOT call `session.begin()` — they should be called within a transaction context managed by the caller (typically the route handler)
- If nesting is required, use `session.begin_nested()` for savepoints
- The `receive_supplier_order()` function correctly follows this pattern (no `session.begin()` in the service)

**Implication for Story 5.4:** The `confirm_order()` function should NOT wrap its logic in `async with session.begin():`. The route handler that calls `confirm_order()` should provide the transaction boundary. Alternatively, `create_invoice()` should be refactored to not call `session.begin()` when called from within an existing transaction.

---

## SUMMARY

| Category | Count |
|----------|-------|
| Critical Issues | 4 |
| Warnings | 5 |
| Confirmed Valid | 13 |

**Top Priority Fix:** C1 (nested transaction) and C4 (`buyer_type` mapping) must be resolved before implementation. C2 (orders domain not existing) is a prerequisite — Story 5.1 must be completed first.

The story is well-researched and architecturally sound in most respects, but the nested `session.begin()` issue and the missing `buyer_type` on Customer are blocking issues.
