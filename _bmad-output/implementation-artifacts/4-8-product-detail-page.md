# Story 4.8: Product Detail Page

**Epic:** 4 — Inventory Operations
**Story ID:** 4.8
**Status:** ready-for-dev

## Story

As a warehouse staff,
I want a dedicated product page instead of a narrow left-side drawer,
So that I can see full analytics, ROP configuration, supplier info, and sales history without the cramped overlay.

## Context

The `ProductDetailDrawer` (currently rendered as a left-overlay in `InventoryPage`) shows: product header, stock health bar, per-warehouse cards, stock trend chart, and recent adjustments. It works but is cramped, cannot show analytics or ROP settings, and the overlay pattern does not support deep-linking.

This story promotes the drawer into a full page at `GET /inventory/:productId` with 4 tabs.

---

## Acceptance Criteria

### AC1: Route changes from drawer to page

**Given** I am on the inventory list (`/inventory`)
**When** I click a product row
**Then** the URL changes to `/inventory/:productId` (e.g. `/inventory/abc-123`)
**And** the full page renders (not the drawer overlay)
**And** the browser back button returns to `/inventory`

**Given** I visit `/inventory/:productId` directly
**When** the page loads
**Then** the product detail page renders with all 4 tabs

### AC2: Tab 1 — Overview

**Given** I am on the product detail page
**When** the Overview tab is active (default)
**Then** I see: product code, name, category badge, status badge
**And** stock health bar with total units
**And** per-warehouse stock cards: warehouse name, current stock, reorder point, last adjusted date
**And** full-width stock trend chart (reuse `StockTrendChart` component)
**And** recent adjustments timeline (reuse `AdjustmentTimeline` component)
**And** footer action buttons: Adjust Stock, Transfer, Order

### AC3: Tab 2 — Analytics

**Given** I am on the product detail page
**When** I click the Analytics tab
**Then** I see a monthly demand bar chart (12-month rolling window)
**And** a sales history table: date, quantity_change, reason_code, actor_id (last 50 records, paginated)
**And** a summary card: avg daily usage, lead time, computed ROP, safety stock
**And** top customer by volume for this product (from order lines)

### AC4: Tab 3 — Settings

**Given** I am on the product detail page
**When** I click the Settings tab
**Then** I see ROP override: editable reorder_point per warehouse (input number)
**And** safety factor slider (0.0–1.0, step 0.1) with live ROP preview
**And** lead time override: editable days per warehouse (input number)
**And** supplier info section: supplier name, unit cost, default lead time (read-only)
**And** when any override is saved, a "Manual override" badge appears on the affected warehouse card in Overview

**Given** a product has no linked supplier
**When** the Settings tab loads
**Then** supplier info section shows "No supplier configured"

### AC5: Tab 4 — Audit Log

**Given** I am on the product detail page
**When** I click the Audit Log tab
**Then** I see a chronological list of all changes to: reorder_point, safety_factor, lead_time_days, status
**And** each entry shows: timestamp, actor_id, field changed, old_value → new_value
**And** entries are paginated, 50 per page

### AC6: Tab switching

**Given** I am on the product detail page
**When** I switch between tabs
**Then** only the tab content updates; the URL (product ID) is preserved
**And** the page does not full-reload

---

## Tasks / Subtasks

### Task 1: Routing & Page Shell (AC1, AC6)

- [ ] Add `PRODUCT_DETAIL_ROUTE = "/inventory/:productId"` to `src/lib/routes.ts`
- [ ] Add route to `App.tsx` using `useParams` pattern (see `InvoicesPage.tsx` for `:invoiceId` precedent)
- [ ] Conditionally render `InventoryPage` (list + drawer) vs `ProductDetailPage` based on `productId` param — or use `InventoryPage` and move detail rendering inside it
- [ ] Remove drawer open logic from `ProductTable.onProductClick`; instead navigate to the new route
- [ ] Add `PRODUCT_DETAIL_ROUTE` to `navigation.tsx` `ROUTE_CONTEXT_KEYS` so sidebar breadcrumb updates
- [ ] Add tab state (`activeTab: 'overview' | 'analytics' | 'settings' | 'audit'`) to the product detail component

### Task 2: Tab 1 — Overview (AC2)

- [ ] Create `src/pages/inventory/ProductDetailPage.tsx` — page shell with 4 tabs
- [ ] Move/adapt product header, stock health bar, per-warehouse cards from `ProductDetailDrawer`
- [ ] Reuse `StockTrendChart` component (already exists)
- [ ] Reuse `AdjustmentTimeline` component (already exists)
- [ ] Reuse footer action buttons (Adjust Stock, Transfer, Order) — link to existing modals/page

### Task 3: Tab 2 — Analytics (AC3)

**Backend:**

- [ ] Add `GET /api/v1/inventory/products/{product_id}/monthly-demand` — returns 12-month rolling monthly totals from `stock_adjustment`
  - Response: `{ month: string (YYYY-MM), total_qty: number }[]`
  - Filter: `reason_code = 'sales_reservation'`, last 12 months
- [ ] Add `GET /api/v1/inventory/products/{product_id}/sales-history` — paginated sales records
  - Query params: `limit` (default 50), `offset` (default 0)
  - Response: `{ items: [{ date, quantity_change, reason_code, actor_id }], total: number }`
- [ ] Add `GET /api/v1/inventory/products/{product_id}/top-customer` — top customer by order line volume
  - Response: `{ customer_id, customer_name, total_qty }` or null

**Frontend:**

- [ ] Create `MonthlyDemandChart` — bar chart, 12 bars, use `recharts` `<BarChart>` (already in project)
- [ ] Create `SalesHistoryTable` — simple table with columns: date, qty, reason, actor
- [ ] Create `AnalyticsSummaryCard` — displays avg_daily, lead_time, ROP, safety_stock (fetch from product detail endpoint)
- [ ] Create `TopCustomerCard` — displays top customer or "No orders yet"

### Task 4: Tab 3 — Settings (AC4)

**Backend:**

- [ ] `inventory_stock` table already has `reorder_point`, `safety_factor`, `lead_time_days` columns — confirm they exist (check model)
- [ ] Add `PATCH /api/v1/inventory/stocks/{stock_id}` — update reorder_point, safety_factor, or lead_time_days per warehouse stock row
  - Request: `{ reorder_point?: number, safety_factor?: number, lead_time_days?: number }`
  - Returns updated `InventoryStockResponse`
- [ ] Add `GET /api/v1/inventory/products/{product_id}/supplier` — returns linked supplier info
  - Response: `{ supplier_id, name, unit_cost, default_lead_time_days }` or null

**Frontend:**

- [ ] Create `SettingsTab` component
- [ ] ROP override input per warehouse (number input, pre-filled with current value)
- [ ] Safety factor slider (`<input type="range" min="0" max="1" step="0.1">`) with live ROP preview = `avg_daily × lead_time × (1 + safety_factor)`
- [ ] Lead time override input per warehouse
- [ ] Save button → `PATCH /api/v1/inventory/stocks/{stock_id}` → success toast
- [ ] Supplier info section (read-only) — or "No supplier configured" empty state
- [ ] Track "has override" state per warehouse and pass to Overview tab to show "Manual override" badge

### Task 5: Tab 4 — Audit Log (AC5)

**Backend:**

- [ ] Add `GET /api/v1/inventory/products/{product_id}/audit-log`
  - Query params: `limit` (default 50), `offset` (default 0)
  - Response: `{ items: [{ id, created_at, actor_id, field, old_value, new_value }], total: number }`
  - Filter by `product_id` (join through `inventory_stock.product_id = product_id`) for reorder_point/safety_factor/lead_time_days changes
  - Filter by `product_id` directly for status changes on `product` table
  - Union both sources, order by `created_at DESC`

**Frontend:**

- [ ] Create `AuditLogTable` — columns: date, actor, field, old → new
- [ ] Pagination controls (prev/next, showing X–Y of Z)
- [ ] Empty state: "No changes recorded"

### Task 6: Navigation & Integration (AC1)

- [ ] `ProductTable` row click → use `useNavigate` to go to `/inventory/:productId` instead of setting `selectedProductId` state
- [ ] Remove `selectedProductId` state from `InventoryWorkspace` (no longer needed for drawer)
- [ ] Remove `<ProductDetailDrawer>` from `InventoryWorkspace` (now a full page)
- [ ] Remove drawer overlay CSS from `inventory.css` if exclusively used by drawer
- [ ] Ensure `/inventory` (no productId) still renders the full inventory workspace (list + alert panel)

### Task 7: Testing

- [ ] Backend: unit tests for each new endpoint (pytest)
- [ ] Frontend: add `ProductDetailPage` to existing test file if any; lint clean

---

## Dev Notes

### Existing patterns to reuse

- **Route params:** `InvoicesPage.tsx` uses `useParams<{ invoiceId: string }>()` with `react-router-dom`; same pattern for `/inventory/:productId`
- **Tab component:** check if `shadcn/ui` `Tabs` is used elsewhere, otherwise implement with simple stateful active tab
- **Chart:** `StockTrendChart.tsx` already uses `recharts` — same library for `MonthlyDemandChart`
- **Table:** `ProductTable` uses `@tanstack/react-table` — reuse for sales history and audit log
- **Toast:** `react-hot-toast` or `sonner` is likely already in use — find and use for save confirmations
- **Drawer CSS:** `src/domain/inventory/inventory.css` — `.inv-drawer-overlay`, `.inv-drawer` — these CSS classes can be removed from that file after migration

### Backend data model notes

- `inventory_stock` table: `id`, `product_id`, `warehouse_id`, `tenant_id`, `current_stock`, `reorder_point`, `safety_factor`, `lead_time_days`, `last_adjusted`, `created_at`, `updated_at`
- `stock_adjustment`: `id`, `tenant_id`, `product_id`, `warehouse_id`, `stock_id`, `quantity_change`, `reason_code`, `actor_id`, `notes`, `created_at`
- `product`: `id`, `code`, `name`, `category`, `status`, `supplier_id` (confirm this column exists)
- `supplier`: `id`, `name`, `unit_cost`, `default_lead_time_days`
- `audit_log` table may already exist — check `common/models/audit_log.py` or similar; if it does, use it for the audit log tab

### File locations

```
Backend:
  backend/domains/inventory/routes.py       — add new endpoints
  backend/domains/inventory/services.py    — add new service functions
  backend/domains/inventory/schemas.py     — add Pydantic request/response schemas

Frontend:
  src/pages/inventory/ProductDetailPage.tsx  — NEW page component
  src/domain/inventory/components/              — new components:
    MonthlyDemandChart.tsx
    SalesHistoryTable.tsx
    AnalyticsSummaryCard.tsx
    TopCustomerCard.tsx
    SettingsTab.tsx
    RopOverrideInput.tsx
    AuditLogTable.tsx
  src/domain/inventory/hooks/               — new hooks:
    useProductMonthlyDemand.ts
    useProductSalesHistory.ts
    useProductTopCustomer.ts
    useProductAuditLog.ts
    useUpdateStockSettings.ts
  src/lib/routes.ts                         — add PRODUCT_DETAIL_ROUTE
  src/App.tsx                               — add route
  src/pages/InventoryPage.tsx               — remove drawer logic
  src/domain/inventory/components/ProductDetailDrawer.tsx  — deprecate after migration
```

### Performance notes

- Monthly demand: aggregate on DB side (GROUP BY DATE_TRUNC), don't load all adjustment rows to frontend
- Sales history: use `limit`/`offset` pagination (already in endpoint spec)
- Audit log: use indexed columns (`created_at`, `product_id`) for efficient pagination

---

## Dependencies

- **Prerequisites:** Stories 4.1, 4.2, 4.6 (completed) — product search, stock detail, warehouse context all exist
- **Conflict:** Story 4.7 (auto-calculate ROP) is in backlog — this story adds manual ROP overrides; they coexist (override wins per-row when set)

---

## Out of Scope

- Editing product name, code, category (Story 4.x does not cover product master data editing)
- Creating/editing suppliers — follow-on story
- Projected availability or order quantity suggestions — follow-on story
- Reorder point auto-calculation UI (Story 4.7 admin panel already exists as `ReorderPointAdmin`)
