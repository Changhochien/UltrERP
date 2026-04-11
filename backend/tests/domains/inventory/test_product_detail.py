"""Tests for GET /api/v1/inventory/products/{product_id} — Story 4.2."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

from httpx import ASGITransport, AsyncClient

from app.main import app
from common.database import get_db
from tests.domains.orders._helpers import auth_header

# ── Fake objects ──────────────────────────────────────────────


class FakeProduct:
    def __init__(
        self,
        *,
        pid: uuid.UUID | None = None,
        code: str = "TST-001",
        name: str = "Test Product",
        category: str | None = "Electronics",
        status: str = "active",
    ):
        self.id = pid or uuid.uuid4()
        self.tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        self.code = code
        self.name = name
        self.category = category
        self.status = status
        self.legacy_master_snapshot = {"legacy_code": code}


class FakeStockRow:
    """Simulates a row returned from the stock + warehouse join query."""

    def __init__(
        self,
        *,
        warehouse_id: uuid.UUID | None = None,
        warehouse_name: str = "Main",
        quantity: int = 50,
        reorder_point: int = 20,
        last_adjusted: datetime | None = None,
    ):
        self.stock_id = uuid.uuid4()
        self.warehouse_id = warehouse_id or uuid.uuid4()
        self.warehouse_name = warehouse_name
        self.quantity = quantity
        self.reorder_point = reorder_point
        self.last_adjusted = last_adjusted or datetime.now(tz=UTC)


class FakeAdjustment:
    def __init__(
        self,
        *,
        quantity_change: int = 10,
        reason_code: str = "received",
        actor_id: str = "user1",
        notes: str | None = None,
    ):
        self.id = uuid.uuid4()
        self.created_at = datetime.now(tz=UTC)
        self.quantity_change = quantity_change
        self.reason_code = type("RC", (), {"value": reason_code})()
        self.actor_id = actor_id
        self.notes = notes


class FakeResult:
    """Handles scalar_one_or_none for product lookups."""

    def __init__(self, obj: object | None):
        self._obj = obj

    def scalar_one_or_none(self) -> object | None:
        return self._obj


class FakeRowsResult:
    """Handles .all() for join queries returning row tuples."""

    def __init__(self, rows: list[object]):
        self._rows = rows

    def all(self) -> list:
        return self._rows


class FakeScalarsResult:
    """Handles .scalars().all() for ORM-model queries."""

    def __init__(self, objs: list[object]):
        self._objs = objs

    def scalars(self) -> FakeScalars:
        return FakeScalars(self._objs)


class FakeScalars:
    def __init__(self, objs: list[object]):
        self._objs = objs

    def all(self) -> list:
        return self._objs


class FakeAsyncSession:
    """Fake session queuing result returns in order."""

    def __init__(self) -> None:
        self._execute_results: list[object] = []
        self._idx = 0
        self.added: list[object] = []

    def add(self, obj: object) -> None:
        self.added.append(obj)

    def add_all(self, objs: list[object]) -> None:
        self.added.extend(objs)

    async def execute(self, _stmt: object) -> object:
        if self._idx < len(self._execute_results):
            result = self._execute_results[self._idx]
            self._idx += 1
            return result
        return FakeResult(None)

    async def flush(self) -> None:
        pass

    async def commit(self) -> None:
        pass

    def queue_scalar(self, obj: object | None) -> None:
        """Queue a result that supports .scalar_one_or_none()."""
        self._execute_results.append(FakeResult(obj))

    def queue_rows(self, rows: list[object]) -> None:
        """Queue a result that supports .all() for row tuples."""
        self._execute_results.append(FakeRowsResult(rows))

    def queue_scalars_list(self, objs: list[object]) -> None:
        """Queue a result that supports .scalars().all()."""
        self._execute_results.append(FakeScalarsResult(objs))


# ── Helper ────────────────────────────────────────────────────

_MISSING = object()


def _setup(session: FakeAsyncSession) -> Any:
    async def _override() -> AsyncGenerator[FakeAsyncSession, None]:
        yield session

    previous = app.dependency_overrides.get(get_db, _MISSING)
    app.dependency_overrides[get_db] = _override
    return previous


def _teardown(previous: Any) -> None:
    if previous is _MISSING:
        app.dependency_overrides.pop(get_db, None)
    else:
        app.dependency_overrides[get_db] = previous


async def _get(path: str, **params: Any) -> Any:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", headers=auth_header()) as c:
        return await c.get(path, params=params)


# ── Tests ─────────────────────────────────────────────────────


async def test_product_not_found() -> None:
    session = FakeAsyncSession()
    session.queue_scalar(None)  # product lookup → None
    prev = _setup(session)
    try:
        resp = await _get(f"/api/v1/inventory/products/{uuid.uuid4()}")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Product not found"
    finally:
        _teardown(prev)


async def test_product_detail_multi_warehouse() -> None:
    product = FakeProduct()
    wh_a_id = uuid.uuid4()
    wh_b_id = uuid.uuid4()
    stock_a = FakeStockRow(
        warehouse_id=wh_a_id,
        warehouse_name="Alpha",
        quantity=50,
        reorder_point=20,
    )
    stock_b = FakeStockRow(
        warehouse_id=wh_b_id,
        warehouse_name="Beta",
        quantity=10,
        reorder_point=15,
    )
    adj1 = FakeAdjustment(quantity_change=50, reason_code="received", actor_id="u1")
    adj2 = FakeAdjustment(quantity_change=-5, reason_code="damaged", actor_id="u2")

    session = FakeAsyncSession()
    session.queue_scalar(product)  # product lookup
    session.queue_rows([stock_a, stock_b])  # stock join query
    session.queue_scalars_list([adj1, adj2])  # adjustment history

    prev = _setup(session)
    try:
        resp = await _get(f"/api/v1/inventory/products/{product.id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == str(product.id)
        assert body["code"] == "TST-001"
        assert body["name"] == "Test Product"
        assert body["category"] == "Electronics"
        assert body["status"] == "active"
        assert body["legacy_master_snapshot"]["legacy_code"] == "TST-001"
        assert body["total_stock"] == 60
        assert len(body["warehouses"]) == 2
        assert len(body["adjustment_history"]) == 2
    finally:
        _teardown(prev)


async def test_warehouse_stock_fields() -> None:
    product = FakeProduct()
    stock = FakeStockRow(
        warehouse_name="Main",
        quantity=50,
        reorder_point=20,
    )

    session = FakeAsyncSession()
    session.queue_scalar(product)
    session.queue_rows([stock])
    session.queue_scalars_list([])

    prev = _setup(session)
    try:
        resp = await _get(f"/api/v1/inventory/products/{product.id}")
        body = resp.json()
        wh = body["warehouses"][0]
        assert wh["warehouse_name"] == "Main"
        assert wh["current_stock"] == 50
        assert wh["reorder_point"] == 20
        assert wh["is_below_reorder"] is False
        assert wh["last_adjusted"] is not None
    finally:
        _teardown(prev)


async def test_reorder_indicator_below() -> None:
    product = FakeProduct()
    stock = FakeStockRow(quantity=10, reorder_point=15)

    session = FakeAsyncSession()
    session.queue_scalar(product)
    session.queue_rows([stock])
    session.queue_scalars_list([])

    prev = _setup(session)
    try:
        resp = await _get(f"/api/v1/inventory/products/{product.id}")
        wh = resp.json()["warehouses"][0]
        assert wh["is_below_reorder"] is True
    finally:
        _teardown(prev)


async def test_reorder_indicator_at_point() -> None:
    """Stock equal to reorder_point is NOT below."""
    product = FakeProduct()
    stock = FakeStockRow(quantity=20, reorder_point=20)

    session = FakeAsyncSession()
    session.queue_scalar(product)
    session.queue_rows([stock])
    session.queue_scalars_list([])

    prev = _setup(session)
    try:
        resp = await _get(f"/api/v1/inventory/products/{product.id}")
        wh = resp.json()["warehouses"][0]
        assert wh["is_below_reorder"] is False
    finally:
        _teardown(prev)


async def test_reorder_zero_reorder_point() -> None:
    """reorder_point=0 should never trigger is_below_reorder."""
    product = FakeProduct()
    stock = FakeStockRow(quantity=0, reorder_point=0)

    session = FakeAsyncSession()
    session.queue_scalar(product)
    session.queue_rows([stock])
    session.queue_scalars_list([])

    prev = _setup(session)
    try:
        resp = await _get(f"/api/v1/inventory/products/{product.id}")
        wh = resp.json()["warehouses"][0]
        assert wh["is_below_reorder"] is False
    finally:
        _teardown(prev)


async def test_no_stock_records() -> None:
    product = FakeProduct()

    session = FakeAsyncSession()
    session.queue_scalar(product)
    session.queue_rows([])  # no stock
    session.queue_scalars_list([])  # no adjustments

    prev = _setup(session)
    try:
        resp = await _get(f"/api/v1/inventory/products/{product.id}")
        body = resp.json()
        assert body["total_stock"] == 0
        assert body["warehouses"] == []
        assert body["adjustment_history"] == []
    finally:
        _teardown(prev)


async def test_adjustment_history_fields() -> None:
    product = FakeProduct()
    adj = FakeAdjustment(
        quantity_change=-5,
        reason_code="damaged",
        actor_id="user1",
        notes="Broken items",
    )

    session = FakeAsyncSession()
    session.queue_scalar(product)
    session.queue_rows([])
    session.queue_scalars_list([adj])

    prev = _setup(session)
    try:
        resp = await _get(f"/api/v1/inventory/products/{product.id}")
        history = resp.json()["adjustment_history"]
        assert len(history) == 1
        h = history[0]
        assert h["quantity_change"] == -5
        assert h["reason_code"] == "damaged"
        assert h["actor_id"] == "user1"
        assert h["notes"] == "Broken items"
        assert "id" in h
        assert "created_at" in h
    finally:
        _teardown(prev)


async def test_history_limit_query_param() -> None:
    product = FakeProduct()

    session = FakeAsyncSession()
    session.queue_scalar(product)
    session.queue_rows([])
    session.queue_scalars_list([])

    prev = _setup(session)
    try:
        resp = await _get(
            f"/api/v1/inventory/products/{product.id}",
            history_limit=1,
        )
        assert resp.status_code == 200
    finally:
        _teardown(prev)


async def test_history_offset_query_param() -> None:
    product = FakeProduct()

    session = FakeAsyncSession()
    session.queue_scalar(product)
    session.queue_rows([])
    session.queue_scalars_list([])

    prev = _setup(session)
    try:
        resp = await _get(
            f"/api/v1/inventory/products/{product.id}",
            history_limit=10,
            history_offset=5,
        )
        assert resp.status_code == 200
    finally:
        _teardown(prev)


async def test_invalid_uuid_returns_422() -> None:
    """Non-UUID product_id should return 422, not match /products/search."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", headers=auth_header()) as c:
        resp = await c.get("/api/v1/inventory/products/not-a-uuid")
    assert resp.status_code == 422


async def test_history_limit_zero_returns_422() -> None:
    """history_limit=0 violates ge=1 constraint."""
    product_id = uuid.uuid4()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", headers=auth_header()) as c:
        resp = await c.get(
            f"/api/v1/inventory/products/{product_id}",
            params={"history_limit": 0},
        )
    assert resp.status_code == 422


async def test_history_limit_exceeds_max_returns_422() -> None:
    """history_limit=501 violates le=500 constraint."""
    product_id = uuid.uuid4()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", headers=auth_header()) as c:
        resp = await c.get(
            f"/api/v1/inventory/products/{product_id}",
            params={"history_limit": 501},
        )
    assert resp.status_code == 422


async def test_history_offset_negative_returns_422() -> None:
    """history_offset=-1 violates ge=0 constraint."""
    product_id = uuid.uuid4()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", headers=auth_header()) as c:
        resp = await c.get(
            f"/api/v1/inventory/products/{product_id}",
            params={"history_offset": -1},
        )
    assert resp.status_code == 422
