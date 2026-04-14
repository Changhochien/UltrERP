"""MCP entrypoint for intelligence tools."""

from __future__ import annotations

import json
import uuid
from typing import Annotated

import jwt
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_http_headers
from pydantic import Field

from app.mcp_server import mcp
from common.config import settings
from common.database import AsyncSessionLocal
from domains.intelligence.service import (
	get_category_trends,
	get_product_affinity_map,
	get_customer_product_profile,
	get_customer_risk_signals,
	get_market_opportunities,
	get_prospect_gaps,
)


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


def _resolve_tenant_id() -> uuid.UUID:
	headers = get_http_headers() or {}
	if headers.get("x-api-key"):
		tenant_header = headers.get("x-tenant-id")
		if tenant_header:
			return _parse_uuid(tenant_header, "tenant_id")
		raise ToolError(
			json.dumps(
				{
					"code": "TENANT_REQUIRED",
					"message": "X-Tenant-ID is required for tenant-bound intelligence API keys",
					"retry": True,
				}
			)
		)

	auth_header = headers.get("authorization", "")
	if auth_header.startswith("Bearer "):
		token = auth_header[7:].strip()
		try:
			payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
		except jwt.InvalidTokenError as exc:
			raise ToolError(
				json.dumps(
					{
						"code": "INVALID_TOKEN",
						"message": "Invalid or expired Bearer token",
						"retry": True,
					}
				)
			) from exc

		tenant_id = payload.get("tenant_id")
		if not isinstance(tenant_id, str) or not tenant_id:
			raise ToolError(
				json.dumps(
					{
						"code": "INVALID_TOKEN",
						"message": "Invalid or expired Bearer token",
						"retry": True,
					}
				)
			)
		resolved_tenant = _parse_uuid(tenant_id, "tenant_id")
		tenant_header = headers.get("x-tenant-id")
		if tenant_header:
			header_tenant = _parse_uuid(tenant_header, "tenant_id")
			if header_tenant != resolved_tenant:
				raise ToolError(
					json.dumps(
						{
							"code": "INVALID_TENANT",
							"message": "X-Tenant-ID does not match the Bearer token tenant",
							"retry": False,
						}
					)
				)
		return resolved_tenant

	tenant_header = headers.get("x-tenant-id")
	if tenant_header:
		return _parse_uuid(tenant_header, "tenant_id")

	raise ToolError(
		json.dumps(
			{
				"code": "TENANT_REQUIRED",
				"message": "X-Tenant-ID or Authorization: Bearer token with tenant_id is required",
				"retry": True,
			}
		)
	)


@mcp.tool(annotations={"readOnlyHint": True})
async def intelligence_market_opportunities(
	period: Annotated[str, Field(description="Rolling period: last_30d, last_90d, or last_12m")] = "last_90d",
) -> dict:
	"""Return stabilized v1 market opportunity signals."""
	if period not in {"last_30d", "last_90d", "last_12m"}:
		raise ToolError(
			json.dumps(
				{
					"code": "VALIDATION_ERROR",
					"field": "period",
					"message": "period must be one of: last_30d, last_90d, last_12m",
					"retry": False,
				}
			)
		)

	tenant_id = _resolve_tenant_id()
	async with AsyncSessionLocal() as session:
		result = await get_market_opportunities(
			session,
			tenant_id,
			period=period,
		)

	return result.model_dump(mode="json")


@mcp.tool(annotations={"readOnlyHint": True})
async def intelligence_prospect_gaps(
	category: Annotated[str, Field(description="Target category name")],
	limit: Annotated[int, Field(description="Maximum number of prospects to return", ge=1, le=100)] = 20,
) -> dict:
	"""Return active non-buyers ranked as whitespace prospects for a target category."""
	if not category.strip():
		raise ToolError(
			json.dumps(
				{
					"code": "VALIDATION_ERROR",
					"field": "category",
					"message": "category is required",
					"retry": False,
				}
			)
		)

	tenant_id = _resolve_tenant_id()
	async with AsyncSessionLocal() as session:
		result = await get_prospect_gaps(
			session,
			tenant_id,
			category=category,
			limit=limit,
		)

	return result.model_dump(mode="json")


@mcp.tool(annotations={"readOnlyHint": True})
async def intelligence_customer_risk_signals(
	status_filter: Annotated[str, Field(description="Risk status filter: all, growing, at_risk, dormant, new, stable")] = "all",
	limit: Annotated[int, Field(description="Maximum number of customers to return", ge=1, le=200)] = 50,
) -> dict:
	"""Return ranked customer risk and growth signals across the tenant."""
	if status_filter not in {"all", "growing", "at_risk", "dormant", "new", "stable"}:
		raise ToolError(
			json.dumps(
				{
					"code": "VALIDATION_ERROR",
					"field": "status_filter",
					"message": "status_filter must be one of: all, growing, at_risk, dormant, new, stable",
					"retry": False,
				}
			)
		)

	tenant_id = _resolve_tenant_id()
	async with AsyncSessionLocal() as session:
		result = await get_customer_risk_signals(
			session,
			tenant_id,
			status_filter=status_filter,
			limit=limit,
		)

	return result.model_dump(mode="json")


@mcp.tool(annotations={"readOnlyHint": True})
async def intelligence_category_trends(
	period: Annotated[str, Field(description="Rolling comparison window: last_30d, last_90d, or last_12m")] = "last_90d",
) -> dict:
	"""Return category demand trends across rolling current vs prior periods."""
	if period not in {"last_30d", "last_90d", "last_12m"}:
		raise ToolError(
			json.dumps(
				{
					"code": "VALIDATION_ERROR",
					"field": "period",
					"message": "period must be one of: last_30d, last_90d, last_12m",
					"retry": False,
				}
			)
		)

	tenant_id = _resolve_tenant_id()
	async with AsyncSessionLocal() as session:
		result = await get_category_trends(
			session,
			tenant_id,
			period=period,
		)

	return result.model_dump(mode="json")


@mcp.tool(annotations={"readOnlyHint": True})
async def intelligence_product_affinity(
	min_shared: Annotated[int, Field(description="Minimum shared-customer threshold", ge=1, le=100)] = 2,
	limit: Annotated[int, Field(description="Maximum number of affinity pairs to return", ge=1, le=200)] = 50,
) -> dict:
	"""Return top product affinity pairs scored by customer-level Jaccard similarity."""
	tenant_id = _resolve_tenant_id()
	async with AsyncSessionLocal() as session:
		result = await get_product_affinity_map(
			session,
			tenant_id,
			min_shared=min_shared,
			limit=limit,
		)

	return result.model_dump(mode="json")


@mcp.tool(annotations={"readOnlyHint": True})
async def intelligence_customer_product_profile(
	customer_id: Annotated[str, Field(description="UUID of the customer to profile")],
) -> dict:
	"""Return a customer purchasing profile for call preparation and account review."""
	parsed_customer_id = _parse_uuid(customer_id, "customer_id")
	tenant_id = _resolve_tenant_id()
	async with AsyncSessionLocal() as session:
		try:
			profile = await get_customer_product_profile(session, parsed_customer_id, tenant_id)
		except ValueError as exc:
			raise ToolError(
				json.dumps(
					{
						"code": "NOT_FOUND",
						"field": "customer_id",
						"message": str(exc),
						"retry": False,
					}
				)
			) from exc

	return profile.model_dump(mode="json")