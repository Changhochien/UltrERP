"""Warehouse model."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.database import Base

if TYPE_CHECKING:
	from common.models.inventory_stock import InventoryStock


class Warehouse(Base):
	__tablename__ = "warehouse"
	__table_args__ = (
		Index("uq_warehouse_tenant_code", "tenant_id", "code", unique=True),
	)

	id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
	)
	tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
	name: Mapped[str] = mapped_column(String(300), nullable=False)
	code: Mapped[str] = mapped_column(String(50), nullable=False)
	location: Mapped[str | None] = mapped_column(String(500))
	address: Mapped[str | None] = mapped_column(String(500))
	contact_email: Mapped[str | None] = mapped_column(String(255))
	is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), server_default=func.now(), nullable=False,
	)

	inventory_stocks: Mapped[list[InventoryStock]] = relationship(
		back_populates="warehouse",
	)
