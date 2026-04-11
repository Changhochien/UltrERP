# Low Stock Alert System — UI/UX Design Specification

**Document Version:** 1.0  
**Date:** 2026-04-11  
**Status:** Draft  
**Author:** UX/UI Design

---

## Table of Contents

1. [Design System Foundation](#1-design-system-foundation)
2. [Alert Dashboard Page](#2-alert-dashboard-page)
3. [Alert Panel/Sidebar](#3-alert-panelsidebar)
4. [Dashboard Widget](#4-dashboard-widget)
5. [Alert Detail Drawer](#5-alert-detail-drawer)
6. [Product Detail Integration](#6-product-detail-integration)
7. [Mobile Views](#7-mobile-views)
8. [Real-time Updates](#8-real-time-updates)
9. [Interaction Flows](#9-interaction-flows)
10. [Component Specifications](#10-component-specifications)
11. [Accessibility Requirements](#11-accessibility-requirements)

---

## 1. Design System Foundation

### 1.1 Color Palette

| Token | Hex | Usage |
|-------|-----|-------|
| `--alert-critical` | `#DC2626` | Critical alerts (stockout, < 25% ROP) |
| `--alert-critical-bg` | `#FEF2F2` | Critical alert background |
| `--alert-warning` | `#D97706` | Warning alerts (below ROP) |
| `--alert-warning-bg` | `#FFFBEB` | Warning alert background |
| `--alert-info` | `#2563EB` | Info alerts (approaching ROP) |
| `--alert-info-bg` | `#EFF6FF` | Info alert background |
| `--alert-success` | `#16A34A` | Resolved state |
| `--alert-success-bg` | `#F0FDF4` | Success background |

### 1.2 Typography

| Style | Font | Size | Weight |
|-------|------|------|--------|
| Page Title | System | 28px | 600 |
| Section Header | System | 18px | 600 |
| Table Header | System | 11px | 600 (uppercase, 0.18em tracking) |
| Body Text | System | 14px | 400 |
| Small Text | System | 12px | 400 |
| Badge Text | System | 11px | 600 (uppercase, 0.18em tracking) |

### 1.3 Spacing System

| Token | Value | Usage |
|-------|-------|-------|
| `--space-xs` | 4px | Icon gaps, inline spacing |
| `--space-sm` | 8px | Compact list items |
| `--space-md` | 16px | Card padding, section gaps |
| `--space-lg` | 24px | Page sections |
| `--space-xl` | 32px | Major section divisions |

### 1.4 Border Radius

| Token | Value | Usage |
|-------|-------|-------|
| `--radius-sm` | 6px | Buttons, inputs |
| `--radius-md` | 8px | Cards, panels |
| `--radius-lg` | 12px | Drawers, modals |
| `--radius-full` | 9999px | Badges, pills |

### 1.5 Elevation

| Level | Shadow | Usage |
|-------|--------|-------|
| Low | `0 1px 2px rgba(0,0,0,0.05)` | Cards, table rows |
| Medium | `0 4px 6px rgba(0,0,0,0.1)` | Dropdowns, popovers |
| High | `0 20px 25px rgba(0,0,0,0.15)` | Modals, drawers |

### 1.6 Motion

| Animation | Duration | Easing | Usage |
|-----------|----------|--------|-------|
| Micro-interaction | 150ms | ease-out | Button hover, badge updates |
| Panel slide | 250ms | ease-in-out | Drawer open/close |
| Fade in/out | 200ms | ease | Toast notifications |
| Loading pulse | 1.5s | ease-in-out | Skeleton shimmer |

---

## 2. Alert Dashboard Page

**Route:** `/inventory/alerts`  
**Access:** Warehouse Managers, Purchasing Staff, Admin

### 2.1 Layout Structure

```
┌─────────────────────────────────────────────────────────────────────┐
│ [PageHeader]                                                        │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │ Low Stock Alerts                               [Warehouse ▾]   │ │
│ │ Manage and triage inventory alerts across all warehouses       │ │
│ └─────────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────┤
│ [MetricCards]                                                      │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ │
│ │ CRITICAL    │ │ WARNING     │ │ RESOLVED    │ │ AVG RESPONSE│ │
│ │    12       │ │    34       │ │   156       │ │   2.3 hrs   │ │
│ │ ▲ 3 today   │ │ ▼ 5 today   │ │ Today: 8    │ │             │ │
│ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ │
├─────────────────────────────────────────────────────────────────────┤
│ [DataTable]                                                        │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │ [Filters ▾] [Severity ▾] [Warehouse ▾] [Date Range ▾] [⌕]    │ │
│ ├─────────────────────────────────────────────────────────────────┤ │
│ │ ☐ │ Severity │ Product      │ Warehouse │ Stock │ Days │ Act │ │
│ │───│──────────│──────────────│───────────│───────│──────│─────│ │
│ │ ☐ │ 🔴 CRIT  │ Widget Pro X  │ Main      │ 3/25  │ 0.5  │ ⋯   │ │
│ │ ☐ │ 🟠 WARN  │ Gadget 2000   │ East      │ 18/50 │ 2.1  │ ⋯   │ │
│ │ ☐ │ 🔴 CRIT  │ Component A   │ Main      │ 0/10  │ 0.0  │ ⋯   │ │
│ └─────────────────────────────────────────────────────────────────┘ │
│ [Bulk Actions Bar - shows when items selected]                     │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │ 5 selected │ [Acknowledge All] [Export] [Dismiss]             │ │
│ └─────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Filters

| Filter | Type | Options | Default |
|--------|------|---------|---------|
| Status | Multi-select dropdown | PENDING, ACKNOWLEDGED, SNOOZED, DISMISSED, RESOLVED | All |
| Severity | Multi-select dropdown | CRITICAL, WARNING, INFO | All |
| Warehouse | Single-select dropdown | All warehouses + "All" | Current warehouse |
| Category | Single-select dropdown | All categories | All |
| Date Range | Date range picker | Presets: Today, 7 days, 30 days, Custom | 7 days |
| Search | Text input | Product name, SKU | Empty |

### 2.3 Table Columns

| Column ID | Header | Width | Sortable | Sort Priority |
|-----------|--------|-------|----------|----------------|
| `select` | Checkbox | 48px | No | - |
| `severity` | Severity | 100px | Yes | 1 (default) |
| `product` | Product | flex | Yes | 2 |
| `warehouse` | Warehouse | 140px | Yes | - |
| `current_stock` | Current Stock | 120px | Yes | 3 |
| `reorder_point` | ROP | 100px | Yes | - |
| `days_until_stockout` | Days Left | 80px | Yes | - |
| `created_at` | Created | 120px | Yes | - |
| `status` | Status | 120px | Yes | - |
| `actions` | Actions | 80px | No | - |

### 2.4 Column Cell Specifications

#### Severity Column
```
┌──────────────────────────────────────┐
│ [🔴 CRITICAL]  or  [🟠 WARNING]     │
│                    or  [🔵 INFO]     │
└──────────────────────────────────────┘
```
- Badge with severity-appropriate background color
- Pulse animation for CRITICAL alerts that are > 1 hour old
- Tooltip on hover showing severity calculation

#### Product Column
```
┌──────────────────────────────────────┐
│ ┌────┐ Widget Pro X                  │
│ │ 🖼️ │ SKU: WPG-X-001                │
│ └────┘ Category: Electronics        │
└──────────────────────────────────────┘
```
- 32x32px product image placeholder (or thumbnail)
- Product name (truncate with ellipsis if > 40 chars)
- SKU in muted text below

#### Stock Column
```
┌──────────────────────────────────────┐
│        3  /  25                      │
│   ████████░░░░░░░░░░░░░ (12%)       │
└──────────────────────────────────────┘
```
- Current stock / Reorder point
- Mini progress bar showing stock percentage
- Red fill if below ROP

#### Actions Column
```
┌──────────────────────────────────────┐
│ [⋮] (dropdown)                       │
│   • View Details                      │
│   • Acknowledge                       │
│   • Snooze (1h, 4h, 24h)             │
│   • Create Purchase Order             │
│   • Dismiss                            │
└──────────────────────────────────────┘
```

### 2.5 Bulk Actions Bar

Appears as a sticky bar at the bottom when items are selected:

```
┌─────────────────────────────────────────────────────────────────────┐
│ ☐ 5 selected │ Total items: 5 CRITICAL, 2 WARNING                 │
│              │ [Acknowledge All] [Create PO] [Export CSV] [Dismiss]│
└─────────────────────────────────────────────────────────────────────┘
```

**States:**
- Hidden when no items selected
- Visible with animation slide-up when items selected
- Shows count breakdown by severity
- Auto-hides when selection cleared

### 2.6 Empty State

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│                         🎉                                         │
│                                                                     │
│                   No alerts match your filters                      │
│                                                                     │
│        All inventory is healthy! No stock issues detected.         │
│                                                                     │
│              [Clear all filters]                                    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.7 Loading State

- Skeleton rows with shimmer animation
- Maintain table structure during load
- 6 skeleton rows by default

---

## 3. Alert Panel/Sidebar

**Location:** Inventory page right sidebar (380px width)  
**Purpose:** Compact view of urgent alerts

### 3.1 Layout Structure

```
┌─────────────────────────────────────┐
│ Reorder Alerts                [12]  │
│ Critical stock alerts requiring... │
├─────────────────────────────────────┤
│ [Status ▾]            [🔄 Refresh]   │
├─────────────────────────────────────┤
│ ┌─────────────────────────────────┐ │
│ │ 🔴 CRITICAL                     │ │
│ │ Widget Pro X                    │ │
│ │ Main Warehouse · 3/25 units     │ │
│ │ [Acknowledge]                   │ │
│ └─────────────────────────────────┘ │
│ ┌─────────────────────────────────┐ │
│ │ 🟠 WARNING                      │ │
│ │ Gadget 2000                     │ │
│ │ East Warehouse · 18/50 units   │ │
│ │ [Acknowledge]                   │ │
│ └─────────────────────────────────┘ │
│ ┌─────────────────────────────────┐ │
│ │ 🔵 INFO                         │ │
│ │ Component B                     │ │
│ │ Main Warehouse · 40/50 units   │ │
│ │ [Acknowledge]                   │ │
│ └─────────────────────────────────┘ │
│ ... (scrollable, max 5 visible)     │
├─────────────────────────────────────┤
│ [View All Alerts →]                 │
└─────────────────────────────────────┘
```

### 3.2 Alert Card States

**Critical Alert Card:**
```
┌─────────────────────────────────────┐
│ 🔴 CRITICAL                        │
│ Widget Pro X (SKU: WPG-X-001)      │
│ Main Warehouse · 3/25 units        │
│ Created: 2 hours ago               │
│                                    │
│ [Acknowledge]      [View →]        │
└─────────────────────────────────────┘
```

- Red left border accent (4px)
- Subtle red background tint
- Pulsing dot indicator for CRITICAL alerts

**Warning Alert Card:**
```
┌─────────────────────────────────────┐
│ 🟠 WARNING                         │
│ Gadget 2000 (SKU: GAD-2000)        │
│ East Warehouse · 18/50 units       │
│ Created: 4 hours ago               │
│                                    │
│ [Acknowledge]                      │
└─────────────────────────────────────┘
```

- Orange left border accent (4px)
- Subtle orange background tint

**Acknowledged Alert Card:**
```
┌─────────────────────────────────────┐
│ Acknowledged                        │
│ Widget Pro X                        │
│ Main Warehouse · 3/25 units         │
│ Acknowledged: 30 min ago           │
└─────────────────────────────────────┘
```

- Gray styling
- No action buttons
- "Acknowledged by [username]" on hover tooltip

### 3.3 Interaction Behaviors

| Action | Behavior |
|--------|----------|
| Click "Acknowledge" | Optimistic update, shows loading spinner, reloads panel on success |
| Click card | Opens Alert Detail Drawer |
| Click "View All" | Navigate to `/inventory/alerts` |
| Pull to refresh | Reloads alert data |

---

## 4. Dashboard Widget

**Location:** Homepage / Dashboard page  
**Type:** KPI Card component

### 4.1 Layout Structure

```
┌─────────────────────────────────────────────┐
│ Stock Alerts                                 │
├─────────────────────────────────────────────┤
│                                             │
│    🔴 12        🟠 34                        │
│  CRITICAL     WARNING                       │
│                                             │
│    ▲ 3 today   ▼ 5 today                    │
│                                             │
│    ┌─────────────────────────────────────┐  │
│    │ [View All Alerts]                   │  │
│    └─────────────────────────────────────┘  │
│                                             │
└─────────────────────────────────────────────┘
```

### 4.2 Widget States

**Healthy State (no alerts):**
```
┌─────────────────────────────────────────────┐
│ Stock Alerts                                 │
├─────────────────────────────────────────────┤
│                                             │
│           ✓                                 │
│     All inventory healthy                    │
│                                             │
└─────────────────────────────────────────────┘
```

**Critical State:**
- Red accent border
- Pulsing animation
- Prominent "View All" button

### 4.3 Click Behavior

- Click anywhere on card → Navigate to `/inventory/alerts?severity=CRITICAL`
- Filter pre-applied to show critical alerts first

---

## 5. Alert Detail Drawer

**Trigger:** Click on alert row or card  
**Width:** 480px (desktop), full-width (mobile)  
**Position:** Right side, slide-in animation

### 5.1 Layout Structure

```
┌─────────────────────────────────────────────────────────────────────┐
│ [×]                                                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ [Product Image]                                                 │ │
│  │ 64x64px, rounded corners                                        │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  Widget Pro X                                                       │
│  SKU: WPG-X-001 · Category: Electronics                             │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ 🔴 CRITICAL — Stockout Risk                                    │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│  CURRENT STOCK                                                      │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │                                                                 │  │
│  │      3  /  25                                                   │  │
│  │      units  /  reorder point                                   │  │
│  │                                                                 │  │
│  │      ████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░ (12%)            │  │
│  │                                                                 │  │
│  │      ⚠️ Estimated stockout in 0.5 days                          │  │
│  │                                                                 │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│  STOCK HISTORY (Last 30 Days)                                       │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  ┌─────────────────────────────────────────────────────────┐   │  │
│  │  │📈 [Mini Sparkline Chart]                                │   │  │
│  │  │   Stock level trend from 50 → 3 units                  │   │  │
│  │  └─────────────────────────────────────────────────────────┘   │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│  SUGGESTED ORDER                                                    │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  Supplier: Acme Supply Co.                          [Best]   │  │
│  │  Lead Time: 3-5 days                                        │  │
│  │                                                                 │  │
│  │  Recommended Quantity: 100 units                             │  │
│  │  Estimated Cost: $2,450.00                                    │  │
│  │                                                                 │  │
│  │  [Create Purchase Order]                                       │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│  QUICK ACTIONS                                                      │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  [Adjust Stock]    [Transfer Stock]    [Snooze Alert]          │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│  TIMELINE                                                           │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │                                                                 │  │
│  │  ● Apr 11, 2026 09:00 AM — Alert Created                       │  │
│  │  │  Stock fell below reorder point (3/25)                      │  │
│  │  │                                                             │  │
│  │  ○ Apr 10, 2026 02:30 PM — Stock Level: 15 units              │  │
│  │  │                                                             │  │
│  │  ○ Apr 08, 2026 10:00 AM — Stock Level: 25 units (ROP hit)    │  │
│  │  │                                                             │  │
│  │  ○ Apr 05, 2026 03:00 PM — Stock Level: 50 units              │  │
│  │                                                                 │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│  [Dismiss Alert]                                                    │
└─────────────────────────────────────────────────────────────────────┘
```

### 5.2 Component Specifications

#### Product Info Section
- Product image: 64x64px with rounded-lg corners
- Fallback: Package icon with category color
- Product name: 20px semibold
- SKU and category: 13px muted text

#### Severity Banner
- Full-width colored banner
- Icon + Severity Level + Description
- CRITICAL: Red background with white text
- WARNING: Orange background with dark text
- INFO: Blue background with white text

#### Stock Display
- Large number typography: 36px monospace
- Visual progress bar with color coding
- Percentage calculation: `(current / reorder_point) * 100`

#### Stock History Mini-Chart
```
┌────────────────────────────────────────────────────────────────┐
│                                                                │
│   50├ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─          │
│      │                                    ╱                    │
│   40├ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ╱                      │
│      │                              ╱                          │
│   30├ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ╱                              │
│      │                        ╱                                  │
│   20├ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ╱                                     │
│      │              ╱                                             │
│   10├ ─ ─ ─ ─ ─ ─ ╱                                               │
│      │        ╱                                                   │
│    0├ ─ ─ ─╱                                                     │
│      └────┴────┴────┴────┴────┴────┴────┴────┴────┴────┴────  │
│        Apr 05  Apr 08  Apr 10  Apr 11                           │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```
- SVG sparkline chart
- 30-day data points
- Hover tooltip showing date and stock level
- Reorder point line (dashed)

#### Suggested Order Section
- Supplier card with rating
- Lead time estimate
- Recommended quantity calculation breakdown
- Create PO button (primary action)

#### Quick Actions
- Three equal-width buttons
- Adjust Stock: Opens stock adjustment modal
- Transfer Stock: Opens transfer modal
- Snooze Alert: Dropdown with duration options

#### Timeline
- Vertical timeline with dot markers
- Past events: hollow dots
- Current/latest event: filled dot
- Event types: Alert Created, Stock Adjusted, Alert Acknowledged, etc.

### 5.3 Drawer Actions

| Action | Button Style | Behavior |
|--------|--------------|----------|
| Create Purchase Order | Primary (filled) | Opens PO creation with product pre-filled |
| Adjust Stock | Secondary (outline) | Opens stock adjustment modal |
| Snooze Alert | Secondary (outline) | Dropdown: 1h, 4h, 24h, Custom |
| Dismiss Alert | Ghost (text) | Confirmation dialog, then dismisses |
| Acknowledge | Primary (filled) | Quick acknowledge if not yet acknowledged |

---

## 6. Product Detail Integration

**Location:** Product Detail Page (`/inventory/:productId`)  
**Purpose:** Low stock indicators within product context

### 6.1 Stock Status Badge

```
┌─────────────────────────────────────────────────────────────────────┐
│ Header Section                                                       │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │ [← Back to Inventory]                                            │ │
│ │                                                                  │ │
│ │ [Image] Widget Pro X                           [Edit] [Delete]   │ │
│ │           SKU: WPG-X-001                                          │ │
│ │                                                                  │ │
│ │ [Category] [Status]  ┌─────────────────┐                        │ │
│ │                      │ 🔴 LOW STOCK     │  ← Badge added         │ │
│ │                      └─────────────────┘                        │ │
│ └─────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

**Badge Variants:**

| Stock Status | Badge | Condition |
|--------------|-------|-----------|
| Critical | `🔴 LOW STOCK - STOCKOUT RISK` | Stock = 0 or < 25% ROP |
| Warning | `🟠 LOW STOCK` | Stock < ROP |
| Healthy | `🟢 IN STOCK` | Stock >= ROP |

### 6.2 Alert History Tab

Within product detail, new "Alerts" tab:

```
┌─────────────────────────────────────────────────────────────────────┐
│ [Overview] [Stock] [Alerts] [History] [Orders]                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Alert History                                          [Export]    │
│                                                                     │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ Date        │ Type           │ Status   │ Warehouse │ Actions │ │
│  │─────────────│────────────────│──────────│───────────│─────────│ │
│  │ Apr 11, 2026│ Stock Warning   │ PENDING  │ Main      │ [View]  │ │
│  │ Apr 05, 2026│ Stock Warning   │ RESOLVED │ Main      │ [View]  │ │
│  │ Mar 28, 2026│ Reorder Created │ RESOLVED │ Main      │ [View]  │ │
│  │ Mar 15, 2026│ Stock Warning   │ RESOLVED │ East      │ [View]  │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  Alert Frequency: 1 per 12 days average                             │
│  Total Alerts: 24 (18 resolved, 2 active)                          │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 6.3 Quick Reorder Button

In the stock section:

```
┌─────────────────────────────────────────────────────────────────────┐
│ Stock by Warehouse                                                  │
│                                                                     │
│  Main Warehouse                                    [Reorder Now]     │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                                                                 │ │
│  │   25 units (ROP: 25)                                          │ │
│  │   ⚠️ Below reorder point                                       │ │
│  │                                                                 │ │
│  │   Suggested Order: 100 units from Acme Supply                  │ │
│  │                                                                 │ │
│  │   [Adjust Stock]  [Reorder Now]                                │ │
│  │                                                                 │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 7. Mobile Views

**Breakpoint:** < 768px

### 7.1 Alert List View (Mobile)

```
┌─────────────────────────────────────┐
│ ☰  Low Stock Alerts           [🔔] │
├─────────────────────────────────────┤
│                                     │
│ [Filters ▾]                         │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ 🔴 Widget Pro X                 │ │
│ │    Main Warehouse               │ │
│ │    3 / 25 units                 │ │
│ │    Est. stockout: 0.5 days      │ │
│ │    [Acknowledge]                │ │
│ └─────────────────────────────────┘ │
│ ┌─────────────────────────────────┐ │
│ │ 🟠 Gadget 2000                  │ │
│ │    East Warehouse              │ │
│ │    18 / 50 units                │ │
│ │    Est. stockout: 2.1 days      │ │
│ │    [Acknowledge]                │ │
│ └─────────────────────────────────┘ │
│                                     │
│ [Swipe ← Right: Acknowledge]        │
│ [Swipe → Left: Dismiss]             │
│                                     │
└─────────────────────────────────────┘
```

### 7.2 Swipe Actions

| Swipe Direction | Action | Visual Feedback |
|-----------------|--------|-----------------|
| Swipe right | Acknowledge | Green background, checkmark icon |
| Swipe left | Dismiss | Red background, X icon |
| Partial swipe | Reveal action button | Tap to confirm |

### 7.3 Bottom Sheet for Details

```
┌─────────────────────────────────────┐
│                                     │
│         ─ ─ ─                      │
│                                     │
│  Widget Pro X                       │
│  SKU: WPG-X-001                     │
│                                     │
│  ┌─────────────────────────────────┐ │
│  │ 🔴 CRITICAL                     │ │
│  └─────────────────────────────────┘ │
│                                     │
│  Current Stock                      │
│  ┌─────────────────────────────────┐ │
│  │      3  /  25                    │ │
│  │      ████░░░░░░ (12%)          │ │
│  └─────────────────────────────────┘ │
│                                     │
│  [View Full Details →]              │
│                                     │
│  ┌─────────────────────────────────┐ │
│  │ Stock History                   │ │
│  │ [Mini Chart]                    │ │
│  └─────────────────────────────────┘ │
│                                     │
│  ┌─────────────────────────────────┐ │
│  │ [Create PO]   [Acknowledge]     │ │
│  └─────────────────────────────────┘ │
│                                     │
└─────────────────────────────────────┘
```

### 7.4 Mobile Metrics

```
┌─────────────────────────────────────┐
│                                     │
│  ┌───────────┐   ┌───────────┐      │
│  │ 🔴 12     │   │ 🟠 34     │      │
│  │ CRITICAL  │   │ WARNING   │      │
│  └───────────┘   └───────────┘      │
│                                     │
└─────────────────────────────────────┘
```

- 2-column grid for KPI cards
- Full-width buttons
- Bottom-fixed action bar

---

## 8. Real-time Updates

### 8.1 Toast Notifications

**Trigger:** New CRITICAL alert created  
**Position:** Top-right corner  
**Duration:** 8 seconds (CRITICAL), 5 seconds (WARNING)  
**Auto-dismiss:** Yes, unless hovered

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  🔴 CRITICAL STOCK ALERT                                │
│                                                         │
│  Widget Pro X is out of stock!                          │
│  Main Warehouse · 0 units remaining                     │
│                                                         │
│  [View Alert]  [Dismiss]                                │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Stacking:**
- Max 3 toasts visible
- New CRITICAL toasts push WARNING toasts down
- Older toasts fade out

### 8.2 Subtle Indicator for WARNING

**Location:** Alert Panel header badge  
**Behavior:** Subtle pulse animation on count change

```
┌─────────────────────────────────────┐
│ Reorder Alerts [12●]  ← Pulse on new│
│ Critical stock alerts requiring...   │
└─────────────────────────────────────┘
```

### 8.3 Navigation Badge Counts

**Sidebar Navigation:**
```
┌─────────────────────────────────────┐
│ [📦 Inventory]                      │
│                                     │
│ [⚠️ Alerts (12)]  ← Badge count    │
│                                     │
│ [📋 Orders]                         │
└─────────────────────────────────────┘
```

**Badge Specifications:**
- Max display: "99+"
- Color: Red for CRITICAL count, Orange for total count
- Animation: Scale pop on new alert

### 8.4 WebSocket Events

| Event | UI Update |
|-------|-----------|
| `alert:created` | Toast (if CRITICAL), Badge increment, List prepend |
| `alert:acknowledged` | Row update, Badge decrement |
| `alert:resolved` | Row update with strikethrough, Badge decrement |
| `alert:snoozed` | Row update with snooze indicator |
| `alert:dismissed` | Row fade out and remove |

---

## 9. Interaction Flows

### 9.1 Acknowledge Alert Flow

```
User clicks "Acknowledge"
        │
        ▼
┌───────────────────┐
│ Optimistic Update │  ← UI updates immediately
│ Status → Pending  │
└───────────────────┘
        │
        ▼
┌───────────────────┐
│ API Call          │
│ POST /acknowledge │
└───────────────────┘
        │
        ├─── Success ─────────────────────────────────────┐
        │                                                 ▼
        │                                    ┌───────────────────┐
        │                                    │ Success Feedback  │
        │                                    │ Badge decrements  │
        │                                    │ Toast: "Alert     │
        │                                    │ acknowledged"     │
        │                                    └───────────────────┘
        │
        └─── Failure ─────────────────────────────────────┐
        │                                                 ▼
        │                                    ┌───────────────────┐
        │                                    │ Error Toast        │
        │                                    │ "Failed to        │
        │                                    │ acknowledge"       │
        │                                    │                    │
        │                                    │ Rollback UI        │
        │                                    │ Status → Pending   │
        │                                    └───────────────────┘
```

### 9.2 Create Purchase Order Flow

```
User clicks "Create Purchase Order" from Alert Detail
        │
        ▼
┌───────────────────┐
│ Pre-fill PO Form  │
│ - Product         │
│ - Quantity         │
│ - Supplier         │
│ - Warehouse       │
└───────────────────┘
        │
        ▼
┌───────────────────┐
│ Open PO Modal     │
│ User reviews and  │
│ confirms details  │
└───────────────────┘
        │
        ├─── Confirm ─────────────────────────────────────┐
        │                                                 ▼
        │                                    ┌───────────────────┐
        │                                    │ API Call          │
        │                                    │ POST /orders      │
        │                                    └───────────────────┘
        │                                                 │
        │                                    ┌───────────────────┐
        │                                    │ Success           │
        │                                    │ Alert status →    │
        │                                    │ RESOLVED          │
        │                                    │                   │
        │                                    │ Toast: "PO        │
        │                                    │ created"          │
        │                                    └───────────────────┘
        │
        └─── Cancel ─────────────────────────────────────┐
                                                         ▼
                                              ┌───────────────────┐
                                              │ Modal closes      │
                                              │ Alert unchanged   │
                                              └───────────────────┘
```

### 9.3 Snooze Alert Flow

```
User clicks "Snooze" on alert
        │
        ▼
┌───────────────────┐
│ Dropdown appears  │
│ [1 hour]          │
│ [4 hours]         │
│ [24 hours]        │
│ [Custom date/time]│
└───────────────────┘
        │
        ▼
User selects duration
        │
        ▼
┌───────────────────┐
│ API Call          │
│ POST /snooze      │
│ duration: 4h      │
└───────────────────┘
        │
        ▼
┌───────────────────┐
│ Success           │
│ Alert status →    │
│ SNOOZED           │
│ Countdown shown   │
│ "Resumes in 4h"   │
└───────────────────┘
```

### 9.4 Bulk Acknowledge Flow

```
User selects multiple alerts (checkboxes)
        │
        ▼
┌───────────────────┐
│ Bulk Actions Bar  │
│ appears at bottom │
│ "5 selected"     │
│ [Acknowledge All] │
└───────────────────┘
        │
        ▼
User clicks "Acknowledge All"
        │
        ▼
┌───────────────────┐
│ Confirmation      │
│ "Acknowledge 5    │
│ alerts?"          │
│ [Cancel] [Confirm]│
└───────────────────┘
        │
        ▼
┌───────────────────┐
│ Batch API Call    │
│ POST /acknowledge │
│ { ids: [...] }    │
└───────────────────┘
        │
        ▼
┌───────────────────┐
│ Progress: 2/5... │
│ 4/5...            │
│ 5/5... ✓          │
└───────────────────┘
        │
        ▼
┌───────────────────┐
│ Summary Toast     │
│ "5 alerts         │
│ acknowledged"     │
│                   │
│ List refreshes    │
└───────────────────┘
```

---

## 10. Component Specifications

### 10.1 AlertBadge

```tsx
interface AlertBadgeProps {
  severity: 'CRITICAL' | 'WARNING' | 'INFO';
  size?: 'sm' | 'md' | 'lg';
  pulse?: boolean;
}
```

| Variant | Background | Text | Border |
|---------|------------|------|--------|
| CRITICAL | `#FEF2F2` | `#DC2626` | `#FEE2E2` |
| WARNING | `#FFFBEB` | `#D97706` | `#FDE68A` |
| INFO | `#EFF6FF` | `#2563EB` | `#BFDBFE` |

### 10.2 AlertCard

```tsx
interface AlertCardProps {
  alert: ReorderAlertItem;
  variant: 'compact' | 'expanded';
  onAcknowledge: (id: string) => void;
  onViewDetails: (id: string) => void;
}
```

**States:**
- Default: Standard card styling
- Hover: Elevated shadow, subtle background shift
- Loading: Skeleton with shimmer
- Acknowledged: Muted colors, no action buttons

### 10.3 AlertDetailDrawer

```tsx
interface AlertDetailDrawerProps {
  alertId: string | null;
  onClose: () => void;
  onCreatePO: (productId: string, suggestedQty: number) => void;
  onAdjustStock: (productId: string, warehouseId: string) => void;
}
```

**Props for child components:**
- `StockMiniChart`: 30-day stock history data points
- `SupplierCard`: Recommended supplier with lead time
- `AlertTimeline`: Event history array

### 10.4 AlertFilters

```tsx
interface AlertFiltersProps {
  filters: AlertFilterState;
  onFiltersChange: (filters: AlertFilterState) => void;
  warehouses: Warehouse[];
  categories: string[];
}
```

### 10.5 AlertKPICard

```tsx
interface AlertKPICardProps {
  criticalCount: number;
  warningCount: number;
  criticalTrend: number; // positive = up, negative = down
  warningTrend: number;
  onClick: () => void;
}
```

### 10.6 AlertTable

```tsx
interface AlertTableProps {
  alerts: ReorderAlertItem[];
  selectedIds: Set<string>;
  onSelectionChange: (ids: Set<string>) => void;
  onSort: (column: string, direction: 'asc' | 'desc') => void;
  onRowClick: (alert: ReorderAlertItem) => void;
  loading?: boolean;
}
```

### 10.7 AlertTimeline

```tsx
interface AlertTimelineProps {
  events: AlertTimelineEvent[];
}
```

### 10.8 BulkActionsBar

```tsx
interface BulkActionsBarProps {
  selectedCount: number;
  selectedItems: ReorderAlertItem[];
  onAcknowledgeAll: (ids: string[]) => void;
  onExport: (ids: string[]) => void;
  onDismiss: (ids: string[]) => void;
  onClearSelection: () => void;
}
```

### 10.9 StockHealthBar

```tsx
interface StockHealthBarProps {
  current: number;
  reorderPoint: number;
  showLabel?: boolean;
}
```

### 10.10 StockMiniChart

```tsx
interface StockMiniChartProps {
  dataPoints: StockDataPoint[];
  reorderPoint: number;
  height?: number;
}
```

---

## 11. Accessibility Requirements

### 11.1 Keyboard Navigation

| Key | Action |
|-----|--------|
| Tab | Navigate between interactive elements |
| Enter/Space | Activate buttons, expand rows |
| Escape | Close drawers, modals, clear selection |
| Arrow Up/Down | Navigate table rows |
| Ctrl+A | Select all visible alerts |

### 11.2 Screen Reader Support

| Element | ARIA Attribute | Value |
|---------|----------------|-------|
| Alert row | `role="row"` | - |
| Severity badge | `aria-label` | "Severity: Critical" |
| Stock level | `aria-label` | "Current stock: 3 of 25 units, 12 percent" |
| Action dropdown | `aria-haspopup="menu"` | - |
| Loading state | `aria-busy="true"` | - |
| Live updates | `aria-live="polite"` | On alert list |

### 11.3 Color Contrast

- All text meets WCAG 2.1 AA contrast ratio (4.5:1 minimum)
- Severity colors distinguishable without color alone
- Focus indicators visible on all interactive elements

### 11.4 Motion Preferences

```css
@media (prefers-reduced-motion: reduce) {
  .pulse-animation,
  .slide-in,
  .fade-in {
    animation: none;
    transition: none;
  }
}
```

---

## Appendix: Component File Structure

```
src/
├── domain/
│   └── inventory/
│       └── components/
│           └── alerts/
│               ├── AlertBadge.tsx
│               ├── AlertCard.tsx
│               ├── AlertDetailDrawer.tsx
│               ├── AlertFilters.tsx
│               ├── AlertKPICard.tsx
│               ├── AlertTable.tsx
│               ├── AlertTimeline.tsx
│               ├── BulkActionsBar.tsx
│               ├── StockHealthBar.tsx
│               ├── StockMiniChart.tsx
│               ├── AlertsPage.tsx
│               └── index.ts
├── hooks/
│   └── alerts/
│       ├── useAlerts.ts
│       ├── useAlertDetail.ts
│       ├── useAcknowledgeAlert.ts
│       ├── useSnoozeAlert.ts
│       ├── useDismissAlert.ts
│       └── useAlertNotifications.ts
└── lib/
    └── api/
        └── inventory/
            └── alerts.ts
```

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-11 | UX/UI Design | Initial draft |
