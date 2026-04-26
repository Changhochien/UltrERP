"""Tests for accounting service (Epic 26)."""

import uuid
from datetime import date

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
from common.models.journal_entry import JournalEntry, VoucherType
from common.models.journal_entry_line import JournalEntryLine
from domains.accounting.schemas import AccountCreate, FiscalYearCreate
from domains.accounting.service import (
    AccountNotFoundError,
    AccountValidationError,
    FiscalYearNotFoundError,
    FiscalYearValidationError,
    _clear_default_fiscal_year,
    _ROOT_TYPE_TO_REPORT_TYPE,
    close_fiscal_year,
    create_account,
    create_fiscal_year,
    delete_account,
    disable_account,
    freeze_account,
    get_account,
    get_account_tree,
    get_fiscal_year,
    get_fiscal_year_for_date,
    list_accounts,
    list_fiscal_years,
    reopen_fiscal_year,
    seed_starter_chart,
    unfreeze_account,
    update_account,
)
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


# ============================================================
# Account Model Tests
# ============================================================


class TestAccountModel:
    """Tests for Account ORM model."""

    def test_account_is_root(self, db: AsyncSession, tenant_id: uuid.UUID) -> None:
        """Root accounts have no parent."""
        account = Account(
            tenant_id=tenant_id,
            account_number="1",
            account_name="Assets",
            root_type=AccountRootType.ASSET,
            report_type=AccountReportType.BALANCE_SHEET,
            account_type=AccountType.ROOT_ASSET,
            is_group=True,
        )
        assert account.is_root is True
        assert account.parent_id is None

    def test_account_is_ledger(self, db: AsyncSession, tenant_id: uuid.UUID) -> None:
        """Non-group accounts are ledger accounts."""
        account = Account(
            tenant_id=tenant_id,
            account_number="1000",
            account_name="Cash",
            root_type=AccountRootType.ASSET,
            report_type=AccountReportType.BALANCE_SHEET,
            account_type=AccountType.CASH,
            is_group=False,
        )
        assert account.is_ledger is True
        assert account.is_group is False

    def test_account_can_receive_postings(
        self, db: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        """Ledger accounts that are not frozen or disabled can receive postings."""
        account = Account(
            tenant_id=tenant_id,
            account_number="1000",
            account_name="Cash",
            root_type=AccountRootType.ASSET,
            report_type=AccountReportType.BALANCE_SHEET,
            account_type=AccountType.CASH,
            is_group=False,
            is_frozen=False,
            is_disabled=False,
        )
        assert account.can_receive_postings is True

    def test_account_cannot_receive_postings_when_frozen(
        self, db: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        """Frozen accounts cannot receive postings."""
        account = Account(
            tenant_id=tenant_id,
            account_number="1000",
            account_name="Cash",
            root_type=AccountRootType.ASSET,
            report_type=AccountReportType.BALANCE_SHEET,
            account_type=AccountType.CASH,
            is_group=False,
            is_frozen=True,
            is_disabled=False,
        )
        assert account.can_receive_postings is False

    def test_account_cannot_receive_postings_when_disabled(
        self, db: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        """Disabled accounts cannot receive postings."""
        account = Account(
            tenant_id=tenant_id,
            account_number="1000",
            account_name="Cash",
            root_type=AccountRootType.ASSET,
            report_type=AccountReportType.BALANCE_SHEET,
            account_type=AccountType.CASH,
            is_group=False,
            is_frozen=False,
            is_disabled=True,
        )
        assert account.can_receive_postings is False

    def test_account_cannot_receive_postings_when_group(
        self, db: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        """Group accounts cannot receive postings."""
        account = Account(
            tenant_id=tenant_id,
            account_number="1",
            account_name="Assets",
            root_type=AccountRootType.ASSET,
            report_type=AccountReportType.BALANCE_SHEET,
            account_type=AccountType.ROOT_ASSET,
            is_group=True,
            is_frozen=False,
            is_disabled=False,
        )
        assert account.can_receive_postings is False

    def test_validate_parent_child_rejects_self_parent(
        self, db: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        """Account cannot be its own parent."""
        account = Account(
            tenant_id=tenant_id,
            account_number="1",
            account_name="Assets",
            root_type=AccountRootType.ASSET,
            report_type=AccountReportType.BALANCE_SHEET,
            account_type=AccountType.ROOT_ASSET,
            is_group=True,
        )
        errors = account.validate_parent_child(account)
        assert "cannot be its own parent" in errors[0]


# ============================================================
# Account Service Tests
# ============================================================


@pytest.mark.asyncio
class TestCreateAccount:
    """Tests for create_account service function."""

    async def test_create_root_account(self, db: AsyncSession, tenant_id: uuid.UUID) -> None:
        """Can create a root account without parent."""
        data = AccountCreate(
            account_number="1",
            account_name="Assets",
            root_type=AccountRootType.ASSET,
            account_type=AccountType.ROOT_ASSET,
            is_group=True,
        )
        account = await create_account(db, tenant_id, data)
        assert account.id is not None
        assert account.account_number == "1"
        assert account.account_name == "Assets"
        assert account.root_type == AccountRootType.ASSET
        assert account.report_type == AccountReportType.BALANCE_SHEET
        assert account.parent_id is None
        assert account.is_group is True

    async def test_create_ledger_account(
        self, db: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        """Can create a ledger account under a group."""
        # Create parent first
        parent_data = AccountCreate(
            account_number="1",
            account_name="Assets",
            root_type=AccountRootType.ASSET,
            account_type=AccountType.ROOT_ASSET,
            is_group=True,
        )
        parent = await create_account(db, tenant_id, parent_data)

        # Create ledger
        data = AccountCreate(
            account_number="1000",
            account_name="Cash",
            root_type=AccountRootType.ASSET,
            account_type=AccountType.CASH,
            is_group=False,
            parent_id=parent.id,
        )
        account = await create_account(db, tenant_id, data)
        assert account.parent_id == parent.id
        assert account.is_group is False

    async def test_duplicate_account_number_rejected(
        self, db: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        """Duplicate account numbers within tenant are rejected."""
        data = AccountCreate(
            account_number="1000",
            account_name="Cash",
            root_type=AccountRootType.ASSET,
            account_type=AccountType.CASH,
        )
        await create_account(db, tenant_id, data)

        with pytest.raises(AccountValidationError) as exc_info:
            await create_account(
                db, tenant_id, data.model_copy(update={"account_name": "Bank"})
            )
        assert "already exists" in str(exc_info.value.errors)

    async def test_non_group_parent_rejected(
        self, db: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        """Cannot set a ledger account as parent."""
        # Create ledger first
        ledger_data = AccountCreate(
            account_number="1000",
            account_name="Cash",
            root_type=AccountRootType.ASSET,
            account_type=AccountType.CASH,
            is_group=False,
        )
        ledger = await create_account(db, tenant_id, ledger_data)

        # Try to create child under ledger
        with pytest.raises(AccountValidationError) as exc_info:
            await create_account(
                db,
                tenant_id,
                AccountCreate(
                    account_number="1001",
                    account_name="Petty Cash",
                    root_type=AccountRootType.ASSET,
                    account_type=AccountType.CASH,
                    parent_id=ledger.id,
                ),
            )
        assert "must be a group account" in str(exc_info.value.errors)


@pytest.mark.asyncio
class TestFreezeAccount:
    """Tests for freeze_account service function."""

    async def test_freeze_ledger_account(
        self, db: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        """Can freeze a ledger account."""
        data = AccountCreate(
            account_number="1000",
            account_name="Cash",
            root_type=AccountRootType.ASSET,
            account_type=AccountType.CASH,
            is_group=False,
        )
        account = await create_account(db, tenant_id, data)
        frozen = await freeze_account(db, tenant_id, account.id)
        assert frozen.is_frozen is True

    async def test_freeze_group_account_rejected(
        self, db: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        """Cannot freeze a group account."""
        data = AccountCreate(
            account_number="1",
            account_name="Assets",
            root_type=AccountRootType.ASSET,
            account_type=AccountType.ROOT_ASSET,
            is_group=True,
        )
        account = await create_account(db, tenant_id, data)

        with pytest.raises(AccountValidationError) as exc_info:
            await freeze_account(db, tenant_id, account.id)
        assert "Group accounts cannot be frozen" in str(exc_info.value.errors)


@pytest.mark.asyncio
class TestDisableAccount:
    """Tests for disable_account service function."""

    async def test_disable_ledger_account(
        self, db: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        """Can disable a ledger account."""
        data = AccountCreate(
            account_number="1000",
            account_name="Cash",
            root_type=AccountRootType.ASSET,
            account_type=AccountType.CASH,
            is_group=False,
        )
        account = await create_account(db, tenant_id, data)
        disabled = await disable_account(db, tenant_id, account.id)
        assert disabled.is_disabled is True

    async def test_disable_group_account_rejected(
        self, db: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        """Cannot disable a group account."""
        data = AccountCreate(
            account_number="1",
            account_name="Assets",
            root_type=AccountRootType.ASSET,
            account_type=AccountType.ROOT_ASSET,
            is_group=True,
        )
        account = await create_account(db, tenant_id, data)

        with pytest.raises(AccountValidationError) as exc_info:
            await disable_account(db, tenant_id, account.id)
        assert "Group accounts cannot be disabled" in str(exc_info.value.errors)


@pytest.mark.asyncio
class TestDeleteAccount:
    """Tests for delete_account service function."""

    async def test_delete_account_rejected_when_referenced_by_journal_line(
        self, db: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        """Accounts already used in journal lines are rejected with a domain error."""
        account = await create_account(
            db,
            tenant_id,
            AccountCreate(
                account_number="1000",
                account_name="Cash",
                root_type=AccountRootType.ASSET,
                account_type=AccountType.CASH,
                is_group=False,
            ),
        )

        journal_entry = JournalEntry(
            tenant_id=tenant_id,
            voucher_type=VoucherType.JOURNAL_ENTRY,
            voucher_number="JE-0001",
            posting_date=date(2026, 1, 15),
            total_debit=100,
            total_credit=100,
        )
        db.add(journal_entry)
        await db.flush()

        db.add(
            JournalEntryLine(
                journal_entry_id=journal_entry.id,
                account_id=account.id,
                debit=100,
                credit=0,
            )
        )
        await db.flush()

        with pytest.raises(AccountValidationError) as exc_info:
            await delete_account(db, tenant_id, account.id)

        assert "referenced by journal entries" in str(exc_info.value.errors)


# ============================================================
# Fiscal Year Service Tests
# ============================================================


@pytest.mark.asyncio
class TestCreateFiscalYear:
    """Tests for create_fiscal_year service function."""

    async def test_create_fiscal_year(self, db: AsyncSession, tenant_id: uuid.UUID) -> None:
        """Can create a fiscal year."""
        data = FiscalYearCreate(
            label="FY2026",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        fy = await create_fiscal_year(db, tenant_id, data)
        assert fy.id is not None
        assert fy.label == "FY2026"
        assert fy.start_date == date(2026, 1, 1)
        assert fy.end_date == date(2026, 12, 31)
        assert fy.status == FiscalYearStatus.OPEN

    async def test_overlapping_fiscal_year_rejected(
        self, db: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        """Overlapping fiscal years are rejected."""
        data = FiscalYearCreate(
            label="FY2026",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        await create_fiscal_year(db, tenant_id, data)

        with pytest.raises((FiscalYearValidationError, Exception)):
            # Use a valid label format but overlapping dates
            await create_fiscal_year(
                db,
                tenant_id,
                FiscalYearCreate(
                    label="FY2027",  # Valid label format
                    start_date=date(2026, 6, 1),  # Overlaps with FY2026
                    end_date=date(2027, 5, 31),
                ),
            )

    async def test_adjacent_fiscal_years_accepted(
        self, db: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        """Adjacent back-to-back fiscal years are valid."""
        data1 = FiscalYearCreate(
            label="FY2025",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
        )
        await create_fiscal_year(db, tenant_id, data1)

        data2 = FiscalYearCreate(
            label="FY2026",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        fy2 = await create_fiscal_year(db, tenant_id, data2)
        assert fy2.label == "FY2026"

    async def test_invalid_date_order_rejected(
        self, db: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        """Start date must be before end date."""
        # Schema validation catches this via end_date validator
        # The Pydantic model has a validator that ensures end_date > start_date
        with pytest.raises(Exception):  # Pydantic ValidationError
            FiscalYearCreate(
                label="FY2026",
                start_date=date(2026, 12, 31),
                end_date=date(2026, 1, 1),
            )


@pytest.mark.asyncio
class TestCloseFiscalYear:
    """Tests for close_fiscal_year service function."""

    async def test_close_open_fiscal_year(
        self, db: AsyncSession, tenant_id: uuid.UUID, actor_id: uuid.UUID
    ) -> None:
        """Can close an open fiscal year."""
        data = FiscalYearCreate(
            label="FY2025",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
        )
        fy = await create_fiscal_year(db, tenant_id, data)

        closed = await close_fiscal_year(db, tenant_id, fy.id, actor_id)
        assert closed.status == FiscalYearStatus.CLOSED
        assert closed.closed_at is not None
        assert closed.closed_by == actor_id

    async def test_reopen_closed_fiscal_year(
        self, db: AsyncSession, tenant_id: uuid.UUID, actor_id: uuid.UUID
    ) -> None:
        """Can reopen a closed fiscal year."""
        data = FiscalYearCreate(
            label="FY2025",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
        )
        fy = await create_fiscal_year(db, tenant_id, data)
        await close_fiscal_year(db, tenant_id, fy.id, actor_id)

        reopened = await reopen_fiscal_year(db, tenant_id, fy.id)
        assert reopened.status == FiscalYearStatus.OPEN
        assert reopened.closed_at is None


# ============================================================
# Root Type to Report Type Mapping Tests
# ============================================================


class TestRootTypeMapping:
    """Tests for root_type to report_type mapping."""

    def test_asset_maps_to_balance_sheet(self) -> None:
        """Asset root_type maps to Balance Sheet report_type."""
        assert _ROOT_TYPE_TO_REPORT_TYPE[AccountRootType.ASSET] == AccountReportType.BALANCE_SHEET

    def test_liability_maps_to_balance_sheet(self) -> None:
        """Liability root_type maps to Balance Sheet report_type."""
        assert _ROOT_TYPE_TO_REPORT_TYPE[AccountRootType.LIABILITY] == AccountReportType.BALANCE_SHEET

    def test_equity_maps_to_balance_sheet(self) -> None:
        """Equity root_type maps to Balance Sheet report_type."""
        assert _ROOT_TYPE_TO_REPORT_TYPE[AccountRootType.EQUITY] == AccountReportType.BALANCE_SHEET

    def test_income_maps_to_profit_and_loss(self) -> None:
        """Income root_type maps to Profit and Loss report_type."""
        assert _ROOT_TYPE_TO_REPORT_TYPE[AccountRootType.INCOME] == AccountReportType.PROFIT_AND_LOSS

    def test_expense_maps_to_profit_and_loss(self) -> None:
        """Expense root_type maps to Profit and Loss report_type."""
        assert _ROOT_TYPE_TO_REPORT_TYPE[AccountRootType.EXPENSE] == AccountReportType.PROFIT_AND_LOSS


# ============================================================
# Seed Starter Chart Tests
# ============================================================


@pytest.mark.asyncio
class TestSeedStarterChart:
    """Tests for seed_starter_chart service function."""

    async def test_seed_creates_standard_chart(
        self, db: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        """Seed creates the standard chart with root and ledger accounts."""
        result = await seed_starter_chart(db, tenant_id)

        # Should return all created accounts (5 roots + 11 ledgers = 16)
        assert len(result) == 16

        # Filter to get only roots
        roots = [acc for acc in result if acc.parent_id is None]
        assert len(roots) == 5

        # Check root types
        root_types = {r.root_type for r in roots}
        assert root_types == {
            "Asset",
            "Liability",
            "Equity",
            "Income",
            "Expense",
        }

        # All roots should be groups
        for root in roots:
            assert root.is_group is True

    async def test_seed_is_idempotent(
        self, db: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        """Running seed twice returns empty list (already exists)."""
        await seed_starter_chart(db, tenant_id)
        second_run = await seed_starter_chart(db, tenant_id)
        assert second_run == []
