# Story 8.2: MCP Tool — Customer Query

Status: complete

## Story

As an AI agent,
I want to query customer data via MCP tools,
So that I can retrieve customer information.

## Acceptance Criteria

**AC1:** `customers_list` tool returns paginated customers
**Given** I'm an AI agent with MCP access and `customers:read` scope
**When** I call `customers_list` with optional filters (search, status, page, page_size)
**Then** I receive a paginated list of customers with id, company name, phone, status
**And** search supports filtering by business number (統一編號) or company name

**AC2:** `customers_get` tool returns a single customer
**Given** I'm an AI agent with MCP access and `customers:read` scope
**When** I call `customers_get` with a `customer_id`
**Then** I receive the full customer record
**And** the response includes all customer fields (company_name, business_number, contact, phone, email, address, status, credit_limit, etc.)

**AC3:** `customers_lookup_by_ban` tool looks up by business number
**Given** I'm an AI agent with MCP access and `customers:read` scope
**When** I call `customers_lookup_by_ban` with a `business_number` (統一編號)
**Then** Taiwan business-number checksum validation is applied
**And** if valid, the customer matching that BAN is returned
**And** if not found, a `NotFoundError` is raised

**AC4:** Customer not found returns structured error
**Given** I call `customers_get` with a non-existent `customer_id`
**When** the service returns `None`
**Then** the tool raises `ToolError` with a JSON-encoded `NotFoundError`
**And** `entity_type` is `"customer"`

**AC5:** Tenant scoping enforced
**Given** the MCP server is running
**When** any customer tool is called
**Then** all queries are scoped to `DEFAULT_TENANT_ID`
**And** RLS is enforced via `set_tenant(session, tenant_id)`

**AC6:** Backend tests pass
**Given** all existing tests
**When** I run `cd backend && python -m pytest tests/ -v --tb=short`
**Then** all existing tests continue to pass
**And** customer MCP tool tests are added (≥ 6 tests)

## Tasks / Subtasks

- [ ] **Task 1: Create customer MCP tools module** (AC1, AC2, AC3, AC4, AC5)
  - [ ] Create `backend/domains/customers/mcp.py`:
    ```python
    """
    MCP tools for the Customers domain.

    Tools:
      - customers_list: List customers with search and pagination
      - customers_get: Get a single customer by ID
      - customers_lookup_by_ban: Look up customer by Taiwan business number
    """
    from __future__ import annotations
    import uuid
    import json
    from typing import Annotated, Literal
    from pydantic import Field
    from fastmcp.exceptions import ToolError

    from app.mcp_server import mcp
    from common.database import AsyncSessionLocal
    from common.tenant import set_tenant, DEFAULT_TENANT_ID
    from domains.customers.service import (
        list_customers,
        get_customer,
        lookup_customer_by_ban,
    )
    from domains.customers.schemas import CustomerListParams
    from domains.customers.validators import validate_taiwan_business_number

    @mcp.tool()
    async def customers_list(
        search: Annotated[str | None, Field(description="Search by company name or business number")] = None,
        status: Annotated[Literal["active", "inactive", "suspended"] | None, Field(description="Filter by status")] = None,
        page: Annotated[int, Field(description="Page number", default=1, ge=1)] = 1,
        page_size: Annotated[int, Field(description="Results per page", default=20, ge=1, le=100)] = 20,
    ) -> dict:
        """List customers with optional search and status filtering."""
        params = CustomerListParams(
            q=search, status=status, page=page, page_size=page_size,
        )
        async with AsyncSessionLocal() as session:
            # NOTE: Do NOT call set_tenant here — list_customers uses session.begin()
            # internally and calls set_tenant itself. Calling it here would trigger
            # autobegin and conflict with the service's session.begin().
            customers, total = await list_customers(session, params, DEFAULT_TENANT_ID)
            return {
                "customers": [_serialize_customer_summary(c) for c in customers],
                "total": total,
                "page": page,
                "page_size": page_size,
            }

    @mcp.tool()
    async def customers_get(
        customer_id: Annotated[str, Field(description="UUID of the customer")],
    ) -> dict:
        """Get full customer details by ID."""
        cid = uuid.UUID(customer_id)
        async with AsyncSessionLocal() as session:
            # NOTE: Do NOT call set_tenant here — get_customer uses session.begin()
            # internally and calls set_tenant itself.
            customer = await get_customer(session, cid, DEFAULT_TENANT_ID)
            if customer is None:
                raise ToolError(json.dumps({
                    "code": "NOT_FOUND",
                    "entity_type": "customer",
                    "entity_id": customer_id,
                    "message": f"Customer {customer_id} not found",
                    "retry": False,
                }))
            return _serialize_customer(customer)

    @mcp.tool()
    async def customers_lookup_by_ban(
        business_number: Annotated[str, Field(description="Taiwan business number (統一編號, 8 digits)")],
    ) -> dict:
        """Look up a customer by Taiwan business number (統一編號)."""
        # AC3: Validate BAN checksum before querying
        ban_result = validate_taiwan_business_number(business_number)
        if not ban_result.valid:
            raise ToolError(json.dumps({
                "code": "VALIDATION_ERROR",
                "field": "business_number",
                "message": ban_result.error or "Invalid Taiwan business number",
                "retry": False,
            }))
        async with AsyncSessionLocal() as session:
            # NOTE: Do NOT call set_tenant here — lookup_customer_by_ban uses
            # session.begin() internally and calls set_tenant itself.
            customer = await lookup_customer_by_ban(
                session, business_number, DEFAULT_TENANT_ID,
            )
            if customer is None:
                raise ToolError(json.dumps({
                    "code": "NOT_FOUND",
                    "entity_type": "customer",
                    "entity_id": business_number,
                    "message": f"No customer found with BAN {business_number}",
                    "retry": False,
                }))
            return _serialize_customer(customer)
    ```
  - [ ] Implement `_serialize_customer(customer)` and `_serialize_customer_summary(customer)` helper functions to convert SQLAlchemy model → dict
  - [ ] Ensure tool names match `TOOL_SCOPES` in `backend/app/mcp_auth.py` (Story 8.4)

- [ ] **Task 2: Register customer tools** (AC1)
  - [ ] Import `backend/domains/customers/mcp` in `backend/app/mcp_server.py`:
    ```python
    import domains.customers.mcp  # noqa: F401 — registers MCP tools
    ```

- [ ] **Task 3: Create customer MCP tests** (AC1, AC2, AC3, AC4, AC6)
  - [ ] Create `backend/tests/test_mcp_customers.py`:
    - Test: `customers_list` returns paginated results
    - Test: `customers_list` with search filter
    - Test: `customers_get` returns customer for valid ID
    - Test: `customers_get` raises ToolError for non-existent ID
    - Test: `customers_lookup_by_ban` returns customer for valid BAN
    - Test: `customers_lookup_by_ban` raises ToolError (VALIDATION_ERROR) for invalid BAN checksum
    - Test: `customers_lookup_by_ban` raises ToolError (NOT_FOUND) for valid but non-existent BAN
  - [ ] Run full test suite

## Dev Notes

### Architecture Compliance
- **§6.1:** Customer tools: `customers.list`, `customers.get`, `customers.create`, `customers.update` — this story implements read-only tools. Write tools are deferred.
- **§6.1 deviation:** `customers_lookup_by_ban` is not listed in architecture §6.1. Justified by operational need — agents frequently look up customers by 統一編號 rather than UUID. Maps to the existing `lookup_customer_by_ban` service function.
- **§4.3:** Tools wrap existing service functions from `domains/customers/service.py`
- **AC3 on 統一編號:** The `lookup_customer_by_ban` service normalises digits but does NOT validate the checksum. The MCP tool layer calls `validate_taiwan_business_number()` from `domains/customers/validators.py` to enforce checksum validation before querying. This returns `ValidationResult(valid, error)` — if `valid` is False, the tool raises a `VALIDATION_ERROR` ToolError.

### Critical Warnings
- ⚠️ The `list_customers` service returns `tuple[list[Customer], int]` — Customer is a SQLAlchemy model. Must serialise to dict before returning from MCP tool.
- ⚠️ `CustomerListParams` uses field name `q` (not `search`). Construct with `CustomerListParams(q=search, ...)`.
- ⚠️ Do NOT return the full SQLAlchemy model from MCP tools. FastMCP will try to JSON-serialize it and fail. Always convert to plain dicts.
- ⚠️ BAN checksum validation does NOT happen inside `lookup_customer_by_ban` — it only normalises digits. The MCP tool MUST call `validate_taiwan_business_number()` from `domains/customers/validators.py` before calling the service (AC3).
- ⚠️ **Transaction pattern:** `list_customers`, `get_customer`, and `lookup_customer_by_ban` all use `session.begin()` internally and call `set_tenant` themselves. MCP tools must NOT call `set_tenant` before these functions — doing so triggers SQLAlchemy autobegin, and the service's `session.begin()` will raise `InvalidRequestError`. Just pass `tenant_id` as a parameter.

### Project Structure Notes
- `backend/domains/customers/mcp.py` — NEW: MCP tool definitions
- `backend/domains/customers/service.py` — EXISTING: wraps these service functions:
  - `list_customers(session, params, tenant_id)` → `tuple[list[Customer], int]`
  - `get_customer(session, customer_id, tenant_id)` → `Customer | None`
  - `lookup_customer_by_ban(session, business_number, tenant_id)` → `Customer | None`
- `backend/domains/customers/schemas.py` — EXISTING: `CustomerListParams`, `CustomerResponse`, `CustomerSummary`

### Previous Story Intelligence
- **Story 8.6:** Creates the MCP server (`backend/app/mcp_server.py`) — tools register on it
- **Story 8.4:** Creates the auth middleware with `TOOL_SCOPES` — tool names must match
- **Story 8.1:** Same pattern for inventory tools — follow the same structure
- **Service signatures:** `create_customer` and `update_customer` exist but are NOT exposed as MCP tools in this story (write tools deferred)

### References
- Architecture v2 §4.3 (MCP Tools), §6.1 (Customer tools)
- PRD: FR30 (customer query via MCP)
- Backend service: `backend/domains/customers/service.py`

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6 (fast mode)

### Completion Notes List
- Created `backend/domains/customers/mcp.py` — 3 tools: `customers_list`, `customers_get`, `customers_lookup_by_ban`
- Confirmed all 3 customer services use `session.begin()` internally — tools do NOT call `set_tenant`
- BAN validation via `validate_taiwan_business_number()` before querying
- Serialization helpers: `_serialize_customer()` and `_serialize_customer_summary()`
- 7 tests in `backend/tests/test_mcp_customers.py`, all passing
