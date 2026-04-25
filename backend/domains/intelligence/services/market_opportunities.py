"""Market opportunities service.

Aggregates market opportunity signals including concentration risk
and category growth trends using a shared lower-level seam.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import Literal

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.order_reporting import commercially_committed_timestamp_expr
from common.models.order import Order
from common.tenant import set_tenant
from domains.customers.models import Customer

from domains.intelligence.schemas import CategoryTrend, MarketOpportunities, OpportunitySignal

from .shared import (
    PCT_QUANT,
    ZERO,
    OPPORTUNITY_SEVERITY_PRIORITY,
    load_category_trends,
    period_windows,
    to_decimal,
)


def _build_category_growth_signals(
    trends: list[CategoryTrend],
    max_signals: int = 3,
) -> list[tuple[CategoryTrend, Decimal, Literal["info", "warning"]]]:
    """Build category growth signals from precomputed category trends."""
    growth_trends = [
        trend
        for trend in trends
        if trend.revenue_delta_pct is not None
        and trend.revenue_delta_pct > 0
        and trend.trend == "growing"
        and trend.customer_count >= 2
        and trend.current_period_orders >= 2
    ]

    signals: list[tuple[CategoryTrend, Decimal, Literal["info", "warning"]]] = []
    for trend in growth_trends[:max_signals]:
        delta_absolute = trend.current_period_revenue - trend.prior_period_revenue
        severity: Literal["info", "warning"] = "warning" if trend.revenue_delta_pct >= 30 else "info"
        signals.append((trend, delta_absolute, severity))

    return signals


async def get_market_opportunities(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    period: Literal["last_30d", "last_90d", "last_12m"] = "last_90d",
) -> MarketOpportunities:
    """Aggregate market opportunity signals.

    Identifies:
    - Concentration risk: customers representing >30% of total revenue
    - Category growth: categories with positive revenue trends
    
    Uses a shared lower-level seam for category trend data instead of
    calling the public get_category_trends() entrypoint.
    """
    current_start, prior_start, end = period_windows(period)
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
                    analytics_timestamp >= prior_start_dt,
                    analytics_timestamp < next_day_dt,
                )
                .group_by(Order.customer_id, Customer.company_name)
            )
        ).all()

    current_revenue_total = ZERO
    prior_revenue_total = ZERO
    current_customer_revenue: dict[uuid.UUID, tuple[str, Decimal]] = {}
    prior_customer_revenue: dict[uuid.UUID, Decimal] = {}
    current_customers_considered = 0
    prior_customers_considered = 0

    for row in customer_revenue_rows:
        current_order_count = int(row.current_order_count or 0)
        prior_order_count = int(row.prior_order_count or 0)
        current_revenue = to_decimal(row.current_revenue)
        prior_revenue = to_decimal(row.prior_revenue)
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
                (prior_customer_revenue.get(customer_id, ZERO) / prior_revenue_total) if prior_revenue_total > 0 else None
            )
            prior_share_text = (
                f" Prior period share was {(prior_share * Decimal('100')).quantize(PCT_QUANT)}%."
                if prior_share is not None
                else ""
            )
            signals.append(
                OpportunitySignal(
                    signal_type="concentration_risk",
                    severity="alert",
                    headline=f"{company_name} represents {(share * Decimal('100')).quantize(PCT_QUANT)}% of total revenue — concentration risk",
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

    category_trends = await load_category_trends(session, tenant_id, period=period)
    growth_signals = _build_category_growth_signals(category_trends)
    
    for trend, delta_absolute, severity in growth_signals:
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
            OPPORTUNITY_SEVERITY_PRIORITY[signal.severity],
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
