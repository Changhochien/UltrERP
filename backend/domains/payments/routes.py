"""Payment API routes."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from common.auth import require_role
from common.database import get_db
from common.errors import ValidationError, error_response
from common.tenant import DEFAULT_TENANT_ID
from domains.payments.schemas import (
    ManualMatchRequest,
    PaymentCreate,
    PaymentCreateUnmatched,
    PaymentListItem,
    PaymentListResponse,
    PaymentResponse,
    ReconciliationResult,
)
from domains.payments.services import (
    confirm_suggested_match,
    get_payment,
    list_payments,
    manual_match,
    record_payment,
    record_unmatched_payment,
    run_reconciliation,
)

router = APIRouter(dependencies=[Depends(require_role("finance"))])

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.post(
    "",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create(data: PaymentCreate, session: DbSession) -> PaymentResponse | JSONResponse:
    try:
        payment = await record_payment(session, DEFAULT_TENANT_ID, data)
        return PaymentResponse.model_validate(payment)
    except ValidationError as exc:
        # Determine status code from error message
        msg = exc.errors[0]["message"] if exc.errors else ""
        if "voided" in msg or "already fully paid" in msg:
            return JSONResponse(
                status_code=409,
                content=error_response(exc.errors),
            )
        return JSONResponse(
            status_code=422,
            content=error_response(exc.errors),
        )
    except IntegrityError:
        return JSONResponse(
            status_code=409,
            content=error_response(
                [{"field": "", "message": "Concurrent conflict. Please retry."}]
            ),
        )


@router.get(
    "",
    response_model=PaymentListResponse,
)
async def list_all(
    session: DbSession,
    invoice_id: uuid.UUID | None = Query(default=None),
    customer_id: uuid.UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaymentListResponse:
    items, total = await list_payments(
        session,
        DEFAULT_TENANT_ID,
        invoice_id=invoice_id,
        customer_id=customer_id,
        page=page,
        page_size=page_size,
    )
    return PaymentListResponse(
        items=[PaymentListItem.model_validate(p) for p in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{payment_id}",
    response_model=PaymentResponse,
)
async def get(payment_id: uuid.UUID, session: DbSession) -> PaymentResponse | JSONResponse:
    payment = await get_payment(session, DEFAULT_TENANT_ID, payment_id)
    if payment is None:
        return JSONResponse(
            status_code=404,
            content={"detail": "Payment not found"},
        )
    return PaymentResponse.model_validate(payment)


@router.post(
    "/unmatched",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_unmatched(
    data: PaymentCreateUnmatched, session: DbSession
) -> PaymentResponse | JSONResponse:
    try:
        payment = await record_unmatched_payment(session, DEFAULT_TENANT_ID, data)
        return PaymentResponse.model_validate(payment)
    except ValidationError as exc:
        return JSONResponse(
            status_code=422,
            content=error_response(exc.errors),
        )
    except IntegrityError:
        return JSONResponse(
            status_code=422,
            content=error_response(
                [{"field": "customer_id", "message": "Invalid customer or concurrent conflict."}]
            ),
        )


@router.post(
    "/reconcile",
    response_model=ReconciliationResult,
)
async def reconcile(session: DbSession) -> ReconciliationResult:
    result = await run_reconciliation(session, DEFAULT_TENANT_ID)
    return ReconciliationResult(**result)


@router.post(
    "/{payment_id}/confirm-match",
    response_model=PaymentResponse,
)
async def confirm_match(
    payment_id: uuid.UUID,
    session: DbSession,
) -> PaymentResponse | JSONResponse:
    try:
        payment = await confirm_suggested_match(session, DEFAULT_TENANT_ID, payment_id)
        return PaymentResponse.model_validate(payment)
    except ValidationError as exc:
        return JSONResponse(
            status_code=422,
            content=error_response(exc.errors),
        )


@router.post(
    "/{payment_id}/manual-match",
    response_model=PaymentResponse,
)
async def do_manual_match(
    payment_id: uuid.UUID,
    data: ManualMatchRequest,
    session: DbSession,
) -> PaymentResponse | JSONResponse:
    try:
        payment = await manual_match(session, DEFAULT_TENANT_ID, payment_id, data.invoice_id)
        return PaymentResponse.model_validate(payment)
    except ValidationError as exc:
        msg = exc.errors[0]["message"] if exc.errors else ""
        code = 409 if "different customer" in msg or "voided" in msg else 422
        return JSONResponse(
            status_code=code,
            content=error_response(exc.errors),
        )
