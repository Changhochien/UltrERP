"""Inventory collaborators used by order confirmation."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.models.inventory_stock import InventoryStock
from common.models.order_line import OrderLine
from common.models.stock_adjustment import ReasonCode
from common.models.warehouse import Warehouse
from domains.inventory.commands import create_stock_adjustment


async def _get_default_warehouse_id_for_order_confirmation(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_ids: Sequence[uuid.UUID],
) -> uuid.UUID:
    if product_ids:
        stocked_result = await session.execute(
            select(InventoryStock.warehouse_id)
            .join(Warehouse, Warehouse.id == InventoryStock.warehouse_id)
            .where(
                InventoryStock.tenant_id == tenant_id,
                InventoryStock.product_id.in_(product_ids),
                InventoryStock.quantity > 0,
                Warehouse.is_active.is_(True),
            )
            .order_by(InventoryStock.quantity.desc(), InventoryStock.warehouse_id.asc())
            .limit(1)
        )
        stocked_warehouse_id = stocked_result.scalar_one_or_none()
        if stocked_warehouse_id is not None:
            return stocked_warehouse_id

    warehouse_result = await session.execute(
        select(Warehouse.id)
        .where(
            Warehouse.tenant_id == tenant_id,
            Warehouse.is_active.is_(True),
        )
        .order_by(Warehouse.created_at.asc(), Warehouse.id.asc())
        .limit(1)
    )
    warehouse_id = warehouse_result.scalar_one_or_none()
    if warehouse_id is None:
        raise ValueError("No active warehouse configured")
    return warehouse_id


async def reserve_stock_for_order_confirmation(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    order_number: str,
    order_lines: Sequence[OrderLine],
    actor_id: str,
) -> None:
    product_ids = [line.product_id for line in order_lines]
    warehouse_id = await _get_default_warehouse_id_for_order_confirmation(
        session,
        tenant_id,
        product_ids,
    )

    for line in order_lines:
        await create_stock_adjustment(
            session,
            tenant_id,
            product_id=line.product_id,
            warehouse_id=warehouse_id,
            quantity_change=-int(line.quantity),
            reason_code=ReasonCode.SALES_RESERVATION,
            actor_id=actor_id,
            notes=f"Sales reservation for order {order_number}",
        )