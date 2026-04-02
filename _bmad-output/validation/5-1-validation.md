# Story 5.1 Validation Report: Create Order Linked to Customer

**Story:** `5-1-create-order-linked-to-customer.md`
**Iteration:** 4-pass validation complete
**Date:** 2026-04-01

---

## CRITICAL Issues (Will Break Implementation)

### CRITICAL-1: Migration Chain Creates Branching Head — Not Linear

**Issue:** The story specifies migration `ii999kk99l21_create_orders_tables.py` with revision chain `hh888jj88k10 → new`. However, `hh888jj88k10` already EXISTS as the current head of the linear migration chain (`aa111dd11c43 → ... → gg777ii77j09 → hh888jj88k10`).

**Evidence:**
```
migrations/versions/aa111dd11c43_initial.py
migrations/versions/bb222ee22d54_create_customers_table.py
migrations/versions/cc333ff33e65_customer_search_indexes.py
migrations/versions/dd444ff44f76_create_inventory_tables.py
migrations/versions/ee555gg55h87_product_code_trgm_index.py
migrations/versions/ee5b6cc6d7e8_create_invoice_tables.py
migrations/versions/ff666hh66i98_add_invoice_void_fields.py
migrations/versions/gg777ii77j09_convert_tenant_id_to_uuid.py
migrations/versions/hh888jj88k10_create_invoice_artifacts.py  ← HEAD OF MAIN CHAIN
```

Using `hh888jj88k10` as the `down_revision` for the orders migration creates a **branch** in Alembic terms (diamond merge), not a linear sequence. The story describes it as `hh888jj88k10 → new` which is accurate for a parent-child relationship but fails to mention this creates a branching scenario.

**Impact:** `alembic upgrade head` will NOT apply the orders migration automatically. A developer must either:
- Manually specify the orders migration branch after upgrading the main branch, OR
- Use `alembic merge` to create a merge migration joining both branches

**Recommendation:** The story must explicitly state this is a branching migration and that the dev should either (a) use `--branch=orders` when stamping the initial orders migration, or (b) coordinate with whoever is working on the main branch to decide the merge strategy. Alternatively, the orders migration could be placed AFTER the current head using the next logical sequential ID.

---

### CRITICAL-2: `actor_type` Not Explicitly Set on AuditLog — Inconsistent with Invoice Pattern

**Issue:** The `AuditLog` model has `actor_type: Mapped[str] = mapped_column(String(20), nullable=False, default="user")`. The story's Task 4 implementation of `create_order()` creates an audit log entry but does NOT specify `actor_type`.

**Evidence:**
- Inventory services (`create_supplier_order`, `transfer_stock`, etc.): AuditLog created WITHOUT `actor_type`, relying on DB default `"user"`
- Invoice service (`void_invoice`): AuditLog created WITH explicit `actor_type="user"` (line 290 of `service.py`)
- Story Task 4: No mention of `actor_type` in the audit log creation step

**Impact:** While the code will work (DB default applies), this is inconsistent with the explicit pattern in invoices and the architecture requirement AR10 that audit logs capture `actor_type`. The story should follow the invoice service pattern and explicitly pass `actor_type="user"` or `actor_type="system"` for MVP.

**Recommendation:** Add `actor_type="user"` to the AuditLog constructor call in the `create_order()` implementation, matching the invoice service pattern.

---

### CRITICAL-3: Order Number Uniqueness — No Retry/Collision Handling Described

**Issue:** AC2 states "the order number is unique per tenant" and the migration has a unique constraint `uq_orders_tenant_order_number` on `(tenant_id, order_number)`. The order number format is `ORD-{YYYYMMDD}-{8-HEX}`. The story says "retry on collision (extremely unlikely with 4 billion combinations per day)" but provides no implementation guidance.

**Evidence:**
- `create_supplier_order()` in inventory services generates `PO-{date}-{uuid.uuid4().hex[:8].upper()}` — NO uniqueness check or retry
- Story: "Generate hex from `uuid.uuid4().hex[:8].upper()`" — no retry logic described
- Story: "Unique constraint + retry on collision" — mentions retry but no implementation

**Impact:** In the extremely unlikely event of a collision (1 in 4 billion per day), the unique constraint violation would cause an unhandled DB exception, returning a 500 error to the client. While unlikely, a production system should implement the promised retry logic.

**Recommendation:** Add explicit retry logic (up to 3 attempts with different UUIDs) in `create_order()` service, catching `IntegrityError` on the unique constraint and regenerating.

---

## WARNINGS (Potential Issues)

### WARNING-1: `actor_id` Value Inconsistency with Inventory Pattern

**Issue:** The story says `ACTOR_ID = str(DEFAULT_TENANT_ID)` for the actor_id field. However, the inventory domain uses `ACTOR_ID = "system"` (a literal string), not a UUID-based string.

**Evidence:**
- `backend/domains/inventory/routes.py` line 67: `ACTOR_ID = "system"`
- Story Task 4: `ACTOR_ID = str(DEFAULT_TENANT_ID)` → produces `"00000000-0000-0000-0000-000000000001"`

Both approaches are technically valid since `AuditLog.actor_id` is `String(100)`. However, this is an inconsistency within the same codebase that could confuse future maintainers. The story's approach (using tenant UUID string) is arguably MORE correct for audit traceability since it identifies the tenant, whereas "system" is generic.

**Recommendation:** This is acceptable but should be documented as a deliberate choice. A follow-up story should standardize `actor_id` conventions across all domains.

---

### WARNING-2: Test File Location Ambiguity

**Issue:** The story specifies `backend/tests/test_orders_api.py` as the test file path. However, existing backend tests are organized as:
- `backend/tests/api/test_create_invoice.py` (API-level httpx tests)
- `backend/tests/domains/inventory/test_supplier_orders.py` (domain-level API tests)

**Evidence:** The existing supplier order tests at `backend/tests/domains/inventory/test_supplier_orders.py` test API endpoints using httpx AsyncClient. An order API test could reasonably live in either location.

**Recommendation:** Use `backend/tests/api/test_orders.py` to match the `backend/tests/api/` pattern used by other API tests (test_create_invoice.py, test_create_customer.py, etc.), or `backend/tests/domains/orders/test_orders.py` to match the supplier order tests. Clarify which location is preferred.

---

### WARNING-3: `invoice_id` Partial Unique Constraint — Partial Index May Not Be Portable

**Issue:** The migration task specifies `Unique constraint: uq_orders_tenant_invoice_id on (tenant_id, invoice_id) WHERE invoice_id IS NOT NULL`. PostgreSQL supports `WHERE` clauses on unique constraints to create partial unique indexes, but this syntax is PostgreSQL-specific.

**Evidence:**
- `CREATE INDEX ... WHERE invoice_id IS NOT NULL` is valid PostgreSQL
- Other migrations in this project use standard PostgreSQL constraints (no MySQL/MSSQL migrations found)
- The gg777 migration converts tenant_id to UUID with pure PostgreSQL syntax

**Impact:** If the project ever needs to support a different database backend, this constraint would need rewriting. Given this is a PostgreSQL-only project currently, this is LOW risk.

**Recommendation:** Acceptable for MVP. Add a comment in the migration noting this is PostgreSQL-specific.

---

### WARNING-4: Supplier Order Hex Case Mismatch

**Issue:** The story references `create_supplier_order()` in inventory services as the pattern for order number generation. That function uses lowercase hex: `uuid.uuid4().hex[:8].upper()`. However, the story's example shows uppercase: `ORD-20260401-A3F1B9C2`.

**Evidence:**
- `backend/domains/inventory/services.py` line 781: `uuid.uuid4().hex[:8].upper()` — explicitly uppercase
- Story AC2 example: `ORD-20260401-A3F1B9C2` — uppercase

Both are uppercase, so they match. But the supplier order pattern uses `.upper()` explicitly, which is correct.

**Status:** No actual issue — confirmed the hex is uppercased in both cases. ✅

---

## CONFIRMED VALID

### VALID-1: `ii999kk99l21` Migration ID — No Conflict

**Finding:** The migration ID `ii999kk99l21` does not exist in `migrations/versions/`. It is available for use. ✅

### VALID-2: `backend/common/models/order.py` and `backend/common/models/order_line.py` Location Pattern

**Finding:** The `backend/common/models/` directory exists with models: `audit_log.py`, `inventory_stock.py`, `product.py`, `reorder_alert.py`, `stock_adjustment.py`, `stock_transfer.py`, `supplier.py`, `supplier_order.py`, `warehouse.py`. The story correctly places Order and OrderLine in `common/models/` following the established pattern. ✅

### VALID-3: `domains.invoices.tax.calculate_line_amounts()` Function Exists with Correct Signature

**Finding:** The function at `backend/domains/invoices/tax.py` exists with the exact signature the story describes:
```python
def calculate_line_amounts(
    *,
    quantity: Decimal,
    unit_price: Decimal,
    policy_code: TaxPolicyCode,
) -> InvoiceLineAmounts:
```
Returns `InvoiceLineAmounts` dataclass with: `subtotal`, `tax_amount`, `total_amount`, `tax_type` (int), `tax_rate` (Decimal), `zero_tax_rate_reason`. ✅

### VALID-4: `AuditLog` Model — `actor_id` is `String(100)` ✅

**Finding:** `backend/common/models/audit_log.py` line 24: `actor_id: Mapped[str] = mapped_column(String(100), nullable=False)`. The story's approach of casting `DEFAULT_TENANT_ID` UUID to string with `str(DEFAULT_TENANT_ID)` produces a 36-character UUID string, well within the 100-character limit. ✅

### VALID-5: `DEFAULT_TENANT_ID` Constant Exists ✅

**Finding:** `backend/common/tenant.py` line 15: `DEFAULT_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")`. Used consistently throughout the codebase in inventory, invoices, and customers domains. ✅

### VALID-6: Route Pattern — FastAPI Router with `/api/v1/` Prefix ✅

**Finding:** `backend/app/main.py` creates an `api_v1 = APIRouter(prefix="/api/v1")` and includes domain routers with prefixes like `"/customers"`, `"/invoices"`, `"/inventory"`. The story specifies `POST /api/v1/orders`, `GET /api/v1/orders`, `GET /api/v1/orders/{order_id}` — this follows the exact established pattern. ✅

### VALID-7: Pydantic Schema Pattern ✅

**Finding:** `backend/domains/invoices/schemas.py` uses `model_config = ConfigDict(from_attributes=True)` on response schemas. The inventory schemas use the same pattern. The story explicitly requires this pattern. ✅

### VALID-8: `FakeAsyncSession` Test Pattern ✅

**Finding:** Multiple test files use `FakeAsyncSession` pattern:
- `backend/tests/api/test_create_invoice.py` — line 29
- `backend/tests/api/test_create_customer.py` — line 30
- `backend/tests/domains/inventory/test_supplier_orders.py` — line 145
- `backend/tests/domains/inventory/test_product_detail.py` — line 106

The pattern is well-established with `begin()`, `add()`, `flush()`, `execute()` methods. ✅

### VALID-9: `TaxPolicyCode` StrEnum — Correct Values ✅

**Finding:** `backend/domains/invoices/tax.py` defines:
```python
class TaxPolicyCode(StrEnum):
    STANDARD = "standard"
    ZERO = "zero"
    EXEMPT = "exempt"
    SPECIAL = "special"
```
Matches exactly what the story's migration task describes for `tax_policy_code` values. ✅

### VALID-10: `customer_id` FK — Customer Model Has No `default_payment_terms` ✅

**Finding:** `backend/domains/customers/models.py` has `credit_limit: Mapped[Decimal]` but NO `default_payment_terms` field. The Dev Notes in the story correctly state "Customer model has `credit_limit` field but no `default_payment_terms` — do NOT add it in this story". ✅

### VALID-11: `product` Table Name (FK Reference) ✅

**Finding:** The `Product` model has `__tablename__ = "product"`. The migration task references `product.id` in the FK constraint — this is correct. The story says `product.id` (using the SQL convention of `table.column`), not `products.id`. ✅

### VALID-12: Decimal Field Precisions Match Existing Patterns ✅

**Finding:**
- `Numeric(20, 2)` for amounts: matches `Invoice.subtotal_amount`, `Invoice.tax_amount`, `Invoice.total_amount`
- `Numeric(18, 3)` for quantities: matches `InvoiceLine.quantity`
- `Numeric(6, 4)` for tax rates: matches `InvoiceLine.tax_rate`
- `String(100)` for created_by: matches `SupplierOrder.created_by`

All decimal precisions and string lengths match existing models exactly. ✅

### VALID-13: `async with session.begin()` Pattern ✅

**Finding:** `backend/domains/customers/service.py` and `backend/domains/invoices/service.py` use `async with session.begin():` for atomic transactions. The story requires this pattern for `create_order()`. This pattern exists in the codebase and works correctly. ✅

### VALID-14: `uuid.uuid4().hex[:8].upper()` Supplier Order Pattern ✅

**Finding:** `backend/domains/inventory/services.py` line 781: `f"PO-{datetime.now(tz=UTC).strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"`. The order number pattern `ORD-{YYYYMMDD}-{8-CHAR-HEX}` with `uuid.uuid4().hex[:8].upper()` is a direct analog and correctly described in the story. ✅

### VALID-15: `OrderStatus` Default "pending" ✅

**Finding:** The migration task specifies `status (String(20), NOT NULL, default "pending")`. This is the same default pattern used by `SupplierOrderStatus.PENDING` in the supplier order model. ✅

---

## Web Search Findings

### Tax Calculation Best Practices for Order APIs

**General Finding:** The story's approach of centralizing tax calculation in a backend module (`domains.invoices.tax`) and having the frontend submit only policy codes is the recommended pattern. This avoids:
- Client-side tax calculation errors
- Jurisdictional tax complexity leaks to the frontend
- Duplicated tax logic across order/invoice domains

The approach of computing `subtotal = qty * unit_price`, `tax = subtotal * tax_rate`, `total = subtotal + tax` in a centralized module with `Decimal` precision (not float) is the industry-standard approach for financial calculations.

**Relevance to Story:** The story correctly delegates tax calculation to `domains.invoices.tax.calculate_line_amounts()` with `Decimal` arithmetic. This is sound.

### Order Number Generation

**General Finding:** Date-prefixed order numbers with UUID-based uniqueness suffixes are a common pattern. The `ORD-{date}-{hex}` format with 8-character hex from UUID provides 4,294,967,296 combinations per day, making collisions functionally impossible even in high-volume scenarios.

**Relevance to Story:** The story's approach is industry-standard and appropriate. The unique constraint + rare retry approach is acceptable for MVP.

---

## Iteration Summary

| Iteration | Focus | Key Finding |
|-----------|-------|-------------|
| 1 | Read story, explore codebase, web search | Confirmed no existing order model, migration chain issue identified |
| 2 | Deep-dive flagged issues, cross-ref patterns | actor_type inconsistency, uniqueness handling, actor_id pattern |
| 3 | Verify external references (IDs, paths, functions) | All file paths valid, all function signatures match, tax calculation confirmed |
| 4 | Final consistency pass | Migration branching confirmed as CRITICAL; all other items validated |

---

## Overall Assessment

**Story is ~85% ready for implementation.** The core technical patterns (models, schemas, services, routes, tax calculation, audit logging) are correctly described and verified against the codebase. The migration branching issue (CRITICAL-1) must be resolved before implementation — the story must either acknowledge this is a branching migration or the dev must be told to use Alembic branching. The `actor_type` omission (CRITICAL-2) is an easy fix in the implementation task. The collision retry (CRITICAL-3) is low probability but should be implemented per the story's own acknowledgment.

**No fundamental architectural issues found.** The story correctly follows the modular monolith pattern, reuses existing tax infrastructure, and maintains consistency with established domain patterns.
