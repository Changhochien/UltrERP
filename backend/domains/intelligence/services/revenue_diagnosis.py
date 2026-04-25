"""Revenue diagnosis service.

Decomposes revenue changes into price, volume, and mix effects using
aggregate monthly data from the sales history.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Literal

from sqlalchemy import and_, case, func
from sqlalchemy.ext.asyncio import AsyncSession

from domains.product_analytics.service import SalesMonthlyPoint, read_sales_monthly_range

from domains.intelligence.schemas import (
    RevenueDiagnosis,
    RevenueDiagnosisComponents,
    RevenueDiagnosisDriver,
    RevenueDiagnosisSummary,
    RevenueDiagnosisWindow,
)

from .shared import (
    MONEY_QUANT,
    QUANTITY_QUANT,
    RATIO_QUANT,
    ZERO,
    REVENUE_DIAGNOSIS_PERIOD_MONTHS,
    months_between_inclusive,
    normalize_month_start,
    percent_change,
    shift_month_start,
    to_decimal,
)


@dataclass(slots=True)
class _RevenueDiagnosisWindowMetrics:
    product_id: uuid.UUID
    product_name: str
    product_category_snapshot: str
    quantity: Decimal
    revenue: Decimal
    order_count: int
    latest_month: date


def _revenue_diagnosis_windows(
    period: Literal["1m", "3m", "6m", "12m"],
    *,
    anchor_month: date,
) -> tuple[date, date, date, date]:
    """Calculate revenue diagnosis window dates."""
    month_count = REVENUE_DIAGNOSIS_PERIOD_MONTHS[period]
    current_end = normalize_month_start(anchor_month)
    current_start = shift_month_start(current_end, -(month_count - 1))
    prior_end = shift_month_start(current_start, -1)
    prior_start = shift_month_start(prior_end, -(month_count - 1))
    return current_start, current_end, prior_start, prior_end


def _safe_unit_price(revenue: Decimal, quantity: Decimal) -> Decimal:
    """Calculate safe unit price, avoiding division by zero."""
    if quantity <= 0:
        return ZERO
    return (revenue / quantity).quantize(MONEY_QUANT)


def _aggregate_revenue_window(
    points: tuple[SalesMonthlyPoint, ...],
    *,
    category: str | None,
) -> dict[uuid.UUID, _RevenueDiagnosisWindowMetrics]:
    """Aggregate revenue metrics by product for a time window."""
    category_filter = category.strip() if category else None
    metrics: dict[uuid.UUID, _RevenueDiagnosisWindowMetrics] = {}

    for point in points:
        if category_filter and point.product_category_snapshot != category_filter:
            continue

        existing = metrics.get(point.product_id)
        if existing is None:
            metrics[point.product_id] = _RevenueDiagnosisWindowMetrics(
                product_id=point.product_id,
                product_name=point.product_name_snapshot,
                product_category_snapshot=point.product_category_snapshot,
                quantity=point.quantity_sold,
                revenue=point.revenue,
                order_count=point.order_count,
                latest_month=point.month_start,
            )
            continue

        existing.quantity = (existing.quantity + point.quantity_sold).quantize(QUANTITY_QUANT)
        existing.revenue = to_decimal(existing.revenue + point.revenue)
        existing.order_count += point.order_count
        if point.month_start >= existing.latest_month:
            existing.latest_month = point.month_start
            existing.product_name = point.product_name_snapshot
            existing.product_category_snapshot = point.product_category_snapshot

    return metrics


def _build_revenue_diagnosis_driver(
    *,
    product_id: uuid.UUID,
    current_metrics: _RevenueDiagnosisWindowMetrics | None,
    prior_metrics: _RevenueDiagnosisWindowMetrics | None,
    current_total_quantity: Decimal,
    prior_total_quantity: Decimal,
    data_basis: Literal["aggregate_only", "aggregate_plus_live_current_month"],
    window_is_partial: bool,
) -> RevenueDiagnosisDriver:
    """Build a revenue diagnosis driver with volume/price/mix decomposition."""
    product_name = (
        current_metrics.product_name
        if current_metrics is not None
        else prior_metrics.product_name  # type: ignore[union-attr]
    )
    product_category_snapshot = (
        current_metrics.product_category_snapshot
        if current_metrics is not None
        else prior_metrics.product_category_snapshot  # type: ignore[union-attr]
    )
    current_quantity = current_metrics.quantity if current_metrics is not None else Decimal("0.000")
    prior_quantity = prior_metrics.quantity if prior_metrics is not None else Decimal("0.000")
    current_revenue = current_metrics.revenue if current_metrics is not None else ZERO
    prior_revenue = prior_metrics.revenue if prior_metrics is not None else ZERO
    current_order_count = current_metrics.order_count if current_metrics is not None else 0
    prior_order_count = prior_metrics.order_count if prior_metrics is not None else 0
    current_avg_unit_price = _safe_unit_price(current_revenue, current_quantity)
    prior_avg_unit_price = _safe_unit_price(prior_revenue, prior_quantity)
    revenue_delta = to_decimal(current_revenue - prior_revenue)

    if current_quantity > 0 and prior_quantity > 0 and prior_total_quantity > 0:
        price_effect = to_decimal((current_avg_unit_price - prior_avg_unit_price) * current_quantity)
        volume_effect = to_decimal(
            (current_total_quantity - prior_total_quantity)
            * (prior_quantity / prior_total_quantity)
            * prior_avg_unit_price
        )
        mix_effect = to_decimal(revenue_delta - price_effect - volume_effect)
    else:
        price_effect = ZERO
        volume_effect = ZERO
        mix_effect = revenue_delta

    return RevenueDiagnosisDriver(
        product_id=product_id,
        product_name=product_name,
        product_category_snapshot=product_category_snapshot,
        current_quantity=current_quantity,
        prior_quantity=prior_quantity,
        current_revenue=current_revenue,
        prior_revenue=prior_revenue,
        current_order_count=current_order_count,
        prior_order_count=prior_order_count,
        current_avg_unit_price=current_avg_unit_price,
        prior_avg_unit_price=prior_avg_unit_price,
        price_effect=price_effect,
        volume_effect=volume_effect,
        mix_effect=mix_effect,
        revenue_delta=revenue_delta,
        revenue_delta_pct=percent_change(current_revenue, prior_revenue),
        data_basis=data_basis,
        window_is_partial=window_is_partial,
    )


async def get_revenue_diagnosis(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    period: Literal["1m", "3m", "6m", "12m"] = "1m",
    anchor_month: date | None = None,
    category: str | None = None,
    limit: int = 20,
) -> RevenueDiagnosis:
    """Diagnose revenue changes with volume, price, and mix decomposition.

    Computes revenue delta and decomposes into:
    - Price effect: change due to unit price changes
    - Volume effect: change due to quantity changes
    - Mix effect: change due to product/category mix shifts
    """
    normalized_anchor_month = normalize_month_start(anchor_month or datetime.now(tz=UTC).date())
    current_month_start = normalize_month_start(datetime.now(tz=UTC).date())
    if normalized_anchor_month > current_month_start:
        raise ValueError("anchor_month cannot be in the future")

    current_start, current_end, prior_start, prior_end = _revenue_diagnosis_windows(
        period,
        anchor_month=normalized_anchor_month,
    )
    window_is_partial = current_start <= current_month_start <= current_end
    data_basis: Literal["aggregate_only", "aggregate_plus_live_current_month"] = (
        "aggregate_plus_live_current_month" if window_is_partial else "aggregate_only"
    )

    current_window_points = await read_sales_monthly_range(
        session,
        tenant_id,
        start_month=current_start,
        end_month=current_end,
    )
    prior_window_points = await read_sales_monthly_range(
        session,
        tenant_id,
        start_month=prior_start,
        end_month=prior_end,
    )

    current_metrics = _aggregate_revenue_window(current_window_points.items, category=category)
    prior_metrics = _aggregate_revenue_window(prior_window_points.items, category=category)
    current_total_quantity = sum(
        (metrics.quantity for metrics in current_metrics.values()),
        Decimal("0.000"),
    ).quantize(QUANTITY_QUANT)
    prior_total_quantity = sum(
        (metrics.quantity for metrics in prior_metrics.values()),
        Decimal("0.000"),
    ).quantize(QUANTITY_QUANT)

    all_product_ids = set(current_metrics) | set(prior_metrics)
    all_drivers = [
        _build_revenue_diagnosis_driver(
            product_id=product_id,
            current_metrics=current_metrics.get(product_id),
            prior_metrics=prior_metrics.get(product_id),
            current_total_quantity=current_total_quantity,
            prior_total_quantity=prior_total_quantity,
            data_basis=data_basis,
            window_is_partial=window_is_partial,
        )
        for product_id in all_product_ids
    ]
    all_drivers.sort(
        key=lambda driver: (
            -abs(driver.revenue_delta),
            -abs(driver.mix_effect),
            driver.product_name,
            str(driver.product_id),
        )
    )

    current_revenue = to_decimal(
        sum((metrics.revenue for metrics in current_metrics.values()), ZERO)
    )
    prior_revenue = to_decimal(
        sum((metrics.revenue for metrics in prior_metrics.values()), ZERO)
    )
    revenue_delta = to_decimal(current_revenue - prior_revenue)
    price_effect_total = to_decimal(sum((driver.price_effect for driver in all_drivers), ZERO))
    volume_effect_total = to_decimal(sum((driver.volume_effect for driver in all_drivers), ZERO))
    mix_effect_total = to_decimal(revenue_delta - price_effect_total - volume_effect_total)

    return RevenueDiagnosis(
        period=period,
        anchor_month=normalized_anchor_month,
        current_window=RevenueDiagnosisWindow(start_month=current_start, end_month=current_end),
        prior_window=RevenueDiagnosisWindow(start_month=prior_start, end_month=prior_end),
        computed_at=datetime.now(tz=UTC),
        summary=RevenueDiagnosisSummary(
            current_revenue=current_revenue,
            prior_revenue=prior_revenue,
            revenue_delta=revenue_delta,
            revenue_delta_pct=percent_change(current_revenue, prior_revenue),
        ),
        components=RevenueDiagnosisComponents(
            price_effect_total=price_effect_total,
            volume_effect_total=volume_effect_total,
            mix_effect_total=mix_effect_total,
        ),
        drivers=all_drivers[:limit],
        data_basis=data_basis,
        window_is_partial=window_is_partial,
    )
