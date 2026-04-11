"""add review_cycle_days to inventory_stock

Revision ID: c1d2e3f4a5b6
Revises: b6c1d2e3f4a5
Create Date: 2026-04-11
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "c1d2e3f4a5b6"
down_revision = "b6c1d2e3f4a5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "inventory_stock",
        sa.Column("review_cycle_days", sa.Integer(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("inventory_stock", "review_cycle_days")
