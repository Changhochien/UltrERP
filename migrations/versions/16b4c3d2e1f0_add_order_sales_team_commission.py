"""add order sales team commission fields

Revision ID: 16b4c3d2e1f0
Revises: 15d9e4c2b7a1
Create Date: 2026-04-20
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "16b4c3d2e1f0"
down_revision = "15d9e4c2b7a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("sales_team", sa.JSON(), nullable=True))
    op.add_column(
        "orders",
        sa.Column(
            "total_commission",
            sa.Numeric(20, 2),
            nullable=False,
            server_default="0.00",
        ),
    )


def downgrade() -> None:
    op.drop_column("orders", "total_commission")
    op.drop_column("orders", "sales_team")