"""add safety_factor and lead_time_days to inventory_stock

Revision ID: b2c3d4e5f6a7
Revises: 7a3b5c8d1e9f
Create Date: 2026-04-09

"""
from alembic import op
import sqlalchemy as sa


revision = "b2c3d4e5f6a7"
down_revision = "7a3b5c8d1e9f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "inventory_stock",
        sa.Column("safety_factor", sa.Float(), server_default="0.0", nullable=False),
    )
    op.add_column(
        "inventory_stock",
        sa.Column("lead_time_days", sa.Integer(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("inventory_stock", "lead_time_days")
    op.drop_column("inventory_stock", "safety_factor")
