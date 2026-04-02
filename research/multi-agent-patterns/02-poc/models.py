"""
Domain models for the UltrERP MCP server PoC.

All models are plain Pydantic dataclasses used for:
  - Tool input validation (via Annotated[..., Field(...)] in main.py)
  - Typed dicts returned by tool implementations
"""

from datetime import date, datetime
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class CustomerStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    OPEN = "open"
    PAID = "paid"
    VOID = "void"


# ---------------------------------------------------------------------------
# Customer
# ---------------------------------------------------------------------------


class Customer(BaseModel):
    id: str
    name: str
    tax_id: str
    email: str
    status: CustomerStatus
    created_at: datetime
    updated_at: datetime


class CustomerCreateInput(BaseModel):
    """Input schema for customers.create tool."""

    name: Annotated[
        str,
        Field(
            description="Legal name of the customer (2–255 characters)",
            min_length=2,
            max_length=255,
        ),
    ]
    tax_id: Annotated[
        str,
        Field(
            description=(
                "Tax identification number. Must be exactly 8 digits "
                "passing MOD11 checksum validation."
            ),
            pattern=r"^\d{8}$",
        ),
    ]
    email: Annotated[
        str,
        Field(
            description="Primary contact email address",
            max_length=255,
        ),
    ]
    status: CustomerStatus = CustomerStatus.ACTIVE


class CustomerListFilters(BaseModel):
    """Query parameters for customers.list."""

    status: CustomerStatus | None = Field(
        default=None,
        description="Filter by customer status (active, inactive, suspended).",
    )
    limit: Annotated[
        int,
        Field(1, description="Maximum number of results to return (1–100).", ge=1, le=100),
    ] = 25
    offset: Annotated[
        int,
        Field(0, description="Number of results to skip for pagination.", ge=0),
    ] = 0


# ---------------------------------------------------------------------------
# Invoice / Line Items
# ---------------------------------------------------------------------------


class LineItem(BaseModel):
    description: str
    quantity: Annotated[int, Field(gt=0, description="Quantity must be positive.")]
    unit_price: Annotated[
        float,
        Field(ge=0.0, description="Unit price in the default currency."),
    ]
    tax_rate: Annotated[
        float,
        Field(
            0.05,
            description="Tax rate applied to this line item. Defaults to 5%.",
            ge=0.0,
            le=1.0,
        ),
    ] = 0.05

    @property
    def subtotal(self) -> float:
        return round(self.quantity * self.unit_price, 2)

    @property
    def tax_amount(self) -> float:
        return round(self.subtotal * self.tax_rate, 2)

    @property
    def total(self) -> float:
        return round(self.subtotal + self.tax_amount, 2)


class Invoice(BaseModel):
    id: str
    customer_id: str
    status: InvoiceStatus
    line_items: list[LineItem]
    subtotal: float
    total_tax: float
    total: float
    created_at: datetime
    due_date: date


class InvoiceCreateInput(BaseModel):
    """Input schema for invoices.create tool."""

    customer_id: Annotated[
        str,
        Field(description="ID of the customer to bill."),
    ]
    due_date: Annotated[
        date,
        Field(description="Payment due date (ISO 8601: YYYY-MM-DD)."),
    ]
    line_items: Annotated[
        list[LineItem],
        Field(
            min_length=1,
            description="At least one line item is required.",
        ),
    ]
    status: InvoiceStatus = InvoiceStatus.DRAFT


class InvoiceListFilters(BaseModel):
    """Query parameters for invoices.list."""

    status: InvoiceStatus | None = Field(
        default=None,
        description="Filter by invoice status (draft, open, paid, void).",
    )
    customer_id: str | None = Field(
        default=None,
        description="Filter by customer ID.",
    )
    limit: Annotated[
        int,
        Field(1, description="Maximum number of results to return (1–100).", ge=1, le=100),
    ] = 25
    offset: Annotated[
        int,
        Field(0, description="Number of results to skip for pagination.", ge=0),
    ] = 0
