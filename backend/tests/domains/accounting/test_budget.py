"""Tests for budget service (Epic 26 Story 26-6)."""
from __future__ import annotations

import uuid
from datetime import date, datetime, UTC
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.common.models.account import Account, AccountRootType, AccountType
from backend.common.models.budget import (
    Budget,
    BudgetCheckAction,
    BudgetPeriod,
    BudgetStatus,
)
from backend.common.models.gl_entry import GLEntry
from backend.domains.accounting.budget_service import (
    allocate_budget_periods,
    check_budget,
    create_budget,
    get_budget_periods,
    get_budget_variance_report,
    list_budgets,
    revise_budget,
    submit_budget,
)


@pytest.fixture
async def tenant_id(db: AsyncSession) -> uuid.UUID:
    """Get or create a test tenant."""
    from common.database import DEFAULT_TENANT_ID
    return DEFAULT_TENANT_ID


@pytest.fixture
async def expense_account(db: AsyncSession, tenant_id: uuid.UUID) -> Account:
    """Create an expense account for testing."""
    account = Account(
        tenant_id=tenant_id,
        account_number="6100",
        account_name="Operating Expenses",
        root_type=AccountRootType.EXPENSE,
        account_type=AccountType.EXPENSE,
        is_group=False,
    )
    db.add(account)
    await db.flush()
    return account


@pytest.fixture
async def budget(db: AsyncSession, tenant_id: uuid.UUID) -> Budget:
    """Create a submitted budget for testing."""
    budget = await create_budget(
        db, tenant_id,
        {
            "budget_name": "Test Budget 2026",
            "fiscal_year": "2026",
            "total_amount": Decimal("120000"),
            "expense_action": BudgetCheckAction.WARN,
        },
        created_by="test"
    )
    await submit_budget(db, budget.id, tenant_id, submitted_by="test")
    return budget


class TestBudgetService:
    """Tests for budget CRUD operations."""

    async def test_create_budget(self, db: AsyncSession, tenant_id: uuid.UUID):
        """Test creating a budget."""
        budget = await create_budget(
            db, tenant_id,
            {
                "budget_name": "Annual Budget 2026",
                "fiscal_year": "2026",
                "total_amount": Decimal("500000"),
                "scope_type": "department",
                "scope_ref": "sales",
            },
            created_by="test"
        )
        
        assert budget.id is not None
        assert budget.budget_number.startswith("BG-")
        assert budget.budget_name == "Annual Budget 2026"
        assert budget.fiscal_year == "2026"
        assert budget.total_amount == Decimal("500000")
        assert budget.status == BudgetStatus.DRAFT
        assert budget.is_latest is True

    async def test_submit_budget(self, db: AsyncSession, tenant_id: uuid.UUID):
        """Test submitting a budget."""
        budget = await create_budget(
            db, tenant_id,
            {"budget_name": "Submit Test", "fiscal_year": "2026", "total_amount": Decimal("100000")},
            created_by="test"
        )
        
        submitted = await submit_budget(db, budget.id, tenant_id, submitted_by="test")
        
        assert submitted.status == BudgetStatus.SUBMITTED
        assert submitted.submitted_by == "test"
        assert submitted.submitted_at is not None

    async def test_cannot_submit_non_draft_budget(self, db: AsyncSession, tenant_id: uuid.UUID):
        """Test that non-draft budgets cannot be submitted."""
        budget = await create_budget(
            db, tenant_id,
            {"budget_name": "Submit Test", "fiscal_year": "2026", "total_amount": Decimal("100000")},
            created_by="test"
        )
        await submit_budget(db, budget.id, tenant_id)
        
        with pytest.raises(ValueError, match="Cannot submit"):
            await submit_budget(db, budget.id, tenant_id)

    async def test_list_budgets(self, db: AsyncSession, tenant_id: uuid.UUID, budget: Budget):
        """Test listing budgets with filters."""
        budgets = await list_budgets(db, tenant_id)
        assert len(budgets) >= 1
        
        submitted = await list_budgets(db, tenant_id, status=BudgetStatus.SUBMITTED)
        assert all(b.status == BudgetStatus.SUBMITTED for b in submitted)


class TestBudgetRevision:
    """Tests for budget revision."""

    async def test_revise_budget(self, db: AsyncSession, tenant_id: uuid.UUID, budget: Budget):
        """Test revising a budget."""
        revision = await revise_budget(db, budget.id, tenant_id, revised_by="test")
        
        # Check original is cancelled
        await db.refresh(budget)
        assert budget.status == BudgetStatus.CANCELLED
        assert budget.is_latest is False
        
        # Check revision is new
        assert revision.budget_name == budget.budget_name
        assert revision.fiscal_year == budget.fiscal_year
        assert revision.version == budget.version + 1
        assert revision.revision_of_budget_id == budget.id
        assert revision.status == BudgetStatus.DRAFT
        assert revision.is_latest is True


class TestBudgetPeriodAllocation:
    """Tests for budget period allocation."""

    async def test_allocate_equal_distribution(
        self, db: AsyncSession, tenant_id: uuid.UUID, budget: Budget
    ):
        """Test equal distribution across 12 months."""
        periods = await allocate_budget_periods(
            db, tenant_id, budget.id, distribution_type="equal", created_by="test"
        )
        
        assert len(periods) == 12
        
        # Check each month
        total = sum(p.allocated_amount for p in periods)
        assert total == budget.total_amount
        
        # Check month names
        assert periods[0].period_name == "January 2026"
        assert periods[11].period_name == "December 2026"

    async def test_get_budget_periods(
        self, db: AsyncSession, tenant_id: uuid.UUID, budget: Budget
    ):
        """Test getting budget periods."""
        await allocate_budget_periods(
            db, tenant_id, budget.id, distribution_type="equal", created_by="test"
        )
        
        periods = await get_budget_periods(db, budget.id, tenant_id)
        
        assert len(periods) == 12


class TestBudgetValidation:
    """Tests for budget validation/checking."""

    async def test_check_budget_within_limit(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        budget: Budget,
        expense_account: Account
    ):
        """Test budget check when within limit."""
        # Allocate budget periods first
        await allocate_budget_periods(
            db, tenant_id, budget.id, distribution_type="equal", created_by="test"
        )
        
        # Check with small amount
        result = await check_budget(
            db, tenant_id, expense_account.id,
            Decimal("1000"), date(2026, 3, 15)
        )
        
        # Should be within budget (we haven't spent anything yet)
        assert result.allocated > Decimal("0")
        assert result.is_within_budget is True

    async def test_check_budget_exceeds_limit(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        budget: Budget,
        expense_account: Account
    ):
        """Test budget check when exceeding limit."""
        # Allocate budget periods first
        await allocate_budget_periods(
            db, tenant_id, budget.id, distribution_type="equal", created_by="test"
        )
        
        # Create existing GL entry that uses up the budget
        gl_entry = GLEntry(
            tenant_id=tenant_id,
            account_id=expense_account.id,
            posting_date=date(2026, 3, 1),
            debit=Decimal("100000"),  # Most of the monthly budget
            credit=Decimal("0"),
            fiscal_year_id=budget.id,
            voucher_type="Test",
            voucher_id=uuid.uuid4(),
            narration="Test entry",
        )
        db.add(gl_entry)
        await db.flush()
        
        # Check with amount that exceeds remaining budget
        result = await check_budget(
            db, tenant_id, expense_account.id,
            Decimal("20000"), date(2026, 3, 15)  # Monthly budget is 10000
        )
        
        assert result.is_within_budget is False
        assert result.action == BudgetCheckAction.WARN

    async def test_check_budget_non_expense_account(
        self, db: AsyncSession, tenant_id: uuid.UUID, budget: Budget
    ):
        """Test that non-expense accounts skip budget check."""
        # Create non-expense account
        revenue = Account(
            tenant_id=tenant_id,
            account_number="4100",
            account_name="Sales Revenue",
            root_type=AccountRootType.INCOME,
            account_type=AccountType.INCOME,
            is_group=False,
        )
        db.add(revenue)
        await db.flush()
        
        result = await check_budget(
            db, tenant_id, revenue.id,
            Decimal("1000"), date(2026, 3, 15)
        )
        
        assert result.is_within_budget is True
        assert result.action == BudgetCheckAction.IGNORE
        assert "Not an expense" in result.message


class TestBudgetVarianceReport:
    """Tests for budget variance reporting."""

    async def test_get_budget_variance_report(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        budget: Budget,
        expense_account: Account
    ):
        """Test generating a budget variance report."""
        # Allocate and create GL entries
        await allocate_budget_periods(
            db, tenant_id, budget.id, distribution_type="equal", created_by="test"
        )
        
        gl_entry = GLEntry(
            tenant_id=tenant_id,
            account_id=expense_account.id,
            posting_date=date(2026, 3, 15),
            debit=Decimal("5000"),
            credit=Decimal("0"),
            fiscal_year_id=budget.id,
            voucher_type="Test",
            voucher_id=uuid.uuid4(),
            narration="Test expense",
        )
        db.add(gl_entry)
        await db.flush()
        
        # Get variance report
        report = await get_budget_variance_report(
            db, tenant_id, budget.id,
            date(2026, 3, 1), date(2026, 3, 31)
        )
        
        assert report["budget"]["budget_number"] == budget.budget_number
        assert "summary" in report
        assert "rows" in report
