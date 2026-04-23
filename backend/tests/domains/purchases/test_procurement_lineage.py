"""Tests for procurement lineage features (Story 24-4).

Tests:
- Line-level reference persistence
- Tolerance flag evaluation
- Lineage read behavior
- Supplier invoice compatibility
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest

from domains.purchases.service import calculate_mismatch_variance


class TestMismatchVarianceCalculation:
    """Test variance calculation for three-way-match readiness."""

    def test_calculate_mismatch_variance_with_all_references(self) -> None:
        """Test variance calculation when all reference values are provided."""
        result = calculate_mismatch_variance(
            invoice_quantity=Decimal("10.000"),
            invoice_unit_price=Decimal("50.00"),
            invoice_total=Decimal("525.00"),
            reference_quantity=Decimal("10.000"),
            reference_unit_price=Decimal("50.00"),
            reference_total=Decimal("500.00"),
        )

        assert result["quantity_variance"] == Decimal("0.000")
        assert result["unit_price_variance"] == Decimal("0.00")
        assert result["total_amount_variance"] == Decimal("25.00")
        assert result["quantity_variance_pct"] == Decimal("0")
        assert result["unit_price_variance_pct"] == Decimal("0")
        # 25 / 500 * 100 = 5
        assert result["total_amount_variance_pct"] == Decimal("5.0000")

    def test_calculate_mismatch_variance_with_quantity_variance(self) -> None:
        """Test variance calculation with quantity difference."""
        result = calculate_mismatch_variance(
            invoice_quantity=Decimal("12.000"),
            invoice_unit_price=Decimal("50.00"),
            invoice_total=Decimal("600.00"),
            reference_quantity=Decimal("10.000"),
            reference_unit_price=Decimal("50.00"),
            reference_total=Decimal("500.00"),
        )

        assert result["quantity_variance"] == Decimal("2.000")
        assert result["unit_price_variance"] == Decimal("0.00")
        assert result["total_amount_variance"] == Decimal("100.00")
        # 2 / 10 * 100 = 20
        assert result["quantity_variance_pct"] == Decimal("20.0000")

    def test_calculate_mismatch_variance_with_price_variance(self) -> None:
        """Test variance calculation with unit price difference."""
        result = calculate_mismatch_variance(
            invoice_quantity=Decimal("10.000"),
            invoice_unit_price=Decimal("55.00"),
            invoice_total=Decimal("577.50"),
            reference_quantity=Decimal("10.000"),
            reference_unit_price=Decimal("50.00"),
            reference_total=Decimal("500.00"),
        )

        assert result["quantity_variance"] == Decimal("0.000")
        assert result["unit_price_variance"] == Decimal("5.00")
        assert result["total_amount_variance"] == Decimal("77.50")
        # 5 / 50 * 100 = 10
        assert result["unit_price_variance_pct"] == Decimal("10.0000")

    def test_calculate_mismatch_variance_with_negative_variance(self) -> None:
        """Test variance calculation when invoice is less than reference."""
        result = calculate_mismatch_variance(
            invoice_quantity=Decimal("8.000"),
            invoice_unit_price=Decimal("45.00"),
            invoice_total=Decimal("378.00"),
            reference_quantity=Decimal("10.000"),
            reference_unit_price=Decimal("50.00"),
            reference_total=Decimal("500.00"),
        )

        assert result["quantity_variance"] == Decimal("-2.000")
        assert result["unit_price_variance"] == Decimal("-5.00")
        assert result["total_amount_variance"] == Decimal("-122.00")
        # -2 / 10 * 100 = -20
        assert result["quantity_variance_pct"] == Decimal("-20.0000")

    def test_calculate_mismatch_variance_with_partial_references(self) -> None:
        """Test variance calculation when only some reference values are provided."""
        result = calculate_mismatch_variance(
            invoice_quantity=Decimal("10.000"),
            invoice_unit_price=Decimal("50.00"),
            invoice_total=Decimal("525.00"),
            reference_quantity=None,  # Not provided
            reference_unit_price=Decimal("50.00"),
            reference_total=None,  # Not provided
        )

        assert result["quantity_variance"] is None
        assert result["unit_price_variance"] == Decimal("0.00")
        assert result["total_amount_variance"] is None
        assert result["quantity_variance_pct"] is None
        assert result["unit_price_variance_pct"] == Decimal("0")
        assert result["total_amount_variance_pct"] is None

    def test_calculate_mismatch_variance_with_no_references(self) -> None:
        """Test variance calculation when no reference values are provided."""
        result = calculate_mismatch_variance(
            invoice_quantity=Decimal("10.000"),
            invoice_unit_price=Decimal("50.00"),
            invoice_total=Decimal("525.00"),
            reference_quantity=None,
            reference_unit_price=None,
            reference_total=None,
        )

        assert all(v is None for v in result.values())

    def test_calculate_mismatch_variance_with_zero_reference(self) -> None:
        """Test variance calculation when reference quantity is zero (avoid division by zero)."""
        result = calculate_mismatch_variance(
            invoice_quantity=Decimal("10.000"),
            invoice_unit_price=Decimal("50.00"),
            invoice_total=Decimal("500.00"),
            reference_quantity=Decimal("0"),
            reference_unit_price=Decimal("50.00"),
            reference_total=Decimal("0"),
        )

        # Should handle division by zero gracefully
        assert result["quantity_variance_pct"] is None  # Avoid div by zero
        assert result["total_amount_variance_pct"] is None  # Avoid div by zero
        assert result["unit_price_variance_pct"] == Decimal("0")  # Non-zero reference


class TestMismatchStatusEnum:
    """Test mismatch status enum values."""

    def test_mismatch_status_values(self) -> None:
        """Verify mismatch status enum values match expected string values."""
        from common.models.supplier_invoice import ProcurementMismatchStatus

        assert ProcurementMismatchStatus.NOT_CHECKED.value == "not_checked"
        assert ProcurementMismatchStatus.WITHIN_TOLERANCE.value == "within_tolerance"
        assert ProcurementMismatchStatus.OUTSIDE_TOLERANCE.value == "outside_tolerance"
        assert ProcurementMismatchStatus.REVIEW_REQUIRED.value == "review_required"


class TestLineageStateDetermination:
    """Test lineage state determination logic."""

    def test_lineage_state_linked(self) -> None:
        """Test that a line with any reference is considered linked."""
        from domains.purchases.service import _has_lineage, _determine_lineage_state

        class MockLine:
            rfq_item_id = uuid.uuid4()
            supplier_quotation_item_id = None
            purchase_order_line_id = None
            goods_receipt_line_id = None

        line = MockLine()
        assert _has_lineage(line) is True
        assert _determine_lineage_state(line) == "linked"

    def test_lineage_state_unlinked_historical(self) -> None:
        """Test that a line with no references is considered unlinked_historical."""
        from domains.purchases.service import _has_lineage, _determine_lineage_state

        class MockLine:
            rfq_item_id = None
            supplier_quotation_item_id = None
            purchase_order_line_id = None
            goods_receipt_line_id = None

        line = MockLine()
        assert _has_lineage(line) is False
        assert _determine_lineage_state(line) == "unlinked_historical"


class TestSchemaValidation:
    """Test schema validation for procurement lineage fields."""

    def test_supplier_invoice_line_create_schema(self) -> None:
        """Test SupplierInvoiceLineCreate schema accepts lineage fields."""
        from domains.purchases.schemas import SupplierInvoiceLineCreate

        line_data = {
            "line_number": 1,
            "description": "Widget A",
            "quantity": "10.000",
            "unit_price": "50.00",
            "subtotal_amount": "500.00",
            "tax_type": 1,
            "tax_rate": "0.05",
            "tax_amount": "25.00",
            "total_amount": "525.00",
            # Procurement lineage references
            "rfq_item_id": str(uuid.uuid4()),
            "supplier_quotation_item_id": str(uuid.uuid4()),
            "purchase_order_line_id": str(uuid.uuid4()),
            "goods_receipt_line_id": str(uuid.uuid4()),
            # Reference values
            "reference_quantity": "10.000",
            "reference_unit_price": "50.00",
            "reference_total_amount": "500.00",
        }

        line = SupplierInvoiceLineCreate(**line_data)
        assert line.line_number == 1
        assert line.purchase_order_line_id is not None
        assert line.reference_quantity is not None

    def test_supplier_invoice_create_schema(self) -> None:
        """Test SupplierInvoiceCreate schema accepts PO reference."""
        from domains.purchases.schemas import SupplierInvoiceCreate

        invoice_data = {
            "supplier_id": str(uuid.uuid4()),
            "invoice_number": "PI-2025001",
            "invoice_date": "2025-03-15",
            "currency_code": "TWD",
            "subtotal_amount": "500.00",
            "tax_amount": "25.00",
            "total_amount": "525.00",
            # Procurement lineage - header-level PO reference
            "purchase_order_id": str(uuid.uuid4()),
            "lines": [],
        }

        invoice = SupplierInvoiceCreate(**invoice_data)
        assert invoice.purchase_order_id is not None

    def test_procurement_mismatch_status_schema(self) -> None:
        """Test ProcurementMismatchStatus schema validation."""
        from domains.purchases.schemas import ProcurementMismatchStatus

        assert ProcurementMismatchStatus.NOT_CHECKED == "not_checked"
        assert ProcurementMismatchStatus.WITHIN_TOLERANCE == "within_tolerance"
        assert ProcurementMismatchStatus.OUTSIDE_TOLERANCE == "outside_tolerance"
        assert ProcurementMismatchStatus.REVIEW_REQUIRED == "review_required"
