# Story 22.3: Breadcrumb Navigation

**Status:** ready-for-dev

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

- [ ] Task 1: Create the shared breadcrumb component. (AC: 1, 2, 3)
  - [ ] Create `src/components/ui/Breadcrumb.tsx` with support for clickable and non-clickable items.
  - [ ] Support a configurable separator while defaulting to the simple slash style from the epic.
  - [ ] Add responsive collapse behavior for narrow screens.
- [ ] Task 2: Extend PageHeader without flattening the current hero layout. (AC: 1, 2, 4)
  - [ ] Add a `breadcrumb` prop to `PageHeader` in `src/components/layout/PageLayout.tsx`.
  - [ ] Render the breadcrumb above the title row while preserving eyebrow, hero copy, actions, and tabs.
  - [ ] Keep the existing visual hierarchy of the hero card intact.
- [ ] Task 3: Wire the current pages that already use PageHeader. (AC: 1, 2)
  - [ ] Add current-page breadcrumbs to the existing top-level list or workspace pages that render `PageHeader`.
  - [ ] Add parent-to-detail breadcrumbs to the current detail surfaces, including the existing customer, product, supplier, count-session, order, and invoice detail flows where applicable.
  - [ ] Prefer wiring actual route surfaces that already exist in the repo instead of documenting placeholder pages.
- [ ] Task 4: Add focused UI coverage. (AC: 1-4)
  - [ ] Add component coverage for item rendering, current-page behavior, and mobile collapse.
  - [ ] Add at least one page-level regression proving breadcrumb wiring does not disturb PageHeader tabs or action areas.

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

Record the implementation model and version here.

### Debug Log References

Record focused frontend test commands and any visual verification notes here.

### Completion Notes List

Summarize the shared breadcrumb API, the touched pages, and the responsive behavior here once implementation is done.

### File List

- `src/components/ui/Breadcrumb.tsx`
- `src/components/layout/PageLayout.tsx`
- touched page and detail components that now pass breadcrumb data
- any focused frontend tests added for breadcrumb behavior