"""Currency snapshot helpers for commercial document creation.

This module provides reusable functions for applying currency snapshots
to commercial documents (quotations, orders, invoices, payments, etc.)
during document creation.

Story 25-2: Currency-Aware Commercial Documents
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from domains.settings.exchange_rate_service import (
    ExchangeRateNotFoundError,
    get_tenant_base_currency,
    resolve_exchange_rate,
)
from domains.settings.fx_conversion import (
    ConversionResult,
    calculate_base_amounts,
    convert_amount,
    get_currency_precision,
    round_for_currency,
)

if TYPE_CHECKING:
    from common.models.currency import Currency


class CurrencyMismatchError(Exception):
    """Raised when currency allocation rules are violated."""

    def __init__(self, payment_currency: str, invoice_currency: str):
        self.payment_currency = payment_currency
        self.invoice_currency = invoice_currency
        super().__init__(
            f"Currency mismatch: payment currency '{payment_currency}' "
            f"does not match invoice currency '{invoice_currency}'. "
            "Cross-currency allocation requires a later finance story."
        )


class DocumentCurrencySnapshot:
    """Manages currency snapshot state for document creation.

    This class provides a clean interface for applying currency snapshots
    to document headers and lines, with proper base currency fallback.
    """

    def __init__(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        transaction_currency: str,
        transaction_date: date,
    ):
        self.session = session
        self.tenant_id = tenant_id
        self.transaction_currency = transaction_currency.upper()
        self.transaction_date = transaction_date

        # These will be set during resolution
        self._base_currency: Currency | None = None
        self._conversion_result: ConversionResult | None = None
        self._base_precision: int = 2

    async def resolve(self) -> ConversionResult:
        """Resolve the conversion rate for this document.

        Returns:
            ConversionResult with rate metadata

        Raises:
            ExchangeRateNotFoundError: If no rate exists
            CurrencyNotFoundError: If currency not found
        """
        # Get base currency
        self._base_currency = await get_tenant_base_currency(
            self.session, self.tenant_id
        )

        # Check if same currency (identity rate)
        if self.transaction_currency == self._base_currency.code:
            from domains.settings.exchange_rate_service import ResolvedExchangeRate

            self._conversion_result = ConversionResult(
                original_amount=Decimal("1.0"),
                converted_amount=Decimal("1.0"),
                rate=Decimal("1.0"),
                source_currency=self.transaction_currency,
                target_currency=self._base_currency.code,
                effective_date=self.transaction_date,
                rate_source="identity",
                precision_used=self._base_currency.decimal_places,
            )
            self._base_precision = self._base_currency.decimal_places
            return self._conversion_result

        # Resolve exchange rate
        resolved = await resolve_exchange_rate(
            self.session,
            self.tenant_id,
            self.transaction_currency,
            self._base_currency.code,
            self.transaction_date,
        )

        # Get target precision
        self._base_precision = self._base_currency.decimal_places

        # Convert with full precision
        converted = convert_amount(Decimal("1.0"), resolved.rate, self._base_precision)

        self._conversion_result = ConversionResult(
            original_amount=Decimal("1.0"),
            converted_amount=converted,
            rate=resolved.rate,
            source_currency=resolved.source_currency_code,
            target_currency=resolved.target_currency_code,
            effective_date=resolved.effective_date,
            rate_source=resolved.rate_source,
            precision_used=self._base_precision,
        )
        return self._conversion_result

    @property
    def rate(self) -> Decimal:
        """Get the conversion rate."""
        if self._conversion_result is None:
            raise RuntimeError("Must call resolve() before accessing rate")
        return self._conversion_result.rate

    @property
    def effective_date(self) -> date:
        """Get the effective date for the rate."""
        if self._conversion_result is None:
            raise RuntimeError("Must call resolve() before accessing effective_date")
        return self._conversion_result.effective_date

    @property
    def rate_source(self) -> str | None:
        """Get the rate source."""
        if self._conversion_result is None:
            raise RuntimeError("Must call resolve() before accessing rate_source")
        return self._conversion_result.rate_source

    @property
    def base_currency(self) -> str:
        """Get the base currency code."""
        if self._base_currency is None:
            raise RuntimeError("Must call resolve() before accessing base_currency")
        return self._base_currency.code

    @property
    def is_same_currency(self) -> bool:
        """Check if transaction and base currencies are the same."""
        return self.transaction_currency == self.base_currency

    def calculate_base_amounts(
        self,
        subtotal: Decimal,
        tax_amount: Decimal,
        total: Decimal,
    ) -> tuple[Decimal, Decimal, Decimal, Decimal]:
        """Calculate base currency amounts from transaction amounts.

        Args:
            subtotal: Transaction subtotal
            tax_amount: Transaction tax amount
            total: Transaction total

        Returns:
            Tuple of (base_subtotal, base_tax, base_total, base_discount)
            base_discount is computed as base_subtotal + base_tax - base_total
        """
        if self.is_same_currency:
            # Identity conversion - base amounts equal transaction amounts
            discount = subtotal + tax_amount - total
            return subtotal, tax_amount, total, discount

        base_subtotal, base_tax, base_total = calculate_base_amounts(
            subtotal, tax_amount, total, self.rate, self._base_precision
        )

        # Calculate discount in base currency
        base_discount = base_subtotal + base_tax - base_total

        return base_subtotal, base_tax, base_total, base_discount

    def calculate_line_base_amounts(
        self,
        unit_price: Decimal,
        subtotal: Decimal,
        tax_amount: Decimal,
        total: Decimal,
    ) -> tuple[Decimal, Decimal, Decimal, Decimal]:
        """Calculate base currency amounts for a line item.

        Args:
            unit_price: Transaction unit price
            subtotal: Line subtotal
            tax_amount: Line tax amount
            total: Line total amount

        Returns:
            Tuple of (base_unit_price, base_subtotal, base_tax, base_total)
        """
        if self.is_same_currency:
            return unit_price, subtotal, tax_amount, total

        # Convert unit price
        base_unit_price = convert_amount(
            unit_price, self.rate, self._base_precision
        )

        base_subtotal, base_tax, base_total = calculate_base_amounts(
            subtotal, tax_amount, total, self.rate, self._base_precision
        )

        return base_unit_price, base_subtotal, base_tax, base_total


async def get_default_currency(session: AsyncSession, tenant_id: uuid.UUID) -> str:
    """Get the default currency code for a tenant.

    Falls back to "TWD" if no base currency is defined.

    Args:
        session: Database session
        tenant_id: Tenant identifier

    Returns:
        Base currency code
    """
    try:
        base_currency = await get_tenant_base_currency(session, tenant_id)
        return base_currency.code
    except Exception:
        return "TWD"


def validate_same_currency_allocation(
    payment_currency: str,
    invoice_currency: str,
) -> None:
    """Validate that payment and invoice currencies match.

    Per Story 25-2 AC: Payment allocations must remain same-currency
    with the linked invoice until a later finance story introduces
    cross-currency allocation rules.

    Args:
        payment_currency: Payment currency code
        invoice_currency: Invoice currency code

    Raises:
        CurrencyMismatchError: If currencies don't match
    """
    if payment_currency.upper() != invoice_currency.upper():
        raise CurrencyMismatchError(payment_currency, invoice_currency)


def get_applied_rate_source_label(
    source: str | None,
    is_identity: bool = False,
    is_manual: bool = False,
) -> str:
    """Get a human-readable label for the applied rate source.

    Args:
        source: Rate source from exchange rate record
        is_identity: True if this is an identity rate
        is_manual: True if user manually specified rate

    Returns:
        Human-readable source label
    """
    if is_identity:
        return "identity"
    if is_manual:
        return "manual"
    if source:
        return source
    return "unknown"
