"""Reorder point computation service — preview and apply.

Provides explainable reorder point calculation using real demand history and
replenishment lead times. Operates in two phases:
  1. Preview — dry-run computation for eligible inventory rows
  2. Apply   — updates reorder_point only on explicitly selected rows
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
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
# Supported replenishment policies
POLICY_CONTINUOUS = "continuous"
POLICY_PERIODIC = "periodic"
POLICY_MANUAL = "manual"
# Minimum demand events required in the lookback window
MIN_DEMAND_EVENTS = 2
# Explicit business default lead time for container replenishment when no row-level or supplier signal exists.
DEFAULT_LEAD_TIME_DAYS = 80


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
    lead_time_days, _sample_count = await get_actual_lead_time_stats(
        session,
        tenant_id,
        product_id,
        warehouse_id,
        supplier_id,
        lookback_days,
    )
    return lead_time_days


async def get_actual_lead_time_stats(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    supplier_id: uuid.UUID,
    lookback_days: int = 180,
) -> tuple[int | None, int]:
    """Calculate average lead time in days from order_date to received_date.

    Returns ``(lead_time_days, sample_count)`` and ``(None, 0)`` when no received orders exist for the given supplier within
    the lookback window.
    """
    cutoff = utc_now() - timedelta(days=lookback_days)

    stmt = (
        select(
            func.avg(
                func.date_trunc("day", SupplierOrder.received_date)
                - func.date_trunc("day", SupplierOrder.order_date)
            ).label("avg_lead_days"),
            func.count(func.distinct(SupplierOrder.id)).label("sample_count"),
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
    row = result.one()

    avg_lead_days = row.avg_lead_days
    sample_count = int(row.sample_count or 0)

    if avg_lead_days is None:
        return None, sample_count

    if hasattr(avg_lead_days, "total_seconds"):
        avg_lead_days_value = avg_lead_days.total_seconds() / 86400
    else:
        avg_lead_days_value = float(avg_lead_days)

    if avg_lead_days_value < 0:
        return None, sample_count

    return max(1, round(avg_lead_days_value)), sample_count


def _get_lead_time_confidence(source: str, sample_count: int) -> str:
    if source == "manual_override":
        return "high"
    if source == "actual":
        if sample_count >= 5:
            return "high"
        if sample_count >= 2:
            return "medium"
        return "low"
    if source == "supplier_default":
        return "medium"
    return "low"


async def get_lead_time_details(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    lookback_days: int = 180,
) -> tuple[int, str, int, str]:
    """Resolve lead time using fallback chain with sample count and confidence."""
    source = await resolve_replenishment_source(
        session, tenant_id, product_id, warehouse_id, lookback_days
    )

    if source != SOURCE_UNRESOLVED:
        actual_lt, sample_count = await get_actual_lead_time_stats(
            session, tenant_id, product_id, warehouse_id, source, lookback_days
        )
        if actual_lt is not None:
            return actual_lt, "actual", sample_count, _get_lead_time_confidence("actual", sample_count)

    lookup_supplier_id = source if source != SOURCE_UNRESOLVED else None
    if lookup_supplier_id is not None:
        supplier_stmt = select(Supplier.default_lead_time_days).where(
            Supplier.id == lookup_supplier_id,
            Supplier.tenant_id == tenant_id,
        )
        supplier_result = await session.execute(supplier_stmt)
        default_lt = supplier_result.scalar_one_or_none()
        if default_lt is not None and default_lt > 0:
            return default_lt, "supplier_default", 0, _get_lead_time_confidence("supplier_default", 0)

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
            return fallback_lt, "supplier_default", 0, _get_lead_time_confidence("supplier_default", 0)

    return DEFAULT_LEAD_TIME_DAYS, "business_default", 0, _get_lead_time_confidence("business_default", 0)


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
    lead_time_days, source, _sample_count, _confidence = await get_lead_time_details(
        session,
        tenant_id,
        product_id,
        warehouse_id,
        lookback_days,
    )
    return lead_time_days, source


def _normalize_policy_type(policy_type: str | None, review_cycle_days: int = 0) -> str:
    if policy_type == POLICY_MANUAL:
        return POLICY_MANUAL
    if review_cycle_days > 0:
        return POLICY_PERIODIC
    if policy_type in {POLICY_CONTINUOUS, POLICY_PERIODIC}:
        return policy_type
    return POLICY_CONTINUOUS


def _compute_inventory_position(
    current_quantity: float,
    on_order_qty: int,
    in_transit_qty: int,
    reserved_qty: int,
) -> int:
    return int(round(current_quantity + on_order_qty + in_transit_qty - reserved_qty))


def _build_quality_note(
    lead_time_source: str,
    lead_time_sample_count: int,
    lead_time_confidence: str,
    policy_type: str,
    target_stock_qty: int,
    review_cycle_days: int,
) -> str | None:
    notes: list[str] = []

    if lead_time_source == "business_default":
        notes.append(
            f"Lead time uses the business default of {DEFAULT_LEAD_TIME_DAYS} days for container replenishment; confidence is low."
        )
    elif lead_time_source == "supplier_default":
        notes.append("Lead time uses the supplier default with no receipt samples; confidence is medium.")
    elif lead_time_source == "actual" and lead_time_sample_count > 0 and lead_time_confidence != "high":
        sample_label = "sample" if lead_time_sample_count == 1 else "samples"
        notes.append(
            f"Lead time is based on {lead_time_sample_count} historical {sample_label}; confidence is {lead_time_confidence}."
        )

    if policy_type == POLICY_CONTINUOUS and target_stock_qty <= 0:
        notes.append("Continuous policy has no target stock configured, so suggested order only tops up to the reorder point.")
    elif policy_type == POLICY_PERIODIC and review_cycle_days <= 0 and target_stock_qty <= 0:
        notes.append("Periodic policy has no review cycle or target stock configured, so target stock falls back to lead-time coverage.")

    return " ".join(notes) or None


def _compute_target_stock_level(
    policy_type: str,
    target_stock_qty: int,
    reorder_point: int,
    avg_daily_usage: float,
    lead_time_days: int,
    planning_horizon_days: int,
    review_cycle_days: int,
    safety_stock: float,
) -> int:
    if target_stock_qty > 0:
        return target_stock_qty

    if policy_type == POLICY_PERIODIC:
        effective_horizon_days = planning_horizon_days if planning_horizon_days > 0 else review_cycle_days
        return round((avg_daily_usage * (lead_time_days + effective_horizon_days)) + safety_stock)

    return reorder_point


# ── Single-row reorder point preview ────────────────────────────


async def compute_reorder_point_preview_row(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    safety_factor: float = 0.5,
    policy_type: str | None = None,
    target_stock_qty: int = 0,
    planning_horizon_days: int = 0,
    review_cycle_days: int = 0,
    demand_lookback_days: int = 90,
    lead_time_lookback_days: int = 180,
    allowed_reasons: tuple[ReasonCode, ...] = (ReasonCode.SALES_RESERVATION,),
    lead_time_days_override: int | None = None,
    current_quantity: float = 0.0,
    on_order_qty: int = 0,
    in_transit_qty: int = 0,
    reserved_qty: int = 0,
) -> dict[str, Any]:
    """Compute reorder point for a single product+warehouse row.

    Returns a dict with all explanation columns plus a ``skipped_reason`` field.
    When ``skipped_reason`` is non-None the row was not computed.
    """
    normalized_policy = _normalize_policy_type(policy_type, review_cycle_days)
    inventory_position = _compute_inventory_position(
        current_quantity,
        on_order_qty,
        in_transit_qty,
        reserved_qty,
    )
    effective_horizon_days = planning_horizon_days if planning_horizon_days > 0 else review_cycle_days

    if normalized_policy == POLICY_MANUAL:
        return {
            "product_id": product_id,
            "warehouse_id": warehouse_id,
            "policy_type": normalized_policy,
            "reorder_point": 0,
            "safety_stock": 0.0,
            "avg_daily_usage": 0.0,
            "lead_time_days": 0,
            "review_cycle_days": review_cycle_days,
            "planning_horizon_days": planning_horizon_days,
            "effective_horizon_days": effective_horizon_days,
            "target_stock_qty": target_stock_qty,
            "inventory_position": inventory_position,
            "on_order_qty": on_order_qty,
            "in_transit_qty": in_transit_qty,
            "reserved_qty": reserved_qty,
            "lead_time_source": "",
            "lead_time_sample_count": None,
            "lead_time_confidence": None,
            "safety_factor": safety_factor,
            "demand_lookback_days": demand_lookback_days,
            "demand_reason": [r.value for r in allowed_reasons],
            "movement_count": 0,
            "skipped_reason": "manual_policy",
            "quality_note": "Manual policy rows are excluded from auto-calculated replenishment.",
            "target_stock_level": target_stock_qty if target_stock_qty > 0 else None,
            "suggested_order_qty": None,
        }

    # Check demand history
    avg_daily_usage, movement_count = await get_average_daily_usage(
        session, tenant_id, product_id, warehouse_id, demand_lookback_days, allowed_reasons
    )

    if movement_count < MIN_DEMAND_EVENTS:
        return {
            "product_id": product_id,
            "warehouse_id": warehouse_id,
            "policy_type": normalized_policy,
            "reorder_point": 0,
            "safety_stock": 0.0,
            "avg_daily_usage": 0.0,
            "lead_time_days": 0,
            "review_cycle_days": review_cycle_days,
            "planning_horizon_days": planning_horizon_days,
            "effective_horizon_days": effective_horizon_days,
            "target_stock_qty": target_stock_qty,
            "inventory_position": inventory_position,
            "on_order_qty": on_order_qty,
            "in_transit_qty": in_transit_qty,
            "reserved_qty": reserved_qty,
            "lead_time_source": "",
            "lead_time_sample_count": None,
            "lead_time_confidence": None,
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
        lead_time_sample_count = 0
        lead_time_confidence = _get_lead_time_confidence("manual_override", 0)
    else:
        lead_time_days, lt_source, lead_time_sample_count, lead_time_confidence = await get_lead_time_details(
            session, tenant_id, product_id, warehouse_id, lead_time_lookback_days
        )

    if lead_time_days_override is None and lt_source == "fallback_7d":
        return {
            "product_id": product_id,
            "warehouse_id": warehouse_id,
            "policy_type": normalized_policy,
            "reorder_point": 0,
            "safety_stock": 0.0,
            "avg_daily_usage": round(avg_daily_usage, 4),
            "lead_time_days": 0,
            "review_cycle_days": review_cycle_days,
            "planning_horizon_days": planning_horizon_days,
            "effective_horizon_days": effective_horizon_days,
            "target_stock_qty": target_stock_qty,
            "inventory_position": inventory_position,
            "on_order_qty": on_order_qty,
            "in_transit_qty": in_transit_qty,
            "reserved_qty": reserved_qty,
            "lead_time_source": lt_source,
            "lead_time_sample_count": lead_time_sample_count,
            "lead_time_confidence": lead_time_confidence,
            "safety_factor": safety_factor,
            "demand_lookback_days": demand_lookback_days,
            "demand_reason": [r.value for r in allowed_reasons],
            "movement_count": movement_count,
            "skipped_reason": "lead_time_unconfigured",
            "quality_note": (
                "No reliable lead time is configured for this stock row. "
                "Add a manual lead time or supplier lead-time data before auto-calculation."
            ),
            "target_stock_level": None,
            "suggested_order_qty": None,
        }

    # Compute ROP
    safety_stock = round(avg_daily_usage * safety_factor * lead_time_days, 2)
    reorder_point = round((lead_time_days * avg_daily_usage) + safety_stock)
    target_stock_level = _compute_target_stock_level(
        normalized_policy,
        target_stock_qty,
        reorder_point,
        avg_daily_usage,
        lead_time_days,
        planning_horizon_days,
        review_cycle_days,
        safety_stock,
    )
    suggested_order_qty = max(0, round(target_stock_level - inventory_position))
    quality_note = _build_quality_note(
        lt_source,
        lead_time_sample_count,
        lead_time_confidence,
        normalized_policy,
        target_stock_qty,
        review_cycle_days,
    )

    return {
        "product_id": product_id,
        "warehouse_id": warehouse_id,
        "policy_type": normalized_policy,
        "reorder_point": reorder_point,
        "safety_stock": safety_stock,
        "avg_daily_usage": round(avg_daily_usage, 4),
        "lead_time_days": lead_time_days,
        "review_cycle_days": review_cycle_days,
        "planning_horizon_days": planning_horizon_days,
        "effective_horizon_days": effective_horizon_days,
        "target_stock_qty": target_stock_qty,
        "inventory_position": inventory_position,
        "on_order_qty": on_order_qty,
        "in_transit_qty": in_transit_qty,
        "reserved_qty": reserved_qty,
        "lead_time_source": lt_source,
        "lead_time_sample_count": lead_time_sample_count,
        "lead_time_confidence": lead_time_confidence,
        "safety_factor": safety_factor,
        "demand_lookback_days": demand_lookback_days,
        "demand_reason": [r.value for r in allowed_reasons],
        "movement_count": movement_count,
        "skipped_reason": None,
        "quality_note": quality_note,
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
            safety_factor=effective_safety_factor,
            policy_type=row.policy_type,
            target_stock_qty=row.target_stock_qty or 0,
            planning_horizon_days=row.planning_horizon_days or 0,
            review_cycle_days=row.review_cycle_days or 0,
            demand_lookback_days=demand_lookback_days,
            lead_time_lookback_days=lead_time_lookback_days,
            lead_time_days_override=(
                row.stored_lead_time_days if row.stored_lead_time_days and row.stored_lead_time_days > 0 else None
            ),
            current_quantity=row.current_quantity,
            on_order_qty=row.on_order_qty or 0,
            in_transit_qty=row.in_transit_qty or 0,
            reserved_qty=row.reserved_qty or 0,
        )
        preview["product_name"] = row.product_name
        preview["category"] = row.category
        preview["current_quantity"] = row.current_quantity
        preview["current_reorder_point"] = row.current_reorder_point
        preview["stock_id"] = row.stock_id
        preview["warehouse_name"] = row.warehouse_name

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
        stock.policy_type = row.get("policy_type") or POLICY_CONTINUOUS
        stock.target_stock_qty = int(row.get("target_stock_qty") or 0)
        stock.on_order_qty = int(row.get("on_order_qty") or 0)
        stock.in_transit_qty = int(row.get("in_transit_qty") or 0)
        stock.reserved_qty = int(row.get("reserved_qty") or 0)
        stock.planning_horizon_days = int(row.get("planning_horizon_days") or 0)
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
