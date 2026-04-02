# FastMCP 2.0 Server PoC — Findings

## Running the Server

```bash
cd 02-poc/
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
# Server starts on http://0.0.0.0:8000/mcp
```

MCP clients connect to `/mcp` (streamable-http transport). The endpoint requires
`Accept: text/event-stream` headers for SSE streaming responses.

---

## 1. FastMCP 2.0 Tool Registration Syntax

### Decorator-based Registration

```python
from fastmcp import FastMCP

mcp = FastMCP(name="UltrERP")

@mcp.tool()
def customers_list(status: Annotated[CustomerStatus | None, Field(description="...")] = None) -> dict:
    """List customers in the UltrERP system. ..."""
    ...
```

**Key observations:**
- The `@mcp.tool()` decorator registers a Python function as an MCP tool.
- The function name becomes the tool name (e.g., `customers_list` → tool `customers_list`).
- The docstring becomes the tool description.
- Type annotations generate the JSON Schema input schema automatically.
- `Annotated[T, Field(...)]` with Pydantic `Field` provides rich parameter descriptions,
  defaults, and validation constraints (`ge`, `le`, `min_length`, `pattern`).

### FastMCP 2.x vs 3.x Differences

| Feature | FastMCP 2.x | FastMCP 3.x |
|---|---|---|
| `host`/`port` | Constructor argument | `run()` argument |
| `mcp.tool(auth=...)` | Not supported | Supported |
| Decorator returns callable | No | Yes (enables direct unit testing) |
| `mount(prefix=...)` | Yes | Renamed to `namespace` |
| Component-level enable/disable | `tool.disable()` | `server.disable(keys=[...])` |

**Critical finding:** The `auth=require_scopes(...)` parameter on `@mcp.tool()` is a
**FastMCP 3.x feature only**. FastMCP 2.x does not support this parameter — attempting
to use it raises `TypeError: got unexpected keyword argument 'auth'`.

**PoC implication:** Auth must be enforced via middleware in FastMCP 2.x. See Section 2.

### Pydantic Field Annotations

```python
from typing import Annotated
from pydantic import Field

name: Annotated[
    str,
    Field(
        description="Legal name (2–255 characters)",
        min_length=2,
        max_length=255,
    ),
]

tax_id: Annotated[
    str,
    Field(description="8-digit MOD11 tax ID", pattern=r"^\d{8}$"),
]
```

The `format="email"` key in `Field(...)` is deprecated in Pydantic 2.x (warning:
`PydanticDeprecatedSince20`). Use a `pattern` regex or a dedicated email validation
library instead.

### Mounting Sub-servers

FastMCP 2.x uses `mount(provider, prefix="...")` to compose servers. In 3.x this
becomes `mount(provider, namespace="...")`. The PoC is implemented as a single
server to avoid this migration issue.

---

## 2. Auth Implementation Notes

### Middleware-based Auth (FastMCP 2.x)

Since `auth=` on decorators is not available in FastMCP 2.x, all authentication
and authorization is handled by a custom `Middleware` class:

```python
from fastmcp.server.middleware import Middleware, MiddlewareContext

class ApiKeyAuth(Middleware):
    async def on_call_tool(self, context: MiddlewareContext, call_next):
        tool_name = context.message.name  # CallToolRequestParams.name
        required = self.protected_tools.get(tool_name)

        if required is None:
            return await call_next(context)  # Unprotected tool

        headers = get_http_headers() or {}
        api_key = headers.get("x-api-key")

        if not api_key:
            raise ToolError("Missing X-API-Key header.")

        # Validate key and scopes...
        if not required.issubset(scopes):
            raise ToolError(f"Requires scope {required}, got {scopes}.")
```

Register with:
```python
mcp = FastMCP(name="UltrERP")
mcp.add_middleware(ApiKeyAuth(protected_tools=TOOL_SCOPES))
```

**FastMCP 2.x MiddlewareContext attributes:**
- `message` — the `CallToolRequestParams` (has `.name` and `.arguments`)
- `fastmcp_context` — the FastMCP `Context` object (session, request_context, etc.)
- `source` — `"client"` or `"server"`
- `type` — `"request"` or `"notification"`

**Does NOT have:** `settings` attribute (present in FastMCP 3.x).

### MiddlewareContext.message.name

`context.message` is typed as `T` (generic) but at runtime for `on_call_tool` it is a
`CallToolRequestParams` with fields:
- `name: str` — the tool name
- `arguments: dict[str, Any] | None` — the call arguments
- `task: TaskMetadata | None`
- `meta: RequestParams.Meta | None`

### API Key Storage

The PoC uses a simple in-memory dict. **For production, use a secrets manager**
(e.g., AWS Secrets Manager, HashiCorp Vault) and never hardcode keys.

```python
_API_KEYS: dict[str, frozenset[str]] = {
    "sk-erp-admin":    frozenset(["customers:read", "customers:write",
                                  "invoices:read", "invoices:write"]),
    "sk-erp-readonly": frozenset(["customers:read", "invoices:read"]),
    ...
}
```

### Header Access in Middleware

```python
from fastmcp.server.dependencies import get_http_headers

def _get_header(context: MiddlewareContext, name: str) -> str | None:
    headers: dict[str, str] = get_http_headers() or {}
    return headers.get(name.lower()) or headers.get(name)
```

`get_http_headers()` returns a case-insensitive dict of HTTP request headers.

---

## 3. Error Response Format Analysis

### Structured Error Types

The PoC defines three structured error classes in `errors.py`:

```python
class ValidationError(StructuredError):
    code = "VALIDATION_ERROR"
    retry = False  # Client must fix input before retry
    # details: {field, value, constraint, received}

class NotFoundError(StructuredError):
    code = "NOT_FOUND"
    retry = True  # May exist on retry (transient)
    # details: {entity_type, entity_id}

class PermissionError(StructuredError):
    code = "PERMISSION_DENIED"
    retry = True  # Can obtain better token via step-up auth
    # details: {required_scope, token_scopes, operation}
```

### Error Propagation Path

1. Tool raises `ValidationError` / `NotFoundError` / `PermissionError`
2. FastMCP catches the exception and calls `ToolError(str(e))`
3. `ToolError` is returned as an MCP protocol error response

**Issue:** FastMCP's `ToolError` only carries a string message — it does not preserve
the structured fields from `StructuredError.to_dict()`. The MCP client sees a flat
error string, not a structured JSON object.

**Current workaround:** The error message embeds key details as plain text:
```
"ValidationError: tax_id MOD11 checksum validation failed."
"PermissionError: This operation requires scope {'invoices:write'} but ..."
```

### ToolError Limitation

```python
# FastMCP 2.x ToolError does NOT accept retriable= kwarg
raise ToolError("message", retriable=False)  # TypeError!

# Must use positional args only
raise ToolError("message")
```

### MCP Protocol Error Format

MCP JSON-RPC errors are:
```json
{
  "jsonrpc": "2.0",
  "id": "...",
  "error": {
    "code": -32602,
    "message": "Error calling tool 'customers_create': ..."
  }
}
```

The JSON-RPC error `code` is -32602 (invalid params) for tool argument validation
failures. The actual error type (ValidationError vs NotFoundError) is only
discernible from the message text.

### Recommendations for Better Error Structure

1. **Extend ToolError in FastMCP 3.x** — v3's `ToolError` may support structured
   error data. Verify before migrating.
2. **Use a result wrapper** — Return a dict with a structured `error` key instead
   of raising exceptions, preserving all fields:
   ```python
   return {"error": validation_error.to_dict()}
   ```
3. **Client-side parsing** — MCP clients can regex-match error messages for error
   codes (`VALIDATION_ERROR`, `NOT_FOUND`, etc.) to take appropriate action.

---

## 4. Recommendations for Full MCP Server

### 4.1 FastMCP Version Strategy

- **PoC:** FastMCP 2.14.6 (this implementation)
- **Production (6-month horizon):** Re-evaluate FastMCP 3.x when it ships stable
  release supporting MCP SDK 1.23+

FastMCP 3.x is incompatible with MCP SDK 1.23+ due to protocol changes introduced
in November 2025. Monitor the [changelog](https://gofastmcp.com/changelog) for
compatibility announcements.

### 4.2 OAuth 2.1 Authorization Server

The PoC uses simple API key auth. For production:

1. **Use an established OIDC provider** (Auth0, Okta, Azure AD) rather than
   building a compliant OAuth 2.1 authorization server from scratch.
2. The MCP server acts as a **resource server** (RFC 9728 Protected Resource
   Metadata) and must:
   - Return `401` with `WWW-Authenticate: Bearer resource_metadata=<url>`
   - Validate token **audience** claim (critical security control — prevents
     token replay across servers)
   - Support PKCE with `S256` code challenge
   - Implement step-up auth (return `403` with `WWW-Authenticate: Bearer
     error="insufficient_scope", scope="required_scope"`)

3. **Map RBAC roles to OAuth scopes:**
   ```
   admin   → erp:admin (full CRUD all domains)
   finance → erp:finance (invoices CRUD+void, payments CRUD)
   warehouse → erp:warehouse (inventory CRUD)
   sales   → erp:sales (customers CRUD, orders CRUD, inventory read)
   agent   → erp:agent (read all, create invoices)
   ```

### 4.3 Token Audience Validation

Critical security control from RFC 8707. Every request must verify:
```python
assert token.aud == "https://ulterp.example.com/mcp"
```

Without this, a token issued for one MCP server can be replayed against another
(the "confused deputy" problem).

### 4.4 Structured Errors

Replace `ToolError` string messages with a structured response format:
```python
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "tax_id MOD11 checksum validation failed",
    "details": {
      "field": "customer.tax_id",
      "value": "10101010",
      "constraint": "valid MOD11 check digit"
    },
    "retry": false
  }
}
```

This requires either:
- FastMCP 3.x with structured `ToolError` support, OR
- Returning a dict result instead of raising exceptions (but this breaks the
  MCP protocol convention of using `isError: true` in content)

### 4.5 Per-Tool Authorization in FastMCP 3.x

When migrating to FastMCP 3.x, use the `auth=` decorator parameter instead of
custom middleware:
```python
from fastmcp.server.auth import require_scopes

@mcp.tool(auth=require_scopes("customers:write"))
def customers_create(...) -> dict:
    ...
```

This moves auth metadata closer to the tool definition and enables FastMCP's
built-in authorization infrastructure.

### 4.6 Multi-server Architecture

Rather than one large server, compose multiple focused servers using FastMCP's
mounting system:
```
root_mcp = FastMCP("UltrERP")
root_mcp.mount(customers_mcp, prefix="customers")
root_mcp.mount(invoices_mcp, prefix="invoices")
root_mcp.mount(inventory_mcp, prefix="inventory")
```

Each sub-server can have its own auth configuration and OAuth scope requirements.

### 4.7 Tool Naming

Follow MCP spec kebab-case convention: `customers.list`, `invoices.create`.
FastMCP uses Python function names as tool names — use snake_case function names
with a mapping layer, or FastMCP 3.x's `name=` parameter if available.

### 4.8 Pagination

MCP spec uses opaque cursor-based pagination. Encode cursors as base64 JSON:
```python
cursor = base64.b64encode(json.dumps({"offset": 25, "filters": {...}}))
```

Validate cursors server-side to prevent clients bypassing access controls
via tampered cursors.

---

## File Structure

```
02-poc/
  main.py          # FastMCP 2.0 server with all 4 tools + MOD11 validation
  auth.py          # ApiKeyAuth middleware + scope constants
  errors.py        # Structured error types (ValidationError, NotFoundError, PermissionError)
  models.py        # Pydantic domain models + enums
  requirements.txt # fastmcp>=2.0,<3.0, uvicorn, pydantic
  test_poc.py      # Functional test suite (9 tests)
  03-findings.md   # This document
```

## Test Results

```
1. customers.list returns mock data          PASS
2. customers.create MOD11 validation (valid) PASS
3. customers.create rejects invalid MOD11    PASS
4. invoices.create 5% tax calculation       PASS
5. invoices.list with status filter          PASS
6. READONLY key → 403 on invoices.create    PASS
7. No API key → 401                         PASS
8. SALES key → 403 on invoices.create       PASS
9. NotFoundError for invalid customer_id     PASS
```
