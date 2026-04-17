"""Supplier order and order line models."""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Index, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.database import Base


class SupplierOrderStatus(str, enum.Enum):
	PENDING = "pending"
	CONFIRMED = "confirmed"
	SHIPPED = "shipped"
	PARTIALLY_RECEIVED = "partially_received"
	RECEIVED = "received"
	CANCELLED = "cancelled"


class SupplierOrder(Base):
	__tablename__ = "supplier_order"
	__table_args__ = (
		Index("ix_supplier_order_status_date", "status", "created_at"),
	)

	id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
	)
	tenant_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), nullable=False, index=True,
	)
	supplier_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), ForeignKey("supplier.id"), nullable=False,
	)
	order_number: Mapped[str] = mapped_column(String(100), nullable=False)
	status: Mapped[SupplierOrderStatus] = mapped_column(
		Enum(
			SupplierOrderStatus,
			name="supplier_order_status_enum",
			create_constraint=True,
		),
		default=SupplierOrderStatus.PENDING,
		nullable=False,
	)
	order_date: Mapped[date] = mapped_column(Date, nullable=False)
	expected_arrival_date: Mapped[date | None] = mapped_column(Date)
	received_date: Mapped[date | None] = mapped_column(Date)
	created_by: Mapped[str] = mapped_column(String(100), nullable=False)
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

	lines: Mapped[list[SupplierOrderLine]] = relationship(
		back_populates="order", cascade="all, delete-orphan",
	)


class SupplierOrderLine(Base):
	__tablename__ = "supplier_order_line"

	id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
	)
	order_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True),
		ForeignKey("supplier_order.id"),
		nullable=False,
	)
	product_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), ForeignKey("product.id"), nullable=False,
	)
	warehouse_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), ForeignKey("warehouse.id"), nullable=False,
	)
	quantity_ordered: Mapped[int] = mapped_column(Integer, nullable=False)
	unit_price: Mapped["Decimal | None"] = mapped_column(Numeric(20, 2), nullable=True)
	quantity_received: Mapped[int] = mapped_column(
		Integer, default=0, nullable=False,
	)
	notes: Mapped[str | None] = mapped_column(Text)

	order: Mapped[SupplierOrder] = relationship(back_populates="lines")
