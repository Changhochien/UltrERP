"""Orders API routes — create, list, get orders."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from common.auth import require_role
from common.database import get_db
from common.tenant import DEFAULT_TENANT_ID
from domains.line.notification import notify_new_order
from domains.orders.schemas import (
    PAYMENT_TERMS_CONFIG,
    OrderCreate,
    OrderLineResponse,
    OrderListItem,
    OrderListResponse,
    OrderResponse,
    OrderStatus,
    OrderStatusUpdate,
    PaymentTermsItem,
    PaymentTermsListResponse,
    StockCheckResponse,
    WarehouseStockInfo,
)
from domains.orders.services import (
    check_stock_availability,
    create_order,
    get_order,
    list_orders,
    update_order_status,
)

router = APIRouter()

DbSession = Annotated[AsyncSession, Depends(get_db)]
ReadUser = Annotated[dict, Depends(require_role("warehouse", "sales"))]
WriteUser = Annotated[dict, Depends(require_role("sales"))]

TENANT_ID = DEFAULT_TENANT_ID
ACTOR_ID = "system"


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
    data = await check_stock_availability(session, TENANT_ID, product_id)
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
    order = await create_order(session, data, tenant_id=TENANT_ID)
    response = _to_order_response(order)
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
    status: OrderStatus | None = Query(None),
    customer_id: uuid.UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> OrderListResponse:
    orders, total = await list_orders(
        session,
        tenant_id=TENANT_ID,
        status=status.value if status else None,
        customer_id=customer_id,
        page=page,
        page_size=page_size,
    )
    return OrderListResponse(
        items=[
            OrderListItem(
                id=o.id,
                tenant_id=o.tenant_id,
                order_number=o.order_number,
                status=o.status,
                customer_id=o.customer_id,
                payment_terms_code=o.payment_terms_code,
                total_amount=o.total_amount,
                created_at=o.created_at,
                updated_at=o.updated_at,
            )
            for o in orders
        ],
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
    order = await get_order(session, order_id, tenant_id=TENANT_ID)
    return _to_order_response(order)


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
    order = await update_order_status(
        session,
        order_id,
        body.new_status,
        tenant_id=TENANT_ID,
        actor_id=ACTOR_ID,
    )
    return _to_order_response(order)


@router.delete(
    "/{order_id}",
    response_model=OrderResponse,
)
async def cancel_order_endpoint(
    order_id: uuid.UUID,
    session: DbSession,
    _user: WriteUser,
) -> OrderResponse:
    order = await update_order_status(
        session,
        order_id,
        OrderStatus.CANCELLED,
        tenant_id=TENANT_ID,
        actor_id=ACTOR_ID,
    )
    return _to_order_response(order)


def _to_order_response(order) -> OrderResponse:
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
        tax_amount=order.tax_amount,
        total_amount=order.total_amount,
        invoice_id=order.invoice_id,
        notes=order.notes,
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
                unit_price=line.unit_price,
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
