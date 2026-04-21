"""Pydantic schemas for order creation and serialization."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PaymentTermsCode(str, enum.Enum):
    NET_30 = "NET_30"
    NET_60 = "NET_60"
    COD = "COD"


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    FULFILLED = "fulfilled"
    CANCELLED = "cancelled"


class OrderCommercialStatus(str, enum.Enum):
    PRE_COMMIT = "pre_commit"
    COMMITTED = "committed"
    CANCELLED = "cancelled"


class OrderFulfillmentStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    READY_TO_SHIP = "ready_to_ship"
    SHIPPED = "shipped"
    FULFILLED = "fulfilled"
    CANCELLED = "cancelled"


class OrderBillingStatus(str, enum.Enum):
    NOT_INVOICED = "not_invoiced"
    UNPAID = "unpaid"
    PARTIAL = "partial"
    PAID = "paid"
    OVERDUE = "overdue"
    VOIDED = "voided"


class OrderReservationStatus(str, enum.Enum):
    NOT_RESERVED = "not_reserved"
    RESERVED = "reserved"
    RELEASED = "released"


ALLOWED_TRANSITIONS: dict[OrderStatus, frozenset[OrderStatus]] = {
    OrderStatus.PENDING: frozenset({OrderStatus.CONFIRMED, OrderStatus.CANCELLED}),
    OrderStatus.CONFIRMED: frozenset({OrderStatus.SHIPPED}),
    OrderStatus.SHIPPED: frozenset({OrderStatus.FULFILLED}),
    OrderStatus.FULFILLED: frozenset(),
    OrderStatus.CANCELLED: frozenset(),
}


PAYMENT_TERMS_CONFIG: dict[PaymentTermsCode, dict[str, str | int]] = {
    PaymentTermsCode.NET_30: {"label": "Net 30", "days": 30},
    PaymentTermsCode.NET_60: {"label": "Net 60", "days": 60},
    PaymentTermsCode.COD: {"label": "Cash on Delivery", "days": 0},
}


class OrderCreateLine(BaseModel):
    product_id: uuid.UUID
    source_quotation_line_no: int | None = Field(default=None, ge=1)
    description: str = Field(..., min_length=1, max_length=500)
    quantity: Decimal = Field(..., gt=0, max_digits=18, decimal_places=3)
    list_unit_price: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=20, decimal_places=2)
    unit_price: Decimal = Field(..., ge=0, max_digits=20, decimal_places=2)
    discount_amount: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=20, decimal_places=2)
    tax_policy_code: str = Field(..., min_length=1, max_length=20)


class OrderSalesTeamAssignmentCreate(BaseModel):
    sales_person: str = Field(..., min_length=1, max_length=120)
    allocated_percentage: Decimal = Field(..., gt=0, le=100, max_digits=5, decimal_places=2)
    commission_rate: Decimal = Field(..., ge=0, le=100, max_digits=5, decimal_places=2)


class OrderSalesTeamAssignment(BaseModel):
    sales_person: str
    allocated_percentage: Decimal
    commission_rate: Decimal
    allocated_amount: Decimal


class OrderCreate(BaseModel):
    customer_id: uuid.UUID
    source_quotation_id: uuid.UUID | None = None
    payment_terms_code: PaymentTermsCode = PaymentTermsCode.NET_30
    discount_amount: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=20, decimal_places=2)
    discount_percent: Decimal = Field(default=Decimal("0.0000"), ge=0, le=1, max_digits=5, decimal_places=4)
    crm_context_snapshot: dict[str, Any] | None = None
    notes: str | None = Field(default=None, max_length=2000)
    sales_team: list[OrderSalesTeamAssignmentCreate] = Field(default_factory=list, max_length=10)
    lines: list[OrderCreateLine] = Field(..., min_length=1, max_length=200)

    @model_validator(mode="after")
    def validate_header_discounts(self) -> "OrderCreate":
        if self.discount_amount > 0 and self.discount_percent > 0:
            raise ValueError("discount_amount and discount_percent cannot both be greater than zero")
        return self


class OrderLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    source_quotation_line_no: int | None = None
    line_number: int
    quantity: Decimal
    list_unit_price: Decimal
    unit_price: Decimal
    discount_amount: Decimal
    tax_policy_code: str
    tax_type: int
    tax_rate: Decimal
    tax_amount: Decimal
    subtotal_amount: Decimal
    total_amount: Decimal
    description: str
    available_stock_snapshot: int | None
    backorder_note: str | None


class OrderExecutionSummary(BaseModel):
    commercial_status: OrderCommercialStatus
    fulfillment_status: OrderFulfillmentStatus
    billing_status: OrderBillingStatus
    reservation_status: OrderReservationStatus
    ready_to_ship: bool
    has_backorder: bool
    backorder_line_count: int


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    customer_id: uuid.UUID
    customer_name: str | None = None
    source_quotation_id: uuid.UUID | None = None
    order_number: str
    status: OrderStatus
    payment_terms_code: str
    payment_terms_days: int
    subtotal_amount: Decimal | None
    discount_amount: Decimal | None
    discount_percent: Decimal | None
    tax_amount: Decimal | None
    total_amount: Decimal | None
    sales_team: list[OrderSalesTeamAssignment] = Field(default_factory=list)
    total_commission: Decimal = Field(default=Decimal("0.00"))
    invoice_id: uuid.UUID | None
    invoice_number: str | None = None
    invoice_payment_status: OrderBillingStatus | None = None
    execution: OrderExecutionSummary
    notes: str | None
    crm_context_snapshot: dict[str, Any] | None = None
    legacy_header_snapshot: dict[str, Any] | None = None
    created_by: str
    created_at: datetime
    updated_at: datetime
    confirmed_at: datetime | None
    lines: list[OrderLineResponse] = []


class OrderListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    customer_id: uuid.UUID
    source_quotation_id: uuid.UUID | None = None
    order_number: str
    status: OrderStatus
    payment_terms_code: str
    total_amount: Decimal | None
    sales_team: list[OrderSalesTeamAssignment] = Field(default_factory=list)
    total_commission: Decimal = Field(default=Decimal("0.00"))
    invoice_number: str | None = None
    invoice_payment_status: OrderBillingStatus | None = None
    execution: OrderExecutionSummary
    crm_context_snapshot: dict[str, Any] | None = None
    legacy_header_snapshot: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class OrderListResponse(BaseModel):
    items: list[OrderListItem]
    total: int
    page: int
    page_size: int


class PaymentTermsItem(BaseModel):
    code: str
    label: str
    days: int


class PaymentTermsListResponse(BaseModel):
    items: list[PaymentTermsItem]
    total: int


class WarehouseStockInfo(BaseModel):
    warehouse_id: uuid.UUID
    warehouse_name: str
    available: int


class StockCheckResponse(BaseModel):
    product_id: uuid.UUID
    warehouses: list[WarehouseStockInfo]
    total_available: int


class OrderStatusUpdate(BaseModel):
    new_status: OrderStatus
