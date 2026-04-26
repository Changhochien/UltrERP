"""
Budget models for Epic 26 Story 26-6.
"""
from __future__ import annotations

import uuid
from datetime import datetime, date, UTC
from decimal import Decimal
from enum import Enum

from sqlalchemy import Boolean, Date, DateTime, Enum as SAEnum, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.database import Base


def _enum_values(enum_cls: type[Enum]) -> list[str]:
    return [member.value for member in enum_cls]


class BudgetStatus(str, Enum):
    """Budget status."""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    CANCELLED = "cancelled"


class BudgetCheckAction(str, Enum):
    """Budget check action."""
    IGNORE = "ignore"
    WARN = "warn"
    STOP = "stop"


class Budget(Base):
    """Budget master with period allocation and revision-safe history."""
    __tablename__ = "budgets"
    __table_args__ = (
        Index("ix_budgets_tenant_year", "tenant_id", "fiscal_year"),
        Index("ix_budgets_tenant_scope", "tenant_id", "scope_type", "scope_ref"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    
    # Budget identification
    budget_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    budget_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Fiscal year
    fiscal_year: Mapped[str] = mapped_column(String(20), nullable=False)  # e.g., "2026"
    
    # Scope (generic - department, project, cost center, or null)
    scope_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # department, project, cost_center, null
    scope_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)  # reference ID
    
    # Status
    status: Mapped[str] = mapped_column(
        SAEnum(BudgetStatus, name="budget_status_enum", values_callable=_enum_values),
        nullable=False,
        default=BudgetStatus.DRAFT
    )
    
    # Policy for expense accounts
    expense_action: Mapped[str] = mapped_column(
        SAEnum(BudgetCheckAction, name="budget_check_action_enum", values_callable=_enum_values),
        nullable=False,
        default=BudgetCheckAction.WARN
    )
    
    # Revision tracking
    revision_of_budget_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("budgets.id"), nullable=True
    )
    is_latest: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(default=1)
    
    # Total budget amount
    total_amount: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False, default="TWD")
    
    # Audit
    submitted_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )


class BudgetPeriod(Base):
    """Budget period allocation."""
    __tablename__ = "budget_periods"
    __table_args__ = (
        Index("ix_budget_period_budget", "budget_id"),
        Index("ix_budget_period_tenant_budget_month", "tenant_id", "budget_id", "period_start", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    budget_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("budgets.id"), nullable=False
    )
    
    # Period
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    period_name: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., "January 2026"
    
    # Allocation
    allocated_amount: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    distribution_type: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")  # equal, manual
    
    # Revision tracking
    revision_of_period_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("budget_periods.id"), nullable=True
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )


class BudgetAccountAllocation(Base):
    """Links budgets to specific accounts for targeted expense control."""
    __tablename__ = "budget_account_allocations"
    __table_args__ = (
        Index("ix_budget_account_budget", "budget_id"),
        Index("ix_budget_account_account", "account_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    budget_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("budgets.id"), nullable=False
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False
    )
    
    # Control
    action: Mapped[str] = mapped_column(
        SAEnum(BudgetCheckAction, name="budget_check_action_enum", values_callable=_enum_values),
        nullable=False,
        default=BudgetCheckAction.WARN
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
