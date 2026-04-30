"""add LEGACY_SNAPSHOT_BASELINE to reason_code_enum

Revision ID: 15f30a4b2c1d
Revises: 2026_04_26_manufacturing, aa1322719559zz
Create Date: 2026-04-30
"""

from __future__ import annotations

from alembic import op

revision = "15f30a4b2c1d"
down_revision = ("2026_04_26_manufacturing", "aa1322719559zz")
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(
            "ALTER TYPE reason_code_enum ADD VALUE IF NOT EXISTS "
            "'LEGACY_SNAPSHOT_BASELINE'"
        )


def downgrade() -> None:
    raise NotImplementedError(
        "Removing 'LEGACY_SNAPSHOT_BASELINE' from reason_code_enum is not "
        "supported automatically because existing stock adjustment rows may "
        "reference it."
    )