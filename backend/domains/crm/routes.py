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
)
from domains.crm.service import (
    convert_lead_to_customer,
    create_lead,
    get_lead,
    handoff_lead_to_opportunity,
    list_leads,
    transition_lead_status,
    update_lead,
)
from domains.customers.schemas import CustomerCreate

router = APIRouter()

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