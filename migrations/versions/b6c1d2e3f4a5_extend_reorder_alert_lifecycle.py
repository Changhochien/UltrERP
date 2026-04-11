"""extend reorder alert lifecycle

Revision ID: b6c1d2e3f4a5
Revises: c7a2d8e9f1b3, f4a7c8d9e1b0
Create Date: 2026-04-11

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "b6c1d2e3f4a5"
down_revision: str | Sequence[str] | None = ("c7a2d8e9f1b3", "f4a7c8d9e1b0")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("ALTER TYPE alert_status_enum ADD VALUE IF NOT EXISTS 'snoozed'"))
    bind.execute(sa.text("ALTER TYPE alert_status_enum ADD VALUE IF NOT EXISTS 'dismissed'"))

    op.add_column(
        "reorder_alert",
        sa.Column("snoozed_until", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "reorder_alert",
        sa.Column("snoozed_by", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "reorder_alert",
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "reorder_alert",
        sa.Column("dismissed_by", sa.String(length=100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("reorder_alert", "dismissed_by")
    op.drop_column("reorder_alert", "dismissed_at")
    op.drop_column("reorder_alert", "snoozed_by")
    op.drop_column("reorder_alert", "snoozed_until")