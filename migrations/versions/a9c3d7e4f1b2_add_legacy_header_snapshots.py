"""add legacy header snapshots to imported documents

Revision ID: a9c3d7e4f1b2
Revises: ee994dccf7d9
Create Date: 2026-04-10
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "a9c3d7e4f1b2"
down_revision = "ee994dccf7d9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("legacy_header_snapshot", sa.JSON(), nullable=True))
    op.add_column("invoices", sa.Column("legacy_header_snapshot", sa.JSON(), nullable=True))
    op.add_column(
        "supplier_invoices",
        sa.Column("legacy_header_snapshot", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("supplier_invoices", "legacy_header_snapshot")
    op.drop_column("invoices", "legacy_header_snapshot")
    op.drop_column("orders", "legacy_header_snapshot")