"""Add supplier procurement controls (Story 24-5).

This migration adds:
- Hold controls: on_hold, hold_type, release_date
- Scorecard controls: scorecard_standing, scorecard_last_evaluated_at,
  warn_rfqs, prevent_rfqs, warn_pos, prevent_pos
- Index for tenant/active filtering

Revision ID: 1a2b3c4d5e6f
Revises: abc123def459
Create Date: 2026-04-24
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = "1a2b3c4d5e6f"
down_revision = "abc123def459"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add hold control columns
    op.add_column(
        "supplier",
        sa.Column("on_hold", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "supplier",
        sa.Column("hold_type", sa.String(50), nullable=True),
    )
    op.add_column(
        "supplier",
        sa.Column("release_date", sa.Date(), nullable=True),
    )

    # Add scorecard control columns
    op.add_column(
        "supplier",
        sa.Column("scorecard_standing", sa.String(30), nullable=True),
    )
    op.add_column(
        "supplier",
        sa.Column(
            "scorecard_last_evaluated_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "supplier",
        sa.Column("warn_rfqs", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "supplier",
        sa.Column("prevent_rfqs", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "supplier",
        sa.Column("warn_pos", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "supplier",
        sa.Column("prevent_pos", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )

    # Add index for tenant/active filtering
    op.create_index(
        "ix_supplier_tenant_active",
        "supplier",
        ["tenant_id", "is_active"],
        unique=False,
    )


def downgrade() -> None:
    # Remove index
    op.drop_index("ix_supplier_tenant_active", table_name="supplier")

    # Remove scorecard control columns
    op.drop_column("supplier", "prevent_pos")
    op.drop_column("supplier", "warn_pos")
    op.drop_column("supplier", "prevent_rfqs")
    op.drop_column("supplier", "warn_rfqs")
    op.drop_column("supplier", "scorecard_last_evaluated_at")
    op.drop_column("supplier", "scorecard_standing")

    # Remove hold control columns
    op.drop_column("supplier", "release_date")
    op.drop_column("supplier", "hold_type")
    op.drop_column("supplier", "on_hold")
