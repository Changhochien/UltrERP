# Story 21.6: Audit, Permissions, and Regression Coverage

Status: completed

## Story

As a platform owner,
I want Epic 21 changes to stay audited, permissioned, and regression-tested,
so that the current order commitment flow remains trustworthy while the newly closed gaps stay protected.

## Acceptance Criteria

1. Given a pending order is confirmed, when the transition succeeds, then the audit trail still links order confirmation and invoice creation under the same business action chain.
2. Given fulfillment changes, commission mutations, or any new order metadata writes are introduced by this epic, when they affect workflow meaning, then the relevant changes are audited with before and after context.
3. Given Epic 21 touches route permissions, when the implementation lands, then existing confirmation permissions are preserved and any new warehouse or finance-specific visibility rules are explicit and tested.
4. Given regression tests run across the touched order workflow, when Epic 21 behavior is exercised, then invoice creation remains tied to confirmation, reservation failures still roll back correctly, and fulfillment or reporting changes do not redefine billing meaning.
5. Given reporting and workflow protections are complete, when the story closes, then the test suite guards against both invoice-on-shipment drift and creation-time committed-order counting.

## Tasks / Subtasks

- [x] Task 1: Preserve and extend audit continuity. (AC: 1, 2)
  - [x] Keep order confirmation and invoice creation correlated as one business action chain.
  - [x] Audit fulfillment mutations, commission writes, and optional metadata writes only where they change workflow meaning.
  - [x] Keep audit changes localized to the Epic 21 surfaces rather than broad unrelated audit refactors.
- [x] Task 2: Lock the permission matrix to the real current baseline. (AC: 3)
  - [x] Preserve the current create or confirm write baseline in `backend/domains/orders/routes.py`, where write access is currently limited to admin and sales roles.
  - [x] Preserve the current read baseline, where order reads are currently allowed for admin, warehouse, and sales roles, unless this epic intentionally expands visibility.
  - [x] If new warehouse-only actions or finance visibility are introduced, make them explicit and route-local rather than implied.
- [x] Task 3: Add backend regression coverage for the preserved commitment flow and new gaps. (AC: 1-5)
  - [x] Extend confirmation, status, and orders API tests for the touched Epic 21 behavior.
  - [x] Keep rollback coverage proving reservation or invoice failures leave the order unconfirmed.
  - [x] Add tests for any new commission serialization, reporting semantics, or permission boundaries introduced by this epic.
- [x] Task 4: Add focused frontend regression coverage. (AC: 4, 5)
  - [x] Add tests for action visibility, workflow labels, toast or inline feedback, and backorder or readiness cues.
  - [x] Add tests that protect the billing and fulfillment presentation separation introduced earlier in the epic.

## Dev Notes

### Context

Epic 21 keeps the working confirmation flow and expands the order surface around it. The safety net should protect the superior existing behavior first, then cover the newly added order-domain capabilities.

### Architecture Compliance

- Keep audit behavior explicit at business transition boundaries.
- Preserve the current confirmation permissions unless a story explicitly widens or splits them.
- Do not allow Epic 21 changes to shift invoice creation away from confirmation.

### Implementation Guidance

- Current route baseline from `backend/domains/orders/routes.py`:
  - `ReadUser = require_role("admin", "warehouse", "sales")`
  - `WriteUser = require_role("admin", "sales")`
- Most likely touched files:
  - `backend/domains/orders/services.py`
  - `backend/domains/orders/routes.py`
  - audit service or audit helpers used by touched order flows
  - `backend/tests/domains/orders/test_order_confirmation.py`
  - `backend/tests/domains/orders/test_order_status.py`
  - `backend/tests/domains/orders/test_orders_api.py`
  - frontend order tests covering workflow cues and action visibility
- Keep the permission story grounded in actual touched routes rather than speculative role models.

### Testing Requirements

- Backend regression tests are mandatory for this story.
- Validate both happy-path and failure-path behavior around confirmation and reporting semantics.
- Protect against analytics drift and workflow drift, not just API shape changes.

### References

- `../planning-artifacts/epic-21.md`
- `backend/domains/orders/routes.py`
- `backend/domains/orders/services.py`
- `backend/tests/domains/orders/test_order_confirmation.py`
- `backend/tests/domains/orders/test_order_status.py`
- `backend/tests/domains/orders/test_orders_api.py`
- `CLAUDE.md`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- `backend/.venv/bin/python -m pytest backend/tests/domains/orders/test_order_confirmation.py backend/tests/domains/orders/test_order_status.py backend/tests/domains/orders/test_orders_api.py`
- `pnpm vitest run src/tests/orders/OrderDetailConfirmationUX.test.tsx src/tests/orders/OrderWorkflowPresentation.test.tsx src/pages/orders/OrdersPage.test.tsx`

### Completion Notes List

- Confirmation audit coverage now proves the order status change and invoice creation stay linked under the same `correlation_id`, and the order audit points at the created invoice while the invoice audit points back at the source order.
- Order creation audit payloads now include the normalized `sales_team` snapshot alongside `total_commission`, so Epic 21 commission writes remain visible in the audit trail.
- Order route regressions now lock the current permission baseline: warehouse retains read access, finance is denied order reads, and warehouse is denied create and status-write endpoints.
- Frontend order surfaces now honor the same write baseline: read-only roles no longer see workflow mutation controls and cannot use the `/orders/new` route to access the create form.
- Existing rollback and billing-semantics protections remain in place; this story added audit and permission regressions without shifting invoice-on-confirmation behavior.

### File List

- `backend/domains/orders/services.py`
- `backend/tests/domains/orders/test_order_confirmation.py`
- `backend/tests/domains/orders/test_order_status.py`
- `backend/tests/domains/orders/test_orders_api.py`
- `src/domain/orders/components/OrderDetail.tsx`
- `src/pages/orders/OrdersPage.tsx`
- `src/pages/orders/OrdersPage.test.tsx`
- `src/tests/orders/OrderDetailConfirmationUX.test.tsx`
- `src/tests/orders/OrderWorkflowPresentation.test.tsx`
- `public/locales/en/common.json`
- `public/locales/zh-Hant/common.json`
