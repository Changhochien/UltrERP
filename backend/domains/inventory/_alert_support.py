"""Private alert helpers shared across inventory modules."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.models.inventory_stock import InventoryStock
from common.models.product import Product
from common.models.reorder_alert import AlertStatus, ReorderAlert
from common.models.warehouse import Warehouse
from common.time import utc_now


def _compute_severity(current_stock: int, reorder_point: int) -> str:
    """Compute alert severity based on stock level."""
    if current_stock == 0:
        return "CRITICAL"
    if reorder_point > 0 and current_stock < reorder_point * 0.25:
        return "CRITICAL"
    if current_stock < reorder_point:
        return "WARNING"
    return "INFO"


def _release_expired_snooze(alert: ReorderAlert, *, now) -> None:
    if (
        alert.status == AlertStatus.SNOOZED
        and alert.snoozed_until is not None
        and alert.snoozed_until <= now
    ):
        alert.status = AlertStatus.PENDING
        alert.snoozed_until = None
        alert.snoozed_by = None


async def _check_reorder_alert(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    current_quantity: int,
    reorder_point: int,
) -> None:
    """Create or resolve reorder alert based on stock level."""
    if reorder_point <= 0:
        return

    now = utc_now()

    stmt = select(ReorderAlert).where(
        ReorderAlert.tenant_id == tenant_id,
        ReorderAlert.product_id == product_id,
        ReorderAlert.warehouse_id == warehouse_id,
    )
    result = await session.execute(stmt)
    alert = result.scalar_one_or_none()

    # NOTE: Alerts trigger at <= (proactive), while is_below_reorder
    # display flag uses strict < ("at reorder point" is not "below").
    if current_quantity <= reorder_point:
        severity = _compute_severity(current_quantity, reorder_point)
        if alert is None:
            alert = ReorderAlert(
                tenant_id=tenant_id,
                product_id=product_id,
                warehouse_id=warehouse_id,
                current_stock=current_quantity,
                reorder_point=reorder_point,
                status=AlertStatus.PENDING,
                severity=severity,
            )
            session.add(alert)
        else:
            previous_stock = alert.current_stock
            _release_expired_snooze(alert, now=now)
            alert.current_stock = current_quantity
            alert.severity = severity
            # Only collapse RESOLVED -> PENDING; preserve ACKNOWLEDGED
            if alert.status == AlertStatus.RESOLVED:
                alert.status = AlertStatus.PENDING
            elif alert.status == AlertStatus.DISMISSED and previous_stock > reorder_point:
                alert.status = AlertStatus.PENDING
                alert.dismissed_at = None
                alert.dismissed_by = None
            # ACKNOWLEDGED stays acknowledged — do not demote
    elif alert is not None:
        _release_expired_snooze(alert, now=now)
        alert.current_stock = current_quantity
        if alert.status in {AlertStatus.PENDING, AlertStatus.SNOOZED}:
            # Only active alerts auto-resolve when stock is restored.
            # ACKNOWLEDGED alerts require explicit resolution or a real supplier delivery.
            alert.status = AlertStatus.RESOLVED
            alert.snoozed_until = None
            alert.snoozed_by = None
    # If alert is ACKNOWLEDGED and stock is above threshold: do nothing (keep acknowledged)


async def _load_reorder_suggestion_source(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    product_id: uuid.UUID,
    warehouse_id: uuid.UUID,
):
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
            Product.id == product_id,
            Warehouse.id == warehouse_id,
        )
    )
    result = await session.execute(stmt)
    return result.first()


def _int_field(row: object, name: str) -> int:
    return int(getattr(row, name, 0) or 0)


def _serialize_reorder_suggestion_row(
    row: object,
    *,
    supplier_hint: dict | None,
    suggested_qty_override: int | None = None,
) -> dict:
    current_stock = _int_field(row, "current_stock")
    reorder_point = _int_field(row, "reorder_point")
    on_order_qty = _int_field(row, "on_order_qty")
    in_transit_qty = _int_field(row, "in_transit_qty")
    reserved_qty = _int_field(row, "reserved_qty")
    raw_target_stock_qty = _int_field(row, "target_stock_qty")
    target_stock_qty = raw_target_stock_qty if raw_target_stock_qty > 0 else None
    inventory_position = current_stock + on_order_qty + in_transit_qty - reserved_qty
    base_target = target_stock_qty if target_stock_qty is not None else reorder_point
    suggested_qty = max(0, base_target - inventory_position)
    if suggested_qty_override is not None:
        suggested_qty = suggested_qty_override

    return {
        "product_id": getattr(row, "product_id"),
        "product_name": getattr(row, "product_name"),
        "product_code": getattr(row, "product_code", None),
        "warehouse_id": getattr(row, "warehouse_id"),
        "warehouse_name": getattr(row, "warehouse_name"),
        "current_stock": current_stock,
        "reorder_point": reorder_point,
        "inventory_position": inventory_position,
        "target_stock_qty": target_stock_qty,
        "suggested_qty": suggested_qty,
        "supplier_hint": supplier_hint,
    }