"""create customers table

Revision ID: bb222ee22d54
Revises: aa111dd11c43
Create Date: 2026-06-30 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "bb222ee22d54"
down_revision: str | None = "aa111dd11c43"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("company_name", sa.String(200), nullable=False),
        sa.Column("normalized_business_number", sa.String(8), nullable=False),
        sa.Column("billing_address", sa.Text(), nullable=False, server_default=""),
        sa.Column("contact_name", sa.String(100), nullable=False),
        sa.Column("contact_phone", sa.String(30), nullable=False),
        sa.Column("contact_email", sa.String(254), nullable=False),
        sa.Column("credit_limit", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_customers")),
    )
    op.create_index(op.f("ix_customers_tenant_id"), "customers", ["tenant_id"])
    op.create_index(
        "uq_customers_tenant_business_number",
        "customers",
        ["tenant_id", "normalized_business_number"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_customers_tenant_business_number", table_name="customers")
    op.drop_index(op.f("ix_customers_tenant_id"), table_name="customers")
    op.drop_table("customers")
