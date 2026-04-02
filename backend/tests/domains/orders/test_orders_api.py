"""Tests for orders API endpoints — Story 5.1."""

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
	def __init__(
		self,
		*,
		tenant_id: uuid.UUID = uuid.UUID("00000000-0000-0000-0000-000000000001"),
	):
		self.id = uuid.uuid4()
		self.tenant_id = tenant_id
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


class FakeProduct:
	def __init__(self, *, product_id: uuid.UUID | None = None):
		self.id = product_id or uuid.uuid4()


class FakeOrderLine:
	def __init__(
		self,
		*,
		order_id: uuid.UUID | None = None,
		product_id: uuid.UUID | None = None,
		line_number: int = 1,
	):
		self.id = uuid.uuid4()
		self.tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
		self.order_id = order_id or uuid.uuid4()
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
		self.description = "Test product"
		self.available_stock_snapshot = None
		self.backorder_note = None
		self.created_at = datetime.now(tz=UTC)


class FakeOrder:
	def __init__(
		self,
		*,
		tenant_id: uuid.UUID = uuid.UUID("00000000-0000-0000-0000-000000000001"),
		customer_id: uuid.UUID | None = None,
		status: str = "pending",
		lines: list[FakeOrderLine] | None = None,
		customer: FakeCustomer | None = None,
	):
		self.id = uuid.uuid4()
		self.tenant_id = tenant_id
		self.customer_id = customer_id or uuid.uuid4()
		self.order_number = "ORD-20260401-ABCD1234"
		self.status = status
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
	"""Context manager for session.begin()."""
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
		# Assign UUIDs to added objects that don't have an id yet
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
	async with AsyncClient(transport=transport, base_url="http://test") as c:
		return await c.post(path, json=json)


async def _get(path: str) -> Any:
	transport = ASGITransport(app=app)
	async with AsyncClient(transport=transport, base_url="http://test") as c:
		return await c.get(path)


# ── Payment terms tests ──────────────────────────────────────

async def test_list_payment_terms() -> None:
	session = FakeAsyncSession()
	prev = _setup(session)
	try:
		resp = await _get("/api/v1/orders/payment-terms")
		assert resp.status_code == 200
		body = resp.json()
		assert body["total"] == 3
		codes = [item["code"] for item in body["items"]]
		assert "NET_30" in codes
		assert "NET_60" in codes
		assert "COD" in codes
	finally:
		_teardown(prev)


# ── Order list tests ─────────────────────────────────────────

async def test_list_orders_empty() -> None:
	session = FakeAsyncSession()
	session.queue_count(0)  # count query
	session.queue_scalars([])  # items query

	prev = _setup(session)
	try:
		resp = await _get("/api/v1/orders")
		assert resp.status_code == 200
		body = resp.json()
		assert body["total"] == 0
		assert body["items"] == []
	finally:
		_teardown(prev)


async def test_list_orders_with_items() -> None:
	o1 = FakeOrder(status="pending")
	o2 = FakeOrder(status="confirmed")

	session = FakeAsyncSession()
	session.queue_count(2)
	session.queue_scalars([o1, o2])

	prev = _setup(session)
	try:
		resp = await _get("/api/v1/orders")
		assert resp.status_code == 200
		body = resp.json()
		assert body["total"] == 2
		assert len(body["items"]) == 2
	finally:
		_teardown(prev)


async def test_list_orders_with_status_filter() -> None:
	o1 = FakeOrder(status="pending")

	session = FakeAsyncSession()
	session.queue_count(1)
	session.queue_scalars([o1])

	prev = _setup(session)
	try:
		resp = await _get("/api/v1/orders?status=pending")
		assert resp.status_code == 200
		body = resp.json()
		assert body["total"] == 1
	finally:
		_teardown(prev)


# ── Order detail tests ───────────────────────────────────────

async def test_get_order_found() -> None:
	customer = FakeCustomer()
	line = FakeOrderLine(product_id=uuid.uuid4())
	order = FakeOrder(
		customer_id=customer.id,
		lines=[line],
		customer=customer,
	)

	session = FakeAsyncSession()
	session.queue_scalar(order)  # get_order query

	prev = _setup(session)
	try:
		resp = await _get(f"/api/v1/orders/{order.id}")
		assert resp.status_code == 200
		body = resp.json()
		assert body["order_number"] == order.order_number
		assert body["status"] == "pending"
		assert len(body["lines"]) == 1
		assert body["lines"][0]["description"] == "Test product"
	finally:
		_teardown(prev)


async def test_get_order_not_found() -> None:
	session = FakeAsyncSession()
	session.queue_scalar(None)  # not found

	prev = _setup(session)
	try:
		resp = await _get(f"/api/v1/orders/{uuid.uuid4()}")
		assert resp.status_code == 404
	finally:
		_teardown(prev)


# ── Order creation tests ─────────────────────────────────────

_PRODUCT_ID = str(uuid.uuid4())


def _valid_order_payload(customer_id: str | None = None) -> dict:
	return {
		"customer_id": customer_id or str(uuid.uuid4()),
		"payment_terms_code": "NET_30",
		"notes": "Test order",
		"lines": [
			{
				"product_id": _PRODUCT_ID,
				"description": "Widget A",
				"quantity": 10,
				"unit_price": 100.00,
				"tax_policy_code": "standard",
			},
		],
	}


async def test_create_order_validation_empty_lines() -> None:
	session = FakeAsyncSession()
	prev = _setup(session)
	try:
		payload = _valid_order_payload()
		payload["lines"] = []
		resp = await _post("/api/v1/orders", json=payload)
		assert resp.status_code == 422
	finally:
		_teardown(prev)


async def test_create_order_validation_missing_customer() -> None:
	session = FakeAsyncSession()
	prev = _setup(session)
	try:
		payload = _valid_order_payload()
		del payload["customer_id"]
		resp = await _post("/api/v1/orders", json=payload)
		assert resp.status_code == 422
	finally:
		_teardown(prev)


async def test_create_order_customer_not_found() -> None:
	session = FakeAsyncSession()
	# set_tenant execute
	session.queue_scalar(None)
	# customer lookup — not found
	session.queue_scalar(None)

	prev = _setup(session)
	try:
		resp = await _post("/api/v1/orders", json=_valid_order_payload())
		assert resp.status_code == 422
		body = resp.json()
		assert any("customer" in str(e).lower() for e in body["detail"])
	finally:
		_teardown(prev)


async def test_create_order_success() -> None:
	customer = FakeCustomer()
	product = FakeProduct(product_id=uuid.UUID(_PRODUCT_ID))

	# For the reload after creation (get_order)
	line = FakeOrderLine(product_id=product.id)
	order = FakeOrder(
		customer_id=customer.id,
		lines=[line],
		customer=customer,
	)

	session = FakeAsyncSession()
	# Inside create_order (within session.begin):
	session.queue_scalar(None)  # set_tenant
	session.queue_scalar(customer)  # customer lookup
	session.queue_scalars([product.id])  # product IDs check
	session.queue_count(100)  # stock availability for line
	# After flush/commit, reload via get_order:
	session.queue_scalar(order)  # get_order with selectinload

	prev = _setup(session)
	try:
		payload = _valid_order_payload(customer_id=str(customer.id))
		payload["lines"][0]["product_id"] = str(product.id)
		resp = await _post("/api/v1/orders", json=payload)
		assert resp.status_code == 201
		body = resp.json()
		assert body["status"] == "pending"
		assert body["payment_terms_code"] == "NET_30"
		assert body["payment_terms_days"] == 30
		assert len(body["lines"]) == 1
	finally:
		_teardown(prev)


async def test_create_order_with_cod_terms() -> None:
	customer = FakeCustomer()
	product = FakeProduct(product_id=uuid.UUID(_PRODUCT_ID))

	line = FakeOrderLine(product_id=product.id)
	order = FakeOrder(
		customer_id=customer.id,
		lines=[line],
		customer=customer,
	)
	order.payment_terms_code = "COD"
	order.payment_terms_days = 0

	session = FakeAsyncSession()
	session.queue_scalar(None)  # set_tenant
	session.queue_scalar(customer)  # customer lookup
	session.queue_scalars([product.id])  # product check
	session.queue_count(100)  # stock availability for line
	session.queue_scalar(order)  # get_order

	prev = _setup(session)
	try:
		payload = _valid_order_payload(customer_id=str(customer.id))
		payload["payment_terms_code"] = "COD"
		payload["lines"][0]["product_id"] = str(product.id)
		resp = await _post("/api/v1/orders", json=payload)
		assert resp.status_code == 201
		body = resp.json()
		assert body["payment_terms_code"] == "COD"
		assert body["payment_terms_days"] == 0
	finally:
		_teardown(prev)


async def test_create_order_invalid_payment_terms() -> None:
	"""Invalid payment_terms_code returns 422."""
	session = FakeAsyncSession()
	prev = _setup(session)
	try:
		payload = _valid_order_payload()
		payload["payment_terms_code"] = "NET_999"
		resp = await _post("/api/v1/orders", json=payload)
		assert resp.status_code == 422
	finally:
		_teardown(prev)


async def test_create_order_defaults_to_net30() -> None:
	"""Omitting payment_terms_code defaults to NET_30."""
	customer = FakeCustomer()
	product = FakeProduct(product_id=uuid.UUID(_PRODUCT_ID))

	line = FakeOrderLine(product_id=product.id)
	order = FakeOrder(
		customer_id=customer.id,
		lines=[line],
		customer=customer,
	)
	order.payment_terms_code = "NET_30"
	order.payment_terms_days = 30

	session = FakeAsyncSession()
	session.queue_scalar(None)  # set_tenant
	session.queue_scalar(customer)  # customer lookup
	session.queue_scalars([product.id])  # product check
	session.queue_count(100)  # stock availability for line
	session.queue_scalar(order)  # get_order

	prev = _setup(session)
	try:
		payload = _valid_order_payload(customer_id=str(customer.id))
		payload["lines"][0]["product_id"] = str(product.id)
		del payload["payment_terms_code"]
		resp = await _post("/api/v1/orders", json=payload)
		assert resp.status_code == 201
		body = resp.json()
		assert body["payment_terms_code"] == "NET_30"
		assert body["payment_terms_days"] == 30
	finally:
		_teardown(prev)
