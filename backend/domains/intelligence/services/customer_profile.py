"""Customer product profile service.

Provides aggregated purchasing profile for individual customers including
revenue trends, category preferences, and dormant detection.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Literal

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.order_reporting import commercially_committed_order_filter, commercially_committed_timestamp_expr
from common.models.order import Order
from common.models.order_line import OrderLine
from common.models.product import Product
from common.tenant import set_tenant
from domains.customers.models import Customer

from domains.intelligence.schemas import (
    CategoryRevenue,
    CustomerProductProfile,
    ProductPurchase,
)

from .shared import RATIO_QUANT, ZERO, aov_trend, frequency_trend, safe_average, subtract_months, to_decimal


def _confidence(order_count_12m: int) -> Literal["high", "medium", "low"]:
    """Determine confidence level based on 12-month order count."""
    if order_count_12m >= 6:
        return "high"
    if order_count_12m >= 2:
        return "medium"
    return "low"


def build_empty_customer_product_profile(
    customer_id: uuid.UUID,
    *,
    company_name: str = "",
) -> CustomerProductProfile:
    """Build an empty customer product profile for new or dormant customers."""
    return CustomerProductProfile(
        customer_id=customer_id,
        company_name=company_name,
        total_revenue_12m=ZERO,
        order_count_12m=0,
        order_count_3m=0,
        order_count_6m=0,
        order_count_prior_12m=0,
        order_count_prior_3m=0,
        frequency_trend="stable",
        avg_order_value=ZERO,
        avg_order_value_prior=ZERO,
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
    """Return a summarized purchasing profile for one customer.

    Includes revenue metrics, category preferences, top products,
    dormant detection, and trend analysis.
    """
    now = datetime.now(tz=UTC)
    window_12m_start = subtract_months(now, 12)
    window_6m_start = subtract_months(now, 6)
    window_3m_start = subtract_months(now, 3)
    window_prior_12m_start = subtract_months(now, 24)
    window_prior_3m_start = subtract_months(now, 6)
    recent_category_cutoff = now - timedelta(days=90)
    analytics_timestamp = commercially_committed_timestamp_expr()

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
                        (analytics_timestamp >= window_12m_start, func.coalesce(Order.total_amount, 0)),
                        else_=0,
                    )
                ),
                0,
            ).label("total_revenue_12m"),
            func.coalesce(
                func.sum(case((analytics_timestamp >= window_12m_start, 1), else_=0)),
                0,
            ).label("order_count_12m"),
            func.coalesce(
                func.sum(case((analytics_timestamp >= window_6m_start, 1), else_=0)),
                0,
            ).label("order_count_6m"),
            func.coalesce(
                func.sum(case((analytics_timestamp >= window_3m_start, 1), else_=0)),
                0,
            ).label("order_count_3m"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(
                                analytics_timestamp >= window_prior_12m_start,
                                analytics_timestamp < window_12m_start,
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
                                analytics_timestamp >= window_prior_12m_start,
                                analytics_timestamp < window_12m_start,
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
                                analytics_timestamp >= window_prior_3m_start,
                                analytics_timestamp < window_3m_start,
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("order_count_prior_3m"),
            func.max(analytics_timestamp).label("last_order_at"),
        ).where(
            Order.tenant_id == tenant_id,
            Order.customer_id == customer_id,
            commercially_committed_order_filter(),
        )
        order_metrics = (await session.execute(order_metrics_stmt)).first()

        total_revenue_12m = to_decimal(getattr(order_metrics, "total_revenue_12m", None))
        order_count_12m = int(getattr(order_metrics, "order_count_12m", 0) or 0)
        order_count_6m = int(getattr(order_metrics, "order_count_6m", 0) or 0)
        order_count_3m = int(getattr(order_metrics, "order_count_3m", 0) or 0)
        order_count_prior_12m = int(getattr(order_metrics, "order_count_prior_12m", 0) or 0)
        order_count_prior_3m = int(getattr(order_metrics, "order_count_prior_3m", 0) or 0)
        total_revenue_prior_12m = to_decimal(getattr(order_metrics, "total_revenue_prior_12m", None))
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
                commercially_committed_order_filter(),
                analytics_timestamp >= window_12m_start,
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
                revenue=to_decimal(row.revenue),
                order_count=int(row.order_count or 0),
                revenue_pct_of_total=(
                    (Decimal(str(row.revenue or "0")) / total_revenue_12m).quantize(RATIO_QUANT)
                    if total_revenue_12m > 0
                    else Decimal("0.0000")
                ),
            )
            for row in category_rows
        ]

        first_category_stmt = (
            select(
                Product.category.label("category"),
                func.min(analytics_timestamp).label("first_order_at"),
            )
            .join(OrderLine, OrderLine.product_id == Product.id)
            .join(Order, OrderLine.order_id == Order.id)
            .where(
                Order.tenant_id == tenant_id,
                Order.customer_id == customer_id,
                commercially_committed_order_filter(),
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
                commercially_committed_order_filter(),
                analytics_timestamp >= window_12m_start,
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
                total_revenue=to_decimal(row.total_revenue),
            )
            for row in (await session.execute(product_stmt)).all()
        ]

    avg_order_value = safe_average(total_revenue_12m, order_count_12m)
    avg_order_value_prior = safe_average(total_revenue_prior_12m, order_count_prior_12m)
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
        frequency_trend=frequency_trend(order_count_3m, order_count_prior_3m),
        avg_order_value=avg_order_value,
        avg_order_value_prior=avg_order_value_prior,
        aov_trend=aov_trend(avg_order_value, avg_order_value_prior),
        top_categories=top_categories,
        top_products=top_products,
        last_order_date=last_order_date,
        days_since_last_order=days_since_last_order,
        is_dormant=days_since_last_order is None or days_since_last_order > 60,
        new_categories=new_categories,
        confidence=_confidence(order_count_12m),
        activity_basis="confirmed_or_later_orders",
    )
