"""merge legacy refresh and category translation heads

Revision ID: 13a3b28ab317
Revises: c2d3e4f5a6b7, f3b4c5d6e7f8
Create Date: 2026-04-19 11:16:28.605254
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '13a3b28ab317'
down_revision: str | None = ('c2d3e4f5a6b7', 'f3b4c5d6e7f8')
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass