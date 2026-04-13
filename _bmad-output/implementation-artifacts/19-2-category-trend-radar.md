# Story 19.2: Category Trend Radar

Status: revised-ready-for-dev

## Story

As an **AI agent or sales staff**,
I want to see which product categories are growing or declining
So that I know where to focus sales effort and which categories to pitch.

## Problem Statement

Sales staff and AI agents currently have no systematic way to answer "which categories are hot right now?" Answers live in individual customer conversations and anecdotal impressions rather than data. A period-over-period category revenue comparison surfaces: categories to double down on (growing), categories needing attention (declining), and stable categories — enabling proactive account management and targeted prospecting.

## Solution

A new `get_category_trends()` service function computes revenue and order deltas by `Product.category` across two equal time windows (current period vs. prior period). Results are classified as `growing` (>10% revenue delta), `declining` (<-10% revenue delta), or `stable`. New and churned customer counts per category reveal acquisition and retention dynamics.

**Period definitions:**
- `last_30d`: current window = today minus 30 days; prior window = day 31–60 ago
- `last_90d`: current window = today minus 90 days; prior window = day 91–180 ago
- `last_12m`: current window = today minus 365 days; prior window = day 366–730 ago

**Derived fields:**
- `revenue_delta_pct = (current_period_revenue - prior_period_revenue) / prior_period_revenue * 100`
- `trend = "growing"` when `revenue_delta_pct > 10`
- `trend = "declining"` when `revenue_delta_pct < -10`
- `trend = "stable"` otherwise
- `new_customer_count` = customers who made their first-ever purchase in this category during the current period
- `churned_customer_count` = customers who purchased in this category in the prior period but have no orders in the current period
- `top_products` = top 5 products by revenue in the current period

The frontend renders a `BarChart` with two bars per category (current period = colored, prior period = gray), plus period selector tabs.

## Best-Practice Update

This section supersedes conflicting details below.

- `Product.category` is a nullable string in the live repo. Do not assume a normalized `categories` table or `category_id` exists.
- Category trending is a demand signal in v1. Use confirmed / shipped / fulfilled order-line value and expose an `activity_basis` or equivalent metadata field so consumers do not confuse it with accounting revenue.
- Null and explicitly excluded non-merchandise categories must be filtered before ranking.
- Zero-baseline cases must not be converted into fake `100%` growth. Emit `newly_active` or `insufficient_history` style context, or keep the delta nullable while still returning support counts.
- Trend labels should only be applied when support floors are met. Include `customer_count`, `prior_customer_count`, and the period window in every record.
- For the human UI, a ranked category list with chart support is preferred over a chart-only radar presentation.

## Acceptance Criteria

**AC1: MCP tool returns complete category trend data**
**Given** orders spanning the current and prior period for a tenant
**When** the AI agent calls `intelligence_category_trends(period="last_90d")`
**Then** each category in the response includes: `category`, `current_period_revenue`, `prior_period_revenue`, `revenue_delta_pct`, `current_period_orders`, `prior_period_orders`, `order_delta_pct`, `customer_count`, `prior_customer_count`, `new_customer_count`, `churned_customer_count`, `top_products` (top 5 by revenue), `trend`
**And** `trend = "growing"` when `revenue_delta_pct > 10`, `trend = "declining"` when `revenue_delta_pct < -10`, else `trend = "stable"`
**And** zero-baseline cases return support metadata or nullable deltas rather than fabricated `100%` growth
**And** `new_customer_count` = customers with first orders in this category during the current period
**And** `churned_customer_count` = customers who ordered in prior period but not current period

**AC2: REST endpoint serves the same data**
**Given** a sales staff user calling `GET /api/v1/intelligence/category-trends?period=last_90d`
**When** the request is authenticated and tenant is set
**Then** the response body matches the MCP tool response schema

**AC3: Empty categories are handled**
**Given** a category with no orders in the current period but orders in the prior period
**Then** `current_period_revenue = 0`, `revenue_delta_pct = -100`, `trend = "declining"`, `churned_customer_count` is populated

**AC4: Tenant isolation is enforced**
**Given** tenant A has orders in category "LED Displays" and tenant B has different data
**When** an agent queries trends for tenant A
**Then** tenant B's orders are not included

**AC5: Frontend chart renders correctly**
**Given** the category trends tab is loaded with period=last_90d
**When** data arrives
**Then** a recharts `BarChart` renders two bars per category (current=green/red/gray by trend, prior=gray)
**And** period selector tabs (30d / 90d / 12m) are visible and functional
**And** categories are sorted by `revenue_delta_pct` descending

## Technical Notes

### File Locations (add to these from Story 19.1)

- `backend/domains/intelligence/schemas.py` — add `CategoryTrend`, `CategoryTrends` Pydantic models
- `backend/domains/intelligence/service.py` — add `get_category_trends()` async function
- `backend/domains/intelligence/routes.py` — add `GET /api/v1/intelligence/category-trends` route
- `backend/domains/intelligence/mcp.py` — add `intelligence_category_trends` tool
- `backend/app/mcp_auth.py` — add `TOOL_SCOPES` entry: `"intelligence_category_trends": frozenset({"orders:read", "customers:read"})`
- `src/domain/intelligence/types.ts` — add `CategoryTrend`, `CategoryTrends` TypeScript interfaces
- `src/domain/intelligence/hooks/useIntelligence.ts` — add `useCategoryTrends(period)` hook
- `src/domain/intelligence/components/CategoryTrendRadar.tsx` — bar chart component

### Key Implementation Details

**Backend — period date windows:**

```python
from datetime import UTC, date, timedelta

def _period_windows(period: Literal["last_30d", "last_90d", "last_12m"]) -> tuple[date, date, date, date]:
    today = date.today()
    if period == "last_30d":
        current_start = today - timedelta(days=30)
        prior_end = current_start - timedelta(days=1)
        prior_start = prior_end - timedelta(days=29)
    elif period == "last_90d":
        current_start = today - timedelta(days=90)
        prior_end = current_start - timedelta(days=1)
        prior_start = prior_end - timedelta(days=89)
    else:  # last_12m
        current_start = today - timedelta(days=365)
        prior_end = current_start - timedelta(days=1)
        prior_start = prior_end - timedelta(days=364)
    return current_start, today, prior_start, prior_end
```

**Backend — service function query structure:**

```python
async def get_category_trends(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    period: Literal["last_30d", "last_90d", "last_12m"] = "last_90d",
) -> CategoryTrends:
    """Compute period-over-period category trends.

    CTEs:
      1. current_orders: orders in current window (join orders → order_lines → products)
      2. prior_orders: orders in prior window
      3. category_revenue_current: SUM(amount) GROUP BY category
      4. category_revenue_prior: SUM(amount) GROUP BY category
      5. customer_first_purchase: first observed `Order.created_at` per customer/category using `func.min(Order.created_at)` in a grouped or windowed subquery
      6. prior_category_customers: SET of customer_ids who bought in category in prior window
      7. current_category_customers: SET of customer_ids who bought in category in current window

    new_customer_count = customers in current_category_customers
                         whose first_purchase_date in this category >= current_start
    churned_customer_count = customers in prior_category_customers
                             who are NOT in current_category_customers
    """
```

**Revenue and order delta computation:**

```python
# Join current and prior revenue CTEs on category
for row in combined_results:
    prior_rev = row.prior_revenue or Decimal("0")
    curr_rev = row.current_revenue or Decimal("0")
    if prior_rev > 0:
      revenue_delta_pct = (curr_rev - prior_rev) / prior_rev * 100
      trend_context = None
    else:
      revenue_delta_pct = None
      trend_context = "newly_active" if curr_rev > 0 else "insufficient_history"

    prior_orders = row.prior_order_count or 0
    curr_orders = row.current_order_count or 0
    if prior_orders > 0:
      order_delta_pct = (curr_orders - prior_orders) / prior_orders * 100
    else:
      order_delta_pct = None

    # trend classification
    if revenue_delta_pct is not None and revenue_delta_pct > 10:
        trend = "growing"
    elif revenue_delta_pct is not None and revenue_delta_pct < -10:
        trend = "declining"
    else:
        trend = "stable"
```

**Top products query (current period only):**

```python
top_products_stmt = (
    select(
        Product.id,
        Product.name,
        func.sum(OrderLine.quantity * OrderLine.unit_price).label("revenue"),
    )
    .join(OrderLine, OrderLine.product_id == Product.id)
    .join(Order, Order.id == OrderLine.order_id)
    .where(
        Order.tenant_id == tenant_id,
        Order.status.in_(["confirmed", "shipped", "fulfilled"]),
        Order.created_at >= current_start,
        Product.category == category,  # outer scalar subquery or join
    )
    .group_by(Product.id, Product.name)
    .order_by(func.sum(OrderLine.quantity * OrderLine.unit_price).desc())
    .limit(5)
)
```

**New customer count query:**

```python
# A new customer in category C in the current period is one whose
# MIN(Order.created_at) OVER (PARTITION BY customer_id, category) >= current_start
# This is a window-function CTE, not a simple GROUP BY.
first_purchase_stmt = (
    select(
        Order.customer_id,
        Product.category,
        func.min(Order.created_at).over(
            partition_by=[Order.customer_id, Product.category],
            order_by=Order.created_at,
        ).label("first_purchase_date"),
    )
    .join(OrderLine, OrderLine.order_id == Order.id)
    .join(Product, Product.id == OrderLine.product_id)
    .where(Order.tenant_id == tenant_id)
    .distinct()
    .cte("first_purchases")
)

# Count distinct customers in current window whose first purchase >= current_start
new_customers_stmt = (
    select(func.count(func.distinct(first_purchase_stmt.c.customer_id)))
    .where(
        first_purchase_stmt.c.category == category,
        first_purchase_stmt.c.first_purchase_date >= current_start,
    )
)
```

**Frontend — TypeScript interfaces:**

```typescript
export interface TopProductByRevenue {
  product_id: string;
  product_name: string;
  revenue: string;
}

export interface CategoryTrend {
  category: string;
  current_period_revenue: string;  // Decimal as string for JSON safety
  prior_period_revenue: string;
  revenue_delta_pct: number | null;
  current_period_orders: number;
  prior_period_orders: number;
  order_delta_pct: number | null;
  customer_count: number;
  prior_customer_count: number;
  new_customer_count: number;
  churned_customer_count: number;
  top_products: TopProductByRevenue[];
  trend: "growing" | "declining" | "stable";
  trend_context?: "newly_active" | "insufficient_history" | null;
  activity_basis: "confirmed_orders";
}

export interface CategoryTrends {
  period: "last_30d" | "last_90d" | "last_12m";
  trends: CategoryTrend[];
  generated_at: string;  // ISO datetime
}
```

**Frontend — hook:**

```typescript
export function useCategoryTrends(period: "last_30d" | "last_90d" | "last_12m" = "last_90d") {
  const [data, setData] = useState<CategoryTrends | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    fetch(`/api/v1/intelligence/category-trends?period=${period}`)
      .then(r => r.json())
      .then(d => { setData(d); setLoading(false); })
      .catch(e => { setError(e.message); setLoading(false); });
  }, [period]);

  return { data, loading, error };
}
```

**CategoryTrendRadar.tsx chart spec:**

```tsx
// Two bars per category: current (colored) and prior (gray)
// Sort categories by revenue_delta_pct desc
// Color by trend: growing = green (#22c55e), declining = red (#ef4444), stable = gray (#9ca3af)
// Prior period bar always gray (#d1d5db)

const BAR_COLORS = {
  growing: "#22c55e",
  declining: "#ef4444",
  stable: "#6b7280",
};

<BarChart data={sortedTrends} layout="vertical">
  <XAxis type="number" />
  <YAxis dataKey="category" type="category" width={120} />
  <Tooltip formatter={(v) => `NT$ ${Number(v).toLocaleString()}`} />
  <Bar dataKey="prior_period_revenue" fill="#d1d5db" name="Prior Period" />
  <Bar dataKey="current_period_revenue" fill={/* trend color */} name="Current Period" />
</BarChart>
```

Period selector tabs: `<button>30d</button> <button>90d</button> <button>12m</button>` — active tab styled with primary color, switching re-fetches.

### Critical Warnings

- **Do NOT** use calendar month boundaries for period windows — use rolling days from `date.today()` as specified above.
- **Do NOT** include cancelled or pending orders — filter to `status IN ('confirmed', 'shipped', 'fulfilled')`.
- **Do NOT** count a customer as "new" if they bought in the category prior to the current period, even if they bought a different product in the current period. New = first purchase ever in that category.
- **Do NOT** count a customer as "churned" if they bought a different category in the current period. Churned = no orders in this category in current period (regardless of other activity).
- Handle division-by-zero in delta calculations by returning `null` delta values plus a `trend_context` such as `newly_active` or `insufficient_history`.
- For MCP tools: each tool creates its own `AsyncSessionLocal()` session. Do NOT accept a session parameter.
- For REST routes: use `tenant_id` from `get_current_user`, not `DEFAULT_TENANT_ID`.
- `top_products` must be a list of up to 5 products sorted by revenue descending.
- Use `Decimal` in Python and `string` in JSON transport for monetary values (avoid float precision issues).

## Tasks / Subtasks

- [ ] Task 1: Add schemas for category trends (AC1)
  - [ ] Add `TopProductByRevenue`, `CategoryTrend`, `CategoryTrends` to `backend/domains/intelligence/schemas.py`

- [ ] Task 2: Implement `get_category_trends()` service (AC1, AC3, AC4)
  - [ ] Implement `_period_windows()` helper
  - [ ] Implement current-period and prior-period revenue CTEs
  - [ ] Implement new_customer_count using first observed `Order.created_at` per customer/category
  - [ ] Implement churned_customer_count as set difference
  - [ ] Implement top_products subquery (limit 5)
  - [ ] Compute revenue_delta_pct, order_delta_pct, trend classification
  - [ ] Return `CategoryTrends` sorted by revenue_delta_pct desc

- [ ] Task 3: Add REST route (AC2)
  - [ ] Add `GET /api/v1/intelligence/category-trends` in `routes.py`
  - [ ] Query param: `period` with values `last_30d | last_90d | last_12m`

- [ ] Task 4: Add MCP tool (AC1)
  - [ ] Add `intelligence_category_trends` tool in `mcp.py`
  - [ ] Add TOOL_SCOPES: `"intelligence_category_trends": frozenset({"orders:read", "customers:read"})` in `mcp_auth.py`

- [ ] Task 5: Frontend types and hook (AC2)
  - [ ] Add `TopProductByRevenue`, `CategoryTrend`, `CategoryTrends` to `types.ts`
  - [ ] Add `useCategoryTrends(period)` to `hooks/useIntelligence.ts`

- [ ] Task 6: CategoryTrendRadar component (AC5)
  - [ ] Create `CategoryTrendRadar.tsx` with recharts `BarChart`
  - [ ] Two bars per category (current colored by trend, prior gray)
  - [ ] Period selector tabs (30d / 90d / 12m)
  - [ ] Sort by `revenue_delta_pct` descending
  - [ ] Loading and error states

## Dev Notes

### Repo Reality

- Service functions use `async def fn(session, tenant_id, *, ...)` + `async with session.begin(): await set_tenant(session, tid)`
- MCP tools: `@mcp.tool(annotations={"readOnlyHint": True})` + `raise ToolError(json.dumps({...}))` + `AsyncSessionLocal()` session management
- Pydantic schemas: `BaseModel` with `ConfigDict(from_attributes=True)` for responses
- TOOL_SCOPES: `dict[str, frozenset[str]]` in `backend/app/mcp_auth.py`
- Existing tables: `orders`, `order_lines`, `products` (has `category` column), `customers`
- Product category is `Product.category` (a `str | None` column, not a foreign key to a categories table)

### References

- `backend/domains/inventory/mcp.py` — MCP tool pattern (copy-paste template)
- `backend/domains/dashboard/routes.py` — REST route pattern with `get_current_user` + tenant_id extraction
- `backend/domains/dashboard/services.py` — period-window aggregation examples
- `backend/domains/customers/service.py:7` — `from datetime import date, datetime, timedelta`
- `backend/app/mcp_auth.py:24` — `TOOL_SCOPES` dict structure
- `backend/app/mcp_server.py:24` — domain MCP registration pattern
- `src/domain/dashboard/components/GrossMarginCard.tsx` — recharts BarChart usage
- `src/domain/inventory/components/MonthlyDemandChart.tsx` — recharts usage with custom colors
- Epic 19 spec: `epic-19.md` lines 62–91
- INTEL-002 from epics.md coverage map

### SQLAlchemy Window Function Note

SQLAlchemy's `func.min(...).over(...)` syntax for window functions requires the column to be a SQL function, not an arbitrary expression. For first purchase by category, use:

```python
from sqlalchemy import func, over
from sqlalchemy.sql import ColumnElement

first_order_date = over(
    func.min(Order.created_at),
    partition_by=[Order.customer_id, Product.category],
    order_by=Order.created_at,
)
```

Then select it as `first_order_date.label("first_order_date")`.

## Story Dependencies

- Prerequisite: Story 19.7 for access wiring and route scaffolding
- Depends on: no additional intelligence story; this is a shared category foundation that can proceed alongside Story 19.3 once scaffolding exists
- Enables: Story 19.5 and Story 19.6 once category support floors and cleaning rules are stable
