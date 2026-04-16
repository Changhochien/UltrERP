"""MCP entrypoint for intelligence tools."""

from __future__ import annotations

import json
import uuid
from datetime import date
from typing import Annotated

from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_http_headers
from pydantic import Field

from app.mcp_identity import parse_uuid, resolve_tenant_id_from_headers
from app.mcp_server import mcp
from common.config import settings
from common.database import AsyncSessionLocal
from domains.intelligence.service import (
	get_category_trends,
	get_customer_buying_behavior,
	get_product_affinity_map,
	get_customer_product_profile,
	get_customer_risk_signals,
	get_market_opportunities,
	get_product_performance,
	get_prospect_gaps,
	get_revenue_diagnosis,
)


def _parse_uuid(value: str, field: str) -> uuid.UUID:
	return parse_uuid(value, field)


def _resolve_tenant_id() -> uuid.UUID:
	return resolve_tenant_id_from_headers(get_http_headers() or {})


def _require_feature_enabled(enabled: bool, message: str) -> None:
	if enabled:
		return
	raise ToolError(
		json.dumps(
			{
				"code": "FEATURE_DISABLED",
				"message": message,
				"retry": False,
			}
		)
	)


@mcp.tool(annotations={"readOnlyHint": True})
async def intelligence_market_opportunities(
	period: Annotated[str, Field(description="Rolling period: last_30d, last_90d, or last_12m")] = "last_90d",
) -> dict:
	"""Return stabilized v1 market opportunity signals."""
	_require_feature_enabled(
		settings.intelligence_market_opportunities_enabled,
		"Market opportunity analysis is disabled",
	)
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
async def intelligence_customer_buying_behavior(
	customer_type: Annotated[str, Field(description="dealer | end_user | unknown | all")] = "dealer",
	period: Annotated[str, Field(description="Window length: 3m, 6m, or 12m")] = "12m",
	limit: Annotated[int, Field(description="Maximum number of rows to return", ge=1, le=100)] = 20,
	include_current_month: Annotated[bool, Field(description="Include the in-progress current month in the selected window")] = False,
) -> dict:
	"""Return segment-aware customer buying behavior and cross-sell evidence."""
	_require_feature_enabled(
		settings.intelligence_customer_buying_behavior_enabled,
		"Customer buying behavior is disabled",
	)
	if customer_type not in {"dealer", "end_user", "unknown", "all"}:
		raise ToolError(
			json.dumps(
				{
					"code": "VALIDATION_ERROR",
					"field": "customer_type",
					"message": "customer_type must be one of: dealer, end_user, unknown, all",
					"retry": False,
				}
			)
		)
	if period not in {"3m", "6m", "12m"}:
		raise ToolError(
			json.dumps(
				{
					"code": "VALIDATION_ERROR",
					"field": "period",
					"message": "period must be one of: 3m, 6m, 12m",
					"retry": False,
				}
			)
		)

	tenant_id = _resolve_tenant_id()
	async with AsyncSessionLocal() as session:
		result = await get_customer_buying_behavior(
			session,
			tenant_id,
			customer_type=customer_type,
			period=period,  # type: ignore[arg-type]
			limit=limit,
			include_current_month=include_current_month,
		)

	return result.model_dump(mode="json")


@mcp.tool(annotations={"readOnlyHint": True})
async def intelligence_product_performance(
	category: Annotated[str | None, Field(description="Optional snapshot category filter")] = None,
	lifecycle_stage: Annotated[
		str | None,
		Field(description="Optional lifecycle stage filter: new, end_of_life, declining, growing, mature, or stable"),
	] = None,
	limit: Annotated[int, Field(description="Maximum number of products to return", ge=1, le=200)] = 50,
	include_current_month: Annotated[bool, Field(description="Include the in-progress current month in the comparison window")] = False,
) -> dict:
	"""Return ranked product performance with lifecycle stage classification."""
	_require_feature_enabled(
		settings.intelligence_product_performance_enabled,
		"Product performance analysis is disabled",
	)
	normalized_category = category.strip() if category is not None else None
	if category is not None and not normalized_category:
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
	if lifecycle_stage is not None and lifecycle_stage not in {
		"new",
		"end_of_life",
		"declining",
		"growing",
		"mature",
		"stable",
	}:
		raise ToolError(
			json.dumps(
				{
					"code": "VALIDATION_ERROR",
					"field": "lifecycle_stage",
					"message": "lifecycle_stage must be one of: new, end_of_life, declining, growing, mature, stable",
					"retry": False,
				}
			)
		)

	tenant_id = _resolve_tenant_id()
	async with AsyncSessionLocal() as session:
		result = await get_product_performance(
			session,
			tenant_id,
			category=normalized_category,
			lifecycle_stage=lifecycle_stage,  # type: ignore[arg-type]
			limit=limit,
			include_current_month=include_current_month,
		)

	return result.model_dump(mode="json")


@mcp.tool(annotations={"readOnlyHint": True})
async def intelligence_revenue_diagnosis(
	period: Annotated[str, Field(description="Comparison window length: 1m, 3m, 6m, or 12m")] = "1m",
	anchor_month: Annotated[str | None, Field(description="Inclusive anchor month in YYYY-MM-DD format")] = None,
	category: Annotated[str | None, Field(description="Optional snapshot category filter")] = None,
	limit: Annotated[int, Field(description="Maximum number of drivers to return", ge=1, le=100)] = 20,
) -> dict:
	"""Return price, volume, and mix decomposition for a monthly revenue comparison window."""
	_require_feature_enabled(
		settings.intelligence_revenue_diagnosis_enabled,
		"Revenue diagnosis is disabled",
	)
	if period not in {"1m", "3m", "6m", "12m"}:
		raise ToolError(
			json.dumps(
				{
					"code": "VALIDATION_ERROR",
					"field": "period",
					"message": "period must be one of: 1m, 3m, 6m, 12m",
					"retry": False,
				}
			)
		)
	normalized_category = category.strip() if category is not None else None
	if category is not None and not normalized_category:
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
	parsed_anchor_month: date | None = None
	if anchor_month is not None:
		try:
			parsed_anchor_month = date.fromisoformat(anchor_month)
		except ValueError as exc:
			raise ToolError(
				json.dumps(
					{
						"code": "VALIDATION_ERROR",
						"field": "anchor_month",
						"message": "anchor_month must be an ISO date in YYYY-MM-DD format",
						"retry": False,
					}
				)
			) from exc

	tenant_id = _resolve_tenant_id()
	async with AsyncSessionLocal() as session:
		try:
			result = await get_revenue_diagnosis(
				session,
				tenant_id,
				period=period,
				anchor_month=parsed_anchor_month,
				category=normalized_category,
				limit=limit,
			)
		except ValueError as exc:
			raise ToolError(
				json.dumps(
					{
						"code": "VALIDATION_ERROR",
						"field": "anchor_month",
						"message": str(exc),
						"retry": False,
					}
				)
			) from exc

	return result.model_dump(mode="json")


@mcp.tool(annotations={"readOnlyHint": True})
async def intelligence_prospect_gaps(
	category: Annotated[str, Field(description="Target category name")],
	customer_type: Annotated[str, Field(description="dealer | end_user | unknown | all")] = "dealer",
	limit: Annotated[int, Field(description="Maximum number of prospects to return", ge=1, le=100)] = 20,
) -> dict:
	"""Return active non-buyers ranked as whitespace prospects for a target category."""
	_require_feature_enabled(
		settings.intelligence_prospect_gaps_enabled,
		"Prospect gap analysis is disabled",
	)
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
	if customer_type not in {"dealer", "end_user", "unknown", "all"}:
		raise ToolError(
			json.dumps(
				{
					"code": "VALIDATION_ERROR",
					"field": "customer_type",
					"message": "customer_type must be one of: dealer, end_user, unknown, all",
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
			customer_type=customer_type,
			limit=limit,
		)

	return result.model_dump(mode="json")


@mcp.tool(annotations={"readOnlyHint": True})
async def intelligence_customer_risk_signals(
	status_filter: Annotated[str, Field(description="Risk status filter: all, growing, at_risk, dormant, new, stable")] = "all",
	limit: Annotated[int, Field(description="Maximum number of customers to return", ge=1, le=200)] = 50,
) -> dict:
	"""Return ranked customer risk and growth signals across the tenant."""
	_require_feature_enabled(
		settings.intelligence_customer_risk_signals_enabled,
		"Customer risk signals are disabled",
	)
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
	_require_feature_enabled(
		settings.intelligence_category_trends_enabled,
		"Category trend analysis is disabled",
	)
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
	_require_feature_enabled(
		settings.intelligence_product_affinity_enabled,
		"Product affinity analysis is disabled",
	)
	if min_shared < 1 or limit < 1:
		raise ToolError(
			json.dumps(
				{
					"code": "VALIDATION_ERROR",
					"message": f"min_shared and limit must be >= 1, got min_shared={min_shared}, limit={limit}",
					"retry": False,
				}
			)
		)
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