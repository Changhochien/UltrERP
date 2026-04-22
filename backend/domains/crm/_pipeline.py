"""CRM pipeline reporting services."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from functools import partial

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

# Terminal statuses for each record type - used by _record_scope()
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

# Scope resolution mapping: record_type -> frozenset of terminal statuses
_SCOPE_MAP: dict[str, frozenset[str]] = {
    "lead": TERMINAL_LEAD_STATUSES,
    "opportunity": TERMINAL_OPPORTUNITY_STATUSES,
    "quotation": TERMINAL_QUOTATION_STATUSES,
}

# Type aliases for bucket dictionaries used throughout the pipeline report
_PipelineBucket = dict[str, object]
_BucketDict = dict[tuple[str | None, str], _PipelineBucket]


# =============================================================================
# Utility Functions
# =============================================================================


def _quantized_amount(value: object | None) -> Decimal:
    if value is None or value == "":
        return Decimal("0.00")
    return Decimal(str(value)).quantize(Decimal("0.01"))


def _build_pipeline_segment_list(buckets: _BucketDict) -> list[CRMPipelineSegment]:
    items = [CRMPipelineSegment.model_validate(item) for item in buckets.values()]
    return sorted(
        items,
        key=lambda item: (-item.count, item.label.lower(), item.record_type or ""),
    )


def _upsert_pipeline_bucket(
    buckets: _BucketDict,
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


# =============================================================================
# Snapshot & Attribution Helpers
# =============================================================================


def _extract_snapshot_text(snapshot: dict[str, object] | None, key: str) -> str:
    """Extract a string value from a CRM context snapshot dict."""
    if not isinstance(snapshot, dict):
        return ""
    value = snapshot.get(key)
    return value.strip() if isinstance(value, str) else ""


def _extract_utm_snapshot(snapshot: dict[str, object] | None) -> tuple[str, str, str, str]:
    """Extract all UTM values from a CRM context snapshot.
    
    Returns:
        Tuple of (utm_source, utm_medium, utm_campaign, utm_content)
    """
    return (
        _extract_snapshot_text(snapshot, "utm_source"),
        _extract_snapshot_text(snapshot, "utm_medium"),
        _extract_snapshot_text(snapshot, "utm_campaign"),
        _extract_snapshot_text(snapshot, "utm_content"),
    )


# =============================================================================
# Scope Resolution
# =============================================================================


def _record_scope(record_type: str, status: str) -> CRMPipelineScope:
    """Determine if a record is in OPEN or TERMINAL scope based on its type and status.
    
    Args:
        record_type: One of 'lead', 'opportunity', or 'quotation'
        status: The current status of the record
        
    Returns:
        CRMPipelineScope.TERMINAL if status is terminal, CRMPipelineScope.OPEN otherwise
    """
    terminal_statuses = _SCOPE_MAP.get(record_type, frozenset())
    return CRMPipelineScope.TERMINAL if status in terminal_statuses else CRMPipelineScope.OPEN


# Convenience aliases for backward compatibility - marked as deprecated
_lead_scope = partial(_record_scope, "lead")
_opportunity_scope = partial(_record_scope, "opportunity")
_quotation_scope = partial(_record_scope, "quotation")


# =============================================================================
# UTM/Attribution Filter Helpers
# =============================================================================


def _matches_utm_filters(
    *,
    params: CRMPipelineReportParams,
    utm_source: str,
    utm_medium: str,
    utm_campaign: str,
    utm_content: str,
) -> bool:
    """Check if record matches UTM attribution filters.
    
    Shared logic used by both report filtering and analytics filtering.
    """
    if params.utm_source and utm_source != params.utm_source:
        return False
    if params.utm_medium and utm_medium != params.utm_medium:
        return False
    if params.utm_campaign and utm_campaign != params.utm_campaign:
        return False
    if params.utm_content and utm_content != params.utm_content:
        return False
    return True


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
    """Check if record matches all attribution filters for order attribution analysis."""
    if params.sales_stage and sales_stage != params.sales_stage:
        return False
    if params.territory and territory != params.territory:
        return False
    if params.customer_group and customer_group != params.customer_group:
        return False
    if params.owner and owner != params.owner:
        return False
    return _matches_utm_filters(
        params=params,
        utm_source=utm_source,
        utm_medium=utm_medium,
        utm_campaign=utm_campaign,
        utm_content=utm_content,
    )


# =============================================================================
# Filter Matching Functions
# =============================================================================


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
    """Check if record matches common report filters (scope, status, dimensions, UTM)."""
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
    return _matches_utm_filters(
        params=params,
        utm_source=utm_source,
        utm_medium=utm_medium,
        utm_campaign=utm_campaign,
        utm_content=utm_content,
    )


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
    """Check if record matches analytics filters (dimensions, UTM).
    
    Note: Does not filter by scope/status as analytics computes those internally.
    """
    if params.sales_stage and sales_stage != params.sales_stage:
        return False
    if params.territory and territory != params.territory:
        return False
    if params.customer_group and customer_group != params.customer_group:
        return False
    if params.owner and owner != params.owner:
        return False
    return _matches_utm_filters(
        params=params,
        utm_source=utm_source,
        utm_medium=utm_medium,
        utm_campaign=utm_campaign,
        utm_content=utm_content,
    )


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
    # Import constants from _lead.py to maintain consistency
    from domains.crm._lead import (
        CONVERSION_TARGET_CUSTOMER,
        CONVERSION_TARGET_OPPORTUNITY,
        CONVERSION_TARGET_QUOTATION,
    )

    targets = {
        part.strip()
        for part in str(getattr(lead, "conversion_path", "") or "").split("+")
        if part.strip()
    }
    if getattr(lead, "converted_customer_id", None) is not None:
        targets.add(CONVERSION_TARGET_CUSTOMER)
    if getattr(lead, "converted_opportunity_id", None) is not None:
        targets.add(CONVERSION_TARGET_OPPORTUNITY)
    if getattr(lead, "converted_quotation_id", None) is not None:
        targets.add(CONVERSION_TARGET_QUOTATION)
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


# =============================================================================
# Pre-computed Record Attributes
# =============================================================================
# Type alias for pre-computed record metadata to avoid repeated getattr calls
_LeadAttrs = dict[str, object]
_OpportunityAttrs = dict[str, object]
_QuotationAttrs = dict[str, object]


def _precompute_lead_attrs(lead: object) -> _LeadAttrs:
    """Pre-compute common lead attributes to avoid repeated getattr calls."""
    return {
        "id": getattr(lead, "id", None),
        "status": str(getattr(lead, "status", "") or ""),
        "scope": _lead_scope(str(getattr(lead, "status", "") or "")),
        "territory": str(getattr(lead, "territory", "") or ""),
        "owner": str(getattr(lead, "lead_owner", "") or ""),
        "utm_source": str(getattr(lead, "utm_source", "") or ""),
        "utm_medium": str(getattr(lead, "utm_medium", "") or ""),
        "utm_campaign": str(getattr(lead, "utm_campaign", "") or ""),
        "utm_content": str(getattr(lead, "utm_content", "") or ""),
        "qualification_status": str(getattr(lead, "qualification_status", "") or ""),
        "conversion_state": str(getattr(lead, "conversion_state", "") or ""),
        "conversion_path": str(getattr(lead, "conversion_path", "") or ""),
        "source": str(getattr(lead, "source", "") or ""),
        "created_at": getattr(lead, "created_at", None),
        "converted_at": getattr(lead, "converted_at", None),
        "company_name": getattr(lead, "company_name", None),
        "lead_name": getattr(lead, "lead_name", None),
        "converted_customer_id": getattr(lead, "converted_customer_id", None),
        "converted_opportunity_id": getattr(lead, "converted_opportunity_id", None),
        "converted_quotation_id": getattr(lead, "converted_quotation_id", None),
    }


def _precompute_opportunity_attrs(opportunity: object) -> _OpportunityAttrs:
    """Pre-compute common opportunity attributes to avoid repeated getattr calls."""
    status = str(getattr(opportunity, "status", "") or "")
    return {
        "id": getattr(opportunity, "id", None),
        "status": status,
        "scope": _opportunity_scope(status),
        "sales_stage": str(getattr(opportunity, "sales_stage", "") or ""),
        "territory": str(getattr(opportunity, "territory", "") or ""),
        "customer_group": str(getattr(opportunity, "customer_group", "") or ""),
        "owner": str(getattr(opportunity, "opportunity_owner", "") or ""),
        "lost_reason": str(getattr(opportunity, "lost_reason", "") or ""),
        "competitor_name": str(getattr(opportunity, "competitor_name", "") or ""),
        "utm_source": str(getattr(opportunity, "utm_source", "") or ""),
        "utm_medium": str(getattr(opportunity, "utm_medium", "") or ""),
        "utm_campaign": str(getattr(opportunity, "utm_campaign", "") or ""),
        "utm_content": str(getattr(opportunity, "utm_content", "") or ""),
        "opportunity_amount": getattr(opportunity, "opportunity_amount", None),
        "amount": _quantized_amount(getattr(opportunity, "opportunity_amount", None)),
        "probability": Decimal(str(getattr(opportunity, "probability", 0) or 0)),
        "expected_closing": getattr(opportunity, "expected_closing", None),
        "created_at": getattr(opportunity, "created_at", None),
        "opportunity_title": getattr(opportunity, "opportunity_title", None),
    }


def _precompute_quotation_attrs(quotation: object) -> _QuotationAttrs:
    """Pre-compute common quotation attributes to avoid repeated getattr calls."""
    status = str(getattr(quotation, "status", "") or "")
    return {
        "id": getattr(quotation, "id", None),
        "status": status,
        "scope": _quotation_scope(status),
        "territory": str(getattr(quotation, "territory", "") or ""),
        "customer_group": str(getattr(quotation, "customer_group", "") or ""),
        "lost_reason": str(getattr(quotation, "lost_reason", "") or ""),
        "competitor_name": str(getattr(quotation, "competitor_name", "") or ""),
        "utm_source": str(getattr(quotation, "utm_source", "") or ""),
        "utm_medium": str(getattr(quotation, "utm_medium", "") or ""),
        "utm_campaign": str(getattr(quotation, "utm_campaign", "") or ""),
        "utm_content": str(getattr(quotation, "utm_content", "") or ""),
        "grand_total": getattr(quotation, "grand_total", None),
        "amount": _quantized_amount(getattr(quotation, "grand_total", None)),
        "transaction_date": getattr(quotation, "transaction_date", None),
        "created_at": getattr(quotation, "created_at", None),
        "party_label": getattr(quotation, "party_label", None),
        "opportunity_id": getattr(quotation, "opportunity_id", None),
        "order_count": int(getattr(quotation, "order_count", 0) or 0),
    }


# =============================================================================
# Analytics Snapshot Builder
# =============================================================================


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
    # Pre-compute record attributes once to avoid repeated getattr calls
    # This optimization reduces O(n*k) attribute lookups to O(n) where k is lookup count
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
    by_status: _BucketDict = {}
    by_sales_stage: _BucketDict = {}
    by_territory: _BucketDict = {}
    by_customer_group: _BucketDict = {}
    by_owner: _BucketDict = {}
    by_lost_reason: _BucketDict = {}
    by_utm_source: _BucketDict = {}
    by_utm_medium: _BucketDict = {}
    by_utm_campaign: _BucketDict = {}
    by_utm_content: _BucketDict = {}
    by_conversion_path: _BucketDict = {}
    by_conversion_source: _BucketDict = {}
    dropoff = CRMPipelineDropOff()
    quotation_by_id = {
        getattr(quotation, "id", None): quotation for quotation in quotations
    }
    opportunity_by_id = {
        getattr(opportunity, "id", None): opportunity for opportunity in opportunities
    }
    conversion_time_total = Decimal("0.00")
    conversion_time_samples = 0

    # Pre-compute record attributes to avoid repeated getattr calls
    precomputed_leads: list[tuple[object, _LeadAttrs]] = [
        (lead, _precompute_lead_attrs(lead)) for lead in leads
    ]
    precomputed_opportunities: list[tuple[object, _OpportunityAttrs]] = [
        (opp, _precompute_opportunity_attrs(opp)) for opp in opportunities
    ]
    precomputed_quotations: list[tuple[object, _QuotationAttrs]] = [
        (quote, _precompute_quotation_attrs(quote)) for quote in quotations
    ]

    def include_record(record_type: CRMPipelineRecordType) -> bool:
        return params.record_type in {CRMPipelineRecordType.ALL, record_type}

    for lead, attrs in precomputed_leads:
        if not include_record(CRMPipelineRecordType.LEAD):
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

        totals.lead_count += 1
        if scope == CRMPipelineScope.OPEN:
            totals.open_count += 1
        else:
            totals.terminal_count += 1
        if attrs["status"] not in {
            LeadStatus.OPPORTUNITY.value,
            LeadStatus.QUOTATION.value,
            LeadStatus.CONVERTED.value,
        }:
            dropoff.lead_only_count += 1

        _upsert_pipeline_bucket(
            by_status,
            record_type="lead",
            key=attrs["status"],
            label=attrs["status"],
            amount=Decimal("0.00"),
        )
        if attrs["territory"]:
            _upsert_pipeline_bucket(
                by_territory,
                record_type="lead",
                key=attrs["territory"],
                label=attrs["territory"],
                amount=Decimal("0.00"),
            )
        if attrs["owner"]:
            _upsert_pipeline_bucket(
                by_owner,
                record_type="lead",
                key=attrs["owner"],
                label=attrs["owner"],
                amount=Decimal("0.00"),
            )
        if attrs["utm_source"]:
            _upsert_pipeline_bucket(
                by_utm_source,
                record_type="lead",
                key=attrs["utm_source"],
                label=attrs["utm_source"],
                amount=Decimal("0.00"),
            )
        if attrs["utm_medium"]:
            _upsert_pipeline_bucket(
                by_utm_medium,
                record_type="lead",
                key=attrs["utm_medium"],
                label=attrs["utm_medium"],
                amount=Decimal("0.00"),
            )
        if attrs["utm_campaign"]:
            _upsert_pipeline_bucket(
                by_utm_campaign,
                record_type="lead",
                key=attrs["utm_campaign"],
                label=attrs["utm_campaign"],
                amount=Decimal("0.00"),
            )
        if attrs["utm_content"]:
            _upsert_pipeline_bucket(
                by_utm_content,
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

    for opportunity, attrs in precomputed_opportunities:
        if not include_record(CRMPipelineRecordType.OPPORTUNITY):
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
        if attrs["status"] not in {
            OpportunityStatus.QUOTATION.value,
            OpportunityStatus.CONVERTED.value,
        }:
            dropoff.opportunity_without_quotation_count += 1

        _upsert_pipeline_bucket(
            by_status,
            record_type="opportunity",
            key=attrs["status"],
            label=attrs["status"],
            amount=amount,
        )
        _upsert_pipeline_bucket(
            by_sales_stage,
            record_type="opportunity",
            key=attrs["sales_stage"],
            label=attrs["sales_stage"],
            amount=amount,
        )
        if attrs["territory"]:
            _upsert_pipeline_bucket(
                by_territory,
                record_type="opportunity",
                key=attrs["territory"],
                label=attrs["territory"],
                amount=amount,
            )
        if attrs["customer_group"]:
            _upsert_pipeline_bucket(
                by_customer_group,
                record_type="opportunity",
                key=attrs["customer_group"],
                label=attrs["customer_group"],
                amount=amount,
            )
        if attrs["owner"]:
            _upsert_pipeline_bucket(
                by_owner,
                record_type="opportunity",
                key=attrs["owner"],
                label=attrs["owner"],
                amount=amount,
            )
        if attrs["lost_reason"]:
            _upsert_pipeline_bucket(
                by_lost_reason,
                record_type="opportunity",
                key=attrs["lost_reason"],
                label=attrs["lost_reason"],
                amount=amount,
            )
        if attrs["utm_source"]:
            _upsert_pipeline_bucket(
                by_utm_source,
                record_type="opportunity",
                key=attrs["utm_source"],
                label=attrs["utm_source"],
                amount=amount,
            )
        if attrs["utm_medium"]:
            _upsert_pipeline_bucket(
                by_utm_medium,
                record_type="opportunity",
                key=attrs["utm_medium"],
                label=attrs["utm_medium"],
                amount=amount,
            )
        if attrs["utm_campaign"]:
            _upsert_pipeline_bucket(
                by_utm_campaign,
                record_type="opportunity",
                key=attrs["utm_campaign"],
                label=attrs["utm_campaign"],
                amount=amount,
            )
        if attrs["utm_content"]:
            _upsert_pipeline_bucket(
                by_utm_content,
                record_type="opportunity",
                key=attrs["utm_content"],
                label=attrs["utm_content"],
                amount=amount,
            )

    for quotation, attrs in precomputed_quotations:
        if not include_record(CRMPipelineRecordType.QUOTATION):
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
        if attrs["order_count"] > 0:
            dropoff.quotation_with_order_count += 1
        else:
            dropoff.quotation_without_order_count += 1

        _upsert_pipeline_bucket(
            by_status,
            record_type="quotation",
            key=attrs["status"],
            label=attrs["status"],
            amount=amount,
        )
        if attrs["territory"]:
            _upsert_pipeline_bucket(
                by_territory,
                record_type="quotation",
                key=attrs["territory"],
                label=attrs["territory"],
                amount=amount,
            )
        if attrs["customer_group"]:
            _upsert_pipeline_bucket(
                by_customer_group,
                record_type="quotation",
                key=attrs["customer_group"],
                label=attrs["customer_group"],
                amount=amount,
            )
        if attrs["lost_reason"]:
            _upsert_pipeline_bucket(
                by_lost_reason,
                record_type="quotation",
                key=attrs["lost_reason"],
                label=attrs["lost_reason"],
                amount=amount,
            )
        if attrs["utm_source"]:
            _upsert_pipeline_bucket(
                by_utm_source,
                record_type="quotation",
                key=attrs["utm_source"],
                label=attrs["utm_source"],
                amount=amount,
            )
        if attrs["utm_medium"]:
            _upsert_pipeline_bucket(
                by_utm_medium,
                record_type="quotation",
                key=attrs["utm_medium"],
                label=attrs["utm_medium"],
                amount=amount,
            )
        if attrs["utm_campaign"]:
            _upsert_pipeline_bucket(
                by_utm_campaign,
                record_type="quotation",
                key=attrs["utm_campaign"],
                label=attrs["utm_campaign"],
                amount=amount,
            )
        if attrs["utm_content"]:
            _upsert_pipeline_bucket(
                by_utm_content,
                record_type="quotation",
                key=attrs["utm_content"],
                label=attrs["utm_content"],
                amount=amount,
            )

    if params.record_type in {
        CRMPipelineRecordType.ALL,
        CRMPipelineRecordType.OPPORTUNITY,
        CRMPipelineRecordType.QUOTATION,
    }:
        for order in orders:
            crm_context_snapshot = getattr(order, "crm_context_snapshot", None)
            utm_source, utm_medium, utm_campaign, utm_content = _extract_utm_snapshot(crm_context_snapshot)
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
