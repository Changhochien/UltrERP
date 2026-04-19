from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

from httpx import ASGITransport, AsyncClient

from app.main import app
from common.database import get_db
from common.errors import ValidationError
from domains.inventory import routes as inventory_routes
from tests.domains.orders._helpers import auth_header


class FakeAsyncSession:
    def __init__(self) -> None:
        self.commit_calls = 0

    async def commit(self) -> None:
        self.commit_calls += 1

    async def rollback(self) -> None:
        pass


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


def _association_payload(product_id: uuid.UUID, supplier_id: uuid.UUID) -> dict[str, object]:
    timestamp = datetime.now(tz=UTC)
    return {
        "id": uuid.uuid4(),
        "product_id": product_id,
        "supplier_id": supplier_id,
        "supplier_name": "Acme Supply",
        "unit_cost": 12.5,
        "lead_time_days": 7,
        "is_default": True,
        "created_at": timestamp,
        "updated_at": timestamp,
    }


async def test_list_product_suppliers_returns_items(monkeypatch: Any) -> None:
    product_id = uuid.uuid4()
    supplier_id = uuid.uuid4()

    async def fake_list_product_suppliers(
        _session: FakeAsyncSession,
        _tenant_id: uuid.UUID,
        requested_product_id: uuid.UUID,
    ) -> list[dict[str, object]]:
        assert requested_product_id == product_id
        return [_association_payload(product_id, supplier_id)]

    monkeypatch.setattr(inventory_routes, "list_product_suppliers", fake_list_product_suppliers)
    session = FakeAsyncSession()
    previous = _setup(session)

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
            headers=auth_header(),
        ) as client:
            resp = await client.get(f"/api/v1/inventory/products/{product_id}/suppliers")

        assert resp.status_code == 200, resp.json()
        body = resp.json()
        assert body["total"] == 1
        assert body["items"][0]["supplier_name"] == "Acme Supply"
        assert body["items"][0]["is_default"] is True
    finally:
        _teardown(previous)


async def test_create_product_supplier_returns_created_item(monkeypatch: Any) -> None:
    product_id = uuid.uuid4()
    supplier_id = uuid.uuid4()

    async def fake_create_product_supplier(
        _session: FakeAsyncSession,
        _tenant_id: uuid.UUID,
        requested_product_id: uuid.UUID,
        *,
        supplier_id: uuid.UUID,
        unit_cost: float | None = None,
        lead_time_days: int | None = None,
        is_default: bool = False,
    ) -> dict[str, object]:
        assert requested_product_id == product_id
        assert unit_cost == 12.5
        assert lead_time_days == 7
        assert is_default is True
        return _association_payload(product_id, supplier_id)

    monkeypatch.setattr(inventory_routes, "create_product_supplier", fake_create_product_supplier)
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
                f"/api/v1/inventory/products/{product_id}/suppliers",
                json={
                    "supplier_id": str(supplier_id),
                    "unit_cost": 12.5,
                    "lead_time_days": 7,
                    "is_default": True,
                },
            )

        assert resp.status_code == 201, resp.json()
        body = resp.json()
        assert body["supplier_id"] == str(supplier_id)
        assert body["supplier_name"] == "Acme Supply"
        assert session.commit_calls == 1
    finally:
        _teardown(previous)


async def test_create_product_supplier_returns_structured_validation(monkeypatch: Any) -> None:
    product_id = uuid.uuid4()
    supplier_id = uuid.uuid4()

    async def fake_create_product_supplier(
        _session: FakeAsyncSession,
        _tenant_id: uuid.UUID,
        _product_id: uuid.UUID,
        *,
        supplier_id: uuid.UUID,
        unit_cost: float | None = None,
        lead_time_days: int | None = None,
        is_default: bool = False,
    ) -> dict[str, object]:
        raise ValidationError([
            {
                "loc": ["supplier_id"],
                "msg": "Supplier association already exists for this product",
                "type": "value_error",
            }
        ])

    monkeypatch.setattr(inventory_routes, "create_product_supplier", fake_create_product_supplier)
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
                f"/api/v1/inventory/products/{product_id}/suppliers",
                json={
                    "supplier_id": str(supplier_id),
                },
            )

        assert resp.status_code == 422
        assert resp.json()["detail"][0]["loc"] == ["supplier_id"]
    finally:
        _teardown(previous)


async def test_update_and_delete_product_supplier_commit_changes(monkeypatch: Any) -> None:
    product_id = uuid.uuid4()
    supplier_id = uuid.uuid4()

    async def fake_update_product_supplier(
        _session: FakeAsyncSession,
        _tenant_id: uuid.UUID,
        requested_product_id: uuid.UUID,
        requested_supplier_id: uuid.UUID,
        *,
        unit_cost: float | None = None,
        lead_time_days: int | None = None,
        is_default: bool | None = None,
    ) -> dict[str, object] | None:
        assert requested_product_id == product_id
        assert requested_supplier_id == supplier_id
        assert unit_cost == 10.0
        assert lead_time_days == 5
        assert is_default is False
        payload = _association_payload(product_id, supplier_id)
        payload["unit_cost"] = 10.0
        payload["lead_time_days"] = 5
        payload["is_default"] = False
        return payload

    async def fake_delete_product_supplier(
        _session: FakeAsyncSession,
        _tenant_id: uuid.UUID,
        requested_product_id: uuid.UUID,
        requested_supplier_id: uuid.UUID,
    ) -> bool:
        assert requested_product_id == product_id
        assert requested_supplier_id == supplier_id
        return True

    monkeypatch.setattr(inventory_routes, "update_product_supplier", fake_update_product_supplier)
    monkeypatch.setattr(inventory_routes, "delete_product_supplier", fake_delete_product_supplier)
    session = FakeAsyncSession()
    previous = _setup(session)

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
            headers=auth_header(),
        ) as client:
            patch_resp = await client.patch(
                f"/api/v1/inventory/products/{product_id}/suppliers/{supplier_id}",
                json={
                    "unit_cost": 10.0,
                    "lead_time_days": 5,
                    "is_default": False,
                },
            )
            delete_resp = await client.delete(
                f"/api/v1/inventory/products/{product_id}/suppliers/{supplier_id}"
            )

        assert patch_resp.status_code == 200, patch_resp.json()
        assert patch_resp.json()["unit_cost"] == 10.0
        assert delete_resp.status_code == 204
        assert session.commit_calls == 2
    finally:
        _teardown(previous)
