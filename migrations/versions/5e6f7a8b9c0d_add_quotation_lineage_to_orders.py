"""add quotation lineage to orders

Revision ID: 5e6f7a8b9c0d
Revises: 4d6e7f8a9b0c
Create Date: 2026-04-22 10:15:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "5e6f7a8b9c0d"
down_revision: str | None = "4d6e7f8a9b0c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("source_quotation_id", sa.Uuid(), nullable=True))
    op.add_column("orders", sa.Column("crm_context_snapshot", sa.JSON(), nullable=True))
    op.create_index(
        "ix_orders_tenant_source_quotation",
        "orders",
        ["tenant_id", "source_quotation_id"],
        unique=False,
    )

    op.add_column("order_lines", sa.Column("source_quotation_line_no", sa.Integer(), nullable=True))
    op.create_index(
        "ix_order_lines_order_source_quotation_line",
        "order_lines",
        ["order_id", "source_quotation_line_no"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_order_lines_order_source_quotation_line", table_name="order_lines")
    op.drop_column("order_lines", "source_quotation_line_no")

    op.drop_index("ix_orders_tenant_source_quotation", table_name="orders")
    op.drop_column("orders", "crm_context_snapshot")
    op.drop_column("orders", "source_quotation_id")