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
from fastmcp.server.dependencies import get_http_headers
from pydantic import Field

from app.mcp_identity import parse_uuid, resolve_tenant_id_from_headers
from app.mcp_server import mcp
from common.errors import ValidationError, VersionConflictError
from common.database import AsyncSessionLocal
from domains.customers.models import Customer
from domains.customers.schemas import CustomerListParams, CustomerUpdate
from domains.customers.service import (
    get_customer,
    list_customers,
    lookup_customer_by_ban,
    update_customer,
)
from domains.customers.validators import validate_taiwan_business_number


def _parse_uuid(value: str, field: str) -> uuid.UUID:
    """Parse a UUID string, raising ToolError with structured JSON on failure."""
    return parse_uuid(value, field)


def _resolve_tenant_id() -> uuid.UUID:
    return resolve_tenant_id_from_headers(get_http_headers() or {})


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
        "customer_type": c.customer_type,
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
        "customer_type": c.customer_type,
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
        q=search,
        status=status,
        page=page,
        page_size=page_size,
    )
    tenant_id = _resolve_tenant_id()
    async with AsyncSessionLocal() as session:
        # NOTE: Do NOT call set_tenant here — list_customers uses session.begin()
        # internally and calls set_tenant itself.
        customers, total = await list_customers(session, params, tenant_id)
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
    tenant_id = _resolve_tenant_id()
    async with AsyncSessionLocal() as session:
        # NOTE: Do NOT call set_tenant here — get_customer uses session.begin()
        # internally and calls set_tenant itself.
        customer = await get_customer(session, cid, tenant_id)
        if customer is None:
            raise ToolError(
                json.dumps(
                    {
                        "code": "NOT_FOUND",
                        "entity_type": "customer",
                        "entity_id": customer_id,
                        "message": f"Customer {customer_id} not found",
                        "retry": False,
                    }
                )
            )
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
        raise ToolError(
            json.dumps(
                {
                    "code": "VALIDATION_ERROR",
                    "field": "business_number",
                    "message": ban_result.error or "Invalid Taiwan business number",
                    "retry": False,
                }
            )
        )
    tenant_id = _resolve_tenant_id()
    async with AsyncSessionLocal() as session:
        # NOTE: Do NOT call set_tenant here — lookup_customer_by_ban uses
        # session.begin() internally and calls set_tenant itself.
        customer = await lookup_customer_by_ban(
            session,
            business_number,
            tenant_id,
        )
        if customer is None:
            raise ToolError(
                json.dumps(
                    {
                        "code": "NOT_FOUND",
                        "entity_type": "customer",
                        "entity_id": business_number,
                        "message": f"No customer found with BAN {business_number}",
                        "retry": False,
                    }
                )
            )
        return _serialize_customer(customer)


@mcp.tool()
async def customers_update(
    customer_id: Annotated[str, Field(description="Customer UUID")],
    customer_type: Annotated[str, Field(description="dealer | end_user | unknown")],
) -> dict:
    """Update a customer's type classification."""
    valid_types = {"dealer", "end_user", "unknown"}
    if customer_type not in valid_types:
        raise ToolError(
            json.dumps(
                {
                    "code": "VALIDATION_ERROR",
                    "field": "customer_type",
                    "message": f"customer_type must be one of: {sorted(valid_types)}",
                    "retry": False,
                }
            )
        )

    cid = _parse_uuid(customer_id, "customer_id")
    tenant_id = _resolve_tenant_id()

    async with AsyncSessionLocal() as session:
        customer = await get_customer(session, cid, tenant_id)
        if customer is None:
            raise ToolError(
                json.dumps(
                    {
                        "code": "NOT_FOUND",
                        "entity_type": "customer",
                        "entity_id": customer_id,
                        "message": f"Customer {customer_id} not found",
                        "retry": False,
                    }
                )
            )

        try:
            updated = await update_customer(
                session,
                cid,
                CustomerUpdate(customer_type=customer_type, version=customer.version),
                tenant_id,
            )
        except VersionConflictError as exc:
            raise ToolError(
                json.dumps(
                    {
                        "code": "VERSION_CONFLICT",
                        "entity_type": "customer",
                        "entity_id": customer_id,
                        "message": f"Customer {customer_id} was modified by another request",
                        "expected_version": exc.expected,
                        "actual_version": exc.actual,
                        "retry": True,
                    }
                )
            ) from exc
        except ValidationError as exc:
            raise ToolError(
                json.dumps(
                    {
                        "code": "VALIDATION_ERROR",
                        "entity_type": "customer",
                        "entity_id": customer_id,
                        "errors": exc.errors,
                        "retry": False,
                    }
                )
            ) from exc
        if updated is None:
            raise ToolError(
                json.dumps(
                    {
                        "code": "NOT_FOUND",
                        "entity_type": "customer",
                        "entity_id": customer_id,
                        "message": f"Customer {customer_id} not found",
                        "retry": False,
                    }
                )
            )

    return {
        "success": True,
        "customer_id": customer_id,
        "customer_type": customer_type,
    }
