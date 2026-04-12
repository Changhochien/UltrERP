"""add planning_horizon_days to inventory_stock

Revision ID: a4d1c8e7b2f3
Revises: f2c9a7b1d4e6
Create Date: 2026-04-11
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "a4d1c8e7b2f3"
down_revision = "f2c9a7b1d4e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "inventory_stock",
        sa.Column("planning_horizon_days", sa.Integer(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("inventory_stock", "planning_horizon_days")