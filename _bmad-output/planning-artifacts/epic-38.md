# Epic 38: Navigation Sidebar Enhancement

## Epic Goal

Update UltrERP's navigation sidebar to match ERPNext's hierarchical workspace pattern — adding report section grouping, collapsible sections, setup page isolation, and expanded module organization — while preserving UltrERP's permission-based filtering and i18n strengths.

## Business Value

- Users get a more organized navigation structure matching industry-standard ERP patterns
- Reports and setup pages are visually segregated from primary workflow items
- Collapsible sections reduce visual clutter for power users
- Navigation mirrors ERPNext familiarity for users migrating from that platform
- Maintains UltrERP's permission-based visibility and multilingual support

## Research Findings Summary

*(Full research: inline investigation of `/reference/erpnext-develop` workspace_sidebar configs and `/src/lib/navigation.tsx`)*

### ERPNext Navigation Architecture

ERPNext defines navigation in **Workspace Sidebar** DocType configurations (JSON):

```json
{
  "doctype": "Workspace Sidebar",
  "header_icon": "crm",
  "items": [
    { "type": "Link", "label": "Home", "link_to": "CRM", "link_type": "Dashboard" },
    { "type": "Link", "label": "Lead", "link_to": "Lead", "link_type": "DocType" },
    { "type": "Section Break", "indent": 1, "label": "Reports" },
    { "type": "Link", "child": 1, "label": "Sales Analytics", "link_type": "Report" }
  ]
}
```

### Key ERPNext Patterns

| Pattern | Implementation |
|---------|----------------|
| Hierarchical grouping | Section Break with `indent: 1` creates child items |
| Report segregation | Dedicated "Reports" section with indentation |
| Setup isolation | "Setup" or "Settings" as separate section breaks |
| Icon assignment | Icon defined per-item in workspace config |
| Module isolation | Each workspace (CRM, Selling, Buying, etc.) has own sidebar |

### UltrERP Current State

**Architecture:**
```
src/components/ui/sidebar.tsx      → Base sidebar primitives
src/components/AppNavigation.tsx   → Main navigation component  
src/lib/navigation.tsx             → Static navigation config
src/hooks/useSidebar.tsx           → Sidebar state management
```

**Current Strengths:**
1. ✅ Permission filtering - Items filtered by `canAccess(item.feature)`
2. ✅ i18n support - Labels use translation keys
3. ✅ Icon-only collapsed mode - Clean icon-only state
4. ✅ Mobile responsive - Separate mobile/desktop states
5. ✅ Type safety - Full TypeScript with `NavigationGroup` interface

**Current Limitations:**

| Issue | ERPNext Has | UltrERP Missing |
|-------|-------------|-----------------|
| Report grouping | ✅ Dedicated sections | ❌ Mixed with docs |
| Nested items | ✅ Indented children | ❌ Flat list only |
| Per-section collapse | ✅ `collapsible: 1` | ❌ Cannot collapse sections |
| Dynamic config | ✅ Database-driven | ❌ Hard-coded |
| Quick actions | ✅ Dashboard shortcuts | Partial |

## Scope

**Phase 1: Structural Enhancements (P1)**
- Add Report section grouping to navigation groups
- Expand navigation groups to match ERPNext module organization
- Add collapsible section capability to `SidebarGroup`

**Phase 2: Feature Parity (P2)**
- Add quick action shortcuts integration
- Visual polish (icons, spacing) to match ERPNext patterns
- Add section-level icon support

**Phase 3: Future Consideration (P3)**
- Dynamic workspace config (backend API-driven)
- User-customizable sidebar layout

## Technical Approach

### Navigation Structure

```typescript
interface NavigationItem {
  feature: AppFeature;
  label: string;      // i18n key
  to: string;
  icon: LucideIcon;
  badge?: string;     // Optional badge text
}

interface NavigationSection {
  label: string;      // i18n key
  type: 'reports' | 'setup' | 'standard';
  items: NavigationItem[];
}

interface NavigationGroup {
  label: string;      // i18n key
  sections: NavigationSection[];
}
```

### Collapsible Sections

```typescript
interface SidebarGroupProps {
  collapsible?: boolean;
  defaultCollapsed?: boolean;
  onToggle?: (collapsed: boolean) => void;
}
```

## Dependencies

- Epic 22 (UI Foundation) for Toast, Breadcrumb patterns
- Epic 14 (i18n) for translation key additions

## Non-Goals

- Complete backend-driven navigation (Epic 37 covers integration patterns)
- Customizable sidebar layouts (future epic)
- Drag-and-drop reordering

---

## Story 38.1: Report Section Grouping and Navigation Group Expansion

**As a user,**
I want reports organized in dedicated sections within each navigation group,
So that I can quickly find analytics and reporting tools separate from primary workflow items.

**As a developer,**
I want to expand the navigation groups to match ERPNext's module organization,
So that the sidebar structure is familiar to users migrating from ERPNext.

**Acceptance Criteria:**

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

## Story 38.2: Collapsible Navigation Sections

**As a user,**
I want to collapse navigation sections I don't use frequently,
So that I can reduce visual clutter and focus on my primary workflow.

**Acceptance Criteria:**

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

## Story 38.3: Quick Action Shortcuts Integration

**As a user,**
I want quick action shortcuts visible in the sidebar,
So that I can quickly create new records without navigating to the full form.

**Acceptance Criteria:**

**Given** the sidebar is in expanded mode
**When** the user scrolls to the bottom of the navigation
**Then** a "Quick Actions" section appears with shortcuts:
  - Create Lead
  - Create Opportunity  
  - Create Invoice
  - Create Order

**Given** a quick action shortcut
**When** clicked
**Then** navigation closes (on mobile)
**And** user is navigated to the creation form

**Given** sidebar is in collapsed mode
**When** quick actions are configured
**Then** quick actions are NOT shown (icons only mode)

---

## Story 38.4: Navigation Visual Polish

**As a user,**
I want the sidebar to match ERPNext's visual patterns,
So that the interface feels professional and familiar.

**Acceptance Criteria:**

**Given** section headers
**When** rendered
**Then** they display uppercase text with tracking
**And** optional icon before the label

**Given** a report or setup section item
**When** rendered
**Then** it has additional left padding (24px indent)

**Given** the active navigation item
**When** rendered
**Then** it has blue accent color
**And** a chevron indicator on the right

**Given** a collapsed section item  
**When** hovered
**Then** subtle transform: translateX(2px) animation
