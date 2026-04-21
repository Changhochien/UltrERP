from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from typing import Any

from httpx import ASGITransport, AsyncClient

from app.main import app
from common.database import get_db
from domains.inventory import routes as inventory_routes
from tests.domains.orders._helpers import auth_header


class FakeAsyncSession:
    def __init__(self) -> None:
        self.commit_calls = 0

    async def commit(self) -> None:
        self.commit_calls += 1


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


async def test_list_reorder_suggestions_returns_items(monkeypatch) -> None:
    requested_warehouse_id = uuid.uuid4()

    async def fake_list_reorder_suggestions(
        _session: FakeAsyncSession,
        _tenant_id: uuid.UUID,
        *,
        warehouse_id: uuid.UUID | None = None,
    ) -> tuple[list[dict], int]:
        assert warehouse_id == requested_warehouse_id
        return (
            [
                {
                    "product_id": uuid.uuid4(),
                    "product_code": "RTC-001",
                    "product_name": "Rotor",
                    "warehouse_id": requested_warehouse_id,
                    "warehouse_name": "Main Warehouse",
                    "current_stock": 5,
                    "reorder_point": 10,
                    "inventory_position": 8,
                    "target_stock_qty": 20,
                    "suggested_qty": 12,
                    "supplier_hint": None,
                }
            ],
            1,
        )

    monkeypatch.setattr(inventory_routes, "list_reorder_suggestions", fake_list_reorder_suggestions)
    session = FakeAsyncSession()
    previous = _setup(session)

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
            headers=auth_header(),
        ) as client:
            resp = await client.get(
                f"/api/v1/inventory/reorder-suggestions?warehouse_id={requested_warehouse_id}"
            )

        assert resp.status_code == 200, resp.json()
        body = resp.json()
        assert body["total"] == 1
        assert body["items"][0]["warehouse_name"] == "Main Warehouse"
        assert body["items"][0]["suggested_qty"] == 12
    finally:
        _teardown(previous)


async def test_create_reorder_suggestion_orders_returns_created_and_unresolved_rows(monkeypatch) -> None:
    product_id = uuid.uuid4()
    warehouse_id = uuid.uuid4()
    supplier_id = uuid.uuid4()
    order_id = uuid.uuid4()

    async def fake_create_reorder_suggestion_orders(
        _session: FakeAsyncSession,
        _tenant_id: uuid.UUID,
        *,
        items: list[dict],
        actor_id: str,
    ) -> dict:
        assert len(items) == 1
        assert actor_id == "00000000-0000-0000-0000-000000000111"
        return {
            "created_orders": [
                {
                    "order_id": order_id,
                    "order_number": "PO-20260418-ABC12345",
                    "supplier_id": supplier_id,
                    "supplier_name": "Acme Supply",
                    "line_count": 1,
                }
            ],
            "unresolved_rows": [
                {
                    "product_id": product_id,
                    "product_code": "VLV-001",
                    "product_name": "Valve",
                    "warehouse_id": warehouse_id,
                    "warehouse_name": "Main Warehouse",
                    "current_stock": 2,
                    "reorder_point": 10,
                    "inventory_position": 2,
                    "target_stock_qty": 15,
                    "suggested_qty": 13,
                    "supplier_hint": None,
                }
            ],
        }

    monkeypatch.setattr(
        inventory_routes,
        "create_reorder_suggestion_orders",
        fake_create_reorder_suggestion_orders,
    )
    session = FakeAsyncSession()
    previous = _setup(session)

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
            headers=auth_header(),
        ) as client:
            resp = await client.post(
                "/api/v1/inventory/reorder-suggestions/orders",
                json={
                    "items": [
                        {
                            "product_id": str(product_id),
                            "warehouse_id": str(warehouse_id),
                            "suggested_qty": 13,
                        }
                    ]
                },
            )

        assert resp.status_code == 200, resp.json()
        body = resp.json()
        assert body["created_orders"][0]["supplier_name"] == "Acme Supply"
        assert body["unresolved_rows"][0]["product_name"] == "Valve"
        assert session.commit_calls == 1
    finally:
        _teardown(previous)