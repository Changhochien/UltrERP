"""User model for authentication and RBAC."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from common.database import Base


class User(Base):
	__tablename__ = "users"
	__table_args__ = (
		UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
	)

	id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
	)
	tenant_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), nullable=False, index=True,
	)
	email: Mapped[str] = mapped_column(String(255), nullable=False)
	password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
	display_name: Mapped[str] = mapped_column(String(200), nullable=False)
	role: Mapped[str] = mapped_column(String(20), nullable=False)
	status: Mapped[str] = mapped_column(
		String(20), nullable=False, default="active",
	)
	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), server_default=func.now(), nullable=False,
	)
	updated_at: Mapped[datetime | None] = mapped_column(
		DateTime(timezone=True), onupdate=func.now(),
	)
