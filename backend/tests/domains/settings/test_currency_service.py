"""Tests for currency and exchange rate service (Epic 25, Story 25-1).

These tests focus on the core conversion and resolution logic.
Integration tests with real database are handled separately.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest


# ============================================================
# Conversion Tests (Pure functions)
# ============================================================


class TestConversion:
    """Tests for amount conversion."""

    def test_convert_amount_basic(self) -> None:
        """Test basic amount conversion."""
        from domains.settings.exchange_rate_service import convert_amount

        result = convert_amount(
            amount=Decimal("100.00"),
            rate=Decimal("32.5"),
            target_precision=2,
        )
        assert result == Decimal("3250.00")

    def test_convert_amount_rounding(self) -> None:
        """Test that conversion applies proper rounding (HALF_UP)."""
        from domains.settings.exchange_rate_service import convert_amount

        # 100.333 * 32.1234567890 = 3223.04... (rounds to 3223.04 with HALF_UP)
        result = convert_amount(
            amount=Decimal("100.333"),
            rate=Decimal("32.1234567890"),
            target_precision=2,
        )
        # Due to floating point precision in Decimal, verify it's properly rounded
        assert result == Decimal("3223.04")

    def test_convert_amount_jpy_precision(self) -> None:
        """Test conversion with JPY (0 decimal places)."""
        from domains.settings.exchange_rate_service import convert_amount

        result = convert_amount(
            amount=Decimal("1000.50"),
            rate=Decimal("0.032"),
            target_precision=0,
        )
        assert result == Decimal("32")

    def test_convert_amount_high_precision(self) -> None:
        """Test conversion with high precision rate."""
        from domains.settings.exchange_rate_service import convert_amount

        result = convert_amount(
            amount=Decimal("1.00"),
            rate=Decimal("32.1234567890"),
            target_precision=4,
        )
        assert result == Decimal("32.1235")

    def test_convert_amount_identity(self) -> None:
        """Test that identity conversion (rate=1) returns same amount."""
        from domains.settings.exchange_rate_service import convert_amount

        result = convert_amount(
            amount=Decimal("1234.56"),
            rate=Decimal("1.0"),
            target_precision=2,
        )
        assert result == Decimal("1234.56")

    def test_convert_amount_small_amount(self) -> None:
        """Test conversion of small amounts."""
        from domains.settings.exchange_rate_service import convert_amount

        result = convert_amount(
            amount=Decimal("0.01"),
            rate=Decimal("32.5"),
            target_precision=2,
        )
        assert result == Decimal("0.33")

    def test_convert_amount_large_amount(self) -> None:
        """Test conversion of large amounts."""
        from domains.settings.exchange_rate_service import convert_amount

        result = convert_amount(
            amount=Decimal("1000000.00"),
            rate=Decimal("32.5"),
            target_precision=2,
        )
        assert result == Decimal("32500000.00")


# ============================================================
# Schema Validation Tests
# ============================================================


class TestCurrencySchemas:
    """Tests for currency Pydantic schemas."""

    def test_currency_create_valid(self) -> None:
        """Test valid currency creation schema."""
        from domains.settings.schemas_currency import CurrencyCreate

        data = CurrencyCreate(
            code="USD",
            symbol="$",
            decimal_places=2,
            is_active=True,
            is_base_currency=False,
        )
        assert data.code == "USD"
        assert data.symbol == "$"
        assert data.decimal_places == 2

    def test_currency_code_normalization(self) -> None:
        """Test that currency codes are normalized."""
        from domains.settings.schemas_currency import ExchangeRateCreate

        # The validator normalizes to uppercase but doesn't trim before length check
        # So we test with valid-length codes
        data = ExchangeRateCreate(
            source_currency_code="usd",
            target_currency_code="twd",
            effective_date=date.today(),
            rate=Decimal("32.5"),
        )
        assert data.source_currency_code == "USD"
        assert data.target_currency_code == "TWD"

    def test_exchange_rate_create_valid(self) -> None:
        """Test valid exchange rate creation schema."""
        from domains.settings.schemas_currency import ExchangeRateCreate

        data = ExchangeRateCreate(
            source_currency_code="USD",
            target_currency_code="TWD",
            effective_date=date.today(),
            rate=Decimal("32.5000000000"),
            rate_source="manual",
        )
        assert data.rate == Decimal("32.5000000000")

    def test_conversion_request_schema(self) -> None:
        """Test conversion request schema."""
        from domains.settings.schemas_currency import ConversionRequest

        data = ConversionRequest(
            source_currency_code="USD",
            target_currency_code="TWD",
            amount=Decimal("100.00"),
            effective_date=date.today(),
        )
        assert data.target_precision is None  # Should default to None

    def test_currency_code_min_length(self) -> None:
        """Test that currency code has minimum length validation."""
        from domains.settings.schemas_currency import CurrencyCreate
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            CurrencyCreate(
                code="US",  # Too short
                symbol="$",
                decimal_places=2,
            )

    def test_rate_positive_validation(self) -> None:
        """Test that rate must be positive."""
        from domains.settings.schemas_currency import ExchangeRateCreate
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ExchangeRateCreate(
                source_currency_code="USD",
                target_currency_code="TWD",
                effective_date=date.today(),
                rate=Decimal("-1.0"),  # Must be positive
            )


# ============================================================
# Data Model Tests
# ============================================================


class TestCurrencyModel:
    """Tests for Currency SQLAlchemy model attributes."""

    def test_currency_attributes(self) -> None:
        """Test Currency model has expected attributes."""
        from common.models.currency import Currency

        # Check that the model has expected columns as attributes
        # This is a basic structural test
        attrs = ["id", "tenant_id", "code", "symbol", "decimal_places", "is_active", "is_base_currency"]
        for attr in attrs:
            assert hasattr(Currency, attr), f"Currency missing attribute: {attr}"

    def test_exchange_rate_attributes(self) -> None:
        """Test ExchangeRate model has expected attributes."""
        from common.models.currency import ExchangeRate

        attrs = [
            "id",
            "tenant_id",
            "source_currency_code",
            "target_currency_code",
            "effective_date",
            "rate",
            "is_inverse",
            "rate_source",
            "is_active",
        ]
        for attr in attrs:
            assert hasattr(ExchangeRate, attr), f"ExchangeRate missing attribute: {attr}"


# ============================================================
# Error Classes Tests
# ============================================================


class TestErrorClasses:
    """Tests for error class behavior."""

    def test_currency_not_found_error(self) -> None:
        """Test CurrencyNotFoundError attributes."""
        import uuid

        from domains.settings.exchange_rate_service import CurrencyNotFoundError

        tenant_id = uuid.uuid4()
        error = CurrencyNotFoundError("USD", tenant_id, is_inactive=False)

        assert error.currency_code == "USD"
        assert error.is_inactive is False
        assert "USD" in str(error)

    def test_currency_not_found_error_inactive(self) -> None:
        """Test CurrencyNotFoundError for inactive currency."""
        import uuid

        from domains.settings.exchange_rate_service import CurrencyNotFoundError

        tenant_id = uuid.uuid4()
        error = CurrencyNotFoundError("USD", tenant_id, is_inactive=True)

        assert error.is_inactive is True
        assert "inactive" in str(error)

    def test_exchange_rate_not_found_error(self) -> None:
        """Test ExchangeRateNotFoundError attributes."""
        import uuid

        from domains.settings.exchange_rate_service import ExchangeRateNotFoundError

        tenant_id = uuid.uuid4()
        today = date.today()
        error = ExchangeRateNotFoundError("USD", "TWD", today, tenant_id)

        assert error.source_currency == "USD"
        assert error.target_currency == "TWD"
        assert error.effective_date == today
        assert "No exchange rate found" in str(error)


# ============================================================
# Service Schema Tests
# ============================================================


class TestServiceSchemas:
    """Tests for service-level schemas and types."""

    def test_resolved_exchange_rate_frozen(self) -> None:
        """Test that ResolvedExchangeRate is a frozen dataclass."""
        from dataclasses import is_dataclass

        from domains.settings.exchange_rate_service import ResolvedExchangeRate

        assert is_dataclass(ResolvedExchangeRate)

    def test_resolved_exchange_rate_immutable(self) -> None:
        """Test that ResolvedExchangeRate is immutable (frozen=True)."""
        from domains.settings.exchange_rate_service import ResolvedExchangeRate

        rate = ResolvedExchangeRate(
            source_currency_code="USD",
            target_currency_code="TWD",
            rate=Decimal("32.5"),
            effective_date=date.today(),
            rate_source="test",
        )

        # Should not be able to modify after creation
        with pytest.raises(Exception):  # dataclasses.FrozenInstanceError
            rate.rate = Decimal("33.0")  # type: ignore

    def test_resolved_exchange_rate_defaults(self) -> None:
        """Test ResolvedExchangeRate default values."""
        from domains.settings.exchange_rate_service import ResolvedExchangeRate

        rate = ResolvedExchangeRate(
            source_currency_code="USD",
            target_currency_code="TWD",
            rate=Decimal("32.5"),
            effective_date=date.today(),
            rate_source="test",
        )

        # is_snapshot should default to False
        assert rate.is_snapshot is False


# ============================================================
# Currency Precision Tests
# ============================================================


class TestCurrencyPrecision:
    """Tests for currency decimal precision handling."""

    def test_common_decimal_places(self) -> None:
        """Test that common decimal places are valid."""
        valid_places = [0, 1, 2, 3, 4, 5, 6]

        for places in valid_places:
            from domains.settings.schemas_currency import CurrencyCreate

            data = CurrencyCreate(
                code="TST",  # Valid 3-character code
                symbol="T",
                decimal_places=places,
            )
            assert data.decimal_places == places

    def test_invalid_decimal_places(self) -> None:
        """Test that invalid decimal places are rejected."""
        from domains.settings.schemas_currency import CurrencyCreate
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            CurrencyCreate(
                code="TEST",
                symbol="T",
                decimal_places=7,  # Max is 6
            )

        with pytest.raises(ValidationError):
            CurrencyCreate(
                code="TEST",
                symbol="T",
                decimal_places=-1,  # Min is 0
            )


# ============================================================
# Seed Default Currencies Tests
# ============================================================


class TestSeedDefaults:
    """Tests for seeding default currencies."""

    async def test_seed_produces_base_currency(self) -> None:
        """Test that seed_default_currencies marks one as base."""
        from tests.domains.orders._helpers import FakeAsyncSession

        from domains.settings.exchange_rate_service import seed_default_currencies

        tenant_id = uuid.uuid4()
        session = FakeAsyncSession()

        currencies = await seed_default_currencies(session, tenant_id, base_currency_code="TWD")
        await session.flush()

        base_currencies = [c for c in currencies if c.is_base_currency]
        assert len(base_currencies) == 1
        assert base_currencies[0].code == "TWD"

    async def test_seed_produces_multiple_currencies(self) -> None:
        """Test that seed produces multiple currencies."""
        from tests.domains.orders._helpers import FakeAsyncSession

        from domains.settings.exchange_rate_service import seed_default_currencies

        tenant_id = uuid.uuid4()
        session = FakeAsyncSession()

        currencies = await seed_default_currencies(session, tenant_id)
        await session.flush()

        assert len(currencies) >= 5  # At least 5 default currencies
        codes = [c.code for c in currencies]
        assert "TWD" in codes
        assert "USD" in codes
        assert "EUR" in codes
