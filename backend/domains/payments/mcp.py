"""MCP tools for the Payments domain."""

from __future__ import annotations

import json
import uuid
from typing import Annotated

from fastmcp.exceptions import ToolError
from pydantic import Field

from app.mcp_server import mcp
from common.database import AsyncSessionLocal
from common.tenant import DEFAULT_TENANT_ID
from domains.payments.schemas import PaymentListItem, PaymentResponse
from domains.payments.services import get_payment, list_payments


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


def _not_found(payment_id: str) -> ToolError:
    return ToolError(
        json.dumps(
            {
                "code": "NOT_FOUND",
                "entity_type": "payment",
                "entity_id": payment_id,
                "message": f"Payment {payment_id} not found",
                "retry": False,
            }
        )
    )


@mcp.tool(annotations={"readOnlyHint": True})
async def payments_list(
    invoice_id: Annotated[
        str | None,
        Field(description="Filter by invoice UUID"),
    ] = None,
    customer_id: Annotated[
        str | None,
        Field(description="Filter by customer UUID"),
    ] = None,
    page: Annotated[int, Field(description="Page number", ge=1)] = 1,
    page_size: Annotated[int, Field(description="Results per page", ge=1, le=100)] = 20,
) -> dict:
    """List payments with optional invoice and customer filters."""
    invoice_uuid = _parse_uuid(invoice_id, "invoice_id") if invoice_id else None
    customer_uuid = _parse_uuid(customer_id, "customer_id") if customer_id else None
    async with AsyncSessionLocal() as session:
        payments, total = await list_payments(
            session,
            DEFAULT_TENANT_ID,
            invoice_id=invoice_uuid,
            customer_id=customer_uuid,
            page=page,
            page_size=page_size,
        )
        return {
            "payments": [
                PaymentListItem.model_validate(payment).model_dump(mode="json")
                for payment in payments
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        }


@mcp.tool(annotations={"readOnlyHint": True})
async def payments_get(
    payment_id: Annotated[str, Field(description="UUID of the payment")],
) -> dict:
    """Get full payment details by ID."""
    pid = _parse_uuid(payment_id, "payment_id")
    async with AsyncSessionLocal() as session:
        payment = await get_payment(session, DEFAULT_TENANT_ID, pid)
        if payment is None:
            raise _not_found(payment_id)
        return PaymentResponse.model_validate(payment).model_dump(mode="json")