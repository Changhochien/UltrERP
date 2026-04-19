"""add unit of measure table

Revision ID: f2b3c4d5e6f7
Revises: e1b2c3d4f5a6
Create Date: 2026-04-18
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "f2b3c4d5e6f7"
down_revision = "e1b2c3d4f5a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "unit_of_measure",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("decimal_places", sa.Integer(), nullable=False, server_default="0"),
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
    op.create_index("ix_unit_of_measure_tenant_id", "unit_of_measure", ["tenant_id"], unique=False)
    op.create_index("uq_unit_of_measure_tenant_code", "unit_of_measure", ["tenant_id", "code"], unique=True)


def downgrade() -> None:
    op.drop_index("uq_unit_of_measure_tenant_code", table_name="unit_of_measure")
    op.drop_index("ix_unit_of_measure_tenant_id", table_name="unit_of_measure")
    op.drop_table("unit_of_measure")