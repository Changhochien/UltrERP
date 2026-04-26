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
from decimal import ROUND_HALF_UP, Decimal
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.models.currency import Currency, ExchangeRate
from domains.settings.models import AppSetting


DEFAULT_CURRENCY_DEFINITIONS: dict[str, dict[str, int | str]] = {
    "TWD": {"symbol": "NT$", "decimal_places": 0},
    "USD": {"symbol": "$", "decimal_places": 2},
    "EUR": {"symbol": "€", "decimal_places": 2},
    "JPY": {"symbol": "¥", "decimal_places": 0},
    "HKD": {"symbol": "HK$", "decimal_places": 2},
    "CNY": {"symbol": "¥", "decimal_places": 2},
    "GBP": {"symbol": "£", "decimal_places": 2},
    "AUD": {"symbol": "A$", "decimal_places": 2},
    "CAD": {"symbol": "C$", "decimal_places": 2},
    "SGD": {"symbol": "S$", "decimal_places": 2},
}
_CURRENCY_SETTING_PATTERN = re.compile(r"^currency\.([^.]+)\.(symbol|decimal_places)$")


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
    await ensure_tenant_currencies_seeded(session, tenant_id)

    result = await session.execute(
        select(Currency).where(
            Currency.tenant_id == tenant_id,
            Currency.is_base_currency,
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
    await ensure_tenant_currencies_seeded(session, tenant_id)

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
            ExchangeRate.is_active,
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


def _build_currency_seed_entries(
    settings_rows: list[AppSetting],
    *,
    fallback_base_currency_code: str = "TWD",
) -> tuple[str, list[dict[str, int | str]]]:
    definitions = {
        code: values.copy() for code, values in DEFAULT_CURRENCY_DEFINITIONS.items()
    }
    base_currency_code = fallback_base_currency_code.upper().strip()

    for row in settings_rows:
        if row.key == "currency.default":
            candidate = str(row.value).upper().strip()
            if candidate:
                base_currency_code = candidate
                definitions.setdefault(candidate, {"symbol": candidate, "decimal_places": 2})
            continue

        match = _CURRENCY_SETTING_PATTERN.match(row.key)
        if match is None:
            continue

        code, field_name = match.groups()
        normalized_code = code.upper().strip()
        entry = definitions.setdefault(
            normalized_code,
            {"symbol": normalized_code, "decimal_places": 2},
        )
        if field_name == "symbol":
            symbol = str(row.value).strip()
            entry["symbol"] = symbol or normalized_code
            continue

        try:
            decimal_places = int(str(row.value).strip())
        except ValueError:
            continue
        entry["decimal_places"] = min(max(decimal_places, 0), 6)

    ordered_codes = sorted(definitions)
    return base_currency_code, [
        {
            "code": code,
            "symbol": str(definitions[code]["symbol"]),
            "decimal_places": int(definitions[code]["decimal_places"]),
        }
        for code in ordered_codes
    ]


async def ensure_tenant_currencies_seeded(
    session: AsyncSession,
    tenant_id: uuid.UUID,
) -> list[Currency]:
    existing = await session.execute(
        select(Currency.id).where(Currency.tenant_id == tenant_id).limit(1)
    )
    if existing.scalar_one_or_none() is not None:
        return []

    settings_result = await session.execute(
        select(AppSetting).where(AppSetting.key.like("currency.%"))
    )
    settings_rows = list(settings_result.scalars().all())
    base_currency_code, seed_definitions = _build_currency_seed_entries(settings_rows)
    return await seed_default_currencies(
        session,
        tenant_id,
        base_currency_code=base_currency_code,
        seed_definitions=seed_definitions,
    )


async def seed_default_currencies(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    base_currency_code: str = "TWD",
    *,
    seed_definitions: list[dict[str, int | str]] | None = None,
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
    default_currencies = seed_definitions or [
        {
            "code": code,
            "symbol": str(values["symbol"]),
            "decimal_places": int(values["decimal_places"]),
        }
        for code, values in sorted(DEFAULT_CURRENCY_DEFINITIONS.items())
    ]

    created = []
    for curr_data in default_currencies:
        currency_code = str(curr_data["code"]).upper().strip()
        currency = Currency(
            tenant_id=tenant_id,
            code=currency_code,
            symbol=str(curr_data["symbol"]),
            decimal_places=int(curr_data["decimal_places"]),
            is_active=True,
            is_base_currency=(currency_code == base_currency_code.upper().strip()),
        )
        session.add(currency)
        created.append(currency)

    await session.flush()
    return created
