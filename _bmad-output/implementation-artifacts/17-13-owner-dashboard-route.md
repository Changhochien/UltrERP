# Story 17.13: Owner Dashboard Page Route

Status: done

## Implementation Status

**Frontend:** DONE — `OwnerDashboardPage` exists at `src/domain/owner-dashboard/OwnerDashboardPage.tsx`

**Completed:**
- Route page component created and imports all KPI card components
- Page layout includes KPI strip, revenue trend, AR/AP aging, top customers sections
- Uses existing page layout pattern (PageHeader + content grid)

## Story

As a frontend developer,
I want to add a new `/owner-dashboard` route,
so that the owner-specific KPI views are accessible via the sidebar.

## Acceptance Criteria

1. [AC-1] Given the route file at `src/lib/routes.ts`, when a new route `OWNER_DASHBOARD_ROUTE = '/owner-dashboard'` is added, then it is exported from the routes module
2. [AC-2] The route is added to the navigation sidebar under the "Overview" group with "Owner Dashboard" label and chart/analytics icon
3. [AC-3] The route renders `OwnerDashboardPage` at `src/domain/owner-dashboard/OwnerDashboardPage.tsx`
4. [AC-4] The page uses the existing page layout pattern (PageHeader + content grid)

## Tasks / Subtasks

- [x] Task 1 (AC: 1)
  - [x] Subtask 1.1: Add `OWNER_DASHBOARD_ROUTE = '/owner-dashboard'` to `src/lib/routes.ts`
  - [x] Subtask 1.2: Add `OWNER_DASHBOARD_ROUTE` to `AppRoute` union type
- [x] Task 2 (AC: 2)
  - [x] Subtask 2.1: Add "Owner Dashboard" menu item to sidebar navigation under "Overview" group
  - [x] Subtask 2.2: Use analytics/chart icon for the menu item
- [x] Task 3 (AC: 3, 4)
  - [x] Subtask 3.1: Create `src/domain/owner-dashboard/OwnerDashboardPage.tsx`
  - [x] Subtask 3.2: Use existing page layout pattern (PageHeader + content grid)
  - [x] Subtask 3.3: Import and compose KPI cards (RevenueCard, CashFlowCard, TopCustomersCard, etc.)

## Dev Notes

- Existing page pattern: see `src/domain/dashboard/DashboardPage.tsx` or similar
- The page should import all owner-specific KPI card components
- Navigation item should be consistent with existing sidebar items (icon + label)
- AppRoute union type update needed in `src/lib/routes.ts`

### Project Structure Notes

- New directory: `src/domain/owner-dashboard/`
- New page file: `src/domain/owner-dashboard/OwnerDashboardPage.tsx`
- No conflicts with existing structure

### References

- [Source: src/lib/routes.ts]
- [Source: existing dashboard page pattern]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

### File List

- `src/lib/routes.ts` (update)
- `src/domain/owner-dashboard/OwnerDashboardPage.tsx` (new)
- sidebar/nav component (update — add menu item)
