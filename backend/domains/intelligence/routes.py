"""Routes for the intelligence domain."""

from datetime import date, datetime, timedelta, UTC
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from common.auth import require_role
from common.config import settings
from common.database import get_db

from domains.intelligence.schemas import (
	CategoryTrends,
	CustomerBuyingBehavior,
	MarketOpportunities,
	CustomerProductProfile,
	ProductPerformance,
	ProspectGaps,
	CustomerRiskSignals,
	ProductAffinityMap,
	RevenueDiagnosis,
)
from domains.intelligence.service import (
	get_category_trends,
	get_customer_buying_behavior,
	get_customer_product_profile,
	get_customer_risk_signals,
	get_market_opportunities,
	get_prospect_gaps,
	get_product_affinity_map,
	get_product_performance,
	get_revenue_diagnosis,
)
from domains.product_analytics.service import refresh_sales_monthly_range

router = APIRouter()
DbSession = Annotated[AsyncSession, Depends(get_db)]

# Sales, admin, and owner users can read commercial intelligence.
IntelligenceReadUser = Annotated[dict, Depends(require_role("admin", "owner", "sales"))]


def _require_feature_enabled(enabled: bool, detail: str) -> None:
	if not enabled:
		raise HTTPException(status_code=403, detail=detail)


@router.get("/customers/risk-signals", response_model=CustomerRiskSignals)
async def customer_risk_signals(
	session: DbSession,
	user: IntelligenceReadUser,
	status: str = Query(default="all", pattern="^(all|growing|at_risk|dormant|new|stable)$"),
	limit: int = Query(default=50, ge=1, le=200),
) -> CustomerRiskSignals:
	_require_feature_enabled(
		settings.intelligence_customer_risk_signals_enabled,
		"Customer risk signals are disabled",
	)
	tenant_id = uuid.UUID(user["tenant_id"])
	return await get_customer_risk_signals(session, tenant_id, status_filter=status, limit=limit)  # type: ignore[arg-type]


@router.get("/customer-buying-behavior", response_model=CustomerBuyingBehavior)
async def customer_buying_behavior(
	session: DbSession,
	user: IntelligenceReadUser,
	customer_type: str = Query(default="dealer", pattern="^(dealer|end_user|unknown|all)$"),
	period: str = Query(default="12m", pattern="^(3m|6m|12m)$"),
	limit: int = Query(default=20, ge=1, le=100),
	include_current_month: bool = Query(default=False),
) -> CustomerBuyingBehavior:
	_require_feature_enabled(
		settings.intelligence_customer_buying_behavior_enabled,
		"Customer buying behavior is disabled",
	)
	tenant_id = uuid.UUID(user["tenant_id"])
	return await get_customer_buying_behavior(
		session,
		tenant_id,
		customer_type=customer_type,
		period=period,  # type: ignore[arg-type]
		limit=limit,
		include_current_month=include_current_month,
	)


@router.get("/revenue-diagnosis", response_model=RevenueDiagnosis)
async def revenue_diagnosis(
	session: DbSession,
	user: IntelligenceReadUser,
	period: str = Query(default="1m", pattern="^(1m|3m|6m|12m)$"),
	anchor_month: date | None = Query(default=None),
	category: str | None = Query(default=None),
	limit: int = Query(default=20, ge=1, le=100),
) -> RevenueDiagnosis:
	_require_feature_enabled(
		settings.intelligence_revenue_diagnosis_enabled,
		"Revenue diagnosis is disabled",
	)
	normalized_category = category.strip() if category is not None else None
	if category is not None and not normalized_category:
		raise HTTPException(status_code=400, detail="category is required")
	tenant_id = uuid.UUID(user["tenant_id"])
	try:
		return await get_revenue_diagnosis(
			session,
			tenant_id,
			period=period,  # type: ignore[arg-type]
			anchor_month=anchor_month,
			category=normalized_category,
			limit=limit,
		)
	except ValueError as exc:
		raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/product-performance", response_model=ProductPerformance)
async def product_performance(
	session: DbSession,
	user: IntelligenceReadUser,
	category: str | None = Query(default=None),
	lifecycle_stage: str | None = Query(default=None, pattern="^(new|end_of_life|declining|growing|mature|stable)$"),
	limit: int = Query(default=50, ge=1, le=200),
	include_current_month: bool = Query(default=False),
) -> ProductPerformance:
	_require_feature_enabled(
		settings.intelligence_product_performance_enabled,
		"Product performance analysis is disabled",
	)
	normalized_category = category.strip() if category is not None else None
	if category is not None and not normalized_category:
		raise HTTPException(status_code=400, detail="category is required")
	tenant_id = uuid.UUID(user["tenant_id"])
	return await get_product_performance(
		session,
		tenant_id,
		category=normalized_category,
		lifecycle_stage=lifecycle_stage,  # type: ignore[arg-type]
		limit=limit,
		include_current_month=include_current_month,
	)


@router.get("/prospect-gaps", response_model=ProspectGaps)
async def prospect_gaps(
	session: DbSession,
	user: IntelligenceReadUser,
	category: str = Query(min_length=1),
	customer_type: str = Query(default="dealer", pattern="^(dealer|end_user|unknown|all)$"),
	limit: int = Query(default=20, ge=1, le=100),
) -> ProspectGaps:
	_require_feature_enabled(
		settings.intelligence_prospect_gaps_enabled,
		"Prospect gap analysis is disabled",
	)
	if not category.strip():
		raise HTTPException(status_code=400, detail="category is required")
	tenant_id = uuid.UUID(user["tenant_id"])
	return await get_prospect_gaps(
		session,
		tenant_id,
		category=category.strip(),
		customer_type=customer_type,
		limit=limit,
	)


@router.get("/market-opportunities", response_model=MarketOpportunities)
async def market_opportunities(
	session: DbSession,
	user: IntelligenceReadUser,
	period: str = Query(default="last_90d", pattern="^(last_30d|last_90d|last_12m)$"),
) -> MarketOpportunities:
	_require_feature_enabled(
		settings.intelligence_market_opportunities_enabled,
		"Market opportunity analysis is disabled",
	)
	tenant_id = uuid.UUID(user["tenant_id"])
	return await get_market_opportunities(session, tenant_id, period=period)  # type: ignore[arg-type]


@router.get("/category-trends", response_model=CategoryTrends)
async def category_trends(
	session: DbSession,
	user: IntelligenceReadUser,
	period: str = Query(default="last_90d", pattern="^(last_30d|last_90d|last_12m)$"),
) -> CategoryTrends:
	_require_feature_enabled(
		settings.intelligence_category_trends_enabled,
		"Category trend analysis is disabled",
	)
	tenant_id = uuid.UUID(user["tenant_id"])
	return await get_category_trends(session, tenant_id, period=period)  # type: ignore[arg-type]


@router.get("/affinity", response_model=ProductAffinityMap)
async def product_affinity_map(
	session: DbSession,
	user: IntelligenceReadUser,
	min_shared: int = Query(default=2, ge=1, le=100),
	limit: int = Query(default=50, ge=1, le=200),
) -> ProductAffinityMap:
	_require_feature_enabled(
		settings.intelligence_product_affinity_enabled,
		"Product affinity analysis is disabled",
	)
	tenant_id = uuid.UUID(user["tenant_id"])
	return await get_product_affinity_map(
		session,
		tenant_id,
		min_shared=min_shared,
		limit=limit,
	)


@router.get("/customers/{customer_id}/product-profile", response_model=CustomerProductProfile)
async def customer_product_profile(
	customer_id: uuid.UUID,
	session: DbSession,
	user: IntelligenceReadUser,
) -> CustomerProductProfile | JSONResponse:
	tenant_id = uuid.UUID(user["tenant_id"])
	try:
		return await get_customer_product_profile(session, customer_id, tenant_id)
	except ValueError as exc:
		return JSONResponse(status_code=404, content={"detail": str(exc)})


# Admin-only route for refreshing sales monthly aggregates
AdminUser = Annotated[dict, Depends(require_role("admin"))]


@router.post("/refresh-sales-monthly", response_model=dict)
async def refresh_sales_monthly(
	session: DbSession,
	user: AdminUser,
	start_month: date = Query(description="Start month (first day of month, e.g. 2026-03-01)"),
	end_month: date = Query(description="End month (first day of month, e.g. 2026-03-01)"),
) -> dict:
	"""Refresh the sales monthly aggregates for the specified date range.

	This endpoint populates the SalesMonthly table with aggregated sales data
	for closed months, which is required for revenue diagnosis and other
	intelligence features to show historical comparisons.

	The current month is never aggregated (it uses live data instead).
	Only closed months can be refreshed.

	Typically, you would call this endpoint:
	- On initial setup to backfill historical data
	- Monthly after a month closes to populate its data
	"""
	_require_feature_enabled(
		settings.intelligence_revenue_diagnosis_enabled,
		"Revenue diagnosis is disabled",
	)
	tenant_id = uuid.UUID(user["tenant_id"])

	# Normalize to first of month
	start_month_normalized = start_month.replace(day=1)
	end_month_normalized = end_month.replace(day=1)

	# Validate range
	if end_month_normalized < start_month_normalized:
		raise HTTPException(status_code=400, detail="end_month must be on or after start_month")

	# Prevent refreshing the current month (it uses live data)
	current_month_start = datetime.now(tz=UTC).date().replace(day=1)
	if end_month_normalized >= current_month_start:
		raise HTTPException(
			status_code=400,
			detail=f"Cannot refresh months at or after the current month ({current_month_start}). "
			f"The current month uses live data. Only specify closed (past) months.",
		)

	try:
		result = await refresh_sales_monthly_range(
			session,
			tenant_id,
			start_month=start_month_normalized,
			end_month=end_month_normalized,
		)
		return {
			"refreshed_month_count": result.refreshed_month_count,
			"results": [
				{
					"month_start": r.month_start.isoformat(),
					"upserted_row_count": r.upserted_row_count,
					"deleted_row_count": r.deleted_row_count,
					"skipped_reason": r.skipped_reason,
					"skipped_line_count": len(r.skipped_lines),
				}
				for r in result.results
			],
		}
	except ValueError as exc:
		raise HTTPException(status_code=400, detail=str(exc)) from exc