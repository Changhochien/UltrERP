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


def _column_exists(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    if not _column_exists("inventory_stock", "safety_factor"):
        op.add_column(
            "inventory_stock",
            sa.Column("safety_factor", sa.Float(), server_default="0.0", nullable=False),
        )
    if not _column_exists("inventory_stock", "lead_time_days"):
        op.add_column(
            "inventory_stock",
            sa.Column("lead_time_days", sa.Integer(), server_default="0", nullable=False),
        )


def downgrade() -> None:
    if _column_exists("inventory_stock", "lead_time_days"):
        op.drop_column("inventory_stock", "lead_time_days")
    if _column_exists("inventory_stock", "safety_factor"):
        op.drop_column("inventory_stock", "safety_factor")
