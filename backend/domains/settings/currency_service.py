"""Currency management service for Epic 25 multi-currency foundation.

This service handles CRUD operations for currency masters and provides
helpers for tenant-scoped currency management.
"""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.models.currency import Currency, ExchangeRate
from domains.settings.exchange_rate_service import (
    CurrencyNotFoundError,
    ExchangeRateNotFoundError,
    ensure_tenant_currencies_seeded,
    resolve_exchange_rate,
)
from domains.settings.schemas_currency import (
    ConversionRequest,
    ConversionResponse,
    CurrencyCreate,
    CurrencyListResponse,
    CurrencyUpdate,
    ExchangeRateCreate,
    ExchangeRateListResponse,
    ExchangeRateLookupRequest,
    ExchangeRateLookupResponse,
    ExchangeRateUpdate,
)

# ============================================================
# Currency Service
# ============================================================


async def list_currencies(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    page: int = 1,
    page_size: int = 20,
    active_only: bool = False,
) -> CurrencyListResponse:
    """List currencies for a tenant with pagination.

    Args:
        session: Database session
        tenant_id: Tenant identifier
        page: Page number (1-indexed)
        page_size: Items per page
        active_only: Filter to active currencies only

    Returns:
        CurrencyListResponse with paginated items
    """
    await ensure_tenant_currencies_seeded(session, tenant_id)

    query = select(Currency).where(Currency.tenant_id == tenant_id)

    if active_only:
        query = query.where(Currency.is_active)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar_one()

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.order_by(Currency.code).offset(offset).limit(page_size)

    result = await session.execute(query)
    currencies = list(result.scalars().all())

    return CurrencyListResponse(
        items=currencies,
        total=total,
        page=page,
        page_size=page_size,
    )


async def get_currency(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    currency_id: uuid.UUID,
) -> Currency:
    """Get a single currency by ID.

    Args:
        session: Database session
        tenant_id: Tenant identifier
        currency_id: Currency identifier

    Returns:
        Currency record

    Raises:
        CurrencyNotFoundError: If currency not found or belongs to different tenant
    """
    result = await session.execute(
        select(Currency).where(
            Currency.id == currency_id,
            Currency.tenant_id == tenant_id,
        )
    )
    currency = result.scalar_one_or_none()
    if currency is None:
        raise CurrencyNotFoundError(currency_code="(by ID)", tenant_id=tenant_id)
    return currency


async def get_currency_by_code(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    code: str,
) -> Currency:
    """Get a single currency by code.

    Args:
        session: Database session
        tenant_id: Tenant identifier
        code: Currency code

    Returns:
        Currency record

    Raises:
        CurrencyNotFoundError: If currency not found
    """
    await ensure_tenant_currencies_seeded(session, tenant_id)

    result = await session.execute(
        select(Currency).where(
            Currency.tenant_id == tenant_id,
            Currency.code == code.upper().strip(),
        )
    )
    currency = result.scalar_one_or_none()
    if currency is None:
        raise CurrencyNotFoundError(currency_code=code, tenant_id=tenant_id)
    return currency


async def create_currency(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    data: CurrencyCreate,
) -> Currency:
    """Create a new currency.

    Args:
        session: Database session
        tenant_id: Tenant identifier
        data: Currency creation data

    Returns:
        Created Currency record

    Raises:
        ValueError: If currency code already exists or base currency conflict
    """
    code = data.code.upper().strip()

    # Check for duplicate code
    existing = await session.execute(
        select(Currency).where(
            Currency.tenant_id == tenant_id,
            Currency.code == code,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise ValueError(f"Currency with code '{code}' already exists")

    # If setting as base, unset any existing base currency
    if data.is_base_currency:
        existing_base = await session.execute(
            select(Currency).where(
                Currency.tenant_id == tenant_id,
                Currency.is_base_currency,
            )
        )
        for base_curr in existing_base.scalars().all():
            base_curr.is_base_currency = False

    currency = Currency(
        tenant_id=tenant_id,
        code=code,
        symbol=data.symbol,
        decimal_places=data.decimal_places,
        is_active=data.is_active,
        is_base_currency=data.is_base_currency,
    )
    session.add(currency)
    await session.flush()
    return currency


async def update_currency(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    currency_id: uuid.UUID,
    data: CurrencyUpdate,
) -> Currency:
    """Update an existing currency.

    Args:
        session: Database session
        tenant_id: Tenant identifier
        currency_id: Currency identifier
        data: Update data

    Returns:
        Updated Currency record

    Raises:
        CurrencyNotFoundError: If currency not found
        ValueError: If base currency conflict
    """
    currency = await get_currency(session, tenant_id, currency_id)

    if data.symbol is not None:
        currency.symbol = data.symbol.strip()
    if data.decimal_places is not None:
        currency.decimal_places = data.decimal_places
    if data.is_active is not None:
        # Cannot deactivate base currency
        if not data.is_active and currency.is_base_currency:
            raise ValueError("Cannot deactivate base currency")
        currency.is_active = data.is_active

    await session.flush()
    return currency


async def set_base_currency(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    currency_id: uuid.UUID,
) -> Currency:
    """Set a currency as the tenant's base currency.

    Args:
        session: Database session
        tenant_id: Tenant identifier
        currency_id: Currency identifier to set as base

    Returns:
        Updated Currency record

    Raises:
        CurrencyNotFoundError: If currency not found or inactive
    """
    currency = await get_currency(session, tenant_id, currency_id)

    if not currency.is_active:
        raise ValueError("Cannot set inactive currency as base")

    # Unset current base
    result = await session.execute(
        select(Currency).where(
            Currency.tenant_id == tenant_id,
            Currency.is_base_currency,
        )
    )
    for curr in result.scalars().all():
        curr.is_base_currency = False

    # Set new base
    currency.is_base_currency = True
    await session.flush()
    return currency


# ============================================================
# Exchange Rate Service
# ============================================================


async def list_exchange_rates(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    page: int = 1,
    page_size: int = 20,
    source_currency: str | None = None,
    target_currency: str | None = None,
    active_only: bool = True,
) -> ExchangeRateListResponse:
    """List exchange rates with filtering and pagination.

    Args:
        session: Database session
        tenant_id: Tenant identifier
        page: Page number
        page_size: Items per page
        source_currency: Filter by source currency
        target_currency: Filter by target currency
        active_only: Filter to active rates only

    Returns:
        ExchangeRateListResponse with paginated items
    """
    query = select(ExchangeRate).where(ExchangeRate.tenant_id == tenant_id)

    if source_currency:
        query = query.where(ExchangeRate.source_currency_code == source_currency.upper())
    if target_currency:
        query = query.where(ExchangeRate.target_currency_code == target_currency.upper())
    if active_only:
        query = query.where(ExchangeRate.is_active)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar_one()

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.order_by(
        ExchangeRate.source_currency_code,
        ExchangeRate.target_currency_code,
        ExchangeRate.effective_date.desc(),
    ).offset(offset).limit(page_size)

    result = await session.execute(query)
    rates = list(result.scalars().all())

    return ExchangeRateListResponse(
        items=rates,
        total=total,
        page=page,
        page_size=page_size,
    )


async def create_exchange_rate(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    data: ExchangeRateCreate,
) -> ExchangeRate:
    """Create a new exchange rate.

    Args:
        session: Database session
        tenant_id: Tenant identifier
        data: Exchange rate creation data

    Returns:
        Created ExchangeRate record

    Raises:
        ValueError: If rate already exists for this date or currencies invalid
    """
    normalized_source = data.source_currency_code.upper().strip()
    normalized_target = data.target_currency_code.upper().strip()

    if normalized_source == normalized_target:
        raise ValueError("Cannot create an exchange rate for the same currency pair")

    # Validate currencies exist
    try:
        source_currency = await get_currency_by_code(session, tenant_id, normalized_source)
        target_currency = await get_currency_by_code(session, tenant_id, normalized_target)
    except CurrencyNotFoundError as e:
        raise ValueError(f"Invalid currency: {e.currency_code}") from e

    if not source_currency.is_active:
        raise ValueError(f"Currency '{normalized_source}' is inactive")
    if not target_currency.is_active:
        raise ValueError(f"Currency '{normalized_target}' is inactive")

    # Check for duplicate effective date
    existing = await session.execute(
        select(ExchangeRate).where(
            ExchangeRate.tenant_id == tenant_id,
            ExchangeRate.source_currency_code == normalized_source,
            ExchangeRate.target_currency_code == normalized_target,
            ExchangeRate.effective_date == data.effective_date,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise ValueError(
            f"Exchange rate for {normalized_source} -> {normalized_target} "
            f"already exists for {data.effective_date}"
        )

    rate = ExchangeRate(
        tenant_id=tenant_id,
        source_currency_code=normalized_source,
        target_currency_code=normalized_target,
        effective_date=data.effective_date,
        rate=data.rate,
        is_inverse=data.is_inverse,
        rate_source=data.rate_source,
        is_active=True,
    )
    session.add(rate)
    await session.flush()
    return rate


async def update_exchange_rate(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    rate_id: uuid.UUID,
    data: ExchangeRateUpdate,
) -> ExchangeRate:
    """Update an existing exchange rate.

    Args:
        session: Database session
        tenant_id: Tenant identifier
        rate_id: Rate identifier
        data: Update data

    Returns:
        Updated ExchangeRate record

    Raises:
        ExchangeRateNotFoundError: If rate not found
    """
    result = await session.execute(
        select(ExchangeRate).where(
            ExchangeRate.id == rate_id,
            ExchangeRate.tenant_id == tenant_id,
        )
    )
    rate = result.scalar_one_or_none()
    if rate is None:
        raise ExchangeRateNotFoundError(
            source_currency="(by ID)",
            target_currency="",
            effective_date=date.today(),
            tenant_id=tenant_id,
        )

    if data.rate is not None:
        rate.rate = data.rate
    if data.rate_source is not None:
        rate.rate_source = data.rate_source
    if data.is_active is not None:
        rate.is_active = data.is_active

    await session.flush()
    return rate


async def lookup_exchange_rate(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    request: ExchangeRateLookupRequest,
) -> ExchangeRateLookupResponse:
    """Look up exchange rate for a currency pair and date.

    Args:
        session: Database session
        tenant_id: Tenant identifier
        request: Lookup request

    Returns:
        ExchangeRateLookupResponse with resolved rate

    Raises:
        CurrencyNotFoundError: If currency not found
        ExchangeRateNotFoundError: If no rate exists
    """
    resolved = await resolve_exchange_rate(
        session=session,
        tenant_id=tenant_id,
        source_currency_code=request.source_currency_code,
        target_currency_code=request.target_currency_code,
        effective_date=request.effective_date,
        allow_identity=request.allow_identity,
    )

    return ExchangeRateLookupResponse(
        source_currency_code=resolved.source_currency_code,
        target_currency_code=resolved.target_currency_code,
        rate=resolved.rate,
        effective_date=resolved.effective_date,
        rate_source=resolved.rate_source,
    )


async def convert_amount(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    request: ConversionRequest,
) -> ConversionResponse:
    """Convert an amount between currencies.

    Args:
        session: Database session
        tenant_id: Tenant identifier
        request: Conversion request

    Returns:
        ConversionResponse with converted amount and rate details

    Raises:
        CurrencyNotFoundError: If currency not found
        ExchangeRateNotFoundError: If no rate exists
    """
    # Get target currency precision if not specified
    target_precision = request.target_precision
    if target_precision is None:
        try:
            target_curr = await get_currency_by_code(
                session, tenant_id, request.target_currency_code
            )
            target_precision = target_curr.decimal_places
        except CurrencyNotFoundError:
            target_precision = 2  # Default fallback

    # Resolve rate
    resolved = await resolve_exchange_rate(
        session=session,
        tenant_id=tenant_id,
        source_currency_code=request.source_currency_code,
        target_currency_code=request.target_currency_code,
        effective_date=request.effective_date,
    )

    # Convert
    from domains.settings.exchange_rate_service import convert_amount as do_convert

    converted = do_convert(request.amount, resolved.rate, target_precision)

    return ConversionResponse(
        source_currency_code=request.source_currency_code,
        target_currency_code=request.target_currency_code,
        source_amount=request.amount,
        target_amount=converted,
        rate=resolved.rate,
        effective_date=resolved.effective_date,
        rate_source=resolved.rate_source,
    )
