# Story 19.6: Market Opportunities Signal Feed

Status: done

## Story

As an **AI agent or sales staff**,
I want to see high-level market signals — new product adoption, concentration risk, churn risk — so that I understand macro trends and can act on them before problems compound or opportunities pass.

## Problem Statement

Without a unified signal feed, AI agents and sales staff must synthesize insights from multiple dashboards and reports to understand market dynamics. This manual synthesis is error-prone, slow, and not actionable for AI agents that need a single API call to assess the current market landscape. The signal feed distills the output of all other intelligence types (affinity maps, segmentation, trend analysis) into a small set of actionable, severity-coded alerts.

## Solution

The system aggregates signals derived from existing intelligence computations across the portfolio. The `get_market_opportunities()` service function is a **read-only aggregator** — it does not compute new intelligence but wraps stabilized upstream outputs into a unified signal model.

For v1, the emitted signal set is intentionally narrow:

1. **Concentration Risk** — any single customer representing >30% of total revenue → required portfolio risk alert
2. **Category Growth** — top categories ranked by `revenue_delta_pct` when Story 19.2 support floors and cleaning rules are satisfied → optional momentum signal

`new_product_adoption` and `churn_risk` remain documented future signal types, but they are deferred until upstream signal quality is validated.

Signals are returned in priority order: `alert` → `warning` → `info`.

## Best-Practice Update

This section supersedes conflicting details below.

- Story 19.6 is a composition layer, not a primary source of truth. It should reuse stabilized upstream intelligence rather than introduce novel heavy logic.
- `concentration_risk` is the strongest v1 signal and should be the required initial output.
- `category_growth` can be included once Story 19.2 support floors and category cleaning rules are stable.
- `new_product_adoption` and `churn_risk` should be deferred until upstream signal quality is validated.
- Every emitted signal must include support counts and source period metadata so banners cannot overstate certainty.
- Do not reference nonexistent schema elements such as `order_date`, `categories`, or `category_id` in implementation guidance.

## Acceptance Criteria

### AC-1: Market Opportunities Endpoint

**Given** a valid `period` parameter (e.g., `last_30d`, `last_90d`, `last_12m`)  
**When** calling `GET /api/v1/intelligence/market-opportunities?period=last_90d`  
**Then** the response contains:
- `period`: the requested period string
- `generated_at`: ISO 8601 timestamp of when the signals were computed
- `signals`: array of `OpportunitySignal` objects sorted by severity (alert first)

### AC-2: Deferred Signals Stay Out of v1

**Given** market opportunities are computed in the first production pass  
**When** the response is generated  
**Then** `new_product_adoption` and `churn_risk` are not emitted  
**And** the response contract or documentation explicitly notes that those signal types are deferred pending upstream validation

### AC-3: Category Growth Signal Is Optional

**Given** category revenue delta is computed from the stabilized Story 19.2 contract  
**When** support floors are met and the category-cleaning rules pass  
**Then** a `category_growth` signal may be emitted with:
- `signal_type`: `"category_growth"`
- `severity`: `"info"` if delta < 30%, `"warning"` if delta >= 30%
- `headline`: e.g., "Electronics revenue up 45% vs prior period"
- `detail`: revenue delta absolute and percentage, category name
- `affected_customer_count`: distinct customers purchasing in that category
- `revenue_impact`: absolute revenue change in dollars
- `recommended_action`: e.g., "Review supply, pricing, and sales focus for Electronics."
- `support_counts`: enough evidence to explain why the signal was emitted

### AC-4: Concentration Risk Signal Is Required in v1

**Given** revenue concentration is computed  
**When** any single customer represents >30% of total period revenue  
**Then** a signal is emitted with:
- `signal_type`: `"concentration_risk"`
- `severity`: `"alert"`
- `headline`: e.g., "Acme Corp represents 47% of total revenue — concentration risk"
- `detail`: customer name, revenue amount, percentage of total, prior period percentage when available
- `affected_customer_count`: 1
- `revenue_impact`: that customer's revenue amount
- `recommended_action`: e.g., "Diversify revenue concentration and review expansion or mitigation actions."
- `support_counts`: the denominator and affected-customer evidence needed to audit the signal

### AC-5: MCP Tool Interface

**Given** an AI agent with valid credentials  
**When** calling the `intelligence_market_opportunities` MCP tool with `period` argument  
**Then** the tool returns a JSON object matching the `MarketOpportunities` schema and raises `ToolError` on invalid period or auth failure  
**And** only stabilized v1 signals are emitted in the payload

### AC-6: Frontend Signal Banner Component

**Given** the Category Trends tab is open  
**When** `useMarketOpportunities(period)` returns signals  
**Then**:
- Alert-style banners are rendered above the chart area
- `alert` severity: red background/border with white text
- `warning` severity: amber/yellow background/border
- `info` severity: blue/gray background/border
- Each banner displays: severity icon, headline, detail snippet, affected customer count, recommended action button
- Clicking a banner expands to show full detail

### AC-7: Frontend Hook

**Given** a React component consuming `useIntelligence`  
**When** calling `useMarketOpportunities(period)`  
**Then** the hook returns `{ data, isLoading, error }` where `data` conforms to the `MarketOpportunities` TypeScript interface

---

## Technical Notes

### File Locations (create/extend these)

**Backend:**
- `backend/domains/intelligence/schemas.py` — add `OpportunitySignal`, `MarketOpportunities` Pydantic models
- `backend/domains/intelligence/service.py` — add `get_market_opportunities()` function
- `backend/domains/intelligence/routes.py` — add `GET /api/v1/intelligence/market-opportunities`
- `backend/domains/intelligence/mcp.py` — add `intelligence_market_opportunities` MCP tool
- `backend/app/mcp_auth.py` — add `TOOL_SCOPES` entry: `intelligence_market_opportunities` → `frozenset(["customers:read", "orders:read"])`

**Frontend:**
- `src/domain/intelligence/types.ts` — add `OpportunitySignal`, `MarketOpportunities` TypeScript interfaces
- `src/domain/intelligence/hooks/useIntelligence.ts` — add `useMarketOpportunities(period)` hook
- `src/domain/intelligence/components/OpportunitySignalBanner.tsx` — new banner component

### Key Implementation Details

#### Query: New Product Adoption (deferred in v1)

```python
# Deferred until upstream signal quality is validated.
# Do not implement in the first pass of Story 19.6.
```

#### Query: Category Growth (revenue delta)

```python
# Compare current period value to prior period by category using Product.category
category_revenue_current = (
    select(
        products.c.category.label("category_name"),
        func.sum(order_lines.c.quantity * order_lines.c.unit_price).label("revenue"),
    )
    .select_from(orders)
    .join(order_lines, order_lines.c.order_id == orders.c.id)
    .join(products, products.c.id == order_lines.c.product_id)
    .where(orders.c.created_at >= func.current_date() - text(f"INTERVAL '{period_days} days'"))
    .where(orders.c.tenant_id == tenant_id)
    .where(products.c.category.isnot(None))
    .group_by(products.c.category)
)
# Compute delta_pct by joining with prior period, rank top 3
```

#### Query: Concentration Risk

```python
# Customer revenue share
total_revenue = (
    select(func.sum(orders.c.total_amount))
    .where(orders.c.tenant_id == tenant_id)
    .scalar_subquery()
)
customer_revenue_share = (
    select(
        customers.c.id,
        customers.c.company_name,
        func.sum(orders.c.total_amount).label("revenue"),
        (func.sum(orders.c.total_amount) / total_revenue * 100).label("pct_of_total"),
    )
    .select_from(orders)
    .join(customers, customers.c.id == orders.c.customer_id)
    .where(orders.c.tenant_id == tenant_id)
    .group_by(customers.c.id, customers.c.company_name)
    .having(func.sum(orders.c.total_amount) / total_revenue > 0.30)
)
```

#### Query: Churn Risk (deferred in v1)

```python
# Deferred until the upstream risk trend logic is stabilized and validated.
```

#### Pydantic Schema

```python
class OpportunitySignal(BaseModel):
  signal_type: Literal["category_growth", "concentration_risk"]
    severity: Literal["info", "warning", "alert"]
    headline: str
    detail: str
    affected_customer_count: int
    revenue_impact: float  # positive for growth signals, negative for risk signals
    recommended_action: str
    support_counts: dict[str, int] | None = None
    source_period: str
    model_config = ConfigDict(from_attributes=True)

class MarketOpportunities(BaseModel):
    period: str
    generated_at: datetime
    signals: list[OpportunitySignal]
```

#### MCP Tool Pattern

```python
@mcp.tool(annotations={"readOnlyHint": True})
async def intelligence_market_opportunities(period: str = "90d") -> str:
  period_map = {"last_30d": 30, "last_90d": 90, "last_12m": 365}
  period_days = period_map.get(period, 90)
    async with AsyncSessionLocal() as session:
        tid = await get_tenant_id(session)
        async with session.begin():
            await set_tenant(session, tid)
        result = await get_market_opportunities(session, tid, period_days=period_days)
        return json.dumps(result.model_dump(), default=str)
```

### Edge Cases

- **Period parameter validation**: only accept `last_30d`, `last_90d`, `last_12m` — return 400 for anything else
- **No signals found**: return `signals: []` with `generated_at` timestamp (not an error)
- **Multiple concentration risk customers**: emit one signal per customer (each > 30% individually)
- **Zero total revenue**: skip concentration risk and category growth calculations, return empty signals
- **New-product adoption and churn-risk signals**: explicitly omit them in v1 until their source logic is stabilized
- **Signal ordering**: always sort by severity: `alert` > `warning` > `info`; within same severity, sort by `revenue_impact` descending

### Critical Warnings

- **DO NOT** create a new database table for signals — compute on-the-fly from existing tables
- **DO NOT** compute new intelligence in this story — aggregate only; delegate actual computation to the service functions from stories 19.1–19.4
- **DO NOT** expose raw SQL — use SQLAlchemy 2.0 async queries
- **DO NOT** skip tenant isolation — every query MUST filter by `tenant_id`
- **DO NOT** hardcode period days in SQL — use parameterized period values to prevent injection
- The `detail` field on `OpportunitySignal` should be a JSON-encoded string (not a nested object) to ensure MCP tool compatibility

---

## Tasks / Subtasks

- [x] Task 19.6.1: Add schemas and service function (AC: #1–5)
  - [x] Add `OpportunitySignal` and `MarketOpportunities` Pydantic schemas to `schemas.py`
    - [x] Implement `get_market_opportunities()` in `service.py` with concentration risk as the required v1 signal and optional category growth once Story 19.2 is stable
  - [x] Add `GET /api/v1/intelligence/market-opportunities` route in `routes.py`
  - [x] Add `TOOL_SCOPES` entry for `intelligence_market_opportunities` in `mcp_auth.py`

- [x] Task 19.6.2: Add MCP tool endpoint (AC: #6)
  - [x] Implement `intelligence_market_opportunities` MCP tool
  - [x] Validate period parameter (`last_30d`, `last_90d`, `last_12m`)
  - [x] Handle ToolError for invalid inputs and auth failures

- [x] Task 19.6.3: Frontend types and hook (AC: #8)
  - [x] Add `OpportunitySignal` and `MarketOpportunities` TypeScript interfaces
  - [x] Add `useMarketOpportunities(period)` to `useIntelligence.ts`
  - [x] Wire to API endpoint with loading/error states

- [x] Task 19.6.4: OpportunitySignalBanner component (AC: #7)
  - [x] Banner with severity-based color coding (alert=red, warning=amber, info=blue)
  - [x] Headline, detail, customer count, and recommended action display
  - [x] Expand/collapse for full detail on click
  - [x] Embed banners at top of Category Trends tab

- [x] Task 19.6.5: Period validation and edge cases (AC: #1)
  - [x] Validate period parameter values
  - [x] Handle zero-revenue tenant case
    - [x] Omit deferred signals with an explicit note in the response contract or documentation
  - [x] Signal ordering by severity then revenue impact

---

## Dev Notes

### Repo Reality

- The `backend/domains/intelligence/` package created in Story 19.5 continues here — extend existing files rather than creating new ones for 19.6
- Signal aggregation should only emit signals backed by completed upstream helpers; do not add placeholder signal outputs for unfinished dependencies
- The frontend `Category Trends` tab already exists in `src/domain/inventory/components/StockTrendChart.tsx` or a related file — `OpportunitySignalBanner` should be embedded there
- Recharts is already in use in the frontend; banner components do not use recharts
- Existing MCP tools use `raise ToolError(json.dumps({...}))` for error signaling

### References

- `backend/domains/inventory/routes.py` — route pattern for GET endpoints with query params
- `backend/app/mcp_auth.py` — `TOOL_SCOPES` with multiple scope entries: `frozenset(["customers:read", "orders:read"])`
- `src/domain/inventory/components/StockTrendChart.tsx` — Category Trends tab embedding point
- `src/domain/dashboard/components/GrossMarginCard.tsx` — severity/color coding pattern for alert-style cards

### Story Dependencies

- **Prerequisite:** Story 19.7 for access wiring and the shared intelligence module scaffolding
- **Depends on:** Story 19.2 for optional `category_growth`, plus the shared intelligence contracts stabilized by earlier stories
- **Enables:** optional later composition work for deferred signals once upstream signal quality is proven trustworthy

## Review Findings

- [x] Tightened `category_growth` emission to positive growing categories that meet the Story 19.2 support floors, preventing weak or declining categories from leaking into the v1 banner feed
- [x] Aligned market-opportunity tenant resolution and auth precedence with the broader intelligence surface so API-key tenant binding remains enforced while sales bearer access matches the shipped REST/UI contract
- [x] Exposed `support_counts` and `source_period` in the expanded banner path and added focused regression coverage for the composition-layer filter rules

## Completion Notes

- Implemented the market-opportunity composition layer end to end: schemas, service aggregation, REST endpoint, MCP tool, frontend types/hook, and expandable banner integration in the category trend radar.
- The v1 response now emits only `concentration_risk` and support-floor-qualified `category_growth` signals, while documenting `new_product_adoption` and `churn_risk` as deferred signal types.
- Validation: `uv run pytest tests/domains/intelligence/test_service.py tests/domains/intelligence/test_routes.py tests/test_mcp_intelligence.py tests/test_mcp_auth.py -q` (72 passed) and `pnpm --dir /Volumes/2T_SSD_App/Projects/UltrERP exec vitest run src/tests/intelligence/AffinityMatrix.test.tsx src/tests/intelligence/CategoryTrendRadar.test.tsx src/tests/intelligence/OpportunitySignalBanner.test.tsx src/tests/intelligence/ProspectGapTable.test.tsx src/tests/intelligence/RiskSignalFeed.test.tsx src/tests/customers/CustomerAnalyticsTab.test.tsx src/tests/auth/rbac-ui.test.tsx` (40 passed).
