"""Tests for POST /api/v1/inventory/adjustments — Story 4.4."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

from httpx import ASGITransport, AsyncClient

from app.main import app
from common.database import get_db
from tests.domains.orders._helpers import auth_header

# ── Fake objects ──────────────────────────────────────────────


class FakeInventoryStock:
    def __init__(
        self,
        *,
        product_id: uuid.UUID | None = None,
        warehouse_id: uuid.UUID | None = None,
        quantity: int = 50,
        reorder_point: int = 10,
    ):
        self.id = uuid.uuid4()
        self.tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        self.product_id = product_id or uuid.uuid4()
        self.warehouse_id = warehouse_id or uuid.uuid4()
        self.quantity = quantity
        self.reorder_point = reorder_point
        self.updated_at = datetime.now(tz=UTC)


class FakeResult:
    def __init__(self, obj: object | None):
        self._obj = obj

    def scalar_one_or_none(self) -> object | None:
        return self._obj


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
        return FakeResult(None)

    async def flush(self) -> None:
        pass

    async def commit(self) -> None:
        pass

    def queue_scalar(self, obj: object | None) -> None:
        self._execute_results.append(FakeResult(obj))


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


async def _post(path: str, json: dict) -> Any:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", headers=auth_header()) as c:
        return await c.post(path, json=json)


async def _get(path: str) -> Any:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", headers=auth_header()) as c:
        return await c.get(path)


# ── Reason codes tests ───────────────────────────────────────


async def test_list_reason_codes() -> None:
    resp = await _get("/api/v1/inventory/reason-codes")
    assert resp.status_code == 200
    body = resp.json()
    values = [item["value"] for item in body["items"]]
    assert "received" in values
    assert "damaged" in values
    assert "transfer_out" in values
    assert "physical_count" in values

    user_codes = [i for i in body["items"] if i["user_selectable"]]
    system_codes = [i for i in body["items"] if not i["user_selectable"]]
    assert len(user_codes) == 5
    assert len(system_codes) == 6


async def test_reason_codes_user_selectable_excludes_system() -> None:
    resp = await _get("/api/v1/inventory/reason-codes")
    body = resp.json()
    user_values = {i["value"] for i in body["items"] if i["user_selectable"]}
    assert "transfer_out" not in user_values
    assert "transfer_in" not in user_values
    assert "supplier_delivery" not in user_values
    assert "physical_count" not in user_values


# ── Adjustment success tests ─────────────────────────────────


async def test_create_adjustment_success() -> None:
    product_id = uuid.uuid4()
    warehouse_id = uuid.uuid4()
    stock = FakeInventoryStock(
        product_id=product_id,
        warehouse_id=warehouse_id,
        quantity=50,
        reorder_point=10,
    )

    session = FakeAsyncSession()
    session.queue_scalar(stock)  # inventory stock lookup
    session.queue_scalar(None)  # reorder alert lookup

    prev = _setup(session)
    try:
        resp = await _post(
            "/api/v1/inventory/adjustments",
            json={
                "product_id": str(product_id),
                "warehouse_id": str(warehouse_id),
                "quantity_change": -5,
                "reason_code": "damaged",
                "notes": "Found 5 broken items",
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["quantity_change"] == -5
        assert body["reason_code"] == "damaged"
        assert body["updated_stock"] == 45
        assert body["notes"] == "Found 5 broken items"
    finally:
        _teardown(prev)


async def test_create_adjustment_add_stock() -> None:
    product_id = uuid.uuid4()
    warehouse_id = uuid.uuid4()
    stock = FakeInventoryStock(
        product_id=product_id,
        warehouse_id=warehouse_id,
        quantity=20,
        reorder_point=10,
    )

    session = FakeAsyncSession()
    session.queue_scalar(stock)  # inventory stock lookup
    session.queue_scalar(None)  # reorder alert lookup (resolved)

    prev = _setup(session)
    try:
        resp = await _post(
            "/api/v1/inventory/adjustments",
            json={
                "product_id": str(product_id),
                "warehouse_id": str(warehouse_id),
                "quantity_change": 30,
                "reason_code": "received",
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["quantity_change"] == 30
        assert body["updated_stock"] == 50
    finally:
        _teardown(prev)


# ── Validation tests ─────────────────────────────────────────


async def test_insufficient_stock_returns_409() -> None:
    product_id = uuid.uuid4()
    warehouse_id = uuid.uuid4()
    stock = FakeInventoryStock(
        product_id=product_id,
        warehouse_id=warehouse_id,
        quantity=10,
    )

    session = FakeAsyncSession()
    session.queue_scalar(stock)

    prev = _setup(session)
    try:
        resp = await _post(
            "/api/v1/inventory/adjustments",
            json={
                "product_id": str(product_id),
                "warehouse_id": str(warehouse_id),
                "quantity_change": -20,
                "reason_code": "damaged",
            },
        )
        assert resp.status_code == 409
        body = resp.json()
        assert body["detail"]["available"] == 10
        assert body["detail"]["requested"] == 20
    finally:
        _teardown(prev)


async def test_zero_quantity_change_returns_422() -> None:
    product_id = uuid.uuid4()
    warehouse_id = uuid.uuid4()
    stock = FakeInventoryStock(
        product_id=product_id,
        warehouse_id=warehouse_id,
    )

    session = FakeAsyncSession()
    session.queue_scalar(stock)

    prev = _setup(session)
    try:
        resp = await _post(
            "/api/v1/inventory/adjustments",
            json={
                "product_id": str(product_id),
                "warehouse_id": str(warehouse_id),
                "quantity_change": 0,
                "reason_code": "correction",
            },
        )
        assert resp.status_code == 422
    finally:
        _teardown(prev)


async def test_system_reason_code_rejected() -> None:
    """System-only reason codes must not be accepted from the API."""
    resp = await _post(
        "/api/v1/inventory/adjustments",
        json={
            "product_id": str(uuid.uuid4()),
            "warehouse_id": str(uuid.uuid4()),
            "quantity_change": 10,
            "reason_code": "transfer_in",
        },
    )
    assert resp.status_code == 422
    assert "Invalid reason code" in resp.json()["detail"]


async def test_invalid_reason_code_rejected() -> None:
    resp = await _post(
        "/api/v1/inventory/adjustments",
        json={
            "product_id": str(uuid.uuid4()),
            "warehouse_id": str(uuid.uuid4()),
            "quantity_change": 5,
            "reason_code": "nonexistent",
        },
    )
    assert resp.status_code == 422


async def test_missing_fields_returns_422() -> None:
    resp = await _post(
        "/api/v1/inventory/adjustments",
        json={
            "product_id": str(uuid.uuid4()),
            # missing warehouse_id, quantity_change, reason_code
        },
    )
    assert resp.status_code == 422


# ── Audit trail tests ────────────────────────────────────────


async def test_audit_log_created_on_adjustment() -> None:
    product_id = uuid.uuid4()
    warehouse_id = uuid.uuid4()
    stock = FakeInventoryStock(
        product_id=product_id,
        warehouse_id=warehouse_id,
        quantity=100,
        reorder_point=10,
    )

    session = FakeAsyncSession()
    session.queue_scalar(stock)  # inventory stock lookup
    session.queue_scalar(None)  # reorder alert lookup

    prev = _setup(session)
    try:
        resp = await _post(
            "/api/v1/inventory/adjustments",
            json={
                "product_id": str(product_id),
                "warehouse_id": str(warehouse_id),
                "quantity_change": -10,
                "reason_code": "damaged",
            },
        )
        assert resp.status_code == 201
        # Verify audit log was added to session
        audit_logs = [
            o for o in session.added if hasattr(o, "action") and o.action == "stock_adjustment"
        ]
        assert len(audit_logs) == 1
        audit = audit_logs[0]
        assert audit.before_state == {"quantity": 100}
        assert audit.after_state == {"quantity": 90}
    finally:
        _teardown(prev)


async def test_stock_adjustment_record_created() -> None:
    product_id = uuid.uuid4()
    warehouse_id = uuid.uuid4()
    stock = FakeInventoryStock(
        product_id=product_id,
        warehouse_id=warehouse_id,
        quantity=50,
    )

    session = FakeAsyncSession()
    session.queue_scalar(stock)
    session.queue_scalar(None)  # reorder alert

    prev = _setup(session)
    try:
        resp = await _post(
            "/api/v1/inventory/adjustments",
            json={
                "product_id": str(product_id),
                "warehouse_id": str(warehouse_id),
                "quantity_change": 10,
                "reason_code": "received",
            },
        )
        assert resp.status_code == 201
        # Verify StockAdjustment record was added
        from common.models.stock_adjustment import StockAdjustment

        adjustments = [o for o in session.added if isinstance(o, StockAdjustment)]
        assert len(adjustments) == 1
        assert adjustments[0].quantity_change == 10
        assert adjustments[0].reason_code.value == "RECEIVED"
    finally:
        _teardown(prev)
