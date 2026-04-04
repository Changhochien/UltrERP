"""Mount helper — returns the MCP ASGI app for FastAPI mounting."""
from __future__ import annotations

from starlette.applications import Starlette

from app.mcp_server import mcp


def get_mcp_app() -> Starlette:
	"""Return the MCP ASGI app for mounting."""
	return mcp.http_app(path="/")
