"""add unit_price to supplier_order_line

Revision ID: 1c2d3e4f5a6b
Revises: a4d1c8e7b2f3
Create Date: 2026-04-12
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "1c2d3e4f5a6b"
down_revision = "a4d1c8e7b2f3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "supplier_order_line",
        sa.Column("unit_price", sa.Numeric(precision=20, scale=2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("supplier_order_line", "unit_price")