"""Customer API routes."""

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
    DuplicateBusinessNumberError,
    ValidationError,
    VersionConflictError,
    duplicate_response,
    error_response,
)
from domains.customers.schemas import (
    CustomerCreate,
    CustomerListParams,
    CustomerListResponse,
    CustomerOutstandingSummary,
    CustomerResponse,
    CustomerSummary,
    CustomerUpdate,
)
from domains.customers.service import (
    create_customer,
    get_customer,
    list_customers,
    lookup_customer_by_ban,
    update_customer,
)

router = APIRouter()

DbSession = Annotated[AsyncSession, Depends(get_db)]
ReadUser = Annotated[dict, Depends(require_role("admin", "finance", "sales"))]
WriteUser = Annotated[dict, Depends(require_role("admin", "sales"))]


@router.get("", response_model=CustomerListResponse)
async def list_all(
    session: DbSession,
    _user: ReadUser,
    q: str | None = Query(default=None, max_length=200),
    customer_status: str | None = Query(default=None, alias="status", max_length=20),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> CustomerListResponse:
    params = CustomerListParams(q=q, status=customer_status, page=page, page_size=page_size)
    items, total_count = await list_customers(session, params)
    total_pages = max(1, math.ceil(total_count / page_size))
    return CustomerListResponse(
        items=[CustomerSummary.model_validate(c) for c in items],
        page=page,
        page_size=page_size,
        total_count=total_count,
        total_pages=total_pages,
    )


@router.get("/lookup", response_model=CustomerResponse | None)
async def lookup_by_ban(
    session: DbSession,
    _user: ReadUser,
    business_number: str = Query(..., min_length=1, max_length=20),
) -> CustomerResponse | JSONResponse:
    customer = await lookup_customer_by_ban(session, business_number)
    if customer is None:
        return JSONResponse(status_code=404, content={"detail": "Customer not found."})
    return CustomerResponse.model_validate(customer)


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_by_id(
    session: DbSession,
    _user: ReadUser,
    customer_id: uuid.UUID,
) -> CustomerResponse | JSONResponse:
    customer = await get_customer(session, customer_id)
    if customer is None:
        return JSONResponse(status_code=404, content={"detail": "Customer not found."})
    return CustomerResponse.model_validate(customer)


@router.post(
    "",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create(
    data: CustomerCreate, session: DbSession, _user: WriteUser
) -> CustomerResponse | JSONResponse:
    try:
        customer = await create_customer(session, data)
        return CustomerResponse.model_validate(customer)
    except DuplicateBusinessNumberError as exc:
        return JSONResponse(
            status_code=409,
            content=duplicate_response(exc),
        )
    except ValidationError as exc:
        return JSONResponse(
            status_code=422,
            content=error_response(exc.errors),
        )


@router.patch("/{customer_id}", response_model=CustomerResponse)
async def update(
    customer_id: uuid.UUID,
    data: CustomerUpdate,
    session: DbSession,
    _user: WriteUser,
) -> CustomerResponse | JSONResponse:
    try:
        customer = await update_customer(session, customer_id, data)
        if customer is None:
            return JSONResponse(status_code=404, content={"detail": "Customer not found."})
        return CustomerResponse.model_validate(customer)
    except VersionConflictError as exc:
        return JSONResponse(
            status_code=409,
            content={
                "error": "version_conflict",
                "expected_version": exc.expected,
                "actual_version": exc.actual,
            },
        )
    except DuplicateBusinessNumberError as exc:
        return JSONResponse(
            status_code=409,
            content=duplicate_response(exc),
        )
    except ValidationError as exc:
        return JSONResponse(
            status_code=422,
            content=error_response(exc.errors),
        )


@router.get("/{customer_id}/outstanding", response_model=CustomerOutstandingSummary)
async def outstanding(
    customer_id: uuid.UUID,
    session: DbSession,
    _user: ReadUser,
) -> CustomerOutstandingSummary | JSONResponse:
    from domains.invoices.service import get_customer_outstanding

    try:
        summary = await get_customer_outstanding(session, customer_id, verify_customer=True)
    except ValueError as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})
    if summary is None:
        return JSONResponse(status_code=404, content={"detail": "Customer not found."})
    return CustomerOutstandingSummary(**summary)
