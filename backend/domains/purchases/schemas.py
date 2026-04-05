"""Schemas for purchase and supplier invoice APIs."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class SupplierInvoiceLineResponse(BaseModel):
    id: uuid.UUID
    line_number: int
    product_id: uuid.UUID | None
    product_code_snapshot: str | None
    product_name: str | None
    description: str
    quantity: Decimal
    unit_price: Decimal
    subtotal_amount: Decimal
    tax_type: int
    tax_rate: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    created_at: datetime


class SupplierInvoiceResponse(BaseModel):
    id: uuid.UUID
    supplier_id: uuid.UUID
    supplier_name: str
    invoice_number: str
    invoice_date: date
    currency_code: str
    subtotal_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    status: str
    notes: str | None
    created_at: datetime
    updated_at: datetime
    lines: list[SupplierInvoiceLineResponse]


class SupplierInvoiceListItem(BaseModel):
    id: uuid.UUID
    supplier_id: uuid.UUID
    supplier_name: str
    invoice_number: str
    invoice_date: date
    currency_code: str
    total_amount: Decimal
    status: str
    created_at: datetime
    updated_at: datetime
    line_count: int


class SupplierInvoiceListResponse(BaseModel):
    items: list[SupplierInvoiceListItem]
    total: int
    page: int
    page_size: int