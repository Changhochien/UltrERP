"""add replenishment planning fields to inventory_stock

Revision ID: f2c9a7b1d4e6
Revises: c1d2e3f4a5b6
Create Date: 2026-04-11
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "f2c9a7b1d4e6"
down_revision = "c1d2e3f4a5b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "inventory_stock",
        sa.Column("policy_type", sa.String(length=20), server_default="continuous", nullable=False),
    )
    op.add_column(
        "inventory_stock",
        sa.Column("target_stock_qty", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "inventory_stock",
        sa.Column("on_order_qty", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "inventory_stock",
        sa.Column("in_transit_qty", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "inventory_stock",
        sa.Column("reserved_qty", sa.Integer(), server_default="0", nullable=False),
    )
    op.execute(
        "UPDATE inventory_stock SET policy_type = 'periodic' "
        "WHERE COALESCE(review_cycle_days, 0) > 0"
    )


def downgrade() -> None:
    op.drop_column("inventory_stock", "reserved_qty")
    op.drop_column("inventory_stock", "in_transit_qty")
    op.drop_column("inventory_stock", "on_order_qty")
    op.drop_column("inventory_stock", "target_stock_qty")
    op.drop_column("inventory_stock", "policy_type")