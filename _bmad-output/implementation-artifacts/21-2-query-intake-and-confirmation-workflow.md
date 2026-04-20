# Story 21.2: Customer-Linked Order Intake and Confirmation UX

Status: done

## Story

As a sales or customer-service user,
I want to create orders from an existing customer context and confirm them with clear invoice and reservation language,
so that the current pre-commit order flow is usable without inventing a second order lifecycle.

## Acceptance Criteria

1. Given a user starts from an existing customer context, when they create an order, then the workflow preserves the selected customer and saves the order into the existing `pending` state.
2. Given a pending order is shown in the UI, when the user is ready to commit it, then the primary action clearly states that confirmation creates the invoice and reserves stock.
3. Given confirmation succeeds, when the UI refreshes, then the order detail flow exposes the linked invoice and clear success feedback.
4. Given confirmation fails because invoice creation or stock reservation fails, when the user stays in the order flow, then the order remains editable and the error explains what must be fixed before retry.
5. Given this story is implemented, when the backend is inspected, then no new query-only persistence model or parallel orders API is introduced.

## Tasks / Subtasks

- [x] Task 1: Make customer-linked order intake obvious in the frontend. (AC: 1)
  - [x] Update the orders creation entry point so users can create an order from an existing customer context without re-entering customer identity manually.
  - [x] Preserve existing pricing, payment terms, notes, and line-item behavior.
  - [x] Keep the saved record in the current `pending` state.
- [x] Task 2: Standardize the confirmation interaction. (AC: 2-4)
  - [x] Update `src/domain/orders/components/OrderDetail.tsx` and any related action surfaces so the confirm action explicitly says it creates the invoice and reserves stock.
  - [x] Show success feedback and invoice continuity after confirmation.
  - [x] Show retryable, actionable error states when confirmation fails.
- [x] Task 3: Add only the minimum backend support needed for the improved UX. (AC: 2-5)
  - [x] Reuse the existing create and confirm endpoints under `/api/v1/orders`.
  - [x] Enrich responses only where the frontend needs additional invoice or reservation context.
  - [x] Do not introduce a separate `queries` domain or alternate confirmation workflow.
- [x] Task 4: Add focused regression coverage for intake and confirmation UX. (AC: 1-5)
  - [x] Add frontend tests for customer-linked creation flow, confirmation copy, success feedback, and failure states.
  - [x] Extend backend confirmation tests only where the new UX depends on response data.

## Dev Notes

### Context

The backend already accepts `customer_id` on order creation and already confirms orders atomically. The missing capability is primarily a workspace and interaction gap, not a missing commercial stage in persistence.

### Architecture Compliance

- Keep the existing `/api/v1/orders` surface.
- Keep `pending` as the current pre-commit state.
- Keep invoice creation and stock reservation on confirmation.
- Do not pull Quotation or CRM workflow into this story.

### Implementation Guidance

- Most likely touched files:
  - `src/domain/orders/components/OrderForm.tsx`
  - `src/domain/orders/components/OrderDetail.tsx`
  - `src/pages/orders/OrdersPage.tsx`
  - `src/lib/api/orders.ts`
  - `backend/domains/orders/routes.py`
  - `backend/domains/orders/services.py`
- Favor improving the existing create and confirm experience over renaming the domain language everywhere.
- If a customer-detail action is added, keep it thin and routed through the existing order form flow.
- If Epic 22.4 later migrates `OrderForm.tsx` to the shared Zod and react-hook-form stack, treat that as a form-architecture follow-on that preserves this story's workflow semantics.

### Testing Requirements

- Frontend validation is the center of gravity for this story.
- Preserve backend confirmation regression coverage for invoice creation and stock reservation rollback behavior.
- If any i18n keys are added, keep locale files synchronized.

### References

- `../planning-artifacts/epic-21.md`
- `ERPnext-Validated-Research-Report.md`
- `backend/domains/orders/services.py`
- `backend/tests/domains/orders/test_order_confirmation.py`
- `src/domain/orders/components/OrderForm.tsx`
- `src/domain/orders/components/OrderDetail.tsx`
- `CLAUDE.md`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- `pnpm test -- src/tests/orders/CustomerOrdersTab.test.tsx src/tests/orders/OrderFormCustomerContext.test.tsx src/tests/orders/OrderDetailConfirmationUX.test.tsx`
- Follow-up reruns after aligning the new locale placeholders with the repo's single-brace i18n interpolation config and narrowing the invoice-number assertion in `OrderDetailConfirmationUX.test.tsx`.
- Static error checks over the touched orders/customer UI files and locale files returned no issues.

### Completion Notes List

- Added a thin customer-context create-order entry from `CustomerOrdersTab` into `/orders/new?customer_id=...`, and updated `OrdersPage` plus `OrderForm` so the selected customer is initialized, preserved, and submitted through the existing pending-order flow.
- Added contextual order-form guidance explaining that the customer is preselected and that the order remains in the current `pending` state until confirmation.
- Updated `OrderDetail` so the primary confirmation action explicitly communicates invoice creation and stock reservation, successful confirmation surfaces invoice continuity with a direct invoice CTA, and failures remain actionable and retryable.
- Kept the backend on the existing `/api/v1/orders` create and confirm endpoints and reused the additive order response enrichment from Story 21.1 instead of introducing a parallel query-only model.
- Added focused frontend coverage for customer-linked creation, confirmation copy, success feedback, and failure messaging in the order detail flow.
- Validation passed on 2026-04-20 after two local fixes discovered during the test loop: locale interpolation syntax and a narrowed invoice assertion.

### File List

- `src/domain/orders/components/OrderForm.tsx`
- `src/pages/orders/OrdersPage.tsx`
- `src/components/customers/CustomerOrdersTab.tsx`
- `src/domain/orders/components/OrderDetail.tsx`
- `public/locales/en/common.json`
- `public/locales/zh-Hant/common.json`
- `src/tests/orders/CustomerOrdersTab.test.tsx`
- `src/tests/orders/OrderFormCustomerContext.test.tsx`
- `src/tests/orders/OrderDetailConfirmationUX.test.tsx`
