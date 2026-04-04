"""Dashboard API routes."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from common.auth import get_current_user
from common.config import settings
from common.database import get_db
from common.tenant import DEFAULT_TENANT_ID
from domains.dashboard.schemas import (
    RevenueSummaryResponse,
    TopProductsResponse,
    VisitorStatsResponse,
)
from domains.dashboard.services import get_revenue_summary, get_top_products

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(get_current_user)])

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.get("/revenue-summary", response_model=RevenueSummaryResponse)
async def get_revenue_summary_endpoint(session: DbSession) -> RevenueSummaryResponse:
    return await get_revenue_summary(session, DEFAULT_TENANT_ID)


@router.get("/top-products", response_model=TopProductsResponse)
async def get_top_products_endpoint(
    session: DbSession,
    period: Annotated[Literal["day", "week"], Query()] = "day",
) -> TopProductsResponse:
    return await get_top_products(session, DEFAULT_TENANT_ID, period=period)


@router.get("/visitor-stats", response_model=VisitorStatsResponse)
async def get_visitor_stats_endpoint() -> VisitorStatsResponse:
    yesterday = datetime.now(UTC).date() - timedelta(days=1)

    if not settings.posthog_api_key or not settings.posthog_project_id:
        return VisitorStatsResponse(
            visitor_count=0,
            inquiry_count=0,
            conversion_rate=None,
            date=yesterday,
            is_configured=False,
        )

    try:
        from domains.dashboard.posthog_client import get_visitor_stats

        stats = await get_visitor_stats(
            host=settings.posthog_host,
            project_id=settings.posthog_project_id,
            api_key=settings.posthog_api_key,
            target_date=yesterday,
        )
    except Exception:
        logger.exception("PostHog API error")
        return VisitorStatsResponse(
            visitor_count=0,
            inquiry_count=0,
            conversion_rate=None,
            date=yesterday,
            is_configured=True,
            error="Analytics unavailable",
        )

    conversion_rate: Decimal | None = None
    if stats.visitor_count > 0:
        conversion_rate = (
            Decimal(stats.inquiry_count) / Decimal(stats.visitor_count) * 100
        ).quantize(Decimal("0.1"))

    return VisitorStatsResponse(
        visitor_count=stats.visitor_count,
        inquiry_count=stats.inquiry_count,
        conversion_rate=conversion_rate,
        date=yesterday,
        is_configured=True,
    )
