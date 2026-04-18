"""Product model."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, Index, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.database import Base

if TYPE_CHECKING:
	from common.models.inventory_stock import InventoryStock
	from common.models.stock_adjustment import StockAdjustment


class Product(Base):
	__tablename__ = "product"
	__table_args__ = (
		Index("uq_product_tenant_code", "tenant_id", "code", unique=True),
	)

	id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
	)
	tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
	code: Mapped[str] = mapped_column(String(100), nullable=False)
	name: Mapped[str] = mapped_column(String(500), nullable=False)
	category: Mapped[str | None] = mapped_column(String(200))
	description: Mapped[str | None] = mapped_column(Text)
	unit: Mapped[str] = mapped_column(String(50), default="pcs", nullable=False)
	standard_cost: Mapped["Decimal | None"] = mapped_column(Numeric(19, 4), nullable=True)
	status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
	legacy_master_snapshot: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
	search_vector: Mapped[Any] = mapped_column(TSVECTOR, nullable=True)
	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), server_default=func.now(), nullable=False,
	)
	updated_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True),
		server_default=func.now(),
		onupdate=func.now(),
		nullable=False,
	)

	inventory_stocks: Mapped[list[InventoryStock]] = relationship(
		back_populates="product",
	)
	adjustments: Mapped[list[StockAdjustment]] = relationship(
		back_populates="product",
	)
