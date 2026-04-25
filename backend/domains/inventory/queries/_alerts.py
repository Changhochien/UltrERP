"""Alert queries — read operations that fetch alert data."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
import uuid

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.time import utc_now
from domains.inventory._alert_support import _serialize_reorder_suggestion_row
from domains.inventory._product_supplier_support import _batch_get_product_suppliers

_ProductSupplierLoader = Callable[
    [AsyncSession, uuid.UUID, list[uuid.UUID]],
    Awaitable[dict[uuid.UUID, dict | None]],
]


async def list_reorder_alerts(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    status_filter: str | None = None,
    warehouse_id: uuid.UUID | None = None,
    sort_by: str = "severity",
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """List reorder alerts with product/warehouse names."""
    from common.models.product import Product
    from common.models.reorder_alert import AlertStatus, ReorderAlert
    from common.models.warehouse import Warehouse

    now = utc_now()

    base_where = [ReorderAlert.tenant_id == tenant_id]
    if status_filter:
        if status_filter == AlertStatus.PENDING.value:
            base_where.append(
                or_(
                    ReorderAlert.status == AlertStatus.PENDING,
                    and_(
                        ReorderAlert.status == AlertStatus.SNOOZED,
                        ReorderAlert.snoozed_until.is_not(None),
                        ReorderAlert.snoozed_until <= now,
                    ),
                )
            )
        elif status_filter == AlertStatus.SNOOZED.value:
            base_where.append(ReorderAlert.status == AlertStatus.SNOOZED)
            base_where.append(
                or_(
                    ReorderAlert.snoozed_until.is_(None),
                    ReorderAlert.snoozed_until > now,
                )
            )
        else:
            base_where.append(ReorderAlert.status == AlertStatus(status_filter))
    if warehouse_id:
        base_where.append(ReorderAlert.warehouse_id == warehouse_id)

    # Count
    count_stmt = select(func.count(ReorderAlert.id)).where(*base_where)
    count_result = await session.execute(count_stmt)
    total = count_result.scalar() or 0

    # Days-until-stockout expression: current_stock / GREATEST(avg_daily_usage_estimate, 0.001)
    # avg_daily_usage_estimate = reorder_point / 14 (2-week lead time at 0.5 safety factor proxy)
    days_until_stockout = ReorderAlert.current_stock / func.greatest(
        ReorderAlert.reorder_point / 14.0, 0.001,
    )

    # Severity tier ordering: CRITICAL=1, WARNING=2, INFO=3
    severity_order = case(
        (ReorderAlert.severity == "CRITICAL", 1),
        (ReorderAlert.severity == "WARNING", 2),
        else_=3,
    )

    # Apply sort
    if sort_by == "created_at":
        order_col = ReorderAlert.created_at.desc()
    elif sort_by == "current_stock":
        order_col = ReorderAlert.current_stock.asc()
    else:
        # Default: severity tier, then days_until_stockout ascending (most urgent first)
        order_col = [severity_order.asc(), days_until_stockout.asc()]

    # Fetch with joins
    stmt = (
        select(
            ReorderAlert.id,
            ReorderAlert.product_id,
            Product.name.label("product_name"),
            ReorderAlert.warehouse_id,
            Warehouse.name.label("warehouse_name"),
            ReorderAlert.current_stock,
            ReorderAlert.reorder_point,
            ReorderAlert.status,
            ReorderAlert.severity,
            ReorderAlert.created_at,
            ReorderAlert.acknowledged_at,
            ReorderAlert.acknowledged_by,
            ReorderAlert.snoozed_until,
            ReorderAlert.snoozed_by,
            ReorderAlert.dismissed_at,
            ReorderAlert.dismissed_by,
        )
        .join(Product, ReorderAlert.product_id == Product.id)
        .join(Warehouse, ReorderAlert.warehouse_id == Warehouse.id)
        .where(*base_where)
        .order_by(*order_col if isinstance(order_col, list) else (order_col,))
        .offset(offset)
        .limit(limit)
    )
    result = await session.execute(stmt)
    rows = result.all()

    items = [
        {
            "id": row.id,
            "product_id": row.product_id,
            "product_name": row.product_name,
            "warehouse_id": row.warehouse_id,
            "warehouse_name": row.warehouse_name,
            "current_stock": row.current_stock,
            "reorder_point": row.reorder_point,
            "status": (
                AlertStatus.PENDING.value
                if (
                    row.status == AlertStatus.SNOOZED
                    and row.snoozed_until is not None
                    and row.snoozed_until <= now
                )
                else (row.status.value if hasattr(row.status, "value") else row.status)
            ),
            "severity": row.severity,
            "created_at": row.created_at,
            "acknowledged_at": row.acknowledged_at,
            "acknowledged_by": row.acknowledged_by,
            "snoozed_until": row.snoozed_until,
            "snoozed_by": row.snoozed_by,
            "dismissed_at": row.dismissed_at,
            "dismissed_by": row.dismissed_by,
        }
        for row in rows
    ]
    return items, total


async def _list_reorder_suggestions_with_supplier_loader(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    warehouse_id: uuid.UUID | None = None,
    product_supplier_loader: _ProductSupplierLoader,
) -> tuple[list[dict], int]:
    """List reorder suggestions with supplier hints."""
    from common.models.inventory_stock import InventoryStock
    from common.models.product import Product
    from common.models.warehouse import Warehouse

    stmt = (
        select(
            InventoryStock.product_id,
            Product.name.label("product_name"),
            Product.code.label("product_code"),
            InventoryStock.warehouse_id,
            Warehouse.name.label("warehouse_name"),
            InventoryStock.quantity.label("current_stock"),
            InventoryStock.reorder_point,
            InventoryStock.target_stock_qty,
            InventoryStock.on_order_qty,
            InventoryStock.in_transit_qty,
            InventoryStock.reserved_qty,
        )
        .join(Product, Product.id == InventoryStock.product_id)
        .join(Warehouse, Warehouse.id == InventoryStock.warehouse_id)
        .where(
            InventoryStock.tenant_id == tenant_id,
            Product.tenant_id == tenant_id,
            Warehouse.tenant_id == tenant_id,
            Product.status == "active",
            InventoryStock.quantity <= InventoryStock.reorder_point,
        )
        .order_by(Warehouse.name, Product.name)
    )
    if warehouse_id is not None:
        stmt = stmt.where(InventoryStock.warehouse_id == warehouse_id)

    result = await session.execute(stmt)
    rows = result.all()

    product_ids = [row.product_id for row in rows]
    supplier_map = await product_supplier_loader(session, tenant_id, product_ids)

    items: list[dict] = []
    for row in rows:
        items.append(
            _serialize_reorder_suggestion_row(
                row,
                supplier_hint=supplier_map.get(row.product_id),
            )
        )

    return items, len(items)


async def list_reorder_suggestions(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    warehouse_id: uuid.UUID | None = None,
) -> tuple[list[dict], int]:
    return await _list_reorder_suggestions_with_supplier_loader(
        session,
        tenant_id,
        warehouse_id=warehouse_id,
        product_supplier_loader=_batch_get_product_suppliers,
    )
