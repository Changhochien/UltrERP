"""add crm settings

Revision ID: 6f7a8b9c0d1e
Revises: 5e6f7a8b9c0d
Create Date: 2026-04-22 12:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "6f7a8b9c0d1e"
down_revision: str | None = "5e6f7a8b9c0d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "crm_settings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("lead_duplicate_policy", sa.String(length=20), nullable=False, server_default="block"),
        sa.Column("contact_creation_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("default_quotation_validity_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("carry_forward_communications", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("carry_forward_comments", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("opportunity_auto_close_days", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_crm_settings_tenant_id", "crm_settings", ["tenant_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_crm_settings_tenant_id", table_name="crm_settings")
    op.drop_table("crm_settings")