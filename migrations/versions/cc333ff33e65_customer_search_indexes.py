"""add customer search indexes

Revision ID: cc333ff33e65
Revises: bb222ee22d54
Create Date: 2026-07-01 12:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "cc333ff33e65"
down_revision: str | None = "bb222ee22d54"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # btree index on company_name for prefix / ilike search within a tenant
    op.create_index(
        "ix_customers_tenant_company_name",
        "customers",
        ["tenant_id", "company_name"],
    )
    # btree index on status for filtered queries within a tenant
    op.create_index(
        "ix_customers_tenant_status",
        "customers",
        ["tenant_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_customers_tenant_status", table_name="customers")
    op.drop_index("ix_customers_tenant_company_name", table_name="customers")
