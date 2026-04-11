"""add legacy master snapshots to imported master data

Revision ID: d9e1a2b3c4d5
Revises: c4f8b91d2e6a
Create Date: 2026-04-10
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "d9e1a2b3c4d5"
down_revision = "c4f8b91d2e6a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("customers", sa.Column("legacy_master_snapshot", sa.JSON(), nullable=True))
    op.add_column("supplier", sa.Column("legacy_master_snapshot", sa.JSON(), nullable=True))
    op.add_column("product", sa.Column("legacy_master_snapshot", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("product", "legacy_master_snapshot")
    op.drop_column("supplier", "legacy_master_snapshot")
    op.drop_column("customers", "legacy_master_snapshot")