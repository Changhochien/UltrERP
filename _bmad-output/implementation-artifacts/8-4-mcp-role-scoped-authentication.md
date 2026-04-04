# Story 8.4: MCP Tool — Role-Scoped Authentication

Status: complete

## Story

As a system,
I want MCP tools to support role-scoped authentication,
So that agents only access what they're permitted to.

## Acceptance Criteria

**AC1:** API key middleware validates requests
**Given** an MCP tool is called
**When** the request includes an `X-API-Key` header
**Then** the middleware validates the key against a known key store
**And** attaches the key's scopes to the request context

**AC2:** Missing key returns 401
**Given** an MCP tool is called
**When** no `X-API-Key` header is present
**Then** the middleware returns a ToolError with code `AUTH_REQUIRED`
**And** the response includes `"retry": true`

**AC3:** Invalid key returns 401
**Given** an MCP tool is called
**When** the `X-API-Key` header contains an unrecognised key
**Then** the middleware returns a ToolError with code `INVALID_KEY`
**And** the response includes `"retry": true`

**AC4:** Insufficient scope returns 403
**Given** a valid API key with scopes `["customers:read"]`
**When** the agent calls a tool requiring `invoices:write`
**Then** the middleware returns a ToolError with code `INSUFFICIENT_SCOPE`
**And** the response includes `required_scope` and `token_scopes`

**AC5:** Tool-to-scope mapping applied
**Given** each MCP tool has a required scope
**When** a tool is called
**Then** the middleware checks the caller's scopes against the tool's required scope
**And** rejects if the caller lacks the required scope
**And** the scope mapping follows architecture §7.3 for scope names: `customers:read`, `invoices:read`, `inventory:read`, `invoices:write`, `invoices:create`, etc.

**AC6:** API key configuration via settings
**Given** the backend configuration
**When** API keys are configured
**Then** keys and scopes are loaded from settings (not hardcoded)
**And** the settings follow `pydantic_settings.BaseSettings` with `AliasChoices` pattern
**And** `.env.example` is updated with `MCP_API_KEYS` placeholder

**AC7:** RBAC scope sets match architecture
**Given** the defined roles
**When** each role's scopes are configured
**Then** they match architecture §7.3:
  - `agent`: `customers:read`, `invoices:read`, `invoices:create`, `inventory:read`, `orders:read`
  - `finance`: `customers:read`, `invoices:read`, `invoices:write`, `payments:read`, `payments:write`
  - `sales`: `customers:read`, `customers:write`, `invoices:read`, `invoices:create`, `orders:read`, `orders:write`
  - `admin`: `["admin"]` meta-scope — grants access to ALL tools (bypasses per-tool scope check)

**AC8:** Backend tests pass
**Given** all existing tests
**When** I run `cd backend && python -m pytest tests/ -v --tb=short`
**Then** all existing tests continue to pass
**And** auth middleware tests are added (≥ 6 tests)

## Tasks / Subtasks

- [ ] **Task 1: Create auth middleware module** (AC1, AC2, AC3, AC4)
  - [ ] Create `backend/app/mcp_auth.py`:
    ```python
    """
    API Key authentication middleware for MCP tools.
    
    Validates X-API-Key header, attaches scopes to request context,
    and rejects insufficient-scope calls with structured errors.
    """
    from __future__ import annotations
    import json
    from typing import Any
    from fastmcp.exceptions import ToolError
    from fastmcp.server.middleware import Middleware, MiddlewareContext
    from fastmcp.server.dependencies import get_http_headers

    class ApiKeyAuth(Middleware):
        def __init__(
            self,
            api_keys: dict[str, frozenset[str]],
            tool_scopes: dict[str, frozenset[str]],
        ):
            self._api_keys = api_keys
            self._tool_scopes = tool_scopes

        async def on_call_tool(
            self,
            context: MiddlewareContext,
            call_next,
        ) -> Any:
            # 1. Extract tool name from context
            tool_name = context.message.name

            # 2. Extract X-API-Key from headers
            headers = get_http_headers() or {}
            api_key = headers.get("x-api-key")

            # 3. Validate key exists
            if not api_key:
                raise ToolError(json.dumps({
                    "code": "AUTH_REQUIRED",
                    "message": "X-API-Key header is required",
                    "retry": True,
                }))

            # 4. Validate key is known
            scopes = self._api_keys.get(api_key)
            if scopes is None:
                raise ToolError(json.dumps({
                    "code": "INVALID_KEY",
                    "message": "Invalid API key",
                    "retry": True,
                }))

            # 5. Admin bypass — "admin" is a meta-scope (architecture §7.3)
            # Admin keys get ["admin"] which grants access to ALL tools.
            if "admin" in scopes:
                return await call_next(context)

            # 6. Check tool scope
            required = self._tool_scopes.get(tool_name)
            if required and not required.issubset(scopes):
                raise ToolError(json.dumps({
                    "code": "INSUFFICIENT_SCOPE",
                    "message": f"Missing scope for {tool_name}",
                    "required_scope": sorted(required),
                    "token_scopes": sorted(scopes),
                    "retry": True,
                }))

            return await call_next(context)
    ```

- [ ] **Task 2: Add MCP settings to config** (AC6)
  - [ ] In `backend/common/config.py`, add:
    ```python
    # MCP Authentication
    mcp_api_keys: str = Field(
        default="",
        validation_alias=AliasChoices("MCP_API_KEYS", "mcp_api_keys"),
    )
    ```
  - [ ] Parse JSON mapping: `{"key": ["scope1", "scope2"]}`
  - [ ] Update `.env.example` with `MCP_API_KEYS` placeholder and comment:
    ```env
    # MCP API Keys — JSON mapping of key → scopes.
    # Format: {"<key>": ["<scope1>", "<scope2>", ...], ...}
    # Use DEFAULT_ROLE_SCOPES role names to generate scope lists.
    # Example: {"test-admin-key": ["admin"], "test-agent-key": ["customers:read", "invoices:read", "inventory:read", "orders:read"]}
    MCP_API_KEYS=
    ```

- [ ] **Task 3: Define TOOL_SCOPES mapping** (AC5, AC7)
  - [ ] In `backend/app/mcp_auth.py`, define `TOOL_SCOPES` dict:
    ```python
    TOOL_SCOPES: dict[str, frozenset[str]] = {
        # inventory domain (Story 8.1)
        "inventory_check": frozenset({"inventory:read"}),
        "inventory_search": frozenset({"inventory:read"}),
        "inventory_reorder_alerts": frozenset({"inventory:read"}),
        # customers domain (Story 8.2)
        "customers_list": frozenset({"customers:read"}),
        "customers_get": frozenset({"customers:read"}),
        "customers_lookup_by_ban": frozenset({"customers:read"}),
        # invoices domain (Story 8.3)
        "invoices_list": frozenset({"invoices:read"}),
        "invoices_get": frozenset({"invoices:read"}),
    }
    ```
  - [ ] Define `DEFAULT_ROLE_SCOPES` matching architecture §7.3:
    ```python
    DEFAULT_ROLE_SCOPES: dict[str, list[str]] = {
        "admin": ["admin"],
        "finance": [
            "customers:read", "invoices:read", "invoices:write",
            "payments:read", "payments:write",
        ],
        "sales": [
            "customers:read", "customers:write",
            "invoices:read", "invoices:create",
            "orders:read", "orders:write",
        ],
        "agent": [
            "customers:read", "invoices:read", "invoices:create",
            "inventory:read", "orders:read",
        ],
    }
    ```
    Note: `invoices:create` is a narrower scope than `invoices:write` (§7.2: sales gets Create, finance gets CRUD+void). No current MCP tool requires `invoices:create` — it will be needed by future write tools (Epic 9+). Include it in role definitions for forward-compatibility.

- [ ] **Task 4: Wire middleware into MCP server** (AC1)
  - [ ] **Sequencing note:** This task modifies `backend/app/mcp_server.py` which is created by Story 8.6. If implementing out of order, create a minimal `mcp_server.py` stub or defer this task until after Story 8.6 is complete.
  - [ ] In `backend/app/mcp_server.py`, after creating `mcp`:
    ```python
    from app.mcp_auth import ApiKeyAuth, TOOL_SCOPES, parse_api_keys
    from common.config import get_settings

    settings = get_settings()
    api_keys = parse_api_keys(settings.mcp_api_keys)
    mcp.add_middleware(ApiKeyAuth(api_keys=api_keys, tool_scopes=TOOL_SCOPES))
    ```

- [ ] **Task 4b: Implement `parse_api_keys` helper** (AC6)
  - [ ] In `backend/app/mcp_auth.py`, add:
    ```python
    def parse_api_keys(raw: str) -> dict[str, frozenset[str]]:
        """Parse MCP_API_KEYS JSON string into key→scopes mapping.

        Expected format: {"key": ["scope1", "scope2"], ...}
        Returns empty dict if raw is empty.
        """
        if not raw:
            return {}
        data = json.loads(raw)
        return {k: frozenset(v) for k, v in data.items()}
    ```

- [ ] **Task 5: Create auth tests** (AC2, AC3, AC4, AC8)
  - [ ] Create `backend/tests/test_mcp_auth.py`:
    - Test: Missing API key returns AUTH_REQUIRED error
    - Test: Invalid API key returns INVALID_KEY error
    - Test: Valid key with insufficient scope returns INSUFFICIENT_SCOPE error
    - Test: Valid key with sufficient scope allows tool execution
    - Test: Admin key (`["admin"]` meta-scope) can call any tool regardless of tool_scopes
    - Test: Tool without scope mapping is accessible (open by default)
    - Test: `parse_api_keys` parses valid JSON correctly
    - Test: `parse_api_keys` returns empty dict for empty string
  - [ ] Run full test suite

## Dev Notes

### Architecture Compliance
- **§7.1:** Authentication Matrix — AI agents use API keys with scopes (for automation); interactive agents use audience-validated bearer tokens (future OAuth story in Epic 11)
- **§7.2:** RBAC matrix — defines which operations each role can perform (CRUD granularity)
- **§7.3:** Automation API key scope sets — `erp_key_admin_*: ["admin"]`, `erp_key_agent_*`, `erp_key_finance_*`, `erp_key_sales_*`. Note: `admin` is a meta-scope that bypasses per-tool scope checks. `invoices:create` is a valid narrower scope (vs `invoices:write` which includes void/update).
- **This story implements API key auth only.** Bearer token / OAuth 2.1 is deferred to Epic 11 per architecture §7.1.

### Critical Warnings
- ⚠️ Do NOT hardcode API keys in source code. Load from `MCP_API_KEYS` env var / settings.
- ⚠️ FastMCP 2.x `on_call_tool` signature is `(self, context: MiddlewareContext, call_next)` — NOT `(self, context, tool_name, arguments)`. Access tool name via `context.message.name`. Delegate via `await call_next(context)`. The PoC (`research/multi-agent-patterns/02-poc/auth.py`) is the authoritative reference.
- ⚠️ `ToolError` only accepts a string message (no `retriable=` kwarg in FastMCP 2.x). Encode structured error data as JSON string.
- ⚠️ `get_http_headers()` returns lowercase header names. Always use `.get("x-api-key")`, not `X-API-Key`.

### Project Structure Notes
- `backend/app/mcp_auth.py` — NEW: ApiKeyAuth middleware + TOOL_SCOPES
- `backend/app/mcp_server.py` — MODIFIED: attach middleware (from Story 8.6)
- `backend/common/config.py` — MODIFIED: add `mcp_api_keys` setting
- `.env.example` — MODIFIED: add `MCP_API_KEYS` variable

### Previous Story Intelligence
- **Story 8.6:** Creates the MCP server and mount — this story adds auth middleware on top
- **PoC reference:** `research/multi-agent-patterns/02-poc/auth.py` — `ApiKeyAuth(Middleware)` with `on_call_tool`, `get_http_headers()`, scope validation
- **PoC reference:** `research/multi-agent-patterns/02-poc/errors.py` — `PermissionError` with `required_scope`, `token_scopes`
- **Config pattern:** `backend/common/config.py` uses `AliasChoices` — follow same pattern for `mcp_api_keys`

### References
- Architecture v2 §7.1-7.5 (Security)
- PRD: FR33
- PoC: `research/multi-agent-patterns/02-poc/auth.py`
- PoC findings: `research/multi-agent-patterns/02-poc/03-findings.md` — FastMCP 2.x middleware limitations

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6 (fast mode)

### Completion Notes List
- Created `backend/app/mcp_auth.py` — `ApiKeyAuth(Middleware)` with `TOOL_SCOPES`, `DEFAULT_ROLE_SCOPES`, `parse_api_keys()`
- Added `mcp_api_keys` field to `backend/common/config.py` with `AliasChoices`
- Updated `.env.example` with `MCP_API_KEYS` variable
- Wired middleware in `mcp_server.py` via `mcp.add_middleware()`
- Admin meta-scope bypasses per-tool scope checks
- 8 tests in `backend/tests/test_mcp_auth.py`, all passing
- 2026-04-04 follow-up: `parse_api_keys()` now accepts a plain non-JSON `MCP_API_KEYS=<token>` value as a single admin-scoped local-dev key while keeping the JSON-object mapping as the primary production format.
