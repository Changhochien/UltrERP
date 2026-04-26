"""Reusable exchange rate resolution service for Epic 25 multi-currency foundation.

This service provides deterministic exchange rate lookup with fallback behavior:
1. Same-currency identity rate (1.0)
2. Latest active exact currency pair on or before requested date
3. Validation error if no rate exists

NOTE: This service does NOT compute inverse or triangulated rates.
Rate resolution fails explicitly rather than silently inferring rates.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Literal

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.models.currency import Currency, ExchangeRate


@dataclass(frozen=True)
class ResolvedExchangeRate:
    """Result of exchange rate resolution with metadata for audit trail."""

    source_currency_code: str
    target_currency_code: str
    rate: Decimal
    effective_date: date
    rate_source: str | None
    is_snapshot: bool = False  # True if this is a frozen snapshot, not live lookup


class ExchangeRateResolutionError(Exception):
    """Raised when exchange rate cannot be resolved."""

    def __init__(
        self,
        message: str,
        source_currency: str,
        target_currency: str,
        effective_date: date | None = None,
    ):
        super().__init__(message)
        self.source_currency = source_currency
        self.target_currency = target_currency
        self.effective_date = effective_date


class CurrencyNotFoundError(ExchangeRateResolutionError):
    """Raised when a currency code is not found or inactive."""

    def __init__(self, currency_code: str, tenant_id: uuid.UUID, is_inactive: bool = False):
        status = "inactive" if is_inactive else "not found"
        message = f"Currency '{currency_code}' is {status} for tenant {tenant_id}"
        super().__init__(
            message=message,
            source_currency=currency_code,
            target_currency="",
            effective_date=None,
        )
        self.currency_code = currency_code
        self.is_inactive = is_inactive


class ExchangeRateNotFoundError(ExchangeRateResolutionError):
    """Raised when no exchange rate exists for the requested currency pair and date."""

    def __init__(
        self,
        source_currency: str,
        target_currency: str,
        effective_date: date,
        tenant_id: uuid.UUID,
    ):
        message = (
            f"No exchange rate found for {source_currency} -> {target_currency} "
            f"effective on or before {effective_date} for tenant {tenant_id}"
        )
        super().__init__(
            message=message,
            source_currency=source_currency,
            target_currency=target_currency,
            effective_date=effective_date,
        )


async def get_tenant_base_currency(
    session: AsyncSession,
    tenant_id: uuid.UUID,
) -> Currency:
    """Get the tenant's base currency.

    Args:
        session: Database session
        tenant_id: Tenant identifier

    Returns:
        The Currency record marked as base currency

    Raises:
        CurrencyNotFoundError: If no base currency is defined
    """
    result = await session.execute(
        select(Currency).where(
            Currency.tenant_id == tenant_id,
            Currency.is_base_currency == True,
        )
    )
    currency = result.scalar_one_or_none()
    if currency is None:
        raise CurrencyNotFoundError(
            currency_code="(base currency)",
            tenant_id=tenant_id,
        )
    return currency


async def resolve_exchange_rate(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    source_currency_code: str,
    target_currency_code: str,
    effective_date: date,
    *,
    allow_identity: bool = True,
) -> ResolvedExchangeRate:
    """Resolve exchange rate for a currency pair on a given effective date.

    Resolution order (deterministic fallback):
    1. Same-currency identity rate (1.0) - if allow_identity=True
    2. Latest active exact currency pair rate on or before effective_date
    3. Validation error (explicit, not silent)

    Args:
        session: Database session
        tenant_id: Tenant identifier
        source_currency_code: Source/transaction currency code (e.g., "USD")
        target_currency_code: Target/base currency code (e.g., "TWD")
        effective_date: Date for rate lookup
        allow_identity: If True, return identity rate for same currency pair

    Returns:
        ResolvedExchangeRate with rate metadata

    Raises:
        CurrencyNotFoundError: If either currency is not found or inactive
        ExchangeRateNotFoundError: If no rate exists and allow_identity=False
    """
    # Normalize currency codes to uppercase
    source_code = source_currency_code.upper().strip()
    target_code = target_currency_code.upper().strip()

    # Step 1: Identity rate for same currency
    if source_code == target_code:
        if allow_identity:
            return ResolvedExchangeRate(
                source_currency_code=source_code,
                target_currency_code=target_code,
                rate=Decimal("1.0"),
                effective_date=effective_date,
                rate_source="identity",
            )
        raise ExchangeRateNotFoundError(
            source_currency=source_code,
            target_currency=target_code,
            effective_date=effective_date,
            tenant_id=tenant_id,
        )

    # Validate source currency exists and is active
    source_result = await session.execute(
        select(Currency).where(
            Currency.tenant_id == tenant_id,
            Currency.code == source_code,
        )
    )
    source_currency = source_result.scalar_one_or_none()
    if source_currency is None:
        raise CurrencyNotFoundError(source_code, tenant_id)
    if not source_currency.is_active:
        raise CurrencyNotFoundError(source_code, tenant_id, is_inactive=True)

    # Validate target currency exists and is active
    target_result = await session.execute(
        select(Currency).where(
            Currency.tenant_id == tenant_id,
            Currency.code == target_code,
        )
    )
    target_currency = target_result.scalar_one_or_none()
    if target_currency is None:
        raise CurrencyNotFoundError(target_code, tenant_id)
    if not target_currency.is_active:
        raise CurrencyNotFoundError(target_code, tenant_id, is_inactive=True)

    # Step 2: Lookup latest active rate on or before effective_date
    result = await session.execute(
        select(ExchangeRate)
        .where(
            ExchangeRate.tenant_id == tenant_id,
            ExchangeRate.source_currency_code == source_code,
            ExchangeRate.target_currency_code == target_code,
            ExchangeRate.effective_date <= effective_date,
            ExchangeRate.is_active == True,
        )
        .order_by(ExchangeRate.effective_date.desc())
        .limit(1)
    )
    rate_record = result.scalar_one_or_none()

    if rate_record is None:
        raise ExchangeRateNotFoundError(
            source_currency=source_code,
            target_currency=target_code,
            effective_date=effective_date,
            tenant_id=tenant_id,
        )

    return ResolvedExchangeRate(
        source_currency_code=rate_record.source_currency_code,
        target_currency_code=rate_record.target_currency_code,
        rate=rate_record.rate,
        effective_date=rate_record.effective_date,
        rate_source=rate_record.rate_source,
    )


def convert_amount(
    amount: Decimal,
    rate: Decimal,
    target_precision: int = 2,
) -> Decimal:
    """Convert an amount using the given exchange rate.

    Args:
        amount: Amount in source currency
        rate: Exchange rate (source to target)
        target_precision: Decimal places for result

    Returns:
        Converted amount rounded to target precision
    """
    converted = amount * rate
    quantize_str = "0." + "0" * target_precision
    return converted.quantize(Decimal(quantize_str), rounding=ROUND_HALF_UP)


async def seed_default_currencies(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    base_currency_code: str = "TWD",
) -> list[Currency]:
    """Seed default currencies for a new tenant from legacy app_settings compatibility.

    This provides a compatibility path during rollout. Once the currency master
    is authoritative, new tenants should use the currency master directly.

    Args:
        session: Database session
        tenant_id: Tenant identifier
        base_currency_code: Code for the base currency

    Returns:
        List of created Currency records
    """
    default_currencies = [
        {"code": "TWD", "symbol": "NT$", "decimal_places": 0},
        {"code": "USD", "symbol": "$", "decimal_places": 2},
        {"code": "EUR", "symbol": "€", "decimal_places": 2},
        {"code": "JPY", "symbol": "¥", "decimal_places": 0},
        {"code": "HKD", "symbol": "HK$", "decimal_places": 2},
        {"code": "CNY", "symbol": "¥", "decimal_places": 2},
        {"code": "GBP", "symbol": "£", "decimal_places": 2},
        {"code": "AUD", "symbol": "A$", "decimal_places": 2},
        {"code": "CAD", "symbol": "C$", "decimal_places": 2},
        {"code": "SGD", "symbol": "S$", "decimal_places": 2},
    ]

    created = []
    for curr_data in default_currencies:
        currency = Currency(
            tenant_id=tenant_id,
            code=curr_data["code"],
            symbol=curr_data["symbol"],
            decimal_places=curr_data["decimal_places"],
            is_active=True,
            is_base_currency=(curr_data["code"] == base_currency_code),
        )
        session.add(currency)
        created.append(currency)

    await session.flush()
    return created
