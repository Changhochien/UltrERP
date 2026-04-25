"""Unit of Measure commands — seed, create, update, set_status."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from common.errors import DuplicateUnitCodeError
from common.models.unit_of_measure import UnitOfMeasure
from domains.inventory.domain import (
    DEFAULT_UNIT_OF_MEASURE_SEEDS,
    normalize_unit_code,
    normalize_unit_name,
)

if TYPE_CHECKING:
    from domains.inventory.schemas import UnitOfMeasureCreate, UnitOfMeasureUpdate


async def _find_unit_by_code(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    code: str,
    *,
    exclude_unit_id: uuid.UUID | None = None,
) -> UnitOfMeasure | None:
    stmt = select(UnitOfMeasure).where(
        UnitOfMeasure.tenant_id == tenant_id,
        UnitOfMeasure.code == code,
    )
    if exclude_unit_id is not None:
        stmt = stmt.where(UnitOfMeasure.id != exclude_unit_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


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


async def seed_default_units(
    session: AsyncSession,
    tenant_id: uuid.UUID,
) -> list[UnitOfMeasure]:
    stmt = select(UnitOfMeasure).where(UnitOfMeasure.tenant_id == tenant_id)
    result = await session.execute(stmt)
    existing_units = list(result.scalars().all())
    existing_codes = {unit.code for unit in existing_units}

    created_units: list[UnitOfMeasure] = []
    for code, name, decimal_places in DEFAULT_UNIT_OF_MEASURE_SEEDS:
        if code in existing_codes:
            continue
        created_units.append(
            UnitOfMeasure(
                tenant_id=tenant_id,
                code=code,
                name=name,
                decimal_places=decimal_places,
                is_active=True,
            )
        )

    if created_units:
        session.add_all(created_units)
        await session.flush()

    return created_units


async def create_unit(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    data: "UnitOfMeasureCreate",
) -> UnitOfMeasure:
    code = normalize_unit_code(data.code)
    name = normalize_unit_name(data.name)

    existing = await _find_unit_by_code(session, tenant_id, code)
    if existing is not None:
        raise DuplicateUnitCodeError(existing_id=existing.id, existing_code=existing.code)

    unit = UnitOfMeasure(
        tenant_id=tenant_id,
        code=code,
        name=name,
        decimal_places=data.decimal_places,
        is_active=True,
    )
    try:
        session.add(unit)
        await session.flush()
    except IntegrityError:
        await session.rollback()
        existing = await _find_unit_by_code(session, tenant_id, code)
        if existing is not None:
            raise DuplicateUnitCodeError(existing_id=existing.id, existing_code=existing.code)
        raise

    return unit


async def update_unit(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    unit_id: uuid.UUID,
    data: "UnitOfMeasureUpdate",
) -> UnitOfMeasure | None:
    unit = await _find_unit_by_id(session, tenant_id, unit_id)
    if unit is None:
        return None

    code = normalize_unit_code(data.code)
    name = normalize_unit_name(data.name)
    existing = await _find_unit_by_code(
        session,
        tenant_id,
        code,
        exclude_unit_id=unit.id,
    )
    if existing is not None:
        raise DuplicateUnitCodeError(existing_id=existing.id, existing_code=existing.code)

    unit.code = code
    unit.name = name
    unit.decimal_places = data.decimal_places
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        existing = await _find_unit_by_code(
            session,
            tenant_id,
            code,
            exclude_unit_id=unit_id,
        )
        if existing is not None:
            raise DuplicateUnitCodeError(existing_id=existing.id, existing_code=existing.code)
        raise

    return unit


async def set_unit_status(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    unit_id: uuid.UUID,
    *,
    is_active: bool,
) -> UnitOfMeasure | None:
    unit = await _find_unit_by_id(session, tenant_id, unit_id)
    if unit is None:
        return None

    unit.is_active = is_active
    await session.flush()
    return unit
