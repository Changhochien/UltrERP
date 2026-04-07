"""Tests for reorder alert endpoints — Story 4.3."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

from httpx import ASGITransport, AsyncClient

from app.main import app
from common.database import get_db
from common.models.reorder_alert import AlertStatus
from tests.domains.orders._helpers import auth_header

# ── Fake objects ──────────────────────────────────────────────


class FakeRow:
    """Simulates a Row returned by session.execute() with labeled columns."""

    def __init__(self, **kwargs: Any) -> None:
        for k, v in kwargs.items():
            setattr(self, k, v)


class FakeResult:
    def __init__(
        self,
        obj: object | None = None,
        *,
        rows: list[Any] | None = None,
        scalar_val: Any = None,
    ):
        self._obj = obj
        self._rows = rows
        self._scalar_val = scalar_val

    def scalar_one_or_none(self) -> object | None:
        return self._obj

    def scalar(self) -> Any:
        return self._scalar_val

    def all(self) -> list[Any]:
        return self._rows if self._rows is not None else []


class FakeReorderAlert:
    """Mutable fake alert for acknowledge tests."""

    def __init__(
        self,
        *,
        alert_id: uuid.UUID | None = None,
        status: AlertStatus = AlertStatus.PENDING,
    ) -> None:
        self.id = alert_id or uuid.uuid4()
        self.tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        self.product_id = uuid.uuid4()
        self.warehouse_id = uuid.uuid4()
        self.current_stock = 5
        self.reorder_point = 10
        self.status = status
        self.created_at = datetime.now(tz=UTC)
        self.acknowledged_at = None
        self.acknowledged_by = None


class FakeAsyncSession:
    def __init__(self) -> None:
        self._execute_results: list[object] = []
        self._idx = 0
        self.added: list[object] = []

    def add(self, obj: object) -> None:
        self.added.append(obj)

    async def execute(self, _stmt: object) -> object:
        if self._idx < len(self._execute_results):
            result = self._execute_results[self._idx]
            self._idx += 1
            return result
        return FakeResult()

    async def flush(self) -> None:
        pass

    async def commit(self) -> None:
        pass

    def queue_result(self, result: object) -> None:
        self._execute_results.append(result)


# ── Helper ────────────────────────────────────────────────────

_MISSING = object()


def _setup(session: FakeAsyncSession) -> Any:
    async def _override() -> AsyncGenerator[FakeAsyncSession, None]:
        yield session

    previous = app.dependency_overrides.get(get_db, _MISSING)
    app.dependency_overrides[get_db] = _override
    return previous


def _teardown(previous: Any) -> None:
    if previous is _MISSING:
        app.dependency_overrides.pop(get_db, None)
    else:
        app.dependency_overrides[get_db] = previous


async def _get(path: str, *, role: str = "owner") -> Any:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", headers=auth_header(role)) as c:
        return await c.get(path)


async def _put(path: str) -> Any:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", headers=auth_header()) as c:
        return await c.put(path)


# ── List alerts tests ────────────────────────────────────────


async def test_list_alerts_empty() -> None:
    session = FakeAsyncSession()
    # count query returns 0
    session.queue_result(FakeResult(scalar_val=0))
    # data query returns empty
    session.queue_result(FakeResult(rows=[]))

    prev = _setup(session)
    try:
        resp = await _get("/api/v1/inventory/alerts/reorder")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 0
        assert body["items"] == []
    finally:
        _teardown(prev)


async def test_list_alerts_returns_items() -> None:
    session = FakeAsyncSession()
    now = datetime.now(tz=UTC)
    alert_id = uuid.uuid4()
    product_id = uuid.uuid4()
    warehouse_id = uuid.uuid4()

    # count query
    session.queue_result(FakeResult(scalar_val=1))
    # data query
    session.queue_result(
        FakeResult(
            rows=[
                FakeRow(
                    id=alert_id,
                    product_id=product_id,
                    product_name="Widget A",
                    warehouse_id=warehouse_id,
                    warehouse_name="Main",
                    current_stock=3,
                    reorder_point=10,
                    status=AlertStatus.PENDING,
                    created_at=now,
                    acknowledged_at=None,
                    acknowledged_by=None,
                ),
            ]
        )
    )

    prev = _setup(session)
    try:
        resp = await _get("/api/v1/inventory/alerts/reorder")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        item = body["items"][0]
        assert item["product_name"] == "Widget A"
        assert item["warehouse_name"] == "Main"
        assert item["current_stock"] == 3
        assert item["reorder_point"] == 10
        assert item["status"] == "pending"
    finally:
        _teardown(prev)


async def test_list_alerts_allows_admin_role() -> None:
    session = FakeAsyncSession()
    session.queue_result(FakeResult(scalar_val=0))
    session.queue_result(FakeResult(rows=[]))

    prev = _setup(session)
    try:
        resp = await _get("/api/v1/inventory/alerts/reorder", role="admin")
        assert resp.status_code == 200
    finally:
        _teardown(prev)


async def test_list_alerts_rejects_finance_role() -> None:
    resp = await _get("/api/v1/inventory/alerts/reorder", role="finance")
    assert resp.status_code == 403


async def test_list_alerts_with_status_filter() -> None:
    session = FakeAsyncSession()
    session.queue_result(FakeResult(scalar_val=0))
    session.queue_result(FakeResult(rows=[]))

    prev = _setup(session)
    try:
        resp = await _get("/api/v1/inventory/alerts/reorder?status=pending")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 0
    finally:
        _teardown(prev)


async def test_list_alerts_invalid_status_rejected() -> None:
    resp = await _get("/api/v1/inventory/alerts/reorder?status=invalid")
    assert resp.status_code == 422


async def test_list_alerts_with_warehouse_filter() -> None:
    session = FakeAsyncSession()
    wh_id = uuid.uuid4()
    session.queue_result(FakeResult(scalar_val=0))
    session.queue_result(FakeResult(rows=[]))

    prev = _setup(session)
    try:
        resp = await _get(f"/api/v1/inventory/alerts/reorder?warehouse_id={wh_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 0
    finally:
        _teardown(prev)


async def test_list_alerts_limit_exceeds_max_returns_422() -> None:
    resp = await _get("/api/v1/inventory/alerts/reorder?limit=999")
    assert resp.status_code == 422


async def test_list_alerts_negative_offset_returns_422() -> None:
    resp = await _get("/api/v1/inventory/alerts/reorder?offset=-1")
    assert resp.status_code == 422


# ── Acknowledge alert tests ──────────────────────────────────


async def test_acknowledge_alert_success() -> None:
    session = FakeAsyncSession()
    alert = FakeReorderAlert()

    # acknowledge_alert does one select
    session.queue_result(FakeResult(obj=alert))

    prev = _setup(session)
    try:
        resp = await _put(f"/api/v1/inventory/alerts/reorder/{alert.id}/acknowledge")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "acknowledged"
        assert body["acknowledged_by"] == "system"
        assert body["acknowledged_at"] is not None
    finally:
        _teardown(prev)


async def test_acknowledge_alert_not_found() -> None:
    session = FakeAsyncSession()
    # No alert found
    session.queue_result(FakeResult(obj=None))

    prev = _setup(session)
    try:
        fake_id = uuid.uuid4()
        resp = await _put(f"/api/v1/inventory/alerts/reorder/{fake_id}/acknowledge")
        assert resp.status_code == 200
        body = resp.json()
        assert body.get("status") == "already_resolved"
    finally:
        _teardown(prev)


async def test_acknowledge_resolved_alert_returns_200_already_resolved() -> None:
    session = FakeAsyncSession()
    alert = FakeReorderAlert(status=AlertStatus.RESOLVED)
    session.queue_result(FakeResult(obj=alert))

    prev = _setup(session)
    try:
        resp = await _put(f"/api/v1/inventory/alerts/reorder/{alert.id}/acknowledge")
        assert resp.status_code == 200
        body = resp.json()
        assert body.get("status") == "already_resolved"
    finally:
        _teardown(prev)


async def test_acknowledge_invalid_uuid_returns_422() -> None:
    resp = await _put("/api/v1/inventory/alerts/reorder/not-a-uuid/acknowledge")
    assert resp.status_code == 422
