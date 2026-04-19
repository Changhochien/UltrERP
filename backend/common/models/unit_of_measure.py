"""Unit of measure master model."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from common.database import Base


class UnitOfMeasure(Base):
	__tablename__ = "unit_of_measure"
	__table_args__ = (
		Index("uq_unit_of_measure_tenant_code", "tenant_id", "code", unique=True),
	)

	id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
	)
	tenant_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), nullable=False, index=True,
	)
	code: Mapped[str] = mapped_column(String(50), nullable=False)
	name: Mapped[str] = mapped_column(String(200), nullable=False)
	decimal_places: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
	is_active: Mapped[bool] = mapped_column(
		Boolean, default=True, nullable=False,
	)
	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), server_default=func.now(), nullable=False,
	)
	updated_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True),
		server_default=func.now(),
		onupdate=func.now(),
		nullable=False,
	)