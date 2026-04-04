"""
UltrERP MCP Server — FastMCP 2.14.6, session-mode HTTP.

Mounted at /mcp on the FastAPI app. AI agents connect here
via streamable-http transport.
"""
from __future__ import annotations

from fastmcp import FastMCP

from app.mcp_auth import TOOL_SCOPES, ApiKeyAuth, parse_api_keys
from common.config import get_settings

mcp = FastMCP(
	name="UltrERP",
	instructions=(
		"UltrERP MCP server — exposes inventory, customers, "
		"invoices, orders, and payments domains. "
		"All tools require a valid X-API-Key header with "
		"appropriate scopes."
	),
)

# Attach API key authentication middleware.
_settings = get_settings()
_api_keys = parse_api_keys(_settings.mcp_api_keys)
mcp.add_middleware(ApiKeyAuth(api_keys=_api_keys, tool_scopes=TOOL_SCOPES))

# Register domain MCP tools — decorators execute at import time.
import domains.customers.mcp  # noqa: E402, F401
import domains.inventory.mcp  # noqa: E402, F401
import domains.invoices.mcp  # noqa: E402, F401
