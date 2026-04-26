"""Tests for Story 25-4: Customer and Supplier Commercial Profiles.

This test module validates:
1. Commercial profile default application
2. Source metadata tracking
3. Deterministic fallback ordering
4. Model field existence
"""

import uuid
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from domains.settings.commercial_profile_service import (
    CommercialValueSource,
    determine_payment_terms_source,
)


# === Test CommercialValueSource Enum ===

class TestCommercialValueSource:
    """Tests for CommercialValueSource enum."""

    def test_all_sources_defined(self):
        """Test all expected sources are defined."""
        assert CommercialValueSource.SOURCE_DOCUMENT.value == "source_document"
        assert CommercialValueSource.PROFILE_DEFAULT.value == "profile_default"
        assert CommercialValueSource.LEGACY_COMPATIBILITY.value == "legacy_compatibility"
        assert CommercialValueSource.MANUAL_OVERRIDE.value == "manual_override"


# === Test determine_payment_terms_source ===

class TestDeterminePaymentTermsSource:
    """Tests for determine_payment_terms_source function."""

    def test_source_document_template_takes_precedence(self):
        """Test source document template takes precedence."""
        template_id = uuid.uuid4()
        result = determine_payment_terms_source(
            explicit_terms_code="NET_30",
            explicit_template_id=None,
            source_document_terms_code=None,
            source_document_template_id=template_id,
            profile_template_id=uuid.uuid4(),
            legacy_terms_code="NET_60",
        )

        assert result[1] == template_id
        assert result[2] == CommercialValueSource.SOURCE_DOCUMENT

    def test_source_document_terms_code_takes_precedence(self):
        """Test source document terms code takes precedence."""
        result = determine_payment_terms_source(
            explicit_terms_code="NET_30",
            explicit_template_id=None,
            source_document_terms_code="NET_15",
            source_document_template_id=None,
            profile_template_id=uuid.uuid4(),
            legacy_terms_code="NET_60",
        )

        assert result[0] == "NET_15"
        assert result[2] == CommercialValueSource.SOURCE_DOCUMENT

    def test_explicit_template_takes_precedence(self):
        """Test explicit template override takes precedence."""
        template_id = uuid.uuid4()
        result = determine_payment_terms_source(
            explicit_terms_code=None,
            explicit_template_id=template_id,
            source_document_terms_code=None,
            source_document_template_id=None,
            profile_template_id=uuid.uuid4(),
            legacy_terms_code="NET_60",
        )

        assert result[1] == template_id
        assert result[2] == CommercialValueSource.MANUAL_OVERRIDE

    def test_explicit_terms_takes_precedence(self):
        """Test explicit terms override takes precedence."""
        result = determine_payment_terms_source(
            explicit_terms_code="NET_45",
            explicit_template_id=None,
            source_document_terms_code=None,
            source_document_template_id=None,
            profile_template_id=uuid.uuid4(),
            legacy_terms_code="NET_60",
        )

        assert result[0] == "NET_45"
        assert result[2] == CommercialValueSource.MANUAL_OVERRIDE

    def test_profile_default_fallback(self):
        """Test profile template fallback."""
        template_id = uuid.uuid4()
        result = determine_payment_terms_source(
            explicit_terms_code=None,
            explicit_template_id=None,
            source_document_terms_code=None,
            source_document_template_id=None,
            profile_template_id=template_id,
            legacy_terms_code="NET_60",
        )

        assert result[1] == template_id
        assert result[2] == CommercialValueSource.PROFILE_DEFAULT

    def test_legacy_fallback(self):
        """Test legacy term fallback."""
        result = determine_payment_terms_source(
            explicit_terms_code=None,
            explicit_template_id=None,
            source_document_terms_code=None,
            source_document_template_id=None,
            profile_template_id=None,
            legacy_terms_code="NET_30",
        )

        assert result[0] == "NET_30"
        assert result[2] == CommercialValueSource.LEGACY_COMPATIBILITY

    def test_no_defaults(self):
        """Test when no defaults available."""
        result = determine_payment_terms_source(
            explicit_terms_code=None,
            explicit_template_id=None,
            source_document_terms_code=None,
            source_document_template_id=None,
            profile_template_id=None,
            legacy_terms_code=None,
        )

        assert result[0] is None
        assert result[1] is None
        assert result[2] == CommercialValueSource.LEGACY_COMPATIBILITY

    def test_template_precedence_over_terms(self):
        """Test template takes precedence over terms code when both present."""
        template_id = uuid.uuid4()
        result = determine_payment_terms_source(
            explicit_terms_code="NET_30",
            explicit_template_id=template_id,
            source_document_terms_code=None,
            source_document_template_id=None,
            profile_template_id=None,
            legacy_terms_code=None,
        )

        # Template should win
        assert result[1] == template_id
        assert result[2] == CommercialValueSource.MANUAL_OVERRIDE


# === Test Model Fields ===

class TestCustomerModelFields:
    """Tests for Customer model commercial profile fields."""

    def test_customer_has_default_currency_code(self):
        """Test Customer has default_currency_code field."""
        from domains.customers.models import Customer

        assert hasattr(Customer, "default_currency_code")

    def test_customer_has_payment_terms_template_id(self):
        """Test Customer has payment_terms_template_id field."""
        from domains.customers.models import Customer

        assert hasattr(Customer, "payment_terms_template_id")

    def test_customer_has_payment_terms_template_relationship(self):
        """Test Customer has payment_terms_template relationship."""
        from domains.customers.models import Customer

        assert hasattr(Customer, "payment_terms_template")


class TestSupplierModelFields:
    """Tests for Supplier model commercial profile fields."""

    def test_supplier_has_default_currency_code(self):
        """Test Supplier has default_currency_code field."""
        from common.models.supplier import Supplier

        assert hasattr(Supplier, "default_currency_code")

    def test_supplier_has_payment_terms_template_id(self):
        """Test Supplier has payment_terms_template_id field."""
        from common.models.supplier import Supplier

        assert hasattr(Supplier, "payment_terms_template_id")

    def test_supplier_has_payment_terms_template_relationship(self):
        """Test Supplier has payment_terms_template relationship."""
        from common.models.supplier import Supplier

        assert hasattr(Supplier, "payment_terms_template")


class TestDocumentSourceFields:
    """Tests for document source metadata fields."""

    def test_order_has_currency_source(self):
        """Test Order has currency_source field."""
        from common.models.order import Order

        assert hasattr(Order, "currency_source")

    def test_order_has_payment_terms_source(self):
        """Test Order has payment_terms_source field."""
        from common.models.order import Order

        assert hasattr(Order, "payment_terms_source")

    def test_quotation_has_currency_source(self):
        """Test Quotation has currency_source field."""
        from domains.crm.models import Quotation

        assert hasattr(Quotation, "currency_source")

    def test_quotation_has_payment_terms_source(self):
        """Test Quotation has payment_terms_source field."""
        from domains.crm.models import Quotation

        assert hasattr(Quotation, "payment_terms_source")

    def test_invoice_has_currency_source(self):
        """Test Invoice has currency_source field."""
        from domains.invoices.models import Invoice

        assert hasattr(Invoice, "currency_source")

    def test_invoice_has_payment_terms_source(self):
        """Test Invoice has payment_terms_source field."""
        from domains.invoices.models import Invoice

        assert hasattr(Invoice, "payment_terms_source")


# === Test Edge Cases ===

class TestEdgeCases:
    """Tests for edge cases."""

    def test_source_metadata_string_values(self):
        """Test that source metadata can be converted to string."""
        for source in CommercialValueSource:
            # Should be convertible to string
            str_value = source.value
            assert isinstance(str_value, str)
            assert len(str_value) > 0

    @pytest.mark.asyncio
    async def test_missing_non_base_rate_is_not_silently_identity(self, monkeypatch):
        """Foreign-currency defaults must fail if no dated rate is configured."""
        from domains.settings import commercial_profile_service, exchange_rate_service
        from domains.settings.exchange_rate_service import ExchangeRateNotFoundError

        async def fake_base_currency(session, tenant_id):
            return SimpleNamespace(code="TWD")

        async def fake_resolve_exchange_rate(*args, **kwargs):
            raise ExchangeRateNotFoundError("USD", "TWD", date(2026, 4, 20), uuid.uuid4())

        monkeypatch.setattr(
            commercial_profile_service,
            "get_tenant_base_currency",
            fake_base_currency,
        )
        monkeypatch.setattr(
            exchange_rate_service,
            "resolve_exchange_rate",
            fake_resolve_exchange_rate,
        )

        with pytest.raises(ExchangeRateNotFoundError):
            await commercial_profile_service.resolve_document_currency(
                session=object(),
                tenant_id=uuid.uuid4(),
                explicit_currency="USD",
                effective_date=date(2026, 4, 20),
            )

    def test_fallback_order_determinism(self):
        """Test that fallback order is deterministic."""
        template_id_1 = uuid.uuid4()
        template_id_2 = uuid.uuid4()

        # Same inputs should always produce same outputs
        result1 = determine_payment_terms_source(
            explicit_terms_code=None,
            explicit_template_id=None,
            source_document_terms_code=None,
            source_document_template_id=None,
            profile_template_id=template_id_1,
            legacy_terms_code="NET_30",
        )

        result2 = determine_payment_terms_source(
            explicit_terms_code=None,
            explicit_template_id=None,
            source_document_terms_code=None,
            source_document_template_id=None,
            profile_template_id=template_id_2,
            legacy_terms_code="NET_30",
        )

        # Both should have same source
        assert result1[2] == result2[2] == CommercialValueSource.PROFILE_DEFAULT
        # But different template IDs
        assert result1[1] == template_id_1
        assert result2[1] == template_id_2
