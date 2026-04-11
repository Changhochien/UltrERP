"""
MCP tools for the Invoices domain.

Tools:
  - invoices_list: List invoices with payment status filtering
  - invoices_get: Get a single invoice with line items and payment summary
"""

from __future__ import annotations

import json
import uuid
from typing import Annotated, Literal

from fastmcp.exceptions import ToolError
from pydantic import Field

from app.mcp_server import mcp
from common.database import AsyncSessionLocal
from common.tenant import DEFAULT_TENANT_ID, set_tenant
from domains.invoices.schemas import InvoiceLineResponse, InvoiceListItem, InvoiceResponse
from domains.invoices.service import (
    compute_invoice_payment_summary,
    get_invoice,
    list_invoices,
)


def _parse_uuid(value: str, field: str) -> uuid.UUID:
    """Parse a UUID string, raising ToolError with structured JSON on failure."""
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError):
        raise ToolError(
            json.dumps(
                {
                    "code": "VALIDATION_ERROR",
                    "field": field,
                    "message": f"Invalid UUID: {value}",
                    "retry": False,
                }
            )
        )


def _serialize_list_item(inv: dict) -> dict:
    """Convert enriched invoice dict to the external MCP response shape."""
    return InvoiceListItem(
        id=inv["id"],
        invoice_number=inv["invoice_number"],
        invoice_date=inv["invoice_date"],
        customer_id=inv["customer_id"],
        order_id=inv.get("order_id"),
        currency_code=inv["currency_code"],
        total_amount=inv["total_amount"],
        status=inv["status"],
        legacy_header_snapshot=inv.get("legacy_header_snapshot"),
        created_at=inv["created_at"],
        amount_paid=inv["amount_paid"],
        outstanding_balance=inv["outstanding_balance"],
        payment_status=inv["payment_status"],
        due_date=inv["due_date"],
        days_overdue=inv["days_overdue"],
    ).model_dump(mode="json")


def _serialize_invoice(invoice, payment) -> dict:
    """Convert Invoice model + payment summary to the external MCP response shape."""
    return InvoiceResponse(
        id=invoice.id,
        invoice_number=invoice.invoice_number,
        invoice_date=invoice.invoice_date,
        customer_id=invoice.customer_id,
        order_id=invoice.order_id,
        buyer_type=invoice.buyer_type,
        buyer_identifier_snapshot=invoice.buyer_identifier_snapshot,
        currency_code=invoice.currency_code,
        subtotal_amount=invoice.subtotal_amount,
        tax_amount=invoice.tax_amount,
        total_amount=invoice.total_amount,
        status=invoice.status,
        version=invoice.version,
        legacy_header_snapshot=getattr(invoice, "legacy_header_snapshot", None),
        voided_at=getattr(invoice, "voided_at", None),
        void_reason=getattr(invoice, "void_reason", None),
        created_at=invoice.created_at,
        updated_at=invoice.updated_at,
        lines=[
            InvoiceLineResponse(
                id=line.id,
                product_id=line.product_id,
                product_code_snapshot=line.product_code_snapshot,
                description=line.description,
                quantity=line.quantity,
                unit_price=line.unit_price,
                subtotal_amount=line.subtotal_amount,
                tax_type=line.tax_type,
                tax_rate=line.tax_rate,
                tax_amount=line.tax_amount,
                total_amount=line.total_amount,
                zero_tax_rate_reason=line.zero_tax_rate_reason,
            )
            for line in invoice.lines
        ],
        amount_paid=payment["amount_paid"],
        outstanding_balance=payment["outstanding_balance"],
        payment_status=payment["payment_status"],
        due_date=payment["due_date"],
        days_overdue=payment["days_overdue"],
    ).model_dump(mode="json")


@mcp.tool(annotations={"readOnlyHint": True})
async def invoices_list(
    payment_status: Annotated[
        Literal["paid", "unpaid", "partial", "overdue"] | None,
        Field(description="Filter: paid, unpaid, partial, overdue"),
    ] = None,
    sort_by: Annotated[
        Literal["created_at", "total_amount", "invoice_number"],
        Field(description="Sort field"),
    ] = "created_at",
    sort_order: Annotated[
        Literal["asc", "desc"],
        Field(description="Sort direction"),
    ] = "desc",
    page: Annotated[int, Field(description="Page number", ge=1)] = 1,
    page_size: Annotated[int, Field(description="Results per page", ge=1, le=100)] = 20,
) -> dict:
    """List invoices with optional payment status filtering and sorting."""
    async with AsyncSessionLocal() as session:
        # NOTE: Do NOT call set_tenant here — list_invoices uses session.begin()
        # internally and calls set_tenant itself.
        invoices, total = await list_invoices(
            session,
            tenant_id=DEFAULT_TENANT_ID,
            page=page,
            page_size=page_size,
            payment_status=payment_status,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        return {
            "invoices": [_serialize_list_item(inv) for inv in invoices],
            "total": total,
            "page": page,
            "page_size": page_size,
        }


@mcp.tool(annotations={"readOnlyHint": True})
async def invoices_get(
    invoice_id: Annotated[str, Field(description="UUID of the invoice")],
) -> dict:
    """Get full invoice details including line items and payment summary."""
    iid = _parse_uuid(invoice_id, "invoice_id")
    async with AsyncSessionLocal() as session:
        await set_tenant(session, DEFAULT_TENANT_ID)
        invoice = await get_invoice(session, iid, DEFAULT_TENANT_ID)
        if invoice is None:
            raise ToolError(
                json.dumps(
                    {
                        "code": "NOT_FOUND",
                        "entity_type": "invoice",
                        "entity_id": invoice_id,
                        "message": f"Invoice {invoice_id} not found",
                        "retry": False,
                    }
                )
            )
        payment = await compute_invoice_payment_summary(
            session,
            invoice,
            DEFAULT_TENANT_ID,
        )
        return _serialize_invoice(invoice, payment)
