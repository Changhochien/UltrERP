# UI/UX Gap Analysis: ERPnext vs UltrERP

**Date:** 2026-04-20
**Sources:** `.omc/research/erpnext-ui-design.md`, `.omc/research/ultrerp-ui-design.md`

---

## 1. Component Comparison Table

| Component | ERPnext | UltrERP | Gap |
|-----------|---------|---------|-----|
| **Framework** | Jinja2 + Vanilla JS + Bootstrap 4 | React 19 + Vite + Tailwind CSS v4 + Radix UI | N/A |
| **Form Fields** | Server-rendered via Frappe DocType | Field component (vertical/horizontal/responsive) + Input/Select/Textarea | UltrERP lacks Link (autocomplete), Dynamic Link field types |
| **Child Tables** | HTML table with inline editing, row numbers, stock color indicators | InvoiceLineEditor exists but no generic reusable child table | No inline editing, no row numbers, no stock indicators |
| **Date Picker** | Native date input (browser) | Native `<input type="date">` only | **Missing calendar picker component** |
| **File Upload** | Attach/AttachImage field types | No file upload component | **Missing** |
| **Item Selector** | Grid with images, search, quantity badges, barcode scanning | No equivalent | **Missing** |
| **Modals/Dialogs** | `frappe.ui.Dialog`, Bootstrap modals | Dialog, Sheet (Radix) | Functional parity, but UltrERP lacks quick-entry dialog pattern |
| **Toasts/Notifications** | `frappe.msgprint()`, `frappe.throw()` | None | **Missing toast notification system** |
| **Sidebar Navigation** | Workspace JSON config, collapsible sidebar | `SidebarProvider` + `SidebarInset`, localStorage persistence | Functional parity |
| **Breadcrumbs** | Jinja2 block `{% block breadcrumbs %}` | None | **Missing** |
| **Command Palette** | Not present | `Command` component (cmdk) exists but not wired globally | **Global ⌘K palette not implemented** |
| **Data Table** | Server-rendered HTML tables, Frappe listview | DataTable component with sort/filter/pagination/skeleton | Functional parity; lacks inline editing |
| **Cards** | Bootstrap `.card` with `.card-md`, `.h-100` | Card component (CardHeader/Title/Content/Footer) | Parity |
| **Tabs** | Bootstrap nav-tabs | PageTabs (Framer Motion), Radix Tabs | Parity |
| **Badges/Indicators** | `.indicator-pill` with color variants | Badge with tone variants | Parity |
| **Progress** | Bootstrap progress bar | Progress (Base UI) | Parity |
| **Loading States** | `start_item_loading_animation()`, skeletons in newer versions | Skeleton component, DataTable skeleton rows | Parity |
| **Print Templates** | Jinja2 HTML with inline styles | InvoicePrintSheet + `invoice-print.css` | Print output handled differently |
| **Responsive Design** | Bootstrap `.col-xs-*`, `.hidden-xs`, `.visible-xs` | Tailwind breakpoints, `overflow-x-auto` on DataTable | **DataTable uses horizontal scroll only — no mobile card view** |

---

## 2. New Components to Build

### 2.1 Toast Notification System
- Replace `frappe.msgprint()` pattern
- Use Radix Toast primitive as base
- Variants: success, error, warning, info
- Auto-dismiss with configurable duration
- Action button support (e.g., "Undo", "View")
- Stack multiple toasts
- Portal-rendered, accessible (`role="status"`, `aria-live`)

### 2.2 Date Picker
- Replace all native `<input type="date">` usages
- Calendar dropdown with month/year navigation
- Range selection support (for DateRangeFilter replacement)
- Keyboard navigation (arrow keys, Enter, Esc)
- Integrate with Field component

### 2.3 Global Command Palette (⌘K)
- Wire `Command` component globally via keyboard listener
- Actions: navigate to pages, search customers/orders/invoices, quick-create
- Grouped results with keyboard navigation
- Recent searches, favorite actions
- Fuzzy search via cmdk

### 2.4 Breadcrumb Navigation
- Use in all page headers
- Items from route hierarchy
- Clickable links + current page indicator
- Collapsible on mobile
- Slot in PageHeader component

### 2.5 Inline Table Editing
- Editable cells in DataTable (or separate InlineDataTable)
- Double-click or Enter to edit
- Escape to cancel
- Save on blur or explicit save button
- Validation per cell
- Dirty state tracking per row

### 2.6 Mobile Card View for Data Tables
- Transform table rows to card layout on mobile (`< md`)
- Card shows key columns only (prioritized)
- Swipe actions for edit/delete
- Pull-to-refresh
- Replace `overflow-x-auto` as mobile strategy

### 2.7 Quick Entry Modal
- Inline mini-form in Combobox popover (already partially exists in CustomerCombobox)
- Extract as generic `QuickEntryDialog` component
- Used for: new Customer, new Product, new Supplier
- Auto-focus first field
- Submit creates and selects the new record

---

## 3. Enhancements to Existing Components

### 3.1 RecordPaymentForm — Use react-hook-form
- Currently uses raw `useState` — inconsistent with CustomerForm
- Migrate to `useForm` with same resolver pattern
- Add `zod` validation schema
- Add submit loading spinner state
- Add form-level error summary

### 3.2 Consistent Tailwind Usage
- **AlertFeed** (`src/domain/inventory/components/AlertFeed.tsx`): uses raw CSS classes (`.alert-sidebar`, `.alert-item`) from `inventory.css` — replace with Tailwind
- **CommandBar** (`src/domain/inventory/components/CommandBar.tsx`): uses raw CSS (`.command-bar`, `.command-search`) — replace with Tailwind
- Audit all components for `className` vs `cn()` usage inconsistency

### 3.3 Zod Validation Schema
- Add `zod` dependency
- Create centralized validation schemas per domain
- Replace custom native resolver in CustomerForm
- Use `z.infer<typeof schema>` for TypeScript types
- Schema: Customer, Invoice, Order, Payment, Product

### 3.4 Chart Color Distinction
- Chart tokens are all monochrome (`--chart-1` through `--chart-5` in gray scale)
- Update chart palette to use distinct colors for multi-series charts
- Per-domain palettes: revenue (blue/green), status (red/yellow/green), categories (categorical palette)

### 3.5 Accessibility Improvements
- Focus management after Dialog/Sheet close
- `aria-live="polite"` regions for dynamic content updates (reconciliation totals, alert counts)
- `role="status"` for toast notifications
- Skip-to-content link
- Color contrast audit
- Keyboard navigation for all interactive elements
- `useReducedMotion` respected in all animations (already done for PageTabs)

---

## 4. UX Micro-Patterns to Add

### 4.1 Auto-Save Drafts
- Implement `useAutoSave` hook
- Debounced save after last edit (e.g., 2s)
- Visual indicator: "Saving...", "Saved"
- On form unmount with dirty state, prompt user

### 4.2 Dirty Form Detection
- `useForm` `isDirty` state
- Before navigating away from unsaved form, show confirmation dialog
- "You have unsaved changes. Leave anyway?"

### 4.3 Optimistic UI Updates
- Apply mutation result to UI immediately
- Roll back on API error with toast notification
- Use in: payment recording, status changes, inline edits

### 4.4 Loading Skeletons
- Already exist for DataTable
- Extend to: PageHeader, SectionCard, forms
- Skeleton variants matching component shapes

### 4.5 Empty States
- Add to all DataTable usages
- Include: icon, title, description, optional CTA button
- Illustration optional (not required per existing patterns)

### 4.6 Keyboard Shortcuts
- Expand `ShortcutOverlay` usage
- Document all shortcuts in a help modal
- Add: `Ctrl+N` (new record), `Ctrl+K` (command palette), `Ctrl+S` (save), `Escape` (close dialog)
- Per-page shortcuts (e.g., `P` for print on invoice detail)

---

## 5. Design System Gaps

### 5.1 Missing CSS Tokens
- `--ring` is gray, not primary-colored (should alias to `--primary` for focus rings)
- No `--sidebar-primary` in light mode (only in dark mode)
- No `oklch` token for destructive foreground (only destructive background exists)
- No `opacity` scale tokens for hover states
- No `shadow` token scale (Tailwind shadows hardcoded)

### 5.2 Icon Library Standardization
- Mix of Lucide/Feather SVG icons inline
- No centralized icon import (icons imported individually)
- Create `Icon` component or standardize icon imports
- Consider icon build step (e.g., `lucide-react` with tree-shaking)

### 5.3 Spacing System Gaps
- Inconsistent use of Tailwind spacing vs hardcoded values
- Some components use `p-4`, others `p-3`, `p-6` — no documented spacing scale
- Document `space-y` and `gap` conventions for components

---

## 6. Priority Ranking

| Priority | Item | Impact |
|----------|------|--------|
| P0 | Toast Notification System | Critical UX — all feedback currently silent |
| P0 | RecordPaymentForm react-hook-form | Security/correctness — manual validation is error-prone |
| P0 | Zod Integration | Validation scattered, no schema centralization |
| P1 | Date Picker | Used everywhere, native inputs are poor UX |
| P1 | Global Command Palette (⌘K) | Navigation efficiency |
| P1 | AlertFeed CSS → Tailwind | Consistency, maintainability |
| P1 | CommandBar CSS → Tailwind | Consistency, maintainability |
| P2 | Breadcrumb Navigation | Navigation clarity |
| P2 | Inline Table Editing | Core ERP pattern |
| P2 | Mobile Card View | Mobile usability |
| P2 | Chart Color Distinction | Data visualization quality |
| P3 | Auto-save / Dirty form detection | Polish |
| P3 | Keyboard Shortcuts expansion | Power-user efficiency |
| P3 | Empty states | Polish |
| P3 | Accessibility audit | Compliance, inclusive design |

---

*Analysis synthesized from ERPnext v15+ codebase and UltrERP component inventory dated 2026-04-20*
