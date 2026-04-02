"""Stock transfer history model."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from common.database import Base


class StockTransferHistory(Base):
	__tablename__ = "stock_transfer_history"

	id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
	)
	tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
	product_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), ForeignKey("product.id"), nullable=False,
	)
	from_warehouse_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), ForeignKey("warehouse.id"), nullable=False,
	)
	to_warehouse_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), ForeignKey("warehouse.id"), nullable=False,
	)
	quantity: Mapped[int] = mapped_column(Integer, nullable=False)
	actor_id: Mapped[str] = mapped_column(String(100), nullable=False)
	notes: Mapped[str | None] = mapped_column(Text)
	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), server_default=func.now(), nullable=False,
	)
