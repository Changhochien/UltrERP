"""CRM pipeline reporting services."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.models.order import Order
from common.tenant import DEFAULT_TENANT_ID, set_tenant
from domains.crm.models import Lead, Opportunity, Quotation
from domains.crm.schemas import (
    CRMPipelineAnalytics,
    CRMPipelineAnalyticsKpis,
    CRMPipelineComparisonMetric,
    CRMPipelineDrilldownGroup,
    CRMPipelineDrilldownRecord,
    CRMPipelineDropOff,
    CRMPipelineFunnelStage,
    CRMPipelineOwnerScorecard,
    CRMPipelineRecordType,
    CRMPipelineReportParams,
    CRMPipelineReportResponse,
    CRMPipelineScope,
    CRMPipelineSegment,
    CRMPipelineTotals,
    LeadStatus,
    OpportunityStatus,
    QuotationStatus,
)

TERMINAL_LEAD_STATUSES = frozenset(
    {
        LeadStatus.INTERESTED.value,
        LeadStatus.CONVERTED.value,
        LeadStatus.DO_NOT_CONTACT.value,
        LeadStatus.LOST_QUOTATION.value,
    }
)
TERMINAL_OPPORTUNITY_STATUSES = frozenset(
    {
        OpportunityStatus.CONVERTED.value,
        OpportunityStatus.CLOSED.value,
        OpportunityStatus.LOST.value,
    }
)
TERMINAL_QUOTATION_STATUSES = frozenset(
    {
        QuotationStatus.ORDERED.value,
        QuotationStatus.LOST.value,
        QuotationStatus.CANCELLED.value,
        QuotationStatus.EXPIRED.value,
    }
)


def _quantized_amount(value: object | None) -> Decimal:
    if value is None or value == "":
        return Decimal("0.00")
    return Decimal(str(value)).quantize(Decimal("0.01"))


def _build_pipeline_segment_list(
    buckets: dict[tuple[str | None, str], dict[str, object]],
) -> list[CRMPipelineSegment]:
    items = [CRMPipelineSegment.model_validate(item) for item in buckets.values()]
    return sorted(
        items,
        key=lambda item: (-item.count, item.label.lower(), item.record_type or ""),
    )


def _upsert_pipeline_bucket(
    buckets: dict[tuple[str | None, str], dict[str, object]],
    *,
    record_type: str | None,
    key: str,
    label: str,
    amount: Decimal,
    ordered_revenue: Decimal = Decimal("0.00"),
) -> None:
    bucket_key = (record_type, key)
    bucket = buckets.setdefault(
        bucket_key,
        {
            "record_type": record_type,
            "key": key,
            "label": label,
            "count": 0,
            "amount": Decimal("0.00"),
            "ordered_revenue": Decimal("0.00"),
        },
    )
    bucket["count"] = int(bucket["count"]) + 1
    bucket["amount"] = (_quantized_amount(bucket["amount"]) + amount).quantize(
        Decimal("0.01")
    )
    bucket["ordered_revenue"] = (
        _quantized_amount(bucket["ordered_revenue"]) + ordered_revenue
    ).quantize(Decimal("0.01"))


def _extract_snapshot_text(snapshot: dict[str, object] | None, key: str) -> str:
    if not isinstance(snapshot, dict):
        return ""
    value = snapshot.get(key)
    return value.strip() if isinstance(value, str) else ""


def _matches_attribution_filters(
    *,
    params: CRMPipelineReportParams,
    sales_stage: str,
    territory: str,
    customer_group: str,
    owner: str,
    utm_source: str,
    utm_medium: str,
    utm_campaign: str,
    utm_content: str,
) -> bool:
    if params.sales_stage and sales_stage != params.sales_stage:
        return False
    if params.territory and territory != params.territory:
        return False
    if params.customer_group and customer_group != params.customer_group:
        return False
    if params.owner and owner != params.owner:
        return False
    if params.utm_source and utm_source != params.utm_source:
        return False
    if params.utm_medium and utm_medium != params.utm_medium:
        return False
    if params.utm_campaign and utm_campaign != params.utm_campaign:
        return False
    if params.utm_content and utm_content != params.utm_content:
        return False
    return True


def _lead_scope(status: str) -> CRMPipelineScope:
    return (
        CRMPipelineScope.TERMINAL
        if status in TERMINAL_LEAD_STATUSES
        else CRMPipelineScope.OPEN
    )


def _opportunity_scope(status: str) -> CRMPipelineScope:
    return (
        CRMPipelineScope.TERMINAL
        if status in TERMINAL_OPPORTUNITY_STATUSES
        else CRMPipelineScope.OPEN
    )


def _quotation_scope(status: str) -> CRMPipelineScope:
    return (
        CRMPipelineScope.TERMINAL
        if status in TERMINAL_QUOTATION_STATUSES
        else CRMPipelineScope.OPEN
    )


def _matches_common_filters(
    *,
    params: CRMPipelineReportParams,
    scope: CRMPipelineScope,
    status: str,
    territory: str,
    customer_group: str,
    owner: str,
    lost_reason: str,
    utm_source: str,
    utm_medium: str,
    utm_campaign: str,
    utm_content: str,
) -> bool:
    if params.scope != CRMPipelineScope.ALL and scope != params.scope:
        return False
    if params.status and status != params.status:
        return False
    if params.territory and territory != params.territory:
        return False
    if params.customer_group and customer_group != params.customer_group:
        return False
    if params.owner and owner != params.owner:
        return False
    if params.lost_reason and lost_reason != params.lost_reason:
        return False
    if params.utm_source and utm_source != params.utm_source:
        return False
    if params.utm_medium and utm_medium != params.utm_medium:
        return False
    if params.utm_campaign and utm_campaign != params.utm_campaign:
        return False
    if params.utm_content and utm_content != params.utm_content:
        return False
    return True


def _matches_analytics_filters(
    *,
    params: CRMPipelineReportParams,
    sales_stage: str,
    territory: str,
    customer_group: str,
    owner: str,
    utm_source: str,
    utm_medium: str,
    utm_campaign: str,
    utm_content: str,
) -> bool:
    if params.sales_stage and sales_stage != params.sales_stage:
        return False
    if params.territory and territory != params.territory:
        return False
    if params.customer_group and customer_group != params.customer_group:
        return False
    if params.owner and owner != params.owner:
        return False
    if params.utm_source and utm_source != params.utm_source:
        return False
    if params.utm_medium and utm_medium != params.utm_medium:
        return False
    if params.utm_campaign and utm_campaign != params.utm_campaign:
        return False
    if params.utm_content and utm_content != params.utm_content:
        return False
    return True


def _coerce_date(value: object | None) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


def _matches_period(value: object | None, start_date: date | None, end_date: date | None) -> bool:
    if start_date is None and end_date is None:
        return True
    resolved = _coerce_date(value)
    if resolved is None:
        return False
    if start_date is not None and resolved < start_date:
        return False
    if end_date is not None and resolved > end_date:
        return False
    return True


def _percentage(numerator: int, denominator: int) -> Decimal:
    if denominator <= 0:
        return Decimal("0.00")
    return ((Decimal(numerator) * Decimal("100")) / Decimal(denominator)).quantize(
        Decimal("0.01")
    )


def _comparison_metric(current_value: Decimal, previous_value: Decimal) -> CRMPipelineComparisonMetric:
    return CRMPipelineComparisonMetric(
        current_value=current_value,
        previous_value=previous_value,
        delta=(current_value - previous_value).quantize(Decimal("0.01")),
    )


def _lead_conversion_targets(lead: object) -> set[str]:
    targets = {
        part.strip()
        for part in str(getattr(lead, "conversion_path", "") or "").split("+")
        if part.strip()
    }
    if getattr(lead, "converted_customer_id", None) is not None:
        targets.add("customer")
    if getattr(lead, "converted_opportunity_id", None) is not None:
        targets.add("opportunity")
    if getattr(lead, "converted_quotation_id", None) is not None:
        targets.add("quotation")
    return targets


def _lead_is_converted_compatible(lead: object) -> bool:
    if str(getattr(lead, "conversion_state", "") or "") in {"converted", "partially_converted"}:
        return True
    if getattr(lead, "converted_at", None) is not None:
        return True
    if _lead_conversion_targets(lead):
        return True
    return str(getattr(lead, "status", "") or "") in {
        LeadStatus.OPPORTUNITY.value,
        LeadStatus.QUOTATION.value,
        LeadStatus.CONVERTED.value,
        LeadStatus.LOST_QUOTATION.value,
    }


def _build_analytics_snapshot(
    *,
    leads: list[object],
    opportunities: list[object],
    quotations: list[object],
    orders: list[object],
    quotation_by_id: dict[object, object],
    opportunity_by_id: dict[object, object],
    params: CRMPipelineReportParams,
    start_date: date | None,
    end_date: date | None,
) -> dict[str, object]:
    filtered_leads: list[object] = []
    filtered_opportunities: list[object] = []
    filtered_quotations: list[object] = []
    filtered_orders: list[tuple[object, object | None, object | None]] = []

    terminal_by_status: dict[tuple[str | None, str], dict[str, object]] = {}
    terminal_by_lost_reason: dict[tuple[str | None, str], dict[str, object]] = {}
    terminal_by_competitor: dict[tuple[str | None, str], dict[str, object]] = {}
    owner_buckets: dict[str, dict[str, object]] = {}

    weighted_pipeline_value = Decimal("0.00")
    converted_revenue = Decimal("0.00")
    total_time_to_conversion = Decimal("0.00")
    total_time_to_conversion_samples = 0
    terminal_converted = 0
    terminal_lost = 0

    def owner_bucket(owner: str) -> dict[str, object]:
        key = owner or "Unassigned"
        return owner_buckets.setdefault(
            key,
            {
                "owner": key,
                "assigned_leads": 0,
                "owned_opportunities": 0,
                "open_pipeline_value": Decimal("0.00"),
                "weighted_pipeline_value": Decimal("0.00"),
                "converted_revenue": Decimal("0.00"),
                "time_total": Decimal("0.00"),
                "time_samples": 0,
            },
        )

    for lead in leads:
        if not _matches_analytics_filters(
            params=params,
            sales_stage="",
            territory=str(getattr(lead, "territory", "") or ""),
            customer_group="",
            owner=str(getattr(lead, "lead_owner", "") or ""),
            utm_source=str(getattr(lead, "utm_source", "") or ""),
            utm_medium=str(getattr(lead, "utm_medium", "") or ""),
            utm_campaign=str(getattr(lead, "utm_campaign", "") or ""),
            utm_content=str(getattr(lead, "utm_content", "") or ""),
        ):
            continue
        if not _matches_period(getattr(lead, "created_at", None), start_date, end_date):
            continue
        filtered_leads.append(lead)
        owner = str(getattr(lead, "lead_owner", "") or "")
        owner_bucket(owner)["assigned_leads"] = int(owner_bucket(owner)["assigned_leads"]) + 1

        if _lead_is_converted_compatible(lead):
            created_at = getattr(lead, "created_at", None)
            converted_at = getattr(lead, "converted_at", None)
            if created_at is not None and converted_at is not None:
                elapsed_days = Decimal(
                    str((converted_at - created_at).total_seconds() / 86400)
                ).quantize(Decimal("0.01"))
                total_time_to_conversion = (
                    total_time_to_conversion + elapsed_days
                ).quantize(Decimal("0.01"))
                total_time_to_conversion_samples += 1
                bucket = owner_bucket(owner)
                bucket["time_total"] = (
                    _quantized_amount(bucket["time_total"]) + elapsed_days
                ).quantize(Decimal("0.01"))
                bucket["time_samples"] = int(bucket["time_samples"]) + 1

    for opportunity in opportunities:
        sales_stage = str(getattr(opportunity, "sales_stage", "") or "")
        territory = str(getattr(opportunity, "territory", "") or "")
        customer_group = str(getattr(opportunity, "customer_group", "") or "")
        owner = str(getattr(opportunity, "opportunity_owner", "") or "")
        utm_source = str(getattr(opportunity, "utm_source", "") or "")
        utm_medium = str(getattr(opportunity, "utm_medium", "") or "")
        utm_campaign = str(getattr(opportunity, "utm_campaign", "") or "")
        utm_content = str(getattr(opportunity, "utm_content", "") or "")
        if not _matches_analytics_filters(
            params=params,
            sales_stage=sales_stage,
            territory=territory,
            customer_group=customer_group,
            owner=owner,
            utm_source=utm_source,
            utm_medium=utm_medium,
            utm_campaign=utm_campaign,
            utm_content=utm_content,
        ):
            continue
        period_value = getattr(opportunity, "expected_closing", None) or getattr(opportunity, "created_at", None)
        if not _matches_period(period_value, start_date, end_date):
            continue

        filtered_opportunities.append(opportunity)
        amount = _quantized_amount(getattr(opportunity, "opportunity_amount", None))
        probability = Decimal(str(getattr(opportunity, "probability", 0) or 0))
        status = str(getattr(opportunity, "status", "") or "")
        bucket = owner_bucket(owner)
        bucket["owned_opportunities"] = int(bucket["owned_opportunities"]) + 1
        if _opportunity_scope(status) == CRMPipelineScope.OPEN:
            bucket["open_pipeline_value"] = (
                _quantized_amount(bucket["open_pipeline_value"]) + amount
            ).quantize(Decimal("0.01"))
            weighted_amount = ((amount * probability) / Decimal("100")).quantize(Decimal("0.01"))
            bucket["weighted_pipeline_value"] = (
                _quantized_amount(bucket["weighted_pipeline_value"]) + weighted_amount
            ).quantize(Decimal("0.01"))
            weighted_pipeline_value = (weighted_pipeline_value + weighted_amount).quantize(Decimal("0.01"))

        if status == OpportunityStatus.CONVERTED.value:
            terminal_converted += 1
        elif status == OpportunityStatus.LOST.value:
            terminal_lost += 1

        if _opportunity_scope(status) == CRMPipelineScope.TERMINAL:
            _upsert_pipeline_bucket(
                terminal_by_status,
                record_type="opportunity",
                key=status,
                label=status,
                amount=amount,
            )
            lost_reason = str(getattr(opportunity, "lost_reason", "") or "")
            if lost_reason:
                _upsert_pipeline_bucket(
                    terminal_by_lost_reason,
                    record_type="opportunity",
                    key=lost_reason,
                    label=lost_reason,
                    amount=amount,
                )
            competitor = str(getattr(opportunity, "competitor_name", "") or "")
            if competitor:
                _upsert_pipeline_bucket(
                    terminal_by_competitor,
                    record_type="opportunity",
                    key=competitor,
                    label=competitor,
                    amount=amount,
                )

    for quotation in quotations:
        territory = str(getattr(quotation, "territory", "") or "")
        customer_group = str(getattr(quotation, "customer_group", "") or "")
        utm_source = str(getattr(quotation, "utm_source", "") or "")
        utm_medium = str(getattr(quotation, "utm_medium", "") or "")
        utm_campaign = str(getattr(quotation, "utm_campaign", "") or "")
        utm_content = str(getattr(quotation, "utm_content", "") or "")
        if not _matches_analytics_filters(
            params=params,
            sales_stage="",
            territory=territory,
            customer_group=customer_group,
            owner="",
            utm_source=utm_source,
            utm_medium=utm_medium,
            utm_campaign=utm_campaign,
            utm_content=utm_content,
        ):
            continue
        period_value = getattr(quotation, "transaction_date", None) or getattr(quotation, "created_at", None)
        if not _matches_period(period_value, start_date, end_date):
            continue

        filtered_quotations.append(quotation)
        amount = _quantized_amount(getattr(quotation, "grand_total", None))
        status = str(getattr(quotation, "status", "") or "")
        if _quotation_scope(status) == CRMPipelineScope.TERMINAL:
            _upsert_pipeline_bucket(
                terminal_by_status,
                record_type="quotation",
                key=status,
                label=status,
                amount=amount,
            )
            lost_reason = str(getattr(quotation, "lost_reason", "") or "")
            if lost_reason:
                _upsert_pipeline_bucket(
                    terminal_by_lost_reason,
                    record_type="quotation",
                    key=lost_reason,
                    label=lost_reason,
                    amount=amount,
                )
            competitor = str(getattr(quotation, "competitor_name", "") or "")
            if competitor:
                _upsert_pipeline_bucket(
                    terminal_by_competitor,
                    record_type="quotation",
                    key=competitor,
                    label=competitor,
                    amount=amount,
                )

    for order in orders:
        source_quotation = quotation_by_id.get(getattr(order, "source_quotation_id", None))
        if source_quotation is None:
            continue
        source_opportunity = opportunity_by_id.get(getattr(source_quotation, "opportunity_id", None))
        territory = str(getattr(source_quotation, "territory", "") or "")
        customer_group = str(getattr(source_quotation, "customer_group", "") or "")
        owner = str(getattr(source_opportunity, "opportunity_owner", "") or "")
        sales_stage = str(getattr(source_opportunity, "sales_stage", "") or "")
        crm_context_snapshot = getattr(order, "crm_context_snapshot", None)
        utm_source = _extract_snapshot_text(crm_context_snapshot, "utm_source")
        utm_medium = _extract_snapshot_text(crm_context_snapshot, "utm_medium")
        utm_campaign = _extract_snapshot_text(crm_context_snapshot, "utm_campaign")
        utm_content = _extract_snapshot_text(crm_context_snapshot, "utm_content")
        if not _matches_analytics_filters(
            params=params,
            sales_stage=sales_stage,
            territory=territory,
            customer_group=customer_group,
            owner=owner,
            utm_source=utm_source,
            utm_medium=utm_medium,
            utm_campaign=utm_campaign,
            utm_content=utm_content,
        ):
            continue
        if not _matches_period(getattr(order, "created_at", None), start_date, end_date):
            continue

        filtered_orders.append((order, source_quotation, source_opportunity))
        amount = _quantized_amount(getattr(order, "total_amount", None))
        converted_revenue = (converted_revenue + amount).quantize(Decimal("0.01"))
        bucket = owner_bucket(owner)
        bucket["converted_revenue"] = (
            _quantized_amount(bucket["converted_revenue"]) + amount
        ).quantize(Decimal("0.01"))

    qualified_leads = [
        lead
        for lead in filtered_leads
        if str(getattr(lead, "qualification_status", "") or "") == "qualified"
    ]
    converted_qualified_leads = [lead for lead in qualified_leads if _lead_is_converted_compatible(lead)]

    funnel_counts = [
        ("lead", "Lead", len(filtered_leads)),
        (
            "opportunity",
            "Opportunity",
            sum(
                1
                for lead in filtered_leads
                if "opportunity" in _lead_conversion_targets(lead)
                or str(getattr(lead, "status", "") or "")
                in {LeadStatus.OPPORTUNITY.value, LeadStatus.QUOTATION.value, LeadStatus.CONVERTED.value}
            ),
        ),
        (
            "quotation",
            "Quotation",
            sum(
                1
                for lead in filtered_leads
                if "quotation" in _lead_conversion_targets(lead)
                or str(getattr(lead, "status", "") or "")
                in {LeadStatus.QUOTATION.value, LeadStatus.CONVERTED.value, LeadStatus.LOST_QUOTATION.value}
            ),
        ),
        (
            "converted",
            "Converted",
            sum(1 for lead in filtered_leads if _lead_is_converted_compatible(lead)),
        ),
    ]
    funnel: list[CRMPipelineFunnelStage] = []
    previous_count = 0
    for index, (key, label, count) in enumerate(funnel_counts):
        conversion_rate = Decimal("100.00") if index == 0 and count > 0 else _percentage(count, previous_count)
        dropoff_count = 0 if index == 0 else max(previous_count - count, 0)
        funnel.append(
            CRMPipelineFunnelStage(
                key=key,
                label=label,
                count=count,
                dropoff_count=dropoff_count,
                conversion_rate=conversion_rate,
            )
        )
        previous_count = count

    owner_scorecards: list[CRMPipelineOwnerScorecard] = []
    for bucket in owner_buckets.values():
        time_samples = int(bucket["time_samples"])
        owner_scorecards.append(
            CRMPipelineOwnerScorecard(
                owner=str(bucket["owner"]),
                assigned_leads=int(bucket["assigned_leads"]),
                owned_opportunities=int(bucket["owned_opportunities"]),
                open_pipeline_value=_quantized_amount(bucket["open_pipeline_value"]),
                weighted_pipeline_value=_quantized_amount(bucket["weighted_pipeline_value"]),
                converted_revenue=_quantized_amount(bucket["converted_revenue"]),
                time_to_conversion=(
                    _quantized_amount(bucket["time_total"]) / Decimal(time_samples)
                ).quantize(Decimal("0.01"))
                if time_samples > 0
                else Decimal("0.00"),
            )
        )
    owner_scorecards.sort(
        key=lambda item: (
            -_quantized_amount(item.open_pipeline_value),
            -item.assigned_leads,
            item.owner.lower(),
        )
    )

    drilldowns = [
        CRMPipelineDrilldownGroup(
            key="qualified_leads",
            label="Qualified Leads",
            records=[
                CRMPipelineDrilldownRecord(
                    record_type="lead",
                    record_id=str(getattr(lead, "id", "")),
                    label=str(getattr(lead, "company_name", "") or getattr(lead, "lead_name", "") or getattr(lead, "id", "")),
                    status=str(getattr(lead, "status", "") or ""),
                    owner=str(getattr(lead, "lead_owner", "") or ""),
                    amount=Decimal("0.00"),
                )
                for lead in qualified_leads
            ],
        ),
        CRMPipelineDrilldownGroup(
            key="open_pipeline",
            label="Open Pipeline",
            records=[
                CRMPipelineDrilldownRecord(
                    record_type="opportunity",
                    record_id=str(getattr(opportunity, "id", "")),
                    label=str(getattr(opportunity, "opportunity_title", "") or getattr(opportunity, "id", "")),
                    status=str(getattr(opportunity, "status", "") or ""),
                    owner=str(getattr(opportunity, "opportunity_owner", "") or ""),
                    amount=_quantized_amount(getattr(opportunity, "opportunity_amount", None)),
                )
                for opportunity in filtered_opportunities
                if _opportunity_scope(str(getattr(opportunity, "status", "") or "")) == CRMPipelineScope.OPEN
            ],
        ),
        CRMPipelineDrilldownGroup(
            key="terminal_outcomes",
            label="Terminal Outcomes",
            records=[
                *[
                    CRMPipelineDrilldownRecord(
                        record_type="opportunity",
                        record_id=str(getattr(opportunity, "id", "")),
                        label=str(getattr(opportunity, "opportunity_title", "") or getattr(opportunity, "id", "")),
                        status=str(getattr(opportunity, "status", "") or ""),
                        owner=str(getattr(opportunity, "opportunity_owner", "") or ""),
                        amount=_quantized_amount(getattr(opportunity, "opportunity_amount", None)),
                    )
                    for opportunity in filtered_opportunities
                    if _opportunity_scope(str(getattr(opportunity, "status", "") or "")) == CRMPipelineScope.TERMINAL
                ],
                *[
                    CRMPipelineDrilldownRecord(
                        record_type="quotation",
                        record_id=str(getattr(quotation, "id", "")),
                        label=str(getattr(quotation, "party_label", "") or getattr(quotation, "id", "")),
                        status=str(getattr(quotation, "status", "") or ""),
                        owner="",
                        amount=_quantized_amount(getattr(quotation, "grand_total", None)),
                    )
                    for quotation in filtered_quotations
                    if _quotation_scope(str(getattr(quotation, "status", "") or "")) == CRMPipelineScope.TERMINAL
                ],
            ],
        ),
        CRMPipelineDrilldownGroup(
            key="converted_orders",
            label="Converted Orders",
            records=[
                CRMPipelineDrilldownRecord(
                    record_type="order",
                    record_id=str(getattr(order, "id", "")),
                    label=f"Order {getattr(order, 'id', '')}",
                    status=str(getattr(order, "status", "") or ""),
                    owner=str(getattr(source_opportunity, "opportunity_owner", "") or ""),
                    amount=_quantized_amount(getattr(order, "total_amount", None)),
                )
                for order, _source_quotation, source_opportunity in filtered_orders
            ],
        ),
    ]

    open_pipeline_value = sum(
        (
            _quantized_amount(getattr(opportunity, "opportunity_amount", None))
            for opportunity in filtered_opportunities
            if _opportunity_scope(str(getattr(opportunity, "status", "") or "")) == CRMPipelineScope.OPEN
        ),
        start=Decimal("0.00"),
    ).quantize(Decimal("0.01"))
    average_deal_size = (
        converted_revenue / Decimal(len(filtered_orders))
    ).quantize(Decimal("0.01")) if filtered_orders else Decimal("0.00")
    time_to_conversion = (
        total_time_to_conversion / Decimal(total_time_to_conversion_samples)
    ).quantize(Decimal("0.01")) if total_time_to_conversion_samples > 0 else Decimal("0.00")

    return {
        "kpis": CRMPipelineAnalyticsKpis(
            open_pipeline_value=open_pipeline_value,
            weighted_pipeline_value=weighted_pipeline_value,
            win_rate=_percentage(terminal_converted, terminal_converted + terminal_lost),
            lead_conversion_rate=_percentage(len(converted_qualified_leads), len(qualified_leads)),
            average_deal_size=average_deal_size,
            converted_revenue=converted_revenue,
            time_to_conversion=time_to_conversion,
        ),
        "funnel": funnel,
        "terminal_by_status": _build_pipeline_segment_list(terminal_by_status),
        "terminal_by_lost_reason": _build_pipeline_segment_list(terminal_by_lost_reason),
        "terminal_by_competitor": _build_pipeline_segment_list(terminal_by_competitor),
        "owner_scorecards": owner_scorecards,
        "drilldowns": drilldowns,
    }


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

    totals = CRMPipelineTotals()
    by_status: dict[tuple[str | None, str], dict[str, object]] = {}
    by_sales_stage: dict[tuple[str | None, str], dict[str, object]] = {}
    by_territory: dict[tuple[str | None, str], dict[str, object]] = {}
    by_customer_group: dict[tuple[str | None, str], dict[str, object]] = {}
    by_owner: dict[tuple[str | None, str], dict[str, object]] = {}
    by_lost_reason: dict[tuple[str | None, str], dict[str, object]] = {}
    by_utm_source: dict[tuple[str | None, str], dict[str, object]] = {}
    by_utm_medium: dict[tuple[str | None, str], dict[str, object]] = {}
    by_utm_campaign: dict[tuple[str | None, str], dict[str, object]] = {}
    by_utm_content: dict[tuple[str | None, str], dict[str, object]] = {}
    by_conversion_path: dict[tuple[str | None, str], _PipelineBucket] = {}
    by_conversion_source: dict[tuple[str | None, str], _PipelineBucket] = {}
    dropoff = CRMPipelineDropOff()
    quotation_by_id = {
        getattr(quotation, "id", None): quotation for quotation in quotations
    }
    opportunity_by_id = {
        getattr(opportunity, "id", None): opportunity for opportunity in opportunities
    }
    conversion_time_total = Decimal("0.00")
    conversion_time_samples = 0

    def include_record(record_type: CRMPipelineRecordType) -> bool:
        return params.record_type in {CRMPipelineRecordType.ALL, record_type}

    for lead in leads:
        if not include_record(CRMPipelineRecordType.LEAD):
            continue
        scope = _lead_scope(str(lead.status))
        if params.sales_stage:
            continue
        if not _matches_common_filters(
            params=params,
            scope=scope,
            status=str(lead.status),
            territory=str(getattr(lead, "territory", "") or ""),
            customer_group="",
            owner=str(getattr(lead, "lead_owner", "") or ""),
            lost_reason="",
            utm_source=str(getattr(lead, "utm_source", "") or ""),
            utm_medium=str(getattr(lead, "utm_medium", "") or ""),
            utm_campaign=str(getattr(lead, "utm_campaign", "") or ""),
            utm_content=str(getattr(lead, "utm_content", "") or ""),
        ):
            continue

        totals.lead_count += 1
        if scope == CRMPipelineScope.OPEN:
            totals.open_count += 1
        else:
            totals.terminal_count += 1
        if str(lead.status) not in {
            LeadStatus.OPPORTUNITY.value,
            LeadStatus.QUOTATION.value,
            LeadStatus.CONVERTED.value,
        }:
            dropoff.lead_only_count += 1

        _upsert_pipeline_bucket(
            by_status,
            record_type="lead",
            key=str(lead.status),
            label=str(lead.status),
            amount=Decimal("0.00"),
        )
        if getattr(lead, "territory", ""):
            _upsert_pipeline_bucket(
                by_territory,
                record_type="lead",
                key=str(lead.territory),
                label=str(lead.territory),
                amount=Decimal("0.00"),
            )
        if getattr(lead, "lead_owner", ""):
            _upsert_pipeline_bucket(
                by_owner,
                record_type="lead",
                key=str(lead.lead_owner),
                label=str(lead.lead_owner),
                amount=Decimal("0.00"),
            )
        if getattr(lead, "utm_source", ""):
            _upsert_pipeline_bucket(
                by_utm_source,
                record_type="lead",
                key=str(lead.utm_source),
                label=str(lead.utm_source),
                amount=Decimal("0.00"),
            )
        if getattr(lead, "utm_medium", ""):
            _upsert_pipeline_bucket(
                by_utm_medium,
                record_type="lead",
                key=str(lead.utm_medium),
                label=str(lead.utm_medium),
                amount=Decimal("0.00"),
            )
        if getattr(lead, "utm_campaign", ""):
            _upsert_pipeline_bucket(
                by_utm_campaign,
                record_type="lead",
                key=str(lead.utm_campaign),
                label=str(lead.utm_campaign),
                amount=Decimal("0.00"),
            )
        if getattr(lead, "utm_content", ""):
            _upsert_pipeline_bucket(
                by_utm_content,
                record_type="lead",
                key=str(lead.utm_content),
                label=str(lead.utm_content),
                amount=Decimal("0.00"),
            )
        conversion_state = str(getattr(lead, "conversion_state", "") or "")
        converted_at = getattr(lead, "converted_at", None)
        created_at = getattr(lead, "created_at", None)
        conversion_path = str(getattr(lead, "conversion_path", "") or "")
        conversion_source = str(getattr(lead, "source", "") or "")
        if conversion_state not in {"", "not_converted"} or converted_at is not None:
            totals.conversion_count += 1
            if conversion_path:
                _upsert_pipeline_bucket(
                    by_conversion_path,
                    record_type="lead",
                    key=conversion_path,
                    label=conversion_path,
                    amount=Decimal("0.00"),
                )
            if conversion_source:
                _upsert_pipeline_bucket(
                    by_conversion_source,
                    record_type="lead",
                    key=conversion_source,
                    label=conversion_source,
                    amount=Decimal("0.00"),
                )
            if created_at is not None and converted_at is not None:
                elapsed_days = Decimal(
                    str((converted_at - created_at).total_seconds() / 86400)
                ).quantize(Decimal("0.01"))
                conversion_time_total = (conversion_time_total + elapsed_days).quantize(
                    Decimal("0.01")
                )
                conversion_time_samples += 1

    for opportunity in opportunities:
        if not include_record(CRMPipelineRecordType.OPPORTUNITY):
            continue
        scope = _opportunity_scope(str(opportunity.status))
        if params.sales_stage and str(opportunity.sales_stage) != params.sales_stage:
            continue
        amount = _quantized_amount(getattr(opportunity, "opportunity_amount", None))
        if not _matches_common_filters(
            params=params,
            scope=scope,
            status=str(opportunity.status),
            territory=str(getattr(opportunity, "territory", "") or ""),
            customer_group=str(getattr(opportunity, "customer_group", "") or ""),
            owner=str(getattr(opportunity, "opportunity_owner", "") or ""),
            lost_reason=str(getattr(opportunity, "lost_reason", "") or ""),
            utm_source=str(getattr(opportunity, "utm_source", "") or ""),
            utm_medium=str(getattr(opportunity, "utm_medium", "") or ""),
            utm_campaign=str(getattr(opportunity, "utm_campaign", "") or ""),
            utm_content=str(getattr(opportunity, "utm_content", "") or ""),
        ):
            continue

        totals.opportunity_count += 1
        if scope == CRMPipelineScope.OPEN:
            totals.open_count += 1
            totals.open_pipeline_amount = (
                totals.open_pipeline_amount + amount
            ).quantize(Decimal("0.01"))
        else:
            totals.terminal_count += 1
            totals.terminal_pipeline_amount = (
                totals.terminal_pipeline_amount + amount
            ).quantize(Decimal("0.01"))
        if str(opportunity.status) not in {
            OpportunityStatus.QUOTATION.value,
            OpportunityStatus.CONVERTED.value,
        }:
            dropoff.opportunity_without_quotation_count += 1

        _upsert_pipeline_bucket(
            by_status,
            record_type="opportunity",
            key=str(opportunity.status),
            label=str(opportunity.status),
            amount=amount,
        )
        _upsert_pipeline_bucket(
            by_sales_stage,
            record_type="opportunity",
            key=str(opportunity.sales_stage),
            label=str(opportunity.sales_stage),
            amount=amount,
        )
        if getattr(opportunity, "territory", ""):
            _upsert_pipeline_bucket(
                by_territory,
                record_type="opportunity",
                key=str(opportunity.territory),
                label=str(opportunity.territory),
                amount=amount,
            )
        if getattr(opportunity, "customer_group", ""):
            _upsert_pipeline_bucket(
                by_customer_group,
                record_type="opportunity",
                key=str(opportunity.customer_group),
                label=str(opportunity.customer_group),
                amount=amount,
            )
        if getattr(opportunity, "opportunity_owner", ""):
            _upsert_pipeline_bucket(
                by_owner,
                record_type="opportunity",
                key=str(opportunity.opportunity_owner),
                label=str(opportunity.opportunity_owner),
                amount=amount,
            )
        if getattr(opportunity, "lost_reason", ""):
            _upsert_pipeline_bucket(
                by_lost_reason,
                record_type="opportunity",
                key=str(opportunity.lost_reason),
                label=str(opportunity.lost_reason),
                amount=amount,
            )
        if getattr(opportunity, "utm_source", ""):
            _upsert_pipeline_bucket(
                by_utm_source,
                record_type="opportunity",
                key=str(opportunity.utm_source),
                label=str(opportunity.utm_source),
                amount=amount,
            )
        if getattr(opportunity, "utm_medium", ""):
            _upsert_pipeline_bucket(
                by_utm_medium,
                record_type="opportunity",
                key=str(opportunity.utm_medium),
                label=str(opportunity.utm_medium),
                amount=amount,
            )
        if getattr(opportunity, "utm_campaign", ""):
            _upsert_pipeline_bucket(
                by_utm_campaign,
                record_type="opportunity",
                key=str(opportunity.utm_campaign),
                label=str(opportunity.utm_campaign),
                amount=amount,
            )
        if getattr(opportunity, "utm_content", ""):
            _upsert_pipeline_bucket(
                by_utm_content,
                record_type="opportunity",
                key=str(opportunity.utm_content),
                label=str(opportunity.utm_content),
                amount=amount,
            )

    for quotation in quotations:
        if not include_record(CRMPipelineRecordType.QUOTATION):
            continue
        scope = _quotation_scope(str(quotation.status))
        if params.sales_stage:
            continue
        amount = _quantized_amount(getattr(quotation, "grand_total", None))
        if not _matches_common_filters(
            params=params,
            scope=scope,
            status=str(quotation.status),
            territory=str(getattr(quotation, "territory", "") or ""),
            customer_group=str(getattr(quotation, "customer_group", "") or ""),
            owner="",
            lost_reason=str(getattr(quotation, "lost_reason", "") or ""),
            utm_source=str(getattr(quotation, "utm_source", "") or ""),
            utm_medium=str(getattr(quotation, "utm_medium", "") or ""),
            utm_campaign=str(getattr(quotation, "utm_campaign", "") or ""),
            utm_content=str(getattr(quotation, "utm_content", "") or ""),
        ):
            continue

        totals.quotation_count += 1
        if scope == CRMPipelineScope.OPEN:
            totals.open_count += 1
            totals.open_pipeline_amount = (
                totals.open_pipeline_amount + amount
            ).quantize(Decimal("0.01"))
        else:
            totals.terminal_count += 1
            totals.terminal_pipeline_amount = (
                totals.terminal_pipeline_amount + amount
            ).quantize(Decimal("0.01"))
        if int(getattr(quotation, "order_count", 0) or 0) > 0:
            dropoff.quotation_with_order_count += 1
        else:
            dropoff.quotation_without_order_count += 1

        _upsert_pipeline_bucket(
            by_status,
            record_type="quotation",
            key=str(quotation.status),
            label=str(quotation.status),
            amount=amount,
        )
        if getattr(quotation, "territory", ""):
            _upsert_pipeline_bucket(
                by_territory,
                record_type="quotation",
                key=str(quotation.territory),
                label=str(quotation.territory),
                amount=amount,
            )
        if getattr(quotation, "customer_group", ""):
            _upsert_pipeline_bucket(
                by_customer_group,
                record_type="quotation",
                key=str(quotation.customer_group),
                label=str(quotation.customer_group),
                amount=amount,
            )
        if getattr(quotation, "lost_reason", ""):
            _upsert_pipeline_bucket(
                by_lost_reason,
                record_type="quotation",
                key=str(quotation.lost_reason),
                label=str(quotation.lost_reason),
                amount=amount,
            )
        if getattr(quotation, "utm_source", ""):
            _upsert_pipeline_bucket(
                by_utm_source,
                record_type="quotation",
                key=str(quotation.utm_source),
                label=str(quotation.utm_source),
                amount=amount,
            )
        if getattr(quotation, "utm_medium", ""):
            _upsert_pipeline_bucket(
                by_utm_medium,
                record_type="quotation",
                key=str(quotation.utm_medium),
                label=str(quotation.utm_medium),
                amount=amount,
            )
        if getattr(quotation, "utm_campaign", ""):
            _upsert_pipeline_bucket(
                by_utm_campaign,
                record_type="quotation",
                key=str(quotation.utm_campaign),
                label=str(quotation.utm_campaign),
                amount=amount,
            )
        if getattr(quotation, "utm_content", ""):
            _upsert_pipeline_bucket(
                by_utm_content,
                record_type="quotation",
                key=str(quotation.utm_content),
                label=str(quotation.utm_content),
                amount=amount,
            )

    if params.record_type in {
        CRMPipelineRecordType.ALL,
        CRMPipelineRecordType.OPPORTUNITY,
        CRMPipelineRecordType.QUOTATION,
    }:
        for order in orders:
            crm_context_snapshot = getattr(order, "crm_context_snapshot", None)
            utm_source = _extract_snapshot_text(crm_context_snapshot, "utm_source")
            utm_medium = _extract_snapshot_text(crm_context_snapshot, "utm_medium")
            utm_campaign = _extract_snapshot_text(crm_context_snapshot, "utm_campaign")
            utm_content = _extract_snapshot_text(crm_context_snapshot, "utm_content")
            if not any((utm_source, utm_medium, utm_campaign, utm_content)):
                continue

            source_quotation = quotation_by_id.get(
                getattr(order, "source_quotation_id", None)
            )
            source_opportunity = opportunity_by_id.get(
                getattr(source_quotation, "opportunity_id", None)
                if source_quotation is not None
                else None
            )
            if (
                params.record_type == CRMPipelineRecordType.OPPORTUNITY
                and source_opportunity is None
            ):
                continue
            if (
                params.record_type == CRMPipelineRecordType.QUOTATION
                and source_quotation is None
            ):
                continue
            territory = str(
                getattr(source_quotation, "territory", "")
                or _extract_snapshot_text(crm_context_snapshot, "territory")
            )
            customer_group = str(
                getattr(source_quotation, "customer_group", "")
                or _extract_snapshot_text(crm_context_snapshot, "customer_group")
            )
            owner = str(getattr(source_opportunity, "opportunity_owner", "") or "")
            sales_stage = str(getattr(source_opportunity, "sales_stage", "") or "")

            if not _matches_attribution_filters(
                params=params,
                sales_stage=sales_stage,
                territory=territory,
                customer_group=customer_group,
                owner=owner,
                utm_source=utm_source,
                utm_medium=utm_medium,
                utm_campaign=utm_campaign,
                utm_content=utm_content,
            ):
                continue

            ordered_revenue = _quantized_amount(getattr(order, "total_amount", None))
            totals.ordered_revenue = (
                totals.ordered_revenue + ordered_revenue
            ).quantize(Decimal("0.01"))

            if utm_source:
                _upsert_pipeline_bucket(
                    by_utm_source,
                    record_type="order",
                    key=utm_source,
                    label=utm_source,
                    amount=ordered_revenue,
                    ordered_revenue=ordered_revenue,
                )
            if utm_medium:
                _upsert_pipeline_bucket(
                    by_utm_medium,
                    record_type="order",
                    key=utm_medium,
                    label=utm_medium,
                    amount=ordered_revenue,
                    ordered_revenue=ordered_revenue,
                )
            if utm_campaign:
                _upsert_pipeline_bucket(
                    by_utm_campaign,
                    record_type="order",
                    key=utm_campaign,
                    label=utm_campaign,
                    amount=ordered_revenue,
                    ordered_revenue=ordered_revenue,
                )
            if utm_content:
                _upsert_pipeline_bucket(
                    by_utm_content,
                    record_type="order",
                    key=utm_content,
                    label=utm_content,
                    amount=ordered_revenue,
                    ordered_revenue=ordered_revenue,
                )

    if conversion_time_samples > 0:
        totals.avg_days_to_conversion = (
            conversion_time_total / Decimal(conversion_time_samples)
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
        previous_analytics = {
            "kpis": CRMPipelineAnalyticsKpis(),
            "funnel": [],
            "terminal_by_status": [],
            "terminal_by_lost_reason": [],
            "terminal_by_competitor": [],
            "owner_scorecards": [],
            "drilldowns": [],
        }
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
        totals=totals,
        analytics=analytics,
        by_status=_build_pipeline_segment_list(by_status),
        by_sales_stage=_build_pipeline_segment_list(by_sales_stage),
        by_territory=_build_pipeline_segment_list(by_territory),
        by_customer_group=_build_pipeline_segment_list(by_customer_group),
        by_owner=_build_pipeline_segment_list(by_owner),
        by_lost_reason=_build_pipeline_segment_list(by_lost_reason),
        by_utm_source=_build_pipeline_segment_list(by_utm_source),
        by_utm_medium=_build_pipeline_segment_list(by_utm_medium),
        by_utm_campaign=_build_pipeline_segment_list(by_utm_campaign),
        by_utm_content=_build_pipeline_segment_list(by_utm_content),
        by_conversion_path=_build_pipeline_segment_list(by_conversion_path),
        by_conversion_source=_build_pipeline_segment_list(by_conversion_source),
        dropoff=dropoff,
    )
