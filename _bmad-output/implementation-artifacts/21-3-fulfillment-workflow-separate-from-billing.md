# Story 21.3: Fulfillment and Billing Presentation Separation

Status: done

## Story

As a warehouse or finance user,
I want fulfillment actions, billing context, and backorder cues to be presented separately on orders,
so that I can act on the same order without misreading shipping, invoicing, or payment meaning.

## Acceptance Criteria

1. Given a confirmed order is opened, when the detail page renders, then warehouse actions are grouped separately from billing and invoice navigation.
2. Given an order has a linked invoice or payment status, when the user reviews the detail view, then billing context is visible without implying that shipment creates the invoice.
3. Given an order is ready to ship or partially constrained by stock, when the workspace renders it, then readiness, reservation, and backorder cues are explicit.
4. Given shipped or fulfilled orders are viewed, when the user scans workflow cues, then fulfillment progress remains clear while billing semantics continue to come from confirmation and payment state.
5. Given regression tests run after this story lands, when fulfillment actions are exercised, then the UI labels and workflow cues stay aligned with the preserved backend lifecycle.

## Tasks / Subtasks

- [x] Task 1: Regroup order detail actions by concern. (AC: 1, 2)
  - [x] Update `src/domain/orders/components/OrderDetail.tsx` so commercial actions, warehouse actions, and billing navigation are visually distinct.
  - [x] Replace generic status-action wording with fulfillment-specific labels.
  - [x] Keep invoice navigation separate from warehouse mutations.
- [x] Task 2: Expose billing, reservation, and backorder context needed by the workspace. (AC: 2-4)
  - [x] Extend the order response only as needed to show invoice linkage, payment meaning, and stock/backorder cues.
  - [x] Reuse the existing order lines and stock snapshot data where possible.
  - [x] Avoid inventing a second persisted fulfillment state model in this story.
- [x] Task 3: Make workflow cues legible across detail and list surfaces. (AC: 3-4)
  - [x] Add visible ready-to-ship and backorder callouts where users take action.
  - [x] Ensure shipped and fulfilled states remain readable without mutating billing semantics.
- [x] Task 4: Add focused UI and regression coverage. (AC: 1-5)
  - [x] Add frontend tests for grouped actions, invoice visibility, and backorder or readiness cues.
  - [x] Extend backend or integration coverage only where response shape changes are required.

## Dev Notes

### Context

The existing backend lifecycle already supports confirmation, shipment, and fulfillment. The validated gap is mainly in how the workspace presents that lifecycle, not in a missing warehouse state machine.

### Architecture Compliance

- Do not move invoice creation to shipment or fulfillment.
- Keep the existing orders domain and routes.
- Preserve backend lifecycle semantics and improve presentation first.
- If additional read-side fields are needed, keep them additive and tightly scoped to the orders workflow.

### Implementation Guidance

- Most likely touched files:
  - `src/domain/orders/components/OrderDetail.tsx`
  - `src/domain/orders/components/OrderList.tsx`
  - `src/domain/orders/types.ts`
  - `src/lib/api/orders.ts`
  - `backend/domains/orders/schemas.py`
  - `backend/domains/orders/routes.py`
- Use the existing stock snapshot and `backorder_note` data before introducing new persistence.
- Payment meaning should stay grounded in invoice data rather than a speculative order billing enum.

### Testing Requirements

- Frontend action-visibility and workflow-cue tests are the priority.
- Preserve backend regression coverage for the current order lifecycle.
- Validate that changed copy and labels remain internally consistent.

### References

- `../planning-artifacts/epic-21.md`
- `ERPnext-Validated-Research-Report.md`
- `backend/domains/orders/schemas.py`
- `backend/domains/orders/routes.py`
- `src/domain/orders/components/OrderDetail.tsx`
- `src/domain/orders/components/OrderList.tsx`
- `CLAUDE.md`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- `pnpm test -- src/tests/orders/OrderDetailConfirmationUX.test.tsx src/tests/orders/OrderWorkflowPresentation.test.tsx`
- Follow-up rerun after restoring the explicit confirmation heading and confirm-message copy inside the regrouped action panels; the widened Vitest run completed at `70 files` and `229 tests` passed.
- Static error checks over the touched workflow presentation files and locale files returned no issues.

### Completion Notes List

- Added `src/domain/orders/workflowMeta.ts` to map fulfillment, billing, and reservation read-model states to localized labels and badge variants used consistently across the workspace.
- Reworked `OrderDetail` into separate commercial, fulfillment, and billing sections so warehouse actions, invoice navigation, and payment meaning are visually distinct instead of being overloaded into a single status bucket.
- Added explicit ready-to-ship, reservation, and backorder cues in the detail view and in the line-item stock presentation, while keeping invoice creation and billing meaning tied to confirmation and payment state.
- Updated `OrderList` to show separate fulfillment and billing columns with reservation and backorder support cues so row scanning matches the clarified workflow model from Stories 21.1 and 21.2.
- Added focused presentation coverage in `src/tests/orders/OrderWorkflowPresentation.test.tsx` and preserved the earlier confirmation UX contract under the regrouped layout.
- Validation passed on 2026-04-20 with the focused workflow presentation suite and clean static diagnostics on the touched files.

### File List

- `src/domain/orders/components/OrderDetail.tsx`
- `src/domain/orders/components/OrderList.tsx`
- `src/domain/orders/workflowMeta.ts`
- `public/locales/en/common.json`
- `public/locales/zh-Hant/common.json`
- `src/tests/orders/OrderWorkflowPresentation.test.tsx`
