"""CRM lead lifecycle services."""

from __future__ import annotations

import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.errors import DuplicateLeadConflictError, ValidationError, VersionConflictError
from common.tenant import DEFAULT_TENANT_ID, set_tenant
from domains.crm._shared import _ensure_status_transition_allowed
from domains.crm._setup import _ensure_territory_supported, get_crm_settings
from domains.crm.models import Lead
from domains.crm.schemas import (
    CRMDuplicatePolicy,
    LeadConversionRequest,
    LeadConversionState,
    LeadCreate,
    LeadCustomerConversionResult,
    LeadListParams,
    LeadOpportunityHandoff,
    LeadQualificationStatus,
    LeadStatus,
    LeadUpdate,
)
from domains.customers.models import Customer
from domains.customers.schemas import CustomerCreate
from domains.customers.service import create_customer, lookup_customer_by_ban


@dataclass(frozen=True, slots=True)
class _LeadDuplicateLookup:
    company_name: str
    email_id: str
    phone: str
    mobile_no: str


ALLOWED_LEAD_TRANSITIONS: dict[LeadStatus, frozenset[LeadStatus]] = {
    LeadStatus.LEAD: frozenset(
        {LeadStatus.OPEN, LeadStatus.INTERESTED, LeadStatus.DO_NOT_CONTACT}
    ),
    LeadStatus.OPEN: frozenset(
        {LeadStatus.REPLIED, LeadStatus.INTERESTED, LeadStatus.DO_NOT_CONTACT}
    ),
    LeadStatus.REPLIED: frozenset(
        {
            LeadStatus.QUOTATION,
            LeadStatus.INTERESTED,
            LeadStatus.DO_NOT_CONTACT,
            LeadStatus.LOST_QUOTATION,
        }
    ),
    LeadStatus.OPPORTUNITY: frozenset(
        {
            LeadStatus.QUOTATION,
            LeadStatus.LOST_QUOTATION,
            LeadStatus.DO_NOT_CONTACT,
        }
    ),
    LeadStatus.QUOTATION: frozenset(
        {LeadStatus.LOST_QUOTATION, LeadStatus.DO_NOT_CONTACT}
    ),
    LeadStatus.LOST_QUOTATION: frozenset(),
    LeadStatus.INTERESTED: frozenset(),
    LeadStatus.CONVERTED: frozenset(),
    LeadStatus.DO_NOT_CONTACT: frozenset(),
}


# Conversion target constants for consistency across the codebase
CONVERSION_TARGET_CUSTOMER = "customer"
CONVERSION_TARGET_OPPORTUNITY = "opportunity"
CONVERSION_TARGET_QUOTATION = "quotation"
CONVERSION_TARGET_ORDER = (CONVERSION_TARGET_CUSTOMER, CONVERSION_TARGET_OPPORTUNITY, CONVERSION_TARGET_QUOTATION)


def _canonical_conversion_path(targets: set[str]) -> str:
    return "+".join(target for target in CONVERSION_TARGET_ORDER if target in targets)


def _current_lead_success_targets(lead: Lead) -> set[str]:
    targets: set[str] = set()
    if lead.converted_customer_id is not None:
        targets.add(CONVERSION_TARGET_CUSTOMER)
    if getattr(lead, "converted_opportunity_id", None) is not None:
        targets.add(CONVERSION_TARGET_OPPORTUNITY)
    if getattr(lead, "converted_quotation_id", None) is not None:
        targets.add(CONVERSION_TARGET_QUOTATION)
    return targets


def _resolve_conversion_state(
    requested_targets: set[str],
    successful_targets: set[str],
) -> LeadConversionState:
    if not successful_targets:
        return LeadConversionState.NOT_CONVERTED
    if not requested_targets or successful_targets == requested_targets:
        return LeadConversionState.CONVERTED
    return LeadConversionState.PARTIALLY_CONVERTED


def _resolve_lead_status_after_conversion(successful_targets: set[str]) -> LeadStatus:
    if CONVERSION_TARGET_QUOTATION in successful_targets:
        return LeadStatus.QUOTATION
    if CONVERSION_TARGET_OPPORTUNITY in successful_targets:
        return LeadStatus.OPPORTUNITY
    if CONVERSION_TARGET_CUSTOMER in successful_targets:
        return LeadStatus.CONVERTED
    return LeadStatus.OPEN


def _selected_conversion_targets(data: LeadConversionRequest) -> set[str]:
    targets: set[str] = set()
    if data.reuse_customer_id is not None or data.customer is not None:
        targets.add(CONVERSION_TARGET_CUSTOMER)
    if data.opportunity is not None:
        targets.add(CONVERSION_TARGET_OPPORTUNITY)
    if data.quotation is not None:
        targets.add(CONVERSION_TARGET_QUOTATION)
    return targets


def _normalize_company_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.strip().lower())


def _normalize_email(value: str) -> str:
    return value.strip().lower()


def _normalize_phone(value: str) -> str:
    return re.sub(r"\D", "", value)


def _apply_trimmed_update_field(
    lead: Lead,
    data: LeadUpdate,
    fields: set[str],
    field_name: str,
    *,
    normalized_field: str | None = None,
    normalizer: Callable[[str], str] | None = None,
) -> None:
    if field_name not in fields:
        return
    value = getattr(data, field_name)
    if value is None:
        return
    trimmed = value.strip()
    setattr(lead, field_name, trimmed)
    if normalized_field is not None and normalizer is not None:
        setattr(lead, normalized_field, normalizer(trimmed))


def _ensure_transition_allowed(current_status: LeadStatus, target_status: LeadStatus) -> None:
    _ensure_status_transition_allowed(
        current_status,
        target_status,
        ALLOWED_LEAD_TRANSITIONS,
        lambda current, target: ValidationError(
            [
                {
                    "field": "status",
                    "message": (
                        f"Cannot transition from '{current.value}' "
                        f"to '{target.value}'."
                    ),
                }
            ]
        ),
    )


def _ensure_opportunity_handoff_allowed(current_status: LeadStatus) -> None:
    if current_status != LeadStatus.REPLIED:
        raise ValidationError(
            [
                {
                    "field": "status",
                    "message": "Lead must be in replied status before opportunity handoff.",
                }
            ]
        )


def _build_duplicate_lookup_from_update(
    data: LeadUpdate,
    lead: Lead,
    fields: set[str],
) -> _LeadDuplicateLookup:
    def merged(field_name: str) -> str:
        value = getattr(data, field_name)
        if field_name in fields and value is not None:
            return value
        return getattr(lead, field_name)

    return _LeadDuplicateLookup(
        company_name=merged("company_name"),
        email_id=merged("email_id"),
        phone=merged("phone"),
        mobile_no=merged("mobile_no"),
    )


def _first_matched_field(
    data: LeadCreate | _LeadDuplicateLookup,
    candidate: Lead | Customer,
) -> str:
    normalized_company = _normalize_company_name(data.company_name)
    candidate_company_normalized = getattr(candidate, "normalized_company_name", None)
    if candidate_company_normalized is None:
        candidate_company_normalized = _normalize_company_name(
            getattr(candidate, "company_name", "")
        )
    if normalized_company and candidate_company_normalized == normalized_company:
        return "company_name"

    normalized_email = _normalize_email(data.email_id)
    candidate_email_normalized = getattr(candidate, "normalized_email_id", None)
    if candidate_email_normalized is None:
        candidate_email_normalized = _normalize_email(
            getattr(candidate, "contact_email", "")
        )
    if normalized_email and candidate_email_normalized == normalized_email:
        return "email_id"

    return "phone"


def _candidate_label(candidate: Lead | Customer) -> str:
    if isinstance(candidate, Lead):
        return candidate.lead_name
    return candidate.company_name


async def _find_duplicate_candidates(
    session: AsyncSession,
    data: LeadCreate | _LeadDuplicateLookup,
    tenant_id: uuid.UUID,
    *,
    exclude_lead_id: uuid.UUID | None = None,
) -> list[dict[str, str]]:
    normalized_company = _normalize_company_name(data.company_name)
    normalized_email = _normalize_email(data.email_id)
    normalized_phone_values = {
        value
        for value in {
            _normalize_phone(data.phone),
            _normalize_phone(data.mobile_no),
        }
        if value
    }

    lead_filters = []
    customer_filters = []

    if normalized_company:
        lead_filters.append(Lead.normalized_company_name == normalized_company)
        customer_filters.append(
            func.regexp_replace(
                func.lower(Customer.company_name),
                r"[^a-z0-9]",
                "",
                "g",
            )
            == normalized_company
        )
    if normalized_email:
        lead_filters.append(Lead.normalized_email_id == normalized_email)
        customer_filters.append(func.lower(Customer.contact_email) == normalized_email)
    if normalized_phone_values:
        lead_filters.append(Lead.normalized_phone.in_(normalized_phone_values))
        lead_filters.append(Lead.normalized_mobile_no.in_(normalized_phone_values))
        customer_filters.append(
            func.regexp_replace(
                Customer.contact_phone,
                r"\D",
                "",
                "g",
            ).in_(normalized_phone_values)
        )

    if not lead_filters and not customer_filters:
        return []

    async with session.begin():
        await set_tenant(session, tenant_id)

        lead_stmt = select(Lead).where(Lead.tenant_id == tenant_id)
        if exclude_lead_id is not None:
            lead_stmt = lead_stmt.where(Lead.id != exclude_lead_id)
        if lead_filters:
            lead_result = await session.execute(lead_stmt.where(or_(*lead_filters)))
            lead_matches = list(lead_result.scalars().all())
        else:
            lead_matches = []

        if customer_filters:
            customer_stmt = select(Customer).where(
                Customer.tenant_id == tenant_id,
                or_(*customer_filters),
            )
            customer_result = await session.execute(customer_stmt)
            customer_matches = list(customer_result.scalars().all())
        else:
            customer_matches = []

    candidates: list[dict[str, str]] = []
    for lead in lead_matches:
        candidates.append(
            {
                "kind": "lead",
                "id": str(lead.id),
                "label": _candidate_label(lead),
                "matched_on": _first_matched_field(data, lead),
            }
        )
    for customer in customer_matches:
        candidates.append(
            {
                "kind": "customer",
                "id": str(customer.id),
                "label": _candidate_label(customer),
                "matched_on": _first_matched_field(data, customer),
            }
        )
    return candidates


async def create_lead(
    session: AsyncSession,
    data: LeadCreate,
    tenant_id: uuid.UUID | None = None,
) -> Lead:
    tid = tenant_id or DEFAULT_TENANT_ID
    territory = await _ensure_territory_supported(session, data.territory, tid)
    candidates = await _find_duplicate_candidates(session, data, tid)
    if candidates:
        settings = await get_crm_settings(session, tenant_id=tid)
        if settings.lead_duplicate_policy == CRMDuplicatePolicy.BLOCK:
            raise DuplicateLeadConflictError(candidates)

    lead = Lead(
        tenant_id=tid,
        lead_name=data.lead_name.strip(),
        company_name=data.company_name.strip(),
        normalized_company_name=_normalize_company_name(data.company_name),
        email_id=data.email_id.strip(),
        normalized_email_id=_normalize_email(data.email_id),
        phone=data.phone.strip(),
        mobile_no=data.mobile_no.strip(),
        normalized_phone=_normalize_phone(data.phone),
        normalized_mobile_no=_normalize_phone(data.mobile_no),
        territory=territory,
        lead_owner=data.lead_owner.strip(),
        source=data.source.strip(),
        status=LeadStatus.LEAD,
        qualification_status=data.qualification_status,
        qualified_by=data.qualified_by.strip(),
        annual_revenue=data.annual_revenue,
        no_of_employees=data.no_of_employees,
        industry=data.industry.strip(),
        market_segment=data.market_segment.strip(),
        utm_source=data.utm_source.strip(),
        utm_medium=data.utm_medium.strip(),
        utm_campaign=data.utm_campaign.strip(),
        utm_content=data.utm_content.strip(),
        notes=data.notes.strip(),
    )

    async with session.begin():
        await set_tenant(session, tid)
        session.add(lead)

    await session.refresh(lead)
    return lead


async def list_leads(
    session: AsyncSession,
    params: LeadListParams,
    tenant_id: uuid.UUID | None = None,
) -> tuple[list[Lead], int]:
    tid = tenant_id or DEFAULT_TENANT_ID
    base = select(Lead).where(Lead.tenant_id == tid)

    if params.q:
        escaped_q = params.q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        like_pattern = f"%{escaped_q}%"
        normalized_q = _normalize_phone(params.q)
        predicates = [
            Lead.lead_name.ilike(like_pattern, escape="\\"),
            Lead.company_name.ilike(like_pattern, escape="\\"),
            Lead.email_id.ilike(like_pattern, escape="\\"),
        ]
        if normalized_q:
            predicates.extend(
                [
                    Lead.normalized_phone.contains(normalized_q),
                    Lead.normalized_mobile_no.contains(normalized_q),
                ]
            )
        base = base.where(or_(*predicates))

    if params.status:
        base = base.where(Lead.status == params.status)

    count_stmt = select(func.count()).select_from(base.subquery())
    offset = (params.page - 1) * params.page_size
    items_stmt = (
        base.order_by(Lead.updated_at.desc(), Lead.lead_name.asc(), Lead.id.asc())
        .offset(offset)
        .limit(params.page_size)
    )

    async with session.begin():
        await set_tenant(session, tid)
        total_result = await session.execute(count_stmt)
        total_count = total_result.scalar() or 0
        result = await session.execute(items_stmt)
        items = list(result.scalars().all())

    return items, total_count


async def get_lead(
    session: AsyncSession,
    lead_id: uuid.UUID,
    tenant_id: uuid.UUID | None = None,
) -> Lead | None:
    tid = tenant_id or DEFAULT_TENANT_ID
    async with session.begin():
        await set_tenant(session, tid)
        result = await session.execute(
            select(Lead).where(Lead.id == lead_id, Lead.tenant_id == tid)
        )
        return result.scalar_one_or_none()


async def update_lead(
    session: AsyncSession,
    lead_id: uuid.UUID,
    data: LeadUpdate,
    tenant_id: uuid.UUID | None = None,
) -> Lead | None:
    tid = tenant_id or DEFAULT_TENANT_ID
    lead = await get_lead(session, lead_id, tenant_id=tid)
    if lead is None:
        return None
    if lead.version != data.version:
        raise VersionConflictError(expected=data.version, actual=lead.version)

    fields = data.model_fields_set - {"version"}
    duplicate_lookup = _build_duplicate_lookup_from_update(data, lead, fields)

    candidates = await _find_duplicate_candidates(
        session,
        duplicate_lookup,
        tid,
        exclude_lead_id=lead_id,
    )
    if candidates:
        raise DuplicateLeadConflictError(candidates)

    async with session.begin():
        await set_tenant(session, tid)
        _apply_trimmed_update_field(lead, data, fields, "lead_name")
        _apply_trimmed_update_field(
            lead,
            data,
            fields,
            "company_name",
            normalized_field="normalized_company_name",
            normalizer=_normalize_company_name,
        )
        _apply_trimmed_update_field(
            lead,
            data,
            fields,
            "email_id",
            normalized_field="normalized_email_id",
            normalizer=_normalize_email,
        )
        _apply_trimmed_update_field(
            lead,
            data,
            fields,
            "phone",
            normalized_field="normalized_phone",
            normalizer=_normalize_phone,
        )
        _apply_trimmed_update_field(
            lead,
            data,
            fields,
            "mobile_no",
            normalized_field="normalized_mobile_no",
            normalizer=_normalize_phone,
        )
        _apply_trimmed_update_field(lead, data, fields, "territory")
        _apply_trimmed_update_field(lead, data, fields, "lead_owner")
        _apply_trimmed_update_field(lead, data, fields, "source")
        if "qualification_status" in fields and data.qualification_status is not None:
            lead.qualification_status = data.qualification_status
        _apply_trimmed_update_field(lead, data, fields, "qualified_by")
        if "annual_revenue" in fields:
            lead.annual_revenue = data.annual_revenue
        if "no_of_employees" in fields:
            lead.no_of_employees = data.no_of_employees
        _apply_trimmed_update_field(lead, data, fields, "industry")
        _apply_trimmed_update_field(lead, data, fields, "market_segment")
        _apply_trimmed_update_field(lead, data, fields, "utm_source")
        _apply_trimmed_update_field(lead, data, fields, "utm_medium")
        _apply_trimmed_update_field(lead, data, fields, "utm_campaign")
        _apply_trimmed_update_field(lead, data, fields, "utm_content")
        _apply_trimmed_update_field(lead, data, fields, "notes")

        lead.version += 1
        lead.updated_at = datetime.now(tz=UTC)
    return lead


async def transition_lead_status(
    session: AsyncSession,
    lead_id: uuid.UUID,
    target_status: LeadStatus,
    tenant_id: uuid.UUID | None = None,
) -> Lead | None:
    tid = tenant_id or DEFAULT_TENANT_ID
    lead = await get_lead(session, lead_id, tenant_id=tid)
    if lead is None:
        return None

    _ensure_transition_allowed(LeadStatus(lead.status), target_status)
    async with session.begin():
        await set_tenant(session, tid)
        lead.status = target_status
        lead.updated_at = datetime.now(tz=UTC)
    return lead


async def handoff_lead_to_opportunity(
    session: AsyncSession,
    lead_id: uuid.UUID,
    tenant_id: uuid.UUID | None = None,
) -> LeadOpportunityHandoff:
    tid = tenant_id or DEFAULT_TENANT_ID
    lead = await get_lead(session, lead_id, tenant_id=tid)
    if lead is None:
        raise ValidationError([{"field": "lead_id", "message": "Lead not found."}])
    if (
        LeadQualificationStatus(lead.qualification_status)
        != LeadQualificationStatus.QUALIFIED
    ):
        raise ValidationError(
            [
                {
                    "field": "qualification_status",
                    "message": "Lead must be qualified before opportunity handoff.",
                }
            ]
        )

    _ensure_opportunity_handoff_allowed(LeadStatus(lead.status))
    async with session.begin():
        await set_tenant(session, tid)
        lead.status = LeadStatus.OPPORTUNITY
        lead.updated_at = datetime.now(tz=UTC)
    return LeadOpportunityHandoff(
        lead_id=lead.id,
        lead_name=lead.lead_name,
        company_name=lead.company_name,
        email_id=lead.email_id,
        phone=lead.phone,
        mobile_no=lead.mobile_no,
        territory=lead.territory,
        lead_owner=lead.lead_owner,
        source=lead.source,
        qualification_status=LeadQualificationStatus(lead.qualification_status),
        utm_source=lead.utm_source,
        utm_medium=lead.utm_medium,
        utm_campaign=lead.utm_campaign,
        utm_content=lead.utm_content,
    )


async def _record_lead_conversion(
    session: AsyncSession,
    lead_id: uuid.UUID,
    *,
    tenant_id: uuid.UUID,
    requested_targets: set[str] | None = None,
    converted_by: str | None = None,
    customer_id: uuid.UUID | None = None,
    opportunity_id: uuid.UUID | None = None,
    quotation_id: uuid.UUID | None = None,
    status: LeadStatus | None = None,
) -> Lead | None:
    """Record lead conversion to customer, opportunity, and/or quotation."""
    lead = await get_lead(session, lead_id, tenant_id=tenant_id)
    if lead is None:
        return None

    now = datetime.now(tz=UTC)
    async with session.begin():
        await set_tenant(session, tenant_id)
        if customer_id is not None:
            lead.converted_customer_id = customer_id
        if opportunity_id is not None:
            lead.converted_opportunity_id = opportunity_id
        if quotation_id is not None:
            lead.converted_quotation_id = quotation_id
        if status is not None:
            lead.status = status

        successful_targets = _current_lead_success_targets(lead)
        effective_requested = requested_targets or successful_targets
        lead.conversion_path = _canonical_conversion_path(effective_requested)
        lead.conversion_state = _resolve_conversion_state(
            effective_requested,
            successful_targets,
        ).value
        if successful_targets and lead.converted_at is None:
            lead.converted_at = now
        if converted_by is not None:
            lead.converted_by = converted_by
        lead.updated_at = now
    return lead


async def convert_lead_to_customer(
    session: AsyncSession,
    lead_id: uuid.UUID,
    customer_data: CustomerCreate,
    tenant_id: uuid.UUID | None = None,
    converted_by: str | None = None,
) -> LeadCustomerConversionResult:
    """Convert a qualified lead directly to a customer."""
    tid = tenant_id or DEFAULT_TENANT_ID
    lead = await get_lead(session, lead_id, tenant_id=tid)
    if lead is None:
        raise ValidationError([{"field": "lead_id", "message": "Lead not found."}])
    if (
        LeadQualificationStatus(lead.qualification_status)
        != LeadQualificationStatus.QUALIFIED
    ):
        raise ValidationError(
            [{"field": "qualification_status", "message": "Lead must be qualified before customer conversion."}]
        )

    customer = await lookup_customer_by_ban(session, customer_data.business_number, tenant_id=tid)
    if customer is None:
        customer = await create_customer(session, customer_data, tenant_id=tid)

    lead = await _record_lead_conversion(
        session,
        lead.id,
        tenant_id=tid,
        requested_targets={"customer"},
        converted_by=converted_by,
        customer_id=customer.id,
        status=LeadStatus.CONVERTED,
    )
    return LeadCustomerConversionResult(
        lead_id=lead.id if lead is not None else lead_id,
        customer_id=customer.id,
        status=lead.status if lead is not None else LeadStatus.CONVERTED,
    )
