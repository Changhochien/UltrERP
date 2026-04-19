from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from httpx import ASGITransport, AsyncClient

from app.main import app
from common.database import get_db
from tests.domains.orders._helpers import auth_header


class FakeScalarResult:
    def __init__(self, value: object | None = None) -> None:
        self._value = value

    def scalar_one_or_none(self) -> object | None:
        return self._value


class FakeProduct:
    def __init__(
        self,
        *,
        product_id: uuid.UUID | None = None,
        code: str = "SKU-1",
        name: str = "Widget",
        category: str | None = "Hardware",
        description: str | None = "Original description",
        unit: str = "pcs",
        standard_cost: Decimal | None = Decimal("5.2500"),
    ) -> None:
        self.id = product_id or uuid.uuid4()
        self.code = code
        self.name = name
        self.tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        self.category = category
        self.description = description
        self.unit = unit
        self.standard_cost = standard_cost
        self.status = "active"
        self.created_at = datetime.now(tz=UTC)
        self.updated_at = datetime.now(tz=UTC)
        self.search_vector = None


class FakeAsyncSession:
    def __init__(self) -> None:
        self._execute_results: list[FakeScalarResult] = []
        self.commit_calls = 0
        self.rollback_calls = 0

    async def execute(self, _statement: object, params: object = None) -> FakeScalarResult:
        if self._execute_results:
            return self._execute_results.pop(0)
        return FakeScalarResult(None)

    async def flush(self) -> None:
        pass

    async def commit(self) -> None:
        self.commit_calls += 1

    async def rollback(self) -> None:
        self.rollback_calls += 1

    def queue_scalar(self, value: object | None) -> None:
        self._execute_results.append(FakeScalarResult(value))


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


def _valid_body() -> dict[str, object]:
    return {
        "code": "SKU-2",
        "name": "Widget Pro",
        "category_id": None,
        "description": "Updated description",
        "unit": "box",
        "standard_cost": "7.1250",
    }


async def test_update_product_success() -> None:
    product = FakeProduct()
    session = FakeAsyncSession()
    session.queue_scalar(product)
    session.queue_scalar(None)
    previous = _setup(session)

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
            headers=auth_header(),
        ) as client:
            resp = await client.put(f"/api/v1/inventory/products/{product.id}", json=_valid_body())

        assert resp.status_code == 200, resp.json()
        body = resp.json()
        assert body["id"] == str(product.id)
        assert body["code"] == "SKU-2"
        assert body["name"] == "Widget Pro"
        assert body["description"] == "Updated description"
        assert body["unit"] == "box"
        assert body["standard_cost"] == "7.1250"
        assert body["status"] == "active"
    finally:
        _teardown(previous)


async def test_update_product_negative_standard_cost_returns_422() -> None:
    session = FakeAsyncSession()
    previous = _setup(session)

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
            headers=auth_header(),
        ) as client:
            payload = _valid_body()
            payload["standard_cost"] = "-1.0000"
            resp = await client.put(f"/api/v1/inventory/products/{uuid.uuid4()}", json=payload)

        assert resp.status_code == 422
    finally:
        _teardown(previous)


async def test_update_product_not_found_returns_404() -> None:
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
            resp = await client.put(f"/api/v1/inventory/products/{uuid.uuid4()}", json=_valid_body())

        assert resp.status_code == 404
        assert resp.json()["detail"] == "Product not found"
    finally:
        _teardown(previous)


async def test_update_product_duplicate_returns_409() -> None:
    product = FakeProduct(code="SKU-1")
    existing = FakeProduct(code="SKU-2")
    session = FakeAsyncSession()
    session.queue_scalar(product)
    session.queue_scalar(existing)
    previous = _setup(session)

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
            headers=auth_header(),
        ) as client:
            resp = await client.put(f"/api/v1/inventory/products/{product.id}", json=_valid_body())

        assert resp.status_code == 409
        body = resp.json()
        assert body["error"] == "duplicate_product_code"
        assert body["existing_product_code"] == "SKU-2"
    finally:
        _teardown(previous)


async def test_update_product_blank_code_returns_422() -> None:
    session = FakeAsyncSession()
    previous = _setup(session)

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
            headers=auth_header(),
        ) as client:
            payload = _valid_body()
            payload["code"] = "   "
            resp = await client.put(f"/api/v1/inventory/products/{uuid.uuid4()}", json=payload)

        assert resp.status_code == 422
        body = resp.json()
        assert body["detail"][0]["loc"] == ["code"]
    finally:
        _teardown(previous)
