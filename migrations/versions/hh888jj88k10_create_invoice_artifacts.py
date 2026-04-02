"""Create invoice_artifacts table

Revision ID: hh888jj88k10
Revises: gg777ii77j09
Create Date: 2025-07-17

"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = "hh888jj88k10"
down_revision: str | None = "gg777ii77j09"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
	op.create_table(
		"invoice_artifacts",
		sa.Column("id", UUID(as_uuid=True), nullable=False),
		sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
		sa.Column("invoice_id", UUID(as_uuid=True), nullable=False),
		sa.Column("artifact_kind", sa.String(50), nullable=False),
		sa.Column("object_key", sa.String(500), nullable=False),
		sa.Column("content_type", sa.String(100), nullable=False),
		sa.Column("checksum_sha256", sa.String(64), nullable=False),
		sa.Column("byte_size", sa.Integer(), nullable=False),
		sa.Column("retention_class", sa.String(50), nullable=False, server_default="legal-10y"),
		sa.Column("retention_until", sa.String(10), nullable=False),
		sa.Column("storage_policy", sa.String(50), nullable=False, server_default="standard"),
		sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
		sa.PrimaryKeyConstraint("id"),
		sa.ForeignKeyConstraint(
			["invoice_id"],
			["invoices.id"],
			name="fk_invoice_artifacts_invoice_id",
		),
	)
	op.create_index("ix_invoice_artifacts_tenant_id", "invoice_artifacts", ["tenant_id"])
	op.create_index(
		"uq_invoice_artifacts_invoice_kind",
		"invoice_artifacts",
		["invoice_id", "artifact_kind"],
		unique=True,
	)


def downgrade() -> None:
	op.drop_table("invoice_artifacts")
