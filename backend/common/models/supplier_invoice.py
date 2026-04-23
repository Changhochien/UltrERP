"""Supplier invoice and supplier invoice line models."""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
	JSON,
	Date,
	DateTime,
	Enum,
	ForeignKey,
	Index,
	Integer,
	Numeric,
	String,
	Text,
	Uuid,
	func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.database import Base

if TYPE_CHECKING:
	from common.models.supplier_payment import SupplierPaymentAllocation


class ProcurementMismatchStatus(str, enum.Enum):
	"""Mismatch status for three-way-match readiness (Story 24-4).

	Readiness signals only - no AP posting workflow is implemented here.
	"""

	NOT_CHECKED = "not_checked"
	WITHIN_TOLERANCE = "within_tolerance"
	OUTSIDE_TOLERANCE = "outside_tolerance"
	REVIEW_REQUIRED = "review_required"


class SupplierInvoiceStatus(str, enum.Enum):
	OPEN = "open"
	PAID = "paid"
	VOIDED = "voided"


class SupplierInvoice(Base):
	__tablename__ = "supplier_invoices"
	__table_args__ = (
		Index(
			"uq_supplier_invoices_tenant_supplier_invoice_number",
			"tenant_id",
			"supplier_id",
			"invoice_number",
			unique=True,
		),
		Index("ix_supplier_invoices_tenant_invoice_date", "tenant_id", "invoice_date"),
	)

	id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
	tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
	supplier_id: Mapped[uuid.UUID] = mapped_column(
		Uuid,
		ForeignKey("supplier.id", name="fk_supplier_invoices_supplier_id_supplier"),
		nullable=False,
	)
	invoice_number: Mapped[str] = mapped_column(String(100), nullable=False)
	invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
	currency_code: Mapped[str] = mapped_column(String(3), nullable=False, default="TWD")
	subtotal_amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
	tax_amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
	total_amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
	remaining_payable_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
	status: Mapped[SupplierInvoiceStatus] = mapped_column(
		Enum(
			SupplierInvoiceStatus,
			name="supplier_invoice_status_enum",
			values_callable=lambda enum_type: [member.value for member in enum_type],
			create_constraint=True,
		),
		default=SupplierInvoiceStatus.OPEN,
		nullable=False,
	)
	notes: Mapped[str | None] = mapped_column(Text)
	legacy_header_snapshot: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)

	# ------------------------------------------------------------------
	# Procurement Lineage (Story 24-4) - header-level PO reference for navigation
	# ------------------------------------------------------------------
	purchase_order_id: Mapped[uuid.UUID | None] = mapped_column(
		Uuid, nullable=True, index=True
	)

	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True),
		server_default=func.now(),
		nullable=False,
	)
	updated_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True),
		server_default=func.now(),
		onupdate=func.now(),
		nullable=False,
	)

	lines: Mapped[list[SupplierInvoiceLine]] = relationship(
		back_populates="supplier_invoice",
		cascade="all, delete-orphan",
		order_by="SupplierInvoiceLine.line_number",
	)
	payment_allocations: Mapped[list[SupplierPaymentAllocation]] = relationship(
		back_populates="supplier_invoice",
		order_by="SupplierPaymentAllocation.allocation_date",
	)


class SupplierInvoiceLine(Base):
	__tablename__ = "supplier_invoice_lines"
	__table_args__ = (
		Index(
			"uq_supplier_invoice_lines_invoice_id_line_number",
			"supplier_invoice_id",
			"line_number",
			unique=True,
		),
		Index("ix_supplier_invoice_lines_po_line", "purchase_order_line_id"),
		Index("ix_supplier_invoice_lines_gr_line", "goods_receipt_line_id"),
	)

	id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
	supplier_invoice_id: Mapped[uuid.UUID] = mapped_column(
		Uuid,
		ForeignKey(
			"supplier_invoices.id",
			name="fk_supplier_invoice_lines_invoice_id_supplier_invoices",
		),
		nullable=False,
	)
	tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
	line_number: Mapped[int] = mapped_column(Integer, nullable=False)
	product_id: Mapped[uuid.UUID | None] = mapped_column(
		Uuid,
		ForeignKey("product.id", name="fk_supplier_invoice_lines_product_id_product"),
		nullable=True,
	)
	product_code_snapshot: Mapped[str | None] = mapped_column(String(100), nullable=True)
	description: Mapped[str] = mapped_column(String(500), nullable=False)
	quantity: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False)
	unit_price: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
	subtotal_amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
	tax_type: Mapped[int] = mapped_column(Integer, nullable=False)
	tax_rate: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
	tax_amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
	total_amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)

	# ------------------------------------------------------------------
	# Procurement Lineage (Story 24-4) - stable UUID references
	# ------------------------------------------------------------------
	rfq_item_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
	supplier_quotation_item_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
	purchase_order_line_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
	goods_receipt_line_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)

	# ------------------------------------------------------------------
	# Mismatch and Tolerance-Ready Structures (Story 24-4)
	# ------------------------------------------------------------------
	# Reference values from PO/receipt for comparison
	reference_quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 3), nullable=True)
	reference_unit_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
	reference_total_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)

	# Variance fields (invoice_value - reference_value)
	quantity_variance: Mapped[Decimal | None] = mapped_column(Numeric(18, 3), nullable=True)
	unit_price_variance: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
	total_amount_variance: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)

	# Variance as percentage (for quick review)
	quantity_variance_pct: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
	unit_price_variance_pct: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
	total_amount_variance_pct: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)

	# Comparison basis snapshot (JSON for audit trail)
	comparison_basis_snapshot: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)

	# Mismatch status
	mismatch_status: Mapped[ProcurementMismatchStatus] = mapped_column(
		Enum(
			ProcurementMismatchStatus,
			name="procurement_mismatch_status_enum",
			values_callable=lambda enum_type: [member.value for member in enum_type],
			create_constraint=True,
		),
		default=ProcurementMismatchStatus.NOT_CHECKED,
		nullable=False,
	)

	# Tolerance rule reference (for audit explainability)
	tolerance_rule_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
	tolerance_rule_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)

	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True),
		server_default=func.now(),
		nullable=False,
	)

	supplier_invoice: Mapped[SupplierInvoice] = relationship(back_populates="lines")