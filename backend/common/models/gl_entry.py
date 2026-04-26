"""GL Entry model for immutable general ledger postings (Epic 26).

Defines individual GL entries that are created when journal entries are submitted.
Once created, GL entries are immutable - corrections are made through reversing entries.
"""

from __future__ import annotations

import enum
import uuid
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
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


class GLEntryType(str, enum.Enum):
    """GL entry type for classification."""

    JOURNAL_ENTRY = "Journal Entry"
    OPENING_ENTRY = "Opening Entry"
    # Future types:
    # INVOICE = "Sales Invoice"
    # PAYMENT = "Payment"
    # PURCHASE_INVOICE = "Purchase Invoice"


class GLEntry(Base):
    """Immutable general ledger entry.

    GL entries are created when journal entries are submitted.
    They represent the atomic accounting transactions posted to accounts.
    GL entries are never modified or deleted - corrections use reversing entries.
    """

    __tablename__ = "gl_entries"
    __table_args__ = (
        # Index for account/date ledger queries (most common read pattern)
        Index("ix_gl_entries_account_posting_date", "account_id", "posting_date"),
        # Index for tenant/account lookups
        Index("ix_gl_entries_tenant_account", "tenant_id", "account_id"),
        # Index for voucher-based lookups
        Index("ix_gl_entries_tenant_voucher", "tenant_id", "voucher_type", "voucher_number"),
        # Index for reversal lookups
        Index("ix_gl_entries_tenant_reversed_by", "tenant_id", "reversed_by_id"),
        Index("ix_gl_entries_tenant_reverses", "tenant_id", "reverses_id"),
        # Index for fiscal year queries
        Index("ix_gl_entries_tenant_fiscal_year", "tenant_id", "fiscal_year"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)

    # Account reference (ledger account)
    account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False
    )

    # Posting period
    posting_date: Mapped[date] = mapped_column(Date, nullable=False)
    fiscal_year: Mapped[str] = mapped_column(String(20), nullable=False)

    # Debit or credit amount (exactly one should be non-zero)
    debit: Mapped[float] = mapped_column(
        Numeric(precision=20, scale=6), nullable=False, default=0
    )
    credit: Mapped[float] = mapped_column(
        Numeric(precision=20, scale=6), nullable=False, default=0
    )

    # Voucher/source document lineage
    entry_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default=GLEntryType.JOURNAL_ENTRY.value
    )
    voucher_type: Mapped[str] = mapped_column(String(50), nullable=False)
    voucher_number: Mapped[str] = mapped_column(String(50), nullable=False)

    # Source document reference
    source_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)

    # Journal entry line reference (for drill-down)
    journal_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("journal_entries.id", ondelete="RESTRICT"), nullable=True
    )
    journal_entry_line_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("journal_entry_lines.id", ondelete="RESTRICT"), nullable=True
    )

    # Reversal linkage
    # If this entry was reversed by another GL entry
    reversed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("gl_entries.id", ondelete="RESTRICT"), nullable=True
    )
    # If this entry reverses another GL entry
    reverses_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("gl_entries.id", ondelete="RESTRICT"), nullable=True
    )

    # Line-level remark from journal entry
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Audit metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=UTC)
    )

    # Relationships
    account = relationship(
        "Account",
        foreign_keys=[account_id],
        lazy="selectin",
    )
    journal_entry = relationship(
        "JournalEntry",
        foreign_keys=[journal_entry_id],
        lazy="selectin",
    )
    journal_entry_line = relationship(
        "JournalEntryLine",
        foreign_keys=[journal_entry_line_id],
        lazy="selectin",
    )
    reversed_by = relationship(
        "GLEntry",
        remote_side=[id],
        foreign_keys=[reversed_by_id],
    )
    reverses = relationship(
        "GLEntry",
        remote_side=[id],
        foreign_keys=[reverses_id],
    )

    def __repr__(self) -> str:
        return (
            f"<GLEntry {self.voucher_number} account={self.account_id} "
            f"debit={self.debit} credit={self.credit}>"
        )

    @property
    def is_debit(self) -> bool:
        """True if this is a debit entry."""
        return self.debit > 0 and self.credit == 0

    @property
    def is_credit(self) -> bool:
        """True if this is a credit entry."""
        return self.credit > 0 and self.debit == 0

    @property
    def amount(self) -> float:
        """Get the absolute amount of this entry."""
        return max(self.debit, self.credit)

    @property
    def is_reversed(self) -> bool:
        """True if this entry has been reversed."""
        return self.reversed_by_id is not None

    @property
    def is_reversal(self) -> bool:
        """True if this entry is a reversal of another entry."""
        return self.reverses_id is not None
