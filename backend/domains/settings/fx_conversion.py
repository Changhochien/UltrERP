"""Shared FX conversion utilities for Epic 25 multi-currency support.

This module provides centralized currency conversion and rounding rules
to ensure consistent handling across all commercial documents.

Key principles:
- Store both transaction amounts and base amounts
- Use currency-specific precision for rounding
- Validate conversions to prevent drift
- Expose applied rate metadata for audit
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.models.currency import Currency, ExchangeRate

if TYPE_CHECKING:
    from domains.settings.exchange_rate_service import ResolvedExchangeRate


@dataclass(frozen=True)
class CurrencyPrecision:
    """Currency-specific precision configuration."""

    code: str
    decimal_places: int
    symbol: str
    is_base_currency: bool


@dataclass
class ConversionResult:
    """Result of a currency conversion with full audit trail."""

    original_amount: Decimal
    converted_amount: Decimal
    rate: Decimal
    source_currency: str
    target_currency: str
    effective_date: date
    rate_source: str | None
    precision_used: int

    def to_snapshot(self) -> dict:
        """Convert to snapshot dict for storing on documents."""
        return {
            "rate": str(self.rate),
            "effective_date": self.effective_date.isoformat(),
            "source": self.rate_source,
            "source_currency": self.source_currency,
            "target_currency": self.target_currency,
        }


async def get_currency_precision(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    currency_code: str,
) -> CurrencyPrecision:
    """Get currency precision configuration.

    Args:
        session: Database session
        tenant_id: Tenant identifier
        currency_code: ISO 4217 currency code

    Returns:
        CurrencyPrecision with decimal places and symbol

    Raises:
        ValueError: If currency not found
    """
    result = await session.execute(
        select(Currency).where(
            Currency.tenant_id == tenant_id,
            Currency.code == currency_code.upper(),
        )
    )
    currency = result.scalar_one_or_none()
    if currency is None:
        raise ValueError(f"Currency '{currency_code}' not found for tenant {tenant_id}")

    return CurrencyPrecision(
        code=currency.code,
        decimal_places=currency.decimal_places,
        symbol=currency.symbol,
        is_base_currency=currency.is_base_currency,
    )


def round_for_currency(amount: Decimal, precision: int) -> Decimal:
    """Round an amount to the specified currency precision.

    Uses ROUND_HALF_UP rounding mode for consistency with financial calculations.

    Args:
        amount: Amount to round
        precision: Number of decimal places

    Returns:
        Rounded amount
    """
    quantize_str = "0." + "0" * precision
    return amount.quantize(Decimal(quantize_str), rounding=ROUND_HALF_UP)


def convert_amount(
    amount: Decimal,
    rate: Decimal,
    target_precision: int = 2,
) -> Decimal:
    """Convert an amount using exchange rate and round to target precision.

    Args:
        amount: Amount in source currency
        rate: Exchange rate (source to target)
        target_precision: Target currency decimal places (default: 2)

    Returns:
        Converted and rounded amount
    """
    converted = amount * rate
    return round_for_currency(converted, target_precision)


def convert_and_round(
    amount: Decimal,
    rate: Decimal,
    target_precision: int,
) -> Decimal:
    """Convert an amount using exchange rate and round to target precision.

    Args:
        amount: Amount in source currency
        rate: Exchange rate (source to target)
        target_precision: Target currency decimal places

    Returns:
        Converted and rounded amount
    """
    converted = amount * rate
    return round_for_currency(converted, target_precision)


def convert_amount_with_precision(
    amount: Decimal,
    rate: Decimal,
    source_precision: int,
    target_precision: int,
) -> tuple[Decimal, Decimal]:
    """Convert amount with intermediate precision for audit.

    First converts with full precision (source_precision + rate_precision),
    then rounds to target precision. This allows validation of rounding drift.

    Args:
        amount: Amount in source currency
        rate: Exchange rate
        source_precision: Source currency decimal places
        target_precision: Target currency decimal places

    Returns:
        Tuple of (full_precision_result, rounded_result)
    """
    # Use higher precision during calculation to avoid rounding errors
    # FX rates typically have 6+ decimal places
    intermediate_precision = max(source_precision, target_precision, 6)
    full_precision = round_for_currency(amount * rate, intermediate_precision)
    rounded = round_for_currency(full_precision, target_precision)
    return full_precision, rounded


def calculate_base_amounts(
    subtotal: Decimal,
    tax_amount: Decimal,
    total: Decimal,
    rate: Decimal,
    target_precision: int,
) -> tuple[Decimal, Decimal, Decimal]:
    """Calculate base currency amounts from transaction amounts.

    Args:
        subtotal: Transaction subtotal
        tax_amount: Transaction tax amount
        total: Transaction total
        rate: Exchange rate (transaction to base)
        target_precision: Base currency decimal places

    Returns:
        Tuple of (base_subtotal, base_tax, base_total)
    """
    base_subtotal = convert_and_round(subtotal, rate, target_precision)
    base_tax = convert_and_round(tax_amount, rate, target_precision)
    base_total = convert_and_round(total, rate, target_precision)
    return base_subtotal, base_tax, base_total


def validate_line_header_consistency(
    lines_base_total: Decimal,
    header_base_total: Decimal,
    precision: int,
    tolerance: Decimal | None = None,
) -> tuple[bool, str | None]:
    """Validate that line totals match header totals.

    Args:
        lines_base_total: Sum of line base totals
        header_base_total: Header base total
        precision: Currency precision for tolerance calculation
        tolerance: Optional custom tolerance (defaults to 0.01)

    Returns:
        Tuple of (is_valid, error_message)
    """
    if tolerance is None:
        tolerance = Decimal("0.01")

    diff = abs(lines_base_total - header_base_total)
    if diff > tolerance:
        return False, (
            f"Line-header base total mismatch: lines={lines_base_total}, "
            f"header={header_base_total}, diff={diff} exceeds tolerance {tolerance}"
        )
    return True, None


def validate_conversion_drift(
    original_total: Decimal,
    rate: Decimal,
    stored_base_total: Decimal,
    target_precision: int,
    tolerance: Decimal | None = None,
) -> tuple[bool, str | None]:
    """Validate that a stored base total matches the computed conversion.

    This prevents silent drift between stored and computed values.

    Args:
        original_total: Original transaction total
        rate: Applied conversion rate
        stored_base_total: Stored base total
        target_precision: Base currency precision
        tolerance: Optional custom tolerance

    Returns:
        Tuple of (is_valid, error_message)
    """
    if tolerance is None:
        tolerance = Decimal("0.02")  # Slightly higher for conversion drift

    computed_base = convert_and_round(original_total, rate, target_precision)
    diff = abs(computed_base - stored_base_total)

    if diff > tolerance:
        return False, (
            f"Conversion drift detected: computed_base={computed_base}, "
            f"stored_base={stored_base_total}, diff={diff} exceeds tolerance {tolerance}. "
            f"Rate={rate}, original_total={original_total}"
        )
    return True, None


@dataclass
class MoneyAmount:
    """Represents an amount with both transaction and base currency values."""

    transaction_amount: Decimal
    transaction_currency: str
    base_amount: Decimal
    base_currency: str
    conversion_rate: Decimal
    effective_date: date
    rate_source: str | None

    @classmethod
    def from_conversion(
        cls,
        amount: Decimal,
        currency: str,
        result: ConversionResult,
    ) -> MoneyAmount:
        """Create from a ConversionResult."""
        return cls(
            transaction_amount=amount,
            transaction_currency=currency,
            base_amount=result.converted_amount,
            base_currency=result.target_currency,
            conversion_rate=result.rate,
            effective_date=result.effective_date,
            rate_source=result.rate_source,
        )

    def to_display_dict(self, include_rate: bool = True) -> dict:
        """Convert to dictionary for API response."""
        result = {
            "transaction_amount": str(self.transaction_amount),
            "transaction_currency": self.transaction_currency,
            "base_amount": str(self.base_amount),
            "base_currency": self.base_currency,
        }
        if include_rate:
            result["conversion_rate"] = str(self.conversion_rate)
            result["effective_date"] = self.effective_date.isoformat()
            result["rate_source"] = self.rate_source
        return result


def format_money(amount: Decimal, currency_code: str, symbol: str, precision: int) -> str:
    """Format a money amount for display.

    Args:
        amount: Amount to format
        currency_code: ISO 4217 currency code
        symbol: Currency symbol
        precision: Decimal places

    Returns:
        Formatted string like "NT$1,234.00"
    """
    formatted_number = f"{amount:,.{precision}f}"
    return f"{symbol}{formatted_number}"


def parse_money(value: str | Decimal) -> Decimal:
    """Parse a money string or Decimal to Decimal.

    Args:
        value: String like "1,234.00" or Decimal

    Returns:
        Parsed Decimal
    """
    if isinstance(value, Decimal):
        return value
    # Remove currency symbols and commas
    cleaned = value.replace(",", "").strip()
    # Handle parentheses for negative (accounting format)
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = "-" + cleaned[1:-1]
    return Decimal(cleaned)
