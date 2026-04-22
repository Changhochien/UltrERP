# Story 38.1: Report Section Grouping and Navigation Group Expansion

**Story ID:** 38.1  
**Epic:** Epic 38 - Navigation Sidebar Enhancement  
**Status:** review  
**Created:** 2026-04-22

---

## Story Requirements

### User Story

**As a user,**
I want reports organized in dedicated sections within each navigation group,
So that I can quickly find analytics and reporting tools separate from primary workflow items.

**As a developer,**
I want to expand the navigation groups to match ERPNext's module organization,
So that the sidebar structure is familiar to users migrating from ERPNext.

### Acceptance Criteria

**Given** the navigation configuration is loaded
**When** the sidebar renders
**Then** each navigation group contains:
  - Standard items (primary workflow items)
  - Reports section (indented, with "Reports" header)
  - Setup section (indented, with "Setup" header)

**Given** a navigation group with reports
**When** in collapsed icon-only mode
**Then** only the group-level icon is shown (not section headers)

**Given** the CRM navigation group
**When** expanded
**Then** it displays:
  - Overview section: Leads, Opportunities, Quotations
  - Reports section (indented): Sales Analytics, Pipeline, Funnel
  - Setup section (indented): CRM Settings

**Given** the Operations navigation group
**When** expanded  
**Then** it displays:
  - Overview section: Inventory, Purchases
  - Reports section (indented): Stock Reports, Valuation
  - Setup section (indented): Inventory Settings, Purchase Settings

---

## Tasks/Subtasks

### Implementation Tasks

- [x] Update `NavigationGroup` and `NavigationSection` types
- [x] Restructure `NAVIGATION_GROUPS` with sections
- [x] Add `SidebarSectionHeader` component
- [x] Update `AppNavigation` to render sections
- [x] Apply indented styling to non-standard items
- [ ] Add section collapse state to `useSidebar` (moved to Story 38.2)
- [ ] Add section collapse toggle UI (moved to Story 38.2)
- [x] Update i18n keys for section headers
- [ ] Add tests (deferred to Story 38.2 for collapse functionality)
- [x] Run lint and type check

### Review Follow-ups (AI)

- [ ] Address any code review feedback

---

## Dev Agent Record

### Implementation Summary

Implemented report section grouping and navigation group expansion with the following changes:

1. **Type Updates (`src/lib/navigation.tsx`)**:
   - Added `NavigationSectionType` type with values: `'standard' | 'reports' | 'setup'`
   - Added `NavigationSection` interface with `type`, `label`, and `items`
   - Updated `NavigationGroup` interface to use `sections` instead of `items`
   - Added new imports: `TrendingUp`, `FileBarChart`, `Package` icons

2. **Navigation Groups Restructured**:
   - Overview: Dashboard, Admin, Owner Dashboard, Settings (standard section only)
   - CRM: Leads, Opportunities, Quotations, Customers, Intelligence (standard) + Reports + Setup
   - Finance (NEW): Invoices, Orders, Payments (standard) + Reports
   - Operations: Inventory, Purchases (standard) + Reports + Setup

3. **Sidebar Section Header (`src/components/ui/sidebar.tsx`)**:
   - Added `SidebarSectionHeader` component that renders section headers
   - Reports sections show with `text-sidebar-foreground/50`
   - Setup sections show with `text-sidebar-foreground/40`
   - Hidden in collapsed icon-only mode

4. **AppNavigation Updates (`src/components/AppNavigation.tsx`)**:
   - Added `React` import for `React.Fragment`
   - Updated filtering to work with sections instead of items
   - Added `getSectionIndentClass()` helper for indentation
   - Reports/Setup items get `pl-6` (24px left padding)
   - Standard items have no additional indentation

5. **i18n Updates**:
   - Added new nav keys: `reports`, `setup`, `finance`, `suppliers`, `belowReorderReport`, `inventoryReports`, `invoiceReports`, `inventoryValuation`, `inventoryCategories`
   - Updated both English (`en`) and Traditional Chinese (`zh-Hant`) translation files
   - Added route description keys for new navigation items

### Files Changed

| File | Changes |
|------|---------|
| `src/lib/navigation.tsx` | Type updates, navigation group restructure |
| `src/components/ui/sidebar.tsx` | Added `SidebarSectionHeader` component |
| `src/components/AppNavigation.tsx` | Section rendering, indentation styling |
| `public/locales/en/common.json` | Added nav and route translation keys |
| `public/locales/zh-Hant/common.json` | Added nav and route translation keys (zh-Hant) |

### Validation Results

```
✓ TypeScript type check: No errors
✓ ESLint: No new errors (1 pre-existing unused import fixed)
✓ Test suite: 327 passed (107 test files)
```

### Technical Notes

- **Permission filtering**: Now operates on section items, preserving existing behavior
- **Collapsed mode**: Section headers automatically hidden (handled by `showLabel` check)
- **Indentation**: Applied via `pl-6` class for reports/setup sections
- **Section headers**: Rendered only when `section.label` is not null
- **New Finance group**: Created to match ERPNext's module organization

### Debug Log

- 2026-04-22: Initial implementation complete

---

## Change Log

| Date | Change | Notes |
|------|--------|-------|
| 2026-04-22 | Initial implementation | Added section types, navigation restructure, section headers, indentation |
| 2026-04-22 | i18n updates | Added nav keys for English and zh-Hant |
| 2026-04-22 | Validation | All tests pass, TypeScript clean, ESLint clean |

---

## Status History

| Date | Status | Notes |
|------|--------|-------|
| 2026-04-22 | ready-for-dev | Story created |
| 2026-04-22 | review | Implementation complete, ready for review |

---

## Notes

- Section collapse functionality moved to Story 38.2 (as originally planned per epic scope)
- Permission filtering works at section level (items filtered, empty sections removed)
- Mobile responsive behavior preserved (collapsed mode hides section headers)
- All existing tests pass (327/327)
