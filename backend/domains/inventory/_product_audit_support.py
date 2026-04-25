"""Private product-audit helpers shared across inventory modules."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.models.audit_log import AuditLog
from common.models.inventory_stock import InventoryStock


async def get_product_audit_log(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """Fetch audit log entries for a product.

    Returns entries for both inventory_stock field changes
    (reorder_point, safety_factor, lead_time_days) and product status changes.
    Each field that changed becomes a separate entry.
    """
    stock_ids_sq = (
        select(InventoryStock.id)
        .where(
            InventoryStock.tenant_id == tenant_id,
            InventoryStock.product_id == product_id,
        )
        .subquery()
    )

    stock_logs = (
        select(
            AuditLog.id,
            AuditLog.created_at,
            AuditLog.actor_id,
            AuditLog.before_state,
            AuditLog.after_state,
            AuditLog.entity_type,
        )
        .where(
            AuditLog.tenant_id == tenant_id,
            AuditLog.entity_type == "inventory_stock",
            AuditLog.entity_id.in_(select(stock_ids_sq)),
        )
    )

    product_logs = (
        select(
            AuditLog.id,
            AuditLog.created_at,
            AuditLog.actor_id,
            AuditLog.before_state,
            AuditLog.after_state,
            AuditLog.entity_type,
        )
        .where(
            AuditLog.tenant_id == tenant_id,
            AuditLog.entity_type == "product",
            AuditLog.entity_id == str(product_id),
        )
    )

    all_union = stock_logs.union(product_logs).subquery()
    count_stmt = select(func.count()).select_from(all_union)
    count_result = await session.execute(count_stmt)
    total = count_result.scalar() or 0

    fetch_stmt = (
        select(
            AuditLog.id,
            AuditLog.created_at,
            AuditLog.actor_id,
            AuditLog.before_state,
            AuditLog.after_state,
            AuditLog.entity_type,
        )
        .where(
            AuditLog.tenant_id == tenant_id,
            AuditLog.entity_type.in_(["inventory_stock", "product"]),
            (
                AuditLog.entity_type == "inventory_stock"
                & AuditLog.entity_id.in_(select(stock_ids_sq))
            )
            | (AuditLog.entity_type == "product" & AuditLog.entity_id == str(product_id)),
        )
        .order_by(AuditLog.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await session.execute(fetch_stmt)
    rows = result.all()

    items = []
    for row in rows:
        before = row.before_state or {}
        after = row.after_state or {}

        if row.entity_type == "inventory_stock":
            for field in ("reorder_point", "safety_factor", "lead_time_days"):
                old_val = before.get(field)
                new_val = after.get(field)
                if old_val is not None or new_val is not None:
                    items.append(
                        {
                            "id": row.id,
                            "created_at": row.created_at,
                            "actor_id": row.actor_id,
                            "field": field,
                            "old_value": str(old_val) if old_val is not None else None,
                            "new_value": str(new_val) if new_val is not None else None,
                        }
                    )
        elif row.entity_type == "product":
            old_status = before.get("status")
            new_status = after.get("status")
            if old_status is not None or new_status is not None:
                items.append(
                    {
                        "id": row.id,
                        "created_at": row.created_at,
                        "actor_id": row.actor_id,
                        "field": "status",
                        "old_value": str(old_status) if old_status is not None else None,
                        "new_value": str(new_status) if new_status is not None else None,
                    }
                )

    items.sort(key=lambda x: x["created_at"], reverse=True)

    return {"items": items, "total": total}