"""add customer default discount percent

Revision ID: 17a6c4e5b8d9
Revises: 16b4c3d2e1f0
Create Date: 2026-04-20
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "17a6c4e5b8d9"
down_revision = "16b4c3d2e1f0"
branch_labels = None
depends_on = None


def _column_exists(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    added_default_discount_percent = False
    if not _column_exists("customers", "default_discount_percent"):
        op.add_column(
            "customers",
            sa.Column(
                "default_discount_percent",
                sa.Numeric(precision=5, scale=4),
                nullable=False,
                server_default=sa.text("0.0000"),
            ),
        )
        added_default_discount_percent = True

    if added_default_discount_percent or _column_exists("customers", "default_discount_percent"):
        op.execute(
            "UPDATE customers "
            "SET default_discount_percent = 0.0000 "
            "WHERE default_discount_percent IS NULL;"
        )

    if added_default_discount_percent or _column_exists("customers", "default_discount_percent"):
        op.alter_column(
            "customers",
            "default_discount_percent",
            existing_type=sa.Numeric(precision=5, scale=4),
            nullable=False,
            server_default=None,
        )


def downgrade() -> None:
    if _column_exists("customers", "default_discount_percent"):
        op.drop_column("customers", "default_discount_percent")