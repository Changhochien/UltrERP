"""Tests for order status transitions — Story 5.5."""

from __future__ import annotations

import uuid

from ._helpers import (
    FakeAsyncSession,
    FakeInventoryStock,
    FakeOrder,
)
from ._helpers import (
    http_delete as _delete,
)
from ._helpers import (
    http_patch as _patch,
)
from ._helpers import (
    setup_session as _setup,
)
from ._helpers import (
    teardown_session as _teardown,
)

# ── Helpers ───────────────────────────────────────────────────


def _queue_status_update(session: FakeAsyncSession, order: FakeOrder):
    """Queue results for ship/fulfill transitions (no stock changes).

    Flow (ship/fulfill):
      1. set_tenant → scalar(None)
      2. order lookup (with_for_update) → scalar(order)
      3. flush (audit)
      4. get_order reload: set_tenant → scalar(None)
      5. get_order reload → scalar(order)
    """
    session.queue_scalar(None)  # set_tenant
    session.queue_scalar(order)  # order lookup
    session.queue_scalar(None)  # set_tenant (get_order)
    session.queue_scalar(order)  # get_order reload


def _queue_cancel_pending(session: FakeAsyncSession, order: FakeOrder):
    """Queue results for pending → cancelled transition (with stock restoration).

    Flow:
      1. set_tenant → scalar(None)
      2. order lookup (with_for_update + selectinload) → scalar(order)
      3. warehouse_id lookup: set_tenant → scalar(None), then warehouse query → scalar(uuid)
      4. order_lines lookup → scalars(order.lines)
      5. stock FOR UPDATE (per line) → scalar(FakeInventoryStock)
      6. flush (stock adjustment)
      7. flush (audit log)
    """
    session.queue_scalar(None)  # 1. set_tenant (update_order_status)
    session.queue_scalar(order)  # 2. order lookup (with selectinload)
    session.queue_scalar(None)  # 3. set_tenant (_get_default_warehouse_id)
    session.queue_scalar(order.tenant_id)  # 4. warehouse_id lookup
    session.queue_result(order.lines)  # 5. order_lines lookup
    for _line in order.lines:
        session.queue_scalar(FakeInventoryStock(quantity=100))  # 6. stock rows
    session.queue_scalar(None)  # 7. flush (stock)
    session.queue_scalar(None)  # 8. flush (audit)


# ── Valid transitions ─────────────────────────────────────────


async def test_ship_confirmed_order() -> None:
    """confirmed → shipped succeeds."""
    order = FakeOrder(status="confirmed")
    session = FakeAsyncSession()
    _queue_status_update(session, order)

    prev = _setup(session)
    try:
        resp = await _patch(
            f"/api/v1/orders/{order.id}/status",
            json={"new_status": "shipped"},
        )
        assert resp.status_code == 200
        assert order.status == "shipped"
    finally:
        _teardown(prev)


async def test_fulfill_shipped_order() -> None:
    """shipped → fulfilled succeeds."""
    order = FakeOrder(status="shipped")
    session = FakeAsyncSession()
    _queue_status_update(session, order)

    prev = _setup(session)
    try:
        resp = await _patch(
            f"/api/v1/orders/{order.id}/status",
            json={"new_status": "fulfilled"},
        )
        assert resp.status_code == 200
        assert order.status == "fulfilled"
    finally:
        _teardown(prev)


async def test_cancel_pending_order() -> None:
    """pending → cancelled succeeds."""
    order = FakeOrder(status="pending")
    session = FakeAsyncSession()
    _queue_cancel_pending(session, order)

    prev = _setup(session)
    try:
        resp = await _patch(
            f"/api/v1/orders/{order.id}/status",
            json={"new_status": "cancelled"},
        )
        assert resp.status_code == 200, f"got {resp.status_code}: {resp.json()}"
        assert order.status == "cancelled"
    finally:
        _teardown(prev)


# ── Invalid transitions ──────────────────────────────────────


async def test_ship_pending_order_returns_409() -> None:
    """pending → shipped is not allowed."""
    order = FakeOrder(status="pending")
    session = FakeAsyncSession()
    session.queue_scalar(None)  # set_tenant
    session.queue_scalar(order)  # order lookup

    prev = _setup(session)
    try:
        resp = await _patch(
            f"/api/v1/orders/{order.id}/status",
            json={"new_status": "shipped"},
        )
        assert resp.status_code == 409
        assert "Cannot transition" in resp.json()["detail"]
    finally:
        _teardown(prev)


async def test_fulfill_confirmed_order_returns_409() -> None:
    """confirmed → fulfilled is not allowed (must ship first)."""
    order = FakeOrder(status="confirmed")
    session = FakeAsyncSession()
    session.queue_scalar(None)  # set_tenant
    session.queue_scalar(order)  # order lookup

    prev = _setup(session)
    try:
        resp = await _patch(
            f"/api/v1/orders/{order.id}/status",
            json={"new_status": "fulfilled"},
        )
        assert resp.status_code == 409
        assert "Cannot transition" in resp.json()["detail"]
    finally:
        _teardown(prev)


async def test_cancel_confirmed_order_returns_409() -> None:
    """confirmed → cancelled is not allowed."""
    order = FakeOrder(status="confirmed")
    session = FakeAsyncSession()
    session.queue_scalar(None)  # set_tenant
    session.queue_scalar(order)  # order lookup

    prev = _setup(session)
    try:
        resp = await _patch(
            f"/api/v1/orders/{order.id}/status",
            json={"new_status": "cancelled"},
        )
        assert resp.status_code == 409
        assert "Cannot transition" in resp.json()["detail"]
    finally:
        _teardown(prev)


async def test_transition_from_fulfilled_returns_409() -> None:
    """fulfilled is a terminal state — no transitions allowed."""
    order = FakeOrder(status="fulfilled")
    session = FakeAsyncSession()
    session.queue_scalar(None)  # set_tenant
    session.queue_scalar(order)  # order lookup

    prev = _setup(session)
    try:
        resp = await _patch(
            f"/api/v1/orders/{order.id}/status",
            json={"new_status": "shipped"},
        )
        assert resp.status_code == 409
    finally:
        _teardown(prev)


async def test_transition_from_cancelled_returns_409() -> None:
    """cancelled is a terminal state — no transitions allowed."""
    order = FakeOrder(status="cancelled")
    session = FakeAsyncSession()
    session.queue_scalar(None)  # set_tenant
    session.queue_scalar(order)  # order lookup

    prev = _setup(session)
    try:
        resp = await _patch(
            f"/api/v1/orders/{order.id}/status",
            json={"new_status": "pending"},
        )
        assert resp.status_code == 409
    finally:
        _teardown(prev)


# ── Not found ─────────────────────────────────────────────────


async def test_status_update_not_found_returns_404() -> None:
    """Updating status of non-existent order returns 404."""
    session = FakeAsyncSession()
    session.queue_scalar(None)  # set_tenant
    session.queue_scalar(None)  # order not found

    prev = _setup(session)
    try:
        resp = await _patch(
            f"/api/v1/orders/{uuid.uuid4()}/status",
            json={"new_status": "shipped"},
        )
        assert resp.status_code == 404
    finally:
        _teardown(prev)


# ── Invalid status value ──────────────────────────────────────


async def test_invalid_status_value_returns_422() -> None:
    """Unknown status string returns 422."""
    session = FakeAsyncSession()

    prev = _setup(session)
    try:
        resp = await _patch(
            f"/api/v1/orders/{uuid.uuid4()}/status",
            json={"new_status": "nonexistent"},
        )
        assert resp.status_code == 422
    finally:
        _teardown(prev)


# ── Audit log ─────────────────────────────────────────────────


async def test_status_change_creates_audit_log() -> None:
    """Each status transition creates an ORDER_STATUS_CHANGED audit entry."""
    order = FakeOrder(status="confirmed")
    session = FakeAsyncSession()
    _queue_status_update(session, order)

    prev = _setup(session)
    try:
        resp = await _patch(
            f"/api/v1/orders/{order.id}/status",
            json={"new_status": "shipped"},
        )
        assert resp.status_code == 200

        from common.models.audit_log import AuditLog

        audits = [o for o in session.added if isinstance(o, AuditLog)]
        assert len(audits) == 1
        assert audits[0].action == "ORDER_STATUS_CHANGED"
        assert audits[0].before_state == {"status": "confirmed"}
        assert audits[0].after_state == {"status": "shipped"}
    finally:
        _teardown(prev)


# ── DELETE cancel endpoint ────────────────────────────────────


async def test_delete_cancels_pending_order() -> None:
    """DELETE /orders/{id} cancels a pending order."""
    order = FakeOrder(status="pending")
    session = FakeAsyncSession()
    _queue_cancel_pending(session, order)

    prev = _setup(session)
    try:
        resp = await _delete(f"/api/v1/orders/{order.id}")
        assert resp.status_code == 200
        assert order.status == "cancelled"
    finally:
        _teardown(prev)


async def test_delete_non_pending_order_returns_409() -> None:
    """DELETE /orders/{id} on a confirmed order returns 409."""
    order = FakeOrder(status="confirmed")
    session = FakeAsyncSession()
    session.queue_scalar(None)  # set_tenant
    session.queue_scalar(order)  # order lookup

    prev = _setup(session)
    try:
        resp = await _delete(f"/api/v1/orders/{order.id}")
        assert resp.status_code == 409
    finally:
        _teardown(prev)
