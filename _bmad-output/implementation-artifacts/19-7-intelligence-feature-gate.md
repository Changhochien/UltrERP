# Story 19.7: Intelligence Feature Gate

Status: revised-ready-for-dev

## Story

As an **admin**,
I want to control access to the intelligence module
So that only authorized roles can see the data.

## Problem Statement

The intelligence module exposes sensitive aggregated data about customer purchasing behavior, category performance, and account health. Without an access gate, authenticated users and API clients could reach these routes and tools more broadly than intended. In the live repo, access control is split across the frontend role-to-feature matrix, backend role-based route dependencies, and MCP scope enforcement. This story aligns those three layers for the new intelligence surfaces.

## Solution

Add `intelligence` as a first-class frontend feature in the existing `requiredFeature` guard system used throughout `App.tsx`. Wire the 6 new intelligence MCP tools into `TOOL_SCOPES` and `mcp_server.py`. For REST routes, use the existing `require_role(...)` pattern to define an intelligence-specific read dependency instead of inventing a backend feature registry.

## Best-Practice Update

This section supersedes conflicting details below.

- Align the gate to the repo as it exists today: frontend access is role-to-feature mapping, REST access is existing role-based auth, and MCP access is scope-based.
- Do not assume a backend `user.features` or dynamic per-feature flag system already exists.
- Do not create stub MCP tools or empty REST endpoints just to satisfy the gate story. Wire scopes, routes, and navigation only for concrete surfaces that actually ship.
- Add the new `intelligence` frontend feature to the existing role matrix and navigation surfaces, and pair that with backend role / scope checks.
- If the product wants a clearer access-denied experience than the current redirect behavior, specify that UI explicitly rather than treating it as free fallout from route protection.

## Acceptance Criteria

**AC1: Unauthenticated REST access is blocked**
**Given** a request to `GET /api/v1/intelligence/affinity` without authentication
**When** the request hits the route
**Then** a 401 response is returned with `{"detail": "Not authenticated"}`

**AC2: Unauthorized user REST access is blocked**
**Given** a user authenticated via session/JWT whose role does not satisfy the intelligence route dependency
**When** the user calls `GET /api/v1/intelligence/affinity`
**Then** a 403 response is returned by the existing role-based auth mechanism

**AC3: Authorized user REST access succeeds**
**Given** a user authenticated via session/JWT whose role satisfies the intelligence route dependency
**When** the user calls `GET /api/v1/intelligence/affinity`
**Then** the response is 200 with the affinity data

**AC4: MCP tool without API key is rejected**
**Given** an MCP request to `intelligence_product_affinity` without an `X-API-Key` header
**When** the request hits `ApiKeyAuth` middleware
**Then** a `ToolError` is raised with `{"code": "AUTH_REQUIRED", ...}`

**AC5: MCP tool with insufficient scope is rejected**
**Given** an MCP API key that has scope `orders:read` but NOT `customers:read`
**When** the agent calls `intelligence_category_trends` (which requires both)
**Then** a `ToolError` is raised with `{"code": "INSUFFICIENT_SCOPE", ...}`

**AC6: MCP tool with valid key and scope succeeds**
**Given** an MCP API key with scope `orders:read` and `customers:read`
**When** the agent calls `intelligence_category_trends`
**Then** the tool executes normally and returns the category trends data

**AC7: Sidebar hides Intelligence nav for unauthorized users**
**Given** a user authenticated via session whose frontend role matrix does NOT grant `intelligence`
**When** the sidebar is rendered
**Then** the "Intelligence" navigation item is not shown in the sidebar

**AC8: Sidebar shows Intelligence nav for authorized users**
**Given** a user authenticated via session whose frontend role matrix grants `intelligence`
**When** the sidebar is rendered
**Then** the "Intelligence" navigation item is shown in the sidebar and links to `/intelligence`

## Technical Notes

### File Locations (create these)

**Backend:**
- `backend/domains/intelligence/__init__.py` — package init (empty or exposes shared helpers)
- `backend/domains/intelligence/routes.py` — shared router / dependency surface for concrete intelligence endpoints added by companion stories
- `backend/domains/intelligence/mcp.py` — FastMCP tool definitions for concrete intelligence tools that actually ship
- `backend/app/mcp_auth.py` — add 6 `TOOL_SCOPES` entries
- `backend/app/mcp_server.py` — register `domains.intelligence.mcp`
- backend route registration surface — include the intelligence router alongside other concrete domain routers

**Frontend:**
- `src/lib/routes.ts` — add `INTELLIGENCE_ROUTE = "/intelligence"`
- `src/hooks/usePermissions.ts` — add `intelligence` to `AppFeature` and the role-permission matrix
- `src/App.tsx` — add protected route for `INTELLIGENCE_ROUTE` with `requiredFeature="intelligence"`
- `src/pages/IntelligencePage.tsx` — entry page (can be stubbed for now, composes workbench tabs)

### Key Implementation Details

**`TOOL_SCOPES` entries** (add to `backend/app/mcp_auth.py`):
```python
# intelligence domain (Story 19.7)
"intelligence_product_affinity": frozenset({"orders:read"}),
"intelligence_category_trends": frozenset({"orders:read", "customers:read"}),
"intelligence_customer_product_profile": frozenset({"customers:read", "orders:read"}),
"intelligence_customer_risk_signals": frozenset({"customers:read", "orders:read"}),
"intelligence_prospect_gaps": frozenset({"customers:read", "orders:read"}),
"intelligence_market_opportunities": frozenset({"customers:read", "orders:read"}),
```

**`mcp_server.py` registration** (add to bottom of file, after existing domain imports):
```python
import domains.intelligence.mcp  # noqa: E402, F401
```

**`routes.ts` constant**:
```typescript
export const INTELLIGENCE_ROUTE = "/intelligence";
```

**`App.tsx` route** (add after `OWNER_DASHBOARD_ROUTE` block, before `SETTINGS_ROUTE`):
```tsx
<Route
  path={INTELLIGENCE_ROUTE}
  element={
    <ProtectedAppRoute requiredFeature="intelligence">
      <RoutedPage>
        <IntelligencePage />
      </RoutedPage>
    </ProtectedAppRoute>
  }
/>
```

**Feature gate pattern** — align with the current repo. Add `intelligence` to the frontend `AppFeature` union and role matrix, then pair that with existing backend role checks for REST routes. Do not assume a backend `user.features` registry already exists.

**REST route dependency pattern** — use the same `require_role(...)` approach already used in existing route files, but define the intelligence read roles explicitly for this domain. Example:
```python
from typing import Annotated

from fastapi import Depends
from common.auth import require_role

router = APIRouter()
IntelligenceReadUser = Annotated[dict, Depends(require_role("admin", "owner", "sales"))]

@router.get("/affinity")
async def get_affinity(
    session: AsyncSession,
  user: IntelligenceReadUser,
):
  tenant_id = uuid.UUID(user["tenant_id"])
    ...
```

### Intelligence MCP Tool Signatures

Only add MCP tool functions for concrete services that land in the same change. Do not ship placeholder tools that raise `NotImplementedError`.

```python
@mcp.tool(annotations={"readOnlyHint": True})
async def intelligence_product_affinity(
    min_shared: int = 3,
    limit: int = 50,
) -> str:
    """Return top product affinity pairs (Jaccard co-purchase score)."""
    async with AsyncSessionLocal() as session:
        tenant_id = await _resolve_tenant()
        async with session.begin():
            result = await get_product_affinity_map(
                session, tenant_id, min_shared=min_shared, limit=limit
            )
        return json.dumps(result, default=str)
```

Use `raise ToolError(json.dumps({...}))` for all error cases and `model_dump(mode="json")` for responses, consistent with the existing MCP pattern in `domains/inventory/mcp.py`.

### Critical Warnings

- Do **not** hard-code the feature check to always pass during development — the gate must be enforceable in all environments
- Do **not** grant `intelligence` scope by default to all roles — only to `admin` and `owner` roles initially, with explicit grant to `agent` (AI) role via API key scopes
- Avoid placeholder tools that call missing services. Scope wiring can land before the full UI, but machine-facing tools should only exist once their service contracts are real.
- The feature gate is a **prerequisite gate** — all stories 19.1–19.6 depend on this story being merged first (enables means 19.1–19.6)

## Tasks / Subtasks

- [ ] **Task 1: Add intelligence MCP tool scopes** (AC4, AC5, AC6)
  - [ ] Add 6 `TOOL_SCOPES` entries in `backend/app/mcp_auth.py`
  - [ ] Add `domains/intelligence.mcp` import to `backend/app/mcp_server.py`

- [ ] **Task 2: Prepare intelligence module wiring for concrete tools** (AC4, AC5, AC6)
  - [ ] Create `backend/domains/intelligence/__init__.py`
  - [ ] Create `backend/domains/intelligence/mcp.py` only for real tool implementations that ship with the first intelligence stories

- [ ] **Task 3: Add shared route protection for concrete intelligence endpoints** (AC1, AC2, AC3)
  - [ ] Create `backend/domains/intelligence/routes.py` with shared router helpers or concrete endpoints that actually ship in the same change
  - [ ] Apply an intelligence-specific `require_role(...)` dependency to intelligence routes
  - [ ] Enforce the frontend / backend `intelligence` access contract without inventing a new backend feature registry
  - [ ] Wire the intelligence router into the main FastAPI app once at least one concrete endpoint exists

- [ ] **Task 4: Frontend route and navigation** (AC7, AC8)
  - [ ] Add `INTELLIGENCE_ROUTE = "/intelligence"` to `src/lib/routes.ts`
  - [ ] Add `INTELLIGENCE_ROUTE` to the `AppRoute` type union
  - [ ] Add protected route in `src/App.tsx` with `requiredFeature="intelligence"`
  - [ ] Create `src/pages/IntelligencePage.tsx` stub (simple page with title "Intelligence" — workbench tabs implemented in 19.1–19.6)
  - [ ] Verify sidebar hides/shows based on feature flag (check how `AppNavigation` component reads features)

- [ ] **Task 5: Frontend role matrix update** (AC2, AC7, AC8)
  - [ ] Add `intelligence` to the existing `AppFeature` union and role-permission matrix
  - [ ] Ensure the `intelligence` feature is granted intentionally to the appropriate roles

- [ ] **Task 6: Wire intelligence router into FastAPI app** (AC1, AC2, AC3)
  - [ ] Find where domain routers are included in the FastAPI app (e.g., `backend/app/routes.py` or `backend/app/__init__.py`)
  - [ ] Add `router = APIRouter(prefix="/intelligence", tags=["intelligence"])` and include it in the app

## Dev Notes

### Repo Reality

- `TOOL_SCOPES` dict lives in `backend/app/mcp_auth.py` and already has entries for 6 domains: inventory, orders, customers, invoices, purchases, payments
- `mcp_server.py` bottom section registers domain MCP modules with `# noqa: E402, F401` imports
- `App.tsx` uses `ProtectedAppRoute(requiredFeature="...")` for all protected pages — pattern is consistent
- `ProtectedRoute` component (in `src/components/ProtectedRoute.tsx`) wraps `RequireRole` or similar — read it to understand how `requiredFeature` is checked
- Route files define local read aliases via `require_role(...)` in each domain — follow that pattern for intelligence rather than inventing a backend feature registry
- Frontend access is currently controlled through the role-to-feature matrix and `requiredFeature` checks rather than a backend-managed `user.features` field
- The `domains/intelligence/` directory does not exist yet — this story creates the module skeleton

### References

- `backend/app/mcp_auth.py:24` — `TOOL_SCOPES` dict structure (line 24 onwards)
- `backend/app/mcp_server.py:25–30` — domain MCP registration pattern
- `src/App.tsx:149–165` — `ProtectedAppRoute` component and usage pattern
- `src/App.tsx:167–342` — all route definitions for reference
- `src/lib/routes.ts:1–46` — route constants and `AppRoute` union type
- `domains/inventory/routes.py` — example of a route-level `require_role(...)` alias pattern
- `domains/inventory/mcp.py` — MCP tool pattern with `ToolError` and `AsyncSessionLocal`
- `src/components/ProtectedRoute.tsx` — frontend feature gate implementation

## Story Dependencies

- Prerequisite: None (this story is self-contained for the gate)
- Depends on: None (other stories 19.1–19.6 can be implemented in parallel after this)
- Enables: Stories 19.1, 19.2, 19.3, 19.4, 19.5, 19.6 (all intelligence stories require the feature gate in place)
