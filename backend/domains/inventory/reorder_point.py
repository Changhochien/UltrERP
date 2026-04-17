"""Reorder point computation service — preview and apply.

Provides explainable reorder point calculation using real demand history and
replenishment lead times. Operates in two phases:
  1. Preview — dry-run computation for eligible inventory rows
  2. Apply   — updates reorder_point only on explicitly selected rows
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.models.inventory_stock import InventoryStock
from common.models.product import Product
from common.models.stock_adjustment import ReasonCode, StockAdjustment
from common.models.supplier import Supplier
from common.models.supplier_order import SupplierOrder, SupplierOrderLine, SupplierOrderStatus
from common.models.warehouse import Warehouse
from common.tenant import DEFAULT_TENANT_ID
from common.time import utc_now

# Sentinel for unresolved source
SOURCE_UNRESOLVED = "source_unresolved"
# Minimum demand events required in the lookback window
MIN_DEMAND_EVENTS = 2
# Default lead time fallback when no history exists
DEFAULT_LEAD_TIME_DAYS = 7


async def _build_shared_history_context(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
) -> dict[str, Any] | None:
    from domains.inventory.services import get_planning_support

    planning_support = await get_planning_support(
        session,
        tenant_id,
        product_id,
        months=12,
        include_current_month=True,
    )
    if planning_support is None or planning_support["data_gap"]:
        return None

    history_months_used = int(planning_support["history_months_used"])
    avg_monthly_quantity = None
    if history_months_used > 0:
        total_quantity = sum(
            Decimal(str(item["quantity"]))
            for item in planning_support["items"]
        )
        avg_monthly_quantity = float(total_quantity / Decimal(history_months_used))
    elif planning_support["avg_monthly_quantity"] is not None:
        avg_monthly_quantity = float(planning_support["avg_monthly_quantity"])

    return {
        "advisory_only": bool(planning_support["advisory_only"]),
        "data_basis": planning_support["data_basis"],
        "history_months_used": history_months_used,
        "avg_monthly_quantity": avg_monthly_quantity,
        "seasonality_index": (
            float(planning_support["seasonality_index"])
            if planning_support["seasonality_index"] is not None
            else None
        ),
        "current_month_live_quantity": (
            float(planning_support["current_month_live_quantity"])
            if planning_support["current_month_live_quantity"] is not None
            else None
        ),
    }


# ── Average daily usage ─────────────────────────────────────────


async def get_average_daily_usage(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    lookback_days: int = 90,
    allowed_reasons: tuple[ReasonCode, ...] = (ReasonCode.SALES_RESERVATION,),
) -> tuple[float, int]:
    """Return (avg_daily_usage, movement_count) for whitelisted outbound reasons.

    Sums absolute quantity_change for allowed reason codes within the lookback
    window, then divides by lookback_days.
    Returns (0.0, 0) when no qualifying events exist.
    """
    cutoff = utc_now() - timedelta(days=lookback_days)
    stmt = (
        select(
            func.coalesce(func.sum(func.abs(StockAdjustment.quantity_change)), 0).label("total"),
            func.count(StockAdjustment.id).label("movement_count"),
        )
        .where(
            StockAdjustment.tenant_id == tenant_id,
            StockAdjustment.product_id == product_id,
            StockAdjustment.warehouse_id == warehouse_id,
            StockAdjustment.reason_code.in_(allowed_reasons),
            StockAdjustment.created_at >= cutoff,
        )
    )
    result = await session.execute(stmt)
    row = result.one()

    total_quantity = row.total or 0
    movement_count = row.movement_count or 0

    if movement_count == 0:
        return 0.0, 0

    avg_daily = total_quantity / lookback_days
    return round(avg_daily, 4), movement_count


# ── Replenishment source resolution ──────────────────────────────


async def resolve_replenishment_source(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    lookback_days: int = 180,
) -> str | uuid.UUID:
    """Resolve the dominant supplier for a product+warehouse from received orders.

    Examines supplier order history within the lookback window and selects the
    supplier with the most received lines. If the top supplier accounts for more
    than 60% of all received lines, it is returned as resolved. Otherwise returns
    SOURCE_UNRESOLVED.
    """
    cutoff = utc_now() - timedelta(days=lookback_days)

    # Count received lines per supplier for this product+warehouse
    stmt = (
        select(
            SupplierOrder.supplier_id,
            func.count(SupplierOrderLine.id).label("line_count"),
        )
        .join(SupplierOrderLine, SupplierOrderLine.order_id == SupplierOrder.id)
        .where(
            SupplierOrder.tenant_id == tenant_id,
            SupplierOrderLine.product_id == product_id,
            SupplierOrderLine.warehouse_id == warehouse_id,
            SupplierOrder.status == SupplierOrderStatus.RECEIVED,
            SupplierOrder.received_date >= cutoff,
        )
        .group_by(SupplierOrder.supplier_id)
        .order_by(func.count(SupplierOrderLine.id).desc())
    )
    result = await session.execute(stmt)
    rows = list(result.all())

    if not rows:
        return SOURCE_UNRESOLVED

    total_lines = sum(r.line_count for r in rows)
    top_supplier_id = rows[0].supplier_id
    top_line_count = rows[0].line_count

    if top_line_count / total_lines > 0.6:
        return top_supplier_id

    return SOURCE_UNRESOLVED


# ── Actual lead time calculation ─────────────────────────────────


async def get_actual_lead_time_days(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    supplier_id: uuid.UUID,
    lookback_days: int = 180,
) -> int | None:
    """Calculate average lead time in days from order_date to received_date.

    Returns None when no received orders exist for the given supplier within
    the lookback window.
    """
    cutoff = utc_now() - timedelta(days=lookback_days)

    stmt = (
        select(
            func.avg(
                func.date_trunc("day", SupplierOrder.received_date)
                - func.date_trunc("day", SupplierOrder.order_date)
            ).label("avg_lead_days")
        )
        .join(SupplierOrderLine, SupplierOrderLine.order_id == SupplierOrder.id)
        .where(
            SupplierOrder.tenant_id == tenant_id,
            SupplierOrder.supplier_id == supplier_id,
            SupplierOrderLine.product_id == product_id,
            SupplierOrderLine.warehouse_id == warehouse_id,
            SupplierOrder.status == SupplierOrderStatus.RECEIVED,
            SupplierOrder.received_date >= cutoff,
        )
    )
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()

    if row is None:
        return None

    if isinstance(row, timedelta):
        average_days = row.total_seconds() / 86_400
    else:
        average_days = float(row)

    if average_days < 0:
        return None

    return max(1, round(average_days))


async def get_actual_lead_time_sample_count(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    supplier_id: uuid.UUID,
    lookback_days: int = 180,
) -> int:
    cutoff = utc_now() - timedelta(days=lookback_days)

    stmt = (
        select(func.count(SupplierOrder.id))
        .join(SupplierOrderLine, SupplierOrderLine.order_id == SupplierOrder.id)
        .where(
            SupplierOrder.tenant_id == tenant_id,
            SupplierOrder.supplier_id == supplier_id,
            SupplierOrderLine.product_id == product_id,
            SupplierOrderLine.warehouse_id == warehouse_id,
            SupplierOrder.status == SupplierOrderStatus.RECEIVED,
            SupplierOrder.received_date >= cutoff,
        )
    )
    result = await session.execute(stmt)
    return int(result.scalar_one_or_none() or 0)


def _lead_time_confidence(sample_count: int | None) -> str | None:
    if sample_count is None or sample_count <= 0:
        return None
    if sample_count >= 5:
        return "high"
    if sample_count >= 2:
        return "medium"
    return "low"


async def get_lead_time_days(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    lookback_days: int = 180,
) -> tuple[int, str]:
    """Resolve lead time using fallback chain, returning (lead_time, source).

    Source is one of: "actual", "supplier_default", "fallback"
    """
    # Step 1: resolve source supplier
    source = await resolve_replenishment_source(
        session, tenant_id, product_id, warehouse_id, lookback_days
    )

    if source != SOURCE_UNRESOLVED:
        actual_lt = await get_actual_lead_time_days(
            session, tenant_id, product_id, warehouse_id, source, lookback_days
        )
        if actual_lt is not None:
            return actual_lt, "actual"

    # Step 2: supplier default lead time — try resolved source, or any supplier if unresolved.
    # Even when source is ambiguous (SOURCE_UNRESOLVED), use a supplier's default if found.
    lookup_supplier_id = source if source != SOURCE_UNRESOLVED else None
    if lookup_supplier_id is not None:
        supplier_stmt = select(Supplier.default_lead_time_days).where(
            Supplier.id == lookup_supplier_id,
            Supplier.tenant_id == tenant_id,
        )
        supplier_result = await session.execute(supplier_stmt)
        default_lt = supplier_result.scalar_one_or_none()
        if default_lt is not None and default_lt > 0:
            return default_lt, "supplier_default"

    # If source was unresolved and we couldn't get a supplier default, try to find
    # any supplier that has delivered this product+warehouse (less preferred but usable).
    if lookup_supplier_id is None:
        fallback_stmt = (
            select(Supplier.default_lead_time_days)
            .join(SupplierOrder, SupplierOrder.supplier_id == Supplier.id)
            .join(SupplierOrderLine, SupplierOrderLine.order_id == SupplierOrder.id)
            .where(
                Supplier.tenant_id == tenant_id,
                Supplier.is_active == True,
                SupplierOrderLine.product_id == product_id,
                SupplierOrderLine.warehouse_id == warehouse_id,
                Supplier.default_lead_time_days.isnot(None),
            )
            .order_by(Supplier.default_lead_time_days.desc())
            .limit(1)
        )
        fallback_result = await session.execute(fallback_stmt)
        fallback_lt = fallback_result.scalar_one_or_none()
        if fallback_lt is not None and fallback_lt > 0:
            return fallback_lt, "supplier_default"

    # Step 3: fallback
    return DEFAULT_LEAD_TIME_DAYS, "fallback_7d"


# ── Single-row reorder point preview ────────────────────────────


async def compute_reorder_point_preview_row(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    safety_factor: float = 0.5,
    review_cycle_days: int = 0,
    demand_lookback_days: int = 90,
    lead_time_lookback_days: int = 180,
    allowed_reasons: tuple[ReasonCode, ...] = (ReasonCode.SALES_RESERVATION,),
    lead_time_days_override: int | None = None,
    current_quantity: float = 0.0,
) -> dict[str, Any]:
    """Compute reorder point for a single product+warehouse row.

    Returns a dict with all explanation columns plus a ``skipped_reason`` field.
    When ``skipped_reason`` is non-None the row was not computed.
    """
    # Check demand history
    avg_daily_usage, movement_count = await get_average_daily_usage(
        session, tenant_id, product_id, warehouse_id, demand_lookback_days, allowed_reasons
    )

    if movement_count < MIN_DEMAND_EVENTS:
        return {
            "product_id": product_id,
            "warehouse_id": warehouse_id,
            "reorder_point": 0,
            "safety_stock": 0.0,
            "avg_daily_usage": 0.0,
            "lead_time_days": 0,
            "review_cycle_days": review_cycle_days,
            "lead_time_source": "",
            "safety_factor": safety_factor,
            "demand_lookback_days": demand_lookback_days,
            "demand_reason": [r.value for r in allowed_reasons],
            "movement_count": movement_count,
            "skipped_reason": "insufficient_history",
            "quality_note": (
                f"Only {movement_count} demand events in {demand_lookback_days} days; "
                f"need at least {MIN_DEMAND_EVENTS}"
            ),
            "target_stock_level": None,
            "suggested_order_qty": None,
        }

    # Resolve lead time
    if lead_time_days_override is not None and lead_time_days_override > 0:
        lead_time_days = lead_time_days_override
        lt_source = "manual_override"
    else:
        lead_time_days, lt_source = await get_lead_time_days(
            session, tenant_id, product_id, warehouse_id, lead_time_lookback_days
        )

    lead_time_sample_count: int | None = None
    lead_time_confidence: str | None = None
    if lt_source == "actual":
        supplier_id = await resolve_replenishment_source(
            session,
            tenant_id,
            product_id,
            warehouse_id,
            lead_time_lookback_days,
        )
        if supplier_id != SOURCE_UNRESOLVED:
            lead_time_sample_count = await get_actual_lead_time_sample_count(
                session,
                tenant_id,
                product_id,
                warehouse_id,
                supplier_id,
                lead_time_lookback_days,
            )
            lead_time_confidence = _lead_time_confidence(lead_time_sample_count)

    # Compute ROP
    safety_stock = round(avg_daily_usage * safety_factor * lead_time_days, 2)
    reorder_point = round((lead_time_days * avg_daily_usage) + safety_stock)
    target_stock_level = round((avg_daily_usage * (lead_time_days + review_cycle_days)) + safety_stock)

    suggested_order_qty = max(0, round(target_stock_level - current_quantity))
    return {
        "product_id": product_id,
        "warehouse_id": warehouse_id,
        "reorder_point": reorder_point,
        "safety_stock": safety_stock,
        "avg_daily_usage": round(avg_daily_usage, 4),
        "lead_time_days": lead_time_days,
        "review_cycle_days": review_cycle_days,
        "lead_time_source": lt_source,
        "lead_time_sample_count": lead_time_sample_count,
        "lead_time_confidence": lead_time_confidence,
        "safety_factor": safety_factor,
        "demand_lookback_days": demand_lookback_days,
        "demand_reason": [r.value for r in allowed_reasons],
        "movement_count": movement_count,
        "skipped_reason": None,
        "quality_note": None,
        "target_stock_level": target_stock_level,
        "suggested_order_qty": suggested_order_qty,
    }


# ── Preview: iterate eligible inventory rows ─────────────────────


async def compute_reorder_points_preview(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    safety_factor: float = 0.5,
    demand_lookback_days: int = 90,
    lead_time_lookback_days: int = 180,
    warehouse_id: uuid.UUID | None = None,
    category: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Compute reorder points for all eligible active-product inventory rows.

    Filters:
      - product.status == 'active'
      - has an InventoryStock row (quantity >= 0)
      - optionally warehouse_id
      - optionally category

    Returns (candidate_rows, skipped_rows) where candidates have
    ``skipped_reason is None`` and skipped rows have a non-None reason.
    """
    # Build base query: active products that have an inventory stock row
    conditions = [
        Product.tenant_id == tenant_id,
        Product.status == "active",
        InventoryStock.tenant_id == tenant_id,
        InventoryStock.product_id == Product.id,
    ]
    if warehouse_id is not None:
        conditions.append(InventoryStock.warehouse_id == warehouse_id)
    if category is not None:
        conditions.append(Product.category == category)

    stmt = (
        select(
            Product.id.label("product_id"),
            Product.name.label("product_name"),
            Product.category.label("category"),
            InventoryStock.id.label("stock_id"),
            InventoryStock.warehouse_id.label("warehouse_id"),
            InventoryStock.quantity.label("current_quantity"),
            InventoryStock.reorder_point.label("current_reorder_point"),
            InventoryStock.safety_factor.label("stored_safety_factor"),
            InventoryStock.lead_time_days.label("stored_lead_time_days"),
            InventoryStock.policy_type.label("policy_type"),
            InventoryStock.target_stock_qty.label("target_stock_qty"),
            InventoryStock.on_order_qty.label("on_order_qty"),
            InventoryStock.in_transit_qty.label("in_transit_qty"),
            InventoryStock.reserved_qty.label("reserved_qty"),
            InventoryStock.planning_horizon_days.label("planning_horizon_days"),
            InventoryStock.review_cycle_days.label("review_cycle_days"),
            Warehouse.name.label("warehouse_name"),
        )
        .join(InventoryStock, InventoryStock.product_id == Product.id)
        .join(Warehouse, Warehouse.id == InventoryStock.warehouse_id)
        .where(and_(*conditions))
    )
    result = await session.execute(stmt)
    rows = result.all()

    candidates: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    shared_history_contexts: dict[uuid.UUID, dict[str, Any] | None] = {}

    for row in rows:
        effective_safety_factor = (
            row.stored_safety_factor
            if row.stored_safety_factor is not None and row.stored_safety_factor > 0
            else safety_factor
        )
        preview = await compute_reorder_point_preview_row(
            session,
            tenant_id,
            row.product_id,
            row.warehouse_id,
            effective_safety_factor,
            row.review_cycle_days or 0,
            demand_lookback_days,
            lead_time_lookback_days,
            lead_time_days_override=(
                row.stored_lead_time_days if row.stored_lead_time_days and row.stored_lead_time_days > 0 else None
            ),
            current_quantity=row.current_quantity,
        )
        preview["product_name"] = row.product_name
        preview["category"] = row.category
        preview["current_quantity"] = row.current_quantity
        preview["current_reorder_point"] = row.current_reorder_point
        preview["inventory_position"] = int(
            (row.current_quantity or 0)
            + (row.on_order_qty or 0)
            + (row.in_transit_qty or 0)
            - (row.reserved_qty or 0)
        )
        preview["on_order_qty"] = int(row.on_order_qty or 0)
        preview["in_transit_qty"] = int(row.in_transit_qty or 0)
        preview["reserved_qty"] = int(row.reserved_qty or 0)
        preview["policy_type"] = row.policy_type or "continuous"
        preview["target_stock_qty"] = int(row.target_stock_qty or 0)
        preview["planning_horizon_days"] = int(row.planning_horizon_days or 0)
        preview["effective_horizon_days"] = max(
            int(row.planning_horizon_days or 0),
            int(row.review_cycle_days or 0),
        )
        preview["stock_id"] = row.stock_id
        preview["warehouse_name"] = row.warehouse_name
        if row.product_id not in shared_history_contexts:
            shared_history_contexts[row.product_id] = await _build_shared_history_context(
                session,
                tenant_id,
                row.product_id,
            )
        preview["shared_history_context"] = shared_history_contexts[row.product_id]

        if preview["skipped_reason"] is not None:
            skipped.append(preview)
        else:
            candidates.append(preview)

    return candidates, skipped


# ── Apply: update only explicitly selected rows ──────────────────


async def apply_reorder_points(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    selected_rows: list[dict[str, Any]],
    safety_factor: float,
    demand_lookback_days: int,
    lead_time_lookback_days: int,
) -> dict[str, Any]:
    """Apply reorder points to explicitly selected preview rows.

    Updates persisted replenishment settings for rows whose product_id +
    warehouse_id match a selected row. Returns a summary dict.
    """
    updated_count = 0
    skipped_count = 0

    for row in selected_rows:
        product_id = row["product_id"]
        warehouse_id = row["warehouse_id"]
        new_rop = row["reorder_point"]

        stmt = (
            select(InventoryStock)
            .where(
                InventoryStock.tenant_id == tenant_id,
                InventoryStock.product_id == product_id,
                InventoryStock.warehouse_id == warehouse_id,
            )
            .with_for_update()
        )
        result = await session.execute(stmt)
        stock = result.scalar_one_or_none()

        if stock is None:
            skipped_count += 1
            continue

        stock.reorder_point = new_rop
        stock.safety_factor = float(row.get("safety_factor") or safety_factor)
        stock.lead_time_days = int(row.get("lead_time_days") or 0)
        stock.review_cycle_days = int(row.get("review_cycle_days") or 0)
        updated_count += 1

    await session.flush()

    return {
        "updated_count": updated_count,
        "skipped_count": skipped_count,
        "safety_factor": safety_factor,
        "demand_lookback_days": demand_lookback_days,
        "lead_time_lookback_days": lead_time_lookback_days,
    }
