"""Tests for duplicate business number detection in customer service layer.

These tests verify the optimistic pre-check and the IntegrityError race
condition fallback both raise the same DuplicateBusinessNumberError.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest

from common.errors import DuplicateBusinessNumberError, ValidationError
from domains.customers.schemas import CustomerCreate
from domains.customers.service import create_customer

_TENANT_OK = "SET LOCAL app.tenant_id"


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


class _FakeExistingCustomer:
    """Stub mimicking a Customer ORM object found during pre-check."""

    def __init__(
        self,
        customer_id: uuid.UUID | None = None,
        company_name: str = "Existing Corp",
        normalized_business_number: str = "04595257",
    ) -> None:
        self.id = customer_id or uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
        self.company_name = company_name
        self.normalized_business_number = normalized_business_number


class _FakeScalarResult:
    def __init__(self, value: object = None) -> None:
        self._value = value

    def scalar_one_or_none(self) -> object:
        return self._value


class FakeSessionNoDuplicate:
    """Session stub where the pre-check finds NO existing customer."""

    def __init__(self) -> None:
        self.added: list[Any] = []

    def add(self, instance: object) -> None:
        self.added.append(instance)

    async def execute(self, stmt: object, params: object = None) -> _FakeScalarResult:
        return _FakeScalarResult(None)

    async def refresh(self, instance: object) -> None:
        now = datetime.now(tz=UTC)
        if getattr(instance, "id", None) is None:
            instance.id = uuid.uuid4()  # type: ignore[attr-defined]
        if getattr(instance, "status", None) is None:
            instance.status = "active"  # type: ignore[attr-defined]
        if getattr(instance, "version", None) is None:
            instance.version = 1  # type: ignore[attr-defined]
        if getattr(instance, "created_at", None) is None:
            instance.created_at = now  # type: ignore[attr-defined]
        if getattr(instance, "updated_at", None) is None:
            instance.updated_at = now  # type: ignore[attr-defined]

    def begin(self) -> "FakeSessionNoDuplicate":
        return self

    async def __aenter__(self) -> "FakeSessionNoDuplicate":
        return self

    async def __aexit__(self, *args: object) -> None:
        pass


class FakeSessionWithDuplicate:
    """Session stub where the pre-check finds an existing customer."""

    def __init__(self, existing: _FakeExistingCustomer | None = None) -> None:
        self._existing = existing or _FakeExistingCustomer()

    async def execute(self, stmt: object, params: object = None) -> _FakeScalarResult:
        return _FakeScalarResult(self._existing)

    def begin(self) -> "FakeSessionWithDuplicate":
        return self

    async def __aenter__(self) -> "FakeSessionWithDuplicate":
        return self

    async def __aexit__(self, *args: object) -> None:
        pass


class FakeSessionIntegrityRace:
    """Session stub that passes the pre-check but raises IntegrityError on add.

    This simulates a race condition where another request inserted the same
    BAN between the pre-check and the actual insert.
    """

    def __init__(self, conflict_customer: _FakeExistingCustomer | None = None) -> None:
        self._conflict = conflict_customer or _FakeExistingCustomer()
        self._call_count = 0

    def add(self, instance: object) -> None:
        from sqlalchemy.exc import IntegrityError

        raise IntegrityError(
            statement="INSERT INTO customers ...",
            params={},
            orig=Exception("uq_customers_tenant_business_number"),
        )

    async def execute(self, stmt: object, params: object = None) -> _FakeScalarResult:
        self._call_count += 1
        if self._call_count <= 2:
            # First two execute calls: set_tenant + pre-check → no duplicate found
            return _FakeScalarResult(None)
        # Subsequent execute calls: set_tenant + conflict query after IntegrityError
        return _FakeScalarResult(self._conflict)

    def begin(self) -> "FakeSessionIntegrityRace":
        return self

    async def __aenter__(self) -> "FakeSessionIntegrityRace":
        return self

    async def __aexit__(self, *args: object) -> None:
        pass


class TestDuplicatePreCheck:
    """Pre-check branch: existing customer found before insert."""

    @pytest.mark.asyncio
    async def test_raises_duplicate_error_with_metadata(self) -> None:
        existing = _FakeExistingCustomer(
            customer_id=uuid.UUID("11111111-2222-3333-4444-555555555555"),
            company_name="台灣好公司",
        )
        session = FakeSessionWithDuplicate(existing)
        with pytest.raises(DuplicateBusinessNumberError) as exc_info:
            await create_customer(session, _valid_payload())  # type: ignore[arg-type]

        err = exc_info.value
        assert err.existing_id == uuid.UUID("11111111-2222-3333-4444-555555555555")
        assert err.existing_name == "台灣好公司"
        assert err.normalized_business_number == "04595257"

    @pytest.mark.asyncio
    async def test_duplicate_error_message(self) -> None:
        session = FakeSessionWithDuplicate()
        with pytest.raises(DuplicateBusinessNumberError, match="Duplicate business number"):
            await create_customer(session, _valid_payload())  # type: ignore[arg-type]


class TestNoDuplicate:
    """Non-duplicate create still succeeds."""

    @pytest.mark.asyncio
    async def test_create_succeeds_when_no_duplicate(self) -> None:
        session = FakeSessionNoDuplicate()
        customer = await create_customer(session, _valid_payload())  # type: ignore[arg-type]
        assert customer.company_name == "台灣好公司有限公司"
        assert customer.normalized_business_number == "04595257"
        assert len(session.added) == 1


class TestIntegrityErrorRace:
    """Race condition branch: pre-check passes but INSERT hits unique violation."""

    @pytest.mark.asyncio
    async def test_race_raises_duplicate_error(self) -> None:
        conflict = _FakeExistingCustomer(
            customer_id=uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"),
            company_name="Race Winner Corp",
        )
        session = FakeSessionIntegrityRace(conflict)
        with pytest.raises(DuplicateBusinessNumberError) as exc_info:
            await create_customer(session, _valid_payload())  # type: ignore[arg-type]

        err = exc_info.value
        assert err.existing_id == uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
        assert err.existing_name == "Race Winner Corp"
        assert err.normalized_business_number == "04595257"

    @pytest.mark.asyncio
    async def test_race_metadata_matches_optimistic_shape(self) -> None:
        """Both paths (optimistic + race) should produce errors with the same attributes."""
        # Optimistic path
        existing = _FakeExistingCustomer(
            customer_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
            company_name="Same Corp",
        )
        opt_session = FakeSessionWithDuplicate(existing)
        with pytest.raises(DuplicateBusinessNumberError) as opt:
            await create_customer(opt_session, _valid_payload())  # type: ignore[arg-type]

        # Race path
        conflict = _FakeExistingCustomer(
            customer_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
            company_name="Same Corp",
        )
        race_session = FakeSessionIntegrityRace(conflict)
        with pytest.raises(DuplicateBusinessNumberError) as race:
            await create_customer(race_session, _valid_payload())  # type: ignore[arg-type]

        # Both errors should have the same attributes
        assert opt.value.existing_id == race.value.existing_id
        assert opt.value.existing_name == race.value.existing_name
        assert opt.value.normalized_business_number == race.value.normalized_business_number


class TestValidationBeforeDuplicate:
    """Validation errors should be raised before duplicate checks."""

    @pytest.mark.asyncio
    async def test_validation_error_takes_priority(self) -> None:
        """Invalid data should raise ValidationError even if duplicate exists."""
        session = FakeSessionWithDuplicate()
        with pytest.raises(ValidationError):
            await create_customer(
                session,  # type: ignore[arg-type]
                _valid_payload(contact_phone="bad"),
            )
