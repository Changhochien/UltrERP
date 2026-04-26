"""CRM shared utilities and helper functions."""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable, Mapping
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.errors import ValidationError
from common.tenant import DEFAULT_TENANT_ID, set_tenant
from domains.crm.models import Lead
from domains.crm.schemas import (
    OpportunityItemInput,
    OpportunityPartyKind,
    QuotationPartyKind,
    QuotationTaxInput,
)
from domains.customers.models import Customer

_StatusT = TypeVar("_StatusT", bound=Enum)
_MergeFieldT = TypeVar("_MergeFieldT")

# ---------------------------------------------------------------------------
# String utilities
# ---------------------------------------------------------------------------


def _trim(value: str | None) -> str:
    """Strip whitespace from a string value."""
    return value.strip() if value else ""


def _ensure_status_transition_allowed(
    current: _StatusT,
    target: _StatusT,
    allowed_transitions: Mapping[_StatusT, frozenset[_StatusT]],
    error_factory: Callable[[_StatusT, _StatusT], Exception],
) -> None:
    """Validate a status transition against an allowed-transition map."""
    if target not in allowed_transitions.get(current, frozenset()):
        raise error_factory(current, target)


def _merge_optional_update_field(
    data: object,
    fields: set[str],
    field_name: str,
    existing_value: _MergeFieldT,
    *,
    transform: Callable[[Any], _MergeFieldT] | None = None,
) -> _MergeFieldT:
    """Use the update value when present and non-None, otherwise keep existing."""
    if field_name not in fields:
        return existing_value
    value = getattr(data, field_name)
    if value is None:
        return existing_value
    return transform(value) if transform is not None else value


def _merge_present_update_field(
    data: object,
    fields: set[str],
    field_name: str,
    existing_value: _MergeFieldT,
    *,
    transform: Callable[[Any], _MergeFieldT] | None = None,
) -> _MergeFieldT:
    """Use the update value whenever the field is present, including explicit None."""
    if field_name not in fields:
        return existing_value
    value = getattr(data, field_name)
    return transform(value) if transform is not None else value


def _resolve_contact_context_fields(
    source: object,
    defaults: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Resolve trimmed contact, attribution, and note fields with optional defaults."""
    resolved_defaults = defaults or {}
    return {
        "contact_person": _trim(getattr(source, "contact_person", None))
        or resolved_defaults.get("contact_person", ""),
        "contact_email": _trim(getattr(source, "contact_email", None))
        or resolved_defaults.get("contact_email", ""),
        "contact_mobile": _trim(getattr(source, "contact_mobile", None))
        or resolved_defaults.get("contact_mobile", ""),
        "job_title": _trim(getattr(source, "job_title", None)),
        "territory": _trim(getattr(source, "territory", None))
        or resolved_defaults.get("territory", ""),
        "customer_group": _trim(getattr(source, "customer_group", None)),
        "utm_source": _trim(getattr(source, "utm_source", None))
        or resolved_defaults.get("utm_source", ""),
        "utm_medium": _trim(getattr(source, "utm_medium", None))
        or resolved_defaults.get("utm_medium", ""),
        "utm_campaign": _trim(getattr(source, "utm_campaign", None))
        or resolved_defaults.get("utm_campaign", ""),
        "utm_content": _trim(getattr(source, "utm_content", None))
        or resolved_defaults.get("utm_content", ""),
        "notes": _trim(getattr(source, "notes", None)),
    }


# ---------------------------------------------------------------------------
# Item serialization/deserialization
# ---------------------------------------------------------------------------


def _serialize_opportunity_items(
    items: list[OpportunityItemInput],
) -> list[dict[str, object]]:
    """Serialize opportunity items to database format."""
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
    """Deserialize opportunity items from database format."""
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


def _serialize_quotation_taxes(
    taxes: list[QuotationTaxInput],
    subtotal: Decimal,
) -> list[dict[str, object]]:
    """Serialize quotation taxes to database format."""
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
    """Deserialize quotation taxes from database format."""
    return [QuotationTaxInput.model_validate(item) for item in items]


# ---------------------------------------------------------------------------
# Amount calculation utilities
# ---------------------------------------------------------------------------


def _line_amount_from_item(item: dict[str, object]) -> Decimal:
    """Calculate line amount from item data."""
    raw_amount = item.get("amount")
    if raw_amount is not None and str(raw_amount) != "":
        return Decimal(str(raw_amount)).quantize(Decimal("0.01"))
    quantity = Decimal(str(item.get("quantity") or "0"))
    unit_price = Decimal(str(item.get("unit_price") or "0.00"))
    return (quantity * unit_price).quantize(Decimal("0.01"))


def _resolve_total_amount(
    explicit_amount: Decimal | None,
    serialized_items: list[dict[str, object]],
) -> Decimal | None:
    """Resolve total amount from explicit value or item calculations."""
    if explicit_amount is not None and explicit_amount > 0:
        return explicit_amount.quantize(Decimal("0.01"))
    if serialized_items:
        total = sum(
            _line_amount_from_item(item) for item in serialized_items
        )
        if total > 0:
            return total.quantize(Decimal("0.01"))
    return None


def _resolve_serialized_decimal_sum(
    items: list[dict[str, object]],
    field_name: str,
) -> Decimal:
    """Sum a decimal field across serialized items."""
    return sum(
        (Decimal(str(item[field_name])) for item in items),
        start=Decimal("0.00"),
    ).quantize(Decimal("0.01"))


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
                    "default_currency_code": customer.default_currency_code or "",
                    "payment_terms_template_id": str(customer.payment_terms_template_id or ""),
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
