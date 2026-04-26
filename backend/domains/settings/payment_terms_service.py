"""Payment terms template service for Epic 25.

This module provides:
- Payment terms template CRUD operations
- Schedule generation for commercial documents
- Legacy term compatibility
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.models.payment_terms import (
    LEGACY_TERM_MAPPINGS,
    LegacyPaymentTerms,
    PaymentSchedule,
    PaymentTermsTemplate,
    PaymentTermsTemplateDetail,
)

if TYPE_CHECKING:
    from datetime import timedelta


class PaymentTermsError(Exception):
    """Base exception for payment terms errors."""

    pass


class TemplateNotFoundError(PaymentTermsError):
    """Raised when payment terms template is not found."""

    def __init__(self, template_id: uuid.UUID):
        self.template_id = template_id
        super().__init__(f"Payment terms template {template_id} not found")


class InvalidInstallmentTotalError(PaymentTermsError):
    """Raised when installment portions don't sum to 100%."""

    def __init__(self, total_portion: Decimal):
        self.total_portion = total_portion
        super().__init__(
            f"Installment portions must sum to 100%, got {total_portion}%"
        )


async def create_template(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    template_name: str,
    details: list[dict],
    *,
    description: str | None = None,
    allocate_payment: bool = False,
    legacy_code: str | None = None,
) -> PaymentTermsTemplate:
    """Create a payment terms template with detail rows.

    Args:
        session: Database session
        tenant_id: Tenant identifier
        template_name: Name of the template
        details: List of detail row dictionaries with:
            - row_number: int
            - invoice_portion: Decimal (percentage)
            - credit_days: int (default 30)
            - credit_months: int (default 0)
            - discount_percent: Decimal | None
            - discount_validity_days: int | None
            - mode_of_payment: str | None
            - description: str | None
        description: Optional description
        allocate_payment: Whether to allocate payments based on terms
        legacy_code: Optional legacy term code

    Returns:
        Created PaymentTermsTemplate

    Raises:
        InvalidInstallmentTotalError: If portions don't sum to 100%
    """
    # Validate total portion
    total_portion = sum(d.get("invoice_portion", Decimal("100.00")) for d in details)
    if total_portion != Decimal("100.00"):
        raise InvalidInstallmentTotalError(total_portion)

    template = PaymentTermsTemplate(
        tenant_id=tenant_id,
        template_name=template_name,
        description=description,
        allocate_payment_based_on_payment_terms=allocate_payment,
        legacy_code=legacy_code,
    )
    session.add(template)
    await session.flush()

    # Create detail rows
    for detail_data in details:
        detail = PaymentTermsTemplateDetail(
            tenant_id=tenant_id,
            template_id=template.id,
            row_number=detail_data["row_number"],
            invoice_portion=detail_data.get("invoice_portion", Decimal("100.00")),
            credit_days=detail_data.get("credit_days", 30),
            credit_months=detail_data.get("credit_months", 0),
            discount_percent=detail_data.get("discount_percent"),
            discount_validity_days=detail_data.get("discount_validity_days"),
            mode_of_payment=detail_data.get("mode_of_payment"),
            description=detail_data.get("description"),
        )
        session.add(detail)

    await session.flush()
    return template


async def get_template(
    session: AsyncSession,
    template_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> PaymentTermsTemplate:
    """Get a payment terms template by ID.

    Args:
        session: Database session
        template_id: Template identifier
        tenant_id: Tenant identifier

    Returns:
        PaymentTermsTemplate

    Raises:
        TemplateNotFoundError: If template not found
    """
    result = await session.execute(
        select(PaymentTermsTemplate)
        .where(
            PaymentTermsTemplate.id == template_id,
            PaymentTermsTemplate.tenant_id == tenant_id,
        )
    )
    template = result.scalar_one_or_none()
    if template is None:
        raise TemplateNotFoundError(template_id)
    return template


async def list_templates(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    include_inactive: bool = False,
) -> list[PaymentTermsTemplate]:
    """List all payment terms templates for a tenant.

    Args:
        session: Database session
        tenant_id: Tenant identifier
        include_inactive: Whether to include inactive templates

    Returns:
        List of PaymentTermsTemplate
    """
    query = select(PaymentTermsTemplate).where(PaymentTermsTemplate.tenant_id == tenant_id)
    if not include_inactive:
        query = query.where(PaymentTermsTemplate.is_active == True)  # noqa: E712

    result = await session.execute(query.order_by(PaymentTermsTemplate.template_name))
    return list(result.scalars().all())


async def generate_schedule(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    document_type: str,
    document_id: uuid.UUID,
    template_id: uuid.UUID | None,
    document_date: date,
    total_amount: Decimal,
    *,
    credit_days: int | None = None,
    payment_terms_code: str | None = None,
) -> list[PaymentSchedule]:
    """Generate payment schedule rows for a commercial document.

    If template_id is provided, uses the template to generate the schedule.
    Otherwise, uses legacy term mapping or credit_days parameter.

    Args:
        session: Database session
        tenant_id: Tenant identifier
        document_type: Type of document ('order', 'invoice', etc.)
        document_id: Document identifier
        template_id: Optional payment terms template ID
        document_date: Date of the commercial document
        total_amount: Total amount of the document
        credit_days: Optional credit days override
        payment_terms_code: Optional legacy payment term code

    Returns:
        List of generated PaymentSchedule rows
    """
    schedules: list[PaymentSchedule] = []

    if template_id is not None:
        # Use template-based schedule generation
        template = await get_template(session, template_id, tenant_id)
        details = sorted(template.details, key=lambda d: d.row_number)

        for detail in details:
            due_date = detail.calculate_due_date(document_date)
            payment_amount = (total_amount * detail.invoice_portion / Decimal("100")).quantize(
                Decimal("0.01")
            )

            schedule = PaymentSchedule(
                tenant_id=tenant_id,
                document_type=document_type,
                document_id=document_id,
                template_id=template_id,
                template_detail_id=detail.id,
                row_number=detail.row_number,
                invoice_portion=detail.invoice_portion,
                due_date=due_date,
                payment_amount=payment_amount,
                outstanding_amount=payment_amount,
                discount_percent=detail.discount_percent,
                discount_validity_days=detail.discount_validity_days,
                mode_of_payment=detail.mode_of_payment,
                description=detail.description,
            )
            session.add(schedule)
            schedules.append(schedule)

    elif payment_terms_code is not None and payment_terms_code in LEGACY_TERM_MAPPINGS:
        # Use legacy term mapping
        legacy_config = LEGACY_TERM_MAPPINGS[payment_terms_code]
        due_date = _calculate_legacy_due_date(document_date, legacy_config)
        payment_amount = total_amount

        schedule = PaymentSchedule(
            tenant_id=tenant_id,
            document_type=document_type,
            document_id=document_id,
            row_number=1,
            invoice_portion=Decimal("100.00"),
            due_date=due_date,
            payment_amount=payment_amount,
            outstanding_amount=payment_amount,
            description=f"Legacy term: {payment_terms_code}",
        )
        session.add(schedule)
        schedules.append(schedule)

    elif credit_days is not None:
        # Use credit_days parameter
        due_date = document_date + _timedelta(days=credit_days)
        payment_amount = total_amount

        schedule = PaymentSchedule(
            tenant_id=tenant_id,
            document_type=document_type,
            document_id=document_id,
            row_number=1,
            invoice_portion=Decimal("100.00"),
            due_date=due_date,
            payment_amount=payment_amount,
            outstanding_amount=payment_amount,
            description=f"Credit days: {credit_days}",
        )
        session.add(schedule)
        schedules.append(schedule)

    else:
        # Default: single payment due in 30 days
        due_date = document_date + _timedelta(days=30)
        payment_amount = total_amount

        schedule = PaymentSchedule(
            tenant_id=tenant_id,
            document_type=document_type,
            document_id=document_id,
            row_number=1,
            invoice_portion=Decimal("100.00"),
            due_date=due_date,
            payment_amount=payment_amount,
            outstanding_amount=payment_amount,
            description="Default: Net 30",
        )
        session.add(schedule)
        schedules.append(schedule)

    await session.flush()
    return schedules


def _calculate_legacy_due_date(document_date: date, config: dict) -> date:
    """Calculate due date from legacy term configuration.

    Args:
        document_date: Document date
        config: Legacy term configuration dict

    Returns:
        Calculated due date
    """
    credit_days = config.get("credit_days", 30)
    credit_months = config.get("credit_months", 0)
    due_date = document_date
    if credit_months > 0:
        due_date = _add_months(due_date, credit_months)
    due_date = due_date + _timedelta(days=credit_days)
    return due_date


def _add_months(d: date, months: int) -> date:
    """Add months to a date."""
    from dateutil.relativedelta import relativedelta
    return d + relativedelta(months=months)


def _timedelta(days: int) -> "timedelta":
    """Get timedelta for days."""
    from datetime import timedelta
    return timedelta(days=days)


async def get_document_schedule(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    document_type: str,
    document_id: uuid.UUID,
) -> list[PaymentSchedule]:
    """Get payment schedule for a document.

    Args:
        session: Database session
        tenant_id: Tenant identifier
        document_type: Type of document
        document_id: Document identifier

    Returns:
        List of PaymentSchedule rows
    """
    result = await session.execute(
        select(PaymentSchedule)
        .where(
            PaymentSchedule.tenant_id == tenant_id,
            PaymentSchedule.document_type == document_type,
            PaymentSchedule.document_id == document_id,
        )
        .order_by(PaymentSchedule.row_number)
    )
    return list(result.scalars().all())


async def mark_schedule_paid(
    session: AsyncSession,
    schedule_id: uuid.UUID,
    tenant_id: uuid.UUID,
    paid_date: date,
    amount: Decimal,
) -> PaymentSchedule:
    """Mark a payment schedule row as paid.

    Args:
        session: Database session
        schedule_id: Schedule row identifier
        tenant_id: Tenant identifier
        paid_date: Date of payment
        amount: Amount paid

    Returns:
        Updated PaymentSchedule
    """
    result = await session.execute(
        select(PaymentSchedule).where(
            PaymentSchedule.id == schedule_id,
            PaymentSchedule.tenant_id == tenant_id,
        )
    )
    schedule = result.scalar_one_or_none()
    if schedule is None:
        raise PaymentTermsError(f"Schedule {schedule_id} not found")

    schedule.mark_paid(paid_date, amount)
    await session.flush()
    return schedule


async def seed_default_templates(
    session: AsyncSession,
    tenant_id: uuid.UUID,
) -> list[PaymentTermsTemplate]:
    """Seed default payment terms templates for a new tenant.

    Args:
        session: Database session
        tenant_id: Tenant identifier

    Returns:
        List of created templates
    """
    default_templates = [
        {
            "template_name": "Net 30",
            "description": "Payment due in 30 days",
            "legacy_code": LegacyPaymentTerms.NET_30.value,
            "details": [
                {
                    "row_number": 1,
                    "invoice_portion": Decimal("100.00"),
                    "credit_days": 30,
                    "credit_months": 0,
                }
            ],
        },
        {
            "template_name": "Net 60",
            "description": "Payment due in 60 days",
            "legacy_code": LegacyPaymentTerms.NET_60.value,
            "details": [
                {
                    "row_number": 1,
                    "invoice_portion": Decimal("100.00"),
                    "credit_days": 60,
                    "credit_months": 0,
                }
            ],
        },
        {
            "template_name": "50% Advance, 50% on Delivery",
            "description": "Split payment: half upfront, half on delivery",
            "details": [
                {
                    "row_number": 1,
                    "invoice_portion": Decimal("50.00"),
                    "credit_days": 0,
                    "credit_months": 0,
                    "description": "Advance payment",
                },
                {
                    "row_number": 2,
                    "invoice_portion": Decimal("50.00"),
                    "credit_days": 0,
                    "credit_months": 0,
                    "description": "Payment on delivery",
                },
            ],
        },
        {
            "template_name": "30/60/90",
            "description": "Three equal installments over 90 days",
            "details": [
                {
                    "row_number": 1,
                    "invoice_portion": Decimal("33.33"),
                    "credit_days": 30,
                    "credit_months": 0,
                    "description": "First installment",
                },
                {
                    "row_number": 2,
                    "invoice_portion": Decimal("33.33"),
                    "credit_days": 60,
                    "credit_months": 0,
                    "description": "Second installment",
                },
                {
                    "row_number": 3,
                    "invoice_portion": Decimal("33.34"),
                    "credit_days": 90,
                    "credit_months": 0,
                    "description": "Final installment",
                },
            ],
        },
    ]

    created = []
    for template_data in default_templates:
        template = await create_template(
            session,
            tenant_id,
            template_data["template_name"],
            template_data["details"],
            description=template_data.get("description"),
            legacy_code=template_data.get("legacy_code"),
        )
        created.append(template)

    await session.flush()
    return created
