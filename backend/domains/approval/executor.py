"""Execute approved actions."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from common.tenant import DEFAULT_TENANT_ID
from domains.inventory.services import create_stock_adjustment
from common.models.stock_adjustment import ReasonCode
from common.models.approval_request import ApprovalRequest


async def execute_approval_action(
	session: AsyncSession,
	approval: ApprovalRequest,
) -> dict | None:
	if approval.action != "inventory.adjust":
		return None

	context = approval.context
	result = await create_stock_adjustment(
		session,
		DEFAULT_TENANT_ID,
		product_id=uuid.UUID(context["product_id"]),
		warehouse_id=uuid.UUID(context["warehouse_id"]),
		quantity_change=int(context["quantity_change"]),
		reason_code=ReasonCode(context["reason_code"]),
		actor_id=approval.requested_by,
		notes=context.get("notes"),
	)
	approval.entity_id = str(result["id"])
	return result