"""API routes for accounting domain (Epic 26).

Exposes account tree and fiscal year management endpoints.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from common.auth import require_role
from common.database import get_db
from common.models.account import AccountRootType

from .schemas import (
    AccountCreate,
    AccountListResponse,
    AccountResponse,
    AccountTreeResponse,
    AccountUpdate,
    FiscalYearCreate,
    FiscalYearListResponse,
    FiscalYearResponse,
    FiscalYearUpdate,
    GLEntryListResponse,
    JournalEntryCreate,
    JournalEntryDetailResponse,
    JournalEntryLineCreate,
    JournalEntryListResponse,
    JournalEntryResponse,
    JournalEntryReverseResponse,
    JournalEntrySubmitResponse,
    JournalEntryUpdate,
    LedgerSummaryResponse,
    StarterChartProfile,
    VoucherType,
)
from .service import (
    AccountNotFoundError,
    AccountValidationError,
    FiscalYearNotFoundError,
    FiscalYearValidationError,
    GLEntryValidationError,
    JournalEntryNotFoundError,
    JournalEntryValidationError,
    STANDARD_STARTER_CHART,
    add_journal_entry_line,
    close_fiscal_year,
    create_account,
    create_fiscal_year,
    create_journal_entry,
    delete_account,
    disable_account,
    freeze_account,
    get_account,
    get_account_ledger_response,
    get_account_tree,
    get_fiscal_year,
    get_fiscal_year_for_date,
    get_gl_entries,
    get_journal_entry,
    get_journal_entry_detail,
    get_open_fiscal_years,
    list_accounts,
    list_fiscal_years,
    list_journal_entries,
    remove_journal_entry_line,
    reopen_fiscal_year,
    reverse_journal_entry,
    seed_starter_chart,
    submit_journal_entry,
    unfreeze_account,
    update_account,
    update_fiscal_year,
    update_journal_entry,
)

router = APIRouter(
    prefix="/accounting",
    tags=["accounting"],
    dependencies=[Depends(require_role("owner", "admin", "finance"))],
)

DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[dict, Depends(require_role("owner", "admin", "finance"))]


def _get_tenant_id(current_user: CurrentUser) -> uuid.UUID:
    """Extract tenant ID from current user."""
    return uuid.UUID(current_user["tenant_id"])


def _get_user_id(current_user: CurrentUser) -> uuid.UUID:
    """Extract user ID from current user."""
    return uuid.UUID(current_user["user_id"])


# ============================================================
# Account Routes
# ============================================================


@router.get("/accounts", response_model=AccountTreeResponse)
async def get_account_tree_endpoint(
    db: DbSession,
    current_user: CurrentUser,
    include_disabled: bool = Query(False, description="Include disabled accounts"),
) -> AccountTreeResponse:
    """Get full account tree for the tenant.

    Returns a hierarchical tree structure with all accounts grouped by parent.
    """
    tenant_id = _get_tenant_id(current_user)
    return await get_account_tree(db, tenant_id, include_disabled=include_disabled)


@router.get("/accounts/list", response_model=AccountListResponse)
async def list_accounts_endpoint(
    db: DbSession,
    current_user: CurrentUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
    root_type: AccountRootType | None = None,
    include_disabled: bool = Query(False, description="Include disabled accounts"),
) -> AccountListResponse:
    """List accounts with pagination.

    Returns a flat list of accounts suitable for tables or dropdowns.
    """
    tenant_id = _get_tenant_id(current_user)
    return await list_accounts(
        db,
        tenant_id,
        page=page,
        page_size=page_size,
        root_type=root_type,
        include_disabled=include_disabled,
    )


@router.get("/accounts/{account_id}", response_model=AccountResponse)
async def get_account_endpoint(
    account_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> AccountResponse:
    """Get a single account by ID."""
    tenant_id = _get_tenant_id(current_user)
    try:
        account = await get_account(db, tenant_id, account_id)
        return AccountResponse.model_validate(account)
    except AccountNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/accounts", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account_endpoint(
    data: AccountCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> AccountResponse:
    """Create a new account.

    - **account_number**: Unique identifier within tenant
    - **account_name**: Display name
    - **root_type**: Asset, Liability, Equity, Income, or Expense
    - **account_type**: Detailed type (Bank, Cash, Receivable, etc.)
    - **is_group**: True for structural nodes, False for ledger accounts
    - **parent_id**: Parent account ID (must be a group account)
    """
    tenant_id = _get_tenant_id(current_user)
    try:
        account = await create_account(db, tenant_id, data)
        await db.commit()
        return AccountResponse.model_validate(account)
    except AccountValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"errors": e.errors},
        )


@router.patch("/accounts/{account_id}", response_model=AccountResponse)
async def update_account_endpoint(
    account_id: uuid.UUID,
    data: AccountUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> AccountResponse:
    """Update an existing account.

    Only non-frozen, non-disabled accounts can be updated.
    """
    tenant_id = _get_tenant_id(current_user)
    try:
        account = await update_account(db, tenant_id, account_id, data)
        await db.commit()
        return AccountResponse.model_validate(account)
    except AccountNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except AccountValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"errors": e.errors},
        )


@router.post("/accounts/{account_id}/freeze", response_model=AccountResponse)
async def freeze_account_endpoint(
    account_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> AccountResponse:
    """Freeze an account (rejects postings but retains data).

    Ledger accounts (non-group) can be frozen. Group accounts cannot be frozen.
    """
    tenant_id = _get_tenant_id(current_user)
    try:
        account = await freeze_account(db, tenant_id, account_id)
        await db.commit()
        return AccountResponse.model_validate(account)
    except AccountNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except AccountValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"errors": e.errors},
        )


@router.post("/accounts/{account_id}/unfreeze", response_model=AccountResponse)
async def unfreeze_account_endpoint(
    account_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> AccountResponse:
    """Unfreeze a frozen account (allows postings)."""
    tenant_id = _get_tenant_id(current_user)
    try:
        account = await unfreeze_account(db, tenant_id, account_id)
        await db.commit()
        return AccountResponse.model_validate(account)
    except AccountNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except AccountValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"errors": e.errors},
        )


@router.post("/accounts/{account_id}/disable", response_model=AccountResponse)
async def disable_account_endpoint(
    account_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> AccountResponse:
    """Disable an account (hides from selection, rejects all operations).

    Ledger accounts can be disabled. Group accounts cannot be disabled directly.
    Use freeze instead for group accounts that should reject postings.
    """
    tenant_id = _get_tenant_id(current_user)
    try:
        account = await disable_account(db, tenant_id, account_id)
        await db.commit()
        return AccountResponse.model_validate(account)
    except AccountNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except AccountValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"errors": e.errors},
        )


@router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account_endpoint(
    account_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> None:
    """Delete an account.

    Only accounts without children can be deleted.
    For accounts in use, use freeze/disable instead.
    """
    tenant_id = _get_tenant_id(current_user)
    try:
        await delete_account(db, tenant_id, account_id)
        await db.commit()
    except AccountNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except AccountValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"errors": e.errors},
        )


# ============================================================
# Fiscal Year Routes
# ============================================================


@router.get("/fiscal-years", response_model=FiscalYearListResponse)
async def list_fiscal_years_endpoint(
    db: DbSession,
    current_user: CurrentUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> FiscalYearListResponse:
    """List fiscal years with pagination."""
    tenant_id = _get_tenant_id(current_user)
    return await list_fiscal_years(
        db,
        tenant_id,
        page=page,
        page_size=page_size,
    )


@router.get("/fiscal-years/{fiscal_year_id}", response_model=FiscalYearResponse)
async def get_fiscal_year_endpoint(
    fiscal_year_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> FiscalYearResponse:
    """Get a single fiscal year by ID."""
    tenant_id = _get_tenant_id(current_user)
    try:
        fiscal_year = await get_fiscal_year(db, tenant_id, fiscal_year_id)
        return FiscalYearResponse.model_validate(fiscal_year)
    except FiscalYearNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/fiscal-years", response_model=FiscalYearResponse, status_code=status.HTTP_201_CREATED)
async def create_fiscal_year_endpoint(
    data: FiscalYearCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> FiscalYearResponse:
    """Create a new fiscal year.

    - **label**: Fiscal year identifier (e.g., "FY2026" or "2026")
    - **start_date**: First day of fiscal year
    - **end_date**: Last day of fiscal year
    - **is_default**: Set as default for new transactions
    """
    tenant_id = _get_tenant_id(current_user)
    try:
        fiscal_year = await create_fiscal_year(db, tenant_id, data)
        await db.commit()
        return FiscalYearResponse.model_validate(fiscal_year)
    except FiscalYearValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"errors": e.errors},
        )


@router.patch("/fiscal-years/{fiscal_year_id}", response_model=FiscalYearResponse)
async def update_fiscal_year_endpoint(
    fiscal_year_id: uuid.UUID,
    data: FiscalYearUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> FiscalYearResponse:
    """Update an existing fiscal year."""
    tenant_id = _get_tenant_id(current_user)
    actor_id = _get_user_id(current_user)
    try:
        fiscal_year = await update_fiscal_year(
            db, tenant_id, fiscal_year_id, data, actor_id=actor_id
        )
        await db.commit()
        return FiscalYearResponse.model_validate(fiscal_year)
    except FiscalYearNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except FiscalYearValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"errors": e.errors},
        )


@router.post("/fiscal-years/{fiscal_year_id}/close", response_model=FiscalYearResponse)
async def close_fiscal_year_endpoint(
    fiscal_year_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
    closure_notes: str | None = None,
) -> FiscalYearResponse:
    """Close a fiscal year for posting.

    Once closed, the fiscal year cannot accept new transactions.
    Use reopen to allow modifications (admin operation).
    """
    tenant_id = _get_tenant_id(current_user)
    actor_id = _get_user_id(current_user)
    try:
        fiscal_year = await close_fiscal_year(
            db, tenant_id, fiscal_year_id, actor_id, closure_notes
        )
        await db.commit()
        return FiscalYearResponse.model_validate(fiscal_year)
    except FiscalYearNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except FiscalYearValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"errors": e.errors},
        )


@router.post("/fiscal-years/{fiscal_year_id}/reopen", response_model=FiscalYearResponse)
async def reopen_fiscal_year_endpoint(
    fiscal_year_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> FiscalYearResponse:
    """Reopen a closed fiscal year.

    This is an admin operation to allow corrections to historical periods.
    """
    tenant_id = _get_tenant_id(current_user)
    try:
        fiscal_year = await reopen_fiscal_year(db, tenant_id, fiscal_year_id)
        await db.commit()
        return FiscalYearResponse.model_validate(fiscal_year)
    except FiscalYearNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except FiscalYearValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"errors": e.errors},
        )


@router.get("/fiscal-years/lookup/{check_date}", response_model=FiscalYearResponse)
async def get_fiscal_year_for_date_endpoint(
    check_date: str,
    db: DbSession,
    current_user: CurrentUser,
) -> FiscalYearResponse:
    """Get the fiscal year containing a given date.

    The date should be in ISO format (YYYY-MM-DD).
    """
    from datetime import date as date_type
    tenant_id = _get_tenant_id(current_user)
    try:
        parsed_date = date_type.fromisoformat(check_date)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use YYYY-MM-DD",
        )

    fiscal_year = await get_fiscal_year_for_date(db, tenant_id, parsed_date)
    if not fiscal_year:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No fiscal year found for date {check_date}",
        )
    return FiscalYearResponse.model_validate(fiscal_year)


@router.get("/fiscal-years/open", response_model=list[FiscalYearResponse])
async def get_open_fiscal_years_endpoint(
    db: DbSession,
    current_user: CurrentUser,
) -> list[FiscalYearResponse]:
    """Get all open fiscal years for posting."""
    tenant_id = _get_tenant_id(current_user)
    fiscal_years = await get_open_fiscal_years(db, tenant_id)
    return [FiscalYearResponse.model_validate(fy) for fy in fiscal_years]


# ============================================================
# Starter Chart Routes
# ============================================================


@router.post("/accounts/seed", response_model=AccountTreeResponse, status_code=status.HTTP_201_CREATED)
async def seed_starter_chart_endpoint(
    db: DbSession,
    current_user: CurrentUser,
) -> AccountTreeResponse:
    """Seed the standard starter chart of accounts.

    Creates the 5 root accounts (Asset, Liability, Equity, Income, Expense)
    with essential ledger accounts under each.

    This operation is idempotent - if accounts already exist, no changes are made.
    """
    tenant_id = _get_tenant_id(current_user)
    await seed_starter_chart(db, tenant_id)
    await db.commit()
    return await get_account_tree(db, tenant_id)


@router.get("/accounts/starter-profiles", response_model=list[StarterChartProfile])
async def get_starter_profiles_endpoint() -> list[StarterChartProfile]:
    """Get available starter chart profiles.

    Returns definitions of available starter chart configurations.
    """
    return [STANDARD_STARTER_CHART]


# ============================================================
# Journal Entry Routes
# ============================================================


@router.get("/journal-entries", response_model=JournalEntryListResponse)
async def list_journal_entries_endpoint(
    db: DbSession,
    current_user: CurrentUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
    status: str | None = Query(None, description="Filter by status: Draft, Submitted, Cancelled"),
    voucher_type: str | None = Query(None, description="Filter by voucher type"),
    from_date: str | None = Query(None, description="Filter from date (YYYY-MM-DD)"),
    to_date: str | None = Query(None, description="Filter to date (YYYY-MM-DD)"),
) -> JournalEntryListResponse:
    """List journal entries with pagination and filters."""
    from datetime import date as date_type
    from common.models.journal_entry import JournalEntryStatus

    tenant_id = _get_tenant_id(current_user)

    # Parse status
    status_enum = None
    if status:
        try:
            status_enum = JournalEntryStatus(status)
        except ValueError:
            pass

    # Parse voucher type
    voucher_type_enum = None
    if voucher_type:
        try:
            voucher_type_enum = VoucherType(voucher_type)
        except ValueError:
            pass

    # Parse dates
    from_date_parsed = None
    if from_date:
        try:
            from_date_parsed = date_type.fromisoformat(from_date)
        except ValueError:
            pass

    to_date_parsed = None
    if to_date:
        try:
            to_date_parsed = date_type.fromisoformat(to_date)
        except ValueError:
            pass

    return await list_journal_entries(
        db,
        tenant_id,
        page=page,
        page_size=page_size,
        status=status_enum,
        voucher_type=voucher_type_enum,
        from_date=from_date_parsed,
        to_date=to_date_parsed,
    )


@router.get("/journal-entries/{journal_entry_id}", response_model=JournalEntryDetailResponse)
async def get_journal_entry_endpoint(
    journal_entry_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> JournalEntryDetailResponse:
    """Get a journal entry with full line details."""
    tenant_id = _get_tenant_id(current_user)
    try:
        return await get_journal_entry_detail(db, tenant_id, journal_entry_id)
    except JournalEntryNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post(
    "/journal-entries",
    response_model=JournalEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_journal_entry_endpoint(
    data: JournalEntryCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> JournalEntryResponse:
    """Create a new journal entry (draft state).

    - **voucher_type**: Journal Entry or Opening Entry
    - **posting_date**: Date for GL posting
    - **narration**: Optional description
    - **lines**: At least 2 lines with account, debit, credit

    The entry must balance (total debit == total credit).
    """
    tenant_id = _get_tenant_id(current_user)
    try:
        journal_entry = await create_journal_entry(db, tenant_id, data)
        await db.commit()
        return JournalEntryResponse.model_validate(journal_entry)
    except JournalEntryValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"errors": e.errors},
        )


@router.patch("/journal-entries/{journal_entry_id}", response_model=JournalEntryResponse)
async def update_journal_entry_endpoint(
    journal_entry_id: uuid.UUID,
    data: JournalEntryUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> JournalEntryResponse:
    """Update a draft journal entry.

    Only draft journal entries can be updated.
    """
    tenant_id = _get_tenant_id(current_user)
    try:
        journal_entry = await update_journal_entry(db, tenant_id, journal_entry_id, data)
        await db.commit()
        return JournalEntryResponse.model_validate(journal_entry)
    except JournalEntryNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except JournalEntryValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"errors": e.errors},
        )


@router.post("/journal-entries/{journal_entry_id}/submit", response_model=JournalEntrySubmitResponse)
async def submit_journal_entry_endpoint(
    journal_entry_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> JournalEntrySubmitResponse:
    """Submit a journal entry and create GL entries.

    Validates:
    - Entry is in draft state
    - Has at least 2 lines
    - Debits equal credits
    - All accounts are valid ledger accounts
    - Posting date is in an open fiscal year

    Creates corresponding GL entries for each line.
    """
    tenant_id = _get_tenant_id(current_user)
    actor_id = _get_user_id(current_user)
    try:
        journal_entry, gl_entries = await submit_journal_entry(
            db, tenant_id, journal_entry_id, actor_id
        )
        await db.commit()
        return JournalEntrySubmitResponse(
            journal_entry=JournalEntryResponse.model_validate(journal_entry),
            gl_entries_created=len(gl_entries),
            message=f"Successfully submitted and created {len(gl_entries)} GL entries",
        )
    except JournalEntryNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except JournalEntryValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"errors": e.errors},
        )


@router.post("/journal-entries/{journal_entry_id}/reverse", response_model=JournalEntryReverseResponse)
async def reverse_journal_entry_endpoint(
    journal_entry_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
    reversal_date: str | None = Query(None, description="Reversal date (YYYY-MM-DD)"),
    cancel_reason: str | None = Query(None, description="Reason for reversal"),
) -> JournalEntryReverseResponse:
    """Reverse a submitted journal entry.

    Creates a new journal entry with opposite debits/credits.
    The original entry is marked as cancelled.
    Original GL entries are NOT deleted - they remain in the ledger.
    """
    from datetime import date as date_type

    tenant_id = _get_tenant_id(current_user)
    actor_id = _get_user_id(current_user)

    # Parse reversal date
    reversal_date_parsed = None
    if reversal_date:
        try:
            reversal_date_parsed = date_type.fromisoformat(reversal_date)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD",
            )

    try:
        original, reversing, gl_entries = await reverse_journal_entry(
            db, tenant_id, journal_entry_id, actor_id,
            reversal_date=reversal_date_parsed,
            cancel_reason=cancel_reason,
        )
        await db.commit()
        return JournalEntryReverseResponse(
            original_entry=JournalEntryResponse.model_validate(original),
            reversing_entry=JournalEntryResponse.model_validate(reversing),
            gl_entries_created=len(gl_entries),
            message=f"Successfully reversed entry and created {len(gl_entries)} reversing GL entries",
        )
    except JournalEntryNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except JournalEntryValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"errors": e.errors},
        )


@router.post(
    "/journal-entries/{journal_entry_id}/lines",
    response_model=JournalEntryLineCreate,
    status_code=status.HTTP_201_CREATED,
)
async def add_journal_entry_line_endpoint(
    journal_entry_id: uuid.UUID,
    data: JournalEntryLineCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> JournalEntryLineCreate:
    """Add a line to a draft journal entry."""
    tenant_id = _get_tenant_id(current_user)
    try:
        line = await add_journal_entry_line(db, tenant_id, journal_entry_id, data)
        await db.commit()
        return JournalEntryLineCreate(
            account_id=line.account_id,
            debit=line.debit,
            credit=line.credit,
            remark=line.remark,
            cost_center_id=line.cost_center_id,
            project_id=line.project_id,
        )
    except JournalEntryNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except JournalEntryValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"errors": e.errors},
        )


@router.delete("/journal-entries/{journal_entry_id}/lines/{line_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_journal_entry_line_endpoint(
    journal_entry_id: uuid.UUID,
    line_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> None:
    """Remove a line from a draft journal entry."""
    tenant_id = _get_tenant_id(current_user)
    try:
        await remove_journal_entry_line(db, tenant_id, journal_entry_id, line_id)
        await db.commit()
    except JournalEntryNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except JournalEntryValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"errors": e.errors},
        )


# ============================================================
# General Ledger Routes
# ============================================================


@router.get("/general-ledger", response_model=GLEntryListResponse)
async def get_general_ledger_endpoint(
    db: DbSession,
    current_user: CurrentUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
    account_id: uuid.UUID | None = Query(None, description="Filter by account"),
    from_date: str | None = Query(None, description="Filter from date (YYYY-MM-DD)"),
    to_date: str | None = Query(None, description="Filter to date (YYYY-MM-DD)"),
    voucher_type: str | None = Query(None, description="Filter by voucher type"),
    voucher_number: str | None = Query(None, description="Filter by voucher number"),
    include_reversed: bool = Query(False, description="Include reversed entries"),
) -> GLEntryListResponse:
    """Get general ledger entries with filters.

    Returns GL entries with account details. Use this endpoint for:
    - Account/date range reports
    - Voucher-based lookups
    - Ledger reconciliation
    """
    from datetime import date as date_type

    tenant_id = _get_tenant_id(current_user)

    # Parse dates
    from_date_parsed = None
    if from_date:
        try:
            from_date_parsed = date_type.fromisoformat(from_date)
        except ValueError:
            pass

    to_date_parsed = None
    if to_date:
        try:
            to_date_parsed = date_type.fromisoformat(to_date)
        except ValueError:
            pass

    return await get_gl_entries(
        db,
        tenant_id,
        page=page,
        page_size=page_size,
        account_id=account_id,
        from_date=from_date_parsed,
        to_date=to_date_parsed,
        voucher_type=voucher_type,
        voucher_number=voucher_number,
        include_reversed=include_reversed,
    )


@router.get("/accounts/{account_id}/ledger", response_model=LedgerSummaryResponse)
async def get_account_ledger_endpoint(
    account_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
    from_date: str | None = Query(None, description="Start date (YYYY-MM-DD)"),
    to_date: str | None = Query(None, description="End date (YYYY-MM-DD)"),
) -> LedgerSummaryResponse:
    """Get account ledger with opening balance, entries, and closing balance.

    Returns:
    - Account details
    - Opening balance (before from_date)
    - GL entries in date range
    - Total debits and credits
    - Closing balance
    """
    from datetime import date as date_type

    tenant_id = _get_tenant_id(current_user)

    # Parse dates
    from_date_parsed = None
    if from_date:
        try:
            from_date_parsed = date_type.fromisoformat(from_date)
        except ValueError:
            pass

    to_date_parsed = None
    if to_date:
        try:
            to_date_parsed = date_type.fromisoformat(to_date)
        except ValueError:
            pass

    try:
        return await get_account_ledger_response(
            db, tenant_id, account_id,
            from_date=from_date_parsed,
            to_date=to_date_parsed,
        )
    except GLEntryValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"errors": e.errors},
        )
