"""Tests for auth endpoints and RBAC enforcement (Story 11.3)."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from common.database import get_db
from common.tenant import DEFAULT_TENANT_ID
from domains.users.auth import hash_password
from tests.domains.orders._helpers import (
    TEST_JWT_SECRET,
    auth_header,
    make_test_token,
)

BASE = "http://testserver"


# ── Fake User ────────────────────────────────────────────────


class FakeUser:
    def __init__(self, **kw: Any) -> None:
        now = datetime.now(tz=UTC)
        self.id = kw.get("id", uuid.uuid4())
        self.tenant_id = kw.get("tenant_id", DEFAULT_TENANT_ID)
        self.email = kw.get("email", "test@example.com")
        self.password_hash = kw.get("password_hash", hash_password("Correct!Pass1"))
        self.display_name = kw.get("display_name", "Test User")
        self.role = kw.get("role", "owner")
        self.status = kw.get("status", "active")
        self.created_at = kw.get("created_at", now)
        self.updated_at = kw.get("updated_at", None)


# ── Fake DB session ──────────────────────────────────────────


class _FakeScalars:
    def __init__(self, items: list) -> None:
        self._items = items

    def all(self) -> list:
        return self._items


class _FakeResult:
    def __init__(self, obj: object | None = None) -> None:
        self._obj = obj

    def scalar_one_or_none(self) -> object | None:
        return self._obj

    def scalar(self) -> object | None:
        return self._obj

    def scalars(self) -> _FakeScalars:
        if isinstance(self._obj, list):
            return _FakeScalars(self._obj)
        return _FakeScalars([])

    def all(self) -> list:
        if isinstance(self._obj, list):
            return self._obj
        return []


class _FakeBegin:
    async def __aenter__(self) -> None:
        return None

    async def __aexit__(self, *args: object) -> bool:
        return False


class FakeAsyncSession:
    def __init__(self) -> None:
        self._results: list[object] = []
        self._idx = 0
        self.added: list[object] = []

    def queue(self, obj: object | None) -> None:
        self._results.append(_FakeResult(obj))

    async def execute(self, _stmt: object, _params: object = None) -> object:
        if self._idx < len(self._results):
            r = self._results[self._idx]
            self._idx += 1
            return r
        return _FakeResult(None)

    def add(self, obj: object) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        pass

    async def commit(self) -> None:
        pass

    async def close(self) -> None:
        pass

    def begin(self) -> _FakeBegin:
        return _FakeBegin()


_prev_override: object | None = None


def _setup(session: FakeAsyncSession) -> None:
    global _prev_override  # noqa: PLW0603
    _prev_override = app.dependency_overrides.get(get_db)

    async def _override() -> AsyncGenerator[FakeAsyncSession, None]:
        yield session  # type: ignore[misc]

    app.dependency_overrides[get_db] = _override


def _teardown() -> None:
    if _prev_override is None:
        app.dependency_overrides.pop(get_db, None)
    else:
        app.dependency_overrides[get_db] = _prev_override


def _client(**kw: Any) -> AsyncClient:
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url=BASE,
        **kw,
    )


# ── Login tests ──────────────────────────────────────────────


@pytest.mark.anyio
async def test_login_success() -> None:
    user = FakeUser()
    session = FakeAsyncSession()
    session.queue(user)  # get_user_by_email
    _setup(session)
    try:
        async with _client() as c:
            resp = await c.post(
                "/api/v1/auth/login",
                json={"email": "test@example.com", "password": "Correct!Pass1"},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"
        # Decode and verify claims
        payload = jwt.decode(body["access_token"], TEST_JWT_SECRET, algorithms=["HS256"])
        assert payload["sub"] == str(user.id)
        assert payload["role"] == "owner"
        assert payload["tenant_id"] == str(DEFAULT_TENANT_ID)
    finally:
        _teardown()


@pytest.mark.anyio
async def test_login_wrong_password_401() -> None:
    user = FakeUser()
    session = FakeAsyncSession()
    session.queue(user)
    _setup(session)
    try:
        async with _client() as c:
            resp = await c.post(
                "/api/v1/auth/login",
                json={"email": "test@example.com", "password": "WrongPassword!"},
            )
        assert resp.status_code == 401
    finally:
        _teardown()


@pytest.mark.anyio
async def test_login_nonexistent_email_401() -> None:
    session = FakeAsyncSession()
    session.queue(None)  # no user found
    _setup(session)
    try:
        async with _client() as c:
            resp = await c.post(
                "/api/v1/auth/login",
                json={"email": "ghost@example.com", "password": "Whatever1!"},
            )
        assert resp.status_code == 401
    finally:
        _teardown()


@pytest.mark.anyio
async def test_login_disabled_user_401() -> None:
    user = FakeUser(status="disabled")
    session = FakeAsyncSession()
    session.queue(user)
    _setup(session)
    try:
        async with _client() as c:
            resp = await c.post(
                "/api/v1/auth/login",
                json={"email": "test@example.com", "password": "Correct!Pass1"},
            )
        assert resp.status_code == 401
    finally:
        _teardown()


@pytest.mark.anyio
async def test_login_generic_error_message() -> None:
    """Wrong email and wrong password must produce the same message."""
    session1 = FakeAsyncSession()
    session1.queue(None)
    _setup(session1)
    try:
        async with _client() as c:
            r1 = await c.post(
                "/api/v1/auth/login",
                json={"email": "ghost@example.com", "password": "x"},
            )
    finally:
        _teardown()

    user = FakeUser()
    session2 = FakeAsyncSession()
    session2.queue(user)
    _setup(session2)
    try:
        async with _client() as c:
            r2 = await c.post(
                "/api/v1/auth/login",
                json={"email": "test@example.com", "password": "WrongPassword!"},
            )
    finally:
        _teardown()

    assert r1.status_code == 401
    assert r2.status_code == 401
    assert r1.json()["detail"] == r2.json()["detail"]
    assert "email" not in r1.json()["detail"].lower()
    assert "password" not in r1.json()["detail"].lower()


# ── Token / auth dependency tests ────────────────────────────


@pytest.mark.anyio
async def test_protected_endpoint_no_token_401() -> None:
    """Request without Authorization header → 401."""
    session = FakeAsyncSession()
    _setup(session)
    try:
        async with _client() as c:
            resp = await c.get("/api/v1/dashboard/revenue-summary")
        assert resp.status_code == 401
    finally:
        _teardown()


@pytest.mark.anyio
async def test_protected_endpoint_expired_token_401() -> None:
    payload = {
        "sub": "user-id",
        "tenant_id": str(DEFAULT_TENANT_ID),
        "role": "owner",
        "exp": datetime.now(tz=UTC) - timedelta(hours=1),
    }
    token = jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")
    session = FakeAsyncSession()
    _setup(session)
    try:
        async with _client(headers={"Authorization": f"Bearer {token}"}) as c:
            resp = await c.get("/api/v1/dashboard/revenue-summary")
        assert resp.status_code == 401
        assert "expired" in resp.json()["detail"].lower()
    finally:
        _teardown()


@pytest.mark.anyio
async def test_protected_endpoint_invalid_token_401() -> None:
    session = FakeAsyncSession()
    _setup(session)
    try:
        async with _client(headers={"Authorization": "Bearer not.a.real.jwt"}) as c:
            resp = await c.get("/api/v1/dashboard/revenue-summary")
        assert resp.status_code == 401
    finally:
        _teardown()


@pytest.mark.anyio
async def test_malformed_jwt_missing_claims_401() -> None:
    """JWT that lacks required claims (sub, tenant_id, role) → 401."""
    # Token with valid signature but missing 'role' claim
    incomplete_payload = {
        "sub": str(uuid.uuid4()),
        "exp": datetime.now(tz=UTC) + timedelta(hours=1),
    }
    token = jwt.encode(incomplete_payload, TEST_JWT_SECRET, algorithm="HS256")
    session = FakeAsyncSession()
    _setup(session)
    try:
        async with _client(headers={"Authorization": f"Bearer {token}"}) as c:
            resp = await c.get("/api/v1/dashboard/revenue-summary")
        assert resp.status_code == 401
    finally:
        _teardown()


@pytest.mark.anyio
async def test_malformed_jwt_invalid_role_401() -> None:
    payload = {
        "sub": str(uuid.uuid4()),
        "tenant_id": str(DEFAULT_TENANT_ID),
        "role": "agent",
        "exp": datetime.now(tz=UTC) + timedelta(hours=1),
    }
    token = jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")
    session = FakeAsyncSession()
    _setup(session)
    try:
        async with _client(headers={"Authorization": f"Bearer {token}"}) as c:
            resp = await c.get("/api/v1/dashboard/revenue-summary")
        assert resp.status_code == 401
    finally:
        _teardown()


@pytest.mark.anyio
async def test_malformed_jwt_invalid_uuid_claims_401() -> None:
    payload = {
        "sub": "not-a-uuid",
        "tenant_id": str(DEFAULT_TENANT_ID),
        "role": "owner",
        "exp": datetime.now(tz=UTC) + timedelta(hours=1),
    }
    token = jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")
    session = FakeAsyncSession()
    _setup(session)
    try:
        async with _client(headers={"Authorization": f"Bearer {token}"}) as c:
            resp = await c.get("/api/v1/dashboard/revenue-summary")
        assert resp.status_code == 401
    finally:
        _teardown()


# ── Role enforcement tests ───────────────────────────────────


@pytest.mark.anyio
async def test_role_enforcement_forbidden_403() -> None:
    """Warehouse role cannot access payments (finance-only)."""
    session = FakeAsyncSession()
    _setup(session)
    try:
        async with _client(headers=auth_header("warehouse")) as c:
            resp = await c.get("/api/v1/payments")
        assert resp.status_code == 403
        assert any(
            getattr(entry, "action", None) == "auth.forbidden"
            and getattr(entry, "entity_id", None) == "/api/v1/payments"
            for entry in session.added
        )
    finally:
        _teardown()


@pytest.mark.anyio
async def test_owner_bypasses_role_check() -> None:
    """Owner can access any endpoint regardless of role requirements."""
    session = FakeAsyncSession()
    # set_tenant + count scalar + items scalars
    session.queue(None)
    session.queue(0)
    session.queue([])
    _setup(session)
    try:
        async with _client(headers=auth_header("owner")) as c:
            resp = await c.get("/api/v1/payments")
        # Owner should not get 401 or 403; 500 from fake DB is acceptable
        assert resp.status_code not in (401, 403)
    finally:
        _teardown()


@pytest.mark.anyio
async def test_me_endpoint_returns_user_info() -> None:
    user_id = uuid.uuid4()
    user = FakeUser(
        id=user_id, email="me@example.com", display_name="Me", role="sales", status="active"
    )
    token = make_test_token(role="sales", user_id=str(user_id))
    session = FakeAsyncSession()
    session.queue(user)  # get_user query
    _setup(session)
    try:
        async with _client(headers={"Authorization": f"Bearer {token}"}) as c:
            resp = await c.get("/api/v1/auth/me")
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == str(user_id)
        assert body["email"] == "me@example.com"
        assert body["display_name"] == "Me"
        assert body["role"] == "sales"
        assert body["status"] == "active"
    finally:
        _teardown()


@pytest.mark.anyio
async def test_warehouse_cannot_access_invoices_403() -> None:
    session = FakeAsyncSession()
    _setup(session)
    try:
        async with _client(headers=auth_header("warehouse")) as c:
            resp = await c.get("/api/v1/invoices")
        assert resp.status_code == 403
    finally:
        _teardown()


@pytest.mark.anyio
async def test_finance_can_access_invoices() -> None:
    session = FakeAsyncSession()
    session.queue(None)  # set_tenant
    session.queue(0)  # count
    session.queue([])  # items
    _setup(session)
    try:
        async with _client(headers=auth_header("finance")) as c:
            resp = await c.get("/api/v1/invoices")
        # Should not be 401 or 403; 500 from fake DB is acceptable
        assert resp.status_code not in (401, 403)
    finally:
        _teardown()


@pytest.mark.anyio
async def test_sales_can_access_customers() -> None:
    session = FakeAsyncSession()
    session.queue(None)  # set_tenant
    session.queue(0)  # count
    session.queue([])  # items
    _setup(session)
    try:
        async with _client(headers=auth_header("sales")) as c:
            resp = await c.get("/api/v1/customers")
        # Should not be 401 or 403; 500 from fake DB is acceptable
        assert resp.status_code not in (401, 403)
    finally:
        _teardown()


@pytest.mark.anyio
async def test_sales_cannot_access_payments_403() -> None:
    session = FakeAsyncSession()
    _setup(session)
    try:
        async with _client(headers=auth_header("sales")) as c:
            resp = await c.get("/api/v1/payments")
        assert resp.status_code == 403
    finally:
        _teardown()


@pytest.mark.anyio
async def test_finance_cannot_write_customers_403() -> None:
    """Finance can read customers but cannot create (sales-only write)."""
    session = FakeAsyncSession()
    _setup(session)
    try:
        async with _client(headers=auth_header("finance")) as c:
            resp = await c.post(
                "/api/v1/customers",
                json={
                    "company_name": "Corp",
                    "billing_address": "Taipei",
                    "contact_name": "A",
                    "contact_phone": "0912345678",
                    "contact_email": "a@b.com",
                },
            )
        assert resp.status_code == 403
    finally:
        _teardown()


# ── Public endpoint tests ────────────────────────────────────


@pytest.mark.anyio
async def test_health_is_public() -> None:
    """Health endpoint must be accessible without auth."""
    async with _client() as c:
        resp = await c.get("/api/v1/health")
    assert resp.status_code == 200
