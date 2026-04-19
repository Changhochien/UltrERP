from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

from httpx import ASGITransport, AsyncClient

from app.main import app
from common.database import get_db
from domains.inventory import routes as inventory_routes
from tests.domains.orders._helpers import auth_header


class FakeScalarResult:
    def __init__(
        self,
        *,
        scalar_value: object | None = None,
        mapping_items: list[dict[str, object]] | None = None,
        mapping_value: dict[str, object] | None = None,
    ) -> None:
        self._scalar_value = scalar_value
        self._mapping_items = mapping_items or []
        self._mapping_value = mapping_value

    def scalar(self) -> int:
        return int(self._scalar_value or 0)

    def scalar_one_or_none(self) -> object | None:
        return self._scalar_value

    def mappings(self) -> FakeMappingResult:
        return FakeMappingResult(self._mapping_items, self._mapping_value)


class FakeMappingResult:
    def __init__(
        self,
        items: list[dict[str, object]],
        value: dict[str, object] | None,
    ) -> None:
        self._items = items
        self._value = value

    def all(self) -> list[dict[str, object]]:
        return list(self._items)

    def one_or_none(self) -> dict[str, object] | None:
        return self._value


class FakeAsyncSession:
    def __init__(self) -> None:
        self._execute_results: list[FakeScalarResult] = []
        self.commit_calls = 0

    async def execute(self, _statement: object, params: object = None) -> FakeScalarResult:
        if self._execute_results:
            return self._execute_results.pop(0)
        return FakeScalarResult()

    async def commit(self) -> None:
        self.commit_calls += 1

    async def rollback(self) -> None:
        pass

    def queue_scalar(self, value: object | None) -> None:
        self._execute_results.append(FakeScalarResult(scalar_value=value))

    def queue_count(self, value: int) -> None:
        self._execute_results.append(FakeScalarResult(scalar_value=value))

    def queue_mapping_items(self, items: list[dict[str, object]]) -> None:
        self._execute_results.append(FakeScalarResult(mapping_items=items))

    def queue_mapping_value(self, value: dict[str, object] | None) -> None:
        self._execute_results.append(FakeScalarResult(mapping_value=value))


_MISSING_OVERRIDE = object()


def _setup(session: FakeAsyncSession) -> Any:
    previous = app.dependency_overrides.get(get_db, _MISSING_OVERRIDE)

    async def override() -> AsyncGenerator[FakeAsyncSession, None]:
        yield session

    app.dependency_overrides[get_db] = override
    return previous


def _teardown(previous: Any) -> None:
    if previous is _MISSING_OVERRIDE:
        app.dependency_overrides.pop(get_db, None)
    else:
        app.dependency_overrides[get_db] = previous


def _transfer_row(transfer_id: uuid.UUID | None = None) -> dict[str, object]:
    return {
        "id": transfer_id or uuid.uuid4(),
        "tenant_id": uuid.UUID("00000000-0000-0000-0000-000000000001"),
        "product_id": uuid.uuid4(),
        "product_code": "SKU-1",
        "product_name": "Widget",
        "from_warehouse_id": uuid.uuid4(),
        "from_warehouse_name": "Main Warehouse",
        "from_warehouse_code": "MAIN",
        "to_warehouse_id": uuid.uuid4(),
        "to_warehouse_name": "Outlet Warehouse",
        "to_warehouse_code": "OUTLET",
        "quantity": 12,
        "actor_id": "system",
        "notes": "Balance floor stock",
        "created_at": datetime.now(tz=UTC),
    }


async def test_list_transfers_returns_history_rows() -> None:
    row = _transfer_row()
    session = FakeAsyncSession()
    session.queue_count(1)
    session.queue_mapping_items([row])
    previous = _setup(session)

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
            headers=auth_header(),
        ) as client:
            resp = await client.get("/api/v1/inventory/transfers")

        assert resp.status_code == 200, resp.json()
        body = resp.json()
        assert body["total"] == 1
        assert body["items"][0]["product_code"] == "SKU-1"
        assert body["items"][0]["from_warehouse_name"] == "Main Warehouse"
    finally:
        _teardown(previous)


async def test_get_transfer_returns_detail_row() -> None:
    row = _transfer_row()
    session = FakeAsyncSession()
    session.queue_mapping_value(row)
    previous = _setup(session)

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
            headers=auth_header(),
        ) as client:
            resp = await client.get(f"/api/v1/inventory/transfers/{row['id']}")

        assert resp.status_code == 200, resp.json()
        body = resp.json()
        assert body["notes"] == "Balance floor stock"
        assert body["to_warehouse_code"] == "OUTLET"
    finally:
        _teardown(previous)


async def test_create_transfer_same_warehouse_returns_422() -> None:
    session = FakeAsyncSession()
    previous = _setup(session)
    warehouse_id = str(uuid.uuid4())

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
            headers=auth_header(),
        ) as client:
            resp = await client.post(
                "/api/v1/inventory/transfers",
                json={
                    "from_warehouse_id": warehouse_id,
                    "to_warehouse_id": warehouse_id,
                    "product_id": str(uuid.uuid4()),
                    "quantity": 5,
                },
            )

        assert resp.status_code == 422
        assert "different" in resp.json()["detail"]
    finally:
        _teardown(previous)


async def test_create_transfer_uses_authenticated_actor(monkeypatch: Any) -> None:
    session = FakeAsyncSession()
    previous = _setup(session)
    captured: dict[str, str] = {}

    async def fake_transfer_stock(
        _session: FakeAsyncSession,
        tenant_id: uuid.UUID,
        *,
        from_warehouse_id: uuid.UUID,
        to_warehouse_id: uuid.UUID,
        product_id: uuid.UUID,
        quantity: int,
        actor_id: str,
        notes: str | None,
    ) -> SimpleNamespace:
        captured["actor_id"] = actor_id
        return SimpleNamespace(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            product_id=product_id,
            from_warehouse_id=from_warehouse_id,
            to_warehouse_id=to_warehouse_id,
            quantity=quantity,
            actor_id=actor_id,
            notes=notes,
            created_at=datetime.now(tz=UTC),
        )

    monkeypatch.setattr(inventory_routes, "transfer_stock", fake_transfer_stock)

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
            headers=auth_header(),
        ) as client:
            resp = await client.post(
                "/api/v1/inventory/transfers",
                json={
                    "from_warehouse_id": str(uuid.uuid4()),
                    "to_warehouse_id": str(uuid.uuid4()),
                    "product_id": str(uuid.uuid4()),
                    "quantity": 5,
                    "notes": "Floor rebalance",
                },
            )

        assert resp.status_code == 201, resp.json()
        assert captured["actor_id"] == "00000000-0000-0000-0000-000000000111"
        assert session.commit_calls == 1
    finally:
        _teardown(previous)


async def test_create_transfer_insufficient_stock_returns_409() -> None:
    session = FakeAsyncSession()
    session.queue_scalar(None)
    previous = _setup(session)

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
            headers=auth_header(),
        ) as client:
            resp = await client.post(
                "/api/v1/inventory/transfers",
                json={
                    "from_warehouse_id": str(uuid.uuid4()),
                    "to_warehouse_id": str(uuid.uuid4()),
                    "product_id": str(uuid.uuid4()),
                    "quantity": 5,
                },
            )

        assert resp.status_code == 409
        body = resp.json()["detail"]
        assert body["available"] == 0
        assert body["requested"] == 5
    finally:
        _teardown(previous)