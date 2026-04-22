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


class CRMDuplicatePolicy(StrEnum):
    BLOCK = "block"
    ALLOW = "allow"


class CRMSettingsResponse(BaseModel):
    lead_duplicate_policy: CRMDuplicatePolicy = CRMDuplicatePolicy.BLOCK
    contact_creation_enabled: bool = True
    default_quotation_validity_days: int = Field(default=30, ge=1, le=365)
    carry_forward_communications: bool = True
    carry_forward_comments: bool = True
    opportunity_auto_close_days: int | None = Field(default=None, ge=1, le=365)


class CRMSettingsUpdate(BaseModel):
    lead_duplicate_policy: CRMDuplicatePolicy | None = None
    contact_creation_enabled: bool | None = None
    default_quotation_validity_days: int | None = Field(default=None, ge=1, le=365)
    carry_forward_communications: bool | None = None
    carry_forward_comments: bool | None = None
    opportunity_auto_close_days: int | None = Field(default=None, ge=1, le=365)


class CRMSalesStageCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    probability: int = Field(default=0, ge=0, le=100)
    sort_order: int = Field(default=0, ge=0)
    is_active: bool = True


class CRMSalesStageUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    probability: int | None = Field(default=None, ge=0, le=100)
    sort_order: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


class CRMSalesStageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    probability: int
    sort_order: int
    is_active: bool


class CRMTerritoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    parent_id: uuid.UUID | None = None
    is_group: bool = False
    sort_order: int = Field(default=0, ge=0)
    is_active: bool = True


class CRMTerritoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    parent_id: uuid.UUID | None = None
    is_group: bool | None = None
    sort_order: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


class CRMTerritoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    parent_id: uuid.UUID | None = None
    is_group: bool
    sort_order: int
    is_active: bool


class CRMCustomerGroupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    parent_id: uuid.UUID | None = None
    is_group: bool = False
    sort_order: int = Field(default=0, ge=0)
    is_active: bool = True


class CRMCustomerGroupUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    parent_id: uuid.UUID | None = None
    is_group: bool | None = None
    sort_order: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


class CRMCustomerGroupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    parent_id: uuid.UUID | None = None
    is_group: bool
    sort_order: int
    is_active: bool


class CRMSetupBundleResponse(BaseModel):
    settings: CRMSettingsResponse
    sales_stages: list[CRMSalesStageResponse]
    territories: list[CRMTerritoryResponse]
    customer_groups: list[CRMCustomerGroupResponse]


class CRMPipelineScope(StrEnum):
    ALL = "all"
    OPEN = "open"
    TERMINAL = "terminal"


class CRMPipelineRecordType(StrEnum):
    ALL = "all"
    LEAD = "lead"
    OPPORTUNITY = "opportunity"
    QUOTATION = "quotation"


class CRMPipelineReportParams(BaseModel):
    record_type: CRMPipelineRecordType = CRMPipelineRecordType.ALL
    scope: CRMPipelineScope = CRMPipelineScope.ALL
    status: str | None = Field(default=None, max_length=40)
    sales_stage: str | None = Field(default=None, max_length=120)
    territory: str | None = Field(default=None, max_length=120)
    customer_group: str | None = Field(default=None, max_length=120)
    owner: str | None = Field(default=None, max_length=120)
    lost_reason: str | None = Field(default=None, max_length=200)
    utm_source: str | None = Field(default=None, max_length=120)
    utm_medium: str | None = Field(default=None, max_length=120)
    utm_campaign: str | None = Field(default=None, max_length=120)


class CRMPipelineSegment(BaseModel):
    record_type: str | None = None
    key: str
    label: str
    count: int
    amount: Decimal = Decimal("0.00")


class CRMPipelineTotals(BaseModel):
    lead_count: int = 0
    opportunity_count: int = 0
    quotation_count: int = 0
    open_count: int = 0
    terminal_count: int = 0
    open_pipeline_amount: Decimal = Decimal("0.00")
    terminal_pipeline_amount: Decimal = Decimal("0.00")


class CRMPipelineDropOff(BaseModel):
    lead_only_count: int = 0
    opportunity_without_quotation_count: int = 0
    quotation_without_order_count: int = 0
    quotation_with_order_count: int = 0


class CRMPipelineReportResponse(BaseModel):
    filters: CRMPipelineReportParams
    totals: CRMPipelineTotals
    by_status: list[CRMPipelineSegment]
    by_sales_stage: list[CRMPipelineSegment]
    by_territory: list[CRMPipelineSegment]
    by_customer_group: list[CRMPipelineSegment]
    by_owner: list[CRMPipelineSegment]
    by_lost_reason: list[CRMPipelineSegment]
    by_utm_source: list[CRMPipelineSegment]
    dropoff: CRMPipelineDropOff


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


QuotationPartyKind = OpportunityPartyKind
QuotationItemInput = OpportunityItemInput
QuotationItem = OpportunityItem


class QuotationOrderHandoffLine(BaseModel):
    source_quotation_line_no: int = Field(..., ge=1)
    product_id: uuid.UUID
    description: str = Field(..., min_length=1, max_length=500)
    quantity: Decimal = Field(..., gt=0, max_digits=18, decimal_places=3)
    list_unit_price: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=20, decimal_places=2)
    unit_price: Decimal = Field(..., ge=0, max_digits=20, decimal_places=2)
    discount_amount: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=20, decimal_places=2)
    tax_policy_code: str = Field(default="standard", min_length=1, max_length=20)


class QuotationOrderHandoff(BaseModel):
    quotation_id: uuid.UUID
    source_quotation_id: uuid.UUID
    customer_id: uuid.UUID
    crm_context_snapshot: dict[str, object] | None = None
    notes: str
    lines: list[QuotationOrderHandoffLine]


class QuotationLinkedOrder(BaseModel):
    order_id: uuid.UUID
    order_number: str
    status: str
    total_amount: Decimal | None = None
    linked_line_count: int = 0
    created_at: datetime


class QuotationRemainingItem(BaseModel):
    line_no: int
    item_name: str
    item_code: str
    description: str
    quoted_quantity: Decimal
    ordered_quantity: Decimal
    remaining_quantity: Decimal
    quoted_amount: Decimal
    ordered_amount: Decimal
    remaining_amount: Decimal


class QuotationStatus(StrEnum):
    DRAFT = "draft"
    OPEN = "open"
    REPLIED = "replied"
    PARTIALLY_ORDERED = "partially_ordered"
    ORDERED = "ordered"
    LOST = "lost"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class QuotationTaxInput(BaseModel):
    description: str = Field(..., min_length=1, max_length=200)
    rate: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=7, decimal_places=2)
    tax_amount: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)


class QuotationTax(QuotationTaxInput):
    line_no: int = Field(..., ge=1)
    tax_amount: Decimal = Field(..., ge=0, max_digits=14, decimal_places=2)


class QuotationCreate(BaseModel):
    quotation_to: QuotationPartyKind
    party_name: str = Field(..., min_length=1, max_length=200)
    transaction_date: date
    valid_till: date | None = None
    company: str = Field(..., min_length=1, max_length=200)
    currency: str = Field(default="TWD", min_length=3, max_length=3)
    contact_person: str = Field(default="", max_length=120)
    contact_email: str = Field(default="", max_length=254)
    contact_mobile: str = Field(default="", max_length=30)
    job_title: str = Field(default="", max_length=120)
    territory: str = Field(default="", max_length=120)
    customer_group: str = Field(default="", max_length=120)
    billing_address: str = Field(default="", max_length=4000)
    shipping_address: str = Field(default="", max_length=4000)
    utm_source: str = Field(default="", max_length=120)
    utm_medium: str = Field(default="", max_length=120)
    utm_campaign: str = Field(default="", max_length=120)
    utm_content: str = Field(default="", max_length=200)
    opportunity_id: uuid.UUID | None = None
    items: list[QuotationItemInput] = Field(default_factory=list)
    taxes: list[QuotationTaxInput] = Field(default_factory=list)
    terms_template: str = Field(default="", max_length=200)
    terms_and_conditions: str = Field(default="", max_length=4000)
    auto_repeat_enabled: bool = False
    auto_repeat_frequency: str = Field(default="", max_length=40)
    auto_repeat_until: date | None = None
    notes: str = Field(default="", max_length=4000)


class QuotationRevisionCreate(BaseModel):
    quotation_to: QuotationPartyKind | None = None
    party_name: str | None = Field(default=None, min_length=1, max_length=200)
    transaction_date: date | None = None
    valid_till: date | None = None
    company: str | None = Field(default=None, min_length=1, max_length=200)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    contact_person: str | None = Field(default=None, max_length=120)
    contact_email: str | None = Field(default=None, max_length=254)
    contact_mobile: str | None = Field(default=None, max_length=30)
    job_title: str | None = Field(default=None, max_length=120)
    territory: str | None = Field(default=None, max_length=120)
    customer_group: str | None = Field(default=None, max_length=120)
    billing_address: str | None = Field(default=None, max_length=4000)
    shipping_address: str | None = Field(default=None, max_length=4000)
    utm_source: str | None = Field(default=None, max_length=120)
    utm_medium: str | None = Field(default=None, max_length=120)
    utm_campaign: str | None = Field(default=None, max_length=120)
    utm_content: str | None = Field(default=None, max_length=200)
    opportunity_id: uuid.UUID | None = None
    items: list[QuotationItemInput] | None = None
    taxes: list[QuotationTaxInput] | None = None
    terms_template: str | None = Field(default=None, max_length=200)
    terms_and_conditions: str | None = Field(default=None, max_length=4000)
    auto_repeat_enabled: bool | None = None
    auto_repeat_frequency: str | None = Field(default=None, max_length=40)
    auto_repeat_until: date | None = None
    notes: str | None = Field(default=None, max_length=4000)


class QuotationUpdate(QuotationRevisionCreate):
    version: int = Field(..., ge=1)


class QuotationTransition(BaseModel):
    status: QuotationStatus
    lost_reason: str = Field(default="", max_length=200)
    competitor_name: str = Field(default="", max_length=200)
    loss_notes: str = Field(default="", max_length=4000)


class QuotationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    quotation_to: QuotationPartyKind
    party_name: str
    party_label: str
    status: QuotationStatus
    transaction_date: date
    valid_till: date
    company: str
    currency: str
    grand_total: Decimal
    ordered_amount: Decimal = Decimal("0.00")
    order_count: int = 0
    opportunity_id: uuid.UUID | None = None
    amended_from: uuid.UUID | None = None
    revision_no: int
    updated_at: datetime


class QuotationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    quotation_to: QuotationPartyKind
    party_name: str
    party_label: str
    status: QuotationStatus
    transaction_date: date
    valid_till: date
    company: str
    currency: str
    subtotal: Decimal
    total_taxes: Decimal
    grand_total: Decimal
    base_grand_total: Decimal
    ordered_amount: Decimal
    order_count: int
    contact_person: str
    contact_email: str
    contact_mobile: str
    job_title: str
    territory: str
    customer_group: str
    billing_address: str
    shipping_address: str
    utm_source: str
    utm_medium: str
    utm_campaign: str
    utm_content: str
    items: list[QuotationItem]
    taxes: list[QuotationTax]
    terms_template: str
    terms_and_conditions: str
    opportunity_id: uuid.UUID | None = None
    amended_from: uuid.UUID | None = None
    revision_no: int
    lost_reason: str
    competitor_name: str
    loss_notes: str
    auto_repeat_enabled: bool
    auto_repeat_frequency: str
    auto_repeat_until: date | None = None
    notes: str
    version: int
    created_at: datetime
    updated_at: datetime
    linked_orders: list[QuotationLinkedOrder] = Field(default_factory=list)
    remaining_items: list[QuotationRemainingItem] = Field(default_factory=list)


class QuotationListParams(BaseModel):
    q: str | None = Field(default=None, max_length=200)
    status: QuotationStatus | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=500)


class QuotationListResponse(BaseModel):
    items: list[QuotationSummary]
    page: int
    page_size: int
    total_count: int
    total_pages: int
