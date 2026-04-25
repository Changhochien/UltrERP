"""Prospect gap analysis service.

Identifies non-buying customers as whitespace prospects for target categories
based on affinity scoring, behavioral similarity, and adjacent category support.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Literal

from sqlalchemy import and_, case, func, select, true
from sqlalchemy.ext.asyncio import AsyncSession

from common.order_reporting import commercially_committed_order_filter, commercially_committed_timestamp_expr
from common.models.order import Order
from common.models.order_line import OrderLine
from common.models.product import Product
from common.tenant import set_tenant
from domains.customers.models import Customer

from domains.intelligence.schemas import ProspectFit, ProspectGaps, ProspectScoreComponents

from .shared import (
    ZERO,
    bounded_similarity,
    is_excluded_category,
    safe_average,
    subtract_months,
    to_decimal,
)


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


async def get_prospect_gaps(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    category: str,
    customer_type: str = "dealer",
    limit: int = 20,
) -> ProspectGaps:
    """Return active non-buyers ranked as whitespace prospects for a target category.

    Scores prospects based on:
    - Frequency similarity to existing buyers
    - Category breadth similarity
    - Adjacent category support
    - Recency of activity
    """
    target_category = category.strip()
    normalized_limit = max(1, min(limit, 100))
    now = datetime.now(tz=UTC)
    recent_window_start = subtract_months(now, 12)
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
            if not is_excluded_category(row.category)
        }
    )
    if not target_category:
        return ProspectGaps(
            target_category="",
            target_category_revenue=ZERO,
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
            "total_revenue": to_decimal(row.total_revenue),
            "first_order_date": row.first_order_at.date() if row.first_order_at is not None else None,
            "last_order_date": row.last_order_at.date() if row.last_order_at is not None else None,
            "categories": set(),
            "categories_recent": set(),
        }
        for row in customer_summary_rows
    }

    existing_buyers: set[uuid.UUID] = set()
    target_category_revenue = to_decimal(target_category_summary.target_category_revenue)

    for row in category_presence_rows:
        if is_excluded_category(row.category):
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
            target_category_revenue=ZERO,
            existing_buyers_count=0,
            prospects_count=0,
            prospects=[],
            available_categories=available_categories,
            generated_at=now,
        )

    adjacent_categories = {
        row.category
        for row in adjacent_category_rows
        if not is_excluded_category(row.category)
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
    high_value_threshold = total_revenues[high_value_index] if total_revenues else ZERO

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
        avg_order_value = safe_average(total_revenue, order_count_total)
        last_order_date = metrics["last_order_date"]
        first_order_date = metrics["first_order_date"]
        days_since_last_order = (now.date() - last_order_date).days if last_order_date else None
        recency_factor = 0.0 if days_since_last_order is None else max(0.0, 1.0 - min(days_since_last_order / 180, 1.0))
        frequency_similarity = bounded_similarity(float(order_count_recent), buyer_frequency_baseline)
        breadth_similarity = bounded_similarity(float(category_count_recent), buyer_breadth_baseline)
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
