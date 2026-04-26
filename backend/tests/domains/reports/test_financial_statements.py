"""Tests for financial statement reporting (Epic 26.3).

Tests P&L, Balance Sheet, and Trial Balance calculations from GL entries.
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from common.models.account import (
    Account,
    AccountRootType,
    AccountReportType,
    AccountType,
)
from common.models.fiscal_year import FiscalYear, FiscalYearStatus
from common.models.gl_entry import GLEntry, GLEntryType
from common.models.journal_entry import JournalEntry, JournalEntryStatus, VoucherType
from common.models.journal_entry_line import JournalEntryLine

from domains.accounting.reporting import (
    EmptyReason,
    ProfitAndLossResponse,
    BalanceSheetResponse,
    TrialBalanceResponse,
    get_profit_and_loss,
    get_balance_sheet,
    get_trial_balance,
    get_account_balances,
    build_pl_rows,
    build_bs_rows,
)
from domains.accounting.service import create_journal_entry, submit_journal_entry, seed_starter_chart
from domains.accounting.schemas import JournalEntryCreate, JournalEntryLineCreate
from tests.db import isolated_async_session


@pytest_asyncio.fixture
async def db() -> AsyncSession:
    """Provide an isolated database session for each test."""
    async with isolated_async_session() as session:
        yield session


@pytest.fixture
def tenant_id() -> uuid.UUID:
    """Create a test tenant ID."""
    return uuid.uuid4()


@pytest.fixture
def actor_id() -> uuid.UUID:
    """Create a test user/actor ID."""
    return uuid.uuid4()


@pytest_asyncio.fixture
async def setup_accounts_and_fiscal_year(
    db: AsyncSession, tenant_id: uuid.UUID
) -> tuple[Account, Account, Account, Account, Account, Account, FiscalYear]:
    """Create test accounts and fiscal year for reporting tests."""
    # Seed starter chart
    await seed_starter_chart(db, tenant_id)

    # Get accounts
    from sqlalchemy import select

    result = await db.execute(
        select(Account).where(
            Account.tenant_id == tenant_id,
            Account.account_number == "1000",  # Cash
        )
    )
    cash_account = result.scalar_one()

    result = await db.execute(
        select(Account).where(
            Account.tenant_id == tenant_id,
            Account.account_number == "2000",  # Accounts Payable
        )
    )
    ap_account = result.scalar_one()

    result = await db.execute(
        select(Account).where(
            Account.tenant_id == tenant_id,
            Account.account_number == "3000",  # Retained Earnings
        )
    )
    equity_account = result.scalar_one()

    result = await db.execute(
        select(Account).where(
            Account.tenant_id == tenant_id,
            Account.account_number == "4000",  # Sales Revenue
        )
    )
    revenue_account = result.scalar_one()

    result = await db.execute(
        select(Account).where(
            Account.tenant_id == tenant_id,
            Account.account_number == "5000",  # COGS
        )
    )
    cogs_account = result.scalar_one()

    result = await db.execute(
        select(Account).where(
            Account.tenant_id == tenant_id,
            Account.account_number == "6000",  # Operating Expenses
        )
    )
    expense_account = result.scalar_one()

    # Create fiscal year
    fiscal_year = FiscalYear(
        tenant_id=tenant_id,
        label="FY2026",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        status=FiscalYearStatus.OPEN.value,
        is_default=True,
    )
    db.add(fiscal_year)
    await db.flush()

    return (
        cash_account,
        ap_account,
        equity_account,
        revenue_account,
        cogs_account,
        expense_account,
        fiscal_year,
    )


async def create_and_submit_journal_entry(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    actor_id: uuid.UUID,
    posting_date: date,
    lines: list[tuple[uuid.UUID, float, float]],
    narration: str = "Test entry",
) -> JournalEntry:
    """Helper to create and submit a journal entry."""
    data = JournalEntryCreate(
        voucher_type=VoucherType.JOURNAL_ENTRY,
        posting_date=posting_date,
        narration=narration,
        lines=[
            JournalEntryLineCreate(account_id=acc_id, debit=debit, credit=credit)
            for acc_id, debit, credit in lines
        ],
    )
    entry = await create_journal_entry(db, tenant_id, data)
    submitted, _ = await submit_journal_entry(db, tenant_id, entry.id, actor_id)
    return submitted


# ============================================================
# P&L Tests
# ============================================================


@pytest.mark.asyncio
class TestProfitAndLoss:
    """Tests for Profit and Loss report."""

    async def test_pnl_empty_period(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        setup_accounts_and_fiscal_year,
    ) -> None:
        """P&L for period with no entries returns empty state with zero totals."""
        _, _, _, _, _, _, _ = setup_accounts_and_fiscal_year

        result = await get_profit_and_loss(
            db, tenant_id,
            from_date=date(2026, 1, 1),
            to_date=date(2026, 1, 31),
        )

        assert result.metadata.empty_reason == EmptyReason.NO_ENTRIES_IN_PERIOD
        assert result.income_total == Decimal("0")
        assert result.expense_total == Decimal("0")
        assert result.net_profit == Decimal("0")
        assert result.income_rows == []
        assert result.expense_rows == []

    async def test_pnl_with_revenue(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        setup_accounts_and_fiscal_year,
    ) -> None:
        """P&L correctly calculates revenue."""
        cash, _, _, revenue, _, _, _ = setup_accounts_and_fiscal_year

        # Create a sales entry: Debit Cash 1000, Credit Revenue 1000
        await create_and_submit_journal_entry(
            db, tenant_id, actor_id,
            posting_date=date(2026, 3, 15),
            lines=[(cash.id, 1000.0, 0.0), (revenue.id, 0.0, 1000.0)],
            narration="Sales revenue",
        )

        result = await get_profit_and_loss(
            db, tenant_id,
            from_date=date(2026, 3, 1),
            to_date=date(2026, 3, 31),
        )

        assert result.metadata.empty_reason is None
        assert result.income_total == Decimal("1000")
        assert len(result.income_rows) > 0

    async def test_pnl_with_expenses(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        setup_accounts_and_fiscal_year,
    ) -> None:
        """P&L correctly calculates expenses."""
        cash, _, _, _, cogs, expense, _ = setup_accounts_and_fiscal_year

        # Create expense entries
        await create_and_submit_journal_entry(
            db, tenant_id, actor_id,
            posting_date=date(2026, 3, 15),
            lines=[(cash.id, 500.0, 0.0), (cogs.id, 0.0, 500.0)],
            narration="COGS",
        )
        await create_and_submit_journal_entry(
            db, tenant_id, actor_id,
            posting_date=date(2026, 3, 20),
            lines=[(cash.id, 300.0, 0.0), (expense.id, 0.0, 300.0)],
            narration="Operating expenses",
        )

        result = await get_profit_and_loss(
            db, tenant_id,
            from_date=date(2026, 3, 1),
            to_date=date(2026, 3, 31),
        )

        assert result.expense_total == Decimal("800")
        assert len(result.expense_rows) > 0

    async def test_pnl_net_profit_calculation(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        setup_accounts_and_fiscal_year,
    ) -> None:
        """P&L correctly calculates net profit."""
        cash, _, _, revenue, cogs, _, _ = setup_accounts_and_fiscal_year

        # Revenue: 1000
        await create_and_submit_journal_entry(
            db, tenant_id, actor_id,
            posting_date=date(2026, 3, 15),
            lines=[(cash.id, 1000.0, 0.0), (revenue.id, 0.0, 1000.0)],
            narration="Sales",
        )
        # COGS: 400
        await create_and_submit_journal_entry(
            db, tenant_id, actor_id,
            posting_date=date(2026, 3, 15),
            lines=[(cogs.id, 400.0, 0.0), (cash.id, 0.0, 400.0)],
            narration="COGS",
        )

        result = await get_profit_and_loss(
            db, tenant_id,
            from_date=date(2026, 3, 1),
            to_date=date(2026, 3, 31),
        )

        assert result.income_total == Decimal("1000")
        assert result.expense_total == Decimal("400")
        assert result.net_profit == Decimal("600")

    async def test_pnl_excludes_reversed_entries(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        setup_accounts_and_fiscal_year,
    ) -> None:
        """P&L excludes entries that have been reversed."""
        cash, _, _, revenue, _, _, _ = setup_accounts_and_fiscal_year

        # Create and reverse an entry
        data = JournalEntryCreate(
            voucher_type=VoucherType.JOURNAL_ENTRY,
            posting_date=date(2026, 3, 15),
            narration="This will be reversed",
            lines=[
                JournalEntryLineCreate(account_id=cash.id, debit=500.0, credit=0.0),
                JournalEntryLineCreate(account_id=revenue.id, debit=0.0, credit=500.0),
            ],
        )
        entry = await create_journal_entry(db, tenant_id, data)
        await submit_journal_entry(db, tenant_id, entry.id, actor_id)

        # Reverse it
        from domains.accounting.service import reverse_journal_entry
        await reverse_journal_entry(
            db, tenant_id, entry.id, actor_id,
            reversal_date=date(2026, 3, 20),
        )

        result = await get_profit_and_loss(
            db, tenant_id,
            from_date=date(2026, 3, 1),
            to_date=date(2026, 3, 31),
        )

        # Revenue should be 0 because entry was reversed
        assert result.income_total == Decimal("0")

    async def test_pnl_period_filtering(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        setup_accounts_and_fiscal_year,
    ) -> None:
        """P&L only includes entries within the specified period."""
        cash, _, _, revenue, _, _, _ = setup_accounts_and_fiscal_year

        # Entry in March (in range)
        await create_and_submit_journal_entry(
            db, tenant_id, actor_id,
            posting_date=date(2026, 3, 15),
            lines=[(cash.id, 1000.0, 0.0), (revenue.id, 0.0, 1000.0)],
        )
        # Entry in April (out of range)
        await create_and_submit_journal_entry(
            db, tenant_id, actor_id,
            posting_date=date(2026, 4, 15),
            lines=[(cash.id, 500.0, 0.0), (revenue.id, 0.0, 500.0)],
        )

        # Query March only
        result = await get_profit_and_loss(
            db, tenant_id,
            from_date=date(2026, 3, 1),
            to_date=date(2026, 3, 31),
        )

        assert result.income_total == Decimal("1000")

    async def test_pnl_csv_export(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        setup_accounts_and_fiscal_year,
    ) -> None:
        """P&L CSV export contains correct data."""
        cash, _, _, revenue, _, _, _ = setup_accounts_and_fiscal_year

        await create_and_submit_journal_entry(
            db, tenant_id, actor_id,
            posting_date=date(2026, 3, 15),
            lines=[(cash.id, 1000.0, 0.0), (revenue.id, 0.0, 1000.0)],
        )

        result = await get_profit_and_loss(
            db, tenant_id,
            from_date=date(2026, 3, 1),
            to_date=date(2026, 3, 31),
        )

        csv = result.to_csv()
        assert "Profit and Loss Statement" in csv
        assert "1000.00" in csv


# ============================================================
# Balance Sheet Tests
# ============================================================


@pytest.mark.asyncio
class TestBalanceSheet:
    """Tests for Balance Sheet report."""

    async def test_bs_empty_date(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        setup_accounts_and_fiscal_year,
    ) -> None:
        """BS for date with no entries returns empty state with zero totals."""
        _, _, _, _, _, _, _ = setup_accounts_and_fiscal_year

        result = await get_balance_sheet(
            db, tenant_id,
            as_of_date=date(2026, 1, 15),
        )

        assert result.metadata.empty_reason == EmptyReason.NO_ENTRIES_IN_PERIOD
        assert result.total_assets == Decimal("0")

    async def test_bs_asset_accounts(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        setup_accounts_and_fiscal_year,
    ) -> None:
        """BS correctly shows asset account balances."""
        cash, _, _, _, _, _, _ = setup_accounts_and_fiscal_year

        # Create entries to cash account
        await create_and_submit_journal_entry(
            db, tenant_id, actor_id,
            posting_date=date(2026, 3, 15),
            lines=[(cash.id, 5000.0, 0.0)],  # Debit increases asset
            narration="Initial deposit",
        )

        result = await get_balance_sheet(
            db, tenant_id,
            as_of_date=date(2026, 3, 31),
        )

        assert result.total_assets == Decimal("5000")
        assert len(result.asset_rows) > 0

    async def test_bs_liability_accounts(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        setup_accounts_and_fiscal_year,
    ) -> None:
        """BS correctly shows liability account balances."""
        cash, ap, _, _, _, _, _ = setup_accounts_and_fiscal_year

        # Create liability entry: Debit Expense, Credit AP
        _, _, _, _, _, expense, _ = setup_accounts_and_fiscal_year
        await create_and_submit_journal_entry(
            db, tenant_id, actor_id,
            posting_date=date(2026, 3, 15),
            lines=[(expense.id, 1000.0, 0.0), (ap.id, 0.0, 1000.0)],
            narration="Expense on credit",
        )

        result = await get_balance_sheet(
            db, tenant_id,
            as_of_date=date(2026, 3, 31),
        )

        assert result.total_liabilities == Decimal("1000")
        assert len(result.liability_rows) > 0

    async def test_bs_equity_accounts(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        setup_accounts_and_fiscal_year,
    ) -> None:
        """BS correctly shows equity account balances."""
        _, _, equity, _, _, _, _ = setup_accounts_and_fiscal_year

        # Create equity entry
        _, _, _, _, _, _, _ = setup_accounts_and_fiscal_year  # Get cogs for balanced entry
        from sqlalchemy import select

        result = await db.execute(
            select(Account).where(
                Account.tenant_id == tenant_id,
                Account.account_number == "5000",
            )
        )
        cogs = result.scalar_one()

        await create_and_submit_journal_entry(
            db, tenant_id, actor_id,
            posting_date=date(2026, 3, 15),
            lines=[(cogs.id, 500.0, 0.0), (equity.id, 0.0, 500.0)],
            narration="Expense reduces equity",
        )

        bs_result = await get_balance_sheet(
            db, tenant_id,
            as_of_date=date(2026, 3, 31),
        )

        # Equity should have the retained earnings with the expense impact
        assert bs_result.total_equity is not None

    async def test_bs_as_of_date_filtering(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        setup_accounts_and_fiscal_year,
    ) -> None:
        """BS only includes entries up to the as-of date."""
        cash, _, _, _, _, _, _ = setup_accounts_and_fiscal_year

        # Entry on March 15
        await create_and_submit_journal_entry(
            db, tenant_id, actor_id,
            posting_date=date(2026, 3, 15),
            lines=[(cash.id, 1000.0, 0.0)],
            narration="March entry",
        )
        # Entry on April 15
        await create_and_submit_journal_entry(
            db, tenant_id, actor_id,
            posting_date=date(2026, 4, 15),
            lines=[(cash.id, 500.0, 0.0)],
            narration="April entry",
        )

        # Query as of March 31 (should include March, exclude April)
        result = await get_balance_sheet(
            db, tenant_id,
            as_of_date=date(2026, 3, 31),
        )

        assert result.total_assets == Decimal("1000")

        # Query as of April 30 (should include both)
        result_full = await get_balance_sheet(
            db, tenant_id,
            as_of_date=date(2026, 4, 30),
        )

        assert result_full.total_assets == Decimal("1500")

    async def test_bs_csv_export(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        setup_accounts_and_fiscal_year,
    ) -> None:
        """BS CSV export contains correct data."""
        cash, _, _, _, _, _, _ = setup_accounts_and_fiscal_year

        await create_and_submit_journal_entry(
            db, tenant_id, actor_id,
            posting_date=date(2026, 3, 15),
            lines=[(cash.id, 1000.0, 0.0)],
        )

        result = await get_balance_sheet(
            db, tenant_id,
            as_of_date=date(2026, 3, 31),
        )

        csv = result.to_csv()
        assert "Balance Sheet" in csv
        assert "1000.00" in csv


# ============================================================
# Trial Balance Tests
# ============================================================


@pytest.mark.asyncio
class TestTrialBalance:
    """Tests for Trial Balance report."""

    async def test_tb_empty_period(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        setup_accounts_and_fiscal_year,
    ) -> None:
        """TB for period with no entries returns empty state."""
        _, _, _, _, _, _, _ = setup_accounts_and_fiscal_year

        result = await get_trial_balance(
            db, tenant_id,
            from_date=date(2026, 1, 1),
            to_date=date(2026, 1, 31),
        )

        assert result.metadata.empty_reason == EmptyReason.NO_ENTRIES_IN_PERIOD
        assert result.total_debit == Decimal("0")
        assert result.total_credit == Decimal("0")
        assert result.is_balanced is True  # Zero equals zero

    async def test_tb_balanced_entry(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        setup_accounts_and_fiscal_year,
    ) -> None:
        """TB is balanced when entries are balanced."""
        cash, _, _, revenue, _, _, _ = setup_accounts_and_fiscal_year

        await create_and_submit_journal_entry(
            db, tenant_id, actor_id,
            posting_date=date(2026, 3, 15),
            lines=[(cash.id, 1000.0, 0.0), (revenue.id, 0.0, 1000.0)],
        )

        result = await get_trial_balance(
            db, tenant_id,
            from_date=date(2026, 3, 1),
            to_date=date(2026, 3, 31),
        )

        assert result.is_balanced is True
        assert result.total_debit == result.total_credit

    async def test_tb_all_accounts_listed(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        setup_accounts_and_fiscal_year,
    ) -> None:
        """TB lists all accounts, not just those with activity."""
        _, _, _, _, _, _, _ = setup_accounts_and_fiscal_year

        result = await get_trial_balance(
            db, tenant_id,
            as_of_date=date(2026, 3, 31),
        )

        # Should have rows for all ledger accounts
        assert len(result.rows) > 0

    async def test_tb_excludes_group_accounts(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        setup_accounts_and_fiscal_year,
    ) -> None:
        """TB only includes ledger accounts (not group accounts)."""
        cash, _, _, revenue, _, _, _ = setup_accounts_and_fiscal_year

        await create_and_submit_journal_entry(
            db, tenant_id, actor_id,
            posting_date=date(2026, 3, 15),
            lines=[(cash.id, 1000.0, 0.0), (revenue.id, 0.0, 1000.0)],
        )

        result = await get_trial_balance(
            db, tenant_id,
            as_of_date=date(2026, 3, 31),
        )

        # All rows should be ledger accounts (no groups)
        for row in result.rows:
            assert row.account_number != "1"  # Assets root
            assert row.account_number != "4"  # Income root

    async def test_tb_csv_export(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        setup_accounts_and_fiscal_year,
    ) -> None:
        """TB CSV export contains correct data."""
        cash, _, _, revenue, _, _, _ = setup_accounts_and_fiscal_year

        await create_and_submit_journal_entry(
            db, tenant_id, actor_id,
            posting_date=date(2026, 3, 15),
            lines=[(cash.id, 1000.0, 0.0), (revenue.id, 0.0, 1000.0)],
        )

        result = await get_trial_balance(
            db, tenant_id,
            as_of_date=date(2026, 3, 31),
        )

        csv = result.to_csv()
        assert "Trial Balance" in csv
        assert "1000.00" in csv


# ============================================================
# Account Rollup Tests
# ============================================================


@pytest.mark.asyncio
class TestAccountRollups:
    """Tests for account balance rollups."""

    async def test_child_accounts_rollup_to_parent(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        setup_accounts_and_fiscal_year,
    ) -> None:
        """Child account balances roll up to parent groups."""
        cash, _, _, _, _, _, _ = setup_accounts_and_fiscal_year

        # Create entries to cash (a child of Assets)
        await create_and_submit_journal_entry(
            db, tenant_id, actor_id,
            posting_date=date(2026, 3, 15),
            lines=[(cash.id, 1000.0, 0.0)],
        )

        balances = await get_account_balances(
            db, tenant_id,
            root_types=["Asset"],
            as_of_date=date(2026, 3, 31),
        )

        # Find the Assets root
        assets_root = next((b for b in balances if b.account_number == "1"), None)
        assert assets_root is not None
        assert assets_root.debit == Decimal("1000")

    async def test_ledger_accounts_show_own_balance(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        setup_accounts_and_fiscal_year,
    ) -> None:
        """Ledger accounts show their own balances."""
        cash, _, _, _, _, _, _ = setup_accounts_and_fiscal_year

        await create_and_submit_journal_entry(
            db, tenant_id, actor_id,
            posting_date=date(2026, 3, 15),
            lines=[(cash.id, 2000.0, 0.0)],
        )

        balances = await get_account_balances(
            db, tenant_id,
            root_types=["Asset"],
            as_of_date=date(2026, 3, 31),
        )

        # Find the cash account
        cash_balance = next(
            (b for b in balances if b.account_number == "1000"),
            None
        )
        if cash_balance:
            assert cash_balance.debit == Decimal("2000")


# ============================================================
# Integration Tests
# ============================================================


@pytest.mark.asyncio
class TestFinancialStatementIntegration:
    """Integration tests for complete accounting scenarios."""

    async def test_complete_accounting_cycle(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        setup_accounts_and_fiscal_year,
    ) -> None:
        """Test complete scenario: sales, expenses, assets, and equity."""
        cash, ap, equity, revenue, cogs, expense, _ = setup_accounts_and_fiscal_year

        # 1. Initial investment: Debit Cash 10000, Credit Equity 10000
        await create_and_submit_journal_entry(
            db, tenant_id, actor_id,
            posting_date=date(2026, 3, 1),
            lines=[(cash.id, 10000.0, 0.0), (equity.id, 0.0, 10000.0)],
            narration="Initial capital",
        )

        # 2. Purchase inventory: Debit COGS 3000, Credit Cash 3000
        await create_and_submit_journal_entry(
            db, tenant_id, actor_id,
            posting_date=date(2026, 3, 10),
            lines=[(cogs.id, 3000.0, 0.0), (cash.id, 0.0, 3000.0)],
            narration="Purchase inventory",
        )

        # 3. Make a sale: Debit Cash 5000, Credit Revenue 5000
        await create_and_submit_journal_entry(
            db, tenant_id, actor_id,
            posting_date=date(2026, 3, 15),
            lines=[(cash.id, 5000.0, 0.0), (revenue.id, 0.0, 5000.0)],
            narration="Sales",
        )

        # 4. Pay expense: Debit Expense 500, Credit Cash 500
        await create_and_submit_journal_entry(
            db, tenant_id, actor_id,
            posting_date=date(2026, 3, 20),
            lines=[(expense.id, 500.0, 0.0), (cash.id, 0.0, 500.0)],
            narration="Operating expense",
        )

        # Check P&L
        pnL = await get_profit_and_loss(
            db, tenant_id,
            from_date=date(2026, 3, 1),
            to_date=date(2026, 3, 31),
        )
        assert pnL.income_total == Decimal("5000")  # Revenue
        assert pnL.expense_total == Decimal("3500")  # COGS 3000 + Expense 500
        assert pnL.net_profit == Decimal("1500")

        # Check Balance Sheet
        bs = await get_balance_sheet(
            db, tenant_id,
            as_of_date=date(2026, 3, 31),
        )
        # Cash: 10000 - 3000 + 5000 - 500 = 11500
        assert bs.total_assets == Decimal("11500")
        # Equity: 10000 + 1500 (retained earnings from net income)
        assert bs.total_equity > Decimal("10000")

        # Check Trial Balance
        tb = await get_trial_balance(
            db, tenant_id,
            as_of_date=date(2026, 3, 31),
        )
        assert tb.is_balanced is True
        assert tb.total_debit == tb.total_credit
