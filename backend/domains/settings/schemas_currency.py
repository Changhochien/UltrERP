"""Pydantic schemas for currency and exchange rate API (Epic 25)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

# ============================================================
# Currency Schemas
# ============================================================


class CurrencyBase(BaseModel):
    """Base schema for currency with common fields."""

    code: Annotated[str, Field(min_length=3, max_length=3, description="ISO 4217 currency code")]
    symbol: Annotated[str, Field(max_length=10, description="Currency symbol for display")]
    decimal_places: Annotated[int, Field(ge=0, le=6, description="Decimal precision for amounts")]
    is_active: Annotated[bool, Field(default=True, description="Whether currency is available")]

    @field_validator("code", mode="before")
    @classmethod
    def normalize_currency_code(cls, v: str) -> str:
        return v.upper().strip()

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        symbol = v.strip()
        if not symbol:
            raise ValueError("Symbol cannot be empty")
        return symbol


class CurrencyCreate(CurrencyBase):
    """Schema for creating a new currency."""

    is_base_currency: Annotated[
        bool, Field(default=False, description="Set as tenant base currency")
    ]


class CurrencyUpdate(BaseModel):
    """Schema for updating an existing currency."""

    symbol: Annotated[str | None, Field(max_length=10)] = None
    decimal_places: Annotated[int | None, Field(ge=0, le=6)] = None
    is_active: Annotated[bool | None, Field(default=None)] = None

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            raise ValueError("Symbol cannot be empty")
        return v.strip() if v is not None else None


class CurrencyResponse(CurrencyBase):
    """Schema for currency response."""

    id: UUID
    tenant_id: UUID
    is_base_currency: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CurrencyListResponse(BaseModel):
    """Schema for paginated currency list."""

    items: list[CurrencyResponse]
    total: int
    page: int
    page_size: int


# ============================================================
# Exchange Rate Schemas
# ============================================================


class ExchangeRateBase(BaseModel):
    """Base schema for exchange rate with common fields."""

    source_currency_code: Annotated[
        str, Field(min_length=3, max_length=3, description="Source currency code")
    ]
    target_currency_code: Annotated[
        str, Field(min_length=3, max_length=3, description="Target currency code")
    ]
    effective_date: Annotated[date, Field(description="Date from which this rate applies")]
    rate: Annotated[Decimal, Field(gt=0, description="Exchange rate (positive decimal)")]
    rate_source: Annotated[str | None, Field(max_length=50)] = None


class ExchangeRateCreate(ExchangeRateBase):
    """Schema for creating a new exchange rate."""

    is_inverse: Annotated[
        bool, Field(default=False, description="Is this an inverse/computed rate")
    ]

    @field_validator("source_currency_code", "target_currency_code", mode="before")
    @classmethod
    def normalize_currency_code(cls, v: str) -> str:
        return v.upper().strip()

    @field_validator("rate")
    @classmethod
    def validate_rate_precision(cls, v: Decimal) -> Decimal:
        # Ensure rate has reasonable precision for FX
        return v.quantize(Decimal("0.0000000001"))


class ExchangeRateUpdate(BaseModel):
    """Schema for updating an exchange rate."""

    rate: Annotated[Decimal | None, Field(gt=0)] = None
    rate_source: Annotated[str | None, Field(max_length=50)] = None
    is_active: Annotated[bool | None, Field(default=None)] = None

    @field_validator("rate")
    @classmethod
    def validate_rate_precision(cls, v: Decimal | None) -> Decimal | None:
        if v is not None:
            return v.quantize(Decimal("0.0000000001"))
        return v


class ExchangeRateResponse(ExchangeRateBase):
    """Schema for exchange rate response."""

    id: UUID
    tenant_id: UUID
    is_inverse: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ExchangeRateListResponse(BaseModel):
    """Schema for paginated exchange rate list."""

    items: list[ExchangeRateResponse]
    total: int
    page: int
    page_size: int


class ExchangeRateLookupRequest(BaseModel):
    """Schema for exchange rate lookup request."""

    source_currency_code: Annotated[str, Field(min_length=3, max_length=3)]
    target_currency_code: Annotated[str, Field(min_length=3, max_length=3)]
    effective_date: Annotated[date, Field(description="Date to look up rate for")]
    allow_identity: Annotated[
        bool,
        Field(default=True, description="Allow identity rate for same currency"),
    ]

    @field_validator("source_currency_code", "target_currency_code", mode="before")
    @classmethod
    def normalize_currency_code(cls, v: str) -> str:
        return v.upper().strip()


class ExchangeRateLookupResponse(BaseModel):
    """Schema for exchange rate lookup response."""

    source_currency_code: str
    target_currency_code: str
    rate: Decimal
    effective_date: date
    rate_source: str | None


class ConversionRequest(BaseModel):
    """Schema for amount conversion request."""

    source_currency_code: Annotated[str, Field(min_length=3, max_length=3)]
    target_currency_code: Annotated[str, Field(min_length=3, max_length=3)]
    amount: Annotated[Decimal, Field(gt=0, description="Amount to convert")]
    effective_date: Annotated[date, Field(description="Date to use for rate lookup")]
    target_precision: Annotated[int | None, Field(ge=0, le=6)] = None

    @field_validator("source_currency_code", "target_currency_code", mode="before")
    @classmethod
    def normalize_currency_code(cls, v: str) -> str:
        return v.upper().strip()


class ConversionResponse(BaseModel):
    """Schema for amount conversion response."""

    source_currency_code: str
    target_currency_code: str
    source_amount: Decimal
    target_amount: Decimal
    rate: Decimal
    effective_date: date
    rate_source: str | None
