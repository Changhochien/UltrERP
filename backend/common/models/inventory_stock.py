"""Inventory stock model — per-warehouse stock level."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.database import Base

if TYPE_CHECKING:
	from common.models.product import Product
	from common.models.warehouse import Warehouse


class InventoryStock(Base):
	__tablename__ = "inventory_stock"
	__table_args__ = (
		Index(
			"uq_inventory_stock_tenant_product_warehouse",
			"tenant_id", "product_id", "warehouse_id",
			unique=True,
		),
		Index(
			"ix_inventory_stock_warehouse_product",
			"warehouse_id", "product_id",
		),
	)

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
	quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
	reorder_point: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
	safety_factor: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
	lead_time_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
	review_cycle_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
	updated_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True),
		server_default=func.now(),
		onupdate=func.now(),
		nullable=False,
	)

	product: Mapped[Product] = relationship(back_populates="inventory_stocks")
	warehouse: Mapped[Warehouse] = relationship(
		back_populates="inventory_stocks",
	)
