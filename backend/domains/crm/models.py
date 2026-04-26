"""CRM SQLAlchemy models."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import JSON, Boolean, Date, DateTime, Index, Integer, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from common.database import Base


class CRMSettings(Base):
    __tablename__ = "crm_settings"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, unique=True, index=True)

    lead_duplicate_policy: Mapped[str] = mapped_column(String(20), nullable=False, default="block")
    contact_creation_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    default_quotation_validity_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    carry_forward_communications: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    carry_forward_comments: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    opportunity_auto_close_days: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(tz=UTC),
        onupdate=lambda: datetime.now(tz=UTC),
    )


class CRMSalesStage(Base):
    __tablename__ = "crm_sales_stages"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    probability: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
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

    __table_args__ = (
        Index("uq_crm_sales_stages_tenant_name", "tenant_id", "name", unique=True),
        Index("ix_crm_sales_stages_tenant_sort", "tenant_id", "sort_order"),
    )


class CRMTerritory(Base):
    __tablename__ = "crm_territories"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    is_group: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
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

    __table_args__ = (
        Index("uq_crm_territories_tenant_name", "tenant_id", "name", unique=True),
        Index("ix_crm_territories_tenant_sort", "tenant_id", "sort_order"),
    )


class CRMCustomerGroup(Base):
    __tablename__ = "crm_customer_groups"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    is_group: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
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

    __table_args__ = (
        Index("uq_crm_customer_groups_tenant_name", "tenant_id", "name", unique=True),
        Index("ix_crm_customer_groups_tenant_sort", "tenant_id", "sort_order"),
    )


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
    converted_opportunity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    converted_quotation_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    conversion_state: Mapped[str] = mapped_column(String(40), nullable=False, default="not_converted")
    conversion_path: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    converted_by: Mapped[str] = mapped_column(String(120), nullable=False, default="")
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


class Quotation(Base):
    __tablename__ = "crm_quotations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)

    quotation_to: Mapped[str] = mapped_column(String(20), nullable=False)
    party_name: Mapped[str] = mapped_column(String(200), nullable=False)
    party_label: Mapped[str] = mapped_column(String(200), nullable=False, default="")

    status: Mapped[str] = mapped_column(String(24), nullable=False, default="draft")
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    valid_till: Mapped[date] = mapped_column(Date, nullable=False)
    company: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="TWD")

    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    total_taxes: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    grand_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    base_grand_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))

    # Currency snapshot fields (Story 25-2)
    conversion_rate: Mapped[Decimal | None] = mapped_column(Numeric(20, 10), nullable=True, default=Decimal("1.0"))
    conversion_effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    applied_rate_source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    base_subtotal: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    base_total_taxes: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)

    # Commercial value source tracking (Story 25-4)
    currency_source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    payment_terms_source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ordered_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    order_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    contact_person: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    contact_email: Mapped[str] = mapped_column(String(254), nullable=False, default="")
    contact_mobile: Mapped[str] = mapped_column(String(30), nullable=False, default="")
    job_title: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    territory: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    customer_group: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    billing_address: Mapped[str] = mapped_column(Text, nullable=False, default="")
    shipping_address: Mapped[str] = mapped_column(Text, nullable=False, default="")

    utm_source: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    utm_medium: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    utm_campaign: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    utm_content: Mapped[str] = mapped_column(String(200), nullable=False, default="")

    items: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False, default=list)
    taxes: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False, default=list)
    terms_template: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    terms_and_conditions: Mapped[str] = mapped_column(Text, nullable=False, default="")
    opportunity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    amended_from: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    revision_no: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    lost_reason: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    competitor_name: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    loss_notes: Mapped[str] = mapped_column(Text, nullable=False, default="")

    auto_repeat_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    auto_repeat_frequency: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    auto_repeat_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")

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
        Index("ix_crm_quotations_tenant_status", "tenant_id", "status"),
        Index("ix_crm_quotations_tenant_party", "tenant_id", "quotation_to", "party_name"),
        Index("ix_crm_quotations_tenant_valid_till", "tenant_id", "valid_till"),
        Index("ix_crm_quotations_tenant_opportunity", "tenant_id", "opportunity_id"),
    )
