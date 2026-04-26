"""Journal Entry model for manual accounting postings (Epic 26).

Defines journal entry headers and lines with explicit debit/credit balancing,
voucher type classification, and reversal linkage support.
"""

from __future__ import annotations

import enum
import uuid
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.database import Base

if TYPE_CHECKING:
    pass


class JournalEntryStatus(str, enum.Enum):
    """Journal entry lifecycle states."""

    DRAFT = "Draft"  # Being edited
    SUBMITTED = "Submitted"  # Posted to GL
    CANCELLED = "Cancelled"  # Reversed


class VoucherType(str, enum.Enum):
    """Voucher type classification for journal entries.

    Start with minimal types; extend later for Credit Note, Debit Note,
    Exchange Gain/Loss, bank-derived vouchers, etc.
    """

    JOURNAL_ENTRY = "Journal Entry"  # General manual journal entry
    OPENING_ENTRY = "Opening Entry"  # Opening balance entry


class JournalEntry(Base):
    """Tenant-scoped journal entry header.

    Contains metadata for a batch of GL postings. Each entry has one or more
    lines that must balance (total debit == total credit) before submission.
    """

    __tablename__ = "journal_entries"
    __table_args__ = (
        # Tenant-scoped unique voucher number
        Index(
            "ix_journal_entries_tenant_voucher",
            "tenant_id",
            "voucher_number",
            unique=True,
        ),
        # Index for date range queries
        Index("ix_journal_entries_tenant_posting_date", "tenant_id", "posting_date"),
        # Index for status filtering
        Index("ix_journal_entries_tenant_status", "tenant_id", "status"),
        # Index for voucher type filtering
        Index("ix_journal_entries_tenant_voucher_type", "tenant_id", "voucher_type"),
        # Index for reversal lookups
        Index("ix_journal_entries_tenant_reversed_by", "tenant_id", "reversed_by_id"),
        Index("ix_journal_entries_tenant_reverses", "tenant_id", "reverses_id"),
        # Ensure total debit equals total credit on submit
        CheckConstraint(
            "total_debit = total_credit",
            name="ck_journal_entries_balanced",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)

    # Voucher identification
    voucher_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default=VoucherType.JOURNAL_ENTRY.value
    )
    voucher_number: Mapped[str] = mapped_column(String(50), nullable=False)

    # Posting period
    posting_date: Mapped[date] = mapped_column(Date, nullable=False)
    reference_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Entry status
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=JournalEntryStatus.DRAFT.value
    )

    # Descriptive content
    narration: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Totals (must balance on submit)
    total_debit: Mapped[float] = mapped_column(
        Numeric(precision=20, scale=6), nullable=False, default=0
    )
    total_credit: Mapped[float] = mapped_column(
        Numeric(precision=20, scale=6), nullable=False, default=0
    )

    # Reference fields for linking to external documents (future use)
    # e.g., invoices, supplier invoices, payments, bank activity
    reference_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reference_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    external_reference_number: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    external_reference_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Reversal linkage
    # If this entry was reversed by another entry
    reversed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("journal_entries.id", ondelete="RESTRICT"), nullable=True
    )
    # If this entry reverses another entry
    reverses_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("journal_entries.id", ondelete="RESTRICT"), nullable=True
    )

    # Submit/cancel metadata
    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    submitted_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancelled_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    cancel_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Audit metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(tz=UTC),
        onupdate=lambda: datetime.now(tz=UTC),
    )

    # Relationships
    lines: Mapped[list["JournalEntryLine"]] = relationship(
        "JournalEntryLine",
        back_populates="journal_entry",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    reversed_by: Mapped["JournalEntry | None"] = relationship(
        "JournalEntry",
        remote_side=[id],
        foreign_keys=[reversed_by_id],
        back_populates="reverses",
    )
    reverses: Mapped["JournalEntry | None"] = relationship(
        "JournalEntry",
        remote_side=[id],
        foreign_keys=[reverses_id],
        back_populates="reversed_by",
    )

    def __repr__(self) -> str:
        return (
            f"<JournalEntry {self.voucher_number} ({self.voucher_type}, "
            f"{self.status.value}, {self.total_debit}/{self.total_credit})>"
        )

    @property
    def is_draft(self) -> bool:
        """True if entry is in draft state."""
        return self.status == JournalEntryStatus.DRAFT

    @property
    def is_submitted(self) -> bool:
        """True if entry has been posted to GL."""
        return self.status == JournalEntryStatus.SUBMITTED

    @property
    def is_cancelled(self) -> bool:
        """True if entry was reversed."""
        return self.status == JournalEntryStatus.CANCELLED

    @property
    def is_balanced(self) -> bool:
        """True if debits equal credits."""
        return self.total_debit == self.total_credit

    @property
    def can_submit(self) -> bool:
        """True if entry can be submitted."""
        return self.is_draft and self.is_balanced and len(self.lines) >= 2

    @property
    def can_cancel(self) -> bool:
        """True if entry can be cancelled."""
        return self.is_submitted

    @property
    def can_edit(self) -> bool:
        """True if entry can be edited."""
        return self.is_draft
