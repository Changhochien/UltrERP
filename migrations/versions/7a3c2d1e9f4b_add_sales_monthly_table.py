"""add sales_monthly table

Revision ID: 7a3c2d1e9f4b
Revises: 6c4d2e1f9a7b
Create Date: 2026-04-16 21:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "7a3c2d1e9f4b"
down_revision: str | tuple[str, ...] | None = "6c4d2e1f9a7b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sales_monthly",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("month_start", sa.Date(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("product_name_snapshot", sa.String(length=500), nullable=False),
        sa.Column("product_category_snapshot", sa.String(length=200), nullable=False),
        sa.Column("quantity_sold", sa.Numeric(precision=18, scale=3), nullable=False),
        sa.Column("order_count", sa.Integer(), nullable=False),
        sa.Column("revenue", sa.Numeric(precision=20, scale=2), nullable=False),
        sa.Column("avg_unit_price", sa.Numeric(precision=20, scale=2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sales_monthly")),
    )
    op.create_index(
        "ix_sales_monthly_tenant_month",
        "sales_monthly",
        ["tenant_id", "month_start"],
        unique=False,
    )
    op.create_index(
        "ix_sales_monthly_tenant_product_month",
        "sales_monthly",
        ["tenant_id", "product_id", "month_start"],
        unique=False,
    )
    op.create_index(
        "ix_sales_monthly_tenant_id",
        "sales_monthly",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "uq_sales_monthly_tenant_month_product_snapshot",
        "sales_monthly",
        [
            "tenant_id",
            "month_start",
            "product_id",
            "product_name_snapshot",
            "product_category_snapshot",
        ],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_sales_monthly_tenant_month_product_snapshot", table_name="sales_monthly")
    op.drop_index("ix_sales_monthly_tenant_id", table_name="sales_monthly")
    op.drop_index("ix_sales_monthly_tenant_product_month", table_name="sales_monthly")
    op.drop_index("ix_sales_monthly_tenant_month", table_name="sales_monthly")
    op.drop_table("sales_monthly")