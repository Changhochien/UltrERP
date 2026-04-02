"""Invoice service — create, void, and query operations."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from common.errors import ValidationError
from common.events import DomainEvent
from common.models.audit_log import AuditLog
from common.tenant import DEFAULT_TENANT_ID, set_tenant
from domains.customers.models import Customer
from domains.customers.validators import validate_taiwan_business_number
from domains.invoices.enums import BuyerType
from domains.invoices.models import Invoice, InvoiceLine, InvoiceNumberRange
from domains.invoices.schemas import InvoiceCreate, InvoiceCreateLine
from domains.invoices.tax import aggregate_invoice_totals, calculate_line_amounts


_B2C_SENTINEL = "0000000000"


def _format_invoice_number(prefix: str, number: int) -> str:
    return f"{prefix}{number:08d}"


def _validate_invoice_lines(lines: list[InvoiceCreateLine]) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []

    if not 1 <= len(lines) <= 9999:
        errors.append({
            "field": "lines",
            "message": "Invoice line count must be between 1 and 9999.",
        })
        return errors

    for index, line in enumerate(lines, start=1):
        if line.quantity <= 0:
            errors.append({
                "field": f"lines[{index - 1}].quantity",
                "message": "Quantity must be positive.",
            })
        if line.unit_price < 0:
            errors.append({
                "field": f"lines[{index - 1}].unit_price",
                "message": "Unit price must not be negative.",
            })

    return errors


def normalize_buyer_identifier(
    buyer_type: BuyerType,
    buyer_identifier: str | None,
) -> str:
    if buyer_type == BuyerType.B2C:
        if buyer_identifier not in (None, ""):
            raise ValueError("B2C invoices must not provide an explicit buyer identifier.")
        return _B2C_SENTINEL

    if not buyer_identifier:
        raise ValueError("B2B invoices require a buyer identifier.")

    validation = validate_taiwan_business_number(buyer_identifier)
    if not validation.valid:
        raise ValueError("Invalid buyer identifier for B2B invoice.")

    return buyer_identifier


async def _get_customer(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    customer_id: uuid.UUID,
) -> Customer | None:
    result = await session.execute(
        select(Customer).where(
            Customer.id == customer_id,
            Customer.tenant_id == tenant_id,
        )
    )
    return cast(Customer | None, result.scalar_one_or_none())


async def _get_active_number_range(
    session: AsyncSession,
    tenant_id: uuid.UUID,
) -> InvoiceNumberRange | None:
    result = await session.execute(
        select(InvoiceNumberRange)
        .where(
            InvoiceNumberRange.tenant_id == tenant_id,
            InvoiceNumberRange.is_active.is_(True),
        )
        .order_by(InvoiceNumberRange.prefix, InvoiceNumberRange.start_number)
        .with_for_update()
    )
    return cast(InvoiceNumberRange | None, result.scalar_one_or_none())


async def _create_invoice_core(
    session: AsyncSession,
    data: InvoiceCreate,
    tenant_id: uuid.UUID,
    buyer_identifier: str,
) -> Invoice:
    """Create invoice within an already-active transaction.

    Caller is responsible for session.begin() and set_tenant().
    """
    customer = await _get_customer(session, tenant_id, data.customer_id)
    if customer is None:
        raise ValidationError([
            {"field": "customer_id", "message": "Customer does not exist."}
        ])

    number_range = await _get_active_number_range(session, tenant_id)
    if number_range is None:
        raise ValidationError([
            {
                "field": "invoice_number",
                "message": "No active invoice number range is configured.",
            }
        ])

    if number_range.next_number > number_range.end_number:
        raise ValidationError([
            {
                "field": "invoice_number",
                "message": "No invoice numbers remain in the active range.",
            }
        ])

    calculated_lines = [
        calculate_line_amounts(
            quantity=line.quantity,
            unit_price=line.unit_price,
            policy_code=line.tax_policy_code,
        )
        for line in data.lines
    ]
    totals = aggregate_invoice_totals(calculated_lines)

    invoice = Invoice(
        tenant_id=tenant_id,
        invoice_number=_format_invoice_number(number_range.prefix, number_range.next_number),
        invoice_date=data.invoice_date or date.today(),
        customer_id=customer.id,
        buyer_type=data.buyer_type.value,
        buyer_identifier_snapshot=buyer_identifier,
        currency_code=data.currency_code.upper(),
        subtotal_amount=totals["subtotal_amount"],
        tax_amount=totals["tax_amount"],
        total_amount=totals["total_amount"],
        status="issued",
        version=1,
    )

    invoice.lines = [
        InvoiceLine(
            tenant_id=tenant_id,
            line_number=index,
            product_id=line.product_id,
            product_code_snapshot=line.product_code,
            description=line.description,
            quantity=line.quantity,
            unit_price=line.unit_price,
            subtotal_amount=amounts.subtotal,
            tax_type=amounts.tax_type,
            tax_rate=amounts.tax_rate,
            tax_amount=amounts.tax_amount,
            total_amount=amounts.total_amount,
            zero_tax_rate_reason=amounts.zero_tax_rate_reason,
        )
        for index, (line, amounts) in enumerate(zip(data.lines, calculated_lines, strict=True), start=1)
    ]

    number_range.next_number += 1
    number_range.updated_at = datetime.now(tz=UTC)

    session.add(invoice)
    await session.flush()
    return invoice


async def create_invoice(
    session: AsyncSession,
    data: InvoiceCreate,
    tenant_id: uuid.UUID | None = None,
) -> Invoice:
    tid = tenant_id or DEFAULT_TENANT_ID

    errors = _validate_invoice_lines(data.lines)

    try:
        buyer_identifier = normalize_buyer_identifier(data.buyer_type, data.buyer_identifier)
    except ValueError as exc:
        errors.append({"field": "buyer_identifier", "message": str(exc)})
        buyer_identifier = ""

    if errors:
        raise ValidationError(errors)

    async with session.begin():
        await set_tenant(session, tid)
        invoice = await _create_invoice_core(session, data, tid, buyer_identifier)

    await session.refresh(invoice)
    invoice.domain_events = [DomainEvent(name="InvoiceIssued")]
    return invoice


# ── Void window ────────────────────────────────────────────────

def compute_void_deadline(invoice_date: date) -> date:
    """Compute the Taiwan eGUI void deadline for a given invoice date.

    Filing periods are bimonthly: Jan-Feb, Mar-Apr, …, Nov-Dec.
    The void window closes on the 15th of the first month of the
    next filing period.  E.g. an invoice dated 2025-03-20 (Mar-Apr
    period) has a void deadline of 2025-05-15.
    """
    month = invoice_date.month
    # Determine end month of the bimonthly period.
    period_end_month = month + (month % 2)  # 2,4,6,8,10,12
    # Next period starts on the month after.
    next_period_start_month = period_end_month + 1
    year = invoice_date.year
    if next_period_start_month > 12:
        next_period_start_month = 1
        year += 1
    return date(year, next_period_start_month, 15)


# ── Void invoice ───────────────────────────────────────────────

async def void_invoice(
    session: AsyncSession,
    invoice_id: uuid.UUID,
    reason: str,
    actor_id: str = "system",
    tenant_id: uuid.UUID | None = None,
    *,
    now: datetime | None = None,
) -> Invoice:
    """Void an invoice if within the regulatory void window.

    Raises ``ValueError`` for status/window violations.
    """
    from domains.invoices.enums import ALLOWED_TRANSITIONS, InvoiceStatus

    tid = tenant_id or DEFAULT_TENANT_ID
    current_time = now or datetime.now(tz=UTC)
    today = current_time.date()

    async with session.begin():
        result = await session.execute(
            select(Invoice)
            .options(selectinload(Invoice.lines))
            .where(Invoice.id == invoice_id, Invoice.tenant_id == tid)
            .with_for_update()
        )
        invoice = result.scalar_one_or_none()
        if invoice is None:
            raise ValueError("Invoice not found")

        current_status = InvoiceStatus(invoice.status)
        if InvoiceStatus.VOIDED not in ALLOWED_TRANSITIONS.get(current_status, frozenset()):
            raise ValueError(f"Cannot void invoice in status '{invoice.status}'")

        deadline = compute_void_deadline(invoice.invoice_date)
        if today > deadline:
            raise ValueError(
                f"Void window expired. Deadline was {deadline.isoformat()}."
            )

        before_state = {
            "status": invoice.status,
            "voided_at": None,
            "void_reason": None,
        }

        invoice.status = InvoiceStatus.VOIDED.value
        invoice.voided_at = current_time
        invoice.void_reason = reason
        invoice.updated_at = current_time

        after_state = {
            "status": invoice.status,
            "voided_at": invoice.voided_at.isoformat(),
            "void_reason": invoice.void_reason,
        }

        audit = AuditLog(
            tenant_id=tid,
            actor_id=actor_id,
            actor_type="user",
            action="invoice.voided",
            entity_type="invoice",
            entity_id=str(invoice.id),
            before_state=before_state,
            after_state=after_state,
            notes=reason,
        )
        session.add(audit)

        await session.flush()

    invoice.domain_events = [DomainEvent(name="InvoiceVoided")]
    return invoice


# ── Query helpers ──────────────────────────────────────────────

async def get_invoice(
    session: AsyncSession,
    invoice_id: uuid.UUID,
    tenant_id: uuid.UUID | None = None,
) -> Invoice | None:
    """Fetch a single invoice with lines."""
    tid = tenant_id or DEFAULT_TENANT_ID
    result = await session.execute(
        select(Invoice)
        .options(selectinload(Invoice.lines))
        .where(Invoice.id == invoice_id, Invoice.tenant_id == tid)
    )
    return result.scalar_one_or_none()