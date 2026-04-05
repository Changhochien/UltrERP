"""Tests for LINE order confirmation formatters and reply_or_push_message."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from domains.line.client import reply_or_push_message
from domains.line.confirmation import (
    OrderLineInfo,
    format_order_confirmation,
    format_order_error,
    format_parse_help,
    format_unregistered_user,
)

# ── format_order_confirmation ────────────────────────────────────────────


class TestFormatOrderConfirmation:
    def test_normal_total(self):
        result = format_order_confirmation(
            order_number="ORD-001",
            lines=[
                OrderLineInfo(description="Widget A", quantity=Decimal("3")),
                OrderLineInfo(description="Widget B", quantity=Decimal("5")),
            ],
            total_amount=Decimal("1500.00"),
        )
        assert "✅ Order Received: ORD-001" in result
        assert "• Widget A × 3" in result
        assert "• Widget B × 5" in result
        assert "Total: NT$1,500.00" in result
        assert "Status: Pending" in result

    def test_zero_total_shows_pricing_pending(self):
        """LINE BOT draft orders have unit_price=0 → total=0."""
        result = format_order_confirmation(
            order_number="ORD-002",
            lines=[OrderLineInfo(description="Product X", quantity=Decimal("1"))],
            total_amount=Decimal("0"),
        )
        assert "Pricing pending" in result
        assert "NT$" not in result

    def test_none_total_shows_pricing_pending(self):
        result = format_order_confirmation(
            order_number="ORD-003",
            lines=[OrderLineInfo(description="Product Y", quantity=Decimal("2"))],
            total_amount=None,
        )
        assert "Pricing pending" in result

    def test_decimal_quantity_formatting(self):
        """Decimal(3.000) → '3', Decimal(1.500) → '1.5'."""
        result = format_order_confirmation(
            order_number="ORD-004",
            lines=[
                OrderLineInfo(description="A", quantity=Decimal("3.000")),
                OrderLineInfo(description="B", quantity=Decimal("1.500")),
            ],
            total_amount=Decimal("0"),
        )
        assert "• A × 3" in result
        assert "• B × 1.5" in result
        # Ensure trailing zeros are stripped
        assert "3.000" not in result
        assert "1.500" not in result

    def test_truncation_at_5000_chars(self):
        """Very large orders should be truncated to 5000 chars."""
        lines = [
            OrderLineInfo(description=f"Product-{i:04d}-{'X' * 80}", quantity=Decimal("1"))
            for i in range(100)
        ]
        result = format_order_confirmation(
            order_number="ORD-BIG",
            lines=lines,
            total_amount=Decimal("99999"),
        )
        assert len(result) <= 5000
        assert result.endswith("...")


# ── format_order_error ───────────────────────────────────────────────────


def test_format_order_error():
    result = format_order_error("Validation failed: missing product")
    assert "❌ Order could not be created" in result
    assert "Validation failed: missing product" in result
    assert "try again" in result


# ── format_parse_help ────────────────────────────────────────────────────


def test_format_parse_help():
    result = format_parse_help()
    assert "📋" in result
    assert "商品A x 3" in result
    assert "ProductA 3" in result


# ── format_unregistered_user ─────────────────────────────────────────────


def test_format_unregistered_user():
    result = format_unregistered_user()
    assert "👤" in result
    assert "not linked" in result
    assert "contact" in result.lower()


# ── reply_or_push_message ────────────────────────────────────────────────


class TestReplyOrPushMessage:
    @pytest.mark.asyncio
    async def test_uses_reply_first(self):
        with (
            patch(
                "domains.line.client._reply_text_message",
                new_callable=AsyncMock,
                return_value=True,
            ) as mock_reply,
            patch(
                "domains.line.client.push_text_message",
                new_callable=AsyncMock,
                return_value=True,
            ) as mock_push,
        ):
            result = await reply_or_push_message("token123", "U" + "a" * 32, "hello")
            assert result is True
            mock_reply.assert_awaited_once_with("token123", "hello")
            mock_push.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_falls_back_to_push_when_reply_fails(self):
        with (
            patch(
                "domains.line.client._reply_text_message",
                new_callable=AsyncMock,
                return_value=False,
            ),
            patch(
                "domains.line.client.push_text_message",
                new_callable=AsyncMock,
                return_value=True,
            ) as mock_push,
        ):
            result = await reply_or_push_message("expired_token", "U" + "b" * 32, "hello")
            assert result is True
            mock_push.assert_awaited_once_with("U" + "b" * 32, "hello")

    @pytest.mark.asyncio
    async def test_push_when_no_reply_token(self):
        with (
            patch(
                "domains.line.client._reply_text_message",
                new_callable=AsyncMock,
            ) as mock_reply,
            patch(
                "domains.line.client.push_text_message",
                new_callable=AsyncMock,
                return_value=True,
            ) as mock_push,
        ):
            result = await reply_or_push_message(None, "U" + "c" * 32, "hello")
            assert result is True
            mock_reply.assert_not_awaited()
            mock_push.assert_awaited_once()
