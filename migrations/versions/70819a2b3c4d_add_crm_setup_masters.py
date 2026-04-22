"""add crm setup masters

Revision ID: 70819a2b3c4d
Revises: 6f7a8b9c0d1e
Create Date: 2026-04-22 13:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "70819a2b3c4d"
down_revision: str | None = "6f7a8b9c0d1e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "crm_sales_stages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("probability", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_crm_sales_stages_tenant_id", "crm_sales_stages", ["tenant_id"], unique=False)
    op.create_index("uq_crm_sales_stages_tenant_name", "crm_sales_stages", ["tenant_id", "name"], unique=True)
    op.create_index("ix_crm_sales_stages_tenant_sort", "crm_sales_stages", ["tenant_id", "sort_order"], unique=False)

    op.create_table(
        "crm_territories",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column("is_group", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_crm_territories_tenant_id", "crm_territories", ["tenant_id"], unique=False)
    op.create_index("uq_crm_territories_tenant_name", "crm_territories", ["tenant_id", "name"], unique=True)
    op.create_index("ix_crm_territories_tenant_sort", "crm_territories", ["tenant_id", "sort_order"], unique=False)

    op.create_table(
        "crm_customer_groups",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column("is_group", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_crm_customer_groups_tenant_id", "crm_customer_groups", ["tenant_id"], unique=False)
    op.create_index(
        "uq_crm_customer_groups_tenant_name",
        "crm_customer_groups",
        ["tenant_id", "name"],
        unique=True,
    )
    op.create_index(
        "ix_crm_customer_groups_tenant_sort",
        "crm_customer_groups",
        ["tenant_id", "sort_order"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_crm_customer_groups_tenant_sort", table_name="crm_customer_groups")
    op.drop_index("uq_crm_customer_groups_tenant_name", table_name="crm_customer_groups")
    op.drop_index("ix_crm_customer_groups_tenant_id", table_name="crm_customer_groups")
    op.drop_table("crm_customer_groups")

    op.drop_index("ix_crm_territories_tenant_sort", table_name="crm_territories")
    op.drop_index("uq_crm_territories_tenant_name", table_name="crm_territories")
    op.drop_index("ix_crm_territories_tenant_id", table_name="crm_territories")
    op.drop_table("crm_territories")

    op.drop_index("ix_crm_sales_stages_tenant_sort", table_name="crm_sales_stages")
    op.drop_index("uq_crm_sales_stages_tenant_name", table_name="crm_sales_stages")
    op.drop_index("ix_crm_sales_stages_tenant_id", table_name="crm_sales_stages")
    op.drop_table("crm_sales_stages")