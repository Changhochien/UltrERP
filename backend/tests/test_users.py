"""Tests for user CRUD (Story 11.1)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest

from common.tenant import DEFAULT_TENANT_ID
from domains.users.auth import hash_password, verify_password
from domains.users.service import create_user, get_user, get_user_by_email, list_users, update_user
from tests.domains.orders._helpers import (
    FakeAsyncSession,
    auth_header,
    http_get,
    http_patch,
    http_post,
    make_test_token,
    setup_session,
    teardown_session,
)

# ── Fake User objects ─────────────────────────────────────────


class FakeUser:
    """Lightweight stand-in for User ORM model."""

    def __init__(self, **kwargs: Any) -> None:
        now = datetime.now(tz=UTC)
        self.id = kwargs.get("id", uuid.uuid4())
        self.tenant_id = kwargs.get("tenant_id", DEFAULT_TENANT_ID)
        self.email = kwargs.get("email", "alice@example.com")
        self.password_hash = kwargs.get("password_hash", "$2b$12$fakehash")
        self.display_name = kwargs.get("display_name", "Alice")
        self.role = kwargs.get("role", "owner")
        self.status = kwargs.get("status", "active")
        self.created_at = kwargs.get("created_at", now)
        self.updated_at = kwargs.get("updated_at", None)


# ── Password hashing tests ───────────────────────────────────


def test_hash_password_returns_bcrypt_hash():
    hashed = hash_password("mysecretpw")
    assert hashed.startswith("$2b$")
    assert len(hashed) == 60


def test_verify_password_correct():
    hashed = hash_password("correcthorse")
    assert verify_password("correcthorse", hashed) is True


def test_verify_password_incorrect():
    hashed = hash_password("correcthorse")
    assert verify_password("wrongpassword", hashed) is False


# ── Service-layer tests ──────────────────────────────────────


@pytest.mark.asyncio
async def test_create_user_service():
    session = FakeAsyncSession()
    user = await create_user(
        session,
        email="bob@example.com",
        password="strongpass123",
        display_name="Bob",
        role="finance",
    )
    assert user.email == "bob@example.com"
    assert user.display_name == "Bob"
    assert user.role == "finance"
    assert user.password_hash.startswith("$2b$")
    # User + AuditLog both added
    assert len(session.added) == 2


@pytest.mark.asyncio
async def test_list_users_service():
    session = FakeAsyncSession()
    fake = FakeUser()
    session.queue_scalars([fake])
    result = await list_users(session)
    assert len(result) == 1
    assert result[0].email == "alice@example.com"


@pytest.mark.asyncio
async def test_get_user_service():
    session = FakeAsyncSession()
    fake = FakeUser()
    session.queue_scalar(fake)
    result = await get_user(session, fake.id)
    assert result is not None
    assert result.email == fake.email


@pytest.mark.asyncio
async def test_get_user_by_email_service():
    session = FakeAsyncSession()
    fake = FakeUser(email="find@example.com")
    session.queue_scalar(fake)
    result = await get_user_by_email(session, "find@example.com")
    assert result is not None
    assert result.email == "find@example.com"


@pytest.mark.asyncio
async def test_update_user_service():
    session = FakeAsyncSession()
    fake = FakeUser(role="sales")
    session.queue_scalar(fake)  # for get_user inside update_user
    result = await update_user(session, fake.id, role="finance")
    assert result is not None
    assert result.role == "finance"
    # AuditLog entry added
    assert any(getattr(obj, "action", None) == "user.update" for obj in session.added)


# ── API tests ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_user_api_success():
    session = FakeAsyncSession()
    previous = setup_session(session)
    try:
        resp = await http_post(
            "/api/v1/admin/users/",
            {
                "email": "new@example.com",
                "password": "longpassword99",
                "display_name": "New User",
                "role": "sales",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "new@example.com"
        assert data["role"] == "sales"
        assert data["status"] == "active"
        assert "password_hash" not in data
        assert "password" not in data
        assert "id" in data
    finally:
        teardown_session(previous)


@pytest.mark.asyncio
async def test_create_user_invalid_role_422():
    session = FakeAsyncSession()
    previous = setup_session(session)
    try:
        resp = await http_post(
            "/api/v1/admin/users/",
            {
                "email": "bad@example.com",
                "password": "longpassword99",
                "display_name": "Bad Role",
                "role": "superadmin",
            },
        )
        assert resp.status_code == 422
    finally:
        teardown_session(previous)


@pytest.mark.asyncio
async def test_create_user_short_password_422():
    session = FakeAsyncSession()
    previous = setup_session(session)
    try:
        resp = await http_post(
            "/api/v1/admin/users/",
            {
                "email": "short@example.com",
                "password": "abc",
                "display_name": "Short PW",
                "role": "owner",
            },
        )
        assert resp.status_code == 422
    finally:
        teardown_session(previous)


@pytest.mark.asyncio
async def test_list_users_api():
    session = FakeAsyncSession()
    fake = FakeUser()
    session.queue_scalars([fake])
    previous = setup_session(session)
    try:
        resp = await http_get("/api/v1/admin/users/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert "password_hash" not in data["items"][0]
    finally:
        teardown_session(previous)


@pytest.mark.asyncio
async def test_get_user_api_200():
    session = FakeAsyncSession()
    fake = FakeUser()
    session.queue_scalar(fake)
    previous = setup_session(session)
    try:
        resp = await http_get(f"/api/v1/admin/users/{fake.id}")
        assert resp.status_code == 200
        assert resp.json()["email"] == "alice@example.com"
    finally:
        teardown_session(previous)


@pytest.mark.asyncio
async def test_get_user_api_404():
    session = FakeAsyncSession()
    session.queue_scalar(None)
    previous = setup_session(session)
    try:
        missing_id = uuid.uuid4()
        resp = await http_get(f"/api/v1/admin/users/{missing_id}")
        assert resp.status_code == 404
    finally:
        teardown_session(previous)


@pytest.mark.asyncio
async def test_update_user_api_role_change():
    session = FakeAsyncSession()
    fake = FakeUser(role="sales")
    session.queue_scalar(fake)  # for get_user inside update_user
    previous = setup_session(session)
    try:
        resp = await http_patch(
            f"/api/v1/admin/users/{fake.id}",
            {
                "role": "finance",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["role"] == "finance"
    finally:
        teardown_session(previous)


@pytest.mark.asyncio
async def test_update_user_api_password_reset():
    session = FakeAsyncSession()
    fake = FakeUser()
    session.queue_scalar(fake)
    previous = setup_session(session)
    try:
        resp = await http_patch(
            f"/api/v1/admin/users/{fake.id}",
            {
                "password": "newstrongpass99",
            },
        )
        assert resp.status_code == 200
        # Verify the password was re-hashed
        assert fake.password_hash.startswith("$2b$")
    finally:
        teardown_session(previous)


@pytest.mark.asyncio
async def test_update_user_creates_audit_log():
    session = FakeAsyncSession()
    fake = FakeUser(display_name="Old Name")
    session.queue_scalar(fake)
    previous = setup_session(session)
    try:
        resp = await http_patch(
            f"/api/v1/admin/users/{fake.id}",
            {
                "display_name": "New Name",
            },
        )
        assert resp.status_code == 200
        audit_entries: list[Any] = [
            obj for obj in session.added if getattr(obj, "action", None) == "user.update"
        ]
        assert len(audit_entries) == 1
        assert audit_entries[0].before_state == {"display_name": "Old Name"}
        assert audit_entries[0].after_state == {"display_name": "New Name"}
    finally:
        teardown_session(previous)


@pytest.mark.asyncio
async def test_non_owner_cannot_list_users_api():
    session = FakeAsyncSession()
    previous = setup_session(session)
    try:
        resp = await http_get("/api/v1/admin/users/", headers=auth_header("finance"))
        assert resp.status_code == 403
    finally:
        teardown_session(previous)


@pytest.mark.asyncio
async def test_create_user_api_audits_authenticated_owner():
    session = FakeAsyncSession()
    previous = setup_session(session)
    actor_id = str(uuid.uuid4())
    try:
        resp = await http_post(
            "/api/v1/admin/users/",
            {
                "email": "owner-audit@example.com",
                "password": "longpassword99",
                "display_name": "Owner Audit",
                "role": "sales",
            },
            headers={"Authorization": f"Bearer {make_test_token(role='owner', user_id=actor_id)}"},
        )
        assert resp.status_code == 201
        audit_entries: list[Any] = [
            obj for obj in session.added if getattr(obj, "action", None) == "user.create"
        ]
        assert len(audit_entries) == 1
        assert audit_entries[0].actor_id == actor_id
    finally:
        teardown_session(previous)
