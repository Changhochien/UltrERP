"""Tests for dashboard top-products service."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from sqlalchemy.dialects import postgresql

from domains.dashboard.services import get_top_products
from tests.domains.orders._helpers import FakeAsyncSession, FakeResult

TENANT = uuid.UUID("00000000-0000-0000-0000-000000000001")


class _Row:
    """Fake row returned by result.all() — tuple-like access via __getitem__."""

    def __init__(self, product_id: uuid.UUID, name: str, qty: Decimal, rev: Decimal):
        self._data = (product_id, name, qty, rev)

    def __getitem__(self, idx: int) -> object:
        return self._data[idx]


def _queue_top_products(session: FakeAsyncSession, rows: list[_Row]) -> None:
    """Queue: set_tenant(None) + query result rows."""
    session.queue_scalar(None)  # set_tenant
    session._execute_results.append(FakeResult(items=rows))


@pytest.mark.asyncio
async def test_top_products_returns_sorted() -> None:
    pid1, pid2, pid3 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    rows = [
        _Row(pid1, "Widget A", Decimal("100.000"), Decimal("50000.00")),
        _Row(pid2, "Widget B", Decimal("80.000"), Decimal("40000.00")),
        _Row(pid3, "Widget C", Decimal("50.000"), Decimal("25000.00")),
    ]
    session = FakeAsyncSession()
    _queue_top_products(session, rows)

    result = await get_top_products(session, TENANT, period="day")

    assert result.period == "day"
    assert len(result.items) == 3
    assert result.items[0].product_name == "Widget A"
    assert result.items[0].quantity_sold == Decimal("100.000")
    assert result.items[0].revenue == Decimal("50000.00")
    assert result.items[1].product_name == "Widget B"
    assert result.items[2].product_name == "Widget C"


@pytest.mark.asyncio
async def test_top_products_weekly_period() -> None:
    session = FakeAsyncSession()
    _queue_top_products(session, [])

    result = await get_top_products(session, TENANT, period="week")

    assert result.period == "week"
    diff = (result.end_date - result.start_date).days
    assert diff == 6  # 7-day window inclusive


@pytest.mark.asyncio
async def test_top_products_empty() -> None:
    session = FakeAsyncSession()
    _queue_top_products(session, [])

    result = await get_top_products(session, TENANT, period="day")

    assert result.items == []


@pytest.mark.asyncio
async def test_top_products_uses_confirmation_timestamp_window() -> None:
    session = FakeAsyncSession()
    _queue_top_products(session, [])

    await get_top_products(session, TENANT, period="day")

    executed_sql = "\n".join(
        str(statement.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
        for statement, _params in session.executed_statements
        if hasattr(statement, "compile")
    )
    normalized_sql = executed_sql.lower()

    assert "coalesce(orders.confirmed_at, orders.created_at)" in normalized_sql
    assert "product.tenant_id = '00000000-0000-0000-0000-000000000001'" in normalized_sql
    assert "order_lines.tenant_id = '00000000-0000-0000-0000-000000000001'" in normalized_sql
    assert "orders.tenant_id = '00000000-0000-0000-0000-000000000001'" in normalized_sql
    assert "'confirmed'" in normalized_sql
    assert "'shipped'" in normalized_sql
    assert "'fulfilled'" in normalized_sql
    assert "'pending'" not in normalized_sql


@pytest.mark.asyncio
async def test_top_products_route_returns_json() -> None:
    """HTTP integration test through the route."""
    from tests.domains.orders._helpers import http_get, setup_session, teardown_session

    pid = uuid.uuid4()
    rows = [_Row(pid, "SuperWidget", Decimal("42.000"), Decimal("12600.00"))]

    session = FakeAsyncSession()
    _queue_top_products(session, rows)

    prev = setup_session(session)
    try:
        resp = await http_get("/api/v1/dashboard/top-products?period=day")
        assert resp.status_code == 200
        body = resp.json()
        assert body["period"] == "day"
        assert len(body["items"]) == 1
        assert body["items"][0]["product_name"] == "SuperWidget"
        assert body["items"][0]["quantity_sold"] == "42.000"
        assert body["items"][0]["revenue"] == "12600.00"
    finally:
        teardown_session(prev)


@pytest.mark.asyncio
async def test_top_products_invalid_period_returns_422() -> None:
    """Invalid period value should return 422."""
    from tests.domains.orders._helpers import http_get, setup_session, teardown_session

    session = FakeAsyncSession()
    prev = setup_session(session)
    try:
        resp = await http_get("/api/v1/dashboard/top-products?period=month")
        assert resp.status_code == 422
    finally:
        teardown_session(prev)
