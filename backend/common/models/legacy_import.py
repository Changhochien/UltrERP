"""Legacy import control tables for batch-level staging runs."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from common.database import Base


class LegacyImportRun(Base):
	__tablename__ = "legacy_import_runs"

	id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
	)
	tenant_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), nullable=False, index=True,
	)
	batch_id: Mapped[str] = mapped_column(String(120), nullable=False)
	source_path: Mapped[str] = mapped_column(Text, nullable=False)
	target_schema: Mapped[str] = mapped_column(
		String(63), nullable=False, default="raw_legacy",
	)
	attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
	requested_tables: Mapped[list[str] | None] = mapped_column(JSON)
	status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")
	error_message: Mapped[str | None] = mapped_column(Text)
	started_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), server_default=func.now(), nullable=False,
	)
	completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), server_default=func.now(), nullable=False,
	)

	__table_args__ = (
		UniqueConstraint(
			"tenant_id",
			"batch_id",
			"attempt_number",
			name="uq_legacy_import_runs_tenant_batch_attempt",
		),
	)


class LegacyImportTableRun(Base):
	__tablename__ = "legacy_import_table_runs"

	id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
	)
	run_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), ForeignKey("legacy_import_runs.id"), nullable=False, index=True,
	)
	table_name: Mapped[str] = mapped_column(String(120), nullable=False)
	source_file: Mapped[str] = mapped_column(Text, nullable=False)
	expected_row_count: Mapped[int | None] = mapped_column(Integer)
	loaded_row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
	column_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
	status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")
	error_message: Mapped[str | None] = mapped_column(Text)
	started_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), server_default=func.now(), nullable=False,
	)
	completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

	__table_args__ = (
		UniqueConstraint("run_id", "table_name", name="uq_legacy_import_table_runs_run_table"),
	)