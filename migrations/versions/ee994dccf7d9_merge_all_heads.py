"""merge all heads

Revision ID: ee994dccf7d9
Revises: 55e4a1b2c3d4, e4f5a6b7c8d9, f0a1b2c3d4e5, f7a2b3c4d5e6, qq777ss77t09, catchup_20260409
Create Date: 2026-04-09 14:36:26.447076
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ee994dccf7d9'
down_revision: str | None = ('55e4a1b2c3d4', 'e4f5a6b7c8d9', 'f0a1b2c3d4e5', 'f7a2b3c4d5e6', 'qq777ss77t09', 'catchup_20260409')
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass