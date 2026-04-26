"""Service layer for accounting domain (Epic 26).

Implements business logic for account tree operations and fiscal year management.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, date, datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from common.models.account import (
    Account,
    AccountRootType,
    _ROOT_TYPE_TO_REPORT_TYPE,
)
from common.models.fiscal_year import FiscalYear, FiscalYearStatus
from common.models.gl_entry import GLEntry, GLEntryType
from common.models.journal_entry import JournalEntry, JournalEntryStatus, VoucherType
from common.models.journal_entry_line import JournalEntryLine

from .schemas import (
    AccountCreate,
    AccountListResponse,
    AccountResponse,
    AccountTreeNode,
    AccountTreeResponse,
    AccountUpdate,
    FiscalYearCreate,
    FiscalYearListResponse,
    FiscalYearResponse,
    FiscalYearUpdate,
    GLEntryListResponse,
    GLEntryWithAccount,
    JournalEntryCreate,
    JournalEntryDetailResponse,
    JournalEntryLineCreate,
    JournalEntryListResponse,
    JournalEntryResponse,
    JournalEntryReverseResponse,
    JournalEntrySubmitResponse,
    JournalEntryUpdate,
    LedgerAccountSummary,
    LedgerSummaryResponse,
    StarterAccountDefinition,
    StarterChartProfile,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Balance tolerance for floating-point comparison
BALANCE_TOLERANCE = 0.0001


def _enum_value(enum: Enum | str) -> str:
    """Convert enum to string value, handling both Enum and already-string values."""
    return enum.value if isinstance(enum, Enum) else enum

# ============================================================
# Custom Exceptions
# ============================================================


class AccountNotFoundError(Exception):
    """Raised when an account is not found."""

    def __init__(self, account_id: uuid.UUID):
        self.account_id = account_id
        super().__init__(f"Account not found: {account_id}")


class FiscalYearNotFoundError(Exception):
    """Raised when a fiscal year is not found."""

    def __init__(self, fiscal_year_id: uuid.UUID):
        self.fiscal_year_id = fiscal_year_id
        super().__init__(f"Fiscal year not found: {fiscal_year_id}")


class AccountValidationError(Exception):
    """Raised when account validation fails."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


class FiscalYearValidationError(Exception):
    """Raised when fiscal year validation fails."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


# ============================================================
# Account Service Functions
# ============================================================


async def create_account(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    data: AccountCreate,
) -> Account:
    """Create a new account.

    Args:
        db: Database session
        tenant_id: Tenant identifier
        data: Account creation data

    Returns:
        Created Account instance

    Raises:
        AccountValidationError: If validation fails
    """
    # Validate parent if specified
    parent = None
    if data.parent_id:
        result = await db.execute(
            select(Account).where(
                and_(
                    Account.tenant_id == tenant_id,
                    Account.id == data.parent_id,
                )
            )
        )
        parent = result.scalar_one_or_none()
        if not parent:
            raise AccountValidationError([f"Parent account not found: {data.parent_id}"])

        # Parent must be a group account
        if not parent.is_group:
            raise AccountValidationError(["Parent account must be a group account"])

        # Root type must match parent
        parent_root_type = _enum_value(parent.root_type)
        if parent_root_type != _enum_value(data.root_type):
            raise AccountValidationError([
                f"Account root_type ({_enum_value(data.root_type)}) must match parent root_type ({parent_root_type})"
            ])

    # Check for duplicate account number
    result = await db.execute(
        select(Account).where(
            and_(
                Account.tenant_id == tenant_id,
                Account.account_number == data.account_number,
            )
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise AccountValidationError([
            f"Account number already exists: {data.account_number}"
        ])

    # Create account (convert enums to string values)
    account = Account(
        tenant_id=tenant_id,
        parent_id=data.parent_id,
        account_number=data.account_number,
        account_name=data.account_name,
        root_type=_enum_value(data.root_type),
        report_type=_enum_value(_ROOT_TYPE_TO_REPORT_TYPE[data.root_type]),
        account_type=_enum_value(data.account_type),
        is_group=data.is_group,
        is_frozen=data.is_frozen,
        is_disabled=data.is_disabled,
        sort_order=data.sort_order,
        currency_code=data.currency_code,
        parent_number=parent.account_number if parent else None,
    )

    db.add(account)
    await db.flush()
    await db.refresh(account)

    logger.info(
        f"Created account {account.account_number} ({account.account_name}) "
        f"for tenant {tenant_id}"
    )

    return account


async def get_account(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    account_id: uuid.UUID,
) -> Account:
    """Get a single account by ID.

    Args:
        db: Database session
        tenant_id: Tenant identifier
        account_id: Account identifier

    Returns:
        Account instance

    Raises:
        AccountNotFoundError: If account not found
    """
    result = await db.execute(
        select(Account).where(
            and_(
                Account.tenant_id == tenant_id,
                Account.id == account_id,
            )
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise AccountNotFoundError(account_id)
    return account


async def list_accounts(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    page: int = 1,
    page_size: int = 50,
    root_type: AccountRootType | None = None,
    include_disabled: bool = False,
) -> AccountListResponse:
    """List accounts with pagination.

    Args:
        db: Database session
        tenant_id: Tenant identifier
        page: Page number (1-indexed)
        page_size: Items per page
        root_type: Optional filter by root type
        include_disabled: Whether to include disabled accounts

    Returns:
        Paginated list of accounts
    """
    # Build base query
    conditions = [Account.tenant_id == tenant_id]

    if root_type:
        conditions.append(Account.root_type == root_type)

    if not include_disabled:
        conditions.append(Account.is_disabled == False)

    # Count total
    count_query = select(Account).where(and_(*conditions))
    count_result = await db.execute(count_query)
    total = len(count_result.scalars().all())

    # Get page
    offset = (page - 1) * page_size
    query = (
        select(Account)
        .where(and_(*conditions))
        .order_by(Account.root_type, Account.sort_order, Account.account_number)
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(query)
    accounts = result.scalars().all()

    return AccountListResponse(
        items=[AccountResponse.model_validate(a) for a in accounts],
        total=total,
        page=page,
        page_size=page_size,
    )


async def get_account_tree(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    include_disabled: bool = False,
) -> AccountTreeResponse:
    """Get full account tree for a tenant.

    Args:
        db: Database session
        tenant_id: Tenant identifier
        include_disabled: Whether to include disabled accounts

    Returns:
        Tree structure with root accounts and their children
    """
    # Build base conditions
    conditions = [Account.tenant_id == tenant_id]
    if not include_disabled:
        conditions.append(Account.is_disabled == False)

    # Get all accounts
    query = (
        select(Account)
        .where(and_(*conditions))
        .order_by(Account.root_type, Account.sort_order, Account.account_number)
    )
    result = await db.execute(query)
    all_accounts = result.scalars().all()

    # Build tree structure
    account_map: dict[uuid.UUID, AccountTreeNode] = {}
    roots: list[AccountTreeNode] = []

    # First pass: create nodes
    for acc in all_accounts:
        node = AccountTreeNode(
            id=acc.id,
            tenant_id=acc.tenant_id,
            parent_id=acc.parent_id,
            parent_number=acc.parent_number,
            account_number=acc.account_number,
            account_name=acc.account_name,
            root_type=acc.root_type,
            report_type=acc.report_type,
            account_type=acc.account_type,
            is_group=acc.is_group,
            is_frozen=acc.is_frozen,
            is_disabled=acc.is_disabled,
            sort_order=acc.sort_order,
            currency_code=acc.currency_code,
            created_at=acc.created_at,
            updated_at=acc.updated_at,
            children=[],
        )
        account_map[acc.id] = node

    # Second pass: build parent-child relationships
    for acc in all_accounts:
        node = account_map[acc.id]
        if acc.parent_id and acc.parent_id in account_map:
            account_map[acc.parent_id].children.append(node)
        else:
            roots.append(node)

    return AccountTreeResponse(
        roots=roots,
        total_accounts=len(all_accounts),
    )


async def update_account(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    account_id: uuid.UUID,
    data: AccountUpdate,
) -> Account:
    """Update an existing account.

    Args:
        db: Database session
        tenant_id: Tenant identifier
        account_id: Account identifier
        data: Update data

    Returns:
        Updated Account instance

    Raises:
        AccountNotFoundError: If account not found
        AccountValidationError: If validation fails
    """
    account = await get_account(db, tenant_id, account_id)

    # Check if account can be modified (not frozen or disabled)
    if account.is_frozen:
        raise AccountValidationError(["Cannot update frozen account"])
    if account.is_disabled:
        raise AccountValidationError(["Cannot update disabled account"])

    # Check if account has children (can't change is_group if has children)
    if data.is_group is not None and data.is_group != account.is_group:
        children_result = await db.execute(
            select(Account).where(Account.parent_id == account_id)
        )
        if children_result.scalar_one_or_none():
            raise AccountValidationError([
                "Cannot change is_group when account has children"
            ])

    # Check for duplicate account number
    if data.account_number and data.account_number != account.account_number:
        result = await db.execute(
            select(Account).where(
                and_(
                    Account.tenant_id == tenant_id,
                    Account.account_number == data.account_number,
                    Account.id != account_id,
                )
            )
        )
        if result.scalar_one_or_none():
            raise AccountValidationError([
                f"Account number already exists: {data.account_number}"
            ])

    # Validate parent change
    if data.parent_id is not None and data.parent_id != account.parent_id:
        parent_result = await db.execute(
            select(Account).where(
                and_(
                    Account.tenant_id == tenant_id,
                    Account.id == data.parent_id,
                )
            )
        )
        parent = parent_result.scalar_one_or_none()
        if not parent:
            raise AccountValidationError([f"Parent account not found: {data.parent_id}"])
        if not parent.is_group:
            raise AccountValidationError(["Parent account must be a group account"])
        if _enum_value(parent.root_type) != _enum_value(account.root_type):
            raise AccountValidationError([
                f"Account root_type ({_enum_value(account.root_type)}) must match "
                f"parent root_type ({_enum_value(parent.root_type)})"
            ])

    # Apply updates
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "account_type" and value:
            # account_type change doesn't affect report_type
            setattr(account, field, value)
        else:
            setattr(account, field, value)

    account.updated_at = datetime.now(tz=UTC)
    await db.flush()
    await db.refresh(account)

    logger.info(f"Updated account {account.account_number} ({account.account_name})")

    return account


async def freeze_account(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    account_id: uuid.UUID,
) -> Account:
    """Freeze an account (rejects postings but retains data).

    Args:
        db: Database session
        tenant_id: Tenant identifier
        account_id: Account identifier

    Returns:
        Updated Account instance

    Raises:
        AccountNotFoundError: If account not found
        AccountValidationError: If account cannot be frozen
    """
    account = await get_account(db, tenant_id, account_id)

    if account.is_frozen:
        raise AccountValidationError(["Account is already frozen"])
    if account.is_group:
        raise AccountValidationError(["Group accounts cannot be frozen"])

    account.is_frozen = True
    account.updated_at = datetime.now(tz=UTC)
    await db.flush()
    await db.refresh(account)

    logger.info(f"Froze account {account.account_number}")

    return account


async def unfreeze_account(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    account_id: uuid.UUID,
) -> Account:
    """Unfreeze an account (allows postings).

    Args:
        db: Database session
        tenant_id: Tenant identifier
        account_id: Account identifier

    Returns:
        Updated Account instance

    Raises:
        AccountNotFoundError: If account not found
    """
    account = await get_account(db, tenant_id, account_id)

    if not account.is_frozen:
        raise AccountValidationError(["Account is not frozen"])

    account.is_frozen = False
    account.updated_at = datetime.now(tz=UTC)
    await db.flush()
    await db.refresh(account)

    logger.info(f"Unfroze account {account.account_number}")

    return account


async def disable_account(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    account_id: uuid.UUID,
) -> Account:
    """Disable an account (hides from selection, rejects all operations).

    Args:
        db: Database session
        tenant_id: Tenant identifier
        account_id: Account identifier

    Returns:
        Updated Account instance

    Raises:
        AccountNotFoundError: If account not found
        AccountValidationError: If account cannot be disabled
    """
    account = await get_account(db, tenant_id, account_id)

    if account.is_disabled:
        raise AccountValidationError(["Account is already disabled"])
    if account.is_group:
        raise AccountValidationError(["Group accounts cannot be disabled directly"])

    account.is_disabled = True
    account.updated_at = datetime.now(tz=UTC)
    await db.flush()
    await db.refresh(account)

    logger.info(f"Disabled account {account.account_number}")

    return account


async def delete_account(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    account_id: uuid.UUID,
) -> None:
    """Delete an account (only if it has no children).

    Args:
        db: Database session
        tenant_id: Tenant identifier
        account_id: Account identifier

    Raises:
        AccountNotFoundError: If account not found
        AccountValidationError: If account has children or is in use
    """
    account = await get_account(db, tenant_id, account_id)

    # Check for children
    children_result = await db.execute(
        select(Account).where(Account.parent_id == account_id)
    )
    if children_result.scalar_one_or_none():
        raise AccountValidationError([
            "Cannot delete account with children. Freeze and disable instead."
        ])

    await db.delete(account)
    await db.flush()

    logger.info(f"Deleted account {account.account_number}")


# ============================================================
# Fiscal Year Service Functions
# ============================================================


async def create_fiscal_year(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    data: FiscalYearCreate,
) -> FiscalYear:
    """Create a new fiscal year.

    Args:
        db: Database session
        tenant_id: Tenant identifier
        data: Fiscal year creation data

    Returns:
        Created FiscalYear instance

    Raises:
        FiscalYearValidationError: If validation fails
    """
    # Manual validation - date range is validated below

    # Validate date range
    if data.start_date >= data.end_date:
        raise FiscalYearValidationError(["Start date must be before end date"])

    # Check for overlapping fiscal years
    result = await db.execute(
        select(FiscalYear).where(
            and_(
                FiscalYear.tenant_id == tenant_id,
                FiscalYear.start_date < data.end_date,
                FiscalYear.end_date > data.start_date,
            )
        )
    )
    overlapping = result.scalars().all()
    if overlapping:
        raise FiscalYearValidationError([
            f"Fiscal year overlaps with existing: {overlapping[0].label}"
        ])

    # Check for duplicate label
    result = await db.execute(
        select(FiscalYear).where(
            and_(
                FiscalYear.tenant_id == tenant_id,
                FiscalYear.label == data.label,
            )
        )
    )
    if result.scalar_one_or_none():
        raise FiscalYearValidationError([f"Fiscal year label already exists: {data.label}"])

    # Create fiscal year (status stored as string)
    fiscal_year = FiscalYear(
        tenant_id=tenant_id,
        label=data.label,
        start_date=data.start_date,
        end_date=data.end_date,
        status=_enum_value(FiscalYearStatus.OPEN),
        is_default=data.is_default,
    )

    # If this is the default fiscal year, unset other defaults
    if data.is_default:
        await _clear_default_fiscal_year(db, tenant_id)
        fiscal_year.is_default = True

    db.add(fiscal_year)
    await db.flush()
    await db.refresh(fiscal_year)

    logger.info(
        f"Created fiscal year {fiscal_year.label} "
        f"({fiscal_year.start_date} to {fiscal_year.end_date}) for tenant {tenant_id}"
    )

    return fiscal_year


async def _clear_default_fiscal_year(
    db: AsyncSession,
    tenant_id: uuid.UUID,
) -> None:
    """Clear default flag from all fiscal years for a tenant."""
    result = await db.execute(
        select(FiscalYear).where(
            and_(
                FiscalYear.tenant_id == tenant_id,
                FiscalYear.is_default == True,
            )
        )
    )
    for fy in result.scalars().all():
        fy.is_default = False
    await db.flush()


async def get_fiscal_year(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    fiscal_year_id: uuid.UUID,
) -> FiscalYear:
    """Get a single fiscal year by ID.

    Args:
        db: Database session
        tenant_id: Tenant identifier
        fiscal_year_id: Fiscal year identifier

    Returns:
        FiscalYear instance

    Raises:
        FiscalYearNotFoundError: If fiscal year not found
    """
    result = await db.execute(
        select(FiscalYear).where(
            and_(
                FiscalYear.tenant_id == tenant_id,
                FiscalYear.id == fiscal_year_id,
            )
        )
    )
    fiscal_year = result.scalar_one_or_none()
    if not fiscal_year:
        raise FiscalYearNotFoundError(fiscal_year_id)
    return fiscal_year


async def list_fiscal_years(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    page: int = 1,
    page_size: int = 50,
    status: FiscalYearStatus | None = None,
) -> FiscalYearListResponse:
    """List fiscal years with pagination.

    Args:
        db: Database session
        tenant_id: Tenant identifier
        page: Page number (1-indexed)
        page_size: Items per page
        status: Optional filter by status

    Returns:
        Paginated list of fiscal years
    """
    conditions = [FiscalYear.tenant_id == tenant_id]
    if status:
        conditions.append(FiscalYear.status == status)

    # Count total
    count_result = await db.execute(select(FiscalYear).where(and_(*conditions)))
    total = len(count_result.scalars().all())

    # Get page
    offset = (page - 1) * page_size
    query = (
        select(FiscalYear)
        .where(and_(*conditions))
        .order_by(FiscalYear.start_date.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(query)
    fiscal_years = result.scalars().all()

    return FiscalYearListResponse(
        items=[FiscalYearResponse.model_validate(fy) for fy in fiscal_years],
        total=total,
        page=page,
        page_size=page_size,
    )


async def update_fiscal_year(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    fiscal_year_id: uuid.UUID,
    data: FiscalYearUpdate,
    actor_id: uuid.UUID | None = None,
) -> FiscalYear:
    """Update an existing fiscal year.

    Args:
        db: Database session
        tenant_id: Tenant identifier
        fiscal_year_id: Fiscal year identifier
        data: Update data
        actor_id: User performing the update

    Returns:
        Updated FiscalYear instance

    Raises:
        FiscalYearNotFoundError: If fiscal year not found
        FiscalYearValidationError: If validation fails
    """
    fiscal_year = await get_fiscal_year(db, tenant_id, fiscal_year_id)

    # Apply updates
    update_data = data.model_dump(exclude_unset=True)

    # Handle status transitions
    if "status" in update_data:
        new_status = update_data["status"]
        if new_status == FiscalYearStatus.CLOSED and fiscal_year.is_open:
            fiscal_year.closed_at = datetime.now(tz=UTC)
            fiscal_year.closed_by = actor_id

    # Handle default flag change
    if update_data.get("is_default") and not fiscal_year.is_default:
        await _clear_default_fiscal_year(db, tenant_id)

    for field, value in update_data.items():
        setattr(fiscal_year, field, value)

    fiscal_year.updated_at = datetime.now(tz=UTC)
    await db.flush()
    await db.refresh(fiscal_year)

    logger.info(f"Updated fiscal year {fiscal_year.label}")

    return fiscal_year


async def close_fiscal_year(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    fiscal_year_id: uuid.UUID,
    actor_id: uuid.UUID,
    closure_notes: str | None = None,
) -> FiscalYear:
    """Close a fiscal year for posting.

    Args:
        db: Database session
        tenant_id: Tenant identifier
        fiscal_year_id: Fiscal year identifier
        actor_id: User closing the fiscal year
        closure_notes: Optional closure notes

    Returns:
        Closed FiscalYear instance

    Raises:
        FiscalYearNotFoundError: If fiscal year not found
        FiscalYearValidationError: If fiscal year cannot be closed
    """
    fiscal_year = await get_fiscal_year(db, tenant_id, fiscal_year_id)

    if not fiscal_year.is_open:
        raise FiscalYearValidationError([f"Fiscal year is not open: {fiscal_year.status.value}"])

    fiscal_year.status = FiscalYearStatus.CLOSED
    fiscal_year.closed_at = datetime.now(tz=UTC)
    fiscal_year.closed_by = actor_id
    fiscal_year.closure_notes = closure_notes
    fiscal_year.updated_at = datetime.now(tz=UTC)

    await db.flush()
    await db.refresh(fiscal_year)

    logger.info(f"Closed fiscal year {fiscal_year.label} by user {actor_id}")

    return fiscal_year


async def reopen_fiscal_year(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    fiscal_year_id: uuid.UUID,
) -> FiscalYear:
    """Reopen a closed fiscal year (admin operation).

    Args:
        db: Database session
        tenant_id: Tenant identifier
        fiscal_year_id: Fiscal year identifier

    Returns:
        Reopened FiscalYear instance

    Raises:
        FiscalYearNotFoundError: If fiscal year not found
        FiscalYearValidationError: If fiscal year cannot be reopened
    """
    fiscal_year = await get_fiscal_year(db, tenant_id, fiscal_year_id)

    if not fiscal_year.is_closed:
        raise FiscalYearValidationError([f"Fiscal year is not closed: {fiscal_year.status.value}"])

    fiscal_year.status = FiscalYearStatus.OPEN
    fiscal_year.closed_at = None
    fiscal_year.closed_by = None
    fiscal_year.closure_notes = None
    fiscal_year.updated_at = datetime.now(tz=UTC)

    await db.flush()
    await db.refresh(fiscal_year)

    logger.info(f"Reopened fiscal year {fiscal_year.label}")

    return fiscal_year


async def get_fiscal_year_for_date(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    check_date: date,
) -> FiscalYear | None:
    """Get the fiscal year that contains a given date.

    Args:
        db: Database session
        tenant_id: Tenant identifier
        check_date: Date to check

    Returns:
        FiscalYear containing the date, or None if not found
    """
    result = await db.execute(
        select(FiscalYear).where(
            and_(
                FiscalYear.tenant_id == tenant_id,
                FiscalYear.start_date <= check_date,
                FiscalYear.end_date >= check_date,
            )
        )
    )
    return result.scalar_one_or_none()


async def get_open_fiscal_years(
    db: AsyncSession,
    tenant_id: uuid.UUID,
) -> list[FiscalYear]:
    """Get all open fiscal years for a tenant.

    Args:
        db: Database session
        tenant_id: Tenant identifier

    Returns:
        List of open fiscal years
    """
    result = await db.execute(
        select(FiscalYear).where(
            and_(
                FiscalYear.tenant_id == tenant_id,
                FiscalYear.status == FiscalYearStatus.OPEN,
            )
        ).order_by(FiscalYear.start_date)
    )
    return list(result.scalars().all())


# ============================================================
# Starter Chart Profiles
# ============================================================


# Standard minimal starter chart
STANDARD_STARTER_CHART = StarterChartProfile(
    name="Standard Minimal",
    description="Minimal chart of accounts for basic accounting",
    accounts=[
        # Asset roots
        StarterAccountDefinition(
            account_number="1", account_name="Assets", root_type=AccountRootType.ASSET,
            account_type=AccountType.ROOT_ASSET, parent_number=None, is_group=True
        ),
        StarterAccountDefinition(
            account_number="1000", account_name="Cash", root_type=AccountRootType.ASSET,
            account_type=AccountType.CASH, parent_number="1", is_group=False
        ),
        StarterAccountDefinition(
            account_number="1100", account_name="Bank", root_type=AccountRootType.ASSET,
            account_type=AccountType.BANK, parent_number="1", is_group=False
        ),
        StarterAccountDefinition(
            account_number="1200", account_name="Accounts Receivable", root_type=AccountRootType.ASSET,
            account_type=AccountType.RECEIVABLE, parent_number="1", is_group=False
        ),
        StarterAccountDefinition(
            account_number="1500", account_name="Inventory", root_type=AccountRootType.ASSET,
            account_type=AccountType.INVENTORY, parent_number="1", is_group=False
        ),
        # Liability roots
        StarterAccountDefinition(
            account_number="2", account_name="Liabilities", root_type=AccountRootType.LIABILITY,
            account_type=AccountType.ROOT_LIABILITY, parent_number=None, is_group=True
        ),
        StarterAccountDefinition(
            account_number="2000", account_name="Accounts Payable", root_type=AccountRootType.LIABILITY,
            account_type=AccountType.PAYABLE, parent_number="2", is_group=False
        ),
        StarterAccountDefinition(
            account_number="2100", account_name="Tax Payable", root_type=AccountRootType.LIABILITY,
            account_type=AccountType.TAX_LIABILITY, parent_number="2", is_group=False
        ),
        # Equity roots
        StarterAccountDefinition(
            account_number="3", account_name="Equity", root_type=AccountRootType.EQUITY,
            account_type=AccountType.ROOT_EQUITY, parent_number=None, is_group=True
        ),
        StarterAccountDefinition(
            account_number="3000", account_name="Retained Earnings", root_type=AccountRootType.EQUITY,
            account_type=AccountType.RETAINED_EARNINGS, parent_number="3", is_group=False
        ),
        # Income roots
        StarterAccountDefinition(
            account_number="4", account_name="Income", root_type=AccountRootType.INCOME,
            account_type=AccountType.ROOT_INCOME, parent_number=None, is_group=True
        ),
        StarterAccountDefinition(
            account_number="4000", account_name="Sales Revenue", root_type=AccountRootType.INCOME,
            account_type=AccountType.SALES, parent_number="4", is_group=False
        ),
        StarterAccountDefinition(
            account_number="4100", account_name="Service Revenue", root_type=AccountRootType.INCOME,
            account_type=AccountType.SERVICE_REVENUE, parent_number="4", is_group=False
        ),
        # Expense roots
        StarterAccountDefinition(
            account_number="5", account_name="Expenses", root_type=AccountRootType.EXPENSE,
            account_type=AccountType.ROOT_EXPENSE, parent_number=None, is_group=True
        ),
        StarterAccountDefinition(
            account_number="5000", account_name="Cost of Goods Sold", root_type=AccountRootType.EXPENSE,
            account_type=AccountType.COST_OF_GOODS_SOLD, parent_number="5", is_group=False
        ),
        StarterAccountDefinition(
            account_number="6000", account_name="Operating Expenses", root_type=AccountRootType.EXPENSE,
            account_type=AccountType.EXPENSE, parent_number="5", is_group=False
        ),
    ],
)


async def seed_starter_chart(
    db: AsyncSession,
    tenant_id: uuid.UUID,
) -> list[Account]:
    """Seed the standard starter chart for a tenant.

    Args:
        db: Database session
        tenant_id: Tenant identifier

    Returns:
        List of all created accounts (roots + ledgers)
    """
    # Check if chart already exists (any account with this tenant)
    result = await db.execute(
        select(Account).where(Account.tenant_id == tenant_id).limit(1)
    )
    existing = result.scalar_one_or_none()
    if existing:
        logger.warning(f"Starter chart already exists for tenant {tenant_id}")
        # Return empty list since we didn't create anything
        return []

    created_accounts: list[Account] = []
    account_map: dict[str, Account] = {}

    # Create accounts in order (parents first)
    for defn in STANDARD_STARTER_CHART.accounts:
        parent = None
        if defn.parent_number:
            parent = account_map.get(defn.parent_number)

        account = Account(
            tenant_id=tenant_id,
            parent_id=parent.id if parent else None,
            account_number=defn.account_number,
            account_name=defn.account_name,
            root_type=_enum_value(defn.root_type),
            report_type=_enum_value(_ROOT_TYPE_TO_REPORT_TYPE[defn.root_type]),
            account_type=_enum_value(defn.account_type),
            is_group=defn.is_group,
            is_frozen=False,
            is_disabled=False,
            sort_order=0,
            parent_number=defn.parent_number,
        )
        db.add(account)
        await db.flush()
        await db.refresh(account)
        created_accounts.append(account)
        account_map[defn.account_number] = account

    logger.info(f"Seeded starter chart for tenant {tenant_id}: {len(created_accounts)} accounts")

    return created_accounts


# ============================================================
# Journal Entry Custom Exceptions
# ============================================================


class JournalEntryNotFoundError(Exception):
    """Raised when a journal entry is not found."""

    def __init__(self, journal_entry_id: uuid.UUID):
        self.journal_entry_id = journal_entry_id
        super().__init__(f"Journal entry not found: {journal_entry_id}")


class JournalEntryValidationError(Exception):
    """Raised when journal entry validation fails."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


class GLEntryValidationError(Exception):
    """Raised when GL entry validation fails."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


# ============================================================
# Journal Entry Service Functions
# ============================================================


def _generate_voucher_number(voucher_type: VoucherType, tenant_id: str) -> str:
    """Generate a unique voucher number for a journal entry.
    
    Format: JE-{type_prefix}-{timestamp}-{random}
    """
    import random
    prefix_map = {
        VoucherType.JOURNAL_ENTRY: "JE",
        VoucherType.OPENING_ENTRY: "OE",
    }
    prefix = prefix_map.get(voucher_type, "JE")
    return f"{prefix}-{datetime.now(tz=UTC).strftime('%Y%m%d%H%M%S')}-{random.randint(1000, 9999)}"


async def create_journal_entry(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    data: JournalEntryCreate,
) -> JournalEntry:
    """Create a new journal entry (draft state).

    Args:
        db: Database session
        tenant_id: Tenant identifier
        data: Journal entry creation data with lines

    Returns:
        Created JournalEntry instance

    Raises:
        JournalEntryValidationError: If validation fails
    """
    errors: list[str] = []

    # Validate posting date falls in open fiscal year
    fiscal_year = await get_fiscal_year_for_date(db, tenant_id, data.posting_date)
    if not fiscal_year:
        errors.append(f"No open fiscal year found for posting date {data.posting_date}")
    elif not fiscal_year.is_open:
        errors.append(f"Fiscal year {fiscal_year.label} is not open for posting")

    # Validate all accounts exist and are ledger accounts
    account_ids = [line.account_id for line in data.lines]
    accounts_result = await db.execute(
        select(Account).where(
            and_(
                Account.tenant_id == tenant_id,
                Account.id.in_(account_ids),
            )
        )
    )
    accounts = {acc.id: acc for acc in accounts_result.scalars().all()}

    for i, line in enumerate(data.lines):
        if line.account_id not in accounts:
            errors.append(f"Line {i+1}: Account not found")
        else:
            account = accounts[line.account_id]
            if account.is_group:
                errors.append(f"Line {i+1}: Cannot post to group account {account.account_number}")
            if account.is_frozen:
                errors.append(f"Line {i+1}: Cannot post to frozen account {account.account_number}")
            if account.is_disabled:
                errors.append(f"Line {i+1}: Cannot post to disabled account {account.account_number}")

    # Validate balanced lines
    total_debit = sum(line.debit for line in data.lines)
    total_credit = sum(line.credit for line in data.lines)
    if abs(total_debit - total_credit) > BALANCE_TOLERANCE:
        errors.append(f"Entry is not balanced: debit {total_debit} != credit {total_credit}")

    if errors:
        raise JournalEntryValidationError(errors)

    # Generate voucher number
    voucher_number = _generate_voucher_number(data.voucher_type, str(tenant_id))

    # Create journal entry
    journal_entry = JournalEntry(
        tenant_id=tenant_id,
        voucher_type=_enum_value(data.voucher_type),
        voucher_number=voucher_number,
        posting_date=data.posting_date,
        reference_date=data.reference_date,
        status=_enum_value(JournalEntryStatus.DRAFT),
        narration=data.narration,
        total_debit=total_debit,
        total_credit=total_credit,
        reference_type=data.reference_type,
        reference_id=data.reference_id,
        external_reference_number=data.external_reference_number,
        external_reference_date=data.external_reference_date,
    )

    db.add(journal_entry)
    await db.flush()

    # Create lines
    for line_data in data.lines:
        line = JournalEntryLine(
            journal_entry_id=journal_entry.id,
            account_id=line_data.account_id,
            debit=line_data.debit,
            credit=line_data.credit,
            remark=line_data.remark,
            cost_center_id=line_data.cost_center_id,
            project_id=line_data.project_id,
        )
        db.add(line)

    await db.flush()
    await db.refresh(journal_entry)

    logger.info(
        f"Created journal entry {voucher_number} "
        f"({journal_entry.voucher_type}, {len(data.lines)} lines)"
    )

    return journal_entry


async def get_journal_entry(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    journal_entry_id: uuid.UUID,
) -> JournalEntry:
    """Get a journal entry by ID.

    Args:
        db: Database session
        tenant_id: Tenant identifier
        journal_entry_id: Journal entry identifier

    Returns:
        JournalEntry instance

    Raises:
        JournalEntryNotFoundError: If journal entry not found
    """
    result = await db.execute(
        select(JournalEntry)
        .options(selectinload(JournalEntry.lines))
        .where(
            and_(
                JournalEntry.tenant_id == tenant_id,
                JournalEntry.id == journal_entry_id,
            )
        )
    )
    journal_entry = result.scalar_one_or_none()
    if not journal_entry:
        raise JournalEntryNotFoundError(journal_entry_id)
    return journal_entry


async def list_journal_entries(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    page: int = 1,
    page_size: int = 50,
    status: JournalEntryStatus | None = None,
    voucher_type: VoucherType | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
) -> JournalEntryListResponse:
    """List journal entries with pagination and filters.

    Args:
        db: Database session
        tenant_id: Tenant identifier
        page: Page number (1-indexed)
        page_size: Items per page
        status: Optional filter by status
        voucher_type: Optional filter by voucher type
        from_date: Optional start date filter
        to_date: Optional end date filter

    Returns:
        Paginated list of journal entries
    """
    conditions = [JournalEntry.tenant_id == tenant_id]

    if status:
        conditions.append(JournalEntry.status == _enum_value(status))

    if voucher_type:
        conditions.append(JournalEntry.voucher_type == _enum_value(voucher_type))

    if from_date:
        conditions.append(JournalEntry.posting_date >= from_date)

    if to_date:
        conditions.append(JournalEntry.posting_date <= to_date)

    # Count total
    count_result = await db.execute(
        select(JournalEntry).where(and_(*conditions))
    )
    total = len(count_result.scalars().all())

    # Get page
    offset = (page - 1) * page_size
    query = (
        select(JournalEntry)
        .where(and_(*conditions))
        .order_by(JournalEntry.posting_date.desc(), JournalEntry.voucher_number.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(query)
    journal_entries = result.scalars().all()

    return JournalEntryListResponse(
        items=[JournalEntryResponse.model_validate(je) for je in journal_entries],
        total=total,
        page=page,
        page_size=page_size,
    )


async def get_journal_entry_detail(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    journal_entry_id: uuid.UUID,
) -> JournalEntryDetailResponse:
    """Get journal entry with full line details.

    Args:
        db: Database session
        tenant_id: Tenant identifier
        journal_entry_id: Journal entry identifier

    Returns:
        JournalEntryDetailResponse with lines and account details

    Raises:
        JournalEntryNotFoundError: If journal entry not found
    """
    journal_entry = await get_journal_entry(db, tenant_id, journal_entry_id)

    # Get account details for lines
    account_ids = [line.account_id for line in journal_entry.lines]
    accounts_result = await db.execute(
        select(Account).where(Account.id.in_(account_ids))
    )
    accounts = {acc.id: acc for acc in accounts_result.scalars().all()}

    # Build response
    lines_with_accounts = []
    for line in journal_entry.lines:
        account = accounts.get(line.account_id)
        lines_with_accounts.append(
            JournalEntryLineWithAccount(
                id=line.id,
                journal_entry_id=line.journal_entry_id,
                account_id=line.account_id,
                debit=line.debit,
                credit=line.credit,
                remark=line.remark,
                cost_center_id=line.cost_center_id,
                project_id=line.project_id,
                created_at=line.created_at,
                updated_at=line.updated_at,
                account_number=account.account_number if account else "",
                account_name=account.account_name if account else "",
                account_root_type=account.root_type if account else "",
            )
        )

    return JournalEntryDetailResponse(
        id=journal_entry.id,
        tenant_id=journal_entry.tenant_id,
        voucher_type=journal_entry.voucher_type,
        voucher_number=journal_entry.voucher_number,
        posting_date=journal_entry.posting_date,
        reference_date=journal_entry.reference_date,
        status=journal_entry.status,
        narration=journal_entry.narration,
        total_debit=journal_entry.total_debit,
        total_credit=journal_entry.total_credit,
        reference_type=journal_entry.reference_type,
        reference_id=journal_entry.reference_id,
        external_reference_number=journal_entry.external_reference_number,
        external_reference_date=journal_entry.external_reference_date,
        reversed_by_id=journal_entry.reversed_by_id,
        reverses_id=journal_entry.reverses_id,
        submitted_at=journal_entry.submitted_at,
        submitted_by=journal_entry.submitted_by,
        cancelled_at=journal_entry.cancelled_at,
        cancelled_by=journal_entry.cancelled_by,
        cancel_reason=journal_entry.cancel_reason,
        created_at=journal_entry.created_at,
        updated_at=journal_entry.updated_at,
        lines=lines_with_accounts,
    )


async def update_journal_entry(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    journal_entry_id: uuid.UUID,
    data: JournalEntryUpdate,
) -> JournalEntry:
    """Update a draft journal entry.

    Args:
        db: Database session
        tenant_id: Tenant identifier
        journal_entry_id: Journal entry identifier
        data: Update data

    Returns:
        Updated JournalEntry instance

    Raises:
        JournalEntryNotFoundError: If journal entry not found
        JournalEntryValidationError: If validation fails
    """
    journal_entry = await get_journal_entry(db, tenant_id, journal_entry_id)

    if not journal_entry.is_draft:
        raise JournalEntryValidationError(["Can only update draft journal entries"])

    # Apply updates
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(journal_entry, field, value)

    journal_entry.updated_at = datetime.now(tz=UTC)
    await db.flush()
    await db.refresh(journal_entry)

    logger.info(f"Updated journal entry {journal_entry.voucher_number}")

    return journal_entry


async def add_journal_entry_line(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    journal_entry_id: uuid.UUID,
    data: JournalEntryLineCreate,
) -> JournalEntryLine:
    """Add a line to a draft journal entry.

    Args:
        db: Database session
        tenant_id: Tenant identifier
        journal_entry_id: Journal entry identifier
        data: Line creation data

    Returns:
        Created JournalEntryLine instance

    Raises:
        JournalEntryNotFoundError: If journal entry not found
        JournalEntryValidationError: If validation fails
    """
    journal_entry = await get_journal_entry(db, tenant_id, journal_entry_id)

    if not journal_entry.is_draft:
        raise JournalEntryValidationError(["Can only add lines to draft journal entries"])

    # Validate account
    account_result = await db.execute(
        select(Account).where(
            and_(
                Account.tenant_id == tenant_id,
                Account.id == data.account_id,
            )
        )
    )
    account = account_result.scalar_one_or_none()
    if not account:
        raise JournalEntryValidationError([f"Account not found: {data.account_id}"])
    if account.is_group:
        raise JournalEntryValidationError([f"Cannot post to group account {account.account_number}"])
    if account.is_frozen:
        raise JournalEntryValidationError([f"Cannot post to frozen account {account.account_number}"])

    # Create line
    line = JournalEntryLine(
        journal_entry_id=journal_entry_id,
        account_id=data.account_id,
        debit=data.debit,
        credit=data.credit,
        remark=data.remark,
        cost_center_id=data.cost_center_id,
        project_id=data.project_id,
    )
    db.add(line)

    # Update totals
    journal_entry.total_debit += data.debit
    journal_entry.total_credit += data.credit
    journal_entry.updated_at = datetime.now(tz=UTC)

    await db.flush()
    await db.refresh(line)

    logger.info(f"Added line to journal entry {journal_entry.voucher_number}")

    return line


async def remove_journal_entry_line(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    journal_entry_id: uuid.UUID,
    line_id: uuid.UUID,
) -> None:
    """Remove a line from a draft journal entry.

    Args:
        db: Database session
        tenant_id: Tenant identifier
        journal_entry_id: Journal entry identifier
        line_id: Line identifier

    Raises:
        JournalEntryNotFoundError: If journal entry not found
        JournalEntryValidationError: If validation fails
    """
    journal_entry = await get_journal_entry(db, tenant_id, journal_entry_id)

    if not journal_entry.is_draft:
        raise JournalEntryValidationError(["Can only remove lines from draft journal entries"])

    # Find and delete line
    result = await db.execute(
        select(JournalEntryLine).where(
            and_(
                JournalEntryLine.id == line_id,
                JournalEntryLine.journal_entry_id == journal_entry_id,
            )
        )
    )
    line = result.scalar_one_or_none()
    if not line:
        raise JournalEntryValidationError([f"Line not found: {line_id}"])

    # Update totals
    journal_entry.total_debit -= line.debit
    journal_entry.total_credit -= line.credit
    journal_entry.updated_at = datetime.now(tz=UTC)

    await db.delete(line)
    await db.flush()

    logger.info(f"Removed line from journal entry {journal_entry.voucher_number}")


# ============================================================
# GL Posting Service Functions
# ============================================================


async def submit_journal_entry(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    journal_entry_id: uuid.UUID,
    actor_id: uuid.UUID,
) -> tuple[JournalEntry, list[GLEntry]]:
    """Submit a journal entry and create GL entries.

    Args:
        db: Database session
        tenant_id: Tenant identifier
        journal_entry_id: Journal entry identifier
        actor_id: User submitting the entry

    Returns:
        Tuple of (submitted JournalEntry, list of created GLEntries)

    Raises:
        JournalEntryNotFoundError: If journal entry not found
        JournalEntryValidationError: If validation fails
    """
    journal_entry = await get_journal_entry(db, tenant_id, journal_entry_id)
    errors: list[str] = []

    # Check status
    if not journal_entry.is_draft:
        errors.append("Can only submit draft journal entries")

    # Check for at least 2 lines
    if len(journal_entry.lines) < 2:
        errors.append("At least 2 lines are required")

    # Check balance
    if not journal_entry.is_balanced:
        errors.append(
            f"Entry is not balanced: debit {journal_entry.total_debit} != "
            f"credit {journal_entry.total_credit}"
        )

    # Check fiscal year is open
    fiscal_year = await get_fiscal_year_for_date(db, tenant_id, journal_entry.posting_date)
    if not fiscal_year:
        errors.append(f"No fiscal year found for posting date {journal_entry.posting_date}")
    elif not fiscal_year.is_open:
        errors.append(f"Fiscal year {fiscal_year.label} is not open for posting")

    # Validate all accounts
    for line in journal_entry.lines:
        account_result = await db.execute(
            select(Account).where(Account.id == line.account_id)
        )
        account = account_result.scalar_one_or_none()
        if not account:
            errors.append(f"Line {line.id}: Account not found")
        elif account.is_group:
            errors.append(f"Line {line.id}: Cannot post to group account {account.account_number}")
        elif account.is_frozen:
            errors.append(f"Line {line.id}: Cannot post to frozen account {account.account_number}")
        elif account.is_disabled:
            errors.append(f"Line {line.id}: Cannot post to disabled account {account.account_number}")

    if errors:
        raise JournalEntryValidationError(errors)

    # Create GL entries
    gl_entries: list[GLEntry] = []
    for line in journal_entry.lines:
        gl_entry = GLEntry(
            tenant_id=tenant_id,
            account_id=line.account_id,
            posting_date=journal_entry.posting_date,
            fiscal_year=fiscal_year.label,
            debit=line.debit,
            credit=line.credit,
            entry_type=GLEntryType[journal_entry.voucher_type.upper().replace(" ", "_")].value,
            voucher_type=journal_entry.voucher_type,
            voucher_number=journal_entry.voucher_number,
            journal_entry_id=journal_entry.id,
            journal_entry_line_id=line.id,
            remark=line.remark,
        )
        db.add(gl_entry)
        gl_entries.append(gl_entry)

    # Update journal entry status
    journal_entry.status = _enum_value(JournalEntryStatus.SUBMITTED)
    journal_entry.submitted_at = datetime.now(tz=UTC)
    journal_entry.submitted_by = actor_id
    journal_entry.updated_at = datetime.now(tz=UTC)

    await db.flush()

    logger.info(
        f"Submitted journal entry {journal_entry.voucher_number}: "
        f"created {len(gl_entries)} GL entries"
    )

    return journal_entry, gl_entries


async def reverse_journal_entry(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    journal_entry_id: uuid.UUID,
    actor_id: uuid.UUID,
    reversal_date: date | None = None,
    cancel_reason: str | None = None,
) -> tuple[JournalEntry, JournalEntry, list[GLEntry]]:
    """Reverse a submitted journal entry.

    Creates a new journal entry with opposite debits/credits and links them.
    Original entry is marked as cancelled. Original GL entries are NOT deleted.

    Args:
        db: Database session
        tenant_id: Tenant identifier
        journal_entry_id: Journal entry to reverse
        actor_id: User reversing the entry
        reversal_date: Optional date for the reversal (defaults to today)
        cancel_reason: Reason for reversal

    Returns:
        Tuple of (original entry, reversing entry, reversing GL entries)

    Raises:
        JournalEntryNotFoundError: If journal entry not found
        JournalEntryValidationError: If validation fails
    """
    original = await get_journal_entry(db, tenant_id, journal_entry_id)
    errors: list[str] = []

    if not original.is_submitted:
        errors.append("Can only reverse submitted journal entries")

    if original.is_cancelled:
        errors.append("Journal entry is already cancelled")

    # Use today if reversal date not provided
    if reversal_date is None:
        reversal_date = date.today()

    # Check fiscal year is open
    fiscal_year = await get_fiscal_year_for_date(db, tenant_id, reversal_date)
    if not fiscal_year:
        errors.append(f"No fiscal year found for reversal date {reversal_date}")
    elif not fiscal_year.is_open:
        errors.append(f"Fiscal year {fiscal_year.label} is not open for reversal")

    if errors:
        raise JournalEntryValidationError(errors)

    # Create reversing journal entry
    reversing_voucher_number = _generate_voucher_number(
        VoucherType[original.voucher_type.upper().replace(" ", "_")],
        str(tenant_id)
    )

    reversing = JournalEntry(
        tenant_id=tenant_id,
        voucher_type=original.voucher_type,
        voucher_number=reversing_voucher_number,
        posting_date=reversal_date,
        status=JournalEntryStatus.SUBMITTED.value,
        narration=f"Reversal of {original.voucher_number}: {cancel_reason or 'Reversed entry'}",
        total_debit=original.total_credit,  # Swapped!
        total_credit=original.total_debit,  # Swapped!
        reverses_id=original.id,
        submitted_at=datetime.now(tz=UTC),
        submitted_by=actor_id,
    )
    db.add(reversing)
    await db.flush()

    # Create reversing GL entries
    gl_entries: list[GLEntry] = []
    for line in original.lines:
        gl_entry = GLEntry(
            tenant_id=tenant_id,
            account_id=line.account_id,
            posting_date=reversal_date,
            fiscal_year=fiscal_year.label,
            debit=line.credit,  # Swapped!
            credit=line.debit,  # Swapped!
            entry_type=GLEntryType[original.voucher_type.upper().replace(" ", "_")].value,
            voucher_type=original.voucher_type,
            voucher_number=reversing_voucher_number,
            journal_entry_id=reversing.id,
            journal_entry_line_id=line.id,
            remark=f"Reversal: {line.remark or ''}",
            reverses_id=None,  # We don't link GL entries, just the journal entries
        )
        db.add(gl_entry)
        gl_entries.append(gl_entry)

    # Update original entry status
    original.status = _enum_value(JournalEntryStatus.CANCELLED)
    original.reversed_by_id = reversing.id
    original.cancelled_at = datetime.now(tz=UTC)
    original.cancelled_by = actor_id
    original.cancel_reason = cancel_reason
    original.updated_at = datetime.now(tz=UTC)

    await db.flush()

    logger.info(
        f"Reversed journal entry {original.voucher_number} "
        f"-> {reversing.voucher_number}: created {len(gl_entries)} reversing GL entries"
    )

    return original, reversing, gl_entries


# ============================================================
# GL Entry Service Functions
# ============================================================


async def get_gl_entries(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    page: int = 1,
    page_size: int = 50,
    account_id: uuid.UUID | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    voucher_type: str | None = None,
    voucher_number: str | None = None,
    journal_entry_id: uuid.UUID | None = None,
    include_reversed: bool = False,
) -> GLEntryListResponse:
    """Get GL entries with filters.

    Args:
        db: Database session
        tenant_id: Tenant identifier
        page: Page number (1-indexed)
        page_size: Items per page
        account_id: Optional filter by account
        from_date: Optional start date filter
        to_date: Optional end date filter
        voucher_type: Optional filter by voucher type
        voucher_number: Optional filter by voucher number
        journal_entry_id: Optional filter by journal entry
        include_reversed: Whether to include reversed entries

    Returns:
        Paginated list of GL entries with account details
    """
    conditions = [GLEntry.tenant_id == tenant_id]

    if account_id:
        conditions.append(GLEntry.account_id == account_id)

    if from_date:
        conditions.append(GLEntry.posting_date >= from_date)

    if to_date:
        conditions.append(GLEntry.posting_date <= to_date)

    if voucher_type:
        conditions.append(GLEntry.voucher_type == voucher_type)

    if voucher_number:
        conditions.append(GLEntry.voucher_number == voucher_number)

    if journal_entry_id:
        conditions.append(GLEntry.journal_entry_id == journal_entry_id)

    if not include_reversed:
        # By default, show entries that haven't been reversed
        conditions.append(GLEntry.reversed_by_id.is_(None))

    # Count total
    count_result = await db.execute(
        select(GLEntry).where(and_(*conditions))
    )
    total = len(count_result.scalars().all())

    # Get page
    offset = (page - 1) * page_size
    query = (
        select(GLEntry)
        .options(selectinload(GLEntry.account))
        .where(and_(*conditions))
        .order_by(GLEntry.posting_date, GLEntry.created_at)
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(query)
    gl_entries = result.scalars().all()

    # Build response with account details
    items = []
    for entry in gl_entries:
        account = entry.account
        items.append(
            GLEntryWithAccount(
                id=entry.id,
                tenant_id=entry.tenant_id,
                account_id=entry.account_id,
                posting_date=entry.posting_date,
                fiscal_year=entry.fiscal_year,
                debit=entry.debit,
                credit=entry.credit,
                entry_type=entry.entry_type,
                voucher_type=entry.voucher_type,
                voucher_number=entry.voucher_number,
                source_type=entry.source_type,
                source_id=entry.source_id,
                journal_entry_id=entry.journal_entry_id,
                journal_entry_line_id=entry.journal_entry_line_id,
                reversed_by_id=entry.reversed_by_id,
                reverses_id=entry.reverses_id,
                remark=entry.remark,
                created_at=entry.created_at,
                account_number=account.account_number if account else "",
                account_name=account.account_name if account else "",
                account_root_type=account.root_type if account else "",
                account_type=account.account_type if account else "",
            )
        )

    return GLEntryListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


async def get_account_ledger(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    account_id: uuid.UUID,
    from_date: date | None = None,
    to_date: date | None = None,
) -> LedgerAccountSummary:
    """Get account ledger with opening balance, entries, and closing balance.

    Args:
        db: Database session
        tenant_id: Tenant identifier
        account_id: Account identifier
        from_date: Optional start date (ledger date range)
        to_date: Optional end date (ledger date range)

    Returns:
        LedgerAccountSummary with entries and balances

    Raises:
        GLEntryValidationError: If account not found
    """
    # Get account
    account_result = await db.execute(
        select(Account).where(
            and_(
                Account.tenant_id == tenant_id,
                Account.id == account_id,
            )
        )
    )
    account = account_result.scalar_one_or_none()
    if not account:
        raise GLEntryValidationError([f"Account not found: {account_id}"])

    # Calculate opening balance (sum of all entries before from_date)
    opening_conditions = [
        GLEntry.tenant_id == tenant_id,
        GLEntry.account_id == account_id,
    ]
    if from_date:
        opening_conditions.append(GLEntry.posting_date < from_date)

    opening_result = await db.execute(
        select(GLEntry).where(and_(*opening_conditions))
    )
    opening_entries = opening_result.scalars().all()

    opening_debit = sum(e.debit for e in opening_entries)
    opening_credit = sum(e.credit for e in opening_entries)
    opening_balance = opening_debit - opening_credit

    # Get entries in range
    entry_conditions = [
        GLEntry.tenant_id == tenant_id,
        GLEntry.account_id == account_id,
    ]
    if from_date:
        entry_conditions.append(GLEntry.posting_date >= from_date)
    if to_date:
        entry_conditions.append(GLEntry.posting_date <= to_date)

    query = (
        select(GLEntry)
        .where(and_(*entry_conditions))
        .order_by(GLEntry.posting_date, GLEntry.created_at)
    )
    result = await db.execute(query)
    entries = result.scalars().all()

    # Build GL entry responses
    gl_responses = []
    for entry in entries:
        gl_responses.append(
            GLEntryWithAccount(
                id=entry.id,
                tenant_id=entry.tenant_id,
                account_id=entry.account_id,
                posting_date=entry.posting_date,
                fiscal_year=entry.fiscal_year,
                debit=entry.debit,
                credit=entry.credit,
                entry_type=entry.entry_type,
                voucher_type=entry.voucher_type,
                voucher_number=entry.voucher_number,
                source_type=entry.source_type,
                source_id=entry.source_id,
                journal_entry_id=entry.journal_entry_id,
                journal_entry_line_id=entry.journal_entry_line_id,
                reversed_by_id=entry.reversed_by_id,
                reverses_id=entry.reverses_id,
                remark=entry.remark,
                created_at=entry.created_at,
                account_number=account.account_number,
                account_name=account.account_name,
                account_root_type=account.root_type,
                account_type=account.account_type,
            )
        )

    # Calculate totals and closing balance
    total_debit = sum(e.debit for e in entries)
    total_credit = sum(e.credit for e in entries)
    closing_balance = opening_balance + total_debit - total_credit

    return LedgerAccountSummary(
        account_id=account_id,
        account_number=account.account_number,
        account_name=account.account_name,
        opening_balance=opening_balance,
        total_debit=total_debit,
        total_credit=total_credit,
        closing_balance=closing_balance,
        entries=gl_responses,
    )


async def get_account_ledger_response(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    account_id: uuid.UUID,
    from_date: date | None = None,
    to_date: date | None = None,
) -> LedgerSummaryResponse:
    """Get full ledger response with account details.

    Args:
        db: Database session
        tenant_id: Tenant identifier
        account_id: Account identifier
        from_date: Optional start date
        to_date: Optional end date

    Returns:
        LedgerSummaryResponse with account and summary
    """
    account_result = await db.execute(
        select(Account).where(
            and_(
                Account.tenant_id == tenant_id,
                Account.id == account_id,
            )
        )
    )
    account = account_result.scalar_one_or_none()
    if not account:
        raise GLEntryValidationError([f"Account not found: {account_id}"])

    account_response = AccountResponse(
        id=account.id,
        tenant_id=account.tenant_id,
        parent_id=account.parent_id,
        parent_number=account.parent_number,
        account_number=account.account_number,
        account_name=account.account_name,
        root_type=account.root_type,
        report_type=account.report_type,
        account_type=account.account_type,
        is_group=account.is_group,
        is_frozen=account.is_frozen,
        is_disabled=account.is_disabled,
        sort_order=account.sort_order,
        currency_code=account.currency_code,
        created_at=account.created_at,
        updated_at=account.updated_at,
    )

    summary = await get_account_ledger(db, tenant_id, account_id, from_date, to_date)

    return LedgerSummaryResponse(
        account=account_response,
        summary=summary,
    )
