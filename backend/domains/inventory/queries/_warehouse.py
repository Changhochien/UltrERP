"""Warehouse queries — list and get warehouses."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.models.warehouse import Warehouse


async def list_warehouses(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    active_only: bool = True,
) -> list[Warehouse]:
    stmt = select(Warehouse).where(Warehouse.tenant_id == tenant_id).order_by(Warehouse.name)
    if active_only:
        stmt = stmt.where(Warehouse.is_active.is_(True))
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_warehouse(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    warehouse_id: uuid.UUID,
) -> Warehouse | None:
    stmt = select(Warehouse).where(
        Warehouse.id == warehouse_id,
        Warehouse.tenant_id == tenant_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
