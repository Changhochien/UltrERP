"""Schemas for purchase and supplier invoice APIs."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ------------------------------------------------------------------
# Mismatch Status Enum (Story 24-4)
# ------------------------------------------------------------------


class ProcurementMismatchStatus(StrEnum):
    """Mismatch status for three-way-match readiness.

    Readiness signals only - no AP posting workflow is implemented here.
    """

    NOT_CHECKED = "not_checked"
    WITHIN_TOLERANCE = "within_tolerance"
    OUTSIDE_TOLERANCE = "outside_tolerance"
    REVIEW_REQUIRED = "review_required"


# ------------------------------------------------------------------
# Procurement Lineage Response (Story 24-4)
# ------------------------------------------------------------------


class ProcurementLineageResponse(BaseModel):
    """Procurement lineage trace for a single line item.

    Shows upstream document references from RFQ through supplier quotation
    to PO and goods receipt for audit and three-way-match review.
    """

    rfq_id: uuid.UUID | None = None
    rfq_name: str | None = None
    rfq_item_id: uuid.UUID | None = None

    supplier_quotation_id: uuid.UUID | None = None
    supplier_quotation_name: str | None = None
    supplier_quotation_item_id: uuid.UUID | None = None

    purchase_order_id: uuid.UUID | None = None
    purchase_order_name: str | None = None
    purchase_order_line_id: uuid.UUID | None = None

    goods_receipt_id: uuid.UUID | None = None
    goods_receipt_name: str | None = None
    goods_receipt_line_id: uuid.UUID | None = None

    lineage_state: str = Field(
        default="unlinked_historical",
        description="One of: linked, unlinked_historical, missing_reference",
    )


class MismatchSummaryResponse(BaseModel):
    """Mismatch summary for a supplier invoice line (Story 24-4)."""

    mismatch_status: ProcurementMismatchStatus
    quantity_variance: Decimal | None = None
    unit_price_variance: Decimal | None = None
    total_amount_variance: Decimal | None = None
    quantity_variance_pct: Decimal | None = None
    unit_price_variance_pct: Decimal | None = None
    total_amount_variance_pct: Decimal | None = None
    tolerance_rule_code: str | None = None
    tolerance_rule_id: uuid.UUID | None = None
    comparison_basis_snapshot: dict[str, Any] | None = None


# ------------------------------------------------------------------
# Supplier Invoice Line Schemas
# ------------------------------------------------------------------


class SupplierInvoiceLineCreate(BaseModel):
    """Create schema for supplier invoice line (Story 24-4)."""

    line_number: int
    product_id: uuid.UUID | None = None
    product_code_snapshot: str | None = None
    description: str = Field(default="", max_length=500)
    quantity: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    unit_price: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    subtotal_amount: Decimal = Field(default=Decimal("0"))
    tax_type: int = Field(default=0, ge=0)
    tax_rate: Decimal = Field(default=Decimal("0"))
    tax_amount: Decimal = Field(default=Decimal("0"))
    total_amount: Decimal = Field(default=Decimal("0"))

    # Procurement lineage references (Story 24-4)
    rfq_item_id: uuid.UUID | None = None
    supplier_quotation_item_id: uuid.UUID | None = None
    purchase_order_line_id: uuid.UUID | None = None
    goods_receipt_line_id: uuid.UUID | None = None

    # Reference values for mismatch calculation (Story 24-4)
    reference_quantity: Decimal | None = None
    reference_unit_price: Decimal | None = None
    reference_total_amount: Decimal | None = None


class SupplierInvoiceLineUpdate(BaseModel):
    """Update schema for supplier invoice line (Story 24-4)."""

    product_id: uuid.UUID | None = None
    product_code_snapshot: str | None = None
    description: str | None = Field(default=None, max_length=500)
    quantity: Decimal | None = Field(default=None, ge=Decimal("0"))
    unit_price: Decimal | None = Field(default=None, ge=Decimal("0"))
    subtotal_amount: Decimal | None = None
    tax_type: int | None = Field(default=None, ge=0)
    tax_rate: Decimal | None = None
    tax_amount: Decimal | None = None
    total_amount: Decimal | None = None

    # Procurement lineage references (Story 24-4)
    rfq_item_id: uuid.UUID | None = None
    supplier_quotation_item_id: uuid.UUID | None = None
    purchase_order_line_id: uuid.UUID | None = None
    goods_receipt_line_id: uuid.UUID | None = None

    # Reference values for mismatch calculation (Story 24-4)
    reference_quantity: Decimal | None = None
    reference_unit_price: Decimal | None = None
    reference_total_amount: Decimal | None = None


class SupplierInvoiceLineResponse(BaseModel):
    """Response schema for supplier invoice line (Story 24-4)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    line_number: int
    product_id: uuid.UUID | None
    product_code_snapshot: str | None
    product_name: str | None = None
    description: str
    quantity: Decimal
    unit_price: Decimal
    subtotal_amount: Decimal
    tax_type: int
    tax_rate: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    base_unit_price: Decimal | None = None
    base_subtotal_amount: Decimal | None = None
    base_tax_amount: Decimal | None = None
    base_total_amount: Decimal | None = None
    created_at: datetime

    # Procurement lineage references (Story 24-4)
    rfq_item_id: uuid.UUID | None = None
    supplier_quotation_item_id: uuid.UUID | None = None
    purchase_order_line_id: uuid.UUID | None = None
    goods_receipt_line_id: uuid.UUID | None = None

    # Mismatch and tolerance-ready fields (Story 24-4)
    reference_quantity: Decimal | None = None
    reference_unit_price: Decimal | None = None
    reference_total_amount: Decimal | None = None
    quantity_variance: Decimal | None = None
    unit_price_variance: Decimal | None = None
    total_amount_variance: Decimal | None = None
    quantity_variance_pct: Decimal | None = None
    unit_price_variance_pct: Decimal | None = None
    total_amount_variance_pct: Decimal | None = None
    comparison_basis_snapshot: dict[str, Any] | None = None
    mismatch_status: ProcurementMismatchStatus = ProcurementMismatchStatus.NOT_CHECKED
    tolerance_rule_code: str | None = None
    tolerance_rule_id: uuid.UUID | None = None


# ------------------------------------------------------------------
# Supplier Invoice Schemas
# ------------------------------------------------------------------


class SupplierInvoiceCreate(BaseModel):
    """Create schema for supplier invoice (Story 24-4)."""

    supplier_id: uuid.UUID
    invoice_number: str = Field(..., max_length=100)
    invoice_date: date
    currency_code: str = Field(default="TWD", max_length=3)
    subtotal_amount: Decimal = Field(default=Decimal("0"))
    tax_amount: Decimal = Field(default=Decimal("0"))
    total_amount: Decimal = Field(default=Decimal("0"))
    remaining_payable_amount: Decimal | None = None
    notes: str | None = None
    legacy_header_snapshot: dict[str, Any] | None = None

    # Procurement lineage - header-level PO reference (Story 24-4)
    purchase_order_id: uuid.UUID | None = None

    lines: list[SupplierInvoiceLineCreate] = Field(default_factory=list)


class SupplierInvoiceUpdate(BaseModel):
    """Update schema for supplier invoice (Story 24-4)."""

    supplier_id: uuid.UUID | None = None
    invoice_number: str | None = Field(default=None, max_length=100)
    invoice_date: date | None = None
    currency_code: str | None = Field(default=None, max_length=3)
    subtotal_amount: Decimal | None = None
    tax_amount: Decimal | None = None
    total_amount: Decimal | None = None
    remaining_payable_amount: Decimal | None = None
    notes: str | None = None
    legacy_header_snapshot: dict[str, Any] | None = None

    # Procurement lineage - header-level PO reference (Story 24-4)
    purchase_order_id: uuid.UUID | None = None


class SupplierInvoiceResponse(BaseModel):
    """Response schema for supplier invoice (Story 24-4)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    supplier_id: uuid.UUID
    supplier_name: str
    invoice_number: str
    invoice_date: date
    currency_code: str
    subtotal_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    remaining_payable_amount: Decimal | None = None
    conversion_rate: Decimal | None = None
    conversion_effective_date: date | None = None
    applied_rate_source: str | None = None
    currency_source: str | None = None
    payment_terms_source: str | None = None
    base_subtotal_amount: Decimal | None = None
    base_tax_amount: Decimal | None = None
    base_total_amount: Decimal | None = None
    remaining_base_payable_amount: Decimal | None = None
    status: str
    notes: str | None = None
    legacy_header_snapshot: dict[str, Any] | None = None

    # Procurement lineage - header-level PO reference (Story 24-4)
    purchase_order_id: uuid.UUID | None = None

    created_at: datetime
    updated_at: datetime
    lines: list[SupplierInvoiceLineResponse] = Field(default_factory=list)


# ------------------------------------------------------------------
# Supplier Invoice with Lineage Response (Story 24-4)
# ------------------------------------------------------------------


class SupplierInvoiceLineWithLineageResponse(SupplierInvoiceLineResponse):
    """Extended response with procurement lineage trace."""

    lineage: ProcurementLineageResponse = Field(default_factory=ProcurementLineageResponse)
    mismatch_summary: MismatchSummaryResponse | None = None


class SupplierInvoiceWithLineageResponse(SupplierInvoiceResponse):
    """Extended response with procurement lineage and mismatch data."""

    lines: list[SupplierInvoiceLineWithLineageResponse] = Field(default_factory=list)


# ------------------------------------------------------------------
# Supplier Invoice List Schemas
# ------------------------------------------------------------------


class SupplierInvoiceListItem(BaseModel):
    """List item schema for supplier invoice."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    supplier_id: uuid.UUID
    supplier_name: str
    invoice_number: str
    invoice_date: date
    currency_code: str
    total_amount: Decimal
    remaining_payable_amount: Decimal | None = None
    conversion_rate: Decimal | None = None
    conversion_effective_date: date | None = None
    applied_rate_source: str | None = None
    currency_source: str | None = None
    payment_terms_source: str | None = None
    base_total_amount: Decimal | None = None
    remaining_base_payable_amount: Decimal | None = None
    status: str
    legacy_header_snapshot: dict[str, Any] | None = None

    # Procurement lineage - header-level PO reference (Story 24-4)
    purchase_order_id: uuid.UUID | None = None

    created_at: datetime
    updated_at: datetime
    line_count: int


class SupplierInvoiceListResponse(BaseModel):
    """List response for supplier invoices."""

    items: list[SupplierInvoiceListItem]
    status_totals: dict[str, int]
    total: int
    page: int
    page_size: int


# ------------------------------------------------------------------
# Lineage Query Response (Story 24-4)
# ------------------------------------------------------------------


class LineageDocumentRef(BaseModel):
    """Reference to a single document in the lineage chain."""

    id: uuid.UUID
    name: str
    document_type: str  # rfq, supplier_quotation, purchase_order, goods_receipt
    status: str | None = None
    transaction_date: date | None = None


class LineageChainResponse(BaseModel):
    """Full lineage chain from RFQ through supplier invoice."""

    supplier_invoice_id: uuid.UUID
    supplier_invoice_name: str

    rfq: LineageDocumentRef | None = None
    supplier_quotation: LineageDocumentRef | None = None
    purchase_order: LineageDocumentRef | None = None
    goods_receipt: LineageDocumentRef | None = None

    line_count: int
    lines: list[SupplierInvoiceLineWithLineageResponse]
