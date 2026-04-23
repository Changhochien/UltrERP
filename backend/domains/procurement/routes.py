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


# ---------------------------------------------------------------------------
# Purchase Order Routes
# ---------------------------------------------------------------------------


@router.post(
    "/purchase-orders",
    response_model=s.PurchaseOrderResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_purchase_order(
    data: s.PurchaseOrderCreate,
    db: AsyncSession = Depends(get_db),
    tenant_user: TenantUser = Depends(get_tenant_and_user),
) -> s.PurchaseOrderResponse:
    """Create a Purchase Order, optionally from an awarded supplier quotation.

    Provide award_id to auto-fill supplier, items, and commercial data from
    the awarded supplier quotation without manual re-entry.
    """
    tenant_id, current_user = tenant_user
    po = await svc.create_purchase_order(
        db,
        tenant_id=tenant_id,
        data=data.model_dump(),
        current_user=current_user,
    )
    return s.PurchaseOrderResponse.model_validate(po)


@router.get("/purchase-orders", response_model=s.PurchaseOrderListResponse)
async def list_purchase_orders(
    status: s.POStatus | None = None,
    supplier_id: uuid.UUID | None = None,
    q: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    tenant_user: TenantUser = Depends(get_tenant_and_user),
) -> s.PurchaseOrderListResponse:
    """List purchase orders with optional filtering."""
    tenant_id, _ = tenant_user
    pos, total = await svc.list_purchase_orders(
        db, tenant_id,
        status=status.value if status else None,
        supplier_id=supplier_id,
        q=q,
        page=page,
        page_size=page_size,
    )
    return s.PurchaseOrderListResponse(
        items=[s.PurchaseOrderSummary.model_validate(p) for p in pos],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


@router.get("/purchase-orders/{po_id}", response_model=s.PurchaseOrderResponse)
async def get_purchase_order(
    po_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_user: TenantUser = Depends(get_tenant_and_user),
) -> s.PurchaseOrderResponse:
    """Get a single purchase order with items."""
    tenant_id, _ = tenant_user
    try:
        po = await svc.get_purchase_order(db, tenant_id, po_id)
    except ValidationError as exc:
        errors = exc.errors if hasattr(exc, "errors") else [str(exc)]
        status_code = 404 if any(
            isinstance(e, dict) and e.get("field") == "po_id" for e in errors
        ) else 422
        return JSONResponse(status_code=status_code, content=error_response(errors))
    return s.PurchaseOrderResponse.model_validate(po)


@router.patch("/purchase-orders/{po_id}", response_model=s.PurchaseOrderResponse)
async def update_purchase_order(
    po_id: uuid.UUID,
    data: s.PurchaseOrderUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_user: TenantUser = Depends(get_tenant_and_user),
) -> s.PurchaseOrderResponse:
    """Update purchase order fields."""
    tenant_id, _ = tenant_user
    try:
        po = await svc.update_purchase_order(
            db, tenant_id, po_id, data.model_dump(exclude_none=True)
        )
    except ValidationError as exc:
        errors = exc.errors if hasattr(exc, "errors") else [str(exc)]
        status_code = 404 if any(
            isinstance(e, dict) and e.get("field") == "po_id" for e in errors
        ) else 422
        return JSONResponse(status_code=status_code, content=error_response(errors))
    return s.PurchaseOrderResponse.model_validate(po)


@router.post("/purchase-orders/{po_id}/submit", response_model=s.PurchaseOrderResponse)
async def submit_purchase_order(
    po_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_user: TenantUser = Depends(get_tenant_and_user),
) -> s.PurchaseOrderResponse:
    """Submit a purchase order for approval."""
    tenant_id, current_user = tenant_user
    try:
        po = await svc.submit_purchase_order(db, tenant_id, po_id, current_user=current_user)
    except ValidationError as exc:
        errors = exc.errors if hasattr(exc, "errors") else [str(exc)]
        status_code = 422
        return JSONResponse(status_code=status_code, content=error_response(errors))
    return s.PurchaseOrderResponse.model_validate(po)


@router.post("/purchase-orders/{po_id}/hold", response_model=s.PurchaseOrderResponse)
async def hold_purchase_order(
    po_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_user: TenantUser = Depends(get_tenant_and_user),
) -> s.PurchaseOrderResponse:
    """Place a purchase order on hold."""
    tenant_id, _ = tenant_user
    try:
        po = await svc.hold_purchase_order(db, tenant_id, po_id)
    except ValidationError as exc:
        errors = exc.errors if hasattr(exc, "errors") else [str(exc)]
        return JSONResponse(status_code=422, content=error_response(errors))
    return s.PurchaseOrderResponse.model_validate(po)


@router.post("/purchase-orders/{po_id}/release", response_model=s.PurchaseOrderResponse)
async def release_purchase_order(
    po_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_user: TenantUser = Depends(get_tenant_and_user),
) -> s.PurchaseOrderResponse:
    """Release a purchase order from hold."""
    tenant_id, _ = tenant_user
    try:
        po = await svc.release_purchase_order(db, tenant_id, po_id)
    except ValidationError as exc:
        errors = exc.errors if hasattr(exc, "errors") else [str(exc)]
        return JSONResponse(status_code=422, content=error_response(errors))
    return s.PurchaseOrderResponse.model_validate(po)


@router.post("/purchase-orders/{po_id}/complete", response_model=s.PurchaseOrderResponse)
async def complete_purchase_order(
    po_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_user: TenantUser = Depends(get_tenant_and_user),
) -> s.PurchaseOrderResponse:
    """Manually complete a purchase order."""
    tenant_id, _ = tenant_user
    try:
        po = await svc.complete_purchase_order(db, tenant_id, po_id)
    except ValidationError as exc:
        errors = exc.errors if hasattr(exc, "errors") else [str(exc)]
        return JSONResponse(status_code=422, content=error_response(errors))
    return s.PurchaseOrderResponse.model_validate(po)


@router.post("/purchase-orders/{po_id}/cancel", response_model=s.PurchaseOrderResponse)
async def cancel_purchase_order(
    po_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_user: TenantUser = Depends(get_tenant_and_user),
) -> s.PurchaseOrderResponse:
    """Cancel a purchase order."""
    tenant_id, _ = tenant_user
    try:
        po = await svc.cancel_purchase_order(db, tenant_id, po_id)
    except ValidationError as exc:
        errors = exc.errors if hasattr(exc, "errors") else [str(exc)]
        return JSONResponse(status_code=422, content=error_response(errors))
    return s.PurchaseOrderResponse.model_validate(po)


@router.post("/purchase-orders/{po_id}/close", response_model=s.PurchaseOrderResponse)
async def close_purchase_order(
    po_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_user: TenantUser = Depends(get_tenant_and_user),
) -> s.PurchaseOrderResponse:
    """Close a purchase order."""
    tenant_id, _ = tenant_user
    try:
        po = await svc.close_purchase_order(db, tenant_id, po_id)
    except ValidationError as exc:
        errors = exc.errors if hasattr(exc, "errors") else [str(exc)]
        return JSONResponse(status_code=422, content=error_response(errors))
    return s.PurchaseOrderResponse.model_validate(po)


@router.post("/purchase-orders/{po_id}/recompute-progress", response_model=s.PurchaseOrderResponse)
async def recompute_po_progress(
    po_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_user: TenantUser = Depends(get_tenant_and_user),
) -> s.PurchaseOrderResponse:
    """Recompute per_received and per_billed from downstream coverage.

    Called by goods receipt (Story 24-3) and supplier invoice (Story 24-6)
    to update PO progress fields.
    """
    tenant_id, _ = tenant_user
    try:
        po = await svc.recompute_po_progress(db, tenant_id, po_id)
    except ValidationError as exc:
        errors = exc.errors if hasattr(exc, "errors") else [str(exc)]
        return JSONResponse(status_code=422, content=error_response(errors))
    return s.PurchaseOrderResponse.model_validate(po)


@router.get("/awards/{award_id}/create-po", response_model=s.PurchaseOrderResponse)
async def create_po_from_award(
    award_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_user: TenantUser = Depends(get_tenant_and_user),
) -> s.PurchaseOrderResponse:
    """Create a PO directly from an award ID.

    Convenience endpoint that auto-fills all data from the awarded quotation.
    """
    tenant_id, current_user = tenant_user
    try:
        po = await svc.create_purchase_order(
            db,
            tenant_id=tenant_id,
            data={"award_id": str(award_id)},
            current_user=current_user,
        )
    except ValidationError as exc:
        errors = exc.errors if hasattr(exc, "errors") else [str(exc)]
        return JSONResponse(status_code=422, content=error_response(errors))
    return s.PurchaseOrderResponse.model_validate(po)


# ---------------------------------------------------------------------------
# Goods Receipt Routes (Story 24-3)
# ---------------------------------------------------------------------------


@router.post(
    "/goods-receipts",
    response_model=s.GoodsReceiptResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_goods_receipt(
    data: s.GoodsReceiptCreate,
    db: AsyncSession = Depends(get_db),
    tenant_user: TenantUser = Depends(get_tenant_and_user),
) -> s.GoodsReceiptResponse:
    """Create a goods receipt against a purchase order.

    Each line must link to a PO line via purchase_order_item_id.
    Accepted and rejected quantities are validated to be non-negative.
    """
    tenant_id, current_user = tenant_user
    try:
        gr = await svc.create_goods_receipt(
            db,
            tenant_id=tenant_id,
            data=data.model_dump(),
            current_user=current_user,
        )
    except ValidationError as exc:
        errors = exc.errors if hasattr(exc, "errors") else [str(exc)]
        return JSONResponse(status_code=422, content=error_response(errors))
    return s.GoodsReceiptResponse.model_validate(gr)


@router.get("/goods-receipts", response_model=s.GoodsReceiptListResponse)
async def list_goods_receipts(
    purchase_order_id: uuid.UUID | None = None,
    status: s.GoodsReceiptStatus | None = None,
    q: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    tenant_user: TenantUser = Depends(get_tenant_and_user),
) -> s.GoodsReceiptListResponse:
    """List goods receipts with optional filtering."""
    tenant_id, _ = tenant_user
    receipts, total = await svc.list_goods_receipts(
        db, tenant_id,
        purchase_order_id=purchase_order_id,
        status=status.value if status else None,
        q=q,
        page=page,
        page_size=page_size,
    )
    return s.GoodsReceiptListResponse(
        items=[s.GoodsReceiptSummary.model_validate(r) for r in receipts],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


@router.get("/goods-receipts/{gr_id}", response_model=s.GoodsReceiptResponse)
async def get_goods_receipt(
    gr_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_user: TenantUser = Depends(get_tenant_and_user),
) -> s.GoodsReceiptResponse:
    """Get a single goods receipt with items."""
    tenant_id, _ = tenant_user
    try:
        gr = await svc.get_goods_receipt(db, tenant_id, gr_id)
    except ValidationError as exc:
        errors = exc.errors if hasattr(exc, "errors") else [str(exc)]
        status_code = 404 if any(
            isinstance(e, dict) and e.get("field") == "gr_id" for e in errors
        ) else 422
        return JSONResponse(status_code=status_code, content=error_response(errors))
    return s.GoodsReceiptResponse.model_validate(gr)


@router.post("/goods-receipts/{gr_id}/submit", response_model=s.GoodsReceiptResponse)
async def submit_goods_receipt(
    gr_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_user: TenantUser = Depends(get_tenant_and_user),
) -> s.GoodsReceiptResponse:
    """Submit a goods receipt to trigger inventory mutation and PO progress update."""
    tenant_id, _ = tenant_user
    try:
        gr = await svc.submit_goods_receipt(db, tenant_id, gr_id)
    except ValidationError as exc:
        errors = exc.errors if hasattr(exc, "errors") else [str(exc)]
        return JSONResponse(status_code=422, content=error_response(errors))
    return s.GoodsReceiptResponse.model_validate(gr)


@router.post("/goods-receipts/{gr_id}/cancel", response_model=s.GoodsReceiptResponse)
async def cancel_goods_receipt(
    gr_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_user: TenantUser = Depends(get_tenant_and_user),
) -> s.GoodsReceiptResponse:
    """Cancel a goods receipt. Draft receipts are immediately cancelled.

    Submitted receipts are cancelled and PO progress is recomputed.
    """
    tenant_id, _ = tenant_user
    try:
        gr = await svc.cancel_goods_receipt(db, tenant_id, gr_id)
    except ValidationError as exc:
        errors = exc.errors if hasattr(exc, "errors") else [str(exc)]
        return JSONResponse(status_code=422, content=error_response(errors))
    return s.GoodsReceiptResponse.model_validate(gr)


@router.get("/purchase-orders/{po_id}/receipts", response_model=s.GoodsReceiptListResponse)
async def list_receipts_for_po(
    po_id: uuid.UUID,
    status: s.GoodsReceiptStatus | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    tenant_user: TenantUser = Depends(get_tenant_and_user),
) -> s.GoodsReceiptListResponse:
    """List all goods receipts for a specific purchase order."""
    tenant_id, _ = tenant_user
    receipts, total = await svc.list_goods_receipts(
        db, tenant_id,
        purchase_order_id=po_id,
        status=status.value if status else None,
        page=page,
        page_size=page_size,
    )
    return s.GoodsReceiptListResponse(
        items=[s.GoodsReceiptSummary.model_validate(r) for r in receipts],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


# ---------------------------------------------------------------------------
# Procurement Lineage - Downstream Invoice Links (Story 24-4)
# ---------------------------------------------------------------------------


@router.get(
    "/purchase-orders/{po_id}/invoice-lineage",
    response_model=dict,
    summary="Get downstream supplier invoices linked to a purchase order",
    description="""
    Returns supplier invoices that reference this purchase order via procurement lineage.
    Allows procurement users to trace which invoices have been created against their PO.

    **Story 24-4: Procurement Lineage and Three-Way-Match Readiness**

    Note: This is a readiness endpoint - no AP posting workflow is implemented.
    """,
)
async def get_po_invoice_lineage(
    po_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_user: TenantUser = Depends(get_tenant_and_user),
) -> dict:
    """Get downstream supplier invoices linked to a purchase order."""
    tenant_id, _ = tenant_user

    # Import here to avoid circular imports
    from common.models.supplier_invoice import SupplierInvoice, SupplierInvoiceLine
    from sqlalchemy import select, func
    from sqlalchemy.orm import selectinload

    async with db:
        # Find all supplier invoices that reference this PO
        result = await db.execute(
            select(SupplierInvoice)
            .options(selectinload(SupplierInvoice.lines))
            .where(
                SupplierInvoice.tenant_id == tenant_id,
                SupplierInvoice.purchase_order_id == po_id,
            )
            .order_by(SupplierInvoice.invoice_date.desc())
        )
        invoices = result.scalars().unique().all()

    linked_invoices = []
    for inv in invoices:
        # Count lines that reference PO lines
        po_line_count = sum(
            1 for line in inv.lines
            if line.purchase_order_line_id is not None
        )
        linked_invoices.append({
            "invoice_id": str(inv.id),
            "invoice_number": inv.invoice_number,
            "invoice_date": inv.invoice_date.isoformat(),
            "total_amount": str(inv.total_amount),
            "status": inv.status.value if hasattr(inv.status, "value") else str(inv.status),
            "linked_lines": po_line_count,
        })

    # Fetch PO name
    po_name = str(po_id)  # Fallback to ID if PO not found
    from common.models.supplier_invoice import SupplierInvoice  # re-import for PO query
    from domains.procurement.models import PurchaseOrder
    async with db:
        po_result = await db.execute(
            select(PurchaseOrder.name).where(PurchaseOrder.id == po_id)
        )
        po_row = po_result.scalar_one_or_none()
        if po_row:
            po_name = po_row

    return {
        "purchase_order_id": str(po_id),
        "purchase_order_name": po_name,
        "linked_invoices": linked_invoices,
    }


@router.get(
    "/goods-receipts/{gr_id}/lines/{gr_line_id}/invoice-lineage",
    response_model=dict,
    summary="Get downstream supplier invoices linked to a goods receipt line",
    description="""
    Returns supplier invoices that reference a specific goods receipt line via procurement lineage.
    Allows procurement users to trace which invoices have been created against their receipt.

    **Story 24-4: Procurement Lineage and Three-Way-Match Readiness**

    Note: This is a readiness endpoint - no AP posting workflow is implemented.
    """,
)
async def get_gr_line_invoice_lineage(
    gr_id: uuid.UUID,
    gr_line_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_user: TenantUser = Depends(get_tenant_and_user),
) -> dict:
    """Get downstream supplier invoices linked to a goods receipt line."""
    tenant_id, _ = tenant_user

    from common.models.supplier_invoice import SupplierInvoice, SupplierInvoiceLine
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    async with db:
        # Find all supplier invoice lines that reference this GR line
        result = await db.execute(
            select(SupplierInvoice)
            .options(selectinload(SupplierInvoice.lines))
            .join(SupplierInvoiceLine)
            .where(
                SupplierInvoice.tenant_id == tenant_id,
                SupplierInvoiceLine.goods_receipt_line_id == gr_line_id,
            )
            .order_by(SupplierInvoice.invoice_date.desc())
        )
        invoices = result.scalars().unique().all()

    linked_invoices = []
    for inv in invoices:
        # Count lines that reference this GR line
        gr_line_count = sum(
            1 for line in inv.lines
            if line.goods_receipt_line_id == gr_line_id
        )
        linked_invoices.append({
            "invoice_id": str(inv.id),
            "invoice_number": inv.invoice_number,
            "invoice_date": inv.invoice_date.isoformat(),
            "total_amount": str(inv.total_amount),
            "status": inv.status.value if hasattr(inv.status, "value") else str(inv.status),
            "linked_lines": gr_line_count,
        })

    # Fetch GR name
    gr_name = str(gr_id)  # Fallback to ID if GR not found
    from domains.procurement.models import GoodsReceipt
    async with db:
        gr_result = await db.execute(
            select(GoodsReceipt.name).where(GoodsReceipt.id == gr_id)
        )
        gr_row = gr_result.scalar_one_or_none()
        if gr_row:
            gr_name = gr_row

    return {
        "goods_receipt_id": str(gr_id),
        "goods_receipt_name": gr_name,
        "linked_invoices": linked_invoices,
    }
