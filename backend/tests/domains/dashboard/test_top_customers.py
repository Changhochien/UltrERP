"""Tests for dashboard top-customers service."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from freezegun import freeze_time

from domains.dashboard.services import get_top_customers
from tests.domains.orders._helpers import FakeAsyncSession

TENANT = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _make_customer_row(
    customer_id: uuid.UUID,
    company_name: str,
    total_revenue: Decimal,
    invoice_count: int,
    last_invoice_date: date,
) -> tuple:
    """Make a fake row matching the select output."""
    return (customer_id, company_name, total_revenue, invoice_count, last_invoice_date)


@pytest.mark.asyncio
@freeze_time("2026-04-09")
async def test_top_customers_returns_sorted_by_revenue() -> None:
    """Returns top N customers sorted by total_revenue descending."""
    session = FakeAsyncSession()
    c1 = uuid.uuid4()
    c2 = uuid.uuid4()
    today = datetime.now(UTC).date()
    session.queue_scalar(None)  # set_tenant
    session.queue_rows([
        _make_customer_row(c1, "Acme Corp", Decimal("50000.00"), 10, today),
        _make_customer_row(c2, "Beta LLC", Decimal("30000.00"), 5, today),
    ])

    result = await get_top_customers(session, TENANT, period="month", limit=10)

    assert len(result.customers) == 2
    assert result.customers[0].company_name == "Acme Corp"
    assert result.customers[0].total_revenue == Decimal("50000.00")
    assert result.customers[1].company_name == "Beta LLC"
    assert result.customers[1].total_revenue == Decimal("30000.00")
    assert result.period == "month"
    assert result.start_date == date(today.year, today.month, 1)
    assert result.end_date >= result.start_date


@pytest.mark.asyncio
@freeze_time("2026-04-09")
async def test_top_customers_respects_limit() -> None:
    """Results are limited to the limit parameter."""
    session = FakeAsyncSession()
    today = datetime.now(UTC).date()
    c = uuid.uuid4()
    session.queue_scalar(None)  # set_tenant
    session.queue_rows([
        _make_customer_row(c, "Single Corp", Decimal("10000.00"), 1, today),
    ])

    result = await get_top_customers(session, TENANT, period="month", limit=1)

    assert len(result.customers) == 1


@pytest.mark.asyncio
@freeze_time("2026-04-09")
async def test_top_customers_empty_result() -> None:
    """No invoices returns empty customers array."""
    session = FakeAsyncSession()
    session.queue_scalar(None)  # set_tenant
    session.queue_rows([])

    result = await get_top_customers(session, TENANT, period="month")

    assert result.customers == []
    assert result.period == "month"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("period", "anchor_date", "expected_start", "expected_end"),
    [
        ("month", date(2025, 11, 18), date(2025, 11, 1), date(2025, 11, 30)),
        ("quarter", date(2025, 11, 18), date(2025, 10, 1), date(2025, 12, 31)),
        ("year", date(2025, 11, 18), date(2025, 1, 1), date(2025, 12, 31)),
    ],
)
async def test_top_customers_uses_anchor_date_for_period_boundaries(
    period: str,
    anchor_date: date,
    expected_start: date,
    expected_end: date,
) -> None:
    session = FakeAsyncSession()
    session.queue_scalar(None)  # set_tenant
    session.queue_rows([])

    result = await get_top_customers(session, TENANT, period=period, anchor_date=anchor_date)

    assert result.start_date == expected_start
    assert result.end_date == expected_end


@pytest.mark.asyncio
@freeze_time("2026-04-09")
async def test_top_customers_route_returns_json() -> None:
    """Integration-style test through HTTP."""
    from tests.domains.orders._helpers import http_get, setup_session, teardown_session

    session = FakeAsyncSession()
    today = datetime.now(UTC).date()
    c1 = uuid.uuid4()
    c2 = uuid.uuid4()
    session.queue_scalar(None)  # set_tenant
    session.queue_rows([
        _make_customer_row(c1, "Acme Corp", Decimal("50000.00"), 10, today),
        _make_customer_row(c2, "Beta LLC", Decimal("30000.00"), 5, today),
    ])

    prev = setup_session(session)
    try:
        resp = await http_get("/api/v1/dashboard/top-customers?period=month&limit=10")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["customers"]) == 2
        assert body["customers"][0]["company_name"] == "Acme Corp"
        assert body["customers"][0]["total_revenue"] == "50000.00"
        assert body["period"] == "month"
    finally:
        teardown_session(prev)
