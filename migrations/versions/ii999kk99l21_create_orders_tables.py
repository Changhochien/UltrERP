"""Create orders and order_lines tables

Revision ID: ii999kk99l21
Revises: hh888jj88k10
Create Date: 2026-04-01

"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = "ii999kk99l21"
down_revision: str | None = "hh888jj88k10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
	op.create_table(
		"orders",
		sa.Column("id", UUID(as_uuid=True), nullable=False),
		sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
		sa.Column("customer_id", UUID(as_uuid=True), nullable=False),
		sa.Column("order_number", sa.String(50), nullable=False),
		sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
		sa.Column("payment_terms_code", sa.String(20), nullable=False, server_default="NET_30"),
		sa.Column("payment_terms_days", sa.Integer(), nullable=False, server_default="30"),
		sa.Column("subtotal_amount", sa.Numeric(20, 2), nullable=True),
		sa.Column("tax_amount", sa.Numeric(20, 2), nullable=True),
		sa.Column("total_amount", sa.Numeric(20, 2), nullable=True),
		sa.Column("invoice_id", UUID(as_uuid=True), nullable=True),
		sa.Column("notes", sa.Text(), nullable=True),
		sa.Column("created_by", sa.String(100), nullable=False),
		sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
		sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
		sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
		sa.PrimaryKeyConstraint("id"),
		sa.ForeignKeyConstraint(
			["customer_id"],
			["customers.id"],
			name="fk_orders_customer_id_customers",
			ondelete="RESTRICT",
		),
		sa.ForeignKeyConstraint(
			["invoice_id"],
			["invoices.id"],
			name="fk_orders_invoice_id_invoices",
		),
	)
	op.create_index("ix_orders_tenant_id", "orders", ["tenant_id"])
	op.create_index("ix_orders_tenant_created", "orders", ["tenant_id", sa.text("created_at DESC")])
	op.create_index("ix_orders_tenant_status", "orders", ["tenant_id", "status"])
	op.create_index("ix_orders_customer_id", "orders", ["customer_id"])
	op.create_index(
		"uq_orders_tenant_order_number",
		"orders",
		["tenant_id", "order_number"],
		unique=True,
	)
	op.create_index(
		"uq_orders_tenant_invoice_id",
		"orders",
		["tenant_id", "invoice_id"],
		unique=True,
		postgresql_where=sa.text("invoice_id IS NOT NULL"),
	)

	op.create_table(
		"order_lines",
		sa.Column("id", UUID(as_uuid=True), nullable=False),
		sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
		sa.Column("order_id", UUID(as_uuid=True), nullable=False),
		sa.Column("product_id", UUID(as_uuid=True), nullable=False),
		sa.Column("line_number", sa.Integer(), nullable=False),
		sa.Column("quantity", sa.Numeric(18, 3), nullable=False),
		sa.Column("unit_price", sa.Numeric(20, 2), nullable=False),
		sa.Column("tax_policy_code", sa.String(20), nullable=False),
		sa.Column("tax_type", sa.Integer(), nullable=False),
		sa.Column("tax_rate", sa.Numeric(6, 4), nullable=False),
		sa.Column("tax_amount", sa.Numeric(20, 2), nullable=False),
		sa.Column("subtotal_amount", sa.Numeric(20, 2), nullable=False),
		sa.Column("total_amount", sa.Numeric(20, 2), nullable=False),
		sa.Column("description", sa.String(500), nullable=False),
		sa.Column("available_stock_snapshot", sa.Integer(), nullable=True),
		sa.Column("backorder_note", sa.String(255), nullable=True),
		sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
		sa.PrimaryKeyConstraint("id"),
		sa.ForeignKeyConstraint(
			["order_id"],
			["orders.id"],
			name="fk_order_lines_order_id_orders",
			ondelete="CASCADE",
		),
		sa.ForeignKeyConstraint(
			["product_id"],
			["product.id"],
			name="fk_order_lines_product_id_product",
			ondelete="RESTRICT",
		),
		sa.CheckConstraint("quantity > 0", name="ck_order_lines_quantity_positive"),
		sa.CheckConstraint("unit_price >= 0", name="ck_order_lines_unit_price_non_negative"),
	)
	op.create_index("ix_order_lines_order_id", "order_lines", ["order_id"])


def downgrade() -> None:
	op.drop_table("order_lines")
	op.drop_table("orders")
