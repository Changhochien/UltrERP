"""
API Key authentication middleware for the UltrERP MCP server.

This module implements the authentication layer required by the PoC:

  - Checks X-API-Key request header
  - Validates the key against a known key store
  - Attaches the key's scopes to the request context
  - Returns 401 for missing/invalid keys
  - 403 with required scope for insufficient privileges

Scoped access model (per 00-context.md):
  - customers:read   — list and retrieve customers
  - customers:write  — create and update customers
  - invoices:read    — list and retrieve invoices
  - invoices:write   — create, update, and void invoices

Production note: Replace this module with an OAuth 2.1 / OIDC integration.
See 01-survey-memo.md "3-Point Recommendation" item 2 for details.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp.exceptions import ToolError
from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.server.dependencies import get_http_headers

# ---------------------------------------------------------------------------
# Known API keys (PoC only — never hardcode secrets in production)
# ---------------------------------------------------------------------------
# Format: key → set of granted scopes
_API_KEYS: dict[str, frozenset[str]] = {
    "sk-erp-admin":      frozenset(["customers:read", "customers:write",
                                     "invoices:read", "invoices:write"]),
    "sk-erp-sales":       frozenset(["customers:read", "customers:write"]),
    "sk-erp-finance":     frozenset(["invoices:read", "invoices:write"]),
    "sk-erp-agent":       frozenset(["customers:read", "invoices:read",
                                     "invoices:write"]),
    # Read-only key for dashboards / read agents
    "sk-erp-readonly":    frozenset(["customers:read", "invoices:read"]),
}


def _get_header(
    context: MiddlewareContext,
    name: str,
) -> str | None:
    """Case-insensitive header lookup helper."""
    headers: dict[str, str] = get_http_headers() or {}
    return headers.get(name.lower()) or headers.get(name)


def _error_response(code: str, message: str, **kwargs: Any) -> dict[str, Any]:
    """Build a structured JSON error response matching errors.py types."""
    body: dict[str, Any] = {"code": code, "message": message, "retry": True}
    body.update(kwargs)
    return {"error": body}


class ApiKeyAuth(Middleware):
    """
    FastMCP middleware that enforces API key authentication and per-tool scope checks.

    Usage::

        mcp = FastMCP("UltrERP")
        mcp.add_middleware(ApiKeyAuth(
            protected_tools={
                "customers.list":   {"customers:read"},
                "customers.create": {"customers:write"},
                "invoices.list":    {"invoices:read"},
                "invoices.create":  {"invoices:write"},
            },
        ))
    """

    def __init__(
        self,
        protected_tools: dict[str, frozenset[str]],
    ) -> None:
        """
        Args:
            protected_tools: Map of tool name → required scope set.
                             Tools not listed are publicly accessible.
        """
        self.protected_tools = protected_tools

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        """
        Intercept every tool call.

        1. Look up the required scope for the target tool.
        2. If the tool is unprotected, pass through.
        3. Validate X-API-Key header presence.
        4. Check the key is known.
        5. Verify the key's scopes include the required scope.
        """
        tool_name = context.message.name

        # Step 1 — determine if this tool requires auth
        required = self.protected_tools.get(tool_name)

        # Unprotected — no auth required
        if required is None:
            return await call_next(context)

        # Step 2 — require X-API-Key header
        raw_key = _get_header(context, "x-api-key")
        if not raw_key:
            raise ToolError(
                "Missing X-API-Key header. "
                "Provide a valid API key to access this tool."
            )

        # Step 3 — validate key is known
        key_lower = raw_key.lower()
        scopes: frozenset[str] | None = None
        for known, s in _API_KEYS.items():
            if known.lower() == key_lower:
                scopes = s
                break

        if scopes is None:
            raise ToolError(
                f"Invalid API key '{raw_key[:8]}***'. "
                "Request a valid key from the UltrERP administrator."
            )

        # Step 4 — scope check
        if not required.issubset(scopes):
            missing = required - scopes
            raise ToolError(
                f"This operation requires scope {required!r} but "
                f"your key only grants {scopes!r}. "
                f"Missing scope(s): {missing!r}. "
                "Contact your administrator to obtain a key with appropriate scopes."
            )

        return await call_next(context)


# ---------------------------------------------------------------------------
# Scope constants (exported for use in tools / documentation)
# ---------------------------------------------------------------------------
SCOPE_CUSTOMERS_READ  = "customers:read"
SCOPE_CUSTOMERS_WRITE = "customers:write"
SCOPE_INVOICES_READ   = "invoices:read"
SCOPE_INVOICES_WRITE  = "invoices:write"

# All scopes known to this server
ALL_SCOPES: frozenset[str] = frozenset([
    SCOPE_CUSTOMERS_READ,
    SCOPE_CUSTOMERS_WRITE,
    SCOPE_INVOICES_READ,
    SCOPE_INVOICES_WRITE,
])

# Tool → required scope mapping
# NOTE: FastMCP 2.x uses the Python function name as the tool name.
# These keys MUST match the registered tool names (snake_case).
TOOL_SCOPES: dict[str, frozenset[str]] = {
    "customers_list":   {SCOPE_CUSTOMERS_READ},
    "customers_create": {SCOPE_CUSTOMERS_WRITE},
    "invoices_list":    {SCOPE_INVOICES_READ},
    "invoices_create":  {SCOPE_INVOICES_WRITE},
}
