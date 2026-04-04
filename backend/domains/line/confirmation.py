"""Format LINE confirmation messages for orders."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass
class OrderLineInfo:
	description: str  # from OrderLine.description (product name)
	quantity: Decimal  # from OrderLine.quantity (Numeric(18,3))


_MAX_LINE_MESSAGE_CHARS = 5000


def _fmt_qty(qty: Decimal) -> str:
	"""Format quantity stripping trailing zeros: 3.000 → '3', 1.500 → '1.5'."""
	return f"{qty:f}".rstrip("0").rstrip(".")


def format_order_confirmation(
	*,
	order_number: str,
	lines: list[OrderLineInfo],
	total_amount: Decimal | None,
) -> str:
	"""Format order confirmation message text.

	For LINE BOT draft orders, total_amount may be 0 (unit_price=0).
	In that case, show 'Pricing pending' instead of NT$0.
	Truncates to LINE's 5,000 character limit.
	"""
	items_text = "\n".join(
		f"• {line.description} × {_fmt_qty(line.quantity)}" for line in lines
	)
	# LINE BOT draft orders have unit_price=0, so total=0
	if total_amount and total_amount > 0:
		total_line = f"Total: NT${total_amount:,.2f}"
	else:
		total_line = "Total: Pricing pending (staff will confirm)"
	message = (
		f"✅ Order Received: {order_number}\n\n"
		f"Items:\n{items_text}\n\n"
		f"{total_line}\n"
		f"Status: Pending\n\n"
		f"We'll process your order shortly. Thank you!"
	)
	if len(message) > _MAX_LINE_MESSAGE_CHARS:
		message = message[: _MAX_LINE_MESSAGE_CHARS - 3] + "..."
	return message


def format_order_error(error_message: str) -> str:
	"""Format order creation failure message."""
	return (
		f"❌ Order could not be created\n\n"
		f"Reason: {error_message}\n\n"
		f"Please check your order and try again, "
		f"or contact our staff for assistance."
	)


def format_parse_help() -> str:
	"""Format help message for unparseable input."""
	return (
		"📋 To place an order, send a message like:\n\n"
		"商品A x 3, 商品B x 5\n\n"
		"or\n\n"
		"ProductA 3\n"
		"ProductB 5\n\n"
		"Each item should have a product name and quantity."
	)


def format_unregistered_user() -> str:
	"""Message for LINE users not linked to a customer account."""
	return (
		"👤 Your LINE account is not linked to a customer account.\n\n"
		"Please contact our staff to register your LINE account "
		"before placing orders."
	)
