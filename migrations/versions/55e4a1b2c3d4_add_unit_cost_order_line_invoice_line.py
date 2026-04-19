"""add unit_cost to OrderLine InvoiceLine

Revision ID: 55e4a1b2c3d4
Revises: b2c3d4e5f6a7
Create Date: 2026-04-08

"""
from alembic import op
import sqlalchemy as sa


revision = "55e4a1b2c3d4"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def _column_exists(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    if not _column_exists("order_lines", "unit_cost"):
        op.add_column(
            "order_lines",
            sa.Column("unit_cost", sa.Numeric(precision=20, scale=2), nullable=True),
        )
    if not _column_exists("invoice_lines", "unit_cost"):
        op.add_column(
            "invoice_lines",
            sa.Column("unit_cost", sa.Numeric(precision=20, scale=2), nullable=True),
        )


def downgrade() -> None:
    if _column_exists("order_lines", "unit_cost"):
        op.drop_column("order_lines", "unit_cost")
    if _column_exists("invoice_lines", "unit_cost"):
        op.drop_column("invoice_lines", "unit_cost")
