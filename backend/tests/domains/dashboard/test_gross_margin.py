"""Tests for gross margin dashboard service and route."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest

from domains.dashboard.services import get_gross_margin
from tests.domains.orders._helpers import FakeAsyncSession, http_get, setup_session, teardown_session

TENANT = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _queue_period(
    session: FakeAsyncSession,
    *,
    revenue: Decimal,
    cogs: Decimal,
    line_count: int,
    priced_line_count: int,
) -> None:
    session.queue_scalar(revenue)
    session.queue_scalar(cogs)
    session.queue_scalar(line_count)
    session.queue_scalar(priced_line_count)


@pytest.mark.asyncio
async def test_gross_margin_available_with_previous_period() -> None:
    session = FakeAsyncSession()
    session.queue_scalar(None)
    _queue_period(
        session,
        revenue=Decimal("1000.00"),
        cogs=Decimal("600.00"),
        line_count=2,
        priced_line_count=2,
    )
    _queue_period(
        session,
        revenue=Decimal("800.00"),
        cogs=Decimal("400.00"),
        line_count=2,
        priced_line_count=2,
    )

    result = await get_gross_margin(session, TENANT)

    assert result.available is True
    assert result.gross_margin == Decimal("400.00")
    assert result.gross_margin_percent == Decimal("40.0")
    assert result.margin_percent == Decimal("40.0")
    assert result.previous_period.available is True
    assert result.previous_period.gross_margin_percent == Decimal("50.0")


@pytest.mark.asyncio
async def test_gross_margin_marks_partial_costs_unavailable() -> None:
    session = FakeAsyncSession()
    session.queue_scalar(None)
    _queue_period(
        session,
        revenue=Decimal("1000.00"),
        cogs=Decimal("300.00"),
        line_count=2,
        priced_line_count=1,
    )
    _queue_period(
        session,
        revenue=Decimal("0.00"),
        cogs=Decimal("0.00"),
        line_count=0,
        priced_line_count=0,
    )

    result = await get_gross_margin(session, TENANT)

    assert result.available is False
    assert result.gross_margin == Decimal("700.00")
    assert result.gross_margin_percent == Decimal("70.0")
    assert result.previous_period.available is False
    assert result.previous_period.gross_margin_percent is None


@pytest.mark.asyncio
async def test_gross_margin_route_returns_contract_fields() -> None:
    session = FakeAsyncSession()
    session.queue_scalar(None)
    _queue_period(
        session,
        revenue=Decimal("1000.00"),
        cogs=Decimal("600.00"),
        line_count=2,
        priced_line_count=2,
    )
    _queue_period(
        session,
        revenue=Decimal("800.00"),
        cogs=Decimal("400.00"),
        line_count=2,
        priced_line_count=2,
    )

    prev = setup_session(session)
    try:
        resp = await http_get("/api/v1/dashboard/gross-margin")
        assert resp.status_code == 200
        body = resp.json()
        assert body["available"] is True
        assert body["gross_margin"] == "400.00"
        assert body["gross_margin_percent"] == "40.0"
        assert body["margin_percent"] == "40.0"
        assert body["previous_period"] == {
            "available": True,
            "gross_margin_percent": "50.0",
        }
    finally:
        teardown_session(prev)