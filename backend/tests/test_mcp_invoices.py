"""Tests for invoice MCP tools (Story 8.3)."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from fastmcp.exceptions import ToolError

from domains.invoices.mcp import invoices_get, invoices_list

# Access underlying function from FunctionTool wrapper.
_list_fn = invoices_list.fn
_get_fn = invoices_get.fn

_INV_ID = str(uuid.uuid4())
_CUST_ID = str(uuid.uuid4())

_LIST_RESULT = [
    {
        "id": uuid.UUID(_INV_ID),
        "invoice_number": "AB12345678",
        "invoice_date": date(2025, 1, 1),
        "customer_id": uuid.UUID(_CUST_ID),
        "currency_code": "TWD",
        "total_amount": Decimal("1000.00"),
        "status": "issued",
        "created_at": date(2025, 1, 1),
        "amount_paid": Decimal("0.00"),
        "outstanding_balance": Decimal("1000.00"),
        "payment_status": "unpaid",
        "due_date": date(2025, 2, 1),
        "days_overdue": 0,
    },
]

_PAYMENT_SUMMARY = {
    "amount_paid": Decimal("400.00"),
    "outstanding_balance": Decimal("600.00"),
    "payment_status": "partial",
    "due_date": date(2025, 2, 1),
    "days_overdue": 0,
}


@dataclass
class FakeLine:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    line_number: int = 1
    description: str = "Widget"
    quantity: Decimal = Decimal("2.000")
    unit_price: Decimal = Decimal("500.00")
    subtotal_amount: Decimal = Decimal("1000.00")
    tax_amount: Decimal = Decimal("50.00")
    total_amount: Decimal = Decimal("1050.00")


@dataclass
class FakeInvoice:
    id: uuid.UUID = field(default_factory=lambda: uuid.UUID(_INV_ID))
    invoice_number: str = "AB12345678"
    customer_id: uuid.UUID = field(default_factory=lambda: uuid.UUID(_CUST_ID))
    order_id: uuid.UUID | None = None
    status: str = "issued"
    invoice_date: date = field(default_factory=lambda: date(2025, 1, 1))
    subtotal_amount: Decimal = Decimal("1000.00")
    tax_amount: Decimal = Decimal("50.00")
    total_amount: Decimal = Decimal("1050.00")
    lines: list = field(default_factory=lambda: [FakeLine()])


class FakeSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


def _patch_session():
    return patch("domains.invoices.mcp.AsyncSessionLocal", return_value=FakeSession())


def _patch_tenant():
    return patch("domains.invoices.mcp.set_tenant", new_callable=AsyncMock)


# ── Tests ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_invoices_list_returns_paginated_results():
    """AC1: invoices_list returns paginated invoice list."""
    with (
        _patch_session(),
        patch(
            "domains.invoices.mcp.list_invoices",
            new_callable=AsyncMock,
            return_value=(_LIST_RESULT, 1),
        ),
    ):
        result = await _list_fn()

    assert result["total"] == 1
    assert result["page"] == 1
    assert len(result["invoices"]) == 1
    inv = result["invoices"][0]
    assert inv["id"] == _INV_ID
    assert inv["total_amount"] == "1000.00"
    assert inv["invoice_date"] == "2025-01-01"


@pytest.mark.asyncio
async def test_invoices_list_with_payment_status_filter():
    """AC1/AC4: invoices_list passes payment_status filter."""
    with (
        _patch_session(),
        patch(
            "domains.invoices.mcp.list_invoices",
            new_callable=AsyncMock,
            return_value=([], 0),
        ) as mock_list,
    ):
        result = await _list_fn(payment_status="overdue", page=2, page_size=10)

    assert result["total"] == 0
    mock_list.assert_awaited_once()
    call_kwargs = mock_list.call_args[1]
    assert call_kwargs["payment_status"] == "overdue"
    assert call_kwargs["page"] == 2


@pytest.mark.asyncio
async def test_invoices_get_returns_invoice_with_payment():
    """AC2/AC4: invoices_get returns full invoice with line items and payment summary."""
    fake_inv = FakeInvoice()
    with (
        _patch_session(),
        _patch_tenant(),
        patch(
            "domains.invoices.mcp.get_invoice",
            new_callable=AsyncMock,
            return_value=fake_inv,
        ),
        patch(
            "domains.invoices.mcp.compute_invoice_payment_summary",
            new_callable=AsyncMock,
            return_value=_PAYMENT_SUMMARY,
        ),
    ):
        result = await _get_fn(invoice_id=_INV_ID)

    assert result["id"] == _INV_ID
    assert result["invoice_number"] == "AB12345678"
    assert result["payment_status"] == "partial"
    assert result["amount_paid"] == "400.00"
    assert result["outstanding_balance"] == "600.00"
    assert len(result["line_items"]) == 1
    assert result["line_items"][0]["description"] == "Widget"


@pytest.mark.asyncio
async def test_invoices_get_includes_payment_summary_fields():
    """AC4: invoices_get payment enrichment includes all required fields."""
    fake_inv = FakeInvoice()
    with (
        _patch_session(),
        _patch_tenant(),
        patch(
            "domains.invoices.mcp.get_invoice",
            new_callable=AsyncMock,
            return_value=fake_inv,
        ),
        patch(
            "domains.invoices.mcp.compute_invoice_payment_summary",
            new_callable=AsyncMock,
            return_value=_PAYMENT_SUMMARY,
        ),
    ):
        result = await _get_fn(invoice_id=_INV_ID)

    assert "amount_paid" in result
    assert "outstanding_balance" in result
    assert "payment_status" in result
    assert "due_date" in result
    assert "days_overdue" in result


@pytest.mark.asyncio
async def test_invoices_get_raises_not_found():
    """AC3: invoices_get raises ToolError for non-existent invoice."""
    with (
        _patch_session(),
        _patch_tenant(),
        patch("domains.invoices.mcp.get_invoice", new_callable=AsyncMock, return_value=None),
    ):
        with pytest.raises(ToolError) as exc_info:
            await _get_fn(invoice_id=_INV_ID)

    error = json.loads(str(exc_info.value))
    assert error["code"] == "NOT_FOUND"
    assert error["entity_type"] == "invoice"
    assert error["entity_id"] == _INV_ID
    assert error["retry"] is False
