"""Add invoice void fields

Revision ID: ff666hh66i98
Revises: ee555gg55h87
Create Date: 2025-07-16

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "ff666hh66i98"
down_revision = "ee5b6cc6d7e8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("invoices", sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("invoices", sa.Column("void_reason", sa.String(500), nullable=True))
    op.add_column("invoices", sa.Column("replaces_invoice_id", sa.Uuid(), nullable=True))
    op.add_column("invoices", sa.Column("replaced_by_invoice_id", sa.Uuid(), nullable=True))


def downgrade() -> None:
    op.drop_column("invoices", "replaced_by_invoice_id")
    op.drop_column("invoices", "replaces_invoice_id")
    op.drop_column("invoices", "void_reason")
    op.drop_column("invoices", "voided_at")
