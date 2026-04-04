"""Create egui_submissions table.

Revision ID: rr888tt88u10
Revises: qq777ss77t09
Create Date: 2026-04-04

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "rr888tt88u10"
down_revision: str | None = "qq777ss77t09"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
	op.create_table(
		"egui_submissions",
		sa.Column("id", sa.Uuid(), nullable=False),
		sa.Column("tenant_id", sa.Uuid(), nullable=False),
		sa.Column("invoice_id", sa.Uuid(), nullable=False),
		sa.Column("status", sa.String(length=20), nullable=False),
		sa.Column("mode", sa.String(length=10), nullable=False, server_default=sa.text("'mock'")),
		sa.Column("fia_reference", sa.String(length=100), nullable=True),
		sa.Column("retry_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
		sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=False),
		sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
		sa.Column("last_error_message", sa.Text(), nullable=True),
		sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
		sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
		sa.ForeignKeyConstraint(
			["invoice_id"],
			["invoices.id"],
			name="fk_egui_submissions_invoice_id_invoices",
		),
		sa.PrimaryKeyConstraint("id"),
	)
	op.create_index("ix_egui_submissions_tenant_id", "egui_submissions", ["tenant_id"])
	op.create_index(
		"uq_egui_submissions_tenant_invoice",
		"egui_submissions",
		["tenant_id", "invoice_id"],
		unique=True,
	)


def downgrade() -> None:
	op.drop_index("uq_egui_submissions_tenant_invoice", table_name="egui_submissions")
	op.drop_index("ix_egui_submissions_tenant_id", table_name="egui_submissions")
	op.drop_table("egui_submissions")