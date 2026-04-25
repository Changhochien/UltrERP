"""Supplier queries — read operations that fetch supplier data."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

if TYPE_CHECKING:
    from common.models.supplier import Supplier

# Re-export helpers for internal use
from domains.inventory._supplier_order_support import _serialize_order


async def list_suppliers(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    q: str | None = None,
    active_only: bool = True,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[Supplier], int]:
    """List suppliers with search, active filter, and pagination."""
    from common.models.supplier import Supplier

    where_conditions = [Supplier.tenant_id == tenant_id]

    if active_only:
        where_conditions.append(Supplier.is_active.is_(True))

    stripped = q.strip() if q else ""
    if stripped:
        q_like = stripped.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        where_conditions.append(Supplier.name.ilike(f"%{q_like}%", escape="\\"))

    count_stmt = select(func.count(Supplier.id)).where(*where_conditions)
    count_result = await session.execute(count_stmt)
    raw_total = count_result.scalar()

    prefetched_rows: list[Supplier] = []
    if raw_total is None:
        prefetched_rows = list(count_result.scalars().all())
    if prefetched_rows:
        return prefetched_rows, len(prefetched_rows)

    stmt = (
        select(Supplier)
        .where(*where_conditions)
        .order_by(Supplier.name)
        .offset(offset)
        .limit(limit)
    )
    result = await session.execute(stmt)
    suppliers = list(result.scalars().all())
    total = int(raw_total or 0) if raw_total is not None else len(suppliers)
    return suppliers, total


async def get_supplier(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    supplier_id: uuid.UUID,
) -> Supplier | None:
    """Get a single supplier by ID."""
    from common.models.supplier import Supplier

    stmt = select(Supplier).where(
        Supplier.id == supplier_id,
        Supplier.tenant_id == tenant_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_supplier_order(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    order_id: uuid.UUID,
) -> dict | None:
    """Fetch supplier order with line items."""
    return await _serialize_order(session, tenant_id, order_id)


async def list_supplier_orders(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    status_filter: str | None = None,
    supplier_id: uuid.UUID | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """List supplier orders with optional filters."""
    from common.models.supplier import Supplier
    from common.models.supplier_order import SupplierOrder, SupplierOrderStatus

    base_where = [SupplierOrder.tenant_id == tenant_id]
    if status_filter:
        base_where.append(SupplierOrder.status == SupplierOrderStatus(status_filter))
    if supplier_id:
        base_where.append(SupplierOrder.supplier_id == supplier_id)

    # Count
    count_stmt = select(func.count(SupplierOrder.id)).where(*base_where)
    count_result = await session.execute(count_stmt)
    total = count_result.scalar() or 0

    # Fetch with pagination
    stmt = (
        select(SupplierOrder)
        .options(selectinload(SupplierOrder.lines))
        .where(*base_where)
        .order_by(SupplierOrder.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await session.execute(stmt)
    orders = result.scalars().unique().all()

    # Batch-fetch supplier names
    order_supplier_ids = {o.supplier_id for o in orders}
    if order_supplier_ids:
        name_stmt = select(Supplier.id, Supplier.name).where(Supplier.id.in_(order_supplier_ids))
        name_result = await session.execute(name_stmt)
        supplier_names = {row[0]: row[1] for row in name_result.all()}
    else:
        supplier_names = {}

    items = [
        {
            "id": order.id,
            "supplier_id": order.supplier_id,
            "supplier_name": supplier_names.get(order.supplier_id, "Unknown"),
            "order_number": order.order_number,
            "status": order.status.value,
            "order_date": order.order_date,
            "expected_arrival_date": order.expected_arrival_date,
            "received_date": order.received_date,
            "created_by": order.created_by,
            "created_at": order.created_at,
            "updated_at": order.updated_at,
            "line_count": len(order.lines),
        }
        for order in orders
    ]

    return items, total


async def get_top_customer(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
) -> dict | None:
    """Return the customer who has ordered the most of this product (by quantity)."""
    from common.models.order import Order
    from common.models.order_line import OrderLine
    from domains.customers.models import Customer

    stmt = (
        select(
            Customer.id.label("customer_id"),
            Customer.company_name.label("customer_name"),
            func.sum(OrderLine.quantity).label("total_qty"),
        )
        .join(Order, Order.id == OrderLine.order_id)
        .join(Customer, Customer.id == Order.customer_id)
        .where(
            Order.tenant_id == tenant_id,
            OrderLine.product_id == product_id,
        )
        .group_by(Customer.id, Customer.company_name)
        .order_by(func.sum(OrderLine.quantity).desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    row = result.first()

    if row is None:
        return None
    return {
        "customer_id": row.customer_id,
        "customer_name": row.customer_name,
        "total_qty": int(row.total_qty or 0),
    }
