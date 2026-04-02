"""Create invoice, invoice_lines, and invoice_number_ranges tables

Revision ID: ee5b6cc6d7e8
Revises: ee555gg55h87
Create Date: 2025-07-17

"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "ee5b6cc6d7e8"
down_revision: str | None = "ee555gg55h87"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
	op.create_table(
		"invoice_number_ranges",
		sa.Column("id", sa.Uuid(), nullable=False),
		sa.Column("tenant_id", sa.Uuid(), nullable=False),
		sa.Column("prefix", sa.String(2), nullable=False),
		sa.Column("start_number", sa.Integer(), nullable=False),
		sa.Column("end_number", sa.Integer(), nullable=False),
		sa.Column("next_number", sa.Integer(), nullable=False),
		sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
		sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
		sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
		sa.PrimaryKeyConstraint("id"),
	)
	op.create_index("ix_invoice_number_ranges_tenant_id", "invoice_number_ranges", ["tenant_id"])
	op.create_index(
		"uq_invoice_number_ranges_tenant_prefix_start_end",
		"invoice_number_ranges",
		["tenant_id", "prefix", "start_number", "end_number"],
		unique=True,
	)

	op.create_table(
		"invoices",
		sa.Column("id", sa.Uuid(), nullable=False),
		sa.Column("tenant_id", sa.Uuid(), nullable=False),
		sa.Column("invoice_number", sa.String(10), nullable=False),
		sa.Column("invoice_date", sa.Date(), nullable=False),
		sa.Column("customer_id", sa.Uuid(), nullable=False),
		sa.Column("buyer_type", sa.String(10), nullable=False),
		sa.Column("buyer_identifier_snapshot", sa.String(10), nullable=False),
		sa.Column("currency_code", sa.String(3), nullable=False, server_default=sa.text("'TWD'")),
		sa.Column("subtotal_amount", sa.Numeric(20, 2), nullable=False),
		sa.Column("tax_amount", sa.Numeric(20, 2), nullable=False),
		sa.Column("total_amount", sa.Numeric(20, 2), nullable=False),
		sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'issued'")),
		sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
		sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
		sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
		sa.PrimaryKeyConstraint("id"),
		sa.ForeignKeyConstraint(
			["customer_id"],
			["customers.id"],
			name="fk_invoices_customer_id_customers",
		),
	)
	op.create_index("ix_invoices_tenant_id", "invoices", ["tenant_id"])
	op.create_index(
		"uq_invoices_tenant_invoice_number",
		"invoices",
		["tenant_id", "invoice_number"],
		unique=True,
	)

	op.create_table(
		"invoice_lines",
		sa.Column("id", sa.Uuid(), nullable=False),
		sa.Column("invoice_id", sa.Uuid(), nullable=False),
		sa.Column("tenant_id", sa.Uuid(), nullable=False),
		sa.Column("line_number", sa.Integer(), nullable=False),
		sa.Column("product_id", sa.Uuid(), nullable=True),
		sa.Column("product_code_snapshot", sa.String(100), nullable=True),
		sa.Column("description", sa.String(500), nullable=False),
		sa.Column("quantity", sa.Numeric(18, 3), nullable=False),
		sa.Column("unit_price", sa.Numeric(20, 2), nullable=False),
		sa.Column("subtotal_amount", sa.Numeric(20, 2), nullable=False),
		sa.Column("tax_type", sa.Integer(), nullable=False),
		sa.Column("tax_rate", sa.Numeric(6, 4), nullable=False),
		sa.Column("tax_amount", sa.Numeric(20, 2), nullable=False),
		sa.Column("total_amount", sa.Numeric(20, 2), nullable=False),
		sa.Column("zero_tax_rate_reason", sa.String(50), nullable=True),
		sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
		sa.PrimaryKeyConstraint("id"),
		sa.ForeignKeyConstraint(
			["invoice_id"],
			["invoices.id"],
			name="fk_invoice_lines_invoice_id_invoices",
		),
	)
	op.create_index("ix_invoice_lines_tenant_id", "invoice_lines", ["tenant_id"])
	op.create_index("ix_invoice_lines_invoice_id", "invoice_lines", ["invoice_id"])
	op.create_index(
		"uq_invoice_lines_invoice_id_line_number",
		"invoice_lines",
		["invoice_id", "line_number"],
		unique=True,
	)


def downgrade() -> None:
	op.drop_table("invoice_lines")
	op.drop_table("invoices")
	op.drop_table("invoice_number_ranges")
