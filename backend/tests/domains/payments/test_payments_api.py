"""Tests for payment API endpoints."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import pytest

from tests.domains.orders._helpers import (
	FakeAsyncSession,
	FakeResult,
	setup_session,
	teardown_session,
	http_get,
	http_post,
)


# ── Fake domain objects ───────────────────────────────────────


class FakeInvoice:
	def __init__(
		self,
		*,
		total_amount: Decimal = Decimal("1000.00"),
		status: str = "issued",
	):
		self.id = uuid.uuid4()
		self.tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
		self.customer_id = uuid.uuid4()
		self.invoice_number = "AA00000001"
		self.total_amount = total_amount
		self.status = status
		self.updated_at = datetime.now(tz=UTC)


class FakePayment:
	def __init__(
		self,
		*,
		invoice_id: uuid.UUID | None = None,
		amount: Decimal = Decimal("500.00"),
	):
		self.id = uuid.uuid4()
		self.tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
		self.invoice_id = invoice_id or uuid.uuid4()
		self.customer_id = uuid.uuid4()
		self.payment_ref = "PAY-20260401-0001"
		self.amount = amount
		self.payment_method = "BANK_TRANSFER"
		self.payment_date = date.today()
		self.reference_number = None
		self.notes = None
		self.created_by = "00000000-0000-0000-0000-000000000001"
		self.created_at = datetime.now(tz=UTC)
		self.updated_at = datetime.now(tz=UTC)
		self.match_status = "matched"
		self.match_type = "manual"
		self.matched_at = datetime.now(tz=UTC)
		self.suggested_invoice_id = None


# ── Queue helpers ─────────────────────────────────────────────


def _queue_record_payment(
	session: FakeAsyncSession,
	invoice: FakeInvoice,
	paid_total: Decimal = Decimal("0"),
	max_ref: str | None = None,
) -> None:
	"""Queue results for record_payment service call."""
	# 1. set_tenant
	session.queue_scalar(None)
	# 2. Fetch invoice with_for_update
	session.queue_scalar(invoice)
	# 3. SUM(payments) for outstanding calculation
	session.queue_scalar(paid_total)
	# 4. MAX(payment_ref) for reference generation
	session.queue_scalar(max_ref)


# ── Tests ─────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_record_payment_happy_path():
	session = FakeAsyncSession()
	invoice = FakeInvoice(total_amount=Decimal("1000.00"))
	_queue_record_payment(session, invoice)

	prev = setup_session(session)
	try:
		resp = await http_post("/api/v1/payments", {
			"invoice_id": str(invoice.id),
			"amount": 500,
			"payment_method": "BANK_TRANSFER",
		})
		assert resp.status_code == 201
		body = resp.json()
		assert body["payment_method"] == "BANK_TRANSFER"
		assert body["payment_ref"].startswith("PAY-")
		assert body["invoice_id"] == str(invoice.id)
	finally:
		teardown_session(prev)


@pytest.mark.anyio
async def test_record_partial_payment_leaves_issued():
	session = FakeAsyncSession()
	invoice = FakeInvoice(total_amount=Decimal("1000.00"))
	_queue_record_payment(session, invoice)

	prev = setup_session(session)
	try:
		resp = await http_post("/api/v1/payments", {
			"invoice_id": str(invoice.id),
			"amount": 300,
			"payment_method": "CASH",
		})
		assert resp.status_code == 201
		# Invoice should remain "issued" — check the added objects
		# Invoice status is only changed if amount == outstanding
		assert invoice.status == "issued"
	finally:
		teardown_session(prev)


@pytest.mark.anyio
async def test_record_full_payment_marks_paid():
	session = FakeAsyncSession()
	invoice = FakeInvoice(total_amount=Decimal("1000.00"))
	_queue_record_payment(session, invoice)

	prev = setup_session(session)
	try:
		resp = await http_post("/api/v1/payments", {
			"invoice_id": str(invoice.id),
			"amount": 1000,
			"payment_method": "BANK_TRANSFER",
		})
		assert resp.status_code == 201
		# Invoice should transition to "paid"
		assert invoice.status == "paid"
	finally:
		teardown_session(prev)


@pytest.mark.anyio
async def test_record_remaining_payment_marks_paid():
	"""Partial payment exists, recording the remainder marks invoice paid."""
	session = FakeAsyncSession()
	invoice = FakeInvoice(total_amount=Decimal("1000.00"))
	_queue_record_payment(session, invoice, paid_total=Decimal("700.00"))

	prev = setup_session(session)
	try:
		resp = await http_post("/api/v1/payments", {
			"invoice_id": str(invoice.id),
			"amount": 300,
			"payment_method": "CHECK",
		})
		assert resp.status_code == 201
		assert invoice.status == "paid"
	finally:
		teardown_session(prev)


@pytest.mark.anyio
async def test_overpayment_returns_422():
	session = FakeAsyncSession()
	invoice = FakeInvoice(total_amount=Decimal("1000.00"))
	_queue_record_payment(session, invoice)

	prev = setup_session(session)
	try:
		resp = await http_post("/api/v1/payments", {
			"invoice_id": str(invoice.id),
			"amount": 1500,
			"payment_method": "CASH",
		})
		assert resp.status_code == 422
		body = resp.json()
		assert any("exceeds" in e["message"] for e in body["detail"])
	finally:
		teardown_session(prev)


@pytest.mark.anyio
async def test_payment_voided_invoice_returns_409():
	session = FakeAsyncSession()
	invoice = FakeInvoice(status="voided")
	# set_tenant + fetch invoice (voided guard fires before SUM)
	session.queue_scalar(None)
	session.queue_scalar(invoice)

	prev = setup_session(session)
	try:
		resp = await http_post("/api/v1/payments", {
			"invoice_id": str(invoice.id),
			"amount": 100,
			"payment_method": "CASH",
		})
		assert resp.status_code == 409
		body = resp.json()
		assert any("voided" in e["message"] for e in body["detail"])
	finally:
		teardown_session(prev)


@pytest.mark.anyio
async def test_payment_fully_paid_returns_409():
	session = FakeAsyncSession()
	invoice = FakeInvoice(total_amount=Decimal("1000.00"))
	# set_tenant + fetch invoice + SUM = 1000 (fully paid)
	session.queue_scalar(None)
	session.queue_scalar(invoice)
	session.queue_scalar(Decimal("1000.00"))

	prev = setup_session(session)
	try:
		resp = await http_post("/api/v1/payments", {
			"invoice_id": str(invoice.id),
			"amount": 100,
			"payment_method": "CASH",
		})
		assert resp.status_code == 409
		body = resp.json()
		assert any("fully paid" in e["message"] for e in body["detail"])
	finally:
		teardown_session(prev)


@pytest.mark.anyio
async def test_payment_invoice_not_found_returns_422():
	session = FakeAsyncSession()
	# set_tenant + fetch invoice = None
	session.queue_scalar(None)
	session.queue_scalar(None)

	prev = setup_session(session)
	try:
		resp = await http_post("/api/v1/payments", {
			"invoice_id": str(uuid.uuid4()),
			"amount": 100,
			"payment_method": "CASH",
		})
		assert resp.status_code == 422
		body = resp.json()
		assert any("not found" in e["message"] for e in body["detail"])
	finally:
		teardown_session(prev)


@pytest.mark.anyio
async def test_list_payments_empty():
	session = FakeAsyncSession()
	# set_tenant + count + fetch
	session.queue_scalar(None)
	session.queue_count(0)
	session.queue_scalars([])

	prev = setup_session(session)
	try:
		resp = await http_get("/api/v1/payments")
		assert resp.status_code == 200
		body = resp.json()
		assert body["items"] == []
		assert body["total"] == 0
	finally:
		teardown_session(prev)


@pytest.mark.anyio
async def test_list_payments_with_invoice_filter():
	session = FakeAsyncSession()
	payment = FakePayment()
	# set_tenant + count + fetch
	session.queue_scalar(None)
	session.queue_count(1)
	session.queue_scalars([payment])

	prev = setup_session(session)
	try:
		resp = await http_get(f"/api/v1/payments?invoice_id={payment.invoice_id}")
		assert resp.status_code == 200
		body = resp.json()
		assert len(body["items"]) == 1
		assert body["items"][0]["payment_ref"] == payment.payment_ref
	finally:
		teardown_session(prev)


@pytest.mark.anyio
async def test_get_payment_by_id():
	session = FakeAsyncSession()
	payment = FakePayment()
	# set_tenant + fetch payment
	session.queue_scalar(None)
	session.queue_scalar(payment)

	prev = setup_session(session)
	try:
		resp = await http_get(f"/api/v1/payments/{payment.id}")
		assert resp.status_code == 200
		body = resp.json()
		assert body["id"] == str(payment.id)
		assert body["payment_ref"] == payment.payment_ref
	finally:
		teardown_session(prev)


@pytest.mark.anyio
async def test_get_payment_not_found():
	session = FakeAsyncSession()
	# set_tenant + fetch payment = None
	session.queue_scalar(None)
	session.queue_scalar(None)

	prev = setup_session(session)
	try:
		resp = await http_get(f"/api/v1/payments/{uuid.uuid4()}")
		assert resp.status_code == 404
	finally:
		teardown_session(prev)


@pytest.mark.anyio
async def test_payment_ref_increments():
	"""When existing payment ref exists, next one increments."""
	session = FakeAsyncSession()
	invoice = FakeInvoice(total_amount=Decimal("1000.00"))
	_queue_record_payment(session, invoice, max_ref="PAY-20260401-0003")

	prev = setup_session(session)
	try:
		resp = await http_post("/api/v1/payments", {
			"invoice_id": str(invoice.id),
			"amount": 100,
			"payment_method": "CREDIT_CARD",
		})
		assert resp.status_code == 201
		body = resp.json()
		# Should be PAY-YYYYMMDD-0004 (incremented from 0003)
		assert body["payment_ref"].endswith("-0004")
	finally:
		teardown_session(prev)


@pytest.mark.anyio
async def test_record_payment_audit_log():
	"""Payment recording creates an audit log entry."""
	session = FakeAsyncSession()
	invoice = FakeInvoice(total_amount=Decimal("1000.00"))
	_queue_record_payment(session, invoice)

	prev = setup_session(session)
	try:
		resp = await http_post("/api/v1/payments", {
			"invoice_id": str(invoice.id),
			"amount": 500,
			"payment_method": "BANK_TRANSFER",
		})
		assert resp.status_code == 201
		# Check audit log was added
		from common.models.audit_log import AuditLog
		audits = [o for o in session.added if isinstance(o, AuditLog)]
		assert len(audits) == 1
		assert audits[0].action == "PAYMENT_RECORDED"
		assert audits[0].entity_type == "payment"
	finally:
		teardown_session(prev)
