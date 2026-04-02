"""Pydantic schemas for invoice creation and serialization."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from domains.invoices.enums import BuyerType
from domains.invoices.tax import TaxPolicyCode


class InvoiceCreateLine(BaseModel):
    product_id: uuid.UUID | None = None
    product_code: str | None = Field(default=None, max_length=100)
    description: str = Field(..., min_length=1, max_length=500)
    quantity: Decimal
    unit_price: Decimal
    tax_policy_code: TaxPolicyCode


class InvoiceCreate(BaseModel):
    customer_id: uuid.UUID
    buyer_type: BuyerType
    buyer_identifier: str | None = Field(default=None, max_length=20)
    invoice_date: date | None = None
    currency_code: str = Field(default="TWD", min_length=3, max_length=3)
    lines: list[InvoiceCreateLine]


class VoidInvoiceRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)


class InvoiceLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID | None
    product_code_snapshot: str | None
    description: str
    quantity: Decimal
    unit_price: Decimal
    subtotal_amount: Decimal
    tax_type: int
    tax_rate: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    zero_tax_rate_reason: str | None


class InvoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    invoice_number: str
    invoice_date: date
    customer_id: uuid.UUID
    buyer_type: str
    buyer_identifier_snapshot: str
    currency_code: str
    subtotal_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    status: str
    version: int
    voided_at: datetime | None = None
    void_reason: str | None = None
    created_at: datetime
    updated_at: datetime
    lines: list[InvoiceLineResponse]