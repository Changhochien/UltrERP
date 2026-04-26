"""
Budget Service for Epic 26 Story 26-6.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, UTC
from decimal import Decimal
from typing import Any

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from common.models.account import Account, AccountRootType, AccountType
from common.models.budget import (
    Budget,
    BudgetAccountAllocation,
    BudgetCheckAction,
    BudgetPeriod,
    BudgetStatus,
)
from common.models.gl_entry import GLEntry


# ============================================================
# Budget CRUD Service
# ============================================================

async def create_budget(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    data: dict[str, Any],
    created_by: str | None = None
) -> Budget:
    """Create a new budget."""
    # Generate budget number
    count = (await session.execute(
        select(func.count(Budget.id)).where(Budget.tenant_id == tenant_id)
    )).scalar() or 0
    
    budget_number = f"BG-{datetime.now(UTC).strftime('%Y%m')}-{count + 1:04d}"
    
    budget = Budget(
        tenant_id=tenant_id,
        budget_number=budget_number,
        budget_name=data["budget_name"],
        description=data.get("description"),
        fiscal_year=data["fiscal_year"],
        scope_type=data.get("scope_type"),
        scope_ref=data.get("scope_ref"),
        status=BudgetStatus.DRAFT,
        expense_action=data.get("expense_action", BudgetCheckAction.WARN),
        total_amount=data.get("total_amount", Decimal("0")),
        currency_code=data.get("currency_code", "TWD"),
        created_by=created_by,
    )
    session.add(budget)
    await session.flush()
    return budget


async def get_budget(
    session: AsyncSession,
    budget_id: uuid.UUID,
    tenant_id: uuid.UUID
) -> Budget | None:
    """Get a budget by ID."""
    result = await session.execute(
        select(Budget).where(
            Budget.id == budget_id,
            Budget.tenant_id == tenant_id
        )
    )
    return result.scalar_one_or_none()


async def list_budgets(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    fiscal_year: str | None = None,
    status: BudgetStatus | None = None,
    is_latest: bool | None = True
) -> list[Budget]:
    """List budgets with filters."""
    query = select(Budget).where(Budget.tenant_id == tenant_id)
    
    if fiscal_year:
        query = query.where(Budget.fiscal_year == fiscal_year)
    if status:
        query = query.where(Budget.status == status)
    if is_latest is not None:
        query = query.where(Budget.is_latest == is_latest)
    
    result = await session.execute(query.order_by(Budget.budget_number.desc()))
    return list(result.scalars().all())


async def submit_budget(
    session: AsyncSession,
    budget_id: uuid.UUID,
    tenant_id: uuid.UUID,
    submitted_by: str | None = None
) -> Budget:
    """Submit a budget for use."""
    budget = await get_budget(session, budget_id, tenant_id)
    if not budget:
        raise ValueError("Budget not found")
    
    if budget.status != BudgetStatus.DRAFT:
        raise ValueError(f"Cannot submit budget in status '{budget.status}'")
    
    budget.status = BudgetStatus.SUBMITTED
    budget.submitted_by = submitted_by
    budget.submitted_at = datetime.now(UTC)
    
    await session.flush()
    return budget


async def revise_budget(
    session: AsyncSession,
    budget_id: uuid.UUID,
    tenant_id: uuid.UUID,
    revised_by: str | None = None
) -> Budget:
    """Create a revised version of a budget."""
    original = await get_budget(session, budget_id, tenant_id)
    if not original:
        raise ValueError("Budget not found")
    
    # Mark original as not latest
    original.is_latest = False
    original.cancelled_by = revised_by
    original.cancelled_at = datetime.now(UTC)
    original.status = BudgetStatus.CANCELLED
    
    # Create revision
    revision = Budget(
        tenant_id=tenant_id,
        budget_number=f"{original.budget_number}-R{original.version + 1}",
        budget_name=original.budget_name,
        description=original.description,
        fiscal_year=original.fiscal_year,
        scope_type=original.scope_type,
        scope_ref=original.scope_ref,
        status=BudgetStatus.DRAFT,
        expense_action=original.expense_action,
        total_amount=original.total_amount,
        currency_code=original.currency_code,
        revision_of_budget_id=original.id,
        is_latest=True,
        version=original.version + 1,
        created_by=revised_by,
    )
    session.add(revision)
    await session.flush()
    
    return revision


# ============================================================
# Budget Period Service
# ============================================================

async def allocate_budget_periods(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    budget_id: uuid.UUID,
    distribution_type: str = "equal",
    period_amounts: dict[str, Decimal] | None = None,
    created_by: str | None = None
) -> list[BudgetPeriod]:
    """Allocate budget to periods."""
    budget = await get_budget(session, budget_id, tenant_id)
    if not budget:
        raise ValueError("Budget not found")
    
    # Get fiscal year date range
    year = int(budget.fiscal_year)
    periods = []
    
    if distribution_type == "equal":
        # Equal distribution across 12 months
        monthly_amount = budget.total_amount / Decimal("12")
        
        for month in range(1, 13):
            period_start = date(year, month, 1)
            if month == 12:
                period_end = date(year, 12, 31)
            else:
                period_end = date(year, month + 1, 1) - timedelta(days=1)
            
            period = BudgetPeriod(
                tenant_id=tenant_id,
                budget_id=budget_id,
                period_start=period_start,
                period_end=period_end,
                period_name=period_start.strftime("%B %Y"),
                allocated_amount=monthly_amount.quantize(Decimal("0.01")),
                distribution_type="equal",
            )
            session.add(period)
            periods.append(period)
    
    elif distribution_type == "manual" and period_amounts:
        # Manual distribution
        for month_str, amount in period_amounts.items():
            month = int(month_str)
            period_start = date(year, month, 1)
            if month == 12:
                period_end = date(year, 12, 31)
            else:
                period_end = date(year, month + 1, 1) - timedelta(days=1)
            
            period = BudgetPeriod(
                tenant_id=tenant_id,
                budget_id=budget_id,
                period_start=period_start,
                period_end=period_end,
                period_name=period_start.strftime("%B %Y"),
                allocated_amount=amount,
                distribution_type="manual",
            )
            session.add(period)
            periods.append(period)
    
    await session.flush()
    return periods


async def get_budget_periods(
    session: AsyncSession,
    budget_id: uuid.UUID,
    tenant_id: uuid.UUID
) -> list[BudgetPeriod]:
    """Get all periods for a budget."""
    result = await session.execute(
        select(BudgetPeriod).where(
            BudgetPeriod.budget_id == budget_id,
            BudgetPeriod.tenant_id == tenant_id
        ).order_by(BudgetPeriod.period_start)
    )
    return list(result.scalars().all())


# ============================================================
# Budget Validation Service
# ============================================================

class BudgetCheckResult:
    """Result of a budget check."""
    def __init__(
        self,
        is_within_budget: bool,
        action: BudgetCheckAction,
        message: str,
        allocated: Decimal = Decimal("0"),
        spent: Decimal = Decimal("0"),
        available: Decimal = Decimal("0"),
        this_transaction: Decimal = Decimal("0"),
    ):
        self.is_within_budget = is_within_budget
        self.action = action
        self.message = message
        self.allocated = allocated
        self.spent = spent
        self.available = available
        self.this_transaction = this_transaction


async def check_budget(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    account_id: uuid.UUID,
    amount: Decimal,
    transaction_date: date,
    scope_type: str | None = None,
    scope_ref: str | None = None
) -> BudgetCheckResult:
    """Check if a transaction is within budget limits."""
    # Get the account
    result = await session.execute(
        select(Account).where(
            Account.id == account_id,
            Account.tenant_id == tenant_id
        )
    )
    account = result.scalar_one_or_none()
    
    if not account:
        return BudgetCheckResult(
            is_within_budget=True,
            action=BudgetCheckAction.IGNORE,
            message="Account not found"
        )
    
    # Only check expense accounts
    if account.root_type != AccountRootType.EXPENSE:
        return BudgetCheckResult(
            is_within_budget=True,
            action=BudgetCheckAction.IGNORE,
            message="Not an expense account"
        )
    
    # Get the fiscal year from the date
    year = str(transaction_date.year)
    
    # Find active budgets for this year and scope
    query = select(Budget).where(
        Budget.tenant_id == tenant_id,
        Budget.fiscal_year == year,
        Budget.status == BudgetStatus.SUBMITTED,
        Budget.is_latest == True
    )
    
    if scope_type and scope_ref:
        query = query.where(
            (Budget.scope_type == scope_type) & (Budget.scope_ref == scope_ref)
        )
    
    result = await session.execute(query)
    budgets = result.scalars().all()
    
    if not budgets:
        return BudgetCheckResult(
            is_within_budget=True,
            action=BudgetCheckAction.IGNORE,
            message="No active budget found"
        )
    
    # Use the first matching budget
    budget = budgets[0]
    
    # Get the period for this transaction
    period_result = await session.execute(
        select(BudgetPeriod).where(
            BudgetPeriod.budget_id == budget.id,
            BudgetPeriod.tenant_id == tenant_id,
            BudgetPeriod.period_start <= transaction_date,
            BudgetPeriod.period_end >= transaction_date
        )
    )
    period = period_result.scalar_one_or_none()
    
    if not period:
        return BudgetCheckResult(
            is_within_budget=True,
            action=BudgetCheckAction.IGNORE,
            message="No budget period found for this date"
        )
    
    # Calculate spent amount from GL entries
    spent_result = await session.execute(
        select(func.coalesce(func.sum(GLEntry.debit), Decimal("0"))).where(
            GLEntry.tenant_id == tenant_id,
            GLEntry.account_id == account_id,
            GLEntry.posting_date >= period.period_start,
            GLEntry.posting_date <= period.period_end,
            GLEntry.reversed_by_id.is_(None)
        )
    )
    spent = spent_result.scalar() or Decimal("0")
    
    # Calculate available
    allocated = period.allocated_amount
    available = allocated - spent
    
    # Check if within budget
    if amount > available:
        return BudgetCheckResult(
            is_within_budget=False,
            action=budget.expense_action,
            message=f"Exceeds budget by {amount - available}",
            allocated=allocated,
            spent=spent,
            available=available,
            this_transaction=amount
        )
    
    return BudgetCheckResult(
        is_within_budget=True,
        action=BudgetCheckAction.IGNORE,
        message="Within budget",
        allocated=allocated,
        spent=spent,
        available=available,
        this_transaction=amount
    )


# ============================================================
# Variance Reporting Service
# ============================================================

class BudgetVarianceRow:
    """A row in a budget variance report."""
    def __init__(
        self,
        account_id: uuid.UUID,
        account_number: str,
        account_name: str,
        allocated: Decimal = Decimal("0"),
        actual: Decimal = Decimal("0"),
        variance: Decimal = Decimal("0"),
        variance_percent: Decimal = Decimal("0"),
    ):
        self.account_id = account_id
        self.account_number = account_number
        self.account_name = account_name
        self.allocated = allocated
        self.actual = actual
        self.variance = variance
        self.variance_percent = variance_percent


async def get_budget_variance_report(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    budget_id: uuid.UUID,
    from_date: date,
    to_date: date
) -> dict[str, Any]:
    """Generate a budget variance report comparing budget vs actuals."""
    budget = await get_budget(session, budget_id, tenant_id)
    if not budget:
        raise ValueError("Budget not found")
    
    # Get budget periods in range
    periods_result = await session.execute(
        select(BudgetPeriod).where(
            BudgetPeriod.budget_id == budget_id,
            BudgetPeriod.tenant_id == tenant_id,
            BudgetPeriod.period_start >= from_date,
            BudgetPeriod.period_end <= to_date
        )
    )
    periods = periods_result.scalars().all()
    
    # Get total allocated for the period
    total_allocated = sum(p.allocated_amount for p in periods)
    
    # Get GL actuals for the budget scope
    query = select(
        GLEntry.account_id,
        func.coalesce(func.sum(GLEntry.debit), Decimal("0")).label("actual")
    ).where(
        GLEntry.tenant_id == tenant_id,
        GLEntry.posting_date >= from_date,
        GLEntry.posting_date <= to_date,
        GLEntry.reversed_by_id.is_(None)
    ).group_by(GLEntry.account_id)
    
    actuals_result = await session.execute(query)
    actuals = {row.account_id: row.actual for row in actuals_result}
    
    # Get account details
    account_ids = list(actuals.keys())
    accounts_result = await session.execute(
        select(Account).where(Account.id.in_(account_ids))
    )
    accounts = {a.id: a for a in accounts_result.scalars().all()}
    
    # Build variance rows
    rows = []
    total_actual = Decimal("0")
    
    for account_id, actual in actuals.items():
        if account_id not in accounts:
            continue
        
        account = accounts[account_id]
        # Find period allocation for this account's period
        # For simplicity, use proportional allocation based on total budget
        if total_allocated > 0 and budget.total_amount > 0:
            allocated = (account.debit_budget or Decimal("0")) if hasattr(account, 'debit_budget') else Decimal("0")
        else:
            allocated = Decimal("0")
        
        variance = allocated - actual
        variance_percent = Decimal("0") if allocated == 0 else (variance / allocated * 100)
        
        rows.append(BudgetVarianceRow(
            account_id=account_id,
            account_number=account.account_number,
            account_name=account.account_name,
            allocated=allocated,
            actual=actual,
            variance=variance,
            variance_percent=variance_percent,
        ))
        total_actual += actual
    
    # Summary
    total_variance = total_allocated - total_actual
    total_variance_percent = Decimal("0") if total_allocated == 0 else (total_variance / total_allocated * 100)
    
    return {
        "budget": {
            "id": str(budget.id),
            "budget_number": budget.budget_number,
            "budget_name": budget.budget_name,
            "fiscal_year": budget.fiscal_year,
            "scope_type": budget.scope_type,
            "scope_ref": budget.scope_ref,
        },
        "period": {
            "from_date": from_date.isoformat(),
            "to_date": to_date.isoformat(),
        },
        "summary": {
            "total_allocated": str(total_allocated),
            "total_actual": str(total_actual),
            "total_variance": str(total_variance),
            "variance_percent": str(total_variance_percent.quantize(Decimal("0.01"))),
        },
        "rows": [
            {
                "account_id": str(r.account_id),
                "account_number": r.account_number,
                "account_name": r.account_name,
                "allocated": str(r.allocated),
                "actual": str(r.actual),
                "variance": str(r.variance),
                "variance_percent": str(r.variance_percent.quantize(Decimal("0.01"))),
            }
            for r in rows
        ],
    }
