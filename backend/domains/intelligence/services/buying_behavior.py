"""Customer buying behavior service.

Analyzes customer segment buying patterns and cross-sell opportunities,
identifying category co-purchase patterns and lift scores.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date
from decimal import Decimal

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.order_reporting import commercially_committed_order_filter, commercially_committed_timestamp_expr
from common.models.order import Order
from common.models.order_line import OrderLine
from common.tenant import set_tenant
from domains.customers.models import Customer

from domains.intelligence.schemas import (
    CustomerBuyingBehavior,
    CustomerBuyingBehaviorCrossSell,
    CustomerBuyingBehaviorPattern,
    CustomerBuyingBehaviorPeriod,
    CustomerBuyingBehaviorWindow,
)

from .shared import (
    RATIO_QUANT,
    ZERO,
    CUSTOMER_BUYING_BEHAVIOR_PERIOD_MONTHS,
    average_count,
    is_excluded_category,
    iter_month_starts,
    ratio,
    safe_average,
    shift_month_start,
    subtract_months,
    to_decimal,
)


@dataclass(slots=True)
class _CustomerBehaviorLine:
    customer_id: uuid.UUID
    customer_type: str
    order_id: uuid.UUID
    month_start: date
    category: str
    revenue: Decimal


async def get_customer_buying_behavior(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    customer_type: str = "dealer",
    period: CustomerBuyingBehaviorPeriod = "12m",
    limit: int = 20,
    include_current_month: bool = False,
) -> CustomerBuyingBehavior:
    """Analyze customer segment buying behavior and cross-sell patterns.

    Computes:
    - Top categories by revenue and customer count
    - Cross-sell opportunities with lift scores
    - Monthly buying patterns over the analysis window
    """
    normalized_limit = max(1, min(limit, 100))
    anchor_month = date.today().replace(day=1)  # Use date directly
    months = CUSTOMER_BUYING_BEHAVIOR_PERIOD_MONTHS[period]
    window_end = anchor_month if include_current_month else shift_month_start(anchor_month, -1)
    window_start = shift_month_start(window_end, -(months - 1))
    window_end_exclusive = shift_month_start(window_end, 1)
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
                    analytics_timestamp >= window_start,
                    analytics_timestamp < window_end_exclusive,
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
        for month_start in iter_month_starts(window_start, window_end)
    }

    for row in rows:
        category = (row.category or "").strip()
        if not category or is_excluded_category(category):
            continue

        line = _CustomerBehaviorLine(
            customer_id=row.customer_id,
            customer_type=row.customer_type,
            order_id=row.order_id,
            month_start=row.analytics_at.date().replace(day=1) if row.analytics_at else window_start,
            category=category,
            revenue=to_decimal(row.line_revenue),
        )

        if customer_type == "all" or row.customer_type == customer_type:
            selected_lines.append(line)
            total_revenue += line.revenue

            metrics = customer_metrics.setdefault(
                line.customer_id,
                {"revenue": Decimal("0.00"), "orders": set(), "categories": set()},
            )
            metrics["revenue"] = to_decimal(metrics["revenue"] + line.revenue)
            metrics["orders"].add(line.order_id)
            metrics["categories"].add(line.category)

            category_entry = category_metrics.setdefault(
                line.category,
                {"revenue": Decimal("0.00"), "orders": set(), "customers": set()},
            )
            category_entry["revenue"] = to_decimal(category_entry["revenue"] + line.revenue)
            category_entry["orders"].add(line.order_id)
            category_entry["customers"].add(line.customer_id)

            pattern_entry = pattern_metrics[line.month_start]
            pattern_entry["revenue"] = to_decimal(pattern_entry["revenue"] + line.revenue)
            pattern_entry["orders"].add(line.order_id)
            pattern_entry["customers"].add(line.customer_id)
        else:
            outside_lines.append(line)

    customer_count = len(customer_metrics)
    avg_revenue_per_customer = safe_average(total_revenue, customer_count)
    avg_order_count_per_customer = average_count(
        sum(len(metrics["orders"]) for metrics in customer_metrics.values()),
        customer_count,
    )
    avg_categories_per_customer = average_count(
        sum(len(metrics["categories"]) for metrics in customer_metrics.values()),
        customer_count,
    )

    top_categories = [
        {
            "category": category,
            "revenue": to_decimal(metrics["revenue"]),
            "order_count": len(metrics["orders"]),
            "customer_count": len(metrics["customers"]),
            "revenue_share": (
                (to_decimal(metrics["revenue"]) / total_revenue).quantize(RATIO_QUANT)
                if total_revenue > 0
                else Decimal("0.0000")
            ),
        }
        for category, metrics in category_metrics.items()
    ]
    top_categories.sort(key=lambda item: (-item["revenue"], -item["customer_count"], item["category"]))

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

        segment_penetration = ratio(shared_customer_count, anchor_customer_count)
        if customer_type == "all":
            outside_anchor_customer_count = 0
            outside_shared_customer_count = 0
            outside_segment_penetration = Decimal("0.0000")
            lift_score = None
        else:
            outside_anchor_customer_count = outside_anchor_counts.get(anchor_category, 0)
            outside_shared_customer_count = outside_pair_counts.get((anchor_category, recommended_category), 0)
            outside_segment_penetration = ratio(outside_shared_customer_count, outside_anchor_customer_count)
            lift_score = (
                (segment_penetration / outside_segment_penetration).quantize(RATIO_QUANT)
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
            revenue=to_decimal(metrics["revenue"]),
            order_count=len(metrics["orders"]),
            customer_count=len(metrics["customers"]),
        )
        for month_start, metrics in sorted(pattern_metrics.items())
    ]

    return CustomerBuyingBehavior(
        customer_type=customer_type,  # type: ignore[arg-type]
        period=period,
        window=CustomerBuyingBehaviorWindow(start_month=window_start, end_month=window_end),
        computed_at=date.today(),
        customer_count=customer_count,
        avg_revenue_per_customer=avg_revenue_per_customer,
        avg_order_count_per_customer=avg_order_count_per_customer,
        avg_categories_per_customer=avg_categories_per_customer,
        top_categories=[{
            "category": item["category"],
            "revenue": item["revenue"],
            "order_count": item["order_count"],
            "customer_count": item["customer_count"],
            "revenue_share": item["revenue_share"],
        } for item in top_categories[:normalized_limit]],
        cross_sell_opportunities=cross_sell_opportunities[:normalized_limit],
        buying_patterns=buying_patterns,
        data_basis="transactional_fallback",
        window_is_partial=include_current_month,
    )
