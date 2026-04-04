"""Add reconciliation fields to payments table.

Revision ID: ll222nn22o54
Revises: kk111mm11n43
Create Date: 2025-07-15

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "ll222nn22o54"
down_revision = "kk111mm11n43"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "payments",
        sa.Column("match_status", sa.String(20), nullable=False, server_default="matched"),
    )
    op.add_column(
        "payments",
        sa.Column("match_type", sa.String(20), nullable=True),
    )
    op.add_column(
        "payments",
        sa.Column("matched_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "payments",
        sa.Column(
            "suggested_invoice_id",
            UUID(as_uuid=True),
            sa.ForeignKey("invoices.id", name="fk_payments_suggested_invoice_id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_payments_match_status",
        "payments",
        ["tenant_id", "match_status"],
    )


def downgrade() -> None:
    op.drop_index("ix_payments_match_status", table_name="payments")
    op.drop_column("payments", "suggested_invoice_id")
    op.drop_column("payments", "matched_at")
    op.drop_column("payments", "match_type")
    op.drop_column("payments", "match_status")
