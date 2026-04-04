"""Tests for MCP API key authentication middleware (Story 8.4)."""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from fastmcp.exceptions import ToolError

from app.mcp_auth import TOOL_SCOPES, ApiKeyAuth, parse_api_keys
from common.config import settings

# ── parse_api_keys tests ───────────────────────────────────────


def test_parse_api_keys_valid_json():
	"""AC6: parse_api_keys parses valid JSON correctly."""
	raw = '{"key1": ["customers:read", "invoices:read"], "key2": ["admin"]}'
	result = parse_api_keys(raw)
	assert result == {
		"key1": frozenset({"customers:read", "invoices:read"}),
		"key2": frozenset({"admin"}),
	}


def test_parse_api_keys_empty_string():
	"""AC6: parse_api_keys returns empty dict for empty string."""
	assert parse_api_keys("") == {}


def test_parse_api_keys_invalid_json_returns_empty_dict():
	"""parse_api_keys logs warning and returns empty dict on malformed JSON."""
	result = parse_api_keys("{bad json}")
	assert result == {}


# ── Middleware tests ───────────────────────────────────────────

_TEST_KEYS = {
	"valid-admin": frozenset({"admin"}),
	"valid-agent": frozenset({"customers:read", "invoices:read", "inventory:read", "orders:read"}),
	"valid-narrow": frozenset({"customers:read"}),
}


def _make_context(tool_name: str) -> MagicMock:
	ctx = MagicMock()
	ctx.message.name = tool_name
	return ctx


def _make_jwt(role: str = "owner", *, expires_at: datetime | None = None) -> str:
	payload = {
		"sub": "test-user-id",
		"tenant_id": "00000000-0000-0000-0000-000000000001",
		"role": role,
		"exp": expires_at or (datetime.now(tz=UTC) + timedelta(hours=1)),
	}
	return jwt.encode(
		payload,
		settings.jwt_secret,
		algorithm="HS256",
	)


@pytest.mark.asyncio
async def test_missing_api_key_returns_auth_required():
	"""AC2: Missing API key returns AUTH_REQUIRED."""
	mw = ApiKeyAuth(api_keys=_TEST_KEYS, tool_scopes=TOOL_SCOPES)
	ctx = _make_context("inventory_check")

	with patch("app.mcp_auth.get_http_headers", return_value={}):
		with pytest.raises(ToolError) as exc_info:
			await mw.on_call_tool(ctx, AsyncMock())

	error = json.loads(str(exc_info.value))
	assert error["code"] == "AUTH_REQUIRED"
	assert error["retry"] is True


@pytest.mark.asyncio
async def test_invalid_api_key_returns_invalid_key():
	"""AC3: Unknown API key returns INVALID_KEY."""
	mw = ApiKeyAuth(api_keys=_TEST_KEYS, tool_scopes=TOOL_SCOPES)
	ctx = _make_context("inventory_check")

	with patch("app.mcp_auth.get_http_headers", return_value={"x-api-key": "bad-key"}):
		with pytest.raises(ToolError) as exc_info:
			await mw.on_call_tool(ctx, AsyncMock())

	error = json.loads(str(exc_info.value))
	assert error["code"] == "INVALID_KEY"
	assert error["retry"] is True


@pytest.mark.asyncio
async def test_insufficient_scope_returns_error():
	"""AC4: Valid key with wrong scope returns INSUFFICIENT_SCOPE."""
	mw = ApiKeyAuth(api_keys=_TEST_KEYS, tool_scopes=TOOL_SCOPES)
	ctx = _make_context("inventory_check")  # requires inventory:read

	with patch("app.mcp_auth.get_http_headers", return_value={"x-api-key": "valid-narrow"}):
		with pytest.raises(ToolError) as exc_info:
			await mw.on_call_tool(ctx, AsyncMock())

	error = json.loads(str(exc_info.value))
	assert error["code"] == "INSUFFICIENT_SCOPE"
	assert "inventory:read" in error["required_scope"]
	assert "customers:read" in error["token_scopes"]


@pytest.mark.asyncio
async def test_valid_key_with_correct_scope_allows_call():
	"""AC5: Valid key with correct scope passes through."""
	mw = ApiKeyAuth(api_keys=_TEST_KEYS, tool_scopes=TOOL_SCOPES)
	ctx = _make_context("customers_list")  # requires customers:read
	call_next = AsyncMock(return_value="ok")

	with patch("app.mcp_auth.get_http_headers", return_value={"x-api-key": "valid-narrow"}):
		result = await mw.on_call_tool(ctx, call_next)

	assert result == "ok"
	call_next.assert_awaited_once_with(ctx)


@pytest.mark.asyncio
async def test_admin_key_bypasses_scope_check():
	"""AC7: Admin meta-scope bypasses per-tool scope check."""
	mw = ApiKeyAuth(api_keys=_TEST_KEYS, tool_scopes=TOOL_SCOPES)
	ctx = _make_context("inventory_check")  # admin shouldn't need inventory:read
	call_next = AsyncMock(return_value="admin-ok")

	with patch("app.mcp_auth.get_http_headers", return_value={"x-api-key": "valid-admin"}):
		result = await mw.on_call_tool(ctx, call_next)

	assert result == "admin-ok"
	call_next.assert_awaited_once_with(ctx)


@pytest.mark.asyncio
async def test_tool_without_scope_mapping_is_accessible():
	"""Tools not in TOOL_SCOPES are accessible to any valid key."""
	mw = ApiKeyAuth(api_keys=_TEST_KEYS, tool_scopes=TOOL_SCOPES)
	ctx = _make_context("some_future_tool")  # not in TOOL_SCOPES
	call_next = AsyncMock(return_value="future-ok")

	with patch("app.mcp_auth.get_http_headers", return_value={"x-api-key": "valid-narrow"}):
		result = await mw.on_call_tool(ctx, call_next)

	assert result == "future-ok"


@pytest.mark.asyncio
async def test_jwt_bearer_token_accepted():
	"""JWT Bearer token grants access when API key is absent."""
	mw = ApiKeyAuth(api_keys=_TEST_KEYS, tool_scopes=TOOL_SCOPES)
	ctx = _make_context("inventory_check")
	call_next = AsyncMock(return_value="jwt-ok")
	jwt_token = _make_jwt("warehouse")

	with patch(
		"app.mcp_auth.get_http_headers",
		return_value={"authorization": f"Bearer {jwt_token}"},
	):
		result = await mw.on_call_tool(ctx, call_next)

	assert result == "jwt-ok"
	call_next.assert_awaited_once_with(ctx)


@pytest.mark.asyncio
async def test_jwt_warehouse_cannot_access_invoices():
	"""Warehouse role is mapped to inventory/orders scopes only."""
	mw = ApiKeyAuth(api_keys=_TEST_KEYS, tool_scopes=TOOL_SCOPES)
	ctx = _make_context("invoices_list")
	jwt_token = _make_jwt("warehouse")

	with patch(
		"app.mcp_auth.get_http_headers",
		return_value={"authorization": f"Bearer {jwt_token}"},
	):
		with pytest.raises(ToolError) as exc_info:
			await mw.on_call_tool(ctx, AsyncMock())

	error = json.loads(str(exc_info.value))
	assert error["code"] == "INSUFFICIENT_SCOPE"
	assert "invoices:read" in error["required_scope"]
	assert "inventory:read" in error["token_scopes"]


@pytest.mark.asyncio
async def test_jwt_owner_bypasses_scope_check():
	"""Owner JWT maps to admin scope and bypasses tool-level checks."""
	mw = ApiKeyAuth(api_keys=_TEST_KEYS, tool_scopes=TOOL_SCOPES)
	ctx = _make_context("invoices_get")
	call_next = AsyncMock(return_value="owner-ok")
	jwt_token = _make_jwt("owner")

	with patch(
		"app.mcp_auth.get_http_headers",
		return_value={"authorization": f"Bearer {jwt_token}"},
	):
		result = await mw.on_call_tool(ctx, call_next)

	assert result == "owner-ok"
	call_next.assert_awaited_once_with(ctx)


@pytest.mark.asyncio
async def test_jwt_expired_token_rejected():
	"""Expired JWTs are rejected with INVALID_TOKEN."""
	mw = ApiKeyAuth(api_keys=_TEST_KEYS, tool_scopes=TOOL_SCOPES)
	ctx = _make_context("inventory_check")
	jwt_token = _make_jwt("warehouse", expires_at=datetime.now(tz=UTC) - timedelta(minutes=1))

	with patch(
		"app.mcp_auth.get_http_headers",
		return_value={"authorization": f"Bearer {jwt_token}"},
	):
		with pytest.raises(ToolError) as exc_info:
			await mw.on_call_tool(ctx, AsyncMock())

	error = json.loads(str(exc_info.value))
	assert error["code"] == "INVALID_TOKEN"


@pytest.mark.asyncio
async def test_jwt_invalid_token_rejected():
	"""Malformed JWTs are rejected with INVALID_TOKEN."""
	mw = ApiKeyAuth(api_keys=_TEST_KEYS, tool_scopes=TOOL_SCOPES)
	ctx = _make_context("inventory_check")

	with patch("app.mcp_auth.get_http_headers", return_value={"authorization": "Bearer not-a-jwt"}):
		with pytest.raises(ToolError) as exc_info:
			await mw.on_call_tool(ctx, AsyncMock())

	error = json.loads(str(exc_info.value))
	assert error["code"] == "INVALID_TOKEN"


@pytest.mark.asyncio
async def test_api_key_takes_precedence_over_jwt():
	"""When both headers are present, X-API-Key remains authoritative."""
	mw = ApiKeyAuth(api_keys=_TEST_KEYS, tool_scopes=TOOL_SCOPES)
	ctx = _make_context("inventory_check")
	jwt_token = _make_jwt("owner")

	with patch(
		"app.mcp_auth.get_http_headers",
		return_value={
			"x-api-key": "valid-narrow",
			"authorization": f"Bearer {jwt_token}",
		},
	):
		with pytest.raises(ToolError) as exc_info:
			await mw.on_call_tool(ctx, AsyncMock())

	error = json.loads(str(exc_info.value))
	assert error["code"] == "INSUFFICIENT_SCOPE"
	assert "customers:read" in error["token_scopes"]
