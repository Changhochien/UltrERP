"""API tests for PATCH /api/v1/customers/{id}.

Uses a fake async session that can return a pre-loaded customer for update
operations and track attribute mutations.
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

# ── Fake infrastructure ──────────────────────────────────────────

_CUSTOMER_ID = uuid.uuid4()
_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _make_customer(**overrides: object) -> Customer:
    """Build a real Customer ORM instance with sensible defaults."""
    now = datetime.now(tz=UTC)
    defaults: dict[str, object] = {
        "id": _CUSTOMER_ID,
        "tenant_id": _TENANT_ID,
        "company_name": "台灣好公司有限公司",
        "normalized_business_number": "04595257",
        "billing_address": "台北市信義區信義路五段7號",
        "contact_name": "王大明",
        "contact_phone": "0912-345-678",
        "contact_email": "wang@example.com",
        "credit_limit": "100000.00",
        "status": "active",
        "version": 1,
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    c = Customer(**defaults)
    return c


class FakeScalarResult:
    """Stub for query results returned by session.execute()."""

    def __init__(self, value: object = None) -> None:
        self._value = value

    def scalar_one_or_none(self) -> object:
        return self._value


class FakeAsyncSession:
    """Minimal async session stub for update-customer API tests.

    Call sequence in update_customer:
      1. set_tenant → execute(SET LOCAL ...)  → irrelevant
      2. execute(SELECT customer)             → _customer
      3. execute(SELECT duplicate BAN)        → _duplicate  (only if BAN changed)
    """

    def __init__(
        self,
        customer: Customer | None = None,
        duplicate: Customer | None = None,
    ) -> None:
        self._customer = customer
        self._duplicate = duplicate
        self._call_count = 0

    async def execute(self, statement: object, params: object = None) -> FakeScalarResult:
        self._call_count += 1
        # Call 1 is set_tenant (SET LOCAL), ignore
        if self._call_count == 1:
            return FakeScalarResult(None)
        # Call 2 is the customer lookup
        if self._call_count == 2:
            return FakeScalarResult(self._customer)
        # Call 3+ is the duplicate BAN lookup
        return FakeScalarResult(self._duplicate)

    async def refresh(self, instance: object) -> None:
        pass  # Customer already has all attributes set

    def begin(self) -> "FakeAsyncSession":
        return self

    async def __aenter__(self) -> "FakeAsyncSession":
        return self

    async def __aexit__(self, *args: object) -> None:
        pass


_MISSING_OVERRIDE = object()


def _setup(customer: Customer | None = None, duplicate: Customer | None = None) -> Any:
    async def _override() -> AsyncGenerator[FakeAsyncSession, None]:
        yield FakeAsyncSession(customer=customer, duplicate=duplicate)

    previous_override = app.dependency_overrides.get(get_db, _MISSING_OVERRIDE)
    app.dependency_overrides[get_db] = _override
    return previous_override


def _teardown(previous_override: Any) -> None:
    if previous_override is _MISSING_OVERRIDE:
        app.dependency_overrides.pop(get_db, None)
    else:
        app.dependency_overrides[get_db] = previous_override


def _url(cid: uuid.UUID | None = None) -> str:
    return f"/api/v1/customers/{cid or _CUSTOMER_ID}"


# ── Tests ────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_update_customer_success() -> None:
    customer = _make_customer()
    prev = _setup(customer=customer)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            resp = await client.patch(
                _url(), json={"company_name": "新名稱", "version": 1}
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["company_name"] == "新名稱"
        assert body["version"] == 2
    finally:
        _teardown(prev)


@pytest.mark.anyio
async def test_update_customer_not_found() -> None:
    prev = _setup(customer=None)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            resp = await client.patch(
                _url(), json={"company_name": "新名稱", "version": 1}
            )
        assert resp.status_code == 404
    finally:
        _teardown(prev)


@pytest.mark.anyio
async def test_update_customer_version_conflict() -> None:
    customer = _make_customer(version=2)
    prev = _setup(customer=customer)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            resp = await client.patch(
                _url(), json={"company_name": "新名稱", "version": 1}
            )
        assert resp.status_code == 409
        body = resp.json()
        assert body["error"] == "version_conflict"
        assert body["expected_version"] == 1
        assert body["actual_version"] == 2
    finally:
        _teardown(prev)


@pytest.mark.anyio
async def test_update_customer_duplicate_ban() -> None:
    customer = _make_customer()
    other = _make_customer(
        id=uuid.uuid4(),
        company_name="Other Corp",
        normalized_business_number="22099131",
    )
    prev = _setup(customer=customer, duplicate=other)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            resp = await client.patch(
                _url(), json={"business_number": "22099131", "version": 1}
            )
        assert resp.status_code == 409
        body = resp.json()
        assert body["error"] == "duplicate_business_number"
        assert body["existing_customer_name"] == "Other Corp"
    finally:
        _teardown(prev)


@pytest.mark.anyio
async def test_update_customer_validation_error() -> None:
    customer = _make_customer()
    prev = _setup(customer=customer)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            resp = await client.patch(
                _url(), json={"contact_phone": "bad", "version": 1}
            )
        assert resp.status_code == 422
        body = resp.json()
        assert any(e["field"] == "contact_phone" for e in body["detail"])
    finally:
        _teardown(prev)


@pytest.mark.anyio
async def test_update_customer_invalid_email() -> None:
    customer = _make_customer()
    prev = _setup(customer=customer)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            resp = await client.patch(
                _url(), json={"contact_email": "not-email", "version": 1}
            )
        assert resp.status_code == 422
        body = resp.json()
        assert any(e["field"] == "contact_email" for e in body["detail"])
    finally:
        _teardown(prev)


@pytest.mark.anyio
async def test_update_credit_limit_only() -> None:
    customer = _make_customer()
    prev = _setup(customer=customer)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            resp = await client.patch(
                _url(), json={"credit_limit": "50000.00", "version": 1}
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["credit_limit"] == "50000.00"
        assert body["version"] == 2
    finally:
        _teardown(prev)


@pytest.mark.anyio
async def test_update_missing_version_rejected() -> None:
    prev = _setup(customer=_make_customer())
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            resp = await client.patch(
                _url(), json={"company_name": "No version"}
            )
        assert resp.status_code == 422
    finally:
        _teardown(prev)
