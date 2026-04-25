"""Product performance service.

Analyzes product lifecycle stages and performance metrics using
aggregate monthly data and live order line evidence.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from decimal import Decimal
from typing import Literal

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.order_reporting import commercially_committed_order_filter, commercially_committed_timestamp_expr
from common.models.order import Order
from common.models.order_line import OrderLine
from common.tenant import set_tenant
from domains.product_analytics.service import SalesMonthlyPoint, read_sales_monthly_range

from domains.intelligence.schemas import (
    ProductLifecycleStage,
    ProductPerformance,
    ProductPerformanceDataBasis,
    ProductPerformancePeriodMetrics,
    ProductPerformanceRow,
    ProductPerformanceWindow,
)

from .shared import (
    MONEY_QUANT,
    QUANTITY_QUANT,
    ZERO,
    months_between_inclusive,
    month_start_from_timestamp,
    normalize_month_start,
    percent_change,
    shift_month_start,
    to_decimal,
)


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


def _product_performance_windows(
    *,
    include_current_month: bool,
    anchor_month: date,
) -> tuple[date, date, date, date]:
    """Calculate product performance window dates."""
    if include_current_month:
        current_end = anchor_month
    else:
        current_end = shift_month_start(anchor_month, -1)
    current_start = shift_month_start(current_end, -11)
    prior_end = shift_month_start(current_start, -1)
    prior_start = shift_month_start(prior_end, -11)
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

        aggregate["revenue"] = to_decimal(aggregate["revenue"] + point.revenue)
        aggregate["quantity"] = to_decimal(
            aggregate["quantity"] + point.quantity_sold,
            quant=QUANTITY_QUANT,
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
            revenue=to_decimal(values["revenue"]),
            quantity=to_decimal(values["quantity"], quant=QUANTITY_QUANT),
            order_count=int(values["order_count"]),
            avg_unit_price=(
                (to_decimal(values["revenue"]) / to_decimal(values["quantity"], quant=QUANTITY_QUANT)).quantize(MONEY_QUANT)
                if to_decimal(values["quantity"], quant=QUANTITY_QUANT) > 0
                else ZERO
            ),
            first_sale_month=values["first_sale_month"],
            last_sale_month=values["last_sale_month"],
            latest_month=values["latest_month"],
            peak_month_revenue=to_decimal(values["peak_month_revenue"]),
        )
        for product_id, values in aggregates.items()
    }


def _empty_product_performance_period_metrics() -> ProductPerformancePeriodMetrics:
    """Return empty period metrics."""
    return ProductPerformancePeriodMetrics(
        revenue=ZERO,
        quantity=Decimal("0.000"),
        order_count=0,
        avg_unit_price=ZERO,
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
    six_complete_month_cutoff = shift_month_start(anchor_month, -6)
    if current_revenue > ZERO and prior_revenue == ZERO and first_sale_month >= current_window_start:
        return "new", ["rule:new", "prior_revenue_zero", "first_sale_in_current_window"]
    if current_revenue == ZERO and prior_revenue > ZERO and last_sale_month <= six_complete_month_cutoff:
        return "end_of_life", [
            "rule:end_of_life",
            "current_revenue_zero",
            "last_sale_at_least_6_complete_months_before_anchor",
        ]
    if prior_revenue > ZERO and (
        current_revenue == ZERO or current_revenue < (prior_revenue * Decimal("0.80"))
    ):
        return "declining", ["rule:declining", "current_revenue_below_0.80x_prior"]
    if prior_revenue > ZERO and current_revenue >= (prior_revenue * Decimal("1.20")):
        return "growing", ["rule:growing", "current_revenue_at_least_1.20x_prior"]
    if (
        current_revenue > ZERO
        and prior_revenue > ZERO
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
        shift_month_start(included_window_end, 1),
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
                first_sale_month=month_start_from_timestamp(first_analytics_at),
                last_sale_month=month_start_from_timestamp(last_analytics_at),
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
    """Analyze product performance with lifecycle staging.

    Classifies products into lifecycle stages:
    - new: First sale in current window
    - growing: Revenue increased >= 20%
    - stable: Revenue within 80%-120% of prior
    - declining: Revenue decreased >= 20%
    - end_of_life: No current sales after 6+ months
    """
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
        months_on_sale = months_between_inclusive(first_sale_month, last_sale_month)
        current_revenue = current_metric.revenue if current_metric is not None else ZERO
        prior_revenue = prior_metric.revenue if prior_metric is not None else ZERO
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
                revenue_delta_pct=percent_change(current_revenue, prior_revenue),
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
