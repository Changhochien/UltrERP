"""Invoice ORM models for the invoice lifecycle epic foundation."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.database import Base

if TYPE_CHECKING:
    from domains.customers.models import Customer
    from common.models.order import Order


class InvoiceNumberRange(Base):
    __tablename__ = "invoice_number_ranges"
    __table_args__ = (
        Index(
            "uq_invoice_number_ranges_tenant_prefix_start_end",
            "tenant_id",
            "prefix",
            "start_number",
            "end_number",
            unique=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    prefix: Mapped[str] = mapped_column(String(2), nullable=False)
    start_number: Mapped[int] = mapped_column(Integer, nullable=False)
    end_number: Mapped[int] = mapped_column(Integer, nullable=False)
    next_number: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(tz=UTC),
        onupdate=lambda: datetime.now(tz=UTC),
    )


class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (
        Index("uq_invoices_tenant_invoice_number", "tenant_id", "invoice_number", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    invoice_number: Mapped[str] = mapped_column(String(10), nullable=False)
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("customers.id", name="fk_invoices_customer_id_customers"),
        nullable=False,
    )
    buyer_type: Mapped[str] = mapped_column(String(10), nullable=False)
    buyer_identifier_snapshot: Mapped[str] = mapped_column(String(10), nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False, default="TWD")
    subtotal_amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="issued")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Void-related fields
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    void_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    replaces_invoice_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    replaced_by_invoice_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("orders.id", name="fk_invoices_order_id_orders", ondelete="SET NULL"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(tz=UTC),
        onupdate=lambda: datetime.now(tz=UTC),
    )

    customer: Mapped[Customer] = relationship()
    lines: Mapped[list[InvoiceLine]] = relationship(
        back_populates="invoice",
        cascade="all, delete-orphan",
        order_by="InvoiceLine.line_number",
    )
    egui_submission: Mapped[EguiSubmission | None] = relationship(
        back_populates="invoice",
        cascade="all, delete-orphan",
        uselist=False,
    )


class EguiSubmission(Base):
    __tablename__ = "egui_submissions"
    __table_args__ = (
        Index("uq_egui_submissions_tenant_invoice", "tenant_id", "invoice_id", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("invoices.id", name="fk_egui_submissions_invoice_id_invoices"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    mode: Mapped[str] = mapped_column(String(10), nullable=False, default="mock")
    fia_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    deadline_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(tz=UTC),
        onupdate=lambda: datetime.now(tz=UTC),
    )

    invoice: Mapped[Invoice] = relationship(back_populates="egui_submission")


class InvoiceLine(Base):
    __tablename__ = "invoice_lines"
    __table_args__ = (
        Index("uq_invoice_lines_invoice_id_line_number", "invoice_id", "line_number", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("invoices.id", name="fk_invoice_lines_invoice_id_invoices"),
        nullable=False,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    product_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    product_code_snapshot: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    subtotal_amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    tax_type: Mapped[int] = mapped_column(Integer, nullable=False)
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    zero_tax_rate_reason: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=UTC)
    )

    invoice: Mapped[Invoice] = relationship(back_populates="lines")