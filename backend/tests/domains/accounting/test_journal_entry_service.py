"""Tests for journal entry and GL posting services (Epic 26.2)."""

import uuid
from datetime import date, timedelta

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
from domains.accounting.schemas import (
    JournalEntryCreate,
    JournalEntryLineCreate,
)
from domains.accounting.service import (
    GLEntryValidationError,
    JournalEntryNotFoundError,
    JournalEntryValidationError,
    create_journal_entry,
    create_journal_entry as svc_create_journal_entry,
    get_journal_entry,
    get_open_fiscal_years,
    list_journal_entries,
    remove_journal_entry_line,
    reverse_journal_entry,
    seed_starter_chart,
    submit_journal_entry,
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


@pytest_asyncio.fixture
async def setup_accounts_and_fiscal_year(
    db: AsyncSession, tenant_id: uuid.UUID
) -> tuple[Account, Account, FiscalYear]:
    """Create test accounts and fiscal year."""
    # Seed starter chart
    await seed_starter_chart(db, tenant_id)

    # Get accounts
    from sqlalchemy import select

    result = await db.execute(
        select(Account).where(
            Account.tenant_id == tenant_id,
            Account.account_number == "1000",
        )
    )
    cash_account = result.scalar_one()

    result = await db.execute(
        select(Account).where(
            Account.tenant_id == tenant_id,
            Account.account_number == "4000",
        )
    )
    revenue_account = result.scalar_one()

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

    return cash_account, revenue_account, fiscal_year


# ============================================================
# Journal Entry Model Tests
# ============================================================


class TestJournalEntryModel:
    """Tests for JournalEntry ORM model."""

    def test_journal_entry_is_draft(self, db: AsyncSession) -> None:
        """New journal entries are in draft state."""
        entry = JournalEntry(
            tenant_id=uuid.uuid4(),
            voucher_type=VoucherType.JOURNAL_ENTRY.value,
            voucher_number="JE-001",
            posting_date=date.today(),
            status=JournalEntryStatus.DRAFT.value,
            total_debit=100.0,
            total_credit=100.0,
        )
        assert entry.is_draft is True
        assert entry.is_submitted is False
        assert entry.is_cancelled is False

    def test_journal_entry_is_balanced(self, db: AsyncSession) -> None:
        """Balanced journal entries have equal debits and credits."""
        entry = JournalEntry(
            tenant_id=uuid.uuid4(),
            voucher_type=VoucherType.JOURNAL_ENTRY.value,
            voucher_number="JE-001",
            posting_date=date.today(),
            status=JournalEntryStatus.DRAFT.value,
            total_debit=100.0,
            total_credit=100.0,
        )
        assert entry.is_balanced is True

    def test_journal_entry_is_not_balanced(self, db: AsyncSession) -> None:
        """Unbalanced journal entries have unequal debits and credits."""
        entry = JournalEntry(
            tenant_id=uuid.uuid4(),
            voucher_type=VoucherType.JOURNAL_ENTRY.value,
            voucher_number="JE-001",
            posting_date=date.today(),
            status=JournalEntryStatus.DRAFT.value,
            total_debit=100.0,
            total_credit=50.0,
        )
        assert entry.is_balanced is False

    def test_journal_entry_can_submit(self, db: AsyncSession) -> None:
        """Draft and balanced entries with at least 2 lines can be submitted."""
        entry = JournalEntry(
            tenant_id=uuid.uuid4(),
            voucher_type=VoucherType.JOURNAL_ENTRY.value,
            voucher_number="JE-001",
            posting_date=date.today(),
            status=JournalEntryStatus.DRAFT.value,
            total_debit=100.0,
            total_credit=100.0,
        )
        # No lines yet
        assert entry.can_submit is False

    def test_journal_entry_can_cancel(self, db: AsyncSession) -> None:
        """Submitted entries can be cancelled."""
        entry = JournalEntry(
            tenant_id=uuid.uuid4(),
            voucher_type=VoucherType.JOURNAL_ENTRY.value,
            voucher_number="JE-001",
            posting_date=date.today(),
            status=JournalEntryStatus.SUBMITTED.value,
            total_debit=100.0,
            total_credit=100.0,
        )
        assert entry.can_cancel is True


# ============================================================
# Journal Entry Service Tests
# ============================================================


@pytest.mark.asyncio
class TestCreateJournalEntry:
    """Tests for create_journal_entry service function."""

    async def test_create_balanced_journal_entry(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        setup_accounts_and_fiscal_year,
    ) -> None:
        """Can create a balanced journal entry."""
        cash, revenue, _ = setup_accounts_and_fiscal_year

        data = JournalEntryCreate(
            voucher_type=VoucherType.JOURNAL_ENTRY,
            posting_date=date(2026, 3, 15),
            narration="Test entry",
            lines=[
                JournalEntryLineCreate(account_id=cash.id, debit=1000.0, credit=0),
                JournalEntryLineCreate(account_id=revenue.id, debit=0, credit=1000.0),
            ],
        )

        entry = await create_journal_entry(db, tenant_id, data)

        assert entry.id is not None
        assert entry.voucher_number.startswith("JE-")
        assert entry.status == JournalEntryStatus.DRAFT.value
        assert entry.total_debit == 1000.0
        assert entry.total_credit == 1000.0
        assert len(entry.lines) == 2

    async def test_create_unbalanced_journal_entry_rejected(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        setup_accounts_and_fiscal_year,
    ) -> None:
        """Unbalanced journal entries are rejected."""
        cash, revenue, _ = setup_accounts_and_fiscal_year

        data = JournalEntryCreate(
            voucher_type=VoucherType.JOURNAL_ENTRY,
            posting_date=date(2026, 3, 15),
            narration="Unbalanced entry",
            lines=[
                JournalEntryLineCreate(account_id=cash.id, debit=1000.0, credit=0),
                JournalEntryLineCreate(account_id=revenue.id, debit=0, credit=500.0),
            ],
        )

        with pytest.raises(JournalEntryValidationError) as exc_info:
            await create_journal_entry(db, tenant_id, data)
        assert "not balanced" in str(exc_info.value.errors[0])

    async def test_create_entry_with_frozen_account_rejected(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        setup_accounts_and_fiscal_year,
    ) -> None:
        """Entries with frozen accounts are rejected."""
        cash, revenue, _ = setup_accounts_and_fiscal_year

        # Freeze the revenue account
        from sqlalchemy import select
        result = await db.execute(select(Account).where(Account.id == revenue.id))
        revenue_account = result.scalar_one()
        revenue_account.is_frozen = True
        await db.flush()

        data = JournalEntryCreate(
            voucher_type=VoucherType.JOURNAL_ENTRY,
            posting_date=date(2026, 3, 15),
            lines=[
                JournalEntryLineCreate(account_id=cash.id, debit=1000.0, credit=0),
                JournalEntryLineCreate(account_id=revenue.id, debit=0, credit=1000.0),
            ],
        )

        with pytest.raises(JournalEntryValidationError) as exc_info:
            await create_journal_entry(db, tenant_id, data)
        assert any("frozen" in e.lower() for e in exc_info.value.errors)

    async def test_create_entry_with_group_account_rejected(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        setup_accounts_and_fiscal_year,
    ) -> None:
        """Entries posting to group accounts are rejected."""
        _, revenue, _ = setup_accounts_and_fiscal_year

        from sqlalchemy import select

        # Get the root Assets account (a group)
        result = await db.execute(
            select(Account).where(
                Account.tenant_id == tenant_id,
                Account.account_number == "1",
            )
        )
        assets_root = result.scalar_one()

        data = JournalEntryCreate(
            voucher_type=VoucherType.JOURNAL_ENTRY,
            posting_date=date(2026, 3, 15),
            lines=[
                JournalEntryLineCreate(account_id=assets_root.id, debit=1000.0, credit=0),
                JournalEntryLineCreate(account_id=revenue.id, debit=0, credit=1000.0),
            ],
        )

        with pytest.raises(JournalEntryValidationError) as exc_info:
            await create_journal_entry(db, tenant_id, data)
        assert any("group" in e.lower() for e in exc_info.value.errors)

    async def test_create_entry_with_closed_fiscal_year_rejected(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        setup_accounts_and_fiscal_year,
    ) -> None:
        """Entries in closed fiscal years are rejected."""
        cash, revenue, fiscal_year = setup_accounts_and_fiscal_year

        # Close the fiscal year
        fiscal_year.status = FiscalYearStatus.CLOSED.value
        await db.flush()

        data = JournalEntryCreate(
            voucher_type=VoucherType.JOURNAL_ENTRY,
            posting_date=date(2026, 3, 15),
            lines=[
                JournalEntryLineCreate(account_id=cash.id, debit=1000.0, credit=0),
                JournalEntryLineCreate(account_id=revenue.id, debit=0, credit=1000.0),
            ],
        )

        with pytest.raises(JournalEntryValidationError) as exc_info:
            await create_journal_entry(db, tenant_id, data)
        assert any("not open" in e.lower() for e in exc_info.value.errors)


@pytest.mark.asyncio
class TestSubmitJournalEntry:
    """Tests for submit_journal_entry service function."""

    async def test_submit_balanced_journal_entry(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        setup_accounts_and_fiscal_year,
    ) -> None:
        """Can submit a balanced journal entry."""
        cash, revenue, _ = setup_accounts_and_fiscal_year

        # Create entry
        data = JournalEntryCreate(
            voucher_type=VoucherType.JOURNAL_ENTRY,
            posting_date=date(2026, 3, 15),
            narration="Test submit",
            lines=[
                JournalEntryLineCreate(account_id=cash.id, debit=1000.0, credit=0),
                JournalEntryLineCreate(account_id=revenue.id, debit=0, credit=1000.0),
            ],
        )
        entry = await create_journal_entry(db, tenant_id, data)

        # Submit
        submitted, gl_entries = await submit_journal_entry(
            db, tenant_id, entry.id, actor_id
        )

        assert submitted.status == JournalEntryStatus.SUBMITTED.value
        assert submitted.submitted_by == actor_id
        assert submitted.submitted_at is not None
        assert len(gl_entries) == 2

        # Check GL entries
        for gl in gl_entries:
            assert gl.tenant_id == tenant_id
            assert gl.posting_date == date(2026, 3, 15)
            assert gl.fiscal_year == "FY2026"
            assert gl.voucher_type == VoucherType.JOURNAL_ENTRY.value

        # Check debit/credit amounts
        debit_gl = [gl for gl in gl_entries if gl.debit > 0][0]
        credit_gl = [gl for gl in gl_entries if gl.credit > 0][0]
        assert debit_gl.debit == 1000.0
        assert credit_gl.credit == 1000.0

    async def test_submit_unbalanced_journal_entry_rejected(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        setup_accounts_and_fiscal_year,
    ) -> None:
        """Cannot submit an unbalanced journal entry."""
        cash, revenue, _ = setup_accounts_and_fiscal_year

        # Create entry manually with unbalanced amounts
        entry = JournalEntry(
            tenant_id=tenant_id,
            voucher_type=VoucherType.JOURNAL_ENTRY.value,
            voucher_number="JE-TEST",
            posting_date=date(2026, 3, 15),
            status=JournalEntryStatus.DRAFT.value,
            total_debit=1000.0,
            total_credit=500.0,
        )
        db.add(entry)
        await db.flush()

        # Add lines
        line1 = JournalEntryLine(
            journal_entry_id=entry.id,
            account_id=cash.id,
            debit=1000.0,
            credit=0,
        )
        line2 = JournalEntryLine(
            journal_entry_id=entry.id,
            account_id=revenue.id,
            debit=0,
            credit=500.0,
        )
        db.add_all([line1, line2])
        await db.flush()

        with pytest.raises(JournalEntryValidationError) as exc_info:
            await submit_journal_entry(db, tenant_id, entry.id, actor_id)
        assert "not balanced" in str(exc_info.value.errors[0])


@pytest.mark.asyncio
class TestReverseJournalEntry:
    """Tests for reverse_journal_entry service function."""

    async def test_reverse_submitted_journal_entry(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        setup_accounts_and_fiscal_year,
    ) -> None:
        """Can reverse a submitted journal entry."""
        cash, revenue, _ = setup_accounts_and_fiscal_year

        # Create and submit entry
        data = JournalEntryCreate(
            voucher_type=VoucherType.JOURNAL_ENTRY,
            posting_date=date(2026, 3, 15),
            narration="Original entry",
            lines=[
                JournalEntryLineCreate(account_id=cash.id, debit=1000.0, credit=0),
                JournalEntryLineCreate(account_id=revenue.id, debit=0, credit=1000.0),
            ],
        )
        entry = await create_journal_entry(db, tenant_id, data)
        original, gl_entries = await submit_journal_entry(
            db, tenant_id, entry.id, actor_id
        )

        # Reverse
        reversed_orig, reversing, reversing_gl = await reverse_journal_entry(
            db, tenant_id, original.id, actor_id,
            reversal_date=date(2026, 3, 20),
            cancel_reason="Correction"
        )

        assert reversed_orig.status == JournalEntryStatus.CANCELLED.value
        assert reversed_orig.reversed_by_id == reversing.id
        assert reversed_orig.cancel_reason == "Correction"

        assert reversing.status == JournalEntryStatus.SUBMITTED.value
        assert reversing.reverses_id == original.id
        assert len(reversing.lines) == 2

        # Reversing amounts should be swapped
        assert reversing.total_debit == 1000.0  # Was credit
        assert reversing.total_credit == 1000.0  # Was debit

        # GL entries should have swapped amounts
        assert len(reversing_gl) == 2
        reversing_line_ids = {line.id for line in reversing.lines}
        assert all(gl.journal_entry_line_id in reversing_line_ids for gl in reversing_gl)
        assert {(line.debit, line.credit) for line in reversing.lines} == {
            (0, 1000.0),
            (1000.0, 0),
        }

        # Check original GL entries are still there (not deleted)
        from sqlalchemy import select
        result = await db.execute(
            select(GLEntry).where(GLEntry.journal_entry_id == original.id)
        )
        original_gl = result.scalars().all()
        assert len(original_gl) == 2

    async def test_cannot_reverse_draft_entry(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        setup_accounts_and_fiscal_year,
    ) -> None:
        """Cannot reverse a draft journal entry."""
        cash, revenue, _ = setup_accounts_and_fiscal_year

        # Create draft entry
        data = JournalEntryCreate(
            voucher_type=VoucherType.JOURNAL_ENTRY,
            posting_date=date(2026, 3, 15),
            lines=[
                JournalEntryLineCreate(account_id=cash.id, debit=1000.0, credit=0),
                JournalEntryLineCreate(account_id=revenue.id, debit=0, credit=1000.0),
            ],
        )
        entry = await create_journal_entry(db, tenant_id, data)

        with pytest.raises(JournalEntryValidationError) as exc_info:
            await reverse_journal_entry(db, tenant_id, entry.id, actor_id)
        assert "submitted" in str(exc_info.value.errors[0])


@pytest.mark.asyncio
class TestGLEntryIntegrity:
    """Tests for GL entry creation and integrity."""

    async def test_gl_entries_created_on_submit(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        setup_accounts_and_fiscal_year,
    ) -> None:
        """GL entries are created when journal entry is submitted."""
        cash, revenue, _ = setup_accounts_and_fiscal_year

        data = JournalEntryCreate(
            voucher_type=VoucherType.JOURNAL_ENTRY,
            posting_date=date(2026, 3, 15),
            narration="Multi-line entry",
            lines=[
                JournalEntryLineCreate(account_id=cash.id, debit=5000.0, credit=0),
                JournalEntryLineCreate(account_id=revenue.id, debit=0, credit=5000.0),
            ],
        )
        entry = await create_journal_entry(db, tenant_id, data)
        await submit_journal_entry(db, tenant_id, entry.id, actor_id)

        # Verify GL entries
        from sqlalchemy import select
        result = await db.execute(
            select(GLEntry).where(GLEntry.journal_entry_id == entry.id)
        )
        gl_entries = result.scalars().all()

        assert len(gl_entries) == 2
        assert all(gl.tenant_id == tenant_id for gl in gl_entries)
        assert all(gl.posting_date == date(2026, 3, 15) for gl in gl_entries)
        assert all(gl.fiscal_year == "FY2026" for gl in gl_entries)

    async def test_gl_entries_immutable(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        setup_accounts_and_fiscal_year,
    ) -> None:
        """GL entries should be immutable (no update endpoint)."""
        cash, revenue, _ = setup_accounts_and_fiscal_year

        data = JournalEntryCreate(
            voucher_type=VoucherType.JOURNAL_ENTRY,
            posting_date=date(2026, 3, 15),
            lines=[
                JournalEntryLineCreate(account_id=cash.id, debit=1000.0, credit=0),
                JournalEntryLineCreate(account_id=revenue.id, debit=0, credit=1000.0),
            ],
        )
        entry = await create_journal_entry(db, tenant_id, data)
        await submit_journal_entry(db, tenant_id, entry.id, actor_id)

        # GL entries have no update method - they are created once
        from sqlalchemy import select
        result = await db.execute(
            select(GLEntry).where(GLEntry.journal_entry_id == entry.id)
        )
        gl_entries = result.scalars().all()

        # Entries should exist
        assert len(gl_entries) == 2
        for gl in gl_entries:
            # created_at is set, no updated_at
            assert gl.created_at is not None
