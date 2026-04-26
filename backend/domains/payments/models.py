"""Payment ORM model."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Index, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.database import Base

if TYPE_CHECKING:
    from domains.customers.models import Customer
    from domains.invoices.models import Invoice


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        Index("uq_payments_tenant_payment_ref", "tenant_id", "payment_ref", unique=True),
        Index("ix_payments_tenant_invoice", "tenant_id", "invoice_id"),
        Index("ix_payments_tenant_invoice_match", "tenant_id", "invoice_id", "match_status"),
        Index("ix_payments_tenant_customer", "tenant_id", "customer_id"),
        Index("ix_payments_tenant_date", "tenant_id", "payment_date"),
        Index("ix_payments_match_status", "tenant_id", "match_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("invoices.id", name="fk_payments_invoice_id_invoices", ondelete="RESTRICT"),
        nullable=True,
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("customers.id", name="fk_payments_customer_id_customers", ondelete="RESTRICT"),
        nullable=False,
    )
    payment_ref: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    payment_method: Mapped[str] = mapped_column(String(20), nullable=False)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    reference_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(tz=UTC),
        onupdate=lambda: datetime.now(tz=UTC),
    )

    # Reconciliation fields (Story 6.2)
    match_status: Mapped[str] = mapped_column(String(20), nullable=False, default="matched")
    match_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    matched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    suggested_invoice_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("invoices.id", name="fk_payments_suggested_invoice_id", ondelete="SET NULL"),
        nullable=True,
    )

    invoice: Mapped[Invoice | None] = relationship(foreign_keys=[invoice_id])
    customer: Mapped[Customer] = relationship()
    suggested_invoice: Mapped[Invoice | None] = relationship(foreign_keys=[suggested_invoice_id])

    # Currency snapshot fields (Story 25-2)
    currency_code: Mapped[str | None] = mapped_column(String(3), nullable=True, default="TWD")
    conversion_rate: Mapped[Decimal | None] = mapped_column(Numeric(20, 10), nullable=True, default=Decimal("1.0"))
    conversion_effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    applied_rate_source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    base_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
