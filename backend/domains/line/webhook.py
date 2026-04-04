"""LINE webhook endpoint for receiving BOT messages.

Uses WebhookParser (not WebhookHandler) to avoid sync/async mismatch.
"""

from __future__ import annotations

import logging
import re
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhook import WebhookParser
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.config import get_settings
from common.database import get_db
from common.tenant import DEFAULT_TENANT_ID
from domains.line.client import reply_or_push_message
from domains.line.confirmation import (
	OrderLineInfo,
	format_order_confirmation,
	format_order_error,
	format_parse_help,
	format_unregistered_user,
)
from domains.line.models import LineCustomerMapping
from domains.line.parser import parse_order_text
from domains.orders.schemas import OrderCreate, OrderCreateLine
from domains.orders.services import create_order

logger = logging.getLogger(__name__)
router = APIRouter()
DbSession = Annotated[AsyncSession, Depends(get_db)]

_LINE_USER_ID_RE = re.compile(r"^U[0-9a-f]{32}$")


def _get_parser() -> WebhookParser | None:
	settings = get_settings()
	if not settings.line_channel_secret:
		return None
	return WebhookParser(settings.line_channel_secret)


@router.post("/webhook")
async def line_webhook(request: Request, session: DbSession):
	"""Receive LINE webhook events."""
	parser = _get_parser()
	if parser is None:
		raise HTTPException(status_code=503, detail="LINE not configured")

	signature = request.headers.get("X-Line-Signature", "")
	body = (await request.body()).decode("utf-8")

	try:
		events = parser.parse(body, signature)
	except InvalidSignatureError:
		raise HTTPException(status_code=400, detail="Invalid signature")

	for event in events:
		if isinstance(event, MessageEvent) and isinstance(event.message, TextMessageContent):
			await _handle_text_message(event, session)

	return "OK"


async def _handle_text_message(event: MessageEvent, session: AsyncSession) -> None:
	"""Parse → lookup → create order → reply."""
	user_id = event.source.user_id
	if not user_id or not _LINE_USER_ID_RE.match(user_id):
		logger.warning("Invalid LINE user_id: %s", user_id)
		return

	reply_token = event.reply_token
	text = event.message.text

	# 1. Look up customer mapping
	tenant_id = DEFAULT_TENANT_ID
	stmt = select(LineCustomerMapping).where(
		LineCustomerMapping.tenant_id == tenant_id,
		LineCustomerMapping.line_user_id == user_id,
	)
	result = await session.execute(stmt)
	mapping = result.scalar_one_or_none()

	if mapping is None:
		await reply_or_push_message(
			reply_token, user_id, format_unregistered_user(),
		)
		return

	# 2. Parse order text
	parsed_lines = parse_order_text(text)
	if not parsed_lines:
		logger.info("Unparseable LINE message from user %s: %r", user_id, text)
		await reply_or_push_message(
			reply_token, user_id, format_parse_help(),
		)
		return

	# 3. Look up products
	from domains.inventory.services import search_products

	order_lines: list[OrderCreateLine] = []
	not_found: list[str] = []

	for pl in parsed_lines:
		results = await search_products(session, tenant_id, pl.product_query, limit=1)
		if not results:
			not_found.append(pl.product_query)
			continue
		product = results[0]
		order_lines.append(
			OrderCreateLine(
				product_id=product["id"],
				description=product["name"],
				quantity=Decimal(str(pl.quantity)),
				unit_price=Decimal("0"),
				tax_policy_code="TAXABLE_5",
			)
		)

	if not_found:
		await reply_or_push_message(
			reply_token, user_id,
			f"找不到以下商品：{', '.join(not_found)}\n"
			"請確認商品名稱後重新下單。",
		)
		return

	if not order_lines:
		await reply_or_push_message(reply_token, user_id, "未找到有效商品，請重新下單。")
		return

	# 4. Create order
	try:
		order_data = OrderCreate(
			customer_id=mapping.customer_id,
			lines=order_lines,
		)
		order = await create_order(session, order_data, tenant_id=tenant_id)
		line_infos = [
			OrderLineInfo(description=ol.description, quantity=ol.quantity)
			for ol in order_lines
		]
		confirmation = format_order_confirmation(
			order_number=order.order_number,
			lines=line_infos,
			total_amount=order.total_amount,
		)
		await reply_or_push_message(reply_token, user_id, confirmation)
	except Exception:
		logger.exception("Failed to create order from LINE for user %s", user_id)
		await reply_or_push_message(
			reply_token, user_id,
			format_order_error("An unexpected error occurred"),
		)
