"""Orders API routes — create, list, get orders."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from common.auth import require_role
from common.database import get_db
from domains.line.notification import notify_new_order
from domains.orders.schemas import (
    PAYMENT_TERMS_CONFIG,
    OrderCreate,
    OrderExecutionSummary,
    OrderLineResponse,
    OrderListItem,
    OrderListResponse,
    OrderResponse,
    OrderSalesTeamAssignment,
    OrderStatus,
    OrderStatusUpdate,
    PaymentTermsItem,
    PaymentTermsListResponse,
    StockCheckResponse,
    WarehouseStockInfo,
)
from domains.orders.services import (
    build_order_workspace_meta,
    check_stock_availability,
    create_order,
    get_order,
    list_orders,
    update_order_status,
)

router = APIRouter()

DbSession = Annotated[AsyncSession, Depends(get_db)]
ReadUser = Annotated[dict, Depends(require_role("admin", "warehouse", "sales"))]
WriteUser = Annotated[dict, Depends(require_role("admin", "sales"))]


def _serialize_sales_team(raw_sales_team: list[dict[str, object]] | None) -> list[OrderSalesTeamAssignment]:
    return [OrderSalesTeamAssignment.model_validate(item) for item in (raw_sales_team or [])]


# ── Payment Terms reference ──────────────────────────────────


@router.get(
    "/payment-terms",
    response_model=PaymentTermsListResponse,
)
async def list_payment_terms_endpoint(_user: ReadUser) -> PaymentTermsListResponse:
    items = [
        PaymentTermsItem(
            code=code.value,
            label=cfg["label"],
            days=cfg["days"],
        )
        for code, cfg in PAYMENT_TERMS_CONFIG.items()
    ]
    return PaymentTermsListResponse(items=items, total=len(items))


# ── Stock check ──────────────────────────────────────────────


@router.get(
    "/check-stock",
    response_model=StockCheckResponse,
)
async def check_stock_endpoint(
    session: DbSession,
    _user: ReadUser,
    product_id: uuid.UUID = Query(...),
) -> StockCheckResponse:
    tenant_id = uuid.UUID(_user["tenant_id"])
    data = await check_stock_availability(session, tenant_id, product_id)
    return StockCheckResponse(
        product_id=data["product_id"],
        warehouses=[
            WarehouseStockInfo(
                warehouse_id=w["warehouse_id"],
                warehouse_name=w["warehouse_name"],
                available=w["available"],
            )
            for w in data["warehouses"]
        ],
        total_available=data["total_available"],
    )


# ── Order endpoints ──────────────────────────────────────────


@router.post(
    "",
    response_model=OrderResponse,
    status_code=201,
)
async def create_order_endpoint(
    data: OrderCreate,
    session: DbSession,
    background_tasks: BackgroundTasks,
    _user: WriteUser,
) -> OrderResponse:
    tenant_id = uuid.UUID(_user["tenant_id"])
    order = await create_order(session, data, tenant_id=tenant_id)
    response = await _to_order_response(session, order, tenant_id=tenant_id)
    background_tasks.add_task(
        notify_new_order,
        order_number=order.order_number,
        customer_name=response.customer_name or "Unknown",
        total_amount=str(order.total_amount or 0),
        line_count=len(data.lines),
    )
    return response


@router.get(
    "",
    response_model=OrderListResponse,
)
async def list_orders_endpoint(
    session: DbSession,
    _user: ReadUser,
    status: list[OrderStatus] | None = Query(None),
    workflow_view: Literal[
        "pending_intake",
        "ready_to_ship",
        "shipped_not_completed",
        "invoiced_not_paid",
    ]
    | None = Query(default=None),
    customer_id: uuid.UUID | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    search: str | None = Query(None),
    sort_by: Literal["created_at", "order_number", "total_amount", "status"] | None = Query(
        default=None
    ),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> OrderListResponse:
    tenant_id = uuid.UUID(_user["tenant_id"])
    orders, total = await list_orders(
        session,
        tenant_id=tenant_id,
        status=[item.value for item in status] if status else None,
        customer_id=customer_id,
        date_from=date_from,
        date_to=date_to,
        search=search,
        workflow_view=workflow_view,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )
    meta_by_order_id = await build_order_workspace_meta(session, orders, tenant_id=tenant_id)
    return OrderListResponse(
        items=[_to_order_list_item(o, meta_by_order_id.get(o.id)) for o in orders],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
)
async def get_order_endpoint(
    order_id: uuid.UUID,
    session: DbSession,
    _user: ReadUser,
) -> OrderResponse:
    tenant_id = uuid.UUID(_user["tenant_id"])
    order = await get_order(session, order_id, tenant_id=tenant_id)
    return await _to_order_response(session, order, tenant_id=tenant_id)


@router.patch(
    "/{order_id}/status",
    response_model=OrderResponse,
)
async def update_order_status_endpoint(
    order_id: uuid.UUID,
    body: OrderStatusUpdate,
    session: DbSession,
    _user: WriteUser,
) -> OrderResponse:
    tenant_id = uuid.UUID(_user["tenant_id"])
    order = await update_order_status(
        session,
        order_id,
        body.new_status,
        tenant_id=tenant_id,
        actor_id="system",
    )
    return await _to_order_response(session, order, tenant_id=tenant_id)


@router.delete(
    "/{order_id}",
    response_model=OrderResponse,
)
async def cancel_order_endpoint(
    order_id: uuid.UUID,
    session: DbSession,
    _user: WriteUser,
) -> OrderResponse:
    tenant_id = uuid.UUID(_user["tenant_id"])
    order = await update_order_status(
        session,
        order_id,
        OrderStatus.CANCELLED,
        tenant_id=tenant_id,
        actor_id="system",
    )
    return await _to_order_response(session, order, tenant_id=tenant_id)


def _to_order_list_item(order, meta: dict | None = None) -> OrderListItem:
    meta = meta or {}
    return OrderListItem(
        id=order.id,
        tenant_id=order.tenant_id,
        order_number=order.order_number,
        status=order.status,
        customer_id=order.customer_id,
        payment_terms_code=order.payment_terms_code,
        total_amount=order.total_amount,
        sales_team=_serialize_sales_team(getattr(order, "sales_team", None)),
        total_commission=getattr(order, "total_commission", 0),
        invoice_number=meta.get("invoice_number"),
        invoice_payment_status=meta.get("invoice_payment_status"),
        execution=OrderExecutionSummary(**meta.get("execution", {})),
        legacy_header_snapshot=getattr(order, "legacy_header_snapshot", None),
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


async def _to_order_response(
    session: DbSession,
    order,
    *,
    tenant_id: uuid.UUID,
) -> OrderResponse:
    meta_by_order_id = await build_order_workspace_meta(session, [order], tenant_id=tenant_id)
    meta = meta_by_order_id.get(order.id, {})
    return OrderResponse(
        id=order.id,
        tenant_id=order.tenant_id,
        order_number=order.order_number,
        status=order.status,
        customer_id=order.customer_id,
        customer_name=getattr(order, "customer", None) and order.customer.company_name,
        payment_terms_code=order.payment_terms_code,
        payment_terms_days=order.payment_terms_days,
        subtotal_amount=order.subtotal_amount,
        discount_amount=order.discount_amount,
        discount_percent=order.discount_percent,
        tax_amount=order.tax_amount,
        total_amount=order.total_amount,
        sales_team=_serialize_sales_team(getattr(order, "sales_team", None)),
        total_commission=getattr(order, "total_commission", 0),
        invoice_id=order.invoice_id,
        invoice_number=meta.get("invoice_number"),
        invoice_payment_status=meta.get("invoice_payment_status"),
        execution=OrderExecutionSummary(**meta.get("execution", {})),
        notes=order.notes,
        legacy_header_snapshot=getattr(order, "legacy_header_snapshot", None),
        created_by=order.created_by,
        created_at=order.created_at,
        updated_at=order.updated_at,
        confirmed_at=order.confirmed_at,
        lines=[
            OrderLineResponse(
                id=line.id,
                product_id=line.product_id,
                line_number=line.line_number,
                description=line.description,
                quantity=line.quantity,
                list_unit_price=line.list_unit_price,
                unit_price=line.unit_price,
                discount_amount=line.discount_amount,
                tax_policy_code=line.tax_policy_code,
                tax_type=line.tax_type,
                tax_rate=line.tax_rate,
                tax_amount=line.tax_amount,
                subtotal_amount=line.subtotal_amount,
                total_amount=line.total_amount,
                available_stock_snapshot=line.available_stock_snapshot,
                backorder_note=line.backorder_note,
            )
            for line in order.lines
        ],
    )
