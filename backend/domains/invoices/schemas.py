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
    order_id: uuid.UUID | None = None
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


class InvoicePaymentSummary(BaseModel):
    amount_paid: Decimal
    outstanding_balance: Decimal
    payment_status: str  # "paid" | "partial" | "unpaid" | "overdue"
    due_date: date | None
    days_overdue: int


class EguiSubmissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: str
    mode: str
    fia_reference: str | None = None
    retry_count: int
    deadline_at: datetime
    deadline_label: str
    is_overdue: bool
    last_synced_at: datetime | None = None
    last_error_message: str | None = None
    updated_at: datetime


class InvoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    invoice_number: str
    invoice_date: date
    customer_id: uuid.UUID
    order_id: uuid.UUID | None = None
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
    # Payment summary fields (computed, not stored)
    amount_paid: Decimal | None = None
    outstanding_balance: Decimal | None = None
    payment_status: str | None = None
    due_date: date | None = None
    days_overdue: int | None = None
    egui_submission: EguiSubmissionResponse | None = None


class InvoiceListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    invoice_number: str
    invoice_date: date
    customer_id: uuid.UUID
    order_id: uuid.UUID | None = None
    currency_code: str
    total_amount: Decimal
    status: str
    created_at: datetime
    # Payment summary fields (computed)
    amount_paid: Decimal
    outstanding_balance: Decimal
    payment_status: str
    due_date: date | None
    days_overdue: int


class InvoiceListResponse(BaseModel):
    items: list[InvoiceListItem]
    total: int
    page: int
    page_size: int
