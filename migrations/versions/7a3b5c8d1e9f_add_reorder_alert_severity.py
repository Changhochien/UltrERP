"""add severity to reorder_alert

Revision ID: 7a3b5c8d1e9f
Revises:
Create Date: 2026-04-08

"""
from alembic import op
import sqlalchemy as sa


revision = "7a3b5c8d1e9f"
down_revision = "c8d4f7a1e2b3"  # chains after runtime stability indexes; reorder_alert table was created in 06b5cc5dbfa6
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "reorder_alert",
        sa.Column("severity", sa.String(length=20), nullable=True, server_default=None),
    )


def downgrade() -> None:
    op.drop_column("reorder_alert", "severity")
