"""Customer Pydantic schemas for request/response serialization."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class CustomerCreate(BaseModel):
    """POST /api/v1/customers request body."""

    company_name: str = Field(..., min_length=1, max_length=200)
    business_number: str = Field(..., min_length=1, max_length=20)
    billing_address: str = Field(default="", max_length=500)
    contact_name: str = Field(..., min_length=1, max_length=100)
    contact_phone: str = Field(..., min_length=1, max_length=30)
    contact_email: str = Field(..., min_length=1, max_length=254)
    credit_limit: Decimal = Field(default=Decimal("0.00"), ge=0, decimal_places=2)


class CustomerUpdate(BaseModel):
    """PATCH /api/v1/customers/{id} request body.

    All fields are optional — only provided fields are updated.
    ``version`` is required for optimistic locking.
    """

    company_name: str | None = Field(default=None, min_length=1, max_length=200)
    business_number: str | None = Field(default=None, min_length=1, max_length=20)
    billing_address: str | None = Field(default=None, max_length=500)
    contact_name: str | None = Field(default=None, min_length=1, max_length=100)
    contact_phone: str | None = Field(default=None, min_length=1, max_length=30)
    contact_email: str | None = Field(default=None, min_length=1, max_length=254)
    credit_limit: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    version: int = Field(..., ge=1)


class CustomerResponse(BaseModel):
    """Serialized customer for API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    company_name: str
    normalized_business_number: str
    billing_address: str
    contact_name: str
    contact_phone: str
    contact_email: str
    credit_limit: Decimal
    status: str
    legacy_master_snapshot: dict[str, Any] | None = None
    version: int
    created_at: datetime
    updated_at: datetime


class CustomerSummary(BaseModel):
    """Compact customer row for list results."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_name: str
    normalized_business_number: str
    contact_phone: str
    status: str


class CustomerListParams(BaseModel):
    """Query parameters for GET /api/v1/customers."""

    q: str | None = Field(default=None, max_length=200)
    status: str | None = Field(default=None, max_length=20)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class CustomerListResponse(BaseModel):
    """Paginated customer list response."""

    items: list[CustomerSummary]
    page: int
    page_size: int
    total_count: int
    total_pages: int


class CustomerOutstandingSummary(BaseModel):
    """Outstanding balance summary for a customer."""

    total_outstanding: Decimal
    overdue_count: int
    overdue_amount: Decimal
    invoice_count: int
    currency_code: str = "TWD"


class CustomerStatementParams(BaseModel):
    """Query parameters for GET /api/v1/customers/{customer_id}/statement."""

    from_date: date | None = None
    to_date: date | None = None


class StatementLine(BaseModel):
    """A single line item in a customer account statement."""

    date: date
    type: Literal["invoice", "payment"]
    reference: str
    description: str
    debit: Decimal
    credit: Decimal
    balance: Decimal


class CustomerStatementResponse(BaseModel):
    """Account statement response for a customer."""

    customer_id: uuid.UUID
    company_name: str
    currency_code: str = "TWD"
    opening_balance: Decimal
    current_balance: Decimal
    lines: list[StatementLine]
