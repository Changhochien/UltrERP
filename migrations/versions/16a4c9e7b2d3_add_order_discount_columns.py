"""add order discount columns

Revision ID: 16a4c9e7b2d3
Revises: 15d9e4c2b7a1
Create Date: 2026-04-19
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "16a4c9e7b2d3"
down_revision = "15d9e4c2b7a1"
branch_labels = None
depends_on = None


def _column_exists(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    added_discount_amount = False
    if not _column_exists("orders", "discount_amount"):
        op.add_column(
            "orders",
            sa.Column(
                "discount_amount",
                sa.Numeric(precision=20, scale=2),
                nullable=False,
                server_default=sa.text("0.00"),
            ),
        )
        added_discount_amount = True

    added_discount_percent = False
    if not _column_exists("orders", "discount_percent"):
        op.add_column(
            "orders",
            sa.Column(
                "discount_percent",
                sa.Numeric(precision=5, scale=4),
                nullable=False,
                server_default=sa.text("0.0000"),
            ),
        )
        added_discount_percent = True

    if added_discount_amount or _column_exists("orders", "discount_amount"):
        op.execute("UPDATE orders SET discount_amount = COALESCE(discount_amount, 0.00);")
    if added_discount_percent or _column_exists("orders", "discount_percent"):
        op.execute("UPDATE orders SET discount_percent = COALESCE(discount_percent, 0.0000);")

    op.alter_column(
        "orders",
        "discount_amount",
        existing_type=sa.Numeric(precision=20, scale=2),
        nullable=False,
        server_default=None,
    )
    op.alter_column(
        "orders",
        "discount_percent",
        existing_type=sa.Numeric(precision=5, scale=4),
        nullable=False,
        server_default=None,
    )


def downgrade() -> None:
    if _column_exists("orders", "discount_percent"):
        op.drop_column("orders", "discount_percent")
    if _column_exists("orders", "discount_amount"):
        op.drop_column("orders", "discount_amount")