"""add stock_adjustment history composite index for trend chart queries

Revision ID: f7a2b3c4d5e6
Revises: e4f5a6b7c8d9
Create Date: 2026-04-08 12:30:00.000000
"""

from alembic import op

revision: str = "f7a2b3c4d5e6"
down_revision: str | None = "b2c3d4e5f6a7"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
            "ix_stock_adjustment_product_warehouse_created "
            "ON stock_adjustment (product_id, warehouse_id, created_at)"
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(
            "DROP INDEX CONCURRENTLY IF EXISTS ix_stock_adjustment_product_warehouse_created"
        )
