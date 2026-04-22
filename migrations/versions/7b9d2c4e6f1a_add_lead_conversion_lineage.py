"""add lead conversion lineage

Revision ID: 7b9d2c4e6f1a
Revises: 70819a2b3c4d
Create Date: 2026-04-22 17:30:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "7b9d2c4e6f1a"
down_revision: str | None = "70819a2b3c4d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("crm_leads", sa.Column("converted_opportunity_id", sa.Uuid(), nullable=True))
    op.add_column("crm_leads", sa.Column("converted_quotation_id", sa.Uuid(), nullable=True))
    op.add_column(
        "crm_leads",
        sa.Column("conversion_state", sa.String(length=40), nullable=False, server_default="not_converted"),
    )
    op.add_column(
        "crm_leads",
        sa.Column("conversion_path", sa.String(length=120), nullable=False, server_default=""),
    )
    op.add_column(
        "crm_leads",
        sa.Column("converted_by", sa.String(length=120), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("crm_leads", "converted_by")
    op.drop_column("crm_leads", "conversion_path")
    op.drop_column("crm_leads", "conversion_state")
    op.drop_column("crm_leads", "converted_quotation_id")
    op.drop_column("crm_leads", "converted_opportunity_id")