"""Approval requests for sensitive writes initiated by non-human actors."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from common.database import Base


class ApprovalRequest(Base):
	__tablename__ = "approval_requests"

	id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
	)
	tenant_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), nullable=False, index=True,
	)
	action: Mapped[str] = mapped_column(String(100), nullable=False)
	entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
	entity_id: Mapped[str | None] = mapped_column(String(100))
	requested_by: Mapped[str] = mapped_column(String(100), nullable=False)
	requested_by_type: Mapped[str] = mapped_column(String(20), nullable=False)
	context: Mapped[dict] = mapped_column(JSON, nullable=False)
	status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
	resolved_by: Mapped[str | None] = mapped_column(String(100))
	resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
	expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), server_default=func.now(), nullable=False, index=True,
	)