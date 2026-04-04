# Story 7.2: Top Selling Products

Status: done

## Story

As an owner,
I want to view top selling products by day/week on the dashboard,
So that I can identify trends and make sourcing decisions.

## Acceptance Criteria

**AC1:** Top 3 products by day
**Given** orders exist with `status IN ('confirmed', 'shipped', 'fulfilled')` for today
**When** the dashboard loads
**Then** I see the top 3 products ranked by total quantity sold today
**And** each product shows: product name, quantity sold, revenue (TWD)

**AC2:** Toggle to weekly view
**Given** I'm viewing the top products section
**When** I toggle between "Today" and "This Week"
**Then** the data refreshes to show top 3 by the selected period
**And** "This Week" = last 7 days from today (inclusive)

**AC3:** Revenue per product
**Given** a product appears in the top 3
**When** I view its entry
**Then** revenue = `SUM(order_lines.total_amount)` for that product in the selected period
**And** quantity = `SUM(order_lines.quantity)` for that product in the selected period

**AC4:** No-data graceful handling
**Given** no orders exist for the selected period
**When** I view the top products section
**Then** I see an empty state message: "No sales data for this period"

**AC5:** Backend API endpoint
**Given** the backend is running
**When** I call `GET /api/v1/dashboard/top-products?period=day` or `period=week`
**Then** the response returns JSON with a list of up to 3 products
**And** each item has: `product_id`, `product_name`, `quantity_sold`, `revenue`
**And** results are sorted by `quantity_sold` descending
**And** the response is tenant-scoped

**AC6:** Correct order status filter
**Given** orders exist with various statuses
**When** the top products query runs
**Then** only orders with status `confirmed`, `shipped`, or `fulfilled` are included
**And** `pending` and `cancelled` orders are excluded

## Tasks / Subtasks

- [ ] **Task 1: Top Products Schema** (AC5)
  - [ ] Add to `backend/domains/dashboard/schemas.py`:
    ```python
    class TopProductItem(BaseModel):
        product_id: uuid.UUID
        product_name: str
        quantity_sold: Decimal
        revenue: Decimal

    class TopProductsResponse(BaseModel):
        period: str  # "day" or "week"
        start_date: date
        end_date: date
        items: list[TopProductItem]
    ```

- [ ] **Task 2: Top Products Service** (AC1, AC3, AC5, AC6)
  - [ ] Implement `get_top_products(session, tenant_id, period: str = "day") -> TopProductsResponse`:
    - Call `await set_tenant(session, tenant_id)` first
    - Determine date range:
      - `period="day"`: `start_date = end_date = date.today()`
      - `period="week"`: `start_date = date.today() - timedelta(days=6)`, `end_date = date.today()`
    - Query:
      ```sql
      SELECT p.id, p.name,
             SUM(ol.quantity) AS quantity_sold,
             SUM(ol.total_amount) AS revenue
      FROM order_lines ol
      JOIN orders o ON ol.order_id = o.id
      JOIN product p ON ol.product_id = p.id
      WHERE o.tenant_id = :tid
        AND o.status IN ('confirmed', 'shipped', 'fulfilled')
        AND o.created_at::date BETWEEN :start AND :end
      GROUP BY p.id, p.name
      ORDER BY quantity_sold DESC
      LIMIT 3
      ```
    - Return `TopProductsResponse`

- [ ] **Task 3: Top Products Route** (AC5)
  - [ ] `GET /top-products` with query param `period: str = "day"` (validate: `day` or `week`)
  - [ ] Returns `TopProductsResponse`
  - [ ] Add to existing dashboard router

- [ ] **Task 4: Frontend — Top Products Widget** (AC1, AC2, AC4)
  - [ ] Create `src/domain/dashboard/components/TopProductsCard.tsx`:
    - Table/list showing product name, quantity, revenue
    - Toggle buttons: "Today" | "This Week"
    - Empty state for no data
    - Loading skeleton state
  - [ ] Add to `src/lib/api/dashboard.ts`:
    - `fetchTopProducts(period: 'day' | 'week'): Promise<TopProductsResponse>`
  - [ ] Add to `src/domain/dashboard/types.ts`:
    ```typescript
    export interface TopProductItem {
      product_id: string;
      product_name: string;
      quantity_sold: string;
      revenue: string;
    }
    export interface TopProductsResponse {
      period: string;
      start_date: string;
      end_date: string;
      items: TopProductItem[];
    }
    ```
  - [ ] Add to `src/domain/dashboard/hooks/useDashboard.ts`:
    - `useTopProducts(period)` — refetches when period changes

- [ ] **Task 5: Integrate into Dashboard Page** (AC1)
  - [ ] Add `TopProductsCard` to `DashboardPage.tsx` grid
  - [ ] Position below or beside the revenue card

- [ ] **Task 6: Backend Tests** (AC1, AC3, AC4, AC6)
  - [ ] Create `backend/tests/domains/dashboard/test_top_products.py`
  - [ ] Test: top 3 products returned sorted by quantity
  - [ ] Test: excluded statuses (pending, cancelled) are not counted
  - [ ] Test: uses `fulfilled` (NOT `delivered`) as valid status
  - [ ] Test: period="week" aggregates 7 days
  - [ ] Test: no orders → empty items list
  - [ ] Test: products with same quantity maintain stable sort

- [ ] **Task 7: Frontend Tests** (AC1, AC2, AC4)
  - [ ] Create `src/domain/dashboard/__tests__/TopProductsCard.test.tsx`
  - [ ] Test: renders product list
  - [ ] Test: toggle changes period param
  - [ ] Test: empty state renders message

## Dev Notes

### Architecture Compliance

- **Domain structure:** Extends `backend/domains/dashboard/` created in Story 7.1
- **Query joins:** Requires joining `order_lines` → `orders` → `product`. All models exist in `common/models/`
- **No new models or migrations:** Pure aggregation query over existing tables

### Query Design

- **Date filter:** Uses `orders.created_at::date` (cast TIMESTAMPTZ to DATE) for the period filter. Alternative: filter by `created_at >= start_of_day AND created_at < start_of_next_day` for index friendliness — preferred if performance matters. **NOTE:** The `::date` cast prevents index usage on `ix_orders_tenant_created`. Use range-based filtering (`created_at >= :start AND created_at < :end_exclusive`) for the production query to leverage the existing index.
- **"This Week" label:** "This Week" is actually a rolling 7-day window (today minus 6 days), not a calendar week (Monday–Sunday). Consider labeling it "Last 7 Days" to avoid confusion, or keep as-is and document.
- **GROUP BY:** `GROUP BY p.id, p.name` — `p.name` is functionally dependent on `p.id` (PK), so the extra column is redundant for PostgreSQL. SQLAlchemy may require it explicitly for portability. Acceptable as-is.
- **Status filter:** Only count fulfilled orders: `confirmed`, `shipped`, `fulfilled`. Verified against `OrderStatus` enum in `domains/orders/schemas.py`.
- **Product model:** `Product` lives in `common/models/product.py`, has `id` (UUID) and `name` (String). Table name is `product` (singular).
- **OrderLine model:** `OrderLine` lives in `common/models/order_line.py`, has `product_id`, `quantity` (Numeric(18,3)), `total_amount` (Numeric(20,2)).

### Critical Warnings

- **Order date field:** Use `orders.created_at` (TIMESTAMPTZ) not `order_date` — there is no `order_date` field on the Order model. Cast to date for day-level comparison.
- **Product table name:** The table is `product` (singular), NOT `products`. Check the model's `__tablename__` before writing raw SQL or SQLAlchemy queries.
- **Quantity type:** `order_lines.quantity` is `Numeric(18,3)` — it supports fractional quantities (e.g., 2.5 kg). Display with appropriate precision.
- **SUM result type:** SQLAlchemy returns `Decimal` from `func.sum()` over `Numeric` columns. Do not convert to `float`.
- **Dependency on Story 7.1:** This story extends the dashboard domain and page scaffold created in 7.1. Story 7.1 must be completed first.

### Previous Story Intelligence

- **FakeAsyncSession for joins:** When testing queries with JOINs, queue a single `execute()` result containing all joined rows. The fake session returns the entire result set as queued.
- **OrderStatus enum:** Defined in `domains/orders/schemas.py`. Verified values: `pending`, `confirmed`, `shipped`, `fulfilled`, `cancelled`. NOTE: It's `fulfilled`, NOT `delivered`.
- **Product model import:** `from common.models.product import Product`
- **OrderLine model import:** `from common.models.order_line import OrderLine`

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic 7, Story 7.2] AC definitions: top 3 by day/week
- [Source: _bmad-output/planning-artifacts/epics.md#FR26] Owner can view top selling products by day/week
- [Source: _bmad-output/planning-artifacts/prd.md#Journey 1] Morning Pulse Check — top 3 selling products
- [Source: common/models/product.py] Product model with id, name
- [Source: common/models/order_line.py] OrderLine with product_id, quantity, total_amount
- [Source: common/models/order.py] Order with status, created_at, tenant_id
- [Source: domains/orders/schemas.py] OrderStatus enum with allowed transitions

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (via GitHub Copilot)

### Completion Notes List

- Story created after analyzing Order, OrderLine, and Product model schemas
- Date filter uses orders.created_at (TIMESTAMPTZ) cast to date — no order_date field exists
- Product table name is singular ("product") — verified from model's __tablename__
- Quantity is Numeric(18,3) supporting fractional units — display precision noted
