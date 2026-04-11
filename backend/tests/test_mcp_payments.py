"""Tests for payment MCP tools."""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from fastmcp.exceptions import ToolError

from domains.payments.mcp import payments_get, payments_list

_list_fn = payments_list
_get_fn = payments_get

_PAYMENT_ID = str(uuid.uuid4())
_INVOICE_ID = str(uuid.uuid4())
_CUSTOMER_ID = str(uuid.uuid4())


class FakePayment:
    def __init__(self) -> None:
        self.id = uuid.UUID(_PAYMENT_ID)
        self.invoice_id = uuid.UUID(_INVOICE_ID)
        self.customer_id = uuid.UUID(_CUSTOMER_ID)
        self.payment_ref = "PAY-20260411-0001"
        self.amount = Decimal("500.00")
        self.payment_method = "BANK_TRANSFER"
        self.payment_date = date(2026, 4, 11)
        self.reference_number = "REF-001"
        self.notes = "Applied"
        self.created_by = "system"
        self.created_at = datetime(2026, 4, 11, 9, 0, 0)
        self.updated_at = datetime(2026, 4, 11, 9, 0, 0)
        self.match_status = "matched"
        self.match_type = "manual"
        self.matched_at = datetime(2026, 4, 11, 9, 0, 0)
        self.suggested_invoice_id = None


class FakeSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


def _patch_session():
    return patch("domains.payments.mcp.AsyncSessionLocal", return_value=FakeSession())


@pytest.mark.asyncio
async def test_payments_list_returns_results():
    fake_payment = FakePayment()
    with (
        _patch_session(),
        patch(
            "domains.payments.mcp.list_payments",
            new_callable=AsyncMock,
            return_value=([fake_payment], 1),
        ),
    ):
        result = await _list_fn(invoice_id=_INVOICE_ID, customer_id=_CUSTOMER_ID)

    assert result["total"] == 1
    assert result["payments"][0]["id"] == _PAYMENT_ID
    assert result["payments"][0]["payment_ref"] == "PAY-20260411-0001"


@pytest.mark.asyncio
async def test_payments_get_returns_detail():
    fake_payment = FakePayment()
    with (
        _patch_session(),
        patch(
            "domains.payments.mcp.get_payment",
            new_callable=AsyncMock,
            return_value=fake_payment,
        ),
    ):
        result = await _get_fn(payment_id=_PAYMENT_ID)

    assert result["id"] == _PAYMENT_ID
    assert result["reference_number"] == "REF-001"
    assert result["notes"] == "Applied"


@pytest.mark.asyncio
async def test_payments_get_raises_not_found():
    with (
        _patch_session(),
        patch(
            "domains.payments.mcp.get_payment",
            new_callable=AsyncMock,
            return_value=None,
        ),
    ):
        with pytest.raises(ToolError) as exc_info:
            await _get_fn(payment_id=_PAYMENT_ID)

    error = json.loads(str(exc_info.value))
    assert error["code"] == "NOT_FOUND"
    assert error["entity_type"] == "payment"
    assert error["entity_id"] == _PAYMENT_ID