# Story 5.3 Validation Report: Set Payment Terms on Order

**Story:** 5.3-set-payment-terms.md
**Iteration:** 4-pass complete
**Date:** 2026-04-01

---

## CRITICAL Issues (will break implementation)

### C1: Wrong `ReasonCode` enum reference in story
**Location:** Dev Notes, "same pattern as `ReasonCode` enum in inventory"

The story states:
> `PaymentTermsCode` should be defined alongside schemas in `domains/orders/schemas.py` (same pattern as `ReasonCode` enum in inventory)

**Finding:** `ReasonCode` is NOT in `backend/domains/inventory/schemas.py`. That file only has:
- `USER_SELECTABLE_REASON_CODES = ["received", "damaged", ...]` (plain list constant, not an enum)
- `ReasonCodeItem(BaseModel)` (a Pydantic schema model, not an enum)

The actual `ReasonCode` enum is at:
- `backend/common/models/stock_adjustment.py` — `class ReasonCode(str, enum.Enum)` with member values like `RECEIVED = "received"`

**Impact:** The story's enum reference is incorrect. A developer following this reference would look in the wrong file and not find the enum pattern.

**Resolution needed:** Update the reference to point to `backend/common/models/stock_adjustment.py` for the `ReasonCode` enum pattern.

---

### C2: Order immutability claim contradicts Story 5.5
**Location:** AC4 and Dev Notes

The story states:
> **AC4:** Payment terms immutability — "orders are immutable after creation, matching invoice pattern (NFR21)"

**Finding:** This is factually incorrect. NFR21 (per `prd.md` and `epics.md`) applies to **invoice records only**: "All invoice records immutable after creation (void only, no edits)."

Story 5.5 (Update Order Status, same Epic 5) explicitly models orders as **mutable** through a state machine with allowed transitions (pending → confirmed → shipped → fulfilled, and pending → cancelled). Story 5.5's AC1-AC4 define a full status update mechanism, and AC3 explicitly handles cancellation as a status change.

The payment terms fields specifically cannot be changed, but the order record itself is NOT immutable — only the `payment_terms_code` and `payment_terms_days` fields are locked after creation.

**Impact:** AC4's acceptance criteria is wrong. It says "I try to change the payment terms" and expects the entire order to be protected, but what the story actually needs to enforce is field-level immutability for `payment_terms_code` and `payment_terms_days` specifically — not record-level immutability like invoices.

**Resolution needed:** Reword AC4 to specify "payment_terms_code and payment_terms_days fields cannot be changed after order creation" rather than "orders are immutable after creation."

---

### C3: Story 5.1 code does not exist — "already scaffolded" claim is false
**Location:** Task 2, "This is already scaffolded in Story 5.1's OrderCreate schema and create_order() service"

**Finding:** The orders domain has **no implementation whatsoever**:
- `backend/domains/orders/` does not exist
- `backend/common/models/order.py` does not exist
- `backend/common/models/order_line.py` does not exist
- No migration for orders tables exists in `migrations/versions/`
- `backend/tests/test_orders_api.py` does not exist

The Story 5.1 spec file exists, but no code was implemented. There is no `create_order()` service and no `OrderCreate` schema with `payment_terms_code` field.

**Impact:** Task 2's subtasks cannot be done as described. A developer would need to create the entire orders domain first, then add payment terms. The story should clarify the dependency chain.

**Resolution needed:** The story should note it depends on Story 5.1 being implemented first, and that Task 2 actually includes building the orders domain infrastructure.

---

### C4: `TaxPolicyCode` in order_lines is an cross-domain reference problem
**Location:** Story 5.1 migration spec (referenced by Story 5.3)

The migration in Story 5.1 specifies `tax_policy_code (String(20), NOT NULL)` on order_lines, referencing the same `TaxPolicyCode` from `domains/invoices/tax.py`.

**Finding:** This is a cross-domain import dependency. The order domain would need to import `TaxPolicyCode` from the invoices domain. While this works in Python, it creates a tight coupling. The story does not acknowledge this dependency.

**Resolution needed:** The story should explicitly note the cross-domain import of `TaxPolicyCode` from `domains.invoices.tax`.

---

## WARNINGS (potential issues)

### W1: `str, Enum` vs `StrEnum` — inconsistent with existing pattern
**Location:** Task 1, enum definition

The story specifies:
```python
class PaymentTermsCode(str, Enum):
    NET_30 = "NET_30"
```

**Finding:** The existing codebase uses `StrEnum` (Python 3.11+) for all enum-like types:
- `backend/domains/invoices/enums.py`: `class BuyerType(StrEnum)`, `class InvoiceStatus(StrEnum)`
- `backend/domains/invoices/tax.py`: `class TaxPolicyCode(StrEnum)`

The alternative `str, Enum` pattern does work for Pydantic v2 serialization (values serialize as plain strings), but it is inconsistent with the established project pattern.

**Additionally:** Story 5.5's Dev Notes also specify `class OrderStatus(str, Enum)`, so this pattern IS used in the codebase for enums that aren't in the dedicated enums module.

**Assessment:** Lower severity — both patterns work with Pydantic v2, but `StrEnum` is cleaner. The story should align with existing `domains/invoices/enums.py` pattern and create a `domains/orders/enums.py` module.

---

### W2: `payment_terms_days` derivation vs database column
**Location:** Task 1 and Story 5.1 migration

The story says `payment_terms_days` is "derived from the code, not independently settable."

**Finding:** Story 5.1's migration defines `payment_terms_days` as a separate INTEGER column with `default 30`. The story's statement about it being derived conflicts with the database schema where it's a stored column.

**Assessment:** Both approaches work. If `payment_terms_days` is stored as a column, the service layer populates it from `PAYMENT_TERMS_CONFIG[code].days` at creation time. This is acceptable but the story should clarify this is application-level derivation at create time, not a computed column or virtual field.

---

### W3: Frontend `OrderForm.tsx` does not exist yet
**Location:** Task 3, references `OrderForm.tsx (from Story 5.1)`

**Finding:** No `src/domain/orders/components/OrderForm.tsx` exists. Story 5.3 describes Task 3 as modifying this file, but it was never created (Story 5.1 has no implementation).

**Assessment:** The story can still describe the changes needed, but the dev agent will need to create the file, not modify it. This is a minor documentation issue.

---

### W4: Order number format inconsistency between Story 5.1 and Story 5.3
**Location:** Task 4, backend tests path

**Finding:** Story 5.1 specifies the order number format as `ORD-{YYYYMMDD}-{hex}`, but Story 5.3's Dev Notes references the same format. Story 5.3 does not add new information but references Story 5.1. This is fine but the story should clearly cross-reference rather than duplicate.

---

### W5: Client-side vs server-side dropdown — story is ambiguous
**Location:** Task 3

The story says "can be client-side constants matching backend, or fetched from /payment-terms endpoint."

**Assessment:** Both approaches are valid for MVP. The story should pick one or clarify that both are acceptable. The `StockAdjustmentForm.tsx` pattern (fetched from backend) is more aligned with the existing codebase pattern.

---

## CONFIRMED VALID

### V1: `StrEnum`-compatible Pydantic serialization works
**Pattern verified at:** `backend/domains/invoices/enums.py`, `backend/domains/invoices/tax.py`

Both `StrEnum`-based and `str, Enum`-based enums serialize correctly in Pydantic v2. JSON output is the string value (e.g., `"NET_30"`), not the enum member name. This is confirmed by examining how `BuyerType` and `TaxPolicyCode` are used in schema fields and validated.

**Verdict:** The enum pattern will work for Pydantic serialization regardless of whether `StrEnum` or `str, Enum` is used.

---

### V2: `PAYMENT_TERMS_CONFIG` dict pattern is valid
**Pattern reference:** `backend/domains/invoices/tax.py` — `_POLICIES: dict[TaxPolicyCode, TaxPolicy]`

The story's `PAYMENT_TERMS_CONFIG` dict mapping code → { label, days } is a direct, valid analog to the existing `_POLICIES` pattern. This is a confirmed project convention.

---

### V3: Frontend dropdown pattern is confirmed
**Pattern reference:** `src/domain/inventory/components/StockAdjustmentForm.tsx`

The `<select>` + `<option>` pattern with `value={item.value}` and `{item.label}` display is the established pattern in this codebase. The payment terms dropdown in `OrderForm.tsx` should follow the same pattern, using `useReasonCodes()` style hook or client-side constants.

---

### V4: `payment_terms_code` column exists in Story 5.1 migration spec
**Verified at:** Story 5.1 Task 1 migration spec

The `orders` table migration includes:
```
payment_terms_code (String(20), NOT NULL, default "NET_30")
payment_terms_days (Integer, NOT NULL, default 30)
```

This confirms the payment terms fields are planned in the database schema from Story 5.1.

---

### V5: `GET /payment-terms` endpoint pattern is confirmed
**Pattern reference:** `backend/domains/inventory/routes.py` — `GET /reason-codes`

The pattern of returning a list response (`ReasonCodeListResponse` with `items: list[ReasonCodeItem]`) is established. The payment terms endpoint should follow the same pattern with a `PaymentTermsListResponse`.

---

### V6: `OrderStatus(str, Enum)` pattern confirmed in Story 5.5
**Verified at:** Story 5.5 Task 1

Story 5.5 explicitly uses `class OrderStatus(str, Enum)` in the schemas.py. This confirms the `str, Enum` pattern is acceptable for domain enums in this project, even though `StrEnum` is used in the dedicated `enums.py` modules.

---

### V7: Backend test file pattern confirmed
**Pattern reference:** `backend/tests/domains/inventory/test_stock_adjustment.py`

The `FakeAsyncSession` pattern, `@pytest.fixture` approach, and error response testing patterns (422 with field-level errors) are established in the project. The test file `backend/tests/test_orders_api.py` follows the same pattern when created.

---

### V8: Frontend types.ts pattern confirmed
**Pattern reference:** `src/domain/inventory/types.ts`, `src/domain/invoices/types.ts`

The `PaymentTermsCode` type can be defined as a TypeScript union type:
```typescript
export type PaymentTermsCode = "NET_30" | "NET_60" | "COD";
```
This mirrors how `SupplierOrderStatus` is defined in `inventory/types.ts` as a union type rather than an enum.

---

## Web Search Findings

### Payment Terms Best Practices in Order/Invoice Systems

1. **Payment terms are standard business practice**: NET 30, NET 60, COD are universally recognized terms. The three options in this story (NET_30, NET_60, COD) cover the most common B2B scenarios.

2. **Enum vs Literal type**: For a fixed, small set of payment terms (MVP), a TypeScript union type or string enum is appropriate. Since payment terms rarely change in the short term, hardcoding client-side is acceptable for MVP.

3. **Immutability**: Payment terms on an order should be immutable after creation to prevent billing disputes. This is a standard accounting practice — once terms are agreed upon, they should not change. This validates the intent of AC4 (field-level immutability), even though the scope (entire order vs. just payment_terms fields) is wrong in the story.

4. **Payment terms inheritance**: Best practice is for invoices to inherit payment terms from orders. The AC3 in Story 5.3 correctly identifies this pattern, with implementation in Story 5.4.

5. **Days derivation**: Deriving `payment_terms_days` from the code is correct — it prevents inconsistency between code and days (e.g., saying NET_30 but storing 60 days).

---

## Iteration Summary

| Iteration | Focus | Key Finding |
|----------|-------|-------------|
| 1 | Story reading + codebase enum exploration | Found C1 (wrong ReasonCode reference), confirmed V1-V8 patterns |
| 2 | Deep-dive on flagged issues | Found C2 (order immutability contradiction), C3 (no Story 5.1 code) |
| 3 | External references verification | Confirmed C4 (cross-domain TaxPolicyCode), W1-W5 |
| 4 | Final consistency pass | Web search confirms business logic intent of AC4 is correct but scope is wrong |

---

## Recommended Priority for Dev Agent

1. **Fix C2 first**: Clarify that orders ARE mutable (per Story 5.5) and payment terms fields are what is locked
2. **Fix C1**: Update ReasonCode reference to `common/models/stock_adjustment.py`
3. **Fix C3**: Acknowledge Story 5.1 must be implemented first; this story's Tasks 2 depends on it
4. **Address W1**: Use `StrEnum` in a new `domains/orders/enums.py` module, consistent with `domains/invoices/enums.py`
5. **Proceed with V1-V8**: All other patterns are confirmed correct
