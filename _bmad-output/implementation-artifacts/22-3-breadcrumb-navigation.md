# Story 22.3: Breadcrumb Navigation

**Status:** done

**Story ID:** 22.3

**Epic:** Epic 22 - UI Foundation System: Toast, DatePicker, Breadcrumb, Form Validation, and TanStackDataTable

---

## Story

As a user moving between list and detail surfaces,
I want breadcrumb navigation in the page header,
so that I can understand my location and jump back up the navigation hierarchy without losing context.

## Acceptance Criteria

1. Given a detail page renders `PageHeader`, when breadcrumb data is provided, then the header shows clickable ancestor segments and a non-clickable current-page segment.
2. Given a list page renders `PageHeader`, when the breadcrumb is displayed, then the current page is shown as a single non-clickable crumb.
3. Given the breadcrumb renders on narrow screens, when the available width is constrained, then the trail collapses to an ellipsis plus the last visible segments instead of breaking the layout.
4. Given a page already uses the hero header or tabs, when breadcrumb support is added, then the existing hero and tabs composition remains intact.

## Tasks / Subtasks

- [x] Task 1: Create the shared breadcrumb component. (AC: 1, 2, 3)
  - [x] Create `src/components/ui/Breadcrumb.tsx` with support for clickable and non-clickable items.
  - [x] Support a configurable separator while defaulting to the simple slash style from the epic.
  - [x] Add responsive collapse behavior for narrow screens.
- [x] Task 2: Extend PageHeader without flattening the current hero layout. (AC: 1, 2, 4)
  - [x] Add a `breadcrumb` prop to `PageHeader` in `src/components/layout/PageLayout.tsx`.
  - [x] Render the breadcrumb above the title row while preserving eyebrow, hero copy, actions, and tabs.
  - [x] Keep the existing visual hierarchy of the hero card intact.
- [x] Task 3: Wire the current pages that already use PageHeader. (AC: 1, 2)
  - [x] Add current-page breadcrumbs to the existing top-level list or workspace pages that render `PageHeader`.
  - [x] Add parent-to-detail breadcrumbs to the current detail surfaces, including the existing customer, product, supplier, count-session, order, and invoice detail flows where applicable.
  - [x] Prefer wiring actual route surfaces that already exist in the repo instead of documenting placeholder pages.
- [x] Task 4: Add focused UI coverage. (AC: 1-4)
  - [x] Add component coverage for item rendering, current-page behavior, and mobile collapse.
  - [x] Add at least one page-level regression proving breadcrumb wiring does not disturb PageHeader tabs or action areas.

## Dev Notes

### Context

- `PageHeader` already exists in `src/components/layout/PageLayout.tsx` and currently supports `eyebrow`, `title`, `description`, `actions`, and `tabs`.
- The header is already reused across many pages, so the breadcrumb must be additive and low-risk.
- The repo has real detail surfaces for customers, products, suppliers, count sessions, orders, and invoices; wire the existing route surface rather than generic placeholders.

### Architecture Compliance

- Do not remove or visually flatten the current hero-card treatment.
- Keep the breadcrumb as a UI primitive and pass data from the page layer instead of hardcoding route assumptions inside the component.
- Preserve the existing PageTabs composition.

### Implementation Guidance

- Primary files:
  - `src/components/ui/Breadcrumb.tsx`
  - `src/components/layout/PageLayout.tsx`
  - current pages under `src/pages/**` that render `PageHeader`
  - detail components or pages under `src/domain/**` or `src/pages/**` that own the current header content
- Use `react-router-dom` links for navigable breadcrumb segments.
- Keep the current page crumb as plain text.

### Testing Requirements

- Add focused frontend coverage for the shared breadcrumb component.
- Add at least one integration test around a touched page header.
- Validate responsive behavior for the collapsed mobile state.

### References

- `src/components/layout/PageLayout.tsx`
- `src/pages/orders/OrdersPage.tsx`
- `src/pages/customers/CustomerDetailPage.tsx`
- `src/pages/inventory/ProductDetailPage.tsx`
- `src/pages/inventory/SupplierDetailPage.tsx`
- `src/pages/inventory/CountSessionDetailPage.tsx`
- `src/domain/orders/components/OrderDetail.tsx`
- `src/domain/invoices/components/InvoiceDetail.tsx`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- `pnpm vitest run src/tests/ui/Breadcrumb.test.tsx src/pages/inventory/SupplierDetailPage.test.tsx`
- `pnpm vitest run src/tests/ui/Breadcrumb.test.tsx src/pages/inventory/SupplierDetailPage.test.tsx src/pages/InventoryPage.test.tsx src/domain/invoices/__tests__/CreateInvoicePage.test.tsx src/domain/purchases/__tests__/PurchasesPage.test.tsx src/pages/inventory/CountSessionsPage.test.tsx src/pages/inventory/CountSessionDetailPage.test.tsx src/pages/inventory/SuppliersPage.test.tsx src/pages/inventory/BelowReorderReportPage.test.tsx src/pages/inventory/InventoryValuationPage.test.tsx src/pages/inventory/CategoriesPage.test.tsx src/pages/inventory/UnitsPage.test.tsx src/pages/inventory/TransfersPage.test.tsx src/pages/inventory/ReorderSuggestionsPage.test.tsx` (`25 passed` after the transfers-page header fix)
- `pnpm vitest run src/pages/inventory/ProductDetailPage.test.tsx src/tests/orders/OrderDetailConfirmationUX.test.tsx src/domain/invoices/__tests__/InvoiceDetail.test.tsx` (`19 passed` after restoring invoice-number interpolation in the order detail success copy)

### Completion Notes List

- Added a shared `Breadcrumb` UI primitive with clickable ancestor links, plain-text current crumbs, a configurable separator, and a mobile-collapsed trail that reduces deeper paths to an ellipsis plus the trailing segments.
- Extended `PageHeader` with an additive `breadcrumb` prop and rendered it above the existing hero content without flattening the hero card or disturbing actions and `PageTabs` composition.
- Wired breadcrumbs into the current `PageHeader` route surfaces across dashboard, customer, invoice, inventory, intelligence, payments, and purchases pages, including parent-to-detail trails for customer, supplier, and count-session detail screens.
- Added breadcrumb support to the custom header owners that do not use `PageHeader` today: product detail, order detail, and invoice detail.
- Focused validation caught and fixed two adjacent defects during the story pass: a misplaced transfers-page prop insertion and missing invoice-number interpolation in the order-confirmation success copy.

### File List

- `src/components/ui/Breadcrumb.tsx`
- `src/components/layout/PageLayout.tsx`
- `src/domain/invoices/components/InvoiceDetail.tsx`
- `src/domain/orders/components/OrderDetail.tsx`
- `src/pages/dashboard/DashboardPage.tsx`
- `src/pages/IntelligencePage.tsx`
- `src/pages/InventoryPage.tsx`
- `src/pages/InvoicesPage.tsx`
- `src/pages/PaymentsPage.tsx`
- `src/pages/PurchasesPage.tsx`
- `src/pages/customers/CreateCustomerPage.tsx`
- `src/pages/customers/CustomerDetailPage.tsx`
- `src/pages/customers/CustomerListPage.tsx`
- `src/pages/invoices/CreateInvoicePage.tsx`
- `src/pages/inventory/BelowReorderReportPage.tsx`
- `src/pages/inventory/CategoriesPage.tsx`
- `src/pages/inventory/CountSessionDetailPage.tsx`
- `src/pages/inventory/CountSessionsPage.tsx`
- `src/pages/inventory/InventoryValuationPage.tsx`
- `src/pages/inventory/ProductDetailPage.tsx`
- `src/pages/inventory/ReorderSuggestionsPage.tsx`
- `src/pages/inventory/SupplierDetailPage.tsx`
- `src/pages/inventory/SuppliersPage.tsx`
- `src/pages/inventory/TransfersPage.tsx`
- `src/pages/inventory/UnitsPage.tsx`
- `src/tests/ui/Breadcrumb.test.tsx`
- `src/pages/inventory/SupplierDetailPage.test.tsx`