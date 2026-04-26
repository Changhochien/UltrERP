"""Journal entry and general ledger tables (Epic 26.2).

Revision ID: aa1322719554zz
Revises: aa1322719553zz
Create Date: 2026-04-26

This migration creates the journal entry and general ledger tables:
- journal_entries: header for batch GL postings
- journal_entry_lines: individual debit/credit lines
- gl_entries: immutable GL postings created on journal entry submission

Features:
- Journal entry status: Draft, Submitted, Cancelled
- Voucher types: Journal Entry, Opening Entry
- Balanced debit/credit validation
- Reversal linkage for audit trail
- Reference fields for future document linking
"""

from __future__ import annotations

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "aa1322719554zz"
down_revision: str | None = "aa1322719553zz"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # Create journal_entry_status enum
    journal_entry_status = postgresql.ENUM(
        "Draft", "Submitted", "Cancelled",
        name="journal_entry_status",
        create_type=False,
    )
    journal_entry_status.create(op.get_bind(), checkfirst=True)

    # Create voucher_type enum
    voucher_type = postgresql.ENUM(
        "Journal Entry", "Opening Entry",
        name="voucher_type",
        create_type=False,
    )
    voucher_type.create(op.get_bind(), checkfirst=True)

    # Create gl_entry_type enum
    gl_entry_type = postgresql.ENUM(
        "Journal Entry", "Opening Entry",
        name="gl_entry_type",
        create_type=False,
    )
    gl_entry_type.create(op.get_bind(), checkfirst=True)

    # Create journal_entries table
    op.create_table(
        "journal_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("voucher_type", voucher_type, nullable=False, server_default="Journal Entry"),
        sa.Column("voucher_number", sa.String(length=50), nullable=False),
        sa.Column("posting_date", sa.Date(), nullable=False),
        sa.Column("reference_date", sa.Date(), nullable=True),
        sa.Column("status", journal_entry_status, nullable=False, server_default="Draft"),
        sa.Column("narration", sa.Text(), nullable=True),
        sa.Column("total_debit", sa.Numeric(precision=20, scale=6), nullable=False, server_default="0"),
        sa.Column("total_credit", sa.Numeric(precision=20, scale=6), nullable=False, server_default="0"),
        sa.Column("reference_type", sa.String(length=50), nullable=True),
        sa.Column("reference_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("external_reference_number", sa.String(length=100), nullable=True),
        sa.Column("external_reference_date", sa.Date(), nullable=True),
        sa.Column("reversed_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reverses_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("cancel_reason", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for journal_entries table
    op.create_index(
        "ix_journal_entries_tenant_voucher",
        "journal_entries",
        ["tenant_id", "voucher_number"],
        unique=True,
    )
    op.create_index(
        "ix_journal_entries_tenant_posting_date",
        "journal_entries",
        ["tenant_id", "posting_date"],
    )
    op.create_index(
        "ix_journal_entries_tenant_status",
        "journal_entries",
        ["tenant_id", "status"],
    )
    op.create_index(
        "ix_journal_entries_tenant_voucher_type",
        "journal_entries",
        ["tenant_id", "voucher_type"],
    )
    op.create_index(
        "ix_journal_entries_tenant_reversed_by",
        "journal_entries",
        ["tenant_id", "reversed_by_id"],
    )
    op.create_index(
        "ix_journal_entries_tenant_reverses",
        "journal_entries",
        ["tenant_id", "reverses_id"],
    )

    # Add check constraint for balanced entries
    op.create_check_constraint(
        "ck_journal_entries_balanced",
        "journal_entries",
        "status <> 'Submitted' OR total_debit = total_credit",
    )

    # Add foreign key for reversal linkage
    op.create_foreign_key(
        "fk_journal_entries_reversed_by",
        "journal_entries", "journal_entries",
        ["reversed_by_id"], ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_journal_entries_reverses",
        "journal_entries", "journal_entries",
        ["reverses_id"], ["id"],
        ondelete="RESTRICT",
    )

    # Create journal_entry_lines table
    op.create_table(
        "journal_entry_lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column("journal_entry_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("debit", sa.Numeric(precision=20, scale=6), nullable=False, server_default="0"),
        sa.Column("credit", sa.Numeric(precision=20, scale=6), nullable=False, server_default="0"),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("cost_center_id", sa.String(length=50), nullable=True),
        sa.Column("project_id", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for journal_entry_lines table
    op.create_index(
        "ix_journal_entry_lines_account",
        "journal_entry_lines",
        ["account_id"],
    )
    op.create_index(
        "ix_journal_entry_lines_journal_entry",
        "journal_entry_lines",
        ["journal_entry_id"],
    )

    # Add foreign keys for journal_entry_lines
    op.create_foreign_key(
        "fk_journal_entry_lines_journal_entry",
        "journal_entry_lines", "journal_entries",
        ["journal_entry_id"], ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_journal_entry_lines_account",
        "journal_entry_lines", "accounts",
        ["account_id"], ["id"],
        ondelete="RESTRICT",
    )

    # Create gl_entries table
    op.create_table(
        "gl_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("posting_date", sa.Date(), nullable=False),
        sa.Column("fiscal_year", sa.String(length=20), nullable=False),
        sa.Column("debit", sa.Numeric(precision=20, scale=6), nullable=False, server_default="0"),
        sa.Column("credit", sa.Numeric(precision=20, scale=6), nullable=False, server_default="0"),
        sa.Column("entry_type", gl_entry_type, nullable=False, server_default="Journal Entry"),
        sa.Column("voucher_type", sa.String(length=50), nullable=False),
        sa.Column("voucher_number", sa.String(length=50), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("journal_entry_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("journal_entry_line_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reversed_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reverses_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for gl_entries table
    op.create_index(
        "ix_gl_entries_account_posting_date",
        "gl_entries",
        ["account_id", "posting_date"],
    )
    op.create_index(
        "ix_gl_entries_tenant_account",
        "gl_entries",
        ["tenant_id", "account_id"],
    )
    op.create_index(
        "ix_gl_entries_tenant_voucher",
        "gl_entries",
        ["tenant_id", "voucher_type", "voucher_number"],
    )
    op.create_index(
        "ix_gl_entries_tenant_reversed_by",
        "gl_entries",
        ["tenant_id", "reversed_by_id"],
    )
    op.create_index(
        "ix_gl_entries_tenant_reverses",
        "gl_entries",
        ["tenant_id", "reverses_id"],
    )
    op.create_index(
        "ix_gl_entries_tenant_fiscal_year",
        "gl_entries",
        ["tenant_id", "fiscal_year"],
    )

    # Add foreign keys for gl_entries
    op.create_foreign_key(
        "fk_gl_entries_account",
        "gl_entries", "accounts",
        ["account_id"], ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_gl_entries_journal_entry",
        "gl_entries", "journal_entries",
        ["journal_entry_id"], ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_gl_entries_journal_entry_line",
        "gl_entries", "journal_entry_lines",
        ["journal_entry_line_id"], ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_gl_entries_reversed_by",
        "gl_entries", "gl_entries",
        ["reversed_by_id"], ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_gl_entries_reverses",
        "gl_entries", "gl_entries",
        ["reverses_id"], ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    # Drop gl_entries table
    op.drop_constraint("fk_gl_entries_reverses", "gl_entries", type_="foreignkey")
    op.drop_constraint("fk_gl_entries_reversed_by", "gl_entries", type_="foreignkey")
    op.drop_constraint("fk_gl_entries_journal_entry_line", "gl_entries", type_="foreignkey")
    op.drop_constraint("fk_gl_entries_journal_entry", "gl_entries", type_="foreignkey")
    op.drop_constraint("fk_gl_entries_account", "gl_entries", type_="foreignkey")
    op.drop_index("ix_gl_entries_tenant_fiscal_year", table_name="gl_entries")
    op.drop_index("ix_gl_entries_tenant_reverses", table_name="gl_entries")
    op.drop_index("ix_gl_entries_tenant_reversed_by", table_name="gl_entries")
    op.drop_index("ix_gl_entries_tenant_voucher", table_name="gl_entries")
    op.drop_index("ix_gl_entries_tenant_account", table_name="gl_entries")
    op.drop_index("ix_gl_entries_account_posting_date", table_name="gl_entries")
    op.drop_table("gl_entries")

    # Drop journal_entry_lines table
    op.drop_constraint("fk_journal_entry_lines_account", "journal_entry_lines", type_="foreignkey")
    op.drop_constraint("fk_journal_entry_lines_journal_entry", "journal_entry_lines", type_="foreignkey")
    op.drop_index("ix_journal_entry_lines_journal_entry", table_name="journal_entry_lines")
    op.drop_index("ix_journal_entry_lines_account", table_name="journal_entry_lines")
    op.drop_table("journal_entry_lines")

    # Drop journal_entries table
    op.drop_constraint("fk_journal_entries_reverses", "journal_entries", type_="foreignkey")
    op.drop_constraint("fk_journal_entries_reversed_by", "journal_entries", type_="foreignkey")
    op.drop_index("ix_journal_entries_tenant_reverses", table_name="journal_entries")
    op.drop_index("ix_journal_entries_tenant_reversed_by", table_name="journal_entries")
    op.drop_index("ix_journal_entries_tenant_voucher_type", table_name="journal_entries")
    op.drop_index("ix_journal_entries_tenant_status", table_name="journal_entries")
    op.drop_index("ix_journal_entries_tenant_posting_date", table_name="journal_entries")
    op.drop_index("ix_journal_entries_tenant_voucher", table_name="journal_entries")
    op.drop_table("journal_entries")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS gl_entry_type")
    op.execute("DROP TYPE IF EXISTS voucher_type")
    op.execute("DROP TYPE IF EXISTS journal_entry_status")
