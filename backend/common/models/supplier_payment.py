"""Supplier payment and payment allocation models."""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Index, Numeric, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.database import Base

if TYPE_CHECKING:
	from common.models.supplier import Supplier
	from common.models.supplier_invoice import SupplierInvoice


class SupplierPaymentKind(str, enum.Enum):
	PREPAYMENT = "prepayment"
	SPECIAL_PAYMENT = "special_payment"
	ADJUSTMENT = "adjustment"


class SupplierPaymentStatus(str, enum.Enum):
	UNAPPLIED = "unapplied"
	PARTIALLY_APPLIED = "partially_applied"
	APPLIED = "applied"
	VOIDED = "voided"


class SupplierPaymentAllocationKind(str, enum.Enum):
	INVOICE_SETTLEMENT = "invoice_settlement"
	PREPAYMENT_APPLICATION = "prepayment_application"
	REVERSAL = "reversal"


class SupplierPayment(Base):
	__tablename__ = "supplier_payments"
	__table_args__ = (
		Index(
			"uq_supplier_payments_tenant_supplier_payment_number",
			"tenant_id",
			"supplier_id",
			"payment_number",
			unique=True,
		),
		Index("ix_supplier_payments_tenant_payment_date", "tenant_id", "payment_date"),
		Index("ix_supplier_payments_tenant_status", "tenant_id", "status"),
	)

	id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
	tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
	supplier_id: Mapped[uuid.UUID] = mapped_column(
		Uuid,
		ForeignKey("supplier.id", name="fk_supplier_payments_supplier_id_supplier"),
		nullable=False,
	)
	payment_number: Mapped[str] = mapped_column(String(100), nullable=False)
	payment_kind: Mapped[SupplierPaymentKind] = mapped_column(
		Enum(
			SupplierPaymentKind,
			name="supplier_payment_kind_enum",
			create_constraint=True,
		),
		default=SupplierPaymentKind.PREPAYMENT,
		nullable=False,
	)
	status: Mapped[SupplierPaymentStatus] = mapped_column(
		Enum(
			SupplierPaymentStatus,
			name="supplier_payment_status_enum",
			create_constraint=True,
		),
		default=SupplierPaymentStatus.UNAPPLIED,
		nullable=False,
	)
	currency_code: Mapped[str] = mapped_column(String(3), nullable=False, default="TWD")
	payment_date: Mapped[date] = mapped_column(Date, nullable=False)
	gross_amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
	payment_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
	reference_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
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

	supplier: Mapped[Supplier] = relationship()
	allocations: Mapped[list[SupplierPaymentAllocation]] = relationship(
		back_populates="supplier_payment",
		cascade="all, delete-orphan",
		order_by="SupplierPaymentAllocation.allocation_date",
	)


class SupplierPaymentAllocation(Base):
	__tablename__ = "supplier_payment_allocations"
	__table_args__ = (
		Index(
			"ix_supplier_payment_allocations_tenant_payment",
			"tenant_id",
			"supplier_payment_id",
		),
		Index(
			"ix_supplier_payment_allocations_tenant_invoice",
			"tenant_id",
			"supplier_invoice_id",
		),
	)

	id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
	tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
	supplier_payment_id: Mapped[uuid.UUID] = mapped_column(
		Uuid,
		ForeignKey(
			"supplier_payments.id",
			name="fk_supplier_payment_allocations_payment_id_supplier_payments",
		),
		nullable=False,
	)
	supplier_invoice_id: Mapped[uuid.UUID] = mapped_column(
		Uuid,
		ForeignKey(
			"supplier_invoices.id",
			name="fk_supplier_payment_allocations_invoice_id_supplier_invoices",
		),
		nullable=False,
	)
	allocation_date: Mapped[date] = mapped_column(Date, nullable=False)
	applied_amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
	allocation_kind: Mapped[SupplierPaymentAllocationKind] = mapped_column(
		Enum(
			SupplierPaymentAllocationKind,
			name="supplier_payment_allocation_kind_enum",
			create_constraint=True,
		),
		default=SupplierPaymentAllocationKind.INVOICE_SETTLEMENT,
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

	supplier_payment: Mapped[SupplierPayment] = relationship(back_populates="allocations")
	supplier_invoice: Mapped[SupplierInvoice] = relationship(back_populates="payment_allocations")