"""Inventory API routes — warehouses and stock transfers."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.auth import require_role
from common.config import settings
from common.database import get_db
from common.errors import (
    DuplicateCategoryNameError,
    DuplicateProductCodeError,
    ValidationError,
    duplicate_category_name_response,
    duplicate_product_code_response,
    error_response,
)
from common.models.inventory_stock import InventoryStock
from common.models.product import Product
from common.models.stock_adjustment import ReasonCode
from common.tenant import get_tenant_id
from domains.aeo.content import generate_aeo_content
from domains.aeo.jsonld import generate_product_jsonld
from domains.approval.checks import needs_approval
from domains.approval.schemas import ApprovalRequiredResponse
from domains.approval.service import create_approval
from domains.inventory.reorder_point import (
    apply_reorder_points,
    compute_reorder_points_preview,
)
from domains.inventory.schemas import (
    USER_SELECTABLE_REASON_CODES,
    AcknowledgeAlertResponse,
    AuditLogListResponse,
    CategoryCreate,
    CategoryListResponse,
    CategoryResponse,
    CategoryStatusUpdate,
    CategoryUpdate,
    DismissAlertResponse,
    InventoryStockResponse,
    MonthlyDemandResponse,
    PlanningSupportResponse,
    ProductCreate,
    ProductDetailResponse,
    ProductResponse,
    ProductSearchResponse,
    ProductSearchResult,
    ProductStatusUpdate,
    ProductSupplierResponse,
    ProductUpdate,
    ReasonCodeItem,
    ReasonCodeListResponse,
    ReceiveOrderRequest,
    ReorderAlertItem,
    ReorderAlertListResponse,
    ReorderPointApplyRequest,
    ReorderPointApplyResponse,
    ReorderPointComputeRequest,
    ReorderPointComputeResponse,
    ReorderPointPreviewRow,
    SalesHistoryItem,
    SalesHistoryResponse,
    SnoozeAlertRequest,
    SnoozeAlertResponse,
    StockAdjustmentRequest,
    StockAdjustmentResponse,
    StockHistoryResponse,
    StockSettingsUpdateRequest,
    SupplierListResponse,
    SupplierOrderCreate,
    SupplierOrderListResponse,
    SupplierOrderResponse,
    SupplierResponse,
    TopCustomerResponse,
    TransferRequest,
    TransferResponse,
    UpdateOrderStatusRequest,
    WarehouseCreate,
    WarehouseList,
    WarehouseResponse,
)
from domains.inventory.services import (
    InsufficientStockError,
    TransferValidationError,
    acknowledge_alert,
    create_category,
    create_product,
    create_stock_adjustment,
    create_supplier_order,
    create_warehouse,
    dismiss_alert,
    get_category,
    get_inventory_stocks,
    get_monthly_demand,
    get_planning_support,
    get_product_audit_log,
    get_product_detail,
    get_product_supplier,
    get_sales_history,
    get_stock_history,
    get_supplier_order,
    get_top_customer,
    get_warehouse,
    list_categories,
    list_reorder_alerts,
    list_supplier_orders,
    list_suppliers,
    list_warehouses,
    receive_supplier_order,
    search_products,
    set_category_status,
    set_product_status,
    snooze_alert,
    transfer_stock,
    update_category,
    update_product,
    update_stock_settings,
    update_supplier_order_status,
)

router = APIRouter()


DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentTenant = Annotated[uuid.UUID, Depends(get_tenant_id)]
ReadUser = Annotated[dict, Depends(require_role("admin", "warehouse", "sales"))]
WriteUser = Annotated[dict, Depends(require_role("admin", "warehouse"))]

ACTOR_ID = "system"


def _require_feature_enabled(enabled: bool, detail: str) -> None:
    if not enabled:
        raise HTTPException(status_code=403, detail=detail)


def _api_reason_code(value: str) -> str:
    return value.lower()


def _enum_reason_code(value: str) -> ReasonCode:
    return ReasonCode(value.upper())
# ── Warehouse endpoints ───────────────────────────────────────


@router.get(
    "/warehouses",
    response_model=WarehouseList,
)
async def list_warehouses_endpoint(
    session: DbSession,
    _user: ReadUser,
    tenant_id: CurrentTenant,
    active_only: bool = Query(True),
) -> WarehouseList:
    warehouses = await list_warehouses(
        session,
        tenant_id,
        active_only=active_only,
    )
    return WarehouseList(
        items=[WarehouseResponse.model_validate(w) for w in warehouses],
        total=len(warehouses),
    )


@router.get(
    "/warehouses/{warehouse_id}",
    response_model=WarehouseResponse,
)
async def get_warehouse_endpoint(
    warehouse_id: uuid.UUID,
    session: DbSession,
    _user: ReadUser,
    tenant_id: CurrentTenant,
) -> WarehouseResponse:
    warehouse = await get_warehouse(session, tenant_id, warehouse_id)
    if warehouse is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Warehouse not found",
        )
    return WarehouseResponse.model_validate(warehouse)


@router.post(
    "/warehouses",
    response_model=WarehouseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_warehouse_endpoint(
    data: WarehouseCreate,
    session: DbSession,
    _user: WriteUser,
    tenant_id: CurrentTenant,
) -> WarehouseResponse:
    warehouse = await create_warehouse(
        session,
        tenant_id,
        name=data.name,
        code=data.code,
        location=data.location,
        address=data.address,
        contact_email=data.contact_email,
    )
    await session.commit()
    return WarehouseResponse.model_validate(warehouse)


# ── Transfer endpoints ────────────────────────────────────────


@router.post(
    "/transfers",
    response_model=TransferResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_transfer_endpoint(
    data: TransferRequest,
    session: DbSession,
    _user: WriteUser,
    tenant_id: CurrentTenant,
) -> TransferResponse:
    try:
        transfer = await transfer_stock(
            session,
            tenant_id,
            from_warehouse_id=data.from_warehouse_id,
            to_warehouse_id=data.to_warehouse_id,
            product_id=data.product_id,
            quantity=data.quantity,
            actor_id=ACTOR_ID,
            notes=data.notes,
        )
        await session.commit()
        return TransferResponse.model_validate(transfer)
    except TransferValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except InsufficientStockError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": f"Insufficient stock: {exc.available} units available",
                "available": exc.available,
                "requested": exc.requested,
            },
        ) from exc


# ── Reorder point endpoints ────────────────────────────────────


@router.post(
    "/reorder-points/compute",
    response_model=ReorderPointComputeResponse,
)
async def compute_reorder_points_endpoint(
    data: ReorderPointComputeRequest,
    session: DbSession,
    _user: ReadUser,
    tenant_id: CurrentTenant,
) -> ReorderPointComputeResponse:
    """Preview reorder point computation — dry run, no changes saved."""
    candidates, skipped = await compute_reorder_points_preview(
        session,
        tenant_id,
        safety_factor=data.safety_factor,
        demand_lookback_days=data.lookback_days,
        lead_time_lookback_days=data.lookback_days_lead_time,
        warehouse_id=data.warehouse_id,
    )

    def _make_row(d: dict) -> ReorderPointPreviewRow:
        return ReorderPointPreviewRow(
            stock_id=d.get("stock_id", 0),
            product_id=d["product_id"],
            product_name=d.get("product_name", ""),
            warehouse_id=d["warehouse_id"],
            warehouse_name=d.get("warehouse_name", ""),
            current_quantity=d.get("current_quantity", 0.0),
            inventory_position=d.get("inventory_position"),
            on_order_qty=d.get("on_order_qty"),
            in_transit_qty=d.get("in_transit_qty"),
            reserved_qty=d.get("reserved_qty"),
            current_reorder_point=d.get("current_reorder_point", 0.0),
            policy_type=d.get("policy_type", "continuous"),
            target_stock_qty=d.get("target_stock_qty"),
            planning_horizon_days=d.get("planning_horizon_days"),
            effective_horizon_days=d.get("effective_horizon_days"),
            computed_reorder_point=None if d.get("skipped_reason") else float(d["reorder_point"]),
            avg_daily_usage=d.get("avg_daily_usage"),
            lead_time_days=d.get("lead_time_days"),
            lead_time_sample_count=d.get("lead_time_sample_count"),
            lead_time_confidence=d.get("lead_time_confidence"),
            review_cycle_days=d.get("review_cycle_days"),
            safety_stock=d.get("safety_stock"),
            target_stock_level=d.get("target_stock_level"),
            demand_basis=",".join(d.get("demand_reason") or []),
            movement_count=d.get("movement_count"),
            lead_time_source=d.get("lead_time_source"),
            quality_note=d.get("quality_note"),
            skip_reason=d.get("skipped_reason"),
            shared_history_context=d.get("shared_history_context"),
            is_selected=False,
            suggested_order_qty=d.get("suggested_order_qty"),
        )

    return ReorderPointComputeResponse(
        candidate_rows=[_make_row(c) for c in candidates],
        skipped_rows=[_make_row(s) for s in skipped],
        parameters={
            "safety_factor": data.safety_factor,
            "lookback_days": data.lookback_days,
            "lookback_days_lead_time": data.lookback_days_lead_time,
            "warehouse_id": str(data.warehouse_id) if data.warehouse_id else None,
        },
    )


@router.put(
    "/reorder-points/apply",
    response_model=ReorderPointApplyResponse,
)
async def apply_reorder_points_endpoint(
    data: ReorderPointApplyRequest,
    session: DbSession,
    _user: WriteUser,
    tenant_id: CurrentTenant,
) -> ReorderPointApplyResponse:
    """Apply reorder points to explicitly selected preview rows."""
    # Re-compute with same params to get the candidate rows
    candidates, _skipped = await compute_reorder_points_preview(
        session,
        tenant_id,
        safety_factor=data.safety_factor,
        demand_lookback_days=data.lookback_days,
        lead_time_lookback_days=data.lookback_days_lead_time,
        warehouse_id=data.warehouse_id,
    )

    # Filter candidates by UUID stock_id (from the re-computed preview).
    selected_stock_ids_set = {sid for sid in data.selected_stock_ids}
    selected_rows = [c for c in candidates if c.get("stock_id") in selected_stock_ids_set]

    result = await apply_reorder_points(
        session,
        tenant_id,
        selected_rows=selected_rows,
        safety_factor=data.safety_factor,
        demand_lookback_days=data.lookback_days,
        lead_time_lookback_days=data.lookback_days_lead_time,
    )
    await session.commit()
    return ReorderPointApplyResponse(
        updated_count=result["updated_count"],
        skipped_count=result["skipped_count"],
        run_parameters={
            "safety_factor": data.safety_factor,
            "lookback_days": data.lookback_days,
            "lookback_days_lead_time": data.lookback_days_lead_time,
            "warehouse_id": str(data.warehouse_id) if data.warehouse_id else None,
        },
    )


# ── Reason codes endpoint ─────────────────────────────────────


@router.get(
    "/reason-codes",
    response_model=ReasonCodeListResponse,
)
async def list_reason_codes(
    _user: ReadUser,
    tenant_id: CurrentTenant,
) -> ReasonCodeListResponse:
    items = [
        ReasonCodeItem(
            value=_api_reason_code(rc.value),
            label=rc.value.replace("_", " ").title(),
            user_selectable=_api_reason_code(rc.value) in USER_SELECTABLE_REASON_CODES,
        )
        for rc in ReasonCode
    ]
    return ReasonCodeListResponse(items=items)


# ── Stock adjustment endpoint ─────────────────────────────────


@router.post(
    "/adjustments",
    response_model=StockAdjustmentResponse,
    status_code=status.HTTP_201_CREATED,
    responses={202: {"model": ApprovalRequiredResponse}},
)
async def create_adjustment_endpoint(
    data: StockAdjustmentRequest,
    session: DbSession,
    user: WriteUser,
    tenant_id: CurrentTenant,
    actor_type: str = Header(default="user", alias="X-Actor-Type"),
    actor_id_header: str | None = Header(default=None, alias="X-Actor-Id"),
) -> StockAdjustmentResponse:
    # Validate reason code is user-selectable
    if data.reason_code not in USER_SELECTABLE_REASON_CODES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Invalid reason code: {data.reason_code}. "
            f"Must be one of: {', '.join(USER_SELECTABLE_REASON_CODES)}",
        )

    try:
        reason = _enum_reason_code(data.reason_code)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Unknown reason code: {data.reason_code}",
        )

    if actor_type not in {"user", "agent", "line_bot", "automation"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid X-Actor-Type header",
        )

    actor_id = actor_id_header or str(user.get("sub") or ACTOR_ID)

    if needs_approval(
        actor_type=actor_type,
        action="inventory.adjust",
        quantity=data.quantity_change,
    ):
        approval = await create_approval(
            session,
            action="inventory.adjust",
            entity_type="stock_adjustment",
            entity_id=None,
            requested_by=actor_id,
            requested_by_type=actor_type,
            context={
                "product_id": str(data.product_id),
                "warehouse_id": str(data.warehouse_id),
                "quantity_change": data.quantity_change,
                "reason_code": data.reason_code,
                "notes": data.notes,
            },
            tenant_id=tenant_id,
        )
        await session.commit()
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content=ApprovalRequiredResponse(
                approval_required=True,
                approval_request_id=approval.id,
                status=approval.status,
            ).model_dump(mode="json"),
        )

    try:
        result = await create_stock_adjustment(
            session,
            tenant_id,
            product_id=data.product_id,
            warehouse_id=data.warehouse_id,
            quantity_change=data.quantity_change,
            reason_code=reason,
            actor_id=actor_id,
            notes=data.notes,
        )
        await session.commit()
        return StockAdjustmentResponse(
            **{
                **result,
                "reason_code": _api_reason_code(str(result["reason_code"])),
            }
        )
    except TransferValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except InsufficientStockError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": f"Insufficient stock: {exc.available} units available",
                "available": exc.available,
                "requested": exc.requested,
            },
        ) from exc


# ── Product search endpoints ──────────────────────────────────


@router.get(
    "/products/search",
    response_model=ProductSearchResponse,
)
async def search_products_endpoint(
    session: DbSession,
    _user: ReadUser,
    tenant_id: CurrentTenant,
    q: str = Query("", max_length=100),
    category: str | None = Query(None, max_length=200),
    limit: int = Query(20, ge=1, le=500),
    offset: int = Query(0, ge=0),
    warehouse_id: uuid.UUID | None = Query(None),
    include_inactive: bool = Query(False),
    sort_by: str = Query("code", pattern="^(code|name|category|status|current_stock)$"),
    sort_dir: str = Query("asc", pattern="^(asc|desc)$"),
) -> ProductSearchResponse:
    stripped = q.strip()
    results, total = await search_products(
        session,
        tenant_id,
        stripped,
        warehouse_id=warehouse_id,
        category=category,
        include_inactive=include_inactive,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )
    return ProductSearchResponse(
        items=[ProductSearchResult(**r) for r in results],
        total=total,
    )


# ── Category endpoints ────────────────────────────────────────


@router.get(
    "/categories",
    response_model=CategoryListResponse,
)
async def list_categories_endpoint(
    session: DbSession,
    _user: ReadUser,
    tenant_id: CurrentTenant,
    q: str = Query("", max_length=200),
    active_only: bool = Query(True),
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> CategoryListResponse:
    items, total = await list_categories(
        session,
        tenant_id,
        q=q,
        active_only=active_only,
        limit=limit,
        offset=offset,
    )
    return CategoryListResponse(
        items=[CategoryResponse.model_validate(item) for item in items],
        total=total,
    )


@router.post(
    "/categories",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_category_endpoint(
    data: CategoryCreate,
    session: DbSession,
    _user: WriteUser,
    tenant_id: CurrentTenant,
) -> CategoryResponse:
    try:
        category = await create_category(session, tenant_id, data)
        await session.commit()
    except DuplicateCategoryNameError as exc:
        return JSONResponse(status_code=409, content=duplicate_category_name_response(exc))
    except ValidationError as exc:
        return JSONResponse(status_code=422, content=error_response(exc.errors))

    return CategoryResponse.model_validate(category)


@router.get(
    "/categories/{category_id}",
    response_model=CategoryResponse,
)
async def get_category_endpoint(
    category_id: uuid.UUID,
    session: DbSession,
    _user: ReadUser,
    tenant_id: CurrentTenant,
) -> CategoryResponse:
    category = await get_category(session, tenant_id, category_id)
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )
    return CategoryResponse.model_validate(category)


@router.put(
    "/categories/{category_id}",
    response_model=CategoryResponse,
)
async def update_category_endpoint(
    category_id: uuid.UUID,
    data: CategoryUpdate,
    session: DbSession,
    _user: WriteUser,
    tenant_id: CurrentTenant,
) -> CategoryResponse:
    try:
        category = await update_category(session, tenant_id, category_id, data)
        if category is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found",
            )
        await session.commit()
    except DuplicateCategoryNameError as exc:
        return JSONResponse(status_code=409, content=duplicate_category_name_response(exc))
    except ValidationError as exc:
        return JSONResponse(status_code=422, content=error_response(exc.errors))

    return CategoryResponse.model_validate(category)


@router.patch(
    "/categories/{category_id}/status",
    response_model=CategoryResponse,
)
async def update_category_status_endpoint(
    category_id: uuid.UUID,
    data: CategoryStatusUpdate,
    session: DbSession,
    _user: WriteUser,
    tenant_id: CurrentTenant,
) -> CategoryResponse:
    category = await set_category_status(
        session,
        tenant_id,
        category_id,
        is_active=data.is_active,
    )
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    await session.commit()
    return CategoryResponse.model_validate(category)


# ── Product creation endpoint ──────────────────────────────────


@router.post(
    "/products",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_product_endpoint(
    data: ProductCreate,
    session: DbSession,
    _user: WriteUser,
    tenant_id: CurrentTenant,
) -> ProductResponse:
    try:
        product = await create_product(session, tenant_id, data)
        await session.commit()
    except DuplicateProductCodeError as exc:
        return JSONResponse(status_code=409, content=duplicate_product_code_response(exc))
    except ValidationError as exc:
        return JSONResponse(status_code=422, content=error_response(exc.errors))
    return ProductResponse.model_validate(product)


@router.put(
    "/products/{product_id}",
    response_model=ProductResponse,
)
async def update_product_endpoint(
    product_id: uuid.UUID,
    data: ProductUpdate,
    session: DbSession,
    _user: WriteUser,
    tenant_id: CurrentTenant,
) -> ProductResponse:
    try:
        product = await update_product(session, tenant_id, product_id, data)
        if product is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found",
            )
        await session.commit()
    except DuplicateProductCodeError as exc:
        return JSONResponse(status_code=409, content=duplicate_product_code_response(exc))
    except ValidationError as exc:
        return JSONResponse(status_code=422, content=error_response(exc.errors))
    return ProductResponse.model_validate(product)


@router.patch(
    "/products/{product_id}/status",
    response_model=ProductResponse,
)
async def set_product_status_endpoint(
    product_id: uuid.UUID,
    data: ProductStatusUpdate,
    session: DbSession,
    _user: WriteUser,
    tenant_id: CurrentTenant,
) -> ProductResponse:
    product = await set_product_status(session, tenant_id, product_id, data.status)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    await session.commit()
    return ProductResponse.model_validate(product)


# ── Product detail endpoint ────────────────────────────────────


@router.get(
    "/products/{product_id}",
    response_model=ProductDetailResponse,
)
async def get_product_detail_endpoint(
    product_id: uuid.UUID,
    session: DbSession,
    _user: ReadUser,
    tenant_id: CurrentTenant,
    history_limit: int = Query(100, ge=1, le=500),
    history_offset: int = Query(0, ge=0),
) -> ProductDetailResponse:
    detail = await get_product_detail(
        session,
        tenant_id,
        product_id,
        history_limit=history_limit,
        history_offset=history_offset,
    )
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    return ProductDetailResponse(**detail)


# ── JSON-LD structured data endpoint ──────────────────────────


@router.get(
    "/products/{product_id}/jsonld",
    include_in_schema=False,
)
async def get_product_jsonld(
    product_id: uuid.UUID,
    session: DbSession,
    _user: ReadUser,
) -> JSONResponse:
    """Return schema.org Product JSON-LD structured data."""
    product = await session.get(Product, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    jsonld = generate_product_jsonld(product)
    return JSONResponse(content=jsonld, media_type="application/ld+json")


# ── AEO content endpoint ─────────────────────────────────────


@router.get(
    "/products/{product_id}/aeo",
    include_in_schema=False,
)
async def get_product_aeo(
    product_id: uuid.UUID,
    session: DbSession,
    _user: ReadUser,
) -> dict:
    """Return AEO-optimized content bundle for a product."""
    product = await session.get(Product, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    return generate_aeo_content(product)


# ── Stock query endpoints ─────────────────────────────────────


@router.get(
    "/stocks/{product_id}",
    response_model=list[InventoryStockResponse],
)
async def get_product_stocks(
    product_id: uuid.UUID,
    session: DbSession,
    _user: ReadUser,
    tenant_id: CurrentTenant,
    warehouse_id: uuid.UUID | None = Query(None),
) -> list[InventoryStockResponse]:
    stocks = await get_inventory_stocks(
        session,
        tenant_id,
        product_id,
        warehouse_id=warehouse_id,
    )
    return [InventoryStockResponse.model_validate(s) for s in stocks]


# ── Stock history endpoints ───────────────────────────────────


@router.get(
    "/stock-history/{stock_id}",
    response_model=StockHistoryResponse,
)
async def get_stock_history_by_stock_id(
    stock_id: uuid.UUID,
    session: DbSession,
    _user: ReadUser,
    tenant_id: CurrentTenant,
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    granularity: str = Query("event", pattern="^(event|daily)$"),
) -> StockHistoryResponse:
    """Return stock history for a specific inventory stock record.

    Resolves stock_id → product_id + warehouse_id then fetches history.
    """
    stock_stmt = select(InventoryStock).where(
        InventoryStock.id == stock_id,
        InventoryStock.tenant_id == tenant_id,
    )
    stock_result = await session.execute(stock_stmt)
    stock = stock_result.scalar_one_or_none()

    if stock is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stock record not found",
        )

    result = await get_stock_history(
        session,
        tenant_id,
        stock.product_id,
        stock.warehouse_id,
        start_date=start_date,
        end_date=end_date,
        granularity=granularity,
    )
    return StockHistoryResponse(**result)


@router.get(
    "/stock-history/product/{product_id}",
    response_model=dict,
)
async def get_stock_history_by_product(
    product_id: uuid.UUID,
    session: DbSession,
    _user: ReadUser,
    tenant_id: CurrentTenant,
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    granularity: str = Query("event", pattern="^(event|daily)$"),
) -> dict:
    """Return stock history for all warehouses of a product.

    Returns a map of warehouse_id → StockHistoryResponse.
    """
    stocks = await get_inventory_stocks(
        session,
        tenant_id,
        product_id,
    )

    result = {}
    for stock in stocks:
        wh_result = await get_stock_history(
            session,
            tenant_id,
            product_id,
            stock.warehouse_id,
            start_date=start_date,
            end_date=end_date,
            granularity=granularity,
        )
        result[str(stock.warehouse_id)] = wh_result

    return result


# ── Reorder alert endpoints ───────────────────────────────────


@router.get(
    "/alerts/reorder",
    response_model=ReorderAlertListResponse,
)
async def list_reorder_alerts_endpoint(
    session: DbSession,
    _user: ReadUser,
    tenant_id: CurrentTenant,
    status: str | None = Query(None, pattern="^(pending|acknowledged|resolved|snoozed|dismissed)$"),
    warehouse_id: uuid.UUID | None = Query(None),
    sort_by: str = Query("severity", pattern="^(severity|created_at|current_stock)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> ReorderAlertListResponse:
    items, total = await list_reorder_alerts(
        session,
        tenant_id,
        status_filter=status,
        warehouse_id=warehouse_id,
        sort_by=sort_by,
        limit=limit,
        offset=offset,
    )
    return ReorderAlertListResponse(
        items=[ReorderAlertItem(**i) for i in items],
        total=total,
    )


@router.put(
    "/alerts/reorder/{alert_id}/acknowledge",
    response_model=AcknowledgeAlertResponse,
)
async def acknowledge_alert_endpoint(
    alert_id: uuid.UUID,
    session: DbSession,
    _user: WriteUser,
    tenant_id: CurrentTenant,
) -> AcknowledgeAlertResponse:
    result = await acknowledge_alert(
        session,
        tenant_id,
        alert_id,
        actor_id=ACTOR_ID,
    )
    if result is None:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "already_resolved", "detail": "Alert not found or already resolved"},
        )
    await session.commit()
    return AcknowledgeAlertResponse(**result)


@router.put(
    "/alerts/reorder/{alert_id}/snooze",
    response_model=SnoozeAlertResponse,
)
async def snooze_alert_endpoint(
    alert_id: uuid.UUID,
    data: SnoozeAlertRequest,
    session: DbSession,
    _user: WriteUser,
    tenant_id: CurrentTenant,
) -> SnoozeAlertResponse:
    result = await snooze_alert(
        session,
        tenant_id,
        alert_id,
        actor_id=ACTOR_ID,
        duration_minutes=data.duration_minutes,
    )
    if result is None:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "already_resolved", "detail": "Alert not found or already closed"},
        )
    await session.commit()
    return SnoozeAlertResponse(**result)


@router.put(
    "/alerts/reorder/{alert_id}/dismiss",
    response_model=DismissAlertResponse,
)
async def dismiss_alert_endpoint(
    alert_id: uuid.UUID,
    session: DbSession,
    _user: WriteUser,
    tenant_id: CurrentTenant,
) -> DismissAlertResponse:
    result = await dismiss_alert(
        session,
        tenant_id,
        alert_id,
        actor_id=ACTOR_ID,
    )
    if result is None:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "already_resolved", "detail": "Alert not found or already closed"},
        )
    await session.commit()
    return DismissAlertResponse(**result)


# ── Supplier endpoints ────────────────────────────────────────


@router.get(
    "/suppliers",
    response_model=SupplierListResponse,
)
async def list_suppliers_endpoint(
    session: DbSession,
    _user: ReadUser,
    tenant_id: CurrentTenant,
    active_only: bool = Query(True),
) -> SupplierListResponse:
    suppliers = await list_suppliers(
        session,
        tenant_id,
        active_only=active_only,
    )
    return SupplierListResponse(
        items=[SupplierResponse(**s) for s in suppliers],
        total=len(suppliers),
    )


# ── Supplier order endpoints ──────────────────────────────────


@router.post(
    "/supplier-orders",
    response_model=SupplierOrderResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_supplier_order_endpoint(
    data: SupplierOrderCreate,
    session: DbSession,
    _user: WriteUser,
    tenant_id: CurrentTenant,
) -> SupplierOrderResponse:
    result = await create_supplier_order(
        session,
        tenant_id,
        supplier_id=data.supplier_id,
        order_date=data.order_date,
        expected_arrival_date=data.expected_arrival_date,
        lines=[line.model_dump() for line in data.lines],
        actor_id=ACTOR_ID,
    )
    await session.commit()
    return SupplierOrderResponse(**result)


@router.get(
    "/supplier-orders",
    response_model=SupplierOrderListResponse,
)
async def list_supplier_orders_endpoint(
    session: DbSession,
    _user: ReadUser,
    tenant_id: CurrentTenant,
    status_filter: str | None = Query(
        None,
        alias="status",
        pattern=r"^(pending|confirmed|shipped|partially_received|received|cancelled)$",
    ),
    supplier_id: uuid.UUID | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> SupplierOrderListResponse:
    items, total = await list_supplier_orders(
        session,
        tenant_id,
        status_filter=status_filter,
        supplier_id=supplier_id,
        limit=limit,
        offset=offset,
    )
    return SupplierOrderListResponse(
        items=items,
        total=total,
    )


@router.get(
    "/supplier-orders/{order_id}",
    response_model=SupplierOrderResponse,
)
async def get_supplier_order_endpoint(
    order_id: uuid.UUID,
    session: DbSession,
    _user: ReadUser,
    tenant_id: CurrentTenant,
) -> SupplierOrderResponse:
    order = await get_supplier_order(session, tenant_id, order_id)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier order not found",
        )
    return SupplierOrderResponse(**order)


@router.put(
    "/supplier-orders/{order_id}/status",
    response_model=SupplierOrderResponse,
)
async def update_supplier_order_status_endpoint(
    order_id: uuid.UUID,
    data: UpdateOrderStatusRequest,
    session: DbSession,
    _user: WriteUser,
    tenant_id: CurrentTenant,
) -> SupplierOrderResponse:
    try:
        result = await update_supplier_order_status(
            session,
            tenant_id,
            order_id,
            new_status=data.status,
            actor_id=ACTOR_ID,
            notes=data.notes,
        )
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Supplier order not found",
            )
        await session.commit()
        return SupplierOrderResponse(**result)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc


# ── Stock settings PATCH endpoint ─────────────────────────────────


@router.patch(
    "/stocks/{stock_id}",
    response_model=InventoryStockResponse,
)
async def update_stock_settings_endpoint(
    stock_id: uuid.UUID,
    data: StockSettingsUpdateRequest,
    session: DbSession,
    _user: WriteUser,
    tenant_id: CurrentTenant,
) -> InventoryStockResponse:
    stock = await update_stock_settings(
        session,
        tenant_id,
        stock_id,
        reorder_point=data.reorder_point,
        safety_factor=data.safety_factor,
        lead_time_days=data.lead_time_days,
        policy_type=data.policy_type,
        target_stock_qty=data.target_stock_qty,
        on_order_qty=data.on_order_qty,
        in_transit_qty=data.in_transit_qty,
        reserved_qty=data.reserved_qty,
        planning_horizon_days=data.planning_horizon_days,
        review_cycle_days=data.review_cycle_days,
    )
    if stock is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stock record not found",
        )
    await session.commit()
    return InventoryStockResponse.model_validate(stock)


# ── Monthly demand endpoint ──────────────────────────────────────


@router.get(
    "/products/{product_id}/monthly-demand",
    response_model=MonthlyDemandResponse,
)
async def get_monthly_demand_endpoint(
    product_id: uuid.UUID,
    session: DbSession,
    _user: ReadUser,
    tenant_id: CurrentTenant,
) -> MonthlyDemandResponse:
    result = await get_monthly_demand(session, tenant_id, product_id)
    return MonthlyDemandResponse(**result)


@router.get(
    "/products/{product_id}/planning-support",
    response_model=PlanningSupportResponse,
)
async def get_planning_support_endpoint(
    product_id: uuid.UUID,
    session: DbSession,
    _user: ReadUser,
    tenant_id: CurrentTenant,
    months: int = Query(12, ge=1, le=24),
    include_current_month: bool = Query(True),
) -> PlanningSupportResponse:
    _require_feature_enabled(
        settings.inventory_planning_support_enabled,
        "Planning support is disabled",
    )
    result = await get_planning_support(
        session,
        tenant_id,
        product_id,
        months=months,
        include_current_month=include_current_month,
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    return PlanningSupportResponse(**result)


# ── Sales history endpoint ───────────────────────────────────────


@router.get(
    "/products/{product_id}/sales-history",
    response_model=SalesHistoryResponse,
)
async def get_sales_history_endpoint(
    product_id: uuid.UUID,
    session: DbSession,
    _user: ReadUser,
    tenant_id: CurrentTenant,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> SalesHistoryResponse:
    result = await get_sales_history(
        session,
        tenant_id,
        product_id,
        limit=limit,
        offset=offset,
    )
    return SalesHistoryResponse(
        items=[SalesHistoryItem(**item) for item in result["items"]],
        total=result["total"],
    )


# ── Top customer endpoint ────────────────────────────────────────


@router.get(
    "/products/{product_id}/top-customer",
    response_model=TopCustomerResponse | None,
)
async def get_top_customer_endpoint(
    product_id: uuid.UUID,
    session: DbSession,
    _user: ReadUser,
    tenant_id: CurrentTenant,
) -> TopCustomerResponse | None:
    result = await get_top_customer(session, tenant_id, product_id)
    if result is None:
        return None
    return TopCustomerResponse(**result)


# ── Product supplier endpoint ────────────────────────────────────


@router.get(
    "/products/{product_id}/supplier",
    response_model=ProductSupplierResponse | None,
)
async def get_product_supplier_endpoint(
    product_id: uuid.UUID,
    session: DbSession,
    _user: ReadUser,
    tenant_id: CurrentTenant,
) -> ProductSupplierResponse | None:
    result = await get_product_supplier(session, tenant_id, product_id)
    if result is None:
        return None
    return ProductSupplierResponse(**result)


@router.put(
    "/supplier-orders/{order_id}/receive",
    response_model=SupplierOrderResponse,
)
async def receive_supplier_order_endpoint(
    order_id: uuid.UUID,
    data: ReceiveOrderRequest,
    session: DbSession,
    _user: WriteUser,
    tenant_id: CurrentTenant,
) -> SupplierOrderResponse:
    try:
        result = await receive_supplier_order(
            session,
            tenant_id,
            order_id,
            received_quantities=data.received_quantities,
            received_date=data.received_date,
            actor_id=ACTOR_ID,
        )
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Supplier order not found",
            )
        await session.commit()
        return SupplierOrderResponse(**result)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc


# ── Product audit log endpoint ────────────────────────────────


@router.get(
    "/products/{product_id}/audit-log",
    response_model=AuditLogListResponse,
)
async def get_product_audit_log_endpoint(
    product_id: uuid.UUID,
    session: DbSession,
    _user: ReadUser,
    tenant_id: CurrentTenant,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> AuditLogListResponse:
    result = await get_product_audit_log(
        session,
        tenant_id,
        product_id,
        limit=limit,
        offset=offset,
    )
    return AuditLogListResponse(**result)
