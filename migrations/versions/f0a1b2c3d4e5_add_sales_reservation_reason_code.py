"""add SALES_RESERVATION to reason_code_enum

Revision ID: f0a1b2c3d4e5
Revises: e4f5a6b7c8d9
Create Date: 2026-04-08 12:00:00.000000
"""

from alembic import op

revision: str = "f0a1b2c3d4e5"
down_revision: str | None = "b2c3d4e5f6a7"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        # Add SALES_RESERVATION to the reason_code_enum.
        # PostgreSQL requires ALTER TYPE ... ADD VALUE to be run inside a
        # transaction block when using autocommit_block().
        op.execute(
            "ALTER TYPE reason_code_enum ADD VALUE IF NOT EXISTS 'SALES_RESERVATION'"
        )


def downgrade() -> None:
    # Removing an enum value is unsafe if any rows use it.
    # PostgreSQL does not support REMOVE VALUE inside a transaction.
    # Marking as not supported — remove manually with care.
    raise NotImplementedError(
        "Removing 'SALES_RESERVATION' from reason_code_enum is not supported "
        "automatically because existing rows may reference it. "
        "Drop rows or migrate data first if truly needed."
    )
