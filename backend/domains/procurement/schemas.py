"""Procurement request and response schemas - RFQ and Supplier Quotation."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

# ------------------------------------------------------------------
# Enums
# ------------------------------------------------------------------


class RFQStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class QuoteStatus(StrEnum):
    PENDING = "pending"
    RECEIVED = "received"
    LOST = "lost"
    CANCELLED = "cancelled"


class SupplierQuotationStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    CANCELLED = "cancelled"


# ------------------------------------------------------------------
# RFQ Schemas
# ------------------------------------------------------------------


class RFQItemCreate(BaseModel):
    item_code: str = Field(default="", max_length=100)
    item_name: str = Field(default="", max_length=200)
    description: str = Field(default="", max_length=2000)
    qty: Decimal = Field(default=Decimal("0"), ge=Decimal("0"), decimal_places=3)
    uom: str = Field(default="", max_length=40)
    warehouse: str = Field(default="", max_length=120)


class RFQItemUpdate(BaseModel):
    item_code: str | None = Field(default=None, max_length=100)
    item_name: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    qty: Decimal | None = Field(default=None, ge=Decimal("0"), decimal_places=3)
    uom: str | None = Field(default=None, max_length=40)
    warehouse: str | None = Field(default=None, max_length=120)


class RFQItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    rfq_id: uuid.UUID
    idx: int
    item_code: str
    item_name: str
    description: str
    qty: Decimal
    uom: str
    warehouse: str
    created_at: datetime


class RFQSupplierCreate(BaseModel):
    supplier_id: uuid.UUID | None = None
    supplier_name: str = Field(..., min_length=1, max_length=200)
    contact_email: str = Field(default="", max_length=254)
    notes: str = Field(default="", max_length=2000)


class RFQSupplierUpdate(BaseModel):
    supplier_id: uuid.UUID | None = None
    supplier_name: str | None = Field(default=None, max_length=200)
    contact_email: str | None = Field(default=None, max_length=254)
    quote_status: QuoteStatus | None = None
    notes: str | None = Field(default=None, max_length=2000)


class RFQSupplierResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    rfq_id: uuid.UUID
    supplier_id: uuid.UUID | None
    supplier_name: str
    contact_email: str
    quote_status: str
    quotation_id: uuid.UUID | None
    notes: str
    created_at: datetime
    updated_at: datetime


class RFQCreate(BaseModel):
    name: str = Field(default="", max_length=100)
    status: RFQStatus = RFQStatus.DRAFT
    company: str = Field(default="", max_length=200)
    currency: str = Field(default="TWD", max_length=3)
    transaction_date: date
    schedule_date: date | None = None
    terms_and_conditions: str = Field(default="", max_length=5000)
    notes: str = Field(default="", max_length=5000)
    items: list[RFQItemCreate] = Field(default_factory=list)
    suppliers: list[RFQSupplierCreate] = Field(default_factory=list)


class RFQUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    status: RFQStatus | None = None
    company: str | None = Field(default=None, max_length=200)
    currency: str | None = Field(default=None, max_length=3)
    transaction_date: date | None = None
    schedule_date: date | None = None
    terms_and_conditions: str | None = Field(default=None, max_length=5000)
    notes: str | None = Field(default=None, max_length=5000)


class RFQResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    status: str
    company: str
    currency: str
    transaction_date: date
    schedule_date: date | None
    terms_and_conditions: str
    notes: str
    supplier_count: int
    quotes_received: int
    created_at: datetime
    updated_at: datetime

    items: list[RFQItemResponse] = Field(default_factory=list)
    suppliers: list[RFQSupplierResponse] = Field(default_factory=list)


class RFQListParams(BaseModel):
    status: RFQStatus | None = None
    q: str | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class RFQSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    status: str
    company: str
    currency: str
    transaction_date: date
    schedule_date: date | None
    supplier_count: int
    quotes_received: int
    created_at: datetime


class RFQListResponse(BaseModel):
    items: list[RFQSummary]
    total: int
    page: int
    page_size: int
    pages: int


# ------------------------------------------------------------------
# Supplier Quotation Schemas
# ------------------------------------------------------------------


class SQItemCreate(BaseModel):
    rfq_item_id: uuid.UUID | None = None
    item_code: str = Field(default="", max_length=100)
    item_name: str = Field(default="", max_length=200)
    description: str = Field(default="", max_length=2000)
    qty: Decimal = Field(default=Decimal("0"), ge=Decimal("0"), decimal_places=3)
    uom: str = Field(default="", max_length=40)
    unit_rate: Decimal = Field(default=Decimal("0"), ge=Decimal("0"), decimal_places=4)
    amount: Decimal = Field(default=Decimal("0"), ge=Decimal("0"), decimal_places=2)
    tax_rate: Decimal = Field(default=Decimal("0"), ge=Decimal("0"), decimal_places=3)
    tax_amount: Decimal = Field(default=Decimal("0"), ge=Decimal("0"), decimal_places=2)
    tax_code: str = Field(default="", max_length=40)
    normalized_unit_rate: Decimal = Field(default=Decimal("0"), decimal_places=4)
    normalized_amount: Decimal = Field(default=Decimal("0"), decimal_places=2)


class SQItemUpdate(BaseModel):
    unit_rate: Decimal | None = Field(default=None, ge=Decimal("0"), decimal_places=4)
    amount: Decimal | None = Field(default=None, ge=Decimal("0"), decimal_places=2)
    tax_rate: Decimal | None = Field(default=None, ge=Decimal("0"), decimal_places=3)
    tax_amount: Decimal | None = Field(default=None, ge=Decimal("0"), decimal_places=2)
    tax_code: str | None = Field(default=None, max_length=40)
    normalized_unit_rate: Decimal | None = Field(default=None, decimal_places=4)
    normalized_amount: Decimal | None = Field(default=None, decimal_places=2)


class SQItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    quotation_id: uuid.UUID
    idx: int
    rfq_item_id: uuid.UUID | None
    item_code: str
    item_name: str
    description: str
    qty: Decimal
    uom: str
    unit_rate: Decimal
    amount: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    tax_code: str
    normalized_unit_rate: Decimal
    normalized_amount: Decimal
    created_at: datetime


class SupplierQuotationCreate(BaseModel):
    name: str = Field(default="", max_length=100)
    status: SupplierQuotationStatus = SupplierQuotationStatus.DRAFT
    rfq_id: uuid.UUID | None = None
    supplier_id: uuid.UUID | None = None
    supplier_name: str = Field(default="", max_length=200)
    company: str = Field(default="", max_length=200)
    currency: str = Field(default="TWD", max_length=3)
    transaction_date: date
    valid_till: date | None = None
    lead_time_days: int | None = Field(default=None, ge=0)
    delivery_date: date | None = None
    subtotal: Decimal = Field(default=Decimal("0.00"), decimal_places=2)
    total_taxes: Decimal = Field(default=Decimal("0.00"), decimal_places=2)
    grand_total: Decimal = Field(default=Decimal("0.00"), decimal_places=2)
    base_grand_total: Decimal = Field(default=Decimal("0.00"), decimal_places=2)
    taxes: list[dict[str, object]] = Field(default_factory=list)
    contact_person: str = Field(default="", max_length=120)
    contact_email: str = Field(default="", max_length=254)
    terms_and_conditions: str = Field(default="", max_length=5000)
    notes: str = Field(default="", max_length=5000)
    comparison_base_total: Decimal = Field(default=Decimal("0.00"), decimal_places=2)
    items: list[SQItemCreate] = Field(default_factory=list)


class SupplierQuotationUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    status: SupplierQuotationStatus | None = None
    valid_till: date | None = None
    lead_time_days: int | None = Field(default=None, ge=0)
    delivery_date: date | None = None
    subtotal: Decimal | None = Field(default=None, decimal_places=2)
    total_taxes: Decimal | None = Field(default=None, decimal_places=2)
    grand_total: Decimal | None = Field(default=None, decimal_places=2)
    base_grand_total: Decimal | None = Field(default=None, decimal_places=2)
    taxes: list[dict[str, object]] | None = None
    contact_person: str | None = Field(default=None, max_length=120)
    contact_email: str | None = Field(default=None, max_length=254)
    terms_and_conditions: str | None = Field(default=None, max_length=5000)
    notes: str | None = Field(default=None, max_length=5000)
    comparison_base_total: Decimal | None = Field(default=None, decimal_places=2)


class SupplierQuotationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    status: str
    rfq_id: uuid.UUID | None
    supplier_id: uuid.UUID | None
    supplier_name: str
    company: str
    currency: str
    transaction_date: date
    valid_till: date | None
    lead_time_days: int | None
    delivery_date: date | None
    subtotal: Decimal
    total_taxes: Decimal
    grand_total: Decimal
    base_grand_total: Decimal
    taxes: list[dict[str, object]]
    contact_person: str
    contact_email: str
    terms_and_conditions: str
    notes: str
    comparison_base_total: Decimal
    is_awarded: bool
    created_at: datetime
    updated_at: datetime

    items: list[SQItemResponse] = Field(default_factory=list)


class SupplierQuotationListParams(BaseModel):
    rfq_id: uuid.UUID | None = None
    status: SupplierQuotationStatus | None = None
    q: str | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class SupplierQuotationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    status: str
    rfq_id: uuid.UUID | None
    supplier_name: str
    currency: str
    transaction_date: date
    valid_till: date | None
    lead_time_days: int | None
    grand_total: Decimal
    base_grand_total: Decimal
    comparison_base_total: Decimal
    is_awarded: bool
    created_at: datetime


class SupplierQuotationListResponse(BaseModel):
    items: list[SupplierQuotationSummary]
    total: int
    page: int
    page_size: int
    pages: int


# ------------------------------------------------------------------
# Purchase Order Schemas
# ------------------------------------------------------------------


class POStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    ON_HOLD = "on_hold"
    TO_RECEIVE = "to_receive"
    TO_BILL = "to_bill"
    TO_RECEIVE_AND_BILL = "to_receive_and_bill"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    CLOSED = "closed"


class POItemCreate(BaseModel):
    quotation_item_id: uuid.UUID | None = None
    rfq_item_id: uuid.UUID | None = None
    item_code: str = Field(default="", max_length=100)
    item_name: str = Field(default="", max_length=200)
    description: str = Field(default="", max_length=2000)
    qty: Decimal = Field(default=Decimal("0"), ge=Decimal("0"), decimal_places=3)
    uom: str = Field(default="", max_length=40)
    warehouse: str = Field(default="", max_length=120)
    unit_rate: Decimal = Field(default=Decimal("0"), ge=Decimal("0"), decimal_places=4)
    amount: Decimal = Field(default=Decimal("0"), ge=Decimal("0"), decimal_places=2)
    tax_rate: Decimal = Field(default=Decimal("0"), ge=Decimal("0"), decimal_places=3)
    tax_amount: Decimal = Field(default=Decimal("0"), decimal_places=2)
    tax_code: str = Field(default="", max_length=40)


class POItemUpdate(BaseModel):
    qty: Decimal | None = Field(default=None, ge=Decimal("0"), decimal_places=3)
    warehouse: str | None = Field(default=None, max_length=120)
    unit_rate: Decimal | None = Field(default=None, ge=Decimal("0"), decimal_places=4)
    amount: Decimal | None = Field(default=None, ge=Decimal("0"), decimal_places=2)
    tax_rate: Decimal | None = Field(default=None, ge=Decimal("0"), decimal_places=3)
    tax_amount: Decimal | None = Field(default=None, decimal_places=2)
    tax_code: str | None = Field(default=None, max_length=40)


class POItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    purchase_order_id: uuid.UUID
    idx: int
    quotation_item_id: uuid.UUID | None
    rfq_item_id: uuid.UUID | None
    item_code: str
    item_name: str
    description: str
    qty: Decimal
    uom: str
    warehouse: str
    unit_rate: Decimal
    amount: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    tax_code: str
    received_qty: Decimal
    billed_amount: Decimal
    created_at: datetime


class PurchaseOrderCreate(BaseModel):
    name: str = Field(default="", max_length=100)
    status: POStatus = POStatus.DRAFT
    # Supplier
    supplier_id: uuid.UUID | None = None
    supplier_name: str = Field(default="", max_length=200)
    # Sourcing lineage (award_id triggers auto-fill from awarded quotation)
    award_id: uuid.UUID | None = None
    rfq_id: uuid.UUID | None = None
    quotation_id: uuid.UUID | None = None
    # Company context
    company: str = Field(default="", max_length=200)
    currency: str = Field(default="TWD", max_length=3)
    # Dates
    transaction_date: date
    schedule_date: date | None = None
    # Pricing
    subtotal: Decimal = Field(default=Decimal("0.00"), decimal_places=2)
    total_taxes: Decimal = Field(default=Decimal("0.00"), decimal_places=2)
    grand_total: Decimal = Field(default=Decimal("0.00"), decimal_places=2)
    base_grand_total: Decimal = Field(default=Decimal("0.00"), decimal_places=2)
    taxes: list[dict[str, object]] = Field(default_factory=list)
    # Contact
    contact_person: str = Field(default="", max_length=120)
    contact_email: str = Field(default="", max_length=254)
    # Warehouse
    set_warehouse: str = Field(default="", max_length=120)
    # Terms
    terms_and_conditions: str = Field(default="", max_length=5000)
    notes: str = Field(default="", max_length=5000)
    items: list[POItemCreate] = Field(default_factory=list)


class PurchaseOrderUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    status: POStatus | None = None
    supplier_name: str | None = Field(default=None, max_length=200)
    company: str | None = Field(default=None, max_length=200)
    currency: str | None = Field(default=None, max_length=3)
    transaction_date: date | None = None
    schedule_date: date | None = None
    subtotal: Decimal | None = Field(default=None, decimal_places=2)
    total_taxes: Decimal | None = Field(default=None, decimal_places=2)
    grand_total: Decimal | None = Field(default=None, decimal_places=2)
    base_grand_total: Decimal | None = Field(default=None, decimal_places=2)
    taxes: list[dict[str, object]] | None = None
    contact_person: str | None = Field(default=None, max_length=120)
    contact_email: str | None = Field(default=None, max_length=254)
    set_warehouse: str | None = Field(default=None, max_length=120)
    terms_and_conditions: str | None = Field(default=None, max_length=5000)
    notes: str | None = Field(default=None, max_length=5000)


class PurchaseOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    status: str
    supplier_id: uuid.UUID | None
    supplier_name: str
    rfq_id: uuid.UUID | None
    quotation_id: uuid.UUID | None
    award_id: uuid.UUID | None
    company: str
    currency: str
    transaction_date: date
    schedule_date: date | None
    subtotal: Decimal
    total_taxes: Decimal
    grand_total: Decimal
    base_grand_total: Decimal
    taxes: list[dict[str, object]]
    contact_person: str
    contact_email: str
    set_warehouse: str
    terms_and_conditions: str
    notes: str
    per_received: Decimal
    per_billed: Decimal
    is_approved: bool
    approved_by: str
    approved_at: datetime | None
    created_at: datetime
    updated_at: datetime

    items: list[POItemResponse] = Field(default_factory=list)


class PurchaseOrderListParams(BaseModel):
    status: POStatus | None = None
    supplier_id: uuid.UUID | None = None
    q: str | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class PurchaseOrderSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    status: str
    supplier_name: str
    company: str
    currency: str
    transaction_date: date
    schedule_date: date | None
    grand_total: Decimal
    per_received: Decimal
    per_billed: Decimal
    is_approved: bool
    created_at: datetime


class PurchaseOrderListResponse(BaseModel):
    items: list[PurchaseOrderSummary]
    total: int
    page: int
    page_size: int
    pages: int


# ------------------------------------------------------------------
# Award Schemas
# ------------------------------------------------------------------


class AwardCreate(BaseModel):
    rfq_id: uuid.UUID
    quotation_id: uuid.UUID
    awarded_by: str = Field(default="", max_length=120)


class AwardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    rfq_id: uuid.UUID
    quotation_id: uuid.UUID
    awarded_supplier_name: str
    awarded_total: Decimal
    awarded_currency: str
    awarded_lead_time_days: int | None
    awarded_by: str
    awarded_at: datetime
    po_created: bool
    po_reference: str
    created_at: datetime


# ------------------------------------------------------------------
# Comparison Schema
# ------------------------------------------------------------------


class SupplierComparisonRow(BaseModel):
    """One supplier quotation in the comparison view."""

    quotation_id: uuid.UUID
    supplier_name: str
    currency: str
    grand_total: Decimal
    base_grand_total: Decimal
    comparison_base_total: Decimal
    lead_time_days: int | None
    valid_till: date | None
    is_awarded: bool
    is_expired: bool
    status: str

    # Per-item comparison detail (optional, for expansion)
    items: list[SQItemResponse] = Field(default_factory=list)


class RFQComparisonResponse(BaseModel):
    """Side-by-side comparison of all supplier quotations for one RFQ."""

    rfq_id: uuid.UUID
    rfq_name: str
    status: str
    items: list[RFQItemResponse]
    quotations: list[SupplierComparisonRow]
