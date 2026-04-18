"""API integration tests for POST /api/v1/inventory/products.

Uses a fake async session to avoid needing a real database.
"""

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

# ── Fakes ─────────────────────────────────────────────────────


class FakeScalarResult:
    def __init__(self, value: object = None) -> None:
        self._value = value

    def scalar_one_or_none(self) -> object:
        return self._value


class _FakeProduct:
    def __init__(self, id=None, code="WIDGET-001", name="Test Widget"):
        self.id = id or uuid.uuid4()
        self.code = code
        self.name = name
        self.tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        self.category = None
        self.description = None
        self.unit = "pcs"
        self.standard_cost = Decimal("12.5000")
        self.status = "active"
        self.created_at = datetime.now(tz=UTC)
        self.updated_at = datetime.now(tz=UTC)


class FakeAsyncSession:
    """Minimal async session stub for create-product API tests."""

    def __init__(self, existing=None) -> None:
        self.added: list[Any] = []
        self._existing = existing

    def add(self, instance: object) -> None:
        self.added.append(instance)

    async def execute(self, statement: object, params: object = None) -> FakeScalarResult:
        return FakeScalarResult(self._existing)

    async def refresh(self, instance: object) -> None:
        now = datetime.now(tz=UTC)
        if getattr(instance, "id", None) is None:
            instance.id = uuid.uuid4()  # type: ignore[attr-defined]
        if getattr(instance, "status", None) is None:
            instance.status = "active"  # type: ignore[attr-defined]
        if getattr(instance, "created_at", None) is None:
            instance.created_at = now  # type: ignore[attr-defined]
        if getattr(instance, "updated_at", None) is None:
            instance.updated_at = now  # type: ignore[attr-defined]

    def begin(self):
        return self

    async def __aenter__(self) -> FakeAsyncSession:
        return self

    async def __aexit__(self, *args: object) -> None:
        pass

    async def flush(self) -> None:
        for instance in self.added:
            await self.refresh(instance)

    async def commit(self) -> None:
        pass


# ── DB override ───────────────────────────────────────────────


async def _override_get_db(existing=None) -> AsyncGenerator[FakeAsyncSession, None]:
    yield FakeAsyncSession(existing=existing)


_MISSING_OVERRIDE = object()


def _setup(existing=None) -> Any:
    previous = app.dependency_overrides.get(get_db, _MISSING_OVERRIDE)

    async def _override() -> AsyncGenerator[FakeAsyncSession, None]:
        yield FakeAsyncSession(existing=existing)

    app.dependency_overrides[get_db] = _override
    return previous


def _teardown(previous: Any) -> None:
    if previous is _MISSING_OVERRIDE:
        app.dependency_overrides.pop(get_db, None)
    else:
        app.dependency_overrides[get_db] = previous


# ── Helpers ───────────────────────────────────────────────────


def _valid_body() -> dict[str, object]:
    return {
        "code": "WIDGET-001",
        "name": "Test Widget",
        "category": "",
        "description": "",
        "unit": "pcs",
        "standard_cost": "12.5000",
    }


# ── Tests ─────────────────────────────────────────────────────


async def test_create_product_success() -> None:
    """POST /api/v1/inventory/products returns 201 with product on valid input."""
    previous = _setup(existing=None)
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://testserver", headers=auth_header()
        ) as client:
            resp = await client.post("/api/v1/inventory/products", json=_valid_body())

        assert resp.status_code == 201, resp.json()
        body = resp.json()
        assert body["code"] == "WIDGET-001"
        assert body["name"] == "Test Widget"
        assert body["standard_cost"] == "12.5000"
        assert body["status"] == "active"
        assert "id" in body
    finally:
        _teardown(previous)


async def test_create_product_negative_standard_cost_returns_422() -> None:
    previous = _setup(existing=None)
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://testserver", headers=auth_header()
        ) as client:
            payload = _valid_body()
            payload["standard_cost"] = "-0.0100"
            resp = await client.post("/api/v1/inventory/products", json=payload)

        assert resp.status_code == 422
    finally:
        _teardown(previous)


async def test_create_product_missing_required_fields() -> None:
    """POST with empty body returns 422."""
    previous = _setup(existing=None)
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://testserver", headers=auth_header()
        ) as client:
            resp = await client.post("/api/v1/inventory/products", json={})

        assert resp.status_code == 422
    finally:
        _teardown(previous)


async def test_create_product_blank_code_returns_422() -> None:
    """POST with blank code in body returns 422."""
    previous = _setup(existing=None)
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://testserver", headers=auth_header()
        ) as client:
            payload = _valid_body()
            payload["code"] = "   "
            resp = await client.post("/api/v1/inventory/products", json=payload)

        assert resp.status_code == 422
    finally:
        _teardown(previous)


async def test_create_product_duplicate_returns_409() -> None:
    """POST with a duplicate code returns 409 Conflict."""
    existing = _FakeProduct(id=uuid.uuid4(), code="WIDGET-001", name="Existing Widget")
    previous = _setup(existing=existing)
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://testserver", headers=auth_header()
        ) as client:
            resp = await client.post("/api/v1/inventory/products", json=_valid_body())

        assert resp.status_code == 409
        body = resp.json()
        assert body["error"] == "duplicate_product_code"
        assert body["existing_product_code"] == "WIDGET-001"
    finally:
        _teardown(previous)
