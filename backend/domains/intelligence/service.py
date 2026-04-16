"""Service functions for intelligence domain analytics."""

from __future__ import annotations

import calendar
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from sqlalchemy import Float, Numeric, String, and_, case, cast, func, select, true
from sqlalchemy.ext.asyncio import AsyncSession

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
    CustomerProductProfile,
    CustomerRiskSignal,
    CustomerRiskSignals,
    MarketOpportunities,
    OpportunitySignal,
    ProductAffinityMap,
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

_COUNTABLE_STATUSES = ("confirmed", "shipped", "fulfilled")
_MONEY_QUANT = Decimal("0.01")
_QUANTITY_QUANT = Decimal("0.001")
_RATIO_QUANT = Decimal("0.0001")
_PCT_QUANT = Decimal("0.01")
_ZERO = Decimal("0.00")
_EXCLUDED_CATEGORIES = {
    "discount",
    "discounts",
    "freight",
    "misc",
    "miscellaneous",
    "non-merchandise",
    "service",
    "services",
    "shipping",
}
_RISK_STATUS_PRIORITY = {"dormant": 0, "at_risk": 1, "growing": 2, "stable": 3, "new": 4}
_OPPORTUNITY_SEVERITY_PRIORITY = {"alert": 0, "warning": 1, "info": 2}
_REVENUE_DIAGNOSIS_PERIOD_MONTHS = {"1m": 1, "3m": 3, "6m": 6, "12m": 12}


@dataclass(slots=True)
class _RevenueDiagnosisWindowMetrics:
    product_id: uuid.UUID
    product_name: str
    product_category_snapshot: str
    quantity: Decimal
    revenue: Decimal
    order_count: int
    latest_month: date


def _subtract_months(anchor: datetime, months: int) -> datetime:
    year = anchor.year
    month = anchor.month - months
    while month <= 0:
        year -= 1
        month += 12
    day = min(anchor.day, calendar.monthrange(year, month)[1])
    return anchor.replace(year=year, month=month, day=day)


def _to_decimal(value: object | None, *, quant: Decimal = _MONEY_QUANT) -> Decimal:
    return Decimal(str(value or "0")).quantize(quant)


def _safe_average(total: Decimal, count: int) -> Decimal:
    if count <= 0:
        return _ZERO
    return (total / Decimal(count)).quantize(_MONEY_QUANT)


def _frequency_trend(current_count: int, prior_count: int) -> Literal["increasing", "declining", "stable"]:
    if prior_count <= 0:
        return "increasing" if current_count > 0 else "stable"
    if current_count > prior_count * 1.20:
        return "increasing"
    if current_count < prior_count * 0.80:
        return "declining"
    return "stable"


def _aov_trend(current_value: Decimal, prior_value: Decimal) -> Literal["increasing", "declining", "stable"]:
    if prior_value <= 0:
        return "increasing" if current_value > 0 else "stable"
    if current_value > prior_value * Decimal("1.10"):
        return "increasing"
    if current_value < prior_value * Decimal("0.90"):
        return "declining"
    return "stable"


def _confidence(order_count_12m: int) -> Literal["high", "medium", "low"]:
    if order_count_12m >= 6:
        return "high"
    if order_count_12m >= 2:
        return "medium"
    return "low"


def _pair_key(product_a_id: uuid.UUID, product_b_id: uuid.UUID) -> tuple[uuid.UUID, uuid.UUID]:
    return (product_a_id, product_b_id) if str(product_a_id) < str(product_b_id) else (product_b_id, product_a_id)


def _to_ratio(value: Decimal, *, quant: Decimal = _RATIO_QUANT) -> float:
    return float(value.quantize(quant))


def _make_pitch_hint(product_a_name: str, product_b_name: str, score: Decimal) -> str:
    if score >= Decimal("0.5000"):
        return (
            f"Strong affinity — '{product_a_name}' and '{product_b_name}' are frequently bought together. "
            "Bundle pitch recommended."
        )
    if score >= Decimal("0.2000"):
        return f"Consider pitching '{product_b_name}' when customer buys '{product_a_name}'."
    return f"'{product_a_name}' customers occasionally also buy '{product_b_name}'."


def _classify_risk_status(
    *,
    first_order_date: date | None,
    last_order_date: date | None,
    revenue_current: Decimal,
    revenue_prior: Decimal,
    today: date,
) -> Literal["growing", "at_risk", "dormant", "new", "stable"]:
    if last_order_date is None:
        return "dormant"
    if last_order_date is not None and (today - last_order_date).days > 60:
        return "dormant"
    if first_order_date is not None and (today - first_order_date).days <= 90:
        return "new"
    if revenue_prior > 0:
        ratio = revenue_current / revenue_prior
        if ratio >= Decimal("1.20"):
            return "growing"
        if ratio <= Decimal("0.80"):
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


def _bounded_similarity(value: float, baseline: float) -> float:
    if baseline <= 0:
        return 0.0
    return max(0.0, 1.0 - min(abs(value - baseline) / baseline, 1.0))


def _prospect_confidence(order_count_recent: int, category_count_recent: int, recency_factor: float) -> Literal["high", "medium", "low"]:
    if order_count_recent >= 4 and category_count_recent >= 2 and recency_factor >= 0.6:
        return "high"
    if order_count_recent >= 2 and recency_factor >= 0.3:
        return "medium"
    return "low"


def _prospect_reason(company_name: str, category_count: int, adjacent_support: float, recency_factor: float) -> str:
    parts = [f"{company_name} is a fit candidate"]
    if adjacent_support > 0:
        parts.append(f"buys {category_count} adjacent categories")
    if recency_factor >= 0.6:
        parts.append("has strong recent activity")
    return " and ".join(parts) + "."


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

    async with session.begin():
        await set_tenant(session, tenant_id)

        current_order_window = and_(Order.created_at >= current_start_dt, Order.created_at < next_day_dt)
        prior_order_window = and_(Order.created_at >= prior_start_dt, Order.created_at < current_start_dt)

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
                    Order.status.in_(_COUNTABLE_STATUSES),
                    Order.created_at >= prior_start_dt,
                    Order.created_at < next_day_dt,
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


def _is_excluded_category(category: str | None) -> bool:
    if category is None:
        return True
    return category.strip().casefold() in _EXCLUDED_CATEGORIES


def _period_windows(
    period: Literal["last_30d", "last_90d", "last_12m"],
    *,
    anchor: datetime | None = None,
) -> tuple[date, date, date]:
    end = (anchor or datetime.now(tz=UTC)).date()
    days = 90
    if period == "last_30d":
        days = 30
    elif period == "last_12m":
        days = 365

    current_start = end - timedelta(days=days)
    prior_start = current_start - timedelta(days=days)
    return current_start, prior_start, end


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

    async with session.begin():
        await set_tenant(session, tenant_id)

        current_order_window = and_(Order.created_at >= current_start_dt, Order.created_at < next_day_dt)
        prior_order_window = and_(Order.created_at >= prior_start_dt, Order.created_at < current_start_dt)

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
                    Order.status.in_(_COUNTABLE_STATUSES),
                    Product.category.is_not(None),
                    Order.created_at >= prior_start_dt,
                    Order.created_at < next_day_dt,
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
                    Order.status.in_(_COUNTABLE_STATUSES),
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
                Order.status.in_(_COUNTABLE_STATUSES),
                Product.category.is_not(None),
                Order.created_at >= prior_start_dt,
                Order.created_at < next_day_dt,
            )
            .group_by(Order.customer_id, Product.category)
            .subquery()
        )

        first_purchase_by_category = (
            select(
                Order.customer_id.label("customer_id"),
                Product.category.label("category"),
                func.min(Order.created_at).label("first_purchase_at"),
            )
            .join(OrderLine, OrderLine.order_id == Order.id)
            .join(Product, Product.id == OrderLine.product_id)
            .where(
                Order.tenant_id == tenant_id,
                Product.tenant_id == tenant_id,
                Order.status.in_(_COUNTABLE_STATUSES),
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

    async with session.begin():
        await set_tenant(session, tenant_id)

        customers = (
            await session.execute(
                select(Customer.id, Customer.company_name)
                .where(Customer.tenant_id == tenant_id)
                .order_by(Customer.company_name)
            )
        ).all()

        current_order_window = Order.created_at >= window_current_start
        prior_order_window = and_(
            Order.created_at >= window_prior_start,
            Order.created_at < window_current_start,
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
                    func.min(Order.created_at).label("first_order_at"),
                    func.max(Order.created_at).label("last_order_at"),
                )
                .where(
                    Order.tenant_id == tenant_id,
                    Order.status.in_(_COUNTABLE_STATUSES),
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
                    Order.status.in_(_COUNTABLE_STATUSES),
                    Product.category.is_not(None),
                    Order.created_at >= window_prior_start,
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

    async with session.begin():
        await set_tenant(session, tenant_id)

        customer_summary_rows = (
            await session.execute(
                select(Customer.id, Customer.company_name)
                .add_columns(
                    func.count(func.distinct(Order.id)).label("order_count_total"),
                    func.count(
                        func.distinct(
                            case((Order.created_at >= recent_window_start, Order.id), else_=None)
                        )
                    ).label("order_count_recent"),
                    func.coalesce(func.sum(func.coalesce(Order.total_amount, 0)), 0).label("total_revenue"),
                    func.min(Order.created_at).label("first_order_at"),
                    func.max(Order.created_at).label("last_order_at"),
                )
                .join(Order, Order.customer_id == Customer.id)
                .where(
                    Customer.tenant_id == tenant_id,
                    customer_type_filter,
                    Order.tenant_id == tenant_id,
                    Order.status.in_(_COUNTABLE_STATUSES),
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
                    func.max(case((Order.created_at >= recent_window_start, 1), else_=0)).label("in_recent"),
                )
                .join(Customer, Customer.id == Order.customer_id)
                .join(OrderLine, OrderLine.order_id == Order.id)
                .join(Product, Product.id == OrderLine.product_id)
                .where(
                    Customer.tenant_id == tenant_id,
                    customer_type_filter,
                    Order.tenant_id == tenant_id,
                    Product.tenant_id == tenant_id,
                    Order.status.in_(_COUNTABLE_STATUSES),
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
                    Order.status.in_(_COUNTABLE_STATUSES),
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
                Order.status.in_(_COUNTABLE_STATUSES),
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


async def get_product_affinity_map(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    min_shared: int = 2,
    limit: int = 50,
) -> ProductAffinityMap:
    """Compute customer-level product affinity pairs from qualifying orders."""
    if min_shared < 1 or limit < 1:
        raise ValueError(f"min_shared and limit must be >= 1, got min_shared={min_shared}, limit={limit}")
    normalized_limit = limit
    computed_at = datetime.now(tz=UTC)

    async with session.begin():
        await set_tenant(session, tenant_id)

        qualifying_rows = (
            select(
                Order.customer_id.label("customer_id"),
                Order.id.label("order_id"),
                Product.id.label("product_id"),
            )
            .join(OrderLine, OrderLine.order_id == Order.id)
            .join(Product, Product.id == OrderLine.product_id)
            .where(
                Order.tenant_id == tenant_id,
                Product.tenant_id == tenant_id,
                Order.status.in_(_COUNTABLE_STATUSES),
            )
            .distinct()
            .cte("qualifying_rows")
        )

        customer_counts = (
            select(
                qualifying_rows.c.product_id.label("product_id"),
                func.count(func.distinct(qualifying_rows.c.customer_id)).label("customer_count"),
            )
            .group_by(qualifying_rows.c.product_id)
            .cte("customer_counts")
        )

        customer_rows_a = qualifying_rows.alias("customer_rows_a")
        customer_rows_b = qualifying_rows.alias("customer_rows_b")
        pair_customer_counts = (
            select(
                customer_rows_a.c.product_id.label("product_a_id"),
                customer_rows_b.c.product_id.label("product_b_id"),
                func.count(func.distinct(customer_rows_a.c.customer_id)).label("shared_customer_count"),
            )
            .select_from(
                customer_rows_a.join(
                    customer_rows_b,
                    and_(
                        customer_rows_a.c.customer_id == customer_rows_b.c.customer_id,
                        cast(customer_rows_a.c.product_id, String) < cast(customer_rows_b.c.product_id, String),
                    ),
                )
            )
            .group_by(customer_rows_a.c.product_id, customer_rows_b.c.product_id)
            .having(func.count(func.distinct(customer_rows_a.c.customer_id)) >= min_shared)
            .cte("pair_customer_counts")
        )

        order_rows_a = qualifying_rows.alias("order_rows_a")
        order_rows_b = qualifying_rows.alias("order_rows_b")
        pair_order_counts = (
            select(
                order_rows_a.c.product_id.label("product_a_id"),
                order_rows_b.c.product_id.label("product_b_id"),
                func.count(func.distinct(order_rows_a.c.order_id)).label("shared_order_count"),
            )
            .select_from(
                order_rows_a.join(
                    order_rows_b,
                    and_(
                        order_rows_a.c.order_id == order_rows_b.c.order_id,
                        cast(order_rows_a.c.product_id, String) < cast(order_rows_b.c.product_id, String),
                    ),
                )
            )
            .group_by(order_rows_a.c.product_id, order_rows_b.c.product_id)
            .cte("pair_order_counts")
        )

        customer_count_a = customer_counts.alias("customer_count_a")
        customer_count_b = customer_counts.alias("customer_count_b")
        product_a = Product.__table__.alias("product_a")
        product_b = Product.__table__.alias("product_b")

        total_pairs = int(
            (
                await session.execute(
                    select(func.count()).select_from(pair_customer_counts)
                )
            ).scalar_one()
            or 0
        )

        if total_pairs <= 0:
            return ProductAffinityMap(
                pairs=[],
                total=0,
                min_shared=min_shared,
                limit=normalized_limit,
                computed_at=computed_at,
            )

        union_count = (
            customer_count_a.c.customer_count
            + customer_count_b.c.customer_count
            - pair_customer_counts.c.shared_customer_count
        )
        affinity_rank = cast(pair_customer_counts.c.shared_customer_count, Float) / func.nullif(
            cast(union_count, Float),
            0.0,
        )
        rounded_affinity_rank = func.round(cast(affinity_rank, Numeric(18, 8)), 4)

        rows = (
            await session.execute(
                select(
                    pair_customer_counts.c.product_a_id,
                    pair_customer_counts.c.product_b_id,
                    product_a.c.name.label("product_a_name"),
                    product_b.c.name.label("product_b_name"),
                    pair_customer_counts.c.shared_customer_count,
                    customer_count_a.c.customer_count.label("customer_count_a"),
                    customer_count_b.c.customer_count.label("customer_count_b"),
                    pair_order_counts.c.shared_order_count,
                )
                .select_from(
                    pair_customer_counts
                    .join(customer_count_a, customer_count_a.c.product_id == pair_customer_counts.c.product_a_id)
                    .join(customer_count_b, customer_count_b.c.product_id == pair_customer_counts.c.product_b_id)
                    .join(product_a, product_a.c.id == pair_customer_counts.c.product_a_id)
                    .join(product_b, product_b.c.id == pair_customer_counts.c.product_b_id)
                    .outerjoin(
                        pair_order_counts,
                        and_(
                            pair_order_counts.c.product_a_id == pair_customer_counts.c.product_a_id,
                            pair_order_counts.c.product_b_id == pair_customer_counts.c.product_b_id,
                        ),
                    )
                )
                .order_by(
                    rounded_affinity_rank.desc(),
                    pair_customer_counts.c.shared_customer_count.desc(),
                    product_a.c.name.asc(),
                    product_b.c.name.asc(),
                )
                .limit(normalized_limit)
            )
        ).all()

    pairs: list[AffinityPair] = []
    for row in rows:
        shared_customer_count = int(row.shared_customer_count or 0)
        customer_count_a_value = int(row.customer_count_a or 0)
        customer_count_b_value = int(row.customer_count_b or 0)
        min_customer_count = min(customer_count_a_value, customer_count_b_value)
        union_count_value = customer_count_a_value + customer_count_b_value - shared_customer_count
        if min_customer_count <= 0 or union_count_value <= 0:
            continue

        overlap_pct = (
            Decimal(shared_customer_count) * Decimal("100") / Decimal(min_customer_count)
        ).quantize(_PCT_QUANT)
        affinity_score = (
            Decimal(shared_customer_count) / Decimal(union_count_value)
        ).quantize(_RATIO_QUANT, rounding=ROUND_HALF_UP)

        pairs.append(
            AffinityPair(
                product_a_id=row.product_a_id,
                product_b_id=row.product_b_id,
                product_a_name=row.product_a_name,
                product_b_name=row.product_b_name,
                shared_customer_count=shared_customer_count,
                customer_count_a=customer_count_a_value,
                customer_count_b=customer_count_b_value,
                shared_order_count=(
                    int(row.shared_order_count)
                    if row.shared_order_count is not None
                    else None
                ),
                overlap_pct=_to_ratio(overlap_pct, quant=_PCT_QUANT),
                affinity_score=_to_ratio(affinity_score),
                pitch_hint=_make_pitch_hint(row.product_a_name, row.product_b_name, affinity_score),
            )
        )

    return ProductAffinityMap(
        pairs=pairs,
        total=total_pairs,
        min_shared=min_shared,
        limit=normalized_limit,
        computed_at=computed_at,
    )


def build_empty_customer_product_profile(
    customer_id: uuid.UUID,
    *,
    company_name: str = "",
) -> CustomerProductProfile:
    return CustomerProductProfile(
        customer_id=customer_id,
        company_name=company_name,
        total_revenue_12m=_ZERO,
        order_count_12m=0,
        order_count_3m=0,
        order_count_6m=0,
        order_count_prior_12m=0,
        order_count_prior_3m=0,
        frequency_trend="stable",
        avg_order_value=_ZERO,
        avg_order_value_prior=_ZERO,
        aov_trend="stable",
        top_categories=[],
        top_products=[],
        last_order_date=None,
        days_since_last_order=None,
        is_dormant=True,
        new_categories=[],
        confidence="low",
        activity_basis="confirmed_or_later_orders",
    )


async def get_customer_product_profile(
    session: AsyncSession,
    customer_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> CustomerProductProfile:
    """Return a summarized purchasing profile for one customer."""
    now = datetime.now(tz=UTC)
    window_12m_start = _subtract_months(now, 12)
    window_6m_start = _subtract_months(now, 6)
    window_3m_start = _subtract_months(now, 3)
    window_prior_12m_start = _subtract_months(now, 24)
    window_prior_3m_start = _subtract_months(now, 6)
    recent_category_cutoff = now - timedelta(days=90)

    async with session.begin():
        await set_tenant(session, tenant_id)

        customer_result = await session.execute(
            select(Customer).where(
                Customer.id == customer_id,
                Customer.tenant_id == tenant_id,
            )
        )
        customer = customer_result.scalar_one_or_none()
        if customer is None:
            raise ValueError("Customer not found.")

        order_metrics_stmt = select(
            func.coalesce(
                func.sum(
                    case(
                        (Order.created_at >= window_12m_start, func.coalesce(Order.total_amount, 0)),
                        else_=0,
                    )
                ),
                0,
            ).label("total_revenue_12m"),
            func.coalesce(
                func.sum(case((Order.created_at >= window_12m_start, 1), else_=0)),
                0,
            ).label("order_count_12m"),
            func.coalesce(
                func.sum(case((Order.created_at >= window_6m_start, 1), else_=0)),
                0,
            ).label("order_count_6m"),
            func.coalesce(
                func.sum(case((Order.created_at >= window_3m_start, 1), else_=0)),
                0,
            ).label("order_count_3m"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(
                                Order.created_at >= window_prior_12m_start,
                                Order.created_at < window_12m_start,
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("order_count_prior_12m"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(
                                Order.created_at >= window_prior_12m_start,
                                Order.created_at < window_12m_start,
                            ),
                            func.coalesce(Order.total_amount, 0),
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("total_revenue_prior_12m"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(
                                Order.created_at >= window_prior_3m_start,
                                Order.created_at < window_3m_start,
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("order_count_prior_3m"),
            func.max(Order.created_at).label("last_order_at"),
        ).where(
            Order.tenant_id == tenant_id,
            Order.customer_id == customer_id,
            Order.status.in_(_COUNTABLE_STATUSES),
        )
        order_metrics = (await session.execute(order_metrics_stmt)).first()

        total_revenue_12m = _to_decimal(getattr(order_metrics, "total_revenue_12m", None))
        order_count_12m = int(getattr(order_metrics, "order_count_12m", 0) or 0)
        order_count_6m = int(getattr(order_metrics, "order_count_6m", 0) or 0)
        order_count_3m = int(getattr(order_metrics, "order_count_3m", 0) or 0)
        order_count_prior_12m = int(getattr(order_metrics, "order_count_prior_12m", 0) or 0)
        order_count_prior_3m = int(getattr(order_metrics, "order_count_prior_3m", 0) or 0)
        total_revenue_prior_12m = _to_decimal(getattr(order_metrics, "total_revenue_prior_12m", None))
        last_order_at = getattr(order_metrics, "last_order_at", None)

        if order_count_12m == 0 and last_order_at is None:
            return build_empty_customer_product_profile(
                customer_id,
                company_name=customer.company_name,
            )

        category_stmt = (
            select(
                Product.category.label("category"),
                func.coalesce(func.sum(OrderLine.total_amount), 0).label("revenue"),
                func.count(func.distinct(Order.id)).label("order_count"),
            )
            .join(OrderLine, OrderLine.product_id == Product.id)
            .join(Order, OrderLine.order_id == Order.id)
            .where(
                Order.tenant_id == tenant_id,
                Order.customer_id == customer_id,
                Order.status.in_(_COUNTABLE_STATUSES),
                Order.created_at >= window_12m_start,
                Product.category.is_not(None),
            )
            .group_by(Product.category)
            .order_by(func.sum(OrderLine.total_amount).desc(), Product.category.asc())
            .limit(10)
        )
        category_rows = (await session.execute(category_stmt)).all()

        top_categories = [
            CategoryRevenue(
                category=row.category,
                revenue=_to_decimal(row.revenue),
                order_count=int(row.order_count or 0),
                revenue_pct_of_total=(
                    (Decimal(str(row.revenue or "0")) / total_revenue_12m).quantize(_RATIO_QUANT)
                    if total_revenue_12m > 0
                    else Decimal("0.0000")
                ),
            )
            for row in category_rows
        ]

        first_category_stmt = (
            select(
                Product.category.label("category"),
                func.min(Order.created_at).label("first_order_at"),
            )
            .join(OrderLine, OrderLine.product_id == Product.id)
            .join(Order, OrderLine.order_id == Order.id)
            .where(
                Order.tenant_id == tenant_id,
                Order.customer_id == customer_id,
                Order.status.in_(_COUNTABLE_STATUSES),
                Product.category.is_not(None),
            )
            .group_by(Product.category)
            .order_by(Product.category.asc())
        )
        new_categories = [
            row.category
            for row in (await session.execute(first_category_stmt)).all()
            if row.first_order_at is not None and row.first_order_at >= recent_category_cutoff
        ]

        product_stmt = (
            select(
                Product.id.label("product_id"),
                Product.name.label("product_name"),
                Product.category.label("category"),
                func.count(func.distinct(Order.id)).label("order_count"),
                func.coalesce(func.sum(OrderLine.quantity), 0).label("total_quantity"),
                func.coalesce(func.sum(OrderLine.total_amount), 0).label("total_revenue"),
            )
            .join(OrderLine, OrderLine.product_id == Product.id)
            .join(Order, OrderLine.order_id == Order.id)
            .where(
                Order.tenant_id == tenant_id,
                Order.customer_id == customer_id,
                Order.status.in_(_COUNTABLE_STATUSES),
                Order.created_at >= window_12m_start,
            )
            .group_by(Product.id, Product.name, Product.category)
            .order_by(
                func.count(func.distinct(Order.id)).desc(),
                func.sum(OrderLine.total_amount).desc(),
                Product.name.asc(),
            )
            .limit(20)
        )
        top_products = [
            ProductPurchase(
                product_id=row.product_id,
                product_name=row.product_name,
                category=row.category,
                order_count=int(row.order_count or 0),
                total_quantity=Decimal(str(row.total_quantity or "0")),
                total_revenue=_to_decimal(row.total_revenue),
            )
            for row in (await session.execute(product_stmt)).all()
        ]

    avg_order_value = _safe_average(total_revenue_12m, order_count_12m)
    avg_order_value_prior = _safe_average(total_revenue_prior_12m, order_count_prior_12m)
    last_order_date = last_order_at.date() if last_order_at is not None else None
    days_since_last_order = (
        (now.date() - last_order_date).days if last_order_date is not None else None
    )

    return CustomerProductProfile(
        customer_id=customer.id,
        company_name=customer.company_name,
        total_revenue_12m=total_revenue_12m,
        order_count_12m=order_count_12m,
        order_count_3m=order_count_3m,
        order_count_6m=order_count_6m,
        order_count_prior_12m=order_count_prior_12m,
        order_count_prior_3m=order_count_prior_3m,
        frequency_trend=_frequency_trend(order_count_3m, order_count_prior_3m),
        avg_order_value=avg_order_value,
        avg_order_value_prior=avg_order_value_prior,
        aov_trend=_aov_trend(avg_order_value, avg_order_value_prior),
        top_categories=top_categories,
        top_products=top_products,
        last_order_date=last_order_date,
        days_since_last_order=days_since_last_order,
        is_dormant=days_since_last_order is None or days_since_last_order > 60,
        new_categories=new_categories,
        confidence=_confidence(order_count_12m),
        activity_basis="confirmed_or_later_orders",
    )


def _shift_month_start(month_start: date, months: int) -> date:
    month_index = (month_start.year * 12 + month_start.month - 1) + months
    year = month_index // 12
    month = month_index % 12 + 1
    return date(year, month, 1)


def _revenue_diagnosis_windows(
    period: Literal["1m", "3m", "6m", "12m"],
    *,
    anchor_month: date,
) -> tuple[date, date, date, date]:
    month_count = _REVENUE_DIAGNOSIS_PERIOD_MONTHS[period]
    current_end = normalize_month_start(anchor_month)
    current_start = _shift_month_start(current_end, -(month_count - 1))
    prior_end = _shift_month_start(current_start, -1)
    prior_start = _shift_month_start(prior_end, -(month_count - 1))
    return current_start, current_end, prior_start, prior_end


def _safe_unit_price(revenue: Decimal, quantity: Decimal) -> Decimal:
    if quantity <= 0:
        return _ZERO
    return (revenue / quantity).quantize(_MONEY_QUANT)


def _percent_change(current_value: Decimal, prior_value: Decimal) -> float | None:
    if prior_value == 0:
        return None
    return float(((current_value - prior_value) / prior_value * Decimal("100")).quantize(_PCT_QUANT))


def _aggregate_revenue_window(
    points: tuple[SalesMonthlyPoint, ...],
    *,
    category: str | None,
) -> dict[uuid.UUID, _RevenueDiagnosisWindowMetrics]:
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
