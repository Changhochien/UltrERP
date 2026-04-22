"""CRM service layer."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

import domains.crm._pipeline as crm_pipeline
import domains.crm._setup as crm_setup
from common.errors import DuplicateLeadConflictError, ValidationError, VersionConflictError
from common.models.order import Order
from common.models.order_line import OrderLine
from common.tenant import DEFAULT_TENANT_ID, set_tenant
from domains.crm.models import (
    Lead,
    Opportunity,
    Quotation,
)
from domains.crm.schemas import (
    CRMDuplicatePolicy,
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
    QuotationCreate,
    QuotationItemInput,
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
from domains.customers.models import Customer
from domains.customers.schemas import CustomerCreate
from domains.customers.service import create_customer

get_crm_pipeline_report = crm_pipeline.get_crm_pipeline_report
get_crm_settings = crm_setup.get_crm_settings
update_crm_settings = crm_setup.update_crm_settings
_resolve_effective_quotation_valid_till = crm_setup._resolve_effective_quotation_valid_till
_ensure_sales_stage_supported = crm_setup._ensure_sales_stage_supported
_ensure_territory_supported = crm_setup._ensure_territory_supported
_ensure_customer_group_supported = crm_setup._ensure_customer_group_supported
list_sales_stages = crm_setup.list_sales_stages
list_territories = crm_setup.list_territories
list_customer_groups = crm_setup.list_customer_groups
get_crm_setup_bundle = crm_setup.get_crm_setup_bundle
create_sales_stage = crm_setup.create_sales_stage
update_sales_stage = crm_setup.update_sales_stage
create_territory = crm_setup.create_territory
update_territory = crm_setup.update_territory
create_customer_group = crm_setup.create_customer_group
update_customer_group = crm_setup.update_customer_group


@dataclass(frozen=True, slots=True)
class _LeadDuplicateLookup:
    company_name: str
    email_id: str
    phone: str
    mobile_no: str


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

DERIVED_QUOTATION_STATUSES = frozenset(
    {
        QuotationStatus.PARTIALLY_ORDERED,
        QuotationStatus.ORDERED,
        QuotationStatus.EXPIRED,
    }
)

ALLOWED_QUOTATION_TRANSITIONS: dict[QuotationStatus, frozenset[QuotationStatus]] = {
    QuotationStatus.DRAFT: frozenset({QuotationStatus.OPEN, QuotationStatus.CANCELLED}),
    QuotationStatus.OPEN: frozenset(
        {QuotationStatus.REPLIED, QuotationStatus.LOST, QuotationStatus.CANCELLED}
    ),
    QuotationStatus.REPLIED: frozenset(
        {QuotationStatus.OPEN, QuotationStatus.LOST, QuotationStatus.CANCELLED}
    ),
    QuotationStatus.EXPIRED: frozenset(
        {QuotationStatus.OPEN, QuotationStatus.LOST, QuotationStatus.CANCELLED}
    ),
    QuotationStatus.PARTIALLY_ORDERED: frozenset(),
    QuotationStatus.ORDERED: frozenset(),
    QuotationStatus.LOST: frozenset(),
    QuotationStatus.CANCELLED: frozenset(),
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
                    "message": (
                        f"Cannot transition from '{current_status.value}' "
                        f"to '{target_status.value}'."
                    ),
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
                    "message": (
                        f"Cannot transition from '{current_status.value}' "
                        f"to '{target_status.value}'."
                    ),
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
                    "message": (
                        "Only open or active opportunities can be prepared "
                        "for quotation handoff."
                    ),
                }
            ]
        )


def _ensure_order_handoff_allowed(current_status: QuotationStatus) -> None:
    if current_status in {
        QuotationStatus.DRAFT,
        QuotationStatus.LOST,
        QuotationStatus.CANCELLED,
        QuotationStatus.EXPIRED,
    }:
        raise ValidationError(
            [
                {
                    "field": "status",
                    "message": "Only active quotations can be prepared for order conversion.",
                }
            ]
        )


def _ensure_quotation_transition_allowed(
    current_status: QuotationStatus,
    target_status: QuotationStatus,
) -> None:
    if target_status in DERIVED_QUOTATION_STATUSES:
        raise ValidationError(
            [
                {
                    "field": "status",
                    "message": (
                        f"Quotation status '{target_status.value}' is derived "
                        "from expiry or downstream order coverage."
                    ),
                }
            ]
        )
    if target_status not in ALLOWED_QUOTATION_TRANSITIONS.get(current_status, frozenset()):
        raise ValidationError(
            [
                {
                    "field": "status",
                    "message": (
                        f"Cannot transition from '{current_status.value}' "
                        f"to '{target_status.value}'."
                    ),
                }
            ]
        )


def _ensure_quotation_lost_context(data: QuotationTransition) -> None:
    if data.status == QuotationStatus.LOST and not data.lost_reason.strip():
        raise ValidationError(
            [
                {
                    "field": "lost_reason",
                    "message": "Lost quotations require a lost reason.",
                }
            ]
        )


def _ensure_quotation_validity(transaction_date: date, valid_till: date) -> None:
    if valid_till < transaction_date:
        raise ValidationError(
            [
                {
                    "field": "valid_till",
                    "message": "Valid till date cannot be earlier than the transaction date.",
                }
            ]
        )


def _ensure_auto_repeat_metadata(enabled: bool, frequency: str) -> None:
    if enabled and not frequency.strip():
        raise ValidationError(
            [
                {
                    "field": "auto_repeat_frequency",
                    "message": "Auto repeat frequency is required when auto repeat is enabled.",
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
    """Return the field name that caused the first match for duplicate detection."""
    # Use getattr to handle both Lead (with normalized_* fields) and Customer models
    normalized_company = _normalize_company_name(data.company_name)
    candidate_company_normalized = getattr(candidate, "normalized_company_name", None)
    if candidate_company_normalized is None:
        # Customer model doesn't have normalized_company_name, normalize on access
        candidate_company_normalized = _normalize_company_name(
            getattr(candidate, "company_name", "")
        )
    if normalized_company and candidate_company_normalized == normalized_company:
        return "company_name"

    normalized_email = _normalize_email(data.email_id)
    candidate_email_normalized = getattr(candidate, "normalized_email_id", None)
    if candidate_email_normalized is None:
        # Customer model uses contact_email
        candidate_email_normalized = _normalize_email(getattr(candidate, "contact_email", ""))
    if normalized_email and candidate_email_normalized == normalized_email:
        return "email_id"

    return "phone"


def _candidate_label(candidate: Lead | Customer) -> str:
    """Return a human-readable label for a duplicate candidate."""
    if isinstance(candidate, Lead):
        return candidate.lead_name
    return candidate.company_name


def _trim(value: str | None) -> str:
    return value.strip() if value else ""


def _serialize_opportunity_items(
    items: list[OpportunityItemInput],
) -> list[dict[str, object]]:
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


def _deserialize_opportunity_items(
    items: list[dict[str, object]],
) -> list[OpportunityItemInput]:
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


def _serialize_quotation_items(items: list[QuotationItemInput]) -> list[dict[str, object]]:
    return _serialize_opportunity_items(items)


def _deserialize_quotation_items(
    items: list[dict[str, object]],
) -> list[QuotationItemInput]:
    return [QuotationItemInput.model_validate(item) for item in items]


def _serialize_quotation_taxes(
    taxes: list[QuotationTaxInput],
    subtotal: Decimal,
) -> list[dict[str, object]]:
    serialized: list[dict[str, object]] = []
    for line_no, tax in enumerate(taxes, start=1):
        rate = tax.rate.quantize(Decimal("0.01"))
        tax_amount = (
            tax.tax_amount
            if tax.tax_amount is not None
            else (subtotal * rate / Decimal("100.00"))
        ).quantize(Decimal("0.01"))
        serialized.append(
            {
                "line_no": line_no,
                "description": tax.description.strip(),
                "rate": f"{rate:.2f}",
                "tax_amount": f"{tax_amount:.2f}",
            }
        )
    return serialized


def _deserialize_quotation_taxes(items: list[dict[str, object]]) -> list[QuotationTaxInput]:
    return [QuotationTaxInput.model_validate(item) for item in items]


def _build_quotation_crm_context_snapshot(
    quotation: Quotation,
) -> dict[str, object]:
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
                    [
                        {
                            "field": "items",
                            "message": (
                                "Quotation item product mapping is invalid "
                                "for order conversion."
                            ),
                        }
                    ]
                ) from exc

        if product_id is None:
            item_code = str(item.get("item_code") or "").strip()
            product_id = product_ids_by_code.get(item_code)

        if product_id is None:
            raise ValidationError(
                [
                    {
                        "field": "items",
                        "message": (
                            "Resolve quotation items to catalog products "
                            "before order conversion."
                        ),
                    }
                ]
            )

        description = str(item.get("description") or item.get("item_name") or "").strip()
        if not description:
            raise ValidationError(
                [
                    {
                        "field": "items",
                        "message": "Quotation items require a description before order conversion.",
                    }
                ]
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
    quotation_to = QuotationPartyKind(quotation.quotation_to)
    if quotation_to == QuotationPartyKind.CUSTOMER:
        try:
            return uuid.UUID(quotation.party_name)
        except ValueError as exc:
            raise ValidationError(
                [
                    {
                        "field": "party_name",
                        "message": "Quotation customer context is invalid for order conversion.",
                    }
                ]
            ) from exc

    if quotation_to == QuotationPartyKind.LEAD:
        try:
            lead_id = uuid.UUID(quotation.party_name)
        except ValueError as exc:
            raise ValidationError(
                [
                    {
                        "field": "party_name",
                        "message": "Quotation lead context is invalid for order conversion.",
                    }
                ]
            ) from exc

        lead = await get_lead(session, lead_id, tenant_id=tenant_id)
        if lead is not None and lead.converted_customer_id is not None:
            return lead.converted_customer_id

    raise ValidationError(
        [
            {
                "field": "party_name",
                "message": (
                    "Resolve this quotation to an existing customer "
                    "before order conversion."
                ),
            }
        ]
    )


def _resolve_serialized_decimal_sum(
    items: list[dict[str, object]],
    field_name: str,
) -> Decimal:
    return sum(
        (Decimal(str(item[field_name])) for item in items),
        start=Decimal("0.00"),
    ).quantize(Decimal("0.01"))


def _line_amount_from_item(item: dict[str, object]) -> Decimal:
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
        quoted_quantity = Decimal(
            str(item.get("quantity") or "0")
        ).quantize(quantity_quant)
        ordered_quantity = min(
            ordered_quantities.get(line_no, Decimal("0.000")).quantize(quantity_quant),
            quoted_quantity,
        )
        remaining_quantity = max(
            quoted_quantity - ordered_quantity,
            Decimal("0.000"),
        ).quantize(quantity_quant)

        quoted_amount = _line_amount_from_item(item)
        ordered_line_amount = Decimal("0.00")
        if quoted_quantity > 0:
            ordered_line_amount = (
                quoted_amount * (ordered_quantity / quoted_quantity)
            ).quantize(Decimal("0.01"))
        remaining_amount = max(
            quoted_amount - ordered_line_amount,
            Decimal("0.00"),
        ).quantize(Decimal("0.01"))
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


async def sync_quotation_order_coverage_in_transaction(
    session: AsyncSession,
    quotation: Quotation,
    tenant_id: uuid.UUID,
) -> Quotation:
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


def _derive_quotation_status(quotation: Quotation) -> QuotationStatus:
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
    derived_status = _derive_quotation_status(quotation)
    if derived_status == QuotationStatus(quotation.status):
        return quotation

    async with session.begin():
        await set_tenant(session, tenant_id)
        quotation.status = derived_status
        quotation.updated_at = datetime.now(tz=UTC)
    return quotation


def _resolve_total_amount(
    explicit_amount: Decimal | None,
    serialized_items: list[dict[str, object]],
) -> Decimal | None:
    if explicit_amount is not None:
        return explicit_amount.quantize(Decimal("0.01"))
    if not serialized_items:
        return None
    return sum(
        (Decimal(str(item["amount"])) for item in serialized_items),
        start=Decimal("0.00"),
    ).quantize(Decimal("0.01"))


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
                    "message": (
                        f"{opportunity_from.value.capitalize()} party links "
                        "must use a valid record id."
                    ),
                }
            ]
        ) from exc

    async with session.begin():
        await set_tenant(session, tenant_id)
        if opportunity_from == OpportunityPartyKind.LEAD:
            result = await session.execute(
                select(Lead).where(
                    Lead.id == party_id,
                    Lead.tenant_id == tenant_id,
                )
            )
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

        result = await session.execute(
            select(Customer).where(
                Customer.id == party_id,
                Customer.tenant_id == tenant_id,
            )
        )
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
            [
                {
                    "field": "qualification_status",
                    "message": "Lead must be qualified before customer conversion.",
                }
            ]
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
        party_name=(
            data.party_name
            if "party_name" in fields and data.party_name is not None
            else opportunity.party_name
        ),
        sales_stage=(
            data.sales_stage
            if "sales_stage" in fields and data.sales_stage is not None
            else opportunity.sales_stage
        ),
        probability=(
            data.probability
            if "probability" in fields and data.probability is not None
            else opportunity.probability
        ),
        expected_closing=(
            data.expected_closing
            if "expected_closing" in fields
            else opportunity.expected_closing
        ),
        currency=(
            data.currency
            if "currency" in fields and data.currency is not None
            else opportunity.currency
        ),
        opportunity_amount=(
            data.opportunity_amount
            if "opportunity_amount" in fields
            else opportunity.opportunity_amount
        ),
        opportunity_owner=(
            data.opportunity_owner
            if "opportunity_owner" in fields and data.opportunity_owner is not None
            else opportunity.opportunity_owner
        ),
        territory=(
            data.territory
            if "territory" in fields and data.territory is not None
            else opportunity.territory
        ),
        customer_group=(
            data.customer_group
            if "customer_group" in fields and data.customer_group is not None
            else opportunity.customer_group
        ),
        contact_person=(
            data.contact_person
            if "contact_person" in fields and data.contact_person is not None
            else opportunity.contact_person
        ),
        contact_email=(
            data.contact_email
            if "contact_email" in fields and data.contact_email is not None
            else opportunity.contact_email
        ),
        contact_mobile=(
            data.contact_mobile
            if "contact_mobile" in fields and data.contact_mobile is not None
            else opportunity.contact_mobile
        ),
        job_title=(
            data.job_title
            if "job_title" in fields and data.job_title is not None
            else opportunity.job_title
        ),
        utm_source=(
            data.utm_source
            if "utm_source" in fields and data.utm_source is not None
            else opportunity.utm_source
        ),
        utm_medium=(
            data.utm_medium
            if "utm_medium" in fields and data.utm_medium is not None
            else opportunity.utm_medium
        ),
        utm_campaign=(
            data.utm_campaign
            if "utm_campaign" in fields and data.utm_campaign is not None
            else opportunity.utm_campaign
        ),
        utm_content=(
            data.utm_content
            if "utm_content" in fields and data.utm_content is not None
            else opportunity.utm_content
        ),
        items=(
            data.items
            if "items" in fields and data.items is not None
            else _deserialize_opportunity_items(opportunity.items)
        ),
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
        opportunity.territory = (
            _trim(merged.territory) or party_defaults.get("territory", "")
        )
        opportunity.customer_group = _trim(merged.customer_group)
        opportunity.contact_person = (
            _trim(merged.contact_person)
            or party_defaults.get("contact_person", "")
        )
        opportunity.contact_email = (
            _trim(merged.contact_email)
            or party_defaults.get("contact_email", "")
        )
        opportunity.contact_mobile = (
            _trim(merged.contact_mobile)
            or party_defaults.get("contact_mobile", "")
        )
        opportunity.job_title = _trim(merged.job_title)
        opportunity.utm_source = (
            _trim(merged.utm_source) or party_defaults.get("utm_source", "")
        )
        opportunity.utm_medium = (
            _trim(merged.utm_medium) or party_defaults.get("utm_medium", "")
        )
        opportunity.utm_campaign = (
            _trim(merged.utm_campaign)
            or party_defaults.get("utm_campaign", "")
        )
        opportunity.utm_content = (
            _trim(merged.utm_content)
            or party_defaults.get("utm_content", "")
        )
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
            [
                {
                    "field": "items",
                    "message": "At least one opportunity item is required for quotation handoff.",
                }
            ]
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


async def create_quotation(
    session: AsyncSession,
    data: QuotationCreate,
    tenant_id: uuid.UUID | None = None,
) -> Quotation:
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

    serialized_items = _serialize_quotation_items(data.items)
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

    quotation = Quotation(
        tenant_id=tid,
        quotation_to=data.quotation_to,
        party_name=party_name,
        party_label=party_label,
        status=QuotationStatus.DRAFT,
        transaction_date=data.transaction_date,
        valid_till=valid_till,
        company=data.company.strip(),
        currency=data.currency.strip().upper(),
        subtotal=subtotal,
        total_taxes=total_taxes,
        grand_total=grand_total,
        base_grand_total=grand_total,
        ordered_amount=Decimal("0.00"),
        order_count=0,
        contact_person=_trim(data.contact_person) or party_defaults.get("contact_person", ""),
        contact_email=_trim(data.contact_email) or party_defaults.get("contact_email", ""),
        contact_mobile=_trim(data.contact_mobile) or party_defaults.get("contact_mobile", ""),
        job_title=_trim(data.job_title),
        territory=territory or party_defaults.get("territory", ""),
        customer_group=customer_group,
        billing_address=_trim(data.billing_address),
        shipping_address=_trim(data.shipping_address),
        utm_source=_trim(data.utm_source) or party_defaults.get("utm_source", ""),
        utm_medium=_trim(data.utm_medium) or party_defaults.get("utm_medium", ""),
        utm_campaign=_trim(data.utm_campaign) or party_defaults.get("utm_campaign", ""),
        utm_content=_trim(data.utm_content) or party_defaults.get("utm_content", ""),
        items=serialized_items,
        taxes=serialized_taxes,
        terms_template=_trim(data.terms_template),
        terms_and_conditions=_trim(data.terms_and_conditions),
        opportunity_id=data.opportunity_id,
        auto_repeat_enabled=data.auto_repeat_enabled,
        auto_repeat_frequency=_trim(data.auto_repeat_frequency),
        auto_repeat_until=data.auto_repeat_until,
        notes=_trim(data.notes),
    )

    async with session.begin():
        await set_tenant(session, tid)
        session.add(quotation)

    await session.refresh(quotation)
    return quotation


async def list_quotations(
    session: AsyncSession,
    params: QuotationListParams,
    tenant_id: uuid.UUID | None = None,
) -> tuple[list[Quotation], int]:
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

    for quotation in items:
        await _synchronize_quotation_status(session, quotation, tid)

    return items, total_count


async def get_quotation(
    session: AsyncSession,
    quotation_id: uuid.UUID,
    tenant_id: uuid.UUID | None = None,
) -> Quotation | None:
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
    tid = tenant_id or DEFAULT_TENANT_ID
    quotation = await get_quotation(session, quotation_id, tenant_id=tid)
    if quotation is None:
        raise ValidationError([{"field": "quotation_id", "message": "Quotation not found."}])

    _ensure_order_handoff_allowed(QuotationStatus(quotation.status))
    if not quotation.items:
        raise ValidationError(
            [
                {
                    "field": "items",
                    "message": "At least one quotation item is required for order conversion.",
                }
            ]
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
    tid = tenant_id or DEFAULT_TENANT_ID
    quotation = await get_quotation(session, quotation_id, tenant_id=tid)
    if quotation is None:
        return None
    if quotation.version != data.version:
        raise VersionConflictError(expected=data.version, actual=quotation.version)

    fields = data.model_fields_set - {"version"}
    merged = QuotationCreate(
        quotation_to=(
            data.quotation_to
            if "quotation_to" in fields and data.quotation_to is not None
            else QuotationPartyKind(quotation.quotation_to)
        ),
        party_name=(
            data.party_name
            if "party_name" in fields and data.party_name is not None
            else quotation.party_name
        ),
        transaction_date=(
            data.transaction_date
            if "transaction_date" in fields and data.transaction_date is not None
            else quotation.transaction_date
        ),
        valid_till=(
            data.valid_till
            if "valid_till" in fields and data.valid_till is not None
            else quotation.valid_till
        ),
        company=(
            data.company
            if "company" in fields and data.company is not None
            else quotation.company
        ),
        currency=(
            data.currency
            if "currency" in fields and data.currency is not None
            else quotation.currency
        ),
        contact_person=(
            data.contact_person
            if "contact_person" in fields and data.contact_person is not None
            else quotation.contact_person
        ),
        contact_email=(
            data.contact_email
            if "contact_email" in fields and data.contact_email is not None
            else quotation.contact_email
        ),
        contact_mobile=(
            data.contact_mobile
            if "contact_mobile" in fields and data.contact_mobile is not None
            else quotation.contact_mobile
        ),
        job_title=(
            data.job_title
            if "job_title" in fields and data.job_title is not None
            else quotation.job_title
        ),
        territory=(
            data.territory
            if "territory" in fields and data.territory is not None
            else quotation.territory
        ),
        customer_group=(
            data.customer_group
            if "customer_group" in fields and data.customer_group is not None
            else quotation.customer_group
        ),
        billing_address=(
            data.billing_address
            if "billing_address" in fields and data.billing_address is not None
            else quotation.billing_address
        ),
        shipping_address=(
            data.shipping_address
            if "shipping_address" in fields and data.shipping_address is not None
            else quotation.shipping_address
        ),
        utm_source=(
            data.utm_source
            if "utm_source" in fields and data.utm_source is not None
            else quotation.utm_source
        ),
        utm_medium=(
            data.utm_medium
            if "utm_medium" in fields and data.utm_medium is not None
            else quotation.utm_medium
        ),
        utm_campaign=(
            data.utm_campaign
            if "utm_campaign" in fields and data.utm_campaign is not None
            else quotation.utm_campaign
        ),
        utm_content=(
            data.utm_content
            if "utm_content" in fields and data.utm_content is not None
            else quotation.utm_content
        ),
        opportunity_id=(
            data.opportunity_id
            if "opportunity_id" in fields
            else quotation.opportunity_id
        ),
        items=(
            data.items
            if "items" in fields and data.items is not None
            else _deserialize_quotation_items(quotation.items)
        ),
        taxes=(
            data.taxes
            if "taxes" in fields and data.taxes is not None
            else _deserialize_quotation_taxes(quotation.taxes)
        ),
        terms_template=(
            data.terms_template
            if "terms_template" in fields and data.terms_template is not None
            else quotation.terms_template
        ),
        terms_and_conditions=(
            data.terms_and_conditions
            if "terms_and_conditions" in fields and data.terms_and_conditions is not None
            else quotation.terms_and_conditions
        ),
        auto_repeat_enabled=(
            data.auto_repeat_enabled
            if "auto_repeat_enabled" in fields and data.auto_repeat_enabled is not None
            else quotation.auto_repeat_enabled
        ),
        auto_repeat_frequency=(
            data.auto_repeat_frequency
            if "auto_repeat_frequency" in fields and data.auto_repeat_frequency is not None
            else quotation.auto_repeat_frequency
        ),
        auto_repeat_until=(
            data.auto_repeat_until
            if "auto_repeat_until" in fields
            else quotation.auto_repeat_until
        ),
        notes=(data.notes if "notes" in fields and data.notes is not None else quotation.notes),
    )

    _ensure_quotation_validity(merged.transaction_date, merged.valid_till)
    _ensure_auto_repeat_metadata(merged.auto_repeat_enabled, merged.auto_repeat_frequency)
    serialized_items = _serialize_quotation_items(merged.items)
    if not serialized_items:
        raise ValidationError(
            [{"field": "items", "message": "At least one quotation item is required."}]
        )
    subtotal = _resolve_total_amount(None, serialized_items) or Decimal("0.00")
    serialized_taxes = _serialize_quotation_taxes(merged.taxes, subtotal)
    total_taxes = _resolve_serialized_decimal_sum(serialized_taxes, "tax_amount")
    grand_total = (subtotal + total_taxes).quantize(Decimal("0.01"))
    if merged.quotation_to == quotation.quotation_to and merged.party_name == quotation.party_name:
        party_name = quotation.party_name
        party_label = quotation.party_label
        party_defaults: dict[str, str] = {}
    else:
        party_name, party_label, party_defaults = await _resolve_party_context(
            session,
            OpportunityPartyKind(merged.quotation_to),
            merged.party_name,
            tid,
        )

    async with session.begin():
        await set_tenant(session, tid)
        quotation.quotation_to = merged.quotation_to
        quotation.party_name = party_name
        quotation.party_label = party_label
        quotation.transaction_date = merged.transaction_date
        quotation.valid_till = merged.valid_till
        quotation.company = merged.company.strip()
        quotation.currency = merged.currency.strip().upper()
        quotation.subtotal = subtotal
        quotation.total_taxes = total_taxes
        quotation.grand_total = grand_total
        quotation.base_grand_total = grand_total
        quotation.contact_person = (
            _trim(merged.contact_person)
            or party_defaults.get("contact_person", "")
        )
        quotation.contact_email = (
            _trim(merged.contact_email)
            or party_defaults.get("contact_email", "")
        )
        quotation.contact_mobile = (
            _trim(merged.contact_mobile)
            or party_defaults.get("contact_mobile", "")
        )
        quotation.job_title = _trim(merged.job_title)
        quotation.territory = (
            _trim(merged.territory) or party_defaults.get("territory", "")
        )
        quotation.customer_group = _trim(merged.customer_group)
        quotation.billing_address = _trim(merged.billing_address)
        quotation.shipping_address = _trim(merged.shipping_address)
        quotation.utm_source = (
            _trim(merged.utm_source) or party_defaults.get("utm_source", "")
        )
        quotation.utm_medium = (
            _trim(merged.utm_medium) or party_defaults.get("utm_medium", "")
        )
        quotation.utm_campaign = (
            _trim(merged.utm_campaign)
            or party_defaults.get("utm_campaign", "")
        )
        quotation.utm_content = (
            _trim(merged.utm_content)
            or party_defaults.get("utm_content", "")
        )
        quotation.items = serialized_items
        quotation.taxes = serialized_taxes
        quotation.terms_template = _trim(merged.terms_template)
        quotation.terms_and_conditions = _trim(merged.terms_and_conditions)
        quotation.opportunity_id = merged.opportunity_id
        quotation.auto_repeat_enabled = merged.auto_repeat_enabled
        quotation.auto_repeat_frequency = _trim(merged.auto_repeat_frequency)
        quotation.auto_repeat_until = merged.auto_repeat_until
        quotation.notes = _trim(merged.notes)
        quotation.version += 1
        quotation.updated_at = datetime.now(tz=UTC)
    return await _synchronize_quotation_status(session, quotation, tid)


async def transition_quotation_status(
    session: AsyncSession,
    quotation_id: uuid.UUID,
    data: QuotationTransition,
    tenant_id: uuid.UUID | None = None,
) -> Quotation | None:
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
    tid = tenant_id or DEFAULT_TENANT_ID
    quotation = await get_quotation(session, quotation_id, tenant_id=tid)
    if quotation is None:
        return None

    fields = data.model_fields_set
    merged = QuotationCreate(
        quotation_to=(
            data.quotation_to
            if "quotation_to" in fields and data.quotation_to is not None
            else QuotationPartyKind(quotation.quotation_to)
        ),
        party_name=(
            data.party_name
            if "party_name" in fields and data.party_name is not None
            else quotation.party_name
        ),
        transaction_date=(
            data.transaction_date
            if "transaction_date" in fields and data.transaction_date is not None
            else quotation.transaction_date
        ),
        valid_till=(
            data.valid_till
            if "valid_till" in fields and data.valid_till is not None
            else quotation.valid_till
        ),
        company=(
            data.company
            if "company" in fields and data.company is not None
            else quotation.company
        ),
        currency=(
            data.currency
            if "currency" in fields and data.currency is not None
            else quotation.currency
        ),
        contact_person=(
            data.contact_person
            if "contact_person" in fields and data.contact_person is not None
            else quotation.contact_person
        ),
        contact_email=(
            data.contact_email
            if "contact_email" in fields and data.contact_email is not None
            else quotation.contact_email
        ),
        contact_mobile=(
            data.contact_mobile
            if "contact_mobile" in fields and data.contact_mobile is not None
            else quotation.contact_mobile
        ),
        job_title=(
            data.job_title
            if "job_title" in fields and data.job_title is not None
            else quotation.job_title
        ),
        territory=(
            data.territory
            if "territory" in fields and data.territory is not None
            else quotation.territory
        ),
        customer_group=(
            data.customer_group
            if "customer_group" in fields and data.customer_group is not None
            else quotation.customer_group
        ),
        billing_address=(
            data.billing_address
            if "billing_address" in fields and data.billing_address is not None
            else quotation.billing_address
        ),
        shipping_address=(
            data.shipping_address
            if "shipping_address" in fields and data.shipping_address is not None
            else quotation.shipping_address
        ),
        utm_source=(
            data.utm_source
            if "utm_source" in fields and data.utm_source is not None
            else quotation.utm_source
        ),
        utm_medium=(
            data.utm_medium
            if "utm_medium" in fields and data.utm_medium is not None
            else quotation.utm_medium
        ),
        utm_campaign=(
            data.utm_campaign
            if "utm_campaign" in fields and data.utm_campaign is not None
            else quotation.utm_campaign
        ),
        utm_content=(
            data.utm_content
            if "utm_content" in fields and data.utm_content is not None
            else quotation.utm_content
        ),
        opportunity_id=(
            data.opportunity_id
            if "opportunity_id" in fields
            else quotation.opportunity_id
        ),
        items=(
            data.items
            if "items" in fields and data.items is not None
            else _deserialize_quotation_items(quotation.items)
        ),
        taxes=(
            data.taxes
            if "taxes" in fields and data.taxes is not None
            else _deserialize_quotation_taxes(quotation.taxes)
        ),
        terms_template=(
            data.terms_template
            if "terms_template" in fields and data.terms_template is not None
            else quotation.terms_template
        ),
        terms_and_conditions=(
            data.terms_and_conditions
            if "terms_and_conditions" in fields and data.terms_and_conditions is not None
            else quotation.terms_and_conditions
        ),
        auto_repeat_enabled=(
            data.auto_repeat_enabled
            if "auto_repeat_enabled" in fields and data.auto_repeat_enabled is not None
            else quotation.auto_repeat_enabled
        ),
        auto_repeat_frequency=(
            data.auto_repeat_frequency
            if "auto_repeat_frequency" in fields and data.auto_repeat_frequency is not None
            else quotation.auto_repeat_frequency
        ),
        auto_repeat_until=(
            data.auto_repeat_until
            if "auto_repeat_until" in fields
            else quotation.auto_repeat_until
        ),
        notes=(data.notes if "notes" in fields and data.notes is not None else quotation.notes),
    )

    if merged.quotation_to == quotation.quotation_to and merged.party_name == quotation.party_name:
        party_name = quotation.party_name
        party_label = quotation.party_label
        party_defaults: dict[str, str] = {}
    else:
        party_name, party_label, party_defaults = await _resolve_party_context(
            session,
            OpportunityPartyKind(merged.quotation_to),
            merged.party_name,
            tid,
        )

    _ensure_quotation_validity(merged.transaction_date, merged.valid_till)
    _ensure_auto_repeat_metadata(merged.auto_repeat_enabled, merged.auto_repeat_frequency)
    serialized_items = _serialize_quotation_items(merged.items)
    if not serialized_items:
        raise ValidationError(
            [{"field": "items", "message": "At least one quotation item is required."}]
        )
    subtotal = _resolve_total_amount(None, serialized_items) or Decimal("0.00")
    serialized_taxes = _serialize_quotation_taxes(merged.taxes, subtotal)
    total_taxes = _resolve_serialized_decimal_sum(serialized_taxes, "tax_amount")
    grand_total = (subtotal + total_taxes).quantize(Decimal("0.01"))

    revised = Quotation(
        tenant_id=tid,
        quotation_to=merged.quotation_to,
        party_name=party_name,
        party_label=party_label,
        status=QuotationStatus.DRAFT,
        transaction_date=merged.transaction_date,
        valid_till=merged.valid_till,
        company=merged.company.strip(),
        currency=merged.currency.strip().upper(),
        subtotal=subtotal,
        total_taxes=total_taxes,
        grand_total=grand_total,
        base_grand_total=grand_total,
        ordered_amount=Decimal("0.00"),
        order_count=0,
        contact_person=_trim(merged.contact_person) or party_defaults.get("contact_person", ""),
        contact_email=_trim(merged.contact_email) or party_defaults.get("contact_email", ""),
        contact_mobile=_trim(merged.contact_mobile) or party_defaults.get("contact_mobile", ""),
        job_title=_trim(merged.job_title),
        territory=_trim(merged.territory) or party_defaults.get("territory", ""),
        customer_group=_trim(merged.customer_group),
        billing_address=_trim(merged.billing_address),
        shipping_address=_trim(merged.shipping_address),
        utm_source=_trim(merged.utm_source) or party_defaults.get("utm_source", ""),
        utm_medium=_trim(merged.utm_medium) or party_defaults.get("utm_medium", ""),
        utm_campaign=_trim(merged.utm_campaign) or party_defaults.get("utm_campaign", ""),
        utm_content=_trim(merged.utm_content) or party_defaults.get("utm_content", ""),
        items=serialized_items,
        taxes=serialized_taxes,
        terms_template=_trim(merged.terms_template),
        terms_and_conditions=_trim(merged.terms_and_conditions),
        opportunity_id=merged.opportunity_id,
        amended_from=quotation.id,
        revision_no=quotation.revision_no + 1,
        auto_repeat_enabled=merged.auto_repeat_enabled,
        auto_repeat_frequency=_trim(merged.auto_repeat_frequency),
        auto_repeat_until=merged.auto_repeat_until,
        notes=_trim(merged.notes),
    )

    async with session.begin():
        await set_tenant(session, tid)
        session.add(revised)

    await session.refresh(revised)
    return revised
