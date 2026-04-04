"""Tests for stock check endpoint and stock snapshot on order creation — Story 5.2."""

from __future__ import annotations

import uuid

from tests.domains.orders._helpers import (
	FakeAsyncSession,
	FakeCustomer,
	FakeOrder,
	FakeOrderLine,
	FakeWarehouseRow,
	setup_session as _setup,
	teardown_session as _teardown,
	http_get as _get,
	http_post as _post,
)


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
