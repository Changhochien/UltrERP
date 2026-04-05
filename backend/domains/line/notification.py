"""LINE notification service for order events.

Sends push messages to staff group when orders are created.
All errors are caught and logged — never blocks order flow.
"""

from __future__ import annotations

import logging

from common.config import get_settings
from domains.line.client import push_text_message

logger = logging.getLogger(__name__)


async def notify_new_order(
    *,
    order_number: str,
    customer_name: str,
    total_amount: str,
    line_count: int,
) -> None:
    """Send new-order notification to staff. Fire-and-forget."""
    settings = get_settings()
    group_id = settings.line_staff_group_id
    if not group_id:
        logger.debug("LINE_STAFF_GROUP_ID not set — skipping notification")
        return

    text = (
        f"📦 New Order: {order_number}\n"
        f"Customer: {customer_name}\n"
        f"Items: {line_count}\n"
        f"Total: NT${total_amount}"
    )
    success = await push_text_message(group_id, text, order_number=order_number)
    if success:
        logger.info("LINE notification sent for order %s", order_number)
    else:
        logger.warning("LINE notification failed for order %s", order_number)
