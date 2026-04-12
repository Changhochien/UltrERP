# Story 4.7: Auto-Calculate Reorder Points

**Epic:** 4 — Inventory Operations
**Story ID:** 4.7
**Status:** done

## Story

As a warehouse staff member,
I want the system to calculate reorder points for eligible product and warehouse stock rows using real demand history and replenishment lead times,
So that alerts focus on items that genuinely need replenishment without overwriting manually managed thresholds or relying on guesswork.

---

## Context

The reorder alert system (Story 4.3) exists and is correct, but all products currently have `reorder_point = 0`, so no alerts ever fire.

This story should implement reorder point calculation as a scoped, explainable replenishment policy for stock rows that have usable history. It should not behave like a full forecasting engine or a blanket bulk overwrite across every SKU and warehouse.

**Core formula:** `ROP = Safety Stock + (Lead Time x Average Daily Usage)`

- Safety Stock = `avg_daily_usage x safety_factor x lead_time_days`
- Average Daily Usage = whitelisted outbound demand over lookback window / lookback days
- Lead Time = actual average from resolved replenishment-source history, or source default lead time; rows without reliable lead time stay in review instead of using a guessed fallback

**Holistic replenishment principles for this story:**

- Compute only for eligible inventory rows in the selected scope, not blindly for every row.
- Use demand-relevant stock movements only; do not treat every negative adjustment as consumption.
- Resolve a replenishment source before using supplier lead time; skip ambiguous rows rather than guessing.
- Make preview results explainable so planners can trust the output.
- Apply only selected preview rows so manually managed thresholds are not overwritten by accident.
- Keep the current alert trigger (`current_quantity <= reorder_point`) for now; projected availability, reorder quantity policy, MOQ, and order multiples are follow-on work.

**V1 demand basis:**

- Include `sales_reservation` outbound adjustments in average daily usage.
- Exclude correction noise such as `correction`, `damaged`, `returned`, `other`, and inbound reasons.
- Do not include `transfer_out` in v1 until transfer intent can be distinguished between true consumption and stock rebalancing.

**V1 replenishment-source rule:**

- Resolve source from supplier receipt history for the same product and warehouse.
- If a clear single supplier source can be resolved, use its historical lead time.
- If the source is ambiguous, return a skipped preview row with a reason such as `source_unresolved`.

---

## Acceptance Criteria

### AC1: Sales confirmation creates usable demand history

**Given** a confirmed sales order exists with line items
**When** the order is confirmed
**Then** `StockAdjustment` records are created for each line with reason `sales_reservation`
**And** `StockChangedEvent` is emitted so reorder alerts can fire
**And** those outbound adjustments become eligible demand history for reorder point calculation

### AC2: Only eligible rows and whitelisted demand signals are used

**Given** product and warehouse inventory rows exist
**When** I trigger reorder point computation
**Then** only active product inventory rows in the selected scope are evaluated
**And** average daily usage is calculated from whitelisted outbound demand reasons only
**And** correction, damaged, returned, other, and inbound adjustments are excluded from usage math

### AC3: Replenishment source is resolved before lead time is calculated

**Given** an eligible product and warehouse row has demand history
**When** reorder points are computed
**Then** the system resolves a replenishment source from supplier receipt history for that product and warehouse
**And** if a clear source exists, actual lead time is averaged from received supplier orders for that source
**And** if no actual lead time history exists, `supplier.default_lead_time_days` is used when a reliable source can be resolved
**And** if no reliable lead time exists, the row is skipped with reason `lead_time_unconfigured`
**And** if multiple competing sources exist and no clear source can be resolved, the row is skipped with reason `source_unresolved`

### AC4: Reorder point preview is explainable before saving

**Given** I am on the reorder point admin UI
**When** I set safety factor, lookback days, and scope filters, then click `Preview`
**Then** I see a decision-focused preview with:
- summary cards for candidate rows, selected rows, skipped rows, and rows missing lead time
- a compact candidate table for scanning and batch selection
- a detail panel that explains demand signal, stock position, lead time quality, and recommendation inputs for the focused row
- skipped rows that clearly explain whether demand history, replenishment source, or lead time configuration is missing
**And** no values are saved yet

### AC5: Apply updates only explicitly selected preview rows

**Given** I have reviewed the dry-run preview
**When** I select rows and click `Apply`
**Then** only the selected eligible rows have `inventory_stock.reorder_point` updated
**And** skipped rows and unselected rows are not overwritten
**And** the apply response returns updated count, skipped count, and the parameters used for the run
**And** alerts immediately begin firing for products now below their new threshold

### AC6: Insufficient history is skipped instead of forced

**Given** a product and warehouse row has no usable demand history or too few demand events in the lookback window
**When** reorder points are computed
**Then** the row is excluded from auto-update
**And** the preview shows a note such as `insufficient_history`
**And** rows missing reliable lead time remain in review instead of silently defaulting to 7 days

---

## Completion Notes (2026-04-12)

- Reworked the reorder-point admin UI into a clearer workflow: parameter controls, decision rules, summary cards, compact candidate/skipped tables, and a localized detail panel.
- Removed the silent 7-day default from the product planning settings UI; unset lead time now stays explicit and blocks auto-preview messaging until configured.
- Changed reorder-point preview behavior so rows with unresolved lead time no longer auto-enter candidates with `fallback_7d`; they now surface as `lead_time_unconfigured` review rows.
- Added localized review notes for lead-time confidence and policy fallback behavior, so planners do not need to decode raw backend notes.
- Validated with focused backend integration tests, focused frontend Vitest coverage, and end-to-end browser verification against a fresh backend instance proxied through the frontend dev server.

---

## Technical Notes

### Existing architecture

- **Event system**: `StockChangedEvent` in `backend/common/events.py` is emitted by `transfer_stock`, `create_stock_adjustment`, and `receive_supplier_order` via `emit()`. Handler `handle_reorder_alert` in `backend/domains/inventory/handlers.py` creates or updates `ReorderAlert` when `current_quantity <= reorder_point`.

- **Alert model**: `backend/common/models/reorder_alert.py` defines `ReorderAlert` with `AlertStatus` enum (`PENDING`, `ACKNOWLEDGED`, `RESOLVED`) and a unique constraint on `(tenant_id, product_id, warehouse_id)`.

- **Inventory stock model**: `backend/common/models/inventory_stock.py` stores per-product and per-warehouse stock rows with `quantity` and `reorder_point`.

- **Demand history model**: `backend/common/models/stock_adjustment.py` stores `product_id`, `warehouse_id`, `quantity_change`, `reason_code`, `actor_id`, and `created_at`. Relevant reason codes already include `sales_reservation`, `sales_release`, `transfer_out`, `transfer_in`, and `supplier_delivery`.

- **Product model**: `backend/common/models/product.py` includes `status`, which can be used as an initial eligibility filter for active products.

- **Supplier receipt history**: `backend/common/models/supplier_order.py` and `supplier_order_line.py` already link supplier, product, warehouse, `order_date`, and `received_date`, which can be used to calculate source-specific lead time.

- **Order confirm**: `backend/domains/orders/service.py` `confirm_order()` currently does not emit `StockChangedEvent`. This is the key gap for outbound demand history.

- **Alert queries**: `list_reorder_alerts()` in `backend/domains/inventory/services.py` joins `ReorderAlert` with `Product` and `Warehouse`.

- **Frontend**: `LowStockAlertsCard` in `src/domain/dashboard/components/LowStockAlertsCard.tsx` fetches pending alerts. `useReorderAlerts` in `src/domain/inventory/hooks/useReorderAlerts.ts` already exists.

- **Current limitation**: alert logic compares current quantity to reorder point only. This story does not add projected-availability-based planning.

### What needs to be built

1. **`confirm_order` emits `StockChangedEvent` and creates clean demand history**
   - For each confirmed sales line, create outbound stock history with reason `sales_reservation`
   - Emit `StockChangedEvent` so alerts and usage calculations share the same signal

2. **Historical query support for product and warehouse lookbacks**
   - Add a composite index on `stock_adjustment` to support tenant, product, warehouse, and created-at historical queries efficiently

3. **`backend/domains/inventory/reorder_point.py` service module**
   - `get_average_daily_usage(session, tenant_id, product_id, warehouse_id, lookback_days=90, allowed_reasons=(ReasonCode.SALES_RESERVATION,))`
   - `resolve_replenishment_source(session, tenant_id, product_id, warehouse_id, lookback_days=180)` returning either a resolved supplier or a skip reason
   - `get_actual_lead_time_days(session, tenant_id, product_id, warehouse_id, supplier_id, lookback_days=180)`
   - `compute_reorder_point_preview_row(...)` returning computed values plus explanation metadata
   - `compute_reorder_points_preview(session, tenant_id, safety_factor, lookback_days, filters)` returning candidate and skipped rows
   - `apply_reorder_points(session, tenant_id, selected_rows, run_parameters)` updating only explicitly selected preview rows

4. **API endpoints** in `backend/domains/inventory/routes.py`
   - `POST /api/v1/inventory/reorder-points/compute` returning explainable preview rows and skipped rows
   - `PUT /api/v1/inventory/reorder-points/apply` accepting explicit selected stock rows from the preview

5. **Frontend admin workflow** in `src/domain/inventory/components/ReorderPointAdmin.tsx`
   - Safety factor slider (`0.0-1.0`, default `0.5`)
   - Lookback days selector (`30 / 60 / 90 / 180`)
   - Scope filters such as warehouse and category where feasible
   - Preview table with selection checkboxes
   - Explanation columns for demand basis, movement count, lead time source, and skipped reason
   - Apply button that updates selected rows only

6. **Migration**
   - Add the stock-adjustment historical query index needed for reorder point preview performance

### Files to create

- `backend/domains/inventory/reorder_point.py` — computation and preview service
- `src/domain/inventory/components/ReorderPointAdmin.tsx` — admin UI
- `src/domain/inventory/hooks/useReorderPointAdmin.ts` — API hook
- `migrations/versions/xxxxxxxx_add_stock_adjustment_history_index.py`

### Files to modify

- `backend/domains/orders/service.py` — emit `StockChangedEvent` in `confirm_order`
- `backend/domains/inventory/routes.py` — add reorder-point preview and apply endpoints
- `backend/domains/inventory/schemas.py` — add request and response models for preview and apply
- `src/lib/api/inventory.ts` — add `computeReorderPoints()` and `applyReorderPoints()`
- `src/domain/inventory/components/ReorderAlerts.tsx` — add entry point to reorder point admin workflow

### Testing

- `backend/tests/domains/inventory/test_reorder_point_calculation.py`
  - formula calculation
  - demand-reason filtering
  - lead-time fallback behavior
  - ambiguous source skip behavior

- `backend/tests/domains/inventory/test_reorder_point_integration.py`
  - confirm order -> demand history -> preview -> apply selected rows
  - insufficient-history skip behavior
  - unselected rows remain unchanged

- Frontend
  - manual browser test for preview selection flow and explanation columns

### What NOT to build (see Follow-on Items below)

- No background scheduler; computation remains API-triggered
- No new database tables
- No projected-availability or forecast-based alerting in this story
- No automatic purchase-order, transfer-order, or manufacturing-order creation
- No MOQ, maximum order quantity, order multiple, or min/max target policy yet
- No seasonality, ABC/XYZ segmentation, or service-level-based safety stock yet
- No transfer-out demand modeling until transfer intent can be classified safely

### Follow-on Items (post-Story 4.7)

These items were identified during development as necessary for a complete replenishment system but were intentionally deferred from this story's scope.

#### Follow-on A: Static Minimum Threshold Alerts

**Problem:** 6,558 products (99.5%) are skipped because `movement_count < 2` — they have no usable demand history. These products never fire low-stock alerts even when physically at zero stock.

**What to build:**
- A static minimum threshold per product or warehouse (e.g., `min_stock = 10` units)
- Separate alert logic: `quantity < min_stock AND quantity < reorder_point` fires a "critical stock" alert
- Separate UI indicator in LowStockAlertsCard distinguishing "history-based" vs "static threshold" alerts
- Migration to add `safety_min_qty` or similar field to `inventory_stock` or a warehouse-level default

**Acceptance:** Products with no demand history still generate alerts when stock is critically low.

#### Follow-on B: Recommended Order Quantity

**Problem:** ROP tells you WHEN to reorder but not HOW MUCH. A follow-on story should compute suggested order quantities.

**What to build (options, pick one):**
- **Simple:** `order_qty = ROP - current_qty` (replenish to ROP)
- **Economic Order Quantity (EOQ):** `order_qty = sqrt(2 × D × S / H)` where D=annual demand, S=order cost, H=holding cost
- **Period-order-quantity:** Fixed-period review (e.g., order every 2 weeks, quantity = sum of forecasted demand for 2 weeks + safety stock)
- **MOQ/order multiple handling:** Round up to supplier's minimum order quantity and nearest pack/multiple size

**New fields:**
- `suggested_order_qty` on a preview response (not persisted)
- Optional `economic_order_qty` on `inventory_stock` if using EOQ model

**UI:** Add "Suggested Order" column to preview table; show `order_qty` in reorder alert detail.

#### Follow-on C: Extended / Full-Demand Lookback

**Problem:** 90-day lookback is arbitrary. Products with seasonal demand (e.g., sells heavily in 2 months per year) need longer history to compute reliable averages.

**What to build:**
- Configurable lookback up to 365 days (already wired in `lookback_days` parameter)
- Or: use all available history (no window limit)
- Or: weighted average that recenters toward recent months (exponential smoothing)
- Consider: demand seasonality detection (if only 3 months of data, don't claim 90-day reliability)

**Known gap:** Currently if data is 12 months old, 90-day lookback finds nothing. Extended lookback helps if demand records exist in older periods.

#### Follow-on D: Alert Severity / Prioritization

**Problem:** All alerts are equal weight. A warehouse staff member with 100 pending alerts can't prioritize.

**What to build:**
- Severity tiers: `critical` (stock=0), `warning` (stock < safety_stock), `info` (stock < ROP but > safety_stock)
- Sort alerts by severity then by `days_until_stockout = current_qty / avg_daily_usage` descending
- Dashboard LowStockAlertsCard should show severity badges and sort by priority

#### Follow-on E: Per-Product Inventory Trend Charts

**Problem:** ROP numbers are abstract without seeing the actual stock trajectory. A chart showing stock level over time — with ROP threshold and demand events overlaid — makes replenishment decisions intuitive and auditable.

**What to build:**

**1. Backend: Stock history endpoint**
- `GET /api/v1/inventory/stock-history/{stock_id}` — returns time-series data
  - Query params: `from` (date), `to` (date), `granularity` (`daily` | `weekly` | `raw`)
  - Returns: `[{ date, stock_level, quantity_change, reason_code, running_total }]`
  - Reconstructs stock level by cumulative-summing `quantity_change` from oldest to newest
- `GET /api/v1/inventory/stock-history/product/{product_id}` — same for all warehouses of a product
- Query: `stock_adjustment` filtered by `product_id`, `warehouse_id`, date range
- Compute `stock_level_at_date = SUM(quantity_change) ORDER BY created_at` running total

**2. Frontend: StockTrendChart component**
- **Chart type:** Line chart (recharts `LineChart` or equivalent)
- **X-axis:** Date/time
- **Y-axis:** Stock quantity
- **Data line:** `stock_level` over time (cumulative from adjustments)
- **Reference line:** ROP threshold (from `inventory_stock.reorder_point`)
- **Reference area:** Safety stock zone (below ROP but above 0, or shaded area)
- **Annotations / dots:** Markers at each demand event with tooltip showing reason_code
- **Time range selector:** 30d / 90d / 180d / 1yr / all time (default: 90d)
- **Warehouse toggle:** If product in multiple warehouses, tab or overlay per warehouse
- **Placement:**
  - Product detail page (full-width chart below product info)
  - Inventory list → click product → modal with chart
  - LowStockAlertsCard → click alert → modal with chart + ROP context

**3. Overlay reference lines**
- ROP line: `y = reorder_point` constant horizontal line (red dashed)
- Safety stock line: `y = safety_stock` constant (orange dashed) if computed
- Lead time stockout line: `y = avg_daily_usage × lead_time_days` (yellow dashed) — shows days-of-stock remaining

**4. Event markers (enrich adjustment data)**
- `sales_reservation` → small red dot on the line
- `supplier_delivery` → green dot (shows replenishment arrivals)
- `transfer_in / transfer_out` → blue dot
- `correction` → gray dot

Tooltip on each dot: date, quantity change, reason, running stock level after this event

**5. Projected stockout line (optional)**
- Extrapolate current `avg_daily_usage` forward in time
- Show where the stock level line would cross zero (`days_until_stockout`)
- Dashed continuation of the line past today into the future
- Formula: `projected_stockout_date = today + (current_stock / avg_daily_usage)`

**6. Empty / sparse data state**
- If fewer than 2 data points: show message "Not enough history to display trend"
- If stock level is flat (no adjustments): show flat line at current quantity with message "No movements in selected period"

**7. Export**
- CSV download button: export chart data as `product_code, date, stock_level, quantity_change, reason`
- Useful for reporting and further analysis in Excel

**New backend fields / endpoints:**
- `GET /api/v1/inventory/stock-history/{stock_id}` — new endpoint
- `GET /api/v1/inventory/stock-history/product/{product_id}` — new endpoint
- Response model: `StockHistoryPoint(date, stock_level, quantity_change, reason_code, notes)`
- Response model: `StockHistoryResponse(points: list[StockHistoryPoint], current_stock, reorder_point, avg_daily_usage, lead_time_days, safety_stock)`

**New frontend files:**
- `src/domain/inventory/components/StockTrendChart.tsx`
- `src/domain/inventory/hooks/useStockHistory.ts`
- `src/pages/ProductDetailPage.tsx` — embed chart
- `src/domain/inventory/components/StockHistoryModal.tsx` — modal for alert/product context

**Performance considerations:**
- Aggregate to daily granularity for ranges > 90d (too many raw points)
- Index on `(product_id, warehouse_id, created_at)` for efficient time-range queries
- Consider caching recent history in Redis for frequently-viewed products

---

## Tasks

- [ ] Task 1: Emit clean sales demand history from order confirmation
  - [ ] Subtask 1.1: Write failing test `test_confirm_order_emits_stock_changed_event`
  - [ ] Subtask 1.2: Ensure confirmed sales lines create `sales_reservation` stock history
  - [ ] Subtask 1.3: Emit `StockChangedEvent` for each affected stock row

- [ ] Task 2: Optimize historical query path for product and warehouse lookbacks
  - [ ] Subtask 2.1: Add migration for stock-adjustment history index
  - [ ] Subtask 2.2: Verify preview queries use the indexable shape

- [ ] Task 3: Build source-aware reorder point preview service
  - [ ] Subtask 3.1: Write failing unit tests for demand filtering and lead-time resolution
  - [ ] Subtask 3.2: Implement `get_average_daily_usage()` with whitelisted reasons
  - [ ] Subtask 3.3: Implement `resolve_replenishment_source()` and ambiguous-source skip behavior
  - [ ] Subtask 3.4: Implement `compute_reorder_point_preview_row()` and preview list generation

- [ ] Task 4: Add preview and apply API contracts
  - [ ] Subtask 4.1: Add preview and apply request and response schemas
  - [ ] Subtask 4.2: Add `POST /compute` endpoint returning candidate and skipped rows
  - [ ] Subtask 4.3: Add `PUT /apply` endpoint accepting selected preview rows only
  - [ ] Subtask 4.4: Write endpoint tests for selected-row apply and skipped-row handling

- [ ] Task 5: Build admin UI for explainable preview and explicit apply
  - [ ] Subtask 5.1: Create `useReorderPointAdmin` hook
  - [ ] Subtask 5.2: Create `ReorderPointAdmin` component with filters, explanation columns, and selection controls
  - [ ] Subtask 5.3: Add "Compute ROP" entry point to reorder alerts UI
  - [ ] Subtask 5.4: Validate browser flow for preview and selected apply

- [ ] Task 6: Add integration and regression coverage
  - [ ] Subtask 6.1: Write end-to-end backend test for confirm order -> preview -> apply
  - [ ] Subtask 6.2: Add regression coverage for `insufficient_history` and `source_unresolved`
  - [ ] Subtask 6.3: Ensure unselected rows are not changed by apply

---

## Dev Notes

- Use `common.tenant.DEFAULT_TENANT_ID` as in the rest of the inventory domain
- Safety factor default remains `0.5`
- Usage lookback default remains `90` days
- Lead-time lookback default remains `180` days
- Initial demand allowlist is `ReasonCode.SALES_RESERVATION` only
- Initial eligibility guard is active product inventory rows within the selected scope
- If no clear replenishment source can be resolved, return a skipped preview row instead of guessing
- If demand history is insufficient, skip the row instead of fabricating a baseline reorder point
- Lead-time fallback applies only after usable demand exists
- Existing reorder alerts still compare `current_quantity` to `reorder_point`; projected availability is intentionally deferred
- Apply must update only explicitly selected preview rows

## Time Provider (Dev Note)

`common/time.py` provides `today()` and `utc_now()` which auto-detect the effective "today" for business logic.

**How it works:**
- `CURRENT_DATE` env var (optional) — explicit override, e.g. `CURRENT_DATE=2025-06-09`
- Falls back to auto-detection from `MAX(created_at)` across `stock_adjustment` and `raw_legacy.tbsslipdto` (the latest demand date)
- Auto-detection runs once at startup, cached for 24 hours
- If no demand data found, falls back to real `date.today()`

**For running with historical data:**
- Data ends 2025-06-09 in the legacy system
- Backend must be started with `CURRENT_DATE=2025-06-09` to correctly simulate that date
- Or: ensure `stock_adjustment` table contains recent demand records (real orders in production)

**For production:**
- No `CURRENT_DATE` needed — system uses `date.today()` automatically
- Each confirmed sales order creates `sales_reservation` records which become the demand history for ROP computation

**Backfill script** (`backend/scripts/backfill_sales_reservations.py`):
- One-time seed of `stock_adjustment` from `raw_legacy.tbsslipdto` for development
- Usage: `CURRENT_DATE=2025-06-09 python -m scripts.backfill_sales_reservations --lookback 180 --live`
- Required before Preview will return candidates when running against legacy-imported data
