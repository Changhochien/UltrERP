# Story 5.3 Re-Validation Report: Set Payment Terms on Order

**Story:** `5-3-set-payment-terms.md`
**Re-Validation Date:** 2026-04-01
**Prior Validation:** `5-3-validation.md` (2026-04-01)

---

## Summary of Prior Issues

| Issue ID | Description | Status This Pass |
|----------|-------------|-----------------|
| C1 | Wrong ReasonCode enum reference path | STILL BROKEN |
| C2 | AC4 order immutability contradicts Story 5.5 | PARTIALLY FIXED (AC4 updated, Dev Notes NOT updated) |
| C3 | Story 5.1 code doesn't exist | STILL BROKEN |
| W1 | `str, Enum` vs `StrEnum` inconsistency | NOT ADDRESSED |

---

## FIXED: Issues Resolved

### None

No issues from the prior validation have been fully resolved. AC4 was partially updated but introduced a new contradiction.

---

## STILL BROKEN: Issues That Remain

### C1: Wrong ReasonCode Enum Reference Path (Dev Notes line 93)

**Prior Finding:** The story says `ReasonCode` enum is in `domains/inventory/schemas.py`.

**Actual Location:** `ReasonCode` is defined in `backend/common/models/stock_adjustment.py` line 20:
```python
class ReasonCode(str, enum.Enum):
    RECEIVED = "received"
    DAMAGED = "damaged"
    ...
```

**Status:** STILL BROKEN. The Dev Notes line 93 unchanged:
> `PaymentTermsCode` should be defined alongside schemas in `domains/orders/schemas.py` (same pattern as `ReasonCode` enum in inventory)

The reference "in inventory" is wrong. `domains/inventory/schemas.py` does NOT contain a `ReasonCode` enum — only `USER_SELECTABLE_REASON_CODES` (a plain list of strings) and `ReasonCodeItem` (a Pydantic model).

**Impact:** Developer following this reference will look in the wrong file.

---

### C3: Story 5.1 Code Does Not Exist

**Prior Finding:** Story 5.3 Task 2 claims "This is already scaffolded in Story 5.1's OrderCreate schema and create_order() service."

**Verification:**
- `backend/domains/orders/` directory: **DOES NOT EXIST**
- `backend/common/models/order.py`: **DOES NOT EXIST**
- `backend/common/models/order_line.py`: **DOES NOT EXIST**
- No migration for orders tables in `migrations/versions/`
- No `create_order()` service function exists
- `backend/tests/test_orders_api.py`: **DOES NOT EXIST**
- `src/domain/orders/` frontend directory: **DOES NOT EXIST**

**Status:** STILL BROKEN. The claim that payment terms is "already scaffolded" is false. Story 5.1 has NOT been implemented. All orders-related code must be created as part of Story 5.1 implementation first.

---

## NEW ISSUES: Contradictions Introduced by AC4 Fix

### NEW-1: AC4 Updated But Dev Notes Line 88 Contradicts It

**AC4 (line 34-37) — UPDATED:**
> **AC4:** Payment terms immutability
> Given an order has been created
> When I try to change the payment terms
> Then the system does not allow modification (payment terms are immutable after order creation, matching invoice immutability pattern — **note: order STATUS changes via Story 5.5 are still allowed**)

The note about Story 5.5 was added to AC4.

**Dev Notes line 88 — NOT UPDATED:**
> **Immutability Pattern:** Orders cannot be modified after creation — matching the invoice immutability pattern (NFR21)

**The Contradiction:**
- AC4 now explicitly allows "order STATUS changes via Story 5.5"
- Dev Notes line 88 still claims "Orders cannot be modified after creation" — implying NO modifications allowed
- Story 5.5's state machine allows: pending → confirmed → shipped → fulfilled, and pending → cancelled
- Dev Notes line 88 would incorrectly suggest these status changes are NOT allowed

**Impact:** A developer reading Dev Notes line 88 would believe the entire order record is immutable, contradicting the explicit exception in AC4 and Story 5.5's state machine.

**Resolution Required:** Dev Notes line 88 must be updated to:
> **Immutability Pattern:** `payment_terms_code` and `payment_terms_days` fields are immutable after order creation. However, order **status** transitions via Story 5.5 are allowed (pending → confirmed → shipped → fulfilled/cancelled).

---

## CONFIRMED VALID: Patterns That Still Check Out

### V1: Enum Pattern — `str, Enum` Works for Pydantic Serialization

Both `str, Enum` (Story 5.3 line 105, Story 5.5 Task 1) and `StrEnum` (in `domains/invoices/enums.py`) work correctly with Pydantic v2 serialization. JSON output is the string value, not the enum member name.

**Verdict:** Acceptable, though inconsistent with `domains/invoices/enums.py` pattern. Not a blocker.

---

### V2: `PAYMENT_TERMS_CONFIG` Dict Pattern

Directly analogous to `_POLICIES: dict[TaxPolicyCode, TaxPolicy]` in `domains/invoices/tax.py`. This is a confirmed project convention.

**Verdict:** Valid. ✅

---

### V3: `GET /payment-terms` Endpoint Pattern

Matches `GET /reason-codes` in `backend/domains/inventory/routes.py` and `ReasonCodeListResponse` schema pattern.

**Verdict:** Valid. ✅

---

### V4: Story 5.5 State Machine Is the Source of Truth for Order Mutability

Story 5.5 defines:
- `pending → confirmed` (via Story 5.4)
- `confirmed → shipped`
- `shipped → fulfilled`
- `pending → cancelled`

**Verdict:** Confirmed valid. Orders are mutable through status transitions. Only payment_terms fields are locked. ✅

---

### V5: `payment_terms_days` Is a Stored Column, Not Derived

Story 5.1 migration spec defines `payment_terms_days` as an INTEGER column with `default 30`. The service layer populates it from `PAYMENT_TERMS_CONFIG[code].days` at creation time.

**Verdict:** Valid storage pattern. ✅

---

## Iteration Pass Findings

| Iteration | Focus | Finding |
|-----------|-------|---------|
| 1 | Read story, check AC4 vs Dev Notes | Found NEW-1: Dev Notes line 88 contradicts AC4 fix |
| 2 | Verify ReasonCode enum path | Confirmed C1 STILL BROKEN — path unchanged |
| 3 | Cross-story consistency with 5.5 | AC4 allows Story 5.5 status changes; Dev Notes line 88 denies them |
| 4 | Final consistency pass | No additional issues found |

---

## Required Fixes Before Implementation

1. **Dev Notes line 88**: Must update to clarify orders ARE mutable via Story 5.5 status transitions, only payment_terms fields are immutable.

2. **Dev Notes line 93**: Must update ReasonCode reference from "in inventory" to `backend/common/models/stock_adjustment.py`.

3. **Task 2 header**: Must acknowledge Story 5.1 code does NOT exist and that Task 2 depends on Story 5.1 being implemented first. The entire orders domain infrastructure must be created.

---

## Overall Assessment

**Story is NOT ready for implementation.** Three critical issues remain from prior validation (C1, C3) plus one new issue (NEW-1) introduced by the AC4 fix that was not propagated to Dev Notes. The story has an internal contradiction: AC4 says status changes are allowed via Story 5.5, but Dev Notes line 88 says orders cannot be modified after creation.

The AC4 note was a correct fix — but it was incomplete. Dev Notes must be updated to match.
