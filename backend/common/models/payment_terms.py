"""Payment terms template and schedule models for Epic 25 multi-currency foundation.

This module provides:
- PaymentTermsTemplate: Reusable payment term definitions
- PaymentTermsTemplateDetail: Installment schedule rows for templates
- PaymentSchedule: Generated schedule rows on commercial documents
- Legacy payment term compatibility enums
"""

from __future__ import annotations

import enum
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.database import Base


class LegacyPaymentTerms(str, enum.Enum):
    """Legacy payment term codes for backward compatibility."""

    NET_30 = "NET_30"
    NET_60 = "NET_60"
    NET_90 = "NET_90"
    COD = "COD"  # Cash on Delivery
    PREPAID = "PREPAID"


def get_legacy_due_date(document_date: date, payment_terms_code: str) -> date:
    """Calculate due date from legacy payment term code.

    Args:
        document_date: Date of the commercial document
        payment_terms_code: Legacy payment term code

    Returns:
        Calculated due date
    """
    if payment_terms_code == LegacyPaymentTerms.COD.value:
        return document_date  # Due immediately
    elif payment_terms_code == LegacyPaymentTerms.NET_30.value:
        return date(document_date.year, document_date.month, document_date.day) + _timedelta(days=30)
    elif payment_terms_code == LegacyPaymentTerms.NET_60.value:
        return date(document_date.year, document_date.month, document_date.day) + _timedelta(days=60)
    elif payment_terms_code == LegacyPaymentTerms.NET_90.value:
        return date(document_date.year, document_date.month, document_date.day) + _timedelta(days=90)
    elif payment_terms_code == LegacyPaymentTerms.PREPAID.value:
        return document_date  # Prepaid = due immediately
    else:
        # Default to NET_30 behavior
        return date(document_date.year, document_date.month, document_date.day) + _timedelta(days=30)


def _timedelta(days: int) -> "datetime.timedelta":
    """Get timedelta for days (lazy import to avoid circular)."""
    import datetime
    return datetime.timedelta(days=days)


class PaymentTermsTemplate(Base):
    """Reusable payment term template with installment schedule.

    A template defines a reusable payment schedule that can be applied
    to multiple commercial documents. Templates contain detail rows
    defining each installment.
    """

    __tablename__ = "payment_terms_templates"
    __table_args__ = (
        Index("uq_payment_terms_templates_tenant_name", "tenant_id", "template_name", unique=True),
        Index("ix_payment_terms_templates_active", "tenant_id", "is_active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)

    # Template identification
    template_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Allocation behavior
    allocate_payment_based_on_payment_terms: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Optional: link to legacy payment term code for migration compatibility
    legacy_code: Mapped[str | None] = mapped_column(String(20), nullable=True)

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
    details: Mapped[list[PaymentTermsTemplateDetail]] = relationship(
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="PaymentTermsTemplateDetail.row_number",
    )

    def __repr__(self) -> str:
        return f"<PaymentTermsTemplate {self.template_name}>"


class PaymentTermsTemplateDetail(Base):
    """Installment schedule row for a payment term template.

    Each detail row defines an installment with portion, due date offset,
    and optional early payment discount.
    """

    __tablename__ = "payment_terms_template_details"
    __table_args__ = (
        Index(
            "ix_payment_terms_template_details_template_row",
            "template_id",
            "row_number",
            unique=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    template_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey(
            "payment_terms_templates.id",
            name="fk_payment_terms_template_details_template",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    # Row ordering
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # Installment portion (percentage of total)
    invoice_portion: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False, default=Decimal("100.00"))

    # Due date calculation
    credit_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    credit_months: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Optional early payment discount
    discount_percent: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    discount_validity_days: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Optional mode of payment
    mode_of_payment: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Description
    description: Mapped[str | None] = mapped_column(String(200), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=UTC)
    )

    # Relationships
    template: Mapped[PaymentTermsTemplate] = relationship(back_populates="details")

    def calculate_due_date(self, document_date: date) -> date:
        """Calculate the due date for this installment row.

        Args:
            document_date: The commercial document date

        Returns:
            Calculated due date
        """
        from dateutil.relativedelta import relativedelta

        due_date = document_date
        if self.credit_months > 0:
            due_date = due_date + relativedelta(months=self.credit_months)
        due_date = due_date + _timedelta(days=self.credit_days)
        return due_date

    def __repr__(self) -> str:
        return f"<PaymentTermsTemplateDetail row={self.row_number} portion={self.invoice_portion}%>"


class PaymentSchedule(Base):
    """Generated payment schedule row on a commercial document.

    Each schedule row represents an installment with calculated due date,
    payment amount, and outstanding balance.
    """

    __tablename__ = "payment_schedules"
    __table_args__ = (
        Index("ix_payment_schedules_tenant_document", "tenant_id", "document_type", "document_id"),
        Index("ix_payment_schedules_due_date", "tenant_id", "due_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)

    # Document linkage
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'order', 'invoice', etc.
    document_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)

    # Reference to source template (if applicable)
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey(
            "payment_terms_templates.id",
            name="fk_payment_schedules_template",
            ondelete="SET NULL",
        ),
        nullable=True,
    )
    template_detail_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey(
            "payment_terms_template_details.id",
            name="fk_payment_schedules_template_detail",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    # Installment details
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    invoice_portion: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)

    # Due date and amounts
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    payment_amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    outstanding_amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False, default=Decimal("0.00"))

    # Discount info
    discount_percent: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    discount_validity_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    discount_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)

    # Status
    is_paid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    paid_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Mode of payment
    mode_of_payment: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Description
    description: Mapped[str | None] = mapped_column(String(200), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(tz=UTC),
        onupdate=lambda: datetime.now(tz=UTC),
    )

    def mark_paid(self, paid_date: date, amount: Decimal) -> None:
        """Mark this schedule row as paid.

        Args:
            paid_date: Date of payment
            amount: Amount paid
        """
        self.paid_amount = self.paid_amount + amount
        self.outstanding_amount = self.payment_amount - self.paid_amount
        if self.outstanding_amount <= Decimal("0.00"):
            self.is_paid = True
            self.outstanding_amount = Decimal("0.00")
        self.paid_date = paid_date

    def __repr__(self) -> str:
        return f"<PaymentSchedule row={self.row_number} due={self.due_date} outstanding={self.outstanding_amount}>"


# Legacy term mappings for backward compatibility
LEGACY_TERM_MAPPINGS: dict[str, dict] = {
    LegacyPaymentTerms.NET_30.value: {
        "template_name": "Net 30 (Legacy)",
        "credit_days": 30,
        "credit_months": 0,
        "invoice_portion": Decimal("100.00"),
    },
    LegacyPaymentTerms.NET_60.value: {
        "template_name": "Net 60 (Legacy)",
        "credit_days": 60,
        "credit_months": 0,
        "invoice_portion": Decimal("100.00"),
    },
    LegacyPaymentTerms.NET_90.value: {
        "template_name": "Net 90 (Legacy)",
        "credit_days": 90,
        "credit_months": 0,
        "invoice_portion": Decimal("100.00"),
    },
    LegacyPaymentTerms.COD.value: {
        "template_name": "Cash on Delivery (Legacy)",
        "credit_days": 0,
        "credit_months": 0,
        "invoice_portion": Decimal("100.00"),
    },
    LegacyPaymentTerms.PREPAID.value: {
        "template_name": "Prepaid (Legacy)",
        "credit_days": 0,
        "credit_months": 0,
        "invoice_portion": Decimal("100.00"),
    },
}
