"""Tests for customer creation service logic.

These tests exercise the validation and business logic in the service layer
without a real database — the DB interaction is tested in the API tests.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError as PydanticValidationError

from domains.customers.schemas import CustomerCreate
from domains.customers.service import _validate_customer_fields


def _valid_payload(**overrides: object) -> CustomerCreate:
    defaults = {
        "company_name": "台灣好公司有限公司",
        "business_number": "04595257",
        "billing_address": "台北市信義區信義路五段7號",
        "contact_name": "王大明",
        "contact_phone": "0912-345-678",
        "contact_email": "wang@example.com",
        "credit_limit": Decimal("100000.00"),
    }
    defaults.update(overrides)
    return CustomerCreate(**defaults)  # type: ignore[arg-type]


class TestValidPayload:
    def test_no_errors_for_valid_payload(self) -> None:
        errors = _validate_customer_fields(_valid_payload())
        assert errors == []

    def test_accepts_landline_phone(self) -> None:
        errors = _validate_customer_fields(_valid_payload(contact_phone="(02) 2345-6789"))
        assert errors == []

    def test_accepts_plus886_mobile(self) -> None:
        errors = _validate_customer_fields(_valid_payload(contact_phone="+886912345678"))
        assert errors == []

    def test_accepts_zero_credit_limit(self) -> None:
        errors = _validate_customer_fields(_valid_payload(credit_limit=Decimal("0.00")))
        assert errors == []


class TestBusinessNumberValidation:
    def test_invalid_checksum(self) -> None:
        errors = _validate_customer_fields(_valid_payload(business_number="04595258"))
        assert len(errors) == 1
        assert errors[0]["field"] == "business_number"

    def test_short_business_number(self) -> None:
        errors = _validate_customer_fields(_valid_payload(business_number="0459525"))
        assert len(errors) == 1
        assert errors[0]["field"] == "business_number"


class TestPhoneValidation:
    def test_invalid_phone(self) -> None:
        errors = _validate_customer_fields(_valid_payload(contact_phone="12345"))
        assert len(errors) == 1
        assert errors[0]["field"] == "contact_phone"

    def test_us_phone_rejected(self) -> None:
        errors = _validate_customer_fields(_valid_payload(contact_phone="+1-212-555-1234"))
        assert len(errors) == 1
        assert errors[0]["field"] == "contact_phone"


class TestEmailValidation:
    def test_missing_at_sign(self) -> None:
        errors = _validate_customer_fields(_valid_payload(contact_email="foo.example.com"))
        assert len(errors) == 1
        assert errors[0]["field"] == "contact_email"

    def test_missing_tld(self) -> None:
        errors = _validate_customer_fields(_valid_payload(contact_email="foo@bar"))
        assert len(errors) == 1
        assert errors[0]["field"] == "contact_email"


class TestCreditLimitValidation:
    def test_negative_credit_limit_rejected_by_schema(self) -> None:
        with pytest.raises(PydanticValidationError):
            _valid_payload(credit_limit=Decimal("-1.00"))

    def test_exceeds_numeric_precision(self) -> None:
        errors = _validate_customer_fields(
            _valid_payload(credit_limit=Decimal("99999999999.99"))
        )
        assert len(errors) == 1
        assert errors[0]["field"] == "credit_limit"


class TestMultipleErrors:
    def test_multiple_validation_failures(self) -> None:
        errors = _validate_customer_fields(
            _valid_payload(
                business_number="bad",
                contact_phone="bad",
                contact_email="bad",
            )
        )
        fields = {e["field"] for e in errors}
        assert fields == {"business_number", "contact_phone", "contact_email"}
