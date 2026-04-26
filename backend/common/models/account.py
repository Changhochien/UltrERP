"""Account model for chart of accounts (Epic 26).

Defines the tenant-scoped account tree with root types, account types,
numbering, and freeze/disable policy.
"""

from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.database import Base

if TYPE_CHECKING:
    pass


class AccountRootType(str, enum.Enum):
    """Root account classifications per accounting equation."""

    ASSET = "Asset"
    LIABILITY = "Liability"
    EQUITY = "Equity"
    INCOME = "Income"
    EXPENSE = "Expense"


class AccountReportType(str, enum.Enum):
    """Report type derived from root_type for Balance Sheet vs P&L classification."""

    BALANCE_SHEET = "Balance Sheet"  # Asset, Liability, Equity
    PROFIT_AND_LOSS = "Profit and Loss"  # Income, Expense


class AccountType(str, enum.Enum):
    """Detailed account types for posting and reporting semantics."""

    # Asset subtypes
    ROOT_ASSET = "Root Asset"
    BANK = "Bank"
    CASH = "Cash"
    RECEIVABLE = "Receivable"
    INVENTORY = "Inventory"
    CURRENT_ASSET = "Current Asset"
    FIXED_ASSET = "Fixed Asset"
    NON_CURRENT_ASSET = "Non-Current Asset"
    PREPAYMENT = "Prepayment"
    TAX_ASSET = "Tax Asset"

    # Liability subtypes
    ROOT_LIABILITY = "Root Liability"
    PAYABLE = "Payable"
    CREDIT_CARD = "Credit Card"
    CURRENT_LIABILITY = "Current Liability"
    NON_CURRENT_LIABILITY = "Non-Current Liability"
    TAX_LIABILITY = "Tax Liability"

    # Equity subtypes
    ROOT_EQUITY = "Root Equity"
    RETAINED_EARNINGS = "Retained Earnings"
    SHAREHOLDERS_EQUITY = "Shareholders Equity"

    # Income subtypes
    ROOT_INCOME = "Root Income"
    SALES = "Sales"
    SERVICE_REVENUE = "Service Revenue"
    OTHER_INCOME = "Other Income"

    # Expense subtypes
    ROOT_EXPENSE = "Root Expense"
    COST_OF_GOODS_SOLD = "Cost of Goods Sold"
    EXPENSE = "Expense"
    DEPRECIATION = "Depreciation"
    TAX_EXPENSE = "Tax Expense"


# Mapping from root_type to default report_type
_ROOT_TYPE_TO_REPORT_TYPE: dict[AccountRootType, AccountReportType] = {
    AccountRootType.ASSET: AccountReportType.BALANCE_SHEET,
    AccountRootType.LIABILITY: AccountReportType.BALANCE_SHEET,
    AccountRootType.EQUITY: AccountReportType.BALANCE_SHEET,
    AccountRootType.INCOME: AccountReportType.PROFIT_AND_LOSS,
    AccountRootType.EXPENSE: AccountReportType.PROFIT_AND_LOSS,
}


class Account(Base):
    """Tenant-scoped chart of accounts tree node.

    Supports adjacency-list parent-child relationships with group vs ledger semantics.
    Group accounts are structural nodes (cannot receive postings).
    Ledger accounts are leaf nodes that can receive GL postings (Story 26.2+).
    """

    __tablename__ = "accounts"
    __table_args__ = (
        # Tenant-scoped uniqueness for account numbers
        Index("ix_accounts_tenant_number", "tenant_id", "account_number", unique=True),
        # Tenant-scoped account tree index
        Index("ix_accounts_tenant_parent", "tenant_id", "parent_id"),
        # Index for tree traversal queries
        Index("ix_accounts_tenant_root", "tenant_id", "root_type"),
        # Ensure is_group and is_frozen are never both True (ledger posting rule)
        CheckConstraint(
            "NOT (is_group AND is_frozen)",
            name="ck_accounts_not_group_and_frozen",
        ),
        # Ensure is_group and is_disabled are never both True
        CheckConstraint(
            "NOT (is_group AND is_disabled)",
            name="ck_accounts_not_group_and_disabled",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)

    # Adjacency-list parent reference (NULL for root nodes)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=True
    )

    # Account numbering within tenant (must be unique)
    account_number: Mapped[str] = mapped_column(String(50), nullable=False)

    # Account display name
    account_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Root type: Asset, Liability, Equity, Income, Expense (stored as string)
    root_type: Mapped[str] = mapped_column(String(20), nullable=False)

    # Report type: Balance Sheet or Profit and Loss (stored as string)
    report_type: Mapped[str] = mapped_column(String(30), nullable=False)

    # Detailed account type for posting semantics (stored as string)
    account_type: Mapped[str] = mapped_column(String(50), nullable=False)

    # Group vs Ledger semantics
    # - is_group=True: structural node, can have children, cannot receive postings
    # - is_group=False: leaf ledger account, can receive GL postings
    is_group: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Frozen accounts reject posting operations (but retain data integrity)
    is_frozen: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Disabled accounts are inactive and hidden from normal selection
    is_disabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Sort order within parent (for UI ordering)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Optional: account-level currency override (references Currency.code)
    # If NULL, uses tenant's base currency
    currency_code: Mapped[str | None] = mapped_column(String(3), nullable=True)

    # Optional: parent account number for display (denormalized)
    parent_number: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Audit metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(tz=UTC),
        onupdate=lambda: datetime.now(tz=UTC),
    )

    # Relationships
    parent = relationship(
        "Account",
        remote_side=[id],
        back_populates="children",
        foreign_keys=[parent_id],
    )
    children = relationship(
        "Account",
        back_populates="parent",
        foreign_keys=[parent_id],
        cascade="all",
        # Only load children when explicitly queried
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<Account {self.account_number} {self.account_name} "
            f"({self.root_type}, {'Group' if self.is_group else 'Ledger'})>"
        )

    @property
    def is_root(self) -> bool:
        """True if this is a top-level root account (no parent)."""
        return self.parent_id is None

    @property
    def is_ledger(self) -> bool:
        """True if this is a leaf ledger account (can receive postings)."""
        return not self.is_group

    @property
    def can_receive_postings(self) -> bool:
        """True if this account can receive GL postings."""
        return self.is_ledger and not self.is_frozen and not self.is_disabled

    def validate_parent_child(self, new_parent: Account | None) -> list[str]:
        """Validate that parent-child relationship is valid.

        Returns list of validation error messages (empty if valid).
        """
        errors = []

        if new_parent is None:
            # Becoming a root node - ensure root_type consistency
            # This is allowed only for the 5 standard root accounts
            return errors

        # Prevent circular references
        if new_parent.id == self.id:
            errors.append("Account cannot be its own parent")

        # Prevent parent being a ledger (leaf) account
        if not new_parent.is_group:
            errors.append("Parent account must be a group account")

        # Prevent creating circular chains
        current = new_parent
        visited = {self.id}
        while current:
            if current.id in visited:
                errors.append("Circular reference detected in account hierarchy")
                break
            visited.add(current.id)
            current = current.parent

        # Validate root_type consistency (children must match parent's root_type)
        if new_parent.root_type != self.root_type:
            errors.append(
                f"Child account root_type ({self.root_type.value}) must match "
                f"parent's root_type ({new_parent.root_type.value})"
            )

        return errors
