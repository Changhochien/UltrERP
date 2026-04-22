# Story 38.3: Quick Action Shortcuts Integration

**Story ID:** 38.3 | **Epic:** Epic 38 | **Status:** done

## User Story
**As a user,** I want quick action shortcuts visible in the sidebar, **So that** I can quickly create new records without navigating to the full form.

## Acceptance Criteria
- ✅ Sidebar expanded → Quick Actions section appears with Create Lead, Create Opportunity, Create Invoice, New Order
- ✅ Quick action clicked → Mobile nav closes + navigate to creation form
- ✅ Sidebar collapsed → Quick actions NOT shown

## Implementation
- `src/lib/navigation.tsx`: Added `'quick-actions'` type + Quick Actions section
- `src/components/AppNavigation.tsx`: `shouldShowQuickActions()` + accent styling
- `src/components/ui/sidebar.tsx`: Quick actions header with Zap SVG icon
- `public/locales/{en,zh-Hant}/common.json`: i18n keys

## Validation
- TypeScript: Clean
- ESLint: Clean  
- Tests: 327 passed (107 files)

## Commit
`c03d099` - feat(epic-38): Implement quick action shortcuts in navigation sidebar
