"""Product-supplier commands — write operations that modify product-supplier associations."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.errors import ValidationError

if TYPE_CHECKING:
    from common.models.product_supplier import ProductSupplier

# Re-export helpers for internal use
from domains.inventory._product_supplier_support import (
    _serialize_product_supplier_association,
)


async def create_product_supplier(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    *,
    supplier_id: uuid.UUID,
    unit_cost: float | None = None,
    lead_time_days: int | None = None,
    is_default: bool = False,
) -> dict[str, Any]:
    """Create a product-supplier association."""
    from common.models.product_supplier import ProductSupplier
    from common.models.product import Product
    from common.models.supplier import Supplier

    # Validate product exists and belongs to tenant
    product = await session.get(Product, product_id)
    if product is None or product.tenant_id != tenant_id:
        raise ValidationError([
            {"loc": ["product_id"], "msg": "Product not found", "type": "value_error"},
        ])

    # Validate supplier exists and belongs to tenant
    supplier = await session.get(Supplier, supplier_id)
    if supplier is None or supplier.tenant_id != tenant_id:
        raise ValidationError([
            {"loc": ["supplier_id"], "msg": "Supplier not found", "type": "value_error"},
        ])

    # Check for existing association
    existing_stmt = select(ProductSupplier).where(
        ProductSupplier.tenant_id == tenant_id,
        ProductSupplier.product_id == product_id,
        ProductSupplier.supplier_id == supplier_id,
    )
    existing_result = await session.execute(existing_stmt)
    existing = existing_result.scalar_one_or_none()
    if existing is not None:
        raise ValidationError([
            {
                "loc": ["supplier_id"],
                "msg": "Supplier association already exists for this product",
                "type": "value_error",
            }
        ])

    # If setting as default, clear other defaults
    if is_default:
        default_result = await session.execute(
            select(ProductSupplier).where(
                ProductSupplier.tenant_id == tenant_id,
                ProductSupplier.product_id == product_id,
                ProductSupplier.is_default.is_(True),
            )
        )
        for association in default_result.scalars().all():
            association.is_default = False

    association = ProductSupplier(
        tenant_id=tenant_id,
        product_id=product_id,
        supplier_id=supplier_id,
        unit_cost=(Decimal(str(unit_cost)) if unit_cost is not None else None),
        lead_time_days=lead_time_days,
        is_default=is_default,
    )
    session.add(association)
    await session.flush()

    return _serialize_product_supplier_association(association, supplier.name)


async def update_product_supplier(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    supplier_id: uuid.UUID,
    *,
    unit_cost: float | None = None,
    lead_time_days: int | None = None,
    is_default: bool | None = None,
) -> dict[str, Any] | None:
    """Update a product-supplier association."""
    from common.models.product_supplier import ProductSupplier
    from common.models.supplier import Supplier

    stmt = (
        select(ProductSupplier, Supplier.name)
        .join(
            Supplier,
            and_(Supplier.id == ProductSupplier.supplier_id, Supplier.tenant_id == tenant_id),
        )
        .where(
            ProductSupplier.tenant_id == tenant_id,
            ProductSupplier.product_id == product_id,
            ProductSupplier.supplier_id == supplier_id,
        )
    )
    result = await session.execute(stmt)
    row = result.first()
    if row is None:
        return None

    association, supplier_name = row

    # If setting as default, clear other defaults
    if is_default:
        default_result = await session.execute(
            select(ProductSupplier).where(
                ProductSupplier.tenant_id == tenant_id,
                ProductSupplier.product_id == product_id,
                ProductSupplier.is_default.is_(True),
                ProductSupplier.supplier_id != supplier_id,
            )
        )
        for assoc in default_result.scalars().all():
            assoc.is_default = False

    if unit_cost is not None:
        association.unit_cost = Decimal(str(unit_cost))
    if lead_time_days is not None:
        association.lead_time_days = lead_time_days
    if is_default is not None:
        association.is_default = is_default

    await session.flush()
    return _serialize_product_supplier_association(association, supplier_name)


async def delete_product_supplier(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    supplier_id: uuid.UUID,
) -> bool:
    """Delete a product-supplier association."""
    from common.models.product_supplier import ProductSupplier

    stmt = select(ProductSupplier).where(
        ProductSupplier.tenant_id == tenant_id,
        ProductSupplier.product_id == product_id,
        ProductSupplier.supplier_id == supplier_id,
    )
    result = await session.execute(stmt)
    association = result.scalar_one_or_none()
    if association is None:
        return False

    await session.delete(association)
    await session.flush()
    return True
