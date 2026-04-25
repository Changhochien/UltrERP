"""Physical count queries — session listing and retrieval."""

from __future__ import annotations

import uuid

from sqlalchemy import desc, func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from common.models.physical_count_line import PhysicalCountLine
from common.models.physical_count_session import (
    PhysicalCountSession,
    PhysicalCountSessionStatus,
)

from domains.inventory.commands._physical import (
    _get_physical_count_session_record,
    _serialize_physical_count_session,
)


async def list_physical_count_sessions(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    warehouse_id: uuid.UUID | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict[str, object | None]], int]:
    filters = [PhysicalCountSession.tenant_id == tenant_id]
    if warehouse_id is not None:
        filters.append(PhysicalCountSession.warehouse_id == warehouse_id)
    if status is not None:
        filters.append(PhysicalCountSession.status == PhysicalCountSessionStatus(status))

    count_stmt = select(func.count(PhysicalCountSession.id)).where(*filters)
    total = (await session.execute(count_stmt)).scalar() or 0

    stmt = (
        select(PhysicalCountSession)
        .options(
            selectinload(PhysicalCountSession.warehouse),
            selectinload(PhysicalCountSession.lines),
        )
        .where(*filters)
        .order_by(desc(PhysicalCountSession.created_at))
        .offset(offset)
        .limit(limit)
    )
    items = list((await session.execute(stmt)).scalars().all())
    return [
        _serialize_physical_count_session(item, include_lines=False) for item in items
    ], total


async def get_physical_count_session(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    session_id: uuid.UUID,
) -> dict[str, object | None] | None:
    count_session = await _get_physical_count_session_record(session, tenant_id, session_id)
    if count_session is None:
        return None
    return _serialize_physical_count_session(count_session, include_lines=True)
