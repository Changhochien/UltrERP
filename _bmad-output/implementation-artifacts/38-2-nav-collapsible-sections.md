# Story 38.2: Collapsible Navigation Sections

**Story ID:** 38.2  
**Epic:** Epic 38 - Navigation Sidebar Enhancement  
**Status:** review  
**Created:** 2026-04-22

---

## Story Requirements

### User Story

**As a user,**
I want to collapse navigation sections I don't use frequently,
So that I can reduce visual clutter and focus on my primary workflow.

### Acceptance Criteria

**Given** a navigation group with multiple sections
**When** I click the collapse toggle on a section header
**Then** that section collapses to hide its items
**And** the collapse state persists in localStorage

**Given** a collapsed section
**When** I click the expand toggle
**Then** the section expands to show its items
**And** the expand state persists in localStorage

**Given** sidebar is in collapsed icon-only mode
**When** any section is collapsed or expanded
**Then** the collapse state is NOT shown (all sections hidden)

---

## Tasks/Subtasks

### Implementation Tasks

- [x] Add section collapse state to `useSidebar` context
- [x] Implement `toggleSection` function
- [x] Implement `isSectionCollapsed` function
- [x] Add localStorage persistence for collapse state
- [x] Handle localStorage errors gracefully
- [x] Update `SidebarSectionHeader` props interface
- [x] Add collapsible styling (chevron, cursor, hover)
- [x] Add toggle handler to section header
- [x] Pass collapse state to `SidebarSectionHeader`
- [x] Update `AppNavigation` to use collapse state
- [x] Conditionally render section items
- [x] Test mobile responsive behavior
- [x] Test permission-filtered sections
- [x] Run lint and type check

### Review Follow-ups (AI)

- [ ] Address any code review feedback

---

## Dev Agent Record

### Implementation Summary

Implemented collapsible navigation sections with the following changes:

1. **useSidebar.tsx Updates:**
   - Added `collapsedSections` state (`Set<string>`) for tracking collapsed section IDs
   - Added `toggleSection(sectionId)` function to toggle collapse state
   - Added `isSectionCollapsed(sectionId)` function to check collapse state
   - Added localStorage persistence with key `ultrerp.sidebar.collapsed-sections`
   - Added graceful error handling for localStorage (quota exceeded, private browsing)
   - Updated context value with new functions

2. **sidebar.tsx Updates:**
   - Added `ChevronDown` icon import from lucide-react
   - Changed `SidebarSectionHeader` from `div` to `button` for accessibility
   - Added new props: `sectionId`, `isCollapsed`, `onToggle`
   - Added click and keyboard handlers for toggle
   - Added chevron icon that rotates based on collapse state
   - Added hover effect styling (`hover:bg-sidebar-accent/40`)
   - Added ARIA attributes (`aria-expanded`, `aria-controls`)

3. **AppNavigation.tsx Updates:**
   - Added `isSectionCollapsed` and `toggleSection` from useSidebar
   - Changed section rendering to use explicit `sectionId` key
   - Added conditional rendering of `SidebarMenu` based on collapse state
   - Pass collapse state and toggle handler to `SidebarSectionHeader`

### Files Changed

| File | Changes |
|------|---------|
| `src/hooks/useSidebar.tsx` | Added section collapse state management with localStorage persistence |
| `src/components/ui/sidebar.tsx` | Updated `SidebarSectionHeader` with collapsible toggle UI |
| `src/components/AppNavigation.tsx` | Integrated collapse state, conditional rendering of items |

### Validation Results

```
✓ TypeScript type check: No errors
✓ ESLint: No new errors
✓ Test suite: 327 passed (107 test files)
```

### Technical Notes

- **Section ID format:** `{group_label}-{section_index}` (e.g., "nav.crm-1")
- **localStorage key:** `ultrerp.sidebar.collapsed-sections`
- **localStorage format:** JSON array of section IDs
- **Error handling:** localStorage failures silently fall back to memory-only state
- **Accessibility:** Button element with keyboard support (Enter/Space), ARIA attributes
- **Visual feedback:** ChevronDown icon rotates (down when expanded, right when collapsed)

### Debug Log

- 2026-04-22: Initial implementation complete

---

## Change Log

| Date | Change | Notes |
|------|--------|-------|
| 2026-04-22 | Initial implementation | Added section collapse state to useSidebar, collapsible UI to sidebar, integration in AppNavigation |
| 2026-04-22 | Validation | All tests pass, TypeScript clean, ESLint clean |

---

## Status History

| Date | Status | Notes |
|------|--------|-------|
| 2026-04-22 | ready-for-dev | Story created |
| 2026-04-22 | review | Implementation complete |

---

## Notes

- **Backward Compatibility:** All existing behavior preserved - collapse state only affects labeled sections
- **Performance:** Using Set for O(1) lookups, useMemo for context value
- **Accessibility:** Keyboard navigation works (Tab to header, Enter/Space to toggle)
- **Story 38.1 Already Done:** Section structure and `SidebarSectionHeader` component are implemented
- **Story 38.3 Next:** Quick Action Shortcuts Integration
- **Story 38.4 Final:** Navigation Visual Polish
