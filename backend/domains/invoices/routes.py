"""Invoice API routes."""

from __future__ import annotations

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from common.auth import require_role
from common.config import get_settings
from common.database import get_db
from common.errors import ValidationError, error_response
from common.object_store import S3ObjectStore
from domains.invoices.pdf import DEFAULT_SELLER, generate_invoice_pdf, pdf_filename
from domains.invoices.schemas import (
    EguiSubmissionResponse,
    InvoiceCreate,
    InvoiceListItem,
    InvoiceListResponse,
    InvoiceResponse,
    VoidInvoiceRequest,
)
from domains.invoices.service import (
    compute_invoice_payment_summary,
    create_invoice,
    get_invoice,
    get_invoice_egui_submission,
    list_invoices,
    refresh_invoice_egui_submission,
    serialize_invoice_egui_submission,
    void_invoice,
)
from domains.invoices.validators import IMMUTABLE_ERROR

router = APIRouter(dependencies=[Depends(require_role("admin", "finance", "sales"))])

DbSession = Annotated[AsyncSession, Depends(get_db)]


def _build_invoice_artifact_store() -> S3ObjectStore | None:
    settings = get_settings()
    if not (
        settings.object_store_endpoint_url
        and settings.object_store_access_key
        and settings.object_store_secret_key
    ):
        return None

    return S3ObjectStore(
        endpoint_url=settings.object_store_endpoint_url,
        access_key=settings.object_store_access_key,
        secret_key=settings.object_store_secret_key,
        region=settings.object_store_region,
    )


@router.get("", response_model=InvoiceListResponse)
async def list_all(
    session: DbSession,
    current_user: Annotated[dict, Depends(require_role("admin", "finance", "sales"))],
    customer_id: uuid.UUID | None = Query(default=None),
    payment_status: Literal["paid", "unpaid", "partial", "overdue"] | None = Query(default=None),
    sort_by: Literal["created_at", "invoice_date", "outstanding_balance"] = Query(
        default="created_at"
    ),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> InvoiceListResponse:
    real_tid = uuid.UUID(current_user["tenant_id"])
    items, total = await list_invoices(
        session,
        tenant_id=real_tid,
        customer_id=customer_id,
        page=page,
        page_size=page_size,
        payment_status=payment_status or None,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return InvoiceListResponse(
        items=[InvoiceListItem(**item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "",
    response_model=InvoiceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create(
    data: InvoiceCreate,
    session: DbSession,
    current_user: Annotated[dict, Depends(require_role("admin", "finance", "sales"))],
) -> InvoiceResponse | JSONResponse:
    real_tid = uuid.UUID(current_user["tenant_id"])
    try:
        settings = get_settings()
        invoice = await create_invoice(
            session,
            data,
            tenant_id=real_tid,
            artifact_store=_build_invoice_artifact_store(),
            artifact_retention_class=settings.invoice_artifact_retention_class,
            artifact_storage_policy=settings.invoice_artifact_storage_policy,
            seller_ban=settings.invoice_seller_ban,
            seller_name=settings.invoice_seller_name,
        )
        return InvoiceResponse.model_validate(invoice)
    except ValidationError as exc:
        return JSONResponse(
            status_code=422,
            content=error_response(exc.errors),
        )


@router.get(
    "/{invoice_id}",
    response_model=InvoiceResponse,
)
async def get(
    invoice_id: uuid.UUID,
    session: DbSession,
    current_user: Annotated[dict, Depends(require_role("admin", "finance", "sales"))],
) -> InvoiceResponse | JSONResponse:
    from common.tenant import set_tenant

    real_tid = uuid.UUID(current_user["tenant_id"])
    settings = get_settings()
    async with session.begin():
        await set_tenant(session, real_tid)
        invoice = await get_invoice(session, invoice_id, tenant_id=real_tid)
        if invoice is None:
            return JSONResponse(
                status_code=404,
                content={"detail": "Invoice not found"},
            )
        summary = await compute_invoice_payment_summary(session, invoice, real_tid)
        egui_submission = await get_invoice_egui_submission(
            session,
            invoice,
            real_tid,
            enabled=settings.egui_tracking_enabled,
            mode=settings.egui_submission_mode,
        )

    resp = InvoiceResponse.model_validate(invoice)
    updates: dict[str, object] = {**summary}
    if egui_submission is not None:
        updates["egui_submission"] = EguiSubmissionResponse.model_validate(
            serialize_invoice_egui_submission(egui_submission, invoice)
        )
    resp = resp.model_copy(update=updates)
    return resp


@router.post(
    "/{invoice_id}/egui/refresh",
    response_model=EguiSubmissionResponse,
)
async def refresh_egui(
    invoice_id: uuid.UUID,
    session: DbSession,
    current_user: Annotated[dict, Depends(require_role("admin", "finance", "sales"))],
) -> EguiSubmissionResponse | JSONResponse:
    from common.tenant import set_tenant

    real_tid = uuid.UUID(current_user["tenant_id"])
    settings = get_settings()
    if not settings.egui_tracking_enabled:
        return JSONResponse(
            status_code=404,
            content={"detail": "eGUI tracking is not enabled"},
        )
    if settings.egui_submission_mode != "mock":
        return JSONResponse(
            status_code=503,
            content={"detail": "Live eGUI refresh is not implemented"},
        )

    async with session.begin():
        await set_tenant(session, real_tid)
        invoice = await get_invoice(session, invoice_id, tenant_id=real_tid)
        if invoice is None:
            return JSONResponse(
                status_code=404,
                content={"detail": "Invoice not found"},
            )
        egui_submission = await refresh_invoice_egui_submission(
            session,
            invoice,
            real_tid,
            enabled=settings.egui_tracking_enabled,
            mode=settings.egui_submission_mode,
        )

    if egui_submission is None:
        return JSONResponse(
            status_code=404,
            content={"detail": "eGUI tracking is not enabled"},
        )

    return EguiSubmissionResponse.model_validate(
        serialize_invoice_egui_submission(egui_submission, invoice)
    )


@router.post(
    "/{invoice_id}/void",
    response_model=InvoiceResponse,
)
async def void(
    invoice_id: uuid.UUID,
    data: VoidInvoiceRequest,
    session: DbSession,
    current_user: Annotated[dict, Depends(require_role("admin", "finance", "sales"))],
) -> InvoiceResponse | JSONResponse:
    real_tid = uuid.UUID(current_user["tenant_id"])
    try:
        invoice = await void_invoice(session, invoice_id, reason=data.reason, tenant_id=real_tid)
        return InvoiceResponse.model_validate(invoice)
    except ValueError as exc:
        msg = str(exc)
        if msg == "Invoice not found":
            return JSONResponse(
                status_code=404,
                content={"detail": msg},
            )
        return JSONResponse(
            status_code=422,
            content=error_response([{"field": "invoice", "message": msg}]),
        )


@router.get("/{invoice_id}/pdf", response_model=None)
async def export_pdf(
    invoice_id: uuid.UUID,
    session: DbSession,
    current_user: Annotated[dict, Depends(require_role("admin", "finance", "sales"))],
) -> Response | JSONResponse:
    from common.tenant import set_tenant

    real_tid = uuid.UUID(current_user["tenant_id"])
    async with session.begin():
        await set_tenant(session, real_tid)
        invoice = await get_invoice(session, invoice_id, tenant_id=real_tid)
    if invoice is None:
        return JSONResponse(
            status_code=404,
            content={"detail": "Invoice not found"},
        )
    try:
        pdf_bytes = generate_invoice_pdf(invoice, DEFAULT_SELLER)
    except ValueError as exc:
        return JSONResponse(
            status_code=422,
            content=error_response([{"field": "invoice", "message": str(exc)}]),
        )
    except RuntimeError as exc:
        return JSONResponse(
            status_code=503,
            content={"detail": str(exc)},
        )
    filename = pdf_filename(invoice)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.put(
    "/{invoice_id}",
    status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
)
async def update_rejected(invoice_id: uuid.UUID) -> JSONResponse:
    """Reject any PUT update — invoices are immutable after creation."""
    return JSONResponse(
        status_code=405,
        content={"detail": IMMUTABLE_ERROR},
    )


@router.patch(
    "/{invoice_id}",
    status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
)
async def patch_rejected(invoice_id: uuid.UUID) -> JSONResponse:
    """Reject any PATCH update — invoices are immutable after creation."""
    return JSONResponse(
        status_code=405,
        content={"detail": IMMUTABLE_ERROR},
    )


@router.delete(
    "/{invoice_id}",
    status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
)
async def delete_rejected(invoice_id: uuid.UUID) -> JSONResponse:
    """Reject any DELETE — invoices are immutable; use void instead."""
    return JSONResponse(
        status_code=405,
        content={"detail": IMMUTABLE_ERROR},
    )
