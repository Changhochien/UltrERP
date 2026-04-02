"""API tests for POST /api/v1/customers.

Uses a fake async session to avoid needing a real database.
The session records calls so we can assert persistence behavior.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

from httpx import ASGITransport, AsyncClient

from app.main import app
from common.database import get_db


class FakeAsyncSession:
    """Minimal async session stub for create-customer API tests."""

    def __init__(self) -> None:
        self.added: list[Any] = []
        self._in_transaction = False

    def add(self, instance: object) -> None:
        self.added.append(instance)

    async def execute(self, statement: object, params: object = None) -> None:
        pass

    async def refresh(self, instance: object) -> None:
        # Simulate DB-assigned defaults that the ORM normally populates
        now = datetime.now(tz=UTC)
        if getattr(instance, "id", None) is None:
            instance.id = uuid.uuid4()  # type: ignore[attr-defined]
        if getattr(instance, "status", None) is None:
            instance.status = "active"  # type: ignore[attr-defined]
        if getattr(instance, "version", None) is None:
            instance.version = 1  # type: ignore[attr-defined]
        if getattr(instance, "created_at", None) is None:
            instance.created_at = now  # type: ignore[attr-defined]
        if getattr(instance, "updated_at", None) is None:
            instance.updated_at = now  # type: ignore[attr-defined]

    def begin(self) -> FakeAsyncSession:
        return self

    async def __aenter__(self) -> FakeAsyncSession:
        self._in_transaction = True
        return self

    async def __aexit__(self, *args: object) -> None:
        self._in_transaction = False


async def _override_get_db() -> AsyncGenerator[FakeAsyncSession, None]:
    yield FakeAsyncSession()


_MISSING_OVERRIDE = object()


def _setup() -> Any:
    previous_override = app.dependency_overrides.get(get_db, _MISSING_OVERRIDE)
    app.dependency_overrides[get_db] = _override_get_db
    return previous_override


def _teardown(previous_override: Any) -> None:
    if previous_override is _MISSING_OVERRIDE:
        app.dependency_overrides.pop(get_db, None)
        return

    app.dependency_overrides[get_db] = previous_override


def _valid_body() -> dict[str, object]:
    return {
        "company_name": "台灣好公司有限公司",
        "business_number": "04595257",
        "billing_address": "台北市信義區信義路五段7號",
        "contact_name": "王大明",
        "contact_phone": "0912-345-678",
        "contact_email": "wang@example.com",
        "credit_limit": "100000.00",
    }


async def test_create_customer_success() -> None:
    previous_override = _setup()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            resp = await client.post("/api/v1/customers", json=_valid_body())
        assert resp.status_code == 201
        body = resp.json()
        assert body["company_name"] == "台灣好公司有限公司"
        assert body["normalized_business_number"] == "04595257"
        assert body["version"] == 1
        assert body["status"] == "active"
        assert "id" in body
    finally:
        _teardown(previous_override)


async def test_create_customer_invalid_business_number() -> None:
    previous_override = _setup()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            payload = _valid_body()
            payload["business_number"] = "04595258"
            resp = await client.post("/api/v1/customers", json=payload)
        assert resp.status_code == 422
        body = resp.json()
        assert any(e["field"] == "business_number" for e in body["detail"])
    finally:
        _teardown(previous_override)


async def test_create_customer_invalid_phone() -> None:
    previous_override = _setup()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            payload = _valid_body()
            payload["contact_phone"] = "not-a-phone"
            resp = await client.post("/api/v1/customers", json=payload)
        assert resp.status_code == 422
        body = resp.json()
        assert any(e["field"] == "contact_phone" for e in body["detail"])
    finally:
        _teardown(previous_override)


async def test_create_customer_invalid_email() -> None:
    previous_override = _setup()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            payload = _valid_body()
            payload["contact_email"] = "not-an-email"
            resp = await client.post("/api/v1/customers", json=payload)
        assert resp.status_code == 422
        body = resp.json()
        assert any(e["field"] == "contact_email" for e in body["detail"])
    finally:
        _teardown(previous_override)


async def test_create_customer_negative_credit_limit() -> None:
    previous_override = _setup()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            payload = _valid_body()
            payload["credit_limit"] = "-1.00"
            resp = await client.post("/api/v1/customers", json=payload)
        # Pydantic rejects ge=0 before our service layer sees it
        assert resp.status_code == 422
    finally:
        _teardown(previous_override)


async def test_create_customer_missing_required_fields() -> None:
    previous_override = _setup()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            resp = await client.post("/api/v1/customers", json={})
        assert resp.status_code == 422
    finally:
        _teardown(previous_override)


async def test_create_customer_returns_structured_errors() -> None:
    previous_override = _setup()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            payload = _valid_body()
            payload["business_number"] = "bad"
            payload["contact_phone"] = "bad"
            resp = await client.post("/api/v1/customers", json=payload)
        assert resp.status_code == 422
        body = resp.json()
        assert "detail" in body
        fields = {e["field"] for e in body["detail"]}
        assert "business_number" in fields
        assert "contact_phone" in fields
    finally:
        _teardown(previous_override)
