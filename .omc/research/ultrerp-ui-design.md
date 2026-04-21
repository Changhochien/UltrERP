# UltrERP UI Design System — Component Inventory & Quality Assessment

## 1. Component Library

### UI Framework

**Base Components:** Base UI (base-ui/react) — a headless UI library built by Cursor/MANNI Studio. Used for Button, Input, Checkbox, Radio, Switch, Select, Dialog, Popover, Separator, Progress.

**Primitive Wrappers:** Radix UI (@radix-ui/react-*) — used for Select, Tabs, Tooltip, DropdownMenu, Avatar, ScrollArea, Dialog (Sheet variant), Tooltip.

**Custom Components:** Tailwind CSS v4 with CSS custom properties (design tokens), CVA (class-variance-authority) for variant management.

### Full Component Inventory

#### Layout Components (`src/components/layout/`)
- **DataTable** — Generic paginated table with sort, filter, toolbar, skeleton loading, empty state, row click, row class fn, pagination bar
- **PageLayout** — exports PageHeader (with hero/eyebrow pattern), PageHero, SectionCard, MetricCard, PaginationBar, SurfaceMessage
- **PageTabs** — Animated tab bar using Framer Motion, memoized, with sliding indicator

#### Shared UI Primitives (`src/components/ui/`)
| Component | Variants | Notes |
|---|---|---|
| `Button` | default, outline, secondary, ghost, destructive, link | Sizes: default, xs, sm, lg, icon, icon-xs, icon-sm, icon-lg |
| `Input` | — | Base UI wrapper, h-8, rounded-lg |
| `Textarea` | — | field-sizing-content, min-h-16 |
| `Select` | — | Radix UI, rounded-2xl content |
| `Checkbox` | — | Base UI, custom check icon |
| `RadioGroup` / `RadioGroupItem` | — | Base UI, circular indicator |
| `Switch` | default, sm | Base UI, pill toggle |
| `Label` | — | — |
| `Badge` | default, secondary, outline, neutral, info, success, warning, destructive | CVA, uppercase tracking |
| `Card` | — | CardHeader, CardTitle, CardDescription, CardContent, CardFooter |
| `Dialog` | — | Base UI, with overlay, portal, header/footer/title/description |
| `Sheet` | — | Radix Dialog, slide-in panel (right/top/bottom/left) |
| `Popover` | — | Base UI Popover with Header/Title/Description |
| `DropdownMenu` | — | Radix UI, full set: Item, CheckboxItem, Label, Separator, Shortcut, SubTrigger/SubContent |
| `Tooltip` | — | Radix UI, simple wrapper |
| `Command` | — | cmdk-based, CommandDialog/Input/List/Empty/Group/Item/Separator/Shortcut |
| `Tabs` | — | Radix UI, TabsList/Trigger/Content |
| `Avatar` | — | Radix UI, AvatarImage + AvatarFallback |
| `Progress` | — | Base UI, ProgressTrack/Indicator/Label/Value |
| `Separator` | horizontal, vertical | Base UI |
| `ScrollArea` | — | Radix UI ScrollArea with custom ScrollBar |
| `Skeleton` | — | animate-pulse, rounded-xl bg-muted |
| `InputGroup` | — | Complex addon/input/textarea grouping with align variants |
| `InfoPopover` | — | LabeledInfoPopover compound |
| `Field` | vertical, horizontal, responsive | CVA, with FieldLabel, FieldError, FieldDescription, FieldGroup, FieldSeparator |

### Design Tokens (CSS Custom Properties)

**Light Mode:**
- `--background`: oklch(1 0 0), `--foreground`: oklch(0.145 0 0)
- `--primary`: oklch(0.205 0 0), `--primary-foreground`: oklch(0.985 0 0)
- `--secondary`: oklch(0.97 0 0), `--muted`: oklch(0.97 0 0)
- `--accent`: oklch(0.97 0 0), `--destructive`: oklch(0.577 0.245 27.325)
- `--border`: oklch(0.922 0 0), `--input`: oklch(0.922 0 0), `--ring`: oklch(0.708 0 0)
- `--radius`: 0.625rem (10px)
- `--sidebar`: oklch(0.985 0 0)
- Semantic color tokens: `--success`, `--warning`, `--info`, `--neutral` with -foreground, -surface, -border variants
- Chart tokens: --chart-1 through --chart-5 (monochrome)

**Dark Mode:** Full dark-mode override with adjusted oklch values. Uses `.dark` class on `<html>`.

**Tone Utilities:** `.tone-success`, `.tone-warning`, `.tone-info`, `.tone-neutral`, `.tone-destructive` classes for alert-style colored surfaces.

**Alert Utilities:** `.alert-success`, `.alert-warning`, `.alert-info`, `.alert-neutral`, `.alert-destructive` for inline alert boxes.

**Surface Hero:** `.surface-hero` gradient utility using `--hero-start`, `--hero-mid`, `--hero-end`.

**Key Observations:**
- Uses oklch color space (modern, perceptually uniform)
- No `--ring` semantic alias to `--primary` (ring is gray, not primary)
- Chart colors are all monochrome — no color-coded charts by default
- `--sidebar-primary` is blue (oklch(0.52 0.08 240)) in dark mode but gray in light mode

---

## 2. Form Components

### Field System

The `Field` component (`src/components/ui/field.tsx`) is a layout wrapper supporting three orientations: `vertical`, `horizontal`, and `responsive` (stacks on mobile, side-by-side on desktop).

**Form field composition:**
```
Field
  FieldLabel (Label + required indicator)
  [Input | Select | Combobox | Textarea]
  FieldDescription
  FieldError
```

**Validation Errors:** `FieldError` component accepts `errors?: Array<{ message?: string }>` and renders a `<ul>` list of errors with `role="alert"`. Error text is red (`text-destructive`). Does NOT automatically integrate with react-hook-form — form must manually pass errors.

### Form Components

**CustomerForm** (`src/components/customers/CustomerForm.tsx`):
- Uses `react-hook-form` with a **custom native resolver** (not Zod)
- `buildNativeResolver()` maps field-level validation rules to error keys
- i18n translation keys used for error messages (e.g., `"customer.form.companyNameRequired"`)
- `serverErrors` prop maps API errors onto fields via `setError()`
- No `zod` schema — validation is scattered across a custom resolver function
- Two-column grid layout (`sm:grid-cols-2`)

**CustomerCombobox** (`src/components/customers/CustomerCombobox.tsx`):
- Popover + Command (cmdk) pattern for customer autocomplete
- Debounced 300ms server-side search
- Inline "Create new customer" panel with mini-form
- Handles duplicate detection with `window.confirm()` dialog
- Loads all 200 active customers on open, server-filters as query types

**InputGroup** (`src/components/ui/input-group.tsx`):
- Complex compound component: InputGroup > InputGroupAddon + InputGroupInput
- Supports addons on all four sides (inline-start, inline-end, block-start, block-end)
- Can wrap Button for icon buttons that focus the input
- Integrates with combobox via `in-data-[slot=combobox-content]:focus-within:border-inherit`

**StatusMultiSelect** (`src/components/filters/StatusMultiSelect.tsx`):
- Popover + Checkbox list for multi-select status filtering
- Exports reusable `INVOICE_STATUS_OPTIONS` and `ORDER_STATUS_OPTIONS` arrays

**DateRangeFilter** (`src/components/filters/DateRangeFilter.tsx`):
- Two native `<input type="date">` fields, no calendar picker component
- Minimal styling with h-8 inputs

**SearchInput** (`src/components/filters/SearchInput.tsx`):
- Native `<input type="text">` with Search icon
- 300ms debounce on `onChange`
- Does NOT use the Input component (inconsistent)

**InvoiceLineEditor** (`src/domain/invoices/components/InvoiceLineEditor.tsx`): [exists but not read in full]

**RecordPaymentForm** (`src/domain/payments/components/RecordPaymentForm.tsx`):
- Controlled form with local useState (no react-hook-form)
- Uses native `<select>` for payment method
- Uses native `<textarea>` for notes
- No validation library — inline manual checks

### Validation Gaps
- **Inconsistent validation approach**: CustomerForm uses react-hook-form with custom resolver; RecordPaymentForm uses raw useState; other forms may differ
- **No Zod integration** — validation schemas are not centralized
- **No form-level error summary** — only FieldError per-field
- **No loading state on submit buttons** — `disabled` prop is used but no spinner
- **Native date inputs** — no calendar picker component exists in the UI library

---

## 3. Layout Components

### Page Layout (`src/components/layout/PageLayout.tsx`)

**PageHeader:**
- Hero pattern with eyebrow badge, title (h1), description
- Actions area (rendered in a frosted-glass panel on xl screens)
- Optional tabs slot below the content area
- Background: `surface-hero` gradient with radial blur glow

**SectionCard:**
- Standard Card wrapper with optional title/description/actions
- Content padding adjustment when header is present

**MetricCard:**
- KPI display card with sparkline (SVG polyline), trend badge
- Supports `trendDirection: "up" | "down" | "flat"` with arrow icons

**SurfaceMessage:**
- Inline alert-style message with tone variants: default, danger, success, warning

### Sidebar (`src/components/ui/sidebar.tsx`)

- Collapsible (w-72 expanded, w-20 collapsed)
- Mobile: overlay with backdrop blur, w-72 drawer
- Desktop: fixed, hidden on mobile
- `SidebarProvider` wraps `TooltipProvider` and root div
- `SidebarInset` applies padding-left based on sidebar state
- `SidebarGroup` with `SidebarGroupLabel` that hides when collapsed
- LocalStorage persistence of open state (`ultrerp.sidebar.open`)

### Navigation (`src/components/AppNavigation.tsx`)

- NavLink via React Router with `end` prop for exact match on "/"
- Active state: border + background + shadow
- ChevronRight arrow animates on hover
- Permission-gated items via `canAccess(item.feature)`
- User menu with Avatar, role badge, tenant info
- Language switcher in sidebar footer
- Theme toggle in user dropdown menu

### Loading & Empty States

- **Skeleton** component: `animate-pulse rounded-xl bg-muted/70`
- **DataTable**: Skeleton rows during loading (configurable `loadingRowCount`)
- **Empty state**: centered message with title + description
- **Error state**: `role="alert"` box with destructive styling
- **No dedicated Spinner component** — Skeleton or text shown during loading

---

## 4. Data Table / List View

### DataTable (`src/components/layout/DataTable.tsx`)

**Features:**
- Column definitions with `id`, `header`, `cell` (render fn), `sortable`, `getSortValue`, `className`, `onClick`
- Client-side sort with `useMemo` + localeCompare (when `sortState` + `onSortChange` not provided)
- Server-side sort (when `sortState` + `onSortChange` provided — URL-driven)
- Pagination with Previous/Next buttons, page count, item range display
- Row click handler with keyboard support (Enter/Space)
- `getRowClassName` for conditional row styling (e.g., overdue highlight)
- `getRowId` for stable row keys
- Loading: renders N skeleton rows
- Empty state: centered title + description
- Error state: destructive alert box
- Toolbar slot: `DataTableToolbar` wrapper
- Filter bar slot: rendered between toolbar and table

**Pagination Bar:** Custom `PaginationBar` component but DataTable also has inline pagination.

### TanStack Table

**Not directly used.** The DataTable is a custom implementation. No `@tanstack/react-table` import found in the codebase.

### List Components Using DataTable
- **InvoiceList** (`src/domain/invoices/components/InvoiceList.tsx`) — URL-synced filters, CustomerCombobox, DateRangeFilter, StatusMultiSelect, SearchInput, ActiveFilterBar, overdue row highlighting
- **OrderList** (`src/domain/orders/components/OrderList.tsx`) — same filter pattern
- **ReorderAlerts** (`src/domain/inventory/components/ReorderAlerts.tsx`) — DataTable with action buttons (Acknowledge, Snooze, Dismiss)
- **AlertFeed** (`src/domain/inventory/components/AlertFeed.tsx`) — NOT a DataTable, custom scrollable alert list with CSS-based styling (alert-sidebar pattern)

### URL-Driven Filtering Pattern

Both InvoiceList and OrderList use `useSearchParams()` to derive filter state. All filters serialize to URL params (`payment_status`, `customer_id`, `date_from`, `date_to`, `search`, `sort_by`, `sort_order`). Filter changes call `setSearchParams()` which triggers re-render and re-fetch.

**ActiveFilterBar** (`src/components/filters/ActiveFilterBar.tsx`): Renders chips for each active filter with dismiss (×) button and "Clear all" action.

---

## 5. Domain-Specific Components

### Customers (`src/components/customers/`)
- `CustomerAnalyticsTab`, `CustomerDetailDialog`, `CustomerForm`, `CustomerInvoicesTab`, `CustomerOrdersTab`, `CustomerOutstandingTab`, `CustomerResultsTable`, `CustomerSearchBar`, `CustomerStatementTab`, `CustomerCombobox`, `DuplicateCustomerWarning`, `EditCustomerDialog`

### Invoices (`src/components/invoices/`)
- `InvoiceExportButton`, `InvoiceTotalsCard`, `InvoiceLineEditor`, `InvoicePrintPreviewModal`, `InvoicePrintSheet`

### Filters (`src/components/filters/`)
- `ActiveFilterBar`, `ActiveFilterChip`, `DateRangeFilter`, `SearchInput`, `StatusMultiSelect`

### Inventory (`src/domain/inventory/components/`)
- `AdjustmentTimeline`, `AlertFeed`, `AnalyticsSummaryCard`, `AnalyticsTab`, `AuditLogTable`, `CommandBar`, `InventoryMetrics`, `PlanningSupportCard`, `ProductGrid`, `ReorderAlerts`, `SalesHistoryTable`, `StockHistoryModal`, `SupplierOrderDetail`, `SupplierOrderList`, `TopCustomerCard`, `WarehouseSelector`, `CreateProductForm`, `MonthlyDemandChart`

### Dashboard (`src/domain/dashboard/components/`)
- `APAgingCard`, `ARAgingCard`, `CashFlowCard`, `GrossMarginCard`, `KPISummaryCard`, `LowStockAlertsCard`, `RevenueCard`, `RevenueTrendChart`, `TopCustomersCard`, `TopProductsCard`, `VisitorStatsCard`

### Intelligence (`src/domain/intelligence/components/`)
- `AffinityMatrix`, `CategoryTrendRadar`, `CustomerBuyingBehaviorCard`, `CustomerProductProfile`, `OpportunitySignalBanner`, `ProductPerformanceCard`, `ProspectGapTable`, `RevenueDiagnosisCard`, `RiskSignalFeed`

### Orders (`src/domain/orders/components/`)
- `OrderDetail`, `OrderList`

### Payments (`src/domain/payments/components/`)
- `PaymentHistory`, `ReconciliationScreen`, `RecordPaymentForm`, `RecordUnmatchedPayment`

### Purchases (`src/domain/purchases/components/`)
- `SupplierInvoiceDetail`, `SupplierInvoiceList`

### Reusable Patterns Across Domains
- **DataTable** is the standard list component across Invoice, Order, ReorderAlerts, CustomerResultsTable
- **SectionCard** wraps domain-specific content sections
- **Filter bar pattern**: SearchInput + CustomerCombobox + DateRangeFilter + StatusMultiSelect consistently composed in toolbar
- **Badge with variant** for status display: `statusBadgeVariant()` helper functions in each domain hook
- **ActiveFilterBar** for URL-synced filter display and dismissal

---

## 6. Design Quality Gaps

### Missing Components (vs ERPnext)
- **No Calendar/DatePicker component** — native `<input type="date">` used everywhere
- **No ColorPicker** — not relevant for ERP
- **No Rich Text Editor** — not present
- **No File Upload component** — no attachment/upload UI
- **No Breadcrumb component** — no breadcrumb navigation
- **No Toast/Notification system** — no toast messages for success/error feedback
- **No Command Palette (global)** — Command component exists but is not used as a global ⌘K palette
- **No Multi-step Form wizard** — no stepper component
- **No DataGrid with inline editing** — no editable cells
- **No Tree component** — for category trees, BOMs
- **No Kanban board** — no board view
- **No Chart builder** — no custom chart configuration UI

### Inconsistent Styling
- **AlertFeed** uses raw CSS classes (`.alert-sidebar`, `.alert-item`, `.alert-filters`) from `inventory.css` — not Tailwind. This is the only component using CSS-class-based styling instead of Tailwind. Inconsistent with the rest of the app.
- **CommandBar** uses CSS classes (`.command-bar`, `.command-search`, `.drawer-action-btn`) — also raw CSS
- **RecordPaymentForm** uses native `<select>` and `<textarea>` instead of UI library components
- **InvoicePrintSheet** has its own `invoice-print.css` with print-specific styles
- **ReorderAlerts** uses native `<select>` for status/warehouse filters instead of Select component
- Some places use `className` directly on elements, others use the `cn()` utility

### Micro-interactions Missing
- **No Toast notifications** — success/error feedback relies on form re-render or alert boxes
- **No loading spinners** — only Skeleton components and `disabled` buttons
- **No inline success confirmation** — forms navigate away or nothing confirms success
- **No empty state illustrations** — just text
- **No drag-to-reorder** — no drag-drop anywhere
- **No copy-to-clipboard feedback** — no toast on copy

### Accessibility Gaps
- **Focus management after dialog close** — not explicitly handled
- **No `aria-live` regions** except `aria-live="polite"` on pagination count
- **No keyboard shortcuts documentation** — ShortcutOverlay exists but shortcuts are limited
- **No skip-to-content link** — no bypass blocks
- **Color contrast** — not systematically audited
- **No `role="status"` for dynamic content updates** (alerts, reconciliation totals)

### Responsive Design Issues
- **DataTable** overflows with `overflow-x-auto` — horizontal scroll is the only mobile strategy
- **PageHeader** actions panel stacks on xl, not on mobile — good but only xl breakpoint
- **InvoiceList/OrderList** toolbar: `flex-wrap` helps but on very small screens could overflow
- **Sidebar** collapses to icon-only on desktop but mobile drawer has no close-on-navigation behavior for `<a>` links (only button close)
- **No mobile-specific list views** — same table on mobile
- **No responsive typography scale** — body text is same size on mobile

### PageTabs Animation
- Uses Framer Motion `layoutId` for animated indicator — smooth but adds bundle weight
- `useReducedMotion` respected — good

---

## 7. Form Building Patterns

### React Hook Form Usage

**Pattern A: react-hook-form + custom native resolver (CustomerForm)**
```tsx
const { register, handleSubmit, setError, formState: { errors } } = useForm({
  resolver: buildNativeResolver(t),  // custom async resolver
  defaultValues: { ... },
  mode: "onSubmit",
});
// Credit limit custom check after hook-form validation
// Taiwan business number checksum after form validation
// Server errors mapped via setError()
```

**Pattern B: Raw useState (RecordPaymentForm)**
```tsx
const [amount, setAmount] = useState(String(outstandingBalance));
// Manual validation checks, mutate() from useCreatePayment hook
```

### Zod Validation
**Not used.** No Zod schemas found in the codebase. Validation is custom or relies on HTML5 `type="email"`, `min`, `max` attributes.

### Field Arrays (Line Items)
**InvoiceLineEditor** exists but not read in full. Cannot confirm if it uses `useFieldArray` from react-hook-form.

### Error Display Pattern
- Form-level errors: `SurfaceMessage tone="danger"` at top of form
- Field-level errors: `<FieldError errors={errors.fieldName ? [...] : []} />`
- Server errors: `setError(fieldName, { message: t(key) })` maps to FieldError

---

## 8. Navigation & Routing

### React Router v7

**Route definitions** in `src/lib/routes.ts`:
- Flat TypeScript constants: `HOME_ROUTE`, `INVENTORY_ROUTE`, `CUSTOMERS_ROUTE`, etc.
- Typed `AppRoute` union type
- Builder functions: `buildSupplierDetailPath()`, `buildCountSessionDetailPath()`, `buildProductDetailPath()`, `buildInventoryTransfersPath()`

**Page files** in `src/pages/`:
- Flat structure: `DashboardPage.tsx`, `InvoicesPage.tsx`, `OrdersPage.tsx`, `PaymentsPage.tsx`, `PurchasesPage.tsx`, `IntelligencePage.tsx`, `AdminPage.tsx`, `SettingsPage.tsx`, `LoginPage.tsx`
- Subdirectories: `customers/`, `inventory/`, `orders/`, `invoices/`, `settings/`
- Nested routes not visible in file structure (likely in `App.tsx` or `main.tsx`)

**Navigation Features:**
- `NavLink` with `end` prop for exact root match
- `APP_NAVIGATION_GROUPS` imported from `src/lib/navigation` — controls visible nav items based on permissions
- Permission gating: `canAccess(item.feature)` filter on nav items
- `handleNavigation()` closes mobile sidebar on nav

**Breadcrumbs:** Not implemented. No Breadcrumb component or usage found.

**URL vs UI Filtering:**
- **URL-driven:** InvoiceList, OrderList, CustomerResultsTable — all filters sync to URL params via `useSearchParams`
- **UI-only:** Some filter components (DateRangeFilter, SearchInput) still call back to parent which updates URL
- This is consistent — URL is source of truth for all list views

**Filter-Sort Pattern:**
```
useSearchParams() → derive filter state
→ useDomainHook({ ...filters })
→ DataTable with onSortChange → setSearchParams()
→ re-render, re-derive, re-fetch
```

---

## Summary

UltrERP has a **well-structured component library** with consistent patterns:
- Base UI + Radix UI as primitives
- Tailwind CSS v4 with oklch design tokens
- Strong DataTable abstraction with URL-synced filtering
- Consistent form field composition with Field component
- Good i18n integration

**Key improvement opportunities:**
1. **No toast notification system** — critical UX gap
2. **No date picker** — native inputs everywhere
3. **Inconsistent CSS vs Tailwind** — AlertFeed and CommandBar use raw CSS classes
4. **No Zod** — validation scattered, no schema centralized
5. **No global command palette** — ⌘K palette exists but not wired globally
6. **No breadcrumb navigation**
7. **Chart colors all monochrome** — limited data visualization
8. **Mobile table experience** — horizontal scroll only, no responsive cards
9. **No inline editing in tables** — read-only everywhere
10. **RecordPaymentForm doesn't use react-hook-form** — inconsistent form approach
