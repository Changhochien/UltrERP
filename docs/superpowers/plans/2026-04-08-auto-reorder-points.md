# Story 4.7: Auto-Calculate Reorder Points

**Epic:** Epic 4 — Inventory Operations
**FR coverage:** Extends FR8, FR9
**Story points:** 5
**Priority:** High

---

## Story

As a warehouse staff,
I want the system to automatically calculate reorder points based on my sales history and supplier lead times,
So that alerts fire for products that actually need monitoring without me manually guessing thresholds.

---

## Context

The reorder alert system (Story 4.3) exists and is correct, but all products have `reorder_point = 0` — so no alerts ever fire.

To calculate ROP automatically, the formula is:

**ROP = Safety Stock + (Lead Time × Average Daily Usage)**

- **Safety Stock** = `avg_daily_usage × safety_factor × lead_time_days`
- **Average Daily Usage** = total outbound stock movements ÷ lookback days
- **Lead Time** = actual average from supplier orders, or `supplier.default_lead_time_days`, or 7-day fallback

---

## Acceptance Criteria

### AC1: Sales create stock adjustment history

**Given** a confirmed sales order exists with line items
**When** the order is confirmed
**Then** `StockAdjustment` records are created for each line with reason `sales_reservation`
**And** `StockChangedEvent` is emitted so reorder alerts can fire

### AC2: Reorder points are computed from historical data

**Given** I have 90 days of stock adjustment history and supplier orders
**When** I trigger reorder point computation
**Then** the system calculates average daily outbound usage per product/warehouse
**And** the system calculates average lead time per supplier (from received orders)
**And** ROP = safety_stock + (lead_time × avg_daily_usage) is computed

### AC3: Dry-run preview before saving

**Given** I am on the reorder point admin UI
**When** I set safety factor and lookback days, then click "Preview"
**Then** I see a table of all products with: product name, warehouse, computed reorder point, avg daily usage, lead time, safety stock
**And** no values are saved yet

### AC4: Apply saves all computed reorder points

**Given** I have reviewed the dry-run preview
**When** I click "Apply"
**Then** all `inventory_stock.reorder_point` values are updated to the computed values
**And** alerts immediately begin firing for products now below their new threshold

### AC5: Fallback when no history

**Given** a product has no stock adjustment history (new product)
**When** reorder points are computed
**Then** it is excluded from the computation with a note "insufficient history"
**And** products with a `supplier.default_lead_time_days` get a default ROP of `default_lead_time_days × 7` (one week avg usage at 1/day)

---

## Non-Functional Requirements

- Query performance: stock adjustment history query must use a composite index on `(product_id, created_at)`
- No new database tables — reuse existing `stock_adjustment`, `supplier_order`, `inventory_stock`
- Computation is triggered via API (not a background job/scheduler)

---

## Technical Notes

- `confirm_order` in `backend/domains/orders/service.py` needs to emit `StockChangedEvent` for each line
- New composite index needed: `ix_stock_adjustment_product_created ON stock_adjustment (product_id, created_at DESC)`
- A new `backend/domains/inventory/reorder_point.py` service handles the formula computation
- Lead time from history: average of `(received_date - order_date)` for `SupplierOrderStatus.RECEIVED` orders
- Safety factor configurable: default 0.5 (50% buffer), range 0.0–1.0

---

## Out of Scope

- Automatic periodic recomputation (no scheduler)
- Per-product manual override of computed ROP (manual entry already works)
- Multi-tenant: use hardcoded `TENANT_ID` like rest of inventory domain
