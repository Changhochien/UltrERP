# Story 19.5: Prospect Gap Analysis

Status: revised-ready-for-dev

## Story

As an **AI agent or sales staff**,
I want to know which customers are NOT buying in a given product category but would be good fits,
so that I can prioritize prospecting efficiently and focus outreach on the highest-value targets.

## Problem Statement

Sales teams waste cycles reaching out to customers who are poor fits or already well-served. Without data-driven prospect prioritization, outreach is random and inefficient. AI agents acting on behalf of sales need a structured "who to target and why" signal derived from existing purchase behavior. The gap between who buys a category today and who *should* be buying it is the core intelligence this story surfaces.

## Solution

The system computes the **set difference** between all active customers and those who have purchased in a given category. Each non-buyer is scored using an **affinity model** that combines:
1. **Order frequency similarity** — how often this customer orders vs. buyers of the target category
2. **Category breadth proximity** — how many distinct categories the customer buys in vs. buyers of the target category
3. **Adjacent-category support** — whether the customer already buys categories that co-occur with the target category
4. **Recency factor** — whether the customer has recent qualifying activity strong enough to support outreach now

Customers with high affinity scores but no purchases in the target category are surfaced as warm prospects with a human-readable reason, explicit score components, and tags.

## Best-Practice Update

This section supersedes conflicting details below.

- Treat v1 as a transparency-first whitespace candidate list, not a predictive prospecting oracle.
- The live repo uses `Product.category` as a string. Do not assume a `categories` table or `category_id` in queries or score logic.
- Default MCP and REST payloads should omit contact phone and email. Contact PII belongs in human drill-ins or stricter-scope payload variants.
- Return `score_components`, `reason_codes`, and `confidence` alongside `affinity_score` so agents can evaluate why a candidate ranked well.
- Keep the candidate universe coherent. If the story is limited to active customers, remove `never_order`; if true zero-order customers are included, document that explicitly and treat them as a separate low-confidence cohort.
- The first human UI should behave like an outreach queue: company, rationale, recency, tags, and drill-through matter more than wide contact columns.

## Acceptance Criteria

### AC-1: Prospect Gap List

**Given** a valid product `category` parameter  
**When** the AI agent or sales staff calls `GET /api/v1/intelligence/prospect-gaps?category=<cat>&limit=20`  
**Then** the response includes:
- `target_category`: the requested category name
- `target_category_revenue`: total revenue from existing buyers in that category
- `existing_buyers_count`: number of distinct customers who bought in the category
- `prospects_count`: total number of non-buyers identified as prospects
- `prospects`: array of up to `limit` prospects sorted by `affinity_score` descending

### AC-2: Prospect Record Structure

**Given** a prospect in the `prospects` array  
**When** examining the record  
**Then** each prospect contains:
- `customer_id` (UUID)
- `company_name` (string)
- `total_revenue` (float, total revenue from all orders)
- `category_count` (int, distinct categories purchased)
- `avg_order_value` (float)
- `last_order_date` (date string, nullable)
- `affinity_score` (float 0.0–1.0, higher = better fit)
- `score_components` (object with normalized component scores)
- `reason_codes` (string[])
- `confidence` ("high" | "medium" | "low")
- `reason` (string, human-readable explanation e.g. "High AOV customer with 8 categories, no purchases in Electronics")
- `tags` (string[] e.g. `["dormant", "adjacent_category"]`)

### AC-3: Affinity Score Computation

**Given** a prospect customer `C` and target category `K`  
**When** the affinity score is computed  
**Then** the score is derived from:
- `frequency_similarity`: normalized similarity between C's order frequency and the buyer cohort for K
- `breadth_similarity`: normalized similarity between C's category count and the buyer cohort for K
- `adjacent_category_support`: whether C already buys categories with strong affinity to K
- `recency_factor`: a recency score based on recent activity
- `affinity_score = 0.35 * frequency_similarity + 0.35 * breadth_similarity + 0.20 * adjacent_category_support + 0.10 * recency_factor`

### AC-4: Tag Assignment Logic

**Given** a prospect customer  
**When** tags are assigned  
**Then** the following tags are applied based on conditions:
- `"dormant"`: last_order_date is more than 90 days ago
- `"high_value"`: total_revenue is in the top 20% of all customers
- `"adjacent_category"`: customer buys in at least one category that co-occurs with the target category in the same orders
- `"new_customer"`: customer has been active for less than 90 days

### AC-5: MCP Tool Interface

**Given** an AI agent with valid credentials  
**When** calling the `intelligence_prospect_gaps` MCP tool with `category` and `limit` arguments  
**Then** the tool returns a JSON object matching the `ProspectGaps` schema and raises `ToolError` on invalid category or auth failure

### AC-6: Frontend Table Display

**Given** the Prospect Gap Analysis page  
**When** rendered  
**Then**:
- A category dropdown selector is displayed above the table
- The table is sorted by `affinity_score` descending (default)
- Columns displayed: Company, Reason, Last Order Date, Category Count, AOV, Affinity Score (progress bar), Tags
- Each affinity score renders as a progress bar (0–100%) with color coding: red < 0.3, yellow 0.3–0.6, green > 0.6
- Existing buyer count is shown as a badge near the category selector

### AC-7: Frontend Hook

**Given** a React component consuming `useIntelligence`  
**When** calling `useProspectGaps(category, limit)`  
**Then** the hook returns `{ data, isLoading, error }` where `data` conforms to the `ProspectGaps` TypeScript interface

---

## Technical Notes

### File Locations (create/extend these)

**Backend:**
- `backend/domains/intelligence/__init__.py` — new package init
- `backend/domains/intelligence/schemas.py` — add `ProspectFit`, `ProspectGaps` Pydantic models
- `backend/domains/intelligence/service.py` — add `get_prospect_gaps()` async function
- `backend/domains/intelligence/routes.py` — add `GET /api/v1/intelligence/prospect-gaps`
- `backend/domains/intelligence/mcp.py` — add `intelligence_prospect_gaps` MCP tool
- `backend/app/mcp_auth.py` — add `TOOL_SCOPES` entry: `intelligence_prospect_gaps` → `frozenset(["customers:read", "orders:read"])`
- `backend/app/mcp_server.py` — import `intelligence` module at bottom (follow existing pattern)

**Frontend:**
- `src/domain/intelligence/__init__.py` — new package init
- `src/domain/intelligence/types.ts` — add `ProspectFit`, `ProspectGaps` TypeScript interfaces
- `src/domain/intelligence/hooks/useIntelligence.ts` — extend/add `useProspectGaps(category, limit)` hook
- `src/domain/intelligence/components/ProspectGapTable.tsx` — new component

### Key Implementation Details

#### Query Structure (SQLAlchemy 2.0)

```python
# Get all active customer IDs (have placed at least one order)
active_customers = (
    select(customers.c.id)
    .join(orders, orders.c.customer_id == customers.c.id)
    .where(customers.c.tenant_id == tenant_id)
    .group_by(customers.c.id)
)

# Get existing buyer IDs for target category
category_buyers = (
    select(orders.c.customer_id)
    .join(order_lines, order_lines.c.order_id == orders.c.id)
    .join(products, products.c.id == order_lines.c.product_id)
  .where(products.c.category == category)
    .where(orders.c.tenant_id == tenant_id)
    .distinct()
)

# Prospect gap = active_customers MINUS category_buyers
prospect_ids = (
    select(customers.c.id)
    .where(customers.c.id.in_(active_customers))
    .where(~customers.c.id.in_(category_buyers))
)
```

#### Affinity Score Formula

```python
# Compute buyer stats for target category
buyer_stats = await session.execute(
    select(
        func.avg(orders.c.total_amount).label("mean_aov"),
        func.count(func.distinct(orders.c.id)).label("order_count"),
    func.count(func.distinct(products.c.category)).label("category_count"),
    )
    .select_from(orders)
    .join(order_lines, order_lines.c.order_id == orders.c.id)
    .join(products, products.c.id == order_lines.c.product_id)
  .where(products.c.category == target_category)
    .where(orders.c.tenant_id == tenant_id)
)
# Normalize and compute weighted score components per prospect customer
```

#### Pydantic Schema

```python
class ProspectFit(BaseModel):
    customer_id: uuid.UUID
    company_name: str
    total_revenue: float
    category_count: int
    avg_order_value: float
    last_order_date: date | None
    affinity_score: float  # 0.0–1.0
  score_components: dict[str, float]
  reason_codes: list[str]
  confidence: Literal["high", "medium", "low"]
    reason: str
    tags: list[str]
    model_config = ConfigDict(from_attributes=True)

class ProspectGaps(BaseModel):
    target_category: str
    target_category_revenue: float
    existing_buyers_count: int
    prospects_count: int
    prospects: list[ProspectFit]
```

#### MCP Tool Pattern

```python
@mcp.tool(annotations={"readOnlyHint": True})
async def intelligence_prospect_gaps(category: str, limit: int = 20) -> str:
    async with AsyncSessionLocal() as session:
        tid = await get_tenant_id(session)
        async with session.begin():
            await set_tenant(session, tid)
        result = await get_prospect_gaps(session, tid, category=category, limit=limit)
        if result is None:
            raise ToolError(json.dumps({"error": "invalid_category"}))
        return json.dumps(result.model_dump(), default=str)
```

### Edge Cases

- **Empty category**: return 400 error with message "category is required"
- **Invalid category name**: return empty prospects list with `existing_buyers_count: 0`
- **No prospects found**: return `prospects_count: 0, prospects: []` (not an error)
- **limit > 100**: cap at 100
- **Customer with no orders but exists in DB**: exclude from the v1 active-customer candidate set unless the story is explicitly expanded to a low-confidence cold-start cohort
- **Tenant isolation**: ALWAYS filter by `tenant_id` on all queries

### Critical Warnings

- **DO NOT** create a new database table for prospects — compute on-the-fly from existing `orders`, `order_lines`, `products`, `customers` tables
- **DO NOT** expose raw SQL — use SQLAlchemy 2.0 async queries throughout
- **DO NOT** skip tenant isolation — every query MUST filter by `tenant_id`
- **DO NOT** use `category_id` directly in the public API — use `category` name string for human readability
- Affinity score inputs depend on Story 19.1 (Affinity Map) — if 19.1 is not complete, stub the affinity computation with a simplified fallback using only category count proximity

---

## Tasks / Subtasks

- [ ] Task 19.5.1: Create `backend/domains/intelligence/` package structure (AC: #1–3)
  - [ ] Create `__init__.py` with package exports
  - [ ] Add `ProspectFit` and `ProspectGaps` Pydantic schemas
  - [ ] Implement `get_prospect_gaps()` in `service.py`
  - [ ] Add `GET /api/v1/intelligence/prospect-gaps` route in `routes.py`
  - [ ] Add `TOOL_SCOPES` entry in `mcp_auth.py`
  - [ ] Register MCP tool in `mcp.py` and import in `mcp_server.py`

- [ ] Task 19.5.2: Add MCP tool endpoint (AC: #5)
  - [ ] Implement `intelligence_prospect_gaps` MCP tool with session management
  - [ ] Handle ToolError for invalid inputs
  - [ ] Test tool invocation with valid/invalid category

- [ ] Task 19.5.3: Frontend types and hook (AC: #7)
  - [ ] Add `ProspectFit` and `ProspectGaps` TypeScript interfaces to `types.ts`
  - [ ] Add `useProspectGaps(category, limit)` to `useIntelligence.ts`
  - [ ] Wire hook to API endpoint with proper loading/error states

- [ ] Task 19.5.4: ProspectGapTable component (AC: #6)
  - [ ] Category dropdown selector with current selection state
  - [ ] Table sorted by affinity_score desc with all specified columns
  - [ ] Affinity score progress bar with red/yellow/green color coding
  - [ ] Existing buyer count badge
  - [ ] Tag chips rendering

- [ ] Task 19.5.5: Integration and edge cases (AC: #4, #6)
  - [ ] Tag assignment logic (dormant, high_value, adjacent_category, new_customer)
  - [ ] Return `score_components`, `reason_codes`, and `confidence`
  - [ ] Exclude zero-order customers from the default active-customer candidate set
  - [ ] Limit capping at 100
  - [ ] Tenant isolation verification

---

## Dev Notes

### Repo Reality

- The `backend/domains/` directory already exists with `inventory/`, `orders/`, `customers/`, `invoices/` — use these as structural templates for the new `intelligence/` domain
- Existing service functions follow the pattern: `async def fn(session: AsyncSession, tenant_id: uuid.UUID, *, ...)` with `async with session.begin(): await set_tenant(session, tid)`
- MCP tools in existing domains (e.g., `inventory/mcp.py`) follow the `@mcp.tool()` + `AsyncSessionLocal()` pattern
- Frontend components follow the `SectionCard` + `PageHeader` layout pattern from `PageLayout.tsx`
- Recharts `BarChart`/`LineChart` are used in sibling intelligence components

### References

- `backend/domains/customers/service.py` — customer query patterns with tenant isolation
- `backend/domains/inventory/mcp.py` — MCP tool registration pattern (import at bottom of `mcp_server.py`)
- `backend/app/mcp_auth.py` — `TOOL_SCOPES` dict structure
- `src/domain/inventory/components/StockTrendChart.tsx` — recharts usage pattern
- `src/domain/intelligence/` — will be new directory, see sibling `dashboard/` domain for patterns

### Story Dependencies

- **Prerequisite:** Story 19.7 for access wiring, plus Story 19.1 for affinity inputs
- **Depends on:** Story 19.1 and the shared customer/category aggregates stabilized by Stories 19.2 and 19.3
- **Enables:** targeted outreach queues and optional later recommendation layers once signal quality is proven
