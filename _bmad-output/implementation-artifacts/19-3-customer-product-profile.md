# Story 19.3: Customer Product Profile

Status: done

## Story

As an **AI agent** preparing for a customer call,
I want to know what this customer buys, how often, and what they've recently started or stopped buying
So that I can have an informed conversation and pitch relevant products.

## Problem Statement

AI agents preparing for customer calls need a synthesized view of each customer's purchasing behavior — not raw order history. Sales staff similarly need a quick account health snapshot. Without a dedicated per-customer intelligence layer, agents must manually aggregate multiple API calls and derive metrics like frequency trends and AOV changes. A unified `CustomerProductProfile` consolidates this in one call.

## Solution

A new `domains/intelligence/` backend module that aggregates `orders` + `order_lines` + `products` data per customer into a rich product-profile response. On the frontend, a two-column `CustomerProductProfile` component renders top categories as a horizontal bar chart (left) and a top-products ranked table (right), with a metrics summary row above and dormancy/new-category indicators.

## Best-Practice Update

This section supersedes conflicting details below.

- This story should extend the existing customer detail analytics experience instead of creating a disconnected parallel customer intelligence surface.
- All value and activity metrics in v1 are derived from confirmed / shipped / fulfilled orders. Expose `activity_basis` so the payload is explicit about that choice.
- The `prior_3m` comparison means the immediately preceding 3-month window, not months 10–12 ago.
- Add `days_since_last_order`, `order_count_prior_3m`, and a lightweight `confidence` field so agents can distinguish strong signals from sparse history.
- `is_dormant` and trend labels should remain descriptive and transparent; they should not hide the raw counts and dates that justified the classification.
- The MCP scope for this story must include the order activity it reads; `customers:read` alone is too weak.

## Acceptance Criteria

**AC1: Full profile response**

Given a customer with orders spanning multiple categories and products over 12 months
When the AI agent calls `GET /api/v1/intelligence/customers/{customer_id}/product-profile`
Then the response includes:
- `customer_id`: UUID of the customer
- `company_name`: string
- `total_revenue_12m`: sum of `order.total_amount` for all orders in the trailing 12 months
- `order_count_12m`: count of orders in trailing 12 months
- `order_count_3m`: count of orders in trailing 3 months
- `order_count_6m`: count of orders in trailing 6 months
- `order_count_prior_12m`: count of orders in the 12 months before the trailing 12 months (i.e., months 13–24 ago)
- `frequency_trend`: string — `"increasing"` when `order_count_3m > order_count_prior_3m * 1.20`, `"declining"` when `order_count_3m < order_count_prior_3m * 0.80`, else `"stable"`; where `order_count_prior_3m` = orders in the immediately preceding 3-month window
- `avg_order_value`: `total_revenue_12m / order_count_12m`
- `avg_order_value_prior`: revenue in months 13–24 ago / `order_count_prior_12m` (0 if no prior orders)
- `aov_trend`: string — `"increasing"` when `avg_order_value > avg_order_value_prior * 1.10`, `"declining"` when `avg_order_value < avg_order_value_prior * 0.90`, else `"stable"`
- `top_categories`: array of `CategoryRevenue`, sorted by `revenue` descending, max 10
- `top_products`: array of `ProductPurchase`, sorted by `order_count` descending, max 20
- `last_order_date`: ISO date string of the most recent `order.created_at`
- `is_dormant`: true when no orders exist in the last 60 days
- `new_categories`: array of category names that had their first ever order for this customer in the last 90 days

**AC2: Dormant badge**

Given a customer with no orders in the last 60 days
When the frontend renders the CustomerProductProfile
Then a red "Dormant" badge is displayed alongside the last order date

**AC3: New category chip**

Given a customer with categories that had first orders in the last 90 days
When the frontend renders the top categories section
Then each new category shows a green "New" chip beside its name

**AC4: MCP tool parity**

Given a valid MCP API key with `customers:read` and `orders:read` scopes
When the AI agent calls `intelligence_customer_product_profile(customer_id=<uuid>)`
Then the response matches the REST API schema exactly
And the tool is registered in `TOOL_SCOPES` as `intelligence_customer_product_profile → customers:read`, `orders:read`

## Technical Notes

### File Locations (create these)

- `backend/domains/intelligence/__init__.py`
- `backend/domains/intelligence/schemas.py` — add `CategoryRevenue`, `ProductPurchase`, `CustomerProductProfile` Pydantic models
- `backend/domains/intelligence/service.py` — add `get_customer_product_profile()`
- `backend/domains/intelligence/routes.py` — add `GET /api/v1/intelligence/customers/{customer_id}/product-profile`
- `backend/domains/intelligence/mcp.py` — add `intelligence_customer_product_profile` tool
- `src/domain/intelligence/__init__.py`
- `src/domain/intelligence/types.ts` — add `CategoryRevenue`, `ProductPurchase`, `CustomerProductProfile` TypeScript interfaces
- `src/domain/intelligence/hooks/useIntelligence.ts` — add `useCustomerProductProfile(customerId)` hook
- `src/domain/intelligence/components/CustomerProductProfile.tsx` — two-column layout component
- `src/lib/api/intelligence.ts` — add `fetchCustomerProductProfile(customerId)` API helper

### Key Implementation Details

**Query strategy for `get_customer_product_profile`:**

Use a single tenant-scoped query joining `orders → order_lines → product`. All date windows are computed relative to `today` (UTC date). Use three explicit date anchors:

```
today = date.today()
window_12m_start  = today - relativedelta(months=12)
window_6m_start   = today - relativedelta(months=6)
window_3m_start   = today - relativedelta(months=3)
window_prior_12m_start = today - relativedelta(months=24)
window_prior_6m_start  = today - relativedelta(months=12)
window_prior_3m_start  = today - relativedelta(months=6)
```

For `total_revenue_12m`: `sum(order.total_amount)` WHERE `order.created_at >= window_12m_start`
For `order_count_3m`: `count(*)` WHERE `order.created_at >= window_3m_start`
For `order_count_prior_3m`: `count(*)` WHERE `order.created_at >= window_prior_3m_start AND order.created_at < window_3m_start`
For `days_since_last_order`: difference between `date.today()` and `last_order_date` when present

**Category aggregation subquery:**
```python
category_q = (
    select(
        Product.category,
        func.sum(OrderLine.total_amount).label("revenue"),
        func.count(func.distinct(Order.id)).label("order_count"),
    )
    .join(Product, OrderLine.product_id == Product.id)
    .join(Order, OrderLine.order_id == Order.id)
    .where(Order.customer_id == customer_id)
    .where(Order.created_at >= window_12m_start)
    .where(Product.category.isnot(None))
    .group_by(Product.category)
    .order_by(func.sum(OrderLine.total_amount).desc())
    .limit(10)
)
```

**Product aggregation subquery:**
```python
product_q = (
    select(
        Product.id,
        Product.name,
        Product.category,
        func.count(func.distinct(Order.id)).label("order_count"),
        func.sum(OrderLine.quantity).label("total_quantity"),
        func.sum(OrderLine.total_amount).label("total_revenue"),
    )
    .join(OrderLine, OrderLine.product_id == Product.id)
    .join(Order, OrderLine.order_id == Order.id)
    .where(Order.customer_id == customer_id)
    .where(Order.created_at >= window_12m_start)
    .group_by(Product.id, Product.name, Product.category)
    .order_by(func.count(func.distinct(Order.id)).desc())
    .limit(20)
)
```

**`new_categories` detection:**
Identify categories where the `min(order.created_at)` for that customer+category falls within the last 90 days. Use a subquery or CTE:

```python
first_order_per_category = (
    select(
        Product.category,
        func.min(Order.created_at).label("first_order_at"),
    )
    .join(OrderLine, OrderLine.product_id == Product.id)
    .join(Order, OrderLine.order_id == Order.id)
    .where(Order.customer_id == customer_id)
    .where(Product.category.isnot(None))
    .group_by(Product.category)
    .subquery()
)
new_categories = [
    row.category for row in session.execute(
        select(first_order_per_category.c.category)
        .where(first_order_per_category.c.first_order_at >= date.today() - relativedelta(days=90))
    )
]
```

**`is_dormant` check:**
```python
last_order = session.execute(
    select(func.max(Order.created_at))
    .where(Order.customer_id == customer_id)
    .where(Order.tenant_id == tenant_id)
)
is_dormant = last_order_date < date.today() - relativedelta(days=60)
```

**MCP tool error handling:**
If the customer does not exist or has no orders, return an empty profile with zero values rather than raising a 404. The AI agent should always get a valid response.

**Pydantic schemas:**

```python
# backend/domains/intelligence/schemas.py
from pydantic import BaseModel, ConfigDict
from datetime import date
from uuid import UUID
from decimal import Decimal

class CategoryRevenue(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    category: str
    revenue: Decimal
    order_count: int
    revenue_pct_of_total: Decimal  # fraction, e.g. 0.35

class ProductPurchase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    product_id: UUID
    product_name: str
    category: str | None
    order_count: int
    total_quantity: Decimal
    total_revenue: Decimal

class CustomerProductProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    customer_id: UUID
    company_name: str
    total_revenue_12m: Decimal
    order_count_12m: int
    order_count_3m: int
    order_count_6m: int
    order_count_prior_12m: int
    order_count_prior_3m: int
    frequency_trend: Literal["increasing", "declining", "stable"]
    avg_order_value: Decimal
    avg_order_value_prior: Decimal
    aov_trend: Literal["increasing", "declining", "stable"]
    top_categories: list[CategoryRevenue]
    top_products: list[ProductPurchase]
    last_order_date: date | None
    days_since_last_order: int | None
    is_dormant: bool
    new_categories: list[str]
    confidence: Literal["high", "medium", "low"]
    activity_basis: Literal["confirmed_orders"]
```

**TypeScript interfaces:**

```typescript
// src/domain/intelligence/types.ts
export interface CategoryRevenue {
  category: string;
  revenue: string;  // Decimal as string
  order_count: number;
  revenue_pct_of_total: string;
}

export interface ProductPurchase {
  product_id: string;
  product_name: string;
  category: string | null;
  order_count: number;
  total_quantity: string;
  total_revenue: string;
}

export interface CustomerProductProfile {
  customer_id: string;
  company_name: string;
  total_revenue_12m: string;
  order_count_12m: number;
  order_count_3m: number;
  order_count_6m: number;
  order_count_prior_12m: number;
  order_count_prior_3m: number;
  frequency_trend: "increasing" | "declining" | "stable";
  avg_order_value: string;
  avg_order_value_prior: string;
  aov_trend: "increasing" | "declining" | "stable";
  top_categories: CategoryRevenue[];
  top_products: ProductPurchase[];
  last_order_date: string | null;
  days_since_last_order: number | null;
  is_dormant: boolean;
  new_categories: string[];
  confidence: "high" | "medium" | "low";
  activity_basis: "confirmed_orders";
}
```

**Frontend component layout (`CustomerProductProfile.tsx`):**

```
┌─────────────────────────────────────────────────────────────┐
│  Metrics Row: [Total Revenue 12m] [Orders 12m] [AOV] [Last]│
│  [Dormant badge if is_dormant]                             │
├──────────────────────────────┬──────────────────────────────┤
│  Top Categories (bar chart) │  Top Products (table)        │
│  HorizontalBarChart         │  Name | Cat | Count | Rev    │
│  top_categories[0..9]        │  top_products[0..19]        │
│                              │                              │
│  Green "New" chip on any    │                              │
│  category in new_categories  │                              │
└──────────────────────────────┴──────────────────────────────┘
```

Use recharts `BarChart` with `CartesianGrid`, `XAxis` (categories), `YAxis` (revenue in TWD), `Tooltip`. Table uses shadcn/ui `Table` components.

### Critical Warnings

- **Do NOT create new database tables.** All data is derived from existing `orders`, `order_lines`, `products`, and `customers` tables.
- **Do NOT** use `order_lines.subtotal_amount` for revenue — use `Order.total_amount` per order, then aggregate. Alternatively use `OrderLine.total_amount` if per-line is needed; just be consistent and document it.
- **`is_dormant` uses 60 days**, while **`new_categories` uses 90 days** — these are different windows. Do not confuse them.
- **`frequency_trend` compares 3m vs. the immediately preceding 3m**. The prior 3m window must not overlap with the current window.
- **Guard division by zero** on `avg_order_value` when `order_count_12m == 0`. Return `Decimal("0")`.
- **Customer must exist** — verify the customer UUID is valid and belongs to the tenant before running aggregations.
- **All queries must be tenant-scoped** using `Order.tenant_id == tenant_id`.
- **Use `func.count(func.distinct(Order.id))`** for order_count in category/product subqueries, not `func.count(Order.id)`, because a single order can have multiple lines for the same product/category.

## Tasks / Subtasks

- [x] Task 1: Create `backend/domains/intelligence/__init__.py` and add Pydantic schemas (AC1)
  - [x] Subtask 1.1: Create `__init__.py` with module docstring
  - [x] Subtask 1.2: Add `CategoryRevenue`, `ProductPurchase`, `CustomerProductProfile` to `schemas.py`

- [x] Task 2: Implement `get_customer_product_profile()` in `service.py` (AC1, AC4)
  - [x] Subtask 2.1: Implement date window constants with `relativedelta`
  - [x] Subtask 2.2: Query `total_revenue_12m`, `order_count_12m`, `order_count_3m`, `order_count_6m`, `order_count_prior_12m`
  - [x] Subtask 2.3: Compute `avg_order_value` and `avg_order_value_prior`, handle division by zero
  - [x] Subtask 2.4: Compute `frequency_trend` from 3m vs. prior 3m comparison
  - [x] Subtask 2.5: Compute `aov_trend` from current vs. prior AOV
  - [x] Subtask 2.6: Query `top_categories` with revenue aggregation and `revenue_pct_of_total`
  - [x] Subtask 2.7: Query `top_products` with order_count and revenue aggregation
  - [x] Subtask 2.8: Query `last_order_date` using `func.max(Order.created_at)`
  - [x] Subtask 2.9: Compute `is_dormant` from 60-day window
  - [x] Subtask 2.10: Compute `new_categories` from first-order-per-category in last 90 days

- [x] Task 3: Add REST route in `routes.py` (AC1)
  - [x] Subtask 3.1: Add `GET /api/v1/intelligence/customers/{customer_id}/product-profile`
  - [x] Subtask 3.2: Use an intelligence-specific route dependency via the existing `require_role(...)` pattern and tenant-scoped customer lookup
  - [x] Subtask 3.3: Return `CustomerProductProfile` response model

- [x] Task 4: Add MCP tool in `mcp.py` and wire `TOOL_SCOPES` (AC4)
  - [x] Subtask 4.1: Add `intelligence_customer_product_profile` tool using `AsyncSessionLocal()`
  - [x] Subtask 4.2: Add `TOOL_SCOPES` entry: `intelligence_customer_product_profile → customers:read`, `orders:read`
  - [x] Subtask 4.3: Register `domains.intelligence.mcp` in `backend/app/mcp_server.py`

- [x] Task 5: Frontend TypeScript types and API helper (AC1)
  - [x] Subtask 5.1: Add interfaces to `src/domain/intelligence/types.ts`
  - [x] Subtask 5.2: Add `fetchCustomerProductProfile(customerId)` to `src/lib/api/intelligence.ts`

- [x] Task 6: Frontend hook `useCustomerProductProfile` (AC1)
  - [x] Subtask 6.1: Add `useCustomerProductProfile(customerId)` to `useIntelligence.ts`

- [x] Task 7: Frontend component `CustomerProductProfile.tsx` (AC2, AC3)
  - [x] Subtask 7.1: Metrics row with total revenue, order count, AOV, last order date
  - [x] Subtask 7.2: Red "Dormant" badge when `is_dormant === true`
  - [x] Subtask 7.3: Left column — horizontal bar chart of `top_categories`
  - [x] Subtask 7.4: Green "New" chip on categories present in `new_categories`
  - [x] Subtask 7.5: Right column — table of `top_products` with Name, Category, Count, Revenue columns

## Completion Notes

- Implemented the customer product profile service, REST endpoint, MCP tool, TypeScript types, API helper, hook, and UI component, and embedded the panel in the existing customer analytics experience.
- Follow-up review work corrected the exposed `activity_basis` contract to `confirmed_or_later_orders`, made missing-customer MCP calls return structured `NOT_FOUND`, and aligned the MCP path with explicit tenant context.
- Validation: `uv run pytest tests/domains/intelligence/test_service.py tests/domains/intelligence/test_routes.py tests/test_mcp_intelligence.py tests/test_mcp_auth.py -q`, `pnpm --dir /Volumes/2T_SSD_App/Projects/UltrERP exec vitest run src/tests/customers/CustomerAnalyticsTab.test.tsx src/tests/customers/CustomerProductProfile.test.tsx`.

## Dev Notes

### Repo Reality

- `Product.category` is `str | None` at `backend/common/models/product.py:32`
- `Order.total_amount` is `Decimal | None` at `backend/common/models/order.py:48`
- `Order.created_at` is `datetime` at `backend/common/models/order.py:57`
- `Customer.company_name` is `str` at `backend/domains/customers/models.py:21`
- `relativedelta` from `dateutil.relativedelta` is used across the codebase for date arithmetic (verify import)
- `SectionCard` is exported from `src/components/layout/PageLayout.tsx`
- `apiFetch` pattern: `apiFetch("/api/v1/...")` returns `Promise<Response>`, caller calls `.json()`
- `appTodayISO()` from `src/lib/time` returns today's date as ISO string
- Recharts is already used in the codebase (e.g., `RevenueTrendChart.tsx`, `MonthlyDemandChart.tsx`)
- shadcn/ui `Table`, `TableHead`, `TableRow`, `TableCell` components available
- `Badge` component from shadcn/ui for status badges

### References

- `backend/common/models/order.py:29-59` — Order model fields
- `backend/common/models/order_line.py:35-57` — OrderLine model fields
- `backend/common/models/product.py:30-32` — Product model, `category` field
- `backend/domains/customers/models.py:15-21` — Customer model, `company_name` field
- `backend/domains/customers/service.py:7-11` — `relativedelta` import and date arithmetic pattern
- `backend/app/mcp_auth.py:24-45` — `TOOL_SCOPES` dict format and existing entries
- `backend/app/mcp_server.py:25` — domain MCP module registration pattern
- `src/components/layout/PageLayout.tsx:43` — `SectionCard` component signature
- `src/domain/dashboard/components/GrossMarginCard.tsx` — SectionCard usage with recharts
- `src/domain/dashboard/hooks/useDashboard.ts` — `useCallback` + `useEffect` pattern for hooks
- `src/lib/api/dashboard.ts` — API helper pattern with `apiFetch`
