from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest
import pytest_asyncio

from common.models.product import Product
from common.models.supplier import Supplier
from common.models.supplier_invoice import SupplierInvoice, SupplierInvoiceLine
from common.models.supplier_order import SupplierOrder, SupplierOrderLine, SupplierOrderStatus
from common.models.warehouse import Warehouse
from domains.customers.models import Customer
from domains.invoices.enums import InvoiceStatus
from domains.invoices.models import Invoice, InvoiceLine
from domains.invoices.service import (
    _resolve_latest_unit_cost,
    backfill_missing_invoice_line_unit_costs,
)
from tests.db import isolated_async_session


async def _commit(session) -> None:
    await session.commit()


@pytest.fixture
def tenant_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest_asyncio.fixture
async def db_session():
    async with isolated_async_session() as session:
        yield session


async def _make_product(session, *, tenant_id: uuid.UUID) -> Product:
    product = Product(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        code=f"P-{uuid.uuid4().hex[:8].upper()}",
        name="Backfill Test Product",
        category="Test",
        status="active",
    )
    session.add(product)
    await session.flush()
    return product


async def _make_supplier(
    session,
    *,
    tenant_id: uuid.UUID,
    name: str = "Backfill Supplier",
) -> Supplier:
    supplier = Supplier(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name=name,
        is_active=True,
    )
    session.add(supplier)
    await session.flush()
    return supplier


async def _make_warehouse(session, *, tenant_id: uuid.UUID) -> Warehouse:
    warehouse = Warehouse(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name="Backfill WH",
        code=f"BWH{uuid.uuid4().hex[:6].upper()}",
        is_active=True,
    )
    session.add(warehouse)
    await session.flush()
    return warehouse


async def _make_customer(session, *, tenant_id: uuid.UUID) -> Customer:
    customer = Customer(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        company_name="Backfill Customer Co.",
        normalized_business_number=str(uuid.uuid4().int % 10**8).zfill(8),
        billing_address="Taipei",
        contact_name="Owner",
        contact_phone="02-12345678",
        contact_email=f"owner-{uuid.uuid4().hex[:6]}@example.com",
        credit_limit=Decimal("100000.00"),
    )
    session.add(customer)
    await session.flush()
    return customer


async def _make_invoice_with_null_cost(
    session,
    *,
    tenant_id: uuid.UUID,
    customer: Customer,
    product: Product,
    invoice_date: date,
) -> InvoiceLine:
    invoice = Invoice(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        invoice_number=f"AZ{uuid.uuid4().int % 10**8:08d}",
        invoice_date=invoice_date,
        customer_id=customer.id,
        buyer_type="b2b",
        buyer_identifier_snapshot=customer.normalized_business_number,
        currency_code="TWD",
        subtotal_amount=Decimal("100.00"),
        tax_amount=Decimal("5.00"),
        total_amount=Decimal("105.00"),
        status=InvoiceStatus.ISSUED,
        version=1,
    )
    session.add(invoice)
    await session.flush()

    line = InvoiceLine(
        id=uuid.uuid4(),
        invoice_id=invoice.id,
        tenant_id=tenant_id,
        line_number=1,
        product_id=product.id,
        product_code_snapshot=product.code,
        description="Backfill invoice line",
        quantity=Decimal("1.000"),
        unit_price=Decimal("100.00"),
        unit_cost=None,
        subtotal_amount=Decimal("100.00"),
        tax_type=1,
        tax_rate=Decimal("0.0500"),
        tax_amount=Decimal("5.00"),
        total_amount=Decimal("105.00"),
        zero_tax_rate_reason=None,
    )
    session.add(line)
    await session.flush()
    return line


async def _make_supplier_order_cost(
    session,
    *,
    tenant_id: uuid.UUID,
    supplier: Supplier,
    product: Product,
    warehouse: Warehouse,
    received_date: date,
    unit_price: Decimal,
) -> None:
    order = SupplierOrder(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        supplier_id=supplier.id,
        order_number=f"PO-{uuid.uuid4().hex[:8].upper()}",
        status=SupplierOrderStatus.RECEIVED,
        order_date=received_date,
        received_date=received_date,
        created_by="test",
    )
    session.add(order)
    await session.flush()

    line = SupplierOrderLine(
        id=uuid.uuid4(),
        order_id=order.id,
        product_id=product.id,
        warehouse_id=warehouse.id,
        quantity_ordered=10,
        unit_price=unit_price,
        quantity_received=10,
        notes=None,
    )
    session.add(line)
    await session.flush()


async def _make_supplier_invoice_cost(
    session,
    *,
    tenant_id: uuid.UUID,
    supplier: Supplier,
    product: Product,
    invoice_date: date,
    unit_price: Decimal,
    line_number: int = 1,
) -> None:
    supplier_invoice = SupplierInvoice(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        supplier_id=supplier.id,
        invoice_number=f"SI-{uuid.uuid4().hex[:8].upper()}",
        invoice_date=invoice_date,
        currency_code="TWD",
        subtotal_amount=unit_price,
        tax_amount=Decimal("0.00"),
        total_amount=unit_price,
        status="open",
        notes=None,
    )
    session.add(supplier_invoice)
    await session.flush()

    supplier_invoice_line = SupplierInvoiceLine(
        id=uuid.uuid4(),
        supplier_invoice_id=supplier_invoice.id,
        tenant_id=tenant_id,
        line_number=line_number,
        product_id=product.id,
        product_code_snapshot=product.code,
        description="Historical supplier invoice line",
        quantity=Decimal("1.000"),
        unit_price=unit_price,
        subtotal_amount=unit_price,
        tax_type=1,
        tax_rate=Decimal("0.0000"),
        tax_amount=Decimal("0.00"),
        total_amount=unit_price,
    )
    session.add(supplier_invoice_line)
    await session.flush()


@pytest.mark.asyncio
async def test_backfill_invoice_unit_costs_dry_run_and_live_use_same_day_invoice_precedence(
    db_session,
    tenant_id: uuid.UUID,
) -> None:
    product = await _make_product(db_session, tenant_id=tenant_id)
    supplier = await _make_supplier(db_session, tenant_id=tenant_id)
    warehouse = await _make_warehouse(db_session, tenant_id=tenant_id)
    customer = await _make_customer(db_session, tenant_id=tenant_id)

    await _make_supplier_order_cost(
        db_session,
        tenant_id=tenant_id,
        supplier=supplier,
        product=product,
        warehouse=warehouse,
        received_date=date(2024, 3, 10),
        unit_price=Decimal("10.00"),
    )
    await _make_supplier_invoice_cost(
        db_session,
        tenant_id=tenant_id,
        supplier=supplier,
        product=product,
        invoice_date=date(2024, 3, 10),
        unit_price=Decimal("12.00"),
    )
    invoice_line = await _make_invoice_with_null_cost(
        db_session,
        tenant_id=tenant_id,
        customer=customer,
        product=product,
        invoice_date=date(2024, 3, 11),
    )
    await _commit(db_session)

    dry_run_summary = await backfill_missing_invoice_line_unit_costs(
        db_session,
        tenant_id=tenant_id,
        dry_run=True,
    )

    assert dry_run_summary.candidate_count == 1
    assert dry_run_summary.updated_count == 1
    assert dry_run_summary.skipped_count == 0
    assert dry_run_summary.unmatched_count == 0
    assert dry_run_summary.ambiguous_count == 0
    await db_session.refresh(invoice_line)
    assert invoice_line.unit_cost is None

    live_summary = await backfill_missing_invoice_line_unit_costs(
        db_session,
        tenant_id=tenant_id,
        dry_run=False,
    )
    await _commit(db_session)

    assert live_summary.updated_count == 1
    await db_session.refresh(invoice_line)
    assert invoice_line.unit_cost == Decimal("12.00")


@pytest.mark.asyncio
async def test_backfill_invoice_unit_costs_skips_unmatched_rows(
    db_session,
    tenant_id: uuid.UUID,
) -> None:
    product = await _make_product(db_session, tenant_id=tenant_id)
    supplier = await _make_supplier(db_session, tenant_id=tenant_id, name="Future Cost Supplier")
    customer = await _make_customer(db_session, tenant_id=tenant_id)

    await _make_supplier_invoice_cost(
        db_session,
        tenant_id=tenant_id,
        supplier=supplier,
        product=product,
        invoice_date=date(2024, 4, 10),
        unit_price=Decimal("18.00"),
    )
    invoice_line = await _make_invoice_with_null_cost(
        db_session,
        tenant_id=tenant_id,
        customer=customer,
        product=product,
        invoice_date=date(2024, 4, 1),
    )
    await _commit(db_session)

    summary = await backfill_missing_invoice_line_unit_costs(
        db_session,
        tenant_id=tenant_id,
        dry_run=False,
    )
    await _commit(db_session)

    assert summary.candidate_count == 1
    assert summary.updated_count == 0
    assert summary.skipped_count == 1
    assert summary.unmatched_count == 1
    assert summary.ambiguous_count == 0
    await db_session.refresh(invoice_line)
    assert invoice_line.unit_cost is None


@pytest.mark.asyncio
async def test_backfill_invoice_unit_costs_skips_ambiguous_top_ranked_prices(
    db_session,
    tenant_id: uuid.UUID,
) -> None:
    product = await _make_product(db_session, tenant_id=tenant_id)
    supplier_a = await _make_supplier(db_session, tenant_id=tenant_id, name="Ambiguous A")
    supplier_b = await _make_supplier(db_session, tenant_id=tenant_id, name="Ambiguous B")
    customer = await _make_customer(db_session, tenant_id=tenant_id)

    await _make_supplier_invoice_cost(
        db_session,
        tenant_id=tenant_id,
        supplier=supplier_a,
        product=product,
        invoice_date=date(2024, 5, 10),
        unit_price=Decimal("21.00"),
        line_number=1,
    )
    await _make_supplier_invoice_cost(
        db_session,
        tenant_id=tenant_id,
        supplier=supplier_b,
        product=product,
        invoice_date=date(2024, 5, 10),
        unit_price=Decimal("23.00"),
        line_number=1,
    )
    invoice_line = await _make_invoice_with_null_cost(
        db_session,
        tenant_id=tenant_id,
        customer=customer,
        product=product,
        invoice_date=date(2024, 5, 11),
    )
    await _commit(db_session)

    summary = await backfill_missing_invoice_line_unit_costs(
        db_session,
        tenant_id=tenant_id,
        dry_run=False,
    )
    await _commit(db_session)

    assert summary.candidate_count == 1
    assert summary.updated_count == 0
    assert summary.skipped_count == 1
    assert summary.unmatched_count == 0
    assert summary.ambiguous_count == 1
    await db_session.refresh(invoice_line)
    assert invoice_line.unit_cost is None


@pytest.mark.asyncio
async def test_backfill_invoice_unit_costs_is_replay_safe(
    db_session,
    tenant_id: uuid.UUID,
) -> None:
    product = await _make_product(db_session, tenant_id=tenant_id)
    supplier = await _make_supplier(db_session, tenant_id=tenant_id, name="Replay Supplier")
    customer = await _make_customer(db_session, tenant_id=tenant_id)

    await _make_supplier_invoice_cost(
        db_session,
        tenant_id=tenant_id,
        supplier=supplier,
        product=product,
        invoice_date=date(2024, 6, 10),
        unit_price=Decimal("30.00"),
    )
    invoice_line = await _make_invoice_with_null_cost(
        db_session,
        tenant_id=tenant_id,
        customer=customer,
        product=product,
        invoice_date=date(2024, 6, 11),
    )
    await _commit(db_session)

    first_run = await backfill_missing_invoice_line_unit_costs(
        db_session,
        tenant_id=tenant_id,
        dry_run=False,
    )
    await _commit(db_session)
    await db_session.refresh(invoice_line)

    second_run = await backfill_missing_invoice_line_unit_costs(
        db_session,
        tenant_id=tenant_id,
        dry_run=False,
    )
    await _commit(db_session)

    assert first_run.updated_count == 1
    assert invoice_line.unit_cost == Decimal("30.00")
    assert second_run.candidate_count == 0
    assert second_run.updated_count == 0
    assert second_run.skipped_count == 0


@pytest.mark.asyncio
async def test_backfill_invoice_unit_costs_can_commit_per_batch(
    db_session,
    tenant_id: uuid.UUID,
) -> None:
    product = await _make_product(db_session, tenant_id=tenant_id)
    supplier = await _make_supplier(db_session, tenant_id=tenant_id, name="Batch Commit Supplier")
    customer = await _make_customer(db_session, tenant_id=tenant_id)

    await _make_supplier_invoice_cost(
        db_session,
        tenant_id=tenant_id,
        supplier=supplier,
        product=product,
        invoice_date=date(2024, 7, 10),
        unit_price=Decimal("44.00"),
    )
    first_line = await _make_invoice_with_null_cost(
        db_session,
        tenant_id=tenant_id,
        customer=customer,
        product=product,
        invoice_date=date(2024, 7, 11),
    )
    second_line = await _make_invoice_with_null_cost(
        db_session,
        tenant_id=tenant_id,
        customer=customer,
        product=product,
        invoice_date=date(2024, 7, 12),
    )
    await _commit(db_session)

    summary = await backfill_missing_invoice_line_unit_costs(
        db_session,
        tenant_id=tenant_id,
        dry_run=False,
        batch_size=1,
        commit_per_batch=True,
    )
    await _commit(db_session)
    await db_session.refresh(first_line)
    await db_session.refresh(second_line)

    assert summary.candidate_count == 2
    assert summary.updated_count == 2
    assert first_line.unit_cost == Decimal("44.00")
    assert second_line.unit_cost == Decimal("44.00")


@pytest.mark.asyncio
async def test_forward_resolver_returns_none_for_ambiguous_top_ranked_prices(
    db_session,
    tenant_id: uuid.UUID,
) -> None:
    product = await _make_product(db_session, tenant_id=tenant_id)
    supplier_a = await _make_supplier(db_session, tenant_id=tenant_id, name="Forward Ambiguous A")
    supplier_b = await _make_supplier(db_session, tenant_id=tenant_id, name="Forward Ambiguous B")
    warehouse = await _make_warehouse(db_session, tenant_id=tenant_id)

    await _make_supplier_order_cost(
        db_session,
        tenant_id=tenant_id,
        supplier=supplier_a,
        product=product,
        warehouse=warehouse,
        received_date=date(2024, 8, 10),
        unit_price=Decimal("50.00"),
    )

    await _make_supplier_invoice_cost(
        db_session,
        tenant_id=tenant_id,
        supplier=supplier_a,
        product=product,
        invoice_date=date(2024, 8, 10),
        unit_price=Decimal("51.00"),
    )
    await _make_supplier_invoice_cost(
        db_session,
        tenant_id=tenant_id,
        supplier=supplier_b,
        product=product,
        invoice_date=date(2024, 8, 10),
        unit_price=Decimal("52.00"),
    )
    await _commit(db_session)

    result = await _resolve_latest_unit_cost(
        db_session,
        tenant_id,
        product.id,
        as_of_date=date(2024, 8, 11),
    )

    assert result is None


@pytest.mark.asyncio
async def test_forward_resolver_ignores_future_purchase_costs(
    db_session,
    tenant_id: uuid.UUID,
) -> None:
    product = await _make_product(db_session, tenant_id=tenant_id)
    supplier = await _make_supplier(db_session, tenant_id=tenant_id, name="Forward Future Supplier")

    await _make_supplier_invoice_cost(
        db_session,
        tenant_id=tenant_id,
        supplier=supplier,
        product=product,
        invoice_date=date(2024, 10, 12),
        unit_price=Decimal("72.00"),
    )
    await _commit(db_session)

    result = await _resolve_latest_unit_cost(
        db_session,
        tenant_id,
        product.id,
        as_of_date=date(2024, 10, 11),
    )

    assert result is None


@pytest.mark.asyncio
async def test_forward_resolver_prefers_same_day_supplier_invoice_when_unique(
    db_session,
    tenant_id: uuid.UUID,
) -> None:
    product = await _make_product(db_session, tenant_id=tenant_id)
    supplier = await _make_supplier(db_session, tenant_id=tenant_id, name="Forward Unique Supplier")
    warehouse = await _make_warehouse(db_session, tenant_id=tenant_id)

    await _make_supplier_order_cost(
        db_session,
        tenant_id=tenant_id,
        supplier=supplier,
        product=product,
        warehouse=warehouse,
        received_date=date(2024, 9, 10),
        unit_price=Decimal("61.00"),
    )
    await _make_supplier_invoice_cost(
        db_session,
        tenant_id=tenant_id,
        supplier=supplier,
        product=product,
        invoice_date=date(2024, 9, 10),
        unit_price=Decimal("63.00"),
    )
    await _commit(db_session)

    result = await _resolve_latest_unit_cost(
        db_session,
        tenant_id,
        product.id,
        as_of_date=date(2024, 9, 11),
    )

    assert result == Decimal("63.00")
