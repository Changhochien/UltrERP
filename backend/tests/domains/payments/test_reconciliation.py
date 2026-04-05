"""Tests for payment reconciliation API endpoints."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from tests.domains.orders._helpers import (
    FakeAsyncSession,
    http_post,
    setup_session,
    teardown_session,
)

# ── Fake domain objects ───────────────────────────────────────

TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


class FakeInvoice:
    def __init__(
        self,
        *,
        total_amount: Decimal = Decimal("1000.00"),
        status: str = "issued",
        customer_id: uuid.UUID | None = None,
        invoice_date: date | None = None,
    ):
        self.id = uuid.uuid4()
        self.tenant_id = TENANT_ID
        self.customer_id = customer_id or uuid.uuid4()
        self.invoice_number = f"AA{uuid.uuid4().hex[:8].upper()}"
        self.total_amount = total_amount
        self.status = status
        self.invoice_date = invoice_date or date.today()
        self.updated_at = datetime.now(tz=UTC)


class FakePayment:
    def __init__(
        self,
        *,
        invoice_id: uuid.UUID | None = None,
        customer_id: uuid.UUID | None = None,
        amount: Decimal = Decimal("500.00"),
        match_status: str = "unmatched",
        match_type: str | None = None,
        suggested_invoice_id: uuid.UUID | None = None,
        payment_date: date | None = None,
    ):
        self.id = uuid.uuid4()
        self.tenant_id = TENANT_ID
        self.invoice_id = invoice_id
        self.customer_id = customer_id or uuid.uuid4()
        self.payment_ref = f"PAY-{date.today().strftime('%Y%m%d')}-0001"
        self.amount = amount
        self.payment_method = "BANK_TRANSFER"
        self.payment_date = payment_date or date.today()
        self.reference_number = None
        self.notes = None
        self.created_by = str(TENANT_ID)
        self.created_at = datetime.now(tz=UTC)
        self.updated_at = datetime.now(tz=UTC)
        self.match_status = match_status
        self.match_type = match_type
        self.matched_at = None
        self.suggested_invoice_id = suggested_invoice_id


# ── Queue helpers ─────────────────────────────────────────────


def _queue_record_unmatched(
    session: FakeAsyncSession,
    max_ref: str | None = None,
) -> None:
    """Queue results for record_unmatched_payment service call."""
    session.queue_scalar(None)  # set_tenant
    session.queue_scalar(uuid.uuid4())  # customer existence check
    session.queue_scalar(max_ref)  # MAX(payment_ref)


def _queue_reconciliation(
    session: FakeAsyncSession,
    unmatched_payments: list[FakePayment],
    invoices_per_payment: list[list[FakeInvoice]],
    date_candidates_per_payment: list[FakeInvoice | None] | None = None,
) -> None:
    """Queue results for run_reconciliation service call.

    For each unmatched payment:
      - exact match query returns invoices_per_payment[i]
      - if no exact match: date proximity query returns date_candidates_per_payment[i]
    """
    session.queue_scalar(None)  # set_tenant
    session.queue_scalars(unmatched_payments)  # unmatched payments query

    for i, payment in enumerate(unmatched_payments):
        exact_invoices = invoices_per_payment[i] if i < len(invoices_per_payment) else []
        session.queue_scalars(exact_invoices)  # exact match query

        if len(exact_invoices) == 1:
            # Auto-allocate: needs paid_total query for _allocate_payment
            session.queue_scalar(Decimal("0"))  # SUM of existing payments
        elif len(exact_invoices) == 0:
            # Try date proximity
            candidate = (
                (date_candidates_per_payment or [])[i]
                if date_candidates_per_payment and i < len(date_candidates_per_payment)
                else None
            )
            session.queue_scalar(candidate)  # date proximity query


def _queue_confirm_match(
    session: FakeAsyncSession,
    payment: FakePayment,
    invoice: FakeInvoice,
    paid_total: Decimal = Decimal("0"),
) -> None:
    """Queue results for confirm_suggested_match service call."""
    session.queue_scalar(None)  # set_tenant
    session.queue_scalar(payment)  # fetch payment
    session.queue_scalar(invoice)  # fetch suggested invoice
    session.queue_scalar(paid_total)  # outstanding balance check
    session.queue_scalar(Decimal("0"))  # SUM in _allocate_payment


def _queue_manual_match(
    session: FakeAsyncSession,
    payment: FakePayment,
    invoice: FakeInvoice,
    paid_total: Decimal = Decimal("0"),
) -> None:
    """Queue results for manual_match service call."""
    session.queue_scalar(None)  # set_tenant
    session.queue_scalar(payment)  # fetch payment
    session.queue_scalar(invoice)  # fetch invoice
    session.queue_scalar(paid_total)  # outstanding balance
    session.queue_scalar(Decimal("0"))  # _allocate_payment: SUM of other matched payments


# ── Tests ─────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_record_unmatched_payment():
    session = FakeAsyncSession()
    _queue_record_unmatched(session)
    prev = setup_session(session)
    try:
        resp = await http_post(
            "/api/v1/payments/unmatched",
            {
                "customer_id": str(uuid.uuid4()),
                "amount": "200.00",
                "payment_method": "BANK_TRANSFER",
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["match_status"] == "unmatched"
        assert body["match_type"] is None
        assert body["invoice_id"] is None
    finally:
        teardown_session(prev)


@pytest.mark.anyio
async def test_reconciliation_exact_match():
    """Exact amount match: single invoice auto-allocated."""
    customer_id = uuid.uuid4()
    payment = FakePayment(customer_id=customer_id, amount=Decimal("1000.00"))
    invoice = FakeInvoice(customer_id=customer_id, total_amount=Decimal("1000.00"))

    session = FakeAsyncSession()
    _queue_reconciliation(session, [payment], [[invoice]])
    prev = setup_session(session)
    try:
        resp = await http_post("/api/v1/payments/reconcile", {})
        assert resp.status_code == 200
        body = resp.json()
        assert body["matched_count"] == 1
        assert body["suggested_count"] == 0
        assert body["unmatched_count"] == 0
        assert body["details"][0]["match_status"] == "matched"
        assert body["details"][0]["match_type"] == "exact_amount"
    finally:
        teardown_session(prev)


@pytest.mark.anyio
async def test_reconciliation_exact_match_multiple_invoices_suggests():
    """Multiple exact matches: first (oldest) suggested, not auto-allocated."""
    customer_id = uuid.uuid4()
    payment = FakePayment(customer_id=customer_id, amount=Decimal("500.00"))
    inv1 = FakeInvoice(customer_id=customer_id, total_amount=Decimal("500.00"))
    inv2 = FakeInvoice(customer_id=customer_id, total_amount=Decimal("500.00"))

    session = FakeAsyncSession()
    _queue_reconciliation(session, [payment], [[inv1, inv2]])
    prev = setup_session(session)
    try:
        resp = await http_post("/api/v1/payments/reconcile", {})
        assert resp.status_code == 200
        body = resp.json()
        assert body["matched_count"] == 0
        assert body["suggested_count"] == 1
        assert body["unmatched_count"] == 0
    finally:
        teardown_session(prev)


@pytest.mark.anyio
async def test_reconciliation_date_proximity_suggested():
    """No exact match, but date proximity candidate found — suggested."""
    customer_id = uuid.uuid4()
    payment = FakePayment(customer_id=customer_id, amount=Decimal("300.00"))
    candidate = FakeInvoice(
        customer_id=customer_id,
        total_amount=Decimal("500.00"),
        invoice_date=date.today() - timedelta(days=5),
    )

    session = FakeAsyncSession()
    _queue_reconciliation(session, [payment], [[]], [candidate])
    prev = setup_session(session)
    try:
        resp = await http_post("/api/v1/payments/reconcile", {})
        assert resp.status_code == 200
        body = resp.json()
        assert body["matched_count"] == 0
        assert body["suggested_count"] == 1
        assert body["unmatched_count"] == 0
    finally:
        teardown_session(prev)


@pytest.mark.anyio
async def test_reconciliation_no_match():
    """No match at all — payment stays unmatched."""
    payment = FakePayment(amount=Decimal("999.00"))

    session = FakeAsyncSession()
    _queue_reconciliation(session, [payment], [[]], [None])
    prev = setup_session(session)
    try:
        resp = await http_post("/api/v1/payments/reconcile", {})
        assert resp.status_code == 200
        body = resp.json()
        assert body["matched_count"] == 0
        assert body["suggested_count"] == 0
        assert body["unmatched_count"] == 1
    finally:
        teardown_session(prev)


@pytest.mark.anyio
async def test_reconciliation_empty():
    """No unmatched payments — empty result."""
    session = FakeAsyncSession()
    session.queue_scalar(None)  # set_tenant
    session.queue_scalars([])  # no unmatched payments
    prev = setup_session(session)
    try:
        resp = await http_post("/api/v1/payments/reconcile", {})
        assert resp.status_code == 200
        body = resp.json()
        assert body["matched_count"] == 0
        assert body["suggested_count"] == 0
        assert body["unmatched_count"] == 0
    finally:
        teardown_session(prev)


@pytest.mark.anyio
async def test_confirm_suggested_match():
    """Confirm a suggested match allocates payment to invoice."""
    customer_id = uuid.uuid4()
    invoice = FakeInvoice(customer_id=customer_id, total_amount=Decimal("500.00"))
    payment = FakePayment(
        customer_id=customer_id,
        amount=Decimal("500.00"),
        match_status="suggested",
        suggested_invoice_id=invoice.id,
    )

    session = FakeAsyncSession()
    _queue_confirm_match(session, payment, invoice)
    prev = setup_session(session)
    try:
        resp = await http_post(f"/api/v1/payments/{payment.id}/confirm-match", {})
        assert resp.status_code == 200
        body = resp.json()
        assert body["match_status"] == "matched"
    finally:
        teardown_session(prev)


@pytest.mark.anyio
async def test_confirm_match_no_suggestion_returns_422():
    """Trying to confirm a payment with no suggestion fails."""
    payment = FakePayment(match_status="unmatched", suggested_invoice_id=None)

    session = FakeAsyncSession()
    session.queue_scalar(None)  # set_tenant
    session.queue_scalar(payment)  # fetch payment
    prev = setup_session(session)
    try:
        resp = await http_post(f"/api/v1/payments/{payment.id}/confirm-match", {})
        assert resp.status_code == 422
    finally:
        teardown_session(prev)


@pytest.mark.anyio
async def test_manual_match_success():
    """Manual match allocates payment to specified invoice."""
    customer_id = uuid.uuid4()
    invoice = FakeInvoice(customer_id=customer_id, total_amount=Decimal("800.00"))
    payment = FakePayment(
        customer_id=customer_id,
        amount=Decimal("400.00"),
        match_status="unmatched",
    )

    session = FakeAsyncSession()
    _queue_manual_match(session, payment, invoice)
    prev = setup_session(session)
    try:
        resp = await http_post(
            f"/api/v1/payments/{payment.id}/manual-match",
            {
                "invoice_id": str(invoice.id),
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["match_status"] == "matched"
        assert body["match_type"] == "manual"
    finally:
        teardown_session(prev)


@pytest.mark.anyio
async def test_manual_match_cross_customer_returns_error():
    """Manual match rejects cross-customer allocation."""
    invoice = FakeInvoice(customer_id=uuid.uuid4())
    payment = FakePayment(customer_id=uuid.uuid4(), match_status="unmatched")

    session = FakeAsyncSession()
    _queue_manual_match(session, payment, invoice)
    prev = setup_session(session)
    try:
        resp = await http_post(
            f"/api/v1/payments/{payment.id}/manual-match",
            {
                "invoice_id": str(invoice.id),
            },
        )
        assert resp.status_code == 409
    finally:
        teardown_session(prev)


@pytest.mark.anyio
async def test_manual_match_already_matched_returns_422():
    """Manual match rejects already-matched payment."""
    payment = FakePayment(match_status="matched")

    session = FakeAsyncSession()
    session.queue_scalar(None)  # set_tenant
    session.queue_scalar(payment)  # fetch payment
    prev = setup_session(session)
    try:
        resp = await http_post(
            f"/api/v1/payments/{payment.id}/manual-match",
            {
                "invoice_id": str(uuid.uuid4()),
            },
        )
        assert resp.status_code == 422
    finally:
        teardown_session(prev)


@pytest.mark.anyio
async def test_auto_match_creates_audit_log():
    """Auto-match creates an audit log entry."""
    customer_id = uuid.uuid4()
    payment = FakePayment(customer_id=customer_id, amount=Decimal("1000.00"))
    invoice = FakeInvoice(customer_id=customer_id, total_amount=Decimal("1000.00"))

    session = FakeAsyncSession()
    _queue_reconciliation(session, [payment], [[invoice]])
    prev = setup_session(session)
    try:
        resp = await http_post("/api/v1/payments/reconcile", {})
        assert resp.status_code == 200
        # Check that audit log was added
        audit_logs = [
            obj
            for obj in session.added
            if hasattr(obj, "action") and obj.action == "PAYMENT_MATCHED_AUTO"
        ]
        assert len(audit_logs) == 1
        assert audit_logs[0].entity_type == "payment"
    finally:
        teardown_session(prev)


@pytest.mark.anyio
async def test_reconciliation_returns_correct_counts():
    """Reconciliation returns correct summary counts for mixed results."""
    cust1 = uuid.uuid4()
    cust2 = uuid.uuid4()

    # Payment 1: exact match (1 invoice)
    p1 = FakePayment(customer_id=cust1, amount=Decimal("500.00"))
    inv1 = FakeInvoice(customer_id=cust1, total_amount=Decimal("500.00"))

    # Payment 2: no match at all
    p2 = FakePayment(customer_id=cust2, amount=Decimal("999.99"))

    session = FakeAsyncSession()
    session.queue_scalar(None)  # set_tenant
    session.queue_scalars([p1, p2])  # unmatched payments

    # p1: exact match with 1 invoice → auto-allocate
    session.queue_scalars([inv1])  # exact match for p1
    session.queue_scalar(Decimal("0"))  # paid_total for _allocate_payment

    # p2: no exact match → date proximity → no match
    session.queue_scalars([])  # no exact match for p2
    session.queue_scalar(None)  # no date proximity match for p2

    prev = setup_session(session)
    try:
        resp = await http_post("/api/v1/payments/reconcile", {})
        assert resp.status_code == 200
        body = resp.json()
        assert body["matched_count"] == 1
        assert body["suggested_count"] == 0
        assert body["unmatched_count"] == 1
        assert len(body["details"]) == 2
    finally:
        teardown_session(prev)
