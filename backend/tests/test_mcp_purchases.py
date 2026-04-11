"""Tests for purchases MCP tools."""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from fastmcp.exceptions import ToolError

from domains.purchases.mcp import supplier_invoices_get, supplier_invoices_list

_list_fn = supplier_invoices_list
_get_fn = supplier_invoices_get

_INVOICE_ID = str(uuid.uuid4())
_SUPPLIER_ID = str(uuid.uuid4())

_LIST_ITEM = {
    "id": uuid.UUID(_INVOICE_ID),
    "supplier_id": uuid.UUID(_SUPPLIER_ID),
    "supplier_name": "Acme Supply",
    "invoice_number": "PI-001",
    "invoice_date": date(2026, 4, 1),
    "currency_code": "TWD",
    "total_amount": Decimal("2500.00"),
    "remaining_payable_amount": Decimal("1000.00"),
    "status": "open",
    "legacy_header_snapshot": {"source": "legacy"},
    "created_at": datetime(2026, 4, 1, 9, 0, 0),
    "updated_at": datetime(2026, 4, 1, 9, 0, 0),
    "line_count": 2,
}

_DETAIL = {
    "id": uuid.UUID(_INVOICE_ID),
    "supplier_id": uuid.UUID(_SUPPLIER_ID),
    "supplier_name": "Acme Supply",
    "invoice_number": "PI-001",
    "invoice_date": date(2026, 4, 1),
    "currency_code": "TWD",
    "subtotal_amount": Decimal("2400.00"),
    "tax_amount": Decimal("100.00"),
    "total_amount": Decimal("2500.00"),
    "remaining_payable_amount": Decimal("1000.00"),
    "status": "open",
    "notes": None,
    "legacy_header_snapshot": {"source": "legacy"},
    "created_at": datetime(2026, 4, 1, 9, 0, 0),
    "updated_at": datetime(2026, 4, 1, 9, 0, 0),
    "lines": [
        {
            "id": uuid.uuid4(),
            "line_number": 1,
            "product_id": None,
            "product_code_snapshot": "P-001",
            "product_name": "Widget",
            "description": "Widget",
            "quantity": Decimal("2.000"),
            "unit_price": Decimal("1200.00"),
            "subtotal_amount": Decimal("2400.00"),
            "tax_type": 1,
            "tax_rate": Decimal("0.05"),
            "tax_amount": Decimal("100.00"),
            "total_amount": Decimal("2500.00"),
            "created_at": datetime(2026, 4, 1, 9, 0, 0),
        }
    ],
}


class FakeSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


def _patch_session():
    return patch("domains.purchases.mcp.AsyncSessionLocal", return_value=FakeSession())


def _patch_tenant():
    return patch("domains.purchases.mcp.set_tenant", new_callable=AsyncMock)


@pytest.mark.asyncio
async def test_supplier_invoices_list_returns_results():
    with (
        _patch_session(),
        patch(
            "domains.purchases.mcp.list_supplier_invoices",
            new_callable=AsyncMock,
            return_value=([_LIST_ITEM], 1, {"open": 1, "paid": 0, "voided": 0}),
        ),
    ):
        result = await _list_fn(status_filter="open", supplier_id=_SUPPLIER_ID)

    assert result["total"] == 1
    assert result["supplier_invoices"][0]["id"] == _INVOICE_ID
    assert result["status_totals"]["open"] == 1


@pytest.mark.asyncio
async def test_supplier_invoices_get_returns_detail():
    with (
        _patch_session(),
        _patch_tenant() as mock_tenant,
        patch(
            "domains.purchases.mcp.get_supplier_invoice",
            new_callable=AsyncMock,
            return_value=_DETAIL,
        ),
    ):
        result = await _get_fn(invoice_id=_INVOICE_ID)

    assert result["id"] == _INVOICE_ID
    assert result["lines"][0]["description"] == "Widget"
    mock_tenant.assert_awaited_once()


@pytest.mark.asyncio
async def test_supplier_invoices_get_raises_not_found():
    with (
        _patch_session(),
        _patch_tenant(),
        patch(
            "domains.purchases.mcp.get_supplier_invoice",
            new_callable=AsyncMock,
            return_value=None,
        ),
    ):
        with pytest.raises(ToolError) as exc_info:
            await _get_fn(invoice_id=_INVOICE_ID)

    error = json.loads(str(exc_info.value))
    assert error["code"] == "NOT_FOUND"
    assert error["entity_type"] == "supplier_invoice"
    assert error["entity_id"] == _INVOICE_ID