"""CRM SQLAlchemy models."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import JSON, Date, DateTime, Index, Integer, Numeric, String, Text, Uuid
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


class Opportunity(Base):
    __tablename__ = "crm_opportunities"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)

    opportunity_title: Mapped[str] = mapped_column(String(200), nullable=False)
    opportunity_from: Mapped[str] = mapped_column(String(20), nullable=False)
    party_name: Mapped[str] = mapped_column(String(200), nullable=False)
    party_label: Mapped[str] = mapped_column(String(200), nullable=False, default="")

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    sales_stage: Mapped[str] = mapped_column(String(120), nullable=False, default="qualification")
    probability: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expected_closing: Mapped[date | None] = mapped_column(Date, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="TWD")
    opportunity_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    base_opportunity_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)

    opportunity_owner: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    territory: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    customer_group: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    contact_person: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    contact_email: Mapped[str] = mapped_column(String(254), nullable=False, default="")
    contact_mobile: Mapped[str] = mapped_column(String(30), nullable=False, default="")
    job_title: Mapped[str] = mapped_column(String(120), nullable=False, default="")

    utm_source: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    utm_medium: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    utm_campaign: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    utm_content: Mapped[str] = mapped_column(String(200), nullable=False, default="")

    items: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False, default=list)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    lost_reason: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    competitor_name: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    loss_notes: Mapped[str] = mapped_column(Text, nullable=False, default="")

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
        Index("ix_crm_opportunities_tenant_status", "tenant_id", "status"),
        Index("ix_crm_opportunities_tenant_party", "tenant_id", "opportunity_from", "party_name"),
        Index("ix_crm_opportunities_tenant_expected_closing", "tenant_id", "expected_closing"),
    )
