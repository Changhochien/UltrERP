"""Routes for the intelligence domain."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from common.auth import require_role
from common.database import get_db

from domains.intelligence.schemas import (
	CategoryTrends,
	MarketOpportunities,
	CustomerProductProfile,
	ProspectGaps,
	CustomerRiskSignals,
	ProductAffinityMap,
)
from domains.intelligence.service import (
	get_category_trends,
	get_customer_product_profile,
	get_customer_risk_signals,
	get_market_opportunities,
	get_prospect_gaps,
	get_product_affinity_map,
)

router = APIRouter()
DbSession = Annotated[AsyncSession, Depends(get_db)]

# Sales, admin, and owner users can read commercial intelligence.
IntelligenceReadUser = Annotated[dict, Depends(require_role("admin", "owner", "sales"))]


@router.get("/customers/risk-signals", response_model=CustomerRiskSignals)
async def customer_risk_signals(
	session: DbSession,
	user: IntelligenceReadUser,
	status: str = Query(default="all", pattern="^(all|growing|at_risk|dormant|new|stable)$"),
	limit: int = Query(default=50, ge=1, le=200),
) -> CustomerRiskSignals:
	tenant_id = uuid.UUID(user["tenant_id"])
	return await get_customer_risk_signals(session, tenant_id, status_filter=status, limit=limit)  # type: ignore[arg-type]


@router.get("/prospect-gaps", response_model=ProspectGaps)
async def prospect_gaps(
	session: DbSession,
	user: IntelligenceReadUser,
	category: str = Query(min_length=1),
	limit: int = Query(default=20, ge=1, le=100),
) -> ProspectGaps:
	if not category.strip():
		raise HTTPException(status_code=400, detail="category is required")
	tenant_id = uuid.UUID(user["tenant_id"])
	return await get_prospect_gaps(session, tenant_id, category=category.strip(), limit=limit)


@router.get("/market-opportunities", response_model=MarketOpportunities)
async def market_opportunities(
	session: DbSession,
	user: IntelligenceReadUser,
	period: str = Query(default="last_90d", pattern="^(last_30d|last_90d|last_12m)$"),
) -> MarketOpportunities:
	tenant_id = uuid.UUID(user["tenant_id"])
	return await get_market_opportunities(session, tenant_id, period=period)  # type: ignore[arg-type]


@router.get("/category-trends", response_model=CategoryTrends)
async def category_trends(
	session: DbSession,
	user: IntelligenceReadUser,
	period: str = Query(default="last_90d", pattern="^(last_30d|last_90d|last_12m)$"),
) -> CategoryTrends:
	tenant_id = uuid.UUID(user["tenant_id"])
	return await get_category_trends(session, tenant_id, period=period)  # type: ignore[arg-type]


@router.get("/affinity", response_model=ProductAffinityMap)
async def product_affinity_map(
	session: DbSession,
	user: IntelligenceReadUser,
	min_shared: int = Query(default=2, ge=1, le=100),
	limit: int = Query(default=50, ge=1, le=200),
) -> ProductAffinityMap:
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