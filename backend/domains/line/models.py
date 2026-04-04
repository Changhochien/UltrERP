"""LINE integration database models."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from common.database import Base


class LineCustomerMapping(Base):
	__tablename__ = "line_customer_mappings"
	__table_args__ = (
		UniqueConstraint("tenant_id", "line_user_id", name="uq_line_mapping_tenant_user"),
	)

	id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid(),
	)
	tenant_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), nullable=False, index=True,
	)
	line_user_id: Mapped[str] = mapped_column(
		String(64), nullable=False,
	)
	customer_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False,
	)
	display_name: Mapped[str | None] = mapped_column(
		String(200), nullable=True,
	)
	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), server_default=func.now(),
	)
	updated_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
	)
