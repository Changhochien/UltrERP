"""CRM lead request and response schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
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
