"""
API Key authentication middleware for MCP tools.

Validates X-API-Key header, attaches scopes to request context,
and rejects insufficient-scope calls with structured errors.
"""
from __future__ import annotations

import json
import logging
from typing import Any

import jwt
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_http_headers
from fastmcp.server.middleware import Middleware, MiddlewareContext

from common.config import settings

logger = logging.getLogger(__name__)

# ── Tool → required-scope mapping ──────────────────────────────

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

# ── Default role scope sets (architecture §7.3) ────────────────

DEFAULT_ROLE_SCOPES: dict[str, list[str]] = {
	"admin": ["admin"],
	"owner": ["admin"],
	"finance": [
		"customers:read", "invoices:read", "invoices:write",
		"payments:read", "payments:write",
	],
	"warehouse": [
		"inventory:read", "inventory:write",
		"orders:read",
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


# ── Key parsing ────────────────────────────────────────────────

def parse_api_keys(raw: str) -> dict[str, frozenset[str]]:
	"""Parse MCP_API_KEYS JSON string into key→scopes mapping.

	Expected format: {"key": ["scope1", "scope2"], ...}
	A plain non-JSON string is treated as a single admin key for local dev.
	Returns empty dict if raw is empty.
	"""
	raw = raw.strip()
	if not raw:
		return {}
	try:
		data = json.loads(raw)
	except json.JSONDecodeError as exc:
		if raw[0] not in "[{":
			return {raw: frozenset({"admin"})}
		logger.warning("MCP_API_KEYS is not valid JSON, starting with no keys: %s", exc)
		return {}
	if not isinstance(data, dict):
		logger.warning("MCP_API_KEYS JSON must be an object, starting with no keys")
		return {}
	return {k: frozenset(v) for k, v in data.items()}


# ── Middleware ─────────────────────────────────────────────────

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
		tool_name = context.message.name

		headers = get_http_headers() or {}
		scopes = self._resolve_scopes(headers)

		# Admin bypass — "admin" is a meta-scope (architecture §7.3).
		if "admin" in scopes:
			if context.fastmcp_context:
				context.fastmcp_context.set_state("auth_scopes", scopes)
			return await call_next(context)

		required = self._tool_scopes.get(tool_name)
		if required and not required.issubset(scopes):
			raise ToolError(json.dumps({
				"code": "INSUFFICIENT_SCOPE",
				"message": f"Missing scope for {tool_name}",
				"required_scope": sorted(required),
				"token_scopes": sorted(scopes),
				"retry": True,
			}))

		# Attach resolved scopes for downstream tool use.
		if context.fastmcp_context:
			context.fastmcp_context.set_state("auth_scopes", scopes)

		return await call_next(context)

	def _resolve_scopes(self, headers: dict[str, str]) -> frozenset[str]:
		api_key = headers.get("x-api-key")
		if api_key:
			scopes = self._api_keys.get(api_key)
			if scopes is None:
				raise ToolError(json.dumps({
					"code": "INVALID_KEY",
					"message": "Invalid API key",
					"retry": True,
				}))
			return scopes

		auth_header = headers.get("authorization", "")
		if auth_header.startswith("Bearer "):
			token = auth_header[7:].strip()
			if not token:
				raise ToolError(json.dumps({
					"code": "INVALID_TOKEN",
					"message": "Invalid or expired Bearer token",
					"retry": True,
				}))
			try:
				payload = jwt.decode(
					token,
					settings.jwt_secret,
					algorithms=["HS256"],
				)
			except jwt.InvalidTokenError as exc:
				raise ToolError(json.dumps({
					"code": "INVALID_TOKEN",
					"message": "Invalid or expired Bearer token",
					"retry": True,
				})) from exc

			role = payload.get("role")
			if not isinstance(role, str) or not role:
				raise ToolError(json.dumps({
					"code": "INVALID_TOKEN",
					"message": "Invalid or expired Bearer token",
					"retry": True,
				}))

			return frozenset(DEFAULT_ROLE_SCOPES.get(role, ()))

		raise ToolError(json.dumps({
			"code": "AUTH_REQUIRED",
			"message": "X-API-Key or Authorization: Bearer header is required",
			"retry": True,
		}))
