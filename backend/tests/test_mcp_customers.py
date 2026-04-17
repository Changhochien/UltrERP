"""Tests for customer MCP tools (Story 8.2)."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from fastmcp.exceptions import ToolError

from common.errors import ValidationError, VersionConflictError
from domains.customers.mcp import (
    customers_get,
    customers_list,
    customers_lookup_by_ban,
    customers_update,
)

# FastMCP 3.x exports decorated tools as plain async callables in tests,
# while older wrappers exposed the underlying coroutine via `.fn`.
_list_fn = getattr(customers_list, "fn", customers_list)
_get_fn = getattr(customers_get, "fn", customers_get)
_lookup_fn = getattr(customers_lookup_by_ban, "fn", customers_lookup_by_ban)
_update_fn = getattr(customers_update, "fn", customers_update)

_CID = str(uuid.uuid4())
_NOW = datetime.now(tz=UTC)


@dataclass
class FakeCustomer:
    """Minimal Customer stand-in for serialization tests."""

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    company_name: str = "Test Corp"
    normalized_business_number: str = "12345675"
    billing_address: str = "Taipei"
    contact_name: str = "Jane"
    contact_phone: str = "02-12345678"
    contact_email: str = "jane@test.com"
    credit_limit: Decimal = Decimal("50000.00")
    status: str = "active"
    customer_type: str = "unknown"
    version: int = 1
    created_at: datetime = field(default_factory=lambda: _NOW)
    updated_at: datetime = field(default_factory=lambda: _NOW)


class FakeSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


def _patch_session():
    return patch("domains.customers.mcp.AsyncSessionLocal", return_value=FakeSession())


def _patch_headers(tenant_id: str = "00000000-0000-0000-0000-000000000001"):
    return patch("domains.customers.mcp.get_http_headers", return_value={"x-tenant-id": tenant_id})


@dataclass
class FakeValidationResult:
    valid: bool
    error: str | None = None


# ── Tests ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_customers_list_returns_paginated_results():
    """AC1: customers_list returns paginated customer list."""
    fake = FakeCustomer()
    with (
        _patch_session(),
        _patch_headers(),
        patch(
            "domains.customers.mcp.list_customers",
            new_callable=AsyncMock,
            return_value=([fake], 1),
        ),
    ):
        result = await _list_fn()

    assert result["total"] == 1
    assert result["page"] == 1
    assert len(result["customers"]) == 1
    assert result["customers"][0]["company_name"] == "Test Corp"


@pytest.mark.asyncio
async def test_customers_list_with_search():
    """AC1: customers_list passes search parameter correctly."""
    with (
        _patch_session(),
        _patch_headers(),
        patch(
            "domains.customers.mcp.list_customers",
            new_callable=AsyncMock,
            return_value=([], 0),
        ) as mock_list,
    ):
        result = await _list_fn(search="Test", status="active", page=2, page_size=10)

    assert result["total"] == 0
    params = mock_list.call_args[0][1]
    assert params.q == "Test"
    assert params.status == "active"
    assert params.page == 2
    assert mock_list.call_args[0][2] == uuid.UUID("00000000-0000-0000-0000-000000000001")


@pytest.mark.asyncio
async def test_customers_get_returns_customer():
    """AC2: customers_get returns full customer details."""
    fake = FakeCustomer(id=uuid.UUID(_CID))
    with (
        _patch_session(),
        _patch_headers(),
        patch("domains.customers.mcp.get_customer", new_callable=AsyncMock, return_value=fake),
    ):
        result = await _get_fn(customer_id=_CID)

    assert result["id"] == _CID
    assert result["company_name"] == "Test Corp"
    assert result["credit_limit"] == "50000.00"


@pytest.mark.asyncio
async def test_customers_get_raises_not_found():
    """AC4: customers_get raises ToolError for non-existent ID."""
    with (
        _patch_session(),
        _patch_headers(),
        patch("domains.customers.mcp.get_customer", new_callable=AsyncMock, return_value=None),
    ):
        with pytest.raises(ToolError) as exc_info:
            await _get_fn(customer_id=_CID)

    error = json.loads(str(exc_info.value))
    assert error["code"] == "NOT_FOUND"
    assert error["entity_type"] == "customer"


@pytest.mark.asyncio
async def test_customers_lookup_by_ban_returns_customer():
    """AC3: customers_lookup_by_ban returns customer for valid BAN."""
    fake = FakeCustomer()
    with (
        _patch_session(),
        _patch_headers(),
        patch(
            "domains.customers.mcp.validate_taiwan_business_number",
            return_value=FakeValidationResult(valid=True),
        ),
        patch(
            "domains.customers.mcp.lookup_customer_by_ban",
            new_callable=AsyncMock,
            return_value=fake,
        ),
    ):
        result = await _lookup_fn(business_number="12345675")

    assert result["company_name"] == "Test Corp"


@pytest.mark.asyncio
async def test_customers_lookup_by_ban_invalid_checksum():
    """AC3: customers_lookup_by_ban raises VALIDATION_ERROR for invalid BAN."""
    with (
        patch(
            "domains.customers.mcp.validate_taiwan_business_number",
            return_value=FakeValidationResult(valid=False, error="Bad checksum"),
        ),
    ):
        with pytest.raises(ToolError) as exc_info:
            await _lookup_fn(business_number="00000000")

    error = json.loads(str(exc_info.value))
    assert error["code"] == "VALIDATION_ERROR"
    assert error["field"] == "business_number"


@pytest.mark.asyncio
async def test_customers_lookup_by_ban_not_found():
    """AC3: customers_lookup_by_ban raises NOT_FOUND for valid but non-existent BAN."""
    with (
        _patch_session(),
        _patch_headers(),
        patch(
            "domains.customers.mcp.validate_taiwan_business_number",
            return_value=FakeValidationResult(valid=True),
        ),
        patch(
            "domains.customers.mcp.lookup_customer_by_ban",
            new_callable=AsyncMock,
            return_value=None,
        ),
    ):
        with pytest.raises(ToolError) as exc_info:
            await _lookup_fn(business_number="12345675")

    error = json.loads(str(exc_info.value))
    assert error["code"] == "NOT_FOUND"
    assert error["entity_type"] == "customer"


@pytest.mark.asyncio
async def test_customers_update_updates_customer_type():
    fake = FakeCustomer(id=uuid.UUID(_CID), customer_type="unknown")
    updated = FakeCustomer(id=uuid.UUID(_CID), customer_type="dealer", version=2)
    with (
        _patch_session(),
        _patch_headers(),
        patch("domains.customers.mcp.get_customer", new_callable=AsyncMock, return_value=fake),
        patch("domains.customers.mcp.update_customer", new_callable=AsyncMock, return_value=updated) as mock_update,
    ):
        result = await _update_fn(customer_id=_CID, customer_type="dealer")

    assert result == {
        "success": True,
        "customer_id": _CID,
        "customer_type": "dealer",
    }
    payload = mock_update.await_args.args[2]
    assert payload.customer_type == "dealer"
    assert payload.version == 1
    assert mock_update.await_args.args[3] == uuid.UUID("00000000-0000-0000-0000-000000000001")


@pytest.mark.asyncio
async def test_customers_update_rejects_invalid_customer_type():
    with _patch_headers():
        with pytest.raises(ToolError) as exc_info:
            await _update_fn(customer_id=_CID, customer_type="reseller")

    error = json.loads(str(exc_info.value))
    assert error["code"] == "VALIDATION_ERROR"
    assert error["field"] == "customer_type"


@pytest.mark.asyncio
async def test_customers_update_respects_tenant_scope():
    with (
        _patch_session(),
        _patch_headers("00000000-0000-0000-0000-000000000123"),
        patch("domains.customers.mcp.get_customer", new_callable=AsyncMock, return_value=None) as mock_get,
    ):
        with pytest.raises(ToolError) as exc_info:
            await _update_fn(customer_id=_CID, customer_type="dealer")

    error = json.loads(str(exc_info.value))
    assert error["code"] == "NOT_FOUND"
    assert mock_get.await_args.args[2] == uuid.UUID("00000000-0000-0000-0000-000000000123")


@pytest.mark.asyncio
async def test_customers_update_translates_version_conflict_to_tool_error():
    fake = FakeCustomer(id=uuid.UUID(_CID), customer_type="unknown")
    with (
        _patch_session(),
        _patch_headers(),
        patch("domains.customers.mcp.get_customer", new_callable=AsyncMock, return_value=fake),
        patch(
            "domains.customers.mcp.update_customer",
            new_callable=AsyncMock,
            side_effect=VersionConflictError(expected=1, actual=2),
        ),
    ):
        with pytest.raises(ToolError) as exc_info:
            await _update_fn(customer_id=_CID, customer_type="dealer")

    error = json.loads(str(exc_info.value))
    assert error["code"] == "VERSION_CONFLICT"
    assert error["entity_type"] == "customer"
    assert error["entity_id"] == _CID
    assert error["expected_version"] == 1
    assert error["actual_version"] == 2
    assert error["retry"] is True


@pytest.mark.asyncio
async def test_customers_update_translates_validation_error_to_tool_error():
    fake = FakeCustomer(id=uuid.UUID(_CID), customer_type="unknown")
    with (
        _patch_session(),
        _patch_headers(),
        patch("domains.customers.mcp.get_customer", new_callable=AsyncMock, return_value=fake),
        patch(
            "domains.customers.mcp.update_customer",
            new_callable=AsyncMock,
            side_effect=ValidationError([
                {"field": "customer_type", "message": "invalid"},
            ]),
        ),
    ):
        with pytest.raises(ToolError) as exc_info:
            await _update_fn(customer_id=_CID, customer_type="dealer")

    error = json.loads(str(exc_info.value))
    assert error["code"] == "VALIDATION_ERROR"
    assert error["entity_type"] == "customer"
    assert error["entity_id"] == _CID
    assert error["errors"] == [{"field": "customer_type", "message": "invalid"}]
    assert error["retry"] is False
