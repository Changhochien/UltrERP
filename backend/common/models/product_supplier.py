"""Explicit product-to-supplier association model."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from common.database import Base


class ProductSupplier(Base):
	__tablename__ = "product_supplier"
	__table_args__ = (
		Index(
			"uq_product_supplier_tenant_product_supplier",
			"tenant_id", "product_id", "supplier_id",
			unique=True,
		),
		Index(
			"uq_product_supplier_default_per_product",
			"tenant_id", "product_id",
			unique=True,
			postgresql_where=text("is_default"),
		),
	)

	id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
	)
	tenant_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), nullable=False, index=True,
	)
	product_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), ForeignKey("product.id"), nullable=False,
	)
	supplier_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), ForeignKey("supplier.id"), nullable=False,
	)
	unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(19, 4), nullable=True)
	lead_time_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
	is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), server_default=func.now(), nullable=False,
	)
	updated_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True),
		server_default=func.now(),
		onupdate=func.now(),
		nullable=False,
	)