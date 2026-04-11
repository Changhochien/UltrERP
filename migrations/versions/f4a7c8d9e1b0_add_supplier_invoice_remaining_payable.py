"""add supplier invoice remaining payable amount

Revision ID: f4a7c8d9e1b0
Revises: d9e1a2b3c4d5
Create Date: 2026-04-11 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f4a7c8d9e1b0"
down_revision = "d9e1a2b3c4d5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "supplier_invoices",
        sa.Column("remaining_payable_amount", sa.Numeric(20, 2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("supplier_invoices", "remaining_payable_amount")