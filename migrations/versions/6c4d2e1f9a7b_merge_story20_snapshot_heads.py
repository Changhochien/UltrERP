"""merge story 20.1 snapshot head with local pending heads

Revision ID: 6c4d2e1f9a7b
Revises: 2f7c1b4d9e3a, 8d2f4c6b7a90, 9b2f3c4d5e6f
Create Date: 2026-04-16 19:15:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence


revision: str = "6c4d2e1f9a7b"
down_revision: str | tuple[str, str, str] | None = (
    "2f7c1b4d9e3a",
    "8d2f4c6b7a90",
    "9b2f3c4d5e6f",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass