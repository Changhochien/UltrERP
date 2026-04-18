"""Physical inventory count line model."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Text, func
from sqlalchemy.dialects.postgresql import UUID

from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.database import Base

if TYPE_CHECKING:
	from common.models.physical_count_session import PhysicalCountSession
	from common.models.product import Product


class PhysicalCountLine(Base):
	__tablename__ = "physical_count_line"
	__table_args__ = (
		Index(
			"uq_physical_count_line_session_product",
			"session_id",
			"product_id",
			unique=True,
		),
	)

	id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
	)
	session_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True),
		ForeignKey("physical_count_session.id", ondelete="CASCADE"),
		nullable=False,
	)
	product_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), ForeignKey("product.id"), nullable=False,
	)
	system_qty_snapshot: Mapped[int] = mapped_column(Integer, nullable=False)
	counted_qty: Mapped[int | None] = mapped_column(Integer)
	variance_qty: Mapped[int | None] = mapped_column(Integer)
	notes: Mapped[str | None] = mapped_column(Text)
	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), server_default=func.now(), nullable=False,
	)
	updated_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True),
		server_default=func.now(),
		onupdate=func.now(),
		nullable=False,
	)

	session: Mapped[PhysicalCountSession] = relationship(back_populates="lines")
	product: Mapped[Product] = relationship()