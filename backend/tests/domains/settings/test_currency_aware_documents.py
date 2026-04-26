"""Tests for Story 25-2: Currency-Aware Commercial Documents.

This test module validates:
1. Currency snapshot fields exist on all commercial documents
2. Applied rate snapshots are stored correctly
3. Base amounts are calculated correctly
4. Same-currency documents get identity rate
5. Cross-currency documents get proper conversion
6. Legacy documents remain compatible
7. Payment allocations stay same-currency
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest

from domains.settings.fx_conversion import (
    ConversionResult,
    calculate_base_amounts,
    convert_and_round,
    convert_amount_with_precision,
    round_for_currency,
    validate_conversion_drift,
    validate_line_header_consistency,
)
from domains.settings.document_currency import (
    CurrencyMismatchError,
    validate_same_currency_allocation,
)


# === Test FX Conversion Utilities ===

class TestRoundForCurrency:
    """Tests for round_for_currency function."""

    def test_round_to_zero_decimals(self):
        """Test rounding to zero decimal places (JPY style)."""
        result = round_for_currency(Decimal("123.7"), 0)
        assert result == Decimal("124")

    def test_round_to_two_decimals(self):
        """Test rounding to two decimal places."""
        result = round_for_currency(Decimal("123.456"), 2)
        assert result == Decimal("123.46")

    def test_round_half_up(self):
        """Test ROUND_HALF_UP behavior."""
        result = round_for_currency(Decimal("123.455"), 2)
        assert result == Decimal("123.46")  # 5 rounds up

    def test_round_truncation(self):
        """Test truncation behavior."""
        result = round_for_currency(Decimal("123.454"), 2)
        assert result == Decimal("123.45")


class TestConvertAndRound:
    """Tests for convert_and_round function."""

    def test_convert_with_two_decimal_target(self):
        """Test conversion with two decimal target."""
        result = convert_and_round(Decimal("100"), Decimal("32.5"), 2)
        assert result == Decimal("3250.00")

    def test_convert_with_zero_decimal_target(self):
        """Test conversion with zero decimal target (JPY style)."""
        result = convert_and_round(Decimal("100"), Decimal("32.567"), 0)
        assert result == Decimal("3257")  # Rounds to nearest whole number


class TestConversionWithPrecision:
    """Tests for convert_amount_with_precision function."""

    def test_full_precision_and_rounded(self):
        """Test that full precision and rounded results are both available."""
        full, rounded = convert_amount_with_precision(
            Decimal("100"),
            Decimal("32.567"),
            2,
            0,
        )
        # Full precision preserves the 3 decimal places from rate
        assert full == Decimal("3256.7")
        # Rounded is to target precision
        assert rounded == Decimal("3257")


class TestCalculateBaseAmounts:
    """Tests for calculate_base_amounts function."""

    def test_calculate_with_standard_rate(self):
        """Test base amount calculation with standard rate."""
        base_sub, base_tax, base_total = calculate_base_amounts(
            Decimal("1000.00"),
            Decimal("100.00"),
            Decimal("1100.00"),
            Decimal("32.5"),
            2,
        )
        assert base_sub == Decimal("32500.00")
        assert base_tax == Decimal("3250.00")
        assert base_total == Decimal("35750.00")

    def test_calculate_with_zero_decimals(self):
        """Test base amount calculation with zero decimal target (JPY)."""
        base_sub, base_tax, base_total = calculate_base_amounts(
            Decimal("1000"),
            Decimal("100"),
            Decimal("1100"),
            Decimal("32.567"),
            0,
        )
        assert base_sub == Decimal("32567")
        assert base_tax == Decimal("3257")
        assert base_total == Decimal("35824")


class TestValidateConversionDrift:
    """Tests for validate_conversion_drift function."""

    def test_no_drift_within_tolerance(self):
        """Test that small differences pass validation."""
        is_valid, error = validate_conversion_drift(
            original_total=Decimal("1000.00"),
            rate=Decimal("32.5"),
            stored_base_total=Decimal("32500.00"),
            target_precision=2,
        )
        assert is_valid is True
        assert error is None

    def test_drift_exceeds_tolerance(self):
        """Test that large differences fail validation."""
        is_valid, error = validate_conversion_drift(
            original_total=Decimal("1000.00"),
            rate=Decimal("32.5"),
            stored_base_total=Decimal("32500.50"),  # 0.50 difference
            target_precision=2,
            tolerance=Decimal("0.01"),
        )
        assert is_valid is False
        assert "Conversion drift detected" in error


class TestValidateLineHeaderConsistency:
    """Tests for validate_line_header_consistency function."""

    def test_consistent_totals(self):
        """Test that matching totals pass validation."""
        is_valid, error = validate_line_header_consistency(
            lines_base_total=Decimal("32500.00"),
            header_base_total=Decimal("32500.00"),
            precision=2,
        )
        assert is_valid is True

    def test_inconsistent_totals(self):
        """Test that mismatched totals fail validation."""
        is_valid, error = validate_line_header_consistency(
            lines_base_total=Decimal("32500.00"),
            header_base_total=Decimal("32501.00"),
            precision=2,
            tolerance=Decimal("0.01"),
        )
        assert is_valid is False
        assert "Line-header base total mismatch" in error


# === Test Payment Currency Validation ===

class TestSameCurrencyAllocationValidation:
    """Tests for same-currency payment allocation validation."""

    def test_same_currency_passes(self):
        """Test that same currencies pass validation."""
        # Should not raise
        validate_same_currency_allocation("USD", "USD")

    def test_different_currencies_fails(self):
        """Test that different currencies fail validation."""
        with pytest.raises(CurrencyMismatchError) as exc_info:
            validate_same_currency_allocation("USD", "TWD")

        assert exc_info.value.payment_currency == "USD"
        assert exc_info.value.invoice_currency == "TWD"
        assert "Cross-currency allocation requires" in str(exc_info.value)

    def test_case_insensitive(self):
        """Test that currency comparison is case insensitive."""
        validate_same_currency_allocation("usd", "USD")
        validate_same_currency_allocation("USD", "usd")


# === Test Model Field Existence ===

class TestModelFieldsExist:
    """Tests that verify model fields exist (import checks)."""

    def test_order_model_has_currency_fields(self):
        """Test that Order model can be imported with currency fields."""
        from common.models.order import Order

        # Check that Order has expected attributes
        assert hasattr(Order, "currency_code")
        assert hasattr(Order, "conversion_rate")
        assert hasattr(Order, "conversion_effective_date")
        assert hasattr(Order, "applied_rate_source")
        assert hasattr(Order, "base_subtotal_amount")
        assert hasattr(Order, "base_discount_amount")
        assert hasattr(Order, "base_tax_amount")
        assert hasattr(Order, "base_total_amount")

    def test_order_line_model_has_base_fields(self):
        """Test that OrderLine model has base amount fields."""
        from common.models.order_line import OrderLine

        assert hasattr(OrderLine, "base_unit_price")
        assert hasattr(OrderLine, "base_subtotal_amount")
        assert hasattr(OrderLine, "base_tax_amount")
        assert hasattr(OrderLine, "base_total_amount")

    def test_invoice_model_has_currency_fields(self):
        """Test that Invoice model has currency fields."""
        from domains.invoices.models import Invoice

        assert hasattr(Invoice, "conversion_rate")
        assert hasattr(Invoice, "conversion_effective_date")
        assert hasattr(Invoice, "applied_rate_source")
        assert hasattr(Invoice, "base_subtotal_amount")
        assert hasattr(Invoice, "base_tax_amount")
        assert hasattr(Invoice, "base_total_amount")

    def test_invoice_line_model_has_base_fields(self):
        """Test that InvoiceLine model has base amount fields."""
        from domains.invoices.models import InvoiceLine

        assert hasattr(InvoiceLine, "base_unit_price")
        assert hasattr(InvoiceLine, "base_subtotal_amount")
        assert hasattr(InvoiceLine, "base_tax_amount")
        assert hasattr(InvoiceLine, "base_total_amount")

    def test_payment_model_has_currency_fields(self):
        """Test that Payment model has currency fields."""
        from domains.payments.models import Payment

        assert hasattr(Payment, "currency_code")
        assert hasattr(Payment, "conversion_rate")
        assert hasattr(Payment, "conversion_effective_date")
        assert hasattr(Payment, "applied_rate_source")
        assert hasattr(Payment, "base_amount")

    def test_supplier_invoice_has_currency_fields(self):
        """Test that SupplierInvoice model has currency fields."""
        from common.models.supplier_invoice import SupplierInvoice

        assert hasattr(SupplierInvoice, "conversion_rate")
        assert hasattr(SupplierInvoice, "conversion_effective_date")
        assert hasattr(SupplierInvoice, "applied_rate_source")
        assert hasattr(SupplierInvoice, "base_subtotal_amount")
        assert hasattr(SupplierInvoice, "base_tax_amount")
        assert hasattr(SupplierInvoice, "base_total_amount")
        assert hasattr(SupplierInvoice, "remaining_base_payable_amount")

    def test_supplier_payment_has_currency_fields(self):
        """Test that SupplierPayment model has currency fields."""
        from common.models.supplier_payment import SupplierPayment

        assert hasattr(SupplierPayment, "conversion_rate")
        assert hasattr(SupplierPayment, "conversion_effective_date")
        assert hasattr(SupplierPayment, "applied_rate_source")
        assert hasattr(SupplierPayment, "base_amount")

    def test_quotation_has_conversion_fields(self):
        """Test that Quotation model has conversion fields."""
        from domains.crm.models import Quotation

        assert hasattr(Quotation, "conversion_rate")
        assert hasattr(Quotation, "conversion_effective_date")
        assert hasattr(Quotation, "applied_rate_source")
        assert hasattr(Quotation, "base_subtotal")
        assert hasattr(Quotation, "base_total_taxes")


# === Test ConversionResult ===

class TestConversionResult:
    """Tests for ConversionResult dataclass."""

    def test_to_snapshot(self):
        """Test that ConversionResult converts to snapshot dict."""
        result = ConversionResult(
            original_amount=Decimal("1.0"),
            converted_amount=Decimal("32.5"),
            rate=Decimal("32.5000000000"),
            source_currency="USD",
            target_currency="TWD",
            effective_date=date(2026, 4, 26),
            rate_source="manual",
            precision_used=0,
        )

        snapshot = result.to_snapshot()
        assert snapshot["rate"] == "32.5000000000"
        assert snapshot["effective_date"] == "2026-04-26"
        assert snapshot["source"] == "manual"
        assert snapshot["source_currency"] == "USD"
        assert snapshot["target_currency"] == "TWD"


# === Test Edge Cases ===

class TestEdgeCases:
    """Tests for edge cases in currency conversion."""

    def test_zero_amount_conversion(self):
        """Test converting zero amount."""
        result = convert_and_round(Decimal("0"), Decimal("32.5"), 2)
        assert result == Decimal("0.00")

    def test_negative_amount_conversion(self):
        """Test converting negative amount (credit memo scenario)."""
        result = convert_and_round(Decimal("-100.00"), Decimal("32.5"), 2)
        assert result == Decimal("-3250.00")

    def test_small_rate_conversion(self):
        """Test conversion with small exchange rate."""
        result = convert_and_round(Decimal("1000"), Decimal("0.0234"), 4)
        # 1000 * 0.0234 = 23.4, rounded to 4 decimals
        assert result == Decimal("23.4000")

    def test_large_rate_conversion(self):
        """Test conversion with large exchange rate."""
        result = convert_and_round(Decimal("100"), Decimal("12345.67"), 2)
        # 100 * 12345.67 = 1,234,567, rounded to 2 decimals
        assert result == Decimal("1234567.00")

    def test_zero_rate_is_valid(self):
        """Test that zero rate conversion is mathematically valid."""
        # 1000 * 0 = 0, so stored_base_total = 0 is correct
        is_valid, error = validate_conversion_drift(
            original_total=Decimal("1000.00"),
            rate=Decimal("0"),  # Zero rate is valid
            stored_base_total=Decimal("0.00"),
            target_precision=2,
            tolerance=Decimal("0.01"),
        )
        assert is_valid is True  # Zero rate * 1000 = 0 is correct
