"""Tests for CRM quotation service helper functions (refactoring Issue #1, #3)."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from types import SimpleNamespace

import pytest

from domains.crm.models import Quotation
from domains.crm.schemas import (
    OpportunityItemInput,
    QuotationCreate,
    QuotationPartyKind,
    QuotationRevisionCreate,
    QuotationStatus,
    QuotationTaxInput,
    QuotationUpdate,
)
from domains.crm.service import (
    _apply_quotation_fields_to_record,
    _build_quotation_merged,
    _build_quotation_record,
    _should_resolve_party,
)


class TestBuildQuotationMerged:
    """Tests for _build_quotation_merged helper (Issue #1 fix)."""

    def test_uses_update_values_when_provided(self) -> None:
        """When a field is in the update payload, use the new value."""
        existing = _mock_quotation(company="Old Company", currency="USD")
        update_data = QuotationUpdate(
            version=1,
            company="New Company",
            currency="EUR",
        )

        merged = _build_quotation_merged(update_data, existing)

        assert merged.company == "New Company"
        assert merged.currency == "EUR"

    def test_uses_existing_values_when_field_not_in_update(self) -> None:
        """When a field is NOT in the update payload, keep existing value."""
        existing = _mock_quotation(
            company="Existing Company",
            currency="USD",
            territory="North",
            contact_person="John Doe",
        )
        update_data = QuotationUpdate(version=1)

        merged = _build_quotation_merged(update_data, existing)

        assert merged.company == "Existing Company"
        assert merged.currency == "USD"
        assert merged.territory == "North"
        assert merged.contact_person == "John Doe"

    def test_handles_none_values_in_update_differently(self) -> None:
        """None in update payload should use existing value (not None)."""
        existing = _mock_quotation(
            contact_email="john@example.com",
            contact_mobile="0912-345-678",
        )
        update_data = QuotationUpdate(
            version=1,
            contact_email=None,
            contact_mobile=None,
        )

        merged = _build_quotation_merged(update_data, existing)

        assert merged.contact_email == "john@example.com"
        assert merged.contact_mobile == "0912-345-678"

    def test_clears_nullable_fields_when_explicit_none_is_provided(self) -> None:
        """Nullable fields that support clearing should honor explicit None."""
        existing = _mock_quotation(
            opportunity_id=uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"),
            auto_repeat_until=date(2026, 12, 31),
        )
        update_data = QuotationUpdate(
            version=1,
            opportunity_id=None,
            auto_repeat_until=None,
        )

        merged = _build_quotation_merged(update_data, existing)

        assert merged.opportunity_id is None
        assert merged.auto_repeat_until is None

    def test_handles_party_kind_conversion(self) -> None:
        """quotation_to is stored as string but schema expects enum."""
        existing = _mock_quotation(quotation_to=QuotationPartyKind.LEAD)
        update_data = QuotationUpdate(
            version=1,
            quotation_to=QuotationPartyKind.CUSTOMER,
        )

        merged = _build_quotation_merged(update_data, existing)

        assert merged.quotation_to == QuotationPartyKind.CUSTOMER

    def test_handles_quotation_to_when_not_in_update(self) -> None:
        """When quotation_to not in update, preserve existing enum type."""
        existing = _mock_quotation(quotation_to=QuotationPartyKind.LEAD)
        update_data = QuotationUpdate(version=1)

        merged = _build_quotation_merged(update_data, existing)

        assert merged.quotation_to == QuotationPartyKind.LEAD

    def test_preserves_party_name_when_not_in_update(self) -> None:
        """party_name should preserve existing value."""
        existing = _mock_quotation(party_name="11111111-2222-3333-4444-555555555555")
        update_data = QuotationUpdate(version=1)

        merged = _build_quotation_merged(update_data, existing)

        assert merged.party_name == "11111111-2222-3333-4444-555555555555"

    def test_handles_items_deserialization(self) -> None:
        """items stored as JSON should be deserialized in merged output."""
        existing = _mock_quotation()
        existing.items = '[{"item_name": "Widget", "quantity": "5"}]'
        update_data = QuotationUpdate(version=1)

        merged = _build_quotation_merged(update_data, existing)

        assert merged.items is not None
        assert len(merged.items) == 1
        assert merged.items[0].item_name == "Widget"

    def test_handles_taxes_deserialization(self) -> None:
        """taxes stored as JSON should be deserialized in merged output."""
        existing = _mock_quotation()
        existing.taxes = '[{"description": "VAT", "rate": "5.00"}]'
        update_data = QuotationUpdate(version=1)

        merged = _build_quotation_merged(update_data, existing)

        assert merged.taxes is not None
        assert len(merged.taxes) == 1
        assert merged.taxes[0].rate == Decimal("5.00")

    def test_handles_revision_create_data(self) -> None:
        """QuotationRevisionCreate (subset of fields) also works."""
        existing = _mock_quotation(
            company="Old Company",
            valid_till=date(2026, 5, 21),
        )
        revision_data = QuotationRevisionCreate(
            valid_till=date(2026, 6, 15),
            terms_and_conditions="Net 45 days.",
        )

        merged = _build_quotation_merged(revision_data, existing)

        assert merged.valid_till == date(2026, 6, 15)
        assert merged.company == "Old Company"  # Preserved from existing
        assert merged.terms_and_conditions == "Net 45 days."

    def test_handles_all_quotation_fields(self) -> None:
        """Verify all 30+ fields are correctly merged."""
        existing = _mock_quotation(
            quotation_to=QuotationPartyKind.LEAD,
            party_name="old-party-id",
            transaction_date=date(2026, 1, 1),
            valid_till=date(2026, 2, 1),
            company="Old Company",
            currency="USD",
            contact_person="Old Contact",
            contact_email="old@example.com",
            contact_mobile="000-000-0000",
            job_title="Old Title",
            territory="Old Territory",
            customer_group="Old Group",
            billing_address="Old Billing",
            shipping_address="Old Shipping",
            utm_source="old_source",
            utm_medium="old_medium",
            utm_campaign="old_campaign",
            utm_content="old_content",
        )
        update_data = QuotationUpdate(
            version=1,
            quotation_to=QuotationPartyKind.CUSTOMER,
            party_name="new-party-id",
            company="New Company",
            currency="EUR",
        )

        merged = _build_quotation_merged(update_data, existing)

        # Updated fields
        assert merged.quotation_to == QuotationPartyKind.CUSTOMER
        assert merged.party_name == "new-party-id"
        assert merged.company == "New Company"
        assert merged.currency == "EUR"

        # Preserved fields
        assert merged.transaction_date == date(2026, 1, 1)
        assert merged.valid_till == date(2026, 2, 1)
        assert merged.contact_person == "Old Contact"
        assert merged.contact_email == "old@example.com"
        assert merged.contact_mobile == "000-000-0000"
        assert merged.job_title == "Old Title"
        assert merged.territory == "Old Territory"
        assert merged.customer_group == "Old Group"
        assert merged.billing_address == "Old Billing"
        assert merged.shipping_address == "Old Shipping"
        assert merged.utm_source == "old_source"
        assert merged.utm_medium == "old_medium"
        assert merged.utm_campaign == "old_campaign"
        assert merged.utm_content == "old_content"


class TestShouldResolveParty:
    """Tests for _should_resolve_party helper (Issue #4 fix)."""

    def test_returns_false_when_unchanged(self) -> None:
        """No party resolution needed when quotation_to and party_name are unchanged."""
        existing = _mock_quotation(
            quotation_to=QuotationPartyKind.LEAD,
            party_name="11111111-2222-3333-4444-555555555555",
        )
        merged = QuotationCreate(
            quotation_to=QuotationPartyKind.LEAD,
            party_name="11111111-2222-3333-4444-555555555555",
            transaction_date=date(2026, 4, 21),
            company="Test",
            items=[],
        )

        assert _should_resolve_party(merged, existing) is False

    def test_returns_true_when_quotation_to_changed(self) -> None:
        """Party resolution needed when quotation_to changes."""
        existing = _mock_quotation(
            quotation_to=QuotationPartyKind.LEAD,
            party_name="same-id",
        )
        merged = QuotationCreate(
            quotation_to=QuotationPartyKind.CUSTOMER,
            party_name="same-id",
            transaction_date=date(2026, 4, 21),
            company="Test",
            items=[],
        )

        assert _should_resolve_party(merged, existing) is True

    def test_returns_true_when_party_name_changed(self) -> None:
        """Party resolution needed when party_name changes."""
        existing = _mock_quotation(
            quotation_to=QuotationPartyKind.LEAD,
            party_name="old-id",
        )
        merged = QuotationCreate(
            quotation_to=QuotationPartyKind.LEAD,
            party_name="new-id",
            transaction_date=date(2026, 4, 21),
            company="Test",
            items=[],
        )

        assert _should_resolve_party(merged, existing) is True

    def test_returns_true_when_both_changed(self) -> None:
        """Party resolution needed when both quotation_to and party_name change."""
        existing = _mock_quotation(
            quotation_to=QuotationPartyKind.LEAD,
            party_name="old-id",
        )
        merged = QuotationCreate(
            quotation_to=QuotationPartyKind.CUSTOMER,
            party_name="new-id",
            transaction_date=date(2026, 4, 21),
            company="Test",
            items=[],
        )

        assert _should_resolve_party(merged, existing) is True

    def test_handles_none_quotation_to_in_existing(self) -> None:
        """Handle existing quotation_to being None."""
        existing = MagicMock()
        existing.quotation_to = None
        existing.party_name = "same"
        merged = QuotationCreate(
            quotation_to=QuotationPartyKind.LEAD,
            party_name="same",
            transaction_date=date(2026, 4, 21),
            company="Test",
            items=[],
        )

        # Should trigger resolution when comparing None vs LEAD
        assert _should_resolve_party(merged, existing) is True


class TestApplyQuotationFieldsToRecord:
    """Tests for _apply_quotation_fields_to_record helper."""

    def test_applies_basic_fields(self) -> None:
        """Verify merged fields are correctly applied to record."""
        record = _mock_quotation_record()
        merged = QuotationCreate(
            quotation_to=QuotationPartyKind.CUSTOMER,
            party_name="new-party",
            party_label="New Party Label",
            transaction_date=date(2026, 4, 21),
            valid_till=date(2026, 5, 21),
            company="New Company",
            currency="EUR",
            subtotal=Decimal("1000.00"),
            total_taxes=Decimal("50.00"),
            grand_total=Decimal("1050.00"),
            base_grand_total=Decimal("1050.00"),
            contact_person="Jane Doe",
            contact_email="jane@example.com",
            contact_mobile="0912-999-888",
            job_title="CEO",
            territory="South",
            customer_group="Tech",
            billing_address="New Billing",
            shipping_address="New Shipping",
            utm_source="new_source",
            utm_medium="new_medium",
            utm_campaign="new_campaign",
            utm_content="new_content",
            terms_template="new_template",
            terms_and_conditions="Net 60 days.",
            opportunity_id=None,
            auto_repeat_enabled=False,
            auto_repeat_frequency="quarterly",
            auto_repeat_until=None,
            notes="New notes",
            items=[],
            taxes=[],
        )

        _apply_quotation_fields_to_record(record, merged, party_name="new-party", party_label="New Party Label")

        assert record.quotation_to == QuotationPartyKind.CUSTOMER
        assert record.party_name == "new-party"
        assert record.party_label == "New Party Label"
        assert record.company == "New Company"
        assert record.currency == "EUR"
        assert record.contact_person == "Jane Doe"
        assert record.contact_email == "jane@example.com"
        assert record.job_title == "CEO"
        assert record.terms_and_conditions == "Net 60 days."

    def test_applies_trimmed_string_fields(self) -> None:
        """Verify string fields are trimmed during application."""
        record = _mock_quotation_record()
        merged = QuotationCreate(
            quotation_to=QuotationPartyKind.LEAD,
            party_name="party",
            party_label="Party",
            transaction_date=date(2026, 4, 21),
            valid_till=date(2026, 5, 21),
            company="  Trimmed Company  ",
            currency="USD",  # Valid 3-char currency (will be uppercased anyway)
            contact_person="  John  ",
            contact_email="john@  example.com  ",
            contact_mobile="  0912-000-000  ",
            job_title="  Manager  ",
            territory="  North  ",
            customer_group="  Group  ",
            billing_address="  Billing  ",
            shipping_address="  Shipping  ",
            utm_source="  source  ",
            utm_medium="  medium  ",
            utm_campaign="  campaign  ",
            utm_content="  content  ",
            terms_template="  template  ",
            terms_and_conditions="  Terms  ",
            notes="  Notes  ",
            auto_repeat_frequency="  monthly  ",
            items=[],
            taxes=[],
        )

        _apply_quotation_fields_to_record(record, merged, party_name="party", party_label="Party")

        assert record.company == "Trimmed Company"
        assert record.currency == "USD"  # Also uppercased
        assert record.contact_person == "John"
        assert record.contact_email == "john@  example.com"  # Internal spaces preserved
        assert record.job_title == "Manager"
        assert record.territory == "North"
        assert record.utm_source == "source"
        assert record.utm_medium == "medium"

    def test_applies_party_defaults_when_provided(self) -> None:
        """Verify party defaults are applied when available."""
        record = _mock_quotation_record()
        merged = QuotationCreate(
            quotation_to=QuotationPartyKind.CUSTOMER,
            party_name="party",
            party_label="Party",
            transaction_date=date(2026, 4, 21),
            valid_till=date(2026, 5, 21),
            company="Company",
            currency="USD",
            contact_person="",  # Empty - should use party_default
            contact_email="",  # Empty - should use party_default
            contact_mobile="",  # Empty - should use party_default
            territory="",  # Empty - should use party_default
            utm_source="",  # Empty - should use party_default
            utm_medium="",  # Empty - should use party_default
            utm_campaign="",  # Empty - should use party_default
            utm_content="",  # Empty - should use party_default
            items=[],
            taxes=[],
        )
        party_defaults = {
            "contact_person": "Default Contact",
            "contact_email": "default@example.com",
            "contact_mobile": "0912-000-000",
            "territory": "Default Territory",
            "utm_source": "default_source",
            "utm_medium": "default_medium",
            "utm_campaign": "default_campaign",
            "utm_content": "default_content",
        }

        _apply_quotation_fields_to_record(record, merged, party_name="party", party_label="Party", party_defaults=party_defaults)

        assert record.contact_person == "Default Contact"
        assert record.contact_email == "default@example.com"
        assert record.contact_mobile == "0912-000-000"
        assert record.territory == "Default Territory"
        assert record.utm_source == "default_source"
        assert record.utm_medium == "default_medium"
        assert record.utm_campaign == "default_campaign"
        assert record.utm_content == "default_content"

    def test_increments_version(self) -> None:
        """Verify version is incremented after applying fields."""
        record = _mock_quotation_record()
        record.version = 5
        merged = QuotationCreate(
            quotation_to=QuotationPartyKind.LEAD,
            party_name="party",
            party_label="Party",
            transaction_date=date(2026, 4, 21),
            valid_till=date(2026, 5, 21),
            company="Company",
            currency="USD",
            items=[],
            taxes=[],
        )

        _apply_quotation_fields_to_record(record, merged, party_name="party", party_label="Party")

        assert record.version == 6


class TestBuildQuotationRecord:
    """Tests for _build_quotation_record helper (Issue #3 fix)."""

    def test_creates_quotation_with_merged_values(self) -> None:
        """Verify record is created with correct merged values."""
        merged = QuotationCreate(
            quotation_to=QuotationPartyKind.CUSTOMER,
            party_name="customer-id",
            party_label="Acme Corp",
            transaction_date=date(2026, 4, 21),
            valid_till=date(2026, 5, 21),
            company="Acme Corp",
            currency="USD",
            subtotal=Decimal("5000.00"),
            total_taxes=Decimal("500.00"),
            grand_total=Decimal("5500.00"),
            base_grand_total=Decimal("5500.00"),
            contact_person="Bob Smith",
            contact_email="bob@acme.com",
            contact_mobile="0912-111-222",
            job_title="Director",
            territory="East",
            customer_group="Enterprise",
            billing_address="123 Main St",
            shipping_address="456 Warehouse Rd",
            utm_source="google",
            utm_medium="cpc",
            utm_campaign="spring-sale",
            utm_content="banner-1",
            terms_template="standard",
            terms_and_conditions="Net 30",
            opportunity_id=uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"),
            auto_repeat_enabled=True,
            auto_repeat_frequency="monthly",
            auto_repeat_until=date(2026, 12, 31),
            notes="First quotation",
            items=[
                OpportunityItemInput(
                    item_name="Widget",
                    description="Blue widget",
                    quantity=Decimal("10"),
                    unit_price=Decimal("500.00"),
                )
            ],
            taxes=[
                QuotationTaxInput(
                    description="Tax",
                    rate=Decimal("10.00"),
                    tax_amount=Decimal("500.00"),
                )
            ],
        )
        tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")

        record = _build_quotation_record(merged, tenant_id, party_name="customer-id", party_label="Acme Corp")

        assert record.tenant_id == tenant_id
        assert record.quotation_to == QuotationPartyKind.CUSTOMER
        assert record.party_name == "customer-id"
        assert record.party_label == "Acme Corp"
        assert record.company == "Acme Corp"
        assert record.currency == "USD"
        assert record.status == QuotationStatus.DRAFT
        assert record.contact_person == "Bob Smith"
        assert record.ordered_amount == Decimal("0.00")
        assert record.order_count == 0

    def test_applies_party_defaults_when_provided(self) -> None:
        """Verify party defaults are applied to record creation."""
        merged = QuotationCreate(
            quotation_to=QuotationPartyKind.CUSTOMER,
            party_name="customer-id",
            party_label="Party",
            transaction_date=date(2026, 4, 21),
            valid_till=date(2026, 5, 21),
            company="Company",
            currency="USD",
            contact_person="",  # Empty
            contact_email="",  # Empty
            contact_mobile="",  # Empty
            territory="",  # Empty
            utm_source="",  # Empty
            utm_medium="",  # Empty
            utm_campaign="",  # Empty
            utm_content="",  # Empty
            items=[],
            taxes=[],
        )
        tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        party_defaults = {
            "contact_person": "Default Person",
            "contact_email": "default@example.com",
            "contact_mobile": "0912-000-000",
            "territory": "Default Territory",
            "utm_source": "default_src",
            "utm_medium": "default_med",
            "utm_campaign": "default_camp",
            "utm_content": "default_cont",
        }

        record = _build_quotation_record(merged, tenant_id, party_name="customer-id", party_label="Party", party_defaults=party_defaults)

        assert record.contact_person == "Default Person"
        assert record.contact_email == "default@example.com"
        assert record.contact_mobile == "0912-000-000"
        assert record.territory == "Default Territory"
        assert record.utm_source == "default_src"
        assert record.utm_medium == "default_med"
        assert record.utm_campaign == "default_camp"
        assert record.utm_content == "default_cont"

    def test_trims_and_uppercases_string_fields(self) -> None:
        """Verify string fields are trimmed and currency is uppercased."""
        merged = QuotationCreate(
            quotation_to=QuotationPartyKind.LEAD,
            party_name="lead-id",
            party_label="Lead",
            transaction_date=date(2026, 4, 21),
            valid_till=date(2026, 5, 21),
            company="  Company Name  ",
            currency="twd",  # Valid 3-char currency (will be uppercased)
            contact_person="  Contact  ",
            job_title="  Title  ",
            items=[],
            taxes=[],
        )
        tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")

        record = _build_quotation_record(merged, tenant_id, party_name="lead-id", party_label="Lead")

        assert record.company == "Company Name"
        assert record.currency == "TWD"
        assert record.contact_person == "Contact"
        assert record.job_title == "Title"


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

def _mock_quotation(**overrides) -> MagicMock:
    """Create a mock Quotation-like object for testing helpers."""
    mock = MagicMock()
    mock.quotation_to = QuotationPartyKind.LEAD
    mock.party_name = "11111111-2222-3333-4444-555555555555"
    mock.party_label = "Test Party"
    mock.transaction_date = date(2026, 4, 21)
    mock.valid_till = date(2026, 5, 21)
    mock.company = "Test Company"
    mock.currency = "USD"
    mock.contact_person = "John Doe"
    mock.contact_email = "john@example.com"
    mock.contact_mobile = "0912-345-678"
    mock.job_title = "Manager"
    mock.territory = "North"
    mock.customer_group = "Industrial"
    mock.billing_address = "123 Test St"
    mock.shipping_address = "456 Ship Rd"
    mock.utm_source = "test_source"
    mock.utm_medium = "test_medium"
    mock.utm_campaign = "test_campaign"
    mock.utm_content = "test_content"
    mock.opportunity_id = None
    mock.items = "[]"  # JSON string
    mock.taxes = "[]"  # JSON string
    mock.terms_template = "standard"
    mock.terms_and_conditions = "Net 30"
    mock.auto_repeat_enabled = False
    mock.auto_repeat_frequency = ""
    mock.auto_repeat_until = None
    mock.notes = "Test notes"
    mock.version = 1

    for key, value in overrides.items():
        setattr(mock, key, value)

    return mock


def _mock_quotation_record() -> MagicMock:
    """Create a mock Quotation record for testing field application."""
    mock = MagicMock(spec=Quotation)
    mock.quotation_to = QuotationPartyKind.LEAD
    mock.party_name = "original-party"
    mock.party_label = "Original Label"
    mock.transaction_date = date(2026, 1, 1)
    mock.valid_till = date(2026, 2, 1)
    mock.company = "Original Company"
    mock.currency = "USD"
    mock.subtotal = Decimal("0.00")
    mock.total_taxes = Decimal("0.00")
    mock.grand_total = Decimal("0.00")
    mock.base_grand_total = Decimal("0.00")
    mock.contact_person = "Original Contact"
    mock.contact_email = "original@example.com"
    mock.contact_mobile = "0912-000-000"
    mock.job_title = "Original Title"
    mock.territory = "Original Territory"
    mock.customer_group = "Original Group"
    mock.billing_address = "Original Billing"
    mock.shipping_address = "Original Shipping"
    mock.utm_source = "original_source"
    mock.utm_medium = "original_medium"
    mock.utm_campaign = "original_campaign"
    mock.utm_content = "original_content"
    mock.items = "[]"
    mock.taxes = "[]"
    mock.terms_template = "original_template"
    mock.terms_and_conditions = "Original Terms"
    mock.opportunity_id = None
    mock.auto_repeat_enabled = False
    mock.auto_repeat_frequency = "original_frequency"
    mock.auto_repeat_until = None
    mock.notes = "Original notes"
    mock.version = 1
    mock.updated_at = datetime(2026, 1, 1, tzinfo=UTC)
    return mock
