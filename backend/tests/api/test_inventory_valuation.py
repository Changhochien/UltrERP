from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from decimal import Decimal
from typing import Any

from httpx import ASGITransport, AsyncClient

from app.main import app
from common.database import get_db
from domains.inventory import routes as inventory_routes
from tests.domains.orders._helpers import auth_header


class FakeAsyncSession:
    async def commit(self) -> None:
        return None


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


async def test_inventory_valuation_route_returns_decimal_strings_and_forwards_warehouse_scope(monkeypatch) -> None:
    requested_warehouse_id = uuid.uuid4()
    calls: list[uuid.UUID | None] = []

    async def fake_get_inventory_valuation(
        _session: FakeAsyncSession,
        _tenant_id: uuid.UUID,
        *,
        warehouse_id: uuid.UUID | None = None,
    ) -> dict:
        calls.append(warehouse_id)
        return {
            "items": [
                {
                    "product_id": uuid.uuid4(),
                    "product_code": "VAL-001",
                    "product_name": "Widget A",
                    "category": "Hardware",
                    "warehouse_id": requested_warehouse_id,
                    "warehouse_name": "Main Warehouse",
                    "quantity": 5,
                    "unit_cost": Decimal("12.5000"),
                    "extended_value": Decimal("62.5000"),
                    "cost_source": "latest_purchase",
                },
                {
                    "product_id": uuid.uuid4(),
                    "product_code": "VAL-002",
                    "product_name": "Widget B",
                    "category": None,
                    "warehouse_id": requested_warehouse_id,
                    "warehouse_name": "Main Warehouse",
                    "quantity": 2,
                    "unit_cost": None,
                    "extended_value": Decimal("0.0000"),
                    "cost_source": "missing",
                },
            ],
            "warehouse_totals": [
                {
                    "warehouse_id": requested_warehouse_id,
                    "warehouse_name": "Main Warehouse",
                    "total_quantity": 7,
                    "total_value": Decimal("62.5000"),
                    "row_count": 2,
                }
            ],
            "grand_total_value": Decimal("62.5000"),
            "grand_total_quantity": 7,
            "total_rows": 2,
        }

    monkeypatch.setattr(inventory_routes, "get_inventory_valuation", fake_get_inventory_valuation)
    session = FakeAsyncSession()
    previous = _setup(session)

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
            headers=auth_header(),
        ) as client:
            response = await client.get(
                f"/api/v1/inventory/reports/valuation?warehouse_id={requested_warehouse_id}"
            )

        assert response.status_code == 200, response.json()
        body = response.json()
        assert body["items"][0]["unit_cost"] == "12.5000"
        assert body["items"][0]["extended_value"] == "62.5000"
        assert body["items"][0]["cost_source"] == "latest_purchase"
        assert body["items"][1]["unit_cost"] is None
        assert body["items"][1]["cost_source"] == "missing"
        assert body["warehouse_totals"][0]["total_value"] == "62.5000"
        assert body["grand_total_value"] == "62.5000"
        assert body["grand_total_quantity"] == 7
        assert body["total_rows"] == 2
        assert calls == [requested_warehouse_id]
    finally:
        _teardown(previous)