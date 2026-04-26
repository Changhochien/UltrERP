"""Customer SQLAlchemy model."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.database import Base

if TYPE_CHECKING:
    from common.models.payment_terms import PaymentTermsTemplate


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)

    company_name: Mapped[str] = mapped_column(String(200), nullable=False)
    normalized_business_number: Mapped[str] = mapped_column(String(8), nullable=False)

    billing_address: Mapped[str] = mapped_column(Text, nullable=False, default="")

    contact_name: Mapped[str] = mapped_column(String(100), nullable=False)
    contact_phone: Mapped[str] = mapped_column(String(30), nullable=False)
    contact_email: Mapped[str] = mapped_column(String(254), nullable=False)

    credit_limit: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    default_discount_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), nullable=False, default=Decimal("0.0000")
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    customer_type: Mapped[str] = mapped_column(String(20), nullable=False, default="unknown")
    legacy_master_snapshot: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    version: Mapped[int] = mapped_column(nullable=False, default=1)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(tz=UTC),
        onupdate=lambda: datetime.now(tz=UTC),
    )

    __table_args__ = (
        Index(
            "uq_customers_tenant_business_number",
            "tenant_id",
            "normalized_business_number",
            unique=True,
        ),
        Index("ix_customers_default_currency", "tenant_id", "default_currency_code"),
    )

    # Commercial profile defaults (Story 25-4)
    default_currency_code: Mapped[str | None] = mapped_column(String(3), nullable=True)
    payment_terms_template_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey(
            "payment_terms_templates.id",
            name="fk_customers_payment_terms_template",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    # Relationships
    payment_terms_template: Mapped[PaymentTermsTemplate | None] = relationship()
