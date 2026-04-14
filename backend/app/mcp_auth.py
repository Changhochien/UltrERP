"""
API Key authentication middleware for MCP tools.

Validates X-API-Key header, attaches scopes to request context,
and rejects insufficient-scope calls with structured errors.
"""
from __future__ import annotations

import json
import logging
import uuid
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
	# orders domain
	"orders_list": frozenset({"orders:read"}),
	"orders_get": frozenset({"orders:read"}),
	# customers domain (Story 8.2)
	"customers_list": frozenset({"customers:read"}),
	"customers_get": frozenset({"customers:read"}),
	"customers_lookup_by_ban": frozenset({"customers:read"}),
	# invoices domain (Story 8.3)
	"invoices_list": frozenset({"invoices:read"}),
	"invoices_get": frozenset({"invoices:read"}),
	# purchases domain
	"supplier_invoices_list": frozenset({"purchases:read"}),
	"supplier_invoices_get": frozenset({"purchases:read"}),
	# payments domain
	"payments_list": frozenset({"payments:read"}),
	"payments_get": frozenset({"payments:read"}),
	# intelligence domain (Epic 19)
	"intelligence_product_affinity": frozenset({"intelligence:read"}),
	"intelligence_category_trends": frozenset({"intelligence:read"}),
	"intelligence_customer_product_profile": frozenset({"intelligence:read"}),
	"intelligence_customer_risk_signals": frozenset({"intelligence:read"}),
	"intelligence_prospect_gaps": frozenset({"intelligence:read"}),
	"intelligence_market_opportunities": frozenset({"intelligence:read"}),
}

# ── Default role scope sets (architecture §7.3) ────────────────

DEFAULT_ROLE_SCOPES: dict[str, list[str]] = {
	"admin": ["admin"],
	"owner": ["admin"],
	"finance": [
		"customers:read", "invoices:read", "invoices:write",
		"payments:read", "payments:write", "purchases:read",
	],
	"warehouse": [
		"inventory:read", "inventory:write",
		"orders:read", "purchases:read",
	],
	"sales": [
		"customers:read", "customers:write",
		"invoices:read", "invoices:create",
		"orders:read", "orders:write",
	],
	"agent": [
		"customers:read", "invoices:read", "invoices:create",
		"inventory:read", "orders:read", "intelligence:read",
	],
}


# ── Key parsing ────────────────────────────────────────────────

def parse_api_keys(raw: str) -> dict[str, frozenset[str]]:
	"""Parse MCP_API_KEYS JSON string into key→scopes mapping.

	Expected format: {"key": ["scope1", "scope2"], ...}
	or {"key": {"scopes": [...], "tenant_id": "..."}, ...}
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
	parsed: dict[str, frozenset[str]] = {}
	for key, value in data.items():
		scopes = value.get("scopes") if isinstance(value, dict) else value
		if not isinstance(scopes, list) or not all(isinstance(scope, str) for scope in scopes):
			logger.warning("MCP_API_KEYS entry for %s must contain a scopes array", key)
			continue
		parsed[key] = frozenset(scopes)
	return parsed


def parse_api_key_tenants(raw: str) -> dict[str, str | None]:
	"""Parse optional tenant bindings from MCP_API_KEYS JSON."""
	raw = raw.strip()
	if not raw:
		return {}
	try:
		data = json.loads(raw)
	except json.JSONDecodeError:
		return {raw: None} if raw and raw[0] not in "[{" else {}
	if not isinstance(data, dict):
		return {}

	tenants: dict[str, str | None] = {}
	for key, value in data.items():
		if isinstance(value, dict):
			tenant_id = value.get("tenant_id")
			if tenant_id is not None and not isinstance(tenant_id, str):
				logger.warning("MCP_API_KEYS tenant_id for %s must be a string UUID", key)
				tenant_id = None
			tenants[key] = tenant_id
		else:
			tenants[key] = None
	return tenants


# ── Middleware ─────────────────────────────────────────────────

class ApiKeyAuth(Middleware):
	def __init__(
		self,
		api_keys: dict[str, frozenset[str]],
		tool_scopes: dict[str, frozenset[str]],
		api_key_tenants: dict[str, str | None] | None = None,
	):
		self._api_keys = api_keys
		self._tool_scopes = tool_scopes
		self._api_key_tenants = api_key_tenants or {}

	async def on_call_tool(
		self,
		context: MiddlewareContext,
		call_next,
	) -> Any:
		tool_name = context.message.name

		headers = get_http_headers() or {}
		scopes, tenant_id = self._resolve_identity(headers, tool_name)

		# Admin bypass — "admin" is a meta-scope (architecture §7.3).
		if "admin" in scopes:
			if context.fastmcp_context:
				context.fastmcp_context.set_state("auth_scopes", scopes)
				if tenant_id:
					context.fastmcp_context.set_state("auth_tenant_id", tenant_id)
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

		if tool_name.startswith("intelligence_") and "admin" not in scopes and headers.get("x-api-key"):
			header_tenant = headers.get("x-tenant-id")
			if tenant_id is None or header_tenant is None:
				raise ToolError(json.dumps({
					"code": "TENANT_REQUIRED",
					"message": "A tenant-bound API key and matching X-Tenant-ID header are required for intelligence tools",
					"retry": True,
				}))
			try:
				bound_uuid = uuid.UUID(tenant_id)
				header_uuid = uuid.UUID(header_tenant)
			except (ValueError, TypeError) as exc:
				raise ToolError(json.dumps({
					"code": "INVALID_TENANT",
					"message": "Invalid tenant binding for intelligence tool",
					"retry": False,
				})) from exc
			if header_uuid != bound_uuid:
				raise ToolError(json.dumps({
					"code": "INVALID_TENANT",
					"message": "X-Tenant-ID does not match the API key tenant binding",
					"retry": False,
				}))

		# Attach resolved scopes for downstream tool use.
		if context.fastmcp_context:
			context.fastmcp_context.set_state("auth_scopes", scopes)
			if tenant_id:
				context.fastmcp_context.set_state("auth_tenant_id", tenant_id)

		return await call_next(context)

	def _resolve_identity(self, headers: dict[str, str], tool_name: str) -> tuple[frozenset[str], str | None]:
		api_key = headers.get("x-api-key")
		if api_key:
			scopes = self._api_keys.get(api_key)
			if scopes is None:
				raise ToolError(json.dumps({
					"code": "INVALID_KEY",
					"message": "Invalid API key",
					"retry": True,
				}))

			bound_tenant = self._api_key_tenants.get(api_key)
			return scopes, bound_tenant

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

			tenant_id = payload.get("tenant_id")
			if not isinstance(tenant_id, str) or not tenant_id:
				raise ToolError(json.dumps({
					"code": "INVALID_TOKEN",
					"message": "Invalid or expired Bearer token",
					"retry": True,
				}))

			return frozenset(DEFAULT_ROLE_SCOPES.get(role, ())), tenant_id

		raise ToolError(json.dumps({
			"code": "AUTH_REQUIRED",
			"message": "X-API-Key or Authorization: Bearer header is required",
			"retry": True,
		}))
