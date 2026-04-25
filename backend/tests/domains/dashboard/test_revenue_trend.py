"""Tests for dashboard revenue trend pagination service."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest
from freezegun import freeze_time

from domains.dashboard.services import get_revenue_trend, get_revenue_trend_series
from tests.domains.orders._helpers import FakeAsyncSession

TENANT = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _trend_row(row_date: date, revenue: str, order_count: int = 1) -> SimpleNamespace:
    return SimpleNamespace(
        date=row_date,
        revenue=Decimal(revenue),
        order_count=order_count,
    )


@pytest.mark.asyncio
@freeze_time("2026-04-09")
async def test_revenue_trend_day_before_pages_backward() -> None:
    session = FakeAsyncSession()
    session.queue_scalar(None)  # set_tenant
    session.queue_rows([
        _trend_row(date(2026, 3, 8), "100.00", 1),
        _trend_row(date(2026, 3, 9), "150.00", 2),
    ])
    session.queue_rows([SimpleNamespace(found=True)])

    result = await get_revenue_trend(
        session,
        TENANT,
        granularity="day",
        days=30,
        before="2026-03-10",
    )

    assert [item.date for item in result.items] == [date(2026, 3, 8), date(2026, 3, 9)]
    assert [item.revenue for item in result.items] == [Decimal("100.00"), Decimal("150.00")]
    assert result.has_more is True


@pytest.mark.asyncio
@freeze_time("2026-04-09")
async def test_revenue_trend_week_before_pages_backward() -> None:
    session = FakeAsyncSession()
    session.queue_scalar(None)  # set_tenant
    session.queue_rows([
        _trend_row(date(2025, 12, 15), "500.00", 3),
        _trend_row(date(2025, 12, 22), "650.00", 4),
    ])
    session.queue_rows([SimpleNamespace(found=True)])

    result = await get_revenue_trend(
        session,
        TENANT,
        granularity="week",
        months=3,
        before="2026-01-05",
    )

    assert [item.date for item in result.items] == [date(2025, 12, 15), date(2025, 12, 22)]
    assert [item.order_count for item in result.items] == [3, 4]
    assert result.has_more is True


@pytest.mark.asyncio
async def test_revenue_trend_series_returns_dense_monthly_points() -> None:
    session = FakeAsyncSession()
    session.queue_rows([
        SimpleNamespace(month=datetime(2026, 1, 1, tzinfo=UTC), revenue=Decimal("100.00")),
        SimpleNamespace(month=datetime(2026, 3, 1, tzinfo=UTC), revenue=Decimal("250.00")),
    ])

    result = await get_revenue_trend_series(
        session,
        TENANT,
        granularity="month",
        start_date="2026-01",
        end_date="2026-03",
    )

    assert [point["bucket_start"] for point in result["points"]] == [
        "2026-01",
        "2026-02",
        "2026-03",
    ]
    assert [point["value"] for point in result["points"]] == [100.0, 0.0, 250.0]
    assert [point["is_zero_filled"] for point in result["points"]] == [False, True, False]
    assert result["range"]["bucket"] == "month"
    assert result["range"]["timezone"] == "Asia/Taipei"