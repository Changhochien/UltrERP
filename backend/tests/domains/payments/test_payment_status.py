"""Tests for invoice payment status (Story 6.3)."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from typing import Any, cast

import pytest
from sqlalchemy.exc import IntegrityError

from domains.invoices.models import Invoice
from domains.invoices.service import get_invoice_egui_submission, list_invoices

from tests.domains.orders._helpers import (
	FakeAsyncSession,
	FakeResult,
	setup_session,
	teardown_session,
	http_get,
	http_post,
)


# ── Fake domain objects ───────────────────────────────────────

TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


class FakeInvoice:
	def __init__(
		self,
		*,
		total_amount: Decimal = Decimal("1000.00"),
		status: str = "issued",
		invoice_date: date | None = None,
		order_id: uuid.UUID | None = None,
		customer_id: uuid.UUID | None = None,
	):
		self.id = uuid.uuid4()
		self.tenant_id = TENANT_ID
		self.invoice_number = "AA00000001"
		self.invoice_date = invoice_date or date.today()
		self.customer_id = customer_id or uuid.uuid4()
		self.buyer_type = "B2B"
		self.buyer_identifier_snapshot = "12345678"
		self.currency_code = "TWD"
		self.subtotal_amount = total_amount
		self.tax_amount = Decimal("0.00")
		self.total_amount = total_amount
		self.status = status
		self.version = 1
		self.voided_at = None
		self.void_reason = None
		self.order_id = order_id
		self.created_at = datetime.now(tz=UTC)
		self.updated_at = datetime.now(tz=UTC)
		self.lines = []


class FakePaymentRow:
	"""Represents a grouped row from (invoice_id, SUM(amount))."""
	def __init__(self, invoice_id: uuid.UUID, total: Decimal):
		self._tuple = (invoice_id, total)

	def __getitem__(self, idx: int):
		return self._tuple[idx]


class FakeOrderTermsRow:
	"""Represents a row from (order.id, order.payment_terms_days)."""
	def __init__(self, order_id: uuid.UUID, days: int):
		self._tuple = (order_id, days)

	def __getitem__(self, idx: int):
		return self._tuple[idx]


class FakeEguiSubmission:
	def __init__(
		self,
		*,
		invoice_id: uuid.UUID,
		status: str = "PENDING",
		mode: str = "mock",
		deadline_at: datetime | None = None,
		last_synced_at: datetime | None = None,
		updated_at: datetime | None = None,
		retry_count: int = 0,
		last_error_message: str | None = None,
	):
		now = datetime.now(tz=UTC)
		self.id = uuid.uuid4()
		self.tenant_id = TENANT_ID
		self.invoice_id = invoice_id
		self.status = status
		self.mode = mode
		self.fia_reference = None
		self.retry_count = retry_count
		self.deadline_at = deadline_at or (now + timedelta(hours=48))
		self.last_synced_at = last_synced_at or now
		self.last_error_message = last_error_message
		self.created_at = now
		self.updated_at = updated_at or now


class FlushConflictSession(FakeAsyncSession):
	def __init__(self) -> None:
		super().__init__()
		self.raise_integrity_error = True

	async def flush(self) -> None:
		if self.raise_integrity_error:
			self.raise_integrity_error = False
			raise IntegrityError("INSERT INTO egui_submissions", {}, Exception("duplicate key"))
		await super().flush()


class RecordingAsyncSession(FakeAsyncSession):
	def __init__(self) -> None:
		super().__init__()
		self.statements: list[object] = []

	async def execute(self, stmt: object, _params: object = None) -> object:
		self.statements.append(stmt)
		return await super().execute(stmt, _params)


# ── Queue helpers ─────────────────────────────────────────────


def _queue_list_invoices(
	session: FakeAsyncSession,
	invoices: list[FakeInvoice],
	total: int | None = None,
	payment_rows: list[FakePaymentRow] | None = None,
	order_term_rows: list[FakeOrderTermsRow] | None = None,
) -> None:
	"""Queue results for list_invoices service call.

	Flow: set_tenant → count → select invoices → batch payment sums → [batch order terms]
	"""
	# 1. set_tenant
	session.queue_scalar(None)
	# 2. count query
	session.queue_count(total if total is not None else len(invoices))
	# 3. select invoices
	session.queue_scalars(invoices)
	# 4. batch payment sums (group by)
	session.queue_rows(payment_rows or [])
	# 5. batch order terms (only if any invoice has order_id)
	if order_term_rows is not None or any(inv.order_id for inv in invoices):
		session.queue_rows(order_term_rows or [])


def _queue_get_invoice_detail(
	session: FakeAsyncSession,
	invoice: FakeInvoice,
	amount_paid: Decimal = Decimal("0"),
	payment_terms_days: int | None = None,
) -> None:
	"""Queue results for get invoice detail with payment summary.

	Flow: set_tenant → get_invoice → SUM(payments) → [order.payment_terms_days]
	"""
	# 1. set_tenant (inside session.begin() before get_invoice)
	session.queue_scalar(None)
	# 2. get_invoice (selectinload)
	session.queue_scalar(invoice)
	# 3. SUM(matched payments)
	session.queue_scalar(amount_paid)
	# 4. order.payment_terms_days (if invoice has order_id)
	if invoice.order_id is not None:
		session.queue_scalar(payment_terms_days)


def _queue_customer_outstanding(
	session: FakeAsyncSession,
	customer_exists: bool,
	invoices: list[FakeInvoice],
	payment_rows: list[FakePaymentRow] | None = None,
	order_term_rows: list[FakeOrderTermsRow] | None = None,
) -> None:
	"""Queue results for customer outstanding endpoint (single transaction).

	Flow: set_tenant → verify customer → select invoices → batch payments → [batch orders]
	"""
	# set_tenant
	session.queue_scalar(None)
	# verify customer existence
	if not customer_exists:
		session.queue_scalar(None)  # customer not found
		return
	session.queue_scalar(uuid.uuid4())  # customer.id exists
	# select invoices
	session.queue_scalars(invoices)
	# batch payment sums
	session.queue_rows(payment_rows or [])
	# batch order terms
	if order_term_rows is not None or any(inv.order_id for inv in invoices):
		session.queue_rows(order_term_rows or [])


def _compiled_sql(statement: object) -> tuple[str, dict[str, Any]]:
	compiled = cast(Any, statement).compile()
	return " ".join(str(compiled).split()).lower(), dict(compiled.params)


def _find_invoice_page_statement(session: RecordingAsyncSession) -> object:
	for statement in session.statements:
		sql = " ".join(str(statement).split()).lower()
		if " from invoices " in f" {sql} " and " order by " in f" {sql} ":
			return statement
	raise AssertionError("Invoice list query was not captured")


# ── Tests: Invoice List ──────────────────────────────────────


@pytest.mark.anyio
async def test_invoice_list_returns_payment_columns():
	"""AC1: Invoice list shows amount_paid, outstanding_balance, payment_status."""
	session = FakeAsyncSession()
	inv = FakeInvoice(total_amount=Decimal("1000.00"))
	_queue_list_invoices(session, [inv])

	prev = setup_session(session)
	try:
		resp = await http_get("/api/v1/invoices")
		assert resp.status_code == 200
		body = resp.json()
		assert body["total"] == 1
		item = body["items"][0]
		assert "amount_paid" in item
		assert "outstanding_balance" in item
		assert "payment_status" in item
		assert item["payment_status"] == "unpaid"
		assert item["outstanding_balance"] == "1000.00"
	finally:
		teardown_session(prev)


@pytest.mark.anyio
async def test_invoice_list_paid_filter():
	"""AC4: Filtering by payment_status=paid."""
	session = FakeAsyncSession()
	inv = FakeInvoice(total_amount=Decimal("500.00"))
	pay_row = FakePaymentRow(inv.id, Decimal("500.00"))
	_queue_list_invoices(session, [inv], payment_rows=[pay_row])

	prev = setup_session(session)
	try:
		resp = await http_get("/api/v1/invoices?payment_status=paid")
		assert resp.status_code == 200
		body = resp.json()
		item = body["items"][0]
		assert item["payment_status"] == "paid"
	finally:
		teardown_session(prev)


@pytest.mark.anyio
async def test_invoice_list_paid_query_includes_legacy_paid_status() -> None:
	"""Deferred fix: paid filter must keep legacy invoices already marked paid."""
	session = RecordingAsyncSession()
	inv = FakeInvoice(total_amount=Decimal("500.00"), status="paid")
	_queue_list_invoices(session, [inv])

	items, total = await list_invoices(session, tenant_id=TENANT_ID, payment_status="paid")

	assert total == 1
	assert items[0]["payment_status"] == "paid"
	statement = _find_invoice_page_statement(session)
	sql, params = _compiled_sql(statement)
	assert re.search(r"invoices\.status = :status_\d+ or case when", sql)
	assert "paid" in params.values()


@pytest.mark.anyio
async def test_invoice_list_sort_by_outstanding():
	"""AC2: Sort by outstanding_balance."""
	session = FakeAsyncSession()
	inv = FakeInvoice()
	_queue_list_invoices(session, [inv])

	prev = setup_session(session)
	try:
		resp = await http_get("/api/v1/invoices?sort_by=outstanding_balance&sort_order=desc")
		assert resp.status_code == 200
		body = resp.json()
		assert body["page"] == 1
	finally:
		teardown_session(prev)


@pytest.mark.anyio
async def test_invoice_list_outstanding_sort_uses_clamped_balance_expression() -> None:
	"""Deferred fix: outstanding sort should use the same zero-clamped balance shown in UI."""
	session = RecordingAsyncSession()
	inv = FakeInvoice(total_amount=Decimal("500.00"))
	_queue_list_invoices(session, [inv], payment_rows=[FakePaymentRow(inv.id, Decimal("600.00"))])

	await list_invoices(session, tenant_id=TENANT_ID, sort_by="outstanding_balance")

	statement = _find_invoice_page_statement(session)
	sql, _params = _compiled_sql(statement)
	assert "order by case when" in sql
	assert "invoices.total_amount - (select coalesce(sum(payments.amount)" in sql


@pytest.mark.anyio
async def test_invoice_list_empty():
	session = FakeAsyncSession()
	_queue_list_invoices(session, [])

	prev = setup_session(session)
	try:
		resp = await http_get("/api/v1/invoices")
		assert resp.status_code == 200
		body = resp.json()
		assert body["items"] == []
		assert body["total"] == 0
	finally:
		teardown_session(prev)


@pytest.mark.anyio
async def test_invoice_list_overdue_highlighting():
	"""AC3: Overdue invoices have payment_status='overdue'."""
	session = FakeAsyncSession()
	# Invoice dated 60 days ago, no payments → overdue with default 30-day terms
	past_date = date.today() - timedelta(days=60)
	inv = FakeInvoice(total_amount=Decimal("1000.00"), invoice_date=past_date)
	_queue_list_invoices(session, [inv])

	prev = setup_session(session)
	try:
		resp = await http_get("/api/v1/invoices")
		assert resp.status_code == 200
		item = resp.json()["items"][0]
		assert item["payment_status"] == "overdue"
		assert item["days_overdue"] > 0
	finally:
		teardown_session(prev)


# ── Tests: Invoice Detail ────────────────────────────────────


@pytest.mark.anyio
async def test_invoice_detail_includes_payment_summary():
	"""AC5/AC6: Invoice detail shows payment summary with computed fields."""
	session = FakeAsyncSession()
	inv = FakeInvoice(total_amount=Decimal("1000.00"))
	_queue_get_invoice_detail(session, inv, amount_paid=Decimal("300.00"))

	prev = setup_session(session)
	try:
		resp = await http_get(f"/api/v1/invoices/{inv.id}")
		assert resp.status_code == 200
		body = resp.json()
		assert body["amount_paid"] == "300.00"
		assert body["outstanding_balance"] == "700.00"
		assert body["payment_status"] == "partial"
		assert body["due_date"] is not None
		assert body["days_overdue"] == 0
	finally:
		teardown_session(prev)


@pytest.mark.anyio
async def test_invoice_detail_fully_paid():
	session = FakeAsyncSession()
	inv = FakeInvoice(total_amount=Decimal("500.00"))
	_queue_get_invoice_detail(session, inv, amount_paid=Decimal("500.00"))

	prev = setup_session(session)
	try:
		resp = await http_get(f"/api/v1/invoices/{inv.id}")
		assert resp.status_code == 200
		body = resp.json()
		assert body["payment_status"] == "paid"
		assert Decimal(body["outstanding_balance"]) == Decimal("0")
	finally:
		teardown_session(prev)


@pytest.mark.anyio
async def test_invoice_detail_overdue():
	session = FakeAsyncSession()
	past_date = date.today() - timedelta(days=60)
	inv = FakeInvoice(total_amount=Decimal("1000.00"), invoice_date=past_date)
	_queue_get_invoice_detail(session, inv, amount_paid=Decimal("0"))

	prev = setup_session(session)
	try:
		resp = await http_get(f"/api/v1/invoices/{inv.id}")
		assert resp.status_code == 200
		body = resp.json()
		assert body["payment_status"] == "overdue"
		assert body["days_overdue"] > 0
	finally:
		teardown_session(prev)


@pytest.mark.anyio
async def test_invoice_detail_with_order_payment_terms():
	"""Due date uses order.payment_terms_days when linked."""
	session = FakeAsyncSession()
	order_id = uuid.uuid4()
	inv = FakeInvoice(
		total_amount=Decimal("1000.00"),
		invoice_date=date.today(),
		order_id=order_id,
	)
	_queue_get_invoice_detail(session, inv, amount_paid=Decimal("0"), payment_terms_days=60)

	prev = setup_session(session)
	try:
		resp = await http_get(f"/api/v1/invoices/{inv.id}")
		assert resp.status_code == 200
		body = resp.json()
		expected_due = (date.today() + timedelta(days=60)).isoformat()
		assert body["due_date"] == expected_due
		assert body["payment_status"] == "unpaid"
	finally:
		teardown_session(prev)


@pytest.mark.anyio
async def test_invoice_detail_stored_paid_status():
	"""Stored status 'paid' takes priority over dynamic outstanding computation."""
	session = FakeAsyncSession()
	inv = FakeInvoice(total_amount=Decimal("1000.00"), status="paid")
	_queue_get_invoice_detail(session, inv, amount_paid=Decimal("1000.00"))

	prev = setup_session(session)
	try:
		resp = await http_get(f"/api/v1/invoices/{inv.id}")
		assert resp.status_code == 200
		body = resp.json()
		assert body["payment_status"] == "paid"
		assert Decimal(body["outstanding_balance"]) == Decimal("0")
	finally:
		teardown_session(prev)


@pytest.mark.anyio
async def test_invoice_detail_not_found():
	session = FakeAsyncSession()
	session.queue_scalar(None)  # set_tenant
	session.queue_scalar(None)  # get_invoice returns None

	prev = setup_session(session)
	try:
		resp = await http_get(f"/api/v1/invoices/{uuid.uuid4()}")
		assert resp.status_code == 404
	finally:
		teardown_session(prev)


@pytest.mark.anyio
async def test_invoice_detail_creates_persisted_egui_state_when_enabled(monkeypatch: pytest.MonkeyPatch):
	"""Story 12.3: enabled tenants get durable eGUI state on invoice detail."""
	session = FakeAsyncSession()
	inv = FakeInvoice(total_amount=Decimal("1000.00"))
	inv.buyer_type = "b2c"
	_queue_get_invoice_detail(session, inv, amount_paid=Decimal("0"))
	session.queue_scalar(None)  # no persisted EguiSubmission yet

	settings = SimpleNamespace(egui_tracking_enabled=True, egui_submission_mode="mock")
	monkeypatch.setattr("domains.invoices.routes.get_settings", lambda: settings)
	monkeypatch.setattr("domains.invoices.service.get_settings", lambda: settings, raising=False)

	prev = setup_session(session)
	try:
		resp = await http_get(f"/api/v1/invoices/{inv.id}")
		assert resp.status_code == 200
		body = resp.json()
		assert body["egui_submission"]["status"] == "PENDING"
		assert body["egui_submission"]["mode"] == "mock"
		assert body["egui_submission"]["deadline_label"] == "48-hour submission window"
		assert len(session.added) == 1
	finally:
		teardown_session(prev)


@pytest.mark.anyio
async def test_invoice_detail_hides_egui_state_when_disabled(monkeypatch: pytest.MonkeyPatch):
	"""Story 12.3: disabled tenants should not receive fake eGUI UI data."""
	session = FakeAsyncSession()
	inv = FakeInvoice(total_amount=Decimal("1000.00"))
	_queue_get_invoice_detail(session, inv, amount_paid=Decimal("0"))

	settings = SimpleNamespace(egui_tracking_enabled=False, egui_submission_mode="mock")
	monkeypatch.setattr("domains.invoices.routes.get_settings", lambda: settings)
	monkeypatch.setattr("domains.invoices.service.get_settings", lambda: settings, raising=False)

	prev = setup_session(session)
	try:
		resp = await http_get(f"/api/v1/invoices/{inv.id}")
		assert resp.status_code == 200
		assert resp.json().get("egui_submission") is None
	finally:
		teardown_session(prev)


@pytest.mark.anyio
async def test_get_invoice_egui_submission_recovers_from_duplicate_insert() -> None:
	"""Story 12.3 review fix: concurrent first-read insert should reuse the existing row."""
	session = FlushConflictSession()
	inv = FakeInvoice(total_amount=Decimal("1000.00"))
	existing = FakeEguiSubmission(invoice_id=inv.id, status="QUEUED")
	session.queue_scalar(None)
	session.queue_scalar(existing)

	submission = await get_invoice_egui_submission(
		session,
		cast(Invoice, inv),
		TENANT_ID,
		enabled=True,
		mode="mock",
	)

	assert submission is existing
	assert session.raise_integrity_error is False


@pytest.mark.anyio
async def test_invoice_egui_refresh_advances_mock_status(monkeypatch: pytest.MonkeyPatch):
	"""Story 12.3: manual refresh rehydrates state from backend mock provider."""
	session = FakeAsyncSession()
	inv = FakeInvoice(total_amount=Decimal("1000.00"))
	session.queue_scalar(None)  # set_tenant
	session.queue_scalar(inv)
	session.queue_scalar(FakeEguiSubmission(invoice_id=inv.id, status="PENDING"))

	settings = SimpleNamespace(egui_tracking_enabled=True, egui_submission_mode="mock")
	monkeypatch.setattr("domains.invoices.routes.get_settings", lambda: settings)
	monkeypatch.setattr("domains.invoices.service.get_settings", lambda: settings, raising=False)

	prev = setup_session(session)
	try:
		resp = await http_post(f"/api/v1/invoices/{inv.id}/egui/refresh", json={})
		assert resp.status_code == 200
		body = resp.json()
		assert body["status"] == "QUEUED"
		assert body["mode"] == "mock"
	finally:
		teardown_session(prev)


@pytest.mark.anyio
async def test_invoice_egui_refresh_rejects_live_mode(monkeypatch: pytest.MonkeyPatch):
	"""Story 12.3: live-mode refresh must fail fast until FIA refresh exists."""
	session = FakeAsyncSession()
	inv = FakeInvoice(total_amount=Decimal("1000.00"))

	settings = SimpleNamespace(egui_tracking_enabled=True, egui_submission_mode="live")
	monkeypatch.setattr("domains.invoices.routes.get_settings", lambda: settings)
	monkeypatch.setattr("domains.invoices.service.get_settings", lambda: settings, raising=False)

	prev = setup_session(session)
	try:
		resp = await http_post(f"/api/v1/invoices/{inv.id}/egui/refresh", json={})
		assert resp.status_code == 503
		assert resp.json()["detail"] == "Live eGUI refresh is not implemented"
	finally:
		teardown_session(prev)


@pytest.mark.anyio
async def test_invoice_egui_refresh_recovers_from_invalid_persisted_status(monkeypatch: pytest.MonkeyPatch):
	"""Story 12.3 review fix: invalid persisted states should not 500 on refresh."""
	session = FakeAsyncSession()
	inv = FakeInvoice(total_amount=Decimal("1000.00"))
	session.queue_scalar(None)
	session.queue_scalar(inv)
	session.queue_scalar(FakeEguiSubmission(invoice_id=inv.id, status="BROKEN"))

	settings = SimpleNamespace(egui_tracking_enabled=True, egui_submission_mode="mock")
	monkeypatch.setattr("domains.invoices.routes.get_settings", lambda: settings)
	monkeypatch.setattr("domains.invoices.service.get_settings", lambda: settings, raising=False)

	prev = setup_session(session)
	try:
		resp = await http_post(f"/api/v1/invoices/{inv.id}/egui/refresh", json={})
		assert resp.status_code == 200
		assert resp.json()["status"] == "QUEUED"
	finally:
		teardown_session(prev)


# ── Tests: Customer Outstanding ───────────────────────────────


@pytest.mark.anyio
async def test_customer_outstanding_summary():
	"""AC7: Customer outstanding aggregates across invoices."""
	session = FakeAsyncSession()
	cid = uuid.uuid4()
	inv1 = FakeInvoice(total_amount=Decimal("1000.00"), customer_id=cid)
	inv2 = FakeInvoice(total_amount=Decimal("500.00"), customer_id=cid)
	pay_row = FakePaymentRow(inv1.id, Decimal("400.00"))
	_queue_customer_outstanding(session, True, [inv1, inv2], payment_rows=[pay_row])

	prev = setup_session(session)
	try:
		resp = await http_get(f"/api/v1/customers/{cid}/outstanding")
		assert resp.status_code == 200
		body = resp.json()
		# inv1: 1000 - 400 = 600 outstanding
		# inv2: 500 - 0 = 500 outstanding
		# total: 1100
		assert body["total_outstanding"] == "1100.00"
		assert body["invoice_count"] == 2
	finally:
		teardown_session(prev)


@pytest.mark.anyio
async def test_customer_outstanding_not_found():
	session = FakeAsyncSession()
	_queue_customer_outstanding(session, False, [])

	prev = setup_session(session)
	try:
		resp = await http_get(f"/api/v1/customers/{uuid.uuid4()}/outstanding")
		assert resp.status_code == 404
	finally:
		teardown_session(prev)


@pytest.mark.anyio
async def test_customer_outstanding_with_overdue():
	"""AC7: Overdue count and amount reported."""
	session = FakeAsyncSession()
	cid = uuid.uuid4()
	past_date = date.today() - timedelta(days=60)
	inv_overdue = FakeInvoice(
		total_amount=Decimal("800.00"),
		customer_id=cid,
		invoice_date=past_date,
	)
	inv_current = FakeInvoice(
		total_amount=Decimal("200.00"),
		customer_id=cid,
		invoice_date=date.today(),
	)
	_queue_customer_outstanding(session, True, [inv_overdue, inv_current])

	prev = setup_session(session)
	try:
		resp = await http_get(f"/api/v1/customers/{cid}/outstanding")
		assert resp.status_code == 200
		body = resp.json()
		assert body["overdue_count"] == 1
		assert body["overdue_amount"] == "800.00"
	finally:
		teardown_session(prev)


@pytest.mark.anyio
async def test_customer_outstanding_rejects_mixed_currency_receivables():
	"""Deferred fix: outstanding summary must not silently add different currencies."""
	session = FakeAsyncSession()
	cid = uuid.uuid4()
	inv_twd = FakeInvoice(total_amount=Decimal("1000.00"), customer_id=cid)
	inv_usd = FakeInvoice(total_amount=Decimal("250.00"), customer_id=cid)
	inv_usd.currency_code = "USD"
	_queue_customer_outstanding(session, True, [inv_twd, inv_usd])

	prev = setup_session(session)
	try:
		resp = await http_get(f"/api/v1/customers/{cid}/outstanding")
		assert resp.status_code == 409
		assert resp.json()["detail"] == (
			"Customer outstanding summary is unavailable for mixed-currency receivables."
		)
	finally:
		teardown_session(prev)


@pytest.mark.anyio
async def test_batch_enrichment_no_payments():
	"""Invoices with zero payments show unpaid status."""
	session = FakeAsyncSession()
	inv = FakeInvoice(total_amount=Decimal("300.00"))
	_queue_list_invoices(session, [inv], payment_rows=[])

	prev = setup_session(session)
	try:
		resp = await http_get("/api/v1/invoices")
		assert resp.status_code == 200
		item = resp.json()["items"][0]
		# Decimal("0") serializes as "0" not "0.00"
		assert Decimal(item["amount_paid"]) == Decimal("0")
		assert item["outstanding_balance"] == "300.00"
		assert item["payment_status"] == "unpaid"
	finally:
		teardown_session(prev)


@pytest.mark.anyio
async def test_voided_invoice_payment_status():
	"""Voided invoices show payment_status='voided'."""
	session = FakeAsyncSession()
	inv = FakeInvoice(total_amount=Decimal("1000.00"), status="voided")
	_queue_list_invoices(session, [inv])

	prev = setup_session(session)
	try:
		resp = await http_get("/api/v1/invoices")
		assert resp.status_code == 200
		item = resp.json()["items"][0]
		assert item["payment_status"] == "voided"
	finally:
		teardown_session(prev)


@pytest.mark.anyio
async def test_overpayment_outstanding_clamped_to_zero():
	"""Overpayment (paid > total) should show outstanding=0 and status=paid."""
	session = FakeAsyncSession()
	inv = FakeInvoice(total_amount=Decimal("500.00"))
	pay_row = FakePaymentRow(inv.id, Decimal("600.00"))  # overpaid
	_queue_list_invoices(session, [inv], payment_rows=[pay_row])

	prev = setup_session(session)
	try:
		resp = await http_get("/api/v1/invoices")
		assert resp.status_code == 200
		item = resp.json()["items"][0]
		assert item["payment_status"] == "paid"
		assert Decimal(item["outstanding_balance"]) == Decimal("0")
	finally:
		teardown_session(prev)


@pytest.mark.anyio
async def test_invoice_list_unpaid_filter():
	"""Filtering by payment_status=unpaid returns only fully-unpaid invoices."""
	session = FakeAsyncSession()
	inv = FakeInvoice(total_amount=Decimal("800.00"))
	_queue_list_invoices(session, [inv], payment_rows=[])

	prev = setup_session(session)
	try:
		resp = await http_get("/api/v1/invoices?payment_status=unpaid")
		assert resp.status_code == 200
		body = resp.json()
		item = body["items"][0]
		assert item["payment_status"] == "unpaid"
		assert Decimal(item["amount_paid"]) == Decimal("0")
		assert item["outstanding_balance"] == "800.00"
	finally:
		teardown_session(prev)


@pytest.mark.anyio
async def test_invoice_list_unpaid_query_excludes_legacy_paid_status() -> None:
	"""Deferred fix: unpaid filter must not leak invoices already marked paid."""
	session = RecordingAsyncSession()
	inv = FakeInvoice(total_amount=Decimal("800.00"), status="issued")
	_queue_list_invoices(session, [inv], payment_rows=[])

	await list_invoices(session, tenant_id=TENANT_ID, payment_status="unpaid")

	statement = _find_invoice_page_statement(session)
	sql, params = _compiled_sql(statement)
	status_lists = [
		list(value)
		for value in params.values()
		if isinstance(value, (list, tuple))
	]
	assert "not in" in sql
	assert ["voided", "paid"] in status_lists


@pytest.mark.anyio
async def test_invoice_list_partial_filter():
	"""Filtering by payment_status=partial returns partially-paid invoices."""
	session = FakeAsyncSession()
	inv = FakeInvoice(total_amount=Decimal("1000.00"))
	pay_row = FakePaymentRow(inv.id, Decimal("200.00"))
	_queue_list_invoices(session, [inv], payment_rows=[pay_row])

	prev = setup_session(session)
	try:
		resp = await http_get("/api/v1/invoices?payment_status=partial")
		assert resp.status_code == 200
		body = resp.json()
		item = body["items"][0]
		assert item["payment_status"] == "partial"
		assert item["amount_paid"] == "200.00"
		assert item["outstanding_balance"] == "800.00"
	finally:
		teardown_session(prev)


@pytest.mark.anyio
async def test_customer_outstanding_zero_invoices():
	"""Customer with zero invoices returns zeroed summary."""
	session = FakeAsyncSession()
	_queue_customer_outstanding(session, True, [])

	prev = setup_session(session)
	try:
		cid = uuid.uuid4()
		resp = await http_get(f"/api/v1/customers/{cid}/outstanding")
		assert resp.status_code == 200
		body = resp.json()
		assert body["total_outstanding"] == "0"
		assert body["overdue_count"] == 0
		assert body["overdue_amount"] == "0"
		assert body["invoice_count"] == 0
	finally:
		teardown_session(prev)
