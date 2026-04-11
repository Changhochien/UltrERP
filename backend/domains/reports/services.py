"""Reports domain services — AR/AP aging and cash flow reports."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import Integer, case, cast, func, select, String
from sqlalchemy.ext.asyncio import AsyncSession

from common.models.order import Order
from common.models.supplier_invoice import SupplierInvoice, SupplierInvoiceStatus
from common.models.supplier_payment import SupplierPaymentAllocation, SupplierPaymentAllocationKind
from common.tenant import DEFAULT_TENANT_ID, set_tenant
from common.time import today
from domains.invoices.enums import InvoiceStatus
from domains.invoices.models import Invoice
from domains.payments.models import Payment
from domains.reports.schemas import APAgingReportResponse, ARAgingBucketItem, ARAgingReportResponse


async def get_ar_aging_report(
    session: AsyncSession,
    tenant_id: uuid.UUID | None = None,
) -> ARAgingReportResponse:
    """Return AR aging report buckets for the given tenant."""
    async with session.begin():
        tid = tenant_id if tenant_id is not None else DEFAULT_TENANT_ID
        await set_tenant(session, tid)

        today_dt = today()
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

        # Age in days past due (due_date = invoice_date + payment_terms_days, default 30)
        order_terms_subq = (
            select(Order.payment_terms_days)
            .where(Order.id == Invoice.order_id, Order.tenant_id == tid)
            .correlate(Invoice)
            .scalar_subquery()
        )
        due_date_expr = Invoice.invoice_date + func.coalesce(order_terms_subq, 30)
        age_days_expr = today_dt - due_date_expr

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
                Invoice.status.notin_((InvoiceStatus.VOIDED, InvoiceStatus.PAID)),
            )
        )

        result = await session.execute(stmt)
        row = result.one_or_none()

        if row is None:
            return ARAgingReportResponse(
                as_of_date=today_dt,
                buckets=[
                    ARAgingBucketItem(bucket_label="0-30 days", amount=Decimal("0"), invoice_count=0),
                    ARAgingBucketItem(bucket_label="31-60 days", amount=Decimal("0"), invoice_count=0),
                    ARAgingBucketItem(bucket_label="61-90 days", amount=Decimal("0"), invoice_count=0),
                    ARAgingBucketItem(bucket_label="90+ days", amount=Decimal("0"), invoice_count=0),
                ],
                total_outstanding=Decimal("0"),
                total_overdue=Decimal("0"),
            )

        return ARAgingReportResponse(
            as_of_date=today_dt,
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
        tid = tenant_id if tenant_id is not None else DEFAULT_TENANT_ID
        await set_tenant(session, tid)

        today_dt = today()

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
                cast(SupplierPaymentAllocation.allocation_kind, String) == "invoice_settlement",
            )
            .group_by(SupplierPaymentAllocation.supplier_invoice_id)
            .subquery()
        )

        # Outstanding per supplier invoice
        outstanding_expr = func.coalesce(
            SupplierInvoice.remaining_payable_amount,
            SupplierInvoice.total_amount - func.coalesce(alloc_subq.c.applied_amount, 0),
            SupplierInvoice.total_amount,
        )

        # Age in days since invoice_date (AP aging uses invoice date, not due date)
        age_days_expr = today_dt - SupplierInvoice.invoice_date

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

        # total_overdue: sum of outstanding invoices older than 0 days.
        # Uses age_days_expr > 0 (not >= 0) to match AR aging semantics, excluding current invoices.
        total_overdue = func.sum(
            case((outstanding_expr > 0, outstanding_expr), else_=0)
        ).filter(age_days_expr > 0)

        # Count invoices per bucket (only outstanding invoices, age > 0 matches AR semantics)
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
            .select_from(SupplierInvoice)
            .outerjoin(alloc_subq, SupplierInvoice.id == alloc_subq.c.supplier_invoice_id)
            .where(
                SupplierInvoice.tenant_id == tid,
                SupplierInvoice.status.notin_(
                    (SupplierInvoiceStatus.VOIDED.value, SupplierInvoiceStatus.PAID.value)
                ),
            )
        )

        result = await session.execute(stmt)
        row = result.one()

        if row is None:
            return APAgingReportResponse(
                as_of_date=today_dt,
                buckets=[
                    ARAgingBucketItem(bucket_label="0-30 days", amount=Decimal("0"), invoice_count=0),
                    ARAgingBucketItem(bucket_label="31-60 days", amount=Decimal("0"), invoice_count=0),
                    ARAgingBucketItem(bucket_label="61-90 days", amount=Decimal("0"), invoice_count=0),
                    ARAgingBucketItem(bucket_label="90+ days", amount=Decimal("0"), invoice_count=0),
                ],
                total_outstanding=Decimal("0"),
                total_overdue=Decimal("0"),
            )

        return APAgingReportResponse(
            as_of_date=today_dt,
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
