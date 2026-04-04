# Story 11.4: RBAC for MCP/CLI

Status: completed

## Story

As a system,
I want to enforce RBAC and auth scopes consistently across MCP and CLI surfaces,
so that all access methods are equally secure.

## Context

The MCP layer already has API key authentication (`app/mcp_auth.py`) with `TOOL_SCOPES`, `DEFAULT_ROLE_SCOPES`, and `ApiKeyAuth` middleware. This story extends MCP auth to also accept JWT Bearer tokens (from Story 11.3), unifying the auth model. API keys remain for automation/agent use; JWT tokens enable interactive users to use MCP tools with their role's scopes.

### Existing MCP Auth (app/mcp_auth.py)

```python
# Already implemented:
TOOL_SCOPES = {
    "inventory_check": frozenset({"inventory:read"}),
    "inventory_search": frozenset({"inventory:read"}),
    # ...9 tools total
}

DEFAULT_ROLE_SCOPES = {
    "admin": ["admin"],
    "finance": ["customers:read", "invoices:read", "invoices:write", "payments:read", "payments:write"],
    "sales": ["customers:read", "customers:write", "invoices:read", "invoices:create", "orders:read", "orders:write"],
    "agent": ["customers:read", "invoices:read", "invoices:create", "inventory:read", "orders:read"],
}
```

`ApiKeyAuth` middleware validates `X-API-Key` header, resolves scopes, and checks against `TOOL_SCOPES` per tool. Admin scope bypasses all checks.

### Architecture Decision

- Extend `ApiKeyAuth` middleware to check `Authorization: Bearer <JWT>` header when `X-API-Key` is absent
- JWT token's `role` field maps to scopes via `DEFAULT_ROLE_SCOPES`
- Owner role maps to `["admin"]` scope (full bypass)
- Add `warehouse` role to `DEFAULT_ROLE_SCOPES` for MCP scope mapping
- Keep CLI auth mechanism the same — CLI uses either API key or JWT token in headers
- Audit log records MCP access attempts (already mostly done in mcp_auth)

### Scope Mapping for New Roles

| Role | MCP Scopes |
|------|------------|
| `owner` | `["admin"]` (bypass) |
| `finance` | `["customers:read", "invoices:read", "invoices:write", "payments:read", "payments:write"]` |
| `warehouse` | `["inventory:read", "inventory:write", "orders:read"]` |
| `sales` | `["customers:read", "customers:write", "invoices:read", "invoices:create", "orders:read", "orders:write"]` |

## Acceptance Criteria

**AC1:** JWT Bearer token accepted in MCP
**Given** a valid JWT Bearer token
**When** an MCP tool call is made with `Authorization: Bearer <token>` header
**Then** the system extracts the user's role from the JWT
**And** maps role to scopes via `DEFAULT_ROLE_SCOPES`
**And** validates tool scopes as normal

**AC2:** API key still works
**Given** a valid API key in `X-API-Key` header
**When** an MCP tool call is made
**Then** the system authenticates via API key as before (no regression)

**AC3:** JWT takes precedence when both headers present
**Given** both `X-API-Key` and `Authorization: Bearer` headers are present
**When** an MCP tool call is made
**Then** `X-API-Key` takes precedence (existing behavior preserved)

**AC4:** Warehouse role scopes
**Given** a warehouse user with JWT token
**When** they call `inventory_check` or `inventory_search`
**Then** access is granted
**When** they call `invoices_list`
**Then** the response is INSUFFICIENT_SCOPE error

**AC5:** Owner JWT bypasses all scope checks
**Given** an owner user with JWT token
**When** they call any MCP tool
**Then** access is granted (admin bypass)

**AC6:** Expired/invalid JWT rejected
**Given** an expired or malformed JWT
**When** an MCP tool call is made
**Then** the response is an AUTH_REQUIRED or INVALID_KEY error

**AC7:** All existing tests pass
**Given** all existing tests
**When** I run `cd backend && python -m pytest tests/ -v --tb=short`
**Then** all existing tests continue to pass
**And** new MCP auth JWT tests are added (≥ 8 tests)

## Tasks / Subtasks

- [x] **Task 1: Scope mapping updates**
  - [x] `backend/app/mcp_auth.py` now maps `owner` to `admin` explicitly and adds `warehouse` read/write inventory scopes.

- [x] **Task 2: JWT fallback in MCP auth**
  - [x] `ApiKeyAuth` now accepts `Authorization: Bearer <token>` when `X-API-Key` is absent and preserves API-key precedence when both headers are present.

- [x] **Task 3: Shared scope enforcement**
  - [x] JWT-authenticated calls flow through the same scope and admin-bypass logic already used for API keys.

- [x] **Task 4: Focused validation**
  - [x] `backend/tests/test_mcp_auth.py` now covers JWT acceptance, warehouse scope rejection, owner bypass, invalid/expired token rejection, and API-key precedence.

## File Changes

### Modified Files
| File | Change |
|------|--------|
| `backend/app/mcp_auth.py` | Add warehouse to DEFAULT_ROLE_SCOPES, add JWT fallback in ApiKeyAuth |
| `backend/tests/test_mcp_auth.py` | Expanded MCP auth coverage for JWT and scope precedence |

### New Files
None — tests go into existing `backend/tests/test_mcp_auth.py`

## Dev Notes

- **Minimal changes to mcp_auth.py.** The JWT fallback is ~15 lines added to the existing `on_call_tool` method.
- Import `jwt` and `settings` at the top of mcp_auth.py.
- The `jwt.decode()` call uses `settings.jwt_secret` — same secret as Story 11.3.
- **Do NOT change the existing API key flow.** Only add JWT as a fallback when X-API-Key is absent.
- `DEFAULT_ROLE_SCOPES` update for warehouse is backward-compatible — it's a new key, doesn't change existing entries.
- CLI tools that use MCP can now authenticate via either API key (for automation) or JWT (for interactive users). The CLI itself is responsible for obtaining the JWT via the login endpoint (Story 11.3).
- TAB indentation. Ruff py312 rules E/F/I.

## Dev Agent Record

- **Implemented by:** Copilot Agent
- **Date:** 2026-04-03
- **Validation:** Focused MCP auth slice passed with 15 tests.
- **Implementation notes:**
  - JWT fallback is deliberately secondary to `X-API-Key` so existing automation behavior does not change.
  - Scope resolution stays centralized inside `mcp_auth.py`; no tool-level authorization logic was duplicated.
