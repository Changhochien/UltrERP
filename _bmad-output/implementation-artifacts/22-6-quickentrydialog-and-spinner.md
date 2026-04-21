# Story 22.6: Spinner, QuickEntryDialog, and StatusBadge

**Status:** done

**Story ID:** 22.6

**Epic:** Epic 22 - UI Foundation System: Toast, DatePicker, Breadcrumb, Form Validation, and TanStackDataTable

---

## Story

As an operator working quickly across forms, lists, and lookup popovers,
I want shared loading, quick-create, and status-display primitives,
so that the app uses one consistent pattern for submission feedback, inline entity creation, and status tone rendering.

## Acceptance Criteria

1. Given a button or loading surface needs a visual loading indicator, when the shared Spinner is used, then it renders in the requested size and matches the current UI system.
2. Given a list or detail surface displays domain status values, when the shared StatusBadge is used, then it composes the existing `Badge` component and maps known statuses to the correct tone.
3. Given a user starts a quick-create flow from a combobox or similar lookup surface, when the shared QuickEntryDialog opens, then it renders the appropriate lightweight create form and reuses the current API contracts.
4. Given the quick-entry form succeeds or fails, when the request resolves, then success and error feedback uses the shared toast system and the dialog closes only on success.
5. Given the customer and product quick-create flows are migrated, when the user creates a record successfully, then the parent selection flow receives the created entity and remains usable without manual page refresh.

## Tasks / Subtasks

- [x] Task 1: Add the shared Spinner component. (AC: 1)
  - [x] Create `src/components/ui/Spinner.tsx` with at least `sm`, `md`, and `lg` variants.
  - [x] Reuse Tailwind animation utilities instead of adding bespoke CSS for the spinner.
  - [x] Apply Spinner to the first touched submission and loading surfaces in this story.
- [x] Task 2: Centralize status tone rendering with StatusBadge. (AC: 2)
  - [x] Create `src/components/ui/StatusBadge.tsx`.
  - [x] Compose the existing `Badge` component rather than introducing a new pill system.
  - [x] Lift the duplicated status-to-variant mapping currently spread across domain hooks into one shared implementation.
- [x] Task 3: Build the shared QuickEntryDialog. (AC: 3, 4)
  - [x] Create `src/components/ui/QuickEntryDialog.tsx` on top of the existing dialog primitive.
  - [x] Support at least customer and product quick-create flows in this story.
  - [x] Keep the dialog form minimal and aligned with the shared form-validation work from Story 22.4.
- [x] Task 4: Migrate the current combobox quick-create flows. (AC: 3-5)
  - [x] Refactor `src/components/customers/CustomerCombobox.tsx` to stop owning a raw inline create panel.
  - [x] Refactor `src/components/products/ProductCombobox.tsx` to the same shared quick-entry pattern.
  - [x] Reuse the current create APIs and ensure the selected entity is returned to the parent flow after success.
- [x] Task 5: Add focused validation coverage. (AC: 1-5)
  - [x] Add tests for Spinner sizing, StatusBadge mapping, and at least one quick-entry dialog flow.
  - [x] Add a regression proving the combobox can still select a newly created entity after migration.

## Dev Notes

### Context

- There is no shared Spinner component today.
- Status rendering currently duplicates badge-variant mapping logic across multiple domain hooks.
- `CustomerCombobox` and `ProductCombobox` currently own raw quick-create behavior and should be standardized in this story.

### Architecture Compliance

- StatusBadge must compose the current `Badge` primitive.
- QuickEntryDialog should build on the existing dialog system rather than adding another modal foundation.
- Reuse the shared toast and form-validation infrastructure from other Epic 22 stories instead of inventing local alternatives.

### Implementation Guidance

- Primary files:
  - `src/components/ui/Spinner.tsx`
  - `src/components/ui/StatusBadge.tsx`
  - `src/components/ui/QuickEntryDialog.tsx`
  - `src/components/ui/badge.tsx`
  - `src/components/ui/dialog.tsx`
  - `src/components/customers/CustomerCombobox.tsx`
  - `src/components/products/ProductCombobox.tsx`
  - any shared status helper introduced during consolidation
- Keep the entity scope narrow in v1. Customer and product are the minimum required migrations.
- If supplier quick-entry falls out naturally from the shared abstraction, document it, but do not let that optional extension block the story.

### Testing Requirements

- Frontend component and interaction coverage is required.
- Validate that the migrated quick-create flows still return the created entity to the parent selection state.
- Preserve current selection and search behavior in the comboboxes after the migration.

### References

- `src/components/ui/badge.tsx`
- `src/components/ui/dialog.tsx`
- `src/components/customers/CustomerCombobox.tsx`
- `src/components/products/ProductCombobox.tsx`
- `src/domain/orders/hooks/useOrders.ts`
- `src/domain/inventory/hooks/useSupplierOrders.ts`
- `src/domain/invoices/hooks/useInvoices.ts`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- `pnpm vitest run src/tests/ui/SharedUiPrimitives.test.tsx`
- `pnpm vitest run src/tests/customers/CustomerCombobox.test.tsx`
- `pnpm vitest run src/tests/products/ProductCombobox.test.tsx src/tests/inventory/ProductForm.test.tsx`
- `pnpm vitest run src/tests/orders/OrderDetailConfirmationUX.test.tsx src/tests/orders/CustomerOrdersTab.test.tsx src/domain/invoices/__tests__/InvoiceList.test.tsx src/domain/invoices/__tests__/InvoiceDetail.test.tsx src/tests/invoices/CustomerInvoicesTab.test.tsx src/domain/purchases/__tests__/PurchasesPage.test.tsx`
- Final focused suite passed with `pnpm vitest run src/tests/ui/SharedUiPrimitives.test.tsx src/tests/customers/CustomerCombobox.test.tsx src/tests/products/ProductCombobox.test.tsx src/tests/inventory/ProductForm.test.tsx src/tests/orders/OrderDetailConfirmationUX.test.tsx src/tests/orders/CustomerOrdersTab.test.tsx src/domain/invoices/__tests__/InvoiceList.test.tsx src/domain/invoices/__tests__/InvoiceDetail.test.tsx src/tests/invoices/CustomerInvoicesTab.test.tsx src/domain/purchases/__tests__/PurchasesPage.test.tsx`.

### Completion Notes List

- Added shared `Spinner`, `StatusBadge`, and `QuickEntryDialog` primitives and validated their core behavior with focused UI tests.
- Migrated customer quick-create from the inline combobox panel into the shared dialog, replaced duplicate resolution with an accessible in-dialog path, and preserved parent selection updates plus toast feedback.
- Added product quick-create to `ProductCombobox` through the shared dialog and the existing product create contract, with successful selections flowing back into the parent combobox state.
- Centralized status tone resolution through `StatusBadge` and updated the touched order, invoice, supplier-order, and supplier-invoice list/detail surfaces to compose the shared badge primitive.

### File List

- `src/components/ui/Spinner.tsx`
- `src/components/ui/StatusBadge.tsx`
- `src/components/ui/QuickEntryDialog.tsx`
- `src/components/customers/CustomerCombobox.tsx`
- `src/components/products/ProductCombobox.tsx`
- `src/domain/inventory/components/ProductForm.tsx`
- `src/domain/orders/hooks/useOrders.ts`
- `src/domain/inventory/hooks/useSupplierOrders.ts`
- `src/domain/invoices/hooks/useInvoices.ts`
- `src/domain/purchases/hooks/useSupplierInvoices.ts`
- `src/domain/orders/components/OrderList.tsx`
- `src/domain/orders/components/OrderDetail.tsx`
- `src/components/customers/CustomerOrdersTab.tsx`
- `src/domain/inventory/components/SupplierOrderList.tsx`
- `src/domain/inventory/components/SupplierOrderDetail.tsx`
- `src/domain/invoices/components/InvoiceList.tsx`
- `src/domain/invoices/components/InvoiceDetail.tsx`
- `src/components/customers/CustomerInvoicesTab.tsx`
- `src/domain/purchases/components/SupplierInvoiceList.tsx`
- `src/domain/purchases/components/SupplierInvoiceDetail.tsx`
- `src/tests/ui/SharedUiPrimitives.test.tsx`
- `src/tests/customers/CustomerCombobox.test.tsx`
- `src/tests/products/ProductCombobox.test.tsx`
- `src/tests/inventory/ProductForm.test.tsx`
- `src/domain/invoices/__tests__/InvoiceList.test.tsx`