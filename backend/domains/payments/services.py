"""Payment service — record payments and query operations."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import DateTime, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.errors import ValidationError
from common.models.audit_log import AuditLog
from common.tenant import DEFAULT_TENANT_ID, set_tenant
from domains.customers.models import Customer
from domains.invoices.enums import InvoiceStatus
from domains.invoices.models import Invoice
from domains.payments.models import Payment
from domains.payments.schemas import PaymentCreate, PaymentCreateUnmatched

ACTOR_ID = str(DEFAULT_TENANT_ID)


async def _generate_payment_ref(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    payment_date: date,
) -> str:
    """Generate PAY-YYYYMMDD-NNNN payment reference."""
    date_str = payment_date.strftime("%Y%m%d")
    prefix = f"PAY-{date_str}-"

    result = await session.execute(
        select(func.max(Payment.payment_ref))
        .where(
            Payment.tenant_id == tenant_id,
            Payment.payment_ref.like(f"{prefix}%"),
        )
        .with_for_update()
    )
    max_ref = result.scalar_one_or_none()

    if max_ref:
        seq = int(max_ref[-4:]) + 1
    else:
        seq = 1

    return f"{prefix}{seq:04d}"


async def record_payment(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    data: PaymentCreate,
    actor_id: str = ACTOR_ID,
) -> Payment:
    """Record a payment against an invoice."""
    tid = tenant_id or DEFAULT_TENANT_ID
    pay_date = data.payment_date or date.today()

    async with session.begin():
        await set_tenant(session, tid)

        # Fetch invoice with row-level lock
        result = await session.execute(
            select(Invoice)
            .where(Invoice.id == data.invoice_id, Invoice.tenant_id == tid)
            .with_for_update()
        )
        invoice = result.scalar_one_or_none()
        if invoice is None:
            raise ValidationError([{"field": "invoice_id", "message": "Invoice not found."}])

        # AC4: Voided invoice guard
        if invoice.status == InvoiceStatus.VOIDED:
            raise ValidationError(
                [
                    {
                        "field": "invoice_id",
                        "message": "Cannot record payment against voided invoice.",
                    }
                ]
            )

        # Compute outstanding balance
        sum_result = await session.execute(
            select(func.coalesce(func.sum(Payment.amount), Decimal("0"))).where(
                Payment.invoice_id == invoice.id,
                Payment.tenant_id == tid,
                Payment.match_status == "matched",
            )
        )
        paid_total = sum_result.scalar()
        outstanding = invoice.total_amount - paid_total

        # AC5: Already-paid guard
        if outstanding <= 0:
            raise ValidationError(
                [{"field": "invoice_id", "message": "Invoice is already fully paid."}]
            )

        # AC3: Overpayment prevention
        if data.amount > outstanding:
            raise ValidationError(
                [{"field": "amount", "message": "Payment amount exceeds outstanding balance."}]
            )

        # Generate payment reference
        payment_ref = await _generate_payment_ref(session, tid, pay_date)

        now = datetime.now(tz=UTC)
        payment = Payment(
            tenant_id=tid,
            invoice_id=invoice.id,
            customer_id=invoice.customer_id,
            payment_ref=payment_ref,
            amount=data.amount,
            payment_method=data.payment_method.value,
            payment_date=pay_date,
            reference_number=data.reference_number,
            notes=data.notes,
            created_by=actor_id,
            created_at=now,
            updated_at=now,
            match_status="matched",
            match_type="manual",
            matched_at=now,
        )
        session.add(payment)

        # AC2: Auto-transition to "paid" when fully paid
        new_outstanding = outstanding - data.amount
        if new_outstanding == 0:
            invoice.status = InvoiceStatus.PAID
            invoice.updated_at = datetime.now(tz=UTC)

        # AC6: Audit log
        audit = AuditLog(
            tenant_id=tid,
            actor_id=actor_id,
            actor_type="user",
            action="PAYMENT_RECORDED",
            entity_type="payment",
            entity_id=str(payment.id),
            after_state={
                "amount": str(data.amount),
                "method": data.payment_method.value,
                "invoice_id": str(invoice.id),
                "payment_ref": payment_ref,
                "outstanding_after": str(new_outstanding),
            },
            correlation_id=str(payment.id),
        )
        session.add(audit)
        await session.flush()

    await session.refresh(payment)
    return payment


async def list_payments(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    invoice_id: uuid.UUID | None = None,
    customer_id: uuid.UUID | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Payment], int]:
    """List payments with optional filters, paginated."""
    tid = tenant_id or DEFAULT_TENANT_ID

    async with session.begin():
        await set_tenant(session, tid)

        conditions = [Payment.tenant_id == tid]
        if invoice_id is not None:
            conditions.append(Payment.invoice_id == invoice_id)
        if customer_id is not None:
            conditions.append(Payment.customer_id == customer_id)

        # Count
        count_result = await session.execute(select(func.count(Payment.id)).where(*conditions))
        total = count_result.scalar()

        # Fetch
        result = await session.execute(
            select(Payment)
            .where(*conditions)
            .order_by(Payment.payment_date.desc(), Payment.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = list(result.scalars().all())

    return items, total


async def get_payment(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    payment_id: uuid.UUID,
) -> Payment | None:
    """Fetch a single payment."""
    tid = tenant_id or DEFAULT_TENANT_ID

    async with session.begin():
        await set_tenant(session, tid)
        result = await session.execute(
            select(Payment).where(
                Payment.id == payment_id,
                Payment.tenant_id == tid,
            )
        )
        return result.scalar_one_or_none()


async def record_unmatched_payment(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    data: PaymentCreateUnmatched,
    actor_id: str = ACTOR_ID,
) -> Payment:
    """Record a payment without a specific invoice (for reconciliation)."""
    tid = tenant_id or DEFAULT_TENANT_ID
    pay_date = data.payment_date or date.today()

    async with session.begin():
        await set_tenant(session, tid)

        # Validate customer exists in current tenant
        cust_result = await session.execute(
            select(Customer.id).where(
                Customer.id == data.customer_id,
                Customer.tenant_id == tid,
            )
        )
        if cust_result.scalar_one_or_none() is None:
            raise ValidationError([{"field": "customer_id", "message": "Customer not found."}])

        payment_ref = await _generate_payment_ref(session, tid, pay_date)

        now = datetime.now(tz=UTC)
        payment = Payment(
            tenant_id=tid,
            invoice_id=None,
            customer_id=data.customer_id,
            payment_ref=payment_ref,
            amount=data.amount,
            payment_method=data.payment_method.value,
            payment_date=pay_date,
            reference_number=data.reference_number,
            notes=data.notes,
            created_by=actor_id,
            created_at=now,
            updated_at=now,
            match_status="unmatched",
            match_type=None,
            matched_at=None,
        )
        session.add(payment)

        audit = AuditLog(
            tenant_id=tid,
            actor_id=actor_id,
            actor_type="user",
            action="PAYMENT_RECORDED_UNMATCHED",
            entity_type="payment",
            entity_id=str(payment.id),
            after_state={
                "amount": str(data.amount),
                "method": data.payment_method.value,
                "customer_id": str(data.customer_id),
                "payment_ref": payment_ref,
            },
            correlation_id=str(payment.id),
        )
        session.add(audit)
        await session.flush()

    await session.refresh(payment)
    return payment


def _outstanding_subquery(tenant_id: uuid.UUID):
    """Scalar subquery: total allocated payments for an invoice."""
    return (
        select(func.coalesce(func.sum(Payment.amount), Decimal("0")))
        .where(
            Payment.invoice_id == Invoice.id,
            Payment.tenant_id == tenant_id,
            Payment.match_status == "matched",
        )
        .correlate(Invoice)
        .scalar_subquery()
    )


async def run_reconciliation(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    actor_id: str = ACTOR_ID,
) -> dict:
    """Run reconciliation on all unmatched payments."""
    tid = tenant_id or DEFAULT_TENANT_ID
    matched = []
    suggested = []
    unmatched_list = []

    async with session.begin():
        await set_tenant(session, tid)

        # Fetch all unmatched payments
        result = await session.execute(
            select(Payment)
            .where(
                Payment.tenant_id == tid,
                Payment.match_status == "unmatched",
                Payment.invoice_id.is_(None),
            )
            .order_by(Payment.payment_date.asc())
        )
        unmatched_payments = list(result.scalars().all())

        paid_subq = _outstanding_subquery(tid)

        for payment in unmatched_payments:
            # --- Exact match: customer + outstanding == amount ---
            exact_result = await session.execute(
                select(Invoice)
                .where(
                    Invoice.tenant_id == tid,
                    Invoice.customer_id == payment.customer_id,
                    Invoice.status == "issued",
                    (Invoice.total_amount - paid_subq) == payment.amount,
                )
                .order_by(Invoice.invoice_date.asc())
                .with_for_update()
            )
            exact_matches = list(exact_result.scalars().all())

            if len(exact_matches) == 1:
                # Auto-allocate
                inv = exact_matches[0]
                await _allocate_payment(session, payment, inv, "exact_amount", tid, actor_id)
                await session.flush()
                matched.append(
                    {
                        "payment_id": str(payment.id),
                        "payment_ref": payment.payment_ref,
                        "invoice_number": inv.invoice_number,
                    }
                )
                continue

            if len(exact_matches) > 1:
                # Multiple exact matches — suggest the oldest
                inv = exact_matches[0]
                payment.match_status = "suggested"
                payment.match_type = "exact_amount"
                payment.suggested_invoice_id = inv.id
                payment.updated_at = datetime.now(tz=UTC)
                suggested.append(
                    {
                        "payment_id": str(payment.id),
                        "payment_ref": payment.payment_ref,
                        "suggested_invoice_number": inv.invoice_number,
                        "match_type": "exact_amount",
                    }
                )
                continue

            # --- Date proximity match ---
            date_result = await session.execute(
                select(Invoice)
                .where(
                    Invoice.tenant_id == tid,
                    Invoice.customer_id == payment.customer_id,
                    Invoice.status == "issued",
                    (Invoice.total_amount - paid_subq) >= payment.amount,
                    func.abs(
                        func.extract("epoch", Invoice.invoice_date)
                        - func.extract("epoch", func.cast(payment.payment_date, DateTime))
                    )
                    <= 90 * 86400,
                )
                .order_by(
                    func.abs(
                        func.extract("epoch", Invoice.invoice_date)
                        - func.extract("epoch", func.cast(payment.payment_date, DateTime))
                    ).asc()
                )
                .limit(1)
                .with_for_update()
            )
            date_candidate = date_result.scalar_one_or_none()

            if date_candidate is not None:
                payment.match_status = "suggested"
                payment.match_type = "date_proximity"
                payment.suggested_invoice_id = date_candidate.id
                payment.updated_at = datetime.now(tz=UTC)
                suggested.append(
                    {
                        "payment_id": str(payment.id),
                        "payment_ref": payment.payment_ref,
                        "suggested_invoice_number": date_candidate.invoice_number,
                        "match_type": "date_proximity",
                    }
                )
                continue

            # No match found
            unmatched_list.append(
                {"payment_id": str(payment.id), "payment_ref": payment.payment_ref}
            )

        await session.flush()

    return {
        "matched_count": len(matched),
        "suggested_count": len(suggested),
        "unmatched_count": len(unmatched_list),
        "details": [{**d, "match_status": "matched", "match_type": "exact_amount"} for d in matched]
        + [{**d, "match_status": "suggested"} for d in suggested]
        + [{**d, "match_status": "unmatched", "match_type": None} for d in unmatched_list],
    }


async def _allocate_payment(
    session: AsyncSession,
    payment: Payment,
    invoice: Invoice,
    match_type: str,
    tenant_id: uuid.UUID,
    actor_id: str,
    *,
    audit_action: str = "PAYMENT_MATCHED_AUTO",
) -> None:
    """Allocate a payment to an invoice and update invoice status if fully paid."""
    # Guard: only issued invoices can receive allocations
    if invoice.status != InvoiceStatus.ISSUED:
        raise ValidationError(
            [
                {
                    "field": "invoice_id",
                    "message": f"Cannot allocate payment: invoice status is '{invoice.status}'.",
                }
            ]
        )

    now = datetime.now(tz=UTC)
    payment.invoice_id = invoice.id
    payment.match_status = "matched"
    payment.match_type = match_type
    payment.matched_at = now
    payment.suggested_invoice_id = None
    payment.updated_at = now

    # Compute outstanding AFTER this allocation
    paid_result = await session.execute(
        select(func.coalesce(func.sum(Payment.amount), Decimal("0"))).where(
            Payment.invoice_id == invoice.id,
            Payment.tenant_id == tenant_id,
            Payment.match_status == "matched",
            Payment.id != payment.id,
        )
    )
    paid_total = paid_result.scalar()
    new_outstanding = invoice.total_amount - paid_total - payment.amount

    if new_outstanding == 0:
        invoice.status = "paid"
        invoice.updated_at = now

    audit = AuditLog(
        tenant_id=tenant_id,
        actor_id=actor_id,
        actor_type="user",
        action=audit_action,
        entity_type="payment",
        entity_id=str(payment.id),
        after_state={
            "invoice_id": str(invoice.id),
            "match_type": match_type,
        },
        correlation_id=str(payment.id),
    )
    session.add(audit)


async def confirm_suggested_match(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    payment_id: uuid.UUID,
    actor_id: str = ACTOR_ID,
) -> Payment:
    """Confirm a suggested match, allocating the payment to the suggested invoice."""
    tid = tenant_id or DEFAULT_TENANT_ID

    async with session.begin():
        await set_tenant(session, tid)

        result = await session.execute(
            select(Payment)
            .where(
                Payment.id == payment_id,
                Payment.tenant_id == tid,
            )
            .with_for_update()
        )
        payment = result.scalar_one_or_none()
        if payment is None:
            raise ValidationError([{"field": "payment_id", "message": "Payment not found."}])

        if payment.match_status != "suggested" or payment.suggested_invoice_id is None:
            raise ValidationError(
                [{"field": "payment_id", "message": "Payment has no suggested match to confirm."}]
            )

        # Fetch the suggested invoice with lock
        inv_result = await session.execute(
            select(Invoice)
            .where(
                Invoice.id == payment.suggested_invoice_id,
                Invoice.tenant_id == tid,
            )
            .with_for_update()
        )
        invoice = inv_result.scalar_one_or_none()
        if invoice is None:
            raise ValidationError(
                [{"field": "invoice_id", "message": "Suggested invoice no longer exists."}]
            )

        if invoice.status != InvoiceStatus.ISSUED:
            if invoice.status == InvoiceStatus.VOIDED:
                raise ValidationError(
                    [{"field": "invoice_id", "message": "Invoice has been voided."}]
                )
            raise ValidationError(
                [{"field": "invoice_id", "message": "Can only match to issued invoices."}]
            )

        # Customer cross-check (guard against reconciliation bugs)
        if invoice.customer_id != payment.customer_id:
            raise ValidationError(
                [{"field": "invoice_id", "message": "Invoice belongs to a different customer."}]
            )

        # Validate outstanding balance
        paid_result = await session.execute(
            select(func.coalesce(func.sum(Payment.amount), Decimal("0"))).where(
                Payment.invoice_id == invoice.id,
                Payment.tenant_id == tid,
                Payment.match_status == "matched",
            )
        )
        outstanding = invoice.total_amount - paid_result.scalar()
        if payment.amount > outstanding:
            raise ValidationError(
                [
                    {
                        "field": "amount",
                        "message": "Payment amount exceeds invoice outstanding balance.",
                    }
                ]
            )

        await _allocate_payment(
            session, payment, invoice, payment.match_type or "manual", tid, actor_id
        )
        await session.flush()

    await session.refresh(payment)
    return payment


async def manual_match(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    payment_id: uuid.UUID,
    invoice_id: uuid.UUID,
    actor_id: str = ACTOR_ID,
) -> Payment:
    """Manually match a payment to an invoice."""
    tid = tenant_id or DEFAULT_TENANT_ID

    async with session.begin():
        await set_tenant(session, tid)

        # Fetch payment
        pay_result = await session.execute(
            select(Payment)
            .where(
                Payment.id == payment_id,
                Payment.tenant_id == tid,
            )
            .with_for_update()
        )
        payment = pay_result.scalar_one_or_none()
        if payment is None:
            raise ValidationError([{"field": "payment_id", "message": "Payment not found."}])

        if payment.match_status == "matched":
            raise ValidationError(
                [{"field": "payment_id", "message": "Payment is already matched."}]
            )

        # Fetch invoice
        inv_result = await session.execute(
            select(Invoice)
            .where(
                Invoice.id == invoice_id,
                Invoice.tenant_id == tid,
            )
            .with_for_update()
        )
        invoice = inv_result.scalar_one_or_none()
        if invoice is None:
            raise ValidationError([{"field": "invoice_id", "message": "Invoice not found."}])

        # AC6: Same customer validation
        if invoice.customer_id != payment.customer_id:
            raise ValidationError(
                [{"field": "invoice_id", "message": "Invoice belongs to a different customer."}]
            )

        if invoice.status != InvoiceStatus.ISSUED:
            if invoice.status == InvoiceStatus.VOIDED:
                raise ValidationError(
                    [{"field": "invoice_id", "message": "Invoice has been voided."}]
                )
            raise ValidationError(
                [{"field": "invoice_id", "message": "Can only match to issued invoices."}]
            )

        # Validate outstanding balance
        paid_result = await session.execute(
            select(func.coalesce(func.sum(Payment.amount), Decimal("0"))).where(
                Payment.invoice_id == invoice.id,
                Payment.tenant_id == tid,
                Payment.match_status == "matched",
            )
        )
        outstanding = invoice.total_amount - paid_result.scalar()
        if payment.amount > outstanding:
            raise ValidationError(
                [
                    {
                        "field": "amount",
                        "message": "Payment amount exceeds invoice outstanding balance.",
                    }
                ]
            )

        await _allocate_payment(
            session,
            payment,
            invoice,
            "manual",
            tid,
            actor_id,
            audit_action="PAYMENT_MATCHED_MANUAL",
        )
        await session.flush()

    await session.refresh(payment)
    return payment
