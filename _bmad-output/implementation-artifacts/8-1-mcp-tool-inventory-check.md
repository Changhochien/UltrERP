# Story 8.1: MCP Tool — Inventory Check

Status: complete

## Story

As an AI agent,
I want to check inventory levels via MCP tools,
So that I can answer questions about stock.

## Acceptance Criteria

**AC1:** `inventory_check` tool returns stock levels
**Given** I'm an AI agent with MCP access and `inventory:read` scope
**When** I call `inventory_check` with a `product_id`
**Then** I receive: product name, current stock per warehouse, reorder point, last adjusted, status
**And** response time is < 1 second (p95) (NFR4)

**AC2:** `inventory_search` tool finds products
**Given** I'm an AI agent with MCP access and `inventory:read` scope
**When** I call `inventory_search` with a query string (SKU, code, or name)
**Then** I receive a list of matching products with `id`, `code`, `name`, `category`, `status`, `current_stock`
**And** the search uses the existing hybrid search (exact → prefix → trigram → full-text)

**AC3:** `inventory_reorder_alerts` tool lists low-stock items
**Given** I'm an AI agent with MCP access and `inventory:read` scope
**When** I call `inventory_reorder_alerts`
**Then** I receive a list of active reorder alerts with product name, warehouse, current stock, reorder point, status
**And** results are filterable by `status` and `warehouse_id`

**AC4:** Product not found returns structured error
**Given** I call `inventory_check` with a non-existent `product_id`
**When** the service returns `None`
**Then** the tool raises `ToolError` with a JSON-encoded `NotFoundError`
**And** `entity_type` is `"product"` and `entity_id` is the provided ID

**AC5:** Tenant scoping enforced
**Given** the MCP server is running
**When** any inventory tool is called
**Then** all queries are scoped to `DEFAULT_TENANT_ID`
**And** RLS is enforced via `set_tenant(session, tenant_id)`

**AC6:** Backend tests pass
**Given** all existing tests
**When** I run `cd backend && python -m pytest tests/ -v --tb=short`
**Then** all existing tests continue to pass
**And** inventory MCP tool tests are added (≥ 6 tests)

## Tasks / Subtasks

- [ ] **Task 1: Create inventory MCP tools module** (AC1, AC2, AC3, AC4, AC5)
  - [ ] Create `backend/domains/inventory/mcp.py`:
    ```python
    """
    MCP tools for the Inventory domain.

    Tools:
      - inventory_check: Check stock levels for a specific product
      - inventory_search: Search products by code, name, or SKU
      - inventory_reorder_alerts: List low-stock reorder alerts
    """
    from __future__ import annotations
    import uuid
    import json
    from typing import Annotated
    from pydantic import Field
    from fastmcp.exceptions import ToolError

    from app.mcp_server import mcp
    from common.database import AsyncSessionLocal
    from common.tenant import set_tenant, DEFAULT_TENANT_ID
    from domains.inventory.services import (
        get_product_detail,
        search_products,
        list_reorder_alerts,
    )

    @mcp.tool()
    async def inventory_check(
        product_id: Annotated[str, Field(description="UUID of the product to check")],
    ) -> dict:
        """Check inventory stock levels for a specific product across all warehouses."""
        pid = uuid.UUID(product_id)
        async with AsyncSessionLocal() as session:
            await set_tenant(session, DEFAULT_TENANT_ID)
            result = await get_product_detail(session, DEFAULT_TENANT_ID, pid)
            if result is None:
                raise ToolError(json.dumps({
                    "code": "NOT_FOUND",
                    "entity_type": "product",
                    "entity_id": product_id,
                    "message": f"Product {product_id} not found",
                    "retry": False,
                }))
            return result

    @mcp.tool()
    async def inventory_search(
        query: Annotated[str, Field(description="Search text: product code, name, or SKU")],
        limit: Annotated[int, Field(description="Max results", default=20)] = 20,
    ) -> list[dict]:
        """Search products by code, name, or SKU using hybrid matching."""
        async with AsyncSessionLocal() as session:
            await set_tenant(session, DEFAULT_TENANT_ID)
            return await search_products(session, DEFAULT_TENANT_ID, query, limit=limit)

    @mcp.tool()
    async def inventory_reorder_alerts(
        status_filter: Annotated[str | None, Field(description="Filter: PENDING, ACKNOWLEDGED, RESOLVED")] = None,
        warehouse_id: Annotated[str | None, Field(description="Filter by warehouse UUID")] = None,
    ) -> dict:
        """List products below their reorder point (low stock alerts)."""
        wid = uuid.UUID(warehouse_id) if warehouse_id else None
        async with AsyncSessionLocal() as session:
            await set_tenant(session, DEFAULT_TENANT_ID)
            alerts, total = await list_reorder_alerts(
                session, DEFAULT_TENANT_ID,
                status_filter=status_filter,
                warehouse_id=wid,
            )
            return {"alerts": alerts, "total": total}
    ```
  - [ ] Ensure tool names match `TOOL_SCOPES` in `backend/app/mcp_auth.py` (Story 8.4)

- [ ] **Task 2: Register inventory tools** (AC1)
  - [ ] Import `backend/domains/inventory/mcp` in `backend/app/mcp_server.py` so decorators register:
    ```python
    import domains.inventory.mcp  # noqa: F401 — registers MCP tools
    ```

- [ ] **Task 3: Create inventory MCP tests** (AC1, AC2, AC3, AC4, AC6)
  - [ ] Create `backend/tests/test_mcp_inventory.py`:
    - Test: `inventory_check` returns product detail for valid product ID
    - Test: `inventory_check` raises ToolError for non-existent product
    - Test: `inventory_search` returns matching products
    - Test: `inventory_search` returns empty list for no matches
    - Test: `inventory_reorder_alerts` returns alerts list
    - Test: `inventory_reorder_alerts` with status filter
  - [ ] Use `AsyncSessionLocal` fixture and test DB
  - [ ] Run full test suite

## Dev Notes

### Architecture Compliance
- **§6.3:** Inventory tools: `inventory.check`, `inventory.adjust`, `inventory.reorder_report` — this story implements the read-only tools. `inventory.adjust` (write) is deferred.
- **§6.3 deviation:** `inventory_search` is an extension not listed in architecture §6.3. Justified by operational need (agents must find products before checking stock). `inventory_reorder_alerts` maps to architecture's `inventory.reorder_report` — name adjusted for clarity.
- **§4.3:** Tool naming uses `{domain}_{action}` flat convention (no dots in Python function names). Architecture shows `{domain}.{action}` but PoC uses underscores.
- **§2.1:** Tools wrap existing service functions — no new business logic. `get_product_detail`, `search_products`, `list_reorder_alerts` already exist.

### Critical Warnings
- ⚠️ Tool names must be valid Python identifiers (no dots). Use `inventory_check` not `inventory.check`. The architecture notation `inventory.check` is a logical name; the Python function is `inventory_check`.
- ⚠️ Each tool creates its own `AsyncSessionLocal()` session — do NOT accept a session parameter. MCP tool functions are called by the framework, not by route handlers.
- ⚠️ Inventory service functions (`get_product_detail`, `search_products`, `list_reorder_alerts`) do NOT use `session.begin()` internally, so the MCP tool must call `set_tenant()` before calling them. This differs from customer/invoice services — see Stories 8.2, 8.3 for the alternate pattern.
- ⚠️ Use `DEFAULT_TENANT_ID` for all queries until multi-tenant auth is implemented in Epic 11.
- ⚠️ `ToolError` only accepts a string. Encode structured errors as JSON strings.
- ⚠️ Return plain dicts from tools, not Pydantic models — FastMCP serializes tool returns as JSON.

### Project Structure Notes
- `backend/domains/inventory/mcp.py` — NEW: MCP tool definitions
- `backend/domains/inventory/services.py` — EXISTING (NOTE: plural `services.py`): wraps these service functions:
  - `get_product_detail(session, tenant_id, product_id, *, history_limit=100, history_offset=0)` → `dict | None`
  - `search_products(session, tenant_id, query, *, warehouse_id=None, limit=20)` → `list[dict]`
  - `list_reorder_alerts(session, tenant_id, *, status_filter=None, warehouse_id=None, limit=50, offset=0)` → `tuple[list[dict], int]`

### Previous Story Intelligence
- **Story 8.6:** Creates the MCP server (`backend/app/mcp_server.py`) — this story registers tools on it
- **Story 8.4:** Creates the auth middleware with `TOOL_SCOPES` — tool names here must match
- **PoC reference:** `research/multi-agent-patterns/02-poc/main.py` — tool pattern with `@mcp.tool()`, `Annotated` params
- **Service inventory:** `get_product_detail` returns `dict | None`; `search_products` returns `list[dict]`; `list_reorder_alerts` returns `tuple[list[dict], int]`
- **Import path:** File is `services.py` (plural), NOT `service.py` — use `from domains.inventory.services import ...`

### References
- Architecture v2 §4.3 (MCP Tools), §6.3 (Inventory tools)
- PRD: FR29 (inventory via MCP), NFR4 (< 1s p95)
- Backend service: `backend/domains/inventory/services.py` (NOTE: plural)

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6 (fast mode)

### Completion Notes List
- Created `backend/domains/inventory/mcp.py` — 3 tools: `inventory_check`, `inventory_search`, `inventory_reorder_alerts`
- All tools call `set_tenant` (inventory services don't use `session.begin()` internally)
- Registered tools in `mcp_server.py` via import side-effect
- Discovered `@mcp.tool()` wraps into `FunctionTool` objects — test via `.fn` attribute
- 6 tests in `backend/tests/test_mcp_inventory.py`, all passing
