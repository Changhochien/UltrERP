"""Tests for order confirmation — Story 5.4."""

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


# ── Fake objects ──────────────────────────────────────────────

class FakeCustomer:
	def __init__(self):
		self.id = uuid.uuid4()
		self.tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
		self.company_name = "Test Corp"
		self.normalized_business_number = "12345678"
		self.status = "active"


class FakeOrderLine:
	def __init__(self, *, product_id: uuid.UUID | None = None, line_number: int = 1):
		self.id = uuid.uuid4()
		self.tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
		self.order_id = uuid.uuid4()
		self.product_id = product_id or uuid.uuid4()
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
	def __init__(
		self,
		*,
		status: str = "pending",
		customer_id: uuid.UUID | None = None,
		lines: list[FakeOrderLine] | None = None,
		invoice_id: uuid.UUID | None = None,
		customer: FakeCustomer | None = None,
	):
		self.id = uuid.uuid4()
		self.tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
		self.customer_id = customer_id or uuid.uuid4()
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
		self.confirmed_at = None
		self.lines = lines if lines is not None else [FakeOrderLine()]
		self.customer = customer


class FakeInvoiceNumberRange:
	def __init__(self):
		self.id = uuid.uuid4()
		self.tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
		self.prefix = "AA"
		self.start_number = 1
		self.end_number = 99999999
		self.next_number = 1
		self.is_active = True
		self.created_at = datetime.now(tz=UTC)
		self.updated_at = datetime.now(tz=UTC)


class FakeResult:
	def __init__(self, obj: object | None = None, *, items: list | None = None, count: int | None = None):
		self._obj = obj
		self._items = items
		self._count = count

	def scalar_one_or_none(self) -> object | None:
		return self._obj

	def scalar(self) -> object | None:
		if self._count is not None:
			return self._count
		return self._obj

	def scalars(self) -> FakeScalarsResult:
		return FakeScalarsResult(self._items if self._items is not None else [])

	def all(self) -> list:
		return list(self._items) if self._items is not None else []


class FakeScalarsResult:
	def __init__(self, objs: list[object]):
		self._objs = objs

	def all(self) -> list[object]:
		return list(self._objs)

	def unique(self) -> FakeScalarsResult:
		return self


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

	def queue_scalars(self, objs: list[object]) -> None:
		self._execute_results.append(FakeResult(items=objs))

	def queue_count(self, value: int) -> None:
		self._execute_results.append(FakeResult(count=value))

	def queue_rows(self, rows: list) -> None:
		self._execute_results.append(FakeResult(items=rows))


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


async def _patch(path: str, json: dict) -> Any:
	transport = ASGITransport(app=app)
	async with AsyncClient(transport=transport, base_url="http://test") as c:
		return await c.patch(path, json=json)


# ── Confirm order tests ──────────────────────────────────────


def _queue_confirm_success(session: FakeAsyncSession, order: FakeOrder, customer: FakeCustomer):
	"""Queue all results needed for successful confirm_order call.

	Execution flow:
	  1. set_tenant → scalar(None)
	  2. order lookup (selectinload + for_update) → scalar(order)
	  3. customer lookup in confirm_order → scalar(customer)
	  4. _create_invoice_core: customer lookup → scalar(customer)
	  5. _create_invoice_core: number_range lookup → scalar(number_range)
	  6. flush (invoice + lines), flush (audits)
	  7. get_order reload: set_tenant → scalar(None)
	  8. get_order reload: selectinload → scalar(confirmed_order)
	"""
	session.queue_scalar(None)  # set_tenant
	session.queue_scalar(order)  # order lookup
	session.queue_scalar(customer)  # customer lookup (confirm_order)
	session.queue_scalar(customer)  # customer lookup (_create_invoice_core)
	session.queue_scalar(FakeInvoiceNumberRange())  # number_range
	session.queue_scalar(None)  # set_tenant (get_order)
	session.queue_scalar(order)  # get_order reload


async def test_confirm_order_success() -> None:
	"""Confirming a pending order creates an invoice and returns confirmed order."""
	customer = FakeCustomer()
	line = FakeOrderLine()
	order = FakeOrder(customer_id=customer.id, lines=[line], customer=customer)

	session = FakeAsyncSession()
	_queue_confirm_success(session, order, customer)

	prev = _setup(session)
	try:
		resp = await _patch(
			f"/api/v1/orders/{order.id}/status",
			json={"new_status": "confirmed"},
		)
		assert resp.status_code == 200
		body = resp.json()
		assert body["status"] == "confirmed"
		assert body["invoice_id"] is not None
	finally:
		_teardown(prev)


async def test_confirm_non_pending_order_returns_409() -> None:
	"""Cannot confirm an order that is not 'pending'."""
	order = FakeOrder(status="confirmed")

	session = FakeAsyncSession()
	session.queue_scalar(None)  # set_tenant
	session.queue_scalar(order)  # order lookup

	prev = _setup(session)
	try:
		resp = await _patch(
			f"/api/v1/orders/{order.id}/status",
			json={"new_status": "confirmed"},
		)
		assert resp.status_code == 409
	finally:
		_teardown(prev)


async def test_confirm_order_with_existing_invoice_returns_409() -> None:
	"""Cannot confirm if order already has an invoice_id."""
	order = FakeOrder(invoice_id=uuid.uuid4())

	session = FakeAsyncSession()
	session.queue_scalar(None)  # set_tenant
	session.queue_scalar(order)  # order lookup

	prev = _setup(session)
	try:
		resp = await _patch(
			f"/api/v1/orders/{order.id}/status",
			json={"new_status": "confirmed"},
		)
		# status check happens first (order is still "pending"), then invoice_id check
		assert resp.status_code == 409
	finally:
		_teardown(prev)


async def test_confirm_order_no_lines_returns_409() -> None:
	"""Cannot confirm an order with no lines."""
	order = FakeOrder(lines=[])

	session = FakeAsyncSession()
	session.queue_scalar(None)  # set_tenant
	session.queue_scalar(order)  # order lookup

	prev = _setup(session)
	try:
		resp = await _patch(
			f"/api/v1/orders/{order.id}/status",
			json={"new_status": "confirmed"},
		)
		assert resp.status_code == 409
	finally:
		_teardown(prev)


async def test_confirm_order_not_found_returns_404() -> None:
	"""Confirming a non-existent order returns 404."""
	session = FakeAsyncSession()
	session.queue_scalar(None)  # set_tenant
	session.queue_scalar(None)  # order not found

	prev = _setup(session)
	try:
		resp = await _patch(
			f"/api/v1/orders/{uuid.uuid4()}/status",
			json={"new_status": "confirmed"},
		)
		assert resp.status_code == 404
	finally:
		_teardown(prev)


async def test_confirm_order_customer_missing_returns_409() -> None:
	"""If customer no longer exists at confirmation time, return 409."""
	order = FakeOrder()

	session = FakeAsyncSession()
	session.queue_scalar(None)  # set_tenant
	session.queue_scalar(order)  # order lookup
	session.queue_scalar(None)  # customer not found

	prev = _setup(session)
	try:
		resp = await _patch(
			f"/api/v1/orders/{order.id}/status",
			json={"new_status": "confirmed"},
		)
		assert resp.status_code == 409
	finally:
		_teardown(prev)


async def test_unsupported_status_transition_returns_422() -> None:
	"""Unknown new_status returns 422."""
	session = FakeAsyncSession()

	prev = _setup(session)
	try:
		resp = await _patch(
			f"/api/v1/orders/{uuid.uuid4()}/status",
			json={"new_status": "bogus_status"},
		)
		assert resp.status_code == 422
	finally:
		_teardown(prev)


async def test_confirm_order_creates_audit_logs() -> None:
	"""Confirm creates both ORDER_STATUS_CHANGED and INVOICE_CREATED audit entries."""
	customer = FakeCustomer()
	line = FakeOrderLine()
	order = FakeOrder(customer_id=customer.id, lines=[line], customer=customer)

	session = FakeAsyncSession()
	_queue_confirm_success(session, order, customer)

	prev = _setup(session)
	try:
		resp = await _patch(
			f"/api/v1/orders/{order.id}/status",
			json={"new_status": "confirmed"},
		)
		assert resp.status_code == 200

		# Check audit logs in session.added
		from common.models.audit_log import AuditLog
		audits = [o for o in session.added if isinstance(o, AuditLog)]
		actions = {a.action for a in audits}
		assert "ORDER_STATUS_CHANGED" in actions
		assert "INVOICE_CREATED" in actions
	finally:
		_teardown(prev)
