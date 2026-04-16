"""add product snapshots to order lines

Revision ID: 2f7c1b4d9e3a
Revises: 4e1db4c8300d
Create Date: 2026-04-16 18:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "2f7c1b4d9e3a"
down_revision: str | tuple[str, str] | None = "4e1db4c8300d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE order_lines "
        "ADD COLUMN IF NOT EXISTS product_name_snapshot VARCHAR(500)"
    )
    op.execute(
        "ALTER TABLE order_lines "
        "ADD COLUMN IF NOT EXISTS product_category_snapshot VARCHAR(200)"
    )


def downgrade() -> None:
    op.drop_column("order_lines", "product_category_snapshot")
    op.drop_column("order_lines", "product_name_snapshot")