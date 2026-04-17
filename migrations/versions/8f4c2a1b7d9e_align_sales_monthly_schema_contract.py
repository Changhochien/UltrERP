"""align sales_monthly schema contract

Revision ID: 8f4c2a1b7d9e
Revises: 7a3c2d1e9f4b
Create Date: 2026-04-16

"""

from alembic import op
import sqlalchemy as sa


revision = "8f4c2a1b7d9e"
down_revision = "7a3c2d1e9f4b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "sales_monthly",
        "avg_unit_price",
        existing_type=sa.Numeric(precision=20, scale=2),
        type_=sa.Numeric(precision=14, scale=4),
        existing_nullable=False,
    )
    op.create_index(
        "ix_sales_monthly_tenant_month_category",
        "sales_monthly",
        ["tenant_id", "month_start", "product_category_snapshot"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_sales_monthly_tenant_month_category", table_name="sales_monthly")
    op.alter_column(
        "sales_monthly",
        "avg_unit_price",
        existing_type=sa.Numeric(precision=14, scale=4),
        type_=sa.Numeric(precision=20, scale=2),
        existing_nullable=False,
    )