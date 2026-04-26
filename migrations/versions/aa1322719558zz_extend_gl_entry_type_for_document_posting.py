"""Extend gl_entry_type enum for document auto-posting.

Revision ID: aa1322719558zz
Revises: aa1322719557zz
Create Date: 2026-04-26
"""

from __future__ import annotations

from alembic import op


# revision identifiers
revision = "aa1322719558zz"
down_revision = "aa1322719557zz"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE gl_entry_type ADD VALUE IF NOT EXISTS 'Customer Invoice'")
    op.execute("ALTER TYPE gl_entry_type ADD VALUE IF NOT EXISTS 'Customer Payment'")
    op.execute("ALTER TYPE gl_entry_type ADD VALUE IF NOT EXISTS 'Supplier Invoice'")
    op.execute("ALTER TYPE gl_entry_type ADD VALUE IF NOT EXISTS 'Supplier Payment'")


def downgrade() -> None:
    # PostgreSQL enums cannot drop values safely in-place.
    pass