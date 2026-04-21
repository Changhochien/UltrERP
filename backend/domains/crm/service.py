"""CRM service layer."""

from __future__ import annotations

from decimal import Decimal
import re
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.errors import DuplicateLeadConflictError, ValidationError, VersionConflictError
from common.tenant import DEFAULT_TENANT_ID, set_tenant
from domains.crm.models import Lead, Opportunity
from domains.crm.schemas import (
    LeadCreate,
    LeadCustomerConversionResult,
    LeadListParams,
    LeadOpportunityHandoff,
    LeadQualificationStatus,
    LeadStatus,
    LeadUpdate,
    OpportunityCreate,
    OpportunityItem,
    OpportunityItemInput,
    OpportunityListParams,
    OpportunityPartyKind,
    OpportunityQuotationHandoff,
    OpportunityResponse,
    OpportunityStatus,
    OpportunityTransition,
    OpportunityUpdate,
)
from domains.customers.models import Customer
from domains.customers.schemas import CustomerCreate
from domains.customers.service import create_customer

ALLOWED_LEAD_TRANSITIONS: dict[LeadStatus, frozenset[LeadStatus]] = {
    LeadStatus.LEAD: frozenset({LeadStatus.OPEN, LeadStatus.INTERESTED, LeadStatus.DO_NOT_CONTACT}),
    LeadStatus.OPEN: frozenset({LeadStatus.REPLIED, LeadStatus.INTERESTED, LeadStatus.DO_NOT_CONTACT}),
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
    LeadStatus.QUOTATION: frozenset({LeadStatus.LOST_QUOTATION, LeadStatus.DO_NOT_CONTACT}),
    LeadStatus.LOST_QUOTATION: frozenset(),
    LeadStatus.INTERESTED: frozenset(),
    LeadStatus.CONVERTED: frozenset(),
    LeadStatus.DO_NOT_CONTACT: frozenset(),
}

ALLOWED_OPPORTUNITY_TRANSITIONS: dict[OpportunityStatus, frozenset[OpportunityStatus]] = {
    OpportunityStatus.OPEN: frozenset(
        {
            OpportunityStatus.REPLIED,
            OpportunityStatus.QUOTATION,
            OpportunityStatus.CLOSED,
            OpportunityStatus.LOST,
        }
    ),
    OpportunityStatus.REPLIED: frozenset(
        {
            OpportunityStatus.QUOTATION,
            OpportunityStatus.CLOSED,
            OpportunityStatus.LOST,
        }
    ),
    OpportunityStatus.QUOTATION: frozenset(
        {
            OpportunityStatus.CONVERTED,
            OpportunityStatus.CLOSED,
            OpportunityStatus.LOST,
        }
    ),
    OpportunityStatus.CONVERTED: frozenset(),
    OpportunityStatus.CLOSED: frozenset(),
    OpportunityStatus.LOST: frozenset(),
}


def _normalize_company_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.strip().lower())


def _normalize_email(value: str) -> str:
    return value.strip().lower()


def _normalize_phone(value: str) -> str:
    return re.sub(r"\D", "", value)


def _ensure_transition_allowed(current_status: LeadStatus, target_status: LeadStatus) -> None:
    if target_status not in ALLOWED_LEAD_TRANSITIONS.get(current_status, frozenset()):
        raise ValidationError(
            [
                {
                    "field": "status",
                    "message": f"Cannot transition from '{current_status.value}' to '{target_status.value}'.",
                }
            ]
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


def _ensure_opportunity_transition_allowed(
    current_status: OpportunityStatus,
    target_status: OpportunityStatus,
) -> None:
    if target_status not in ALLOWED_OPPORTUNITY_TRANSITIONS.get(current_status, frozenset()):
        raise ValidationError(
            [
                {
                    "field": "status",
                    "message": f"Cannot transition from '{current_status.value}' to '{target_status.value}'.",
                }
            ]
        )


def _ensure_lost_context(data: OpportunityTransition) -> None:
    if data.status == OpportunityStatus.LOST and not data.lost_reason.strip():
        raise ValidationError(
            [
                {
                    "field": "lost_reason",
                    "message": "Lost opportunities require a lost reason.",
                }
            ]
        )


def _ensure_quotation_handoff_allowed(current_status: OpportunityStatus) -> None:
    if current_status not in {
        OpportunityStatus.OPEN,
        OpportunityStatus.REPLIED,
        OpportunityStatus.QUOTATION,
    }:
        raise ValidationError(
            [
                {
                    "field": "status",
                    "message": "Only open or active opportunities can be prepared for quotation handoff.",
                }
            ]
        )


def _first_matched_field(data: LeadCreate, candidate: object) -> str:
    normalized_company = _normalize_company_name(data.company_name)
    candidate_company = getattr(
        candidate,
        "normalized_company_name",
        _normalize_company_name(getattr(candidate, "company_name", "")),
    )
    if normalized_company and candidate_company == normalized_company:
        return "company_name"

    normalized_email = _normalize_email(data.email_id)
    candidate_email = getattr(
        candidate,
        "normalized_email_id",
        _normalize_email(getattr(candidate, "contact_email", "")),
    )
    if normalized_email and candidate_email == normalized_email:
        return "email_id"

    return "phone"


def _candidate_label(candidate: object) -> str:
    return getattr(candidate, "lead_name", getattr(candidate, "company_name", ""))


def _trim(value: str | None) -> str:
    return value.strip() if value else ""


def _serialize_opportunity_items(items: list[OpportunityItemInput]) -> list[dict[str, object]]:
    serialized: list[dict[str, object]] = []
    for line_no, item in enumerate(items, start=1):
        quantity = item.quantity.quantize(Decimal("0.01"))
        unit_price = item.unit_price.quantize(Decimal("0.01"))
        amount = (item.amount or (quantity * unit_price)).quantize(Decimal("0.01"))
        serialized.append(
            {
                "line_no": line_no,
                "item_name": item.item_name.strip(),
                "item_code": item.item_code.strip(),
                "description": item.description.strip(),
                "quantity": f"{quantity:.2f}",
                "unit_price": f"{unit_price:.2f}",
                "amount": f"{amount:.2f}",
            }
        )
    return serialized


def _deserialize_opportunity_items(items: list[dict[str, object]]) -> list[OpportunityItemInput]:
    return [
        OpportunityItemInput(
            item_name=str(item.get("item_name", "")),
            item_code=str(item.get("item_code", "")),
            description=str(item.get("description", "")),
            quantity=Decimal(str(item.get("quantity", "1.00"))),
            unit_price=Decimal(str(item.get("unit_price", "0.00"))),
            amount=Decimal(str(item.get("amount", "0.00"))),
        )
        for item in items
    ]


def _resolve_total_amount(
    explicit_amount: Decimal | None,
    serialized_items: list[dict[str, object]],
) -> Decimal | None:
    if explicit_amount is not None:
        return explicit_amount.quantize(Decimal("0.01"))
    if not serialized_items:
        return None
    return sum((Decimal(str(item["amount"])) for item in serialized_items), start=Decimal("0.00")).quantize(
        Decimal("0.01")
    )


async def _resolve_party_context(
    session: AsyncSession,
    opportunity_from: OpportunityPartyKind,
    party_name: str,
    tenant_id: uuid.UUID,
) -> tuple[str, str, dict[str, str]]:
    normalized_party_name = party_name.strip()
    if opportunity_from == OpportunityPartyKind.PROSPECT:
        return normalized_party_name, normalized_party_name, {}

    try:
        party_id = uuid.UUID(normalized_party_name)
    except ValueError as exc:
        raise ValidationError(
            [
                {
                    "field": "party_name",
                    "message": f"{opportunity_from.value.capitalize()} party links must use a valid record id.",
                }
            ]
        ) from exc

    async with session.begin():
        await set_tenant(session, tenant_id)
        if opportunity_from == OpportunityPartyKind.LEAD:
            result = await session.execute(select(Lead).where(Lead.id == party_id, Lead.tenant_id == tenant_id))
            lead = result.scalar_one_or_none()
            if lead is None:
                raise ValidationError([{"field": "party_name", "message": "Lead party not found."}])
            return (
                str(lead.id),
                lead.company_name or lead.lead_name,
                {
                    "contact_person": lead.lead_name,
                    "contact_email": lead.email_id,
                    "contact_mobile": lead.mobile_no or lead.phone,
                    "territory": lead.territory,
                    "utm_source": lead.utm_source,
                    "utm_medium": lead.utm_medium,
                    "utm_campaign": lead.utm_campaign,
                    "utm_content": lead.utm_content,
                },
            )

        result = await session.execute(select(Customer).where(Customer.id == party_id, Customer.tenant_id == tenant_id))
        customer = result.scalar_one_or_none()
        if customer is None:
            raise ValidationError([{"field": "party_name", "message": "Customer party not found."}])
        return (
            str(customer.id),
            customer.company_name,
            {
                "contact_person": customer.contact_name,
                "contact_email": customer.contact_email,
                "contact_mobile": customer.contact_phone,
            },
        )


def _build_opportunity_response(opportunity: Opportunity) -> OpportunityResponse:
    return OpportunityResponse.model_validate(opportunity)


async def _find_duplicate_candidates(
    session: AsyncSession,
    data: LeadCreate,
    tenant_id: uuid.UUID,
    *,
    exclude_lead_id: uuid.UUID | None = None,
) -> list[dict[str, str]]:
    normalized_company = _normalize_company_name(data.company_name)
    normalized_email = _normalize_email(data.email_id)
    normalized_phone_values = {
        value for value in {_normalize_phone(data.phone), _normalize_phone(data.mobile_no)} if value
    }

    lead_filters = []
    customer_filters = []

    if normalized_company:
        lead_filters.append(Lead.normalized_company_name == normalized_company)
        customer_filters.append(
            func.regexp_replace(func.lower(Customer.company_name), r"[^a-z0-9]", "", "g")
            == normalized_company
        )
    if normalized_email:
        lead_filters.append(Lead.normalized_email_id == normalized_email)
        customer_filters.append(func.lower(Customer.contact_email) == normalized_email)
    if normalized_phone_values:
        lead_filters.append(Lead.normalized_phone.in_(normalized_phone_values))
        lead_filters.append(Lead.normalized_mobile_no.in_(normalized_phone_values))
        customer_filters.append(
            func.regexp_replace(Customer.contact_phone, r"\D", "", "g").in_(normalized_phone_values)
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
            customer_stmt = select(Customer).where(Customer.tenant_id == tenant_id, or_(*customer_filters))
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
    candidates = await _find_duplicate_candidates(session, data, tid)
    if candidates:
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
        territory=data.territory.strip(),
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
        result = await session.execute(select(Lead).where(Lead.id == lead_id, Lead.tenant_id == tid))
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
    merged = LeadCreate(
        lead_name=data.lead_name if "lead_name" in fields and data.lead_name is not None else lead.lead_name,
        company_name=data.company_name if "company_name" in fields and data.company_name is not None else lead.company_name,
        email_id=data.email_id if "email_id" in fields and data.email_id is not None else lead.email_id,
        phone=data.phone if "phone" in fields and data.phone is not None else lead.phone,
        mobile_no=data.mobile_no if "mobile_no" in fields and data.mobile_no is not None else lead.mobile_no,
        territory=data.territory if "territory" in fields and data.territory is not None else lead.territory,
        lead_owner=data.lead_owner if "lead_owner" in fields and data.lead_owner is not None else lead.lead_owner,
        source=data.source if "source" in fields and data.source is not None else lead.source,
        qualification_status=(
            data.qualification_status
            if "qualification_status" in fields and data.qualification_status is not None
            else LeadQualificationStatus(lead.qualification_status)
        ),
        qualified_by=data.qualified_by if "qualified_by" in fields and data.qualified_by is not None else lead.qualified_by,
        annual_revenue=data.annual_revenue if "annual_revenue" in fields else lead.annual_revenue,
        no_of_employees=data.no_of_employees if "no_of_employees" in fields else lead.no_of_employees,
        industry=data.industry if "industry" in fields and data.industry is not None else lead.industry,
        market_segment=(
            data.market_segment if "market_segment" in fields and data.market_segment is not None else lead.market_segment
        ),
        utm_source=data.utm_source if "utm_source" in fields and data.utm_source is not None else lead.utm_source,
        utm_medium=data.utm_medium if "utm_medium" in fields and data.utm_medium is not None else lead.utm_medium,
        utm_campaign=(
            data.utm_campaign if "utm_campaign" in fields and data.utm_campaign is not None else lead.utm_campaign
        ),
        utm_content=(
            data.utm_content if "utm_content" in fields and data.utm_content is not None else lead.utm_content
        ),
        notes=data.notes if "notes" in fields and data.notes is not None else lead.notes,
    )

    candidates = await _find_duplicate_candidates(session, merged, tid, exclude_lead_id=lead_id)
    if candidates:
        raise DuplicateLeadConflictError(candidates)

    async with session.begin():
        await set_tenant(session, tid)
        if "lead_name" in fields and data.lead_name is not None:
            lead.lead_name = data.lead_name.strip()
        if "company_name" in fields and data.company_name is not None:
            lead.company_name = data.company_name.strip()
            lead.normalized_company_name = _normalize_company_name(data.company_name)
        if "email_id" in fields and data.email_id is not None:
            lead.email_id = data.email_id.strip()
            lead.normalized_email_id = _normalize_email(data.email_id)
        if "phone" in fields and data.phone is not None:
            lead.phone = data.phone.strip()
            lead.normalized_phone = _normalize_phone(data.phone)
        if "mobile_no" in fields and data.mobile_no is not None:
            lead.mobile_no = data.mobile_no.strip()
            lead.normalized_mobile_no = _normalize_phone(data.mobile_no)
        if "territory" in fields and data.territory is not None:
            lead.territory = data.territory.strip()
        if "lead_owner" in fields and data.lead_owner is not None:
            lead.lead_owner = data.lead_owner.strip()
        if "source" in fields and data.source is not None:
            lead.source = data.source.strip()
        if "qualification_status" in fields and data.qualification_status is not None:
            lead.qualification_status = data.qualification_status
        if "qualified_by" in fields and data.qualified_by is not None:
            lead.qualified_by = data.qualified_by.strip()
        if "annual_revenue" in fields:
            lead.annual_revenue = data.annual_revenue
        if "no_of_employees" in fields:
            lead.no_of_employees = data.no_of_employees
        if "industry" in fields and data.industry is not None:
            lead.industry = data.industry.strip()
        if "market_segment" in fields and data.market_segment is not None:
            lead.market_segment = data.market_segment.strip()
        if "utm_source" in fields and data.utm_source is not None:
            lead.utm_source = data.utm_source.strip()
        if "utm_medium" in fields and data.utm_medium is not None:
            lead.utm_medium = data.utm_medium.strip()
        if "utm_campaign" in fields and data.utm_campaign is not None:
            lead.utm_campaign = data.utm_campaign.strip()
        if "utm_content" in fields and data.utm_content is not None:
            lead.utm_content = data.utm_content.strip()
        if "notes" in fields and data.notes is not None:
            lead.notes = data.notes.strip()

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
    if LeadQualificationStatus(lead.qualification_status) != LeadQualificationStatus.QUALIFIED:
        raise ValidationError(
            [{"field": "qualification_status", "message": "Lead must be qualified before opportunity handoff."}]
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


async def convert_lead_to_customer(
    session: AsyncSession,
    lead_id: uuid.UUID,
    customer_data: CustomerCreate,
    tenant_id: uuid.UUID | None = None,
) -> LeadCustomerConversionResult:
    tid = tenant_id or DEFAULT_TENANT_ID
    lead = await get_lead(session, lead_id, tenant_id=tid)
    if lead is None:
        raise ValidationError([{"field": "lead_id", "message": "Lead not found."}])
    if LeadQualificationStatus(lead.qualification_status) != LeadQualificationStatus.QUALIFIED:
        raise ValidationError(
            [{"field": "qualification_status", "message": "Lead must be qualified before customer conversion."}]
        )

    customer = await create_customer(session, customer_data, tenant_id=tid)
    async with session.begin():
        await set_tenant(session, tid)
        lead.status = LeadStatus.CONVERTED
        lead.converted_customer_id = customer.id
        lead.converted_at = datetime.now(tz=UTC)
        lead.updated_at = datetime.now(tz=UTC)
    return LeadCustomerConversionResult(
        lead_id=lead.id,
        customer_id=customer.id,
        status=LeadStatus.CONVERTED,
    )


async def create_opportunity(
    session: AsyncSession,
    data: OpportunityCreate,
    tenant_id: uuid.UUID | None = None,
) -> Opportunity:
    tid = tenant_id or DEFAULT_TENANT_ID
    serialized_items = _serialize_opportunity_items(data.items)
    opportunity_amount = _resolve_total_amount(data.opportunity_amount, serialized_items)
    party_name, party_label, party_defaults = await _resolve_party_context(
        session,
        data.opportunity_from,
        data.party_name,
        tid,
    )

    opportunity = Opportunity(
        tenant_id=tid,
        opportunity_title=data.opportunity_title.strip(),
        opportunity_from=data.opportunity_from,
        party_name=party_name,
        party_label=party_label,
        status=OpportunityStatus.OPEN,
        sales_stage=data.sales_stage.strip(),
        probability=data.probability,
        expected_closing=data.expected_closing,
        currency=data.currency.strip().upper(),
        opportunity_amount=opportunity_amount,
        base_opportunity_amount=opportunity_amount,
        opportunity_owner=_trim(data.opportunity_owner),
        territory=_trim(data.territory) or party_defaults.get("territory", ""),
        customer_group=_trim(data.customer_group),
        contact_person=_trim(data.contact_person) or party_defaults.get("contact_person", ""),
        contact_email=_trim(data.contact_email) or party_defaults.get("contact_email", ""),
        contact_mobile=_trim(data.contact_mobile) or party_defaults.get("contact_mobile", ""),
        job_title=_trim(data.job_title),
        utm_source=_trim(data.utm_source) or party_defaults.get("utm_source", ""),
        utm_medium=_trim(data.utm_medium) or party_defaults.get("utm_medium", ""),
        utm_campaign=_trim(data.utm_campaign) or party_defaults.get("utm_campaign", ""),
        utm_content=_trim(data.utm_content) or party_defaults.get("utm_content", ""),
        items=serialized_items,
        notes=_trim(data.notes),
    )

    async with session.begin():
        await set_tenant(session, tid)
        session.add(opportunity)

    await session.refresh(opportunity)
    return opportunity


async def list_opportunities(
    session: AsyncSession,
    params: OpportunityListParams,
    tenant_id: uuid.UUID | None = None,
) -> tuple[list[Opportunity], int]:
    tid = tenant_id or DEFAULT_TENANT_ID
    base = select(Opportunity).where(Opportunity.tenant_id == tid)

    if params.q:
        escaped_q = params.q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        like_pattern = f"%{escaped_q}%"
        base = base.where(
            or_(
                Opportunity.opportunity_title.ilike(like_pattern, escape="\\"),
                Opportunity.party_label.ilike(like_pattern, escape="\\"),
                Opportunity.contact_person.ilike(like_pattern, escape="\\"),
                Opportunity.contact_email.ilike(like_pattern, escape="\\"),
            )
        )

    if params.status:
        base = base.where(Opportunity.status == params.status)

    count_stmt = select(func.count()).select_from(base.subquery())
    offset = (params.page - 1) * params.page_size
    items_stmt = (
        base.order_by(Opportunity.updated_at.desc(), Opportunity.expected_closing.asc(), Opportunity.id.asc())
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


async def get_opportunity(
    session: AsyncSession,
    opportunity_id: uuid.UUID,
    tenant_id: uuid.UUID | None = None,
) -> Opportunity | None:
    tid = tenant_id or DEFAULT_TENANT_ID
    async with session.begin():
        await set_tenant(session, tid)
        result = await session.execute(
            select(Opportunity).where(Opportunity.id == opportunity_id, Opportunity.tenant_id == tid)
        )
        return result.scalar_one_or_none()


async def update_opportunity(
    session: AsyncSession,
    opportunity_id: uuid.UUID,
    data: OpportunityUpdate,
    tenant_id: uuid.UUID | None = None,
) -> Opportunity | None:
    tid = tenant_id or DEFAULT_TENANT_ID
    opportunity = await get_opportunity(session, opportunity_id, tenant_id=tid)
    if opportunity is None:
        return None
    if opportunity.version != data.version:
        raise VersionConflictError(expected=data.version, actual=opportunity.version)

    fields = data.model_fields_set - {"version"}
    merged = OpportunityCreate(
        opportunity_title=(
            data.opportunity_title
            if "opportunity_title" in fields and data.opportunity_title is not None
            else opportunity.opportunity_title
        ),
        opportunity_from=(
            data.opportunity_from
            if "opportunity_from" in fields and data.opportunity_from is not None
            else OpportunityPartyKind(opportunity.opportunity_from)
        ),
        party_name=(data.party_name if "party_name" in fields and data.party_name is not None else opportunity.party_name),
        sales_stage=(data.sales_stage if "sales_stage" in fields and data.sales_stage is not None else opportunity.sales_stage),
        probability=(data.probability if "probability" in fields and data.probability is not None else opportunity.probability),
        expected_closing=(data.expected_closing if "expected_closing" in fields else opportunity.expected_closing),
        currency=(data.currency if "currency" in fields and data.currency is not None else opportunity.currency),
        opportunity_amount=(data.opportunity_amount if "opportunity_amount" in fields else opportunity.opportunity_amount),
        opportunity_owner=(
            data.opportunity_owner if "opportunity_owner" in fields and data.opportunity_owner is not None else opportunity.opportunity_owner
        ),
        territory=(data.territory if "territory" in fields and data.territory is not None else opportunity.territory),
        customer_group=(
            data.customer_group if "customer_group" in fields and data.customer_group is not None else opportunity.customer_group
        ),
        contact_person=(
            data.contact_person if "contact_person" in fields and data.contact_person is not None else opportunity.contact_person
        ),
        contact_email=(
            data.contact_email if "contact_email" in fields and data.contact_email is not None else opportunity.contact_email
        ),
        contact_mobile=(
            data.contact_mobile if "contact_mobile" in fields and data.contact_mobile is not None else opportunity.contact_mobile
        ),
        job_title=(data.job_title if "job_title" in fields and data.job_title is not None else opportunity.job_title),
        utm_source=(data.utm_source if "utm_source" in fields and data.utm_source is not None else opportunity.utm_source),
        utm_medium=(data.utm_medium if "utm_medium" in fields and data.utm_medium is not None else opportunity.utm_medium),
        utm_campaign=(
            data.utm_campaign if "utm_campaign" in fields and data.utm_campaign is not None else opportunity.utm_campaign
        ),
        utm_content=(
            data.utm_content if "utm_content" in fields and data.utm_content is not None else opportunity.utm_content
        ),
        items=(data.items if "items" in fields and data.items is not None else _deserialize_opportunity_items(opportunity.items)),
        notes=(data.notes if "notes" in fields and data.notes is not None else opportunity.notes),
    )

    serialized_items = _serialize_opportunity_items(merged.items)
    opportunity_amount = _resolve_total_amount(merged.opportunity_amount, serialized_items)
    party_name, party_label, party_defaults = await _resolve_party_context(
        session,
        merged.opportunity_from,
        merged.party_name,
        tid,
    )

    async with session.begin():
        await set_tenant(session, tid)
        opportunity.opportunity_title = merged.opportunity_title.strip()
        opportunity.opportunity_from = merged.opportunity_from
        opportunity.party_name = party_name
        opportunity.party_label = party_label
        opportunity.sales_stage = merged.sales_stage.strip()
        opportunity.probability = merged.probability
        opportunity.expected_closing = merged.expected_closing
        opportunity.currency = merged.currency.strip().upper()
        opportunity.opportunity_amount = opportunity_amount
        opportunity.base_opportunity_amount = opportunity_amount
        opportunity.opportunity_owner = _trim(merged.opportunity_owner)
        opportunity.territory = _trim(merged.territory) or party_defaults.get("territory", "")
        opportunity.customer_group = _trim(merged.customer_group)
        opportunity.contact_person = _trim(merged.contact_person) or party_defaults.get("contact_person", "")
        opportunity.contact_email = _trim(merged.contact_email) or party_defaults.get("contact_email", "")
        opportunity.contact_mobile = _trim(merged.contact_mobile) or party_defaults.get("contact_mobile", "")
        opportunity.job_title = _trim(merged.job_title)
        opportunity.utm_source = _trim(merged.utm_source) or party_defaults.get("utm_source", "")
        opportunity.utm_medium = _trim(merged.utm_medium) or party_defaults.get("utm_medium", "")
        opportunity.utm_campaign = _trim(merged.utm_campaign) or party_defaults.get("utm_campaign", "")
        opportunity.utm_content = _trim(merged.utm_content) or party_defaults.get("utm_content", "")
        opportunity.items = serialized_items
        opportunity.notes = _trim(merged.notes)
        opportunity.version += 1
        opportunity.updated_at = datetime.now(tz=UTC)
    return opportunity


async def transition_opportunity_status(
    session: AsyncSession,
    opportunity_id: uuid.UUID,
    data: OpportunityTransition,
    tenant_id: uuid.UUID | None = None,
) -> Opportunity | None:
    tid = tenant_id or DEFAULT_TENANT_ID
    opportunity = await get_opportunity(session, opportunity_id, tenant_id=tid)
    if opportunity is None:
        return None

    current_status = OpportunityStatus(opportunity.status)
    _ensure_opportunity_transition_allowed(current_status, data.status)
    _ensure_lost_context(data)

    async with session.begin():
        await set_tenant(session, tid)
        opportunity.status = data.status
        if data.status == OpportunityStatus.LOST:
            opportunity.lost_reason = data.lost_reason.strip()
            opportunity.competitor_name = data.competitor_name.strip()
            opportunity.loss_notes = data.loss_notes.strip()
        opportunity.updated_at = datetime.now(tz=UTC)
    return opportunity


async def prepare_opportunity_quotation_handoff(
    session: AsyncSession,
    opportunity_id: uuid.UUID,
    tenant_id: uuid.UUID | None = None,
) -> OpportunityQuotationHandoff:
    tid = tenant_id or DEFAULT_TENANT_ID
    opportunity = await get_opportunity(session, opportunity_id, tenant_id=tid)
    if opportunity is None:
        raise ValidationError([{"field": "opportunity_id", "message": "Opportunity not found."}])
    _ensure_quotation_handoff_allowed(OpportunityStatus(opportunity.status))
    if not opportunity.items:
        raise ValidationError(
            [{"field": "items", "message": "At least one opportunity item is required for quotation handoff."}]
        )

    async with session.begin():
        await set_tenant(session, tid)
        opportunity.status = OpportunityStatus.QUOTATION
        opportunity.updated_at = datetime.now(tz=UTC)

    return OpportunityQuotationHandoff(
        opportunity_id=opportunity.id,
        opportunity_title=opportunity.opportunity_title,
        opportunity_from=OpportunityPartyKind(opportunity.opportunity_from),
        party_name=opportunity.party_name,
        party_label=opportunity.party_label,
        customer_group=opportunity.customer_group,
        currency=opportunity.currency,
        opportunity_amount=opportunity.opportunity_amount,
        base_opportunity_amount=opportunity.base_opportunity_amount,
        territory=opportunity.territory,
        contact_person=opportunity.contact_person,
        contact_email=opportunity.contact_email,
        contact_mobile=opportunity.contact_mobile,
        job_title=opportunity.job_title,
        utm_source=opportunity.utm_source,
        utm_medium=opportunity.utm_medium,
        utm_campaign=opportunity.utm_campaign,
        utm_content=opportunity.utm_content,
        items=[OpportunityItem.model_validate(item) for item in opportunity.items],
    )
