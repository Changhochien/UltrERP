# Story 5.3: Set Payment Terms on Order

**Status:** ready-for-dev

**Story ID:** 5.3

---

## Story

As a sales rep,
I want to set payment terms on an order (e.g., 30 days),
So that customers can pay according to agreed terms.

---

## Acceptance Criteria

**AC1:** Payment terms selection
**Given** I'm creating an order
**When** I select payment terms from available options (Net 30, Net 60, COD)
**Then** the payment_terms_code and payment_terms_days are recorded on the order

**AC2:** Default payment terms
**Given** I'm creating an order and do not select payment terms
**When** the order is saved
**Then** payment terms default to NET_30 (30 days)

**AC3:** Invoice inherits payment terms
**Given** an order has payment terms set
**When** the order is confirmed and an invoice is auto-generated (Story 5.4)
**Then** the invoice reflects the same payment terms from the order

**AC4:** Payment terms immutability
**Given** an order has been created
**When** I try to change the payment terms
**Then** the system does not allow modification (payment terms are immutable after order creation, matching invoice immutability pattern — note: order STATUS changes via Story 5.5 are still allowed)

**AC5:** Payment terms listing
**Given** I need to see available payment terms
**When** I request the payment terms list
**Then** the system returns all configured payment terms with code, label, and days

---

## Tasks / Subtasks

- [ ] **Task 1: Payment Terms Enum** (AC1, AC2, AC5)
  - [ ] In `backend/domains/orders/schemas.py`, define `PaymentTermsCode` as a Python `str, Enum`:
    ```
    NET_30 = "NET_30"   # 30 days
    NET_60 = "NET_60"   # 60 days
    COD = "COD"         # 0 days, cash on delivery
    ```
  - [ ] Add `PAYMENT_TERMS_CONFIG` dict mapping code → { label: str, days: int }
  - [ ] Add GET `/api/v1/orders/payment-terms` endpoint returning all options

- [ ] **Task 2: Integrate into Order Create** (AC1, AC2)
  - [ ] This is already scaffolded in Story 5.1's OrderCreate schema and create_order() service
  - [ ] Ensure `payment_terms_code` defaults to `NET_30` when not provided
  - [ ] Validate `payment_terms_code` is a valid enum value (422 if not)
  - [ ] Set `payment_terms_days` automatically from PAYMENT_TERMS_CONFIG

- [ ] **Task 3: Frontend — Payment Terms Dropdown** (AC1, AC2)
  - [ ] In OrderForm.tsx (from Story 5.1), add payment terms dropdown populated from PAYMENT_TERMS_CONFIG (can be client-side constants matching backend, or fetched from /payment-terms endpoint)
  - [ ] Default selection: NET_30
  - [ ] Display: "Net 30 Days", "Net 60 Days", "Cash on Delivery"

- [ ] **Task 4: Backend Tests** (AC1-AC2, AC5)
  - [ ] In `backend/tests/test_orders_api.py`:
    - [ ] Test order creation with explicit payment terms
    - [ ] Test order creation without payment terms defaults to NET_30
    - [ ] Test order creation with invalid payment terms returns 422
    - [ ] Test GET /payment-terms returns all options

- [ ] **Task 5: Frontend Tests** (AC1)
  - [ ] In `src/domain/orders/__tests__/OrderForm.test.tsx`:
    - [ ] Test payment terms dropdown renders all options
    - [ ] Test default selection is NET_30

---

## Dev Notes

### Architecture Compliance

- **No Lookup Table (MVP):** Payment terms are a hardcoded Python enum + config dict. No database table needed for MVP. This can be promoted to a configurable table when needed
- **Immutability Pattern:** Orders cannot be modified after creation — matching the invoice immutability pattern (NFR21) [Source: arch]
- **AC3 is implemented in Story 5.4:** The auto-invoice generation story handles copying payment_terms from order → invoice. This story only handles recording the terms on the order

### Implementation Details

- **PaymentTermsCode enum** should be defined alongside schemas in `domains/orders/schemas.py` (same pattern as `ReasonCode` enum in inventory)
- **payment_terms_days** is derived from the code, not independently settable — prevents inconsistency
- **Client-side constants:** The dropdown options can be hardcoded on the frontend since payment terms are a fixed enum for MVP. Optionally fetch from the backend endpoint for consistency

### Dependencies

- **Part of Story 5.1:** Payment terms fields are included in the Order model and OrderCreate schema from Story 5.1. This story defines the enum, validation, and frontend dropdown
- **Used by Story 5.4:** Invoice auto-generation will copy these terms

### Key Conventions

- Tab indentation, `from __future__ import annotations`
- Enum pattern: use `class PaymentTermsCode(str, Enum)` so values serialize as strings
- FakeAsyncSession test pattern
- HTTPException for validation errors

### Project Structure Notes

**Backend (modified files from 5.1):**
- `backend/domains/orders/schemas.py` — PaymentTermsCode enum, PAYMENT_TERMS_CONFIG
- `backend/domains/orders/routes.py` — GET /payment-terms endpoint
- `backend/tests/test_orders_api.py` — additional payment terms tests

**Frontend (modified files from 5.1):**
- `src/domain/orders/components/OrderForm.tsx` — payment terms dropdown
- `src/domain/orders/types.ts` — PaymentTermsCode type

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Epic 5, Story 5.3]
- [Source: backend/domains/inventory/schemas.py — ReasonCode enum pattern (USER_SELECTABLE_REASON_CODES)]
- [Source: backend/domains/invoices/models.py — immutability pattern reference]

---

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
