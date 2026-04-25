"""Warehouse command — create warehouse."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from common.models.warehouse import Warehouse


async def create_warehouse(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    name: str,
    code: str,
    location: str | None = None,
    address: str | None = None,
    contact_email: str | None = None,
) -> Warehouse:
    warehouse = Warehouse(
        tenant_id=tenant_id,
        name=name,
        code=code,
        location=location,
        address=address,
        contact_email=contact_email,
    )
    session.add(warehouse)
    await session.flush()
    return warehouse
