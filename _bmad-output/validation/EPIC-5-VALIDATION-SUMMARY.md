# Epic 5 — Multi-Agent Validation Summary

**Date:** 2026-04-01
**Validators:** 5 parallel agents, 4 iterations each
**Stories Validated:** 5.1, 5.2, 5.3, 5.4, 5.5

---

## Cross-Cutting Critical Issues (Affect All Epic 5 Stories)

These issues appear across multiple Epic 5 stories and must be fixed before any story can move to implementation.

---

### 🚨 CRITICAL-1: All Orders Domain Files Are Pure Fiction

**Affects:** Every Epic 5 story

Every story in Epic 5 references `backend/domains/orders/` and `src/domain/orders/` paths that do not exist. The entire orders domain (models, services, routes, schemas, frontend components) has zero implementation. Stories reference each other as dependencies but no story has been coded.

**Evidence:**
- `backend/domains/orders/` — directory does not exist
- `backend/common/models/order.py` — does not exist
- `backend/common/models/order_line.py` — does not exist
- `src/domain/orders/` — does not exist
- `migrations/versions/ii999kk99l21_create_orders_tables.py` — does not exist
- `backend/tests/test_orders_api.py` — does not exist

**Impact:** No Epic 5 story is independently implementable. All are blocked on Story 5.1 creating the foundational orders domain.

**Recommendation:** Epic 5 is blocked on Story 5.1 being implemented first. The story files describe what SHOULD exist, but nothing has been coded.

---

### 🚨 CRITICAL-2: Migration Chain Branching (Story 5.1)

**Location:** Story 5.1, Task 1 — migration `ii999kk99l21_create_orders_tables.py`

The story specifies `down_revision = hh888jj88k10` for the new orders migration. However, `hh888jj88k10` is already the HEAD of the linear migration chain (`aa111dd11c43 → ... → gg777ii77j09 → hh888jj88k10`).

**Impact:** Using `hh888jj88k10` as parent creates an Alembic **branch**, not a linear extension. `alembic upgrade head` will NOT automatically apply the orders migration. Developers must either use `--branch=orders` or perform a merge migration.

**Recommendation:** The story must explicitly acknowledge this is a branching migration and provide Alembic branching instructions, OR use the next sequential ID after `hh888jj88k10`.

---

### 🚨 CRITICAL-3: Nested `session.begin()` Will Crash (Story 5.4)

**Location:** Story 5.4, Task 3 — `confirm_order()` service

Story 5.4 specifies wrapping ALL operations in `async with session.begin():`. But `create_invoice()` at `domains/invoices/service.py:125` ALSO uses `async with session.begin():` internally. SQLAlchemy 2.0 does not support nested transactions — calling `session.begin()` when already in a transaction raises `InvalidRequestError: A transaction is already begun on this Session`.

**Evidence:** `receive_supplier_order()` at `backend/domains/inventory/services.py:960-1118` does NOT use `session.begin()` — the route handler manages the session. This is the correct pattern.

**Recommendation:** `confirm_order()` should NOT use `async with session.begin():`. The route handler that calls it should provide the transaction boundary. Alternatively, `create_invoice()` should accept an `auto_commit=False` parameter.

---

### 🚨 CRITICAL-4: Order Immutability Claim Contradicts Story 5.5 (Story 5.3)

**Location:** Story 5.3, AC4 — "orders are immutable after creation, matching invoice pattern (NFR21)"

This is factually wrong. NFR21 applies to **invoices only**. Story 5.5 (same epic) explicitly defines a full state machine allowing status transitions (pending → confirmed → shipped → fulfilled, plus cancellation). Orders are mutable through their lifecycle — only specific fields like `payment_terms_code` should be locked.

**Recommendation:** Reword AC4 to specify field-level immutability for payment terms fields only, not record-level immutability.

---

### 🚨 CRITICAL-5: `buyer_type` on Customer Does Not Exist (Story 5.4)

**Location:** Story 5.4, Dev Notes — `buyer_type=BuyerType.B2B,  # BuyerType from customer`

The Customer model at `backend/domains/customers/models.py` has NO `buyer_type` field. The story incorrectly assumes it exists and can be mapped directly.

**Recommendation:** Hardcode `buyer_type=BuyerType.B2B` for Taiwan B2B invoices (which require business number). This is the correct default for the Taiwan market.

---

## Per-Story Critical Issues

### Story 5.1: Create Order Linked to Customer

| # | Issue | Severity |
|---|-------|----------|
| C1 | Migration chain branching — `hh888jj88k10` is already HEAD | CRITICAL |
| C2 | `actor_type` not explicitly set on AuditLog (inconsistent with invoice pattern) | CRITICAL |
| C3 | Order number uniqueness — "retry on collision" promised but no implementation guidance | WARNING |
| W1 | `actor_id = str(DEFAULT_TENANT_ID)` vs inventory's `"system"` — inconsistency | WARNING |
| W2 | Test file path ambiguity: `backend/tests/test_orders_api.py` vs existing patterns | WARNING |

**Confirmed Valid (15 items):** Migration ID available, model locations correct, `calculate_line_amounts()` signature matches, `DEFAULT_TENANT_ID` exists, route pattern confirmed, Pydantic schema pattern confirmed, FakeAsyncSession test pattern confirmed, decimal precisions match, order number pattern confirmed.

---

### Story 5.2: Check Stock Availability

| # | Issue | Severity |
|---|-------|----------|
| C1 | All orders domain code non-existent (blocked on 5.1) | CRITICAL |
| C2 | Stock check endpoint placed in orders domain but queries inventory models — domain cohesion violation | CRITICAL |
| C3 | Schema response field name mismatch: story expects `available`, existing `WarehouseStockInfo` uses `current_stock` | CRITICAL |
| W1 | Frontend `useStockCheck.ts` and `OrderForm.tsx` don't exist yet | WARNING |
| W2 | Debounce cleanup edge case in `useEffect` | WARNING |

**Confirmed Valid (11 items):** `InventoryStock` and `Warehouse` models exist, `get_product_detail()` stock query pattern exists, HTTPException pattern confirmed, `useProductSearch.ts` debounce pattern confirmed, `DEFAULT_TENANT_ID` exists, FakeAsyncSession pattern confirmed, read-only architecture confirmed.

**Web Search:** Story's stock API response format matches Salesforce/Dynamics 365 industry standards.

---

### Story 5.3: Set Payment Terms

| # | Issue | Severity |
|---|-------|----------|
| C1 | Wrong `ReasonCode` enum reference — not in `domains/inventory/schemas.py`, actual location is `common/models/stock_adjustment.py` | CRITICAL |
| C2 | AC4 order immutability claim contradicts Story 5.5 (orders ARE mutable via state machine) | CRITICAL |
| C3 | Story 5.1 code doesn't exist — "already scaffolded" claim is false | CRITICAL |
| C4 | `TaxPolicyCode` on OrderLine is cross-domain import from invoices — not acknowledged | WARNING |
| W1 | `str, Enum` vs `StrEnum` inconsistency with established pattern | WARNING |
| W2 | `payment_terms_days` described as "derived" but stored as DB column | WARNING |

**Confirmed Valid (8 items):** Pydantic v2 serialization works for both enum patterns, `PAYMENT_TERMS_CONFIG` dict pattern confirmed, frontend dropdown pattern confirmed, `GET /payment-terms` endpoint pattern confirmed.

**Web Search:** Field-level immutability for payment terms is industry-standard; record-level immutability (NFR21) applies to invoices only.

---

### Story 5.4: Auto-Generate Invoice from Confirmed Order

| # | Issue | Severity |
|---|-------|----------|
| C1 | Nested `session.begin()` — `create_invoice()` uses `session.begin()` internally, wrapping call in another `session.begin()` raises `InvalidRequestError` | CRITICAL |
| C2 | Orders domain doesn't exist (blocked on 5.1) | CRITICAL |
| C3 | Invoice model missing `order_id` — will be added by this story's migration (expected) | INFO |
| C4 | `buyer_type` mapping from Customer — field doesn't exist on Customer model | CRITICAL |
| W1 | Transaction pattern inconsistency: Story 5.1 uses `session.begin()` in service, but `receive_supplier_order()` doesn't | WARNING |

**Confirmed Valid (13 items):** `create_invoice()` function exists with correct signature, `InvoiceCreate`/`InvoiceCreateLine` schemas confirmed, `BuyerType` and `TaxPolicyCode` enums confirmed, `with_for_update()` and `selectinload()` patterns confirmed, `AuditLog` model confirmed, migration ID unique, `receive_supplier_order()` as correct reference pattern.

**Web Search:** SQLAlchemy 2.0 removed subtransaction support. Nested `session.begin()` is a breaking issue. Industry best practice: only outermost caller uses `session.begin()`, service functions run within existing transaction context.

---

### Story 5.5: Update Order Status

| # | Issue | Severity |
|---|-------|----------|
| C1 | All orders domain code non-existent (blocked on 5.1 + 5.4) | CRITICAL |
| C2 | Frontend `src/domain/orders/` doesn't exist | CRITICAL |
| C3 | `confirm_order()` from Story 5.4 doesn't exist yet | CRITICAL |
| C4 | `Order` and `OrderStatus` models don't exist | CRITICAL |
| C5 | `DELETE /orders/{id}` cancel route has no reference pattern in codebase | CRITICAL |
| C6 | `FULFILLED` vs `RECEIVED` — confusion risk when referencing supplier order pattern | WARNING |
| W1 | `ALLOWED_TRANSITIONS` uses `frozenset` in story, but reference `update_supplier_order_status()` uses plain `set` | WARNING |
| W2 | HTTP 409 vs 422 inconsistency — story says 409, supplier order route uses 422 | WARNING |
| W3 | `async with session.begin():` specified in story but NOT used in `update_supplier_order_status()` reference | WARNING |
| W4 | Confirmation dialogs required for ALL transitions (AC7) but existing `SupplierOrderDetail` has no dialogs | WARNING |

**Confirmed Valid (10 items):** `update_supplier_order_status()` exists with local `ALLOWED_TRANSITIONS`, `with_for_update()` locking confirmed, `statusLabel()`/`statusColor()` helpers exist, `NEXT_STATUSES` map pattern confirmed, `AuditLog` model supports required fields, 409 is used in codebase for state conflicts, `class X(str, Enum)` pattern confirmed throughout.

**Web Search:** HTTP 409 for invalid state transitions is industry-standard (confirmed via MDN, APIPark).

---

## Cross-Story Inconsistencies

| Issue | Stories | Description |
|-------|---------|-------------|
| Nested `session.begin()` | 5.1 + 5.4 | 5.1 uses `session.begin()` in service; 5.4's `confirm_order()` calling `create_invoice()` creates double-nesting |
| Order immutability | 5.3 vs 5.5 | 5.3 AC4 claims orders are immutable; 5.5 defines a full status state machine proving they're mutable |
| `session.begin()` in reference | 5.4 + 5.5 | `receive_supplier_order()` (referenced as pattern) does NOT use `session.begin()`, but stories specify it |
| `frozenset` vs `set` | 5.5 | Story specifies `frozenset` for immutability; reference uses plain `set` |
| HTTP 409 vs 422 | 5.4 + 5.5 | Story says 409 for invalid transitions; `update_supplier_order_status()` route uses 422 |
| `str, Enum` vs `StrEnum` | 5.3 | Story uses `str, Enum`; invoices domain uses `StrEnum` in dedicated enums module |
| Cancellation model | 5.5 vs supplier | Story allows cancel from pending ONLY; supplier orders allow cancel from shipped |

---

## Tally

| Story | CRITICAL | WARNING | CONFIRMED VALID |
|-------|----------|---------|-----------------|
| 5.1 | 2 | 3 | 15 |
| 5.2 | 3 | 4 | 11 |
| 5.3 | 4 | 5 | 8 |
| 5.4 | 4 | 5 | 13 |
| 5.5 | 6 | 6 | 10 |
| **Total** | **19** | **23** | **57** |

---

## Priority Fix Order

**Before ANY Epic 5 story can be implemented:**

1. **Fix migration chain** (5.1 C1) — acknowledge branching or use sequential ID
2. **Implement Story 5.1 first** — all other stories depend on it

**Per-story fixes needed before dev:**

| Story | Must-Fix |
|-------|----------|
| 5.1 | Fix migration branching, add `actor_type` explicit set, add collision retry |
| 5.2 | Move stock check to inventory domain OR keep in orders but reuse inventory services; fix schema field name |
| 5.3 | Fix ReasonCode reference path, fix AC4 immutability scope, clarify Story 5.1 dependency |
| 5.4 | Remove nested `session.begin()` (follow `receive_supplier_order()` pattern), hardcode `buyer_type=B2B` |
| 5.5 | Standardize `frozenset` vs `set`, decide on DELETE vs PATCH for cancel, add confirmation dialogs as explicit scope |

---

## What Web Search Confirmed as Correct

- HTTP 409 for invalid state transitions is industry-standard
- Stock availability API format matches Salesforce/Dynamics 365 patterns
- Debounce hook pattern is industry-standard (useRef + AbortController)
- Tax calculation reuse (centralized module, Decimal precision) is best practice
- Order-to-invoice atomicity requirement is correct
- SQLAlchemy 2.0 removed subtransaction support (nested `begin()` is breaking)
- Payment terms field-level immutability is industry-standard; record-level immutability (NFR21) is invoice-specific
