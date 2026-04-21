"""add crm quotations

Revision ID: 4d6e7f8a9b0c
Revises: 3b2d4f5e6a7b
Create Date: 2026-04-22 00:30:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "4d6e7f8a9b0c"
down_revision: str | None = "3b2d4f5e6a7b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "crm_quotations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("quotation_to", sa.String(length=20), nullable=False),
        sa.Column("party_name", sa.String(length=200), nullable=False),
        sa.Column("party_label", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="draft"),
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("valid_till", sa.Date(), nullable=False),
        sa.Column("company", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="TWD"),
        sa.Column("subtotal", sa.Numeric(precision=14, scale=2), nullable=False, server_default="0"),
        sa.Column("total_taxes", sa.Numeric(precision=14, scale=2), nullable=False, server_default="0"),
        sa.Column("grand_total", sa.Numeric(precision=14, scale=2), nullable=False, server_default="0"),
        sa.Column("base_grand_total", sa.Numeric(precision=14, scale=2), nullable=False, server_default="0"),
        sa.Column("ordered_amount", sa.Numeric(precision=14, scale=2), nullable=False, server_default="0"),
        sa.Column("order_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("contact_person", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("contact_email", sa.String(length=254), nullable=False, server_default=""),
        sa.Column("contact_mobile", sa.String(length=30), nullable=False, server_default=""),
        sa.Column("job_title", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("territory", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("customer_group", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("billing_address", sa.Text(), nullable=False, server_default=""),
        sa.Column("shipping_address", sa.Text(), nullable=False, server_default=""),
        sa.Column("utm_source", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("utm_medium", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("utm_campaign", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("utm_content", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("items", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("taxes", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("terms_template", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("terms_and_conditions", sa.Text(), nullable=False, server_default=""),
        sa.Column("opportunity_id", sa.Uuid(), nullable=True),
        sa.Column("amended_from", sa.Uuid(), nullable=True),
        sa.Column("revision_no", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("lost_reason", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("competitor_name", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("loss_notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("auto_repeat_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("auto_repeat_frequency", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("auto_repeat_until", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_crm_quotations_tenant_id", "crm_quotations", ["tenant_id"])
    op.create_index("ix_crm_quotations_tenant_status", "crm_quotations", ["tenant_id", "status"])
    op.create_index("ix_crm_quotations_tenant_party", "crm_quotations", ["tenant_id", "quotation_to", "party_name"])
    op.create_index("ix_crm_quotations_tenant_valid_till", "crm_quotations", ["tenant_id", "valid_till"])
    op.create_index("ix_crm_quotations_tenant_opportunity", "crm_quotations", ["tenant_id", "opportunity_id"])


def downgrade() -> None:
    op.drop_index("ix_crm_quotations_tenant_opportunity", table_name="crm_quotations")
    op.drop_index("ix_crm_quotations_tenant_valid_till", table_name="crm_quotations")
    op.drop_index("ix_crm_quotations_tenant_party", table_name="crm_quotations")
    op.drop_index("ix_crm_quotations_tenant_status", table_name="crm_quotations")
    op.drop_index("ix_crm_quotations_tenant_id", table_name="crm_quotations")
    op.drop_table("crm_quotations")