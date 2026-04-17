"""add customer_type to customers

Revision ID: 8d2f4c6b7a90
Revises: 4e1db4c8300d
Create Date: 2026-04-15 11:30:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8d2f4c6b7a90"
down_revision: str | None = "4e1db4c8300d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "customers",
        sa.Column("customer_type", sa.String(length=20), nullable=False, server_default="unknown"),
    )


def downgrade() -> None:
    op.drop_column("customers", "customer_type")