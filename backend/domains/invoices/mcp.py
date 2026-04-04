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
		raise ToolError(json.dumps({
			"code": "VALIDATION_ERROR",
			"field": field,
			"message": f"Invalid UUID: {value}",
			"retry": False,
		}))


def _serialize_list_item(inv: dict) -> dict:
	"""Convert enriched invoice dict to JSON-safe types."""
	return {
		"id": str(inv["id"]),
		"invoice_number": inv["invoice_number"],
		"invoice_date": inv["invoice_date"].isoformat(),
		"customer_id": str(inv["customer_id"]),
		"currency_code": inv["currency_code"],
		"total_amount": str(inv["total_amount"]),
		"status": inv["status"],
		"created_at": inv["created_at"].isoformat(),
		"amount_paid": str(inv["amount_paid"]),
		"outstanding_balance": str(inv["outstanding_balance"]),
		"payment_status": inv["payment_status"],
		"due_date": inv["due_date"].isoformat(),
		"days_overdue": inv["days_overdue"],
	}


def _serialize_invoice(invoice, payment) -> dict:
	"""Convert Invoice model + payment summary to JSON-safe dict."""
	return {
		"id": str(invoice.id),
		"invoice_number": invoice.invoice_number,
		"customer_id": str(invoice.customer_id),
		"order_id": str(invoice.order_id) if invoice.order_id else None,
		"status": invoice.status,
		"invoice_date": invoice.invoice_date.isoformat(),
		"subtotal_amount": str(invoice.subtotal_amount),
		"tax_amount": str(invoice.tax_amount),
		"total_amount": str(invoice.total_amount),
		"line_items": [
			{
				"id": str(line.id),
				"line_number": line.line_number,
				"description": line.description,
				"quantity": str(line.quantity),
				"unit_price": str(line.unit_price),
				"subtotal_amount": str(line.subtotal_amount),
				"tax_amount": str(line.tax_amount),
				"total_amount": str(line.total_amount),
			}
			for line in invoice.lines
		],
		"amount_paid": str(payment["amount_paid"]),
		"outstanding_balance": str(payment["outstanding_balance"]),
		"payment_status": payment["payment_status"],
		"due_date": payment["due_date"].isoformat(),
		"days_overdue": payment["days_overdue"],
	}


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
			raise ToolError(json.dumps({
				"code": "NOT_FOUND",
				"entity_type": "invoice",
				"entity_id": invoice_id,
				"message": f"Invoice {invoice_id} not found",
				"retry": False,
			}))
		payment = await compute_invoice_payment_summary(
			session, invoice, DEFAULT_TENANT_ID,
		)
		return _serialize_invoice(invoice, payment)
