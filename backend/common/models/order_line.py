"""Order line model."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.database import Base

if TYPE_CHECKING:
	from common.models.order import Order


class OrderLine(Base):
	__tablename__ = "order_lines"
	__table_args__ = (Index("ix_order_lines_order_source_quotation_line", "order_id", "source_quotation_line_no"),)

	id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
	)
	tenant_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), nullable=False,
	)
	order_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True),
		ForeignKey("orders.id", name="fk_order_lines_order_id_orders", ondelete="CASCADE"),
		nullable=False,
		index=True,
	)
	product_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True),
		ForeignKey("product.id", name="fk_order_lines_product_id_product", ondelete="RESTRICT"),
		nullable=False,
	)
	source_quotation_line_no: Mapped[int | None] = mapped_column(Integer, nullable=True)
	line_number: Mapped[int] = mapped_column(Integer, nullable=False)
	quantity: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False)
	list_unit_price: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False, default=Decimal("0.00"))
	unit_price: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
	unit_cost: Mapped["Decimal | None"] = mapped_column(Numeric(20, 2), nullable=True)
	discount_amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False, default=Decimal("0.00"))
	tax_policy_code: Mapped[str] = mapped_column(String(20), nullable=False)
	tax_type: Mapped[int] = mapped_column(Integer, nullable=False)
	tax_rate: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
	tax_amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
	subtotal_amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
	total_amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
	description: Mapped[str] = mapped_column(String(500), nullable=False)
	product_name_snapshot: Mapped[str | None] = mapped_column(String(500))
	product_category_snapshot: Mapped[str | None] = mapped_column(String(200))
	available_stock_snapshot: Mapped[int | None] = mapped_column(Integer)
	backorder_note: Mapped[str | None] = mapped_column(String(255))
	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), server_default=func.now(), nullable=False,
	)

	order: Mapped[Order] = relationship(back_populates="lines")
