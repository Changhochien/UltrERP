"""Tests for order status transitions — Story 5.5."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from common.database import get_db


# ── Fake objects (mirror test_order_confirmation.py) ──────────

class FakeOrderLine:
	def __init__(self, *, line_number: int = 1):
		self.id = uuid.uuid4()
		self.tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
		self.order_id = uuid.uuid4()
		self.product_id = uuid.uuid4()
		self.line_number = line_number
		self.quantity = Decimal("10.000")
		self.unit_price = Decimal("100.00")
		self.tax_policy_code = "standard"
		self.tax_type = 1
		self.tax_rate = Decimal("0.0500")
		self.tax_amount = Decimal("50.00")
		self.subtotal_amount = Decimal("1000.00")
		self.total_amount = Decimal("1050.00")
		self.description = "Widget A"
		self.available_stock_snapshot = 100
		self.backorder_note = None
		self.created_at = datetime.now(tz=UTC)


class FakeOrder:
	def __init__(self, *, status: str = "pending", invoice_id: uuid.UUID | None = None):
		self.id = uuid.uuid4()
		self.tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
		self.customer_id = uuid.uuid4()
		self.order_number = "ORD-20260401-ABCD1234"
		self.status = status
		self.payment_terms_code = "NET_30"
		self.payment_terms_days = 30
		self.subtotal_amount = Decimal("1000.00")
		self.tax_amount = Decimal("50.00")
		self.total_amount = Decimal("1050.00")
		self.invoice_id = invoice_id
		self.notes = None
		self.created_by = "00000000-0000-0000-0000-000000000001"
		self.created_at = datetime.now(tz=UTC)
		self.updated_at = datetime.now(tz=UTC)
		self.confirmed_at = datetime.now(tz=UTC) if status != "pending" else None
		self.lines = [FakeOrderLine()]


class FakeResult:
	def __init__(self, obj: object | None = None, *, count: int | None = None):
		self._obj = obj
		self._count = count

	def scalar_one_or_none(self) -> object | None:
		return self._obj

	def scalar(self) -> object | None:
		if self._count is not None:
			return self._count
		return self._obj


class _FakeBegin:
	async def __aenter__(self) -> None:
		return None

	async def __aexit__(self, *args: object) -> bool:
		return False


class FakeAsyncSession:
	def __init__(self) -> None:
		self._execute_results: list[object] = []
		self._idx = 0
		self.added: list[object] = []

	def add(self, obj: object) -> None:
		self.added.append(obj)

	def add_all(self, objs: list[object]) -> None:
		self.added.extend(objs)

	async def execute(self, _stmt: object, _params: object = None) -> object:
		if self._idx < len(self._execute_results):
			result = self._execute_results[self._idx]
			self._idx += 1
			return result
		return FakeResult()

	async def flush(self) -> None:
		for obj in self.added:
			if hasattr(obj, "id") and obj.id is None:
				obj.id = uuid.uuid4()

	async def commit(self) -> None:
		pass

	async def refresh(self, obj: object) -> None:
		pass

	def begin(self) -> _FakeBegin:
		return _FakeBegin()

	def queue_scalar(self, obj: object | None) -> None:
		self._execute_results.append(FakeResult(obj=obj))

	def queue_count(self, value: int) -> None:
		self._execute_results.append(FakeResult(count=value))


# ── Helpers ───────────────────────────────────────────────────

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


async def _patch(path: str, json: dict) -> Any:
	transport = ASGITransport(app=app)
	async with AsyncClient(transport=transport, base_url="http://test") as c:
		return await c.patch(path, json=json)


async def _delete(path: str) -> Any:
	transport = ASGITransport(app=app)
	async with AsyncClient(transport=transport, base_url="http://test") as c:
		return await c.delete(path)


def _queue_status_update(session: FakeAsyncSession, order: FakeOrder):
	"""Queue results for a non-confirmed status transition.

	Flow:
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
	_queue_status_update(session, order)

	prev = _setup(session)
	try:
		resp = await _patch(
			f"/api/v1/orders/{order.id}/status",
			json={"new_status": "cancelled"},
		)
		assert resp.status_code == 200
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
	_queue_status_update(session, order)

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
