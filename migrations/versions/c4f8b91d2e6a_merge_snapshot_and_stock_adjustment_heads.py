"""merge snapshot and stock adjustment heads

Revision ID: c4f8b91d2e6a
Revises: 4e1db4c8300d, a9c3d7e4f1b2
Create Date: 2026-04-10
"""

from __future__ import annotations

from collections.abc import Sequence


# revision identifiers, used by Alembic.
revision: str = "c4f8b91d2e6a"
down_revision: str | tuple[str, str] | None = ("4e1db4c8300d", "a9c3d7e4f1b2")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass