"""
MCP tools for the Inventory domain.

Tools:
  - inventory_check: Check stock levels for a specific product
  - inventory_search: Search products by code, name, or SKU
  - inventory_reorder_alerts: List low-stock reorder alerts
"""
from __future__ import annotations

import json
import uuid
from typing import Annotated

from fastmcp.exceptions import ToolError
from pydantic import Field

from app.mcp_server import mcp
from common.database import AsyncSessionLocal
from common.tenant import DEFAULT_TENANT_ID, set_tenant
from domains.inventory.services import (
	get_product_detail,
	list_reorder_alerts,
	search_products,
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


@mcp.tool(annotations={"readOnlyHint": True})
async def inventory_check(
	product_id: Annotated[str, Field(description="UUID of the product to check")],
) -> dict:
	"""Check inventory stock levels for a specific product across all warehouses."""
	pid = _parse_uuid(product_id, "product_id")
	async with AsyncSessionLocal() as session:
		await set_tenant(session, DEFAULT_TENANT_ID)
		result = await get_product_detail(session, DEFAULT_TENANT_ID, pid)
		if result is None:
			raise ToolError(json.dumps({
				"code": "NOT_FOUND",
				"entity_type": "product",
				"entity_id": product_id,
				"message": f"Product {product_id} not found",
				"retry": False,
			}))
		return result


@mcp.tool(annotations={"readOnlyHint": True})
async def inventory_search(
	query: Annotated[str, Field(description="Search text: product code, name, or SKU")],
	limit: Annotated[int, Field(description="Max results", default=20, ge=1, le=100)] = 20,
) -> list[dict]:
	"""Search products by code, name, or SKU using hybrid matching."""
	async with AsyncSessionLocal() as session:
		await set_tenant(session, DEFAULT_TENANT_ID)
		return await search_products(session, DEFAULT_TENANT_ID, query, limit=limit)


@mcp.tool(annotations={"readOnlyHint": True})
async def inventory_reorder_alerts(
	status_filter: Annotated[
		str | None,
		Field(description="Filter: PENDING, ACKNOWLEDGED, RESOLVED"),
	] = None,
	warehouse_id: Annotated[
		str | None,
		Field(description="Filter by warehouse UUID"),
	] = None,
) -> dict:
	"""List products below their reorder point (low stock alerts)."""
	wid = _parse_uuid(warehouse_id, "warehouse_id") if warehouse_id else None
	async with AsyncSessionLocal() as session:
		await set_tenant(session, DEFAULT_TENANT_ID)
		alerts, total = await list_reorder_alerts(
			session, DEFAULT_TENANT_ID,
			status_filter=status_filter,
			warehouse_id=wid,
		)
		return {"alerts": alerts, "total": total}
