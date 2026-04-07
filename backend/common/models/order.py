"""Order model."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.database import Base

if TYPE_CHECKING:
	from common.models.order_line import OrderLine
	from domains.customers.models import Customer


class Order(Base):
	__tablename__ = "orders"
	__table_args__ = (
		Index("uq_orders_tenant_order_number", "tenant_id", "order_number", unique=True),
		Index("ix_orders_tenant_created", "tenant_id", "created_at"),
		Index("ix_orders_tenant_status", "tenant_id", "status"),
	)

	id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
	)
	tenant_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), nullable=False, index=True,
	)
	customer_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True),
		ForeignKey("customers.id", name="fk_orders_customer_id_customers", ondelete="RESTRICT"),
		nullable=False,
	)
	order_number: Mapped[str] = mapped_column(String(50), nullable=False)
	status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
	payment_terms_code: Mapped[str] = mapped_column(String(20), nullable=False, default="NET_30")
	payment_terms_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
	subtotal_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 2))
	discount_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), default=Decimal("0.00"))
	discount_percent: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), default=Decimal("0.0000"))
	tax_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 2))
	total_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 2))
	invoice_id: Mapped[uuid.UUID | None] = mapped_column(
		UUID(as_uuid=True),
		ForeignKey("invoices.id", name="fk_orders_invoice_id_invoices"),
		nullable=True,
	)
	notes: Mapped[str | None] = mapped_column(Text)
	created_by: Mapped[str] = mapped_column(String(100), nullable=False)
	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), server_default=func.now(), nullable=False,
	)
	updated_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False,
	)
	confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

	lines: Mapped[list[OrderLine]] = relationship(
		back_populates="order",
		cascade="all, delete-orphan",
		order_by="OrderLine.line_number",
	)
	customer: Mapped[Customer] = relationship()
