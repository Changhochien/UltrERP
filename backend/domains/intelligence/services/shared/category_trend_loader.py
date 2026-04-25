"""Shared lower-level loader for category trend metrics."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from typing import Literal

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.order_reporting import commercially_committed_order_filter, commercially_committed_timestamp_expr
from common.models.order import Order
from common.models.order_line import OrderLine
from common.models.product import Product
from common.tenant import set_tenant
from domains.intelligence.schemas import CategoryTrend, TopProductByRevenue

from .category_helpers import is_excluded_category
from .date_helpers import period_windows
from .decimal_helpers import to_decimal, to_ratio
from .constants import PCT_QUANT


async def load_category_trends(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    period: Literal["last_30d", "last_90d", "last_12m"] = "last_90d",
) -> list[CategoryTrend]:
    """Load category trend rows for callers that need the shared trend computation."""
    current_start, prior_start, end = period_windows(period)
    current_start_dt = datetime.combine(current_start, time.min, tzinfo=UTC)
    prior_start_dt = datetime.combine(prior_start, time.min, tzinfo=UTC)
    next_day_dt = datetime.combine(end + timedelta(days=1), time.min, tzinfo=UTC)
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
                    current_order_window,
                    Product.category.is_not(None),
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
        if is_excluded_category(row.category):
            continue
        top_products_by_category.setdefault(row.category, []).append(
            TopProductByRevenue(
                product_id=row.product_id,
                product_name=row.product_name,
                revenue=to_decimal(row.revenue),
            )
        )

    new_customer_counts = {
        row.category: int(row.new_customer_count or 0)
        for row in new_customer_rows
        if not is_excluded_category(row.category)
    }
    churned_customer_counts = {
        row.category: int(row.churned_customer_count or 0)
        for row in churned_customer_rows
        if not is_excluded_category(row.category)
    }

    trends: list[CategoryTrend] = []
    for row in category_metric_rows:
        category = row.category
        if is_excluded_category(category):
            continue

        current_revenue = to_decimal(row.current_revenue)
        prior_revenue = to_decimal(row.prior_revenue)
        current_order_count = int(row.current_orders or 0)
        prior_order_count = int(row.prior_orders or 0)
        current_customer_count = int(row.current_customers or 0)
        prior_customer_count = int(row.prior_customers or 0)

        revenue_delta_pct: float | None
        trend_context: Literal["newly_active", "insufficient_history"] | None = None
        if prior_revenue > 0:
            revenue_delta_pct = to_ratio(
                ((current_revenue - prior_revenue) / prior_revenue) * Decimal("100"),
                quant=PCT_QUANT,
            )
        else:
            revenue_delta_pct = None
            if current_revenue > 0:
                trend_context = "newly_active"
            else:
                trend_context = "insufficient_history"

        order_delta_pct: float | None
        if prior_order_count > 0:
            order_delta_pct = to_ratio(
                (
                    (Decimal(current_order_count) - Decimal(prior_order_count))
                    / Decimal(prior_order_count)
                )
                * Decimal("100"),
                quant=PCT_QUANT,
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

    return trends