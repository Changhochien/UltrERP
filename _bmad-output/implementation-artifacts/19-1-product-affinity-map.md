# Story 19.1: Product Affinity Map

Status: done

## Story

As an **AI agent**,
I want to know which products are frequently purchased together
So that I can suggest bundle pitches and cross-sell recommendations to customers.

## Problem Statement

Sales data in `orders` and `order_lines` already contains the raw material for co-purchase intelligence, but no surface exists for AI agents (or human sales staff) to answer questions like "which products should we pitch together?" or "what bundles make sense given our customer base?" Without affinity analysis, bundle recommendations are guesswork rather than data-driven. A product affinity map turns transaction history into actionable commercial intelligence.

## Solution

A new `domains/intelligence/` backend module exposes co-occurrence analysis via both REST (for the human UI) and MCP (for AI agents). The `get_product_affinity_map()` service function runs a Jaccard-coefficient co-occurrence query across `order_lines` joined through `orders` and `customers` — no new tables needed, all computation from existing data.

**Co-occurrence logic:**
1. For every pair of products A and B, find customers who ordered both (via the same or different orders).
2. `shared_customer_count` = distinct customer UUIDs who have at least one order containing A AND at least one order containing B.
3. `overlap_pct = shared_customer_count / min(customer_count_a, customer_count_b) * 100`
4. `affinity_score = shared_customer_count / (customer_count_a + customer_count_b - shared_customer_count)` (customer-level Jaccard index)
5. `pitch_hint` = auto-generated phrase like "Often bought with {product_a_name} — consider a bundle"

The frontend renders a sortable table with inline progress bars for `overlap_pct`.

## Best-Practice Update

This section supersedes conflicting details below.

- The affinity contract is customer-level in v1. Use `shared_customer_count`, `customer_count_a`, and `customer_count_b` as the canonical basis for both `overlap_pct` and Jaccard `affinity_score`.
- Keep `shared_order_count` as optional supporting evidence, but do not mix customer-based numerators with order-based denominators.
- Return structured evidence first: `customer_count_a`, `customer_count_b`, `shared_customer_count`, optional `shared_order_count`, `computed_at`, `min_shared`, and `limit`. `pitch_hint` is convenience text only.
- Deterministic sort order is required: `affinity_score DESC`, `shared_customer_count DESC`, `product_a_name ASC`, `product_b_name ASC`.
- The human UI is optional and should be embeddable in intelligence or customer/prospect surfaces rather than assumed to be a top-level standalone page.
- Qualifying activity uses confirmed / shipped / fulfilled orders only.

## Acceptance Criteria

**AC1: MCP tool returns correctly scored affinity pairs**
**Given** multiple orders containing product pairs from the same or different customers
**When** the AI agent calls `intelligence_product_affinity(min_shared=3, limit=50)`
**Then** the response includes up to 50 product pairs sorted by Jaccard `affinity_score` descending
**And** each pair contains: `product_a_id`, `product_b_id`, `product_a_name`, `product_b_name`, `shared_customer_count`, `customer_count_a`, `customer_count_b`, `overlap_pct`, `affinity_score`, `pitch_hint`
**And** `overlap_pct = shared_customer_count / min(customer_count_a, customer_count_b) * 100`
**And** `affinity_score = shared_customer_count / (customer_count_a + customer_count_b - shared_customer_count)` (customer-level Jaccard)
**And** pairs with `shared_customer_count < min_shared` are excluded

**AC2: REST endpoint serves the same data**
**Given** a sales staff user calling `GET /api/v1/intelligence/affinity?min_shared=3&limit=50`
**When** the request is authenticated and the tenant is set
**Then** the response body matches the MCP tool response schema

**AC3: Empty result set is handled gracefully**
**Given** a tenant with no orders
**When** `get_product_affinity_map()` is called
**Then** the response is `{"pairs": [], "total": 0}`

**AC4: Tenant isolation is enforced**
**Given** tenant A has orders for product X and tenant B has orders for product Y
**When** an agent queries affinity for tenant A
**Then** tenant B's orders are not included in the computation

## Technical Notes

### File Locations (create these)

- `backend/domains/intelligence/__init__.py` — empty init, marks module
- `backend/domains/intelligence/schemas.py` — add `AffinityPair`, `ProductAffinityMap` Pydantic models
- `backend/domains/intelligence/service.py` — add `get_product_affinity_map()` async function
- `backend/domains/intelligence/routes.py` — add `GET /api/v1/intelligence/affinity` route
- `backend/domains/intelligence/mcp.py` — add `intelligence_product_affinity` tool
- `backend/app/mcp_auth.py` — add `TOOL_SCOPES` entry: `"intelligence_product_affinity": frozenset({"orders:read"})`
- `backend/app/mcp_server.py` — register `domains.intelligence.mcp` import
- `src/domain/intelligence/__init__.py` — empty init
- `src/domain/intelligence/types.ts` — add `AffinityPair`, `ProductAffinityMap` TypeScript interfaces
- `src/domain/intelligence/hooks/useIntelligence.ts` — add `useProductAffinity(minShared, limit)` hook
- `src/domain/intelligence/components/AffinityMatrix.tsx` — affinity table component

### Key Implementation Details

**Backend — service function:**

```python
async def get_product_affinity_map(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    min_shared: int = 2,
    limit: int = 50,
) -> ProductAffinityMap:
    """Compute Jaccard-based product affinity pairs from order co-occurrence.

    Query strategy (non-correlated subqueries):
      1. CTE orders_per_product: (product_id, customer_id, order_id) for confirmed orders
         — joins orders → order_lines → products, filtered by tenant_id and status.
      2. CTE pair_counts: self-join orders_per_product on customer_id (different product_id),
        GROUP BY product_a, product_b to get shared_customer_count, customer_count_a, customer_count_b, and optional shared_order_count.
      3. Filter: shared_customer_count >= min_shared.
      4. Compute overlap_pct = shared_customer_count / min(customer_count_a, customer_count_b) * 100.
      5. Compute affinity_score = shared_customer_count / (customer_count_a + customer_count_b - shared_customer_count).
      6. Join product names from products table.
      7. ORDER BY affinity_score DESC, LIMIT.
    """
```

**Co-occurrence query (SQLAlchemy):**

```python
# CTE: per-product, per-customer order presence
orders_per_product = (
    select(
        OrderLine.product_id,
        Order.customer_id,
        Order.id.label("order_id"),
    )
    .join(Order, OrderLine.order_id == Order.id)
    .where(
        Order.tenant_id == tenant_id,
        Order.status.in_(["confirmed", "shipped", "fulfilled"]),
    )
    .cte("orders_per_product")
)

# Self-join on same customer, different product
pair_counts = (
    select(
        op_a.product_id.label("product_a_id"),
        op_b.product_id.label("product_b_id"),
        func.count(func.distinct(op_a.customer_id)).label("shared_customer_count"),
        # total orders containing each product
    )
    .join(
        orders_per_product.op_a,
        orders_per_product.c.customer_id == op_b.c.customer_id,
    )
    .where(op_a.c.product_id != op_b.c.product_id)
    .group_by(op_a.c.product_id, op_b.c.product_id)
    .having(func.count(func.distinct(op_a.c.customer_id)) >= min_shared)
)
```

**Important:** Compute `customer_count_a` and `customer_count_b` as distinct customers who bought each product. `shared_order_count` may still be included as supporting evidence, but it is not part of the canonical Jaccard denominator.

**pitch_hint generation:**

```python
def _make_pitch_hint(name_a: str, name_b: str, score: float) -> str:
    if score >= 0.5:
        return f"Strong affinity — '{name_a}' and '{name_b}' are frequently bought together. Bundle pitch recommended."
    elif score >= 0.2:
        return f"Consider pitching '{name_b}' when customer buys '{name_a}'."
    else:
        return f"'{name_a}' customers occasionally also buy '{name_b}'."
```

**Frontend — TypeScript interfaces:**

```typescript
export interface AffinityPair {
  product_a_id: string;
  product_b_id: string;
  product_a_name: string;
  product_b_name: string;
  shared_customer_count: number;
  customer_count_a: number;
  customer_count_b: number;
  overlap_pct: number;       // 0–100, render as progress bar
  affinity_score: number;     // Jaccard 0–1, sort by this desc
  pitch_hint: string;
}

export interface ProductAffinityMap {
  pairs: AffinityPair[];
  total: number;
  min_shared: number;
  limit: number;
}
```

**Frontend — hook:**

```typescript
// In useIntelligence.ts
export function useProductAffinity(minShared = 2, limit = 50) {
  const [data, setData] = useState<ProductAffinityMap | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    fetch(`/api/v1/intelligence/affinity?min_shared=${minShared}&limit=${limit}`)
      .then(r => r.json())
      .then(d => { setData(d); setLoading(false); })
      .catch(e => { setError(e.message); setLoading(false); });
  }, [minShared, limit]);

  return { data, loading, error };
}
```

**AffinityMatrix.tsx table columns:**

| Column | Sortable | Render |
|---|---|---|
| Product A | yes (name) | text |
| Product B | yes (name) | text |
| Shared Customers | yes | number |
| Overlap % | yes | inline progress bar (0–100) |
| Affinity Score | yes (default) | number (3 decimals) |
| Pitch Hint | no | italic text |

Use `recharts` reference bar or custom CSS progress bar inside a `<td>`.

### Critical Warnings

- **Do NOT** compute affinity from product pairs in the **same order line** only — this misses cross-order co-purchase. Must use customer-level aggregation (a customer who bought A in Jan and B in Feb counts).
- **Do NOT** use `order_id` as the join key between A and B — use `customer_id`. Same customer, multiple orders = co-purchase.
- **Do NOT** include cancelled or pending orders in the computation — filter to `status IN ('confirmed', 'shipped', 'fulfilled')`.
- **Do NOT** return self-pairs (product_a_id == product_b_id).
- **Do NOT** return duplicate pairs (A,B) and (B,A) — enforce ordering (e.g., product_a_id < product_b_id by UUID string comparison) in the query.
- Use `Decimal` for any financial values; IDs as `uuid.UUID`.
- The Jaccard formula denominator `(customer_count_a + customer_count_b - shared_customer_count)` is the **union** of customers who ordered either product. When `shared_customer_count == customer_count_a == customer_count_b`, score = 1.0.
- For MCP tools: each tool creates its own `AsyncSessionLocal()` session. Do NOT accept a session parameter.
- For REST routes: use `tenant_id` from `get_current_user`, not `DEFAULT_TENANT_ID`.
- `ToolError` only accepts a string — encode structured errors as JSON strings: `raise ToolError(json.dumps({...}))`.

## Tasks / Subtasks

- [x] Task 1: Create `backend/domains/intelligence/` module (AC1, AC4)
  - [x] Create `__init__.py`
  - [x] Add `AffinityPair`, `ProductAffinityMap` Pydantic schemas to `schemas.py`
  - [x] Implement `get_product_affinity_map()` in `service.py` with Jaccard co-occurrence query
  - [x] Add `GET /api/v1/intelligence/affinity` route in `routes.py` with `min_shared` (default 2) and `limit` (default 50) query params
  - [x] Add `intelligence_product_affinity` MCP tool in `mcp.py`
  - [x] Register `domains.intelligence.mcp` in `backend/app/mcp_server.py`

- [x] Task 2: Add TOOL_SCOPES entry (AC1)
  - [x] Add `"intelligence_product_affinity": frozenset({"orders:read"})` to `TOOL_SCOPES` in `backend/app/mcp_auth.py`

- [x] Task 3: Create frontend types and hook (AC2)
  - [x] Create `src/domain/intelligence/__init__.py`
  - [x] Add `AffinityPair`, `ProductAffinityMap` to `types.ts`
  - [x] Add `useProductAffinity(minShared, limit)` to `hooks/useIntelligence.ts`

- [x] Task 4: Create AffinityMatrix component (AC2)
  - [x] Create `AffinityMatrix.tsx` with sortable table columns
  - [x] Render `overlap_pct` as inline progress bars
  - [x] Sort by `affinity_score` descending by default
  - [x] Handle loading and error states

- [x] Task 5: Register intelligence route (AC2)
  - [x] Add `INTELLIGENCE_ROUTE` to `src/lib/routes.ts`
  - [x] Wire up protected route in `src/App.tsx`

## Completion Notes

- Implemented the customer-level product affinity service, schemas, REST endpoint, MCP tool, TypeScript contract, API helper, hook, and sortable affinity table with inline overlap progress bars.
- The review cycle closed two contract defects: intelligence MCP tools now require explicit tenant context (`X-Tenant-ID` or a Bearer token with `tenant_id`), and the human read surface is available to sales in line with the story acceptance criteria.
- Validation: `uv run pytest tests/domains/intelligence/test_service.py tests/domains/intelligence/test_routes.py tests/test_mcp_intelligence.py tests/test_mcp_auth.py -q`, `pnpm --dir /Volumes/2T_SSD_App/Projects/UltrERP exec vitest run src/tests/auth/rbac-ui.test.tsx src/tests/intelligence/AffinityMatrix.test.tsx`.

## Dev Notes

### Repo Reality

- Service functions use `async def fn(session: AsyncSession, tenant_id: uuid.UUID, *, ...)` + `async with session.begin(): await set_tenant(session, tid)`
- MCP tools: `@mcp.tool(annotations={"readOnlyHint": True})` + `raise ToolError(json.dumps({...}))` + `AsyncSessionLocal()` session management
- Pydantic schemas: `BaseModel` with `ConfigDict(from_attributes=True)` for responses
- TOOL_SCOPES: `dict[str, frozenset[str]]` in `backend/app/mcp_auth.py`
- MCP registration: import domain mcp module at bottom of `backend/app/mcp_server.py`
- Frontend: `SectionCard`/`PageHeader` from `src/components/layout/PageLayout.tsx`, recharts for charts
- Existing tables: `orders`, `order_lines`, `products`, `customers` — all have `tenant_id` and `status` columns

### References

- `backend/domains/inventory/mcp.py` — MCP tool pattern (use this as copy-paste template)
- `backend/domains/dashboard/routes.py` — REST route pattern with `get_current_user` + tenant_id extraction
- `backend/app/mcp_auth.py:24` — `TOOL_SCOPES` dict structure
- `backend/app/mcp_server.py:24` — domain MCP registration pattern
- `src/domain/dashboard/types.ts` — TypeScript interface pattern
- `backend/domains/customers/service.py` — service function pattern with `set_tenant` inside `session.begin()`
- Epic 19 spec: `epic-19.md` lines 27–59
- INTEL-001 from epics.md coverage map

## Story Dependencies

- Prerequisite: Story 19.7 for access wiring and shared intelligence module scaffolding
- Depends on: no additional upstream story once the customer-level affinity contract in this brief is fixed
- Enables: Story 19.5 (Prospect Gap Analysis uses affinity as one transparent scoring input)
