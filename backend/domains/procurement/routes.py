"""Procurement API routes - RFQ and Supplier Quotation workspace."""

from __future__ import annotations

import math
import os
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from common.database import get_db
from common.errors import ValidationError, error_response
from domains.procurement import schemas as s
from domains.procurement import service as svc

router = APIRouter(prefix="/procurement", tags=["procurement"])


async def get_tenant_and_user(
    x_tenant_id: Annotated[str | None, Header()] = None,
) -> tuple[uuid.UUID, str]:
    """Extract tenant_id and user from request headers.

    For production, this will be wired to Epic 11 RBAC middleware.
    For now, we require X-Tenant-Id header for multi-tenant isolation.
    Falls back to a development default only if header is missing (dev mode).
    """
    # TODO: wire up real auth context (Epic 11 RBAC)
    if x_tenant_id:
        try:
            return uuid.UUID(x_tenant_id), "authenticated_user"
        except ValueError:
            raise ValidationError([{"field": "tenant_id", "message": "Invalid tenant ID format"}])
    # Development fallback
    if os.environ.get("ENVIRONMENT") == "production":
        raise ValidationError([{"field": "tenant_id", "message": "X-Tenant-Id header required in production"}])
    return uuid.UUID("00000000-0000-0000-0000-000000000001"), "dev_user"


# Type alias for dependency injection
TenantUser = tuple[uuid.UUID, str]


# ---------------------------------------------------------------------------
# RFQ Routes
# ---------------------------------------------------------------------------


@router.post(
    "/rfqs",
    response_model=s.RFQResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_rfq(
    data: s.RFQCreate,
    db: AsyncSession = Depends(get_db),
    tenant_user: TenantUser = Depends(get_tenant_and_user),
) -> s.RFQResponse:
    """Create a new Request for Quotation."""
    tenant_id, current_user = tenant_user
    rfq = await svc.create_rfq(
        db,
        tenant_id=tenant_id,
        data=data.model_dump(),
        current_user=current_user,
    )
    return s.RFQResponse.model_validate(rfq)


@router.get("/rfqs", response_model=s.RFQListResponse)
async def list_rfqs(
    status: s.RFQStatus | None = None,
    q: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    tenant_user: TenantUser = Depends(get_tenant_and_user),
) -> s.RFQListResponse:
    """List RFQs with optional filtering."""
    tenant_id, _ = tenant_user
    rfqs, total = await svc.list_rfqs(
        db, tenant_id, status=status.value if status else None, q=q, page=page, page_size=page_size
    )
    return s.RFQListResponse(
        items=[s.RFQSummary.model_validate(r) for r in rfqs],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


@router.get("/rfqs/{rfq_id}", response_model=s.RFQResponse)
async def get_rfq(
    rfq_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_user: TenantUser = Depends(get_tenant_and_user),
) -> s.RFQResponse:
    """Get a single RFQ with items and suppliers."""
    tenant_id, _ = tenant_user
    try:
        rfq = await svc.get_rfq(db, tenant_id, rfq_id)
    except ValidationError as exc:
        errors = exc.errors if hasattr(exc, "errors") else [str(exc)]
        status_code = 404 if any(
            isinstance(e, dict) and e.get("field") == "rfq_id" for e in errors
        ) else 422
        return JSONResponse(status_code=status_code, content=error_response(errors))
    return s.RFQResponse.model_validate(rfq)


@router.patch("/rfqs/{rfq_id}", response_model=s.RFQResponse)
async def update_rfq(
    rfq_id: uuid.UUID,
    data: s.RFQUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_user: TenantUser = Depends(get_tenant_and_user),
) -> s.RFQResponse:
    """Update RFQ fields."""
    tenant_id, _ = tenant_user
    rfq = await svc.update_rfq(db, tenant_id, rfq_id, data.model_dump(exclude_none=True))
    return s.RFQResponse.model_validate(rfq)


@router.post("/rfqs/{rfq_id}/submit", response_model=s.RFQResponse)
async def submit_rfq(
    rfq_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_user: TenantUser = Depends(get_tenant_and_user),
) -> s.RFQResponse:
    """Submit an RFQ."""
    tenant_id, _ = tenant_user
    rfq = await svc.submit_rfq(db, tenant_id, rfq_id)
    return s.RFQResponse.model_validate(rfq)


@router.get("/rfqs/{rfq_id}/comparison", response_model=s.RFQComparisonResponse)
async def get_rfq_comparison(
    rfq_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_user: TenantUser = Depends(get_tenant_and_user),
) -> s.RFQComparisonResponse:
    """Get side-by-side comparison of all supplier quotations for an RFQ."""
    tenant_id, _ = tenant_user
    data = await svc.get_rfq_comparison(db, tenant_id, rfq_id)
    return s.RFQComparisonResponse(
        rfq_id=data["rfq_id"],
        rfq_name=data["rfq_name"],
        status=data["status"],
        items=[s.RFQItemResponse.model_validate(i) for i in data["items"]],
        quotations=[
            s.SupplierComparisonRow(
                quotation_id=r["quotation_id"],
                supplier_name=r["supplier_name"],
                currency=r["currency"],
                grand_total=r["grand_total"],
                base_grand_total=r["base_grand_total"],
                comparison_base_total=r["comparison_base_total"],
                lead_time_days=r["lead_time_days"],
                valid_till=r["valid_till"],
                is_awarded=r["is_awarded"],
                is_expired=r["is_expired"],
                status=r["status"],
                items=[s.SQItemResponse.model_validate(i) for i in r["items"]],
            )
            for r in data["quotations"]
        ],
    )


# ---------------------------------------------------------------------------
# Supplier Quotation Routes
# ---------------------------------------------------------------------------


@router.post(
    "/supplier-quotations",
    response_model=s.SupplierQuotationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_supplier_quotation(
    data: s.SupplierQuotationCreate,
    db: AsyncSession = Depends(get_db),
    tenant_user: TenantUser = Depends(get_tenant_and_user),
) -> s.SupplierQuotationResponse:
    """Create a supplier quotation in response to an RFQ."""
    tenant_id, current_user = tenant_user
    sq = await svc.create_supplier_quotation(
        db,
        tenant_id=tenant_id,
        data=data.model_dump(),
        current_user=current_user,
    )
    return s.SupplierQuotationResponse.model_validate(sq)


@router.get("/supplier-quotations", response_model=s.SupplierQuotationListResponse)
async def list_supplier_quotations(
    rfq_id: uuid.UUID | None = None,
    status: s.SupplierQuotationStatus | None = None,
    q: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    tenant_user: TenantUser = Depends(get_tenant_and_user),
) -> s.SupplierQuotationListResponse:
    """List supplier quotations with optional RFQ filter."""
    tenant_id, _ = tenant_user
    sqs, total = await svc.list_supplier_quotations(
        db, tenant_id,
        rfq_id=rfq_id,
        status=status.value if status else None,
        q=q,
        page=page,
        page_size=page_size,
    )
    return s.SupplierQuotationListResponse(
        items=[s.SupplierQuotationSummary.model_validate(s) for s in sqs],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


@router.get("/supplier-quotations/{quotation_id}", response_model=s.SupplierQuotationResponse)
async def get_supplier_quotation(
    quotation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_user: TenantUser = Depends(get_tenant_and_user),
) -> s.SupplierQuotationResponse:
    """Get a single supplier quotation with items."""
    tenant_id, _ = tenant_user
    try:
        sq = await svc.get_supplier_quotation(db, tenant_id, quotation_id)
    except ValidationError as exc:
        errors = exc.errors if hasattr(exc, "errors") else [str(exc)]
        status_code = 404 if any(
            isinstance(e, dict) and e.get("field") == "quotation_id" for e in errors
        ) else 422
        return JSONResponse(status_code=status_code, content=error_response(errors))
    return s.SupplierQuotationResponse.model_validate(sq)


@router.patch(
    "/supplier-quotations/{quotation_id}",
    response_model=s.SupplierQuotationResponse,
)
async def update_supplier_quotation(
    quotation_id: uuid.UUID,
    data: s.SupplierQuotationUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_user: TenantUser = Depends(get_tenant_and_user),
) -> s.SupplierQuotationResponse:
    """Update supplier quotation fields."""
    tenant_id, _ = tenant_user
    sq = await svc.update_supplier_quotation(
        db, tenant_id, quotation_id, data.model_dump(exclude_none=True)
    )
    return s.SupplierQuotationResponse.model_validate(sq)


@router.post(
    "/supplier-quotations/{quotation_id}/submit",
    response_model=s.SupplierQuotationResponse,
)
async def submit_supplier_quotation(
    quotation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_user: TenantUser = Depends(get_tenant_and_user),
) -> s.SupplierQuotationResponse:
    """Submit a supplier quotation."""
    tenant_id, _ = tenant_user
    sq = await svc.submit_supplier_quotation(db, tenant_id, quotation_id)
    return s.SupplierQuotationResponse.model_validate(sq)


# ---------------------------------------------------------------------------
# Award Routes (PO handoff seam)
# ---------------------------------------------------------------------------


@router.post(
    "/awards",
    response_model=s.AwardResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_award(
    data: s.AwardCreate,
    db: AsyncSession = Depends(get_db),
    tenant_user: TenantUser = Depends(get_tenant_and_user),
) -> s.AwardResponse:
    """Select a supplier quotation as the winning source.

    This is the explicit PO handoff seam consumed by Story 24.2.
    """
    tenant_id, _ = tenant_user
    award = await svc.award_quotation(
        db,
        tenant_id=tenant_id,
        rfq_id=data.rfq_id,
        quotation_id=data.quotation_id,
        awarded_by=data.awarded_by,
    )
    return s.AwardResponse.model_validate(award)


@router.get("/awards", response_model=list[s.AwardResponse])
async def list_awards(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    tenant_user: TenantUser = Depends(get_tenant_and_user),
) -> list[s.AwardResponse]:
    """List all procurement awards."""
    tenant_id, _ = tenant_user
    awards, _ = await svc.list_awards(db, tenant_id, page=page, page_size=page_size)
    return [s.AwardResponse.model_validate(a) for a in awards]


@router.get(
    "/rfqs/{rfq_id}/award",
    response_model=s.AwardResponse | None,
)
async def get_rfq_award(
    rfq_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_user: TenantUser = Depends(get_tenant_and_user),
) -> s.AwardResponse | None:
    """Get the award for an RFQ if one exists (consumed by Story 24.2)."""
    tenant_id, _ = tenant_user
    award = await svc.get_award(db, tenant_id, rfq_id)
    return s.AwardResponse.model_validate(award) if award else None
