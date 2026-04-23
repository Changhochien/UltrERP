"""Analytics helpers for CRM pipeline reporting."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from domains.crm._pipeline_common import (
    _BucketDict,
    _LeadAttrs,
    _OpportunityAttrs,
    _QuotationAttrs,
    _build_pipeline_segment_list,
    _extract_utm_snapshot,
    _lead_conversion_targets,
    _lead_is_converted_compatible,
    _matches_analytics_filters,
    _matches_period,
    _opportunity_scope,
    _percentage,
    _precompute_lead_attrs,
    _precompute_opportunity_attrs,
    _precompute_quotation_attrs,
    _quantized_amount,
    _quotation_scope,
    _upsert_pipeline_bucket,
)
from domains.crm.schemas import (
    CRMPipelineAnalyticsKpis,
    CRMPipelineDrilldownGroup,
    CRMPipelineDrilldownRecord,
    CRMPipelineFunnelStage,
    CRMPipelineOwnerScorecard,
    CRMPipelineReportParams,
    CRMPipelineScope,
    LeadStatus,
    OpportunityStatus,
)


def _empty_analytics_snapshot() -> dict[str, object]:
    return {
        "kpis": CRMPipelineAnalyticsKpis(),
        "funnel": [],
        "terminal_by_status": [],
        "terminal_by_lost_reason": [],
        "terminal_by_competitor": [],
        "owner_scorecards": [],
        "drilldowns": [],
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
    precomputed_leads: list[tuple[object, _LeadAttrs]] = [
        (lead, _precompute_lead_attrs(lead)) for lead in leads
    ]
    precomputed_opportunities: list[tuple[object, _OpportunityAttrs]] = [
        (opp, _precompute_opportunity_attrs(opp)) for opp in opportunities
    ]
    precomputed_quotations: list[tuple[object, _QuotationAttrs]] = [
        (quote, _precompute_quotation_attrs(quote)) for quote in quotations
    ]

    filtered_leads: list[object] = []
    filtered_opportunities: list[object] = []
    filtered_quotations: list[object] = []
    filtered_orders: list[tuple[object, object | None, object | None]] = []

    terminal_by_status: _BucketDict = {}
    terminal_by_lost_reason: _BucketDict = {}
    terminal_by_competitor: _BucketDict = {}
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

    for lead, attrs in precomputed_leads:
        if not _matches_analytics_filters(
            params=params,
            sales_stage="",
            territory=attrs["territory"],
            customer_group="",
            owner=attrs["owner"],
            utm_source=attrs["utm_source"],
            utm_medium=attrs["utm_medium"],
            utm_campaign=attrs["utm_campaign"],
            utm_content=attrs["utm_content"],
        ):
            continue
        if not _matches_period(attrs["created_at"], start_date, end_date):
            continue
        filtered_leads.append(lead)
        owner = attrs["owner"]
        owner_bucket(owner)["assigned_leads"] = int(owner_bucket(owner)["assigned_leads"]) + 1

        if _lead_is_converted_compatible(lead):
            created_at = attrs["created_at"]
            converted_at = attrs["converted_at"]
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

    for opportunity, attrs in precomputed_opportunities:
        if not _matches_analytics_filters(
            params=params,
            sales_stage=attrs["sales_stage"],
            territory=attrs["territory"],
            customer_group=attrs["customer_group"],
            owner=attrs["owner"],
            utm_source=attrs["utm_source"],
            utm_medium=attrs["utm_medium"],
            utm_campaign=attrs["utm_campaign"],
            utm_content=attrs["utm_content"],
        ):
            continue
        period_value = attrs["expected_closing"] or attrs["created_at"]
        if not _matches_period(period_value, start_date, end_date):
            continue

        filtered_opportunities.append(opportunity)
        amount = attrs["amount"]
        probability = attrs["probability"]
        status = attrs["status"]
        bucket = owner_bucket(attrs["owner"])
        bucket["owned_opportunities"] = int(bucket["owned_opportunities"]) + 1
        if attrs["scope"] == CRMPipelineScope.OPEN:
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

        if attrs["scope"] == CRMPipelineScope.TERMINAL:
            _upsert_pipeline_bucket(
                terminal_by_status,
                record_type="opportunity",
                key=status,
                label=status,
                amount=amount,
            )
            lost_reason = attrs["lost_reason"]
            if lost_reason:
                _upsert_pipeline_bucket(
                    terminal_by_lost_reason,
                    record_type="opportunity",
                    key=lost_reason,
                    label=lost_reason,
                    amount=amount,
                )
            competitor = attrs["competitor_name"]
            if competitor:
                _upsert_pipeline_bucket(
                    terminal_by_competitor,
                    record_type="opportunity",
                    key=competitor,
                    label=competitor,
                    amount=amount,
                )

    for quotation, attrs in precomputed_quotations:
        if not _matches_analytics_filters(
            params=params,
            sales_stage="",
            territory=attrs["territory"],
            customer_group=attrs["customer_group"],
            owner="",
            utm_source=attrs["utm_source"],
            utm_medium=attrs["utm_medium"],
            utm_campaign=attrs["utm_campaign"],
            utm_content=attrs["utm_content"],
        ):
            continue
        period_value = attrs["transaction_date"] or attrs["created_at"]
        if not _matches_period(period_value, start_date, end_date):
            continue

        filtered_quotations.append(quotation)
        amount = attrs["amount"]
        if attrs["scope"] == CRMPipelineScope.TERMINAL:
            _upsert_pipeline_bucket(
                terminal_by_status,
                record_type="quotation",
                key=attrs["status"],
                label=attrs["status"],
                amount=amount,
            )
            lost_reason = attrs["lost_reason"]
            if lost_reason:
                _upsert_pipeline_bucket(
                    terminal_by_lost_reason,
                    record_type="quotation",
                    key=lost_reason,
                    label=lost_reason,
                    amount=amount,
                )
            competitor = attrs["competitor_name"]
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
        crm_context_snapshot = getattr(order, "crm_context_snapshot", None)
        utm_source, utm_medium, utm_campaign, utm_content = _extract_utm_snapshot(crm_context_snapshot)
        territory = str(getattr(source_quotation, "territory", "") or "")
        customer_group = str(getattr(source_quotation, "customer_group", "") or "")
        owner = str(getattr(source_opportunity, "opportunity_owner", "") or "")
        sales_stage = str(getattr(source_opportunity, "sales_stage", "") or "")
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
    for key, label, count in funnel_counts:
        funnel.append(
            CRMPipelineFunnelStage(
                key=key,
                label=label,
                count=count,
                dropoff_count=0 if previous_count == 0 else max(previous_count - count, 0),
                conversion_rate=Decimal("100.00") if previous_count == 0 and count > 0 else _percentage(count, previous_count),
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

    def _build_drilldown_record(
        record_type: str,
        record_id: str,
        label: str,
        status: str,
        owner: str,
        amount: Decimal,
    ) -> CRMPipelineDrilldownRecord:
        return CRMPipelineDrilldownRecord(
            record_type=record_type,
            record_id=record_id,
            label=label,
            status=status,
            owner=owner,
            amount=amount,
        )

    drilldowns = [
        CRMPipelineDrilldownGroup(
            key="qualified_leads",
            label="Qualified Leads",
            records=[
                _build_drilldown_record(
                    record_type="lead",
                    record_id=str(getattr(lead, "id", "")),
                    label=str(
                        getattr(lead, "company_name", "")
                        or getattr(lead, "lead_name", "")
                        or getattr(lead, "id", "")
                    ),
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
                _build_drilldown_record(
                    record_type="opportunity",
                    record_id=str(getattr(opp, "id", "")),
                    label=str(getattr(opp, "opportunity_title", "") or getattr(opp, "id", "")),
                    status=str(getattr(opp, "status", "") or ""),
                    owner=str(getattr(opp, "opportunity_owner", "") or ""),
                    amount=_quantized_amount(getattr(opp, "opportunity_amount", None)),
                )
                for opp in filtered_opportunities
                if _opportunity_scope(str(getattr(opp, "status", "") or "")) == CRMPipelineScope.OPEN
            ],
        ),
        CRMPipelineDrilldownGroup(
            key="terminal_outcomes",
            label="Terminal Outcomes",
            records=[
                *[
                    _build_drilldown_record(
                        record_type="opportunity",
                        record_id=str(getattr(opp, "id", "")),
                        label=str(getattr(opp, "opportunity_title", "") or getattr(opp, "id", "")),
                        status=str(getattr(opp, "status", "") or ""),
                        owner=str(getattr(opp, "opportunity_owner", "") or ""),
                        amount=_quantized_amount(getattr(opp, "opportunity_amount", None)),
                    )
                    for opp in filtered_opportunities
                    if _opportunity_scope(str(getattr(opp, "status", "") or "")) == CRMPipelineScope.TERMINAL
                ],
                *[
                    _build_drilldown_record(
                        record_type="quotation",
                        record_id=str(getattr(quote, "id", "")),
                        label=str(getattr(quote, "party_label", "") or getattr(quote, "id", "")),
                        status=str(getattr(quote, "status", "") or ""),
                        owner="",
                        amount=_quantized_amount(getattr(quote, "grand_total", None)),
                    )
                    for quote in filtered_quotations
                    if _quotation_scope(str(getattr(quote, "status", "") or "")) == CRMPipelineScope.TERMINAL
                ],
            ],
        ),
        CRMPipelineDrilldownGroup(
            key="converted_orders",
            label="Converted Orders",
            records=[
                _build_drilldown_record(
                    record_type="order",
                    record_id=str(getattr(order, "id", "")),
                    label=f"Order {getattr(order, 'id', '')}",
                    status=str(getattr(order, "status", "") or ""),
                    owner=str(getattr(source_opportunity, "opportunity_owner", "") if source_opportunity else ""),
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