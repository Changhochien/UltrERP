"""CRM lead SQLAlchemy models."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import DateTime, Index, Integer, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from common.database import Base


class Lead(Base):
    __tablename__ = "crm_leads"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)

    lead_name: Mapped[str] = mapped_column(String(140), nullable=False)
    company_name: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    normalized_company_name: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    email_id: Mapped[str] = mapped_column(String(254), nullable=False, default="")
    normalized_email_id: Mapped[str] = mapped_column(String(254), nullable=False, default="")
    phone: Mapped[str] = mapped_column(String(30), nullable=False, default="")
    mobile_no: Mapped[str] = mapped_column(String(30), nullable=False, default="")
    normalized_phone: Mapped[str] = mapped_column(String(30), nullable=False, default="")
    normalized_mobile_no: Mapped[str] = mapped_column(String(30), nullable=False, default="")

    territory: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    lead_owner: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    source: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="lead")
    qualification_status: Mapped[str] = mapped_column(String(40), nullable=False, default="in_process")
    qualified_by: Mapped[str] = mapped_column(String(120), nullable=False, default="")

    annual_revenue: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    no_of_employees: Mapped[int | None] = mapped_column(Integer, nullable=True)
    industry: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    market_segment: Mapped[str] = mapped_column(String(120), nullable=False, default="")

    utm_source: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    utm_medium: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    utm_campaign: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    utm_content: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")

    converted_customer_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    converted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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
        Index("ix_crm_leads_tenant_company", "tenant_id", "normalized_company_name"),
        Index("ix_crm_leads_tenant_email", "tenant_id", "normalized_email_id"),
        Index("ix_crm_leads_tenant_phone", "tenant_id", "normalized_phone"),
        Index("ix_crm_leads_tenant_mobile", "tenant_id", "normalized_mobile_no"),
    )
