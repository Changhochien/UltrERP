from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from common.models.supplier_invoice import SupplierInvoice, SupplierInvoiceStatus
from common.models.supplier_payment import (
    SupplierPayment,
    SupplierPaymentAllocation,
    SupplierPaymentAllocationKind,
    SupplierPaymentKind,
    SupplierPaymentStatus,
)


def test_supplier_payment_enums_match_documented_values() -> None:
    assert SupplierPaymentKind.PREPAYMENT.value == "prepayment"
    assert SupplierPaymentKind.SPECIAL_PAYMENT.value == "special_payment"
    assert SupplierPaymentStatus.UNAPPLIED.value == "unapplied"
    assert SupplierPaymentStatus.PARTIALLY_APPLIED.value == "partially_applied"
    assert SupplierPaymentAllocationKind.PREPAYMENT_APPLICATION.value == "prepayment_application"


def test_supplier_payment_allocation_relationships_wire_correctly() -> None:
    tenant_id = uuid.uuid4()
    supplier_id = uuid.uuid4()

    invoice = SupplierInvoice(
        tenant_id=tenant_id,
        supplier_id=supplier_id,
        invoice_number="PI-2025001",
        invoice_date=date(2025, 3, 15),
        currency_code="TWD",
        subtotal_amount=Decimal("100.00"),
        tax_amount=Decimal("5.00"),
        total_amount=Decimal("105.00"),
        status=SupplierInvoiceStatus.OPEN,
    )
    payment = SupplierPayment(
        tenant_id=tenant_id,
        supplier_id=supplier_id,
        payment_number="PP-2025001",
        payment_kind=SupplierPaymentKind.PREPAYMENT,
        status=SupplierPaymentStatus.UNAPPLIED,
        currency_code="TWD",
        payment_date=date(2025, 3, 16),
        gross_amount=Decimal("105.00"),
    )

    allocation = SupplierPaymentAllocation(
        tenant_id=tenant_id,
        allocation_date=date(2025, 3, 16),
        applied_amount=Decimal("105.00"),
        allocation_kind=SupplierPaymentAllocationKind.PREPAYMENT_APPLICATION,
    )

    payment.allocations.append(allocation)
    invoice.payment_allocations.append(allocation)

    assert allocation.supplier_payment is payment
    assert allocation.supplier_invoice is invoice
    assert payment.allocations == [allocation]
    assert invoice.payment_allocations == [allocation]