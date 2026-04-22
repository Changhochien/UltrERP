"""Tests for CRM opportunity service helper functions (Issue #2 fix)."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from domains.crm.models import Opportunity
from domains.crm.schemas import (
    OpportunityCreate,
    OpportunityItemInput,
    OpportunityPartyKind,
    OpportunityUpdate,
)
from domains.crm.service import (
    _apply_opportunity_fields_to_record,
    _build_opportunity_merged,
    _should_resolve_opportunity_party,
)


class TestBuildOpportunityMerged:
    """Tests for _build_opportunity_merged helper (Issue #2 fix)."""

    def test_uses_update_values_when_provided(self) -> None:
        """When a field is in the update payload, use the new value."""
        existing = _mock_opportunity(opportunity_title="Old Title", currency="USD")
        update_data = OpportunityUpdate(
            version=1,
            opportunity_title="New Title",
            currency="EUR",
        )

        merged = _build_opportunity_merged(update_data, existing)

        assert merged.opportunity_title == "New Title"
        assert merged.currency == "EUR"

    def test_uses_existing_values_when_field_not_in_update(self) -> None:
        """When a field is NOT in the update payload, keep existing value."""
        existing = _mock_opportunity(
            opportunity_title="Existing Title",
            currency="USD",
            territory="North",
            contact_person="John Doe",
        )
        update_data = OpportunityUpdate(version=1)

        merged = _build_opportunity_merged(update_data, existing)

        assert merged.opportunity_title == "Existing Title"
        assert merged.currency == "USD"
        assert merged.territory == "North"
        assert merged.contact_person == "John Doe"

    def test_handles_party_kind_conversion(self) -> None:
        """opportunity_from is stored as string but schema expects enum."""
        existing = _mock_opportunity(opportunity_from=OpportunityPartyKind.LEAD)
        update_data = OpportunityUpdate(
            version=1,
            opportunity_from=OpportunityPartyKind.CUSTOMER,
        )

        merged = _build_opportunity_merged(update_data, existing)

        assert merged.opportunity_from == OpportunityPartyKind.CUSTOMER

    def test_handles_opportunity_from_when_not_in_update(self) -> None:
        """When opportunity_from not in update, preserve existing enum type."""
        existing = _mock_opportunity(opportunity_from=OpportunityPartyKind.LEAD)
        update_data = OpportunityUpdate(version=1)

        merged = _build_opportunity_merged(update_data, existing)

        assert merged.opportunity_from == OpportunityPartyKind.LEAD

    def test_preserves_party_name_when_not_in_update(self) -> None:
        """party_name should preserve existing value."""
        existing = _mock_opportunity(party_name="11111111-2222-3333-4444-555555555555")
        update_data = OpportunityUpdate(version=1)

        merged = _build_opportunity_merged(update_data, existing)

        assert merged.party_name == "11111111-2222-3333-4444-555555555555"

    def test_handles_items_deserialization(self) -> None:
        """items stored as JSON should be deserialized in merged output."""
        existing = _mock_opportunity()
        existing.items = '[{"item_name": "Widget", "quantity": "5"}]'
        update_data = OpportunityUpdate(version=1)

        merged = _build_opportunity_merged(update_data, existing)

        assert merged.items is not None
        assert len(merged.items) == 1
        assert merged.items[0].item_name == "Widget"

    def test_handles_all_opportunity_fields(self) -> None:
        """Verify all fields are correctly merged."""
        existing = _mock_opportunity(
            opportunity_title="Old Title",
            opportunity_from=OpportunityPartyKind.LEAD,
            party_name="old-party-id",
            sales_stage="qualification",
            probability=20,
            currency="USD",
            contact_person="Old Contact",
            contact_email="old@example.com",
            contact_mobile="000-000-0000",
            job_title="Old Title",
            territory="Old Territory",
            customer_group="Old Group",
            utm_source="old_source",
            utm_medium="old_medium",
            utm_campaign="old_campaign",
            utm_content="old_content",
        )
        update_data = OpportunityUpdate(
            version=1,
            opportunity_title="New Title",
            opportunity_from=OpportunityPartyKind.CUSTOMER,
            party_name="new-party-id",
            probability=50,
        )

        merged = _build_opportunity_merged(update_data, existing)

        # Updated fields
        assert merged.opportunity_title == "New Title"
        assert merged.opportunity_from == OpportunityPartyKind.CUSTOMER
        assert merged.party_name == "new-party-id"
        assert merged.probability == 50

        # Preserved fields
        assert merged.sales_stage == "qualification"
        assert merged.currency == "USD"
        assert merged.contact_person == "Old Contact"
        assert merged.contact_email == "old@example.com"
        assert merged.contact_mobile == "000-000-0000"
        assert merged.job_title == "Old Title"
        assert merged.territory == "Old Territory"
        assert merged.customer_group == "Old Group"
        assert merged.utm_source == "old_source"
        assert merged.utm_medium == "old_medium"
        assert merged.utm_campaign == "old_campaign"
        assert merged.utm_content == "old_content"


class TestShouldResolveOpportunityParty:
    """Tests for _should_resolve_opportunity_party helper."""

    def test_returns_true_when_opportunity_from_changed(self) -> None:
        """Party resolution needed when opportunity_from changes."""
        existing = _mock_opportunity(
            opportunity_from=OpportunityPartyKind.LEAD,
            party_name="same-id",
        )
        merged = OpportunityCreate(
            opportunity_title="Test",
            opportunity_from=OpportunityPartyKind.CUSTOMER,
            party_name="same-id",
        )

        assert _should_resolve_opportunity_party(merged, existing) is True

    def test_returns_true_when_party_name_changed(self) -> None:
        """Party resolution needed when party_name changes."""
        existing = _mock_opportunity(
            opportunity_from=OpportunityPartyKind.LEAD,
            party_name="old-id",
        )
        merged = OpportunityCreate(
            opportunity_title="Test",
            opportunity_from=OpportunityPartyKind.LEAD,
            party_name="new-id",
        )

        assert _should_resolve_opportunity_party(merged, existing) is True

    def test_returns_true_when_both_changed(self) -> None:
        """Party resolution needed when both opportunity_from and party_name change."""
        existing = _mock_opportunity(
            opportunity_from=OpportunityPartyKind.LEAD,
            party_name="old-id",
        )
        merged = OpportunityCreate(
            opportunity_title="Test",
            opportunity_from=OpportunityPartyKind.CUSTOMER,
            party_name="new-id",
        )

        assert _should_resolve_opportunity_party(merged, existing) is True

    def test_handles_none_opportunity_from_in_existing(self) -> None:
        """Handle existing opportunity_from being None."""
        existing = MagicMock()
        existing.opportunity_from = None
        existing.party_name = "same"
        merged = OpportunityCreate(
            opportunity_title="Test",
            opportunity_from=OpportunityPartyKind.LEAD,
            party_name="same",
        )

        # Should trigger resolution when comparing None vs LEAD
        assert _should_resolve_opportunity_party(merged, existing) is True


class TestApplyOpportunityFieldsToRecord:
    """Tests for _apply_opportunity_fields_to_record helper."""

    def test_applies_basic_fields(self) -> None:
        """Verify merged fields are correctly applied to record."""
        record = _mock_opportunity_record()
        merged = OpportunityCreate(
            opportunity_title="New Title",
            opportunity_from=OpportunityPartyKind.CUSTOMER,
            party_name="new-party",
            sales_stage="proposal",
            probability=75,
            expected_closing=date(2026, 6, 15),
            currency="EUR",
            opportunity_amount=Decimal("50000.00"),
            opportunity_owner="Jane Manager",
            territory="South",
            customer_group="Enterprise",
            contact_person="Jane Doe",
            contact_email="jane@example.com",
            contact_mobile="0912-999-888",
            job_title="Director",
            utm_source="new_source",
            utm_medium="new_medium",
            utm_campaign="new_campaign",
            utm_content="new_content",
            notes="Updated notes",
            items=[],
        )

        _apply_opportunity_fields_to_record(
            record, merged, party_name="new-party", party_label="New Party Label"
        )

        assert record.opportunity_title == "New Title"
        assert record.opportunity_from == OpportunityPartyKind.CUSTOMER
        assert record.party_name == "new-party"
        assert record.sales_stage == "proposal"
        assert record.probability == 75
        assert record.currency == "EUR"
        assert record.opportunity_amount == Decimal("50000.00")
        assert record.contact_person == "Jane Doe"
        assert record.job_title == "Director"

    def test_applies_trimmed_string_fields(self) -> None:
        """Verify string fields are trimmed during application."""
        record = _mock_opportunity_record()
        merged = OpportunityCreate(
            opportunity_title="  Trimmed Title  ",
            opportunity_from=OpportunityPartyKind.LEAD,
            party_name="party",
            sales_stage="  qualification  ",
            currency="USD",
            opportunity_owner="  Manager  ",
            contact_person="  John  ",
            contact_email="john@  example.com  ",
            contact_mobile="  0912-000-000  ",
            job_title="  Manager  ",
            territory="  North  ",
            customer_group="  Group  ",
            utm_source="  source  ",
            utm_medium="  medium  ",
            utm_campaign="  campaign  ",
            utm_content="  content  ",
            notes="  Notes  ",
            items=[],
        )

        _apply_opportunity_fields_to_record(
            record, merged, party_name="party", party_label="Party"
        )

        assert record.opportunity_title == "Trimmed Title"
        assert record.sales_stage == "qualification"
        assert record.opportunity_owner == "Manager"
        assert record.contact_person == "John"
        assert record.territory == "North"
        assert record.utm_source == "source"
        assert record.utm_medium == "medium"

    def test_applies_party_defaults_when_provided(self) -> None:
        """Verify party defaults are applied when available."""
        record = _mock_opportunity_record()
        merged = OpportunityCreate(
            opportunity_title="Title",
            opportunity_from=OpportunityPartyKind.CUSTOMER,
            party_name="party",
            sales_stage="qualification",
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

        _apply_opportunity_fields_to_record(
            record, merged, party_name="party", party_label="Party", party_defaults=party_defaults
        )

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
        record = _mock_opportunity_record()
        record.version = 5
        merged = OpportunityCreate(
            opportunity_title="Title",
            opportunity_from=OpportunityPartyKind.LEAD,
            party_name="party",
            sales_stage="qualification",
            currency="USD",
            items=[],
        )

        _apply_opportunity_fields_to_record(
            record, merged, party_name="party", party_label="Party"
        )

        assert record.version == 6

    def test_applies_serialized_items(self) -> None:
        """Verify serialized items are applied to record."""
        record = _mock_opportunity_record()
        merged = OpportunityCreate(
            opportunity_title="Title",
            opportunity_from=OpportunityPartyKind.LEAD,
            party_name="party",
            sales_stage="qualification",
            currency="USD",
            items=[
                OpportunityItemInput(
                    item_name="Widget",
                    description="Blue widget",
                    quantity=Decimal("10"),
                    unit_price=Decimal("500.00"),
                )
            ],
        )
        serialized_items = [
            {
                "line_no": 1,
                "item_name": "Widget",
                "item_code": "",
                "description": "Blue widget",
                "quantity": "10.00",
                "unit_price": "500.00",
                "amount": "5000.00",
            }
        ]

        _apply_opportunity_fields_to_record(
            record, merged, party_name="party", party_label="Party", serialized_items=serialized_items
        )

        assert record.items == serialized_items


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


def _mock_opportunity(**overrides) -> MagicMock:
    """Create a mock Opportunity-like object for testing helpers."""
    mock = MagicMock()
    mock.opportunity_title = "Test Opportunity"
    mock.opportunity_from = OpportunityPartyKind.LEAD
    mock.party_name = "11111111-2222-3333-4444-555555555555"
    mock.sales_stage = "qualification"
    mock.probability = 20
    mock.expected_closing = date(2026, 6, 15)
    mock.currency = "TWD"
    mock.opportunity_amount = Decimal("10000.00")
    mock.base_opportunity_amount = Decimal("10000.00")
    mock.opportunity_owner = "John Owner"
    mock.territory = "North"
    mock.customer_group = "Industrial"
    mock.contact_person = "John Doe"
    mock.contact_email = "john@example.com"
    mock.contact_mobile = "0912-345-678"
    mock.job_title = "Manager"
    mock.utm_source = "test_source"
    mock.utm_medium = "test_medium"
    mock.utm_campaign = "test_campaign"
    mock.utm_content = "test_content"
    mock.items = "[]"  # JSON string
    mock.notes = "Test notes"
    mock.version = 1

    for key, value in overrides.items():
        setattr(mock, key, value)

    return mock


def _mock_opportunity_record() -> MagicMock:
    """Create a mock Opportunity record for testing field application."""
    mock = MagicMock(spec=Opportunity)
    mock.opportunity_title = "Original Title"
    mock.opportunity_from = OpportunityPartyKind.LEAD
    mock.party_name = "original-party"
    mock.party_label = "Original Label"
    mock.sales_stage = "qualification"
    mock.probability = 20
    mock.expected_closing = date(2026, 6, 15)
    mock.currency = "USD"
    mock.opportunity_amount = Decimal("10000.00")
    mock.base_opportunity_amount = Decimal("10000.00")
    mock.opportunity_owner = "Original Owner"
    mock.territory = "Original Territory"
    mock.customer_group = "Original Group"
    mock.contact_person = "Original Contact"
    mock.contact_email = "original@example.com"
    mock.contact_mobile = "0912-000-000"
    mock.job_title = "Original Title"
    mock.utm_source = "original_source"
    mock.utm_medium = "original_medium"
    mock.utm_campaign = "original_campaign"
    mock.utm_content = "original_content"
    mock.items = "[]"
    mock.notes = "Original notes"
    mock.version = 1
    mock.updated_at = datetime(2026, 1, 1, tzinfo=UTC)
    return mock
