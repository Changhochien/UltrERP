"""API tests for customer read endpoints.

GET /api/v1/customers        — paginated list
GET /api/v1/customers/{id}   — single by ID
GET /api/v1/customers/lookup — exact BAN match
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from common.database import get_db
from domains.customers.models import Customer
from tests.domains.orders._helpers import auth_header

DEFAULT_TENANT = uuid.UUID("00000000-0000-0000-0000-000000000001")

# Consumed by set_tenant; return value unused.
_TENANT_RESULT = None


def _make_customer(**overrides: object) -> Customer:
    now = datetime.now(tz=UTC)
    defaults: dict[str, object] = {
        "id": uuid.uuid4(),
        "tenant_id": DEFAULT_TENANT,
        "company_name": "Test Corp",
        "normalized_business_number": "04595252",
        "billing_address": "Taipei",
        "contact_name": "Alice",
        "contact_phone": "0912-345-678",
        "contact_email": "a@b.com",
        "credit_limit": 1000,
        "status": "active",
        "version": 1,
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return Customer(**defaults)  # type: ignore[arg-type]


class _FakeScalarResult:
    def __init__(self, items: list[Customer]) -> None:
        self._items = items

    def all(self) -> list[Customer]:
        return self._items


class _FakeResult:
    def __init__(self, value: object = None, items: list[Customer] | None = None) -> None:
        self._value = value
        self._items = items or []

    def scalar(self) -> object:
        return self._value

    def scalar_one_or_none(self) -> object:
        return self._value

    def scalars(self) -> _FakeScalarResult:
        return _FakeScalarResult(self._items)


class FakeReadSession:
    """Session stub that returns pre-configured results."""

    def __init__(self, results: list[_FakeResult]) -> None:
        self._results = list(results)
        self._call_index = 0

    async def execute(self, statement: Any, params: object = None) -> _FakeResult:
        result = self._results[self._call_index]
        self._call_index += 1
        return result

    # Not used for read tests, but required by DI
    def add(self, instance: object) -> None:
        pass

    async def refresh(self, instance: object) -> None:
        pass

    def begin(self) -> "FakeReadSession":
        return self

    async def __aenter__(self) -> "FakeReadSession":
        return self

    async def __aexit__(self, *args: object) -> None:
        pass


def _make_override(results: list[_FakeResult]):
    async def _override() -> AsyncGenerator[FakeReadSession, None]:
        yield FakeReadSession(results)

    return _override


_MISSING_OVERRIDE = object()


def _install_db_override(results: list[_FakeResult]) -> Any:
    previous_override = app.dependency_overrides.get(get_db, _MISSING_OVERRIDE)
    app.dependency_overrides[get_db] = _make_override(results)
    return previous_override


def _restore_db_override(previous_override: Any) -> None:
    if previous_override is _MISSING_OVERRIDE:
        app.dependency_overrides.pop(get_db, None)
        return

    app.dependency_overrides[get_db] = previous_override


def _base_url() -> str:
    return "http://test"


# ---------------------------------------------------------------------------
# GET /api/v1/customers  — list
# ---------------------------------------------------------------------------
class TestListEndpoint:
    @pytest.mark.asyncio
    async def test_empty_list(self) -> None:
        previous_override = _install_db_override(
            [
                _FakeResult(value=_TENANT_RESULT),  # set_tenant
                _FakeResult(value=0),
                _FakeResult(items=[]),
            ]
        )
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url=_base_url(), headers=auth_header()
            ) as c:
                r = await c.get("/api/v1/customers")
            assert r.status_code == 200
            body = r.json()
            assert body["total_count"] == 0
            assert body["items"] == []
            assert body["page"] == 1
            assert body["total_pages"] == 1
        finally:
            _restore_db_override(previous_override)

    @pytest.mark.asyncio
    async def test_returns_items(self) -> None:
        c1 = _make_customer(company_name="Alpha Co")
        previous_override = _install_db_override(
            [
                _FakeResult(value=_TENANT_RESULT),  # set_tenant
                _FakeResult(value=1),
                _FakeResult(items=[c1]),
            ]
        )
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url=_base_url(), headers=auth_header()
            ) as c:
                r = await c.get("/api/v1/customers")
            assert r.status_code == 200
            body = r.json()
            assert body["total_count"] == 1
            assert len(body["items"]) == 1
            assert body["items"][0]["company_name"] == "Alpha Co"
        finally:
            _restore_db_override(previous_override)

    @pytest.mark.asyncio
    async def test_pagination_params(self) -> None:
        previous_override = _install_db_override(
            [
                _FakeResult(value=_TENANT_RESULT),  # set_tenant
                _FakeResult(value=50),
                _FakeResult(items=[_make_customer()]),
            ]
        )
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url=_base_url(), headers=auth_header()
            ) as c:
                r = await c.get("/api/v1/customers", params={"page": 2, "page_size": 10})
            assert r.status_code == 200
            body = r.json()
            assert body["page"] == 2
            assert body["page_size"] == 10
            assert body["total_pages"] == 5
        finally:
            _restore_db_override(previous_override)

    @pytest.mark.asyncio
    async def test_search_filter(self) -> None:
        c1 = _make_customer(company_name="Matched")
        previous_override = _install_db_override(
            [
                _FakeResult(value=_TENANT_RESULT),  # set_tenant
                _FakeResult(value=1),
                _FakeResult(items=[c1]),
            ]
        )
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url=_base_url(), headers=auth_header()
            ) as c:
                r = await c.get("/api/v1/customers", params={"q": "Match"})
            assert r.status_code == 200
            assert r.json()["total_count"] == 1
        finally:
            _restore_db_override(previous_override)


# ---------------------------------------------------------------------------
# GET /api/v1/customers/{customer_id}  — detail
# ---------------------------------------------------------------------------
class TestGetByIdEndpoint:
    @pytest.mark.asyncio
    async def test_found(self) -> None:
        c = _make_customer()
        previous_override = _install_db_override(
            [
                _FakeResult(value=_TENANT_RESULT),  # set_tenant
                _FakeResult(value=c),
            ]
        )
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url=_base_url(), headers=auth_header()
            ) as cl:
                r = await cl.get(f"/api/v1/customers/{c.id}")
            assert r.status_code == 200
            assert r.json()["id"] == str(c.id)
        finally:
            _restore_db_override(previous_override)

    @pytest.mark.asyncio
    async def test_not_found(self) -> None:
        previous_override = _install_db_override(
            [
                _FakeResult(value=_TENANT_RESULT),  # set_tenant
                _FakeResult(value=None),
            ]
        )
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url=_base_url(), headers=auth_header()
            ) as c:
                r = await c.get(f"/api/v1/customers/{uuid.uuid4()}")
            assert r.status_code == 404
        finally:
            _restore_db_override(previous_override)

    @pytest.mark.asyncio
    async def test_invalid_uuid(self) -> None:
        previous_override = _install_db_override([])
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url=_base_url(), headers=auth_header()
            ) as c:
                r = await c.get("/api/v1/customers/not-a-uuid")
            assert r.status_code == 422
        finally:
            _restore_db_override(previous_override)


# ---------------------------------------------------------------------------
# GET /api/v1/customers/lookup  — BAN lookup
# ---------------------------------------------------------------------------
class TestLookupEndpoint:
    @pytest.mark.asyncio
    async def test_found(self) -> None:
        c = _make_customer(normalized_business_number="04595252")
        previous_override = _install_db_override(
            [
                _FakeResult(value=_TENANT_RESULT),  # set_tenant
                _FakeResult(value=c),
            ]
        )
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url=_base_url(), headers=auth_header()
            ) as cl:
                r = await cl.get("/api/v1/customers/lookup", params={"business_number": "04595252"})
            assert r.status_code == 200
            assert r.json()["normalized_business_number"] == "04595252"
        finally:
            _restore_db_override(previous_override)

    @pytest.mark.asyncio
    async def test_not_found(self) -> None:
        previous_override = _install_db_override(
            [
                _FakeResult(value=_TENANT_RESULT),  # set_tenant
                _FakeResult(value=None),
            ]
        )
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url=_base_url(), headers=auth_header()
            ) as c:
                r = await c.get("/api/v1/customers/lookup", params={"business_number": "99999999"})
            assert r.status_code == 404
        finally:
            _restore_db_override(previous_override)

    @pytest.mark.asyncio
    async def test_missing_param(self) -> None:
        previous_override = _install_db_override([])
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url=_base_url(), headers=auth_header()
            ) as c:
                r = await c.get("/api/v1/customers/lookup")
            assert r.status_code == 422
        finally:
            _restore_db_override(previous_override)
