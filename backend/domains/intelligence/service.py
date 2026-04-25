"""Service functions for intelligence domain analytics.

This module maintains backward compatibility as a facade. Feature implementations
are progressively being extracted into backend/domains/intelligence/services/.
The shared pure helpers have been consolidated into the services/shared module.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from sqlalchemy import Float, Numeric, String, and_, case, cast, func, select, true
from sqlalchemy.ext.asyncio import AsyncSession

from common.order_reporting import (
    commercially_committed_order_filter,
    commercially_committed_timestamp_expr,
)
from common.models.order import Order
from common.models.order_line import OrderLine
from common.models.product import Product
from common.tenant import set_tenant
from domains.customers.models import Customer
from domains.product_analytics.service import SalesMonthlyPoint, normalize_month_start, read_sales_monthly_range
from domains.intelligence.schemas import (
    AffinityPair,
    CategoryRevenue,
    CategoryTrend,
    CategoryTrends,
    CustomerBuyingBehavior,
    CustomerBuyingBehaviorCategory,
    CustomerBuyingBehaviorCrossSell,
    CustomerBuyingBehaviorPattern,
    CustomerBuyingBehaviorPeriod,
    CustomerBuyingBehaviorWindow,
    CustomerProductProfile,
    CustomerRiskSignal,
    CustomerRiskSignals,
    MarketOpportunities,
    OpportunitySignal,
    ProductAffinityMap,
    ProductLifecycleStage,
    ProductPerformance,
    ProductPerformanceDataBasis,
    ProductPerformancePeriodMetrics,
    ProductPerformanceRow,
    ProductPerformanceWindow,
    ProductPurchase,
    ProspectFit,
    ProspectGaps,
    ProspectScoreComponents,
    RevenueDiagnosis,
    RevenueDiagnosisComponents,
    RevenueDiagnosisDriver,
    RevenueDiagnosisSummary,
    RevenueDiagnosisWindow,
    TopProductByRevenue,
)

# Import shared constants and helpers from the consolidated support layer
from .services.shared import (
    MONEY_QUANT as _MONEY_QUANT,
    QUANTITY_QUANT as _QUANTITY_QUANT,
    RATIO_QUANT as _RATIO_QUANT,
    PCT_QUANT as _PCT_QUANT,
    ZERO as _ZERO,
    EXCLUDED_CATEGORIES as _EXCLUDED_CATEGORIES,
    RISK_STATUS_PRIORITY as _RISK_STATUS_PRIORITY,
    OPPORTUNITY_SEVERITY_PRIORITY as _OPPORTUNITY_SEVERITY_PRIORITY,
    REVENUE_DIAGNOSIS_PERIOD_MONTHS as _REVENUE_DIAGNOSIS_PERIOD_MONTHS,
    CUSTOMER_BUYING_BEHAVIOR_PERIOD_MONTHS as _CUSTOMER_BUYING_BEHAVIOR_PERIOD_MONTHS,
    subtract_months,
    shift_month_start,
    months_between_inclusive,
    month_start_from_timestamp,
    iter_month_starts,
    period_windows,
    to_decimal,
    safe_average,
    average_count,
    ratio,
    to_ratio,
    percent_change,
    frequency_trend,
    aov_trend,
    bounded_similarity,
    is_excluded_category,
)

# Import extracted feature modules (Story 40.2)
from .services.affinity import get_product_affinity_map as _get_product_affinity_map
from .services.customer_profile import (
    get_customer_product_profile as _get_customer_product_profile,
    build_empty_customer_product_profile as _build_empty_customer_product_profile,
)

# Import extracted feature modules (Story 40.3)
from .services.risk_signals import get_customer_risk_signals as _get_customer_risk_signals
from .services.prospect_gaps import get_prospect_gaps as _get_prospect_gaps
from .services.buying_behavior import get_customer_buying_behavior as _get_customer_buying_behavior

# Import extracted feature modules (Story 40.4)
from .services.category_trends import get_category_trends as _get_category_trends
from .services.market_opportunities import get_market_opportunities as _get_market_opportunities

# Re-export for backward compatibility (facade pattern)
get_product_affinity_map = _get_product_affinity_map
build_empty_customer_product_profile = _build_empty_customer_product_profile
get_customer_product_profile = _get_customer_product_profile
get_customer_risk_signals = _get_customer_risk_signals
get_prospect_gaps = _get_prospect_gaps
get_customer_buying_behavior = _get_customer_buying_behavior
get_category_trends = _get_category_trends
get_market_opportunities = _get_market_opportunities

# Aliases for backward compatibility with internal usage
_subtract_months = subtract_months
_shift_month_start = shift_month_start
_months_between_inclusive = months_between_inclusive
_month_start_from_timestamp = month_start_from_timestamp
_iter_month_starts = iter_month_starts
_period_windows = period_windows
_to_decimal = to_decimal
_safe_average = safe_average
_average_count = average_count
_ratio = ratio
_to_ratio = to_ratio
_percent_change = percent_change
_frequency_trend = frequency_trend
_aov_trend = aov_trend
_bounded_similarity = bounded_similarity
_is_excluded_category = is_excluded_category


@dataclass(slots=True)
class _RevenueDiagnosisWindowMetrics:
    product_id: uuid.UUID
    product_name: str
    product_category_snapshot: str
    quantity: Decimal
    revenue: Decimal
    order_count: int
    latest_month: date


@dataclass(slots=True)
class _ProductPerformanceWindowMetrics:
    product_id: uuid.UUID
    product_name: str
    product_category_snapshot: str
    revenue: Decimal
    quantity: Decimal
    order_count: int
    avg_unit_price: Decimal
    first_sale_month: date
    last_sale_month: date
    latest_month: date
    peak_month_revenue: Decimal


@dataclass(slots=True)
class _ProductPerformanceEvidence:
    first_sale_month: date
    last_sale_month: date
    latest_product_name: str | None = None
    latest_product_category_snapshot: str | None = None


@dataclass(slots=True)
class _CustomerBehaviorLine:
    customer_id: uuid.UUID
    customer_type: str
    order_id: uuid.UUID
    month_start: date
    category: str
    revenue: Decimal


# ============================================================================
# Public Intelligence Functions
# ============================================================================


async def get_category_trends(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    period: Literal["last_30d", "last_90d", "last_12m"] = "last_90d",
) -> CategoryTrends:
    """Compute period-over-period category demand trends from qualifying order lines."""
    current_start, prior_start, end = _period_windows(period)
    current_start_dt = datetime.combine(current_start, time.min, tzinfo=UTC)
    prior_start_dt = datetime.combine(prior_start, time.min, tzinfo=UTC)
    next_day_dt = datetime.combine(end + timedelta(days=1), time.min, tzinfo=UTC)
    generated_at = datetime.now(tz=UTC)
    analytics_timestamp = commercially_committed_timestamp_expr()

    async with session.begin():
        await set_tenant(session, tenant_id)

        current_order_window = and_(analytics_timestamp >= current_start_dt, analytics_timestamp < next_day_dt)
        prior_order_window = and_(analytics_timestamp >= prior_start_dt, analytics_timestamp < current_start_dt)

        category_metric_rows = (
            await session.execute(
                select(
                    Product.category.label("category"),
                    func.coalesce(
                        func.sum(
                            case(
                                (current_order_window, func.coalesce(OrderLine.total_amount, 0)),
                                else_=0,
                            )
                        ),
                        0,
                    ).label("current_revenue"),
                    func.coalesce(
                        func.sum(
                            case(
                                (prior_order_window, func.coalesce(OrderLine.total_amount, 0)),
                                else_=0,
                            )
                        ),
                        0,
                    ).label("prior_revenue"),
                    func.count(
                        func.distinct(case((current_order_window, Order.id), else_=None))
                    ).label("current_orders"),
                    func.count(
                        func.distinct(case((prior_order_window, Order.id), else_=None))
                    ).label("prior_orders"),
                    func.count(
                        func.distinct(case((current_order_window, Order.customer_id), else_=None))
                    ).label("current_customers"),
                    func.count(
                        func.distinct(case((prior_order_window, Order.customer_id), else_=None))
                    ).label("prior_customers"),
                )
                .join(OrderLine, OrderLine.order_id == Order.id)
                .join(Product, Product.id == OrderLine.product_id)
                .where(
                    Order.tenant_id == tenant_id,
                    Product.tenant_id == tenant_id,
                    commercially_committed_order_filter(),
                    Product.category.is_not(None),
                    analytics_timestamp >= prior_start_dt,
                    analytics_timestamp < next_day_dt,
                )
                .group_by(Product.category)
            )
        ).all()

        top_product_rows = (
            await session.execute(
                select(
                    Product.category.label("category"),
                    Product.id.label("product_id"),
                    Product.name.label("product_name"),
                    func.coalesce(func.sum(OrderLine.total_amount), 0).label("revenue"),
                )
                .join(OrderLine, OrderLine.product_id == Product.id)
                .join(Order, OrderLine.order_id == Order.id)
                .where(
                    Order.tenant_id == tenant_id,
                    Product.tenant_id == tenant_id,
                    commercially_committed_order_filter(),
                    Product.category.is_not(None),
                    current_order_window,
                )
                .group_by(Product.category, Product.id, Product.name)
                .order_by(Product.category.asc(), func.sum(OrderLine.total_amount).desc(), Product.name.asc())
            )
        ).all()

        customer_category_presence = (
            select(
                Order.customer_id.label("customer_id"),
                Product.category.label("category"),
                func.max(case((current_order_window, 1), else_=0)).label("in_current"),
                func.max(case((prior_order_window, 1), else_=0)).label("in_prior"),
            )
            .join(OrderLine, OrderLine.order_id == Order.id)
            .join(Product, Product.id == OrderLine.product_id)
            .where(
                Order.tenant_id == tenant_id,
                Product.tenant_id == tenant_id,
                commercially_committed_order_filter(),
                Product.category.is_not(None),
                analytics_timestamp >= prior_start_dt,
                analytics_timestamp < next_day_dt,
            )
            .group_by(Order.customer_id, Product.category)
            .subquery()
        )

        first_purchase_by_category = (
            select(
                Order.customer_id.label("customer_id"),
                Product.category.label("category"),
                func.min(analytics_timestamp).label("first_purchase_at"),
            )
            .join(OrderLine, OrderLine.order_id == Order.id)
            .join(Product, Product.id == OrderLine.product_id)
            .where(
                Order.tenant_id == tenant_id,
                Product.tenant_id == tenant_id,
                commercially_committed_order_filter(),
                Product.category.is_not(None),
            )
            .group_by(Order.customer_id, Product.category)
            .subquery()
        )

        new_customer_rows = (
            await session.execute(
                select(
                    first_purchase_by_category.c.category,
                    func.count().label("new_customer_count"),
                )
                .select_from(first_purchase_by_category)
                .where(
                    first_purchase_by_category.c.first_purchase_at >= current_start_dt,
                    first_purchase_by_category.c.first_purchase_at < next_day_dt,
                )
                .group_by(first_purchase_by_category.c.category)
            )
        ).all()

        churned_customer_rows = (
            await session.execute(
                select(
                    customer_category_presence.c.category,
                    func.count().label("churned_customer_count"),
                )
                .select_from(customer_category_presence)
                .where(
                    customer_category_presence.c.in_prior == 1,
                    customer_category_presence.c.in_current == 0,
                )
                .group_by(customer_category_presence.c.category)
            )
        ).all()

    top_products_by_category: dict[str, list[TopProductByRevenue]] = {}
    for row in top_product_rows:
        if _is_excluded_category(row.category):
            continue
        top_products_by_category.setdefault(row.category, []).append(
            TopProductByRevenue(
                product_id=row.product_id,
                product_name=row.product_name,
                revenue=_to_decimal(row.revenue),
            )
        )

    new_customer_counts = {
        row.category: int(row.new_customer_count or 0)
        for row in new_customer_rows
        if not _is_excluded_category(row.category)
    }
    churned_customer_counts = {
        row.category: int(row.churned_customer_count or 0)
        for row in churned_customer_rows
        if not _is_excluded_category(row.category)
    }

    trends: list[CategoryTrend] = []
    for row in category_metric_rows:
        category = row.category
        if _is_excluded_category(category):
            continue

        current_revenue = _to_decimal(row.current_revenue)
        prior_revenue = _to_decimal(row.prior_revenue)
        current_order_count = int(row.current_orders or 0)
        prior_order_count = int(row.prior_orders or 0)
        current_customer_count = int(row.current_customers or 0)
        prior_customer_count = int(row.prior_customers or 0)

        revenue_delta_pct: float | None
        trend_context: Literal["newly_active", "insufficient_history"] | None = None
        if prior_revenue > 0:
            revenue_delta_pct = _to_ratio(
                ((current_revenue - prior_revenue) / prior_revenue) * Decimal("100"),
                quant=_PCT_QUANT,
            )
        else:
            revenue_delta_pct = None
            if current_revenue > 0:
                trend_context = "newly_active"
            else:
                trend_context = "insufficient_history"

        order_delta_pct: float | None
        if prior_order_count > 0:
            order_delta_pct = _to_ratio(
                (
                    (Decimal(current_order_count) - Decimal(prior_order_count))
                    / Decimal(prior_order_count)
                )
                * Decimal("100"),
                quant=_PCT_QUANT,
            )
        else:
            order_delta_pct = None

        if revenue_delta_pct is not None and revenue_delta_pct > 10:
            trend = "growing"
        elif revenue_delta_pct is not None and revenue_delta_pct < -10:
            trend = "declining"
        else:
            trend = "stable"

        trends.append(
            CategoryTrend(
                category=category,
                current_period_revenue=current_revenue,
                prior_period_revenue=prior_revenue,
                revenue_delta_pct=revenue_delta_pct,
                current_period_orders=current_order_count,
                prior_period_orders=prior_order_count,
                order_delta_pct=order_delta_pct,
                customer_count=current_customer_count,
                prior_customer_count=prior_customer_count,
                new_customer_count=new_customer_counts.get(category, 0),
                churned_customer_count=churned_customer_counts.get(category, 0),
                top_products=top_products_by_category.get(category, [])[:5],
                trend=trend,
                trend_context=trend_context,
                activity_basis="confirmed_or_later_orders",
            )
        )

    trends.sort(
        key=lambda item: (
            item.revenue_delta_pct is None,
            -(item.revenue_delta_pct or 0),
            -item.current_period_revenue,
            -item.customer_count,
            item.category,
        )
    )

    return CategoryTrends(
        period=period,
        trends=trends,
        generated_at=generated_at,
    )




# ============================================================================
# Revenue Diagnosis and Product Performance Helpers
# ============================================================================


def _revenue_diagnosis_windows(
    period: Literal["1m", "3m", "6m", "12m"],
    *,
    anchor_month: date,
) -> tuple[date, date, date, date]:
    """Calculate revenue diagnosis window dates."""
    month_count = _REVENUE_DIAGNOSIS_PERIOD_MONTHS[period]
    current_end = normalize_month_start(anchor_month)
    current_start = _shift_month_start(current_end, -(month_count - 1))
    prior_end = _shift_month_start(current_start, -1)
    prior_start = _shift_month_start(prior_end, -(month_count - 1))
    return current_start, current_end, prior_start, prior_end


def _safe_unit_price(revenue: Decimal, quantity: Decimal) -> Decimal:
    """Calculate safe unit price, avoiding division by zero."""
    if quantity <= 0:
        return _ZERO
    return (revenue / quantity).quantize(_MONEY_QUANT)


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

        existing.quantity = (existing.quantity + point.quantity_sold).quantize(_QUANTITY_QUANT)
        existing.revenue = _to_decimal(existing.revenue + point.revenue)
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
    current_revenue = current_metrics.revenue if current_metrics is not None else _ZERO
    prior_revenue = prior_metrics.revenue if prior_metrics is not None else _ZERO
    current_order_count = current_metrics.order_count if current_metrics is not None else 0
    prior_order_count = prior_metrics.order_count if prior_metrics is not None else 0
    current_avg_unit_price = _safe_unit_price(current_revenue, current_quantity)
    prior_avg_unit_price = _safe_unit_price(prior_revenue, prior_quantity)
    revenue_delta = _to_decimal(current_revenue - prior_revenue)

    if current_quantity > 0 and prior_quantity > 0 and prior_total_quantity > 0:
        price_effect = _to_decimal((current_avg_unit_price - prior_avg_unit_price) * current_quantity)
        volume_effect = _to_decimal(
            (current_total_quantity - prior_total_quantity)
            * (prior_quantity / prior_total_quantity)
            * prior_avg_unit_price
        )
        mix_effect = _to_decimal(revenue_delta - price_effect - volume_effect)
    else:
        price_effect = _ZERO
        volume_effect = _ZERO
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
        revenue_delta_pct=_percent_change(current_revenue, prior_revenue),
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
    """Diagnose revenue changes with volume, price, and mix decomposition."""
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
    ).quantize(_QUANTITY_QUANT)
    prior_total_quantity = sum(
        (metrics.quantity for metrics in prior_metrics.values()),
        Decimal("0.000"),
    ).quantize(_QUANTITY_QUANT)

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

    current_revenue = _to_decimal(
        sum((metrics.revenue for metrics in current_metrics.values()), _ZERO)
    )
    prior_revenue = _to_decimal(
        sum((metrics.revenue for metrics in prior_metrics.values()), _ZERO)
    )
    revenue_delta = _to_decimal(current_revenue - prior_revenue)
    price_effect_total = _to_decimal(sum((driver.price_effect for driver in all_drivers), _ZERO))
    volume_effect_total = _to_decimal(sum((driver.volume_effect for driver in all_drivers), _ZERO))
    mix_effect_total = _to_decimal(revenue_delta - price_effect_total - volume_effect_total)

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
            revenue_delta_pct=_percent_change(current_revenue, prior_revenue),
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


def _product_performance_windows(
    *,
    include_current_month: bool,
    anchor_month: date,
) -> tuple[date, date, date, date]:
    """Calculate product performance window dates."""
    if include_current_month:
        current_end = anchor_month
    else:
        current_end = _shift_month_start(anchor_month, -1)
    current_start = _shift_month_start(current_end, -11)
    prior_end = _shift_month_start(current_start, -1)
    prior_start = _shift_month_start(prior_end, -11)
    return current_start, current_end, prior_start, prior_end


def _aggregate_product_performance_window(
    points: tuple[SalesMonthlyPoint, ...],
    *,
    category: str | None = None,
) -> dict[uuid.UUID, _ProductPerformanceWindowMetrics]:
    """Aggregate product performance metrics for a time window."""
    aggregates: dict[uuid.UUID, dict[str, object]] = {}

    for point in points:
        if category is not None and point.product_category_snapshot != category:
            continue

        aggregate = aggregates.get(point.product_id)
        if aggregate is None:
            aggregates[point.product_id] = {
                "product_id": point.product_id,
                "product_name": point.product_name_snapshot,
                "product_category_snapshot": point.product_category_snapshot,
                "revenue": point.revenue,
                "quantity": point.quantity_sold,
                "order_count": point.order_count,
                "first_sale_month": point.month_start,
                "last_sale_month": point.month_start,
                "latest_month": point.month_start,
                "peak_month_revenue": point.revenue,
            }
            continue

        aggregate["revenue"] = _to_decimal(aggregate["revenue"] + point.revenue)
        aggregate["quantity"] = _to_decimal(
            aggregate["quantity"] + point.quantity_sold,
            quant=_QUANTITY_QUANT,
        )
        aggregate["order_count"] = int(aggregate["order_count"]) + point.order_count
        aggregate["first_sale_month"] = min(aggregate["first_sale_month"], point.month_start)
        aggregate["last_sale_month"] = max(aggregate["last_sale_month"], point.month_start)
        aggregate["peak_month_revenue"] = max(aggregate["peak_month_revenue"], point.revenue)
        if point.month_start >= aggregate["latest_month"]:
            aggregate["latest_month"] = point.month_start
            aggregate["product_name"] = point.product_name_snapshot
            aggregate["product_category_snapshot"] = point.product_category_snapshot

    return {
        product_id: _ProductPerformanceWindowMetrics(
            product_id=product_id,
            product_name=str(values["product_name"]),
            product_category_snapshot=str(values["product_category_snapshot"]),
            revenue=_to_decimal(values["revenue"]),
            quantity=_to_decimal(values["quantity"], quant=_QUANTITY_QUANT),
            order_count=int(values["order_count"]),
            avg_unit_price=(
                (_to_decimal(values["revenue"]) / _to_decimal(values["quantity"], quant=_QUANTITY_QUANT)).quantize(_MONEY_QUANT)
                if _to_decimal(values["quantity"], quant=_QUANTITY_QUANT) > 0
                else _ZERO
            ),
            first_sale_month=values["first_sale_month"],
            last_sale_month=values["last_sale_month"],
            latest_month=values["latest_month"],
            peak_month_revenue=_to_decimal(values["peak_month_revenue"]),
        )
        for product_id, values in aggregates.items()
    }


def _empty_product_performance_period_metrics() -> ProductPerformancePeriodMetrics:
    """Return empty period metrics."""
    return ProductPerformancePeriodMetrics(
        revenue=_ZERO,
        quantity=Decimal("0.000"),
        order_count=0,
        avg_unit_price=_ZERO,
    )


def _build_product_performance_stage(
    *,
    current_revenue: Decimal,
    prior_revenue: Decimal,
    first_sale_month: date,
    last_sale_month: date,
    months_on_sale: int,
    current_window_start: date,
    anchor_month: date,
) -> tuple[ProductLifecycleStage, list[str]]:
    """Determine product lifecycle stage based on revenue patterns."""
    six_complete_month_cutoff = _shift_month_start(anchor_month, -6)
    if current_revenue > _ZERO and prior_revenue == _ZERO and first_sale_month >= current_window_start:
        return "new", ["rule:new", "prior_revenue_zero", "first_sale_in_current_window"]
    if current_revenue == _ZERO and prior_revenue > _ZERO and last_sale_month <= six_complete_month_cutoff:
        return "end_of_life", [
            "rule:end_of_life",
            "current_revenue_zero",
            "last_sale_at_least_6_complete_months_before_anchor",
        ]
    if prior_revenue > _ZERO and (
        current_revenue == _ZERO or current_revenue < (prior_revenue * Decimal("0.80"))
    ):
        return "declining", ["rule:declining", "current_revenue_below_0.80x_prior"]
    if prior_revenue > _ZERO and current_revenue >= (prior_revenue * Decimal("1.20")):
        return "growing", ["rule:growing", "current_revenue_at_least_1.20x_prior"]
    if (
        current_revenue > _ZERO
        and prior_revenue > _ZERO
        and months_on_sale >= 24
        and current_revenue >= (prior_revenue * Decimal("0.80"))
        and current_revenue <= (prior_revenue * Decimal("1.20"))
    ):
        return "mature", ["rule:mature", "months_on_sale_gte_24", "current_revenue_within_0.80x_to_1.20x_prior"]
    return "stable", ["rule:stable", "current_revenue_positive"]


async def _load_product_performance_evidence(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    product_ids: tuple[uuid.UUID, ...],
    current_window_start: date,
    included_window_start: date,
    included_window_end: date,
    category: str | None = None,
) -> dict[uuid.UUID, _ProductPerformanceEvidence]:
    """Load product name/category evidence from order lines."""
    if not product_ids:
        return {}

    analytics_timestamp = commercially_committed_timestamp_expr()
    current_window_start_dt = datetime.combine(current_window_start, time.min, tzinfo=UTC)
    included_window_start_dt = datetime.combine(included_window_start, time.min, tzinfo=UTC)
    included_window_end_dt = datetime.combine(
        _shift_month_start(included_window_end, 1),
        time.min,
        tzinfo=UTC,
    )
    label_window_rank = case((analytics_timestamp >= current_window_start_dt, 1), else_=0)

    evidence_by_product: dict[uuid.UUID, _ProductPerformanceEvidence] = {}

    async with session.begin():
        await set_tenant(session, tenant_id)

        history_rows = (
            await session.execute(
                select(
                    OrderLine.product_id.label("product_id"),
                    func.min(analytics_timestamp).label("first_analytics_at"),
                    func.max(analytics_timestamp).label("last_analytics_at"),
                )
                .select_from(OrderLine)
                .join(Order, Order.id == OrderLine.order_id)
                .where(
                    Order.tenant_id == tenant_id,
                    OrderLine.tenant_id == tenant_id,
                    OrderLine.product_id.in_(product_ids),
                    commercially_committed_order_filter(),
                )
                .group_by(OrderLine.product_id)
            )
        ).mappings().all()

        for row in history_rows:
            first_analytics_at = row["first_analytics_at"]
            last_analytics_at = row["last_analytics_at"]
            if first_analytics_at is None or last_analytics_at is None:
                continue
            evidence_by_product[row["product_id"]] = _ProductPerformanceEvidence(
                first_sale_month=_month_start_from_timestamp(first_analytics_at),
                last_sale_month=_month_start_from_timestamp(last_analytics_at),
            )

        label_filters = [
            Order.tenant_id == tenant_id,
            OrderLine.tenant_id == tenant_id,
            OrderLine.product_id.in_(product_ids),
            commercially_committed_order_filter(),
            analytics_timestamp >= included_window_start_dt,
            analytics_timestamp < included_window_end_dt,
            OrderLine.product_name_snapshot.is_not(None),
            OrderLine.product_category_snapshot.is_not(None),
        ]
        if category is not None:
            label_filters.append(OrderLine.product_category_snapshot == category)

        label_rows = (
            await session.execute(
                select(
                    OrderLine.product_id.label("product_id"),
                    analytics_timestamp.label("analytics_at"),
                    OrderLine.product_name_snapshot.label("product_name_snapshot"),
                    OrderLine.product_category_snapshot.label("product_category_snapshot"),
                    label_window_rank.label("window_rank"),
                    OrderLine.line_number.label("line_number"),
                    OrderLine.id.label("line_id"),
                )
                .select_from(OrderLine)
                .join(Order, Order.id == OrderLine.order_id)
                .where(*label_filters)
                .order_by(
                    OrderLine.product_id.asc(),
                    label_window_rank.desc(),
                    analytics_timestamp.desc(),
                    OrderLine.line_number.desc(),
                    OrderLine.id.desc(),
                )
            )
        ).mappings().all()

    for row in label_rows:
        evidence = evidence_by_product.setdefault(
            row["product_id"],
            _ProductPerformanceEvidence(
                first_sale_month=included_window_start,
                last_sale_month=included_window_end,
            ),
        )
        if evidence.latest_product_name is not None:
            continue
        evidence.latest_product_name = row["product_name_snapshot"]
        evidence.latest_product_category_snapshot = row["product_category_snapshot"]

    return evidence_by_product


async def get_product_performance(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    category: str | None = None,
    lifecycle_stage: ProductLifecycleStage | None = None,
    limit: int = 50,
    include_current_month: bool = False,
) -> ProductPerformance:
    """Analyze product performance with lifecycle staging."""
    anchor_month = normalize_month_start(datetime.now(tz=UTC).date())
    current_start, current_end, prior_start, prior_end = _product_performance_windows(
        include_current_month=include_current_month,
        anchor_month=anchor_month,
    )
    window_is_partial = include_current_month
    data_basis: ProductPerformanceDataBasis = (
        "aggregate_plus_live_current_month" if include_current_month else "aggregate_only"
    )

    current_points = await read_sales_monthly_range(
        session,
        tenant_id,
        start_month=current_start,
        end_month=current_end,
    )
    prior_points = await read_sales_monthly_range(
        session,
        tenant_id,
        start_month=prior_start,
        end_month=prior_end,
    )

    current_metrics = _aggregate_product_performance_window(current_points.items, category=category)
    prior_metrics = _aggregate_product_performance_window(prior_points.items, category=category)
    product_ids = tuple(set(current_metrics) | set(prior_metrics))
    evidence_by_product = await _load_product_performance_evidence(
        session,
        tenant_id,
        product_ids=product_ids,
        current_window_start=current_start,
        included_window_start=prior_start,
        included_window_end=current_end,
        category=category,
    )

    rows: list[ProductPerformanceRow] = []
    for product_id in product_ids:
        current_metric = current_metrics.get(product_id)
        prior_metric = prior_metrics.get(product_id)
        display_metric = current_metric or prior_metric
        if display_metric is None:
            continue

        fallback_first_sale_month = min(
            metric.first_sale_month for metric in (current_metric, prior_metric) if metric is not None
        )
        fallback_last_sale_month = max(
            metric.last_sale_month for metric in (current_metric, prior_metric) if metric is not None
        )
        evidence = evidence_by_product.get(product_id)
        first_sale_month = evidence.first_sale_month if evidence is not None else fallback_first_sale_month
        last_sale_month = evidence.last_sale_month if evidence is not None else fallback_last_sale_month
        months_on_sale = _months_between_inclusive(first_sale_month, last_sale_month)
        current_revenue = current_metric.revenue if current_metric is not None else _ZERO
        prior_revenue = prior_metric.revenue if prior_metric is not None else _ZERO
        stage, stage_reasons = _build_product_performance_stage(
            current_revenue=current_revenue,
            prior_revenue=prior_revenue,
            first_sale_month=first_sale_month,
            last_sale_month=last_sale_month,
            months_on_sale=months_on_sale,
            current_window_start=current_start,
            anchor_month=anchor_month,
        )
        if lifecycle_stage is not None and stage != lifecycle_stage:
            continue

        rows.append(
            ProductPerformanceRow(
                product_id=product_id,
                product_name=(
                    evidence.latest_product_name
                    if evidence is not None and evidence.latest_product_name is not None
                    else display_metric.product_name
                ),
                product_category_snapshot=(
                    evidence.latest_product_category_snapshot
                    if evidence is not None and evidence.latest_product_category_snapshot is not None
                    else display_metric.product_category_snapshot
                ),
                lifecycle_stage=stage,
                stage_reasons=stage_reasons,
                first_sale_month=first_sale_month,
                last_sale_month=last_sale_month,
                months_on_sale=months_on_sale,
                current_period=(
                    ProductPerformancePeriodMetrics(
                        revenue=current_metric.revenue,
                        quantity=current_metric.quantity,
                        order_count=current_metric.order_count,
                        avg_unit_price=current_metric.avg_unit_price,
                    )
                    if current_metric is not None
                    else _empty_product_performance_period_metrics()
                ),
                prior_period=(
                    ProductPerformancePeriodMetrics(
                        revenue=prior_metric.revenue,
                        quantity=prior_metric.quantity,
                        order_count=prior_metric.order_count,
                        avg_unit_price=prior_metric.avg_unit_price,
                    )
                    if prior_metric is not None
                    else _empty_product_performance_period_metrics()
                ),
                peak_month_revenue=max(
                    metric.peak_month_revenue for metric in (current_metric, prior_metric) if metric is not None
                ),
                revenue_delta_pct=_percent_change(current_revenue, prior_revenue),
                data_basis=data_basis,
                window_is_partial=window_is_partial,
            )
        )

    rows.sort(
        key=lambda row: (
            -row.current_period.revenue,
            -(row.revenue_delta_pct if row.revenue_delta_pct is not None else float("-inf")),
            row.product_name,
            str(row.product_id),
        )
    )

    return ProductPerformance(
        current_window=ProductPerformanceWindow(start_month=current_start, end_month=current_end),
        prior_window=ProductPerformanceWindow(start_month=prior_start, end_month=prior_end),
        computed_at=datetime.now(tz=UTC),
        products=rows[:limit],
        total=len(rows),
        data_basis=data_basis,
        window_is_partial=window_is_partial,
    )


async def get_customer_buying_behavior(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    customer_type: str = "dealer",
    period: CustomerBuyingBehaviorPeriod = "12m",
    limit: int = 20,
    include_current_month: bool = False,
) -> CustomerBuyingBehavior:
    """Analyze customer segment buying behavior and cross-sell patterns."""
    normalized_limit = max(1, min(limit, 100))
    anchor_month = datetime.now(tz=UTC).date().replace(day=1)
    months = _CUSTOMER_BUYING_BEHAVIOR_PERIOD_MONTHS[period]
    window_end = anchor_month if include_current_month else _shift_month_start(anchor_month, -1)
    window_start = _shift_month_start(window_end, -(months - 1))
    window_end_exclusive = _shift_month_start(window_end, 1)
    analytics_start = datetime.combine(window_start, time.min, tzinfo=UTC)
    analytics_end = datetime.combine(window_end_exclusive, time.min, tzinfo=UTC)
    analytics_timestamp = commercially_committed_timestamp_expr()
    async with session.begin():
        await set_tenant(session, tenant_id)
        rows = (
            await session.execute(
                select(
                    Customer.id.label("customer_id"),
                    Customer.customer_type.label("customer_type"),
                    Order.id.label("order_id"),
                    analytics_timestamp.label("analytics_at"),
                    OrderLine.product_category_snapshot.label("category"),
                    OrderLine.total_amount.label("line_revenue"),
                )
                .select_from(OrderLine)
                .join(Order, Order.id == OrderLine.order_id)
                .join(Customer, Customer.id == Order.customer_id)
                .where(
                    Customer.tenant_id == tenant_id,
                    Order.tenant_id == tenant_id,
                    OrderLine.tenant_id == tenant_id,
                    commercially_committed_order_filter(),
                    analytics_timestamp >= analytics_start,
                    analytics_timestamp < analytics_end,
                )
            )
        ).all()

    selected_lines: list[_CustomerBehaviorLine] = []
    outside_lines: list[_CustomerBehaviorLine] = []
    total_revenue = Decimal("0.00")
    customer_metrics: dict[uuid.UUID, dict[str, object]] = {}
    category_metrics: dict[str, dict[str, object]] = {}
    pattern_metrics: dict[date, dict[str, object]] = {
        month_start: {"revenue": Decimal("0.00"), "orders": set(), "customers": set()}
        for month_start in _iter_month_starts(window_start, window_end)
    }

    for row in rows:
        category = (row.category or "").strip()
        if not category or _is_excluded_category(category):
            continue
        analytics_at = row.analytics_at
        if analytics_at is None:
            continue

        line = _CustomerBehaviorLine(
            customer_id=row.customer_id,
            customer_type=row.customer_type,
            order_id=row.order_id,
            month_start=normalize_month_start(analytics_at.date()),
            category=category,
            revenue=_to_decimal(row.line_revenue),
        )

        if customer_type == "all" or row.customer_type == customer_type:
            selected_lines.append(line)
            total_revenue += line.revenue

            metrics = customer_metrics.setdefault(
                line.customer_id,
                {"revenue": Decimal("0.00"), "orders": set(), "categories": set()},
            )
            metrics["revenue"] = _to_decimal(metrics["revenue"] + line.revenue)
            metrics["orders"].add(line.order_id)
            metrics["categories"].add(line.category)

            category_entry = category_metrics.setdefault(
                line.category,
                {"revenue": Decimal("0.00"), "orders": set(), "customers": set()},
            )
            category_entry["revenue"] = _to_decimal(category_entry["revenue"] + line.revenue)
            category_entry["orders"].add(line.order_id)
            category_entry["customers"].add(line.customer_id)

            pattern_entry = pattern_metrics[line.month_start]
            pattern_entry["revenue"] = _to_decimal(pattern_entry["revenue"] + line.revenue)
            pattern_entry["orders"].add(line.order_id)
            pattern_entry["customers"].add(line.customer_id)
        elif customer_type != "all":
            outside_lines.append(line)

    customer_count = len(customer_metrics)
    avg_revenue_per_customer = _safe_average(total_revenue, customer_count)
    avg_order_count_per_customer = _average_count(
        sum(len(metrics["orders"]) for metrics in customer_metrics.values()),
        customer_count,
    )
    avg_categories_per_customer = _average_count(
        sum(len(metrics["categories"]) for metrics in customer_metrics.values()),
        customer_count,
    )

    top_categories = [
        CustomerBuyingBehaviorCategory(
            category=category,
            revenue=_to_decimal(metrics["revenue"]),
            order_count=len(metrics["orders"]),
            customer_count=len(metrics["customers"]),
            revenue_share=(
                (metrics["revenue"] / total_revenue).quantize(_RATIO_QUANT)
                if total_revenue > 0
                else Decimal("0.0000")
            ),
        )
        for category, metrics in category_metrics.items()
    ]
    top_categories.sort(key=lambda item: (-item.revenue, -item.customer_count, item.category))

    segment_customer_categories: dict[uuid.UUID, set[str]] = {}
    for line in selected_lines:
        segment_customer_categories.setdefault(line.customer_id, set()).add(line.category)

    outside_customer_categories: dict[uuid.UUID, set[str]] = {}
    for line in outside_lines:
        outside_customer_categories.setdefault(line.customer_id, set()).add(line.category)

    segment_anchor_counts: dict[str, int] = {}
    segment_pair_counts: dict[tuple[str, str], int] = {}
    for categories in segment_customer_categories.values():
        for anchor_category in categories:
            segment_anchor_counts[anchor_category] = segment_anchor_counts.get(anchor_category, 0) + 1
            for recommended_category in categories:
                if recommended_category == anchor_category:
                    continue
                pair_key = (anchor_category, recommended_category)
                segment_pair_counts[pair_key] = segment_pair_counts.get(pair_key, 0) + 1

    outside_anchor_counts: dict[str, int] = {}
    outside_pair_counts: dict[tuple[str, str], int] = {}
    for categories in outside_customer_categories.values():
        for anchor_category in categories:
            outside_anchor_counts[anchor_category] = outside_anchor_counts.get(anchor_category, 0) + 1
            for recommended_category in categories:
                if recommended_category == anchor_category:
                    continue
                pair_key = (anchor_category, recommended_category)
                outside_pair_counts[pair_key] = outside_pair_counts.get(pair_key, 0) + 1

    cross_sell_opportunities: list[CustomerBuyingBehaviorCrossSell] = []
    for (anchor_category, recommended_category), shared_customer_count in segment_pair_counts.items():
        anchor_customer_count = segment_anchor_counts.get(anchor_category, 0)
        if anchor_customer_count < 5 or shared_customer_count < 3:
            continue

        segment_penetration = _ratio(shared_customer_count, anchor_customer_count)
        if customer_type == "all":
            outside_anchor_customer_count = 0
            outside_shared_customer_count = 0
            outside_segment_penetration = Decimal("0.0000")
            lift_score = None
        else:
            outside_anchor_customer_count = outside_anchor_counts.get(anchor_category, 0)
            outside_shared_customer_count = outside_pair_counts.get((anchor_category, recommended_category), 0)
            outside_segment_penetration = _ratio(outside_shared_customer_count, outside_anchor_customer_count)
            lift_score = (
                (segment_penetration / outside_segment_penetration).quantize(_RATIO_QUANT)
                if outside_segment_penetration > 0
                else None
            )

        cross_sell_opportunities.append(
            CustomerBuyingBehaviorCrossSell(
                anchor_category=anchor_category,
                recommended_category=recommended_category,
                anchor_customer_count=anchor_customer_count,
                shared_customer_count=shared_customer_count,
                outside_segment_anchor_customer_count=outside_anchor_customer_count,
                outside_segment_shared_customer_count=outside_shared_customer_count,
                segment_penetration=segment_penetration,
                outside_segment_penetration=outside_segment_penetration,
                lift_score=lift_score,
            )
        )

    cross_sell_opportunities.sort(
        key=lambda item: (
            1 if item.lift_score is None else 0,
            -(item.lift_score or Decimal("0.0000")),
            -item.shared_customer_count,
            item.anchor_category,
            item.recommended_category,
        )
    )

    buying_patterns = [
        CustomerBuyingBehaviorPattern(
            month_start=month_start,
            revenue=_to_decimal(metrics["revenue"]),
            order_count=len(metrics["orders"]),
            customer_count=len(metrics["customers"]),
        )
        for month_start, metrics in sorted(pattern_metrics.items())
    ]

    return CustomerBuyingBehavior(
        customer_type=customer_type,  # type: ignore[arg-type]
        period=period,
        window=CustomerBuyingBehaviorWindow(start_month=window_start, end_month=window_end),
        computed_at=datetime.now(tz=UTC),
        customer_count=customer_count,
        avg_revenue_per_customer=avg_revenue_per_customer,
        avg_order_count_per_customer=avg_order_count_per_customer,
        avg_categories_per_customer=avg_categories_per_customer,
        top_categories=top_categories[:normalized_limit],
        cross_sell_opportunities=cross_sell_opportunities[:normalized_limit],
        buying_patterns=buying_patterns,
        data_basis="transactional_fallback",
        window_is_partial=include_current_month,
    )
