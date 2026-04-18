"""Physical inventory count session model."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.database import Base

if TYPE_CHECKING:
	from common.models.physical_count_line import PhysicalCountLine
	from common.models.warehouse import Warehouse


class PhysicalCountSessionStatus(str, enum.Enum):
	IN_PROGRESS = "in_progress"
	SUBMITTED = "submitted"
	APPROVED = "approved"


class PhysicalCountSession(Base):
	__tablename__ = "physical_count_session"
	__table_args__ = (
		Index(
			"ix_physical_count_session_tenant_status",
			"tenant_id",
			"status",
		),
		Index(
			"uq_physical_count_open_session",
			"tenant_id",
			"warehouse_id",
			unique=True,
			postgresql_where=text("status IN ('in_progress', 'submitted')"),
		),
	)

	id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
	)
	tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
	warehouse_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), ForeignKey("warehouse.id"), nullable=False,
	)
	status: Mapped[PhysicalCountSessionStatus] = mapped_column(
		Enum(
			PhysicalCountSessionStatus,
			name="physical_count_session_status_enum",
			create_constraint=True,
		),
		default=PhysicalCountSessionStatus.IN_PROGRESS,
		nullable=False,
	)
	created_by: Mapped[str] = mapped_column(String(100), nullable=False)
	submitted_by: Mapped[str | None] = mapped_column(String(100))
	submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
	approved_by: Mapped[str | None] = mapped_column(String(100))
	approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), server_default=func.now(), nullable=False,
	)
	updated_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True),
		server_default=func.now(),
		onupdate=func.now(),
		nullable=False,
	)

	warehouse: Mapped[Warehouse] = relationship()
	lines: Mapped[list[PhysicalCountLine]] = relationship(
		back_populates="session",
		cascade="all, delete-orphan",
	)