"""Pydantic schemas for payment terms template APIs."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PaymentTermsTemplateDetailPayload(BaseModel):
    row_number: int = Field(..., ge=1)
    invoice_portion: Decimal = Field(..., gt=0, le=100, max_digits=6, decimal_places=2)
    credit_days: int = Field(default=30, ge=0)
    credit_months: int = Field(default=0, ge=0)
    discount_percent: Decimal | None = Field(default=None, ge=0, le=100, max_digits=6, decimal_places=2)
    discount_validity_days: int | None = Field(default=None, ge=0)
    mode_of_payment: str | None = Field(default=None, max_length=50)
    description: str | None = Field(default=None, max_length=200)


class PaymentTermsTemplateCreate(BaseModel):
    template_name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    allocate_payment_based_on_payment_terms: bool = False
    legacy_code: str | None = Field(default=None, max_length=20)
    details: list[PaymentTermsTemplateDetailPayload] = Field(..., min_length=1)


class PaymentTermsTemplateUpdate(BaseModel):
    template_name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    allocate_payment_based_on_payment_terms: bool | None = None
    is_active: bool | None = None
    legacy_code: str | None = Field(default=None, max_length=20)
    details: list[PaymentTermsTemplateDetailPayload] | None = Field(default=None, min_length=1)


class PaymentTermsTemplateDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    template_id: UUID
    row_number: int
    invoice_portion: Decimal
    credit_days: int
    credit_months: int
    discount_percent: Decimal | None = None
    discount_validity_days: int | None = None
    mode_of_payment: str | None = None
    description: str | None = None
    created_at: datetime


class PaymentTermsTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    template_name: str
    description: str | None = None
    allocate_payment_based_on_payment_terms: bool
    is_active: bool
    legacy_code: str | None = None
    created_at: datetime
    updated_at: datetime
    details: list[PaymentTermsTemplateDetailResponse]


class PaymentTermsTemplateListResponse(BaseModel):
    items: list[PaymentTermsTemplateResponse]
    total: int
