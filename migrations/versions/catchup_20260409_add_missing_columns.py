"""catchup: add missing columns from branched migrations

This migration adds all schema features that exist in the model definitions
but were lost due to branching migration history:
- safety_factor, lead_time_days on inventory_stock
- unit_cost on order_lines and invoice_lines
- composite index on stock_adjustment

Revision ID: catchup_20260409
Revises: 0d4102e847f6
Create Date: 2026-04-09
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "catchup_20260409"
down_revision = "0d4102e847f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # inventory_stock: add safety_factor and lead_time_days
    op.add_column(
        "inventory_stock",
        sa.Column("safety_factor", sa.Float(), server_default="0.0", nullable=False),
    )
    op.add_column(
        "inventory_stock",
        sa.Column("lead_time_days", sa.Integer(), server_default="0", nullable=False),
    )

    # order_lines: add unit_cost
    op.add_column(
        "order_lines",
        sa.Column("unit_cost", sa.Numeric(20, 2), nullable=True),
    )

    # invoice_lines: add unit_cost
    op.add_column(
        "invoice_lines",
        sa.Column("unit_cost", sa.Numeric(20, 2), nullable=True),
    )

    # stock_adjustment: add composite index for trend queries
    op.create_index(
        "ix_stock_adjustment_product_warehouse_created",
        "stock_adjustment",
        ["product_id", "warehouse_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_stock_adjustment_product_warehouse_created",
        table_name="stock_adjustment",
    )
    op.drop_column("invoice_lines", "unit_cost")
    op.drop_column("order_lines", "unit_cost")
    op.drop_column("inventory_stock", "lead_time_days")
    op.drop_column("inventory_stock", "safety_factor")
