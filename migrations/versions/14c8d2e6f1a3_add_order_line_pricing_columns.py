"""add missing order_line pricing columns

Revision ID: 14c8d2e6f1a3
Revises: 13a3b28ab317
Create Date: 2026-04-19

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "14c8d2e6f1a3"
down_revision = "13a3b28ab317"
branch_labels = None
depends_on = None


def _column_exists(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    added_list_unit_price = False
    if not _column_exists("order_lines", "list_unit_price"):
        op.add_column(
            "order_lines",
            sa.Column(
                "list_unit_price",
                sa.Numeric(precision=20, scale=2),
                nullable=False,
                server_default=sa.text("0.00"),
            ),
        )
        added_list_unit_price = True

    if added_list_unit_price:
        op.execute("UPDATE order_lines SET list_unit_price = unit_price;")

    op.alter_column(
        "order_lines",
        "list_unit_price",
        existing_type=sa.Numeric(precision=20, scale=2),
        nullable=False,
        server_default=None,
    )

    added_discount_amount = False
    if not _column_exists("order_lines", "discount_amount"):
        op.add_column(
            "order_lines",
            sa.Column(
                "discount_amount",
                sa.Numeric(precision=20, scale=2),
                nullable=False,
                server_default=sa.text("0.00"),
            ),
        )
        added_discount_amount = True

    if added_discount_amount:
        op.execute("UPDATE order_lines SET discount_amount = 0.00;")

    op.alter_column(
        "order_lines",
        "discount_amount",
        existing_type=sa.Numeric(precision=20, scale=2),
        nullable=False,
        server_default=None,
    )


def downgrade() -> None:
    if _column_exists("order_lines", "discount_amount"):
        op.drop_column("order_lines", "discount_amount")
    if _column_exists("order_lines", "list_unit_price"):
        op.drop_column("order_lines", "list_unit_price")