"""CRM lead API routes."""

from __future__ import annotations

import math
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from common.auth import require_role
from common.database import get_db
from common.errors import (
    DuplicateLeadConflictError,
    ValidationError,
    VersionConflictError,
    duplicate_lead_response,
    error_response,
)
from domains.crm.schemas import (
    CRMCustomerGroupCreate,
    CRMCustomerGroupResponse,
    CRMCustomerGroupUpdate,
    CRMPipelineReportParams,
    CRMPipelineReportResponse,
    CRMSettingsResponse,
    CRMSettingsUpdate,
    CRMSalesStageCreate,
    CRMSalesStageResponse,
    CRMSalesStageUpdate,
    CRMSetupBundleResponse,
    CRMTerritoryCreate,
    CRMTerritoryResponse,
    CRMTerritoryUpdate,
    LeadCreate,
    LeadConversionRequest,
    LeadConversionResult,
    LeadCustomerConversionResult,
    LeadListParams,
    LeadListResponse,
    LeadOpportunityHandoff,
    LeadResponse,
    LeadSummary,
    LeadTransition,
    LeadUpdate,
    OpportunityCreate,
    OpportunityListParams,
    OpportunityListResponse,
    OpportunityQuotationHandoff,
    OpportunityResponse,
    OpportunitySummary,
    OpportunityTransition,
    OpportunityUpdate,
    QuotationCreate,
    QuotationOrderHandoff,
    QuotationListParams,
    QuotationListResponse,
    QuotationResponse,
    QuotationRevisionCreate,
    QuotationSummary,
    QuotationTransition,
    QuotationUpdate,
)
from domains.crm.service import (
    create_customer_group,
    convert_lead,
    convert_lead_to_customer,
    create_lead,
    create_opportunity,
    create_quotation,
    create_quotation_revision,
    create_sales_stage,
    create_territory,
    get_crm_pipeline_report,
    get_lead,
    get_crm_setup_bundle,
    get_opportunity,
    get_quotation,
    get_crm_settings,
    handoff_lead_to_opportunity,
    list_customer_groups,
    list_leads,
    list_opportunities,
    list_quotations,
    list_sales_stages,
    list_territories,
    prepare_quotation_order_handoff,
    prepare_opportunity_quotation_handoff,
    transition_quotation_status,
    transition_opportunity_status,
    transition_lead_status,
    update_customer_group,
    update_crm_settings,
    update_quotation,
    update_opportunity,
    update_sales_stage,
    update_territory,
    update_lead,
)
from domains.customers.schemas import CustomerCreate

router = APIRouter()
opportunity_router = APIRouter()
quotation_router = APIRouter()
settings_router = APIRouter()
setup_router = APIRouter()
reporting_router = APIRouter()

DbSession = Annotated[AsyncSession, Depends(get_db)]
ReadUser = Annotated[dict, Depends(require_role("admin", "sales"))]
WriteUser = Annotated[dict, Depends(require_role("admin", "sales"))]
AdminUser = Annotated[dict, Depends(require_role("admin"))]


@settings_router.get("", response_model=CRMSettingsResponse)
async def get_settings(
    session: DbSession,
    user: ReadUser,
) -> CRMSettingsResponse:
    real_tid = uuid.UUID(user["tenant_id"])
    return await get_crm_settings(session, tenant_id=real_tid)


@settings_router.patch("", response_model=CRMSettingsResponse)
async def update_settings(
    data: CRMSettingsUpdate,
    session: DbSession,
    user: AdminUser,
) -> CRMSettingsResponse:
    real_tid = uuid.UUID(user["tenant_id"])
    return await update_crm_settings(session, data, tenant_id=real_tid)


@setup_router.get("", response_model=CRMSetupBundleResponse)
async def get_setup_bundle(
    session: DbSession,
    user: ReadUser,
) -> CRMSetupBundleResponse:
    real_tid = uuid.UUID(user["tenant_id"])
    return await get_crm_setup_bundle(session, tenant_id=real_tid)


@setup_router.get("/sales-stages", response_model=list[CRMSalesStageResponse])
async def get_sales_stages(
    session: DbSession,
    user: ReadUser,
) -> list[CRMSalesStageResponse]:
    real_tid = uuid.UUID(user["tenant_id"])
    items = await list_sales_stages(session, tenant_id=real_tid)
    return [CRMSalesStageResponse.model_validate(item) for item in items]


@setup_router.post("/sales-stages", response_model=CRMSalesStageResponse, status_code=status.HTTP_201_CREATED)
async def create_sales_stage_route(
    data: CRMSalesStageCreate,
    session: DbSession,
    user: AdminUser,
) -> CRMSalesStageResponse | JSONResponse:
    real_tid = uuid.UUID(user["tenant_id"])
    try:
        stage = await create_sales_stage(session, data, tenant_id=real_tid)
        return CRMSalesStageResponse.model_validate(stage)
    except ValidationError as exc:
        return JSONResponse(status_code=422, content=error_response(exc.errors))


@setup_router.patch("/sales-stages/{stage_id}", response_model=CRMSalesStageResponse)
async def update_sales_stage_route(
    stage_id: uuid.UUID,
    data: CRMSalesStageUpdate,
    session: DbSession,
    user: AdminUser,
) -> CRMSalesStageResponse | JSONResponse:
    real_tid = uuid.UUID(user["tenant_id"])
    try:
        stage = await update_sales_stage(session, stage_id, data, tenant_id=real_tid)
        if stage is None:
            return JSONResponse(status_code=404, content={"detail": "Sales stage not found."})
        return CRMSalesStageResponse.model_validate(stage)
    except ValidationError as exc:
        return JSONResponse(status_code=422, content=error_response(exc.errors))


@setup_router.get("/territories", response_model=list[CRMTerritoryResponse])
async def get_territories(
    session: DbSession,
    user: ReadUser,
) -> list[CRMTerritoryResponse]:
    real_tid = uuid.UUID(user["tenant_id"])
    items = await list_territories(session, tenant_id=real_tid)
    return [CRMTerritoryResponse.model_validate(item) for item in items]


@setup_router.post("/territories", response_model=CRMTerritoryResponse, status_code=status.HTTP_201_CREATED)
async def create_territory_route(
    data: CRMTerritoryCreate,
    session: DbSession,
    user: AdminUser,
) -> CRMTerritoryResponse | JSONResponse:
    real_tid = uuid.UUID(user["tenant_id"])
    try:
        territory = await create_territory(session, data, tenant_id=real_tid)
        return CRMTerritoryResponse.model_validate(territory)
    except ValidationError as exc:
        return JSONResponse(status_code=422, content=error_response(exc.errors))


@setup_router.patch("/territories/{territory_id}", response_model=CRMTerritoryResponse)
async def update_territory_route(
    territory_id: uuid.UUID,
    data: CRMTerritoryUpdate,
    session: DbSession,
    user: AdminUser,
) -> CRMTerritoryResponse | JSONResponse:
    real_tid = uuid.UUID(user["tenant_id"])
    try:
        territory = await update_territory(session, territory_id, data, tenant_id=real_tid)
        if territory is None:
            return JSONResponse(status_code=404, content={"detail": "Territory not found."})
        return CRMTerritoryResponse.model_validate(territory)
    except ValidationError as exc:
        return JSONResponse(status_code=422, content=error_response(exc.errors))


@setup_router.get("/customer-groups", response_model=list[CRMCustomerGroupResponse])
async def get_customer_groups(
    session: DbSession,
    user: ReadUser,
) -> list[CRMCustomerGroupResponse]:
    real_tid = uuid.UUID(user["tenant_id"])
    items = await list_customer_groups(session, tenant_id=real_tid)
    return [CRMCustomerGroupResponse.model_validate(item) for item in items]


@setup_router.post("/customer-groups", response_model=CRMCustomerGroupResponse, status_code=status.HTTP_201_CREATED)
async def create_customer_group_route(
    data: CRMCustomerGroupCreate,
    session: DbSession,
    user: AdminUser,
) -> CRMCustomerGroupResponse | JSONResponse:
    real_tid = uuid.UUID(user["tenant_id"])
    try:
        customer_group = await create_customer_group(session, data, tenant_id=real_tid)
        return CRMCustomerGroupResponse.model_validate(customer_group)
    except ValidationError as exc:
        return JSONResponse(status_code=422, content=error_response(exc.errors))


@setup_router.patch("/customer-groups/{customer_group_id}", response_model=CRMCustomerGroupResponse)
async def update_customer_group_route(
    customer_group_id: uuid.UUID,
    data: CRMCustomerGroupUpdate,
    session: DbSession,
    user: AdminUser,
) -> CRMCustomerGroupResponse | JSONResponse:
    real_tid = uuid.UUID(user["tenant_id"])
    try:
        customer_group = await update_customer_group(session, customer_group_id, data, tenant_id=real_tid)
        if customer_group is None:
            return JSONResponse(status_code=404, content={"detail": "Customer group not found."})
        return CRMCustomerGroupResponse.model_validate(customer_group)
    except ValidationError as exc:
        return JSONResponse(status_code=422, content=error_response(exc.errors))


@reporting_router.get("/pipeline", response_model=CRMPipelineReportResponse)
async def get_pipeline_report(
    session: DbSession,
    user: ReadUser,
    record_type: str = Query(default="all", max_length=20),
    scope: str = Query(default="all", max_length=20),
    status_filter: str | None = Query(default=None, alias="status", max_length=40),
    sales_stage: str | None = Query(default=None, max_length=120),
    territory: str | None = Query(default=None, max_length=120),
    customer_group: str | None = Query(default=None, max_length=120),
    owner: str | None = Query(default=None, max_length=120),
    lost_reason: str | None = Query(default=None, max_length=200),
    utm_source: str | None = Query(default=None, max_length=120),
    utm_medium: str | None = Query(default=None, max_length=120),
    utm_campaign: str | None = Query(default=None, max_length=120),
) -> CRMPipelineReportResponse:
    real_tid = uuid.UUID(user["tenant_id"])
    params = CRMPipelineReportParams(
        record_type=record_type,
        scope=scope,
        status=status_filter,
        sales_stage=sales_stage,
        territory=territory,
        customer_group=customer_group,
        owner=owner,
        lost_reason=lost_reason,
        utm_source=utm_source,
        utm_medium=utm_medium,
        utm_campaign=utm_campaign,
    )
    return await get_crm_pipeline_report(session, params, tenant_id=real_tid)


@router.get("", response_model=LeadListResponse)
async def list_all(
    session: DbSession,
    user: ReadUser,
    q: str | None = Query(default=None, max_length=200),
    status_filter: str | None = Query(default=None, alias="status", max_length=40),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=500),
) -> LeadListResponse:
    real_tid = uuid.UUID(user["tenant_id"])
    params = LeadListParams(q=q, status=status_filter, page=page, page_size=page_size)
    items, total_count = await list_leads(session, params, tenant_id=real_tid)
    total_pages = max(1, math.ceil(total_count / page_size))
    return LeadListResponse(
        items=[LeadSummary.model_validate(item) for item in items],
        page=page,
        page_size=page_size,
        total_count=total_count,
        total_pages=total_pages,
    )


@router.get("/{lead_id}", response_model=LeadResponse)
async def get_by_id(
    lead_id: uuid.UUID,
    session: DbSession,
    user: ReadUser,
) -> LeadResponse | JSONResponse:
    real_tid = uuid.UUID(user["tenant_id"])
    lead = await get_lead(session, lead_id, tenant_id=real_tid)
    if lead is None:
        return JSONResponse(status_code=404, content={"detail": "Lead not found."})
    return LeadResponse.model_validate(lead)


@router.post("", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
async def create(
    data: LeadCreate,
    session: DbSession,
    user: WriteUser,
) -> LeadResponse | JSONResponse:
    real_tid = uuid.UUID(user["tenant_id"])
    try:
        lead = await create_lead(session, data, tenant_id=real_tid)
        return LeadResponse.model_validate(lead)
    except DuplicateLeadConflictError as exc:
        return JSONResponse(status_code=409, content=duplicate_lead_response(exc))
    except ValidationError as exc:
        return JSONResponse(status_code=422, content=error_response(exc.errors))


@router.patch("/{lead_id}", response_model=LeadResponse)
async def update(
    lead_id: uuid.UUID,
    data: LeadUpdate,
    session: DbSession,
    user: WriteUser,
) -> LeadResponse | JSONResponse:
    real_tid = uuid.UUID(user["tenant_id"])
    try:
        lead = await update_lead(session, lead_id, data, tenant_id=real_tid)
        if lead is None:
            return JSONResponse(status_code=404, content={"detail": "Lead not found."})
        return LeadResponse.model_validate(lead)
    except VersionConflictError as exc:
        return JSONResponse(
            status_code=409,
            content={
                "error": "version_conflict",
                "expected_version": exc.expected,
                "actual_version": exc.actual,
            },
        )
    except DuplicateLeadConflictError as exc:
        return JSONResponse(status_code=409, content=duplicate_lead_response(exc))
    except ValidationError as exc:
        return JSONResponse(status_code=422, content=error_response(exc.errors))


@router.post("/{lead_id}/status", response_model=LeadResponse)
async def transition_status(
    lead_id: uuid.UUID,
    data: LeadTransition,
    session: DbSession,
    user: WriteUser,
) -> LeadResponse | JSONResponse:
    real_tid = uuid.UUID(user["tenant_id"])
    try:
        lead = await transition_lead_status(session, lead_id, data.status, tenant_id=real_tid)
        if lead is None:
            return JSONResponse(status_code=404, content={"detail": "Lead not found."})
        return LeadResponse.model_validate(lead)
    except ValidationError as exc:
        return JSONResponse(status_code=422, content=error_response(exc.errors))


@router.post("/{lead_id}/handoff/opportunity", response_model=LeadOpportunityHandoff)
async def handoff_to_opportunity(
    lead_id: uuid.UUID,
    session: DbSession,
    user: WriteUser,
) -> LeadOpportunityHandoff | JSONResponse:
    real_tid = uuid.UUID(user["tenant_id"])
    try:
        return await handoff_lead_to_opportunity(session, lead_id, tenant_id=real_tid)
    except ValidationError as exc:
        errors = error_response(exc.errors)
        status_code = 404 if any(error.get("field") == "lead_id" for error in exc.errors) else 422
        return JSONResponse(status_code=status_code, content=errors)


@router.post("/{lead_id}/convert/customer", response_model=LeadCustomerConversionResult)
async def convert_to_customer(
    lead_id: uuid.UUID,
    data: CustomerCreate,
    session: DbSession,
    user: WriteUser,
) -> LeadCustomerConversionResult | JSONResponse:
    real_tid = uuid.UUID(user["tenant_id"])
    try:
        return await convert_lead_to_customer(session, lead_id, data, tenant_id=real_tid)
    except DuplicateLeadConflictError as exc:
        return JSONResponse(status_code=409, content=duplicate_lead_response(exc))
    except ValidationError as exc:
        errors = error_response(exc.errors)
        status_code = 404 if any(error.get("field") == "lead_id" for error in exc.errors) else 422
        return JSONResponse(status_code=status_code, content=errors)


@router.post("/{lead_id}/convert", response_model=LeadConversionResult)
async def convert_lead_records(
    lead_id: uuid.UUID,
    data: LeadConversionRequest,
    session: DbSession,
    user: WriteUser,
) -> LeadConversionResult | JSONResponse:
    real_tid = uuid.UUID(user["tenant_id"])
    try:
        return await convert_lead(
            session,
            lead_id,
            data,
            tenant_id=real_tid,
            converted_by=str(user.get("sub") or ""),
        )
    except ValidationError as exc:
        errors = error_response(exc.errors)
        status_code = 404 if any(error.get("field") == "lead_id" for error in exc.errors) else 422
        return JSONResponse(status_code=status_code, content=errors)


@opportunity_router.get("", response_model=OpportunityListResponse)
async def list_all_opportunities(
    session: DbSession,
    user: ReadUser,
    q: str | None = Query(default=None, max_length=200),
    status_filter: str | None = Query(default=None, alias="status", max_length=20),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=500),
) -> OpportunityListResponse:
    real_tid = uuid.UUID(user["tenant_id"])
    params = OpportunityListParams(q=q, status=status_filter, page=page, page_size=page_size)
    items, total_count = await list_opportunities(session, params, tenant_id=real_tid)
    total_pages = max(1, math.ceil(total_count / page_size))
    return OpportunityListResponse(
        items=[OpportunitySummary.model_validate(item) for item in items],
        page=page,
        page_size=page_size,
        total_count=total_count,
        total_pages=total_pages,
    )


@opportunity_router.get("/{opportunity_id}", response_model=OpportunityResponse)
async def get_opportunity_by_id(
    opportunity_id: uuid.UUID,
    session: DbSession,
    user: ReadUser,
) -> OpportunityResponse | JSONResponse:
    real_tid = uuid.UUID(user["tenant_id"])
    opportunity = await get_opportunity(session, opportunity_id, tenant_id=real_tid)
    if opportunity is None:
        return JSONResponse(status_code=404, content={"detail": "Opportunity not found."})
    return OpportunityResponse.model_validate(opportunity)


@opportunity_router.post("", response_model=OpportunityResponse, status_code=status.HTTP_201_CREATED)
async def create_new_opportunity(
    data: OpportunityCreate,
    session: DbSession,
    user: WriteUser,
) -> OpportunityResponse | JSONResponse:
    real_tid = uuid.UUID(user["tenant_id"])
    try:
        opportunity = await create_opportunity(session, data, tenant_id=real_tid)
        return OpportunityResponse.model_validate(opportunity)
    except ValidationError as exc:
        return JSONResponse(status_code=422, content=error_response(exc.errors))


@opportunity_router.patch("/{opportunity_id}", response_model=OpportunityResponse)
async def update_existing_opportunity(
    opportunity_id: uuid.UUID,
    data: OpportunityUpdate,
    session: DbSession,
    user: WriteUser,
) -> OpportunityResponse | JSONResponse:
    real_tid = uuid.UUID(user["tenant_id"])
    try:
        opportunity = await update_opportunity(session, opportunity_id, data, tenant_id=real_tid)
        if opportunity is None:
            return JSONResponse(status_code=404, content={"detail": "Opportunity not found."})
        return OpportunityResponse.model_validate(opportunity)
    except VersionConflictError as exc:
        return JSONResponse(
            status_code=409,
            content={
                "error": "version_conflict",
                "expected_version": exc.expected,
                "actual_version": exc.actual,
            },
        )
    except ValidationError as exc:
        return JSONResponse(status_code=422, content=error_response(exc.errors))


@opportunity_router.post("/{opportunity_id}/status", response_model=OpportunityResponse)
async def transition_opportunity(
    opportunity_id: uuid.UUID,
    data: OpportunityTransition,
    session: DbSession,
    user: WriteUser,
) -> OpportunityResponse | JSONResponse:
    real_tid = uuid.UUID(user["tenant_id"])
    try:
        opportunity = await transition_opportunity_status(session, opportunity_id, data, tenant_id=real_tid)
        if opportunity is None:
            return JSONResponse(status_code=404, content={"detail": "Opportunity not found."})
        return OpportunityResponse.model_validate(opportunity)
    except ValidationError as exc:
        return JSONResponse(status_code=422, content=error_response(exc.errors))


@opportunity_router.post("/{opportunity_id}/handoff/quotation", response_model=OpportunityQuotationHandoff)
async def handoff_opportunity_to_quotation(
    opportunity_id: uuid.UUID,
    session: DbSession,
    user: WriteUser,
) -> OpportunityQuotationHandoff | JSONResponse:
    real_tid = uuid.UUID(user["tenant_id"])
    try:
        return await prepare_opportunity_quotation_handoff(session, opportunity_id, tenant_id=real_tid)
    except ValidationError as exc:
        errors = error_response(exc.errors)
        status_code = 404 if any(error.get("field") == "opportunity_id" for error in exc.errors) else 422
        return JSONResponse(status_code=status_code, content=errors)


@quotation_router.get("", response_model=QuotationListResponse)
async def list_all_quotations(
    session: DbSession,
    user: ReadUser,
    q: str | None = Query(default=None, max_length=200),
    status_filter: str | None = Query(default=None, alias="status", max_length=24),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=500),
) -> QuotationListResponse:
    real_tid = uuid.UUID(user["tenant_id"])
    params = QuotationListParams(q=q, status=status_filter, page=page, page_size=page_size)
    items, total_count = await list_quotations(session, params, tenant_id=real_tid)
    total_pages = max(1, math.ceil(total_count / page_size))
    return QuotationListResponse(
        items=[QuotationSummary.model_validate(item) for item in items],
        page=page,
        page_size=page_size,
        total_count=total_count,
        total_pages=total_pages,
    )


@quotation_router.get("/{quotation_id}", response_model=QuotationResponse)
async def get_quotation_by_id(
    quotation_id: uuid.UUID,
    session: DbSession,
    user: ReadUser,
) -> QuotationResponse | JSONResponse:
    real_tid = uuid.UUID(user["tenant_id"])
    quotation = await get_quotation(session, quotation_id, tenant_id=real_tid)
    if quotation is None:
        return JSONResponse(status_code=404, content={"detail": "Quotation not found."})
    return QuotationResponse.model_validate(quotation)


@quotation_router.post("/{quotation_id}/handoff/order", response_model=QuotationOrderHandoff)
async def handoff_quotation_to_order(
    quotation_id: uuid.UUID,
    session: DbSession,
    user: WriteUser,
) -> QuotationOrderHandoff | JSONResponse:
    real_tid = uuid.UUID(user["tenant_id"])
    try:
        return await prepare_quotation_order_handoff(session, quotation_id, tenant_id=real_tid)
    except ValidationError as exc:
        errors = error_response(exc.errors)
        status_code = 404 if any(error.get("field") == "quotation_id" for error in exc.errors) else 422
        return JSONResponse(status_code=status_code, content=errors)


@quotation_router.post("", response_model=QuotationResponse, status_code=status.HTTP_201_CREATED)
async def create_new_quotation(
    data: QuotationCreate,
    session: DbSession,
    user: WriteUser,
) -> QuotationResponse | JSONResponse:
    real_tid = uuid.UUID(user["tenant_id"])
    try:
        quotation = await create_quotation(session, data, tenant_id=real_tid)
        return QuotationResponse.model_validate(quotation)
    except ValidationError as exc:
        return JSONResponse(status_code=422, content=error_response(exc.errors))


@quotation_router.patch("/{quotation_id}", response_model=QuotationResponse)
async def update_existing_quotation(
    quotation_id: uuid.UUID,
    data: QuotationUpdate,
    session: DbSession,
    user: WriteUser,
) -> QuotationResponse | JSONResponse:
    real_tid = uuid.UUID(user["tenant_id"])
    try:
        quotation = await update_quotation(session, quotation_id, data, tenant_id=real_tid)
        if quotation is None:
            return JSONResponse(status_code=404, content={"detail": "Quotation not found."})
        return QuotationResponse.model_validate(quotation)
    except VersionConflictError as exc:
        return JSONResponse(
            status_code=409,
            content={
                "error": "version_conflict",
                "expected_version": exc.expected,
                "actual_version": exc.actual,
            },
        )
    except ValidationError as exc:
        return JSONResponse(status_code=422, content=error_response(exc.errors))


@quotation_router.post("/{quotation_id}/status", response_model=QuotationResponse)
async def transition_quotation(
    quotation_id: uuid.UUID,
    data: QuotationTransition,
    session: DbSession,
    user: WriteUser,
) -> QuotationResponse | JSONResponse:
    real_tid = uuid.UUID(user["tenant_id"])
    try:
        quotation = await transition_quotation_status(session, quotation_id, data, tenant_id=real_tid)
        if quotation is None:
            return JSONResponse(status_code=404, content={"detail": "Quotation not found."})
        return QuotationResponse.model_validate(quotation)
    except ValidationError as exc:
        return JSONResponse(status_code=422, content=error_response(exc.errors))


@quotation_router.post("/{quotation_id}/revise", response_model=QuotationResponse, status_code=status.HTTP_201_CREATED)
async def revise_quotation(
    quotation_id: uuid.UUID,
    data: QuotationRevisionCreate,
    session: DbSession,
    user: WriteUser,
) -> QuotationResponse | JSONResponse:
    real_tid = uuid.UUID(user["tenant_id"])
    try:
        quotation = await create_quotation_revision(session, quotation_id, data, tenant_id=real_tid)
        if quotation is None:
            return JSONResponse(status_code=404, content={"detail": "Quotation not found."})
        return QuotationResponse.model_validate(quotation)
    except ValidationError as exc:
        errors = error_response(exc.errors)
        status_code = 404 if any(error.get("field") == "quotation_id" for error in exc.errors) else 422
        return JSONResponse(status_code=status_code, content=errors)