"""Tests for stock check endpoint and stock snapshot on order creation — Story 5.2."""

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

class FakeWarehouseRow:
	"""Represents a joined (InventoryStock + Warehouse) row."""
	def __init__(self, warehouse_id: uuid.UUID, warehouse_name: str, quantity: int):
		self.warehouse_id = warehouse_id
		self.warehouse_name = warehouse_name
		self.quantity = quantity


class FakeCustomer:
	def __init__(self):
		self.id = uuid.uuid4()
		self.tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
		self.company_name = "Test Corp"
		self.normalized_business_number = "12345678"
		self.billing_address = "123 Main St"
		self.contact_name = "John Doe"
		self.contact_phone = "0912345678"
		self.contact_email = "john@test.com"
		self.credit_limit = Decimal("100000.00")
		self.status = "active"
		self.version = 1
		self.created_at = datetime.now(tz=UTC)
		self.updated_at = datetime.now(tz=UTC)


class FakeOrderLine:
	def __init__(
		self,
		*,
		order_id: uuid.UUID | None = None,
		product_id: uuid.UUID | None = None,
		available_stock_snapshot: int | None = None,
		backorder_note: str | None = None,
	):
		self.id = uuid.uuid4()
		self.tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
		self.order_id = order_id or uuid.uuid4()
		self.product_id = product_id or uuid.uuid4()
		self.line_number = 1
		self.quantity = Decimal("10.000")
		self.unit_price = Decimal("100.00")
		self.tax_policy_code = "standard"
		self.tax_type = 1
		self.tax_rate = Decimal("0.0500")
		self.tax_amount = Decimal("50.00")
		self.subtotal_amount = Decimal("1000.00")
		self.total_amount = Decimal("1050.00")
		self.description = "Test product"
		self.available_stock_snapshot = available_stock_snapshot
		self.backorder_note = backorder_note
		self.created_at = datetime.now(tz=UTC)


class FakeOrder:
	def __init__(
		self,
		*,
		customer_id: uuid.UUID | None = None,
		lines: list[FakeOrderLine] | None = None,
		customer: FakeCustomer | None = None,
	):
		self.id = uuid.uuid4()
		self.tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
		self.customer_id = customer_id or uuid.uuid4()
		self.order_number = "ORD-20260401-ABCD1234"
		self.status = "pending"
		self.payment_terms_code = "NET_30"
		self.payment_terms_days = 30
		self.subtotal_amount = Decimal("1000.00")
		self.tax_amount = Decimal("50.00")
		self.total_amount = Decimal("1050.00")
		self.invoice_id = None
		self.notes = None
		self.created_by = "00000000-0000-0000-0000-000000000001"
		self.created_at = datetime.now(tz=UTC)
		self.updated_at = datetime.now(tz=UTC)
		self.confirmed_at = None
		self.lines = lines or []
		self.customer = customer


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

	def begin(self) -> _FakeBegin:
		return _FakeBegin()

	def queue_scalar(self, obj: object | None) -> None:
		self._execute_results.append(FakeResult(obj=obj))

	def queue_scalars(self, objs: list[object]) -> None:
		self._execute_results.append(FakeResult(items=objs))

	def queue_count(self, value: int) -> None:
		self._execute_results.append(FakeResult(count=value))

	def queue_rows(self, rows: list[object]) -> None:
		"""Queue result that returns rows via .all()."""
		self._execute_results.append(FakeResult(items=rows))


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


async def _get(path: str) -> Any:
	transport = ASGITransport(app=app)
	async with AsyncClient(transport=transport, base_url="http://test") as c:
		return await c.get(path)


async def _post(path: str, json: dict) -> Any:
	transport = ASGITransport(app=app)
	async with AsyncClient(transport=transport, base_url="http://test") as c:
		return await c.post(path, json=json)


# ── Stock check endpoint tests ────────────────────────────────

_PRODUCT_ID = uuid.uuid4()
_WH1_ID = uuid.uuid4()
_WH2_ID = uuid.uuid4()


async def test_check_stock_with_inventory() -> None:
	"""Stock check returns per-warehouse totals."""
	session = FakeAsyncSession()
	session.queue_scalar(None)  # set_tenant
	session.queue_rows([
		FakeWarehouseRow(_WH1_ID, "Warehouse A", 50),
		FakeWarehouseRow(_WH2_ID, "Warehouse B", 30),
	])

	prev = _setup(session)
	try:
		resp = await _get(f"/api/v1/orders/check-stock?product_id={_PRODUCT_ID}")
		assert resp.status_code == 200
		body = resp.json()
		assert body["total_available"] == 80
		assert len(body["warehouses"]) == 2
		assert body["warehouses"][0]["warehouse_name"] == "Warehouse A"
		assert body["warehouses"][0]["available"] == 50
	finally:
		_teardown(prev)


async def test_check_stock_no_inventory() -> None:
	"""Stock check for product with no inventory returns 0."""
	session = FakeAsyncSession()
	session.queue_scalar(None)  # set_tenant
	session.queue_rows([])

	prev = _setup(session)
	try:
		resp = await _get(f"/api/v1/orders/check-stock?product_id={_PRODUCT_ID}")
		assert resp.status_code == 200
		body = resp.json()
		assert body["total_available"] == 0
		assert body["warehouses"] == []
	finally:
		_teardown(prev)


# ── Order creation with stock snapshot tests ──────────────────

def _order_payload(customer_id: str, product_id: str, quantity: int = 10) -> dict:
	return {
		"customer_id": customer_id,
		"payment_terms_code": "NET_30",
		"lines": [
			{
				"product_id": product_id,
				"description": "Widget A",
				"quantity": quantity,
				"unit_price": 100.00,
				"tax_policy_code": "standard",
			},
		],
	}


async def test_create_order_populates_stock_snapshot() -> None:
	"""Order creation sets available_stock_snapshot on each line."""
	customer = FakeCustomer()
	product_id = uuid.uuid4()
	line = FakeOrderLine(
		product_id=product_id,
		available_stock_snapshot=80,
		backorder_note=None,
	)
	order = FakeOrder(customer_id=customer.id, lines=[line], customer=customer)

	session = FakeAsyncSession()
	session.queue_scalar(None)  # set_tenant
	session.queue_scalar(customer)  # customer lookup
	session.queue_scalars([product_id])  # product check
	session.queue_count(80)  # stock query for line
	session.queue_scalar(None)  # set_tenant (get_order)
	session.queue_scalar(order)  # get_order reload

	prev = _setup(session)
	try:
		resp = await _post(
			"/api/v1/orders",
			json=_order_payload(str(customer.id), str(product_id), quantity=10),
		)
		assert resp.status_code == 201
		body = resp.json()
		assert body["lines"][0]["available_stock_snapshot"] == 80
		assert body["lines"][0]["backorder_note"] is None
	finally:
		_teardown(prev)


async def test_create_order_insufficient_stock_sets_backorder_note() -> None:
	"""When quantity > available, backorder_note is populated."""
	customer = FakeCustomer()
	product_id = uuid.uuid4()
	line = FakeOrderLine(
		product_id=product_id,
		available_stock_snapshot=5,
		backorder_note="Backorder: 95 units",
	)
	order = FakeOrder(customer_id=customer.id, lines=[line], customer=customer)

	session = FakeAsyncSession()
	session.queue_scalar(None)  # set_tenant
	session.queue_scalar(customer)  # customer lookup
	session.queue_scalars([product_id])  # product check
	session.queue_count(5)  # stock query — only 5 available
	session.queue_scalar(None)  # set_tenant (get_order)
	session.queue_scalar(order)  # get_order reload

	prev = _setup(session)
	try:
		resp = await _post(
			"/api/v1/orders",
			json=_order_payload(str(customer.id), str(product_id), quantity=100),
		)
		assert resp.status_code == 201
		body = resp.json()
		assert body["lines"][0]["available_stock_snapshot"] == 5
		assert body["lines"][0]["backorder_note"] == "Backorder: 95 units"
	finally:
		_teardown(prev)


async def test_create_order_sufficient_stock_no_backorder_note() -> None:
	"""When quantity <= available, backorder_note stays null."""
	customer = FakeCustomer()
	product_id = uuid.uuid4()
	line = FakeOrderLine(
		product_id=product_id,
		available_stock_snapshot=100,
		backorder_note=None,
	)
	order = FakeOrder(customer_id=customer.id, lines=[line], customer=customer)

	session = FakeAsyncSession()
	session.queue_scalar(None)  # set_tenant
	session.queue_scalar(customer)  # customer lookup
	session.queue_scalars([product_id])  # product check
	session.queue_count(100)  # stock query — 100 available
	session.queue_scalar(None)  # set_tenant (get_order)
	session.queue_scalar(order)  # get_order reload

	prev = _setup(session)
	try:
		resp = await _post(
			"/api/v1/orders",
			json=_order_payload(str(customer.id), str(product_id), quantity=10),
		)
		assert resp.status_code == 201
		body = resp.json()
		assert body["lines"][0]["available_stock_snapshot"] == 100
		assert body["lines"][0]["backorder_note"] is None
	finally:
		_teardown(prev)
