"""add category master table

Revision ID: d3e8f9a1b2c4
Revises: 8f4c2a1b7d9e
Create Date: 2026-04-18
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "d3e8f9a1b2c4"
down_revision = "8f4c2a1b7d9e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "category",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_category_tenant_id", "category", ["tenant_id"], unique=False)
    op.create_index("uq_category_tenant_name", "category", ["tenant_id", "name"], unique=True)


def downgrade() -> None:
    op.drop_index("uq_category_tenant_name", table_name="category")
    op.drop_index("ix_category_tenant_id", table_name="category")
    op.drop_table("category")