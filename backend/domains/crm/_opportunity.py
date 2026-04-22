"""CRM opportunity services."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.errors import ValidationError, VersionConflictError
from common.tenant import DEFAULT_TENANT_ID, set_tenant
from domains.crm._setup import (
    _ensure_customer_group_supported,
    _ensure_sales_stage_supported,
    _ensure_territory_supported,
)
from domains.crm._shared import (
    _deserialize_opportunity_items,
    _resolve_total_amount,
    _serialize_opportunity_items,
    _trim,
)
from domains.crm.models import Lead, Opportunity
from domains.crm.schemas import (
    LeadStatus,
    OpportunityCreate,
    OpportunityItem,
    OpportunityListParams,
    OpportunityPartyKind,
    OpportunityQuotationHandoff,
    OpportunityStatus,
    OpportunityTransition,
    OpportunityUpdate,
    QuotationPartyKind,
)

# Re-export conversion target constant for use in this module
from domains.crm._lead import CONVERSION_TARGET_OPPORTUNITY  # noqa: F401

# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

ALLOWED_OPPORTUNITY_TRANSITIONS: dict[OpportunityStatus, frozenset[OpportunityStatus]] = {
    OpportunityStatus.OPEN: frozenset({
        OpportunityStatus.REPLIED,
        OpportunityStatus.QUOTATION,
        OpportunityStatus.CLOSED,
        OpportunityStatus.LOST,
    }),
    OpportunityStatus.REPLIED: frozenset({
        OpportunityStatus.QUOTATION,
        OpportunityStatus.CLOSED,
        OpportunityStatus.LOST,
    }),
    OpportunityStatus.QUOTATION: frozenset({
        OpportunityStatus.CONVERTED,
        OpportunityStatus.CLOSED,
        OpportunityStatus.LOST,
    }),
    OpportunityStatus.CLOSED: frozenset(),
    OpportunityStatus.LOST: frozenset({OpportunityStatus.OPEN}),
    OpportunityStatus.CONVERTED: frozenset(),
}


def _ensure_opportunity_transition_allowed(
    current: OpportunityStatus,
    target: OpportunityStatus,
) -> None:
    """Validate opportunity status transition."""
    if target not in ALLOWED_OPPORTUNITY_TRANSITIONS.get(current, frozenset()):
        raise ValidationError(
            [{"field": "status", "message": f"Cannot transition from '{current.value}' to '{target.value}'."}]
        )


def _ensure_lost_context(data: OpportunityTransition) -> None:
    """Validate lost opportunity has required context."""
    if data.status == OpportunityStatus.LOST and not data.lost_reason.strip():
        raise ValidationError(
            [{"field": "lost_reason", "message": "Lost opportunities require a lost reason."}]
        )


# ---------------------------------------------------------------------------
# Merge helpers
# ---------------------------------------------------------------------------


def _should_resolve_opportunity_party(merged: OpportunityCreate, existing: object) -> bool:
    """Determine if party context resolution is needed."""
    existing_opportunity_from_value = existing.opportunity_from
    if existing_opportunity_from_value is None:
        return merged.opportunity_from is not None
    existing_opportunity_from = OpportunityPartyKind(existing_opportunity_from_value)
    return (
        merged.opportunity_from != existing_opportunity_from
        or merged.party_name != existing.party_name
    )


def _build_opportunity_merged(
    data: OpportunityUpdate,
    existing: Opportunity,
) -> OpportunityCreate:
    """Build an OpportunityCreate by merging update data with existing values."""
    fields = data.model_fields_set - {"version"}
    existing_items = _deserialize_opportunity_items(
        json.loads(existing.items) if isinstance(existing.items, str) else existing.items or []
    )

    return OpportunityCreate(
        opportunity_title=(
            data.opportunity_title
            if "opportunity_title" in fields and data.opportunity_title is not None
            else existing.opportunity_title
        ),
        opportunity_from=(
            OpportunityPartyKind(data.opportunity_from)
            if "opportunity_from" in fields and data.opportunity_from is not None
            else OpportunityPartyKind(existing.opportunity_from)
        ),
        party_name=(
            data.party_name
            if "party_name" in fields and data.party_name is not None
            else existing.party_name
        ),
        sales_stage=(
            data.sales_stage
            if "sales_stage" in fields and data.sales_stage is not None
            else existing.sales_stage
        ),
        probability=(
            data.probability
            if "probability" in fields and data.probability is not None
            else existing.probability
        ),
        expected_closing=(
            data.expected_closing
            if "expected_closing" in fields
            else existing.expected_closing
        ),
        currency=(
            data.currency
            if "currency" in fields and data.currency is not None
            else existing.currency
        ),
        opportunity_amount=(
            data.opportunity_amount
            if "opportunity_amount" in fields
            else existing.opportunity_amount
        ),
        opportunity_owner=(
            data.opportunity_owner
            if "opportunity_owner" in fields and data.opportunity_owner is not None
            else existing.opportunity_owner
        ),
        territory=(
            data.territory
            if "territory" in fields and data.territory is not None
            else existing.territory
        ),
        customer_group=(
            data.customer_group
            if "customer_group" in fields and data.customer_group is not None
            else existing.customer_group
        ),
        contact_person=(
            data.contact_person
            if "contact_person" in fields and data.contact_person is not None
            else existing.contact_person
        ),
        contact_email=(
            data.contact_email
            if "contact_email" in fields and data.contact_email is not None
            else existing.contact_email
        ),
        contact_mobile=(
            data.contact_mobile
            if "contact_mobile" in fields and data.contact_mobile is not None
            else existing.contact_mobile
        ),
        job_title=(
            data.job_title
            if "job_title" in fields and data.job_title is not None
            else existing.job_title
        ),
        utm_source=(
            data.utm_source
            if "utm_source" in fields and data.utm_source is not None
            else existing.utm_source
        ),
        utm_medium=(
            data.utm_medium
            if "utm_medium" in fields and data.utm_medium is not None
            else existing.utm_medium
        ),
        utm_campaign=(
            data.utm_campaign
            if "utm_campaign" in fields and data.utm_campaign is not None
            else existing.utm_campaign
        ),
        utm_content=(
            data.utm_content
            if "utm_content" in fields and data.utm_content is not None
            else existing.utm_content
        ),
        items=(
            data.items
            if "items" in fields and data.items is not None
            else existing_items
        ),
        notes=(
            data.notes
            if "notes" in fields and data.notes is not None
            else existing.notes
        ),
    )


def _apply_opportunity_fields_to_record(
    record: Opportunity,
    merged: OpportunityCreate,
    party_name: str,
    party_label: str,
    party_defaults: dict[str, str] | None = None,
    serialized_items: list[dict[str, object]] | None = None,
    resolved_amount: Decimal | None = None,
) -> None:
    """Apply merged OpportunityCreate fields to an existing record."""
    defaults = party_defaults or {}

    record.opportunity_title = merged.opportunity_title.strip()
    record.opportunity_from = merged.opportunity_from
    record.party_name = party_name
    record.party_label = party_label
    record.sales_stage = merged.sales_stage.strip()
    record.probability = merged.probability
    record.expected_closing = merged.expected_closing
    record.currency = merged.currency.strip().upper()
    # Use resolved_amount if provided, otherwise use merged value
    record.opportunity_amount = resolved_amount if resolved_amount is not None else merged.opportunity_amount
    record.base_opportunity_amount = record.opportunity_amount
    record.opportunity_owner = _trim(merged.opportunity_owner)
    record.territory = _trim(merged.territory) or defaults.get("territory", "")
    record.customer_group = _trim(merged.customer_group)
    record.contact_person = _trim(merged.contact_person) or defaults.get("contact_person", "")
    record.contact_email = _trim(merged.contact_email) or defaults.get("contact_email", "")
    record.contact_mobile = _trim(merged.contact_mobile) or defaults.get("contact_mobile", "")
    record.job_title = _trim(merged.job_title)
    record.utm_source = _trim(merged.utm_source) or defaults.get("utm_source", "")
    record.utm_medium = _trim(merged.utm_medium) or defaults.get("utm_medium", "")
    record.utm_campaign = _trim(merged.utm_campaign) or defaults.get("utm_campaign", "")
    record.utm_content = _trim(merged.utm_content) or defaults.get("utm_content", "")
    record.items = serialized_items if serialized_items is not None else record.items
    record.notes = _trim(merged.notes)
    record.version += 1
    record.updated_at = datetime.now(tz=UTC)


# ---------------------------------------------------------------------------
# Party context resolution
# ---------------------------------------------------------------------------


async def _resolve_party_context(
    session: AsyncSession,
    party_kind: OpportunityPartyKind | QuotationPartyKind,
    party_name: str,
    tenant_id: uuid.UUID,
) -> tuple[str, str, dict[str, str]]:
    """Resolve party context including defaults.

    Returns:
        tuple of (party_name, party_label, party_defaults)
    """
    from domains.customers.models import Customer

    party_defaults: dict[str, str] = {}

    if party_kind in {OpportunityPartyKind.CUSTOMER, QuotationPartyKind.CUSTOMER}:
        try:
            customer_id = uuid.UUID(party_name)
        except ValueError:
            return party_name, party_name, party_defaults

        async with session.begin():
            await set_tenant(session, tenant_id)
            result = await session.execute(
                select(Customer).where(
                    Customer.id == customer_id,
                    Customer.tenant_id == tenant_id,
                )
            )
            customer = result.scalar_one_or_none()

        if customer is not None:
            return (
                str(customer.id),
                customer.company_name,
                {
                    "contact_person": customer.contact_name,
                    "contact_email": customer.contact_email,
                    "contact_mobile": customer.contact_phone,
                },
            )
        raise ValidationError(
            [{"field": "party_name", "message": "Customer party not found."}]
        )

    if party_kind in {OpportunityPartyKind.LEAD, QuotationPartyKind.LEAD}:
        try:
            lead_id = uuid.UUID(party_name)
        except ValueError:
            return party_name, party_name, party_defaults

        async with session.begin():
            await set_tenant(session, tenant_id)
            result = await session.execute(
                select(Lead).where(
                    Lead.id == lead_id,
                    Lead.tenant_id == tenant_id,
                )
            )
            lead = result.scalar_one_or_none()

        if lead is not None:
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
        raise ValidationError(
            [{"field": "party_name", "message": "Lead party not found."}]
        )

    return party_name, party_name, party_defaults


# ---------------------------------------------------------------------------
# Conversion payload builders
# ---------------------------------------------------------------------------


def _build_opportunity_conversion_payload(
    lead: Lead,
    payload: OpportunityCreate,
) -> OpportunityCreate:
    """Build opportunity payload from lead for conversion."""
    data = payload.model_dump(mode="python")
    data["opportunity_from"] = OpportunityPartyKind.LEAD
    data["party_name"] = str(lead.id)
    return OpportunityCreate.model_validate(data)


def _try_parse_uuid(value: str) -> uuid.UUID | None:
    """Try to parse a string as UUID."""
    try:
        return uuid.UUID(value)
    except (TypeError, ValueError):
        return None


async def _record_lead_opportunity_conversion(
    session: AsyncSession,
    lead_id: uuid.UUID,
    tenant_id: uuid.UUID,
    opportunity_id: uuid.UUID,
) -> Lead | None:
    """Record lead conversion to opportunity.
    
    Delegates to _record_lead_conversion for consistent state management.
    """
    from domains.crm._lead import _record_lead_conversion

    # Reuse the main conversion recording for consistent state calculation
    return await _record_lead_conversion(
        session,
        lead_id,
        tenant_id=tenant_id,
        requested_targets={CONVERSION_TARGET_OPPORTUNITY},
        opportunity_id=opportunity_id,
    )


# ---------------------------------------------------------------------------
# Public CRUD functions
# ---------------------------------------------------------------------------

import json


async def create_opportunity(
    session: AsyncSession,
    data: OpportunityCreate,
    tenant_id: uuid.UUID | None = None,
) -> Opportunity:
    """Create a new opportunity."""
    tid = tenant_id or DEFAULT_TENANT_ID
    sales_stage = await _ensure_sales_stage_supported(session, data.sales_stage, tid)
    territory = await _ensure_territory_supported(session, data.territory, tid)
    customer_group = await _ensure_customer_group_supported(session, data.customer_group, tid)
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
        sales_stage=sales_stage,
        probability=data.probability,
        expected_closing=data.expected_closing,
        currency=data.currency.strip().upper(),
        opportunity_amount=opportunity_amount,
        base_opportunity_amount=opportunity_amount,
        opportunity_owner=_trim(data.opportunity_owner),
        territory=territory or party_defaults.get("territory", ""),
        customer_group=customer_group,
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
    if opportunity.opportunity_from == OpportunityPartyKind.LEAD:
        lead_id = _try_parse_uuid(opportunity.party_name)
        if lead_id is not None:
            await _record_lead_opportunity_conversion(
                session,
                lead_id,
                tid,
                opportunity.id,
            )
    return opportunity


async def list_opportunities(
    session: AsyncSession,
    params: OpportunityListParams,
    tenant_id: uuid.UUID | None = None,
) -> tuple[list[Opportunity], int]:
    """List opportunities with pagination and filtering."""
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
        base.order_by(
            Opportunity.updated_at.desc(),
            Opportunity.expected_closing.asc(),
            Opportunity.id.asc(),
        )
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
    """Get a single opportunity by ID."""
    tid = tenant_id or DEFAULT_TENANT_ID
    async with session.begin():
        await set_tenant(session, tid)
        result = await session.execute(
            select(Opportunity).where(
                Opportunity.id == opportunity_id,
                Opportunity.tenant_id == tid,
            )
        )
        return result.scalar_one_or_none()


async def update_opportunity(
    session: AsyncSession,
    opportunity_id: uuid.UUID,
    data: OpportunityUpdate,
    tenant_id: uuid.UUID | None = None,
) -> Opportunity | None:
    """Update an existing opportunity."""
    tid = tenant_id or DEFAULT_TENANT_ID
    opportunity = await get_opportunity(session, opportunity_id, tenant_id=tid)
    if opportunity is None:
        return None
    if opportunity.version != data.version:
        raise VersionConflictError(expected=data.version, actual=opportunity.version)

    merged = _build_opportunity_merged(data, opportunity)
    serialized_items = _serialize_opportunity_items(merged.items)
    resolved_opportunity_amount = _resolve_total_amount(merged.opportunity_amount, serialized_items)

    if _should_resolve_opportunity_party(merged, opportunity):
        party_name, party_label, party_defaults = await _resolve_party_context(
            session,
            merged.opportunity_from,
            merged.party_name,
            tid,
        )
    else:
        party_name = opportunity.party_name
        party_label = opportunity.party_label
        party_defaults: dict[str, str] = {}

    async with session.begin():
        await set_tenant(session, tid)
        _apply_opportunity_fields_to_record(
            opportunity,
            merged,
            party_name,
            party_label,
            party_defaults,
            serialized_items=serialized_items,
            resolved_amount=resolved_opportunity_amount,
        )
    return opportunity


async def transition_opportunity_status(
    session: AsyncSession,
    opportunity_id: uuid.UUID,
    data: OpportunityTransition,
    tenant_id: uuid.UUID | None = None,
) -> Opportunity | None:
    """Transition opportunity status."""
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


def _ensure_quotation_handoff_allowed(current_status: OpportunityStatus) -> None:
    """Validate opportunity can be handed off for quotation."""
    if current_status not in {
        OpportunityStatus.OPEN,
        OpportunityStatus.REPLIED,
        OpportunityStatus.QUOTATION,
    }:
        raise ValidationError(
            [{"field": "status", "message": "Only open or active opportunities can be prepared for quotation handoff."}]
        )


async def prepare_opportunity_quotation_handoff(
    session: AsyncSession,
    opportunity_id: uuid.UUID,
    tenant_id: uuid.UUID | None = None,
) -> OpportunityQuotationHandoff:
    """Prepare handoff data for creating quotation from opportunity."""
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
