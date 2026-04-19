"""add physical count tables

Revision ID: e1b2c3d4f5a6
Revises: d7c1e4b9a2f6
Create Date: 2026-04-18 13:30:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "e1b2c3d4f5a6"
down_revision: str | None = "d7c1e4b9a2f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
	with op.get_context().autocommit_block():
		op.execute(
			"ALTER TYPE reason_code_enum ADD VALUE IF NOT EXISTS 'PHYSICAL_COUNT'"
		)

	op.create_table(
		"physical_count_session",
		sa.Column("id", sa.Uuid(), nullable=False),
		sa.Column("tenant_id", sa.Uuid(), nullable=False),
		sa.Column("warehouse_id", sa.Uuid(), nullable=False),
		sa.Column(
			"status",
			sa.Enum(
				"in_progress",
				"submitted",
				"approved",
				name="physical_count_session_status_enum",
				create_constraint=True,
			),
			nullable=False,
		),
		sa.Column("created_by", sa.String(length=100), nullable=False),
		sa.Column("submitted_by", sa.String(length=100), nullable=True),
		sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
		sa.Column("approved_by", sa.String(length=100), nullable=True),
		sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
		sa.Column(
			"created_at",
			sa.DateTime(timezone=True),
			server_default=sa.text("CURRENT_TIMESTAMP"),
			nullable=False,
		),
		sa.Column(
			"updated_at",
			sa.DateTime(timezone=True),
			server_default=sa.text("CURRENT_TIMESTAMP"),
			nullable=False,
		),
		sa.ForeignKeyConstraint(["warehouse_id"], ["warehouse.id"]),
		sa.PrimaryKeyConstraint("id", name=op.f("pk_physical_count_session")),
	)
	op.create_index(
		op.f("ix_physical_count_session_tenant_id"),
		"physical_count_session",
		["tenant_id"],
		unique=False,
	)
	op.create_index(
		"ix_physical_count_session_tenant_status",
		"physical_count_session",
		["tenant_id", "status"],
		unique=False,
	)
	op.create_index(
		"uq_physical_count_open_session",
		"physical_count_session",
		["tenant_id", "warehouse_id"],
		unique=True,
		postgresql_where=sa.text("status IN ('in_progress', 'submitted')"),
	)

	op.create_table(
		"physical_count_line",
		sa.Column("id", sa.Uuid(), nullable=False),
		sa.Column("session_id", sa.Uuid(), nullable=False),
		sa.Column("product_id", sa.Uuid(), nullable=False),
		sa.Column("system_qty_snapshot", sa.Integer(), nullable=False),
		sa.Column("counted_qty", sa.Integer(), nullable=True),
		sa.Column("variance_qty", sa.Integer(), nullable=True),
		sa.Column("notes", sa.Text(), nullable=True),
		sa.Column(
			"created_at",
			sa.DateTime(timezone=True),
			server_default=sa.text("CURRENT_TIMESTAMP"),
			nullable=False,
		),
		sa.Column(
			"updated_at",
			sa.DateTime(timezone=True),
			server_default=sa.text("CURRENT_TIMESTAMP"),
			nullable=False,
		),
		sa.ForeignKeyConstraint(
			["product_id"],
			["product.id"],
			name=op.f("fk_physical_count_line_product_id_product"),
		),
		sa.ForeignKeyConstraint(
			["session_id"],
			["physical_count_session.id"],
			ondelete="CASCADE",
			name=op.f("fk_physical_count_line_session_id_physical_count_session"),
		),
		sa.PrimaryKeyConstraint("id", name=op.f("pk_physical_count_line")),
	)
	op.create_index(
		"uq_physical_count_line_session_product",
		"physical_count_line",
		["session_id", "product_id"],
		unique=True,
	)


def downgrade() -> None:
	op.drop_index("uq_physical_count_line_session_product", table_name="physical_count_line")
	op.drop_table("physical_count_line")
	op.drop_index("uq_physical_count_open_session", table_name="physical_count_session")
	op.drop_index("ix_physical_count_session_tenant_status", table_name="physical_count_session")
	op.drop_index(op.f("ix_physical_count_session_tenant_id"), table_name="physical_count_session")
	op.drop_table("physical_count_session")
	op.execute("DROP TYPE IF EXISTS physical_count_session_status_enum")