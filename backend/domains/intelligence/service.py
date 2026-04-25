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

# Re-export for backward compatibility (facade pattern)
get_product_affinity_map = _get_product_affinity_map
build_empty_customer_product_profile = _build_empty_customer_product_profile
get_customer_product_profile = _get_customer_product_profile

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
# Risk and Prospect Helpers
# ============================================================================


def _confidence(order_count_12m: int) -> Literal["high", "medium", "low"]:
    """Determine confidence level based on order count."""
    if order_count_12m >= 6:
        return "high"
    if order_count_12m >= 2:
        return "medium"
    return "low"


def _classify_risk_status(
    *,
    first_order_date: date | None,
    last_order_date: date | None,
    revenue_current: Decimal,
    revenue_prior: Decimal,
    today: date,
) -> Literal["growing", "at_risk", "dormant", "new", "stable"]:
    """Classify customer risk status based on order history and revenue trends."""
    if last_order_date is None:
        return "dormant"
    if last_order_date is not None and (today - last_order_date).days > 60:
        return "dormant"
    if first_order_date is not None and (today - first_order_date).days <= 90:
        return "new"
    if revenue_prior > 0:
        ratio_val = revenue_current / revenue_prior
        if ratio_val >= Decimal("1.20"):
            return "growing"
        if ratio_val <= Decimal("0.80"):
            return "at_risk"
    return "stable"


def _build_risk_signal_strings(
    *,
    revenue_delta_pct: float | None,
    days_since_last_order: int | None,
    avg_order_value_current: Decimal,
    avg_order_value_prior: Decimal,
    first_order_date: date | None,
    today: date,
    products_expanded_into: list[str],
    products_contracted_from: list[str],
) -> list[str]:
    """Build human-readable risk signal strings."""
    signals: list[str] = []
    if revenue_delta_pct is not None:
        direction = "up" if revenue_delta_pct > 0 else "down"
        if revenue_delta_pct != 0:
            signals.append(f"revenue {direction} {abs(revenue_delta_pct):.0f}%")
    if days_since_last_order is not None and days_since_last_order >= 30:
        signals.append(f"no orders in {days_since_last_order} days")
    if avg_order_value_prior > 0 and avg_order_value_current > 0:
        aov_delta = ((avg_order_value_current - avg_order_value_prior) / avg_order_value_prior) * Decimal("100")
        if aov_delta >= Decimal("10"):
            signals.append(
                f"AOV increased from NT${avg_order_value_prior:,.0f} to NT${avg_order_value_current:,.0f}"
            )
        elif aov_delta <= Decimal("-10"):
            signals.append(
                f"AOV decreased from NT${avg_order_value_prior:,.0f} to NT${avg_order_value_current:,.0f}"
            )
    if first_order_date is not None and (today - first_order_date).days <= 90:
        signals.append(f"first order {(today - first_order_date).days} days ago — new account")
    if products_expanded_into:
        signals.append(f"expanded into {len(products_expanded_into)} new categories")
    if products_contracted_from:
        signals.append(f"reduced purchases in {len(products_contracted_from)} categories")
    return signals


def _prospect_confidence(order_count_recent: int, category_count_recent: int, recency_factor: float) -> Literal["high", "medium", "low"]:
    """Determine prospect confidence level."""
    if order_count_recent >= 4 and category_count_recent >= 2 and recency_factor >= 0.6:
        return "high"
    if order_count_recent >= 2 and recency_factor >= 0.3:
        return "medium"
    return "low"


def _prospect_reason(company_name: str, category_count: int, adjacent_support: float, recency_factor: float) -> str:
    """Generate prospect reason string."""
    parts = [f"{company_name} is a fit candidate"]
    if adjacent_support > 0:
        parts.append(f"buys {category_count} adjacent categories")
    if recency_factor >= 0.6:
        parts.append("has strong recent activity")
    return " and ".join(parts) + "."


# ============================================================================
# Public Intelligence Functions
# ============================================================================


async def get_market_opportunities(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    period: Literal["last_30d", "last_90d", "last_12m"] = "last_90d",
) -> MarketOpportunities:
    """Aggregate stabilized v1 market opportunity signals."""
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

        customer_revenue_rows = (
            await session.execute(
                select(
                    Order.customer_id.label("customer_id"),
                    Customer.company_name.label("company_name"),
                    func.count(
                        func.distinct(case((current_order_window, Order.id), else_=None))
                    ).label("current_order_count"),
                    func.count(
                        func.distinct(case((prior_order_window, Order.id), else_=None))
                    ).label("prior_order_count"),
                    func.coalesce(
                        func.sum(
                            case(
                                (current_order_window, func.coalesce(Order.total_amount, 0)),
                                else_=0,
                            )
                        ),
                        0,
                    ).label("current_revenue"),
                    func.coalesce(
                        func.sum(
                            case(
                                (prior_order_window, func.coalesce(Order.total_amount, 0)),
                                else_=0,
                            )
                        ),
                        0,
                    ).label("prior_revenue"),
                )
                .join(Customer, Customer.id == Order.customer_id)
                .where(
                    Order.tenant_id == tenant_id,
                    commercially_committed_order_filter(),
                    analytics_timestamp >= prior_start_dt,
                    analytics_timestamp < next_day_dt,
                )
                .group_by(Order.customer_id, Customer.company_name)
            )
        ).all()

    current_revenue_total = _ZERO
    prior_revenue_total = _ZERO
    current_customer_revenue: dict[uuid.UUID, tuple[str, Decimal]] = {}
    prior_customer_revenue: dict[uuid.UUID, Decimal] = {}
    current_customers_considered = 0
    prior_customers_considered = 0

    for row in customer_revenue_rows:
        current_order_count = int(row.current_order_count or 0)
        prior_order_count = int(row.prior_order_count or 0)
        current_revenue = _to_decimal(row.current_revenue)
        prior_revenue = _to_decimal(row.prior_revenue)
        current_revenue_total += current_revenue
        prior_revenue_total += prior_revenue
        if current_order_count > 0:
            current_customers_considered += 1
        if prior_order_count > 0:
            prior_customers_considered += 1
        if current_revenue > 0:
            current_customer_revenue[row.customer_id] = (row.company_name, current_revenue)
        if prior_revenue > 0:
            prior_customer_revenue[row.customer_id] = prior_revenue

    signals: list[OpportunitySignal] = []
    if current_revenue_total > 0:
        for customer_id, (company_name, revenue) in current_customer_revenue.items():
            share = (revenue / current_revenue_total) if current_revenue_total > 0 else Decimal("0")
            if share <= Decimal("0.30"):
                continue
            prior_share = (
                (prior_customer_revenue.get(customer_id, _ZERO) / prior_revenue_total) if prior_revenue_total > 0 else None
            )
            prior_share_text = (
                f" Prior period share was {(prior_share * Decimal('100')).quantize(_PCT_QUANT)}%."
                if prior_share is not None
                else ""
            )
            signals.append(
                OpportunitySignal(
                    signal_type="concentration_risk",
                    severity="alert",
                    headline=f"{company_name} represents {(share * Decimal('100')).quantize(_PCT_QUANT)}% of total revenue — concentration risk",
                    detail=(
                        f"{company_name} contributed NT$ {revenue:,.2f} of NT$ {current_revenue_total:,.2f} total period revenue."
                        f"{prior_share_text}"
                    ),
                    affected_customer_count=1,
                    revenue_impact=revenue,
                    recommended_action="Diversify revenue concentration and review expansion or mitigation actions.",
                    support_counts={
                        "customers_considered": current_customers_considered,
                        "prior_customers_considered": prior_customers_considered,
                    },
                    source_period=period,
                )
            )

    category_trends = await get_category_trends(session, tenant_id, period=period)
    growth_trends = [
        trend
        for trend in category_trends.trends
        if trend.revenue_delta_pct is not None
        and trend.revenue_delta_pct > 0
        and trend.trend == "growing"
        and trend.customer_count >= 2
        and trend.current_period_orders >= 2
    ]
    for trend in growth_trends[:3]:
        delta_absolute = trend.current_period_revenue - trend.prior_period_revenue
        severity: Literal["info", "warning"] = "warning" if trend.revenue_delta_pct >= 30 else "info"
        signals.append(
            OpportunitySignal(
                signal_type="category_growth",
                severity=severity,
                headline=f"{trend.category} revenue up {trend.revenue_delta_pct:.2f}% vs prior period",
                detail=(
                    f"{trend.category} changed by NT$ {delta_absolute:,.2f} with {trend.customer_count} active buyers in the current period."
                ),
                affected_customer_count=trend.customer_count,
                revenue_impact=delta_absolute,
                recommended_action=f"Review supply, pricing, and sales focus for {trend.category}.",
                support_counts={
                    "current_period_orders": trend.current_period_orders,
                    "prior_period_orders": trend.prior_period_orders,
                    "current_customer_count": trend.customer_count,
                    "prior_customer_count": trend.prior_customer_count,
                },
                source_period=period,
            )
        )

    signals.sort(
        key=lambda signal: (
            _OPPORTUNITY_SEVERITY_PRIORITY[signal.severity],
            -signal.revenue_impact,
            signal.headline,
        )
    )

    return MarketOpportunities(
        period=period,
        generated_at=generated_at,
        signals=signals,
        deferred_signal_types=["new_product_adoption", "churn_risk"],
    )


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


async def get_customer_risk_signals(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    status_filter: Literal["all", "growing", "at_risk", "dormant", "new", "stable"] = "all",
    limit: int = 50,
) -> CustomerRiskSignals:
    """Rank customer accounts by deterministic risk and growth signals."""
    now = datetime.now(tz=UTC)
    today = now.date()
    window_current_start = _subtract_months(now, 12)
    window_prior_start = _subtract_months(now, 24)
    normalized_limit = max(1, limit)
    analytics_timestamp = commercially_committed_timestamp_expr()

    async with session.begin():
        await set_tenant(session, tenant_id)

        customers = (
            await session.execute(
                select(Customer.id, Customer.company_name)
                .where(Customer.tenant_id == tenant_id)
                .order_by(Customer.company_name)
            )
        ).all()

        current_order_window = analytics_timestamp >= window_current_start
        prior_order_window = and_(
            analytics_timestamp >= window_prior_start,
            analytics_timestamp < window_current_start,
        )

        order_metrics_rows = (
            await session.execute(
                select(
                    Order.customer_id.label("customer_id"),
                    func.coalesce(
                        func.sum(
                            case(
                                (current_order_window, func.coalesce(Order.total_amount, 0)),
                                else_=0,
                            )
                        ),
                        0,
                    ).label("revenue_current"),
                    func.coalesce(
                        func.sum(
                            case(
                                (prior_order_window, func.coalesce(Order.total_amount, 0)),
                                else_=0,
                            )
                        ),
                        0,
                    ).label("revenue_prior"),
                    func.count(
                        func.distinct(case((current_order_window, Order.id), else_=None))
                    ).label("order_count_current"),
                    func.count(
                        func.distinct(case((prior_order_window, Order.id), else_=None))
                    ).label("order_count_prior"),
                    func.min(analytics_timestamp).label("first_order_at"),
                    func.max(analytics_timestamp).label("last_order_at"),
                )
                .where(
                    Order.tenant_id == tenant_id,
                    commercially_committed_order_filter(),
                )
                .group_by(Order.customer_id)
            )
        ).all()

        category_presence_rows = (
            await session.execute(
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
                    analytics_timestamp >= window_prior_start,
                )
                .group_by(Order.customer_id, Product.category)
            )
        ).all()

    customer_metrics: dict[uuid.UUID, dict[str, object]] = {
        row.id: {
            "company_name": row.company_name,
            "revenue_current": _ZERO,
            "revenue_prior": _ZERO,
            "order_count_current": 0,
            "order_count_prior": 0,
            "first_order_date": None,
            "last_order_date": None,
            "categories_current": set(),
            "categories_prior": set(),
        }
        for row in customers
    }

    for row in order_metrics_rows:
        metrics = customer_metrics.get(row.customer_id)
        if metrics is None:
            continue

        metrics["revenue_current"] = _to_decimal(row.revenue_current)
        metrics["revenue_prior"] = _to_decimal(row.revenue_prior)
        metrics["order_count_current"] = int(row.order_count_current or 0)
        metrics["order_count_prior"] = int(row.order_count_prior or 0)
        metrics["first_order_date"] = (
            row.first_order_at.date() if row.first_order_at is not None else None
        )
        metrics["last_order_date"] = (
            row.last_order_at.date() if row.last_order_at is not None else None
        )

    for row in category_presence_rows:
        metrics = customer_metrics.get(row.customer_id)
        if metrics is None or _is_excluded_category(row.category):
            continue

        if bool(row.in_current):
            metrics["categories_current"].add(row.category)
        if bool(row.in_prior):
            metrics["categories_prior"].add(row.category)

    customers_out: list[CustomerRiskSignal] = []
    for customer_id, metrics in customer_metrics.items():
        revenue_current = metrics["revenue_current"]
        revenue_prior = metrics["revenue_prior"]
        order_count_current = metrics["order_count_current"]
        order_count_prior = metrics["order_count_prior"]
        first_order_date = metrics["first_order_date"]
        last_order_date = metrics["last_order_date"]
        categories_current = metrics["categories_current"]
        categories_prior = metrics["categories_prior"]

        avg_order_value_current = _safe_average(revenue_current, order_count_current)
        avg_order_value_prior = _safe_average(revenue_prior, order_count_prior)
        revenue_delta_pct = (
            _to_ratio(((revenue_current - revenue_prior) / revenue_prior) * Decimal("100"), quant=Decimal("0.1"))
            if revenue_prior > 0
            else None
        )
        days_since_last_order = (today - last_order_date).days if last_order_date else None
        if order_count_prior > 0:
            products_expanded_into = sorted(categories_current - categories_prior)
            products_contracted_from = sorted(categories_prior - categories_current)
        else:
            products_expanded_into = []
            products_contracted_from = []
        status = _classify_risk_status(
            first_order_date=first_order_date,
            last_order_date=last_order_date,
            revenue_current=revenue_current,
            revenue_prior=revenue_prior,
            today=today,
        )

        reason_codes: list[str] = []
        if status == "dormant":
            reason_codes.append("dormant_60d")
        elif status == "new":
            reason_codes.append("new_account_90d")
        elif status == "growing":
            reason_codes.append("revenue_growth_20pct")
        elif status == "at_risk":
            reason_codes.append("revenue_decline_20pct")
        else:
            reason_codes.append("stable_demand")
        if revenue_prior <= 0:
            reason_codes.append("sparse_prior_history")
        if products_expanded_into:
            reason_codes.append("category_expansion")
        if products_contracted_from:
            reason_codes.append("category_contraction")

        signal = CustomerRiskSignal(
            customer_id=customer_id,
            company_name=metrics["company_name"],
            status=status,
            revenue_current=revenue_current,
            revenue_prior=revenue_prior,
            revenue_delta_pct=revenue_delta_pct,
            order_count_current=order_count_current,
            order_count_prior=order_count_prior,
            avg_order_value_current=avg_order_value_current,
            avg_order_value_prior=avg_order_value_prior,
            days_since_last_order=days_since_last_order,
            reason_codes=reason_codes,
            confidence=_confidence(order_count_current + order_count_prior),
            signals=_build_risk_signal_strings(
                revenue_delta_pct=revenue_delta_pct,
                days_since_last_order=days_since_last_order,
                avg_order_value_current=avg_order_value_current,
                avg_order_value_prior=avg_order_value_prior,
                first_order_date=first_order_date,
                today=today,
                products_expanded_into=products_expanded_into,
                products_contracted_from=products_contracted_from,
            ),
            products_expanded_into=products_expanded_into,
            products_contracted_from=products_contracted_from,
            last_order_date=last_order_date,
            first_order_date=first_order_date,
        )
        customers_out.append(signal)

    if status_filter != "all":
        customers_out = [customer for customer in customers_out if customer.status == status_filter]

    customers_out.sort(
        key=lambda customer: (
            _RISK_STATUS_PRIORITY[customer.status],
            -(customer.days_since_last_order or 0),
            customer.company_name,
        )
    )

    return CustomerRiskSignals(
        customers=customers_out[:normalized_limit],
        total=len(customers_out),
        status_filter=status_filter,
        limit=normalized_limit,
        generated_at=now,
    )


async def get_prospect_gaps(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    category: str,
    customer_type: str = "dealer",
    limit: int = 20,
) -> ProspectGaps:
    """Return active non-buyers ranked as whitespace prospects for a target category."""
    target_category = category.strip()
    normalized_limit = max(1, min(limit, 100))
    now = datetime.now(tz=UTC)
    recent_window_start = _subtract_months(now, 12)
    customer_type_filter = true() if customer_type == "all" else Customer.customer_type == customer_type
    analytics_timestamp = commercially_committed_timestamp_expr()

    async with session.begin():
        await set_tenant(session, tenant_id)

        customer_summary_rows = (
            await session.execute(
                select(Customer.id, Customer.company_name)
                .add_columns(
                    func.count(func.distinct(Order.id)).label("order_count_total"),
                    func.count(
                        func.distinct(case((analytics_timestamp >= recent_window_start, Order.id), else_=None))
                    ).label("order_count_recent"),
                    func.coalesce(func.sum(func.coalesce(Order.total_amount, 0)), 0).label("total_revenue"),
                    func.min(analytics_timestamp).label("first_order_at"),
                    func.max(analytics_timestamp).label("last_order_at"),
                )
                .join(Order, Order.customer_id == Customer.id)
                .where(
                    Customer.tenant_id == tenant_id,
                    customer_type_filter,
                    Order.tenant_id == tenant_id,
                    commercially_committed_order_filter(),
                )
                .group_by(Customer.id, Customer.company_name)
                .order_by(Customer.company_name)
            )
        ).all()

        category_presence_rows = (
            await session.execute(
                select(
                    Order.customer_id.label("customer_id"),
                    Product.category.label("category"),
                    func.max(case((analytics_timestamp >= recent_window_start, 1), else_=0)).label("in_recent"),
                )
                .join(Customer, Customer.id == Order.customer_id)
                .join(OrderLine, OrderLine.order_id == Order.id)
                .join(Product, Product.id == OrderLine.product_id)
                .where(
                    Customer.tenant_id == tenant_id,
                    customer_type_filter,
                    Order.tenant_id == tenant_id,
                    Product.tenant_id == tenant_id,
                    commercially_committed_order_filter(),
                    Product.category.is_not(None),
                )
                .group_by(Order.customer_id, Product.category)
            )
        ).all()

        target_category_summary = (
            await session.execute(
                select(
                    func.coalesce(func.sum(OrderLine.total_amount), 0).label("target_category_revenue"),
                    func.count(func.distinct(Order.customer_id)).label("existing_buyers_count"),
                )
                .select_from(Order)
                .join(Customer, Customer.id == Order.customer_id)
                .join(OrderLine, OrderLine.order_id == Order.id)
                .join(Product, Product.id == OrderLine.product_id)
                .where(
                    Customer.tenant_id == tenant_id,
                    customer_type_filter,
                    Order.tenant_id == tenant_id,
                    Product.tenant_id == tenant_id,
                    commercially_committed_order_filter(),
                    Product.category == target_category,
                )
            )
        ).one()

        order_categories = (
            select(
                Order.id.label("order_id"),
                Product.category.label("category"),
            )
            .join(Customer, Customer.id == Order.customer_id)
            .join(OrderLine, OrderLine.order_id == Order.id)
            .join(Product, Product.id == OrderLine.product_id)
            .where(
                Customer.tenant_id == tenant_id,
                customer_type_filter,
                Order.tenant_id == tenant_id,
                Product.tenant_id == tenant_id,
                commercially_committed_order_filter(),
                Product.category.is_not(None),
            )
            .distinct()
            .subquery()
        )
        target_order_categories = order_categories.alias("target_order_categories")
        adjacent_order_categories = order_categories.alias("adjacent_order_categories")
        adjacent_category_rows = (
            await session.execute(
                select(
                    adjacent_order_categories.c.category.label("category"),
                    func.count().label("pair_count"),
                )
                .select_from(
                    target_order_categories.join(
                        adjacent_order_categories,
                        and_(
                            target_order_categories.c.order_id == adjacent_order_categories.c.order_id,
                            target_order_categories.c.category != adjacent_order_categories.c.category,
                        ),
                    )
                )
                .where(target_order_categories.c.category == target_category)
                .group_by(adjacent_order_categories.c.category)
            )
        ).all()

    available_categories = sorted(
        {
            row.category
            for row in category_presence_rows
            if not _is_excluded_category(row.category)
        }
    )
    if not target_category:
        return ProspectGaps(
            target_category="",
            target_category_revenue=_ZERO,
            existing_buyers_count=0,
            prospects_count=0,
            prospects=[],
            available_categories=available_categories,
            generated_at=now,
        )

    customer_metrics: dict[uuid.UUID, dict[str, object]] = {
        row.id: {
            "company_name": row.company_name,
            "order_count_total": int(row.order_count_total or 0),
            "order_count_recent": int(row.order_count_recent or 0),
            "total_revenue": _to_decimal(row.total_revenue),
            "first_order_date": row.first_order_at.date() if row.first_order_at is not None else None,
            "last_order_date": row.last_order_at.date() if row.last_order_at is not None else None,
            "categories": set(),
            "categories_recent": set(),
        }
        for row in customer_summary_rows
    }

    existing_buyers: set[uuid.UUID] = set()
    target_category_revenue = _to_decimal(target_category_summary.target_category_revenue)

    for row in category_presence_rows:
        if _is_excluded_category(row.category):
            continue
        metrics = customer_metrics.get(row.customer_id)
        if metrics is None:
            continue
        metrics["categories"].add(row.category)
        if bool(row.in_recent):
            metrics["categories_recent"].add(row.category)
        if row.category == target_category:
            existing_buyers.add(row.customer_id)

    if target_category not in available_categories:
        return ProspectGaps(
            target_category=target_category,
            target_category_revenue=_ZERO,
            existing_buyers_count=0,
            prospects_count=0,
            prospects=[],
            available_categories=available_categories,
            generated_at=now,
        )

    adjacent_categories = {
        row.category
        for row in adjacent_category_rows
        if not _is_excluded_category(row.category)
    }

    buyer_frequency_values: list[float] = []
    buyer_breadth_values: list[float] = []
    for customer_id in existing_buyers:
        metrics = customer_metrics.get(customer_id)
        if metrics is None:
            continue
        buyer_frequency_values.append(float(metrics["order_count_recent"]))
        buyer_breadth_values.append(float(len(metrics["categories_recent"])))
    buyer_frequency_baseline = sum(buyer_frequency_values) / len(buyer_frequency_values) if buyer_frequency_values else 0.0
    buyer_breadth_baseline = sum(buyer_breadth_values) / len(buyer_breadth_values) if buyer_breadth_values else 0.0

    total_revenues = sorted(
        (metrics["total_revenue"] for metrics in customer_metrics.values()),
        reverse=True,
    )
    high_value_index = max(0, int(len(total_revenues) * 0.2) - 1)
    high_value_threshold = total_revenues[high_value_index] if total_revenues else _ZERO

    prospects: list[ProspectFit] = []
    for customer_id, metrics in customer_metrics.items():
        if customer_id in existing_buyers:
            continue

        order_count_total = int(metrics["order_count_total"])
        if order_count_total == 0:
            continue
        if len(metrics["categories"]) == 0:
            continue

        order_count_recent = int(metrics["order_count_recent"])
        category_count_recent = len(metrics["categories_recent"])
        total_revenue = metrics["total_revenue"]
        avg_order_value = _safe_average(total_revenue, order_count_total)
        last_order_date = metrics["last_order_date"]
        first_order_date = metrics["first_order_date"]
        days_since_last_order = (now.date() - last_order_date).days if last_order_date else None
        recency_factor = 0.0 if days_since_last_order is None else max(0.0, 1.0 - min(days_since_last_order / 180, 1.0))
        frequency_similarity = _bounded_similarity(float(order_count_recent), buyer_frequency_baseline)
        breadth_similarity = _bounded_similarity(float(category_count_recent), buyer_breadth_baseline)
        adjacent_overlap = metrics["categories"].intersection(adjacent_categories)
        adjacent_category_support = (
            min(len(adjacent_overlap) / max(len(adjacent_categories), 1), 1.0)
            if adjacent_categories
            else 0.0
        )
        affinity_score = round(
            (0.35 * frequency_similarity)
            + (0.35 * breadth_similarity)
            + (0.20 * adjacent_category_support)
            + (0.10 * recency_factor),
            4,
        )

        reason_codes: list[str] = []
        if frequency_similarity >= 0.7:
            reason_codes.append("frequency_match")
        if breadth_similarity >= 0.7:
            reason_codes.append("breadth_match")
        if adjacent_category_support > 0:
            reason_codes.append("adjacent_category_support")
        if recency_factor >= 0.5:
            reason_codes.append("recent_activity")

        tags: list[str] = []
        if days_since_last_order is not None and days_since_last_order > 90:
            tags.append("dormant")
        if total_revenue >= high_value_threshold and high_value_threshold > 0:
            tags.append("high_value")
        if adjacent_category_support > 0:
            tags.append("adjacent_category")
        if first_order_date is not None and (now.date() - first_order_date).days <= 90:
            tags.append("new_customer")

        prospect = ProspectFit(
            customer_id=customer_id,
            company_name=metrics["company_name"],
            total_revenue=total_revenue,
            category_count=len(metrics["categories"]),
            avg_order_value=avg_order_value,
            last_order_date=last_order_date,
            affinity_score=affinity_score,
            score_components=ProspectScoreComponents(
                frequency_similarity=round(frequency_similarity, 4),
                breadth_similarity=round(breadth_similarity, 4),
                adjacent_category_support=round(adjacent_category_support, 4),
                recency_factor=round(recency_factor, 4),
            ),
            reason_codes=reason_codes,
            confidence=_prospect_confidence(order_count_recent, category_count_recent, recency_factor),
            reason=_prospect_reason(
                metrics["company_name"],
                len(metrics["categories"]),
                adjacent_category_support,
                recency_factor,
            ),
            tags=tags,
        )
        prospects.append(prospect)

    prospects.sort(
        key=lambda prospect: (
            -prospect.affinity_score,
            -prospect.total_revenue,
            prospect.company_name,
        )
    )

    return ProspectGaps(
        target_category=target_category,
        target_category_revenue=target_category_revenue,
        existing_buyers_count=len(existing_buyers),
        prospects_count=len(prospects),
        prospects=prospects[:normalized_limit],
        available_categories=available_categories,
        generated_at=now,
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
