# Story 19.9: Prospect Gap Customer Type Filter

Status: done

## Story

As an **AI agent or sales staff**,
I want the Prospect Gap Analysis to only surface dealer/distributor customers
So that cross-sell scoring is meaningful (dealers stock multiple categories) and not polluted by end-user customers for whom belt cross-sell is irrelevant.

## Problem Statement

The Prospect Gap Analysis (Story 19.5) currently treats all customers uniformly. For the belt industry:
- **Dealers/distributors** stock multiple product categories — cross-sell scoring IS meaningful for them
- **End-user/industrial customers** buy specific belts for specific machines — cross-sell scoring is NOT meaningful

The feature returns empty or useless results because the algorithm scores end-users against dealer baselines. Additionally, there is no mechanism for AI research agents to write customer classifications back, and no per-feature toggles to disable intelligence widgets tenants don't use.

## Solution

1. **Add `customer_type` column** (`dealer | end_user | unknown`) to `Customer` with a migration. All existing customers default to `unknown`.
2. **Import pipeline** passes `customer_type` through canonical import; validation report tracks distribution.
3. **Prospect Gap** filters by `customer_type = "dealer"` by default; REST and MCP surfaces accept a `customer_type` param.
4. **Feature-level toggles** — five boolean flags in `common/config.py` gate each intelligence widget independently.
5. **MCP write tool** `customers_update(customer_id, customer_type)` lets AI agents write classifications; tenant isolation bug in the customers MCP domain is also fixed.

---

## R1: Add `customer_type` Field to Customer Model

**File:** `backend/domains/customers/models.py`

Add after `status` field (line 36):
```python
customer_type: Mapped[str] = mapped_column(String(20), nullable=False, default="unknown")
```

Valid values:
- `dealer` — distributor/reseller who stocks multiple categories
- `end_user` — industrial customer buying for internal use
- `unknown` — not yet classified (sentinel value for all legacy data)

**File:** `backend/domains/customers/schemas.py`

Add to `CustomerCreate` and `CustomerUpdate` Pydantic models:
```python
customer_type: Literal["dealer", "end_user", "unknown"] = "unknown"
```

Also add to `Customer` response schema if present.

---

## R2: Migration

**File:** `migrations/versions/<new_revision>.py`

Use existing migration tooling pattern. Add column:
```python
op.add_column(
    "customers",
    sa.Column("customer_type", sa.String(20), nullable=False, server_default="unknown")
)
```

All existing customers get `unknown`. No data backfill — `unknown` is the intentional sentinel meaning "not yet classified."

---

## R3: Import Pipeline — Classify `customer_type`

**File:** `backend/domains/legacy_import/normalization.py`

In `normalize_party_record`, add `customer_type` to the normalized output dict. Since the legacy `tbscust` table has no explicit dealer/end-user signal in v1, default to `"unknown"`:
```python
normalized["customer_type"] = "unknown"  # No legacy signal in tbscust v1
```

**File:** `backend/domains/legacy_import/canonical.py`

In `_import_customers`, include `customer_type` in the upsert dict:
```python
{
    "customer_type": row.get("customer_type", "unknown"),
    ...
}
```

**File:** `backend/domains/legacy_import/validation.py`

In the validation report, add a section counting `customer_type` distribution:
```python
customer_type_counts = db.session.execute(
    select(Customer.customer_type, func.count(Customer.id))
    .group_by(Customer.customer_type)
)
# Add to report
```

---

## R4: Prospect Gap Filters by `customer_type = "dealer"`

**File:** `backend/domains/intelligence/service.py`

In `get_prospect_gaps` (around line 897):
```python
async def get_prospect_gaps(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    category: str,
    limit: int = 20,
    customer_type: str = "dealer",  # NEW
) -> ProspectGaps:
```

In the customer summary query (`.join(Order, ...).where(...)`), add:
```python
.where(Customer.customer_type == customer_type)
```

This filter is applied when building `customer_metrics` and `existing_buyers`, so both the prospect list and the `existing_buyers_count` badge reflect only the selected customer type.

**File:** `backend/domains/intelligence/routes.py`

In `prospect_gaps` route (around line 48):
```python
@router.get("/prospect-gaps", response_model=ProspectGaps)
async def prospect_gaps(
    ...
    customer_type: str = Query(default="dealer", pattern="^(dealer|end_user|unknown)$"),
) -> ProspectGaps:
```

Pass through:
```python
return await get_prospect_gaps(session, tenant_id, category=category.strip(), limit=limit, customer_type=customer_type)
```

**File:** `backend/domains/intelligence/mcp.py`

In `intelligence_prospect_gaps` (around line 145):
```python
async def intelligence_prospect_gaps(
    category: Annotated[str, Field(description="Target category name")],
    limit: Annotated[int, Field(description="...", ge=1, le=100)] = 20,
    customer_type: Annotated[str, Field(description="dealer | end_user | unknown", pattern="^(dealer|end_user|unknown)$")] = "dealer",
) -> dict:
```

Pass through to `get_prospect_gaps`.

**File:** `src/domain/intelligence/components/ProspectGapTable.tsx`

Update the component to accept and pass the `customer_type` filter. Add a filter chip group (Dealers / End Users / All) above the table. Default to "Dealers". The existing `useProspectGaps` hook should accept `customerType` as a third param.

**File:** `src/domain/intelligence/hooks/useIntelligence.ts`

Update `useProspectGaps` signature:
```typescript
export function useProspectGaps(category: string, customerType: string = "dealer", limit = 20)
```

---

## R5: Feature-Level Intelligence Toggles

**File:** `backend/common/config.py`

Add five toggle fields after `egui_tracking_enabled` (around line 312). Use the same boolean pattern:
```python
intelligence_prospect_gaps_enabled: bool = True
intelligence_product_affinity_enabled: bool = True
intelligence_category_trends_enabled: bool = True
intelligence_customer_risk_signals_enabled: bool = True
intelligence_market_opportunities_enabled: bool = True
```

**File:** `backend/domains/intelligence/routes.py`

Add a helper or decorator. For each route, check the toggle:
```python
@router.get("/prospect-gaps", response_model=ProspectGaps)
async def prospect_gaps(...):
    if not settings.intelligence_prospect_gaps_enabled:
        raise HTTPException(status_code=403, detail="Prospect gap analysis is disabled")
    ...
```

Repeat for each of the 5 endpoints.

**File:** `backend/domains/intelligence/mcp.py`

At the top of each `@mcp.tool()` function body, add the check:
```python
if not settings.intelligence_prospect_gaps_enabled:
    raise ToolError("Prospect gap analysis is disabled")
```

Repeat for each of the 5 tools.

---

## R6: MCP Write Tool for AI Agent Classification

**File:** `backend/domains/customers/mcp.py`

Add `customers_update` tool. Import `CustomerUpdate` from schemas. Use `_resolve_tenant_id()` for tenant resolution (NOT `DEFAULT_TENANT_ID`). The tool:

```python
@mcp.tool()
async def customers_update(
    customer_id: Annotated[str, Field(description="Customer UUID")],
    customer_type: Annotated[str, Field(description="dealer | end_user | unknown")],
) -> dict:
    """Update a customer's type classification."""
    valid_types = {"dealer", "end_user", "unknown"}
    if customer_type not in valid_types:
        raise ToolError(f"customer_type must be one of: {valid_types}")

    tenant_id = _resolve_tenant_id()
    try:
        cid = uuid.UUID(customer_id)
    except ValueError:
        raise ToolError("Invalid customer_id format")

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Customer).where(Customer.id == cid, Customer.tenant_id == tenant_id)
        )
        customer = result.scalar_one_or_none()
        if not customer:
            raise ToolError("Customer not found")

        customer.customer_type = customer_type
        await session.commit()

    return {"success": True, "customer_id": customer_id, "customer_type": customer_type}
```

Also fix the existing customers MCP tools to use `_resolve_tenant_id()` instead of `DEFAULT_TENANT_ID` for consistency:
- `customers_list` — line ~101
- `customers_get` — line ~119
- `customers_lookup_by_ban` — line ~161

**File:** `backend/app/mcp_auth.py`

Add to `TOOL_SCOPES` dict:
```python
"customers_update": ["customers:write"],
```

Existing read tools keep `customers:read`.

---

## Dev Notes

- `customer_type` defaults to `"unknown"` for ALL legacy customers — this is intentional. AI agents via `customers_update` will classify them.
- The `existing_buyers_count` in `ProspectGaps` must also be filtered by `customer_type` — only count dealers who bought the target category as "existing buyers."
- The feature toggle defaults to `True` for all 5 widgets — preserves existing behavior when the flag is not set.
- Tenant isolation fix in Step R6 is HIGH PRIORITY — the customers MCP currently ignores auth headers and hard-codes a default tenant, which is a security bug.
- `unknown` customers should be excluded from Prospect Gap scoring by default (the `customer_type = "dealer"` default handles this), but the API allows `unknown` to be queried explicitly if needed.

---

## Tasks / Subtasks

- [x] **R1** — Add `customer_type` to Customer model + schemas
    - [x] Add field to `backend/domains/customers/models.py`
    - [x] Add to `CustomerCreate`/`CustomerUpdate` in `backend/domains/customers/schemas.py`
    - [x] Add to response schema if present
- [x] **R2** — Create migration for `customer_type` column
    - [x] Generate alembic revision
    - [x] Verify server_default="unknown"
- [x] **R3** — Import pipeline classifies `customer_type`
    - [x] `normalize_party_record` emits `customer_type: "unknown"`
    - [x] `_import_customers` passes `customer_type` through upsert
    - [x] Validation report tracks `customer_type` distribution
- [x] **R4** — Prospect Gap filters by `customer_type`
    - [x] `get_prospect_gaps` adds `customer_type` param + filter in query
    - [x] REST route accepts `customer_type` query param
    - [x] MCP tool accepts `customer_type` param
    - [x] Frontend adds filter chip group (Dealers / End Users / All)
    - [x] `useProspectGaps` hook accepts `customerType`
- [x] **R5** — Feature-level toggles
    - [x] Add 5 toggle fields to `common/config.py`
    - [x] Gate REST routes with 403 when disabled
    - [x] Gate MCP tools with `ToolError` when disabled
- [x] **R6** — MCP write tool + tenant isolation fix
    - [x] Add `customers_update` tool to `domains/customers/mcp.py`
    - [x] Fix `DEFAULT_TENANT_ID` → `_resolve_tenant_id()` in existing customer tools
    - [x] Add `customers_update` to `TOOL_SCOPES` with `customers:write`
- [x] **Tests**
    - [x] Add `test_customer_type_filter` to `test_service.py`
    - [x] Add `test_customers_update` to relevant MCP test file
    - [x] Add feature toggle tests for each gated endpoint

### Review Findings

- [x] [Review][Patch] Prospect-gap scoring still mixes customer types in target-category revenue and adjacency inputs [backend/domains/intelligence/service.py:931] — fixed by applying the selected cohort to category presence, target-category revenue, and adjacency calculations.
- [x] [Review][Patch] Canonical import reads `customer_type` during upsert but never selects it from normalized parties [backend/domains/legacy_import/canonical.py:657] — fixed by selecting `customer_type` in `_iter_normalized_parties` and adding a focused regression test.
- [x] [Review][Patch] `customers_update` can leak raw optimistic-lock or validation exceptions instead of structured MCP errors [backend/domains/customers/mcp.py:178] — fixed by translating version-conflict and validation failures into structured `ToolError` payloads.
- [x] [Review][Defer] Validation flags expected `excluded_path` category rows as provisional assignments [backend/domains/legacy_import/validation.py:291] — deferred, pre-existing

---

## Acceptance Criteria

**AC1: Migration**
**Given** existing customer records in the database
**When** the migration runs
**Then** `customer_type` is set to `"unknown"` for all existing customers
**And** no data is lost or modified

**AC2: Prospect Gap — dealer filter**
**Given** a mix of dealer and end-user customers, with some dealers having purchased from category "Supplies"
**When** `GET /api/v1/intelligence/prospect-gaps?category=Supplies` is called with default params
**Then** only customers with `customer_type = "dealer"` appear in the prospects list
**And** `existing_buyers_count` reflects only dealer buyers of "Supplies"

**AC3: Prospect Gap — end_user filter**
**Given** `customer_type=end_user` is passed
**When** the endpoint is called
**Then** only end-user customers appear in prospects
**And** dealer customers are excluded

**AC4: Feature toggle — REST**
**Given** `INTELLIGENCE_PROSPECT_GAPS_ENABLED=false` is set
**When** `GET /api/v1/intelligence/prospect-gaps` is called
**Then** a 403 response is returned

**AC5: Feature toggle — MCP**
**Given** `intelligence_category_trends_enabled=false`
**When** the `intelligence_category_trends` MCP tool is called
**Then** a `ToolError` is raised with "disabled" message

**AC6: MCP write — customers_update**
**Given** an AI agent with `customers:write` scope
**When** `customers_update(customer_id=<uuid>, customer_type="dealer")` is called
**Then** the customer's `customer_type` is updated immediately
**And** the response is `{"success": True, "customer_id": ..., "customer_type": "dealer"}`

**AC7: Tenant isolation**
**Given** agent with `X-Tenant-ID: tenant-A` calls `customers_update` on a customer belonging to `tenant-B`
**When** the call is made
**Then** a 403 or `ToolError` is raised
**And** tenant-B's data is not modified

**AC8: Tenant isolation — existing tools fixed**
**Given** the tenant isolation fix is applied
**When** `customers_list`, `customers_get`, or `customers_lookup_by_ban` are called
**Then** they use `_resolve_tenant_id()` and respect the caller's tenant

---

## References

- Customer model: `backend/domains/customers/models.py`
- Customer schemas: `backend/domains/customers/schemas.py`
- Prospect gaps service: `backend/domains/intelligence/service.py` — `get_prospect_gaps` at line 897
- Prospect gaps REST route: `backend/domains/intelligence/routes.py` — `prospect_gaps` at line 48
- Prospect gaps MCP tool: `backend/domains/intelligence/mcp.py` — `intelligence_prospect_gaps` at line 145
- Feature gate pattern: `common/config.py` — `egui_tracking_enabled` at line 312
- Customers MCP: `backend/domains/customers/mcp.py`
- MCP auth scopes: `backend/app/mcp_auth.py` — `TOOL_SCOPES` at line 25
- Import canonical: `backend/domains/legacy_import/canonical.py` — `_import_customers`
- Import normalization: `backend/domains/legacy_import/normalization.py` — `normalize_party_record`
- Import validation: `backend/domains/legacy_import/validation.py`
- Frontend hook: `src/domain/intelligence/hooks/useIntelligence.ts` — `useProspectGaps`
- Frontend component: `src/domain/intelligence/components/ProspectGapTable.tsx`
- Epic 19: `_bmad-output/planning-artifacts/epic-19.md`
- Sprint status: `_bmad-output/implementation-artifacts/sprint-status.yaml`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Completion Notes List

- Added `customer_type` to the customer model, schemas, service write paths, and a dedicated Alembic migration with `server_default="unknown"` so existing rows upgrade safely.
- Threaded `customer_type` through legacy normalization, canonical import, and validation reporting; canonical customer upserts now preserve an existing non-`unknown` classification on replay instead of overwriting it with raw legacy defaults.
- Fixed the customers MCP tenant-isolation bug by centralizing tenant/header resolution in `backend/app/mcp_identity.py`, updating existing customer read tools to honor caller tenant context, and adding `customers_update(customer_id, customer_type)` behind `customers:write` scope.
- Added per-widget intelligence feature gates in config, REST routes, and MCP tools, and extended prospect-gap filtering to support `dealer` by default plus `end_user`, `unknown`, and read-time `all` for the new frontend chip group.
- Updated the prospect-gap UI to expose Dealers / End Users / All chips, pass the filter through the API hook, and localize the new control labels in English and Traditional Chinese.
- Focused validation passed with `uv run pytest -q tests/domains/intelligence/test_service.py tests/domains/intelligence/test_routes.py tests/test_mcp_intelligence.py tests/test_mcp_customers.py tests/test_mcp_auth.py tests/api/test_create_customer.py tests/api/test_update_customer.py tests/domains/legacy_import/test_normalization.py tests/domains/legacy_import/test_canonical.py tests/domains/legacy_import/test_validation.py` (`164 passed`) and `pnpm exec vitest run src/tests/intelligence/ProspectGapTable.test.tsx` (`5 passed`).
- BMAD code review found three actionable issues; all were fixed by tightening prospect-gap cohort math, selecting `customer_type` from normalized parties during canonical import, and converting `customers_update` service conflicts into structured MCP errors. Post-review focused backend validation passed with `uv run pytest -q tests/domains/intelligence/test_service.py tests/domains/intelligence/test_routes.py tests/test_mcp_intelligence.py tests/domains/legacy_import/test_canonical.py tests/test_mcp_customers.py` (`95 passed`).

### File List

- backend/app/mcp_auth.py
- backend/app/mcp_identity.py
- backend/common/config.py
- backend/domains/customers/mcp.py
- backend/domains/customers/models.py
- backend/domains/customers/schemas.py
- backend/domains/customers/service.py
- backend/domains/intelligence/mcp.py
- backend/domains/intelligence/routes.py
- backend/domains/intelligence/service.py
- backend/domains/legacy_import/canonical.py
- backend/domains/legacy_import/normalization.py
- backend/domains/legacy_import/validation.py
- backend/tests/api/test_create_customer.py
- backend/tests/api/test_update_customer.py
- backend/tests/domains/intelligence/test_routes.py
- backend/tests/domains/intelligence/test_service.py
- backend/tests/domains/legacy_import/test_canonical.py
- backend/tests/domains/legacy_import/test_normalization.py
- backend/tests/domains/legacy_import/test_validation.py
- backend/tests/test_mcp_auth.py
- backend/tests/test_mcp_customers.py
- backend/tests/test_mcp_intelligence.py
- migrations/versions/8d2f4c6b7a90_add_customer_type_to_customers.py
- public/locales/en/common.json
- public/locales/zh-Hant/common.json
- src/domain/intelligence/components/ProspectGapTable.tsx
- src/domain/intelligence/hooks/useIntelligence.ts
- src/domain/intelligence/types.ts
- src/lib/api/intelligence.ts
- src/tests/intelligence/ProspectGapTable.test.tsx

### Change Log

- 2026-04-15: Implemented Story 19.9 end-to-end across customer classification persistence, legacy import, intelligence feature gates, MCP write support, tenant-safe customer MCP reads, prospect-gap filtering, and the Dealers / End Users / All frontend control.
- 2026-04-15: Completed BMAD code-review remediation for Story 19.9, fixing prospect-gap cohort leakage, canonical import `customer_type` passthrough, and MCP update error translation; deferred one pre-existing validation-noise issue.
