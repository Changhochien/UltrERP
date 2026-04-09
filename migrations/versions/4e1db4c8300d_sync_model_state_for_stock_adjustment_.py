"""sync model state for stock_adjustment index and reorder_alert severity

Revision ID: 4e1db4c8300d
Revises: ee994dccf7d9
Create Date: 2026-04-09 15:24:18.801839

This migration adds:
- The composite index on stock_adjustment(product_id, warehouse_id, created_at)
  that was created by catchup_20260409 but not declared in the model.

- reorder_alert.severity: model was changed from NOT NULL to nullable, matching
  the DB column which has a server_default and allows NULL inserts.
  Also adds server_default='INFO' to match the model default.

The FK constraint changes reported by autogenerate are false positives:
- supplier_invoice_lines, supplier_payments, supplier_payment_allocations all have
  their FKs correctly named and configured in the DB. The differences are in
  ON DELETE behavior (CASCADE vs SET NULL) which we intentionally preserve.
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4e1db4c8300d'
down_revision: str | None = 'ee994dccf7d9'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # stock_adjustment: add the composite index declared in the model
    # IF NOT EXISTS handles the case where catchup_20260409 already created it
    op.create_index(
        "ix_stock_adjustment_product_warehouse_created",
        "stock_adjustment",
        ["product_id", "warehouse_id", "created_at"],
        unique=False,
        if_not_exists=True,
    )

    # reorder_alert: make severity nullable and add server_default to match model
    op.alter_column(
        "reorder_alert",
        "severity",
        nullable=True,
        server_default="INFO",
    )


def downgrade() -> None:
    op.alter_column(
        "reorder_alert",
        "severity",
        nullable=False,
        server_default=None,
    )
    op.drop_index(
        "ix_stock_adjustment_product_warehouse_created",
        table_name="stock_adjustment",
    )
