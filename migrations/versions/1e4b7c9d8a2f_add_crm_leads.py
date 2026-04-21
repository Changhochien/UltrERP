"""add crm leads

Revision ID: 1e4b7c9d8a2f
Revises: 18b7d5e6f9a0
Create Date: 2026-04-21 21:15:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "1e4b7c9d8a2f"
down_revision: str | None = "18b7d5e6f9a0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "crm_leads",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("lead_name", sa.String(length=140), nullable=False),
        sa.Column("company_name", sa.String(length=200), nullable=False),
        sa.Column("normalized_company_name", sa.String(length=200), nullable=False),
        sa.Column("email_id", sa.String(length=254), nullable=False),
        sa.Column("normalized_email_id", sa.String(length=254), nullable=False),
        sa.Column("phone", sa.String(length=30), nullable=False),
        sa.Column("mobile_no", sa.String(length=30), nullable=False),
        sa.Column("normalized_phone", sa.String(length=30), nullable=False),
        sa.Column("normalized_mobile_no", sa.String(length=30), nullable=False),
        sa.Column("territory", sa.String(length=120), nullable=False),
        sa.Column("lead_owner", sa.String(length=120), nullable=False),
        sa.Column("source", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="lead"),
        sa.Column(
            "qualification_status",
            sa.String(length=40),
            nullable=False,
            server_default="in_process",
        ),
        sa.Column("qualified_by", sa.String(length=120), nullable=False),
        sa.Column("annual_revenue", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("no_of_employees", sa.Integer(), nullable=True),
        sa.Column("industry", sa.String(length=120), nullable=False),
        sa.Column("market_segment", sa.String(length=120), nullable=False),
        sa.Column("utm_source", sa.String(length=120), nullable=False),
        sa.Column("utm_medium", sa.String(length=120), nullable=False),
        sa.Column("utm_campaign", sa.String(length=120), nullable=False),
        sa.Column("utm_content", sa.String(length=200), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("converted_customer_id", sa.Uuid(), nullable=True),
        sa.Column("converted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
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
        sa.ForeignKeyConstraint(
            ["converted_customer_id"],
            ["customers.id"],
            name="fk_crm_leads_converted_customer_id_customers",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_crm_leads_tenant_id", "crm_leads", ["tenant_id"])
    op.create_index(
        "ix_crm_leads_tenant_company",
        "crm_leads",
        ["tenant_id", "normalized_company_name"],
    )
    op.create_index(
        "ix_crm_leads_tenant_email",
        "crm_leads",
        ["tenant_id", "normalized_email_id"],
    )
    op.create_index(
        "ix_crm_leads_tenant_phone",
        "crm_leads",
        ["tenant_id", "normalized_phone"],
    )
    op.create_index(
        "ix_crm_leads_tenant_mobile",
        "crm_leads",
        ["tenant_id", "normalized_mobile_no"],
    )


def downgrade() -> None:
    op.drop_index("ix_crm_leads_tenant_mobile", table_name="crm_leads")
    op.drop_index("ix_crm_leads_tenant_phone", table_name="crm_leads")
    op.drop_index("ix_crm_leads_tenant_email", table_name="crm_leads")
    op.drop_index("ix_crm_leads_tenant_company", table_name="crm_leads")
    op.drop_index("ix_crm_leads_tenant_id", table_name="crm_leads")
    op.drop_table("crm_leads")