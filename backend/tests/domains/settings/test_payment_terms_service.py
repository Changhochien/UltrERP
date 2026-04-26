"""Tests for Story 25-3: Payment Terms Template Builder and Schedule Handling.

This test module validates:
1. Payment terms template CRUD operations
2. Schedule generation from templates
3. Legacy term compatibility
4. Due date calculations
5. Payment marking functionality
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest

from common.models.payment_terms import (
    LEGACY_TERM_MAPPINGS,
    LegacyPaymentTerms,
    PaymentSchedule,
    PaymentTermsTemplate,
    PaymentTermsTemplateDetail,
    get_legacy_due_date,
)


# === Test Legacy Payment Terms ===

class TestLegacyPaymentTerms:
    """Tests for legacy payment term calculations."""

    def test_net_30_due_date(self):
        """Test NET_30 adds 30 days."""
        doc_date = date(2026, 4, 15)
        due_date = get_legacy_due_date(doc_date, LegacyPaymentTerms.NET_30.value)
        assert due_date == date(2026, 5, 15)

    def test_net_60_due_date(self):
        """Test NET_60 adds 60 days."""
        doc_date = date(2026, 4, 15)
        due_date = get_legacy_due_date(doc_date, LegacyPaymentTerms.NET_60.value)
        assert due_date == date(2026, 6, 14)

    def test_net_90_due_date(self):
        """Test NET_90 adds 90 days."""
        doc_date = date(2026, 4, 15)
        due_date = get_legacy_due_date(doc_date, LegacyPaymentTerms.NET_90.value)
        assert due_date == date(2026, 7, 14)

    def test_cod_due_date(self):
        """Test COD is due immediately (same day)."""
        doc_date = date(2026, 4, 15)
        due_date = get_legacy_due_date(doc_date, LegacyPaymentTerms.COD.value)
        assert due_date == doc_date

    def test_prepaid_due_date(self):
        """Test PREPAID is due immediately."""
        doc_date = date(2026, 4, 15)
        due_date = get_legacy_due_date(doc_date, LegacyPaymentTerms.PREPAID.value)
        assert due_date == doc_date

    def test_unknown_term_defaults_to_net_30(self):
        """Test unknown terms default to NET_30."""
        doc_date = date(2026, 4, 15)
        due_date = get_legacy_due_date(doc_date, "UNKNOWN_TERM")
        assert due_date == date(2026, 5, 15)


class TestLegacyTermMappings:
    """Tests for legacy term mapping configuration."""

    def test_all_legacy_terms_have_mappings(self):
        """Test all legacy terms are in the mapping."""
        for term in LegacyPaymentTerms:
            assert term.value in LEGACY_TERM_MAPPINGS
            mapping = LEGACY_TERM_MAPPINGS[term.value]
            assert "template_name" in mapping
            assert "credit_days" in mapping
            assert "credit_months" in mapping
            assert "invoice_portion" in mapping

    def test_legacy_portions_are_100(self):
        """Test all legacy terms have 100% portion."""
        for term in LegacyPaymentTerms:
            mapping = LEGACY_TERM_MAPPINGS[term.value]
            assert mapping["invoice_portion"] == Decimal("100.00")


# === Test Model Field Existence ===

class TestModelFieldsExist:
    """Tests that verify model fields exist."""

    def test_payment_terms_template_fields(self):
        """Test PaymentTermsTemplate has required fields."""
        assert hasattr(PaymentTermsTemplate, "tenant_id")
        assert hasattr(PaymentTermsTemplate, "template_name")
        assert hasattr(PaymentTermsTemplate, "description")
        assert hasattr(PaymentTermsTemplate, "allocate_payment_based_on_payment_terms")
        assert hasattr(PaymentTermsTemplate, "is_active")
        assert hasattr(PaymentTermsTemplate, "legacy_code")
        assert hasattr(PaymentTermsTemplate, "details")

    def test_payment_terms_template_detail_fields(self):
        """Test PaymentTermsTemplateDetail has required fields."""
        assert hasattr(PaymentTermsTemplateDetail, "tenant_id")
        assert hasattr(PaymentTermsTemplateDetail, "template_id")
        assert hasattr(PaymentTermsTemplateDetail, "row_number")
        assert hasattr(PaymentTermsTemplateDetail, "invoice_portion")
        assert hasattr(PaymentTermsTemplateDetail, "credit_days")
        assert hasattr(PaymentTermsTemplateDetail, "credit_months")
        assert hasattr(PaymentTermsTemplateDetail, "discount_percent")
        assert hasattr(PaymentTermsTemplateDetail, "discount_validity_days")
        assert hasattr(PaymentTermsTemplateDetail, "mode_of_payment")

    def test_payment_schedule_fields(self):
        """Test PaymentSchedule has required fields."""
        assert hasattr(PaymentSchedule, "tenant_id")
        assert hasattr(PaymentSchedule, "document_type")
        assert hasattr(PaymentSchedule, "document_id")
        assert hasattr(PaymentSchedule, "template_id")
        assert hasattr(PaymentSchedule, "row_number")
        assert hasattr(PaymentSchedule, "invoice_portion")
        assert hasattr(PaymentSchedule, "due_date")
        assert hasattr(PaymentSchedule, "payment_amount")
        assert hasattr(PaymentSchedule, "outstanding_amount")
        assert hasattr(PaymentSchedule, "paid_amount")
        assert hasattr(PaymentSchedule, "is_paid")
        assert hasattr(PaymentSchedule, "paid_date")


class TestPaymentTermsRoutes:
    """Tests for payment terms template API route registration."""

    def test_template_crud_routes_exist(self):
        from domains.settings.routes_payment_terms import router

        routes = {(route.path, tuple(sorted(route.methods))) for route in router.routes}

        assert ("/payment-terms-templates", ("GET",)) in routes
        assert ("/payment-terms-templates", ("POST",)) in routes
        assert ("/payment-terms-templates/{template_id}", ("GET",)) in routes
        assert ("/payment-terms-templates/{template_id}", ("PATCH",)) in routes


# === Test PaymentSchedule Methods ===

class TestPaymentScheduleMarkPaid:
    """Tests for PaymentSchedule.mark_paid method."""

    def test_mark_paid_full_amount(self):
        """Test marking a schedule as fully paid."""
        schedule = PaymentSchedule(
            tenant_id=uuid.uuid4(),
            document_type="invoice",
            document_id=uuid.uuid4(),
            row_number=1,
            invoice_portion=Decimal("100.00"),
            due_date=date(2026, 5, 15),
            payment_amount=Decimal("1000.00"),
            outstanding_amount=Decimal("1000.00"),
            paid_amount=Decimal("0.00"),
        )

        schedule.mark_paid(date(2026, 5, 10), Decimal("1000.00"))

        assert schedule.paid_amount == Decimal("1000.00")
        assert schedule.outstanding_amount == Decimal("0.00")
        assert schedule.is_paid is True
        assert schedule.paid_date == date(2026, 5, 10)

    def test_mark_paid_partial_amount(self):
        """Test marking a schedule as partially paid."""
        schedule = PaymentSchedule(
            tenant_id=uuid.uuid4(),
            document_type="invoice",
            document_id=uuid.uuid4(),
            row_number=1,
            invoice_portion=Decimal("100.00"),
            due_date=date(2026, 5, 15),
            payment_amount=Decimal("1000.00"),
            outstanding_amount=Decimal("1000.00"),
            paid_amount=Decimal("0.00"),
            is_paid=False,  # Explicitly set initial state
        )

        schedule.mark_paid(date(2026, 5, 10), Decimal("400.00"))

        assert schedule.paid_amount == Decimal("400.00")
        assert schedule.outstanding_amount == Decimal("600.00")
        assert schedule.is_paid is False
        assert schedule.paid_date == date(2026, 5, 10)

    def test_mark_paid_overpayment(self):
        """Test marking a schedule as paid with overpayment."""
        schedule = PaymentSchedule(
            tenant_id=uuid.uuid4(),
            document_type="invoice",
            document_id=uuid.uuid4(),
            row_number=1,
            invoice_portion=Decimal("100.00"),
            due_date=date(2026, 5, 15),
            payment_amount=Decimal("1000.00"),
            outstanding_amount=Decimal("1000.00"),
            paid_amount=Decimal("0.00"),
        )

        schedule.mark_paid(date(2026, 5, 10), Decimal("1200.00"))

        assert schedule.paid_amount == Decimal("1200.00")
        assert schedule.outstanding_amount == Decimal("0.00")  # Capped at 0
        assert schedule.is_paid is True

    def test_mark_paid_multiple_payments(self):
        """Test multiple partial payments."""
        schedule = PaymentSchedule(
            tenant_id=uuid.uuid4(),
            document_type="invoice",
            document_id=uuid.uuid4(),
            row_number=1,
            invoice_portion=Decimal("100.00"),
            due_date=date(2026, 5, 15),
            payment_amount=Decimal("1000.00"),
            outstanding_amount=Decimal("1000.00"),
            paid_amount=Decimal("0.00"),
            is_paid=False,  # Explicitly set initial state
        )

        # First partial payment
        schedule.mark_paid(date(2026, 5, 5), Decimal("300.00"))
        assert schedule.paid_amount == Decimal("300.00")
        assert schedule.outstanding_amount == Decimal("700.00")
        assert schedule.is_paid is False

        # Second partial payment
        schedule.mark_paid(date(2026, 5, 10), Decimal("500.00"))
        assert schedule.paid_amount == Decimal("800.00")
        assert schedule.outstanding_amount == Decimal("200.00")
        assert schedule.is_paid is False

        # Final payment
        schedule.mark_paid(date(2026, 5, 15), Decimal("200.00"))
        assert schedule.paid_amount == Decimal("1000.00")
        assert schedule.outstanding_amount == Decimal("0.00")
        assert schedule.is_paid is True


# === Test Due Date Calculations ===

class TestDueDateCalculations:
    """Tests for due date calculation logic."""

    def test_single_installment_due_date(self):
        """Test single installment due date calculation."""
        detail = PaymentTermsTemplateDetail(
            tenant_id=uuid.uuid4(),
            template_id=uuid.uuid4(),
            row_number=1,
            invoice_portion=Decimal("100.00"),
            credit_days=30,
            credit_months=0,
        )

        doc_date = date(2026, 4, 15)
        due_date = detail.calculate_due_date(doc_date)

        assert due_date == date(2026, 5, 15)

    def test_credit_months_calculation(self):
        """Test due date with credit months."""
        detail = PaymentTermsTemplateDetail(
            tenant_id=uuid.uuid4(),
            template_id=uuid.uuid4(),
            row_number=1,
            invoice_portion=Decimal("100.00"),
            credit_days=15,
            credit_months=1,
        )

        doc_date = date(2026, 4, 15)
        due_date = detail.calculate_due_date(doc_date)

        # Should be May 15 + 15 days = May 30
        assert due_date == date(2026, 5, 30)

    def test_zero_credit_days(self):
        """Test due date with zero credit days (immediate)."""
        detail = PaymentTermsTemplateDetail(
            tenant_id=uuid.uuid4(),
            template_id=uuid.uuid4(),
            row_number=1,
            invoice_portion=Decimal("100.00"),
            credit_days=0,
            credit_months=0,
        )

        doc_date = date(2026, 4, 15)
        due_date = detail.calculate_due_date(doc_date)

        assert due_date == doc_date


# === Test Edge Cases ===

class TestEdgeCases:
    """Tests for edge cases in payment terms handling."""

    def test_schedule_repr(self):
        """Test PaymentSchedule string representation."""
        schedule = PaymentSchedule(
            tenant_id=uuid.uuid4(),
            document_type="invoice",
            document_id=uuid.uuid4(),
            row_number=1,
            invoice_portion=Decimal("100.00"),
            due_date=date(2026, 5, 15),
            payment_amount=Decimal("1000.00"),
            outstanding_amount=Decimal("1000.00"),
            paid_amount=Decimal("0.00"),
        )

        repr_str = repr(schedule)
        assert "row=1" in repr_str
        assert "2026-05-15" in repr_str
        assert "1000.00" in repr_str

    def test_template_repr(self):
        """Test PaymentTermsTemplate string representation."""
        template = PaymentTermsTemplate(
            tenant_id=uuid.uuid4(),
            template_name="Net 30",
        )

        repr_str = repr(template)
        assert "Net 30" in repr_str

    def test_detail_repr(self):
        """Test PaymentTermsTemplateDetail string representation."""
        detail = PaymentTermsTemplateDetail(
            tenant_id=uuid.uuid4(),
            template_id=uuid.uuid4(),
            row_number=2,
            invoice_portion=Decimal("50.00"),
            credit_days=30,
            credit_months=0,
        )

        repr_str = repr(detail)
        assert "row=2" in repr_str
        assert "50.00%" in repr_str
