"""Dashboard API routes."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from common.auth import get_current_user
from common.config import settings
from common.database import get_db
from common.tenant import DEFAULT_TENANT_ID
from domains.dashboard.schemas import (
    CashFlowResponse,
    GrossMarginResponse,
    KpiSummaryResponse,
    RevenueSummaryResponse,
    RevenueTrendResponse,
    TopCustomersResponse,
    TopProductsResponse,
    VisitorStatsResponse,
)
from domains.dashboard.services import (
    get_cash_flow,
    get_gross_margin,
    get_kpi_summary,
    get_revenue_summary,
    get_revenue_trend,
    get_top_customers,
    get_top_products,
)

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(get_current_user)])

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.get("/revenue-summary", response_model=RevenueSummaryResponse)
async def get_revenue_summary_endpoint(
    session: DbSession,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> RevenueSummaryResponse:
    return await get_revenue_summary(session, uuid.UUID(current_user["tenant_id"]))


@router.get("/kpi-summary", response_model=KpiSummaryResponse)
async def get_kpi_summary_endpoint(
    session: DbSession,
    response: Response,
    current_user: Annotated[dict, Depends(get_current_user)],
    date: Annotated[date | None, Query(description="Target date YYYY-MM-DD")] = None,
) -> KpiSummaryResponse:
    response.headers["Cache-Control"] = "public, max-age=300"
    return await get_kpi_summary(session, uuid.UUID(current_user["tenant_id"]), target_date=date)


@router.get("/top-products", response_model=TopProductsResponse)
async def get_top_products_endpoint(
    session: DbSession,
    current_user: Annotated[dict, Depends(get_current_user)],
    period: Annotated[Literal["day", "week"], Query()] = "day",
) -> TopProductsResponse:
    return await get_top_products(session, uuid.UUID(current_user["tenant_id"]), period=period)



@router.get("/top-customers", response_model=TopCustomersResponse)
async def get_top_customers_endpoint(
    session: DbSession,
    current_user: Annotated[dict, Depends(get_current_user)],
    period: Annotated[Literal["month", "quarter", "year"], Query()] = "month",
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    anchor_date: Annotated[date | None, Query(description="Anchor date used to derive the selected period")] = None,
) -> TopCustomersResponse:
    return await get_top_customers(
        session,
        uuid.UUID(current_user["tenant_id"]),
        period=period,
        limit=limit,
        anchor_date=anchor_date,
    )


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


@router.get("/cash-flow", response_model=CashFlowResponse)
async def get_cash_flow_endpoint(
    session: DbSession,
    current_user: Annotated[dict, Depends(get_current_user)],
    start_date: Annotated[
        date | None, Query(description="Start date (YYYY-MM-DD), defaults to 30 days ago")
    ] = None,
    end_date: Annotated[
        date | None, Query(description="End date (YYYY-MM-DD), defaults to today")
    ] = None,
) -> CashFlowResponse:
    if end_date is None:
        end_date = datetime.now(UTC).date()
    if start_date is None:
        start_date = end_date - timedelta(days=30)
    return await get_cash_flow(session, uuid.UUID(current_user["tenant_id"]), start_date, end_date)


@router.get("/gross-margin", response_model=GrossMarginResponse)
async def get_gross_margin_endpoint(
    session: DbSession,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> GrossMarginResponse:
    return await get_gross_margin(session, uuid.UUID(current_user["tenant_id"]))


@router.get("/revenue-trend", response_model=RevenueTrendResponse)
async def get_revenue_trend_endpoint(
    session: DbSession,
    current_user: Annotated[dict, Depends(get_current_user)],
    granularity: Annotated[
        Literal["day", "week", "month"],
        Query(description="Granularity: day (30d daily), week (weekly), month (monthly)"),
    ] = "month",
    months: Annotated[int, Query(ge=1, le=24, description="Number of months (for week/month granularity)")] = 12,
    days: Annotated[int, Query(ge=7, le=90, description="Number of days (for day granularity)")] = 30,
    before: Annotated[
        str | None,
        Query(description="Cursor: load trend data before this date (YYYY-MM-DD)"),
    ] = None,
) -> RevenueTrendResponse:
    return await get_revenue_trend(
        session, uuid.UUID(current_user["tenant_id"]),
        granularity=granularity, months=months, days=days, before=before,
    )
