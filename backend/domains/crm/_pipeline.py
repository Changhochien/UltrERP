"""CRM pipeline reporting services."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domains.crm._pipeline_analytics import (
    _build_analytics_snapshot,
    _empty_analytics_snapshot,
)
from domains.crm._pipeline_common import (
    _build_pipeline_segment_list,
    _comparison_metric,
)
from domains.crm._pipeline_reporting import _build_report_aggregation
from common.models.order import Order
from common.tenant import DEFAULT_TENANT_ID, set_tenant
from domains.crm.models import Lead, Opportunity, Quotation
from domains.crm.schemas import (
    CRMPipelineAnalytics,
    CRMPipelineReportParams,
    CRMPipelineReportResponse,
)


async def get_crm_pipeline_report(
    session: AsyncSession,
    params: CRMPipelineReportParams,
    tenant_id: uuid.UUID | None = None,
) -> CRMPipelineReportResponse:
    tid = tenant_id or DEFAULT_TENANT_ID
    async with session.begin():
        await set_tenant(session, tid)
        lead_result = await session.execute(select(Lead).where(Lead.tenant_id == tid))
        opportunity_result = await session.execute(
            select(Opportunity).where(Opportunity.tenant_id == tid)
        )
        quotation_result = await session.execute(
            select(Quotation).where(Quotation.tenant_id == tid)
        )
        order_result = await session.execute(
            select(Order).where(Order.tenant_id == tid, Order.status != "cancelled")
        )
        leads = list(lead_result.scalars().all())
        opportunities = list(opportunity_result.scalars().all())
        quotations = list(quotation_result.scalars().all())
        orders = list(order_result.scalars().all())

    quotation_by_id = {
        getattr(quotation, "id", None): quotation for quotation in quotations
    }
    opportunity_by_id = {
        getattr(opportunity, "id", None): opportunity for opportunity in opportunities
    }
    aggregation = _build_report_aggregation(
        leads=leads,
        opportunities=opportunities,
        quotations=quotations,
        orders=orders,
        quotation_by_id=quotation_by_id,
        opportunity_by_id=opportunity_by_id,
        params=params,
    )
    if aggregation.conversion_time_samples > 0:
        aggregation.totals.avg_days_to_conversion = (
            aggregation.conversion_time_total / aggregation.conversion_time_samples
        ).quantize(Decimal("0.01"))

    current_analytics = _build_analytics_snapshot(
        leads=leads,
        opportunities=opportunities,
        quotations=quotations,
        orders=orders,
        quotation_by_id=quotation_by_id,
        opportunity_by_id=opportunity_by_id,
        params=params,
        start_date=params.start_date,
        end_date=params.end_date,
    )
    if params.compare_start_date is not None or params.compare_end_date is not None:
        previous_analytics = _build_analytics_snapshot(
            leads=leads,
            opportunities=opportunities,
            quotations=quotations,
            orders=orders,
            quotation_by_id=quotation_by_id,
            opportunity_by_id=opportunity_by_id,
            params=params,
            start_date=params.compare_start_date,
            end_date=params.compare_end_date,
        )
    else:
        previous_analytics = _empty_analytics_snapshot()
    current_kpis = current_analytics["kpis"]
    previous_kpis = previous_analytics["kpis"]
    analytics = CRMPipelineAnalytics(
        kpis=current_kpis,
        comparison={
            "open_pipeline_value": _comparison_metric(
                current_kpis.open_pipeline_value,
                previous_kpis.open_pipeline_value,
            ),
            "win_rate": _comparison_metric(
                current_kpis.win_rate,
                previous_kpis.win_rate,
            ),
            "lead_conversion_rate": _comparison_metric(
                current_kpis.lead_conversion_rate,
                previous_kpis.lead_conversion_rate,
            ),
            "converted_revenue": _comparison_metric(
                current_kpis.converted_revenue,
                previous_kpis.converted_revenue,
            ),
        },
        funnel=current_analytics["funnel"],
        terminal_by_status=current_analytics["terminal_by_status"],
        terminal_by_lost_reason=current_analytics["terminal_by_lost_reason"],
        terminal_by_competitor=current_analytics["terminal_by_competitor"],
        owner_scorecards=current_analytics["owner_scorecards"],
        drilldowns=current_analytics["drilldowns"],
    )

    return CRMPipelineReportResponse(
        filters=params,
        totals=aggregation.totals,
        analytics=analytics,
        by_status=_build_pipeline_segment_list(aggregation.by_status),
        by_sales_stage=_build_pipeline_segment_list(aggregation.by_sales_stage),
        by_territory=_build_pipeline_segment_list(aggregation.by_territory),
        by_customer_group=_build_pipeline_segment_list(aggregation.by_customer_group),
        by_owner=_build_pipeline_segment_list(aggregation.by_owner),
        by_lost_reason=_build_pipeline_segment_list(aggregation.by_lost_reason),
        by_utm_source=_build_pipeline_segment_list(aggregation.by_utm_source),
        by_utm_medium=_build_pipeline_segment_list(aggregation.by_utm_medium),
        by_utm_campaign=_build_pipeline_segment_list(aggregation.by_utm_campaign),
        by_utm_content=_build_pipeline_segment_list(aggregation.by_utm_content),
        by_conversion_path=_build_pipeline_segment_list(aggregation.by_conversion_path),
        by_conversion_source=_build_pipeline_segment_list(aggregation.by_conversion_source),
        dropoff=aggregation.dropoff,
    )
