"""
MCP tools for the Customers domain.

Tools:
  - customers_list: List customers with search and pagination
  - customers_get: Get a single customer by ID
  - customers_lookup_by_ban: Look up customer by Taiwan business number
"""
from __future__ import annotations

import json
import uuid
from typing import Annotated, Literal

from fastmcp.exceptions import ToolError
from pydantic import Field

from app.mcp_server import mcp
from common.database import AsyncSessionLocal
from common.tenant import DEFAULT_TENANT_ID
from domains.customers.models import Customer
from domains.customers.schemas import CustomerListParams
from domains.customers.service import (
	get_customer,
	list_customers,
	lookup_customer_by_ban,
)
from domains.customers.validators import validate_taiwan_business_number


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


def _serialize_customer(c: Customer) -> dict:
	"""Convert Customer model to a plain dict for JSON serialization."""
	return {
		"id": str(c.id),
		"company_name": c.company_name,
		"business_number": c.normalized_business_number,
		"billing_address": c.billing_address,
		"contact_name": c.contact_name,
		"contact_phone": c.contact_phone,
		"contact_email": c.contact_email,
		"credit_limit": str(c.credit_limit),
		"status": c.status,
		"version": c.version,
		"created_at": c.created_at.isoformat() if c.created_at else None,
		"updated_at": c.updated_at.isoformat() if c.updated_at else None,
	}


def _serialize_customer_summary(c: Customer) -> dict:
	"""Convert Customer model to a summary dict for list results."""
	return {
		"id": str(c.id),
		"company_name": c.company_name,
		"business_number": c.normalized_business_number,
		"contact_phone": c.contact_phone,
		"status": c.status,
	}


@mcp.tool(annotations={"readOnlyHint": True})
async def customers_list(
	search: Annotated[
		str | None,
		Field(description="Search by company name or business number"),
	] = None,
	status: Annotated[
		Literal["active", "inactive", "suspended"] | None,
		Field(description="Filter by status"),
	] = None,
	page: Annotated[int, Field(description="Page number", ge=1)] = 1,
	page_size: Annotated[int, Field(description="Results per page", ge=1, le=100)] = 20,
) -> dict:
	"""List customers with optional search and status filtering."""
	params = CustomerListParams(
		q=search, status=status, page=page, page_size=page_size,
	)
	async with AsyncSessionLocal() as session:
		# NOTE: Do NOT call set_tenant here — list_customers uses session.begin()
		# internally and calls set_tenant itself.
		customers, total = await list_customers(session, params, DEFAULT_TENANT_ID)
		return {
			"customers": [_serialize_customer_summary(c) for c in customers],
			"total": total,
			"page": page,
			"page_size": page_size,
		}


@mcp.tool(annotations={"readOnlyHint": True})
async def customers_get(
	customer_id: Annotated[str, Field(description="UUID of the customer")],
) -> dict:
	"""Get full customer details by ID."""
	cid = _parse_uuid(customer_id, "customer_id")
	async with AsyncSessionLocal() as session:
		# NOTE: Do NOT call set_tenant here — get_customer uses session.begin()
		# internally and calls set_tenant itself.
		customer = await get_customer(session, cid, DEFAULT_TENANT_ID)
		if customer is None:
			raise ToolError(json.dumps({
				"code": "NOT_FOUND",
				"entity_type": "customer",
				"entity_id": customer_id,
				"message": f"Customer {customer_id} not found",
				"retry": False,
			}))
		return _serialize_customer(customer)


@mcp.tool(annotations={"readOnlyHint": True})
async def customers_lookup_by_ban(
	business_number: Annotated[
		str,
		Field(description="Taiwan business number (統一編號, 8 digits)"),
	],
) -> dict:
	"""Look up a customer by Taiwan business number (統一編號)."""
	ban_result = validate_taiwan_business_number(business_number)
	if not ban_result.valid:
		raise ToolError(json.dumps({
			"code": "VALIDATION_ERROR",
			"field": "business_number",
			"message": ban_result.error or "Invalid Taiwan business number",
			"retry": False,
		}))
	async with AsyncSessionLocal() as session:
		# NOTE: Do NOT call set_tenant here — lookup_customer_by_ban uses
		# session.begin() internally and calls set_tenant itself.
		customer = await lookup_customer_by_ban(
			session, business_number, DEFAULT_TENANT_ID,
		)
		if customer is None:
			raise ToolError(json.dumps({
				"code": "NOT_FOUND",
				"entity_type": "customer",
				"entity_id": business_number,
				"message": f"No customer found with BAN {business_number}",
				"retry": False,
			}))
		return _serialize_customer(customer)
