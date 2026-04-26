"""
Bank Account, Bank Transaction, and Dunning models for Epic 26 Story 26-5.
"""
from __future__ import annotations

import uuid
from datetime import datetime, date, UTC
from decimal import Decimal
from enum import Enum

from sqlalchemy import Boolean, Date, DateTime, Enum as SAEnum, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.database import Base


def _enum_values(enum_cls: type[Enum]) -> list[str]:
    return [member.value for member in enum_cls]


class BankTransactionStatus(str, Enum):
    """Status of a bank transaction."""
    UNMATCHED = "unmatched"
    SUGGESTED = "suggested"
    MATCHED = "matched"
    RECONCILED = "reconciled"
    EXCLUDED = "excluded"


class DunningNoticeStatus(str, Enum):
    """Status of a dunning notice."""
    DRAFT = "draft"
    OPEN = "open"
    RESOLVED = "resolved"
    CANCELLED = "cancelled"


class BankAccount(Base):
    """Bank account master for reconciliation."""
    __tablename__ = "bank_accounts"
    __table_args__ = (
        Index("ix_bank_accounts_tenant", "tenant_id"),
        Index("ix_bank_accounts_tenant_account_number", "tenant_id", "account_number", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    account_name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_number: Mapped[str] = mapped_column(String(100), nullable=False)
    bank_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    bank_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False, default="TWD")
    opening_balance: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False, default=Decimal("0"))
    current_balance: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False, default=Decimal("0"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    created_by: Mapped[str | None] = mapped_column(String(100), nullable=True)


class BankTransaction(Base):
    """Imported bank transaction for reconciliation."""
    __tablename__ = "bank_transactions"
    __table_args__ = (
        Index("ix_bank_tx_tenant_date", "tenant_id", "transaction_date"),
        Index("ix_bank_tx_tenant_bank", "tenant_id", "bank_account_id"),
        Index("ix_bank_tx_status", "tenant_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    bank_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bank_accounts.id"), nullable=False
    )
    
    # Import batch metadata
    import_batch_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    import_file_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    import_row_number: Mapped[int | None] = mapped_column(nullable=True)
    imported_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    
    # Transaction details
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    value_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    reference_number: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    # Amount (use debit and credit OR signed_amount)
    debit: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False, default=Decimal("0"))
    credit: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False, default=Decimal("0"))
    signed_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False, default="TWD")
    base_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    
    # Matching
    status: Mapped[str] = mapped_column(
        SAEnum(BankTransactionStatus, name="bank_tx_status_enum", values_callable=_enum_values),
        nullable=False,
        default=BankTransactionStatus.UNMATCHED
    )
    
    # Match suggestions (JSON array of suggestions)
    suggestions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class BankTransactionMatch(Base):
    """Links a bank transaction to matched vouchers (payments, journal entries)."""
    __tablename__ = "bank_transaction_matches"
    __table_args__ = (
        Index("ix_bank_tx_match_tx", "bank_transaction_id"),
        Index("ix_bank_tx_match_voucher", "voucher_type", "voucher_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    bank_transaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bank_transactions.id"), nullable=False
    )
    
    # Matched voucher
    voucher_type: Mapped[str] = mapped_column(String(50), nullable=False)  # Payment, JournalEntry
    voucher_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    matched_amount: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    
    # Match metadata
    match_type: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")  # manual, auto, exact
    match_confidence: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=True)  # 0-100%
    reference_matched: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    is_reconciled: Mapped[bool] = mapped_column(Boolean, default=False)
    reconciled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reconciled_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class DunningNotice(Base):
    """Manual dunning notice for overdue receivables."""
    __tablename__ = "dunning_notices"
    __table_args__ = (
        Index("ix_dunning_tenant_status", "tenant_id", "status"),
        Index("ix_dunning_customer", "tenant_id", "customer_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    
    # Reference to source invoice
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=True
    )
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True
    )
    
    # Notice details
    notice_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    notice_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    
    # Status
    status: Mapped[str] = mapped_column(
        SAEnum(DunningNoticeStatus, name="dunning_status_enum", values_callable=_enum_values),
        nullable=False,
        default=DunningNoticeStatus.DRAFT
    )
    
    # Financial
    outstanding_amount: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    fee_amount: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False, default=Decimal("0"))
    interest_amount: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False, default=Decimal("0"))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    
    # Content
    notice_text: Mapped[str] = mapped_column(Text, nullable=False)
    reminder_level: Mapped[int] = mapped_column(default=1)  # 1=first, 2=second, 3=final
    
    # Outcome tracking
    outcome: Mapped[str | None] = mapped_column(String(50), nullable=True)  # paid, partially_paid, disputed, escalation, other
    outcome_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    # Audit
    created_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )
