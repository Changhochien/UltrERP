"""Stock adjustment model and ReasonCode enum."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.database import Base

if TYPE_CHECKING:
	from common.models.product import Product


class ReasonCode(str, enum.Enum):
	"""Reason codes for stock adjustments.

	User-selectable: RECEIVED, DAMAGED, RETURNED, CORRECTION, OTHER
	System-only: SUPPLIER_DELIVERY, TRANSFER_OUT, TRANSFER_IN
	"""

	RECEIVED = "received"
	DAMAGED = "damaged"
	RETURNED = "returned"
	CORRECTION = "correction"
	OTHER = "other"
	SUPPLIER_DELIVERY = "supplier_delivery"
	TRANSFER_OUT = "transfer_out"
	TRANSFER_IN = "transfer_in"
	SALES_RESERVATION = "sales_reservation"
	SALES_RELEASE = "sales_release"

	@classmethod
	def user_selectable(cls) -> list[ReasonCode]:
		return [cls.RECEIVED, cls.DAMAGED, cls.RETURNED, cls.CORRECTION, cls.OTHER]

	@classmethod
	def system_only(cls) -> list[ReasonCode]:
		return [
			cls.SUPPLIER_DELIVERY,
			cls.TRANSFER_OUT,
			cls.TRANSFER_IN,
			cls.SALES_RESERVATION,
			cls.SALES_RELEASE,
		]


class StockAdjustment(Base):
	__tablename__ = "stock_adjustment"

	id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
	)
	tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
	product_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), ForeignKey("product.id"), nullable=False,
	)
	warehouse_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), ForeignKey("warehouse.id"), nullable=False,
	)
	quantity_change: Mapped[int] = mapped_column(Integer, nullable=False)
	reason_code: Mapped[ReasonCode] = mapped_column(
		Enum(ReasonCode, name="reason_code_enum", create_constraint=True),
		nullable=False,
	)
	actor_id: Mapped[str] = mapped_column(String(100), nullable=False)
	notes: Mapped[str | None] = mapped_column(Text)
	transfer_id: Mapped[uuid.UUID | None] = mapped_column(
		UUID(as_uuid=True), nullable=True,
	)
	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), server_default=func.now(), nullable=False,
	)

	product: Mapped[Product] = relationship(back_populates="adjustments")
