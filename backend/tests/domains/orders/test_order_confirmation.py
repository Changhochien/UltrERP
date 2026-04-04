"""Tests for order confirmation — Story 5.4."""

from __future__ import annotations

import uuid

from ._helpers import (
	FakeAsyncSession,
	FakeCustomer,
	FakeInvoiceNumberRange,
	FakeOrder,
	FakeOrderLine,
	setup_session as _setup,
	teardown_session as _teardown,
	http_patch as _patch,
)


# ── Confirm order tests ──────────────────────────────────────


def _queue_confirm_success(session: FakeAsyncSession, order: FakeOrder, customer: FakeCustomer):
	"""Queue all results needed for successful confirm_order call.

	Execution flow:
	  1. set_tenant → scalar(None)
	  2. order lookup (selectinload + for_update) → scalar(order)
	  3. product code lookup → rows[(product_id, code)]
	  4. customer lookup in confirm_order → scalar(customer)
	  5. _create_invoice_core: customer lookup → scalar(customer)
	  6. _create_invoice_core: number_range lookup → scalar(number_range)
	  7. flush (invoice + lines), flush (audits)
	  8. get_order reload: set_tenant → scalar(None)
	  9. get_order reload: selectinload → scalar(confirmed_order)
	"""
	session.queue_scalar(None)  # set_tenant
	session.queue_scalar(order)  # order lookup
	# Product code lookup — return fake rows with id and code attributes
	product_rows = [type("Row", (), {"id": line.product_id, "code": f"PROD-{i}"})() for i, line in enumerate(order.lines)]
	session.queue_rows(product_rows)  # product code lookup
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
	product_rows = [type("Row", (), {"id": line.product_id, "code": f"PROD-{i}"})() for i, line in enumerate(order.lines)]
	session.queue_rows(product_rows)  # product code lookup
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
