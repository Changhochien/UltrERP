"""Focused service tests for invoice calculation helpers.

These tests start with the pure business rules that drive Story 2.1:
tax policy resolution, line math using ``Decimal``, and buyer identifier
normalization for B2B vs B2C invoices.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import pytest

from common.errors import ValidationError
from domains.customers.models import Customer
from domains.invoices.enums import InvoiceStatus
from domains.invoices.models import Invoice, InvoiceLine, InvoiceNumberRange
from domains.invoices.schemas import InvoiceCreate, InvoiceCreateLine
from domains.invoices.service import (
    BuyerType,
    compute_void_deadline,
    create_invoice,
    get_invoice,
    normalize_buyer_identifier,
    void_invoice,
)
from domains.invoices.tax import (
    InvoiceLineAmounts,
    TaxPolicyCode,
    aggregate_invoice_totals,
    calculate_line_amounts,
    get_tax_policy,
)
from domains.invoices.validators import (
    IMMUTABLE_ERROR,
    IMMUTABLE_FIELDS,
    TotalsDiscrepancy,
    validate_invoice_totals,
)


class TestTaxPolicyLookup:
    def test_standard_policy_uses_mig_taxable_type(self) -> None:
        policy = get_tax_policy(TaxPolicyCode.STANDARD)

        assert policy.tax_type == 1
        assert policy.tax_rate == Decimal("0.05")

    def test_special_policy_uses_mig_special_type(self) -> None:
        policy = get_tax_policy(TaxPolicyCode.SPECIAL)

        assert policy.tax_type == 4
        assert policy.tax_rate == Decimal("0.10")

    def test_zero_rate_policy_tracks_reason(self) -> None:
        policy = get_tax_policy(TaxPolicyCode.ZERO)

        assert policy.tax_type == 2
        assert policy.tax_rate == Decimal("0.00")
        assert policy.zero_tax_rate_reason == "export"


class TestLineCalculation:
    def test_calculates_standard_tax_using_decimal_math(self) -> None:
        amounts = calculate_line_amounts(
            quantity=Decimal("2"),
            unit_price=Decimal("100.00"),
            policy_code=TaxPolicyCode.STANDARD,
        )

        assert amounts == InvoiceLineAmounts(
            subtotal=Decimal("200.00"),
            tax_amount=Decimal("10.00"),
            total_amount=Decimal("210.00"),
            tax_type=1,
            tax_rate=Decimal("0.05"),
            zero_tax_rate_reason=None,
        )

    def test_calculates_special_tax_rate(self) -> None:
        amounts = calculate_line_amounts(
            quantity=Decimal("3"),
            unit_price=Decimal("50.00"),
            policy_code=TaxPolicyCode.SPECIAL,
        )

        assert amounts.tax_type == 4
        assert amounts.tax_rate == Decimal("0.10")
        assert amounts.tax_amount == Decimal("15.00")
        assert amounts.total_amount == Decimal("165.00")

    def test_zero_rate_line_has_no_tax_amount(self) -> None:
        amounts = calculate_line_amounts(
            quantity=Decimal("4"),
            unit_price=Decimal("25.00"),
            policy_code=TaxPolicyCode.ZERO,
        )

        assert amounts.tax_type == 2
        assert amounts.tax_amount == Decimal("0.00")
        assert amounts.total_amount == Decimal("100.00")
        assert amounts.zero_tax_rate_reason == "export"

    def test_aggregates_multiple_line_totals(self) -> None:
        totals = aggregate_invoice_totals(
            [
                calculate_line_amounts(
                    quantity=Decimal("2"),
                    unit_price=Decimal("100.00"),
                    policy_code=TaxPolicyCode.STANDARD,
                ),
                calculate_line_amounts(
                    quantity=Decimal("1"),
                    unit_price=Decimal("80.00"),
                    policy_code=TaxPolicyCode.ZERO,
                ),
            ]
        )

        assert totals["subtotal_amount"] == Decimal("280.00")
        assert totals["tax_amount"] == Decimal("10.00")
        assert totals["total_amount"] == Decimal("290.00")


class TestBuyerNormalization:
    def test_normalizes_b2c_to_required_sentinel(self) -> None:
        assert normalize_buyer_identifier(BuyerType.B2C, None) == "0000000000"

    def test_accepts_valid_b2b_ban(self) -> None:
        assert normalize_buyer_identifier(BuyerType.B2B, "04595257") == "04595257"

    def test_rejects_invalid_b2b_ban(self) -> None:
        with pytest.raises(ValueError, match="buyer identifier"):
            normalize_buyer_identifier(BuyerType.B2B, "04595258")

    def test_rejects_b2c_with_explicit_identifier(self) -> None:
        with pytest.raises(ValueError, match="B2C"):
            normalize_buyer_identifier(BuyerType.B2C, "04595257")


class FakeResult:
    def __init__(self, obj: object | None = None) -> None:
        self._obj = obj

    def scalar_one_or_none(self) -> object | None:
        return self._obj


class FakeAsyncSession:
    def __init__(self) -> None:
        self.added: list[Any] = []
        self._execute_results: list[FakeResult] = []
        self._execute_index = 0

    def add(self, instance: object) -> None:
        self.added.append(instance)

    def add_all(self, instances: list[object]) -> None:
        self.added.extend(instances)

    def queue_result(self, obj: object | None) -> None:
        self._execute_results.append(FakeResult(obj))

    async def execute(self, statement: object, params: object = None) -> FakeResult:
        # ``set_tenant`` issues a TextClause that should not consume queued select results.
        if type(statement).__name__ == "TextClause":
            return FakeResult(None)

        if self._execute_index < len(self._execute_results):
            result = self._execute_results[self._execute_index]
            self._execute_index += 1
            return result
        return FakeResult(None)

    async def flush(self) -> None:
        for obj in self.added:
            if getattr(obj, "id", None) is None:
                obj.id = uuid.uuid4()  # type: ignore[attr-defined]

    async def refresh(self, instance: object) -> None:
        if getattr(instance, "created_at", None) is None:
            instance.created_at = None  # type: ignore[attr-defined]
        if getattr(instance, "updated_at", None) is None:
            instance.updated_at = None  # type: ignore[attr-defined]

    def begin(self) -> FakeAsyncSession:
        return self

    async def __aenter__(self) -> FakeAsyncSession:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None


def _customer(*, business_number: str = "04595257") -> Customer:
    return Customer(
        id=uuid.uuid4(),
        tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        company_name="台灣好公司有限公司",
        normalized_business_number=business_number,
        billing_address="台北市信義區信義路五段7號",
        contact_name="王大明",
        contact_phone="0912-345-678",
        contact_email="wang@example.com",
        credit_limit=Decimal("100000.00"),
    )


def _range(*, next_number: int = 12345678) -> InvoiceNumberRange:
    return InvoiceNumberRange(
        tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        prefix="AZ",
        start_number=12345678,
        end_number=12345699,
        next_number=next_number,
        is_active=True,
    )


def _invoice_create(**overrides: object) -> InvoiceCreate:
    defaults = {
        "customer_id": uuid.uuid4(),
        "buyer_type": BuyerType.B2B,
        "buyer_identifier": "04595257",
        "lines": [
            InvoiceCreateLine(
                product_id=uuid.uuid4(),
                product_code="P-100",
                description="測試商品",
                quantity=Decimal("2"),
                unit_price=Decimal("100.00"),
                tax_policy_code=TaxPolicyCode.STANDARD,
            )
        ],
    }
    defaults.update(overrides)
    return InvoiceCreate(**defaults)


class TestCreateInvoice:
    @pytest.mark.asyncio
    async def test_persists_snapshot_and_allocates_invoice_number(self) -> None:
        customer = _customer()
        range_record = _range()
        payload = _invoice_create(customer_id=customer.id)
        session = FakeAsyncSession()
        session.queue_result(customer)
        session.queue_result(range_record)

        invoice = await create_invoice(session, payload)

        assert invoice.invoice_number == "AZ12345678"
        assert invoice.customer_id == customer.id
        assert invoice.buyer_identifier_snapshot == "04595257"
        assert invoice.subtotal_amount == Decimal("200.00")
        assert invoice.tax_amount == Decimal("10.00")
        assert invoice.total_amount == Decimal("210.00")
        assert range_record.next_number == 12345679
        assert len(invoice.lines) == 1
        assert invoice.lines[0].description == "測試商品"
        assert invoice.lines[0].product_code_snapshot == "P-100"

    @pytest.mark.asyncio
    async def test_normalizes_b2c_identifier_in_persisted_invoice(self) -> None:
        customer = _customer()
        session = FakeAsyncSession()
        session.queue_result(customer)
        session.queue_result(_range())

        invoice = await create_invoice(
            session,
            _invoice_create(
                customer_id=customer.id,
                buyer_type=BuyerType.B2C,
                buyer_identifier=None,
            ),
        )

        assert invoice.buyer_identifier_snapshot == "0000000000"

    @pytest.mark.asyncio
    async def test_rejects_unknown_customer(self) -> None:
        session = FakeAsyncSession()
        session.queue_result(None)

        with pytest.raises(ValidationError) as exc_info:
            await create_invoice(session, _invoice_create())

        assert exc_info.value.errors == [
            {"field": "customer_id", "message": "Customer does not exist."}
        ]

    @pytest.mark.asyncio
    async def test_rejects_more_than_9999_lines(self) -> None:
        customer = _customer()
        session = FakeAsyncSession()
        session.queue_result(customer)

        lines = [
            InvoiceCreateLine(
                product_id=uuid.uuid4(),
                product_code=f"P-{index}",
                description="測試商品",
                quantity=Decimal("1"),
                unit_price=Decimal("1.00"),
                tax_policy_code=TaxPolicyCode.STANDARD,
            )
            for index in range(10000)
        ]

        with pytest.raises(ValidationError) as exc_info:
            await create_invoice(
                session,
                _invoice_create(customer_id=customer.id, lines=lines),
            )

        assert exc_info.value.errors == [
            {"field": "lines", "message": "Invoice line count must be between 1 and 9999."}
        ]

    @pytest.mark.asyncio
    async def test_rejects_exhausted_number_range(self) -> None:
        customer = _customer()
        session = FakeAsyncSession()
        session.queue_result(customer)
        session.queue_result(_range(next_number=12345700))

        with pytest.raises(ValidationError) as exc_info:
            await create_invoice(session, _invoice_create(customer_id=customer.id))

        assert exc_info.value.errors == [
            {"field": "invoice_number", "message": "No invoice numbers remain in the active range."}
        ]


# ── Void deadline computation ──────────────────────────────────

class TestComputeVoidDeadline:
    def test_jan_feb_period_deadline(self) -> None:
        assert compute_void_deadline(date(2025, 1, 15)) == date(2025, 3, 15)
        assert compute_void_deadline(date(2025, 2, 28)) == date(2025, 3, 15)

    def test_mar_apr_period_deadline(self) -> None:
        assert compute_void_deadline(date(2025, 3, 1)) == date(2025, 5, 15)
        assert compute_void_deadline(date(2025, 4, 30)) == date(2025, 5, 15)

    def test_nov_dec_period_wraps_to_next_year(self) -> None:
        assert compute_void_deadline(date(2025, 11, 1)) == date(2026, 1, 15)
        assert compute_void_deadline(date(2025, 12, 31)) == date(2026, 1, 15)


# ── Void invoice ───────────────────────────────────────────────


def _issued_invoice(
    *,
    invoice_date: date = date(2025, 3, 20),
    invoice_id: uuid.UUID | None = None,
) -> Invoice:
    """Create a fake issued invoice with one line for testing."""
    iid = invoice_id or uuid.uuid4()
    tid = uuid.UUID("00000000-0000-0000-0000-000000000001")
    inv = Invoice(
        id=iid,
        tenant_id=tid,
        invoice_number="AZ12345678",
        invoice_date=invoice_date,
        customer_id=uuid.uuid4(),
        buyer_type="b2b",
        buyer_identifier_snapshot="04595257",
        currency_code="TWD",
        subtotal_amount=Decimal("200.00"),
        tax_amount=Decimal("10.00"),
        total_amount=Decimal("210.00"),
        status="issued",
        version=1,
    )
    inv.lines = [
        InvoiceLine(
            id=uuid.uuid4(),
            invoice_id=iid,
            tenant_id=tid,
            line_number=1,
            product_id=uuid.uuid4(),
            product_code_snapshot="P-100",
            description="測試商品",
            quantity=Decimal("2"),
            unit_price=Decimal("100.00"),
            subtotal_amount=Decimal("200.00"),
            tax_type=1,
            tax_rate=Decimal("0.05"),
            tax_amount=Decimal("10.00"),
            total_amount=Decimal("210.00"),
        ),
    ]
    return inv


class TestVoidInvoice:
    @pytest.mark.asyncio
    async def test_void_invoice_within_window(self) -> None:
        invoice = _issued_invoice(invoice_date=date(2025, 3, 20))
        session = FakeAsyncSession()
        session.queue_result(invoice)

        # Void on April 1 — well within the May 15 deadline
        result = await void_invoice(
            session, invoice.id, reason="Billing error",
            now=datetime(2025, 4, 1, tzinfo=UTC),
        )

        assert result.status == "voided"
        assert result.voided_at is not None
        assert result.void_reason == "Billing error"
        # Audit log should have been added
        assert any(
            getattr(obj, "action", None) == "invoice.voided"
            for obj in session.added
        )

    @pytest.mark.asyncio
    async def test_void_rejected_after_window(self) -> None:
        invoice = _issued_invoice(invoice_date=date(2025, 3, 20))
        session = FakeAsyncSession()
        session.queue_result(invoice)

        # Void on June 1 — past the May 15 deadline
        with pytest.raises(ValueError, match="Void window expired"):
            await void_invoice(
                session, invoice.id, reason="Too late",
                now=datetime(2025, 6, 1, tzinfo=UTC),
            )

    @pytest.mark.asyncio
    async def test_void_rejected_for_already_voided(self) -> None:
        invoice = _issued_invoice()
        invoice.status = "voided"
        session = FakeAsyncSession()
        session.queue_result(invoice)

        with pytest.raises(ValueError, match="Cannot void invoice"):
            await void_invoice(
                session, invoice.id, reason="Double void",
                now=datetime(2025, 4, 1, tzinfo=UTC),
            )

    @pytest.mark.asyncio
    async def test_void_not_found(self) -> None:
        session = FakeAsyncSession()
        session.queue_result(None)

        with pytest.raises(ValueError, match="Invoice not found"):
            await void_invoice(
                session, uuid.uuid4(), reason="Missing",
                now=datetime(2025, 4, 1, tzinfo=UTC),
            )


# ── Totals validation ──────────────────────────────────────────

class TestValidateInvoiceTotals:
    def test_valid_totals_returns_empty(self) -> None:
        invoice = _issued_invoice()
        discrepancies = validate_invoice_totals(invoice)
        assert discrepancies == []

    def test_subtotal_mismatch_detected(self) -> None:
        invoice = _issued_invoice()
        invoice.subtotal_amount = Decimal("999.99")

        discrepancies = validate_invoice_totals(invoice)
        fields = {d.field for d in discrepancies}
        assert "subtotal_amount" in fields

    def test_tax_mismatch_detected(self) -> None:
        invoice = _issued_invoice()
        invoice.tax_amount = Decimal("0.00")

        discrepancies = validate_invoice_totals(invoice)
        fields = {d.field for d in discrepancies}
        assert "tax_amount" in fields

    def test_total_mismatch_detected(self) -> None:
        invoice = _issued_invoice()
        invoice.total_amount = Decimal("0.01")

        discrepancies = validate_invoice_totals(invoice)
        fields = {d.field for d in discrepancies}
        assert "total_amount" in fields

    def test_discrepancy_shows_amounts(self) -> None:
        invoice = _issued_invoice()
        invoice.subtotal_amount = Decimal("300.00")

        discrepancies = validate_invoice_totals(invoice)
        subtotal_disc = next(d for d in discrepancies if d.field == "subtotal_amount")
        assert subtotal_disc.expected == Decimal("200.00")
        assert subtotal_disc.actual == Decimal("300.00")
        assert subtotal_disc.difference == Decimal("100.00")


# ── Immutability constants ─────────────────────────────────────

class TestImmutabilityConstants:
    def test_immutable_fields_cover_financial_content(self) -> None:
        required = {
            "invoice_number", "invoice_date", "customer_id",
            "buyer_type", "buyer_identifier_snapshot",
            "subtotal_amount", "tax_amount", "total_amount",
        }
        assert required.issubset(IMMUTABLE_FIELDS)

    def test_immutable_error_message(self) -> None:
        assert IMMUTABLE_ERROR == "Invoices are immutable after creation"


# ── Get invoice ────────────────────────────────────────────────

class TestGetInvoice:
    @pytest.mark.asyncio
    async def test_get_existing_invoice(self) -> None:
        invoice = _issued_invoice()
        session = FakeAsyncSession()
        session.queue_result(invoice)

        result = await get_invoice(session, invoice.id)
        assert result is invoice

    @pytest.mark.asyncio
    async def test_get_missing_invoice(self) -> None:
        session = FakeAsyncSession()
        session.queue_result(None)

        result = await get_invoice(session, uuid.uuid4())
        assert result is None