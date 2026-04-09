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


def upgrade() -> None:
    op.add_column(
        "order_lines",
        sa.Column("unit_cost", sa.Numeric(precision=20, scale=2), nullable=True),
    )
    op.add_column(
        "invoice_lines",
        sa.Column("unit_cost", sa.Numeric(precision=20, scale=2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("order_lines", "unit_cost")
    op.drop_column("invoice_lines", "unit_cost")
