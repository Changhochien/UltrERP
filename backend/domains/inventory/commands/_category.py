"""Category commands — create, update, set_status."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from common.errors import DuplicateCategoryNameError, ValidationError
from common.models.category import Category, CategoryTranslation
from common.models.product import Product
from domains.inventory.domain import (
    DEFAULT_CATEGORY_LOCALE,
    category_translation_map,
    normalize_category_name,
    normalize_category_translations,
    resolve_category_locale,
)

if TYPE_CHECKING:
    from domains.inventory.schemas import CategoryCreate, CategoryUpdate


async def _find_category_by_name(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    name: str,
    *,
    exclude_category_id: uuid.UUID | None = None,
) -> Category | None:
    stmt = select(Category).where(
        Category.tenant_id == tenant_id,
        func.lower(Category.name) == name.lower(),
    )
    if exclude_category_id is not None:
        stmt = stmt.where(Category.id != exclude_category_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


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


async def create_category(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    data: "CategoryCreate",
    *,
    locale: str = DEFAULT_CATEGORY_LOCALE,
) -> Category:
    requested_locale = resolve_category_locale(locale)
    translations = normalize_category_translations(data.translations)
    translations[requested_locale] = normalize_category_name(data.name)
    fallback_name = translations.get(DEFAULT_CATEGORY_LOCALE) or translations[requested_locale]

    existing = await _find_category_by_name(session, tenant_id, fallback_name)
    if existing is not None:
        raise DuplicateCategoryNameError(existing_id=existing.id, existing_name=existing.name)

    category = Category(
        tenant_id=tenant_id,
        name=fallback_name,
        is_active=True,
        translations=[
            CategoryTranslation(locale=translation_locale, name=translation_name)
            for translation_locale, translation_name in translations.items()
        ],
    )
    try:
        session.add(category)
        await session.flush()
    except IntegrityError:
        await session.rollback()
        existing = await _find_category_by_name(session, tenant_id, fallback_name)
        if existing is not None:
            raise DuplicateCategoryNameError(existing_id=existing.id, existing_name=existing.name)
        raise

    return category


async def update_category(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    category_id: uuid.UUID,
    data: "CategoryUpdate",
    *,
    locale: str = DEFAULT_CATEGORY_LOCALE,
) -> Category | None:
    category = await _find_category_by_id(session, tenant_id, category_id)
    if category is None:
        return None

    requested_locale = resolve_category_locale(locale)
    old_fallback_name = category.name
    translations = category_translation_map(category)
    if data.translations is not None:
        translations.update(normalize_category_translations(data.translations))
    if data.name is not None:
        translations[requested_locale] = normalize_category_name(data.name)

    next_fallback_name = (
        translations.get(DEFAULT_CATEGORY_LOCALE)
        or old_fallback_name
        or next(iter(translations.values()), None)
    )
    if next_fallback_name is None:
        raise ValidationError(
            [{"loc": ("name",), "msg": "name cannot be blank", "type": "value_error"}]
        )

    if next_fallback_name != old_fallback_name:
        existing = await _find_category_by_name(
            session,
            tenant_id,
            next_fallback_name,
            exclude_category_id=category.id,
        )
        if existing is not None:
            raise DuplicateCategoryNameError(existing_id=existing.id, existing_name=existing.name)

    category.name = next_fallback_name
    existing_translations = {translation.locale: translation for translation in category.translations}
    for translation_locale, translation_name in translations.items():
        translation = existing_translations.get(translation_locale)
        if translation is None:
            category.translations.append(
                CategoryTranslation(locale=translation_locale, name=translation_name)
            )
        else:
            translation.name = translation_name

    try:
        if next_fallback_name != old_fallback_name:
            await session.execute(
                update(Product)
                .where(
                    Product.tenant_id == tenant_id,
                    Product.category_id == category.id,
                )
                .values(category=next_fallback_name)
            )
        await session.flush()
    except IntegrityError:
        await session.rollback()
        if next_fallback_name != old_fallback_name:
            existing = await _find_category_by_name(
                session,
                tenant_id,
                next_fallback_name,
                exclude_category_id=category_id,
            )
            if existing is not None:
                raise DuplicateCategoryNameError(existing_id=existing.id, existing_name=existing.name)
        raise

    return category


async def set_category_status(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    category_id: uuid.UUID,
    *,
    is_active: bool,
) -> Category | None:
    category = await _find_category_by_id(session, tenant_id, category_id)
    if category is None:
        return None

    category.is_active = is_active
    await session.flush()
    return category
