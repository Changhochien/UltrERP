"""Tests for dashboard revenue summary service."""

from __future__ import annotations

import uuid
from datetime import timedelta
from decimal import Decimal

import pytest

from common.time import today as get_today
from domains.dashboard.services import get_revenue_summary
from tests.domains.orders._helpers import FakeAsyncSession

TENANT = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _queue_revenue(session: FakeAsyncSession, today_sum: object, yesterday_sum: object) -> None:
    """Queue results: set_tenant(None) + today SUM + yesterday SUM."""
    session.queue_scalar(None)  # set_tenant
    session.queue_scalar(today_sum)  # today revenue
    session.queue_scalar(yesterday_sum)  # yesterday revenue


@pytest.mark.asyncio
async def test_revenue_both_days() -> None:
    session = FakeAsyncSession()
    _queue_revenue(session, Decimal("10000.00"), Decimal("8000.00"))

    result = await get_revenue_summary(session, TENANT)

    assert result.today_revenue == Decimal("10000.00")
    assert result.yesterday_revenue == Decimal("8000.00")
    assert result.change_percent == Decimal("25.0")
    today = get_today()
    assert result.today_date == today
    assert result.yesterday_date == today - timedelta(days=1)


@pytest.mark.asyncio
async def test_revenue_zero_yesterday_positive_today() -> None:
    session = FakeAsyncSession()
    _queue_revenue(session, Decimal("5000.00"), Decimal("0"))

    result = await get_revenue_summary(session, TENANT)

    assert result.today_revenue == Decimal("5000.00")
    assert result.yesterday_revenue == Decimal("0")
    assert result.change_percent == Decimal("100.0")


@pytest.mark.asyncio
async def test_revenue_zero_both_days() -> None:
    session = FakeAsyncSession()
    _queue_revenue(session, Decimal("0"), Decimal("0"))

    result = await get_revenue_summary(session, TENANT)

    assert result.today_revenue == Decimal("0")
    assert result.yesterday_revenue == Decimal("0")
    assert result.change_percent is None


@pytest.mark.asyncio
async def test_revenue_negative_change() -> None:
    session = FakeAsyncSession()
    _queue_revenue(session, Decimal("3000.00"), Decimal("10000.00"))

    result = await get_revenue_summary(session, TENANT)

    assert result.today_revenue == Decimal("3000.00")
    assert result.yesterday_revenue == Decimal("10000.00")
    assert result.change_percent == Decimal("-70.0")


@pytest.mark.asyncio
async def test_revenue_equal_days() -> None:
    session = FakeAsyncSession()
    _queue_revenue(session, Decimal("5000.00"), Decimal("5000.00"))

    result = await get_revenue_summary(session, TENANT)

    assert result.change_percent == Decimal("0.0")


@pytest.mark.asyncio
async def test_revenue_route_returns_json() -> None:
    """Integration-style test through HTTP."""
    from tests.domains.orders._helpers import http_get, setup_session, teardown_session

    session = FakeAsyncSession()
    _queue_revenue(session, Decimal("1234.56"), Decimal("1000.00"))

    prev = setup_session(session)
    try:
        resp = await http_get("/api/v1/dashboard/revenue-summary")
        assert resp.status_code == 200
        body = resp.json()
        assert body["today_revenue"] == "1234.56"
        assert body["yesterday_revenue"] == "1000.00"
        assert body["change_percent"] == "23.5"
        assert "today_date" in body
        assert "yesterday_date" in body
    finally:
        teardown_session(prev)
