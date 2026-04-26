"""Pydantic schemas for accounting domain (Epic 26).

Defines request/response schemas for account and fiscal year APIs.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from common.models.account import (
    AccountRootType,
    AccountReportType,
    AccountType,
)
from common.models.fiscal_year import FiscalYearStatus
from common.models.gl_entry import GLEntryType
from common.models.journal_entry import JournalEntryStatus, VoucherType


# ============================================================
# Account Schemas
# ============================================================


class AccountBase(BaseModel):
    """Base schema for account data."""

    account_number: str = Field(..., min_length=1, max_length=50)
    account_name: str = Field(..., min_length=1, max_length=255)
    root_type: AccountRootType
    account_type: AccountType
    is_group: bool = False
    is_frozen: bool = False
    is_disabled: bool = False
    sort_order: int = 0
    currency_code: str | None = Field(None, max_length=3)

    @field_validator("account_number")
    @classmethod
    def validate_account_number(cls, v: str) -> str:
        """Validate account number format."""
        if not v.strip():
            raise ValueError("Account number cannot be empty")
        return v.strip()

    @field_validator("account_name")
    @classmethod
    def validate_account_name(cls, v: str) -> str:
        """Validate account name format."""
        if not v.strip():
            raise ValueError("Account name cannot be empty")
        return v.strip()


class AccountCreate(AccountBase):
    """Schema for creating a new account."""

    parent_id: uuid.UUID | None = None


class AccountUpdate(BaseModel):
    """Schema for updating an existing account (partial update)."""

    account_number: str | None = Field(None, min_length=1, max_length=50)
    account_name: str | None = Field(None, min_length=1, max_length=255)
    account_type: AccountType | None = None
    is_group: bool | None = None
    is_frozen: bool | None = None
    is_disabled: bool | None = None
    sort_order: int | None = None
    currency_code: str | None = Field(None, max_length=3)
    parent_id: uuid.UUID | None = None

    @field_validator("account_number")
    @classmethod
    def validate_account_number(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            raise ValueError("Account number cannot be empty")
        return v.strip() if v else v

    @field_validator("account_name")
    @classmethod
    def validate_account_name(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            raise ValueError("Account name cannot be empty")
        return v.strip() if v else v


class AccountResponse(AccountBase):
    """Schema for account response data."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    parent_id: uuid.UUID | None
    parent_number: str | None
    report_type: AccountReportType
    created_at: datetime
    updated_at: datetime


class AccountTreeNode(AccountResponse):
    """Schema for account tree node with children."""

    children: list["AccountTreeNode"] = Field(default_factory=list)


class AccountListResponse(BaseModel):
    """Schema for paginated account list response."""

    items: list[AccountResponse]
    total: int
    page: int
    page_size: int


class AccountTreeResponse(BaseModel):
    """Schema for full account tree response."""

    roots: list[AccountTreeNode]
    total_accounts: int


# ============================================================
# Fiscal Year Schemas
# ============================================================


class FiscalYearBase(BaseModel):
    """Base schema for fiscal year data."""

    label: str = Field(..., min_length=4, max_length=20)
    start_date: date
    end_date: date
    is_default: bool = False

    @field_validator("label")
    @classmethod
    def validate_label(cls, v: str) -> str:
        """Validate fiscal year label format (FY2026 or 2026)."""
        v = v.strip()
        if not v:
            raise ValueError("Label cannot be empty")
        # Check format: either YYYY or FYYYYY
        if not (v.startswith("FY") and len(v) == 6 and v[2:].isdigit()) and not (len(v) == 4 and v.isdigit()):
            raise ValueError("Label must be in format YYYY or FYYYYY (e.g., 2026 or FY2026)")
        return v

    @field_validator("end_date")
    @classmethod
    def validate_end_date(cls, v: date, info) -> date:
        """Validate end_date is after start_date."""
        if "start_date" in info.data:
            start = info.data["start_date"]
            if v <= start:
                raise ValueError("End date must be after start date")
        return v


class FiscalYearCreate(FiscalYearBase):
    """Schema for creating a new fiscal year."""

    pass


class FiscalYearUpdate(BaseModel):
    """Schema for updating a fiscal year (partial update)."""

    label: str | None = Field(None, min_length=4, max_length=20)
    start_date: date | None = None
    end_date: date | None = None
    status: FiscalYearStatus | None = None
    is_default: bool | None = None
    closure_notes: str | None = Field(None, max_length=500)

    @field_validator("label")
    @classmethod
    def validate_label(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Label cannot be empty")
            if not (v.startswith("FY") and len(v) == 6 and v[2:].isdigit()) and not (len(v) == 4 and v.isdigit()):
                raise ValueError("Label must be in format YYYY or FYYYYY (e.g., 2026 or FY2026)")
        return v


class FiscalYearResponse(FiscalYearBase):
    """Schema for fiscal year response data."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    status: FiscalYearStatus
    closed_at: datetime | None
    closed_by: uuid.UUID | None
    closure_notes: str | None
    created_at: datetime
    updated_at: datetime


class FiscalYearListResponse(BaseModel):
    """Schema for paginated fiscal year list response."""

    items: list[FiscalYearResponse]
    total: int
    page: int
    page_size: int


# ============================================================
# Validation Error Schemas
# ============================================================


# ============================================================
# Starter Chart Schemas
# ============================================================


class StarterAccountDefinition(BaseModel):
    """Definition for a starter chart account."""

    account_number: str
    account_name: str
    root_type: AccountRootType
    account_type: AccountType
    parent_number: str | None = None
    is_group: bool = False


class StarterChartProfile(BaseModel):
    """Starter chart profile definition."""

    name: str
    description: str
    accounts: list[StarterAccountDefinition]


# Update forward references
AccountTreeNode.model_rebuild()


# ============================================================
# Journal Entry Schemas
# ============================================================


class JournalEntryLineBase(BaseModel):
    """Base schema for journal entry line data."""

    account_id: uuid.UUID
    debit: float = Field(default=0, ge=0)
    credit: float = Field(default=0, ge=0)
    remark: str | None = Field(None, max_length=500)
    cost_center_id: str | None = Field(None, max_length=50)
    project_id: str | None = Field(None, max_length=50)

    @field_validator("debit", "credit")
    @classmethod
    def validate_amount(cls, v: float) -> float:
        """Validate amount is not negative."""
        if v < 0:
            raise ValueError("Amount cannot be negative")
        return round(v, 6)


class JournalEntryLineCreate(JournalEntryLineBase):
    """Schema for creating a journal entry line."""

    pass


class JournalEntryLineUpdate(BaseModel):
    """Schema for updating a journal entry line."""

    account_id: uuid.UUID | None = None
    debit: float | None = Field(None, ge=0)
    credit: float | None = Field(None, ge=0)
    remark: str | None = Field(None, max_length=500)
    cost_center_id: str | None = Field(None, max_length=50)
    project_id: str | None = Field(None, max_length=50)


class JournalEntryLineResponse(JournalEntryLineBase):
    """Schema for journal entry line response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    journal_entry_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class JournalEntryLineWithAccount(JournalEntryLineResponse):
    """Schema for journal entry line with account details."""

    account_number: str
    account_name: str
    account_root_type: str


# ============================================================
# Journal Entry Schemas
# ============================================================


class JournalEntryBase(BaseModel):
    """Base schema for journal entry data."""

    voucher_type: VoucherType = VoucherType.JOURNAL_ENTRY
    posting_date: date
    reference_date: date | None = None
    narration: str | None = Field(None, max_length=1000)
    reference_type: str | None = Field(None, max_length=50)
    reference_id: uuid.UUID | None = None
    external_reference_number: str | None = Field(None, max_length=100)
    external_reference_date: date | None = None


class JournalEntryCreate(JournalEntryBase):
    """Schema for creating a journal entry."""

    lines: list[JournalEntryLineCreate] = Field(..., min_length=2)

    @field_validator("lines")
    @classmethod
    def validate_lines(cls, v: list[JournalEntryLineCreate]) -> list[JournalEntryLineCreate]:
        """Validate at least 2 lines."""
        if len(v) < 2:
            raise ValueError("At least 2 lines are required")
        return v


class JournalEntryUpdate(BaseModel):
    """Schema for updating a journal entry (partial update)."""

    voucher_type: VoucherType | None = None
    posting_date: date | None = None
    reference_date: date | None = None
    narration: str | None = Field(None, max_length=1000)
    reference_type: str | None = Field(None, max_length=50)
    reference_id: uuid.UUID | None = None
    external_reference_number: str | None = Field(None, max_length=100)
    external_reference_date: date | None = None


class JournalEntryResponse(JournalEntryBase):
    """Schema for journal entry response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    voucher_number: str
    status: JournalEntryStatus
    total_debit: float
    total_credit: float
    reversed_by_id: uuid.UUID | None
    reverses_id: uuid.UUID | None
    submitted_at: datetime | None
    submitted_by: uuid.UUID | None
    cancelled_at: datetime | None
    cancelled_by: uuid.UUID | None
    cancel_reason: str | None
    created_at: datetime
    updated_at: datetime


class JournalEntryDetailResponse(JournalEntryResponse):
    """Schema for journal entry detail with lines."""

    lines: list[JournalEntryLineWithAccount] = Field(default_factory=list)


class JournalEntryListResponse(BaseModel):
    """Schema for paginated journal entry list."""

    items: list[JournalEntryResponse]
    total: int
    page: int
    page_size: int


class JournalEntrySubmitResponse(BaseModel):
    """Response after submitting a journal entry."""

    journal_entry: JournalEntryResponse
    gl_entries_created: int
    message: str


class JournalEntryReverseResponse(BaseModel):
    """Response after reversing a journal entry."""

    original_entry: JournalEntryResponse
    reversing_entry: JournalEntryResponse
    gl_entries_created: int
    message: str


# ============================================================
# GL Entry Schemas
# ============================================================


class GLEntryResponse(BaseModel):
    """Schema for GL entry response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    account_id: uuid.UUID
    posting_date: date
    fiscal_year: str
    debit: float
    credit: float
    entry_type: GLEntryType
    voucher_type: str
    voucher_number: str
    source_type: str | None
    source_id: uuid.UUID | None
    journal_entry_id: uuid.UUID | None
    journal_entry_line_id: uuid.UUID | None
    reversed_by_id: uuid.UUID | None
    reverses_id: uuid.UUID | None
    remark: str | None
    created_at: datetime


class GLEntryWithAccount(GLEntryResponse):
    """Schema for GL entry with account details."""

    account_number: str
    account_name: str
    account_root_type: str
    account_type: str


class GLEntryListResponse(BaseModel):
    """Schema for paginated GL entry list."""

    items: list[GLEntryWithAccount]
    total: int
    page: int
    page_size: int


class LedgerAccountSummary(BaseModel):
    """Schema for account ledger summary."""

    account_id: uuid.UUID
    account_number: str
    account_name: str
    opening_balance: float
    total_debit: float
    total_credit: float
    closing_balance: float
    entries: list[GLEntryWithAccount]


class LedgerSummaryResponse(BaseModel):
    """Schema for full ledger summary."""

    account: AccountResponse
    summary: LedgerAccountSummary
