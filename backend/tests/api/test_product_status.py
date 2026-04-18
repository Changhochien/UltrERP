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
        status: str = "active",
    ) -> None:
        self.id = product_id or uuid.uuid4()
        self.code = code
        self.name = name
        self.tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        self.category = category
        self.description = description
        self.unit = unit
        self.status = status
        self.created_at = datetime.now(tz=UTC)
        self.updated_at = datetime.now(tz=UTC)


class FakeAsyncSession:
    def __init__(self) -> None:
        self._execute_results: list[FakeScalarResult] = []
        self.commit_calls = 0

    async def execute(self, _statement: object, params: object = None) -> FakeScalarResult:
        if self._execute_results:
            return self._execute_results.pop(0)
        return FakeScalarResult(None)

    async def flush(self) -> None:
        pass

    async def commit(self) -> None:
        self.commit_calls += 1

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


async def test_set_product_status_success() -> None:
    product = FakeProduct(status="active")
    session = FakeAsyncSession()
    session.queue_scalar(product)
    previous = _setup(session)

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
            headers=auth_header(),
        ) as client:
            resp = await client.patch(
                f"/api/v1/inventory/products/{product.id}/status",
                json={"status": "inactive"},
            )

        assert resp.status_code == 200, resp.json()
        body = resp.json()
        assert body["id"] == str(product.id)
        assert body["status"] == "inactive"
    finally:
        _teardown(previous)


async def test_set_product_status_not_found_returns_404() -> None:
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
            resp = await client.patch(
                f"/api/v1/inventory/products/{uuid.uuid4()}/status",
                json={"status": "inactive"},
            )

        assert resp.status_code == 404
        assert resp.json()["detail"] == "Product not found"
    finally:
        _teardown(previous)