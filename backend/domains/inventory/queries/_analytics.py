"""Analytics queries — read operations for planning and reporting."""

from __future__ import annotations

from collections.abc import Callable
import uuid
from datetime import date as date_type, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import TYPE_CHECKING, Any

from sqlalchemy import and_, func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.models.inventory_stock import InventoryStock
from common.models.product import Product
from common.models.stock_adjustment import ReasonCode, StockAdjustment
from common.time import utc_now

if TYPE_CHECKING:
    pass

_ZERO_QUANTITY = Decimal("0.000")


def _quantize_quantity(value: Any) -> Decimal:
    """Quantize a quantity to integer representation."""
    return Decimal(str(value or "0")).quantize(_ZERO_QUANTITY, rounding=ROUND_HALF_UP)


def _format_month(d: date_type) -> str:
    return d.strftime("%Y-%m")


def _shift_months(d: date_type, months: int) -> date_type:
    """Shift a date by a number of months."""
    month = d.month - 1 + months
    year = d.year + month // 12
    month = month % 12 + 1
    day = min(d.day, [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
    return date_type(year, month, day)


def _iter_month_starts(start: date_type, end: date_type):
    current = start
    while current <= end:
        yield current
        current = _shift_months(current, 1)


def _quantize_index(value: Decimal | float) -> Decimal:
    """Quantize an index value to 3 decimal places."""
    return Decimal(str(value)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)


async def get_stock_history(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    *,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    granularity: str = "event",
    _max_range_days: int = 730,
) -> dict:
    """Return stock history for a product+warehouse.

    - ``granularity='event'``: one row per adjustment event
    - ``granularity='daily'``: one row per day, aggregated

    ``running_stock`` at each point is computed by back-calculating the
    initial stock from the current quantity and applying adjustments forward.
    """
    from collections import Counter

    def is_reconciliation_apply_adjustment(adjustment: StockAdjustment) -> bool:
        return adjustment.actor_id == "reconciliation-apply"

    # Cap start_date to at most _max_range_days ago to avoid loading huge histories
    effective_start = start_date
    if effective_start is None:
        effective_start = utc_now() - timedelta(days=_max_range_days)

    # 1. Get current stock quantity and reorder point
    stock_stmt = select(InventoryStock).where(
        InventoryStock.tenant_id == tenant_id,
        InventoryStock.product_id == product_id,
        InventoryStock.warehouse_id == warehouse_id,
    )
    stock_result = await session.execute(stock_stmt)
    stock = stock_result.scalar_one_or_none()

    current_stock = stock.quantity if stock else 0
    reorder_point = stock.reorder_point if stock else 0
    configured_safety_factor = stock.safety_factor if stock and stock.safety_factor > 0 else 0.5
    configured_lead_time_days = stock.lead_time_days if stock and stock.lead_time_days > 0 else None

    # 2. Fetch adjustments ordered ASC
    adj_where = [
        StockAdjustment.tenant_id == tenant_id,
        StockAdjustment.product_id == product_id,
        StockAdjustment.warehouse_id == warehouse_id,
    ]
    if effective_start:
        adj_where.append(StockAdjustment.created_at >= effective_start)
    if end_date:
        adj_where.append(StockAdjustment.created_at <= end_date)

    adj_stmt = (
        select(StockAdjustment)
        .where(*adj_where)
        .order_by(StockAdjustment.created_at.asc())
    )

    adj_result = await session.execute(adj_stmt)
    adjustments = list(adj_result.scalars().all())

    visible_adjustments = [
        adjustment
        for adjustment in adjustments
        if not is_reconciliation_apply_adjustment(adjustment)
    ]

    total_adjustment = sum(adj.quantity_change for adj in visible_adjustments)
    initial_stock = current_stock - total_adjustment

    # 3. Build running stock
    running = initial_stock
    points: list[dict] = []

    if granularity == "daily":
        # Group by date, sum quantity_change, pick dominant reason_code
        by_date: dict[str, dict] = {}
        for adj in visible_adjustments:
            day_key = adj.created_at.date().isoformat()
            if day_key not in by_date:
                by_date[day_key] = {"quantity_change": 0, "reason_codes": Counter(), "notes": None}
            by_date[day_key]["quantity_change"] += adj.quantity_change
            by_date[day_key]["reason_codes"][adj.reason_code.value] += 1
            if by_date[day_key]["notes"] is None and adj.notes:
                by_date[day_key]["notes"] = adj.notes

        for day_key, info in sorted(by_date.items()):
            running += info["quantity_change"]
            dominant_rc = (
                info["reason_codes"].most_common(1)[0][0]
                if info["reason_codes"]
                else "unknown"
            )
            points.append({
                "date": datetime.fromisoformat(day_key),
                "quantity_change": info["quantity_change"],
                "reason_code": dominant_rc,
                "running_stock": running,
                "notes": info["notes"],
            })
    else:
        # event-level granularity
        for adj in visible_adjustments:
            running += adj.quantity_change
            points.append({
                "date": adj.created_at,
                "quantity_change": adj.quantity_change,
                "reason_code": adj.reason_code.value,
                "running_stock": running,
                "notes": adj.notes,
            })

    # 4. Fetch metadata from reorder point helpers (avg_daily_usage, lead_time, safety_stock)
    try:
        from domains.inventory.reorder_point import (
            get_average_daily_usage,
            get_lead_time_days,
        )

        avg_daily, _mov_count = await get_average_daily_usage(
            session, tenant_id, product_id, warehouse_id, lookback_days=90,
        )
        if configured_lead_time_days is not None:
            lead_time_days = configured_lead_time_days
        else:
            lead_time_days, _lt_source = await get_lead_time_days(
                session, tenant_id, product_id, warehouse_id, lookback_days=180,
            )
        safety_stock = (
            round(avg_daily * configured_safety_factor * lead_time_days, 2)
            if avg_daily and lead_time_days
            else None
        )
    except Exception:
        avg_daily = None
        lead_time_days = None
        safety_stock = None

    return {
        "points": points,
        "current_stock": current_stock,
        "reorder_point": reorder_point,
        "avg_daily_usage": round(avg_daily, 4) if avg_daily else None,
        "lead_time_days": lead_time_days,
        "safety_stock": safety_stock,
    }


async def get_stock_history_series(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    stock_id: uuid.UUID,
    *,
    start_date: str,  # YYYY-MM-DD
    end_date: str,    # YYYY-MM-DD
) -> dict:
    """Dense stock history series with zero-filling and range metadata.

    Returns dense daily time-series data suitable for explorer charts.
    Zero-fills any days without stock movements.
    """
    from common.time_series import densify_daily_series, check_range_limits

    # Parse dates
    start = date_type.fromisoformat(start_date)
    end = date_type.fromisoformat(end_date)

    # Check v1 limits
    within_limits, error_msg = check_range_limits(start, end, "day")
    if not within_limits:
        raise ValueError(error_msg)

    # Get stock record for warehouse_id
    stock_stmt = select(InventoryStock).where(
        InventoryStock.id == stock_id,
        InventoryStock.tenant_id == tenant_id,
    )
    stock_result = await session.execute(stock_stmt)
    stock = stock_result.scalar_one_or_none()
    if not stock:
        return {"points": [], "range": {
            "requested_start": start_date,
            "requested_end": end_date,
            "available_start": None,
            "available_end": None,
            "default_visible_start": start_date,
            "default_visible_end": end_date,
            "bucket": "day",
            "timezone": "Asia/Taipei",
        }}

    # Get daily aggregated adjustments. Current stock includes every visible
    # adjustment after the requested start, so back-calculate the starting
    # baseline before building end-of-day running values inside the window.
    start_dt = datetime(start.year, start.month, start.day, tzinfo=timezone.utc)
    end_dt = datetime(end.year, end.month, end.day, 23, 59, 59, tzinfo=timezone.utc)

    daily_expr = func.date_trunc(
        "day",
        func.timezone("Asia/Taipei", StockAdjustment.created_at),
    ).label("day")

    stmt = (
        select(
            daily_expr,
            func.sum(StockAdjustment.quantity_change).label("total_change"),
        )
        .where(
            StockAdjustment.tenant_id == tenant_id,
            StockAdjustment.product_id == stock.product_id,
            StockAdjustment.warehouse_id == stock.warehouse_id,
            StockAdjustment.created_at >= start_dt,
            StockAdjustment.created_at <= end_dt,
        )
        .group_by(daily_expr)
        .order_by(daily_expr)
    )
    result = await session.execute(stmt)
    rows = result.all()

    # Build sparse source data dict (running stock at end of days that changed).
    # Missing days are carried forward by densify_daily_series and still marked
    # as zero-filled in the response metadata.
    source_data: dict[str, float] = {}
    total_adjustments_since_start = sum(float(row.total_change or 0) for row in rows)
    running_stock = float(stock.quantity) - total_adjustments_since_start

    for row in rows:
        day_date = row.day.date() if hasattr(row.day, "date") else row.day
        if isinstance(day_date, datetime):
            day_date = day_date.date()
        key = day_date.strftime("%Y-%m-%d")
        running_stock += float(row.total_change or 0)
        source_data[key] = running_stock

    points, range_meta = densify_daily_series(
        source_data=source_data,
        requested_start=start,
        requested_end=end,
        carry_forward=True,
        initial_value=float(stock.quantity) - total_adjustments_since_start,
    )

    return {"points": points, "range": range_meta}


async def _get_monthly_demand_with_now_provider(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    *,
    months: int = 12,
    include_current_month: bool = True,
    now_provider: Callable[[], datetime],
) -> dict:
    """Return rolling monthly demand totals for SALES_RESERVATION.

    Uses Asia/Taipei timezone for date truncation to match the business timezone.
    """
    current_month_start = now_provider().date().replace(day=1)
    end_month = (
        current_month_start
        if include_current_month
        else _shift_months(current_month_start, -1)
    )
    requested_months = _iter_month_starts(_shift_months(end_month, -(months - 1)), end_month)
    requested_month_set = set(requested_months)

    # Convert to Taiwan timezone before truncating month
    taiwan_month_expr = func.date_trunc(
        "month",
        func.timezone("Asia/Taipei", StockAdjustment.created_at),
    ).label("month")

    stmt = (
        select(
            taiwan_month_expr,
            func.sum(StockAdjustment.quantity_change).label("total_qty"),
        )
        .where(
            StockAdjustment.tenant_id == tenant_id,
            StockAdjustment.product_id == product_id,
            StockAdjustment.reason_code == ReasonCode.SALES_RESERVATION,
        )
        .group_by(taiwan_month_expr)
        .order_by(taiwan_month_expr)
    )
    result = await session.execute(stmt)
    rows = result.all()

    items = [
        {
            "month": row.month.strftime("%Y-%m"),
            "total_qty": int(abs(_quantize_quantity(row.total_qty or 0))),
        }
        for row in rows
        if (row.month.date() if hasattr(row.month, "date") else row.month) in requested_month_set
    ]
    total = sum(item["total_qty"] for item in items)
    return {"items": items, "total": total}


async def get_monthly_demand(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    *,
    months: int = 12,
    include_current_month: bool = True,
) -> dict:
    return await _get_monthly_demand_with_now_provider(
        session,
        tenant_id,
        product_id,
        months=months,
        include_current_month=include_current_month,
        now_provider=utc_now,
    )


async def get_monthly_demand_series(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    *,
    start_month: str,  # YYYY-MM
    end_month: str,    # YYYY-MM
) -> dict:
    """Dense monthly demand series with zero-filling and range metadata.

    Returns dense monthly time-series data suitable for explorer charts.
    Zero-fills any gaps in the requested range.
    """
    from common.time_series import densify_monthly_series, check_range_limits

    # Parse dates
    start = date_type(int(start_month[:4]), int(start_month[5:7]), 1)
    end = date_type(int(end_month[:4]), int(end_month[5:7]), 1)

    # Check v1 limits
    within_limits, error_msg = check_range_limits(start, end, "month")
    if not within_limits:
        raise ValueError(error_msg)

    # Get monthly data from source
    taiwan_month_expr = func.date_trunc(
        "month",
        func.timezone("Asia/Taipei", StockAdjustment.created_at),
    ).label("month")

    stmt = (
        select(
            taiwan_month_expr,
            func.sum(StockAdjustment.quantity_change).label("total_qty"),
        )
        .where(
            StockAdjustment.tenant_id == tenant_id,
            StockAdjustment.product_id == product_id,
            StockAdjustment.reason_code == ReasonCode.SALES_RESERVATION,
        )
        .group_by(taiwan_month_expr)
        .order_by(taiwan_month_expr)
    )
    result = await session.execute(stmt)
    rows = result.all()

    # Build source data dict
    source_data: dict[str, float] = {}
    for row in rows:
        month_date = row.month.date() if hasattr(row.month, "date") else row.month
        if isinstance(month_date, datetime):
            month_date = month_date.date()
        key = month_date.strftime("%Y-%m")
        source_data[key] = float(abs(int(_quantize_quantity(row.total_qty or 0))))

    # Densify with zero-filling
    points, range_meta = densify_monthly_series(
        source_data=source_data,
        requested_start=start,
        requested_end=end,
    )

    return {"points": points, "range": range_meta}


async def get_planning_support(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    *,
    months: int = 12,
    include_current_month: bool = True,
) -> dict | None:
    """Return planning support metrics for a product.

    Blends closed-month sales snapshots with current-month live data from the
    shared product analytics read path, then derives advisory planning metrics.
    """
    from domains.product_analytics.service import read_sales_monthly_range

    current_month_start = utc_now().date().replace(day=1)
    end_month = (
        current_month_start
        if include_current_month
        else _shift_months(current_month_start, -1)
    )
    start_month = _shift_months(end_month, -(months - 1))
    requested_months = list(_iter_month_starts(start_month, end_month))
    includes_current_month = include_current_month and current_month_start in requested_months

    product_exists = await session.scalar(
        select(Product.id).where(
            Product.id == product_id,
            Product.tenant_id == tenant_id,
        )
    )
    if product_exists is None:
        return None

    monthly_points = await read_sales_monthly_range(
        session,
        tenant_id,
        start_month=start_month,
        end_month=end_month,
    )

    monthly_quantities: dict[date_type, Decimal] = {}
    for point in monthly_points.items:
        if point.product_id != product_id:
            continue
        if point.month_start < start_month or point.month_start > end_month:
            continue
        monthly_quantities[point.month_start] = monthly_quantities.get(
            point.month_start,
            _ZERO_QUANTITY,
        ) + _quantize_quantity(point.quantity_sold)

    stock_context_row = (
        await session.execute(
            select(
                func.coalesce(func.sum(InventoryStock.reorder_point), 0).label("reorder_point"),
                func.coalesce(func.sum(InventoryStock.on_order_qty), 0).label("on_order_qty"),
                func.coalesce(func.sum(InventoryStock.in_transit_qty), 0).label("in_transit_qty"),
                func.coalesce(func.sum(InventoryStock.reserved_qty), 0).label("reserved_qty"),
            ).where(
                InventoryStock.tenant_id == tenant_id,
                InventoryStock.product_id == product_id,
            )
        )
    ).one()

    current_month_live_quantity = None
    if includes_current_month:
        current_month_live_quantity = _quantize_quantity(
            monthly_quantities.get(current_month_start, _ZERO_QUANTITY),
        )

    if not monthly_quantities:
        return {
            "product_id": product_id,
            "items": [],
            "avg_monthly_quantity": None,
            "peak_monthly_quantity": None,
            "low_monthly_quantity": None,
            "seasonality_index": None,
            "above_average_months": [],
            "history_months_used": 0,
            "current_month_live_quantity": current_month_live_quantity,
            "reorder_point": int(stock_context_row.reorder_point or 0),
            "on_order_qty": int(stock_context_row.on_order_qty or 0),
            "in_transit_qty": int(stock_context_row.in_transit_qty or 0),
            "reserved_qty": int(stock_context_row.reserved_qty or 0),
            "data_basis": "no_history",
            "advisory_only": True,
            "data_gap": True,
            "window": {
                "start_month": _format_month(start_month),
                "end_month": _format_month(end_month),
                "includes_current_month": includes_current_month,
                "is_partial": includes_current_month,
            },
        }

    items: list[dict[str, object]] = []
    for month_start in requested_months:
        items.append(
            {
                "month": _format_month(month_start),
                "quantity": _quantize_quantity(
                    monthly_quantities.get(month_start, _ZERO_QUANTITY)
                ),
                "source": (
                    "live"
                    if month_start == current_month_start and includes_current_month
                    else "aggregated"
                ),
            }
        )

    quantities = [item["quantity"] for item in items]
    total_quantity = sum(quantities, start=_ZERO_QUANTITY)
    avg_monthly_quantity = _quantize_quantity(total_quantity / Decimal(len(items)))
    peak_monthly_quantity = max(quantities)
    low_monthly_quantity = min(quantities)
    seasonality_index = (
        _quantize_index(peak_monthly_quantity / avg_monthly_quantity)
        if avg_monthly_quantity > 0
        else Decimal("0.000")
    )
    above_average_months = [
        str(item["month"])
        for item in items
        if item["quantity"] > avg_monthly_quantity
    ]

    if includes_current_month and start_month == current_month_start:
        data_basis = "live_current_month_only"
    elif includes_current_month:
        data_basis = "aggregated_plus_live_current_month"
    else:
        data_basis = "aggregated_only"

    return {
        "product_id": product_id,
        "items": items,
        "avg_monthly_quantity": avg_monthly_quantity,
        "peak_monthly_quantity": peak_monthly_quantity,
        "low_monthly_quantity": low_monthly_quantity,
        "seasonality_index": seasonality_index,
        "above_average_months": above_average_months,
        "history_months_used": len(items),
        "current_month_live_quantity": current_month_live_quantity,
        "reorder_point": int(stock_context_row.reorder_point or 0),
        "on_order_qty": int(stock_context_row.on_order_qty or 0),
        "in_transit_qty": int(stock_context_row.in_transit_qty or 0),
        "reserved_qty": int(stock_context_row.reserved_qty or 0),
        "data_basis": data_basis,
        "advisory_only": True,
        "data_gap": False,
        "window": {
            "start_month": _format_month(start_month),
            "end_month": _format_month(end_month),
            "includes_current_month": includes_current_month,
            "is_partial": includes_current_month,
        },
    }


async def get_sales_history(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    *,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """Return paginated sales history (all reason codes) for a product."""
    count_stmt = select(func.count(StockAdjustment.id)).where(
        StockAdjustment.tenant_id == tenant_id,
        StockAdjustment.product_id == product_id,
    )
    count_result = await session.execute(count_stmt)
    total = count_result.scalar() or 0

    stmt = (
        select(StockAdjustment)
        .where(
            StockAdjustment.tenant_id == tenant_id,
            StockAdjustment.product_id == product_id,
        )
        .order_by(StockAdjustment.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await session.execute(stmt)
    adjustments = result.scalars().all()

    items = [
        {
            "date": adj.created_at,
            "quantity_change": adj.quantity_change,
            "reason_code": adj.reason_code.value,
            "actor_id": adj.actor_id,
        }
        for adj in adjustments
    ]
    return {"items": items, "total": total}
