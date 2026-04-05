"""Tests for inventory MCP tools (Story 8.1)."""

from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastmcp.exceptions import ToolError

from domains.inventory.mcp import (
    inventory_check,
    inventory_reorder_alerts,
    inventory_search,
)

# @mcp.tool() wraps functions into FunctionTool objects; access .fn for the raw callable.
_check = inventory_check.fn
_search = inventory_search.fn
_alerts = inventory_reorder_alerts.fn

_PRODUCT_ID = str(uuid.uuid4())
_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
_WH_ID = str(uuid.uuid4())

_PRODUCT_DETAIL = {
    "id": _PRODUCT_ID,
    "code": "PROD-001",
    "name": "Test Product",
    "status": "ACTIVE",
    "warehouses": [
        {"warehouse": "Main", "quantity": 42, "reorder_point": 10, "last_adjusted": "2025-01-01"},
    ],
}

_SEARCH_RESULTS = [
    {
        "id": _PRODUCT_ID,
        "code": "PROD-001",
        "name": "Test Product",
        "category": "General",
        "status": "ACTIVE",
        "current_stock": 42,
    },
]

_ALERTS = [
    {
        "product": "Test Product",
        "warehouse": "Main",
        "current_stock": 5,
        "reorder_point": 10,
        "status": "PENDING",
    },
]


class FakeSession:
    """Minimal async context manager that does nothing."""

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


def _patch_session():
    return patch(
        "domains.inventory.mcp.AsyncSessionLocal",
        return_value=FakeSession(),
    )


def _patch_tenant():
    return patch("domains.inventory.mcp.set_tenant", new_callable=AsyncMock)


@pytest.mark.asyncio
async def test_inventory_check_returns_product_detail():
    """AC1: inventory_check returns stock levels for a valid product."""
    with (
        _patch_session(),
        _patch_tenant() as mock_tenant,
        patch(
            "domains.inventory.mcp.get_product_detail",
            new_callable=AsyncMock,
            return_value=_PRODUCT_DETAIL,
        ) as mock_get,
    ):
        result = await _check(product_id=_PRODUCT_ID)

    assert result == _PRODUCT_DETAIL
    mock_tenant.assert_awaited_once()
    mock_get.assert_awaited_once()


@pytest.mark.asyncio
async def test_inventory_check_raises_tool_error_for_missing_product():
    """AC4: inventory_check raises ToolError with structured JSON for not-found."""
    with (
        _patch_session(),
        _patch_tenant(),
        patch(
            "domains.inventory.mcp.get_product_detail",
            new_callable=AsyncMock,
            return_value=None,
        ),
    ):
        with pytest.raises(ToolError) as exc_info:
            await _check(product_id=_PRODUCT_ID)

    error_data = json.loads(str(exc_info.value))
    assert error_data["code"] == "NOT_FOUND"
    assert error_data["entity_type"] == "product"
    assert error_data["entity_id"] == _PRODUCT_ID
    assert error_data["retry"] is False


@pytest.mark.asyncio
async def test_inventory_search_returns_results():
    """AC2: inventory_search returns matching products."""
    with (
        _patch_session(),
        _patch_tenant(),
        patch(
            "domains.inventory.mcp.search_products",
            new_callable=AsyncMock,
            return_value=_SEARCH_RESULTS,
        ),
    ):
        result = await _search(query="PROD", limit=20)

    assert result == _SEARCH_RESULTS


@pytest.mark.asyncio
async def test_inventory_search_empty_results():
    """AC2: inventory_search returns empty list for no matches."""
    with (
        _patch_session(),
        _patch_tenant(),
        patch("domains.inventory.mcp.search_products", new_callable=AsyncMock, return_value=[]),
    ):
        result = await _search(query="NONEXISTENT")

    assert result == []


@pytest.mark.asyncio
async def test_inventory_reorder_alerts_returns_alerts():
    """AC3: inventory_reorder_alerts returns low-stock alerts."""
    with (
        _patch_session(),
        _patch_tenant(),
        patch(
            "domains.inventory.mcp.list_reorder_alerts",
            new_callable=AsyncMock,
            return_value=(_ALERTS, 1),
        ),
    ):
        result = await _alerts()

    assert result["alerts"] == _ALERTS
    assert result["total"] == 1


@pytest.mark.asyncio
async def test_inventory_reorder_alerts_with_filters():
    """AC3: inventory_reorder_alerts filters by status and warehouse."""
    with (
        _patch_session(),
        _patch_tenant(),
        patch(
            "domains.inventory.mcp.list_reorder_alerts",
            new_callable=AsyncMock,
            return_value=([], 0),
        ) as mock_alerts,
    ):
        result = await _alerts(
            status_filter="PENDING",
            warehouse_id=_WH_ID,
        )

    assert result["alerts"] == []
    assert result["total"] == 0
    call_kwargs = mock_alerts.call_args[1]
    assert call_kwargs["status_filter"] == "PENDING"
    assert call_kwargs["warehouse_id"] == uuid.UUID(_WH_ID)
