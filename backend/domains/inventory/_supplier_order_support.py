"""Private supplier-order helpers shared across inventory modules."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from common.models.supplier import Supplier
from common.models.supplier_order import SupplierOrder


async def _serialize_order(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    order_id: uuid.UUID,
) -> dict | None:
    """Fetch and serialize a supplier order with eager-loaded lines."""
    stmt = (
        select(SupplierOrder)
        .options(selectinload(SupplierOrder.lines))
        .where(
            SupplierOrder.id == order_id,
            SupplierOrder.tenant_id == tenant_id,
        )
    )
    result = await session.execute(stmt)
    order = result.scalar_one_or_none()

    if order is None:
        return None

    supplier_stmt = select(Supplier.name).where(Supplier.id == order.supplier_id)
    supplier_result = await session.execute(supplier_stmt)
    supplier_name = supplier_result.scalar_one_or_none() or "Unknown"

    return {
        "id": order.id,
        "tenant_id": order.tenant_id,
        "supplier_id": order.supplier_id,
        "supplier_name": supplier_name,
        "order_number": order.order_number,
        "status": order.status.value,
        "order_date": order.order_date,
        "expected_arrival_date": order.expected_arrival_date,
        "received_date": order.received_date,
        "created_by": order.created_by,
        "created_at": order.created_at,
        "updated_at": order.updated_at,
        "lines": [
            {
                "id": line.id,
                "product_id": line.product_id,
                "warehouse_id": line.warehouse_id,
                "quantity_ordered": line.quantity_ordered,
                "unit_price": getattr(line, "unit_price", None),
                "quantity_received": line.quantity_received,
                "notes": line.notes,
            }
            for line in order.lines
        ],
    }