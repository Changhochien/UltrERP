# Story 38.3: Quick Action Shortcuts Integration

**Story ID:** 38.3 | **Epic:** Epic 38 | **Status:** review

---

## User Story
**As a user,** I want quick action shortcuts visible in the sidebar, **So that** I can quickly create new records without navigating to the full form.

## Acceptance Criteria
- **Given** sidebar is expanded → **When** user scrolls to bottom → **Then** "Quick Actions" section appears with: Create Lead, Create Opportunity, Create Invoice, Create Order
- **Given** quick action clicked → **Then** mobile nav closes + navigate to creation form
- **Given** sidebar collapsed → **Then** quick actions NOT shown

---

## Developer Context

### Architecture (from Story 38.1)
- `src/lib/navigation.tsx` → `NavigationGroup`, `NavigationSection`, `NavigationItem` types
- `src/components/AppNavigation.tsx` → section rendering
- `src/hooks/useSidebar.tsx` → `showLabel` state for collapsed/expanded
- `public/locales/{locale}/common.json` → i18n keys

### Pattern to Follow
```typescript
interface NavigationSection {
  type: 'standard' | 'reports' | 'setup' | 'quick-actions'; // Add 'quick-actions'
  label: string;  // i18n key
  items: NavigationItem[];
}
```

### Implementation Tasks
- [x] Add `'quick-actions'` to `NavigationSectionType`
- [x] Define quick action items (Create Lead, Opportunity, Invoice, Order)
- [x] Add Quick Actions section to navigation groups (at bottom)
- [x] Render only when `showLabel` is true (expanded mode)
- [x] Click handler: close mobile nav + navigate to form
- [x] Add i18n keys for quick action labels
- [x] Tests + lint/type check

### Files Changed
| File | Changes |
|------|---------|
| `src/lib/navigation.tsx` | + quick-actions type + quick action items |
| `src/components/AppNavigation.tsx` | Quick Actions section rendering + distinct styling |
| `src/components/ui/sidebar.tsx` | Quick actions header styling with Zap icon |
| `public/locales/en/common.json` | + quickActions + createLead translations |
| `public/locales/zh-Hant/common.json` | + quickActions + createLead translations |

---

## Dev Agent Record

### Implementation Summary

Implemented quick action shortcuts integration with the following changes:

1. **Type Updates (`src/lib/navigation.tsx`)**:
   - Added `'quick-actions'` to `NavigationSectionType`
   - Added Quick Actions section to the home navigation group with:
     - Create Lead → `/crm/leads/new`
     - Create Opportunity → `/crm/opportunities/new`
     - Create Invoice → `/invoices/new`
     - New Order → `/orders/new`

2. **Sidebar Section Header (`src/components/ui/sidebar.tsx`)**:
   - Added distinct styling for quick-actions sections
   - Uses Zap (lightning bolt) SVG icon
   - Accent color text styling
   - Uppercase tracking for header label

3. **AppNavigation Updates (`src/components/AppNavigation.tsx`)**:
   - Added `shouldShowQuickActions()` helper function
   - Quick actions items only shown when sidebar is expanded (`showLabel` is true)
   - Added `isQuickAction` flag for distinct styling
   - Quick action items have highlight styling (accent color background/border)

4. **i18n Updates**:
   - Added `nav.quickActions` key ("Quick Actions" / "快速動作")
   - Added `nav.createLead` key ("Create Lead" / "建立線索")

### Validation Results
```
✓ TypeScript type check: No errors
✓ ESLint: No new errors (fixed pre-existing Zap import)
✓ Test suite: 327 passed (107 test files)
```

### Technical Notes
- Quick actions positioned at bottom of home navigation group
- Only visible when sidebar is in expanded mode
- Mobile navigation closes on quick action click (via `handleNavigation`)
- Distinct visual style: accent color background/border for quick action items
- Section header shows Zap icon with accent color

---

## Change Log
| Date | Change |
|------|--------|
| 2026-04-22 | Story created |
| 2026-04-22 | Implementation complete |
| 2026-04-22 | Tests pass, lint clean, type check clean |

## Status History
| Date | Status |
|------|--------|
| 2026-04-22 | ready-for-dev |
| 2026-04-22 | review |
