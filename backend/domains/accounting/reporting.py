"""Financial reporting services for P&L, Balance Sheet, and Trial Balance.

This module provides GL-based financial statement calculations that:
- Compute statements directly from posted GL entries (not invoice/payment aggregates)
- Roll up child-account balances into parent groups
- Support period-based P&L and as-of-date Balance Sheet/Trial Balance
- Return explicit empty_reason when no data exists for the period
"""

from __future__ import annotations

import csv
import io
import uuid
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.models.account import Account
from common.models.gl_entry import GLEntry

if TYPE_CHECKING:
    pass


# ============================================================
# Data Transfer Objects
# ============================================================


class EmptyReason(str, Enum):
    """Reason why a report has no data."""
    NO_ENTRIES_IN_PERIOD = "no_entries_in_period"
    NO_ACCOUNTS_CONFIGURED = "no_accounts_configured"
    ALL_ACCOUNTS_DISABLED = "all_accounts_disabled"


@dataclass
class AccountBalance:
    """Balance for a single account (leaf or group)."""
    account_id: uuid.UUID
    account_number: str
    account_name: str
    root_type: str
    account_type: str
    is_group: bool
    debit: Decimal = Decimal("0")
    credit: Decimal = Decimal("0")
    balance: Decimal = Decimal("0")  # debit - credit (positive = debit balance)
    children: list[AccountBalance] = field(default_factory=list)

    @property
    def has_children(self) -> bool:
        return len(self.children) > 0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "account_id": str(self.account_id),
            "account_number": self.account_number,
            "account_name": self.account_name,
            "root_type": self.root_type,
            "account_type": self.account_type,
            "is_group": self.is_group,
            "debit": str(self.debit),
            "credit": str(self.credit),
            "balance": str(self.balance),
            "children": [c.to_dict() for c in self.children],
        }


@dataclass
class ReportMetadata:
    """Common metadata for all financial reports."""
    report_type: str
    as_of_date: date | None = None
    from_date: date | None = None
    to_date: date | None = None
    fiscal_year: str | None = None
    empty_reason: EmptyReason | None = None
    generated_at: str | None = None


@dataclass
class ProfitAndLossRow:
    """A single row in the P&L report."""
    account_id: uuid.UUID
    account_number: str
    account_name: str
    amount: Decimal
    is_group: bool
    indent_level: int = 0
    is_subtotal: bool = False


@dataclass
class ProfitAndLossResponse:
    """Profit and Loss statement response."""
    metadata: ReportMetadata
    income_rows: list[ProfitAndLossRow]
    income_total: Decimal
    expense_rows: list[ProfitAndLossRow]
    expense_total: Decimal
    net_profit: Decimal

    def to_dict(self) -> dict:
        return {
            "metadata": {
                "report_type": self.metadata.report_type,
                "as_of_date": str(self.metadata.as_of_date) if self.metadata.as_of_date else None,
                "from_date": str(self.metadata.from_date) if self.metadata.from_date else None,
                "to_date": str(self.metadata.to_date) if self.metadata.to_date else None,
                "fiscal_year": self.metadata.fiscal_year,
                "empty_reason": self.metadata.empty_reason.value if self.metadata.empty_reason else None,
                "generated_at": self.metadata.generated_at,
            },
            "income_rows": [
                {
                    "account_id": str(r.account_id),
                    "account_number": r.account_number,
                    "account_name": r.account_name,
                    "amount": str(r.amount),
                    "is_group": r.is_group,
                    "indent_level": r.indent_level,
                    "is_subtotal": r.is_subtotal,
                }
                for r in self.income_rows
            ],
            "income_total": str(self.income_total),
            "expense_rows": [
                {
                    "account_id": str(r.account_id),
                    "account_number": r.account_number,
                    "account_name": r.account_name,
                    "amount": str(r.amount),
                    "is_group": r.is_group,
                    "indent_level": r.indent_level,
                    "is_subtotal": r.is_subtotal,
                }
                for r in self.expense_rows
            ],
            "expense_total": str(self.expense_total),
            "net_profit": str(self.net_profit),
        }

    def to_csv(self) -> str:
        """Generate CSV export."""
        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(["Profit and Loss Statement"])
        if self.metadata.from_date:
            writer.writerow([f"Period: {self.metadata.from_date} to {self.metadata.to_date}"])
        writer.writerow([])

        # Income section
        writer.writerow(["Income"])
        writer.writerow(["Account Number", "Account Name", "Amount"])
        for row in self.income_rows:
            indent = "  " * row.indent_level
            writer.writerow([
                f"{indent}{row.account_number}" if row.is_group else row.account_number,
                f"{indent}{row.account_name}" if row.is_subtotal else row.account_name,
                f"{row.amount:.2f}",
            ])
        writer.writerow(["", "Total Income", f"{self.income_total:.2f}"])
        writer.writerow([])

        # Expense section
        writer.writerow(["Expenses"])
        writer.writerow(["Account Number", "Account Name", "Amount"])
        for row in self.expense_rows:
            indent = "  " * row.indent_level
            writer.writerow([
                f"{indent}{row.account_number}" if row.is_group else row.account_number,
                f"{indent}{row.account_name}" if row.is_subtotal else row.account_name,
                f"{row.amount:.2f}",
            ])
        writer.writerow(["", "Total Expenses", f"{self.expense_total:.2f}"])
        writer.writerow([])

        # Net profit/loss
        writer.writerow(["", "Net Profit / (Loss)", f"{self.net_profit:.2f}"])

        return output.getvalue()


@dataclass
class BalanceSheetRow:
    """A single row in the Balance Sheet."""
    account_id: uuid.UUID
    account_number: str
    account_name: str
    amount: Decimal
    is_group: bool
    indent_level: int = 0
    is_subtotal: bool = False


@dataclass
class BalanceSheetResponse:
    """Balance Sheet response."""
    metadata: ReportMetadata
    # Assets
    asset_rows: list[BalanceSheetRow]
    total_assets: Decimal
    # Liabilities
    liability_rows: list[BalanceSheetRow]
    total_liabilities: Decimal
    # Equity
    equity_rows: list[BalanceSheetRow]
    total_equity: Decimal
    # Totals
    total_liabilities_and_equity: Decimal

    def to_dict(self) -> dict:
        return {
            "metadata": {
                "report_type": self.metadata.report_type,
                "as_of_date": str(self.metadata.as_of_date) if self.metadata.as_of_date else None,
                "empty_reason": self.metadata.empty_reason.value if self.metadata.empty_reason else None,
                "generated_at": self.metadata.generated_at,
            },
            "asset_rows": [
                {
                    "account_id": str(r.account_id),
                    "account_number": r.account_number,
                    "account_name": r.account_name,
                    "amount": str(r.amount),
                    "is_group": r.is_group,
                    "indent_level": r.indent_level,
                    "is_subtotal": r.is_subtotal,
                }
                for r in self.asset_rows
            ],
            "total_assets": str(self.total_assets),
            "liability_rows": [
                {
                    "account_id": str(r.account_id),
                    "account_number": r.account_number,
                    "account_name": r.account_name,
                    "amount": str(r.amount),
                    "is_group": r.is_group,
                    "indent_level": r.indent_level,
                    "is_subtotal": r.is_subtotal,
                }
                for r in self.liability_rows
            ],
            "total_liabilities": str(self.total_liabilities),
            "equity_rows": [
                {
                    "account_id": str(r.account_id),
                    "account_number": r.account_number,
                    "account_name": r.account_name,
                    "amount": str(r.amount),
                    "is_group": r.is_group,
                    "indent_level": r.indent_level,
                    "is_subtotal": r.is_subtotal,
                }
                for r in self.equity_rows
            ],
            "total_equity": str(self.total_equity),
            "total_liabilities_and_equity": str(self.total_liabilities_and_equity),
        }

    def to_csv(self) -> str:
        """Generate CSV export."""
        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(["Balance Sheet"])
        if self.metadata.as_of_date:
            writer.writerow([f"As of: {self.metadata.as_of_date}"])
        writer.writerow([])

        # Assets
        writer.writerow(["ASSETS"])
        writer.writerow(["Account Number", "Account Name", "Amount"])
        for row in self.asset_rows:
            indent = "  " * row.indent_level
            writer.writerow([
                f"{indent}{row.account_number}" if row.is_group else row.account_number,
                f"{indent}{row.account_name}" if row.is_subtotal else row.account_name,
                f"{row.amount:.2f}",
            ])
        writer.writerow(["", "Total Assets", f"{self.total_assets:.2f}"])
        writer.writerow([])

        # Liabilities
        writer.writerow(["LIABILITIES"])
        writer.writerow(["Account Number", "Account Name", "Amount"])
        for row in self.liability_rows:
            indent = "  " * row.indent_level
            writer.writerow([
                f"{indent}{row.account_number}" if row.is_group else row.account_number,
                f"{indent}{row.account_name}" if row.is_subtotal else row.account_name,
                f"{row.amount:.2f}",
            ])
        writer.writerow(["", "Total Liabilities", f"{self.total_liabilities:.2f}"])
        writer.writerow([])

        # Equity
        writer.writerow(["EQUITY"])
        writer.writerow(["Account Number", "Account Name", "Amount"])
        for row in self.equity_rows:
            indent = "  " * row.indent_level
            writer.writerow([
                f"{indent}{row.account_number}" if row.is_group else row.account_number,
                f"{indent}{row.account_name}" if row.is_subtotal else row.account_name,
                f"{row.amount:.2f}",
            ])
        writer.writerow(["", "Total Equity", f"{self.total_equity:.2f}"])
        writer.writerow([])

        # Totals
        writer.writerow(["", "Total Liabilities and Equity", f"{self.total_liabilities_and_equity:.2f}"])

        return output.getvalue()


@dataclass
class TrialBalanceRow:
    """A single row in the Trial Balance."""
    account_id: uuid.UUID
    account_number: str
    account_name: str
    root_type: str
    debit: Decimal
    credit: Decimal


@dataclass
class TrialBalanceResponse:
    """Trial Balance response."""
    metadata: ReportMetadata
    rows: list[TrialBalanceRow]
    total_debit: Decimal
    total_credit: Decimal
    is_balanced: bool  # Total debits should equal total credits

    def to_dict(self) -> dict:
        return {
            "metadata": {
                "report_type": self.metadata.report_type,
                "as_of_date": str(self.metadata.as_of_date) if self.metadata.as_of_date else None,
                "from_date": str(self.metadata.from_date) if self.metadata.from_date else None,
                "to_date": str(self.metadata.to_date) if self.metadata.to_date else None,
                "fiscal_year": self.metadata.fiscal_year,
                "empty_reason": self.metadata.empty_reason.value if self.metadata.empty_reason else None,
                "generated_at": self.metadata.generated_at,
            },
            "rows": [
                {
                    "account_id": str(r.account_id),
                    "account_number": r.account_number,
                    "account_name": r.account_name,
                    "root_type": r.root_type,
                    "debit": str(r.debit),
                    "credit": str(r.credit),
                }
                for r in self.rows
            ],
            "total_debit": str(self.total_debit),
            "total_credit": str(self.total_credit),
            "is_balanced": self.is_balanced,
        }

    def to_csv(self) -> str:
        """Generate CSV export."""
        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(["Trial Balance"])
        if self.metadata.as_of_date:
            writer.writerow([f"As of: {self.metadata.as_of_date}"])
        elif self.metadata.from_date:
            writer.writerow([f"Period: {self.metadata.from_date} to {self.metadata.to_date}"])
        writer.writerow([])

        # Column headers
        writer.writerow(["Account Number", "Account Name", "Debit", "Credit"])

        # Data rows
        for row in self.rows:
            writer.writerow([
                row.account_number,
                row.account_name,
                f"{row.debit:.2f}",
                f"{row.credit:.2f}",
            ])

        # Totals row
        writer.writerow(["", "TOTAL", f"{self.total_debit:.2f}", f"{self.total_credit:.2f}"])
        writer.writerow(["", f"Balanced: {self.is_balanced}", "", ""])

        return output.getvalue()


# ============================================================
# Helper Functions
# ============================================================


async def get_account_balances(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    root_types: list[str] | None = None,
    as_of_date: date | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
) -> list[AccountBalance]:
    """Get account balances from GL entries, rolled up to parent accounts.

    Args:
        db: Database session
        tenant_id: Tenant identifier
        root_types: Optional filter by root types (e.g., ["Income", "Expense"])
        as_of_date: For balance sheet (as-of-date), include entries up to this date
        from_date: For P&L (period-based), start of period
        to_date: For P&L (period-based), end of period

    Returns:
        List of AccountBalance objects with rolled-up balances
    """
    # Build conditions for GL entry date filtering
    gl_conditions = [GLEntry.tenant_id == tenant_id]

    if as_of_date:
        # Balance sheet: include all entries up to and including as_of_date
        gl_conditions.append(GLEntry.posting_date <= as_of_date)
    elif from_date and to_date:
        # P&L: include entries within the period
        gl_conditions.append(GLEntry.posting_date >= from_date)
        gl_conditions.append(GLEntry.posting_date <= to_date)

    # Exclude reversed entries
    gl_conditions.append(GLEntry.reversed_by_id.is_(None))

    # Get GL balances per account
    balance_query = (
        select(
            GLEntry.account_id,
            func.coalesce(func.sum(GLEntry.debit), 0).label("total_debit"),
            func.coalesce(func.sum(GLEntry.credit), 0).label("total_credit"),
        )
        .where(and_(*gl_conditions))
        .group_by(GLEntry.account_id)
    )
    result = await db.execute(balance_query)
    gl_balances = {row.account_id: (Decimal(str(row.total_debit)), Decimal(str(row.total_credit)))
                   for row in result.all()}

    # Get account tree
    account_conditions = [Account.tenant_id == tenant_id, Account.is_disabled == False]
    if root_types:
        account_conditions.append(Account.root_type.in_(root_types))

    accounts_query = (
        select(Account)
        .where(and_(*account_conditions))
        .order_by(Account.root_type, Account.sort_order, Account.account_number)
    )
    accounts_result = await db.execute(accounts_query)
    accounts = {acc.id: acc for acc in accounts_result.scalars().all()}

    if not accounts:
        return []

    # Build account balance objects
    account_balances: dict[uuid.UUID, AccountBalance] = {}
    for acc_id, acc in accounts.items():
        debit, credit = gl_balances.get(acc_id, (Decimal("0"), Decimal("0")))
        # For Income/Expense accounts, credit reduces balance (expense debit increases)
        # For Asset/Liability/Equity accounts, debit increases, credit decreases
        if acc.root_type in ("Income", "Expense"):
            balance = credit - debit  # Income: credit is positive, Expense: debit is positive
        else:
            balance = debit - credit

        account_balances[acc_id] = AccountBalance(
            account_id=acc_id,
            account_number=acc.account_number,
            account_name=acc.account_name,
            root_type=acc.root_type,
            account_type=acc.account_type,
            is_group=acc.is_group,
            debit=debit,
            credit=credit,
            balance=balance,
        )

    # Roll up child balances to parents
    for acc_id, acc in accounts.items():
        if acc.parent_id and acc.parent_id in account_balances:
            parent_bal = account_balances[acc.parent_id]
            child_bal = account_balances[acc_id]
            parent_bal.debit += child_bal.debit
            parent_bal.credit += child_bal.credit
            parent_bal.balance += child_bal.balance
            parent_bal.children.append(child_bal)

    # Return only root accounts (those without parents in our filter)
    roots = [
        bal for acc_id, bal in account_balances.items()
        if accounts[acc_id].parent_id is None or accounts[acc_id].parent_id not in accounts
    ]

    return roots


async def determine_empty_reason(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    entry_count: int,
    root_types: list[str] | None = None,
) -> EmptyReason | None:
    """Classify empty report output for the requested account scope."""
    if entry_count > 0:
        return None

    account_conditions = [
        Account.tenant_id == tenant_id,
        Account.is_group == False,
    ]
    if root_types:
        account_conditions.append(Account.root_type.in_(root_types))

    account_count_result = await db.execute(
        select(func.count(Account.id)).where(and_(*account_conditions))
    )
    account_count = account_count_result.scalar() or 0
    if account_count == 0:
        return EmptyReason.NO_ACCOUNTS_CONFIGURED

    active_account_count_result = await db.execute(
        select(func.count(Account.id)).where(
            and_(
                *account_conditions,
                Account.is_disabled == False,
            )
        )
    )
    active_account_count = active_account_count_result.scalar() or 0
    if active_account_count == 0:
        return EmptyReason.ALL_ACCOUNTS_DISABLED

    return EmptyReason.NO_ENTRIES_IN_PERIOD


def build_pl_rows(
    balances: list[AccountBalance],
    indent: int = 0,
) -> tuple[list[ProfitAndLossRow], Decimal]:
    """Build P&L rows from account balances with subtotals.

    Args:
        balances: List of account balances (roots, will include children)
        indent: Current indentation level

    Returns:
        Tuple of (rows, total_amount)
    """
    rows: list[ProfitAndLossRow] = []
    total = Decimal("0")

    for bal in balances:
        # Add this account's row
        amount = abs(bal.balance)  # Use absolute value for display
        rows.append(ProfitAndLossRow(
            account_id=bal.account_id,
            account_number=bal.account_number,
            account_name=bal.account_name,
            amount=amount,
            is_group=bal.is_group,
            indent_level=indent,
            is_subtotal=False,
        ))

        # Add children rows
        if bal.children:
            child_rows, child_total = build_pl_rows(sorted(bal.children, key=lambda x: x.account_number), indent + 1)
            rows.extend(child_rows)

            # Add subtotal row for this group
            rows.append(ProfitAndLossRow(
                account_id=bal.account_id,
                account_number="",  # No number for subtotals
                account_name=f"Total {bal.account_name}",
                amount=child_total,
                is_group=False,
                indent_level=indent,
                is_subtotal=True,
            ))
            total += child_total
        else:
            total += amount

    return rows, total


def build_bs_rows(
    balances: list[AccountBalance],
    indent: int = 0,
) -> tuple[list[BalanceSheetRow], Decimal]:
    """Build Balance Sheet rows from account balances with subtotals.

    Args:
        balances: List of account balances
        indent: Current indentation level

    Returns:
        Tuple of (rows, total_amount)
    """
    rows: list[BalanceSheetRow] = []
    total = Decimal("0")

    for bal in balances:
        # Add this account's row
        # Assets: debit balance is positive
        # Liabilities/Equity: credit balance is positive
        if bal.root_type == "Asset":
            amount = bal.debit - bal.credit  # Positive if debit > credit
        else:
            amount = bal.credit - bal.debit  # Positive if credit > debit

        rows.append(BalanceSheetRow(
            account_id=bal.account_id,
            account_number=bal.account_number,
            account_name=bal.account_name,
            amount=abs(amount),
            is_group=bal.is_group,
            indent_level=indent,
            is_subtotal=False,
        ))

        # Add children rows
        if bal.children:
            child_rows, child_total = build_bs_rows(sorted(bal.children, key=lambda x: x.account_number), indent + 1)
            rows.extend(child_rows)

            # Add subtotal row for this group
            rows.append(BalanceSheetRow(
                account_id=bal.account_id,
                account_number="",
                account_name=f"Total {bal.account_name}",
                amount=child_total,
                is_group=False,
                indent_level=indent,
                is_subtotal=True,
            ))
            total += child_total
        else:
            total += abs(amount)

    return rows, total


# ============================================================
# Report Service Functions
# ============================================================


async def get_profit_and_loss(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    from_date: date,
    to_date: date,
) -> ProfitAndLossResponse:
    """Get Profit and Loss statement for a period.

    Args:
        db: Database session
        tenant_id: Tenant identifier
        from_date: Start of period
        to_date: End of period

    Returns:
        ProfitAndLossResponse with income, expenses, and net profit
    """
    from datetime import datetime, timezone

    # Check if any GL entries exist in the period
    entry_check = await db.execute(
        select(func.count(GLEntry.id))
        .where(
            and_(
                GLEntry.tenant_id == tenant_id,
                GLEntry.posting_date >= from_date,
                GLEntry.posting_date <= to_date,
                GLEntry.reversed_by_id.is_(None),
            )
        )
    )
    entry_count = entry_check.scalar() or 0

    # Get income balances
    income_balances = await get_account_balances(
        db, tenant_id,
        root_types=["Income"],
        from_date=from_date,
        to_date=to_date,
    )

    # Get expense balances
    expense_balances = await get_account_balances(
        db, tenant_id,
        root_types=["Expense"],
        from_date=from_date,
        to_date=to_date,
    )

    empty_reason = await determine_empty_reason(
        db,
        tenant_id,
        entry_count,
        root_types=["Income", "Expense"],
    )

    if entry_count == 0:
        income_rows: list[ProfitAndLossRow] = []
        expense_rows: list[ProfitAndLossRow] = []
        income_total = Decimal("0")
        expense_total = Decimal("0")
    else:
        income_rows, income_total = build_pl_rows(income_balances)
        expense_rows, expense_total = build_pl_rows(expense_balances)

    # Net profit = Income - Expenses
    net_profit = income_total - expense_total

    return ProfitAndLossResponse(
        metadata=ReportMetadata(
            report_type="Profit and Loss",
            from_date=from_date,
            to_date=to_date,
            empty_reason=empty_reason,
            generated_at=datetime.now(tz=timezone.utc).isoformat(),
        ),
        income_rows=income_rows,
        income_total=income_total,
        expense_rows=expense_rows,
        expense_total=expense_total,
        net_profit=net_profit,
    )


async def get_balance_sheet(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    as_of_date: date,
) -> BalanceSheetResponse:
    """Get Balance Sheet as of a specific date.

    Args:
        db: Database session
        tenant_id: Tenant identifier
        as_of_date: The as-of date for the balance sheet

    Returns:
        BalanceSheetResponse with assets, liabilities, equity, and totals
    """
    from datetime import datetime, timezone

    # Check if any GL entries exist up to the as_of_date
    entry_check = await db.execute(
        select(func.count(GLEntry.id))
        .where(
            and_(
                GLEntry.tenant_id == tenant_id,
                GLEntry.posting_date <= as_of_date,
                GLEntry.reversed_by_id.is_(None),
            )
        )
    )
    entry_count = entry_check.scalar() or 0

    # Get asset balances
    asset_balances = await get_account_balances(
        db, tenant_id,
        root_types=["Asset"],
        as_of_date=as_of_date,
    )

    # Get liability balances
    liability_balances = await get_account_balances(
        db, tenant_id,
        root_types=["Liability"],
        as_of_date=as_of_date,
    )

    # Get equity balances
    equity_balances = await get_account_balances(
        db, tenant_id,
        root_types=["Equity"],
        as_of_date=as_of_date,
    )

    # Build rows
    asset_rows, total_assets = build_bs_rows(asset_balances)
    liability_rows, total_liabilities = build_bs_rows(liability_balances)
    equity_rows, total_equity = build_bs_rows(equity_balances)

    income_balances = await get_account_balances(
        db,
        tenant_id,
        root_types=["Income"],
        as_of_date=as_of_date,
    )
    expense_balances = await get_account_balances(
        db,
        tenant_id,
        root_types=["Expense"],
        as_of_date=as_of_date,
    )
    _, income_total = build_pl_rows(income_balances)
    _, expense_total = build_pl_rows(expense_balances)
    current_earnings = income_total - expense_total
    if current_earnings != Decimal("0"):
        equity_rows.append(
            BalanceSheetRow(
                account_id=uuid.UUID(int=0),
                account_number="",
                account_name=(
                    "Current Period Earnings"
                    if current_earnings > 0
                    else "Current Period Loss"
                ),
                amount=abs(current_earnings),
                is_group=False,
                indent_level=0,
                is_subtotal=True,
            )
        )
        total_equity += current_earnings

    # Total Liabilities and Equity
    total_liabilities_and_equity = total_liabilities + total_equity

    empty_reason = await determine_empty_reason(
        db,
        tenant_id,
        entry_count,
        root_types=["Asset", "Liability", "Equity"],
    )

    return BalanceSheetResponse(
        metadata=ReportMetadata(
            report_type="Balance Sheet",
            as_of_date=as_of_date,
            empty_reason=empty_reason,
            generated_at=datetime.now(tz=timezone.utc).isoformat(),
        ),
        asset_rows=asset_rows,
        total_assets=total_assets,
        liability_rows=liability_rows,
        total_liabilities=total_liabilities,
        equity_rows=equity_rows,
        total_equity=total_equity,
        total_liabilities_and_equity=total_liabilities_and_equity,
    )


async def get_trial_balance(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    as_of_date: date | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
) -> TrialBalanceResponse:
    """Get Trial Balance.

    Shows all accounts with their debit/credit balances.
    Total debits should equal total credits.

    Args:
        db: Database session
        tenant_id: Tenant identifier
        as_of_date: Optional as-of date (for snapshot)
        from_date: Optional start of period
        to_date: Optional end of period

    Returns:
        TrialBalanceResponse with all accounts and totals
    """
    from datetime import datetime, timezone

    # Build conditions
    gl_conditions = [GLEntry.tenant_id == tenant_id]

    if as_of_date:
        gl_conditions.append(GLEntry.posting_date <= as_of_date)
    elif from_date and to_date:
        gl_conditions.append(GLEntry.posting_date >= from_date)
        gl_conditions.append(GLEntry.posting_date <= to_date)

    # Exclude reversed entries
    gl_conditions.append(GLEntry.reversed_by_id.is_(None))

    # Get GL balances per account
    balance_query = (
        select(
            GLEntry.account_id,
            func.coalesce(func.sum(GLEntry.debit), 0).label("total_debit"),
            func.coalesce(func.sum(GLEntry.credit), 0).label("total_credit"),
        )
        .where(and_(*gl_conditions))
        .group_by(GLEntry.account_id)
    )
    result = await db.execute(balance_query)
    gl_balances = {row.account_id: (Decimal(str(row.total_debit)), Decimal(str(row.total_credit)))
                   for row in result.all()}

    # Get all accounts
    accounts_query = (
        select(Account)
        .where(
            and_(
                Account.tenant_id == tenant_id,
                Account.is_disabled == False,
            )
        )
        .order_by(Account.root_type, Account.account_number)
    )
    accounts_result = await db.execute(accounts_query)
    accounts = list(accounts_result.scalars().all())

    # Build rows
    rows: list[TrialBalanceRow] = []
    total_debit = Decimal("0")
    total_credit = Decimal("0")

    for acc in accounts:
        if acc.is_group:
            continue  # Only include ledger accounts in trial balance

        debit, credit = gl_balances.get(acc.id, (Decimal("0"), Decimal("0")))

        if acc.root_type in ("Asset", "Expense"):
            balance = debit - credit
            if balance >= 0:
                debit = balance
                credit = Decimal("0")
            else:
                credit = abs(balance)
                debit = Decimal("0")
        else:
            balance = credit - debit
            if balance >= 0:
                credit = balance
                debit = Decimal("0")
            else:
                debit = abs(balance)
                credit = Decimal("0")

        rows.append(TrialBalanceRow(
            account_id=acc.id,
            account_number=acc.account_number,
            account_name=acc.account_name,
            root_type=acc.root_type,
            debit=debit,
            credit=credit,
        ))
        total_debit += debit
        total_credit += credit

    # Check if balanced (with small tolerance for floating point)
    is_balanced = abs(total_debit - total_credit) < Decimal("0.01")

    entry_count = sum(1 for debit, credit in gl_balances.values() if debit != 0 or credit != 0)
    empty_reason = await determine_empty_reason(db, tenant_id, entry_count)

    return TrialBalanceResponse(
        metadata=ReportMetadata(
            report_type="Trial Balance",
            as_of_date=as_of_date,
            from_date=from_date,
            to_date=to_date,
            empty_reason=empty_reason,
            generated_at=datetime.now(tz=timezone.utc).isoformat(),
        ),
        rows=rows,
        total_debit=total_debit,
        total_credit=total_credit,
        is_balanced=is_balanced,
    )
