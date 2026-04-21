"""add crm opportunities

Revision ID: 3b2d4f5e6a7b
Revises: 1e4b7c9d8a2f
Create Date: 2026-04-21 23:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "3b2d4f5e6a7b"
down_revision: str | None = "1e4b7c9d8a2f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "crm_opportunities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("opportunity_title", sa.String(length=200), nullable=False),
        sa.Column("opportunity_from", sa.String(length=20), nullable=False),
        sa.Column("party_name", sa.String(length=200), nullable=False),
        sa.Column("party_label", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="open"),
        sa.Column("sales_stage", sa.String(length=120), nullable=False, server_default="qualification"),
        sa.Column("probability", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expected_closing", sa.Date(), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="TWD"),
        sa.Column("opportunity_amount", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("base_opportunity_amount", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("opportunity_owner", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("territory", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("customer_group", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("contact_person", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("contact_email", sa.String(length=254), nullable=False, server_default=""),
        sa.Column("contact_mobile", sa.String(length=30), nullable=False, server_default=""),
        sa.Column("job_title", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("utm_source", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("utm_medium", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("utm_campaign", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("utm_content", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("items", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("lost_reason", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("competitor_name", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("loss_notes", sa.Text(), nullable=False, server_default=""),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_crm_opportunities_tenant_id", "crm_opportunities", ["tenant_id"])
    op.create_index(
        "ix_crm_opportunities_tenant_status",
        "crm_opportunities",
        ["tenant_id", "status"],
    )
    op.create_index(
        "ix_crm_opportunities_tenant_party",
        "crm_opportunities",
        ["tenant_id", "opportunity_from", "party_name"],
    )
    op.create_index(
        "ix_crm_opportunities_tenant_expected_closing",
        "crm_opportunities",
        ["tenant_id", "expected_closing"],
    )


def downgrade() -> None:
    op.drop_index("ix_crm_opportunities_tenant_expected_closing", table_name="crm_opportunities")
    op.drop_index("ix_crm_opportunities_tenant_party", table_name="crm_opportunities")
    op.drop_index("ix_crm_opportunities_tenant_status", table_name="crm_opportunities")
    op.drop_index("ix_crm_opportunities_tenant_id", table_name="crm_opportunities")
    op.drop_table("crm_opportunities")