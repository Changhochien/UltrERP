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
    LeadCreate,
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
    convert_lead_to_customer,
    create_lead,
    create_opportunity,
    create_quotation,
    create_quotation_revision,
    get_lead,
    get_opportunity,
    get_quotation,
    handoff_lead_to_opportunity,
    list_leads,
    list_opportunities,
    list_quotations,
    prepare_quotation_order_handoff,
    prepare_opportunity_quotation_handoff,
    transition_quotation_status,
    transition_opportunity_status,
    transition_lead_status,
    update_quotation,
    update_opportunity,
    update_lead,
)
from domains.customers.schemas import CustomerCreate

router = APIRouter()
opportunity_router = APIRouter()
quotation_router = APIRouter()

DbSession = Annotated[AsyncSession, Depends(get_db)]
ReadUser = Annotated[dict, Depends(require_role("admin", "sales"))]
WriteUser = Annotated[dict, Depends(require_role("admin", "sales"))]


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