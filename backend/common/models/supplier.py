"""Supplier model."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from common.database import Base


class Supplier(Base):
	__tablename__ = "supplier"

	id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
	)
	tenant_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), nullable=False, index=True,
	)
	name: Mapped[str] = mapped_column(String(300), nullable=False)
	contact_email: Mapped[str | None] = mapped_column(String(255))
	phone: Mapped[str | None] = mapped_column(String(50))
	address: Mapped[str | None] = mapped_column(String(500))
	default_lead_time_days: Mapped[int | None] = mapped_column(Integer)
	is_active: Mapped[bool] = mapped_column(
		Boolean, default=True, nullable=False,
	)
	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), server_default=func.now(), nullable=False,
	)
