"""Customer risk signals service.

Analyzes customer accounts to classify risk status and generate actionable signals
based on revenue trends, order frequency, and category expansion patterns.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
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

from domains.intelligence.schemas import CustomerRiskSignal, CustomerRiskSignals

from .shared import (
    ZERO,
    RISK_STATUS_PRIORITY,
    bounded_similarity,
    confidence,
    is_excluded_category,
    safe_average,
    subtract_months,
    to_decimal,
    to_ratio,
)


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


async def get_customer_risk_signals(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    status_filter: Literal["all", "growing", "at_risk", "dormant", "new", "stable"] = "all",
    limit: int = 50,
) -> CustomerRiskSignals:
    """Rank customer accounts by deterministic risk and growth signals.

    Classifies customers as growing, stable, at_risk, dormant, or new based on:
    - Revenue trends (20% threshold)
    - Days since last order (60 day dormant threshold)
    - Account age (90 day new account threshold)
    - Category expansion/contraction patterns
    """
    now = datetime.now(tz=UTC)
    today = now.date()
    window_current_start = subtract_months(now, 12)
    window_prior_start = subtract_months(now, 24)
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
            "revenue_current": ZERO,
            "revenue_prior": ZERO,
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

        metrics["revenue_current"] = to_decimal(row.revenue_current)
        metrics["revenue_prior"] = to_decimal(row.revenue_prior)
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
        if metrics is None or is_excluded_category(row.category):
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

        avg_order_value_current = safe_average(revenue_current, order_count_current)
        avg_order_value_prior = safe_average(revenue_prior, order_count_prior)
        revenue_delta_pct = (
            to_ratio(((revenue_current - revenue_prior) / revenue_prior) * Decimal("100"), quant=Decimal("0.1"))
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
            confidence=confidence(order_count_current + order_count_prior),
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
            RISK_STATUS_PRIORITY[customer.status],
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


# Priority ordering for risk status sorting

