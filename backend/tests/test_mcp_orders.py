"""Tests for order MCP tools."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from fastmcp.exceptions import ToolError

from domains.orders.mcp import orders_get, orders_list
from domains.orders.services import derive_order_execution

_list_fn = orders_list
_get_fn = orders_get

_ORDER_ID = str(uuid.uuid4())
_CUSTOMER_ID = str(uuid.uuid4())
_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


@dataclass
class FakeCustomer:
    company_name: str = "Acme Corp"


@dataclass
class FakeLine:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    product_id: uuid.UUID = field(default_factory=uuid.uuid4)
    line_number: int = 1
    description: str = "Widget"
    quantity: Decimal = Decimal("2.000")
    list_unit_price: Decimal = Decimal("600.00")
    unit_price: Decimal = Decimal("500.00")
    discount_amount: Decimal = Decimal("100.00")
    tax_policy_code: str = "taxable"
    tax_type: int = 1
    tax_rate: Decimal = Decimal("0.05")
    tax_amount: Decimal = Decimal("50.00")
    subtotal_amount: Decimal = Decimal("1000.00")
    total_amount: Decimal = Decimal("1050.00")
    available_stock_snapshot: int | None = 10
    backorder_note: str | None = None


@dataclass
class FakeOrder:
    id: uuid.UUID = field(default_factory=lambda: uuid.UUID(_ORDER_ID))
    tenant_id: uuid.UUID = _TENANT_ID
    customer_id: uuid.UUID = field(default_factory=lambda: uuid.UUID(_CUSTOMER_ID))
    order_number: str = "ORD-20260411-ABC123DEF456"
    status: str = "pending"
    payment_terms_code: str = "NET_30"
    payment_terms_days: int = 30
    subtotal_amount: Decimal = Decimal("1000.00")
    discount_amount: Decimal = Decimal("100.00")
    discount_percent: Decimal = Decimal("0.1000")
    tax_amount: Decimal = Decimal("50.00")
    total_amount: Decimal = Decimal("1050.00")
    invoice_id: uuid.UUID | None = None
    invoice_number: str | None = "INV-20260411-0001"
    invoice_payment_status: str | None = "paid"
    sales_team: list[dict] = field(
        default_factory=lambda: [
            {
                "sales_person": "Alice Chen",
                "allocated_percentage": "100.00",
                "commission_rate": "5.00",
                "allocated_amount": "50.00",
            }
        ]
    )
    total_commission: Decimal = Decimal("50.00")
    notes: str | None = "Priority order"
    legacy_header_snapshot: dict | None = field(default_factory=lambda: {"source": "legacy"})
    created_by: str = "system"
    created_at: datetime = field(default_factory=lambda: datetime(2026, 4, 11, 9, 0, 0))
    updated_at: datetime = field(default_factory=lambda: datetime(2026, 4, 11, 9, 0, 0))
    confirmed_at: datetime | None = None
    customer: FakeCustomer | None = field(default_factory=FakeCustomer)
    lines: list[FakeLine] = field(default_factory=lambda: [FakeLine()])
    execution: dict = field(init=False)

    def __post_init__(self) -> None:
        self.execution = derive_order_execution(
            self,
            invoice_payment_status=self.invoice_payment_status,
        )


class FakeSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


def _patch_session():
    return patch("domains.orders.mcp.AsyncSessionLocal", return_value=FakeSession())


@pytest.mark.asyncio
async def test_orders_list_returns_paginated_results():
    fake_order = FakeOrder()
    with (
        _patch_session(),
        patch(
            "domains.orders.mcp.list_orders",
            new_callable=AsyncMock,
            return_value=([fake_order], 1),
        ),
    ):
        result = await _list_fn(status="pending", customer_id=_CUSTOMER_ID, page=2, page_size=10)

    assert result["total"] == 1
    assert result["page"] == 2
    assert result["orders"][0]["id"] == _ORDER_ID
    assert result["orders"][0]["legacy_header_snapshot"] == {"source": "legacy"}
    assert result["orders"][0]["sales_team"] == fake_order.sales_team
    assert result["orders"][0]["total_commission"] == "50.00"
    assert result["orders"][0]["invoice_number"] == "INV-20260411-0001"
    assert result["orders"][0]["invoice_payment_status"] == "paid"
    assert result["orders"][0]["execution"] == fake_order.execution


@pytest.mark.asyncio
async def test_orders_get_returns_detail():
    fake_order = FakeOrder()
    with (
        _patch_session(),
        patch(
            "domains.orders.mcp.get_order",
            new_callable=AsyncMock,
            return_value=fake_order,
        ),
    ):
        result = await _get_fn(order_id=_ORDER_ID)

    assert result["id"] == _ORDER_ID
    assert result["customer_name"] == "Acme Corp"
    assert result["lines"][0]["description"] == "Widget"
    assert result["sales_team"] == fake_order.sales_team
    assert result["total_commission"] == "50.00"
    assert result["invoice_number"] == "INV-20260411-0001"
    assert result["invoice_payment_status"] == "paid"
    assert result["execution"] == fake_order.execution


@pytest.mark.asyncio
async def test_orders_get_raises_not_found():
    with (
        _patch_session(),
        patch(
            "domains.orders.mcp.get_order",
            new_callable=AsyncMock,
            side_effect=HTTPException(status_code=404, detail="Order not found."),
        ),
    ):
        with pytest.raises(ToolError) as exc_info:
            await _get_fn(order_id=_ORDER_ID)

    error = json.loads(str(exc_info.value))
    assert error["code"] == "NOT_FOUND"
    assert error["entity_type"] == "order"
    assert error["entity_id"] == _ORDER_ID