# Story 22.7: TanStackDataTable Foundation

**Status:** completed

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

- [x] Task 1: Build the shared TanStack table wrapper on the existing dependency. (AC: 1, 2)
  - [x] Create `src/components/layout/TanStackDataTable.tsx` using the already-installed `@tanstack/react-table` package.
  - [x] Keep the public API as close as practical to the existing `DataTable` component to reduce migration friction.
  - [x] Support the row models needed for the current roadmap: core, sorting, filtering, and pagination.
- [x] Task 2: Preserve current visual treatment and behavior contracts. (AC: 1, 2, 6)
  - [x] Reuse the current table, toolbar, summary, loading, empty, and pagination visual language rather than shipping a surprising redesign.
  - [x] Preserve `rowLabel`, `getRowClassName`, `onRowClick`, and existing per-cell click behavior where applicable.
  - [x] Keep client-side pagination as the initial behavior unless the touched consumer already needs server-side control.
- [x] Task 3: Add the missing table capabilities. (AC: 3, 4, 5)
  - [x] Enable column resizing with a minimum width guard.
  - [x] Add sticky-header support.
  - [x] Add opt-in row selection and bulk-action bar rendering.
- [x] Task 4: Migrate the first real consumer. (AC: 1-6)
  - [x] Replace the current order-list consumer with `TanStackDataTable` as the first production migration.
  - [x] Keep the current sorting, filter bar, active-filter summary, and page-change behavior intact.
  - [x] Preserve any order-specific workflow cues, filters, and row interactions already defined by Epic 21 rather than moving that UX ownership into this foundation story.
  - [x] Preserve the current status-cell rendering while allowing later stories to adopt the shared StatusBadge.
- [x] Task 5: Add focused regression coverage. (AC: 1-6)
  - [x] Add tests for sorting, pagination callbacks, sticky-header rendering, column resize hooks, and row selection.
  - [x] Add a migration regression for the order-list consumer proving row activation and conditional styling still work.

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

GPT-5.4

### Debug Log References

- `pnpm test src/components/layout/TanStackDataTable.test.tsx src/tests/orders/OrderWorkflowPresentation.test.tsx src/pages/orders/OrdersPage.test.tsx`
- VS Code diagnostics on the touched Story 22.7 files reported no errors after the final fixes.
- Post-commit BMAD review triage rejected one unrelated wrong-target review result, used TanStack Table docs and web-grounded references for sorting, column sizing, and row selection, and added a request-level regression for cleared sorting.

### Completion Notes List

- Added `TanStackDataTable` as a shared wrapper around `@tanstack/react-table` while keeping the existing table shell and most of the current `DataTable` prop ergonomics.
- Implemented tri-state sorting, client and controlled pagination support, column resize handles with minimum-width guards, sticky-header mode, optional row selection, and bulk-action rendering.
- Migrated `OrderList` as the pilot consumer without moving order-workflow UX ownership into the shared table layer.
- Preserved order-row labels, row click and keyboard activation, active-filter summary, workflow cues, and existing cell rendering.
- Fixed the orders-list sort integration so clearing the sort also clears the request sort params instead of silently forcing the prior default sort.
- Added focused table tests plus order-list migration regressions for row activation and clear-sort URL behavior.
- Follow-up review fixes aligned the shared `DataTableColumn` contract with the resize props already consumed by `TanStackDataTable` and switched column resizing to TanStack's safer documented `onEnd` default for non-memoized React tables.

### Review Findings

- [x] Added a request-level regression proving that clearing order-list sorting removes both `sortBy` and `sortOrder` before the data hook runs again.
- [x] Declared `size`, `minSize`, and `enableResizing` on the shared `DataTableColumn` contract so the public API matches the TanStack wrapper's actual supported surface.
- [x] Switched column resizing to TanStack's `onEnd` mode to avoid unnecessary resize-time re-render pressure in this non-memoized wrapper.

### File List

- `src/components/layout/TanStackDataTable.tsx`
- `src/components/layout/TanStackDataTable.test.tsx`
- `src/domain/orders/components/OrderList.tsx`
- `src/tests/orders/OrderWorkflowPresentation.test.tsx`