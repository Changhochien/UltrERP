"""MCP tools for the Purchases domain."""

from __future__ import annotations

import json
import uuid
from typing import Annotated, Literal

from fastmcp.exceptions import ToolError
from pydantic import Field

from app.mcp_server import mcp
from common.database import AsyncSessionLocal
from common.tenant import DEFAULT_TENANT_ID, set_tenant
from domains.purchases.schemas import SupplierInvoiceListItem, SupplierInvoiceResponse
from domains.purchases.service import get_supplier_invoice, list_supplier_invoices


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


def _not_found(invoice_id: str) -> ToolError:
    return ToolError(
        json.dumps(
            {
                "code": "NOT_FOUND",
                "entity_type": "supplier_invoice",
                "entity_id": invoice_id,
                "message": f"Supplier invoice {invoice_id} not found",
                "retry": False,
            }
        )
    )


@mcp.tool(annotations={"readOnlyHint": True})
async def supplier_invoices_list(
    status_filter: Annotated[
        Literal["open", "paid", "voided"] | None,
        Field(description="Filter by supplier invoice status"),
    ] = None,
    supplier_id: Annotated[
        str | None,
        Field(description="Filter by supplier UUID"),
    ] = None,
    sort_by: Annotated[
        Literal["created_at", "invoice_date", "total_amount"],
        Field(description="Sort field"),
    ] = "created_at",
    sort_order: Annotated[
        Literal["asc", "desc"],
        Field(description="Sort direction"),
    ] = "desc",
    page: Annotated[int, Field(description="Page number", ge=1)] = 1,
    page_size: Annotated[int, Field(description="Results per page", ge=1, le=100)] = 20,
) -> dict:
    """List supplier invoices with status, supplier, and sort filters."""
    supplier_uuid = _parse_uuid(supplier_id, "supplier_id") if supplier_id else None
    async with AsyncSessionLocal() as session:
        items, total, status_totals = await list_supplier_invoices(
            session,
            DEFAULT_TENANT_ID,
            status_filter=status_filter,
            supplier_id=supplier_uuid,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size,
        )
        return {
            "supplier_invoices": [
                SupplierInvoiceListItem(**item).model_dump(mode="json") for item in items
            ],
            "status_totals": status_totals,
            "total": total,
            "page": page,
            "page_size": page_size,
        }


@mcp.tool(annotations={"readOnlyHint": True})
async def supplier_invoices_get(
    invoice_id: Annotated[str, Field(description="UUID of the supplier invoice")],
) -> dict:
    """Get full supplier invoice details by ID."""
    iid = _parse_uuid(invoice_id, "invoice_id")
    async with AsyncSessionLocal() as session:
        await set_tenant(session, DEFAULT_TENANT_ID)
        invoice = await get_supplier_invoice(session, iid, DEFAULT_TENANT_ID)
        if invoice is None:
            raise _not_found(invoice_id)
        return SupplierInvoiceResponse(**invoice).model_dump(mode="json")