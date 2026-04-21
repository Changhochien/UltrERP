"""merge order discount and customer discount heads

Revision ID: 18b7d5e6f9a0
Revises: 16a4c9e7b2d3, 17a6c4e5b8d9
Create Date: 2026-04-20
"""

from __future__ import annotations

from collections.abc import Sequence


revision: str = "18b7d5e6f9a0"
down_revision: str | Sequence[str] | None = ("16a4c9e7b2d3", "17a6c4e5b8d9")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass