"""Alert commands — write operations that modify alert state."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
import uuid
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.time import utc_now
from common.time import today
from domains.inventory._alert_support import (
    _release_expired_snooze,
    _load_reorder_suggestion_source,
    _serialize_reorder_suggestion_row,
)
from domains.inventory._product_supplier_support import _batch_get_product_suppliers
from domains.inventory.commands._supplier import create_supplier_order

_ProductSupplierLoader = Callable[
    [AsyncSession, uuid.UUID, list[uuid.UUID]],
    Awaitable[dict[uuid.UUID, dict | None]],
]


async def acknowledge_alert(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    alert_id: uuid.UUID,
    *,
    actor_id: str,
) -> dict | None:
    """Acknowledge a reorder alert."""
    from common.models.reorder_alert import AlertStatus, ReorderAlert

    stmt = select(ReorderAlert).where(
        ReorderAlert.id == alert_id,
        ReorderAlert.tenant_id == tenant_id,
    )
    result = await session.execute(stmt)
    alert = result.scalar_one_or_none()

    if alert is None:
        return None

    _release_expired_snooze(alert, now=utc_now())

    if alert.status in {AlertStatus.RESOLVED, AlertStatus.DISMISSED}:
        return None

    now = utc_now()
    alert.status = AlertStatus.ACKNOWLEDGED
    alert.acknowledged_at = now
    alert.acknowledged_by = actor_id
    await session.flush()

    return {
        "id": alert.id,
        "status": alert.status.value,
        "acknowledged_at": now,
        "acknowledged_by": actor_id,
    }


async def snooze_alert(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    alert_id: uuid.UUID,
    *,
    actor_id: str,
    duration_minutes: int,
) -> dict | None:
    """Snooze a reorder alert for the requested duration."""
    from common.models.reorder_alert import AlertStatus, ReorderAlert

    stmt = select(ReorderAlert).where(
        ReorderAlert.id == alert_id,
        ReorderAlert.tenant_id == tenant_id,
    )
    result = await session.execute(stmt)
    alert = result.scalar_one_or_none()

    if alert is None:
        return None

    _release_expired_snooze(alert, now=utc_now())

    if alert.status in {AlertStatus.RESOLVED, AlertStatus.DISMISSED}:
        return None

    now = utc_now()
    snoozed_until = now + timedelta(minutes=duration_minutes)
    alert.status = AlertStatus.SNOOZED
    alert.snoozed_until = snoozed_until
    alert.snoozed_by = actor_id
    await session.flush()

    return {
        "id": alert.id,
        "status": alert.status.value,
        "snoozed_until": snoozed_until,
        "snoozed_by": actor_id,
    }


async def dismiss_alert(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    alert_id: uuid.UUID,
    *,
    actor_id: str,
) -> dict | None:
    """Dismiss a reorder alert until stock recovers and breaches again."""
    from common.models.reorder_alert import AlertStatus, ReorderAlert

    stmt = select(ReorderAlert).where(
        ReorderAlert.id == alert_id,
        ReorderAlert.tenant_id == tenant_id,
    )
    result = await session.execute(stmt)
    alert = result.scalar_one_or_none()

    if alert is None:
        return None

    _release_expired_snooze(alert, now=utc_now())

    if alert.status in {AlertStatus.RESOLVED, AlertStatus.DISMISSED}:
        return None

    now = utc_now()
    alert.status = AlertStatus.DISMISSED
    alert.dismissed_at = now
    alert.dismissed_by = actor_id
    alert.snoozed_until = None
    alert.snoozed_by = None
    await session.flush()

    return {
        "id": alert.id,
        "status": alert.status.value,
        "dismissed_at": now,
        "dismissed_by": actor_id,
    }


async def _create_reorder_suggestion_orders_with_supplier_loader(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    items: list[dict],
    actor_id: str,
    product_supplier_loader: _ProductSupplierLoader,
) -> dict:
    """Create supplier orders from reorder suggestions."""
    import uuid
    from typing import cast

    grouped_lines: dict[uuid.UUID, dict[str, object]] = {}
    unresolved_rows: list[dict] = []
    order_date = today()

    product_ids = [item["product_id"] for item in items]
    supplier_map = await product_supplier_loader(session, tenant_id, product_ids)

    for item in items:
        product_id = item["product_id"]
        warehouse_id = item["warehouse_id"]
        suggested_qty = int(item["suggested_qty"])

        supplier_hint = supplier_map.get(product_id)
        if supplier_hint is None:
            row = await _load_reorder_suggestion_source(
                session,
                tenant_id,
                product_id=product_id,
                warehouse_id=warehouse_id,
            )
            if row is not None:
                unresolved_rows.append(
                    _serialize_reorder_suggestion_row(
                        row,
                        supplier_hint=None,
                        suggested_qty_override=suggested_qty,
                    )
                )
            continue

        supplier_id = supplier_hint["supplier_id"]
        group = grouped_lines.setdefault(
            supplier_id,
            {
                "supplier_hint": supplier_hint,
                "lines": [],
            },
        )
        cast(list[dict], group["lines"]).append(
            {
                "product_id": product_id,
                "warehouse_id": warehouse_id,
                "quantity_ordered": suggested_qty,
                "unit_price": supplier_hint.get("unit_cost"),
            }
        )

    created_orders: list[dict] = []
    for supplier_id, group in grouped_lines.items():
        supplier_hint = cast(dict[str, object], group["supplier_hint"])
        lines = cast(list[dict], group["lines"])
        lead_time_days = supplier_hint.get("default_lead_time_days")
        expected_arrival_date = (
            order_date + timedelta(days=int(lead_time_days))
            if lead_time_days is not None
            else None
        )
        created_order = await create_supplier_order(
            session,
            tenant_id,
            supplier_id=supplier_id,
            order_date=order_date,
            expected_arrival_date=expected_arrival_date,
            lines=lines,
            actor_id=actor_id,
        )
        created_orders.append(
            {
                "order_id": created_order["id"],
                "order_number": created_order["order_number"],
                "supplier_id": created_order["supplier_id"],
                "supplier_name": created_order["supplier_name"],
                "line_count": len(lines),
            }
        )

    return {
        "created_orders": created_orders,
        "unresolved_rows": unresolved_rows,
    }


async def create_reorder_suggestion_orders(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    items: list[dict],
    actor_id: str,
) -> dict:
    return await _create_reorder_suggestion_orders_with_supplier_loader(
        session,
        tenant_id,
        items=items,
        actor_id=actor_id,
        product_supplier_loader=_batch_get_product_suppliers,
    )
