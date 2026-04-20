# UI Design System Research: UltrERP Table and Layout Architecture

**Date:** 2026-04-20
**Sources:** Codebase analysis (`src/`), Web research (TanStack Table v8, shadcn/ui, Radix UI theming), ERPnext reference (`reference/erpnext-develop/`)

---

## 1. Executive Summary

UltrERP has a solid React 19 + Tailwind v4 + Base UI + Radix UI foundation. However, the **DataTable is severely limited**, **forms are inconsistent** (10 of 11 forms use raw `useState`), and **critical UI primitives are missing** (Toast, DatePicker, Breadcrumb, Spinner). The result is an inconsistent, incomplete UX that doesn't meet modern ERP standards.

**Priority findings:**
1. DataTable needs: column resize, sticky header, row selection, server-side pagination, inline editing infrastructure
2. Form architecture needs: unified `react-hook-form` + `zod` pattern across all forms
3. Missing components: Toast, DatePicker, Breadcrumb, Spinner — these block every domain story
4. Layout system: `PageHeader` + `SidebarInset` composition works but lacks breadcrumb slot
5. Design tokens: comprehensive oklch palette exists, but no `--chart-*` categorical colors

---

## 2. Current Design System Analysis

### 2.1 Tech Stack

| Layer | Technology | Notes |
|-------|------------|-------|
| UI primitives | **Base UI** + **Radix UI** mixed | Base UI: Button, Input, Dialog, Checkbox, Popover, Progress, Separator, Switch, RadioGroup. Radix: Select, Dropdown, Avatar, Tooltip, ScrollArea, Sheet (via Radix Dialog), Tabs |
| Table | **Custom `DataTable`** | NOT TanStack Table — custom implementation |
| Forms | **Mixed** | 1/11 uses react-hook-form (CustomerForm), 10/11 use raw useState |
| Validation | **Mixed** | Custom native resolver in CustomerForm, manual validation everywhere else |
| Styling | **Tailwind v4** via `@import "tailwindcss"` (no config file) | CSS custom properties in `:root` |
| Animation | **Framer Motion** (PageTabs), **tw-animate-css** | |
| Command palette | **cmdk** library | `Command` component, not wired globally |
| Routing | **React Router v7** | |

### 2.2 Design Tokens (oklch-based)

**Light mode palette:**
```
--background:     oklch(1 0 0)
--foreground:    oklch(0.145 0 0)
--primary:       oklch(0.205 0 0)
--success:       oklch(0.664 0.147 155.2)
--warning:       oklch(0.768 0.157 78.5)
--info:          oklch(0.618 0.104 239.4)
--neutral:       oklch(0.603 0.014 262.8)
--destructive:   oklch(0.577 0.245 27.325)
--radius:        0.625rem (10px)
```

**Critical gaps:**
- No `--chart-1` through `--chart-10` categorical colors (charts are monochrome per validated research)
- `--ring` is gray, not primary-colored (confirmed in gap analysis)
- No `--sidebar-primary` in light mode (only dark)
- Missing oklch destructive foreground token
- Missing opacity scale tokens for hover states

### 2.3 UI Component Inventory

**Files in `src/components/ui/`:**
```
button.tsx         [Base UI] ✓
input.tsx         [Base UI] ✓
select.tsx        [Radix]   ✓
dialog.tsx        [Base UI] ✓
sheet.tsx         [Radix]   ✓
badge.tsx         [CVA]     ✓
card.tsx          [CVA]     ✓
checkbox.tsx      [Base UI] ✓
textarea.tsx       [CVA]     ✓
tabs.tsx          [Radix]   ✓
popover.tsx       [Base UI] ✓
dropdown-menu.tsx [Radix]   ✓
tooltip.tsx       [Radix]   ✓
skeleton.tsx      [CVA]     ✓
table.tsx         [CVA]     ✓
progress.tsx      [Base UI] ✓
avatar.tsx        [Radix]   ✓
separator.tsx     [Base UI] ✓
switch.tsx        [Base UI] ✓
scroll-area.tsx   [Radix]   ✓
label.tsx         [CVA]     ✓
radio-group.tsx   [Base UI] ✓
field.tsx         [CVA]     ✓  ← rich compound component system
input-group.tsx   [CVA]     ✓  ← Button+Input+Textarea composition
info-popover.tsx  [Base UI] ✓
command.tsx       [cmdk]    ✓
DataTable.tsx     [CUSTOM]  △  ← severely limited
Toast.tsx         [MISSING] ✗
DatePicker.tsx    [MISSING] ✗
Breadcrumb.tsx    [MISSING] ✗
Spinner.tsx       [MISSING] ✗
```

---

## 3. DataTable: Current Architecture vs. Requirements

### 3.1 Current Implementation

**File:** `src/components/layout/DataTable.tsx`

```typescript
export interface DataTableColumn<TData> {
  id: string;
  header: ReactNode;
  cell: (row: TData) => ReactNode;
  sortable?: boolean;
  getSortValue?: (row: TData) => string | number | null | undefined;
  className?: string;
  headerClassName?: string;
  onClick?: (event: React.MouseEvent, row: TData) => void;
}
```

**Supported:** Basic columns, client-side sorting with `getSortValue`, custom sort extraction, loading skeleton (6 rows), empty state, error state, filter bar slot, toolbar slot, summary row slot, single-row click activation.

**NOT supported:**
- Column resize (no `resizable` prop, no `column.width`)
- Sticky header (no `position: sticky`)
- Row selection (no `onRowSelect`, `selectedIds`)
- Server-side pagination (client-side only)
- Column visibility toggle
- Column pinning (sticky left/right columns)
- Row grouping
- Expandable rows
- Faceted filtering
- Inline editing

### 3.2 What a Modern ERP DataTable Needs

Based on ERPnext patterns and modern React best practices:

| Feature | ERPnext | Modern Best Practice | UltrERP |
|---------|---------|---------------------|---------|
| Column sorting | ✓ (framework) | ✓ TanStack `getSortedRowModel` | △ Custom, limited |
| Column resize | ✓ | ✓ TanStack built-in | ✗ |
| Sticky header | ✓ | ✓ CSS `position: sticky` | ✗ |
| Row selection | ✓ | ✓ Checkbox column | ✗ |
| Bulk actions | ✓ | ✓ Action bar on selection | ✗ |
| Column visibility toggle | ✓ (framework) | ✓ `columnVisibility` state | ✗ |
| Inline editing | ✓ (`editable_grid`) | ✓ Double-click cell | ✗ |
| Column pinning | ✓ | ✓ Sticky columns | ✗ |
| Server-side pagination | ✓ (framework) | ✓ TanStack Query | △ Client-side only |
| Saved views | ✓ (framework) | ✓ User prefs | ✗ |
| Expandable rows | ✓ | ✓ Accordion pattern | ✗ |
| Row grouping | ✓ | ✓ `getGroupedRowModel` | ✗ |
| Filter per column | ✓ (framework) | ✓ `getFilteredRowModel` | △ Filter bar slot only |

### 3.3 TanStack Table v8 Integration

**Key insight:** The current custom `DataTable` should be **rebuilt on TanStack Table v8** as the headless table logic layer. This is the industry standard for React tables in 2025-2026 and works with any UI library.

**Recommended architecture:**

```typescript
// 1. Column definitions (in each domain page)
const columns: ColumnDef<Order>[] = [
  columnHelper.accessor('order_number', {
    header: 'Order #',
    cell: info => <OrderNumberCell value={info.getValue()} />,
    enableColumnFilter: true,
  }),
  columnHelper.accessor('status', {
    header: 'Status',
    cell: info => <StatusBadge status={info.getValue()} />,
    filterFn: 'equalsString',
  }),
  columnHelper.accessor('total', {
    header: () => <span className="text-right">Total</span>,
    cell: info => formatCurrency(info.getValue()),
    meta: { align: 'right' },
  }),
];

// 2. DataTable component wraps TanStack Table
const table = useReactTable({
  data,
  columns,
  state: { sorting, columnFilters, pagination },
  onSortingChange: setSorting,
  onColumnFiltersChange: setColumnFilters,
  onPaginationChange: setPagination,
  getCoreRowModel: getCoreRowModel(),
  getSortedRowModel: getSortedRowModel(),
  getFilteredRowModel: getFilteredRowModel(),
  getPaginationRowModel: getPaginationRowModel(),
  // Optional:
  enableRowSelection: true,
  onRowSelectionChange: setRowSelection,
  enableColumnResizing: true,
  columnResizeMode: 'onEnd',
});
```

**Features to enable incrementally:**
1. Phase 1: Sorting + pagination + filter bar → replace current DataTable
2. Phase 2: Row selection + bulk actions bar
3. Phase 3: Column resize + column visibility
4. Phase 4: Inline editing (cell-level)
5. Phase 5: Server-side pagination (via TanStack Query)

### 3.4 Radix UI Theming with Tailwind v4

**Issue:** Tailwind CSS v4 has CSS specificity issues with Radix UI. Resolution:

```css
/* In index.css */
@layer base {
  [data-radix-popper-content-wrapper] {
    @apply z-50;
  }
}
```

**Focus ring pattern (from shadcn/ui):**
```tsx
className="focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
```

---

## 4. Page Layout Architecture

### 4.1 Current Composition

```
AppNavigation
└── Sidebar (fixed left, 72px expanded / 80px collapsed)
    └── SidebarInset (wraps page content with pl-20 or pl-72)
        └── Domain Pages
            ├── PageHeader
            │   ├── eyebrow (optional badge)
            │   ├── title
            │   ├── description
            │   ├── actions (right-aligned)
            │   └── tabs (PageTabs below)
            ├── SectionCard (optional wrapper)
            │   └── Content (forms, tables, etc.)
            └── PageTabs (optional)
```

### 4.2 Breadcrumb Slot Missing

**Problem:** `PageHeader` does not have a `breadcrumb` prop. All detail pages lack navigation context.

**Required change:**
```tsx
// PageHeader.tsx
interface PageHeaderProps {
  breadcrumb?: Array<{ label: string; href?: string }>;  // ADD
  eyebrow?: string;
  title: string;
  description?: string;
  actions?: ReactNode;
  tabs?: ReactNode;
}

// Render:
{breadcrumb && (
  <Breadcrumb items={breadcrumb} className="mb-4" />
)}
<div className="flex items-center justify-between">...</div>
```

### 4.3 Sidebar Pattern

**Current:** `SidebarInset` adds `pl-20` or `pl-72` to content area.
**ERPnext pattern:** Workspace sidebar with collapsible sections.
**Recommendation:** Add collapsible sidebar groups (already in sidebar.tsx but not wired to nav data).

---

## 5. Form Architecture Analysis

### 5.1 Current State

| Form | react-hook-form | zod | useState | Custom validation |
|------|----------------|-----|----------|-------------------|
| CustomerForm | ✓ | ✗ | ✗ | Native resolver |
| EditCustomerDialog | ✗ | ✗ | ✓ | None |
| CustomerDetailDialog | ✗ | ✗ | ✓ | None |
| CreateInvoicePage | ✗ | ✗ | ✓ | `isValid` boolean |
| OrderForm | ✗ | ✗ | ✓ | None |
| StockAdjustmentForm | ✗ | ✗ | ✓ | None |
| SupplierOrderForm | ✗ | ✗ | ✓ | None |
| ProductForm | ✗ | ✗ | ✓ | `validate()` fn |
| SupplierForm | ✗ | ✗ | ✓ | `validate()` fn |
| CustomerCombobox inline | ✗ | ✗ | ✓ | None |
| ProductCombobox inline | ✗ | ✗ | ✓ | None |

### 5.2 Recommended Architecture

**Build on existing `field.tsx` compound system:**

```tsx
// src/lib/schemas/order.schema.ts
import { z } from 'zod';

export const orderSchema = z.object({
  customer_id: z.string().uuid('Customer is required'),
  payment_terms: z.enum(['NET_30', 'NET_60', 'COD']),
  lines: z.array(z.object({
    product_id: z.string().uuid(),
    quantity: z.number().positive(),
    unit_price: z.number().nonnegative(),
  })).min(1, 'At least one line is required'),
  notes: z.string().max(1000).optional(),
});

export type OrderFormValues = z.infer<typeof orderSchema>;

// OrderForm.tsx
const form = useForm<OrderFormValues>({
  resolver: zodResolver(orderSchema),
  defaultValues: { customer_id: '', lines: [{ product_id: '', quantity: 1, unit_price: 0 }] },
});

// Error display via existing Field + FieldError components
<Field error={form.formState.errors.customer_id}>
  <FieldLabel>Customer</FieldLabel>
  <CustomerCombobox value={form.watch('customer_id')} onChange={(v) => form.setValue('customer_id', v)} />
  <FieldError />
</Field>
```

### 5.3 Backend-Frontend Schema Sync

**Current:** Backend Pydantic schemas in `backend/domains/*/schemas.py` are the API contract.
**Problem:** No automated sync with frontend.
**Recommendation:** Document the sync requirement in epic-22 story 22.4. Field name divergences are bugs.

---

## 6. Missing Components (Epic 22 Scope)

### 6.1 Toast System

**Why critical:** Zero user feedback on any action currently. `SurfaceMessage` in `PageLayout.tsx` exists but is only used for error display, not action feedback.

**Design:**
- Use **Radix Toast** as primitive (NOT Base UI — Radix Toast is more mature)
- Variants: success (green), error (destructive red), warning (amber), info (blue)
- Position: bottom-right fixed, portal-rendered
- Auto-dismiss: 5000ms default
- Max stack: 5 (oldest dismissed)
- Use existing `--success`, `--warning`, `--info`, `--destructive` tokens

### 6.2 DatePicker

**Why critical:** Native `<input type="date">` everywhere — poor mobile UX, no locale formatting.

**Design:**
- Use **react-day-picker** v8 as base (most mature React date picker)
- Wrap in **Radix Popover** (NOT Base UI Popover — react-day-picker works with any popper)
- Expose both `DatePicker` (single) and `DateRangePicker` (range for filters)
- Locale formatting via existing i18n setup
- Keyboard navigation: Arrow keys, Enter, Escape

### 6.3 Breadcrumb

**Why critical:** No navigation context on detail pages.

**Design:**
- Build on existing navigation route config (`src/lib/navigation.ts`)
- `Breadcrumb` component reads parent routes from React Router
- Last crumb: plain text (current page). Others: `<Link>`.
- Separator: `/` or chevron
- Mobile: collapse to last 2 segments + `...`

### 6.4 Spinner

**Why critical:** Needed for button loading states, not just skeletons.

**Design:**
- Three sizes: `sm` (16px), `md` (24px), `lg` (40px)
- CSS animation `animate-spin` with Tailwind
- Use in: button loading states, form submit in progress, DataTable loading

### 6.5 QuickEntryDialog

**Why critical:** Creating Customer/Product/Supplier from within a transaction (e.g., order form) requires a modal.

**Design:**
- Generic dialog wrapping mini-forms
- Entity type: `'customer' | 'product' | 'supplier'`
- Auto-focus first field
- Success: close + call `onSuccess(created_entity)` + toast
- Error: toast.error()

---

## 7. Design Token Gaps to Address

### 7.1 Chart Colors (P2)

```css
/* Add to :root in index.css */
--chart-1: oklch(0.646 0.189 237.6);   /* blue */
--chart-2: oklch(0.664 0.147 155.2);   /* green */
--chart-3: oklch(0.768 0.157 78.5);    /* amber */
--chart-4: oklch(0.627 0.194 299.4);  /* purple */
--chart-5: oklch(0.627 0.194 155.2);  /* teal */
/* ... through chart-10 */
```

### 7.2 Ring Token Fix

```css
/* Currently --ring is gray, should be primary */
--ring: oklch(0.205 0 0);  /* matches --primary */
```

### 7.3 Sidebar Primary Token (Light Mode)

```css
/* Currently only in .dark — add to :root */
--sidebar-primary: oklch(0.205 0 0);
```

---

## 8. Page Layout Patterns from ERPnext

### 8.1 ListView Configuration Pattern

ERPnext uses `frappe.listview_settings["Doctype"]` JS config:
- `add_fields`: columns shown in list
- `get_indicator`: color-coded status function
- `onload`: bulk action buttons via `page.add_action_item()`
- `refresh`:perms check

**For UltrERP:** The `DataTable` toolbar slot should support a similar action bar pattern:
```tsx
<DataTable
  toolbar={
    <div className="flex items-center gap-2">
      <Button variant="outline" onClick={() => bulkAction('close')}>
        Close
      </Button>
      <Button variant="outline" onClick={() => bulkAction('cancel')}>
        Cancel
      </Button>
    </div>
  }
  // ...
/>
```

### 8.2 Status Indicator Pattern

ERPnext's `get_indicator` returns `[label, color, filter_query]`. UltrERP should adopt a consistent `StatusBadge` component:

```tsx
const STATUS_CONFIG = {
  draft:      { label: 'Draft',     tone: 'neutral' as const },
  confirmed:  { label: 'Confirmed', tone: 'info' as const },
  shipped:    { label: 'Shipped',  tone: 'warning' as const },
  fulfilled:  { label: 'Fulfilled', tone: 'success' as const },
  cancelled:  { label: 'Cancelled', tone: 'destructive' as const },
};
```

### 8.3 Quick Entry Pattern

ERPnext's `ContactAddressQuickEntryForm` is reused for Customer, Supplier. UltrERP's `QuickEntryDialog` should follow the same reuse pattern:
- One `CustomerQuickEntryForm` component
- Used in: `CustomerCombobox` inline panel, `CustomerListPage` "New" button, `CreateInvoicePage` customer selector

---

## 9. Kanban Board — Investigation Results

**Finding:** ERPnext doesn't implement Kanban as a first-class doctype. It delegates to Frappe framework's `Kanban` view, which is a Frappe core feature. The reference checkout does NOT contain a dedicated Kanban doctype or board component.

**ERPnext's Kanban pattern:**
```javascript
// In project.js
frappe.route(() => {
    frappe.set_route("List", "Task", "Kanban", project_name);
});
```

**Implication for UltrERP:** Kanban requires building from scratch or adopting a library like `@dnd-kit` or `react-kanban`. This is P2 in the UI roadmap (Epic 22 does not include it).

---

## 10. Recommended Implementation Priorities

### Phase 1: Foundation (Epic 22 — Stories 22.1, 22.2, 22.3)
1. **Toast** — immediate UX feedback for all mutations
2. **DatePicker** — replace `<input type="date">` everywhere
3. **Breadcrumb** — navigation context for all pages
4. **Spinner** — loading states for buttons and tables

### Phase 2: DataTable Rebuild (Post-Epic 22)
1. **TanStack Table v8 integration** — replace custom DataTable
2. **Column resize** — drag handles with min/max
3. **Sticky header** — `position: sticky; top: 0`
4. **Row selection** — checkbox column + bulk action bar

### Phase 3: Form Standardization (Epic 22 — Story 22.4)
1. **Zod schemas** in `src/lib/schemas/`
2. **RecordPaymentForm rewrite** (use case for toast)
3. **CustomerForm** upgrade to zod (replace native resolver)
4. **All other forms** migrate to react-hook-form + zod

### Phase 4: Table Feature Gaps
1. **Column visibility toggle**
2. **Server-side pagination** (via TanStack Query)
3. **Inline editing** (double-click cell → input)
4. **Expandable rows** (for hierarchical data)

---

## 11. Key File Reference Map

| What | File |
|------|------|
| Design tokens | `src/index.css` (lines 8-167) |
| Button (Base UI) | `src/components/ui/button.tsx` |
| Field compound | `src/components/ui/field.tsx` |
| Table primitive | `src/components/ui/table.tsx` |
| DataTable (custom) | `src/components/layout/DataTable.tsx` |
| PageHeader/Layout | `src/components/layout/PageLayout.tsx` |
| PageTabs (motion) | `src/components/layout/PageTabs.tsx` |
| Sidebar | `src/components/ui/sidebar.tsx` |
| Navigation | `src/components/AppNavigation.tsx` |
| Navigation config | `src/lib/navigation.ts` |
| cn() utility | `src/lib/utils.ts` |
| CustomerForm | `src/components/customers/CustomerForm.tsx` |
| OrderForm | `src/domain/orders/components/OrderForm.tsx` |
| SurfaceMessage | `src/components/layout/PageLayout.tsx` (line 200) |
| Theme provider | `src/components/theme/ThemeProvider.tsx` |
| ERPnext list config | `reference/erpnext-develop/erpnext/selling/doctype/sales_order/sales_order_list.js` |
| ERPnext quick entry | `reference/erpnext-develop/erpnext/public/js/utils/customer_quick_entry.js` |
| TanStack Table | https://tanstack.com/table/v8/docs/framework/react |
| shadcn/ui Table | https://ui.shadcn.com/docs/components/radix/data-table |
| Radix UI theming | https://www.radix-ui.com/themes/docs/components/table |

---

## 12. Specific Technical Decisions to Make

### Decision 1: DataTable — Rebuild or Extend?

**Option A (Rebuild):** Replace `DataTable` with TanStack Table + shadcn/ui Table components. Complete rewrite, 1-2 weeks.

**Option B (Extend):** Add TanStack Table as a second table variant (`DataTable2` / `TanStackDataTable`) alongside the existing one. Incremental, allows domain migration one at a time.

**Recommendation:** Option B — existing DataTable is used across many pages. A clean-break rewrite in parallel with Epic 22's UI work risks breaking in-progress domains. Build `TanStackDataTable` as the new default, keep existing `DataTable` for backward compatibility during migration, deprecate after.

### Decision 2: Toast — Radix vs. Base UI vs. Sonner

**Option A (Radix Toast):** Most mature, best accessibility, most customizable.
**Option B (Base UI Toast):** Consistent with existing Base UI stack, but Base UI Toast is less mature than Radix.
**Option C (Sonner):** Headless, opinionated styling, extremely popular. No Radix/Base UI consistency.

**Recommendation:** Radix Toast — accessibility is critical for an ERP, and Radix is the most battle-tested for complex interaction patterns.

### Decision 3: react-day-picker vs. Custom Calendar

**Option A (react-day-picker v8):** Most mature React date picker, locale support, range selection, keyboard nav.
**Option B (Custom):** Full control, but reinventing wheel.

**Recommendation:** react-day-picker v8 — it handles all edge cases (leap years, locale leap years, timezones) that are painful to get right custom.

### Decision 4: Form State — Zustand vs. Context vs. Local

**Option A (Zustand):** For global table state (filters, sorting, pagination across pages).
**Option B (TanStack Query):** For server-side table state + caching.
**Option C (Local useState):** Keep table state local to each page component.

**Recommendation:** TanStack Query for server data + caching. Zustand for client-side table UI state (column visibility, density preference). Local useState for form state within a page.
