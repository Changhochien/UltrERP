"""Shared CRM pipeline reporting utilities."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from functools import partial

from domains.crm.schemas import (
    CRMPipelineComparisonMetric,
    CRMPipelineReportParams,
    CRMPipelineScope,
    CRMPipelineSegment,
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

_SCOPE_MAP: dict[str, frozenset[str]] = {
    "lead": TERMINAL_LEAD_STATUSES,
    "opportunity": TERMINAL_OPPORTUNITY_STATUSES,
    "quotation": TERMINAL_QUOTATION_STATUSES,
}

_PipelineBucket = dict[str, object]
_BucketDict = dict[tuple[str | None, str], _PipelineBucket]

_LeadAttrs = dict[str, object]
_OpportunityAttrs = dict[str, object]
_QuotationAttrs = dict[str, object]


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


def _extract_snapshot_text(snapshot: dict[str, object] | None, key: str) -> str:
    """Extract a string value from a CRM context snapshot dict."""
    if not isinstance(snapshot, dict):
        return ""
    value = snapshot.get(key)
    return value.strip() if isinstance(value, str) else ""


def _extract_utm_snapshot(snapshot: dict[str, object] | None) -> tuple[str, str, str, str]:
    """Extract all UTM values from a CRM context snapshot."""
    return (
        _extract_snapshot_text(snapshot, "utm_source"),
        _extract_snapshot_text(snapshot, "utm_medium"),
        _extract_snapshot_text(snapshot, "utm_campaign"),
        _extract_snapshot_text(snapshot, "utm_content"),
    )


def _record_scope(record_type: str, status: str) -> CRMPipelineScope:
    """Determine if a record is in OPEN or TERMINAL scope."""
    terminal_statuses = _SCOPE_MAP.get(record_type, frozenset())
    return CRMPipelineScope.TERMINAL if status in terminal_statuses else CRMPipelineScope.OPEN


_lead_scope = partial(_record_scope, "lead")
_opportunity_scope = partial(_record_scope, "opportunity")
_quotation_scope = partial(_record_scope, "quotation")


def _matches_utm_filters(
    *,
    params: CRMPipelineReportParams,
    utm_source: str,
    utm_medium: str,
    utm_campaign: str,
    utm_content: str,
) -> bool:
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


def _precompute_lead_attrs(lead: object) -> _LeadAttrs:
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