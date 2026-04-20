# Epic 22: UI Foundation System — Toast, DatePicker, Breadcrumb, Form Validation, and DataTable Architecture

## Epic Goal

Build the reusable UI component primitives that later order-surface work in Epic 21 and every future domain can consume without duplicating local versions: a toast notification system so users get feedback on every action, a calendar DatePicker that replaces native date inputs everywhere, Breadcrumb navigation so users never lose context, a Zod-backed validation layer so forms are consistent and type-safe, and a TanStack Table v8-backed DataTable that supports sorting, filtering, pagination, row selection, column resize, and sticky headers.

## Business Value

- Users get immediate, visible feedback on every save, error, and async operation — instead of the current silent success / hidden errors.
- DatePicker works correctly on mobile and respects locale formatting.
- Navigation is always traceable — users can always see where they are and click back.
- Form validation is centralized, typed, and consistent — developers stop fixing the same validation bugs in different forms.
- The DataTable supports the features every ERP list view needs: column sorting, filtering, pagination, row selection with bulk actions, column resize, and sticky headers.
- The orders workspace can integrate real toast feedback, breadcrumbs, and a stronger table foundation without Epic 21 having to invent order-local versions of those primitives.

---

## Research Findings Summary

*(Full research: `_bmad-output/planning-artifacts/ui-design-system-research.md`)*

### Design System Architecture

| Layer | Technology | Status |
|-------|-----------|--------|
| UI primitives | **Base UI** + **Radix UI** mixed | Solid foundation |
| Table | Custom `DataTable` (NOT TanStack) | Severely limited — needs rebuild |
| Forms | Mixed: 1/11 react-hook-form, 10/11 raw useState | Inconsistent |
| Validation | No Zod anywhere | Missing |
| Styling | Tailwind v4 via `@import "tailwindcss"` | OK — no config file |
| Animation | Framer Motion + tw-animate-css | OK |
| Design tokens | OKLCH palette, comprehensive | Gaps: chart colors, `--ring` token |

### DataTable Limitations (Current)

The custom `DataTable` (`src/components/layout/DataTable.tsx`) is missing:
- Column resize (no `resizable` prop, no `column.width`)
- Sticky header (no `position: sticky`)
- Row selection (no checkbox column, no `onRowSelect`)
- Server-side pagination (client-side only)
- Column visibility toggle
- Column pinning (sticky left/right columns)
- Row grouping / expandable rows
- Faceted filtering per column
- Inline editing (double-click cell)

### Form State (Current)

| Form | react-hook-form | Zod | Raw useState |
|------|----------------|-----|--------------|
| CustomerForm | ✓ | ✗ (custom resolver) | ✗ |
| EditCustomerDialog | ✗ | ✗ | ✓ |
| CreateInvoicePage | ✗ | ✗ | ✓ |
| OrderForm | ✗ | ✗ | ✓ |
| StockAdjustmentForm | ✗ | ✗ | ✓ |
| SupplierOrderForm | ✗ | ✗ | ✓ |
| ProductForm | ✗ | ✗ | ✓ |
| SupplierForm | ✗ | ✗ | ✓ |
| CustomerCombobox inline | ✗ | ✗ | ✓ |
| ProductCombobox inline | ✗ | ✗ | ✓ |

### Design Token Gaps

- `--chart-1` through `--chart-10` categorical colors missing (charts are monochrome)
- `--ring` is gray, not primary-colored
- `--sidebar-primary` missing in light mode (only in dark)
- Missing destructive foreground oklch token
- Missing opacity scale tokens for hover states

## Preserve Existing UltrERP Strengths

Epic 22 should close confirmed gaps without regressing the surfaces that are already stronger than ERPnext:
- Keep the existing `PageHeader` hero card and `PageTabs` animated tab strip. Breadcrumb is an additive context layer, not a flatter header replacement.
- Keep the `Field` compound system (`Field`, `FieldLabel`, `FieldDescription`, `FieldError`) as the standard form surface. New date and quick-entry controls should compose into this system.
- Keep the current `Sidebar` / `SidebarInset` responsive behavior and the existing OKLCH token + tone language.
- Build `StatusBadge` on top of the existing `Badge` variants instead of introducing a parallel visual language for statuses.
- Treat `TanStackDataTable` as a logic upgrade, not a visual redesign: preserve the current toolbar, filter bar, summary, loading, empty/error states, row keyboard behavior, and row styling hooks.

---

## Scope

**Components to build:**
- `Toast` — Radix Toast base, `useToast()` hook, success/error/warning/info variants, stacking, portal-render
- `DatePicker` + `DateRangePicker` — react-day-picker v8, locale-aware, Radix Popover wrapper
- `Breadcrumb` — clickable path from navigation config, mobile collapse
- `Spinner` — sm/md/lg variants, `animate-spin`
- `QuickEntryDialog` — generic entity creation modal
- StatusBadge — consistent tone-based badge component across all domains
- `DataTable2` / `TanStackDataTable` — TanStack Table v8-backed replacement for the existing DataTable

**Design tokens to fix:**
- Add `--chart-1` through `--chart-10` categorical palette to `src/index.css`
- Fix `--ring` to use `--primary`
- Add `--sidebar-primary` to light mode

**Validation to migrate/upgrade:**
- Add `zod` and `@hookform/resolvers/zod` to `package.json`
- Create `src/lib/schemas/` with Zod schemas for Customer, Invoice, Order, Payment, Product, Supplier
- Migrate `RecordPaymentForm` and `RecordUnmatchedPayment` from raw useState to react-hook-form + zod + toast
- Migrate all other raw useState forms to react-hook-form + zod
- Replace transient action feedback with toast while keeping persistent inline states on `SurfaceMessage`

**CSS cleanup:**
- Convert `AlertFeed` from raw CSS to Tailwind
- Convert `CommandBar` from raw CSS to Tailwind

**Not in scope:**
- Order-domain workflow, reporting, audit, or permission semantics already owned by Epic 21
- Global command palette ⌘K (P2)
- Inline table editing (P2)
- Mobile card view for DataTable (P2)
- Auto-save / dirty form detection (P3)
- TanStack Table full feature set — incremental (resize, sticky header first; row selection second; inline edit third)

---

## Technical Decisions

### TD-1: Toast Library
**Decision: Radix UI Toast** (`@radix-ui/react-toast`)
**Why:** Most mature, best accessibility, battle-tested in production ERPs. Base UI has no toast primitive. Sonner is popular but loses Radix consistency.
**Pattern:**
```typescript
// src/hooks/useToast.ts
const { toast, success, error, warning, info } = useToast()
success({ title: 'Saved', description: 'Order confirmed' })
error({ title: 'Failed', description: 'Network error' })
```

### TD-2: DatePicker Library
**Decision: react-day-picker v8**
**Why:** Handles locale, range selection, keyboard nav, mobile, leap years correctly. Custom calendar would reinvent the wheel.
**Pattern:** Wrap in Radix Popover (NOT Base UI Popover — react-day-picker is popper-agnostic).

### TD-3: DataTable Architecture
**Decision: Build `TanStackDataTable` alongside existing `DataTable`, deprecate old after migration**
**Why:** Complete rewrite risks breaking in-progress domains. Parallel build allows incremental migration. The new component uses TanStack Table v8 as headless table logic + shadcn/ui Table for semantic markup.
**Migration sequence:**
1. Build `TanStackDataTable` with sorting + pagination (same features as current DataTable)
2. Use the Orders list as the first pilot consumer, while preserving the order-specific UX contract defined in Epic 21.4
3. Add column resize
4. Add sticky header
5. Add row selection + bulk action bar
6. Add column visibility toggle
7. Deprecate old `DataTable`

### TD-4: Form State Management
**Decision: react-hook-form + Zod for form state. TanStack Query for server data. Zustand for cross-page table UI state (column visibility, density).**
**Why:** Forms are page-scoped — no need for global state. TanStack Query handles server sync. Table UI state (column visibility, density) benefits from Zustand for cross-page persistence.

### TD-5: Table Column Definition
**Decision: `ColumnDef` from TanStack Table, NOT custom interface**
**Why:** Industry standard. Allows `enableColumnFilter`, `enableSorting`, `enableResizing` per column. Type-safe with `z.infer<typeof schema>`.
**Pattern:**
```typescript
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
```

### TD-6: Status Badge Pattern
**Decision: Consistent `StatusBadge` component across all domains**
**Why:** ERPnext uses `get_indicator` consistently. UltrERP needs the same.
```typescript
const STATUS_CONFIG = {
  draft:      { label: 'Draft',     tone: 'neutral' as const },
  confirmed:  { label: 'Confirmed', tone: 'info' as const },
  shipped:    { label: 'Shipped',   tone: 'warning' as const },
  fulfilled:  { label: 'Fulfilled', tone: 'success' as const },
  cancelled:  { label: 'Cancelled', tone: 'destructive' as const },
};
```

### TD-7: Radix + Tailwind v4 Specificity
**Decision: Use `@layer base` for Radix `[data-*]` attribute selectors**
```css
/* In index.css */
@layer base {
  [data-radix-popper-content-wrapper] {
    @apply z-50;
  }
}
```

---

## Dependency and Phase Order

```
Phase 1 (weeks 1-2): Toast + DatePicker + Breadcrumb + Design token fixes
  → All independent, can run in parallel across agents

Phase 2 (week 3): TanStackDataTable foundation + first pilot consumer
  → Independent of Toast, Breadcrumb, and Zod; coordinate with Epic 21 if the orders list is the pilot consumer

Phase 3 (week 3-4): Zod schemas + RecordPaymentForm rewrite + CustomerForm zod upgrade
  → Depends on Toast (22.1) and DatePicker (22.2) for the touched payment and form flows

Phase 4 (week 4): Spinner, QuickEntryDialog, and StatusBadge
  → Depends on Toast (22.1) and Zod form architecture (22.4)

Phase 5 (week 4): AlertFeed + CommandBar CSS cleanup
  → Independent

Phase 6 (ongoing): DataTable features — column resize, sticky header, row selection
  → Post-epic, incremental
```

## Cross-Epic Coordination With Epic 21

- Epic 22 is not a blanket prerequisite for Epic 21. Stories 21.1 to 21.3 should land first because they define the preserved order lifecycle and workflow semantics.
- Stories 22.1 and 22.3 should land before Epic 21.4 completes its shared feedback and breadcrumb integration, so the orders workspace consumes the reusable toast and breadcrumb primitives instead of creating duplicates.
- Story 22.4 may migrate `OrderForm`, but it must preserve the customer-linked intake and confirmation semantics established by Epic 21.2 rather than redefining them.
- Story 22.7 owns the shared TanStackDataTable foundation and may pilot on the orders list, but Epic 21.4 owns the order-specific filters, workflow cues, and action semantics rendered on that list.
- Stories 22.2, 22.5, and 22.6 remain broadly useful foundation work, but they do not block Epic 21 core order-domain progress.

---

## Story 22.1: Toast Notification System

**Context:** Users get no feedback when they save, confirm, or when an error occurs. `SurfaceMessage` in `PageLayout.tsx` (line 200) exists but is only used for error display, not action feedback. This is the single highest-impact UX fix in the codebase.

**R1 - Toast component and provider**
- Build `src/components/ui/Toast.tsx` using `@radix-ui/react-toast` as base
- Build `src/providers/ToastProvider.tsx` wrapping the app root
- `useToast()` hook from `src/hooks/useToast.ts`
- Variants map to existing design tokens: `success` → `--success`, `error` → `--destructive`, `warning` → `--warning`, `info` → `--info`
- Auto-dismiss after 5000ms default (configurable per-call via `duration` prop)
- Stack up to 5 toasts; oldest dismissed when limit exceeded
- Portal-rendered to `document.body` via Radix Portal
- `role="status"` + `aria-live="polite"` for accessibility
- Enter/exit animations via Framer Motion
- Bottom-right fixed position, click to dismiss

**R2 - Hook API**
```typescript
// Returns { toast, success, error, warning, info }
// Shorthands pre-configure the variant
const { success, error } = useToast()
success({ title: 'Saved', description: 'Order confirmed', duration: 3000 })
error({ title: 'Failed', description: error.message })
toast({ title: 'Custom', description: '...', variant: 'success' })
```

**R3 - SurfaceMessage and action feedback boundaries**
- Audit current `SurfaceMessage` usages and classify them as transient action feedback vs persistent inline state
- Replace transient mutation feedback (create/update/confirm/void/reconcile/receive/acknowledge success and failure) with `toast.error()` / `toast.success()` / `toast.warning()`
- Keep `SurfaceMessage` for persistent page-level load failures, empty states, blocking inline warnings, and long-lived notices where the message must remain visible until the user resolves it
- Document this boundary in the story notes so later stories do not reintroduce silent mutations or misuse toast for persistent errors

**R4 - Global wiring**
- All API mutation hooks (`useCreateOrder`, `useUpdateCustomer`, etc.) should accept `onSuccess` / `onError` callbacks that fire toasts
- Add `toast.success()` to: order confirmation, customer creation, invoice creation, payment recording
- Add `toast.error()` to: API error handlers in all domain hooks

**Acceptance Criteria:**

**Given** the app is loaded with ToastProvider at root
**When** any mutation succeeds (e.g., order confirmed)
**Then** a success toast appears bottom-right with title + description, auto-dismisses after 5s

**Given** the app is loaded
**When** any mutation fails
**Then** an error toast appears with the error message

**Given** a page-level fetch or blocking inline state fails
**When** the page renders
**Then** the error remains visible inline via `SurfaceMessage` instead of disappearing as a transient toast

**Given** multiple mutations fire in quick succession
**Then** toasts stack vertically without overlapping

**Given** 6 toasts are triggered in rapid succession
**Then** only 5 show and the oldest is dismissed automatically

---

## Story 22.2: DatePicker and DateRangePicker Components

**Context:** Every date field uses `<input type="date">` which renders inconsistently across browsers and is a poor experience on mobile. Native date inputs have no locale formatting and behave unpredictably on iOS Safari. A proper calendar picker is needed everywhere.

**R1 - DatePicker component**
- Build `src/components/ui/DatePicker.tsx` using `react-day-picker` v8
- Wraps in Radix Popover (`@radix-ui/react-popover`) — opens on calendar icon click or field focus
- Render the trigger with existing `Input` / `InputGroup` styling so it matches current form and filter controls
- Single date mode: `Date | undefined`
- `mode="single"` prop, `selected` + `onSelect` pattern from react-day-picker
- Locale formatting via existing i18n setup (react-i18next already configured)
- Month/year navigation via react-day-picker built-in calendar navigation
- Keyboard: Arrow keys to navigate dates, Enter to select, Escape to close
- Test on iOS Safari — react-day-picker handles mobile gracefully but must be verified

**R2 - DateRangePicker component**
- Build `src/components/ui/DateRangePicker.tsx` using same react-day-picker base
- `mode="range"` prop
- Returns `{ from: Date, to: Date } | undefined`
- Same Radix Popover wrapper, locale formatting, keyboard nav

**R3 - Field integration**
- Add `DatePicker` variant to the `Field` compound component system (`src/components/ui/field.tsx`) — if feasible within this story scope
- Or: replace `<input type="date">` usages directly with `<DatePicker>` components

**R4 - Replace all native date inputs**
- Audit all `<input type="date">` usages (grep: `type="date"`)
- Replace the current known owners: `src/components/filters/DateRangeFilter.tsx`, `src/domain/payments/components/RecordPaymentForm.tsx`, `src/domain/payments/components/RecordUnmatchedPayment.tsx`, `src/domain/inventory/components/SupplierOrderForm.tsx`, `src/pages/invoices/CreateInvoicePage.tsx`, `src/components/customers/CustomerStatementTab.tsx`, `src/pages/AdminPage.tsx`, and any remaining `type="date"` results returned by grep at implementation time
- For filter bars with From/To date inputs: replace with single `DateRangePicker`

**R5 - Fix `--ring` token and add chart colors**
- In `src/index.css` `:root`: change `--ring: oklch(0.7 0 0)` → `--ring: oklch(0.205 0 0)` (primary color)
- Add categorical chart colors to `:root`:
```css
--chart-1: oklch(0.646 0.189 237.6);   /* blue */
--chart-2: oklch(0.664 0.147 155.2);   /* green */
--chart-3: oklch(0.768 0.157 78.5);    /* amber */
--chart-4: oklch(0.627 0.194 299.4);   /* purple */
--chart-5: oklch(0.627 0.194 155.2);   /* teal */
/* through --chart-10 with distinct hues */
```

**Acceptance Criteria:**

**Given** a date field in any form
**When** the user clicks the calendar icon
**Then** a locale-formatted calendar dropdown opens (e.g., "2026年4月20日" for zh-Hant, "Apr 20, 2026" for en)

**Given** the DatePicker is open
**When** the user selects a date
**Then** the input field shows the locale-formatted date string

**Given** the DatePicker is open on iOS Safari
**When** the user interacts with it
**Then** it renders a native calendar picker without breaking layout

**Given** a filter bar with From/To date inputs
**When** the filter renders
**Then** it shows a single `DateRangePicker` with a "to" separator between two calendar icons

---

## Story 22.3: Breadcrumb Navigation

**Context:** No page currently shows where the user is in the navigation hierarchy. Detail pages especially need breadcrumbs so users can jump back to the list. The `PageHeader` component (`src/components/layout/PageLayout.tsx`) has no breadcrumb slot.

**R1 - Breadcrumb component**
- Build `src/components/ui/Breadcrumb.tsx`
- Props: `items: Array<{ label: string; href?: string }>`
- Last item: plain text span (current page, not clickable)
- Other items: `<Link>` from react-router-dom
- Separator: `/` between items (configurable via `separator?: ReactNode` prop)
- Mobile: collapse to `...` + last 2 segments (use CSS truncation + `truncate`)
- Collapses via `sm:flex` breakpoint

**R2 - PageHeader integration**
- Add `breadcrumb?: Array<{ label: string; href?: string }>` prop to `PageHeader` in `src/components/layout/PageLayout.tsx`
- Render `<Breadcrumb items={breadcrumb} />` at top of `PageHeader`, above the title row
- All detail pages pass breadcrumb: `{ label: 'Orders', href: '/orders' }, { label: orderNumber }`

**R3 - All pages wired**
- Customer detail: `[{ label: 'Customers', href: '/customers' }, { label: customerName }]`
- Invoice detail: `[{ label: 'Invoices', href: '/invoices' }, { label: invoiceNumber }]`
- Order detail: `[{ label: 'Orders', href: '/orders' }, { label: orderNumber }]`
- Product detail: `[{ label: 'Products', href: '/products' }, { label: productName }]`
- Supplier detail: `[{ label: 'Suppliers', href: '/suppliers' }, { label: supplierName }]`
- Warehouse detail: `[{ label: 'Warehouses', href: '/warehouses' }, { label: warehouseName }]`
- List pages (single crumb): `[{ label: 'Orders' }]` (no href = current page indicator)

**Acceptance Criteria:**

**Given** the user is on the Order detail page
**When** the page renders
**Then** the breadcrumb shows "Orders / ORD-001" where "Orders" links back to the list

**Given** the user is on the Orders list page
**When** the page renders
**Then** the breadcrumb shows "Orders" with no link (current page indicator)

**Given** the user is on a narrow mobile screen
**When** the breadcrumb renders
**Then** it collapses to show only the last two segments with "..."

---

## Story 22.4: Zod Schema Centralization and Form Migration

**Context:** Form validation is inconsistent — 10 of 11 forms use raw `useState` with no validation library. `CustomerForm` uses react-hook-form but with a custom native resolver instead of Zod. No schema centralization means the same validation rules are re-implemented differently across forms.

**R1 - Zod setup**
- Add `zod` and `@hookform/resolvers/zod` to `package.json`
- Create `src/lib/schemas/` directory
- Create schemas: `customer.schema.ts`, `invoice.schema.ts`, `order.schema.ts`, `payment.schema.ts`, `product.schema.ts`, `supplier.schema.ts`
- Each schema uses `z.object({ ... })` matching the domain model
- Export inferred TypeScript type via `z.infer<typeof schema>`
- Schemas align with backend Pydantic schemas in `backend/domains/*/schemas.py` — field names must match exactly

```typescript
// src/lib/schemas/order.schema.ts
import { z } from 'zod';

export const orderSchema = z.object({
  customer_id: z.string().uuid('Customer is required'),
  payment_terms: z.enum(['NET_30', 'NET_60', 'COD']),
  payment_terms_days: z.number().optional(),
  lines: z.array(z.object({
    product_id: z.string().uuid('Product is required'),
    quantity: z.number().positive('Quantity must be positive'),
    unit_price: z.number().nonnegative(),
  })).min(1, 'At least one line is required'),
  notes: z.string().max(1000).optional(),
});

export type OrderFormValues = z.infer<typeof orderSchema>;
```

**R2 - CustomerForm upgrade**
- CustomerForm (`src/components/customers/CustomerForm.tsx`) already uses react-hook-form with custom native resolver
- Replace custom resolver with `zodResolver` using the new `customer.schema.ts`
- Keep the existing `Field` + `FieldLabel` + `FieldError` compound component usage — this is the correct pattern
- Keep existing `cn()` utility usage

**R3 - Payments form rewrite**
- Current `RecordPaymentForm` (path: `src/domain/payments/components/RecordPaymentForm.tsx`) uses raw `useState` — confirmed by research
- Rewrite with react-hook-form + `zodResolver`
- Migrate `RecordUnmatchedPayment` (`src/domain/payments/components/RecordUnmatchedPayment.tsx`) in the same slice so matched and unmatched payment workflows share the same schema, field components, date picker, spinner, and toast behavior
- Use existing `Field` compound components
- Add `Spinner` (from Story 22.6) on submit button during submission
- Use `toast.success()` on payment recorded, `toast.error()` on failure

**R4 - Remaining form migrations**
Audit and migrate in priority order:
1. `OrderForm` (`src/domain/orders/components/OrderForm.tsx`) — Epic 21 depends on this
2. `ProductForm` (`src/domain/inventory/components/ProductForm.tsx`)
3. `SupplierForm` (`src/domain/inventory/components/SupplierForm.tsx`)
4. `StockAdjustmentForm` (`src/domain/inventory/components/StockAdjustmentForm.tsx`)
5. `SupplierOrderForm` (`src/domain/inventory/components/SupplierOrderForm.tsx`)
6. `CreateInvoicePage` (`src/pages/invoices/CreateInvoicePage.tsx`)
7. `EditCustomerDialog` (`src/components/customers/EditCustomerDialog.tsx`)
8. `CustomerCombobox` inline create panel (`src/components/customers/CustomerCombobox.tsx`)
9. `ProductCombobox` inline create panel (`src/components/products/ProductCombobox.tsx`)

**R5 - Backend schema sync**
- Read all `backend/domains/*/schemas.py` Pydantic models
- Verify field names match Zod schema field names (this is the source of truth for API contracts)
- Document divergences in comments in both files
- Any divergence is a bug — API field names must be consistent

**Acceptance Criteria:**

**Given** RecordPaymentForm is submitted with invalid data
**When** the user clicks Submit
**Then** inline validation errors appear on the offending fields and no API call is made

**Given** RecordPaymentForm is submitted with valid data
**When** the payment is recorded successfully
**Then** a success toast appears and the form resets

**Given** RecordPaymentForm is submitted and the API fails
**When** the server returns an error
**Then** an error toast appears with the server message

**Given** either payment form is submitted with invalid data
**When** the user clicks Submit
**Then** inline validation errors appear, no API call is made, and both payment workflows behave consistently

**Given** a developer adds a new field to the Customer domain
**When** they update `backend/domains/customers/schemas.py`
**Then** the corresponding `src/lib/schemas/customer.schema.ts` is updated to match

**Given** any form with react-hook-form + zod is submitted with invalid data
**When** the user clicks Submit
**Then** field-level errors appear inline (via `FieldError`) and no API call is made

---

## Story 22.5: CSS Cleanup — AlertFeed and CommandBar

**Context:** `AlertFeed` (`src/domain/inventory/components/AlertFeed.tsx`) and `CommandBar` (`src/domain/inventory/components/CommandBar.tsx`) use raw CSS classes from `inventory.css` instead of Tailwind. This creates style drift and maintenance burden.

**R1 - AlertFeed Tailwind conversion**
- Read `src/domain/inventory/components/AlertFeed.tsx` and `src/index.css` (for `.alert-sidebar`, `.alert-item`, `.alert-unread` rules)
- Replace `.alert-sidebar`, `.alert-item`, `.alert-unread` CSS classes with Tailwind equivalents via `cn()`
- Preserve existing layout and hover behavior
- Remove corresponding CSS rules from `inventory.css` (if no other components use them — verify with grep)

**R2 - CommandBar Tailwind conversion**
- Read `src/domain/inventory/components/CommandBar.tsx` and `inventory.css`
- Replace `.command-bar`, `.command-search`, `.command-results` CSS classes with Tailwind equivalents via `cn()`
- Preserve existing layout: search input + results list structure
- Remove unused CSS from `inventory.css`

**R3 - inventory.css audit**
- After removing AlertFeed/CommandBar rules, check if `inventory.css` still has other unused rules
- Move any remaining rules to `index.css` if still needed, or document for future cleanup

**Acceptance Criteria:**

**Given** the AlertFeed component is rendered
**When** it displays alerts
**Then** all styling comes from Tailwind classes via `cn()`, not from `inventory.css`

**Given** the CommandBar component is rendered
**When** it shows the search input and results
**Then** all styling comes from Tailwind classes via `cn()`, not from `inventory.css`

**Given** `inventory.css` is checked after conversion
**When** unused AlertFeed/CommandBar rules are removed
**Then** the CSS bundle size is reduced

---

## Story 22.6: Spinner, QuickEntryDialog, and StatusBadge

**Context:** Spinner component is needed for button loading states. QuickEntryDialog is needed for inline entity creation. StatusBadge is needed for consistent status rendering across all domains (currently each domain defines its own badge rendering).

**R1 - Spinner component**
- Build `src/components/ui/Spinner.tsx`
- Variants: `sm` (16px), `md` (24px), `lg` (40px)
- Use Tailwind `animate-spin` class
- Used in: button `loading` state, form submit in progress, DataTable loading overlay

**R2 - StatusBadge component**
- Build `src/components/ui/StatusBadge.tsx`
- Props: `status: string`, optional `size?: 'sm' | 'md'`
- Compose the existing `Badge` component variants instead of introducing a separate status-pill visual system
- Tone mapping to existing badge variants:
  - `draft`, `pending` → `neutral`
  - `confirmed`, `submitted`, `active` → `info`
  - `shipped`, `in_progress`, `partial` → `warning`
  - `fulfilled`, `completed`, `paid`, `closed` → `success`
  - `cancelled`, `rejected`, `void`, `failed` → `destructive`
  - Default unknown → `secondary`
- Add to all domain list pages: CustomerListPage, Order list, Invoice list, ProductTable, Supplier list
- This replaces inline badge rendering scattered across pages

**R3 - QuickEntryDialog**
- Build `src/components/ui/QuickEntryDialog.tsx`
- Wraps `Dialog` (Base UI) from `src/components/ui/dialog.tsx`
- Props: `entity: 'customer' | 'product' | 'supplier'`, `onSuccess: (created: Entity) => void`, `open`, `onOpenChange`
- Renders the appropriate mini-form based on entity type (reuse forms from existing combobox inline panels)
- Auto-focuses first field on dialog open
- Submits via existing API (POST), calls `onSuccess` with created entity, closes dialog
- Validation: inline via react-hook-form + zod (from Story 22.4)
- Error: `toast.error()` on failure
- Success: `toast.success()` on creation

**R4 - CustomerCombobox and ProductCombobox upgrade**
- Current `CustomerCombobox` has inline customer creation with raw `useState`
- Extract the inline form into a `CustomerQuickEntryForm` sub-component
- Reuse `QuickEntryDialog` with `entity="customer"` for the "New Customer" flow
- Apply same pattern to `ProductCombobox`
- This standardizes the inline creation UX across all comboboxes

**Acceptance Criteria:**

**Given** the user clicks "New Customer" in a CustomerCombobox popover
**When** the QuickEntryDialog opens
**Then** it shows a minimal customer form with Name, Email, Phone, Type, Status fields

**Given** the QuickEntryDialog form is filled correctly and submitted
**When** the API returns successfully
**Then** the dialog closes, `onSuccess` is called with the created customer, and a success toast appears

**Given** the QuickEntryDialog form is submitted with missing required fields
**When** the user clicks Submit
**Then** inline validation errors appear on the offending fields and no API call is made

**Given** a button is in loading state
**When** it renders
**Then** the Spinner (sm variant) appears inline with the button label

**Given** the Order list page renders rows with various statuses
**When** the page loads
**Then** each status cell shows a StatusBadge with the correct tone (green/amber/red/gray)

---

## Story 22.7: TanStackDataTable Foundation

**Context:** The existing custom `DataTable` (`src/components/layout/DataTable.tsx`) lacks column resize, sticky header, row selection, server-side pagination, and inline editing. The TanStack Table v8-backed `TanStackDataTable` provides a headless table foundation that supports all these features incrementally.

**R1 - TanStack Table setup**
- Add `@tanstack/react-table` to `package.json`
- Create `src/components/layout/TanStackDataTable.tsx`
- Keep same public API shape as existing `DataTable` where possible for easier migration
- Implement with `useReactTable` from TanStack Table v8

**R2 - Column definitions**
```typescript
// Use columnHelper from TanStack Table
const columnHelper = createColumnHelper<Order>();

const columns: ColumnDef<Order>[] = [
  columnHelper.accessor('order_number', {
    header: 'Order #',
    cell: info => info.getValue(),
    enableSorting: true,
    enableColumnFilter: true,
  }),
  // ... more columns
];
```

**R3 - Required row models**
- `getCoreRowModel: getCoreRowModel()` — always required
- `getSortedRowModel: getSortedRowModel()` — sorting
- `getPaginationRowModel: getPaginationRowModel()` — pagination
- `getFilteredRowModel: getFilteredRowModel()` — filtering

**R4 - Replace current DataTable features**
- Toolbar slot (same as current)
- Filter bar slot (same as current)
- Summary row slot (same as current)
- Loading skeleton (same as current)
- Empty state (same as current)
- Error state (same as current)
- Preserve current `Table` / `PaginationBar` visual treatment so migrated pages do not unexpectedly change appearance
- Single-row click activation via `getRowId`, `rowLabel`, and `onRowClick`
- Preserve `getRowClassName` for conditional row styling and existing per-cell `onClick` handlers from current column definitions
- Sorting with `getSortValue` for custom sort extraction

**R5 - Pilot consumer: Orders list page (coordinated with Epic 21.4)**
- Replace `DataTable` usage in `OrdersPage` with `TanStackDataTable` without redefining the order-specific workflow cues that Epic 21.4 owns
- Use existing column definitions from `OrderList` component
- Add `enableSorting: true` to sortable columns
- Add basic pagination (keep client-side for v1, server-side pagination is Phase 5)

**R6 - DataTable column resize**
- Enable via `enableColumnResizing: true` on `useReactTable`
- `columnResizeMode: 'onEnd'` (resize on drag end, not on every pixel)
- Render resize handle on column headers
- Minimum column width: 80px

**R7 - DataTable sticky header**
- Add `stickyHeader` prop to `TanStackDataTable`
- Render: `position: sticky; top: 0; z-index: 10;`
- Works with horizontal scroll — test with wide tables

**R8 - Row selection and bulk action bar**
- Add `enableRowSelection: true` prop
- Add checkbox column via `getSortedRowModel` + manual select column
- `onRowSelectionChange?: (selectedIds: string[]) => void`
- Toolbar renders bulk action bar when `selectedIds.length > 0`:
```tsx
{selectedIds.length > 0 && (
  <div className="flex items-center gap-2 bg-muted px-4 py-2 rounded-lg">
    <span className="text-sm">{selectedIds.length} selected</span>
    <Button size="sm" onClick={bulkClose}>Close</Button>
    <Button size="sm" variant="destructive" onClick={bulkCancel}>Cancel</Button>
  </div>
)}
```

**Acceptance Criteria:**

**Given** the Orders list page uses `TanStackDataTable`
**When** the user clicks a column header
**Then** the table sorts by that column (ascending first click, descending second, off third)

**Given** the `TanStackDataTable` has pagination enabled
**When** the user changes page
**Then** `onPaginationChange` fires with the new page index

**Given** the `TanStackDataTable` has `enableColumnResizing: true`
**When** the user drags a column resize handle
**Then** the column width changes and is reflected in the table

**Given** the `TanStackDataTable` has `stickyHeader: true`
**When** the user scrolls down the table
**Then** the header row stays fixed at the top

**Given** the `TanStackDataTable` has `enableRowSelection: true`
**When** the user selects rows via checkboxes
**Then** the bulk action bar appears with the count and available actions

**Given** a migrated table row is clickable or conditionally styled
**When** the table renders
**Then** `rowLabel`, `getRowClassName`, keyboard activation, and cell click behaviors continue to work

---

## Key Constraints

- `ToastProvider` must be rendered at the app root before any component calls `useToast()`.
- Toast is for transient action feedback; `SurfaceMessage` remains the pattern for persistent inline states.
- DatePicker must be tested on iOS Safari — react-day-picker has mobile quirks.
- Zod schemas must stay in sync with backend Pydantic schemas. Any divergence is a bug.
- Breadcrumb on list pages should not show a link on the current page.
- Breadcrumb must extend the existing `PageHeader` hero layout without removing the current hero/tabs composition.
- Do not introduce shadcn/ui as a dependency — build on top of existing Base UI + Radix + Tailwind stack.
- TanStack Table v8 is headless — render with `flexRender(cell.column.columnDef.cell, cell.getContext())` from TanStack Table, NOT the custom cell renderer pattern.
- Column resize and sticky header must work together — test with both enabled simultaneously.

---

## Key File Changes

| File | Action |
|------|--------|
| `src/components/ui/Toast.tsx` | New |
| `src/providers/ToastProvider.tsx` | New |
| `src/hooks/useToast.ts` | New |
| `src/components/ui/DatePicker.tsx` | New |
| `src/components/ui/DateRangePicker.tsx` | New |
| `src/components/ui/Breadcrumb.tsx` | New |
| `src/components/ui/Spinner.tsx` | New |
| `src/components/ui/StatusBadge.tsx` | New |
| `src/components/ui/QuickEntryDialog.tsx` | New |
| `src/components/layout/TanStackDataTable.tsx` | New |
| `src/components/layout/PageLayout.tsx` | Modify — add breadcrumb prop to PageHeader |
| `src/index.css` | Modify — fix --ring token, add chart colors |
| `src/lib/schemas/customer.schema.ts` | New |
| `src/lib/schemas/order.schema.ts` | New |
| `src/lib/schemas/invoice.schema.ts` | New |
| `src/lib/schemas/payment.schema.ts` | New |
| `src/lib/schemas/product.schema.ts` | New |
| `src/lib/schemas/supplier.schema.ts` | New |
| `src/domain/inventory/components/AlertFeed.tsx` | Modify — convert to Tailwind |
| `src/domain/inventory/components/CommandBar.tsx` | Modify — convert to Tailwind |
| `src/components/customers/CustomerForm.tsx` | Modify — upgrade to zod |
| `src/domain/payments/components/RecordPaymentForm.tsx` | Rewrite — react-hook-form + zod + toast |
| `src/domain/payments/components/RecordUnmatchedPayment.tsx` | Rewrite — react-hook-form + zod + DatePicker + toast |
| `src/components/filters/DateRangeFilter.tsx` | Modify — replace native date inputs with `DateRangePicker` |
| `src/components/customers/CustomerStatementTab.tsx` | Modify — replace native date filters with `DateRangePicker` |
| `src/pages/AdminPage.tsx` | Modify — replace native date filters with `DateRangePicker` |
| `src/domain/orders/components/OrderForm.tsx` | Modify — add react-hook-form + zod |
| `src/domain/inventory/components/ProductForm.tsx` | Modify — add react-hook-form + zod |
| `src/domain/inventory/components/SupplierForm.tsx` | Modify — add react-hook-form + zod |
| `src/domain/inventory/components/StockAdjustmentForm.tsx` | Modify — add react-hook-form + zod |
| `src/pages/invoices/CreateInvoicePage.tsx` | Modify — add react-hook-form + zod |
| `package.json` | Add: `zod`, `@hookform/resolvers/zod`, `@tanstack/react-table`, `react-day-picker` |

---

## Appendix: Component Inventory After Epic 22

```
src/components/ui/
  Toast.tsx              [NEW]
  DatePicker.tsx         [NEW]
  DateRangePicker.tsx    [NEW]
  Breadcrumb.tsx         [NEW]
  Spinner.tsx            [NEW]
  StatusBadge.tsx        [NEW]
  QuickEntryDialog.tsx   [NEW]
  Badge.tsx              [existing]
  Button.tsx             [existing]
  Card.tsx               [existing]
  Dialog.tsx             [existing]
  Input.tsx              [existing]
  Sheet.tsx              [existing]
  Select.tsx             [existing]
  table.tsx              [existing]

src/components/layout/
  DataTable.tsx          [existing — deprecated after TanStackDataTable ships]
  TanStackDataTable.tsx  [NEW]
  PageLayout.tsx         [modified — breadcrumb slot added]

src/hooks/
  useToast.ts            [NEW]

src/providers/
  ToastProvider.tsx      [NEW]

src/lib/schemas/
  customer.schema.ts     [NEW]
  invoice.schema.ts      [NEW]
  order.schema.ts        [NEW]
  payment.schema.ts      [NEW]
  product.schema.ts      [NEW]
  supplier.schema.ts     [NEW]
```
