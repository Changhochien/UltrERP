"""Unit of Measure queries — list and get units."""

from __future__ import annotations

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.models.unit_of_measure import UnitOfMeasure


async def _find_unit_by_id(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    unit_id: uuid.UUID,
) -> UnitOfMeasure | None:
    stmt = select(UnitOfMeasure).where(
        UnitOfMeasure.id == unit_id,
        UnitOfMeasure.tenant_id == tenant_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_units(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    q: str = "",
    active_only: bool = True,
    limit: int = 100,
    offset: int = 0,
    seed_defaults: bool = True,
) -> tuple[list[UnitOfMeasure], int]:
    # Import here to avoid circular import
    from domains.inventory.commands._unit import seed_default_units

    if seed_defaults:
        await seed_default_units(session, tenant_id)

    where_conditions = [UnitOfMeasure.tenant_id == tenant_id]
    if active_only:
        where_conditions.append(UnitOfMeasure.is_active.is_(True))

    stripped = q.strip().lower()
    if stripped:
        q_like = stripped.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        where_conditions.append(
            or_(
                UnitOfMeasure.code.ilike(f"%{q_like}%", escape="\\"),
                UnitOfMeasure.name.ilike(f"%{q_like}%", escape="\\"),
            )
        )

    count_stmt = select(func.count(UnitOfMeasure.id)).where(*where_conditions)
    count_result = await session.execute(count_stmt)
    total = count_result.scalar() or 0

    stmt = (
        select(UnitOfMeasure)
        .where(*where_conditions)
        .order_by(UnitOfMeasure.code)
        .offset(offset)
        .limit(limit)
    )
    result = await session.execute(stmt)
    units = result.scalars().all()
    return list(units), total


async def get_unit(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    unit_id: uuid.UUID,
) -> UnitOfMeasure | None:
    return await _find_unit_by_id(session, tenant_id, unit_id)
