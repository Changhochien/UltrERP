# Story 21.4: Orders Workspace UX Redesign and Shared Foundation Integration

Status: done

## Story

As a sales, warehouse, or finance user,
I want the orders workspace to make commitment, fulfillment, billing, and exception cues obvious,
so that I can act on orders without decoding overloaded status labels or losing my place in the workflow.

## Acceptance Criteria

1. Given the orders list is loaded, when a user scans rows, then each row shows the existing persisted lifecycle plus supporting execution cues for billing, readiness, reservation, or backorder context.
2. Given a user filters the orders workspace, when they need an operational slice, then fast views or filters exist for pending intake, ready to ship, shipped not completed, invoiced not paid, alongside the current customer, date, search, and status filters.
3. Given the order detail page is opened, when the user orients themselves, then breadcrumb navigation, milestone timeline, grouped actions, and invoice linkage make the workflow legible.
4. Given a user confirms an order or another key order action succeeds or fails, when the UI responds, then feedback is explicit and immediate through toast or clearly visible inline state.
5. Given stock is constrained or partially reserved, when a user is deciding what to do next, then reservation and backorder cues are visible where actions are taken.
6. Given this story introduces shared UI support, when the implementation lands, then only the minimal local foundations needed by the orders workflow are added rather than unrelated app-wide cleanup.

## Tasks / Subtasks

- [x] Task 1: Redesign the orders list around actionable workflow cues. (AC: 1, 2, 5)
  - [x] Update `src/domain/orders/components/OrderList.tsx` so rows surface the persisted order lifecycle plus supporting billing, readiness, reservation, and backorder cues.
  - [x] Add fast operational views or filter presets for pending intake, ready to ship, shipped not completed, and invoiced not paid.
  - [x] Preserve existing customer, date, search, sort, and URL-sync behavior.
- [x] Task 2: Redesign the detail page around orientation and action grouping. (AC: 3, 5)
  - [x] Update `src/domain/orders/components/OrderDetail.tsx` to add breadcrumb navigation, milestone timeline, grouped actions, invoice links, and contextual callouts.
  - [x] Keep commercial actions, warehouse actions, and billing navigation visually distinct.
  - [x] Surface reservation and backorder context where users make decisions.
- [x] Task 3: Standardize order action feedback. (AC: 4)
  - [x] Make the primary confirmation interaction explicitly communicate invoice creation and inventory reservation.
  - [x] Add reliable success and failure feedback through a local toast system or clearly visible inline feedback, whichever best matches the existing app structure.
  - [x] Keep failure states retryable where the current workflow already supports retry.
- [x] Task 4: Integrate the shared UI foundations this workflow needs. (AC: 3, 4, 6)
  - [x] Consume the reusable breadcrumb and toast primitives from Epic 22 instead of creating order-local versions.
  - [x] Keep the order-list workflow cues compatible with the current `DataTable` until Epic 22.7 migrates the shared table foundation, or integrate 22.7 directly if it has already landed.
  - [x] Reuse existing date and filter primitives where possible instead of broad shared-component redesign.
- [x] Task 5: Add focused frontend coverage for the redesigned workspace. (AC: 1-6)
  - [x] Add or extend list and detail tests for workflow cues, filter presets, action grouping, feedback states, and edge cases.
  - [x] Keep touched locale files synchronized if any new copy or labels are introduced.

## Dev Notes

### Previous Story Intelligence

- Stories 21.1 to 21.3 preserve the current lifecycle and expose the derived execution meaning this workspace should render.
- This story should consume those clarified signals rather than inventing a second workflow model in the UI.

### Architecture Compliance

- Keep the orders UX inside the existing route and domain structure.
- Preserve the current orders list and detail flow; improve clarity rather than rebuilding the workspace from scratch.
- Shared toast, breadcrumb, and table-foundation primitives remain owned by Epic 22; this story integrates them on the orders surface instead of re-implementing them locally.

### Implementation Guidance

- Most likely touched files:
  - `src/pages/orders/OrdersPage.tsx`
  - `src/domain/orders/components/OrderList.tsx`
  - `src/domain/orders/components/OrderDetail.tsx`
  - `src/domain/orders/hooks/useOrders.ts`
  - `src/domain/orders/types.ts`
  - `src/lib/api/orders.ts`
  - shared UI integration points from Epic 22 if toast or breadcrumb support has already landed
- Reuse existing filter building blocks and URL-backed state where possible.
- Keep invoice linkage and billing meaning visible without implying that shipment creates the invoice.
- Make ready-to-ship and backorder cues explicit enough for warehouse use, not just decorative badges.
- If Epic 22.7 pilots the orders list on `TanStackDataTable`, preserve the workflow cues, filters, and row interactions defined by this story instead of moving UX ownership into Epic 22.

### Testing Requirements

- Frontend validation is the center of gravity for this story.
- Validate workflow cues, filter behavior, action visibility, feedback states, and edge conditions.
- If toast or breadcrumb support is introduced, cover the order surfaces that depend on it.

### References

- `../planning-artifacts/epic-21.md`
- `ERPnext-Validated-Research-Report.md`
- `src/pages/orders/OrdersPage.tsx`
- `src/domain/orders/components/OrderList.tsx`
- `src/domain/orders/components/OrderDetail.tsx`
- `src/domain/orders/hooks/useOrders.ts`
- `CLAUDE.md`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- `pnpm vitest run src/tests/orders/OrderWorkflowPresentation.test.tsx`
- `pnpm vitest run src/tests/orders/OrderWorkflowPresentation.test.tsx src/tests/orders/OrderDetailConfirmationUX.test.tsx`
- `/Users/changtom/Downloads/UltrERP/.venv/bin/python -m py_compile backend/domains/orders/schemas.py backend/domains/orders/services.py backend/domains/orders/routes.py backend/tests/domains/orders/test_orders_api.py`
- Story review pass: diff review of the touched order files found and corrected the `workflow_view=invoiced_not_paid` backend filter so it aligns with matched-payment state instead of raw invoice status.

### Completion Notes List

- Added backend-enriched order workspace metadata with `execution`, `invoice_number`, and `invoice_payment_status`, plus multi-status order filtering and server-backed quick views for pending intake, ready to ship, shipped not completed, and invoiced not paid.
- Redesigned the orders list to show the persisted lifecycle alongside commercial, fulfillment, reservation, backorder, and billing cues while preserving the existing URL-backed customer, date, search, sort, and status filters.
- Redesigned the order detail surface around breadcrumb orientation, a workflow timeline, grouped commercial/warehouse/billing actions, invoice continuity, and contextual reservation or backorder callouts where users decide what to do next.
- Kept order-action feedback explicit and immediate through the shared breadcrumb primitive from Epic 22, the existing toast system, and visible inline confirmation or retry states.
- Added focused frontend coverage for workflow presentation and order confirmation UX, synchronized the touched locale copy, and validated the story with passing Vitest coverage plus backend Python syntax checks. Backend runtime tests were not runnable in the current `.venv` because the environment is missing test/runtime packages such as `pytest` and `fastapi`.

### File List

- `backend/domains/orders/schemas.py`
- `backend/domains/orders/services.py`
- `backend/domains/orders/routes.py`
- `backend/tests/domains/orders/test_orders_api.py`
- `src/domain/orders/components/OrderList.tsx`
- `src/domain/orders/components/OrderDetail.tsx`
- `src/domain/orders/hooks/useOrders.ts`
- `src/domain/orders/types.ts`
- `src/domain/orders/workflowMeta.ts`
- `src/lib/api/orders.ts`
- `src/tests/orders/OrderWorkflowPresentation.test.tsx`
- `src/tests/orders/OrderDetailConfirmationUX.test.tsx`
- `public/locales/en/common.json`
- `public/locales/zh-Hant/common.json`
- `_bmad-output/implementation-artifacts/21-4-orders-workspace-ux-redesign.md`
