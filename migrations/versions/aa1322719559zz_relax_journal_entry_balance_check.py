"""Allow unbalanced draft journal entries while enforcing balance on submit.

Revision ID: aa1322719559zz
Revises: aa1322719558zz
Create Date: 2026-04-26
"""

from __future__ import annotations

from alembic import op


revision = "aa1322719559zz"
down_revision = "aa1322719558zz"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE journal_entries DROP CONSTRAINT IF EXISTS ck_journal_entries_ck_journal_entries_balanced"
    )
    op.execute(
        "ALTER TABLE journal_entries DROP CONSTRAINT IF EXISTS ck_journal_entries_balanced"
    )
    op.create_check_constraint(
        "ck_journal_entries_balanced",
        "journal_entries",
        "status <> 'Submitted' OR total_debit = total_credit",
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE journal_entries DROP CONSTRAINT IF EXISTS ck_journal_entries_ck_journal_entries_balanced"
    )
    op.execute(
        "ALTER TABLE journal_entries DROP CONSTRAINT IF EXISTS ck_journal_entries_balanced"
    )
    op.create_check_constraint(
        "ck_journal_entries_balanced",
        "journal_entries",
        "total_debit = total_credit",
    )