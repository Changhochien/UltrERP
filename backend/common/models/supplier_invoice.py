"""Supplier invoice and supplier invoice line models."""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
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
	status: Mapped[SupplierInvoiceStatus] = mapped_column(
		Enum(
			SupplierInvoiceStatus,
			name="supplier_invoice_status_enum",
			create_constraint=True,
		),
		default=SupplierInvoiceStatus.OPEN,
		nullable=False,
	)
	notes: Mapped[str | None] = mapped_column(Text)
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
	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True),
		server_default=func.now(),
		nullable=False,
	)

	supplier_invoice: Mapped[SupplierInvoice] = relationship(back_populates="lines")