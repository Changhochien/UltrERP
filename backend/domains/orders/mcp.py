"""MCP tools for the Orders domain."""

from __future__ import annotations

import json
import uuid
from typing import Annotated, Literal

from fastapi import HTTPException
from fastmcp.exceptions import ToolError
from pydantic import Field

from app.mcp_server import mcp
from common.database import AsyncSessionLocal
from common.tenant import DEFAULT_TENANT_ID
from domains.orders.schemas import OrderLineResponse, OrderListItem, OrderResponse
from domains.orders.services import build_order_workspace_meta, get_order, list_orders


def _parse_uuid(value: str, field: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError) as exc:
        raise ToolError(
            json.dumps(
                {
                    "code": "VALIDATION_ERROR",
                    "field": field,
                    "message": f"Invalid UUID: {value}",
                    "retry": False,
                }
            )
        ) from exc


def _not_found(entity_type: str, entity_id: str) -> ToolError:
    return ToolError(
        json.dumps(
            {
                "code": "NOT_FOUND",
                "entity_type": entity_type,
                "entity_id": entity_id,
                "message": f"{entity_type.replace('_', ' ').title()} {entity_id} not found",
                "retry": False,
            }
        )
    )


def _serialize_order_summary(order, meta: dict | None = None) -> dict:
    if meta is not None:
        execution = meta.get("execution")
        if execution is None:
            execution = derive_order_execution(order, invoice_payment_status=meta.get("invoice_payment_status"))
        invoice_number = meta.get("invoice_number")
        if invoice_number is None:
            invoice_number = getattr(order, "invoice_number", None)
        invoice_payment_status = meta.get("invoice_payment_status")
        if invoice_payment_status is None:
            invoice_payment_status = getattr(order, "invoice_payment_status", None)
        resolved_meta = {
            "sales_team": meta.get("sales_team") or getattr(order, "sales_team", None) or [],
            "total_commission": meta.get("total_commission") or getattr(order, "total_commission", 0),
            "invoice_number": invoice_number,
            "invoice_payment_status": invoice_payment_status,
            "execution": execution,
        }
    else:
        resolved_meta = {
            "sales_team": getattr(order, "sales_team", None) or [],
            "total_commission": getattr(order, "total_commission", 0),
            "invoice_number": getattr(order, "invoice_number", None),
            "invoice_payment_status": getattr(order, "invoice_payment_status", None),
            "execution": getattr(order, "execution", None),
        }
    return OrderListItem(
        id=order.id,
        tenant_id=order.tenant_id,
        customer_id=order.customer_id,
        order_number=order.order_number,
        status=order.status,
        payment_terms_code=order.payment_terms_code,
        total_amount=order.total_amount,
        **resolved_meta,
        legacy_header_snapshot=getattr(order, "legacy_header_snapshot", None),
        created_at=order.created_at,
        updated_at=order.updated_at,
    ).model_dump(mode="json")


def _serialize_order(order, meta: dict | None = None) -> dict:
    if meta is not None:
        execution = meta.get("execution")
        if execution is None:
            execution = derive_order_execution(order, invoice_payment_status=meta.get("invoice_payment_status"))
        invoice_number = meta.get("invoice_number")
        if invoice_number is None:
            invoice_number = getattr(order, "invoice_number", None)
        invoice_payment_status = meta.get("invoice_payment_status")
        if invoice_payment_status is None:
            invoice_payment_status = getattr(order, "invoice_payment_status", None)
        resolved_meta = {
            "sales_team": meta.get("sales_team") or getattr(order, "sales_team", None) or [],
            "total_commission": meta.get("total_commission") or getattr(order, "total_commission", 0),
            "invoice_number": invoice_number,
            "invoice_payment_status": invoice_payment_status,
            "execution": execution,
        }
    else:
        resolved_meta = {
            "sales_team": getattr(order, "sales_team", None) or [],
            "total_commission": getattr(order, "total_commission", 0),
            "invoice_number": getattr(order, "invoice_number", None),
            "invoice_payment_status": getattr(order, "invoice_payment_status", None),
            "execution": getattr(order, "execution", None),
        }
    return OrderResponse(
        id=order.id,
        tenant_id=order.tenant_id,
        customer_id=order.customer_id,
        customer_name=getattr(order, "customer", None) and order.customer.company_name,
        order_number=order.order_number,
        status=order.status,
        payment_terms_code=order.payment_terms_code,
        payment_terms_days=order.payment_terms_days,
        subtotal_amount=order.subtotal_amount,
        discount_amount=order.discount_amount,
        discount_percent=order.discount_percent,
        tax_amount=order.tax_amount,
        total_amount=order.total_amount,
        invoice_id=order.invoice_id,
        **resolved_meta,
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
    ).model_dump(mode="json")


@mcp.tool(annotations={"readOnlyHint": True})
async def orders_list(
    status: Annotated[
        Literal["pending", "confirmed", "shipped", "fulfilled", "cancelled"] | None,
        Field(description="Filter by order status"),
    ] = None,
    customer_id: Annotated[
        str | None,
        Field(description="Filter by customer UUID"),
    ] = None,
    page: Annotated[int, Field(description="Page number", ge=1)] = 1,
    page_size: Annotated[int, Field(description="Results per page", ge=1, le=100)] = 20,
) -> dict:
    """List orders with optional status and customer filters."""
    customer_uuid = _parse_uuid(customer_id, "customer_id") if customer_id else None
    async with AsyncSessionLocal() as session:
        orders, total = await list_orders(
            session,
            tenant_id=DEFAULT_TENANT_ID,
            status=status,
            customer_id=customer_uuid,
            page=page,
            page_size=page_size,
        )
        meta_by_order_id = await build_order_workspace_meta(session, orders, tenant_id=DEFAULT_TENANT_ID)
        return {
            "orders": [_serialize_order_summary(order, meta_by_order_id.get(order.id)) for order in orders],
            "total": total,
            "page": page,
            "page_size": page_size,
        }


@mcp.tool(annotations={"readOnlyHint": True})
async def orders_get(
    order_id: Annotated[str, Field(description="UUID of the order")],
) -> dict:
    """Get full order details by ID."""
    oid = _parse_uuid(order_id, "order_id")
    async with AsyncSessionLocal() as session:
        try:
            order = await get_order(session, oid, DEFAULT_TENANT_ID)
        except HTTPException as exc:
            if exc.status_code == 404:
                raise _not_found("order", order_id) from exc
            raise
        meta_by_order_id = await build_order_workspace_meta(session, [order], tenant_id=DEFAULT_TENANT_ID)
        return _serialize_order(order, meta_by_order_id.get(order.id))