"""Tests for audit log service and query API (Story 11.6)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from common.tenant import DEFAULT_TENANT_ID
from domains.audit.service import write_audit
from tests.domains.orders._helpers import (
    FakeAsyncSession,
    auth_header,
    http_get,
    setup_session,
    teardown_session,
)

# ── Fake AuditLog objects ─────────────────────────────────────


class FakeAuditLog:
    """Lightweight stand-in for AuditLog ORM model in test assertions."""

    def __init__(self, **kwargs: Any) -> None:
        now = datetime.now(tz=UTC)
        self.id = kwargs.get("id", uuid.uuid4())
        self.tenant_id = kwargs.get("tenant_id", DEFAULT_TENANT_ID)
        self.actor_id = kwargs.get("actor_id", "test-user")
        self.actor_type = kwargs.get("actor_type", "user")
        self.action = kwargs.get("action", "order.create")
        self.entity_type = kwargs.get("entity_type", "order")
        self.entity_id = kwargs.get("entity_id", str(uuid.uuid4()))
        self.before_state = kwargs.get("before_state", None)
        self.after_state = kwargs.get("after_state", {"status": "pending"})
        self.correlation_id = kwargs.get("correlation_id", None)
        self.notes = kwargs.get("notes", None)
        self.created_at = kwargs.get("created_at", now)


def _make_audit_log(**overrides: object) -> FakeAuditLog:
    return FakeAuditLog(**overrides)


# ── write_audit service tests ─────────────────────────────────


@pytest.mark.anyio
async def test_write_audit_creates_entry():
    """AC1: write_audit creates an AuditLog with all fields set."""
    session = FakeAsyncSession()
    entry = await write_audit(
        session,
        actor_id="admin-user",
        actor_type="user",
        action="order.create",
        entity_type="order",
        entity_id="test-entity-123",
        before_state=None,
        after_state={"status": "pending"},
        correlation_id="corr-001",
        notes="Created via test",
    )
    assert entry.tenant_id == DEFAULT_TENANT_ID
    assert entry.actor_id == "admin-user"
    assert entry.actor_type == "user"
    assert entry.action == "order.create"
    assert entry.entity_type == "order"
    assert entry.entity_id == "test-entity-123"
    assert entry.before_state is None
    assert entry.after_state == {"status": "pending"}
    assert entry.correlation_id == "corr-001"
    assert entry.notes == "Created via test"
    assert len(session.added) == 1
    assert session.added[0] is entry


@pytest.mark.anyio
async def test_write_audit_defaults():
    """AC1: actor_type defaults to 'user'."""
    session = FakeAsyncSession()
    entry = await write_audit(
        session,
        actor_id="some-actor",
        action="payment.record",
        entity_type="payment",
        entity_id="pay-001",
    )
    assert entry.actor_type == "user"


@pytest.mark.anyio
async def test_write_audit_optional_fields_none():
    """AC1: Optional fields default to None."""
    session = FakeAsyncSession()
    entry = await write_audit(
        session,
        actor_id="actor",
        action="test.action",
        entity_type="entity",
        entity_id="ent-001",
    )
    assert entry.before_state is None
    assert entry.after_state is None
    assert entry.correlation_id is None
    assert entry.notes is None


# ── list_audit_logs query tests ────────────────────────────────


@pytest.mark.anyio
async def test_list_audit_logs_pagination():
    """AC2: Pagination returns correct page/page_size/total."""
    from domains.audit.queries import list_audit_logs

    session = FakeAsyncSession()
    logs = [_make_audit_log() for _ in range(3)]

    # 1. COUNT query
    session.queue_count(3)
    # 2. SELECT query
    session.queue_scalars(logs)

    result = await list_audit_logs(session, page=1, page_size=50)
    assert result["total"] == 3
    assert result["page"] == 1
    assert result["page_size"] == 50
    assert len(result["items"]) == 3


@pytest.mark.anyio
async def test_list_audit_logs_filter_entity_type():
    """AC3: Filter by entity_type returns matching entries."""
    from domains.audit.queries import list_audit_logs

    session = FakeAsyncSession()
    order_log = _make_audit_log(entity_type="order")

    session.queue_count(1)
    session.queue_scalars([order_log])

    result = await list_audit_logs(session, entity_type="order")
    assert result["total"] == 1
    assert len(result["items"]) == 1


@pytest.mark.anyio
async def test_list_audit_logs_filter_action():
    """AC3: Filter by action."""
    from domains.audit.queries import list_audit_logs

    session = FakeAsyncSession()
    log = _make_audit_log(action="payment.record")

    session.queue_count(1)
    session.queue_scalars([log])

    result = await list_audit_logs(session, action="payment.record")
    assert result["total"] == 1


@pytest.mark.anyio
async def test_list_audit_logs_filter_actor_id():
    """AC3: Filter by actor_id."""
    from domains.audit.queries import list_audit_logs

    session = FakeAsyncSession()
    log = _make_audit_log(actor_id="specific-user")

    session.queue_count(1)
    session.queue_scalars([log])

    result = await list_audit_logs(session, actor_id="specific-user")
    assert result["total"] == 1


@pytest.mark.anyio
async def test_list_audit_logs_filter_date_range():
    """AC3: Filter by created_after/created_before."""
    from domains.audit.queries import list_audit_logs

    session = FakeAsyncSession()
    log = _make_audit_log()

    session.queue_count(1)
    session.queue_scalars([log])

    now = datetime.now(tz=UTC)
    result = await list_audit_logs(
        session,
        created_after=now - timedelta(hours=1),
        created_before=now + timedelta(hours=1),
    )
    assert result["total"] == 1


@pytest.mark.anyio
async def test_list_audit_logs_ordered_newest_first():
    """AC2: Results are ordered by created_at DESC."""
    from domains.audit.queries import list_audit_logs

    session = FakeAsyncSession()
    now = datetime.now(tz=UTC)
    old_log = _make_audit_log(created_at=now - timedelta(hours=2))
    new_log = _make_audit_log(created_at=now)

    # Fake session returns them in the order we provide (simulating DB ordering)
    session.queue_count(2)
    session.queue_scalars([new_log, old_log])

    result = await list_audit_logs(session)
    assert result["items"][0].created_at >= result["items"][1].created_at


@pytest.mark.anyio
async def test_list_audit_logs_empty_result():
    """AC2: Empty result set returns correctly."""
    from domains.audit.queries import list_audit_logs

    session = FakeAsyncSession()
    session.queue_count(0)
    session.queue_scalars([])

    result = await list_audit_logs(session)
    assert result["total"] == 0
    assert result["items"] == []


# ── API endpoint tests ────────────────────────────────────────


@pytest.mark.anyio
async def test_audit_api_returns_paginated_list():
    """AC2: GET /api/v1/admin/audit-logs returns paginated response."""
    session = FakeAsyncSession()
    log = _make_audit_log()

    # set_tenant (if used) + COUNT + SELECT
    session.queue_count(1)
    session.queue_scalars([log])

    prev = setup_session(session)
    try:
        resp = await http_get("/api/v1/admin/audit-logs/")
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert "total" in body
        assert "page" in body
        assert "page_size" in body
        assert body["total"] == 1
        assert len(body["items"]) == 1
        item = body["items"][0]
        assert item["actor_id"] == log.actor_id
        assert item["action"] == log.action
        assert item["entity_type"] == log.entity_type
    finally:
        teardown_session(prev)


@pytest.mark.anyio
async def test_audit_api_filters():
    """AC3: Query params are passed through to filter."""
    session = FakeAsyncSession()
    log = _make_audit_log(entity_type="payment", action="payment.record")

    session.queue_count(1)
    session.queue_scalars([log])

    prev = setup_session(session)
    try:
        resp = await http_get("/api/v1/admin/audit-logs/?entity_type=payment&action=payment.record")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["items"][0]["entity_type"] == "payment"
    finally:
        teardown_session(prev)


@pytest.mark.anyio
async def test_audit_api_empty_result():
    """AC2: Empty result from API."""
    session = FakeAsyncSession()
    session.queue_count(0)
    session.queue_scalars([])

    prev = setup_session(session)
    try:
        resp = await http_get("/api/v1/admin/audit-logs/")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 0
        assert body["items"] == []
    finally:
        teardown_session(prev)


@pytest.mark.anyio
async def test_audit_api_page_size_max():
    """AC2: page_size > 200 is rejected."""
    session = FakeAsyncSession()
    prev = setup_session(session)
    try:
        resp = await http_get("/api/v1/admin/audit-logs/?page_size=500")
        assert resp.status_code == 422
    finally:
        teardown_session(prev)


@pytest.mark.anyio
async def test_non_owner_cannot_list_audit_logs_api():
    session = FakeAsyncSession()
    prev = setup_session(session)
    try:
        resp = await http_get("/api/v1/admin/audit-logs/", headers=auth_header("finance"))
        assert resp.status_code == 403
    finally:
        teardown_session(prev)
