"""CRM request and response schemas."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class LeadStatus(StrEnum):
    LEAD = "lead"
    OPEN = "open"
    REPLIED = "replied"
    OPPORTUNITY = "opportunity"
    QUOTATION = "quotation"
    LOST_QUOTATION = "lost_quotation"
    INTERESTED = "interested"
    CONVERTED = "converted"
    DO_NOT_CONTACT = "do_not_contact"


class LeadQualificationStatus(StrEnum):
    UNQUALIFIED = "unqualified"
    IN_PROCESS = "in_process"
    QUALIFIED = "qualified"


class LeadCreate(BaseModel):
    lead_name: str = Field(..., min_length=1, max_length=140)
    company_name: str = Field(default="", max_length=200)
    email_id: str = Field(default="", max_length=254)
    phone: str = Field(default="", max_length=30)
    mobile_no: str = Field(default="", max_length=30)
    territory: str = Field(default="", max_length=120)
    lead_owner: str = Field(default="", max_length=120)
    source: str = Field(default="", max_length=120)
    qualification_status: LeadQualificationStatus = LeadQualificationStatus.IN_PROCESS
    qualified_by: str = Field(default="", max_length=120)
    annual_revenue: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    no_of_employees: int | None = Field(default=None, ge=0)
    industry: str = Field(default="", max_length=120)
    market_segment: str = Field(default="", max_length=120)
    utm_source: str = Field(default="", max_length=120)
    utm_medium: str = Field(default="", max_length=120)
    utm_campaign: str = Field(default="", max_length=120)
    utm_content: str = Field(default="", max_length=200)
    notes: str = Field(default="", max_length=4000)


class LeadUpdate(BaseModel):
    lead_name: str | None = Field(default=None, min_length=1, max_length=140)
    company_name: str | None = Field(default=None, max_length=200)
    email_id: str | None = Field(default=None, max_length=254)
    phone: str | None = Field(default=None, max_length=30)
    mobile_no: str | None = Field(default=None, max_length=30)
    territory: str | None = Field(default=None, max_length=120)
    lead_owner: str | None = Field(default=None, max_length=120)
    source: str | None = Field(default=None, max_length=120)
    qualification_status: LeadQualificationStatus | None = None
    qualified_by: str | None = Field(default=None, max_length=120)
    annual_revenue: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    no_of_employees: int | None = Field(default=None, ge=0)
    industry: str | None = Field(default=None, max_length=120)
    market_segment: str | None = Field(default=None, max_length=120)
    utm_source: str | None = Field(default=None, max_length=120)
    utm_medium: str | None = Field(default=None, max_length=120)
    utm_campaign: str | None = Field(default=None, max_length=120)
    utm_content: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=4000)
    version: int = Field(..., ge=1)


class LeadTransition(BaseModel):
    status: LeadStatus


class LeadSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    lead_name: str
    company_name: str
    email_id: str
    phone: str
    mobile_no: str
    territory: str
    lead_owner: str
    source: str
    status: LeadStatus
    qualification_status: LeadQualificationStatus
    updated_at: datetime


class LeadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    lead_name: str
    company_name: str
    email_id: str
    phone: str
    mobile_no: str
    territory: str
    lead_owner: str
    source: str
    status: LeadStatus
    qualification_status: LeadQualificationStatus
    qualified_by: str
    annual_revenue: Decimal | None = None
    no_of_employees: int | None = None
    industry: str
    market_segment: str
    utm_source: str
    utm_medium: str
    utm_campaign: str
    utm_content: str
    notes: str
    converted_customer_id: uuid.UUID | None = None
    converted_at: datetime | None = None
    version: int
    created_at: datetime
    updated_at: datetime


class LeadListParams(BaseModel):
    q: str | None = Field(default=None, max_length=200)
    status: LeadStatus | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=500)


class LeadListResponse(BaseModel):
    items: list[LeadSummary]
    page: int
    page_size: int
    total_count: int
    total_pages: int


class LeadOpportunityHandoff(BaseModel):
    lead_id: uuid.UUID
    lead_name: str
    company_name: str
    email_id: str
    phone: str
    mobile_no: str
    territory: str
    lead_owner: str
    source: str
    qualification_status: LeadQualificationStatus
    utm_source: str
    utm_medium: str
    utm_campaign: str
    utm_content: str


class LeadCustomerConversionResult(BaseModel):
    lead_id: uuid.UUID
    customer_id: uuid.UUID
    status: LeadStatus


class OpportunityPartyKind(StrEnum):
    LEAD = "lead"
    CUSTOMER = "customer"
    PROSPECT = "prospect"


class OpportunityStatus(StrEnum):
    OPEN = "open"
    REPLIED = "replied"
    QUOTATION = "quotation"
    CONVERTED = "converted"
    CLOSED = "closed"
    LOST = "lost"


class OpportunityItemInput(BaseModel):
    item_name: str = Field(..., min_length=1, max_length=200)
    item_code: str = Field(default="", max_length=120)
    description: str = Field(default="", max_length=500)
    quantity: Decimal = Field(default=Decimal("1.00"), gt=0, max_digits=12, decimal_places=2)
    unit_price: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=12, decimal_places=2)
    amount: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)


class OpportunityItem(OpportunityItemInput):
    line_no: int = Field(..., ge=1)
    amount: Decimal = Field(..., ge=0, max_digits=14, decimal_places=2)


class OpportunityCreate(BaseModel):
    opportunity_title: str = Field(..., min_length=1, max_length=200)
    opportunity_from: OpportunityPartyKind
    party_name: str = Field(..., min_length=1, max_length=200)
    sales_stage: str = Field(default="qualification", max_length=120)
    probability: int = Field(default=0, ge=0, le=100)
    expected_closing: date | None = None
    currency: str = Field(default="TWD", min_length=3, max_length=3)
    opportunity_amount: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    opportunity_owner: str = Field(default="", max_length=120)
    territory: str = Field(default="", max_length=120)
    customer_group: str = Field(default="", max_length=120)
    contact_person: str = Field(default="", max_length=120)
    contact_email: str = Field(default="", max_length=254)
    contact_mobile: str = Field(default="", max_length=30)
    job_title: str = Field(default="", max_length=120)
    utm_source: str = Field(default="", max_length=120)
    utm_medium: str = Field(default="", max_length=120)
    utm_campaign: str = Field(default="", max_length=120)
    utm_content: str = Field(default="", max_length=200)
    items: list[OpportunityItemInput] = Field(default_factory=list)
    notes: str = Field(default="", max_length=4000)


class OpportunityUpdate(BaseModel):
    opportunity_title: str | None = Field(default=None, min_length=1, max_length=200)
    opportunity_from: OpportunityPartyKind | None = None
    party_name: str | None = Field(default=None, min_length=1, max_length=200)
    sales_stage: str | None = Field(default=None, max_length=120)
    probability: int | None = Field(default=None, ge=0, le=100)
    expected_closing: date | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    opportunity_amount: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    opportunity_owner: str | None = Field(default=None, max_length=120)
    territory: str | None = Field(default=None, max_length=120)
    customer_group: str | None = Field(default=None, max_length=120)
    contact_person: str | None = Field(default=None, max_length=120)
    contact_email: str | None = Field(default=None, max_length=254)
    contact_mobile: str | None = Field(default=None, max_length=30)
    job_title: str | None = Field(default=None, max_length=120)
    utm_source: str | None = Field(default=None, max_length=120)
    utm_medium: str | None = Field(default=None, max_length=120)
    utm_campaign: str | None = Field(default=None, max_length=120)
    utm_content: str | None = Field(default=None, max_length=200)
    items: list[OpportunityItemInput] | None = None
    notes: str | None = Field(default=None, max_length=4000)
    version: int = Field(..., ge=1)


class OpportunityTransition(BaseModel):
    status: OpportunityStatus
    lost_reason: str = Field(default="", max_length=200)
    competitor_name: str = Field(default="", max_length=200)
    loss_notes: str = Field(default="", max_length=4000)


class OpportunitySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    opportunity_title: str
    opportunity_from: OpportunityPartyKind
    party_name: str
    party_label: str
    status: OpportunityStatus
    sales_stage: str
    probability: int
    expected_closing: date | None = None
    currency: str
    opportunity_amount: Decimal | None = None
    opportunity_owner: str
    territory: str
    updated_at: datetime


class OpportunityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    opportunity_title: str
    opportunity_from: OpportunityPartyKind
    party_name: str
    party_label: str
    status: OpportunityStatus
    sales_stage: str
    probability: int
    expected_closing: date | None = None
    currency: str
    opportunity_amount: Decimal | None = None
    base_opportunity_amount: Decimal | None = None
    opportunity_owner: str
    territory: str
    customer_group: str
    contact_person: str
    contact_email: str
    contact_mobile: str
    job_title: str
    utm_source: str
    utm_medium: str
    utm_campaign: str
    utm_content: str
    items: list[OpportunityItem]
    notes: str
    lost_reason: str
    competitor_name: str
    loss_notes: str
    version: int
    created_at: datetime
    updated_at: datetime


class OpportunityListParams(BaseModel):
    q: str | None = Field(default=None, max_length=200)
    status: OpportunityStatus | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=500)


class OpportunityListResponse(BaseModel):
    items: list[OpportunitySummary]
    page: int
    page_size: int
    total_count: int
    total_pages: int


class OpportunityQuotationHandoff(BaseModel):
    opportunity_id: uuid.UUID
    opportunity_title: str
    opportunity_from: OpportunityPartyKind
    party_name: str
    party_label: str
    customer_group: str
    currency: str
    opportunity_amount: Decimal | None = None
    base_opportunity_amount: Decimal | None = None
    territory: str
    contact_person: str
    contact_email: str
    contact_mobile: str
    job_title: str
    utm_source: str
    utm_medium: str
    utm_campaign: str
    utm_content: str
    items: list[OpportunityItem]
