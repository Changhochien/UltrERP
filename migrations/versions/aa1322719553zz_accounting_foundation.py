"""Accounting foundation: accounts and fiscal_years tables.

Revision ID: aa1322719553zz
Revises: previous migration head
Create Date: 2026-04-26

This migration creates the foundational accounting tables:
- accounts: tenant-scoped chart of accounts tree
- fiscal_years: tenant-scoped fiscal year boundaries

These tables support:
- Account tree with root types (Asset, Liability, Equity, Income, Expense)
- Group vs ledger account semantics
- Account freeze/disable policy
- Fiscal year open/closed state for posting validation
"""

from __future__ import annotations

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "aa1322719553zz"
down_revision: str | None = "25_6_procurement_fx"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # Create account_root_type enum
    account_root_type = postgresql.ENUM(
        "Asset", "Liability", "Equity", "Income", "Expense",
        name="account_root_type",
        create_type=False,
    )
    account_root_type.create(op.get_bind(), checkfirst=True)

    # Create account_report_type enum
    account_report_type = postgresql.ENUM(
        "Balance Sheet", "Profit and Loss",
        name="account_report_type",
        create_type=False,
    )
    account_report_type.create(op.get_bind(), checkfirst=True)

    # Create account_type enum
    account_type_enum = postgresql.ENUM(
        "Root Asset", "Bank", "Cash", "Receivable", "Inventory",
        "Current Asset", "Fixed Asset", "Non-Current Asset", "Prepayment", "Tax Asset",
        "Root Liability", "Payable", "Credit Card", "Current Liability",
        "Non-Current Liability", "Tax Liability",
        "Root Equity", "Retained Earnings", "Shareholders Equity",
        "Root Income", "Sales", "Service Revenue", "Other Income",
        "Root Expense", "Cost of Goods Sold", "Expense", "Depreciation", "Tax Expense",
        name="account_type",
        create_type=False,
    )
    account_type_enum.create(op.get_bind(), checkfirst=True)

    # Create fiscal_year_status enum
    fiscal_year_status = postgresql.ENUM(
        "Draft", "Open", "Closed", "Archived",
        name="fiscal_year_status",
        create_type=False,
    )
    fiscal_year_status.create(op.get_bind(), checkfirst=True)

    # Create accounts table
    op.create_table(
        "accounts",
        sa.Column("id", sa.UUID(), nullable=False, default=uuid.uuid4),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("parent_id", sa.UUID(), nullable=True),
        sa.Column("account_number", sa.String(length=50), nullable=False),
        sa.Column("account_name", sa.String(length=255), nullable=False),
        sa.Column("root_type", sa.Enum("Asset", "Liability", "Equity", "Income", "Expense", name="account_root_type"), nullable=False),
        sa.Column("report_type", sa.Enum("Balance Sheet", "Profit and Loss", name="account_report_type"), nullable=False),
        sa.Column("account_type", sa.Enum("Root Asset", "Bank", "Cash", "Receivable", "Inventory", "Current Asset", "Fixed Asset", "Non-Current Asset", "Prepayment", "Tax Asset", "Root Liability", "Payable", "Credit Card", "Current Liability", "Non-Current Liability", "Tax Liability", "Root Equity", "Retained Earnings", "Shareholders Equity", "Root Income", "Sales", "Service Revenue", "Other Income", "Root Expense", "Cost of Goods Sold", "Expense", "Depreciation", "Tax Expense", name="account_type"), nullable=False),
        sa.Column("is_group", sa.Boolean(), nullable=False, default=False),
        sa.Column("is_frozen", sa.Boolean(), nullable=False, default=False),
        sa.Column("is_disabled", sa.Boolean(), nullable=False, default=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, default=0),
        sa.Column("currency_code", sa.String(length=3), nullable=True),
        sa.Column("parent_number", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["parent_id"], ["accounts.id"], ondelete="RESTRICT"),
    )

    # Create indexes for accounts table
    op.create_index(
        "ix_accounts_tenant_number",
        "accounts",
        ["tenant_id", "account_number"],
        unique=True,
    )
    op.create_index(
        "ix_accounts_tenant_parent",
        "accounts",
        ["tenant_id", "parent_id"],
    )
    op.create_index(
        "ix_accounts_tenant_root",
        "accounts",
        ["tenant_id", "root_type"],
    )

    # Add check constraints for accounts
    op.create_check_constraint(
        "ck_accounts_not_group_and_frozen",
        "accounts",
        "NOT (is_group AND is_frozen)",
    )
    op.create_check_constraint(
        "ck_accounts_not_group_and_disabled",
        "accounts",
        "NOT (is_group AND is_disabled)",
    )

    # Create fiscal_years table
    op.create_table(
        "fiscal_years",
        sa.Column("id", sa.UUID(), nullable=False, default=uuid.uuid4),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("label", sa.String(length=20), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("status", sa.Enum("Draft", "Open", "Closed", "Archived", name="fiscal_year_status"), nullable=False, server_default="Open"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_by", sa.UUID(), nullable=True),
        sa.Column("closure_notes", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for fiscal_years table
    op.create_index(
        "ix_fiscal_years_tenant_label",
        "fiscal_years",
        ["tenant_id", "label"],
        unique=True,
    )
    op.create_index(
        "ix_fiscal_years_tenant_dates",
        "fiscal_years",
        ["tenant_id", "start_date", "end_date"],
    )
    op.create_index(
        "ix_fiscal_years_tenant_status",
        "fiscal_years",
        ["tenant_id", "status"],
    )

    # Add check constraints for fiscal_years
    op.create_check_constraint(
        "ck_fiscal_years_date_order",
        "fiscal_years",
        "start_date < end_date",
    )
    op.create_check_constraint(
        "ck_fiscal_years_label_format",
        "fiscal_years",
        "label ~ '^[0-9]{4}$|^FY[0-9]{4}$'",
    )


def downgrade() -> None:
    # Drop fiscal_years table
    op.drop_index("ix_fiscal_years_tenant_status", table_name="fiscal_years")
    op.drop_index("ix_fiscal_years_tenant_dates", table_name="fiscal_years")
    op.drop_index("ix_fiscal_years_tenant_label", table_name="fiscal_years")
    op.drop_table("fiscal_years")

    # Drop accounts table
    op.drop_index("ix_accounts_tenant_root", table_name="accounts")
    op.drop_index("ix_accounts_tenant_parent", table_name="accounts")
    op.drop_index("ix_accounts_tenant_number", table_name="accounts")
    op.drop_table("accounts")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS fiscal_year_status")
    op.execute("DROP TYPE IF EXISTS account_type")
    op.execute("DROP TYPE IF EXISTS account_report_type")
    op.execute("DROP TYPE IF EXISTS account_root_type")
