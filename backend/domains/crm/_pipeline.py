"""CRM pipeline reporting services."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.models.order import Order
from common.tenant import DEFAULT_TENANT_ID, set_tenant
from domains.crm.models import Lead, Opportunity, Quotation
from domains.crm.schemas import (
    CRMPipelineDropOff,
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

    return CRMPipelineReportResponse(
        filters=params,
        totals=totals,
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
