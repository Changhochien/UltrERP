"""FiscalYear model for accounting period management (Epic 26).

Defines fiscal year boundaries with open/closed state for posting period validation.
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
    Index,
    String,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from common.database import Base

if TYPE_CHECKING:
    pass


class FiscalYearStatus(str, enum.Enum):
    """Fiscal year lifecycle states."""

    DRAFT = "Draft"  # Being configured
    OPEN = "Open"  # Active for posting
    CLOSED = "Closed"  # Closed for posting
    ARCHIVED = "Archived"  # Historical record only


class FiscalYear(Base):
    """Tenant-scoped fiscal year with explicit date boundaries and state.

    Adjacent fiscal years are allowed (back-to-back periods).
    Overlapping fiscal years are rejected by database constraint.
    """

    __tablename__ = "fiscal_years"
    __table_args__ = (
        # Tenant-scoped unique label
        Index("ix_fiscal_years_tenant_label", "tenant_id", "label", unique=True),
        # Index for date range queries
        Index("ix_fiscal_years_tenant_dates", "tenant_id", "start_date", "end_date"),
        # Index for status queries
        Index("ix_fiscal_years_tenant_status", "tenant_id", "status"),
        # Ensure start_date is before end_date
        CheckConstraint(
            "start_date < end_date",
            name="ck_fiscal_years_date_order",
        ),
        # Ensure label matches standard format (e.g., "FY2026" or "2026")
        CheckConstraint(
            "label ~ '^[0-9]{4}$|^FY[0-9]{4}$'",
            name="ck_fiscal_years_label_format",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)

    # Fiscal year label/identifier (e.g., "FY2026", "2026")
    label: Mapped[str] = mapped_column(String(20), nullable=False)

    # Explicit date boundaries
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Fiscal year state (stored as string)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=FiscalYearStatus.OPEN.value,
    )

    # Optional: Is this the default fiscal year for new transactions?
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Closure metadata (populated when status transitions to CLOSED)
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    closed_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)

    # Optional: closure notes
    closure_notes: Mapped[str | None] = mapped_column(String(500), nullable=True)

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

    def __repr__(self) -> str:
        return f"<FiscalYear {self.label} ({self.start_date} to {self.end_date}, {self.status.value})>"

    @property
    def is_open(self) -> bool:
        """True if fiscal year is open for posting."""
        return self.status == FiscalYearStatus.OPEN

    @property
    def is_closed(self) -> bool:
        """True if fiscal year is closed for posting."""
        return self.status == FiscalYearStatus.CLOSED

    @property
    def is_draft(self) -> bool:
        """True if fiscal year is still being configured."""
        return self.status == FiscalYearStatus.DRAFT

    def contains_date(self, check_date: date) -> bool:
        """Check if a date falls within this fiscal year."""
        return self.start_date <= check_date <= self.end_date

    def overlaps_with(self, other_start: date, other_end: date) -> bool:
        """Check if this fiscal year overlaps with a date range.

        Returns True if there is any overlap between the two periods.
        """
        # Two ranges overlap if one starts before the other ends and ends after the other starts
        return self.start_date < other_end and self.end_date > other_start

    def is_adjacent_to(self, other_start: date, other_end: date) -> bool:
        """Check if this fiscal year is adjacent to a date range.

        Adjacent means: this.end_date == other.start_date OR this.start_date == other.end_date
        """
        return self.end_date == other_start or self.start_date == other_end

    def validate_date_range(
        self, new_start: date, new_end: date, exclude_id: uuid.UUID | None = None
    ) -> list[str]:
        """Validate that date range is valid.

        Returns list of validation error messages (empty if valid).
        """
        errors = []

        if new_start >= new_end:
            errors.append("Start date must be before end date")

        # Check for invalid date order (already covered by DB constraint, but explicit)
        if new_start < date(2000, 1, 1) or new_end < date(2000, 1, 1):
            errors.append("Date range must be after year 2000")

        if new_end > date(2100, 12, 31):
            errors.append("Date range must be before year 2100")

        return errors
