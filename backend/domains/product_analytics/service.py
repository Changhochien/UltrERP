"""Shared monthly product sales aggregation helpers."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import delete, func, or_, select, tuple_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from common.models.order import Order
from common.models.order_line import OrderLine
from common.order_reporting import (
    commercially_committed_order_filter,
    commercially_committed_timestamp_expr,
)
from common.tenant import set_tenant
from domains.product_analytics.models import SalesMonthly

_MONEY_QUANT = Decimal("0.01")
_QUANTITY_QUANT = Decimal("0.001")
_UNIT_PRICE_QUANT = Decimal("0.0001")
_ZERO_MONEY = Decimal("0.00")
_ZERO_UNIT_PRICE = Decimal("0.0000")


@dataclass(slots=True, frozen=True)
class SalesMonthlySkippedLine:
    order_line_id: uuid.UUID
    order_id: uuid.UUID
    product_id: uuid.UUID
    reason: str


@dataclass(slots=True, frozen=True)
class SalesMonthlyRefreshResult:
    month_start: date
    upserted_row_count: int
    deleted_row_count: int
    skipped_lines: tuple[SalesMonthlySkippedLine, ...]
    skipped_reason: str | None = None


@dataclass(slots=True, frozen=True)
class SalesMonthlyRangeRefreshResult:
    results: tuple[SalesMonthlyRefreshResult, ...]
    refreshed_month_count: int


@dataclass(slots=True, frozen=True)
class SalesMonthlyPoint:
    month_start: date
    product_id: uuid.UUID
    product_name_snapshot: str
    product_category_snapshot: str
    quantity_sold: Decimal
    order_count: int
    revenue: Decimal
    avg_unit_price: Decimal
    source: str


@dataclass(slots=True, frozen=True)
class SalesMonthlyReadResult:
    items: tuple[SalesMonthlyPoint, ...]


# --- Health Check --- #


@dataclass(slots=True, frozen=True)
class SalesMonthlyMissingMonth:
    month_start: date
    transactional_order_count: int
    transactional_revenue: Decimal


@dataclass(slots=True, frozen=True)
class SalesMonthlyHealthResult:
    tenant_id: uuid.UUID
    window_start: date
    window_end: date
    is_healthy: bool
    missing_months: tuple[SalesMonthlyMissingMonth, ...]
    checked_month_count: int
    current_open_month: date
    data_gap_acknowledged: bool


async def check_sales_monthly_health(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    start_month: date | None = None,
    end_month: date | None = None,
) -> SalesMonthlyHealthResult:
    """Check closed-month coverage for sales_monthly.

    Compares closed-month transactional activity against month-level sales_monthly
    coverage. Returns a health report identifying any months with countable commercial
    sales but missing snapshot rows.

    The current open month is never flagged as a health failure since it uses live reads.
    """
    current_month_start = _current_month_start()

    if end_month is None:
        end_month = _previous_month_start(current_month_start)
    if start_month is None:
        start_month = end_month

    normalized_start = normalize_month_start(start_month)
    normalized_end = normalize_month_start(end_month)

    if normalized_end >= current_month_start:
        normalized_end = _previous_month_start(current_month_start)

    if normalized_end < normalized_start:
        return SalesMonthlyHealthResult(
            tenant_id=tenant_id,
            window_start=normalized_start,
            window_end=normalized_end,
            is_healthy=True,
            missing_months=(),
            checked_month_count=0,
            current_open_month=current_month_start,
            data_gap_acknowledged=False,
        )

    async with session.begin():
        await set_tenant(session, tenant_id)

        closed_months: list[date] = []
        cursor = normalized_start
        while cursor <= normalized_end:
            closed_months.append(cursor)
            cursor = _next_month_start(cursor)

        month_bounds = {
            m: _month_bounds(m) for m in closed_months
        }

        aggregate_months_with_data = {
            row.month_start for row in (
                await session.execute(
                    select(SalesMonthly.month_start)
                    .where(
                        SalesMonthly.tenant_id == tenant_id,
                        SalesMonthly.month_start >= normalized_start,
                        SalesMonthly.month_start <= normalized_end,
                    )
                    .group_by(SalesMonthly.month_start)
                )
            ).all()
        }

        transactional_counts: dict[date, tuple[int, Decimal]] = {}
        for month_start, (window_start, window_end) in month_bounds.items():
            rows = (
                await session.execute(
                    select(
                        func.count(func.distinct(Order.id)).label("order_count"),
                        func.coalesce(func.sum(OrderLine.total_amount), 0).label("revenue"),
                    )
                    .select_from(OrderLine)
                    .join(Order, OrderLine.order_id == Order.id)
                    .where(
                        Order.tenant_id == tenant_id,
                        OrderLine.tenant_id == tenant_id,
                        commercially_committed_order_filter(),
                        commercially_committed_timestamp_expr() >= window_start,
                        commercially_committed_timestamp_expr() < window_end,
                    )
                )
            ).one()
            transactional_counts[month_start] = (
                int(rows.order_count or 0),
                _to_money(rows.revenue),
            )

        missing_months: list[SalesMonthlyMissingMonth] = []
        for month_start in closed_months:
            order_count, revenue = transactional_counts.get(month_start, (0, Decimal("0.00")))
            if order_count > 0 and month_start not in aggregate_months_with_data:
                missing_months.append(
                    SalesMonthlyMissingMonth(
                        month_start=month_start,
                        transactional_order_count=order_count,
                        transactional_revenue=revenue,
                    )
                )

        return SalesMonthlyHealthResult(
            tenant_id=tenant_id,
            window_start=normalized_start,
            window_end=normalized_end,
            is_healthy=len(missing_months) == 0,
            missing_months=tuple(missing_months),
            checked_month_count=len(closed_months),
            current_open_month=current_month_start,
            data_gap_acknowledged=False,
        )


async def repair_missing_sales_monthly_months(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    missing_months: Sequence[date],
) -> SalesMonthlyRangeRefreshResult:
    """Repair only the specified missing closed months.

    This is idempotent - running repair multiple times produces the same result.
    Only processes closed months; never touches the current open month.
    """
    current_month_start = _current_month_start()
    closed_missing: list[date] = [
        m for m in missing_months
        if normalize_month_start(m) < current_month_start
    ]

    if not closed_missing:
        return SalesMonthlyRangeRefreshResult(
            results=(),
            refreshed_month_count=0,
        )

    sorted_months = sorted({normalize_month_start(month_start) for month_start in closed_missing})
    results = tuple(
        [
            await refresh_sales_monthly(session, tenant_id, month_start)
            for month_start in sorted_months
        ]
    )
    return SalesMonthlyRangeRefreshResult(
        results=results,
        refreshed_month_count=sum(1 for result in results if result.skipped_reason is None),
    )


async def backfill_sales_monthly_history(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    start_month: date,
    end_month: date | None = None,
) -> SalesMonthlyRangeRefreshResult:
    """Backfill sales_monthly for a bounded historical range.

    This never aggregates the current open month.
    Used for initial historical seeding or large-gap recovery.
    """
    current_month_start = _current_month_start()
    normalized_start = normalize_month_start(start_month)

    if end_month is None:
        end_month = _previous_month_start(current_month_start)
    normalized_end = normalize_month_start(end_month)

    if normalized_end >= current_month_start:
        normalized_end = _previous_month_start(current_month_start)

    if normalized_start > normalized_end:
        return SalesMonthlyRangeRefreshResult(
            results=(),
            refreshed_month_count=0,
        )

    return await refresh_sales_monthly_range(
        session,
        tenant_id,
        start_month=normalized_start,
        end_month=normalized_end,
    )


def normalize_month_start(value: date) -> date:
    return value.replace(day=1)


def _next_month_start(month_start: date) -> date:
    month_index = month_start.year * 12 + month_start.month
    year = month_index // 12
    month = month_index % 12 + 1
    return date(year, month, 1)


def _iter_month_starts(start_month: date, end_month: date) -> list[date]:
    month_starts: list[date] = []
    cursor = start_month
    while cursor <= end_month:
        month_starts.append(cursor)
        cursor = _next_month_start(cursor)
    return month_starts


def _month_bounds(month_start: date) -> tuple[datetime, datetime]:
    normalized_month_start = normalize_month_start(month_start)
    next_month = _next_month_start(normalized_month_start)
    return (
        datetime.combine(normalized_month_start, time.min, tzinfo=UTC),
        datetime.combine(next_month, time.min, tzinfo=UTC),
    )


def _current_month_start() -> date:
    return datetime.now(tz=UTC).date().replace(day=1)


def _previous_month_start(current_month_start: date) -> date:
    return (current_month_start - timedelta(days=1)).replace(day=1)


def _to_money(value: object | None) -> Decimal:
    return Decimal(str(value or "0")).quantize(_MONEY_QUANT, rounding=ROUND_HALF_UP)


def _to_quantity(value: object | None) -> Decimal:
    return Decimal(str(value or "0")).quantize(_QUANTITY_QUANT, rounding=ROUND_HALF_UP)


def _to_unit_price(value: object | None) -> Decimal:
    return Decimal(str(value or "0")).quantize(_UNIT_PRICE_QUANT, rounding=ROUND_HALF_UP)


def _average_unit_price(quantity_sold: Decimal, revenue: Decimal) -> Decimal:
    if quantity_sold == 0:
        return _ZERO_UNIT_PRICE
    return (revenue / quantity_sold).quantize(_UNIT_PRICE_QUANT, rounding=ROUND_HALF_UP)


async def _load_aggregate_points(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    month_start: date,
    *,
    source: str,
) -> list[SalesMonthlyPoint]:
    window_start, window_end = _month_bounds(month_start)
    analytics_timestamp = commercially_committed_timestamp_expr()
    rows = (
        await session.execute(
            select(
                OrderLine.product_id.label("product_id"),
                OrderLine.product_name_snapshot.label("product_name_snapshot"),
                OrderLine.product_category_snapshot.label("product_category_snapshot"),
                func.coalesce(func.sum(OrderLine.quantity), 0).label("quantity_sold"),
                func.count(func.distinct(Order.id)).label("order_count"),
                func.coalesce(func.sum(OrderLine.total_amount), 0).label("revenue"),
            )
            .join(Order, OrderLine.order_id == Order.id)
            .where(
                Order.tenant_id == tenant_id,
                OrderLine.tenant_id == tenant_id,
                commercially_committed_order_filter(),
                analytics_timestamp >= window_start,
                analytics_timestamp < window_end,
                OrderLine.product_name_snapshot.is_not(None),
                OrderLine.product_category_snapshot.is_not(None),
            )
            .group_by(
                OrderLine.product_id,
                OrderLine.product_name_snapshot,
                OrderLine.product_category_snapshot,
            )
            .order_by(
                OrderLine.product_name_snapshot.asc(),
                OrderLine.product_category_snapshot.asc(),
                OrderLine.product_id.asc(),
            )
        )
    ).all()
    return [
        SalesMonthlyPoint(
            month_start=normalize_month_start(month_start),
            product_id=row.product_id,
            product_name_snapshot=row.product_name_snapshot,
            product_category_snapshot=row.product_category_snapshot,
            quantity_sold=_to_quantity(row.quantity_sold),
            order_count=int(row.order_count or 0),
            revenue=_to_money(row.revenue),
            avg_unit_price=_average_unit_price(
                _to_quantity(row.quantity_sold), _to_money(row.revenue)
            ),
            source=source,
        )
        for row in rows
    ]


async def _load_skipped_lines(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    month_start: date,
) -> tuple[SalesMonthlySkippedLine, ...]:
    window_start, window_end = _month_bounds(month_start)
    analytics_timestamp = commercially_committed_timestamp_expr()
    rows = (
        await session.execute(
            select(
                OrderLine.id.label("order_line_id"),
                Order.id.label("order_id"),
                OrderLine.product_id.label("product_id"),
            )
            .join(Order, OrderLine.order_id == Order.id)
            .where(
                Order.tenant_id == tenant_id,
                OrderLine.tenant_id == tenant_id,
                commercially_committed_order_filter(),
                analytics_timestamp >= window_start,
                analytics_timestamp < window_end,
                or_(
                    OrderLine.product_name_snapshot.is_(None),
                    OrderLine.product_category_snapshot.is_(None),
                ),
            )
            .order_by(Order.id.asc(), OrderLine.line_number.asc())
        )
    ).all()
    return tuple(
        SalesMonthlySkippedLine(
            order_line_id=row.order_line_id,
            order_id=row.order_id,
            product_id=row.product_id,
            reason="missing_snapshot",
        )
        for row in rows
    )


async def refresh_sales_monthly(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    month_start: date,
) -> SalesMonthlyRefreshResult:
    normalized_month_start = normalize_month_start(month_start)
    if normalized_month_start >= _current_month_start():
        return SalesMonthlyRefreshResult(
            month_start=normalized_month_start,
            upserted_row_count=0,
            deleted_row_count=0,
            skipped_lines=(),
            skipped_reason="current_month_live_only",
        )

    async def _do_refresh() -> SalesMonthlyRefreshResult:
        await set_tenant(session, tenant_id)

        aggregate_points = await _load_aggregate_points(
            session,
            tenant_id,
            normalized_month_start,
            source="aggregated",
        )
        skipped_lines = await _load_skipped_lines(session, tenant_id, normalized_month_start)

        key_tuples = [
            (
                point.product_id,
                point.product_name_snapshot,
                point.product_category_snapshot,
            )
            for point in aggregate_points
        ]

        if key_tuples:
            delete_stmt = (
                delete(SalesMonthly)
                .where(
                    SalesMonthly.tenant_id == tenant_id,
                    SalesMonthly.month_start == normalized_month_start,
                )
                .where(
                    tuple_(
                        SalesMonthly.product_id,
                        SalesMonthly.product_name_snapshot,
                        SalesMonthly.product_category_snapshot,
                    ).not_in(key_tuples)
                )
            )
        else:
            delete_stmt = delete(SalesMonthly).where(
                SalesMonthly.tenant_id == tenant_id,
                SalesMonthly.month_start == normalized_month_start,
            )
        delete_result = await session.execute(delete_stmt)
        deleted_row_count = delete_result.rowcount or 0

        if aggregate_points:
            insert_stmt = pg_insert(SalesMonthly).values(
                [
                    {
                        "tenant_id": tenant_id,
                        "month_start": point.month_start,
                        "product_id": point.product_id,
                        "product_name_snapshot": point.product_name_snapshot,
                        "product_category_snapshot": point.product_category_snapshot,
                        "quantity_sold": point.quantity_sold,
                        "order_count": point.order_count,
                        "revenue": point.revenue,
                        "avg_unit_price": point.avg_unit_price,
                    }
                    for point in aggregate_points
                ]
            )
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[
                    SalesMonthly.tenant_id,
                    SalesMonthly.month_start,
                    SalesMonthly.product_id,
                    SalesMonthly.product_name_snapshot,
                    SalesMonthly.product_category_snapshot,
                ],
                set_={
                    "quantity_sold": insert_stmt.excluded.quantity_sold,
                    "order_count": insert_stmt.excluded.order_count,
                    "revenue": insert_stmt.excluded.revenue,
                    "avg_unit_price": insert_stmt.excluded.avg_unit_price,
                    "updated_at": func.now(),
                },
            )
            await session.execute(insert_stmt)

        return SalesMonthlyRefreshResult(
            month_start=normalized_month_start,
            upserted_row_count=len(aggregate_points),
            deleted_row_count=deleted_row_count,
            skipped_lines=skipped_lines,
        )

    if session.in_transaction():
        return await _do_refresh()
    async with session.begin():
        return await _do_refresh()


async def refresh_sales_monthly_range(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    start_month: date,
    end_month: date,
) -> SalesMonthlyRangeRefreshResult:
    normalized_start_month = normalize_month_start(start_month)
    normalized_end_month = normalize_month_start(end_month)
    if normalized_end_month < normalized_start_month:
        raise ValueError("end_month must be on or after start_month")

    results = tuple(
        [
            await refresh_sales_monthly(session, tenant_id, month_start)
            for month_start in _iter_month_starts(normalized_start_month, normalized_end_month)
        ]
    )
    return SalesMonthlyRangeRefreshResult(
        results=results,
        refreshed_month_count=sum(1 for result in results if result.skipped_reason is None),
    )


async def read_sales_monthly_range(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    start_month: date,
    end_month: date,
) -> SalesMonthlyReadResult:
    normalized_start_month = normalize_month_start(start_month)
    normalized_end_month = normalize_month_start(end_month)
    if normalized_end_month < normalized_start_month:
        raise ValueError("end_month must be on or after start_month")

    async def _load_points() -> SalesMonthlyReadResult:
        current_month_start = _current_month_start()
        items: list[SalesMonthlyPoint] = []

        if normalized_start_month < current_month_start:
            if normalized_end_month >= current_month_start:
                closed_month_end = current_month_start
            else:
                closed_month_end = _next_month_start(normalized_end_month)
            table_rows = (
                await session.execute(
                    select(SalesMonthly)
                    .where(
                        SalesMonthly.tenant_id == tenant_id,
                        SalesMonthly.month_start >= normalized_start_month,
                        SalesMonthly.month_start < closed_month_end,
                    )
                    .order_by(
                        SalesMonthly.month_start.asc(),
                        SalesMonthly.product_name_snapshot.asc(),
                        SalesMonthly.product_id.asc(),
                    )
                )
            ).scalars().all()
            closed_months: list[date] = []
            cursor = normalized_start_month
            while cursor < closed_month_end:
                closed_months.append(cursor)
                cursor = _next_month_start(cursor)

            months_with_snapshots = {row.month_start for row in table_rows}
            items.extend(
                SalesMonthlyPoint(
                    month_start=row.month_start,
                    product_id=row.product_id,
                    product_name_snapshot=row.product_name_snapshot,
                    product_category_snapshot=row.product_category_snapshot,
                    quantity_sold=_to_quantity(row.quantity_sold),
                    order_count=row.order_count,
                    revenue=_to_money(row.revenue),
                    avg_unit_price=_to_unit_price(row.avg_unit_price),
                    source="aggregated",
                )
                for row in table_rows
            )

            for month_start in closed_months:
                if month_start in months_with_snapshots:
                    continue
                items.extend(
                    await _load_aggregate_points(
                        session,
                        tenant_id,
                        month_start,
                        source="aggregated",
                    )
                )

        if normalized_start_month <= current_month_start <= normalized_end_month:
            items.extend(
                await _load_aggregate_points(
                    session,
                    tenant_id,
                    current_month_start,
                    source="live",
                )
            )

        return SalesMonthlyReadResult(
            items=tuple(
                sorted(
                    items,
                    key=lambda item: (
                        item.month_start,
                        item.product_name_snapshot,
                        str(item.product_id),
                    ),
                )
            )
        )

    if session.in_transaction():
        await set_tenant(session, tenant_id)
        return await _load_points()

    async with session.begin():
        await set_tenant(session, tenant_id)
        return await _load_points()
