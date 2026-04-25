"""Category queries — list and get categories."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from common.models.category import Category
from domains.inventory.domain import (
    DEFAULT_CATEGORY_LOCALE,
    category_translation_map,
    localized_category_name,
    resolve_category_locale,
)


async def _find_category_by_id(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    category_id: uuid.UUID,
) -> Category | None:
    stmt = (
        select(Category)
        .options(selectinload(Category.translations))
        .where(
            Category.id == category_id,
            Category.tenant_id == tenant_id,
        )
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_categories(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    locale: str = DEFAULT_CATEGORY_LOCALE,
    q: str = "",
    active_only: bool = True,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[Category], int]:
    where_conditions = [Category.tenant_id == tenant_id]
    if active_only:
        where_conditions.append(Category.is_active.is_(True))

    stmt = (
        select(Category)
        .options(selectinload(Category.translations))
        .where(*where_conditions)
        .order_by(Category.name)
    )
    result = await session.execute(stmt)
    categories = list(result.scalars().all())

    stripped = q.strip().lower()
    if stripped:
        categories = [
            category
            for category in categories
            if stripped in (category.name or "").lower()
            or any(stripped in translation.name.lower() for translation in category.translations)
        ]

    resolved_locale = resolve_category_locale(locale)
    categories.sort(
        key=lambda category: (
            localized_category_name(category, resolved_locale) or category.name or ""
        ).lower()
    )
    total = len(categories)
    return categories[offset : offset + limit], total


async def get_category(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    category_id: uuid.UUID,
) -> Category | None:
    return await _find_category_by_id(session, tenant_id, category_id)
