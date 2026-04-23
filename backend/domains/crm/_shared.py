"""CRM shared utilities and helper functions."""

from __future__ import annotations

import json
import uuid
from datetime import date
from decimal import Decimal

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

# ---------------------------------------------------------------------------
# String utilities
# ---------------------------------------------------------------------------


def _trim(value: str | None) -> str:
    """Strip whitespace from a string value."""
    return value.strip() if value else ""


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
