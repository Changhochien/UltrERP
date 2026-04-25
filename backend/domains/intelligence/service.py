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

# Import extracted feature modules (Story 40.5)
from .services.revenue_diagnosis import get_revenue_diagnosis as _get_revenue_diagnosis
from .services.product_performance import get_product_performance as _get_product_performance

# Re-export for backward compatibility (facade pattern)
get_product_affinity_map = _get_product_affinity_map
build_empty_customer_product_profile = _build_empty_customer_product_profile
get_customer_product_profile = _get_customer_product_profile
get_customer_risk_signals = _get_customer_risk_signals
get_prospect_gaps = _get_prospect_gaps
get_customer_buying_behavior = _get_customer_buying_behavior
get_category_trends = _get_category_trends
get_market_opportunities = _get_market_opportunities
get_revenue_diagnosis = _get_revenue_diagnosis
get_product_performance = _get_product_performance

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
