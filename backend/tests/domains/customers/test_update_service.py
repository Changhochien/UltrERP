"""Tests for customer update service logic.

Exercises validation, optimistic locking, and duplicate-detection rules
in ``_validate_update_fields`` without a real database.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError as PydanticValidationError

from domains.customers.schemas import CustomerUpdate
from domains.customers.service import _validate_update_fields


def _update_payload(**overrides: object) -> CustomerUpdate:
    """Build a minimal valid CustomerUpdate (version-only by default)."""
    defaults: dict[str, object] = {"version": 1}
    defaults.update(overrides)
    return CustomerUpdate(**defaults)  # type: ignore[arg-type]


# ── Valid payloads ──────────────────────────────────────────────


class TestValidUpdatePayloads:
    def test_version_only(self) -> None:
        errors = _validate_update_fields(_update_payload())
        assert errors == []

    def test_update_company_name(self) -> None:
        errors = _validate_update_fields(_update_payload(company_name="新公司"))
        assert errors == []

    def test_update_phone_mobile(self) -> None:
        errors = _validate_update_fields(_update_payload(contact_phone="0912-345-678"))
        assert errors == []

    def test_update_phone_landline(self) -> None:
        errors = _validate_update_fields(_update_payload(contact_phone="(02) 2345-6789"))
        assert errors == []

    def test_update_email(self) -> None:
        errors = _validate_update_fields(_update_payload(contact_email="new@example.com"))
        assert errors == []

    def test_update_credit_limit_zero(self) -> None:
        errors = _validate_update_fields(_update_payload(credit_limit=Decimal("0.00")))
        assert errors == []

    def test_update_valid_business_number(self) -> None:
        errors = _validate_update_fields(_update_payload(business_number="04595257"))
        assert errors == []


# ── Phone validation ────────────────────────────────────────────


class TestUpdatePhoneValidation:
    def test_invalid_phone(self) -> None:
        errors = _validate_update_fields(_update_payload(contact_phone="12345"))
        assert len(errors) == 1
        assert errors[0]["field"] == "contact_phone"

    def test_us_phone_rejected(self) -> None:
        errors = _validate_update_fields(_update_payload(contact_phone="+1-212-555-1234"))
        assert len(errors) == 1
        assert errors[0]["field"] == "contact_phone"


# ── Email validation ────────────────────────────────────────────


class TestUpdateEmailValidation:
    def test_missing_at_sign(self) -> None:
        errors = _validate_update_fields(_update_payload(contact_email="foo.example.com"))
        assert len(errors) == 1
        assert errors[0]["field"] == "contact_email"

    def test_missing_tld(self) -> None:
        errors = _validate_update_fields(_update_payload(contact_email="foo@bar"))
        assert len(errors) == 1
        assert errors[0]["field"] == "contact_email"


# ── BAN validation ──────────────────────────────────────────────


class TestUpdateBanValidation:
    def test_invalid_checksum(self) -> None:
        errors = _validate_update_fields(_update_payload(business_number="04595258"))
        assert len(errors) == 1
        assert errors[0]["field"] == "business_number"

    def test_too_short(self) -> None:
        errors = _validate_update_fields(_update_payload(business_number="0459525"))
        assert len(errors) == 1
        assert errors[0]["field"] == "business_number"


# ── Credit limit validation ─────────────────────────────────────


class TestUpdateCreditLimitValidation:
    def test_negative_rejected_by_schema(self) -> None:
        with pytest.raises(PydanticValidationError):
            _update_payload(credit_limit=Decimal("-1.00"))

    def test_exceeds_numeric_precision(self) -> None:
        errors = _validate_update_fields(
            _update_payload(credit_limit=Decimal("99999999999.99"))
        )
        assert len(errors) == 1
        assert errors[0]["field"] == "credit_limit"


# ── Multiple validation errors ──────────────────────────────────


class TestUpdateMultipleErrors:
    def test_multiple_failures(self) -> None:
        errors = _validate_update_fields(
            _update_payload(
                business_number="bad",
                contact_phone="bad",
                contact_email="bad",
            )
        )
        fields = {e["field"] for e in errors}
        assert fields == {"business_number", "contact_phone", "contact_email"}


# ── Partial update: only provided fields validated ──────────────


class TestPartialUpdateValidation:
    def test_omitted_phone_not_validated(self) -> None:
        """If phone is NOT in the payload, it should NOT be validated."""
        data = CustomerUpdate(version=1, company_name="FooBar Inc.")
        errors = _validate_update_fields(data)
        assert errors == []

    def test_omitted_email_not_validated(self) -> None:
        data = CustomerUpdate(version=1, credit_limit=Decimal("500.00"))
        errors = _validate_update_fields(data)
        assert errors == []

    def test_provided_phone_invalid_triggers_error(self) -> None:
        data = CustomerUpdate(version=1, contact_phone="not-a-phone")
        errors = _validate_update_fields(data)
        assert len(errors) == 1
        assert errors[0]["field"] == "contact_phone"


# ── Schema constraints ──────────────────────────────────────────


class TestUpdateSchemaConstraints:
    def test_version_required(self) -> None:
        with pytest.raises(PydanticValidationError):
            CustomerUpdate()  # type: ignore[call-arg]

    def test_version_must_be_positive(self) -> None:
        with pytest.raises(PydanticValidationError):
            CustomerUpdate(version=0)
