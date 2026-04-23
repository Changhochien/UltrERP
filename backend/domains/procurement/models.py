"""Procurement SQLAlchemy models - RFQ and Supplier Quotation workspace.

Models owned by this domain:
- RFQ (Request for Quotation) header
- RFQItem: line items on an RFQ (stable UUID for lineage)
- RFQSupplier: supplier recipients with per-supplier quote status
- SupplierQuotation: supplier's response to an RFQ
- SupplierQuotationItem: line items on a supplier quotation (stable UUID)
- ProcurementAward: winner selection before PO creation
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.database import Base

# ------------------------------------------------------------------
# RFQ (Request for Quotation)
# ------------------------------------------------------------------


class RFQ(Base):
    """RFQ header - collects item requests and distributes to suppliers."""

    __tablename__ = "procurement_rfqs"
    __table_args__ = (
        Index("ix_procurement_rfqs_tenant_status", "tenant_id", "status"),
        Index("ix_procurement_rfqs_tenant_schedule_date", "tenant_id", "schedule_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)

    # Reference / naming
    name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="draft")

    # Company context
    company: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="TWD")

    # Dates
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    schedule_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Commercial terms (ready for RFQ distribution)
    terms_and_conditions: Mapped[str] = mapped_column(Text, nullable=False, default="")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # Supplier count snapshot
    supplier_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Quotes received count snapshot (recomputed via service)
    quotes_received: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(tz=UTC),
        onupdate=lambda: datetime.now(tz=UTC),
    )

    # Relationships
    items: Mapped[list[RFQItem]] = relationship(
        back_populates="rfq",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    suppliers: Mapped[list[RFQSupplier]] = relationship(
        back_populates="rfq",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    quotations: Mapped[list[SupplierQuotation]] = relationship(
        back_populates="rfq",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class RFQItem(Base):
    """Line item on an RFQ with a stable UUID for lineage references."""

    __tablename__ = "procurement_rfq_items"
    __table_args__ = (
        Index("ix_procurement_rfq_items_rfq", "rfq_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    rfq_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("procurement_rfqs.id", ondelete="CASCADE"), nullable=False
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)

    # Stable display order (independent of item UUID)
    idx: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Item reference (reuse product master)
    item_code: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    item_name: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # Requested quantity and UOM
    qty: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False, default=Decimal("0"))
    uom: Mapped[str] = mapped_column(String(40), nullable=False, default="")

    # Optional warehouse context
    warehouse: Mapped[str] = mapped_column(String(120), nullable=False, default="")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=UTC)
    )

    rfq: Mapped[RFQ] = relationship(back_populates="items")


class RFQSupplier(Base):
    """Supplier recipient of an RFQ with per-supplier quote status."""

    __tablename__ = "procurement_rfq_suppliers"
    __table_args__ = (
        Index("ix_procurement_rfq_suppliers_rfq", "rfq_id"),
        Index("ix_procurement_rfq_suppliers_supplier", "tenant_id", "supplier_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    rfq_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("procurement_rfqs.id", ondelete="CASCADE"), nullable=False
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)

    # Supplier reference (reuse supplier master)
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    supplier_name: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    contact_email: Mapped[str] = mapped_column(String(254), nullable=False, default="")

    # Per-supplier quote status (pending | received | lost | cancelled)
    quote_status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending")

    # Link to supplier quotation if received
    quotation_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)

    # Supplier-specific notes
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(tz=UTC),
        onupdate=lambda: datetime.now(tz=UTC),
    )

    rfq: Mapped[RFQ] = relationship(back_populates="suppliers")


# ------------------------------------------------------------------
# Supplier Quotation
# ------------------------------------------------------------------


class SupplierQuotation(Base):
    """Supplier quotation in response to an RFQ."""

    __tablename__ = "procurement_supplier_quotations"
    __table_args__ = (
        Index("ix_procurement_sq_tenant_status", "tenant_id", "status"),
        Index("ix_procurement_sq_tenant_rfq", "tenant_id", "rfq_id"),
        Index("ix_procurement_sq_tenant_supplier", "tenant_id", "supplier_id"),
        Index("ix_procurement_sq_tenant_validity", "tenant_id", "valid_till"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)

    # Naming
    name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="draft")

    # RFQ linkage
    rfq_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("procurement_rfqs.id"), nullable=True
    )

    # Supplier reference (reuse supplier master)
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    supplier_name: Mapped[str] = mapped_column(String(200), nullable=False, default="")

    # Company context
    company: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="TWD")

    # Dates
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    valid_till: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Delivery / lead time
    lead_time_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    delivery_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Pricing
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    total_taxes: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    grand_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    base_grand_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    # Tax metadata (templates / row-level)
    taxes: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False, default=list)

    # Contact
    contact_person: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    contact_email: Mapped[str] = mapped_column(String(254), nullable=False, default="")

    # Terms
    terms_and_conditions: Mapped[str] = mapped_column(Text, nullable=False, default="")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # Comparison metadata (normalized values for cross-supplier comparison)
    comparison_base_total: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0.00")
    )

    # Award flag
    is_awarded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(tz=UTC),
        onupdate=lambda: datetime.now(tz=UTC),
    )

    rfq: Mapped[RFQ | None] = relationship(back_populates="quotations")
    items: Mapped[list[SupplierQuotationItem]] = relationship(
        back_populates="quotation",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class SupplierQuotationItem(Base):
    """Line item on a supplier quotation with a stable UUID for lineage."""

    __tablename__ = "procurement_supplier_quotation_items"
    __table_args__ = (
        Index("ix_procurement_sq_items_quotation", "quotation_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    quotation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("procurement_supplier_quotations.id", ondelete="CASCADE"), nullable=False
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)

    # Stable display order
    idx: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Link back to the RFQ item via stable UUID (for lineage, not a DB FK)
    rfq_item_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)

    # Item reference (reuse product master)
    item_code: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    item_name: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # Quoted quantity and UOM
    qty: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False, default=Decimal("0"))
    uom: Mapped[str] = mapped_column(String(40), nullable=False, default="")

    # Pricing
    unit_rate: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False, default=Decimal("0"))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))

    # Tax metadata
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(6, 3), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    tax_code: Mapped[str] = mapped_column(String(40), nullable=False, default="")

    # Normalized comparison values
    normalized_unit_rate: Mapped[Decimal] = mapped_column(
        Numeric(14, 4), nullable=False, default=Decimal("0")
    )
    normalized_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0.00")
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=UTC)
    )

    quotation: Mapped[SupplierQuotation] = relationship(back_populates="items")


# ------------------------------------------------------------------
# Purchase Order (buyer commitment from awarded supplier quotation)
# ------------------------------------------------------------------


class PurchaseOrder(Base):
    """Purchase Order - formal buyer-side commitment record.

    Created from an awarded supplier quotation without rekeying supplier and item data.
    Preserves explicit sourcing lineage back to the awarded quotation and upstream RFQ.
    """

    __tablename__ = "procurement_purchase_orders"
    __table_args__ = (
        Index("ix_procurement_po_tenant_status", "tenant_id", "status"),
        Index("ix_procurement_po_tenant_supplier", "tenant_id", "supplier_id"),
        Index("ix_procurement_po_tenant_award", "tenant_id", "award_id"),
        # Unique constraint: only one PO per name per tenant
        Index("uq_procurement_po_name_tenant", "tenant_id", "name", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)

    # Naming
    name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="draft")

    # Supplier reference (reuse supplier master)
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    supplier_name: Mapped[str] = mapped_column(String(200), nullable=False, default="")

    # Sourcing lineage
    rfq_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    quotation_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    award_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)

    # Company context
    company: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="TWD")

    # Dates
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    schedule_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Pricing
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    total_taxes: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    grand_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    base_grand_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))

    # Tax metadata (templates / row-level)
    taxes: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False, default=list)

    # Contact
    contact_person: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    contact_email: Mapped[str] = mapped_column(String(254), nullable=False, default="")

    # Warehouse context (default for lines)
    set_warehouse: Mapped[str] = mapped_column(String(120), nullable=False, default="")

    # Terms
    terms_and_conditions: Mapped[str] = mapped_column(Text, nullable=False, default="")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # Progress tracking (computed from downstream coverage)
    per_received: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("0.00"))
    per_billed: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("0.00"))

    # Approval state
    is_approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    approved_by: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(tz=UTC),
        onupdate=lambda: datetime.now(tz=UTC),
    )

    # Relationships
    items: Mapped[list[PurchaseOrderItem]] = relationship(
        back_populates="purchase_order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    goods_receipts: Mapped[list[GoodsReceipt]] = relationship(
        back_populates="purchase_order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class PurchaseOrderItem(Base):
    """Line item on a Purchase Order with a stable UUID for downstream references.

    Stable identifiers enable receipt (Story 24-3) and supplier invoice (Story 24-6)
    to reference PO lines without ambiguity.
    """

    __tablename__ = "procurement_purchase_order_items"
    __table_args__ = (
        Index("ix_procurement_po_items_po", "purchase_order_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    purchase_order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("procurement_purchase_orders.id", ondelete="CASCADE"), nullable=False
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)

    # Stable display order
    idx: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Lineage back to supplier quotation item (for auditing)
    quotation_item_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    rfq_item_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)

    # Item reference (reuse product master)
    item_code: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    item_name: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # Quantity and UOM
    qty: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False, default=Decimal("0"))
    uom: Mapped[str] = mapped_column(String(40), nullable=False, default="")

    # Warehouse for this line
    warehouse: Mapped[str] = mapped_column(String(120), nullable=False, default="")

    # Pricing
    unit_rate: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False, default=Decimal("0"))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))

    # Tax metadata
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(6, 3), nullable=False, default=Decimal("0"))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    tax_code: Mapped[str] = mapped_column(String(40), nullable=False, default="")

    # Progress tracking per line
    received_qty: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False, default=Decimal("0"))
    billed_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=UTC)
    )

    purchase_order: Mapped[PurchaseOrder] = relationship(back_populates="items")


# ------------------------------------------------------------------
# Procurement Award (winner selection before PO creation)
# ------------------------------------------------------------------


class ProcurementAward(Base):
    """Records the winning supplier quotation for an RFQ.

    Created when a buyer marks a supplier quotation as the preferred offer.
    Consumed by Story 24.2 to create a PO without rekeying data.
    """

    __tablename__ = "procurement_awards"
    __table_args__ = (
        Index("ix_procurement_awards_rfq", "rfq_id"),
        Index("ix_procurement_awards_tenant", "tenant_id", "rfq_id"),
        # Unique constraint: only one active award per RFQ per tenant
        Index("uq_procurement_awards_rfq_tenant", "tenant_id", "rfq_id", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)

    # RFQ reference
    rfq_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("procurement_rfqs.id"), nullable=False
    )

    # Awarded supplier quotation
    quotation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("procurement_supplier_quotations.id"), nullable=False
    )

    # Snapshot of awarded commercial data (preserved even if quotation changes)
    awarded_supplier_name: Mapped[str] = mapped_column(String(200), nullable=False)
    awarded_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    awarded_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="TWD")
    awarded_lead_time_days: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Awarded by
    awarded_by: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    awarded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=UTC)
    )

    # PO handoff status
    po_created: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    po_reference: Mapped[str] = mapped_column(String(100), nullable=False, default="")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=UTC)
    )


# ------------------------------------------------------------------
# Goods Receipt (receiving inbound from suppliers)
# ------------------------------------------------------------------


class GoodsReceipt(Base):
    """Goods Receipt - records what was actually received against a Purchase Order.

    Created when a receiver processes inbound deliveries from a supplier.
    Updates PO receipt progress and triggers inventory mutation from accepted quantities.

    Linkage preserved for later supplier-invoice (Story 24-6) and procurement-lineage
    stories without implementing them here.
    """

    __tablename__ = "procurement_goods_receipts"
    __table_args__ = (
        Index("ix_procurement_gr_tenant_status", "tenant_id", "status"),
        Index("ix_procurement_gr_tenant_po", "tenant_id", "purchase_order_id"),
        Index("ix_procurement_gr_tenant_supplier", "tenant_id", "supplier_id"),
        # Unique constraint: only one GR per name per tenant
        Index("uq_procurement_gr_name_tenant", "tenant_id", "name", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)

    # Naming
    name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="draft")

    # PO linkage
    purchase_order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("procurement_purchase_orders.id"), nullable=False
    )

    # Supplier reference
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    supplier_name: Mapped[str] = mapped_column(String(200), nullable=False, default="")

    # Company context
    company: Mapped[str] = mapped_column(String(200), nullable=False, default="")

    # Dates
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    posting_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Receiving warehouse context (default for lines)
    set_warehouse: Mapped[str] = mapped_column(String(120), nullable=False, default="")

    # Contact
    contact_person: Mapped[str] = mapped_column(String(120), nullable=False, default="")

    # Notes
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # Inventory mutation tracking
    inventory_mutated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    inventory_mutated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(tz=UTC),
        onupdate=lambda: datetime.now(tz=UTC),
    )

    # Relationships
    purchase_order: Mapped[PurchaseOrder] = relationship(back_populates="goods_receipts")
    items: Mapped[list[GoodsReceiptItem]] = relationship(
        back_populates="goods_receipt",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class GoodsReceiptItem(Base):
    """Line item on a Goods Receipt with PO-line linkage and explicit accepted/rejected handling.

    Stable UUID enables supplier-invoice lineage (Story 24-6) to reference receipt lines
    without ambiguity.
    """

    __tablename__ = "procurement_goods_receipt_items"
    __table_args__ = (
        Index("ix_procurement_gr_items_receipt", "goods_receipt_id"),
        Index("ix_procurement_gr_items_po_line", "purchase_order_item_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    goods_receipt_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("procurement_goods_receipts.id", ondelete="CASCADE"), nullable=False
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)

    # Stable display order
    idx: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # PO line linkage (stable UUID from Story 24-2)
    purchase_order_item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("procurement_purchase_order_items.id"), nullable=False
    )

    # Item reference
    item_code: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    item_name: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # Quantity handling (accepted + rejected = total received)
    # Invariant: total_qty = accepted_qty + rejected_qty
    accepted_qty: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False, default=Decimal("0"))
    rejected_qty: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False, default=Decimal("0"))
    total_qty: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False, default=Decimal("0"))

    # UOM
    uom: Mapped[str] = mapped_column(String(40), nullable=False, default="")

    # Warehouse handling
    warehouse: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    rejected_warehouse: Mapped[str] = mapped_column(String(120), nullable=False, default="")

    # Receiving metadata
    batch_no: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    serial_no: Mapped[str] = mapped_column(String(100), nullable=False, default="")

    # Exception handling
    exception_notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_rejected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Unit rate from PO (for valuation)
    unit_rate: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False, default=Decimal("0"))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=UTC)
    )

    goods_receipt: Mapped[GoodsReceipt] = relationship(back_populates="items")
