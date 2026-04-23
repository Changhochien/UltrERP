"""Report assembly helpers for CRM pipeline reporting."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from domains.crm._pipeline_common import (
    _BucketDict,
    _LeadAttrs,
    _OpportunityAttrs,
    _QuotationAttrs,
    _extract_snapshot_text,
    _extract_utm_snapshot,
    _matches_attribution_filters,
    _matches_common_filters,
    _precompute_lead_attrs,
    _precompute_opportunity_attrs,
    _precompute_quotation_attrs,
    _quantized_amount,
    _upsert_pipeline_bucket,
)
from domains.crm.schemas import (
    CRMPipelineDropOff,
    CRMPipelineRecordType,
    CRMPipelineReportParams,
    CRMPipelineScope,
    CRMPipelineTotals,
    LeadStatus,
    OpportunityStatus,
)


@dataclass(slots=True)
class _PipelineReportAggregation:
    totals: CRMPipelineTotals = field(default_factory=CRMPipelineTotals)
    by_status: _BucketDict = field(default_factory=dict)
    by_sales_stage: _BucketDict = field(default_factory=dict)
    by_territory: _BucketDict = field(default_factory=dict)
    by_customer_group: _BucketDict = field(default_factory=dict)
    by_owner: _BucketDict = field(default_factory=dict)
    by_lost_reason: _BucketDict = field(default_factory=dict)
    by_utm_source: _BucketDict = field(default_factory=dict)
    by_utm_medium: _BucketDict = field(default_factory=dict)
    by_utm_campaign: _BucketDict = field(default_factory=dict)
    by_utm_content: _BucketDict = field(default_factory=dict)
    by_conversion_path: _BucketDict = field(default_factory=dict)
    by_conversion_source: _BucketDict = field(default_factory=dict)
    dropoff: CRMPipelineDropOff = field(default_factory=CRMPipelineDropOff)
    conversion_time_total: Decimal = Decimal("0.00")
    conversion_time_samples: int = 0


def _include_record(params: CRMPipelineReportParams, record_type: CRMPipelineRecordType) -> bool:
    return params.record_type in {CRMPipelineRecordType.ALL, record_type}


def _accumulate_lead_rows(
    aggregation: _PipelineReportAggregation,
    precomputed_leads: list[tuple[object, _LeadAttrs]],
    params: CRMPipelineReportParams,
) -> None:
    for lead, attrs in precomputed_leads:
        if not _include_record(params, CRMPipelineRecordType.LEAD):
            continue
        scope = attrs["scope"]
        if params.sales_stage:
            continue
        if not _matches_common_filters(
            params=params,
            scope=scope,
            status=attrs["status"],
            territory=attrs["territory"],
            customer_group="",
            owner=attrs["owner"],
            lost_reason="",
            utm_source=attrs["utm_source"],
            utm_medium=attrs["utm_medium"],
            utm_campaign=attrs["utm_campaign"],
            utm_content=attrs["utm_content"],
        ):
            continue

        aggregation.totals.lead_count += 1
        if scope == CRMPipelineScope.OPEN:
            aggregation.totals.open_count += 1
        else:
            aggregation.totals.terminal_count += 1
        if attrs["status"] not in {
            LeadStatus.OPPORTUNITY.value,
            LeadStatus.QUOTATION.value,
            LeadStatus.CONVERTED.value,
        }:
            aggregation.dropoff.lead_only_count += 1

        _upsert_pipeline_bucket(
            aggregation.by_status,
            record_type="lead",
            key=attrs["status"],
            label=attrs["status"],
            amount=Decimal("0.00"),
        )
        if attrs["territory"]:
            _upsert_pipeline_bucket(
                aggregation.by_territory,
                record_type="lead",
                key=attrs["territory"],
                label=attrs["territory"],
                amount=Decimal("0.00"),
            )
        if attrs["owner"]:
            _upsert_pipeline_bucket(
                aggregation.by_owner,
                record_type="lead",
                key=attrs["owner"],
                label=attrs["owner"],
                amount=Decimal("0.00"),
            )
        if attrs["utm_source"]:
            _upsert_pipeline_bucket(
                aggregation.by_utm_source,
                record_type="lead",
                key=attrs["utm_source"],
                label=attrs["utm_source"],
                amount=Decimal("0.00"),
            )
        if attrs["utm_medium"]:
            _upsert_pipeline_bucket(
                aggregation.by_utm_medium,
                record_type="lead",
                key=attrs["utm_medium"],
                label=attrs["utm_medium"],
                amount=Decimal("0.00"),
            )
        if attrs["utm_campaign"]:
            _upsert_pipeline_bucket(
                aggregation.by_utm_campaign,
                record_type="lead",
                key=attrs["utm_campaign"],
                label=attrs["utm_campaign"],
                amount=Decimal("0.00"),
            )
        if attrs["utm_content"]:
            _upsert_pipeline_bucket(
                aggregation.by_utm_content,
                record_type="lead",
                key=attrs["utm_content"],
                label=attrs["utm_content"],
                amount=Decimal("0.00"),
            )

        conversion_state = attrs["conversion_state"]
        converted_at = attrs["converted_at"]
        created_at = attrs["created_at"]
        conversion_path = attrs["conversion_path"]
        conversion_source = attrs["source"]
        if conversion_state not in {"", "not_converted"} or converted_at is not None:
            aggregation.totals.conversion_count += 1
            if conversion_path:
                _upsert_pipeline_bucket(
                    aggregation.by_conversion_path,
                    record_type="lead",
                    key=conversion_path,
                    label=conversion_path,
                    amount=Decimal("0.00"),
                )
            if conversion_source:
                _upsert_pipeline_bucket(
                    aggregation.by_conversion_source,
                    record_type="lead",
                    key=conversion_source,
                    label=conversion_source,
                    amount=Decimal("0.00"),
                )
            if created_at is not None and converted_at is not None:
                elapsed_days = Decimal(
                    str((converted_at - created_at).total_seconds() / 86400)
                ).quantize(Decimal("0.01"))
                aggregation.conversion_time_total = (
                    aggregation.conversion_time_total + elapsed_days
                ).quantize(Decimal("0.01"))
                aggregation.conversion_time_samples += 1


def _accumulate_opportunity_rows(
    aggregation: _PipelineReportAggregation,
    precomputed_opportunities: list[tuple[object, _OpportunityAttrs]],
    params: CRMPipelineReportParams,
) -> None:
    for _opportunity, attrs in precomputed_opportunities:
        if not _include_record(params, CRMPipelineRecordType.OPPORTUNITY):
            continue
        scope = attrs["scope"]
        if params.sales_stage and attrs["sales_stage"] != params.sales_stage:
            continue
        amount = attrs["amount"]
        if not _matches_common_filters(
            params=params,
            scope=scope,
            status=attrs["status"],
            territory=attrs["territory"],
            customer_group=attrs["customer_group"],
            owner=attrs["owner"],
            lost_reason=attrs["lost_reason"],
            utm_source=attrs["utm_source"],
            utm_medium=attrs["utm_medium"],
            utm_campaign=attrs["utm_campaign"],
            utm_content=attrs["utm_content"],
        ):
            continue

        aggregation.totals.opportunity_count += 1
        if scope == CRMPipelineScope.OPEN:
            aggregation.totals.open_count += 1
            aggregation.totals.open_pipeline_amount = (
                aggregation.totals.open_pipeline_amount + amount
            ).quantize(Decimal("0.01"))
        else:
            aggregation.totals.terminal_count += 1
            aggregation.totals.terminal_pipeline_amount = (
                aggregation.totals.terminal_pipeline_amount + amount
            ).quantize(Decimal("0.01"))
        if attrs["status"] not in {
            OpportunityStatus.QUOTATION.value,
            OpportunityStatus.CONVERTED.value,
        }:
            aggregation.dropoff.opportunity_without_quotation_count += 1

        _upsert_pipeline_bucket(
            aggregation.by_status,
            record_type="opportunity",
            key=attrs["status"],
            label=attrs["status"],
            amount=amount,
        )
        _upsert_pipeline_bucket(
            aggregation.by_sales_stage,
            record_type="opportunity",
            key=attrs["sales_stage"],
            label=attrs["sales_stage"],
            amount=amount,
        )
        if attrs["territory"]:
            _upsert_pipeline_bucket(
                aggregation.by_territory,
                record_type="opportunity",
                key=attrs["territory"],
                label=attrs["territory"],
                amount=amount,
            )
        if attrs["customer_group"]:
            _upsert_pipeline_bucket(
                aggregation.by_customer_group,
                record_type="opportunity",
                key=attrs["customer_group"],
                label=attrs["customer_group"],
                amount=amount,
            )
        if attrs["owner"]:
            _upsert_pipeline_bucket(
                aggregation.by_owner,
                record_type="opportunity",
                key=attrs["owner"],
                label=attrs["owner"],
                amount=amount,
            )
        if attrs["lost_reason"]:
            _upsert_pipeline_bucket(
                aggregation.by_lost_reason,
                record_type="opportunity",
                key=attrs["lost_reason"],
                label=attrs["lost_reason"],
                amount=amount,
            )
        if attrs["utm_source"]:
            _upsert_pipeline_bucket(
                aggregation.by_utm_source,
                record_type="opportunity",
                key=attrs["utm_source"],
                label=attrs["utm_source"],
                amount=amount,
            )
        if attrs["utm_medium"]:
            _upsert_pipeline_bucket(
                aggregation.by_utm_medium,
                record_type="opportunity",
                key=attrs["utm_medium"],
                label=attrs["utm_medium"],
                amount=amount,
            )
        if attrs["utm_campaign"]:
            _upsert_pipeline_bucket(
                aggregation.by_utm_campaign,
                record_type="opportunity",
                key=attrs["utm_campaign"],
                label=attrs["utm_campaign"],
                amount=amount,
            )
        if attrs["utm_content"]:
            _upsert_pipeline_bucket(
                aggregation.by_utm_content,
                record_type="opportunity",
                key=attrs["utm_content"],
                label=attrs["utm_content"],
                amount=amount,
            )


def _accumulate_quotation_rows(
    aggregation: _PipelineReportAggregation,
    precomputed_quotations: list[tuple[object, _QuotationAttrs]],
    params: CRMPipelineReportParams,
) -> None:
    for _quotation, attrs in precomputed_quotations:
        if not _include_record(params, CRMPipelineRecordType.QUOTATION):
            continue
        scope = attrs["scope"]
        if params.sales_stage:
            continue
        amount = attrs["amount"]
        if not _matches_common_filters(
            params=params,
            scope=scope,
            status=attrs["status"],
            territory=attrs["territory"],
            customer_group=attrs["customer_group"],
            owner="",
            lost_reason=attrs["lost_reason"],
            utm_source=attrs["utm_source"],
            utm_medium=attrs["utm_medium"],
            utm_campaign=attrs["utm_campaign"],
            utm_content=attrs["utm_content"],
        ):
            continue

        aggregation.totals.quotation_count += 1
        if scope == CRMPipelineScope.OPEN:
            aggregation.totals.open_count += 1
            aggregation.totals.open_pipeline_amount = (
                aggregation.totals.open_pipeline_amount + amount
            ).quantize(Decimal("0.01"))
        else:
            aggregation.totals.terminal_count += 1
            aggregation.totals.terminal_pipeline_amount = (
                aggregation.totals.terminal_pipeline_amount + amount
            ).quantize(Decimal("0.01"))
        if attrs["order_count"] > 0:
            aggregation.dropoff.quotation_with_order_count += 1
        else:
            aggregation.dropoff.quotation_without_order_count += 1

        _upsert_pipeline_bucket(
            aggregation.by_status,
            record_type="quotation",
            key=attrs["status"],
            label=attrs["status"],
            amount=amount,
        )
        if attrs["territory"]:
            _upsert_pipeline_bucket(
                aggregation.by_territory,
                record_type="quotation",
                key=attrs["territory"],
                label=attrs["territory"],
                amount=amount,
            )
        if attrs["customer_group"]:
            _upsert_pipeline_bucket(
                aggregation.by_customer_group,
                record_type="quotation",
                key=attrs["customer_group"],
                label=attrs["customer_group"],
                amount=amount,
            )
        if attrs["lost_reason"]:
            _upsert_pipeline_bucket(
                aggregation.by_lost_reason,
                record_type="quotation",
                key=attrs["lost_reason"],
                label=attrs["lost_reason"],
                amount=amount,
            )
        if attrs["utm_source"]:
            _upsert_pipeline_bucket(
                aggregation.by_utm_source,
                record_type="quotation",
                key=attrs["utm_source"],
                label=attrs["utm_source"],
                amount=amount,
            )
        if attrs["utm_medium"]:
            _upsert_pipeline_bucket(
                aggregation.by_utm_medium,
                record_type="quotation",
                key=attrs["utm_medium"],
                label=attrs["utm_medium"],
                amount=amount,
            )
        if attrs["utm_campaign"]:
            _upsert_pipeline_bucket(
                aggregation.by_utm_campaign,
                record_type="quotation",
                key=attrs["utm_campaign"],
                label=attrs["utm_campaign"],
                amount=amount,
            )
        if attrs["utm_content"]:
            _upsert_pipeline_bucket(
                aggregation.by_utm_content,
                record_type="quotation",
                key=attrs["utm_content"],
                label=attrs["utm_content"],
                amount=amount,
            )


def _accumulate_order_attribution(
    aggregation: _PipelineReportAggregation,
    orders: list[object],
    quotation_by_id: dict[object, object],
    opportunity_by_id: dict[object, object],
    params: CRMPipelineReportParams,
) -> None:
    if params.record_type not in {
        CRMPipelineRecordType.ALL,
        CRMPipelineRecordType.OPPORTUNITY,
        CRMPipelineRecordType.QUOTATION,
    }:
        return

    for order in orders:
        crm_context_snapshot = getattr(order, "crm_context_snapshot", None)
        utm_source, utm_medium, utm_campaign, utm_content = _extract_utm_snapshot(crm_context_snapshot)
        if not any((utm_source, utm_medium, utm_campaign, utm_content)):
            continue

        source_quotation = quotation_by_id.get(getattr(order, "source_quotation_id", None))
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
        aggregation.totals.ordered_revenue = (
            aggregation.totals.ordered_revenue + ordered_revenue
        ).quantize(Decimal("0.01"))

        if utm_source:
            _upsert_pipeline_bucket(
                aggregation.by_utm_source,
                record_type="order",
                key=utm_source,
                label=utm_source,
                amount=ordered_revenue,
                ordered_revenue=ordered_revenue,
            )
        if utm_medium:
            _upsert_pipeline_bucket(
                aggregation.by_utm_medium,
                record_type="order",
                key=utm_medium,
                label=utm_medium,
                amount=ordered_revenue,
                ordered_revenue=ordered_revenue,
            )
        if utm_campaign:
            _upsert_pipeline_bucket(
                aggregation.by_utm_campaign,
                record_type="order",
                key=utm_campaign,
                label=utm_campaign,
                amount=ordered_revenue,
                ordered_revenue=ordered_revenue,
            )
        if utm_content:
            _upsert_pipeline_bucket(
                aggregation.by_utm_content,
                record_type="order",
                key=utm_content,
                label=utm_content,
                amount=ordered_revenue,
                ordered_revenue=ordered_revenue,
            )


def _build_report_aggregation(
    *,
    leads: list[object],
    opportunities: list[object],
    quotations: list[object],
    orders: list[object],
    quotation_by_id: dict[object, object],
    opportunity_by_id: dict[object, object],
    params: CRMPipelineReportParams,
) -> _PipelineReportAggregation:
    aggregation = _PipelineReportAggregation()
    precomputed_leads: list[tuple[object, _LeadAttrs]] = [
        (lead, _precompute_lead_attrs(lead)) for lead in leads
    ]
    precomputed_opportunities: list[tuple[object, _OpportunityAttrs]] = [
        (opp, _precompute_opportunity_attrs(opp)) for opp in opportunities
    ]
    precomputed_quotations: list[tuple[object, _QuotationAttrs]] = [
        (quote, _precompute_quotation_attrs(quote)) for quote in quotations
    ]

    _accumulate_lead_rows(aggregation, precomputed_leads, params)
    _accumulate_opportunity_rows(aggregation, precomputed_opportunities, params)
    _accumulate_quotation_rows(aggregation, precomputed_quotations, params)
    _accumulate_order_attribution(
        aggregation,
        orders,
        quotation_by_id,
        opportunity_by_id,
        params,
    )
    return aggregation