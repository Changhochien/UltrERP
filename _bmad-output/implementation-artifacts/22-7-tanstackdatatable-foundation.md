# Story 22.7: TanStackDataTable Foundation

**Status:** ready-for-dev

**Story ID:** 22.7

**Epic:** Epic 22 - UI Foundation System: Toast, DatePicker, Breadcrumb, Form Validation, and TanStackDataTable

---

## Story

As a user working in data-heavy list screens,
I want a stronger table foundation with sorting, sticky headers, resize support, and row selection,
so that large domain workspaces can evolve without outgrowing the current table implementation.

## Acceptance Criteria

1. Given a page uses the new TanStack-based table, when the user sorts a sortable column, then the table cycles through ascending, descending, and off states correctly.
2. Given the table enables pagination, when the user changes pages, then the current page callback fires with the updated pagination state.
3. Given column resizing is enabled, when the user drags a resize handle, then the column width updates without breaking the surrounding layout.
4. Given sticky header mode is enabled, when the table body scrolls, then the header remains fixed and readable.
5. Given row selection is enabled, when the user selects one or more rows, then a bulk-action bar appears with the selected count and action affordances.
6. Given a migrated table row is clickable or conditionally styled today, when the page is moved to TanStackDataTable, then `rowLabel`, `getRowClassName`, keyboard activation, and cell-click behavior continue to work.

## Tasks / Subtasks

- [ ] Task 1: Build the shared TanStack table wrapper on the existing dependency. (AC: 1, 2)
  - [ ] Create `src/components/layout/TanStackDataTable.tsx` using the already-installed `@tanstack/react-table` package.
  - [ ] Keep the public API as close as practical to the existing `DataTable` component to reduce migration friction.
  - [ ] Support the row models needed for the current roadmap: core, sorting, filtering, and pagination.
- [ ] Task 2: Preserve current visual treatment and behavior contracts. (AC: 1, 2, 6)
  - [ ] Reuse the current table, toolbar, summary, loading, empty, and pagination visual language rather than shipping a surprising redesign.
  - [ ] Preserve `rowLabel`, `getRowClassName`, `onRowClick`, and existing per-cell click behavior where applicable.
  - [ ] Keep client-side pagination as the initial behavior unless the touched consumer already needs server-side control.
- [ ] Task 3: Add the missing table capabilities. (AC: 3, 4, 5)
  - [ ] Enable column resizing with a minimum width guard.
  - [ ] Add sticky-header support.
  - [ ] Add opt-in row selection and bulk-action bar rendering.
- [ ] Task 4: Migrate the first real consumer. (AC: 1-6)
  - [ ] Replace the current order-list consumer with `TanStackDataTable` as the first production migration.
  - [ ] Keep the current sorting, filter bar, active-filter summary, and page-change behavior intact.
  - [ ] Preserve any order-specific workflow cues, filters, and row interactions already defined by Epic 21 rather than moving that UX ownership into this foundation story.
  - [ ] Preserve the current status-cell rendering while allowing later stories to adopt the shared StatusBadge.
- [ ] Task 5: Add focused regression coverage. (AC: 1-6)
  - [ ] Add tests for sorting, pagination callbacks, sticky-header rendering, column resize hooks, and row selection.
  - [ ] Add a migration regression for the order-list consumer proving row activation and conditional styling still work.

## Dev Notes

### Context

- `@tanstack/react-table` is already installed in `package.json`.
- The current `src/components/layout/DataTable.tsx` covers basic sorting and pagination but lacks column resize, sticky header, and row-selection support.
- The revised Epic 22 scope explicitly requires preserving the current DataTable ergonomics while upgrading the implementation surface.

### Architecture Compliance

- This story is a foundation upgrade, not a visual redesign.
- Keep the wrapper additive so existing tables can migrate incrementally.
- Preserve row-interaction semantics from the current table instead of treating TanStack as a greenfield rewrite.

### Implementation Guidance

- Primary files:
  - `src/components/layout/DataTable.tsx`
  - `src/components/layout/TanStackDataTable.tsx`
  - `src/domain/orders/components/OrderList.tsx`
  - `src/pages/orders/OrdersPage.tsx`
  - any shared pagination or table helper used by the current DataTable stack
- Column-definition code should stay readable and close to the current column contract.
- If keeping exact prop parity is not possible, document the compatibility gap in the implementation notes before widening the migration.
- The orders list is a pilot consumer for the shared table foundation; it is not the ownership boundary for order-specific workflow semantics.

### Testing Requirements

- Frontend component and interaction coverage is required.
- Add a migration regression around the order-list consumer.
- Confirm the touched list still behaves correctly with active filters, sorting, and pagination.

### References

- `package.json`
- `src/components/layout/DataTable.tsx`
- `src/domain/orders/components/OrderList.tsx`
- `src/pages/orders/OrdersPage.tsx`
- `src/components/layout/PageLayout.tsx`

## Dev Agent Record

### Agent Model Used

Record the implementation model and version here.

### Debug Log References

Record focused frontend validation commands and any interactive verification notes here.

### Completion Notes List

Summarize the shared table API, the migrated consumer, and the preserved behavior contracts here once implementation is done.

### File List

- `src/components/layout/TanStackDataTable.tsx`
- touched table utilities or wrappers
- `src/domain/orders/components/OrderList.tsx`
- any focused frontend tests added for TanStackDataTable behavior