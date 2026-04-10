"""Purchase API routes."""

from __future__ import annotations

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from common.auth import require_role
from common.database import get_db
from common.tenant import set_tenant
from domains.purchases.schemas import (
    SupplierInvoiceListItem,
    SupplierInvoiceListResponse,
    SupplierInvoiceResponse,
)
from domains.purchases.service import get_supplier_invoice, list_supplier_invoices

router = APIRouter(dependencies=[Depends(require_role("admin", "finance", "warehouse"))])

DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[dict, Depends(require_role("admin", "finance", "warehouse"))]


@router.get(
    "/supplier-invoices",
    response_model=SupplierInvoiceListResponse,
)
async def list_supplier_invoices_endpoint(
    session: DbSession,
    user: CurrentUser,
    status_filter: Literal["open", "paid", "voided"] | None = Query(default=None, alias="status"),
    supplier_id: uuid.UUID | None = Query(default=None),
    sort_by: Literal["created_at", "invoice_date", "total_amount"] = Query(
        default="created_at"
    ),
    sort_order: Literal["asc", "desc"] = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> SupplierInvoiceListResponse:
    tenant_id = uuid.UUID(user["tenant_id"])
    items, total = await list_supplier_invoices(
        session,
        tenant_id,
        status_filter=status_filter,
        supplier_id=supplier_id,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return SupplierInvoiceListResponse(
        items=[SupplierInvoiceListItem(**item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/supplier-invoices/{invoice_id}",
    response_model=SupplierInvoiceResponse,
)
async def get_supplier_invoice_endpoint(
    invoice_id: uuid.UUID,
    session: DbSession,
    user: CurrentUser,
) -> SupplierInvoiceResponse:
    tenant_id = uuid.UUID(user["tenant_id"])
    async with session.begin():
        await set_tenant(session, tenant_id)
        invoice = await get_supplier_invoice(session, invoice_id, tenant_id)
    if invoice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier invoice not found",
        )
    return SupplierInvoiceResponse(**invoice)