"""Currency and exchange rate API routes (Epic 25)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from common.auth import require_role
from common.database import get_db
from domains.settings.currency_service import (
    convert_amount as do_convert,
    create_currency,
    create_exchange_rate,
    get_currency,
    get_currency_by_code,
    list_currencies,
    list_exchange_rates,
    lookup_exchange_rate,
    set_base_currency,
    update_currency,
    update_exchange_rate,
)
from domains.settings.exchange_rate_service import (
    CurrencyNotFoundError,
    ExchangeRateNotFoundError,
)
from domains.settings.schemas_currency import (
    ConversionRequest,
    ConversionResponse,
    CurrencyCreate,
    CurrencyListResponse,
    CurrencyResponse,
    CurrencyUpdate,
    ExchangeRateCreate,
    ExchangeRateListResponse,
    ExchangeRateLookupRequest,
    ExchangeRateLookupResponse,
    ExchangeRateResponse,
    ExchangeRateUpdate,
)

router = APIRouter(
    prefix="/currencies",
    tags=["currencies"],
    dependencies=[Depends(require_role("owner", "admin", "finance"))],
)

DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[dict, Depends(require_role("owner", "admin", "finance"))]


def _get_tenant_id(current_user: CurrentUser) -> uuid.UUID:
    """Extract tenant ID from current user."""
    return uuid.UUID(current_user["tenant_id"])


# ============================================================
# Currency Endpoints
# ============================================================


@router.get("", response_model=CurrencyListResponse)
async def list_currencies_endpoint(
    db: DbSession,
    current_user: CurrentUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    active_only: bool = False,
) -> CurrencyListResponse:
    """List currencies for the current tenant.

    - **page**: Page number (1-indexed)
    - **page_size**: Items per page (max 100)
    - **active_only**: Filter to only active currencies
    """
    tenant_id = _get_tenant_id(current_user)
    return await list_currencies(
        db, tenant_id, page=page, page_size=page_size, active_only=active_only
    )


@router.get("/base", response_model=CurrencyResponse)
async def get_base_currency_endpoint(
    db: DbSession,
    current_user: CurrentUser,
) -> CurrencyResponse:
    """Get the tenant's base currency."""
    from domains.settings.exchange_rate_service import get_tenant_base_currency

    tenant_id = _get_tenant_id(current_user)
    try:
        currency = await get_tenant_base_currency(db, tenant_id)
        return CurrencyResponse.model_validate(currency)
    except CurrencyNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get("/{currency_id}", response_model=CurrencyResponse)
async def get_currency_endpoint(
    currency_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> CurrencyResponse:
    """Get a single currency by ID."""
    tenant_id = _get_tenant_id(current_user)
    try:
        currency = await get_currency(db, tenant_id, currency_id)
        return CurrencyResponse.model_validate(currency)
    except CurrencyNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("", response_model=CurrencyResponse, status_code=status.HTTP_201_CREATED)
async def create_currency_endpoint(
    data: CurrencyCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> CurrencyResponse:
    """Create a new currency.

    - **code**: ISO 4217 currency code (e.g., "USD", "EUR")
    - **symbol**: Currency symbol for display
    - **decimal_places**: Decimal precision (0-6)
    - **is_active**: Whether currency is available for transactions
    - **is_base_currency**: Set as tenant's base currency
    """
    tenant_id = _get_tenant_id(current_user)
    try:
        currency = await create_currency(db, tenant_id, data)
        return CurrencyResponse.model_validate(currency)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.patch("/{currency_id}", response_model=CurrencyResponse)
async def update_currency_endpoint(
    currency_id: uuid.UUID,
    data: CurrencyUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> CurrencyResponse:
    """Update an existing currency."""
    tenant_id = _get_tenant_id(current_user)
    try:
        currency = await update_currency(db, tenant_id, currency_id, data)
        return CurrencyResponse.model_validate(currency)
    except CurrencyNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{currency_id}/set-base", response_model=CurrencyResponse)
async def set_base_currency_endpoint(
    currency_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> CurrencyResponse:
    """Set a currency as the tenant's base currency."""
    tenant_id = _get_tenant_id(current_user)
    try:
        currency = await set_base_currency(db, tenant_id, currency_id)
        return CurrencyResponse.model_validate(currency)
    except CurrencyNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# ============================================================
# Exchange Rate Endpoints
# ============================================================

exchange_router = APIRouter(
    prefix="/exchange-rates",
    tags=["exchange-rates"],
    dependencies=[Depends(require_role("owner", "admin", "finance"))],
)


@exchange_router.get("", response_model=ExchangeRateListResponse)
async def list_exchange_rates_endpoint(
    db: DbSession,
    current_user: CurrentUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    source_currency: str | None = None,
    target_currency: str | None = None,
    active_only: bool = True,
) -> ExchangeRateListResponse:
    """List exchange rates with optional filtering.

    - **page**: Page number
    - **page_size**: Items per page
    - **source_currency**: Filter by source currency code
    - **target_currency**: Filter by target currency code
    - **active_only**: Filter to active rates only (default: true)
    """
    tenant_id = _get_tenant_id(current_user)
    return await list_exchange_rates(
        db,
        tenant_id,
        page=page,
        page_size=page_size,
        source_currency=source_currency,
        target_currency=target_currency,
        active_only=active_only,
    )


@exchange_router.post("", response_model=ExchangeRateResponse, status_code=status.HTTP_201_CREATED)
async def create_exchange_rate_endpoint(
    data: ExchangeRateCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> ExchangeRateResponse:
    """Create a new exchange rate.

    - **source_currency_code**: Source/transaction currency code
    - **target_currency_code**: Target/base currency code
    - **effective_date**: Date from which rate applies
    - **rate**: Exchange rate value (must be positive)
    - **rate_source**: Optional source of rate (e.g., "manual", "ecb")
    """
    tenant_id = _get_tenant_id(current_user)
    try:
        rate = await create_exchange_rate(db, tenant_id, data)
        return ExchangeRateResponse.model_validate(rate)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@exchange_router.patch("/{rate_id}", response_model=ExchangeRateResponse)
async def update_exchange_rate_endpoint(
    rate_id: uuid.UUID,
    data: ExchangeRateUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> ExchangeRateResponse:
    """Update an existing exchange rate."""
    tenant_id = _get_tenant_id(current_user)
    try:
        rate = await update_exchange_rate(db, tenant_id, rate_id, data)
        return ExchangeRateResponse.model_validate(rate)
    except ExchangeRateNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@exchange_router.post("/lookup", response_model=ExchangeRateLookupResponse)
async def lookup_exchange_rate_endpoint(
    data: ExchangeRateLookupRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> ExchangeRateLookupResponse:
    """Look up exchange rate for a currency pair and date.

    This endpoint resolves the effective rate using the following fallback:
    1. Identity rate (1.0) if source and target are the same
    2. Latest active rate on or before the effective date
    3. Error if no rate exists
    """
    tenant_id = _get_tenant_id(current_user)
    try:
        return await lookup_exchange_rate(db, tenant_id, data)
    except CurrencyNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except ExchangeRateNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@exchange_router.post("/convert", response_model=ConversionResponse)
async def convert_amount_endpoint(
    data: ConversionRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> ConversionResponse:
    """Convert an amount between currencies.

    - **source_currency_code**: Source currency code
    - **target_currency_code**: Target currency code
    - **amount**: Amount to convert
    - **effective_date**: Date to use for rate lookup
    - **target_precision**: Optional decimal precision for result
    """
    tenant_id = _get_tenant_id(current_user)
    try:
        return await do_convert(db, tenant_id, data)
    except CurrencyNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except ExchangeRateNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
