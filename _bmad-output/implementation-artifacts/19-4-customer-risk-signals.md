# Story 19.4: Customer Risk Signals

Status: revised-ready-for-dev

## Story

As an **AI agent** monitoring the customer base,
I want a ranked list of accounts that need attention — dormant, at-risk, or growing —
So that I can prioritize outreach and capitalize on expansion.

## Problem Statement

Sales and AI agents need a prioritized account list that surfaces where action is most valuable. Without a systematic risk-signal scan, agents waste time on stable accounts while at-risk accounts silently churn. A ranked `CustomerRiskSignals` feed with explicit status classifications (dormant, at-risk, growing, new, stable) lets agents focus on the highest-value outreach.

## Solution

A `get_customer_risk_signals()` service that scans all customers, computes period-over-period revenue deltas, classifies each account into a status bucket, and returns structured evidence first. Human-readable `signals` remain secondary convenience text derived from the evidence. On the frontend, a `RiskSignalFeed` component renders a scrollable card list with a status filter bar and color-coded badges.

## Best-Practice Update

This section supersedes conflicting details below.

- Return structured evidence first: `revenue_current`, `revenue_prior`, `revenue_delta_pct`, `days_since_last_order`, `first_order_date`, category expansion / contraction, `reason_codes`, and `confidence`. Human-readable `signals` are secondary.
- Classification should stay deterministic, but sparse-history cases must not fabricate precision. When prior-period activity is absent or too small, expose that explicitly.
- The UI filter set should match the output set. If `stable` remains a valid status, either show it as a filter or make its omission an intentional product decision.
- This story depends on the customer snapshot logic from Story 19.3; do not duplicate core period and dormancy calculations in multiple places.
- The MCP scope must reflect order-derived intelligence. `customers:read` alone is not sufficient.

## Acceptance Criteria

**AC1: Full risk signals response**

Given all customers in the system with their order history
When the AI agent calls `GET /api/v1/intelligence/customers/risk-signals?status=all&limit=50`
Then the response includes `customers`, an array of `CustomerRiskSignal` objects, sorted: dormant first, then at_risk, then growing, then stable, then new
And each `CustomerRiskSignal` includes:
- `customer_id`: UUID
- `company_name`: string
- `status`: one of `growing`, `at_risk`, `dormant`, `new`, `stable`
- `revenue_current`: sum of `order.total_amount` for trailing 12 months
- `revenue_prior`: sum of `order.total_amount` for months 13–24 ago
- `revenue_delta_pct`: `(revenue_current - revenue_prior) / revenue_prior * 100`, rounded to 1 decimal when prior-period support exists; otherwise nullable or paired with explicit sparse-history context
- `order_count_current`: count of orders in trailing 12 months
- `order_count_prior`: count of orders in months 13–24 ago
- `avg_order_value_current`: `revenue_current / order_count_current` (0 if no current orders)
- `avg_order_value_prior`: `revenue_prior / order_count_prior` (0 if no prior orders)
- `signals`: array of human-readable strings, e.g.:
  - `"revenue up 40%"`
  - `"revenue down 35%"`
  - `"no orders in 75 days"`
  - `"AOV increased from NT$12,000 to NT$18,000"`
  - `"AOV decreased from NT$18,000 to NT$9,000"`
  - `"first order 45 days ago — new account"`
- `products_expanded_into`: array of category names that had orders in trailing 12 months but NOT in months 13–24 ago (empty if none)
- `products_contracted_from`: array of category names that had orders in months 13–24 ago but NOT in trailing 12 months (empty if none)

**AC2: Status classification**

Given a customer with known `revenue_current` and `revenue_prior`
When the classification logic runs
Then:
- `growing`: `revenue_current >= revenue_prior * 1.20` (revenue up 20% or more)
- `at_risk`: `revenue_current <= revenue_prior * 0.80` (revenue down 20% or more)
- `dormant`: no orders in the last 60 days (regardless of revenue)
- `new`: first ever order for this customer was placed in the last 90 days
- `stable`: all other cases, including sparse-history customers that are neither dormant nor new

Note: dormant takes priority over at_risk/growing if a customer went dormant after declining.

**AC3: Filtered query**

Given all customers with their risk classifications
When the AI agent calls `GET /api/v1/intelligence/customers/risk-signals?status=growing&limit=20`
Then only customers with `status == "growing"` are returned
And the result is limited to 20 records

**AC4: Frontend filter bar**

Given a sales staff user viewing the Risk Signal Feed
When the page loads
Then 6 filter buttons are shown: All / Growing / At Risk / Dormant / New / Stable
And clicking a filter updates the displayed list to that status subset
And the active filter button is visually highlighted

**AC5: Status badge colors**

Given a `CustomerRiskSignal` with any status
When the frontend renders each card
Then the status badge uses the correct color:
- `growing`: green
- `at_risk`: red
- `dormant`: orange
- `new`: blue
- `stable`: gray

**AC6: MCP tool parity**

Given a valid MCP API key with `customers:read` and `orders:read` scopes
When the AI agent calls `intelligence_customer_risk_signals(status_filter="all", limit=50)`
Then the response matches the REST API schema exactly
And the tool is registered in `TOOL_SCOPES` as `intelligence_customer_risk_signals → customers:read`, `orders:read`

## Technical Notes

### File Locations (create these)

- `backend/domains/intelligence/schemas.py` — add `CustomerRiskSignal`, `CustomerRiskSignals` Pydantic models (also `ProductPurchase` and `CategoryRevenue` if not yet added by 19.3)
- `backend/domains/intelligence/service.py` — add `get_customer_risk_signals()` (also `get_customer_product_profile()` if not yet added by 19.3)
- `backend/domains/intelligence/routes.py` — add `GET /api/v1/intelligence/customers/risk-signals` with `status` and `limit` query params
- `backend/domains/intelligence/mcp.py` — add `intelligence_customer_risk_signals` tool
- `TOOL_SCOPES` entry: `intelligence_customer_risk_signals → customers:read`, `orders:read`
- `src/domain/intelligence/types.ts` — add `CustomerRiskSignal`, `CustomerRiskSignals` TypeScript interfaces
- `src/domain/intelligence/hooks/useIntelligence.ts` — add `useCustomerRiskSignals(status, limit)` hook
- `src/domain/intelligence/components/RiskSignalFeed.tsx` — scrollable feed with filter bar
- `src/lib/api/intelligence.ts` — add `fetchCustomerRiskSignals(status, limit)` helper

### Key Implementation Details

**Service function signature:**
```python
async def get_customer_risk_signals(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    status_filter: Literal["all", "growing", "at_risk", "dormant", "new", "stable"] = "all",
    limit: int = 50,
) -> CustomerRiskSignals:
```

**Core algorithm:**

1. Get all customer UUIDs for the tenant (single query on `customers` table).
2. For each customer, compute the following aggregates in a single CTE-based query or in Python:
   - `revenue_current`: sum of `order.total_amount` where `order.created_at >= today - 12 months`
   - `revenue_prior`: sum of `order.total_amount` where `order.created_at >= today - 24 months` and `order.created_at < today - 12 months`
   - `order_count_current`: count of such orders
   - `order_count_prior`: count of such prior orders
   - `last_order_date`: max `order.created_at`
   - `first_order_date`: min `order.created_at` (for "new" detection)
   - `categories_current`: set of `Product.category` in current window
   - `categories_prior`: set of `Product.category` in prior window

3. Use a CTE to compute all aggregates per customer in a single efficient query:
```python
order_agg = (
    select(
        Order.customer_id,
        func.sum(Order.total_amount).label("revenue_current"),
        func.count(Order.id).label("order_count_current"),
        func.min(Order.created_at).label("first_order_date"),
        func.max(Order.created_at).label("last_order_date"),
    )
    .where(Order.tenant_id == tenant_id)
    .where(Order.created_at >= window_12m_start)
    .group_by(Order.customer_id)
    .subquery()
)

prior_agg = (
    select(
        Order.customer_id,
        func.sum(Order.total_amount).label("revenue_prior"),
        func.count(Order.id).label("order_count_prior"),
    )
    .where(Order.tenant_id == tenant_id)
    .where(Order.created_at >= window_prior_12m_start)
    .where(Order.created_at < window_12m_start)
    .group_by(Order.customer_id)
    .subquery()
)

# Join customers with aggregates, outer join for customers with no orders in a window
customer_signals = (
    select(
        Customer.id,
        Customer.company_name,
        func.coalesce(order_agg.c.revenue_current, 0).label("revenue_current"),
        func.coalesce(order_agg.c.order_count_current, 0).label("order_count_current"),
        func.coalesce(prior_agg.c.revenue_prior, 0).label("revenue_prior"),
        func.coalesce(prior_agg.c.order_count_prior, 0).label("order_count_prior"),
        order_agg.c.first_order_date,
        order_agg.c.last_order_date,
    )
    .outerjoin(order_agg, Customer.id == order_agg.c.customer_id)
    .outerjoin(prior_agg, Customer.id == prior_agg.c.customer_id)
    .where(Customer.tenant_id == tenant_id)
    .subquery()
)
```

4. **Category expansion/contraction**: These require a per-category per-customer subquery using `order_lines → products`. Use a CTE or two separate subqueries:

```python
# Categories in current window per customer
current_categories = (
    select(
        Order.customer_id,
        Product.category,
    )
    .join(OrderLine, OrderLine.order_id == Order.id)
    .join(Product, OrderLine.product_id == Product.id)
    .where(Order.tenant_id == tenant_id)
    .where(Order.created_at >= window_12m_start)
    .where(Product.category.isnot(None))
    .distinct()
    .subquery()
)

prior_categories = (
    select(
        Order.customer_id,
        Product.category,
    )
    .join(OrderLine, OrderLine.order_id == Order.id)
    .join(Product, OrderLine.product_id == Product.id)
    .where(Order.tenant_id == tenant_id)
    .where(Order.created_at >= window_prior_12m_start)
    .where(Order.created_at < window_12m_start)
    .where(Product.category.isnot(None))
    .distinct()
    .subquery()
)

# Python-side set operations:
# expanded = set(current_categories) - set(prior_categories)
# contracted = set(prior_categories) - set(current_categories)
```

5. **Status classification (in priority order):**
```python
def classify(status_filter: str, last_order_date, revenue_current, revenue_prior,
             first_order_date) -> str:
    now = date.today()
    # dormant: no orders in 60 days
    if last_order_date and (now - last_order_date.date() if hasattr(last_order_date, 'date') else now - last_order_date) > timedelta(days=60):
        return "dormant"
    # new: first order in last 90 days
    if first_order_date and (now - first_order_date.date() if hasattr(first_order_date, 'date') else now - first_order_date) <= timedelta(days=90):
        return "new"
    # growing/at_risk/stable
    if revenue_prior > 0:
        ratio = revenue_current / revenue_prior
        if ratio >= Decimal("1.20"):
            return "growing"
        if ratio <= Decimal("0.80"):
            return "at_risk"
    return "stable"
```

6. **Signal string generation:**
```python
def _build_signals(signal: CustomerRiskSignal) -> list[str]:
    signals = []
    if signal.revenue_prior > 0:
        delta = (signal.revenue_current - signal.revenue_prior) / signal.revenue_prior * 100
        if delta > 0:
            signals.append(f"revenue up {abs(delta):.0f}%")
        elif delta < 0:
            signals.append(f"revenue down {abs(delta):.0f}%")
    # AOV signals
    if signal.avg_order_value_prior > 0 and signal.avg_order_value_current > 0:
        aov_delta = (signal.avg_order_value_current - signal.avg_order_value_prior) / signal.avg_order_value_prior * 100
        if aov_delta >= 10:
            signals.append(f"AOV increased from NT${signal.avg_order_value_prior:,.0f} to NT${signal.avg_order_value_current:,.0f}")
        elif aov_delta <= -10:
            signals.append(f"AOV decreased from NT${signal.avg_order_value_prior:,.0f} to NT${signal.avg_order_value_current:,.0f}")
    # Dormancy signal (if not classified as dormant)
    if signal.last_order_date:
        days_since = (date.today() - signal.last_order_date).days
        if 30 <= days_since < 60:
            signals.append(f"no orders in {days_since} days")
    if signal.products_expanded_into:
        signals.append(f"expanded into {len(signal.products_expanded_into)} new categories")
    if signal.products_contracted_from:
        signals.append(f"reduced purchases in {len(signal.products_contracted_from)} categories")
    return signals
```

7. **Sorting order:**
```python
STATUS_PRIORITY = {"dormant": 0, "at_risk": 1, "growing": 2, "stable": 3, "new": 4}
results.sort(key=lambda r: STATUS_PRIORITY[r.status])
```

8. **Pydantic schemas:**
```python
# backend/domains/intelligence/schemas.py — add to existing file
class CustomerRiskSignal(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    customer_id: UUID
    company_name: str
    status: Literal["growing", "at_risk", "dormant", "new", "stable"]
    revenue_current: Decimal
    revenue_prior: Decimal
    revenue_delta_pct: Decimal  # e.g. Decimal("40.0") for +40%
    order_count_current: int
    order_count_prior: int
    avg_order_value_current: Decimal
    avg_order_value_prior: Decimal
    reason_codes: list[str]
    confidence: Literal["high", "medium", "low"]
    signals: list[str]
    products_expanded_into: list[str]
    products_contracted_from: list[str]
    last_order_date: date | None
    first_order_date: date | None

class CustomerRiskSignals(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    customers: list[CustomerRiskSignal]
    total: int
    status_filter: str
    limit: int
```

9. **TypeScript interfaces:**
```typescript
// src/domain/intelligence/types.ts — add
export interface CustomerRiskSignal {
  customer_id: string;
  company_name: string;
  status: "growing" | "at_risk" | "dormant" | "new" | "stable";
  revenue_current: string;
  revenue_prior: string;
  revenue_delta_pct: string;
  order_count_current: number;
  order_count_prior: number;
  avg_order_value_current: string;
  avg_order_value_prior: string;
    reason_codes: string[];
    confidence: "high" | "medium" | "low";
  signals: string[];
  products_expanded_into: string[];
  products_contracted_from: string[];
  last_order_date: string | null;
  first_order_date: string | null;
}

export interface CustomerRiskSignals {
  customers: CustomerRiskSignal[];
  total: number;
  status_filter: string;
  limit: number;
}
```

10. **Frontend component (`RiskSignalFeed.tsx`) layout:**

```
┌─────────────────────────────────────────────────────┐
│  Filter Bar: [All] [Growing] [At Risk] [Dormant] [New]│
├─────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────┐  │
│  │ Acme Corp  [growing]  revenue up 40%          │  │
│  │ NT$1.2M  (+25 orders)  expanded into 2 cats  │  │
│  └───────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────┐  │
│  │ Beta Inc  [at_risk]  revenue down 35%        │  │
│  │ NT$800K  (-12 orders)  no orders in 45 days  │  │
│  └───────────────────────────────────────────────┘  │
│  ... scrollable list ...                            │
└─────────────────────────────────────────────────────┘
```

Each card uses `SectionCard` with `title` = company name, `actions` = colored `Badge`. The card body shows the first 2–3 signals as text. The entire list is wrapped in a scrollable `div` with `max-height`.

**Badge color map:**
```typescript
const BADGE_COLORS = {
  growing: "bg-green-100 text-green-800 border-green-300",
  at_risk: "bg-red-100 text-red-800 border-red-300",
  dormant: "bg-orange-100 text-orange-800 border-orange-300",
  new: "bg-blue-100 text-blue-800 border-blue-300",
  stable: "bg-gray-100 text-gray-800 border-gray-300",
} as const;
```

### Critical Warnings

- **Do NOT create new database tables.** All data is derived from `orders`, `order_lines`, `products`, and `customers`.
- **Dormant takes priority over at_risk/growing** — a customer with no orders in 60 days is "dormant" regardless of their revenue delta.
- **`new` status takes priority over growing/stable** — if this is the customer's first 90 days, they are "new" even if revenue is surging.
- **Guard division by zero** on `revenue_delta_pct` when `revenue_prior == 0`. Return `None` plus an explanatory `reason_codes` / `confidence` signal rather than fake precision.
- **Guard division by zero** on `avg_order_value_current/prior` when `order_count_current/prior == 0`. Return `Decimal("0")`.
- **All queries must be tenant-scoped** — join or filter by `tenant_id` on all tables.
- **Limit should be applied after sorting** — sort all results first, then slice to `limit`.
- **Avoid N+1 queries** — use CTEs or subqueries to compute all customer aggregates in 2–3 queries maximum, not one query per customer.
- **`products_expanded_into` and `products_contracted_from` require category-level aggregation** — these need a separate subquery join through `order_lines → product`. Do not skip them.
- **`last_order_date` may be NULL** for customers with no orders — handle as `None`.
- **Status badge ordering**: The sort order is dormant → at_risk → growing → stable → new. When filtering by "all", this order must be preserved.

## Tasks / Subtasks

- [ ] Task 1: Add Pydantic schemas for risk signals (AC1)
  - [ ] Subtask 1.1: Add `CustomerRiskSignal`, `CustomerRiskSignals` to `schemas.py`
  - [ ] Subtask 1.2: Ensure `CategoryRevenue`, `ProductPurchase` schemas exist (from 19.3)

- [ ] Task 2: Implement `get_customer_risk_signals()` in `service.py` (AC1, AC2)
  - [ ] Subtask 2.1: Date window constants (reuse same pattern as 19.3)
  - [ ] Subtask 2.2: CTE for current-period aggregates per customer
  - [ ] Subtask 2.3: CTE for prior-period aggregates per customer
  - [ ] Subtask 2.4: Category aggregation CTEs for `products_expanded_into` / `products_contracted_from`
  - [ ] Subtask 2.5: Status classification logic with priority rules
  - [ ] Subtask 2.6: Signal string generation for `signals` array
  - [ ] Subtask 2.7: Sorting by status priority order
  - [ ] Subtask 2.8: Limit application after sorting

- [ ] Task 3: Add REST route in `routes.py` (AC1, AC3)
  - [ ] Subtask 3.1: `GET /api/v1/intelligence/customers/risk-signals` with `status` and `limit` query params
  - [ ] Subtask 3.2: `status` param: `Literal["all", "growing", "at_risk", "dormant", "new", "stable"]`
  - [ ] Subtask 3.3: `limit` param: `Query(default=50, ge=1, le=200)`
  - [ ] Subtask 3.4: Return `CustomerRiskSignals` response model

- [ ] Task 4: Add MCP tool and wire `TOOL_SCOPES` (AC6)
  - [ ] Subtask 4.1: Add `intelligence_customer_risk_signals` tool
    - [ ] Subtask 4.2: Add `TOOL_SCOPES` entry: `intelligence_customer_risk_signals → customers:read`, `orders:read`
  - [ ] Subtask 4.3: Register `domains.intelligence.mcp` in `mcp_server.py` (if not already done by 19.3)

- [ ] Task 5: Frontend TypeScript types and API helper (AC1)
  - [ ] Subtask 5.1: Add `CustomerRiskSignal`, `CustomerRiskSignals` to `types.ts`
  - [ ] Subtask 5.2: Add `fetchCustomerRiskSignals(status, limit)` to `src/lib/api/intelligence.ts`

- [ ] Task 6: Frontend hook `useCustomerRiskSignals` (AC1)
  - [ ] Subtask 6.1: Add `useCustomerRiskSignals(status, limit)` to `useIntelligence.ts`
  - [ ] Subtask 6.2: Re-fetch when `status` or `limit` changes

- [ ] Task 7: Frontend component `RiskSignalFeed.tsx` (AC4, AC5)
    - [ ] Subtask 7.1: Filter bar with 6 buttons (All / Growing / At Risk / Dormant / New / Stable)
  - [ ] Subtask 7.2: Active filter state with visual highlight
  - [ ] Subtask 7.3: Scrollable list of `SectionCard` items
  - [ ] Subtask 7.4: Company name as card title, status badge (color-coded) using correct color map
  - [ ] Subtask 7.5: Revenue delta and first 2–3 signals rendered as text in card body

## Dev Notes

### Repo Reality

- `Product.category` is `str | None` at `backend/common/models/product.py:32`
- `Order.total_amount` is `Decimal | None` at `backend/common/models/order.py:48`
- `Order.created_at` is `datetime` at `backend/common/models/order.py:57`
- `Customer.company_name` is `str` at `backend/domains/customers/models.py:21`
- `relativedelta` from `dateutil.relativedelta` for date arithmetic
- `Badge` component from shadcn/ui available for status badges
- `SectionCard` from `src/components/layout/PageLayout.tsx`
- `apiFetch` pattern: `apiFetch("/api/v1/...").then(r => r.json())`
- shadcn/ui `Card`, `CardHeader`, `CardTitle`, `CardContent` for feed items
- Recharts not needed for this component — plain text/card layout only

### References

- `backend/common/models/order.py:29-59` — Order model fields
- `backend/common/models/order_line.py:35-57` — OrderLine model, join to Product
- `backend/common/models/product.py:30-32` — Product `category` field
- `backend/domains/customers/models.py:15-21` — Customer model
- `backend/domains/customers/service.py:7-11` — `relativedelta` import
- `backend/app/mcp_auth.py:24-45` — `TOOL_SCOPES` format
- `backend/app/mcp_server.py:25` — domain MCP registration pattern
- `src/domain/dashboard/types.ts` — TypeScript interface examples for `Decimal as string` pattern
- `src/domain/dashboard/hooks/useDashboard.ts:34-49` — simple `useState`/`useEffect` hook pattern (sufficient for risk signals)
- `src/lib/api/dashboard.ts` — API helper pattern
- `src/components/layout/PageLayout.tsx:43` — `SectionCard` signature
