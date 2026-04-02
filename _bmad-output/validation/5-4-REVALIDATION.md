# Story 5.4 — Re-Validation Report

**Date:** 2026-04-01
**Story:** Auto-Generate Invoice from Confirmed Order
**Status:** NOT READY-FOR-DEV

---

## C1: Nested `session.begin()` — STILL BROKEN (Option A is aspirational, not implemented)

### Finding
`_create_invoice_core()` does **NOT exist** anywhere in the codebase.

The story's Task 3 says to use **Option A (recommended)**: extract `_create_invoice_core()` from `create_invoice()`. But this function has never been created. The story presents Option A as a done thing, but it is a **prescription, not a description of existing code**.

### Evidence
- `backend/domains/invoices/service.py` — `create_invoice()` is lines 107–203. The entire body from line 114 onward is wrapped in `async with session.begin():` at line 125. There is no `_create_invoice_core()`.
- `grep -r "_create_invoice_core" backend/` — **0 matches**

### Analysis
Option A would require:
1. Extracting lines 114–199 from `create_invoice()` into a new `_create_invoice_core()` function
2. Making `create_invoice()` a thin wrapper: `async with session.begin(): return await _create_invoice_core(...)`
3. This is a non-trivial refactor of the invoice service — the entire function body including validation, customer lookup, number range allocation, line calculation, model instantiation, and flush are all inside the `session.begin()` block

Option B (call `create_invoice()` without wrapping in `session.begin()`) would break atomicity — the order status update and invoice creation would not be in the same transaction.

**The story does not yet have a viable path to fix C1.** The recommended Option A is correct architecture, but it has not been implemented, and the story does not acknowledge this as a pre-requisite task.

### Verdict: STILL BROKEN

---

## C4: `buyer_type` — STILL MISLEADING

### Finding
The Customer model (`backend/domains/customers/models.py`) has **no `buyer_type` field**. The story hardcodes `buyer_type=BuyerType.B2B` at line 159 of the Dev Notes with comment `# BuyerType from customer`.

### Evidence
Customer model fields: `id`, `tenant_id`, `company_name`, `normalized_business_number`, `billing_address`, `contact_name`, `contact_phone`, `contact_email`, `credit_limit`, `status`, `version`, `created_at`, `updated_at`. **No buyer_type.**

The story's Task 3 line 93 says: "Pass customer_id, invoice_date=today, **buyer_type from customer**" — but then the Dev Notes code sample hardcodes `BuyerType.B2B`.

### Analysis
The hardcoded `BuyerType.B2B` is a reasonable **workaround** for MVP since the Customer model lacks buyer_type. However, the comment `# BuyerType from customer` is **actively false and misleading**. It implies the value comes from the customer when it is actually hardcoded.

The comment should be changed to something like `# Hardcoded B2B — Customer model lacks buyer_type field` or simply removed.

### Verdict: STILL MISLEADING (comment not fixed)

---

## NEW ISSUE 1: `orders` domain does not exist

### Finding
`backend/domains/orders/` does not exist. All of the following referenced files are completely unimplemented stubs in the story:
- `backend/domains/orders/services.py` — `confirm_order()` does not exist
- `backend/domains/orders/routes.py` — PATCH endpoint does not exist
- `backend/domains/orders/schemas.py` — `OrderStatusUpdate` schema does not exist

### Evidence
`ls backend/domains/` returns: `__init__.py`, `customers`, `health`, `inventory`, `invoices`. **No `orders`.**

### Analysis
The story's Task 3–4 describe implementing `confirm_order()` in a domain that has not been created. The story references this as if the file exists and needs modification, but it needs to be created from scratch. This is a larger scope than the story implies.

### Verdict: NEW ISSUE — scope significantly larger than documented

---

## NEW ISSUE 2: Invoice model lacks `order_id` field

### Finding
`backend/domains/invoices/models.py` — the `Invoice` model has **no `order_id` field**. The story's Task 2 says to add it, but it has not been added.

### Evidence
Invoice model fields end at `replaced_by_invoice_id` (line 78). No `order_id`.

### Analysis
The story references this as a modification to an existing model (Task 2), but the field does not exist. This is a planned addition, not something that was fixed.

### Verdict: NEW ISSUE — field addition not done

---

## NEW ISSUE 3: Migration chain is broken

### Finding
The story references migration `jj000ll00m32_add_invoice_order_id.py` chaining from a `jj000kk00l31_create_orders_table.py` (implied). Neither exists.

### Evidence
`ls migrations/versions/` shows only invoice/customer/inventory migrations. No orders migration. The migration `jj000ll00m32_add_invoice_order_id.py` is listed in the story's "Backend (new files)" section but does not exist on disk.

### Analysis
The story correctly identifies the migration need but the migration file is not created. The story would depend on a prior Story 5.1 (Order model/services/routes) that does not appear to exist.

### Verdict: NEW ISSUE — migration not created

---

## CONFIRMED VALID

### 1. `create_invoice()` reusable — CONFIRMED
The existing `create_invoice()` function at `backend/domains/invoices/service.py:107` correctly handles: invoice number allocation, tax calculation via `calculate_line_amounts()`, line amount computation, and audit logging. AC3's requirement ("same tax engine as manual invoice creation") is satisfied by calling `create_invoice()`.

### 2. Atomic transaction requirement (AC4) — CONFIRMED as goal
The story correctly identifies that `async with session.begin()` cannot be nested. The solution (Option A's `_create_invoice_core()` extraction) is architecturally correct, even though the function does not exist yet.

### 3. `for_update()` locking pattern — CONFIRMED
The story correctly cites `backend/domains/inventory/services.py — receive_supplier_order()` as the reference pattern for `with_for_update()` locking. This pattern exists and is correctly referenced.

### 4. `actor_id` as String(100) — CONFIRMED
`backend/common/models/audit_log.py:24` defines `actor_id` as `Mapped[str] = mapped_column(String(100))`. The story's Key Conventions note is accurate. Existing inventory service functions (`actor_id: str`) already follow this convention.

### 5. Tax engine reuse — CONFIRMED
`backend/domains/invoices/tax.py` exports `calculate_line_amounts()` and `aggregate_invoice_totals()`. The `create_invoice()` service correctly uses these (service.py lines 151–159). AC3's tax consistency requirement is achievable via `create_invoice()` reuse.

### 6. BuyerType enum — CONFIRMED
`backend/domains/invoices/enums.py:8` defines `BuyerType.B2B = "b2b"` and `BuyerType.B2C = "b2c"`. These are the correct enum values for the hardcoded `BuyerType.B2B` workaround.

---

## Migration chain, actor_id casting, atomic transaction pattern

These three items were grouped in the prior validation. Here is the breakdown:

| Item | Status |
|---|---|
| Migration chain | **NEW ISSUE** — migration file not created; orders domain doesn't exist to chain from |
| `actor_id` casting | **CONFIRMED VALID** — existing code uses `str`, story convention is correct |
| Atomic transaction pattern | **STILL BROKEN** — `_create_invoice_core()` does not exist; Option A is aspirational |

---

## Summary

| Issue | Prior Status | Current Status |
|---|---|---|
| C1: nested `session.begin()` | CRITICAL | **STILL BROKEN** — Option A is correct but unimplemented |
| C4: `buyer_type` misleading comment | CRITICAL | **STILL MISLEADING** — comment not fixed, still says "from customer" |
| Migration chain | Issue | **NEW ISSUE** — migration doesn't exist |
| `orders` domain missing | — | **NEW ISSUE** — domain doesn't exist |
| Invoice `order_id` field missing | — | **NEW ISSUE** — field not added |

**Overall verdict: NOT READY-FOR-DEV**

The story is a solid **design specification** but is not yet an **implementation-ready** document. It describes what should be built but several key dependencies do not exist: the `_create_invoice_core()` helper (Option A), the `orders` domain, the `Invoice.order_id` field, and the migration file. The `buyer_type` hardcoding workaround is reasonable but the misleading comment must be corrected before this story can proceed.
