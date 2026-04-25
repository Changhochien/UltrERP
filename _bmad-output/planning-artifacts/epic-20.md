# Epic 20: Product Sales Analytics

## Epic Goal

Provide a shared historical product-sales analytics foundation that answers: how much of each product sold, in what quantity, in which month — across all historical years of data — with enough context to support revenue diagnosis, product performance analysis, and stronger inventory/customer intelligence without duplicating logic across domains.

## Business Value

- Revenue diagnosis without surprises: break down revenue changes into price effect vs. volume effect vs. product-mix effect
- Inventory planning grounded in actual sales history: no more guessing based on gut feel
- Product managers and sales staff get a consistent, accurate view of product performance across 5–15 years of data
- AI agents can reason about product trends and make recommendations with full historical context
- All analytics remain accurate even after product categories are renamed or reorganized

## Scope

**Backend:**
- New shared product-sales analytics foundation, likely under `domains/product_analytics/`, designed for reuse by `inventory` and `intelligence`
- One primary new aggregate table for v1: `sales_monthly` at a single product-snapshot month grain
- `OrderLine` gains frozen `product_name_snapshot` / `product_category_snapshot` fields for historical correctness
- Legacy import emits product snapshots at import time (not post-hoc)
- Refresh path for `sales_monthly` starts as admin/CLI/on-demand; a scheduled refresh is optional only after scheduler infrastructure exists
- Initial direct analytics APIs focus on revenue diagnosis and product performance; inventory planning extends the existing `inventory` domain and customer buying behavior extends the existing `intelligence` domain
- All historical analytics use `OrderLine.product_name_snapshot` and `OrderLine.product_category_snapshot` (not live `Product.category`) as the base truth

**Frontend:**
- A backend-only `domains/product_analytics/` foundation may feed analytics, but v1 UI ships through the existing `src/domain/intelligence/` and `src/domain/inventory/` surfaces
- Initial UI scope focuses on revenue diagnosis and product performance inside `IntelligencePage`, with shared aggregate data reused by existing inventory screens where appropriate
- Do not add a new top-level `product_analytics` frontend route or `AppFeature` in v1
- Embedded into existing Intelligence / Inventory surfaces where that reduces duplication

**Data Model:**
- `sales_monthly`: single-grain periodic snapshot fact table at `tenant × month × product snapshot`
- `product_snapshots`: optional deferred SCD Type 2 product dimension that activates only if Story 20.3 explicitly needs a conformed dimension beyond sale-time snapshots
- `customer_monthly`: optional later aggregate if segment-level customer behavior analysis needs precomputation after `sales_monthly` stabilizes; not a v1 dependency

**Technical Approach:**
- Snapshots written at order-confirmation time (not order-creation), matching the existing intelligence domain's `confirmed_or_later_orders` intent
- Legacy import backfills `product_name_snapshot` / `product_category_snapshot` on `OrderLine` using the normalized product data at import time
- Monthly aggregations use SQLAlchemy async and refresh via admin/CLI/on-demand execution for v1
- Query layer falls back to live transactional data for the current month and uses the aggregate for prior periods
- Financial values use `Decimal`
- Quantities should remain compatible with the existing `OrderLine.quantity` precision until the repo explicitly standardizes integral-only quantities
- No month partitioning in v1; start with indexes and observed query plans

**Key Constraints:**
- `Product.category` on the live Product table is NOT used for historical analytics — always use the snapshot column
- Aggregation tables do NOT replace live transaction queries; they coexist (aggregate for historical, live for recent/current period)
- Monthly aggregations include only confirmed/shipped/fulfilled orders, and the canonical analytics timestamp is `confirmed_at` first with `created_at` only as the explicit fallback when confirmation data is absent; month boundaries must use that rule consistently
- `sales_monthly` must keep a single grain; do not mix category-only rollups and product rows in the same fact table
- Inventory planning must extend the existing replenishment logic rather than create a parallel planning engine
- Customer behavior analysis should extend Epic 19 intelligence flows rather than create a duplicate customer analytics silo

**Dependency / Phase Order:** start with `20.1` to make historical product context immutable, then `20.3` to build the shared monthly fact. `20.4` and `20.6` can follow on top of that foundation. `20.5` should be implemented as an extension of `inventory`, and `20.7` as an extension of `intelligence`. `20.2` is optional for v1 unless the monthly fact is explicitly modeled against a conformed SCD dimension.

---

## Story 20.1: Product Snapshot on OrderLine

**Context:** Without a frozen product name and category at time of sale, historical analytics become inaccurate whenever a product is renamed or recategorized. The legacy import is the best place to stamp these snapshots because the normalized product data exists at import time.

**R1 — Add snapshot columns to `OrderLine`**
- File: `backend/common/models/order_line.py`
- Add `product_name_snapshot: Mapped[str] = mapped_column(String(500), nullable=True)`
- Add `product_category_snapshot: Mapped[str] = mapped_column(String(200), nullable=True)`
- Both nullable — existing order lines without snapshots may remain null until backfilled, but closed-period analytics must not fall back to the live `Product` table at query time

**R2 — Migration**
- File: `migrations/versions/<new_revision>.py`
- `op.add_column("order_lines", sa.Column("product_name_snapshot", sa.String(500), nullable=True))`
- `op.add_column("order_lines", sa.Column("product_category_snapshot", sa.String(200), nullable=True))`

**R3 — Snapshot written at order confirmation**
- File: `backend/domains/orders/services.py` (or wherever order confirmation mutates state)
- On order status transition to `confirmed`, backfill `product_name_snapshot` and `product_category_snapshot` from the related tenant-scoped `Product` row for each order line that does not already have them set
- Do not overwrite populated snapshot fields during later order edits or reconfirmation flows
- The current schema requires `product_id`, so this story assumes every `order_line` resolves to a product under the existing operational model
- If unresolved historical rows still use the legacy `UNKNOWN` product fallback, preserve imported line description/category context where available and treat any remaining missing snapshots as unsupported historical gaps rather than relying on the live `Product` table at query time

**R4 — Legacy import emits snapshots**
- File: `backend/domains/legacy_import/canonical.py`
- In `_import_sales_history`, ensure the `order_lines` upsert path includes `product_name_snapshot` and `product_category_snapshot` copied from normalized product or imported line fallback data at import time
- This stamps historical order lines with the category as it existed at import time (not the live Product table)

**Acceptance Criteria:**

**Given** an existing order line with `product_id` set but no snapshots
**When** the order is confirmed (status → confirmed)
**Then** `product_name_snapshot` and `product_category_snapshot` are filled from the current `Product` row

**Given** a legacy order line being imported via `canonical-import`
**When** the normalized product row is available
**Then** `product_name_snapshot` receives `normalized_product.name` and `product_category_snapshot` receives `normalized_product.category`
**And** no join to the live `Product` table is needed at query time

**Given** a query for "revenue by category in 2020"
**When** the query uses `OrderLine.product_category_snapshot`
**Then** the 2020 result reflects the category as it was, not any subsequent rename

**Given** a closed-period analytics query encounters a historical order line with missing snapshots
**When** the query is executed
**Then** the row is surfaced as a data gap or excluded per the endpoint contract
**And** the query does not reconstruct historical category/name values from the live `Product` table

---

## Story 20.2: Optional Product Dimension SCD Type 2

**Context:** This story stays deferred by default for v1. A proper product dimension table with slowly changing dimension (SCD) Type 2 support is only activated if Story 20.3 explicitly needs an independent conformed product dimension in addition to sale-time snapshots on `order_lines`.

**R1 — New `product_snapshots` table**
- File: `backend/domains/product_analytics/models.py`
- Table: `product_snapshots`
  - `id: UUID` (PK)
  - `tenant_id: UUID` (indexed)
  - `product_id: UUID` (FK → Product.id)
  - `name: String(500)` — product name at this point in time
  - `category: String(200)` — product category at this point in time
  - `effective_from: date` — when this snapshot became valid
  - `effective_to: date` — when this snapshot expired (NULL = current)
  - `created_at: datetime`
- Index: `ix_product_snapshots_tenant_product` on `(tenant_id, product_id, effective_from)`
- If Story 20.3 explicitly activates this story, the monthly fact may reference it as the conformed historical product dimension; otherwise keep this work deferred

**R2 — SCD Type 2 write on product update**
- File: `backend/domains/product_analytics/service.py`
- `upsert_product_snapshot(tenant_id, product_id)` — called from product create/update flow
- On product CREATE: insert row with `effective_from = today`, `effective_to = NULL`
- On product UPDATE (name or category changes): update old row's `effective_to = yesterday`, insert new row with `effective_from = today`, `effective_to = NULL`
- Uses a single transaction with `SELECT FOR UPDATE` to prevent race conditions

**R3 — Hook product lifecycle events**
- File: hook into the actual service that owns product mutation once that write path is explicit in the repo
- After product create: call `upsert_product_snapshot`
- After product update: call `upsert_product_snapshot` if name or category changed
- If neither changed: no snapshot write needed

**R4 — Snapshot read utility**
- File: `backend/domains/product_analytics/service.py`
- `get_product_snapshot_at(tenant_id, product_id, as_of_date)` — returns the product row as it existed on a given date using SCD Type 2 logic
- Used internally by aggregation refresh jobs only if the monthly fact is modeled against the SCD dimension rather than directly from frozen order-line snapshots

**Acceptance Criteria:**

**Given** a product with `name = "Widget A"`, `category = "Electronics"` created on 2023-01-15
**When** the product is updated to `category = "Hardware"` on 2023-06-01
**Then** `product_snapshots` contains two rows: one with `effective_from=2023-01-15`, `effective_to=2023-05-31`, `category="Electronics"` and one with `effective_from=2023-06-01`, `effective_to=NULL`, `category="Hardware"`

**Given** a query for "what was this product's category on 2023-04-01?"
**When** `get_product_snapshot_at(tenant, product_id, date(2023, 4, 1))` is called
**Then** it returns the row with `category = "Electronics"`

---

## Story 20.3: Monthly Aggregation Tables

**Context:** Scanning 133K+ raw order lines for multi-year historical queries is slow and will only get slower. Pre-computed monthly rollups give O(1) query performance regardless of history depth.

**R1 — `sales_monthly` table**
- File: `backend/domains/product_analytics/models.py`
- Table: `sales_monthly`
  - `id: UUID` (PK)
  - `tenant_id: UUID`
  - `month_start: date` (first day of the month)
  - `product_id: UUID`
  - `product_snapshot_id: UUID | NULL` — present if Story 20.2 is implemented in v1
  - `product_name_snapshot: String(500)`
  - `product_category_snapshot: String(200)`
  - `quantity_sold: Numeric(18, 3)` — keep compatible with `OrderLine.quantity` until the repo standardizes integral-only quantities
  - `order_count: Integer`
  - `revenue: Numeric(14, 2)`
  - `avg_unit_price: Numeric(14, 4)` — derived: revenue / quantity_sold
  - `created_at: datetime`, `updated_at: datetime`
- Grain: exactly one row per `tenant × month × product snapshot`
- Unique constraint: `(tenant_id, month_start, product_id, product_name_snapshot, product_category_snapshot)`
- Composite index: `(tenant_id, month_start, product_category_snapshot)` for category-level queries
- Do not store category-only rollups in this same fact table

**R2 — `customer_monthly` stays deferred**
- Do not build `customer_monthly` in v1.
- If segment-level customer behavior later proves too expensive to compute on demand, add `customer_monthly` only after `sales_monthly` stabilizes and after Story 20.7 demonstrates a real need for precomputation.

**R3 — Aggregation refresh job**
- File: `backend/domains/product_analytics/service.py`
- `refresh_sales_monthly(tenant_id, month_start)` — computes and upserts `sales_monthly` from countable orders for a given month using the canonical analytics timestamp
- Uses `INSERT ... ON CONFLICT ... DO UPDATE` for idempotent upserts
- For v1: refresh is triggered manually, via admin action, or from a dedicated CLI task; add a scheduler only after scheduler infrastructure exists in the app
- Initial historical population remains a full backfill concern, while routine freshness may use a rolling recent closed-month refresh window through the reviewed legacy-refresh CLI surfaces
- Current month always computed live from transactional tables
- A future `refresh_customer_monthly()` belongs to later scope and must not block `sales_monthly` shipment

**R4 — Current-month live fallback**
- File: `backend/domains/product_analytics/service.py`
- All query functions check: if querying current month, compute from live transactional tables instead of `sales_monthly`
- For prior months: always read from `sales_monthly`
- If a closed month has transactional sales but missing snapshot rows, shared reads may temporarily fall back to transactional aggregation rather than zero-filling, while refresh upkeep remains the steady-state fix

**Acceptance Criteria:**

**Given** confirmed order lines for tenant T in April 2026 with 3 products
**When** `refresh_sales_monthly(tenant=T, month_start=date(2026, 4, 1))` runs
**Then** `sales_monthly` has 3 rows (one per product snapshot) with `month_start=2026-04-01`, `quantity_sold`, `order_count`, `revenue`, `avg_unit_price` correctly computed
**And** re-running is idempotent (same result, no duplicates)

**Given** a query for "quantity sold by category for the last 24 months"
**When** the query runs
**Then** it reads from `sales_monthly` for all months except the current month
**And** current month data is computed live from `OrderLine`

---

## Story 20.4: Revenue Diagnosis API

**Context:** "Why did revenue change this month?" requires decomposing the change into: price effect (same volume, different price), volume effect (same price, different quantity), and mix effect (different products selling at different rates).

**Backend deliverables:**
- `backend/domains/intelligence/schemas.py`: revenue-diagnosis response models
- `backend/domains/intelligence/service.py`: `get_revenue_diagnosis()` that reads `sales_monthly` for closed months and live transactional data for the current month
- `backend/domains/intelligence/routes.py`: `GET /api/v1/intelligence/revenue-diagnosis`
- `backend/domains/intelligence/mcp.py`: `intelligence_revenue_diagnosis`
- `backend/common/config.py`: `intelligence_revenue_diagnosis_enabled`
- `backend/app/mcp_auth.py`: `TOOL_SCOPES["intelligence_revenue_diagnosis"] = frozenset({"orders:read"})`

**Frontend deliverables:**
- Extend the existing intelligence types, API client, and hooks
- Mount the UI inside `src/pages/IntelligencePage.tsx` as another evidence-first section
- Do not add a new top-level route or `product_analytics` frontend feature in v1

**Acceptance Criteria:**

**Given** an authenticated intelligence request
**When** `GET /api/v1/intelligence/revenue-diagnosis` is called with a comparison window and optional category filter
**Then** the response includes summary totals, comparison metadata, and ranked driver rows
**And** `price_effect + volume_effect + mix_effect = revenue_delta` after the defined Decimal rounding step
**And** closed historical months read from `sales_monthly`, while any open current-month slice is computed live and marked partial
**And** historical grouping/filtering uses `OrderLine.product_name_snapshot` and `OrderLine.product_category_snapshot` rather than live product fields
**And** driver ordering is deterministic: `abs(revenue_delta)` descending, then `abs(mix_effect)` descending, then `product_name` ascending, then `product_id` ascending
**And** disabled REST/MCP calls reuse the existing intelligence `_require_feature_enabled()` helpers

---

## Story 20.5: Inventory Planning Support from Shared Sales History

**Context:** "Which products should I reorder and when?" requires understanding sales velocity, seasonality, and stockout risk. UltrERP already has reorder-point and replenishment logic in the `inventory` domain, so this story should improve that existing planning flow with better shared sales history rather than build a separate planning engine.

**Backend deliverables:**
- Reuse shared monthly product sales history as an input to `domains/inventory/`
- Extend existing inventory planning/reorder-point services with an inventory-owned planning-support response that adds seasonality and velocity context where useful
- If a new endpoint is needed, prefer `GET /api/v1/inventory/products/{product_id}/planning-support` in `domains/inventory/` or a thin composition layer rather than duplicating replenishment logic inside `product_analytics`
- Any MCP exposure must register concrete tool scopes using existing atoms only; do not invent a generic planning-support scope shape in the plan

**Frontend deliverables:**
- Extend existing inventory planning screens or add a shared history/explainer panel
- Surface velocity, seasonality, lead-time context, and reorder rationale in the existing replenishment workflow
- Optional: seasonal chart showing monthly quantity pattern per product

**Acceptance Criteria:**

1. Given Epic 20 shared sales history is available, when `GET /api/v1/inventory/products/{product_id}/planning-support` is called, then the response returns a month-ordered sales series plus `avg_monthly_quantity`, `peak_monthly_quantity`, `low_monthly_quantity`, `seasonality_index`, `above_average_months`, `history_months_used`, `current_month_live_quantity`, current inventory context, and provenance fields such as `data_basis` and `advisory_only`.
2. Given the inventory product-detail analytics tab is open, when planning support loads, then the user sees shared sales history and seasonality inside the existing inventory UI rather than on a new standalone page.
3. Given reorder-point preview is run for a product that also has planning-support data, when the preview rows are returned, then the existing reorder-point formula remains authoritative and any shared-history context is clearly marked advisory unless a warehouse-allocation rule is explicitly defined.
4. Given only closed months are queried, when planning support loads, then the monthly series is sourced from the Epic 20 aggregate.
5. Given the current month is included, when planning support loads, then the current-month slice is computed live from confirmed, shipped, or fulfilled orders and the payload marks the window as partial.
6. Given no shared sales history exists, when planning support is requested, then the endpoint returns an empty history plus a data-gap flag rather than guessing a demand pattern.
7. Given a closed month has sales activity but its `sales_monthly` rows are temporarily missing, when planning support loads, then the shared read path falls back to transactional aggregation for that closed month instead of returning a misleading zero-filled series.

---

## Story 20.6: Product Performance API

**Context:** "Which products are our top performers, which are declining, and which are new?" — a product portfolio health view that spans the full history.

**Backend deliverables:**
- `backend/domains/intelligence/schemas.py`: product-performance models, lifecycle-stage enums, and machine-readable `stage_reasons`
- `backend/domains/intelligence/service.py`: `get_product_performance()` consuming Story 20.3 history
- `backend/domains/intelligence/routes.py`: `GET /api/v1/intelligence/product-performance`
- `backend/domains/intelligence/mcp.py`: `intelligence_product_performance`
- `backend/common/config.py`: `intelligence_product_performance_enabled`
- `backend/app/mcp_auth.py`: `TOOL_SCOPES["intelligence_product_performance"] = frozenset({"orders:read"})`

**Frontend deliverables:**
- Extend the existing intelligence types, API client, and hooks
- Mount product performance inside `src/pages/IntelligencePage.tsx`
- Link drill-through into the existing inventory product-detail surface rather than a new analytics route

**Acceptance Criteria:**

**Given** an authenticated intelligence request
**When** `GET /api/v1/intelligence/product-performance` is called with optional `category`, `lifecycle_stage`, `limit`, and `include_current_month`
**Then** the response returns a ranked product list plus comparison-window metadata using Story 20 snapshot semantics
**And** the default ranking compares the last 12 complete months to the prior 12 complete months and excludes the open month from the default server sort
**And** if `include_current_month = true`, the current-month slice is computed live from confirmed, shipped, or fulfilled orders while closed months still come from Story 20.3 and `window_is_partial = true`
**And** lifecycle classification is deterministic and uses the exact validated precedence order `new`, `end_of_life`, `declining`, `growing`, `mature`, `stable`
**And** the exact validated thresholds are: `new` when current-window revenue is greater than zero, prior-window revenue is zero, and `first_sale_month` falls inside the current window; `end_of_life` when current-window revenue is zero, prior-window revenue is greater than zero, and `last_sale_month` is at least 6 complete months before the comparison anchor month; `declining` when prior-window revenue is greater than zero and either current-window revenue is zero without meeting `end_of_life` or current-window revenue is less than `0.80 * prior_window_revenue`; `growing` when prior-window revenue is greater than zero and current-window revenue is at least `1.20 * prior_window_revenue`; `mature` when current-window revenue is greater than zero, prior-window revenue is greater than zero, `months_on_sale >= 24`, and current-window revenue stays within the inclusive band `0.80 * prior_window_revenue` to `1.20 * prior_window_revenue`; and `stable` for any remaining product with current-window revenue greater than zero
**And** each returned product row includes machine-readable `stage_reasons`
**And** result ordering is deterministic: current-period revenue descending, then revenue-delta percent descending, then product name ascending, then product id ascending
**And** aggregation stays keyed by `product_id`, while the returned display label comes from the most recent included sale snapshot, preferring current-window months over prior-window months and then the latest analytics timestamp inside that month

---

## Story 20.7: Customer Buying Behavior Extension

**Context:** "What do our customers typically buy, and how does that vary by segment?" — builds on the existing `CustomerProductProfile` from Epic 19 and should extend the existing intelligence layer rather than create a parallel customer analytics silo.

**Backend deliverables:**
- Extend `backend/domains/intelligence/` with segment-level customer buying behavior powered by shared aggregate history where useful
- `get_customer_buying_behavior()` may consume `sales_monthly` for closed months, but must remain functional via on-demand transactional fallback until `customer_monthly` proves necessary
- Route and MCP placement stay in the intelligence domain; do not expose this story through a separate public `product_analytics` route
- `backend/app/mcp_auth.py`: `TOOL_SCOPES["intelligence_customer_buying_behavior"] = frozenset({"customers:read", "orders:read"})`

**Frontend deliverables:**
- Extend `src/pages/IntelligencePage.tsx` with segment profiles, category affinity, and cross-sell opportunity cards, with any later customer-detail reuse handled by composition rather than a parallel public surface

**Acceptance Criteria:**

**Given** `customer_type` is `dealer`, `end_user`, `unknown`, or `all`
**When** `get_customer_buying_behavior(tenant=T, customer_type=...)` is called
**Then** the response returns segment summary metrics, top categories, cross-sell opportunities, and month-ordered buying patterns using Story 20 snapshot and timestamp semantics
**And** `top_categories` sort by revenue descending, then customer count descending, then category ascending
**And** cross-sell evidence uses the validated contract: `segment_penetration = shared_customer_count / anchor_customer_count`, `outside_segment_penetration = outside_segment_shared_customer_count / outside_segment_anchor_customer_count`, `lift_score = segment_penetration / outside_segment_penetration` rounded to 4 decimals only when the outside-segment penetration is positive
**And** a cross-sell row ships only when `anchor_customer_count >= 5` and `shared_customer_count >= 3`
**And** when `outside_segment_anchor_customer_count = 0`, `outside_segment_penetration = 0`, or `customer_type = all`, the outside-segment baseline is treated as unavailable, `lift_score = null`, and those rows sort after numeric lift scores by shared customer count descending, then anchor/recommended category ascending

---

## Story 20.8: Product Analytics Feature Gate

**Context:** Consistency with Epic 19's access control pattern.

**Backend deliverables:**
- `backend/app/mcp_auth.py`: add TOOL_SCOPES entries for the new shared analytics tools in whichever domains actually own them
- `backend/common/config.py`: add feature toggles that follow the final ownership split
- Apply feature flag checks only to the concrete owner-domain routes/tools that ship in v1 (`inventory` and `intelligence`); keep the backend-only `product_analytics` foundation private

**Frontend deliverables:**
- Keep visibility inside the existing `usePermissions().canAccess("intelligence")` and `usePermissions().canAccess("inventory")` gates
- Do not add a new `product_analytics` `AppFeature` or protected route in v1

**Acceptance Criteria:**

**Given** an Epic 20 intelligence capability is disabled
**When** its REST route or MCP tool is called
**Then** the route reuses the existing intelligence `_require_feature_enabled()` 403 pattern and the MCP tool returns `FEATURE_DISABLED`
**And** the relevant section is hidden or suppressed inside `IntelligencePage`

**Given** the inventory planning-support capability is disabled
**When** the inventory-owned endpoint is called
**Then** the inventory route returns a feature-disabled response and the inventory UI hides that section without affecting other inventory surfaces

**Given** an MCP caller lacks the required scope for an Epic 20 tool
**When** the tool is called
**Then** `MCPAuthProvider.authorize()` fails with `INSUFFICIENT_SCOPE` using only the existing scope atoms already in the repo: `orders:read`, `customers:read`, and `inventory:read`

---

## Story 20.9: Product Analytics Backend Test Coverage

**Backend deliverables:**
- `backend/tests/domains/product_analytics/__init__.py`
- `backend/tests/domains/product_analytics/test_service.py`: tests for the shared aggregate foundation and refresh logic
- Extend existing `inventory` / `intelligence` tests where those domains consume the new aggregate history or own public routes/tools
- Add focused `backend/tests/test_mcp_auth.py` assertions for the new Epic 20 tool scopes
- If Story 20.2 remains deferred, do not spend this story on unshipped SCD2 behavior

**Acceptance Criteria:**

1. Given confirmed, shipped, fulfilled, draft, and cancelled orders in the same tenant and month, when the monthly refresh service runs, then only countable commercial orders are aggregated, exactly one historical row exists per tenant-month-product-snapshot grain, and rerunning the refresh is idempotent.
2. Given two tenants with overlapping product names and categories, and a live product record renamed after sale, when the monthly fact is refreshed and queried, then only the caller tenant's data is included and historical assertions are based on immutable sale-time snapshots.
3. Given stale current-month aggregate rows exist, when a shared analytics query requests a window that includes the current month, then the current month is derived from live transactional data while prior months continue to use the historical aggregate.
4. Given two consecutive historical periods with known quantity and price changes, when the revenue-diagnosis service runs, then price effect, volume effect, and mix effect sum exactly to the total revenue delta and the breakdown sort is deterministic.
5. Given products at the boundary between new, growing, stable, declining, mature, and end-of-life behavior, when the product-performance service runs, then lifecycle classification follows the contract exactly and the result ordering is deterministic.
6. Given shared monthly sales history is wired into inventory planning support, when the inventory planning endpoint runs, then sales velocity and seasonality come from the shared history while reorder recommendations still respect current stock, inbound supply, and existing inventory policy inputs.
7. Given shared historical sales inputs are wired into customer buying behavior, when the intelligence extension runs, then segment filtering, top-category ordering, cross-sell evidence, and snapshot semantics remain correct without regressing existing intelligence contracts.
8. Given an Epic 20 owner-domain route is enabled for an authorized role, when the route is called, then the response shape matches the schema contract; and given the corresponding feature setting is false, when the route is called, then a 403 response with a stable disabled-feature detail message is returned.
9. Given an Epic 20 MCP tool is enabled and receives valid tenant context, when the tool is called, then it returns a stable machine-facing payload; and given the tool is disabled, missing tenant context, or missing required scope, when the tool is called, then it raises structured errors consistent with current MCP conventions.
10. Given new Epic 20 tools are registered in the auth layer, when the MCP auth test suite runs, then exact `TOOL_SCOPES` entries and insufficient-scope behavior are asserted in the centralized auth tests.
**And** cross-sell lift, minimum-support thresholds, and null-baseline handling match the validated Epic 20 contract

---

## Story 20.10: Sales Monthly Freshness Health Check and Backfill Automation

**Context:** `sales_monthly` is now a shared foundation for revenue diagnosis, product performance, customer behavior, and inventory planning support. The repo now has a transactional fallback for closed months with missing snapshot rows and a rolling recent-month upkeep path, but operators still lack a proactive way to detect gaps and a stronger repair flow for historical backfill or targeted missing-month recovery.

**Backend deliverables:**
- Add a tenant-scoped closed-month `sales_monthly` health check that identifies months with countable transactional sales but missing snapshot coverage.
- Extend the reviewed refresh/backfill surfaces with explicit missing-month repair and historical backfill modes rather than relying on manual ad hoc refresh windows.
- Surface machine-readable freshness results through existing admin or operator seams, such as the reviewed CLI, summary artifacts, or admin refresh control plane.
- Keep the existing transactional fallback for downstream reads, but treat it as a degraded-state resilience guard rather than the primary steady-state path.

**Frontend deliverables:**
- If UI exposure is needed, reuse the existing admin or operations surface for health visibility and repair controls.
- Do not add a new end-user `product_analytics` page or duplicate planning-support UI just for freshness management.

**Acceptance Criteria:**

1. Given a tenant has a closed month with countable commercial sales but no `sales_monthly` rows, when the health check runs, then the result marks the month as missing and includes enough evidence for remediation such as tenant, month, and transactional support counts.
2. Given a tenant has no missing closed-month snapshot coverage in the requested window, when the health check runs, then the result reports a healthy state with zero missing months.
3. Given one or more missing months are detected, when the operator runs a missing-month repair mode, then only those closed months are refreshed and rerunning the repair remains idempotent.
4. Given a tenant needs initial historical seeding or large-gap recovery, when the operator runs a historical backfill mode, then the system refreshes the requested closed-month range up to the last closed month and never aggregates the current open month.
5. Given rolling upkeep or a reviewed refresh run completes while missing closed months still remain, when the operator inspects the resulting summary or control-plane status, then the degraded freshness state is visible with remediation guidance instead of appearing silently healthy.
6. Given downstream shared reads still need to serve analytics while closed-month snapshot gaps exist, when a query runs, then the existing transactional fallback remains available but the health output continues to mark the tenant as degraded until the missing months are repaired.
