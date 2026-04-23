"""CRM quotation services."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.errors import ValidationError, VersionConflictError
from common.models.order import Order
from common.models.order_line import OrderLine
from common.tenant import DEFAULT_TENANT_ID, set_tenant
from domains.crm._lead import get_lead
from domains.crm._setup import (
    _ensure_customer_group_supported,
    _ensure_territory_supported,
    _resolve_effective_quotation_valid_till,
)
from domains.crm._shared import (
    _deserialize_opportunity_items,
    _deserialize_quotation_taxes,
    _resolve_party_context,
    _resolve_serialized_decimal_sum,
    _resolve_total_amount,
    _serialize_opportunity_items,
    _serialize_quotation_taxes,
    _trim,
)
from domains.crm.models import Lead, Quotation
from domains.crm.schemas import QuotationCreate as QuotationCreateSchema
from domains.crm.schemas import (
    LeadStatus,
    OpportunityPartyKind,
    QuotationCreate,
    QuotationLinkedOrder,
    QuotationListParams,
    QuotationOrderHandoff,
    QuotationOrderHandoffLine,
    QuotationPartyKind,
    QuotationRemainingItem,
    QuotationRevisionCreate,
    QuotationStatus,
    QuotationTaxInput,
    QuotationTransition,
    QuotationUpdate,
)

# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

ALLOWED_QUOTATION_TRANSITIONS: dict[QuotationStatus, frozenset[QuotationStatus]] = {
    QuotationStatus.DRAFT: frozenset({QuotationStatus.OPEN}),
    QuotationStatus.OPEN: frozenset({QuotationStatus.REPLIED, QuotationStatus.LOST, QuotationStatus.CANCELLED}),
    QuotationStatus.REPLIED: frozenset({QuotationStatus.PARTIALLY_ORDERED, QuotationStatus.ORDERED, QuotationStatus.LOST}),
    QuotationStatus.PARTIALLY_ORDERED: frozenset({QuotationStatus.ORDERED, QuotationStatus.LOST}),
    QuotationStatus.ORDERED: frozenset(),
    QuotationStatus.LOST: frozenset({QuotationStatus.OPEN}),
    QuotationStatus.EXPIRED: frozenset({QuotationStatus.OPEN}),
    QuotationStatus.CANCELLED: frozenset({QuotationStatus.OPEN}),
}

DERIVED_QUOTATION_STATUSES = frozenset({QuotationStatus.DRAFT, QuotationStatus.OPEN, QuotationStatus.REPLIED})


def _ensure_quotation_transition_allowed(
    current: QuotationStatus,
    target: QuotationStatus,
) -> None:
    """Validate quotation status transition."""
    if target not in ALLOWED_QUOTATION_TRANSITIONS.get(current, frozenset()):
        raise ValueError(
            f"Cannot transition quotation from {current.value} to {target.value}"
        )


def _ensure_quotation_lost_context(data: QuotationTransition) -> None:
    """Validate lost quotation has required context."""
    if data.status == QuotationStatus.LOST and not data.lost_reason:
        raise ValidationError(
            [{"field": "lost_reason", "message": "Lost reason is required when marking quotation as lost."}]
        )


def _ensure_quotation_validity(transaction_date: date, valid_till: date) -> None:
    """Validate quotation dates."""
    if valid_till < transaction_date:
        raise ValueError("Valid till date must be on or after transaction date")


def _ensure_auto_repeat_metadata(enabled: bool, frequency: str) -> None:
    """Validate auto-repeat configuration."""
    if enabled and not frequency:
        raise ValueError("Auto-repeat frequency is required when auto-repeat is enabled")


def _ensure_order_handoff_allowed(current_status: QuotationStatus) -> None:
    """Validate quotation can be converted to order."""
    if current_status in {QuotationStatus.ORDERED, QuotationStatus.LOST, QuotationStatus.CANCELLED}:
        raise ValueError(
            f"Cannot convert quotation to order when status is {current_status.value}"
        )


# ---------------------------------------------------------------------------
# Merge helpers
# ---------------------------------------------------------------------------


def _should_resolve_party(merged: QuotationCreate, existing: object) -> bool:
    """Determine if party context resolution is needed."""
    existing_quotation_to_value = existing.quotation_to
    if existing_quotation_to_value is None:
        return merged.quotation_to is not None
    existing_quotation_to = QuotationPartyKind(existing_quotation_to_value)
    return (
        merged.quotation_to != existing_quotation_to
        or merged.party_name != existing.party_name
    )


def _build_quotation_merged(
    data: QuotationUpdate | QuotationRevisionCreate,
    existing: Quotation,
) -> QuotationCreate:
    """Build a QuotationCreate by merging update data with existing values."""
    fields = data.model_fields_set
    existing_items = _deserialize_opportunity_items(
        json.loads(existing.items) if isinstance(existing.items, str) else existing.items or []
    )
    existing_taxes = _deserialize_quotation_taxes(
        json.loads(existing.taxes) if isinstance(existing.taxes, str) else existing.taxes or []
    )

    return QuotationCreate(
        quotation_to=(
            QuotationPartyKind(data.quotation_to)
            if "quotation_to" in fields and data.quotation_to is not None
            else QuotationPartyKind(existing.quotation_to)
        ),
        party_name=(
            data.party_name
            if "party_name" in fields and data.party_name is not None
            else existing.party_name
        ),
        transaction_date=(
            data.transaction_date
            if "transaction_date" in fields and data.transaction_date is not None
            else existing.transaction_date
        ),
        valid_till=(
            data.valid_till
            if "valid_till" in fields and data.valid_till is not None
            else existing.valid_till
        ),
        company=(
            data.company
            if "company" in fields and data.company is not None
            else existing.company
        ),
        currency=(
            data.currency
            if "currency" in fields and data.currency is not None
            else existing.currency
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
        billing_address=(
            data.billing_address
            if "billing_address" in fields and data.billing_address is not None
            else existing.billing_address
        ),
        shipping_address=(
            data.shipping_address
            if "shipping_address" in fields and data.shipping_address is not None
            else existing.shipping_address
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
        opportunity_id=(
            data.opportunity_id
            if "opportunity_id" in fields
            else existing.opportunity_id
        ),
        items=(
            data.items
            if "items" in fields and data.items is not None
            else existing_items
        ),
        taxes=(
            data.taxes
            if "taxes" in fields and data.taxes is not None
            else existing_taxes
        ),
        terms_template=(
            data.terms_template
            if "terms_template" in fields and data.terms_template is not None
            else existing.terms_template
        ),
        terms_and_conditions=(
            data.terms_and_conditions
            if "terms_and_conditions" in fields and data.terms_and_conditions is not None
            else existing.terms_and_conditions
        ),
        auto_repeat_enabled=(
            data.auto_repeat_enabled
            if "auto_repeat_enabled" in fields and data.auto_repeat_enabled is not None
            else existing.auto_repeat_enabled
        ),
        auto_repeat_frequency=(
            data.auto_repeat_frequency
            if "auto_repeat_frequency" in fields and data.auto_repeat_frequency is not None
            else existing.auto_repeat_frequency
        ),
        auto_repeat_until=(
            data.auto_repeat_until
            if "auto_repeat_until" in fields
            else existing.auto_repeat_until
        ),
        notes=(
            data.notes
            if "notes" in fields and data.notes is not None
            else existing.notes
        ),
    )


def _apply_quotation_fields_to_record(
    record: Quotation,
    merged: QuotationCreate,
    party_name: str,
    party_label: str,
    party_defaults: dict[str, str] | None = None,
) -> None:
    """Apply merged QuotationCreate fields to an existing record."""
    defaults = party_defaults or {}

    record.quotation_to = merged.quotation_to
    record.party_name = party_name
    record.party_label = party_label
    record.transaction_date = merged.transaction_date
    record.valid_till = merged.valid_till
    record.company = merged.company.strip()
    record.currency = merged.currency.strip().upper()
    record.contact_person = _trim(merged.contact_person) or defaults.get("contact_person", "")
    record.contact_email = _trim(merged.contact_email) or defaults.get("contact_email", "")
    record.contact_mobile = _trim(merged.contact_mobile) or defaults.get("contact_mobile", "")
    record.job_title = _trim(merged.job_title)
    record.territory = _trim(merged.territory) or defaults.get("territory", "")
    record.customer_group = _trim(merged.customer_group)
    record.billing_address = _trim(merged.billing_address)
    record.shipping_address = _trim(merged.shipping_address)
    record.utm_source = _trim(merged.utm_source) or defaults.get("utm_source", "")
    record.utm_medium = _trim(merged.utm_medium) or defaults.get("utm_medium", "")
    record.utm_campaign = _trim(merged.utm_campaign) or defaults.get("utm_campaign", "")
    record.utm_content = _trim(merged.utm_content) or defaults.get("utm_content", "")
    record.terms_template = _trim(merged.terms_template)
    record.terms_and_conditions = _trim(merged.terms_and_conditions)
    record.opportunity_id = merged.opportunity_id
    record.auto_repeat_enabled = merged.auto_repeat_enabled
    record.auto_repeat_frequency = _trim(merged.auto_repeat_frequency)
    record.auto_repeat_until = merged.auto_repeat_until
    record.notes = _trim(merged.notes)
    record.version += 1
    record.updated_at = datetime.now(tz=UTC)


def _build_quotation_record(
    merged: QuotationCreate,
    tenant_id: uuid.UUID,
    party_name: str,
    party_label: str,
    party_defaults: dict[str, str] | None = None,
    subtotal: Decimal | None = None,
    total_taxes: Decimal | None = None,
    grand_total: Decimal | None = None,
    serialized_items: list[dict[str, object]] | None = None,
    serialized_taxes: list[dict[str, object]] | None = None,
    opportunity_id: uuid.UUID | None = None,
    amended_from: uuid.UUID | None = None,
    revision_no: int = 0,
    valid_till_override: date | None = None,
    territory_override: str | None = None,
    customer_group_override: str | None = None,
) -> Quotation:
    """Build a new Quotation record from merged data."""
    defaults = party_defaults or {}

    if serialized_items is None:
        serialized_items = _serialize_opportunity_items(merged.items)
    if subtotal is None:
        subtotal = _resolve_total_amount(None, serialized_items) or Decimal("0.00")
    if serialized_taxes is None:
        serialized_taxes = _serialize_quotation_taxes(merged.taxes, subtotal)
    if total_taxes is None:
        total_taxes = _resolve_serialized_decimal_sum(serialized_taxes, "tax_amount")
    if grand_total is None:
        grand_total = (subtotal + total_taxes).quantize(Decimal("0.01"))

    effective_valid_till = valid_till_override if valid_till_override is not None else merged.valid_till
    effective_territory = territory_override if territory_override is not None else (_trim(merged.territory) or defaults.get("territory", ""))
    effective_customer_group = customer_group_override if customer_group_override is not None else _trim(merged.customer_group)

    return Quotation(
        tenant_id=tenant_id,
        quotation_to=merged.quotation_to,
        party_name=party_name,
        party_label=party_label,
        status=QuotationStatus.DRAFT,
        transaction_date=merged.transaction_date,
        valid_till=effective_valid_till,
        company=merged.company.strip(),
        currency=merged.currency.strip().upper(),
        subtotal=subtotal,
        total_taxes=total_taxes,
        grand_total=grand_total,
        base_grand_total=grand_total,
        ordered_amount=Decimal("0.00"),
        order_count=0,
        contact_person=_trim(merged.contact_person) or defaults.get("contact_person", ""),
        contact_email=_trim(merged.contact_email) or defaults.get("contact_email", ""),
        contact_mobile=_trim(merged.contact_mobile) or defaults.get("contact_mobile", ""),
        job_title=_trim(merged.job_title),
        territory=effective_territory,
        customer_group=effective_customer_group,
        billing_address=_trim(merged.billing_address),
        shipping_address=_trim(merged.shipping_address),
        utm_source=_trim(merged.utm_source) or defaults.get("utm_source", ""),
        utm_medium=_trim(merged.utm_medium) or defaults.get("utm_medium", ""),
        utm_campaign=_trim(merged.utm_campaign) or defaults.get("utm_campaign", ""),
        utm_content=_trim(merged.utm_content) or defaults.get("utm_content", ""),
        items=serialized_items,
        taxes=serialized_taxes,
        terms_template=_trim(merged.terms_template),
        terms_and_conditions=_trim(merged.terms_and_conditions),
        opportunity_id=opportunity_id if opportunity_id is not None else merged.opportunity_id,
        amended_from=amended_from,
        revision_no=revision_no,
        auto_repeat_enabled=merged.auto_repeat_enabled,
        auto_repeat_frequency=_trim(merged.auto_repeat_frequency),
        auto_repeat_until=merged.auto_repeat_until,
        notes=_trim(merged.notes),
    )


# ---------------------------------------------------------------------------
# Conversion payload builders
# ---------------------------------------------------------------------------


def _build_quotation_conversion_payload(
    lead: Lead,
    payload: QuotationCreateSchema,
    opportunity_id: uuid.UUID | None = None,
) -> QuotationCreateSchema:
    """Build quotation payload from lead for conversion."""
    data = payload.model_dump(mode="python")
    data["quotation_to"] = QuotationPartyKind.LEAD
    data["party_name"] = str(lead.id)
    if opportunity_id is not None and data.get("opportunity_id") is None:
        data["opportunity_id"] = opportunity_id
    return QuotationCreateSchema.model_validate(data)


# ---------------------------------------------------------------------------
# Order conversion helpers
# ---------------------------------------------------------------------------


def _build_quotation_crm_context_snapshot(
    quotation: Quotation,
) -> dict[str, object]:
    """Build CRM context snapshot for order handoff."""
    return {
        "source_document_type": "quotation",
        "source_document_id": str(quotation.id),
        "party_kind": quotation.quotation_to,
        "party_label": quotation.party_label,
        "quotation_revision_no": quotation.revision_no,
        "currency": quotation.currency,
        "contact_person": quotation.contact_person,
        "contact_email": quotation.contact_email,
        "contact_mobile": quotation.contact_mobile,
        "job_title": quotation.job_title,
        "territory": quotation.territory,
        "customer_group": quotation.customer_group,
        "billing_address": quotation.billing_address,
        "shipping_address": quotation.shipping_address,
        "utm_source": quotation.utm_source,
        "utm_medium": quotation.utm_medium,
        "utm_campaign": quotation.utm_campaign,
        "utm_content": quotation.utm_content,
        "opportunity_id": (
            str(quotation.opportunity_id)
            if quotation.opportunity_id
            else None
        ),
        "transaction_date": quotation.transaction_date.isoformat(),
        "valid_till": quotation.valid_till.isoformat(),
        "subtotal": str(quotation.subtotal),
        "total_taxes": str(quotation.total_taxes),
        "grand_total": str(quotation.grand_total),
        "taxes": quotation.taxes,
        "terms_template": quotation.terms_template,
        "terms_and_conditions": quotation.terms_and_conditions,
    }


async def _resolve_product_ids_by_item_code(
    session: AsyncSession,
    items: list[dict[str, object]],
    tenant_id: uuid.UUID,
) -> dict[str, uuid.UUID]:
    """Resolve product IDs from item codes."""
    item_codes = {
        str(item.get("item_code") or "").strip()
        for item in items
        if not item.get("product_id")
    }
    item_codes.discard("")
    if not item_codes:
        return {}

    from common.models.product import Product

    result = await session.execute(
        select(Product.id, Product.code).where(
            Product.tenant_id == tenant_id,
            Product.code.in_(sorted(item_codes)),
        )
    )
    return {str(row.code): row.id for row in result.all()}


async def _build_quotation_order_handoff_lines(
    session: AsyncSession,
    items: list[dict[str, object]],
    tenant_id: uuid.UUID,
) -> list[QuotationOrderHandoffLine]:
    """Build order handoff lines from quotation items."""
    product_ids_by_code = await _resolve_product_ids_by_item_code(session, items, tenant_id)
    lines: list[QuotationOrderHandoffLine] = []
    for item in items:
        raw_product_id = item.get("product_id")
        product_id: uuid.UUID | None = None
        if raw_product_id:
            try:
                product_id = uuid.UUID(str(raw_product_id))
            except ValueError as exc:
                raise ValidationError(
                    [{"field": "items", "message": "Quotation item product mapping is invalid for order conversion."}]
                ) from exc

        if product_id is None:
            item_code = str(item.get("item_code") or "").strip()
            product_id = product_ids_by_code.get(item_code)

        if product_id is None:
            raise ValidationError(
                [{"field": "items", "message": "Resolve quotation items to catalog products before order conversion."}]
            )

        description = str(item.get("description") or item.get("item_name") or "").strip()
        if not description:
            raise ValidationError(
                [{"field": "items", "message": "Quotation items require a description before order conversion."}]
            )

        line_no = int(item.get("line_no") or 0)
        quantity = Decimal(str(item.get("quantity") or "0"))
        unit_price = Decimal(str(item.get("unit_price") or "0.00")).quantize(Decimal("0.01"))
        lines.append(
            QuotationOrderHandoffLine(
                source_quotation_line_no=line_no,
                product_id=product_id,
                description=description,
                quantity=quantity,
                list_unit_price=unit_price,
                unit_price=unit_price,
                discount_amount=Decimal("0.00"),
                tax_policy_code="standard",
            )
        )
    return lines


async def _resolve_quotation_order_customer_id(
    session: AsyncSession,
    quotation: Quotation,
    tenant_id: uuid.UUID,
) -> uuid.UUID:
    """Resolve customer ID for order conversion."""
    quotation_to = QuotationPartyKind(quotation.quotation_to)
    if quotation_to == QuotationPartyKind.CUSTOMER:
        try:
            return uuid.UUID(quotation.party_name)
        except ValueError as exc:
            raise ValidationError(
                [{"field": "party_name", "message": "Quotation customer context is invalid for order conversion."}]
            ) from exc

    if quotation_to == QuotationPartyKind.LEAD:
        try:
            lead_id = uuid.UUID(quotation.party_name)
        except ValueError as exc:
            raise ValidationError(
                [{"field": "party_name", "message": "Quotation lead context is invalid for order conversion."}]
            ) from exc

        lead = await get_lead(session, lead_id, tenant_id=tenant_id)
        if lead is not None and lead.converted_customer_id is not None:
            return lead.converted_customer_id

    raise ValidationError(
        [{"field": "party_name", "message": "Resolve this quotation to an existing customer before order conversion."}]
    )


def _line_amount_from_item(item: dict[str, object]) -> Decimal:
    """Calculate line amount from item data."""
    raw_amount = item.get("amount")
    if raw_amount is not None and str(raw_amount) != "":
        return Decimal(str(raw_amount)).quantize(Decimal("0.01"))
    quantity = Decimal(str(item.get("quantity") or "0"))
    unit_price = Decimal(str(item.get("unit_price") or "0.00"))
    return (quantity * unit_price).quantize(Decimal("0.01"))


async def _load_linked_order_rows(
    session: AsyncSession,
    quotation_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> list[object]:
    """Load order rows linked to a quotation."""
    result = await session.execute(
        select(
            Order.id.label("order_id"),
            Order.order_number,
            Order.status,
            Order.total_amount,
            Order.created_at,
            OrderLine.source_quotation_line_no,
            OrderLine.quantity,
        )
        .join(OrderLine, OrderLine.order_id == Order.id)
        .where(
            Order.tenant_id == tenant_id,
            Order.source_quotation_id == quotation_id,
            Order.status != "cancelled",
            OrderLine.source_quotation_line_no.is_not(None),
        )
        .order_by(
            Order.created_at.desc(),
            Order.order_number.asc(),
            OrderLine.line_number.asc(),
        )
    )
    if not hasattr(result, "all"):
        return []
    return list(result.all())


def _build_quotation_conversion_details(
    quotation: Quotation,
    linked_rows: list[object],
) -> tuple[
    Decimal,
    int,
    list[QuotationLinkedOrder],
    list[QuotationRemainingItem],
]:
    """Calculate conversion coverage details."""
    ordered_quantities: dict[int, Decimal] = {}
    linked_orders_by_id: dict[uuid.UUID, QuotationLinkedOrder] = {}
    quantity_quant = Decimal("0.001")

    for row in linked_rows:
        source_line_no = getattr(row, "source_quotation_line_no", None)
        if source_line_no is not None:
            ordered_quantities[source_line_no] = (
                ordered_quantities.get(source_line_no, Decimal("0.000"))
                + Decimal(str(getattr(row, "quantity", "0")))
            )

        order_id = getattr(row, "order_id")
        linked_order = linked_orders_by_id.get(order_id)
        if linked_order is None:
            linked_order = QuotationLinkedOrder(
                order_id=order_id,
                order_number=str(getattr(row, "order_number")),
                status=str(getattr(row, "status")),
                total_amount=getattr(row, "total_amount", None),
                linked_line_count=0,
                created_at=getattr(row, "created_at"),
            )
            linked_orders_by_id[order_id] = linked_order
        linked_order.linked_line_count += 1

    ordered_amount = Decimal("0.00")
    remaining_items: list[QuotationRemainingItem] = []
    for item in quotation.items:
        line_no = int(item.get("line_no") or 0)
        quoted_quantity = Decimal(str(item.get("quantity") or "0")).quantize(quantity_quant)
        ordered_quantity = min(
            ordered_quantities.get(line_no, Decimal("0.000")).quantize(quantity_quant),
            quoted_quantity,
        )
        remaining_quantity = max(quoted_quantity - ordered_quantity, Decimal("0.000")).quantize(quantity_quant)

        quoted_amount = _line_amount_from_item(item)
        ordered_line_amount = Decimal("0.00")
        if quoted_quantity > 0:
            ordered_line_amount = (
                quoted_amount * (ordered_quantity / quoted_quantity)
            ).quantize(Decimal("0.01"))
        remaining_amount = max(quoted_amount - ordered_line_amount, Decimal("0.00")).quantize(Decimal("0.01"))
        ordered_amount += ordered_line_amount

        if remaining_quantity > 0:
            remaining_items.append(
                QuotationRemainingItem(
                    line_no=line_no,
                    item_name=str(item.get("item_name") or ""),
                    item_code=str(item.get("item_code") or ""),
                    description=str(item.get("description") or ""),
                    quoted_quantity=quoted_quantity,
                    ordered_quantity=ordered_quantity,
                    remaining_quantity=remaining_quantity,
                    quoted_amount=quoted_amount,
                    ordered_amount=ordered_line_amount,
                    remaining_amount=remaining_amount,
                )
            )

    return (
        ordered_amount.quantize(Decimal("0.01")),
        len(linked_orders_by_id),
        list(linked_orders_by_id.values()),
        remaining_items,
    )


def _derive_quotation_status(quotation: Quotation) -> QuotationStatus:
    """Derive quotation status from linked order coverage."""
    current_status = QuotationStatus(quotation.status)
    if current_status in {QuotationStatus.LOST, QuotationStatus.CANCELLED}:
        return current_status

    order_count = int(getattr(quotation, "order_count", 0) or 0)
    ordered_amount = Decimal(
        str(getattr(quotation, "ordered_amount", Decimal("0.00")) or Decimal("0.00"))
    ).quantize(Decimal("0.01"))
    grand_total = Decimal(
        str(getattr(quotation, "grand_total", Decimal("0.00")) or Decimal("0.00"))
    ).quantize(Decimal("0.01"))

    if order_count > 0:
        if grand_total > 0 and ordered_amount >= grand_total:
            return QuotationStatus.ORDERED
        return QuotationStatus.PARTIALLY_ORDERED

    if current_status == QuotationStatus.EXPIRED:
        return current_status

    valid_till = getattr(quotation, "valid_till", None)
    if valid_till is not None and valid_till < date.today() and current_status in {
        QuotationStatus.DRAFT,
        QuotationStatus.OPEN,
        QuotationStatus.REPLIED,
        QuotationStatus.PARTIALLY_ORDERED,
        QuotationStatus.ORDERED,
    }:
        return QuotationStatus.EXPIRED

    if current_status in DERIVED_QUOTATION_STATUSES:
        return QuotationStatus.OPEN

    return current_status


async def _synchronize_quotation_status(
    session: AsyncSession,
    quotation: Quotation,
    tenant_id: uuid.UUID,
) -> Quotation:
    """Synchronize quotation status with linked order coverage."""
    derived = _derive_quotation_status(quotation)
    if derived != QuotationStatus(quotation.status):
        async with session.begin():
            await set_tenant(session, tenant_id)
            quotation.status = derived
            quotation.updated_at = datetime.now(tz=UTC)
    return quotation


# ---------------------------------------------------------------------------
# Public CRUD functions
# ---------------------------------------------------------------------------


async def create_quotation(
    session: AsyncSession,
    data: QuotationCreate,
    tenant_id: uuid.UUID | None = None,
) -> Quotation:
    """Create a new quotation."""
    tid = tenant_id or DEFAULT_TENANT_ID
    if not data.items:
        raise ValidationError(
            [{"field": "items", "message": "At least one quotation item is required."}]
        )
    territory = await _ensure_territory_supported(session, data.territory, tid)
    customer_group = await _ensure_customer_group_supported(session, data.customer_group, tid)
    valid_till = await _resolve_effective_quotation_valid_till(
        session,
        transaction_date=data.transaction_date,
        valid_till=data.valid_till,
        tenant_id=tid,
    )
    _ensure_quotation_validity(data.transaction_date, valid_till)
    _ensure_auto_repeat_metadata(data.auto_repeat_enabled, data.auto_repeat_frequency)

    serialized_items = _serialize_opportunity_items(data.items)
    subtotal = _resolve_total_amount(None, serialized_items) or Decimal("0.00")
    serialized_taxes = _serialize_quotation_taxes(data.taxes, subtotal)
    total_taxes = _resolve_serialized_decimal_sum(serialized_taxes, "tax_amount")
    grand_total = (subtotal + total_taxes).quantize(Decimal("0.01"))
    party_name, party_label, party_defaults = await _resolve_party_context(
        session,
        OpportunityPartyKind(data.quotation_to),
        data.party_name,
        tid,
    )

    quotation = _build_quotation_record(
        merged=data,
        tenant_id=tid,
        party_name=party_name,
        party_label=party_label,
        party_defaults=party_defaults,
        subtotal=subtotal,
        total_taxes=total_taxes,
        grand_total=grand_total,
        serialized_items=serialized_items,
        serialized_taxes=serialized_taxes,
        valid_till_override=valid_till,
        territory_override=territory,
        customer_group_override=customer_group,
    )

    async with session.begin():
        await set_tenant(session, tid)
        session.add(quotation)

    await session.refresh(quotation)
    if quotation.quotation_to == QuotationPartyKind.LEAD:
        try:
            lead_id = uuid.UUID(quotation.party_name)
        except ValueError:
            pass
        else:
            lead = await get_lead(session, lead_id, tenant_id=tid)
            if lead is not None:
                async with session.begin():
                    await set_tenant(session, tid)
                    lead.converted_quotation_id = quotation.id
                    lead.status = LeadStatus.QUOTATION
                    lead.updated_at = datetime.now(tz=UTC)
    return quotation


async def list_quotations(
    session: AsyncSession,
    params: QuotationListParams,
    tenant_id: uuid.UUID | None = None,
) -> tuple[list[Quotation], int]:
    """List quotations with pagination and filtering."""
    tid = tenant_id or DEFAULT_TENANT_ID
    base = select(Quotation).where(Quotation.tenant_id == tid)

    if params.q:
        escaped_q = params.q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        like_pattern = f"%{escaped_q}%"
        base = base.where(
            or_(
                Quotation.party_label.ilike(like_pattern, escape="\\"),
                Quotation.company.ilike(like_pattern, escape="\\"),
                Quotation.contact_person.ilike(like_pattern, escape="\\"),
                Quotation.contact_email.ilike(like_pattern, escape="\\"),
            )
        )

    if params.status:
        base = base.where(Quotation.status == params.status)

    count_stmt = select(func.count()).select_from(base.subquery())
    offset = (params.page - 1) * params.page_size
    items_stmt = (
        base.order_by(Quotation.updated_at.desc(), Quotation.valid_till.asc(), Quotation.id.asc())
        .offset(offset)
        .limit(params.page_size)
    )

    async with session.begin():
        await set_tenant(session, tid)
        total_result = await session.execute(count_stmt)
        total_count = total_result.scalar() or 0
        result = await session.execute(items_stmt)
        items = list(result.scalars().all())

    # Batch-sync quotation statuses to avoid N+1 queries
    quotations_needing_sync = [
        q for q in items
        if _derive_quotation_status(q) != QuotationStatus(q.status)
    ]
    if quotations_needing_sync:
        now = datetime.now(tz=UTC)
        async with session.begin():
            await set_tenant(session, tid)
            for quotation in quotations_needing_sync:
                derived = _derive_quotation_status(quotation)
                quotation.status = derived
                quotation.updated_at = now

    return items, total_count


async def get_quotation(
    session: AsyncSession,
    quotation_id: uuid.UUID,
    tenant_id: uuid.UUID | None = None,
) -> Quotation | None:
    """Get a single quotation by ID."""
    tid = tenant_id or DEFAULT_TENANT_ID
    async with session.begin():
        await set_tenant(session, tid)
        result = await session.execute(
            select(Quotation).where(
                Quotation.id == quotation_id,
                Quotation.tenant_id == tid,
            )
        )
        quotation = result.scalar_one_or_none()

    if quotation is None:
        return None
    quotation = await _synchronize_quotation_status(session, quotation, tid)
    if int(getattr(quotation, "order_count", 0) or 0) > 0:
        linked_rows = await _load_linked_order_rows(session, quotation.id, tid)
        _, _, linked_orders, remaining_items = _build_quotation_conversion_details(
            quotation,
            linked_rows,
        )
        quotation.linked_orders = linked_orders
        quotation.remaining_items = remaining_items
    else:
        quotation.linked_orders = []
        quotation.remaining_items = []
    return quotation


async def prepare_quotation_order_handoff(
    session: AsyncSession,
    quotation_id: uuid.UUID,
    tenant_id: uuid.UUID | None = None,
) -> QuotationOrderHandoff:
    """Prepare handoff data for creating order from quotation."""
    tid = tenant_id or DEFAULT_TENANT_ID
    quotation = await get_quotation(session, quotation_id, tenant_id=tid)
    if quotation is None:
        raise ValidationError([{"field": "quotation_id", "message": "Quotation not found."}])

    _ensure_order_handoff_allowed(QuotationStatus(quotation.status))
    if not quotation.items:
        raise ValidationError(
            [{"field": "items", "message": "At least one quotation item is required for order conversion."}]
        )

    customer_id = await _resolve_quotation_order_customer_id(session, quotation, tid)
    lines = await _build_quotation_order_handoff_lines(session, quotation.items, tid)

    return QuotationOrderHandoff(
        quotation_id=quotation.id,
        source_quotation_id=quotation.id,
        customer_id=customer_id,
        crm_context_snapshot=_build_quotation_crm_context_snapshot(quotation),
        notes=quotation.notes,
        lines=lines,
    )


async def update_quotation(
    session: AsyncSession,
    quotation_id: uuid.UUID,
    data: QuotationUpdate,
    tenant_id: uuid.UUID | None = None,
) -> Quotation | None:
    """Update an existing quotation."""
    tid = tenant_id or DEFAULT_TENANT_ID
    quotation = await get_quotation(session, quotation_id, tenant_id=tid)
    if quotation is None:
        return None
    if quotation.version != data.version:
        raise VersionConflictError(expected=data.version, actual=quotation.version)

    merged = _build_quotation_merged(data, quotation)
    _ensure_quotation_validity(merged.transaction_date, merged.valid_till)
    _ensure_auto_repeat_metadata(merged.auto_repeat_enabled, merged.auto_repeat_frequency)
    serialized_items = _serialize_opportunity_items(merged.items)
    if not serialized_items:
        raise ValidationError(
            [{"field": "items", "message": "At least one quotation item is required."}]
        )
    subtotal = _resolve_total_amount(None, serialized_items) or Decimal("0.00")
    serialized_taxes = _serialize_quotation_taxes(merged.taxes, subtotal)
    total_taxes = _resolve_serialized_decimal_sum(serialized_taxes, "tax_amount")
    grand_total = (subtotal + total_taxes).quantize(Decimal("0.01"))

    if _should_resolve_party(merged, quotation):
        party_name, party_label, party_defaults = await _resolve_party_context(
            session,
            OpportunityPartyKind(merged.quotation_to),
            merged.party_name,
            tid,
        )
    else:
        party_name = quotation.party_name
        party_label = quotation.party_label
        party_defaults: dict[str, str] = {}

    async with session.begin():
        await set_tenant(session, tid)
        _apply_quotation_fields_to_record(quotation, merged, party_name, party_label, party_defaults)
        quotation.subtotal = subtotal
        quotation.total_taxes = total_taxes
        quotation.grand_total = grand_total
        quotation.base_grand_total = grand_total
        quotation.items = serialized_items
        quotation.taxes = serialized_taxes
    return await _synchronize_quotation_status(session, quotation, tid)


async def transition_quotation_status(
    session: AsyncSession,
    quotation_id: uuid.UUID,
    data: QuotationTransition,
    tenant_id: uuid.UUID | None = None,
) -> Quotation | None:
    """Transition quotation status."""
    tid = tenant_id or DEFAULT_TENANT_ID
    quotation = await get_quotation(session, quotation_id, tenant_id=tid)
    if quotation is None:
        return None

    current_status = QuotationStatus(quotation.status)
    _ensure_quotation_transition_allowed(current_status, data.status)
    _ensure_quotation_lost_context(data)

    async with session.begin():
        await set_tenant(session, tid)
        quotation.status = data.status
        if data.status == QuotationStatus.LOST:
            quotation.lost_reason = data.lost_reason.strip()
            quotation.competitor_name = data.competitor_name.strip()
            quotation.loss_notes = data.loss_notes.strip()
        quotation.updated_at = datetime.now(tz=UTC)
    return quotation


async def create_quotation_revision(
    session: AsyncSession,
    quotation_id: uuid.UUID,
    data: QuotationRevisionCreate,
    tenant_id: uuid.UUID | None = None,
) -> Quotation | None:
    """Create a revision of an existing quotation."""
    tid = tenant_id or DEFAULT_TENANT_ID
    quotation = await get_quotation(session, quotation_id, tenant_id=tid)
    if quotation is None:
        return None

    merged = _build_quotation_merged(data, quotation)

    if _should_resolve_party(merged, quotation):
        party_name, party_label, party_defaults = await _resolve_party_context(
            session,
            OpportunityPartyKind(merged.quotation_to),
            merged.party_name,
            tid,
        )
    else:
        party_name = quotation.party_name
        party_label = quotation.party_label
        party_defaults: dict[str, str] = {}

    _ensure_quotation_validity(merged.transaction_date, merged.valid_till)
    _ensure_auto_repeat_metadata(merged.auto_repeat_enabled, merged.auto_repeat_frequency)
    serialized_items = _serialize_opportunity_items(merged.items)
    if not serialized_items:
        raise ValidationError(
            [{"field": "items", "message": "At least one quotation item is required."}]
        )
    subtotal = _resolve_total_amount(None, serialized_items) or Decimal("0.00")
    serialized_taxes = _serialize_quotation_taxes(merged.taxes, subtotal)
    total_taxes = _resolve_serialized_decimal_sum(serialized_taxes, "tax_amount")
    grand_total = (subtotal + total_taxes).quantize(Decimal("0.01"))

    revised = _build_quotation_record(
        merged=merged,
        tenant_id=tid,
        party_name=party_name,
        party_label=party_label,
        party_defaults=party_defaults,
        subtotal=subtotal,
        total_taxes=total_taxes,
        grand_total=grand_total,
        serialized_items=serialized_items,
        serialized_taxes=serialized_taxes,
        amended_from=quotation.id,
        revision_no=quotation.revision_no + 1,
    )

    async with session.begin():
        await set_tenant(session, tid)
        session.add(revised)

    await session.refresh(revised)
    return revised


# ---------------------------------------------------------------------------
# Order coverage sync
# ---------------------------------------------------------------------------


async def sync_quotation_order_coverage_in_transaction(
    session: AsyncSession,
    quotation: Quotation,
    tenant_id: uuid.UUID,
) -> Quotation:
    """Sync quotation with linked order coverage within a transaction."""
    linked_rows = await _load_linked_order_rows(session, quotation.id, tenant_id)
    ordered_amount, order_count, _, _ = _build_quotation_conversion_details(quotation, linked_rows)
    quotation.ordered_amount = ordered_amount
    quotation.order_count = order_count
    quotation.status = _derive_quotation_status(quotation).value
    quotation.updated_at = datetime.now(tz=UTC)
    return quotation


async def sync_quotation_order_coverage(
    session: AsyncSession,
    quotation_id: uuid.UUID,
    tenant_id: uuid.UUID | None = None,
) -> Quotation | None:
    """Sync quotation with linked order coverage."""
    tid = tenant_id or DEFAULT_TENANT_ID
    async with session.begin():
        await set_tenant(session, tid)
        result = await session.execute(
            select(Quotation).where(
                Quotation.id == quotation_id,
                Quotation.tenant_id == tid,
            )
        )
        quotation = result.scalar_one_or_none()
        if quotation is None:
            return None
        return await sync_quotation_order_coverage_in_transaction(session, quotation, tid)
