"""add product supplier table

Revision ID: a3d4e5f6b7c8
Revises: f2b3c4d5e6f7
Create Date: 2026-04-18
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "a3d4e5f6b7c8"
down_revision = "f2b3c4d5e6f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "product_supplier",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("unit_cost", sa.Numeric(19, 4), nullable=True),
        sa.Column("lead_time_days", sa.Integer(), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["product_id"], ["product.id"]),
        sa.ForeignKeyConstraint(["supplier_id"], ["supplier.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_product_supplier_tenant_id", "product_supplier", ["tenant_id"], unique=False)
    op.create_index(
        "uq_product_supplier_tenant_product_supplier",
        "product_supplier",
        ["tenant_id", "product_id", "supplier_id"],
        unique=True,
    )
    op.create_index(
        "uq_product_supplier_default_per_product",
        "product_supplier",
        ["tenant_id", "product_id"],
        unique=True,
        postgresql_where=sa.text("is_default"),
    )


def downgrade() -> None:
    op.drop_index("uq_product_supplier_default_per_product", table_name="product_supplier")
    op.drop_index("uq_product_supplier_tenant_product_supplier", table_name="product_supplier")
    op.drop_index("ix_product_supplier_tenant_id", table_name="product_supplier")
    op.drop_table("product_supplier")