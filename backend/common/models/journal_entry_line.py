"""Journal Entry Line model for individual debit/credit postings (Epic 26).

Defines journal entry lines with explicit account, debit/credit amounts,
and optional cost center/project references for future extensibility.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
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


class JournalEntryLine(Base):
    """Journal entry line representing a single debit or credit posting.

    Each line belongs to a journal entry header and references a ledger account.
    The sum of all lines' debits must equal the sum of all lines' credits.
    """

    __tablename__ = "journal_entry_lines"
    __table_args__ = (
        # Index for account/date ledger queries
        Index(
            "ix_journal_entry_lines_account",
            "account_id",
        ),
        # Index for journal entry line lookups
        Index(
            "ix_journal_entry_lines_journal_entry",
            "journal_entry_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    journal_entry_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("journal_entries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Account reference
    account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False
    )

    # Debit or credit amount (exactly one should be non-zero)
    # Using separate columns enforces double-entry integrity
    debit: Mapped[float] = mapped_column(
        Numeric(precision=20, scale=6), nullable=False, default=0
    )
    credit: Mapped[float] = mapped_column(
        Numeric(precision=20, scale=6), nullable=False, default=0
    )

    # Line-level description/remark
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Optional: Cost center reference (deferred to later stories)
    # Keeping as string for flexibility - can be UUID or code
    cost_center_id: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Optional: Project reference (deferred to later stories)
    project_id: Mapped[str | None] = mapped_column(String(50), nullable=True)

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
    journal_entry: Mapped["JournalEntry"] = relationship(
        "JournalEntry",
        back_populates="lines",
    )

    def __repr__(self) -> str:
        return (
            f"<JournalEntryLine account={self.account_id} "
            f"debit={self.debit} credit={self.credit}>"
        )

    @property
    def is_debit(self) -> bool:
        """True if this is a debit line."""
        return self.debit > 0 and self.credit == 0

    @property
    def is_credit(self) -> bool:
        """True if this is a credit line."""
        return self.credit > 0 and self.debit == 0

    @property
    def is_balanced(self) -> bool:
        """True if exactly one of debit/credit is non-zero."""
        return (self.debit == 0) != (self.credit == 0)

    @property
    def amount(self) -> float:
        """Get the absolute amount of this line."""
        return max(self.debit, self.credit)
