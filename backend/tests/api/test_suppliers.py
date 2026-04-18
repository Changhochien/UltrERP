from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

from httpx import ASGITransport, AsyncClient

from app.main import app
from common.database import get_db
from tests.domains.orders._helpers import auth_header


class FakeScalarResult:
    def __init__(
        self,
        *,
        scalar_value: object | None = None,
        scalar_items: list[object] | None = None,
    ) -> None:
        self._scalar_value = scalar_value
        self._scalar_items = scalar_items or []

    def scalar_one_or_none(self) -> object | None:
        return self._scalar_value

    def scalar(self) -> int:
        return int(self._scalar_value or 0)

    def scalars(self) -> FakeScalarResult:
        return self

    def all(self) -> list[object]:
        return list(self._scalar_items)


class FakeSupplier:
    def __init__(
        self,
        *,
        supplier_id: uuid.UUID | None = None,
        name: str = "Acme Supply",
        is_active: bool = True,
    ) -> None:
        self.id = supplier_id or uuid.uuid4()
        self.tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        self.name = name
        self.contact_email = "acme@example.com"
        self.phone = "555-0100"
        self.address = "123 Supply St"
        self.default_lead_time_days = 7
        self.legacy_master_snapshot = {"legacy_code": "SUP-001"}
        self.is_active = is_active
        now = datetime.now(tz=UTC)
        self.created_at = now


class FakeAsyncSession:
    def __init__(self) -> None:
        self._execute_results: list[FakeScalarResult] = []
        self.commit_calls = 0
        self.added: list[object] = []

    def add(self, instance: object) -> None:
        self.added.append(instance)

    async def execute(self, _statement: object, params: object = None) -> FakeScalarResult:
        if self._execute_results:
            return self._execute_results.pop(0)
        return FakeScalarResult()

    async def flush(self) -> None:
        for instance in self.added:
            now = datetime.now(tz=UTC)
            if getattr(instance, "id", None) is None:
                instance.id = uuid.uuid4()  # type: ignore[attr-defined]
            if getattr(instance, "created_at", None) is None:
                instance.created_at = now  # type: ignore[attr-defined]
            if getattr(instance, "tenant_id", None) is None:
                instance.tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")  # type: ignore[attr-defined]
            if getattr(instance, "is_active", None) is None:
                instance.is_active = True  # type: ignore[attr-defined]

    async def commit(self) -> None:
        self.commit_calls += 1

    async def rollback(self) -> None:
        pass

    def queue_scalar(self, value: object | None) -> None:
        self._execute_results.append(FakeScalarResult(scalar_value=value))

    def queue_count(self, value: int) -> None:
        self._execute_results.append(FakeScalarResult(scalar_value=value))

    def queue_scalars(self, items: list[object]) -> None:
        self._execute_results.append(FakeScalarResult(scalar_items=items))


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


async def test_create_supplier_success() -> None:
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
                "/api/v1/inventory/suppliers",
                json={
                    "name": "Acme Supply",
                    "contact_email": "acme@example.com",
                    "phone": "555-0100",
                    "address": "123 Supply St",
                    "default_lead_time_days": 7,
                },
            )

        assert resp.status_code == 201, resp.json()
        body = resp.json()
        assert body["name"] == "Acme Supply"
        assert body["is_active"] is True
    finally:
        _teardown(previous)


async def test_create_supplier_negative_lead_time_returns_422() -> None:
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
                "/api/v1/inventory/suppliers",
                json={"name": "Acme Supply", "default_lead_time_days": -1},
            )

        assert resp.status_code == 422
    finally:
        _teardown(previous)


async def test_create_supplier_blank_name_returns_422() -> None:
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
                "/api/v1/inventory/suppliers",
                json={"name": "   ", "default_lead_time_days": 7},
            )

        assert resp.status_code == 422
    finally:
        _teardown(previous)


async def test_list_suppliers_returns_items() -> None:
    supplier = FakeSupplier(name="Acme Supply")
    session = FakeAsyncSession()
    session.queue_count(1)
    session.queue_scalars([supplier])
    previous = _setup(session)

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
            headers=auth_header(),
        ) as client:
            resp = await client.get("/api/v1/inventory/suppliers?q=Acme")

        assert resp.status_code == 200, resp.json()
        body = resp.json()
        assert body["total"] == 1
        assert body["items"][0]["name"] == "Acme Supply"
    finally:
        _teardown(previous)


async def test_get_supplier_not_found_returns_404() -> None:
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
            resp = await client.get(f"/api/v1/inventory/suppliers/{uuid.uuid4()}")

        assert resp.status_code == 404
    finally:
        _teardown(previous)


async def test_update_supplier_success() -> None:
    supplier = FakeSupplier(name="Acme Supply")
    session = FakeAsyncSession()
    session.queue_scalar(supplier)
    previous = _setup(session)

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
            headers=auth_header(),
        ) as client:
            resp = await client.put(
                f"/api/v1/inventory/suppliers/{supplier.id}",
                json={
                    "name": "Beta Supply",
                    "contact_email": "beta@example.com",
                    "phone": "555-0199",
                    "address": "99 Harbor Rd",
                    "default_lead_time_days": 10,
                },
            )

        assert resp.status_code == 200, resp.json()
        body = resp.json()
        assert body["name"] == "Beta Supply"
        assert body["default_lead_time_days"] == 10
    finally:
        _teardown(previous)


async def test_update_supplier_status_success() -> None:
    supplier = FakeSupplier(name="Acme Supply", is_active=True)
    session = FakeAsyncSession()
    session.queue_scalar(supplier)
    previous = _setup(session)

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
            headers=auth_header(),
        ) as client:
            resp = await client.patch(
                f"/api/v1/inventory/suppliers/{supplier.id}/status",
                json={"is_active": False},
            )

        assert resp.status_code == 200, resp.json()
        body = resp.json()
        assert body["is_active"] is False
    finally:
        _teardown(previous)