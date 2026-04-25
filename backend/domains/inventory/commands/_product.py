"""Product commands — create, update, set status."""

from __future__ import annotations

import uuid
from decimal import Decimal, ROUND_HALF_UP
from typing import TYPE_CHECKING

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from common.errors import DuplicateProductCodeError, ValidationError
from common.models.category import Category
from common.models.product import Product

if TYPE_CHECKING:
    from domains.inventory.schemas import ProductCreate, ProductUpdate

_STANDARD_COST_QUANT = Decimal("0.0001")


def _normalize_standard_cost(value: object | None) -> Decimal | None:
    if value is None or value == "":
        return None

    standard_cost = value if isinstance(value, Decimal) else Decimal(str(value))
    if standard_cost < 0:
        raise ValidationError(
            [
                {
                    "loc": ("standard_cost",),
                    "msg": "standard_cost must be greater than or equal to 0",
                    "type": "value_error",
                }
            ]
        )
    return standard_cost.quantize(_STANDARD_COST_QUANT, rounding=ROUND_HALF_UP)


def _normalize_optional_product_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _normalize_product_payload(
    data: object,
) -> tuple[str, str, uuid.UUID | None, str | None, str, Decimal | None]:
    code = str(getattr(data, "code", "")).strip()
    name = str(getattr(data, "name", "")).strip()
    unit = str(getattr(data, "unit", "")).strip()
    category_id = getattr(data, "category_id", None)
    description = _normalize_optional_product_text(getattr(data, "description", None))
    standard_cost = _normalize_standard_cost(getattr(data, "standard_cost", None))

    errors: list[dict[str, str | tuple[str, ...]]] = []
    if not code:
        errors.append({"loc": ("code",), "msg": "code cannot be blank", "type": "value_error"})
    if not name:
        errors.append({"loc": ("name",), "msg": "name cannot be blank", "type": "value_error"})
    if not unit:
        errors.append({"loc": ("unit",), "msg": "unit cannot be blank", "type": "value_error"})
    if errors:
        raise ValidationError(errors)

    return code, name, category_id, description, unit, standard_cost


async def _find_product_by_code(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    code: str,
    *,
    exclude_product_id: uuid.UUID | None = None,
) -> Product | None:
    stmt = select(Product).where(
        Product.tenant_id == tenant_id,
        func.lower(Product.code) == code.lower(),
    )
    if exclude_product_id is not None:
        stmt = stmt.where(Product.id != exclude_product_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _find_category_by_id(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    category_id: uuid.UUID,
) -> Category | None:
    from sqlalchemy.orm import selectinload

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


async def _resolve_product_category(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    category_id: uuid.UUID | None,
) -> Category | None:
    if category_id is None:
        return None

    category = await _find_category_by_id(session, tenant_id, category_id)
    if category is None:
        raise ValidationError(
            [
                {
                    "loc": ("category_id",),
                    "msg": "category_id does not reference an existing category",
                    "type": "value_error",
                }
            ]
        )
    return category


async def create_product(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    data: "ProductCreate",
) -> Product:
    """Create a new product for a tenant."""
    code, name, category_id, description, unit, standard_cost = _normalize_product_payload(data)
    category = await _resolve_product_category(session, tenant_id, category_id)

    # Check for duplicate code within tenant
    row = await _find_product_by_code(session, tenant_id, code)
    if row is not None:
        raise DuplicateProductCodeError(existing_id=row.id, existing_code=row.code)

    product = Product(
        tenant_id=tenant_id,
        code=code,
        name=name,
        category=category.name if category is not None else None,
        category_id=category.id if category is not None else None,
        description=description,
        unit=unit,
        standard_cost=standard_cost,
        status="active",
        search_vector=func.to_tsvector("simple", name + " " + code),
    )
    try:
        session.add(product)
        await session.flush()
    except IntegrityError:
        await session.rollback()
        # Race condition: another request inserted the same code between our
        # pre-check and insert. Query for the conflicting product and raise
        # DuplicateProductCodeError so the route returns a proper 409.
        existing = await _find_product_by_code(session, tenant_id, code)
        if existing is not None:
            raise DuplicateProductCodeError(existing_id=existing.id, existing_code=existing.code)
        raise
    return product


async def update_product(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    data: "ProductUpdate",
) -> Product | None:
    """Update an existing product for a tenant."""
    code, name, category_id, description, unit, standard_cost = _normalize_product_payload(data)

    stmt = select(Product).where(
        Product.id == product_id,
        Product.tenant_id == tenant_id,
    )
    result = await session.execute(stmt)
    product = result.scalar_one_or_none()
    if product is None:
        return None

    existing = await _find_product_by_code(
        session,
        tenant_id,
        code,
        exclude_product_id=product.id,
    )
    if existing is not None:
        raise DuplicateProductCodeError(existing_id=existing.id, existing_code=existing.code)

    category = await _resolve_product_category(session, tenant_id, category_id)
    code_or_name_changed = product.code != code or product.name != name
    product.code = code
    product.name = name
    product.category = category.name if category is not None else None
    product.category_id = category.id if category is not None else None
    product.description = description
    product.unit = unit
    product.standard_cost = standard_cost
    if code_or_name_changed:
        product.search_vector = func.to_tsvector("simple", name + " " + code)

    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        existing = await _find_product_by_code(
            session,
            tenant_id,
            code,
            exclude_product_id=product_id,
        )
        if existing is not None:
            raise DuplicateProductCodeError(existing_id=existing.id, existing_code=existing.code)
        raise

    return product


async def set_product_status(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    status: str,
) -> Product | None:
    """Set the active/inactive lifecycle status for an existing product."""
    stmt = select(Product).where(
        Product.id == product_id,
        Product.tenant_id == tenant_id,
    )
    result = await session.execute(stmt)
    product = result.scalar_one_or_none()
    if product is None:
        return None

    product.status = status
    await session.flush()
    return product
