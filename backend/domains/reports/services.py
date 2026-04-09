"""Reports domain services — AR/AP aging and cash flow reports."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import Integer, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.models.supplier_invoice import SupplierInvoice
from common.models.supplier_payment import SupplierPaymentAllocation
from common.tenant import get_tenant_id_or_default, set_tenant
from common.time import today
from domains.invoices.models import Invoice
from domains.payments.models import Payment
from domains.reports.schemas import APAgingReportResponse, ARAgingBucketItem, ARAgingReportResponse


async def get_ar_aging_report(
    session: AsyncSession,
    tenant_id: uuid.UUID | None = None,
) -> ARAgingReportResponse:
    """Return AR aging report buckets for the given tenant."""
    async with session.begin():
        tid = tenant_id if tenant_id is not None else get_tenant_id_or_default()
        await set_tenant(session, tid)

        today = today()

        # Subquery: total paid per invoice (only matched/auto_matched payments)
        payment_subq = (
            select(
                Payment.invoice_id,
                func.coalesce(func.sum(Payment.amount), 0).label("paid_amount"),
            )
            .where(
                Payment.tenant_id == tid,
                Payment.match_status.in_(("matched", "auto_matched")),
            )
            .group_by(Payment.invoice_id)
            .subquery()
        )
        # Outstanding per invoice
        outstanding_expr = func.coalesce(
            Invoice.total_amount - func.coalesce(payment_subq.c.paid_amount, 0),
            Invoice.total_amount,
        )

        # Age in days past due
        age_days_expr = func.date_part("day", today - Invoice.due_date).cast(Integer)

        # Build bucket sums using case expressions
        bucket_0_30 = func.sum(
            case(
                (outstanding_expr > 0, outstanding_expr),
                else_=0,
            )
        ).filter(age_days_expr > 0, age_days_expr <= 30)

        bucket_31_60 = func.sum(
            case(
                (outstanding_expr > 0, outstanding_expr),
                else_=0,
            )
        ).filter(age_days_expr > 30, age_days_expr <= 60)

        bucket_61_90 = func.sum(
            case(
                (outstanding_expr > 0, outstanding_expr),
                else_=0,
            )
        ).filter(age_days_expr > 60, age_days_expr <= 90)

        bucket_90_plus = func.sum(
            case(
                (outstanding_expr > 0, outstanding_expr),
                else_=0,
            )
        ).filter(age_days_expr > 90)

        total_outstanding = func.sum(
            case((outstanding_expr > 0, outstanding_expr), else_=0)
        )

        total_overdue = func.sum(
            case(
                (outstanding_expr > 0, outstanding_expr),
                else_=0,
            )
        ).filter(age_days_expr > 0)

        # Count invoices per bucket (only outstanding invoices)
        count_0_30 = func.count().filter(
            outstanding_expr > 0, age_days_expr > 0, age_days_expr <= 30
        )
        count_31_60 = func.count().filter(
            outstanding_expr > 0, age_days_expr > 30, age_days_expr <= 60
        )
        count_61_90 = func.count().filter(
            outstanding_expr > 0, age_days_expr > 60, age_days_expr <= 90
        )
        count_90_plus = func.count().filter(
            outstanding_expr > 0, age_days_expr > 90
        )

        stmt = (
            select(
                func.coalesce(bucket_0_30, 0).label("bucket_0_30_days"),
                func.coalesce(bucket_31_60, 0).label("bucket_31_60_days"),
                func.coalesce(bucket_61_90, 0).label("bucket_61_90_days"),
                func.coalesce(bucket_90_plus, 0).label("bucket_90_plus_days"),
                func.coalesce(total_outstanding, 0).label("total_outstanding"),
                func.coalesce(total_overdue, 0).label("total_overdue"),
                func.coalesce(count_0_30, 0).label("count_0_30"),
                func.coalesce(count_31_60, 0).label("count_31_60"),
                func.coalesce(count_61_90, 0).label("count_61_90"),
                func.coalesce(count_90_plus, 0).label("count_90_plus"),
            )
            .select_from(Invoice)
            .outerjoin(payment_subq, Invoice.id == payment_subq.c.invoice_id)
            .where(
                Invoice.tenant_id == tid,
                Invoice.status.notin_(("voided", "paid")),
            )
        )

        result = await session.execute(stmt)
        row = result.one()

        return ARAgingReportResponse(
            as_of_date=today,
            buckets=[
                ARAgingBucketItem(
                    bucket_label="0-30 days",
                    amount=Decimal(str(row.bucket_0_30_days or "0")),
                    invoice_count=int(row.count_0_30 or 0),
                ),
                ARAgingBucketItem(
                    bucket_label="31-60 days",
                    amount=Decimal(str(row.bucket_31_60_days or "0")),
                    invoice_count=int(row.count_31_60 or 0),
                ),
                ARAgingBucketItem(
                    bucket_label="61-90 days",
                    amount=Decimal(str(row.bucket_61_90_days or "0")),
                    invoice_count=int(row.count_61_90 or 0),
                ),
                ARAgingBucketItem(
                    bucket_label="90+ days",
                    amount=Decimal(str(row.bucket_90_plus_days or "0")),
                    invoice_count=int(row.count_90_plus or 0),
                ),
            ],
            total_outstanding=Decimal(str(row.total_outstanding or "0")),
            total_overdue=Decimal(str(row.total_overdue or "0")),
        )


async def get_ap_aging_report(
    session: AsyncSession,
    tenant_id: uuid.UUID | None = None,
) -> APAgingReportResponse:
    """Return AP aging report buckets for the given tenant."""
    async with session.begin():
        tid = tenant_id if tenant_id is not None else get_tenant_id_or_default()
        await set_tenant(session, tid)

        today = today()

        # Subquery: total applied per supplier invoice (only invoice_settlement allocations)
        alloc_subq = (
            select(
                SupplierPaymentAllocation.supplier_invoice_id,
                func.coalesce(func.sum(SupplierPaymentAllocation.applied_amount), 0).label(
                    "applied_amount"
                ),
            )
            .where(
                SupplierPaymentAllocation.tenant_id == tid,
                SupplierPaymentAllocation.allocation_kind.name == "INVOICE_SETTLEMENT",
            )
            .group_by(SupplierPaymentAllocation.supplier_invoice_id)
            .subquery()
        )

        # Outstanding per supplier invoice
        outstanding_expr = func.coalesce(
            SupplierInvoice.total_amount - func.coalesce(alloc_subq.c.applied_amount, 0),
            SupplierInvoice.total_amount,
        )

        # Age in days since invoice_date (AP aging uses invoice date, not due date)
        age_days_expr = func.date_part("day", today - SupplierInvoice.invoice_date).cast(Integer)

        bucket_0_30 = func.sum(
            case((outstanding_expr > 0, outstanding_expr), else_=0)
        ).filter(age_days_expr >= 0, age_days_expr <= 30)

        bucket_31_60 = func.sum(
            case((outstanding_expr > 0, outstanding_expr), else_=0)
        ).filter(age_days_expr > 30, age_days_expr <= 60)

        bucket_61_90 = func.sum(
            case((outstanding_expr > 0, outstanding_expr), else_=0)
        ).filter(age_days_expr > 60, age_days_expr <= 90)

        bucket_90_plus = func.sum(
            case((outstanding_expr > 0, outstanding_expr), else_=0)
        ).filter(age_days_expr > 90)

        total_outstanding = func.sum(
            case((outstanding_expr > 0, outstanding_expr), else_=0)
        )

        total_overdue = func.sum(
            case((outstanding_expr > 0, outstanding_expr), else_=0)
        ).filter(age_days_expr > 0)

        # Count invoices per bucket (only outstanding invoices)
        count_0_30 = func.count().filter(
            outstanding_expr > 0, age_days_expr >= 0, age_days_expr <= 30
        )
        count_31_60 = func.count().filter(
            outstanding_expr > 0, age_days_expr > 30, age_days_expr <= 60
        )
        count_61_90 = func.count().filter(
            outstanding_expr > 0, age_days_expr > 60, age_days_expr <= 90
        )
        count_90_plus = func.count().filter(
            outstanding_expr > 0, age_days_expr > 90
        )

        stmt = (
            select(
                func.coalesce(bucket_0_30, 0).label("bucket_0_30_days"),
                func.coalesce(bucket_31_60, 0).label("bucket_31_60_days"),
                func.coalesce(bucket_61_90, 0).label("bucket_61_90_days"),
                func.coalesce(bucket_90_plus, 0).label("bucket_90_plus_days"),
                func.coalesce(total_outstanding, 0).label("total_outstanding"),
                func.coalesce(total_overdue, 0).label("total_overdue"),
                func.coalesce(count_0_30, 0).label("count_0_30"),
                func.coalesce(count_31_60, 0).label("count_31_60"),
                func.coalesce(count_61_90, 0).label("count_61_90"),
                func.coalesce(count_90_plus, 0).label("count_90_plus"),
            )
            .select_from(SupplierInvoice)
            .outerjoin(alloc_subq, SupplierInvoice.id == alloc_subq.c.supplier_invoice_id)
            .where(
                SupplierInvoice.tenant_id == tid,
                SupplierInvoice.status.notin_(
                    (SupplierInvoice.status.VOIDED.value, SupplierInvoice.status.PAID.value)
                ),
            )
        )

        result = await session.execute(stmt)
        row = result.one()

        return APAgingReportResponse(
            as_of_date=today,
            buckets=[
                ARAgingBucketItem(
                    bucket_label="0-30 days",
                    amount=Decimal(str(row.bucket_0_30_days or "0")),
                    invoice_count=int(row.count_0_30 or 0),
                ),
                ARAgingBucketItem(
                    bucket_label="31-60 days",
                    amount=Decimal(str(row.bucket_31_60_days or "0")),
                    invoice_count=int(row.count_31_60 or 0),
                ),
                ARAgingBucketItem(
                    bucket_label="61-90 days",
                    amount=Decimal(str(row.bucket_61_90_days or "0")),
                    invoice_count=int(row.count_61_90 or 0),
                ),
                ARAgingBucketItem(
                    bucket_label="90+ days",
                    amount=Decimal(str(row.bucket_90_plus_days or "0")),
                    invoice_count=int(row.count_90_plus or 0),
                ),
            ],
            total_outstanding=Decimal(str(row.total_outstanding or "0")),
            total_overdue=Decimal(str(row.total_overdue or "0")),
        )
