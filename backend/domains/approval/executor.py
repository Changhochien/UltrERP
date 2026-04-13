"""Execute approved actions."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from common.models.approval_request import ApprovalRequest
from common.models.stock_adjustment import ReasonCode
from domains.inventory.services import create_stock_adjustment


async def execute_approval_action(
    session: AsyncSession,
    approval: ApprovalRequest,
) -> dict | None:
    if approval.action != "inventory.adjust":
        return None

    context = approval.context
    result = await create_stock_adjustment(
        session,
        approval.tenant_id,
        product_id=uuid.UUID(context["product_id"]),
        warehouse_id=uuid.UUID(context["warehouse_id"]),
        quantity_change=int(context["quantity_change"]),
        reason_code=ReasonCode(str(context["reason_code"]).upper()),
        actor_id=approval.requested_by,
        notes=context.get("notes"),
    )
    approval.entity_id = str(result["id"])
    return result
