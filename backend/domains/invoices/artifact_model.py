"""Invoice artifact model — stored archive metadata."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from common.database import Base


class InvoiceArtifact(Base):
	__tablename__ = "invoice_artifacts"
	__table_args__ = (
		Index(
			"uq_invoice_artifacts_invoice_kind",
			"invoice_id", "artifact_kind",
			unique=True,
		),
	)

	id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
	)
	tenant_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), nullable=False, index=True,
	)
	invoice_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True),
		ForeignKey("invoices.id", name="fk_invoice_artifacts_invoice_id"),
		nullable=False,
	)
	artifact_kind: Mapped[str] = mapped_column(
		String(50), nullable=False,
	)
	object_key: Mapped[str] = mapped_column(
		String(500), nullable=False,
	)
	content_type: Mapped[str] = mapped_column(
		String(100), nullable=False,
	)
	checksum_sha256: Mapped[str] = mapped_column(
		String(64), nullable=False,
	)
	byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
	retention_class: Mapped[str] = mapped_column(
		String(50), nullable=False, default="legal-10y",
	)
	retention_until: Mapped[str] = mapped_column(
		String(10), nullable=False,
	)
	storage_policy: Mapped[str] = mapped_column(
		String(50), nullable=False, default="standard",
	)
	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), server_default=func.now(), nullable=False,
	)
