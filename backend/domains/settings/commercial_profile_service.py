"""Commercial profile service for Epic 25.

This module provides:
- Commercial profile default application
- Source metadata tracking
- Deterministic fallback ordering
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.models.currency import Currency
from common.models.payment_terms import PaymentTermsTemplate
from domains.customers.models import Customer
from domains.settings.exchange_rate_service import get_tenant_base_currency

if TYPE_CHECKING:
    from common.models.supplier import Supplier


class CommercialValueSource(str, Enum):
    """Source of a commercial value on a document."""

    SOURCE_DOCUMENT = "source_document"
    PROFILE_DEFAULT = "profile_default"
    LEGACY_COMPATIBILITY = "legacy_compatibility"
    MANUAL_OVERRIDE = "manual_override"


@dataclass
class CommercialDefaults:
    """Commercial defaults for a document."""

    currency_code: str | None
    currency_source: CommercialValueSource
    payment_terms_code: str | None
    payment_terms_template_id: uuid.UUID | None
    payment_terms_source: CommercialValueSource


@dataclass
class CurrencySnapshot:
    """Currency snapshot for a document."""

    currency_code: str
    conversion_rate: Decimal
    effective_date: date
    rate_source: str | None
    source: CommercialValueSource


async def get_customer_commercial_defaults(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    customer_id: uuid.UUID,
) -> CommercialDefaults:
    """Get commercial defaults for a customer.

    Args:
        session: Database session
        tenant_id: Tenant identifier
        customer_id: Customer identifier

    Returns:
        CommercialDefaults with currency and payment term defaults
    """
    result = await session.execute(
        select(Customer).where(
            Customer.id == customer_id,
            Customer.tenant_id == tenant_id,
        )
    )
    customer = result.scalar_one_or_none()

    if customer is None:
        return CommercialDefaults(
            currency_code=None,
            currency_source=CommercialValueSource.LEGACY_COMPATIBILITY,
            payment_terms_code=None,
            payment_terms_template_id=None,
            payment_terms_source=CommercialValueSource.LEGACY_COMPATIBILITY,
        )

    return CommercialDefaults(
        currency_code=customer.default_currency_code,
        currency_source=CommercialValueSource.PROFILE_DEFAULT,
        payment_terms_code=None,  # Legacy code not stored on customer
        payment_terms_template_id=customer.payment_terms_template_id,
        payment_terms_source=CommercialValueSource.PROFILE_DEFAULT,
    )


async def get_supplier_commercial_defaults(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    supplier_id: uuid.UUID,
) -> CommercialDefaults:
    """Get commercial defaults for a supplier.

    Args:
        session: Database session
        tenant_id: Tenant identifier
        supplier_id: Supplier identifier

    Returns:
        CommercialDefaults with currency and payment term defaults
    """
    result = await session.execute(
        select(Supplier).where(
            Supplier.id == supplier_id,
            Supplier.tenant_id == tenant_id,
        )
    )
    supplier = result.scalar_one_or_none()

    if supplier is None:
        return CommercialDefaults(
            currency_code=None,
            currency_source=CommercialValueSource.LEGACY_COMPATIBILITY,
            payment_terms_code=None,
            payment_terms_template_id=None,
            payment_terms_source=CommercialValueSource.LEGACY_COMPATIBILITY,
        )

    return CommercialDefaults(
        currency_code=supplier.default_currency_code,
        currency_source=CommercialValueSource.PROFILE_DEFAULT,
        payment_terms_code=None,
        payment_terms_template_id=supplier.payment_terms_template_id,
        payment_terms_source=CommercialValueSource.PROFILE_DEFAULT,
    )


async def resolve_document_currency(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    customer_id: uuid.UUID | None = None,
    supplier_id: uuid.UUID | None = None,
    explicit_currency: str | None = None,
    source_document_currency: str | None = None,
    effective_date: date | None = None,
) -> CurrencySnapshot:
    """Resolve currency for a document with deterministic fallback.

    Fallback order:
    1. Source document currency (if present)
    2. Party profile default (customer or supplier)
    3. Tenant base currency (fallback)

    Args:
        session: Database session
        tenant_id: Tenant identifier
        customer_id: Customer identifier (for sales documents)
        supplier_id: Supplier identifier (for procurement documents)
        explicit_currency: Explicitly set currency code
        source_document_currency: Currency from source document
        effective_date: Date used for exchange-rate lookup

    Returns:
        CurrencySnapshot with resolved currency and metadata
    """
    source: CommercialValueSource
    resolved_currency: str

    # Step 1: Check source document
    if source_document_currency is not None:
        resolved_currency = source_document_currency.upper().strip()
        source = CommercialValueSource.SOURCE_DOCUMENT

    # Step 2: Check explicit/manual override
    elif explicit_currency is not None:
        resolved_currency = explicit_currency.upper().strip()
        source = CommercialValueSource.MANUAL_OVERRIDE

    # Step 3: Check party profile
    elif customer_id is not None:
        customer_defaults = await get_customer_commercial_defaults(
            session, tenant_id, customer_id
        )
        if customer_defaults.currency_code is not None:
            resolved_currency = customer_defaults.currency_code.upper().strip()
            source = CommercialValueSource.PROFILE_DEFAULT
        elif supplier_id is not None:
            supplier_defaults = await get_supplier_commercial_defaults(
                session, tenant_id, supplier_id
            )
            if supplier_defaults.currency_code is not None:
                resolved_currency = supplier_defaults.currency_code.upper().strip()
                source = CommercialValueSource.PROFILE_DEFAULT
            else:
                # Step 4: Fall back to tenant base
                base = await get_tenant_base_currency(session, tenant_id)
                resolved_currency = base.code
                source = CommercialValueSource.LEGACY_COMPATIBILITY
        else:
            # Fall back to tenant base
            base = await get_tenant_base_currency(session, tenant_id)
            resolved_currency = base.code
            source = CommercialValueSource.LEGACY_COMPATIBILITY

    elif supplier_id is not None:
        supplier_defaults = await get_supplier_commercial_defaults(
            session, tenant_id, supplier_id
        )
        if supplier_defaults.currency_code is not None:
            resolved_currency = supplier_defaults.currency_code.upper().strip()
            source = CommercialValueSource.PROFILE_DEFAULT
        else:
            # Fall back to tenant base
            base = await get_tenant_base_currency(session, tenant_id)
            resolved_currency = base.code
            source = CommercialValueSource.LEGACY_COMPATIBILITY

    else:
        # Fall back to tenant base
        base = await get_tenant_base_currency(session, tenant_id)
        resolved_currency = base.code
        source = CommercialValueSource.LEGACY_COMPATIBILITY

    # Get conversion rate
    from domains.settings.exchange_rate_service import resolve_exchange_rate

    base = await get_tenant_base_currency(session, tenant_id)
    lookup_date = effective_date or date.today()

    if resolved_currency == base.code:
        # Identity rate
        rate = Decimal("1.0")
        resolved_effective_date = lookup_date
        rate_source = "identity"
    else:
        resolved_rate = await resolve_exchange_rate(
            session,
            tenant_id,
            resolved_currency,
            base.code,
            lookup_date,
        )
        rate = resolved_rate.rate
        resolved_effective_date = resolved_rate.effective_date
        rate_source = resolved_rate.rate_source

    return CurrencySnapshot(
        currency_code=resolved_currency,
        conversion_rate=rate,
        effective_date=resolved_effective_date,
        rate_source=rate_source,
        source=source,
    )


def determine_payment_terms_source(
    explicit_terms_code: str | None,
    explicit_template_id: uuid.UUID | None,
    source_document_terms_code: str | None,
    source_document_template_id: uuid.UUID | None,
    profile_template_id: uuid.UUID | None,
    legacy_terms_code: str | None,
) -> tuple[str | None, uuid.UUID | None, CommercialValueSource]:
    """Determine payment terms with deterministic fallback.

    Fallback order:
    1. Source document template/terms (if present)
    2. Explicit/manual override (template or code)
    3. Party profile template
    4. Legacy compatibility (tenant default)

    Args:
        explicit_terms_code: Explicitly set legacy term code
        explicit_template_id: Explicitly set template ID
        source_document_terms_code: Terms code from source document
        source_document_template_id: Template ID from source document
        profile_template_id: Template ID from party profile
        legacy_terms_code: Legacy term code fallback

    Returns:
        Tuple of (terms_code, template_id, source)
    """
    # Step 1: Source document
    if source_document_template_id is not None:
        return (None, source_document_template_id, CommercialValueSource.SOURCE_DOCUMENT)
    if source_document_terms_code is not None:
        return (source_document_terms_code, None, CommercialValueSource.SOURCE_DOCUMENT)

    # Step 2: Explicit/manual override
    if explicit_template_id is not None:
        return (None, explicit_template_id, CommercialValueSource.MANUAL_OVERRIDE)
    if explicit_terms_code is not None:
        return (explicit_terms_code, None, CommercialValueSource.MANUAL_OVERRIDE)

    # Step 3: Party profile
    if profile_template_id is not None:
        return (None, profile_template_id, CommercialValueSource.PROFILE_DEFAULT)

    # Step 4: Legacy fallback
    if legacy_terms_code is not None:
        return (legacy_terms_code, None, CommercialValueSource.LEGACY_COMPATIBILITY)

    return (None, None, CommercialValueSource.LEGACY_COMPATIBILITY)
