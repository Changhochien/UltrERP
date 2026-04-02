"""Audit log model — append-only cross-cutting audit trail."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from common.database import Base


class AuditLog(Base):
	__tablename__ = "audit_log"

	id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
	)
	tenant_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), nullable=False, index=True,
	)
	actor_id: Mapped[str] = mapped_column(String(100), nullable=False)
	actor_type: Mapped[str] = mapped_column(
		String(20), nullable=False, default="user",
	)
	action: Mapped[str] = mapped_column(String(100), nullable=False)
	entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
	entity_id: Mapped[str] = mapped_column(String(100), nullable=False)
	before_state: Mapped[dict | None] = mapped_column(JSON)
	after_state: Mapped[dict | None] = mapped_column(JSON)
	correlation_id: Mapped[str | None] = mapped_column(String(100))
	notes: Mapped[str | None] = mapped_column(Text)
	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), server_default=func.now(), nullable=False,
	)
