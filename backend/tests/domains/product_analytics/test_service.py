from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from itertools import count

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.models.order import Order
from common.models.order_line import OrderLine
from common.models.product import Product
from domains.customers.models import Customer
from domains.product_analytics.models import SalesMonthly
from domains.product_analytics.service import (
    backfill_sales_monthly_history,
    check_sales_monthly_health,
    read_sales_monthly_range,
    refresh_sales_monthly,
    refresh_sales_monthly_range,
    repair_missing_sales_monthly_months,
    SalesMonthlyRefreshResult,
)
import domains.product_analytics.service as product_analytics_service
from tests.db import isolated_async_session

_BUSINESS_NUMBER_COUNTER = count(20_000_000)


def _month_start(value: date) -> date:
    return value.replace(day=1)


def _shift_months(value: date, months: int) -> date:
    month_index = (value.year * 12 + value.month - 1) + months
    year = month_index // 12
    month = month_index % 12 + 1
    return date(year, month, 1)


async def _next_business_number(session: AsyncSession, tenant_id: uuid.UUID) -> str:
    while True:
        candidate = f"{next(_BUSINESS_NUMBER_COUNTER):08d}"
        existing_customer_id = await session.scalar(
            select(Customer.id)
            .where(
                Customer.tenant_id == tenant_id,
                Customer.normalized_business_number == candidate,
            )
            .limit(1)
        )
        if existing_customer_id is None:
            return candidate


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    async with isolated_async_session() as session:
        yield session


@pytest.fixture
def tenant_id() -> uuid.UUID:
    return uuid.uuid4()


async def _create_customer(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    company_name: str,
) -> Customer:
    customer = Customer(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        company_name=company_name,
        normalized_business_number=await _next_business_number(session, tenant_id),
        billing_address="Taipei",
        contact_name="Owner",
        contact_phone="0912345678",
        contact_email=f"{uuid.uuid4().hex[:8]}@example.com",
        credit_limit=Decimal("100000.00"),
        customer_type="dealer",
        status="active",
        version=1,
    )
    session.add(customer)
    await session.flush()
    return customer


async def _create_product(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    name: str,
    category: str | None,
) -> Product:
    product = Product(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        code=f"P-{uuid.uuid4().hex[:6].upper()}",
        name=name,
        category=category,
        status="active",
        unit="pcs",
    )
    session.add(product)
    await session.flush()
    return product


async def _create_order(
    session: AsyncSession,
    *,
    customer: Customer,
    created_at: datetime,
    confirmed_at: datetime | None,
    status: str,
    line_specs: list[dict[str, object]],
) -> Order:
    total_amount = Decimal("0.00")
    normalized_specs: list[dict[str, object]] = []
    for spec in line_specs:
        quantity = Decimal(str(spec.get("quantity", "1.000")))
        unit_price = Decimal(str(spec.get("unit_price", "0.00")))
        line_total = Decimal(str(spec.get("line_total", quantity * unit_price)))
        total_amount += line_total
        normalized_specs.append(
            {
                **spec,
                "quantity": quantity,
                "unit_price": unit_price,
                "line_total": line_total,
            }
        )

    order = Order(
        id=uuid.uuid4(),
        tenant_id=customer.tenant_id,
        customer_id=customer.id,
        order_number=f"ORD-{uuid.uuid4().hex[:8].upper()}",
        status=status,
        payment_terms_code="NET_30",
        payment_terms_days=30,
        subtotal_amount=total_amount,
        discount_amount=Decimal("0.00"),
        discount_percent=Decimal("0.0000"),
        tax_amount=Decimal("0.00"),
        total_amount=total_amount,
        notes=None,
        created_by="test-suite",
        created_at=created_at,
        updated_at=created_at,
        confirmed_at=confirmed_at,
    )
    session.add(order)
    await session.flush()

    for index, spec in enumerate(normalized_specs, start=1):
        product = spec["product"]
        quantity = spec["quantity"]
        unit_price = spec["unit_price"]
        line_total = spec["line_total"]
        line = OrderLine(
            id=uuid.uuid4(),
            tenant_id=customer.tenant_id,
            order_id=order.id,
            product_id=product.id,
            line_number=index,
            quantity=quantity,
            list_unit_price=unit_price,
            unit_price=unit_price,
            unit_cost=None,
            discount_amount=Decimal("0.00"),
            tax_policy_code="standard",
            tax_type=1,
            tax_rate=Decimal("0.0000"),
            tax_amount=Decimal("0.00"),
            subtotal_amount=line_total,
            total_amount=line_total,
            description=str(spec.get("description") or product.name),
            product_name_snapshot=spec.get("product_name_snapshot"),
            product_category_snapshot=spec.get("product_category_snapshot"),
        )
        session.add(line)

    await session.flush()
    return order


@pytest.mark.asyncio
async def test_refresh_sales_monthly_uses_confirmation_month_and_snapshot_fields(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
) -> None:
    customer = await _create_customer(db_session, tenant_id, "Boundary Customer")
    product = await _create_product(db_session, tenant_id, "Live Belt Name", "Live Category")
    created_at = datetime(2026, 2, 28, 23, 30, tzinfo=UTC)
    confirmed_at = datetime(2026, 3, 1, 0, 15, tzinfo=UTC)

    await _create_order(
        db_session,
        customer=customer,
        created_at=created_at,
        confirmed_at=confirmed_at,
        status="confirmed",
        line_specs=[
            {
                "product": product,
                "quantity": "2.000",
                "unit_price": "50.00",
                "product_name_snapshot": "Classic V Belt",
                "product_category_snapshot": "V-Belts",
            }
        ],
    )
    await db_session.commit()

    february_result = await refresh_sales_monthly(db_session, tenant_id, date(2026, 2, 1))
    march_result = await refresh_sales_monthly(db_session, tenant_id, date(2026, 3, 1))

    assert february_result.upserted_row_count == 0
    assert march_result.upserted_row_count == 1

    row = await db_session.scalar(
        select(SalesMonthly).where(
            SalesMonthly.tenant_id == tenant_id,
            SalesMonthly.month_start == date(2026, 3, 1),
        )
    )
    assert row is not None
    assert row.product_name_snapshot == "Classic V Belt"
    assert row.product_category_snapshot == "V-Belts"
    assert row.quantity_sold == Decimal("2.000")
    assert row.order_count == 1
    assert row.revenue == Decimal("100.00")
    assert row.avg_unit_price == Decimal("50.00")

    product.name = "Renamed Belt"
    product.category = "Timing Belts"
    await db_session.commit()

    rerun_result = await refresh_sales_monthly(db_session, tenant_id, date(2026, 3, 1))
    rerun_count = await db_session.scalar(
        select(func.count(SalesMonthly.id)).where(
            SalesMonthly.tenant_id == tenant_id,
            SalesMonthly.month_start == date(2026, 3, 1),
        )
    )
    rerun_row = await db_session.scalar(
        select(SalesMonthly).where(
            SalesMonthly.tenant_id == tenant_id,
            SalesMonthly.month_start == date(2026, 3, 1),
        )
    )

    assert rerun_result.upserted_row_count == 1
    assert rerun_count == 1
    assert rerun_row is not None
    assert rerun_row.product_name_snapshot == "Classic V Belt"
    assert rerun_row.product_category_snapshot == "V-Belts"


@pytest.mark.asyncio
async def test_refresh_sales_monthly_is_idempotent_and_duplicate_free(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
) -> None:
    customer = await _create_customer(db_session, tenant_id, "Repeat Customer")
    product = await _create_product(db_session, tenant_id, "Precision Belt", "Timing Belts")

    await _create_order(
        db_session,
        customer=customer,
        created_at=datetime(2026, 1, 15, 8, 0, tzinfo=UTC),
        confirmed_at=datetime(2026, 1, 15, 9, 0, tzinfo=UTC),
        status="fulfilled",
        line_specs=[
            {
                "product": product,
                "quantity": "3.000",
                "unit_price": "20.00",
                "product_name_snapshot": "Precision Belt",
                "product_category_snapshot": "Timing Belts",
            }
        ],
    )
    await db_session.commit()

    first_result = await refresh_sales_monthly(db_session, tenant_id, date(2026, 1, 1))
    second_result = await refresh_sales_monthly(db_session, tenant_id, date(2026, 1, 1))

    count = await db_session.scalar(
        select(func.count(SalesMonthly.id)).where(
            SalesMonthly.tenant_id == tenant_id,
            SalesMonthly.month_start == date(2026, 1, 1),
        )
    )
    row = await db_session.scalar(
        select(SalesMonthly).where(
            SalesMonthly.tenant_id == tenant_id,
            SalesMonthly.month_start == date(2026, 1, 1),
        )
    )

    assert first_result.upserted_row_count == 1
    assert second_result.upserted_row_count == 1
    assert count == 1
    assert row is not None
    assert row.quantity_sold == Decimal("3.000")
    assert row.revenue == Decimal("60.00")
    assert row.avg_unit_price == Decimal("20.00")


@pytest.mark.asyncio
async def test_refresh_sales_monthly_counts_only_commercial_statuses_per_snapshot_grain(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
) -> None:
    customer = await _create_customer(db_session, tenant_id, "Status Customer")
    product = await _create_product(db_session, tenant_id, "Live Belt", "Live Category")
    month_start = date(2026, 1, 1)
    order_moment = datetime(2026, 1, 15, 10, 0, tzinfo=UTC)

    for status, quantity, unit_price, product_name_snapshot, product_category_snapshot in (
        ("confirmed", "2.000", "10.00", "Classic Belt", "Belts"),
        ("shipped", "1.000", "12.00", "Classic Belt", "Belts"),
        ("fulfilled", "3.000", "15.00", "Classic Belt XL", "Timing Belts"),
        ("draft", "9.000", "99.00", "Classic Belt", "Belts"),
        ("cancelled", "7.000", "77.00", "Classic Belt XL", "Timing Belts"),
    ):
        await _create_order(
            db_session,
            customer=customer,
            created_at=order_moment,
            confirmed_at=order_moment if status in {"confirmed", "shipped", "fulfilled"} else None,
            status=status,
            line_specs=[
                {
                    "product": product,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "product_name_snapshot": product_name_snapshot,
                    "product_category_snapshot": product_category_snapshot,
                }
            ],
        )
    await db_session.commit()

    first_result = await refresh_sales_monthly(db_session, tenant_id, month_start)
    second_result = await refresh_sales_monthly(db_session, tenant_id, month_start)
    rows = (
        await db_session.execute(
            select(SalesMonthly)
            .where(
                SalesMonthly.tenant_id == tenant_id,
                SalesMonthly.month_start == month_start,
            )
            .order_by(SalesMonthly.product_name_snapshot)
        )
    ).scalars().all()

    assert first_result.upserted_row_count == 2
    assert second_result.upserted_row_count == 2
    assert len(rows) == 2

    classic_row = next(row for row in rows if row.product_name_snapshot == "Classic Belt")
    xl_row = next(row for row in rows if row.product_name_snapshot == "Classic Belt XL")

    assert classic_row.product_category_snapshot == "Belts"
    assert classic_row.quantity_sold == Decimal("3.000")
    assert classic_row.order_count == 2
    assert classic_row.revenue == Decimal("32.00")
    assert classic_row.avg_unit_price == Decimal("10.6667")

    assert xl_row.product_category_snapshot == "Timing Belts"
    assert xl_row.quantity_sold == Decimal("3.000")
    assert xl_row.order_count == 1
    assert xl_row.revenue == Decimal("45.00")
    assert xl_row.avg_unit_price == Decimal("15.00")


@pytest.mark.asyncio
async def test_refresh_sales_monthly_persists_four_decimal_avg_unit_price(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
) -> None:
    customer = await _create_customer(db_session, tenant_id, "Precision Customer")
    product = await _create_product(db_session, tenant_id, "Precision Belt", "Belts")
    month_start = date(2026, 1, 1)
    order_moment = datetime(2026, 1, 20, 9, 0, tzinfo=UTC)

    await _create_order(
        db_session,
        customer=customer,
        created_at=order_moment,
        confirmed_at=order_moment,
        status="confirmed",
        line_specs=[
            {
                "product": product,
                "quantity": "3.000",
                "unit_price": "10.00",
                "line_total": "32.00",
                "product_name_snapshot": "Precision Belt",
                "product_category_snapshot": "Belts",
            }
        ],
    )
    await db_session.commit()

    await refresh_sales_monthly(db_session, tenant_id, month_start)

    row = await db_session.scalar(
        select(SalesMonthly).where(
            SalesMonthly.tenant_id == tenant_id,
            SalesMonthly.month_start == month_start,
        )
    )

    assert row is not None
    assert row.avg_unit_price == Decimal("10.6667")


def test_sales_monthly_schema_exposes_category_index_and_four_decimal_avg_unit_price() -> None:
    indexes = {
        index.name: tuple(column.name for column in index.columns)
        for index in SalesMonthly.__table__.indexes
    }

    assert SalesMonthly.__table__.c.avg_unit_price.type.scale == 4
    assert indexes["ix_sales_monthly_tenant_month_category"] == (
        "tenant_id",
        "month_start",
        "product_category_snapshot",
    )


@pytest.mark.asyncio
async def test_read_sales_monthly_range_is_tenant_scoped_and_snapshot_immutable(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
) -> None:
    other_tenant_id = uuid.uuid4()
    month_start = date(2026, 2, 1)
    tenant_customer = await _create_customer(db_session, tenant_id, "Tenant A Customer")
    other_customer = await _create_customer(db_session, other_tenant_id, "Tenant B Customer")
    tenant_product = await _create_product(db_session, tenant_id, "Shared Live Belt", "Shared Live Category")
    other_product = await _create_product(db_session, other_tenant_id, "Shared Live Belt", "Shared Live Category")
    order_moment = datetime(2026, 2, 20, 12, 0, tzinfo=UTC)

    await _create_order(
        db_session,
        customer=tenant_customer,
        created_at=order_moment,
        confirmed_at=order_moment,
        status="confirmed",
        line_specs=[
            {
                "product": tenant_product,
                "quantity": "1.000",
                "unit_price": "25.00",
                "product_name_snapshot": "Tenant A Snapshot",
                "product_category_snapshot": "Tenant A Category",
            }
        ],
    )
    await _create_order(
        db_session,
        customer=other_customer,
        created_at=order_moment,
        confirmed_at=order_moment,
        status="confirmed",
        line_specs=[
            {
                "product": other_product,
                "quantity": "4.000",
                "unit_price": "30.00",
                "product_name_snapshot": "Tenant B Snapshot",
                "product_category_snapshot": "Tenant B Category",
            }
        ],
    )
    await db_session.commit()

    await refresh_sales_monthly(db_session, tenant_id, month_start)
    await refresh_sales_monthly(db_session, other_tenant_id, month_start)

    tenant_product.name = "Renamed Tenant A Belt"
    tenant_product.category = "Renamed Tenant A Category"
    other_product.name = "Renamed Tenant B Belt"
    other_product.category = "Renamed Tenant B Category"
    await db_session.commit()

    await refresh_sales_monthly(db_session, tenant_id, month_start)
    await refresh_sales_monthly(db_session, other_tenant_id, month_start)

    tenant_result = await read_sales_monthly_range(
        db_session,
        tenant_id,
        start_month=month_start,
        end_month=month_start,
    )
    other_result = await read_sales_monthly_range(
        db_session,
        other_tenant_id,
        start_month=month_start,
        end_month=month_start,
    )

    assert len(tenant_result.items) == 1
    assert tenant_result.items[0].product_name_snapshot == "Tenant A Snapshot"
    assert tenant_result.items[0].product_category_snapshot == "Tenant A Category"
    assert tenant_result.items[0].quantity_sold == Decimal("1.000")
    assert tenant_result.items[0].revenue == Decimal("25.00")

    assert len(other_result.items) == 1
    assert other_result.items[0].product_name_snapshot == "Tenant B Snapshot"
    assert other_result.items[0].product_category_snapshot == "Tenant B Category"
    assert other_result.items[0].quantity_sold == Decimal("4.000")
    assert other_result.items[0].revenue == Decimal("120.00")


@pytest.mark.asyncio
async def test_read_sales_monthly_range_uses_live_current_month_over_stale_aggregate_row(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
) -> None:
    customer = await _create_customer(db_session, tenant_id, "Range Customer")
    product = await _create_product(db_session, tenant_id, "Range Belt", "V-Belts")
    current_month = _month_start(datetime.now(tz=UTC).date())
    previous_month = _shift_months(current_month, -1)

    await _create_order(
        db_session,
        customer=customer,
        created_at=datetime.combine(previous_month, datetime.min.time(), tzinfo=UTC),
        confirmed_at=datetime.combine(previous_month, datetime.min.time(), tzinfo=UTC),
        status="confirmed",
        line_specs=[
            {
                "product": product,
                "quantity": "1.000",
                "unit_price": "30.00",
                "product_name_snapshot": "Range Belt",
                "product_category_snapshot": "V-Belts",
            }
        ],
    )
    await _create_order(
        db_session,
        customer=customer,
        created_at=datetime.combine(current_month, datetime.min.time(), tzinfo=UTC),
        confirmed_at=datetime.combine(current_month, datetime.min.time(), tzinfo=UTC),
        status="shipped",
        line_specs=[
            {
                "product": product,
                "quantity": "2.000",
                "unit_price": "40.00",
                "product_name_snapshot": "Range Belt",
                "product_category_snapshot": "V-Belts",
            }
        ],
    )
    await db_session.commit()

    await refresh_sales_monthly(db_session, tenant_id, previous_month)

    stale_current_month = SalesMonthly(
        tenant_id=tenant_id,
        month_start=current_month,
        product_id=product.id,
        product_name_snapshot="Stale Name",
        product_category_snapshot="Stale Category",
        quantity_sold=Decimal("99.000"),
        order_count=9,
        revenue=Decimal("999.00"),
        avg_unit_price=Decimal("10.09"),
    )
    db_session.add(stale_current_month)
    await db_session.commit()

    result = await read_sales_monthly_range(
        db_session,
        tenant_id,
        start_month=previous_month,
        end_month=current_month,
    )

    assert len(result.items) == 2
    closed_month_row = next(item for item in result.items if item.month_start == previous_month)
    current_month_row = next(item for item in result.items if item.month_start == current_month)

    assert closed_month_row.source == "aggregated"
    assert closed_month_row.revenue == Decimal("30.00")
    assert current_month_row.source == "live"
    assert current_month_row.product_name_snapshot == "Range Belt"
    assert current_month_row.product_category_snapshot == "V-Belts"
    assert current_month_row.quantity_sold == Decimal("2.000")
    assert current_month_row.revenue == Decimal("80.00")
    assert current_month_row.avg_unit_price == Decimal("40.00")


@pytest.mark.asyncio
async def test_read_sales_monthly_range_includes_last_closed_month_when_no_live_month_is_requested(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
) -> None:
    customer = await _create_customer(db_session, tenant_id, "Closed Window Customer")
    product = await _create_product(db_session, tenant_id, "Closed Belt", "V-Belts")
    current_month = _month_start(datetime.now(tz=UTC).date())
    two_months_ago = _shift_months(current_month, -2)
    previous_month = _shift_months(current_month, -1)

    for month_start, unit_price in (
        (two_months_ago, Decimal("10.00")),
        (previous_month, Decimal("12.00")),
    ):
        await _create_order(
            db_session,
            customer=customer,
            created_at=datetime.combine(month_start, datetime.min.time(), tzinfo=UTC),
            confirmed_at=datetime.combine(month_start, datetime.min.time(), tzinfo=UTC),
            status="confirmed",
            line_specs=[
                {
                    "product": product,
                    "quantity": "1.000",
                    "unit_price": str(unit_price),
                    "product_name_snapshot": "Closed Belt",
                    "product_category_snapshot": "V-Belts",
                }
            ],
        )
    await db_session.commit()

    await refresh_sales_monthly_range(
        db_session,
        tenant_id,
        start_month=two_months_ago,
        end_month=previous_month,
    )

    result = await read_sales_monthly_range(
        db_session,
        tenant_id,
        start_month=two_months_ago,
        end_month=previous_month,
    )

    assert [item.month_start for item in result.items] == [two_months_ago, previous_month]
    assert [item.revenue for item in result.items] == [Decimal("10.00"), Decimal("12.00")]
    assert all(item.source == "aggregated" for item in result.items)


@pytest.mark.asyncio
async def test_read_sales_monthly_range_falls_back_when_closed_month_snapshots_are_missing(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
) -> None:
    customer = await _create_customer(db_session, tenant_id, "Fallback Window Customer")
    product = await _create_product(db_session, tenant_id, "Fallback Belt", "Belts")
    current_month = _month_start(datetime.now(tz=UTC).date())
    two_months_ago = _shift_months(current_month, -2)
    previous_month = _shift_months(current_month, -1)

    for month_start, quantity, unit_price in (
        (two_months_ago, "4.000", "11.00"),
        (previous_month, "6.000", "12.00"),
    ):
        await _create_order(
            db_session,
            customer=customer,
            created_at=datetime.combine(month_start, datetime.min.time(), tzinfo=UTC),
            confirmed_at=datetime.combine(month_start, datetime.min.time(), tzinfo=UTC),
            status="confirmed",
            line_specs=[
                {
                    "product": product,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "product_name_snapshot": "Fallback Belt",
                    "product_category_snapshot": "Belts",
                }
            ],
        )
    await db_session.commit()

    result = await read_sales_monthly_range(
        db_session,
        tenant_id,
        start_month=two_months_ago,
        end_month=previous_month,
    )

    assert [item.month_start for item in result.items] == [two_months_ago, previous_month]
    assert [item.quantity_sold for item in result.items] == [Decimal("4.000"), Decimal("6.000")]
    assert [item.revenue for item in result.items] == [Decimal("44.00"), Decimal("72.00")]
    assert all(item.source == "aggregated" for item in result.items)


@pytest.mark.asyncio
async def test_read_sales_monthly_range_reuses_existing_transaction(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
) -> None:
    customer = await _create_customer(db_session, tenant_id, "Nested Transaction Customer")
    product = await _create_product(db_session, tenant_id, "Nested Belt", "Belts")
    previous_month = _shift_months(_month_start(datetime.now(tz=UTC).date()), -1)

    await _create_order(
        db_session,
        customer=customer,
        created_at=datetime.combine(previous_month, datetime.min.time(), tzinfo=UTC),
        confirmed_at=datetime.combine(previous_month, datetime.min.time(), tzinfo=UTC),
        status="confirmed",
        line_specs=[
            {
                "product": product,
                "quantity": "2.000",
                "unit_price": "18.00",
                "product_name_snapshot": "Nested Belt",
                "product_category_snapshot": "Belts",
            }
        ],
    )
    await db_session.commit()

    await refresh_sales_monthly(db_session, tenant_id, previous_month)

    async with db_session.begin():
        result = await read_sales_monthly_range(
            db_session,
            tenant_id,
            start_month=previous_month,
            end_month=previous_month,
        )

    assert len(result.items) == 1
    assert result.items[0].month_start == previous_month
    assert result.items[0].quantity_sold == Decimal("2.000")
    assert result.items[0].revenue == Decimal("36.00")
    assert result.items[0].source == "aggregated"


@pytest.mark.asyncio
async def test_refresh_sales_monthly_reports_missing_snapshot_lines_without_live_product_fallback(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
) -> None:
    customer = await _create_customer(db_session, tenant_id, "Unsupported Customer")
    product = await _create_product(db_session, tenant_id, "Live Only Product", "Live Category")
    closed_month = _shift_months(_month_start(datetime.now(tz=UTC).date()), -1)

    order = await _create_order(
        db_session,
        customer=customer,
        created_at=datetime.combine(closed_month, datetime.min.time(), tzinfo=UTC),
        confirmed_at=datetime.combine(closed_month, datetime.min.time(), tzinfo=UTC),
        status="confirmed",
        line_specs=[
            {
                "product": product,
                "quantity": "1.000",
                "unit_price": "25.00",
                "product_name_snapshot": None,
                "product_category_snapshot": None,
            }
        ],
    )
    await db_session.commit()

    result = await refresh_sales_monthly(db_session, tenant_id, closed_month)
    count = await db_session.scalar(
        select(func.count(SalesMonthly.id)).where(
            SalesMonthly.tenant_id == tenant_id,
            SalesMonthly.month_start == closed_month,
        )
    )

    assert result.upserted_row_count == 0
    assert len(result.skipped_lines) == 1
    assert result.skipped_lines[0].order_id == order.id
    assert result.skipped_lines[0].reason == "missing_snapshot"
    assert count == 0


@pytest.mark.asyncio
async def test_refresh_sales_monthly_range_skips_current_month_and_refreshes_closed_months(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
) -> None:
    customer = await _create_customer(db_session, tenant_id, "Range Wrapper Customer")
    product = await _create_product(db_session, tenant_id, "Wrapper Belt", "V-Belts")
    current_month = _month_start(datetime.now(tz=UTC).date())
    two_months_ago = _shift_months(current_month, -2)
    previous_month = _shift_months(current_month, -1)

    for month_start in (two_months_ago, previous_month, current_month):
        await _create_order(
            db_session,
            customer=customer,
            created_at=datetime.combine(month_start, datetime.min.time(), tzinfo=UTC),
            confirmed_at=datetime.combine(month_start, datetime.min.time(), tzinfo=UTC),
            status="confirmed",
            line_specs=[
                {
                    "product": product,
                    "quantity": "1.000",
                    "unit_price": "15.00",
                    "product_name_snapshot": "Wrapper Belt",
                    "product_category_snapshot": "V-Belts",
                }
            ],
        )
    await db_session.commit()

    result = await refresh_sales_monthly_range(
        db_session,
        tenant_id,
        start_month=two_months_ago,
        end_month=current_month,
    )

    by_month = {item.month_start: item for item in result.results}
    current_count = await db_session.scalar(
        select(func.count(SalesMonthly.id)).where(
            SalesMonthly.tenant_id == tenant_id,
            SalesMonthly.month_start == current_month,
        )
    )

    assert result.refreshed_month_count == 2
    assert len(result.results) == 3
    assert by_month[two_months_ago].upserted_row_count == 1
    assert by_month[previous_month].upserted_row_count == 1
    assert by_month[current_month].skipped_reason == "current_month_live_only"
    assert current_count == 0


# --- Story 20.10: Health Check, Repair, and Backfill Tests ---


@pytest.mark.asyncio
async def test_health_check_reports_healthy_when_no_gaps(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
) -> None:
    """AC1/AC2: Healthy tenant with no missing months reports is_healthy=True."""
    customer = await _create_customer(db_session, tenant_id, "Healthy Customer")
    product = await _create_product(db_session, tenant_id, "Healthy Belt", "Belts")
    previous_month = _shift_months(_month_start(datetime.now(tz=UTC).date()), -1)

    await _create_order(
        db_session,
        customer=customer,
        created_at=datetime.combine(previous_month, datetime.min.time(), tzinfo=UTC),
        confirmed_at=datetime.combine(previous_month, datetime.min.time(), tzinfo=UTC),
        status="confirmed",
        line_specs=[
            {
                "product": product,
                "quantity": "1.000",
                "unit_price": "10.00",
                "product_name_snapshot": "Healthy Belt",
                "product_category_snapshot": "Belts",
            }
        ],
    )
    await db_session.commit()

    # Refresh to populate sales_monthly
    await refresh_sales_monthly(db_session, tenant_id, previous_month)

    health = await check_sales_monthly_health(
        db_session,
        tenant_id,
        start_month=previous_month,
        end_month=previous_month,
    )

    assert health.is_healthy is True
    assert len(health.missing_months) == 0
    assert health.checked_month_count == 1


@pytest.mark.asyncio
async def test_health_check_detects_missing_closed_month_with_sales(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
) -> None:
    """AC1: Missing month with transactional sales is detected."""
    customer = await _create_customer(db_session, tenant_id, "Gap Customer")
    product = await _create_product(db_session, tenant_id, "Gap Belt", "Belts")
    previous_month = _shift_months(_month_start(datetime.now(tz=UTC).date()), -1)

    await _create_order(
        db_session,
        customer=customer,
        created_at=datetime.combine(previous_month, datetime.min.time(), tzinfo=UTC),
        confirmed_at=datetime.combine(previous_month, datetime.min.time(), tzinfo=UTC),
        status="confirmed",
        line_specs=[
            {
                "product": product,
                "quantity": "5.000",
                "unit_price": "20.00",
                "product_name_snapshot": "Gap Belt",
                "product_category_snapshot": "Belts",
            }
        ],
    )
    await db_session.commit()
    # Note: NOT refreshing sales_monthly, so gap should exist

    health = await check_sales_monthly_health(
        db_session,
        tenant_id,
        start_month=previous_month,
        end_month=previous_month,
    )

    assert health.is_healthy is False
    assert len(health.missing_months) == 1
    missing = health.missing_months[0]
    assert missing.month_start == previous_month
    assert missing.transactional_order_count == 1
    assert missing.transactional_revenue == Decimal("100.00")


@pytest.mark.asyncio
async def test_repair_missing_months_is_idempotent(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
) -> None:
    """AC3: Repairing missing months is idempotent."""
    customer = await _create_customer(db_session, tenant_id, "Repair Customer")
    product = await _create_product(db_session, tenant_id, "Repair Belt", "Belts")
    previous_month = _shift_months(_month_start(datetime.now(tz=UTC).date()), -1)

    await _create_order(
        db_session,
        customer=customer,
        created_at=datetime.combine(previous_month, datetime.min.time(), tzinfo=UTC),
        confirmed_at=datetime.combine(previous_month, datetime.min.time(), tzinfo=UTC),
        status="confirmed",
        line_specs=[
            {
                "product": product,
                "quantity": "2.000",
                "unit_price": "30.00",
                "product_name_snapshot": "Repair Belt",
                "product_category_snapshot": "Belts",
            }
        ],
    )
    await db_session.commit()

    # First repair
    result1 = await repair_missing_sales_monthly_months(
        db_session,
        tenant_id,
        [previous_month],
    )
    assert result1.refreshed_month_count == 1

    # Verify row was created
    row_count1 = await db_session.scalar(
        select(func.count(SalesMonthly.id)).where(
            SalesMonthly.tenant_id == tenant_id,
            SalesMonthly.month_start == previous_month,
        )
    )
    assert row_count1 == 1

    # Second repair should be idempotent
    result2 = await repair_missing_sales_monthly_months(
        db_session,
        tenant_id,
        [previous_month],
    )
    assert result2.refreshed_month_count == 1

    row_count2 = await db_session.scalar(
        select(func.count(SalesMonthly.id)).where(
            SalesMonthly.tenant_id == tenant_id,
            SalesMonthly.month_start == previous_month,
        )
    )
    assert row_count2 == 1  # Still only one row, no duplicates


@pytest.mark.asyncio
async def test_backfill_bounded_history_excludes_current_month(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
) -> None:
    """AC4: Backfill never aggregates the current open month."""
    customer = await _create_customer(db_session, tenant_id, "Backfill Customer")
    product = await _create_product(db_session, tenant_id, "Backfill Belt", "Belts")
    current_month = _month_start(datetime.now(tz=UTC).date())
    two_months_ago = _shift_months(current_month, -2)
    previous_month = _shift_months(current_month, -1)

    for month_start in (two_months_ago, previous_month, current_month):
        await _create_order(
            db_session,
            customer=customer,
            created_at=datetime.combine(month_start, datetime.min.time(), tzinfo=UTC),
            confirmed_at=datetime.combine(month_start, datetime.min.time(), tzinfo=UTC),
            status="confirmed",
            line_specs=[
                {
                    "product": product,
                    "quantity": "1.000",
                    "unit_price": "10.00",
                    "product_name_snapshot": "Backfill Belt",
                    "product_category_snapshot": "Belts",
                }
            ],
        )
    await db_session.commit()

    # Backfill including current month should only process closed months
    result = await backfill_sales_monthly_history(
        db_session,
        tenant_id,
        start_month=two_months_ago,
        end_month=current_month,  # Include current month
    )

    assert result.refreshed_month_count == 2  # Only two closed months

    # Verify current month is NOT in sales_monthly
    current_count = await db_session.scalar(
        select(func.count(SalesMonthly.id)).where(
            SalesMonthly.tenant_id == tenant_id,
            SalesMonthly.month_start == current_month,
        )
    )
    assert current_count == 0


@pytest.mark.asyncio
async def test_repair_missing_sales_monthly_months_only_refreshes_requested_closed_months(
    monkeypatch: pytest.MonkeyPatch,
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
) -> None:
    current_month = _month_start(datetime.now(tz=UTC).date())
    three_months_ago = _shift_months(current_month, -3)
    previous_month = _shift_months(current_month, -1)
    called_months: list[date] = []

    async def fake_refresh_sales_monthly(
        session: AsyncSession,
        inner_tenant_id: uuid.UUID,
        month_start: date,
    ) -> SalesMonthlyRefreshResult:
        assert session is db_session
        assert inner_tenant_id == tenant_id
        called_months.append(month_start)
        return SalesMonthlyRefreshResult(
            month_start=month_start,
            upserted_row_count=1,
            deleted_row_count=0,
            skipped_lines=(),
        )

    monkeypatch.setattr(
        product_analytics_service,
        "refresh_sales_monthly",
        fake_refresh_sales_monthly,
    )

    result = await repair_missing_sales_monthly_months(
        db_session,
        tenant_id,
        [three_months_ago, previous_month, current_month],
    )

    assert called_months == [three_months_ago, previous_month]
    assert result.refreshed_month_count == 2
    assert [item.month_start for item in result.results] == [three_months_ago, previous_month]


@pytest.mark.asyncio
async def test_health_check_returns_healthy_after_repair(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
) -> None:
    """AC6: Health check returns healthy after missing months are repaired."""
    customer = await _create_customer(db_session, tenant_id, "Healed Customer")
    product = await _create_product(db_session, tenant_id, "Healed Belt", "Belts")
    previous_month = _shift_months(_month_start(datetime.now(tz=UTC).date()), -1)

    await _create_order(
        db_session,
        customer=customer,
        created_at=datetime.combine(previous_month, datetime.min.time(), tzinfo=UTC),
        confirmed_at=datetime.combine(previous_month, datetime.min.time(), tzinfo=UTC),
        status="confirmed",
        line_specs=[
            {
                "product": product,
                "quantity": "3.000",
                "unit_price": "15.00",
                "product_name_snapshot": "Healed Belt",
                "product_category_snapshot": "Belts",
            }
        ],
    )
    await db_session.commit()

    # Before repair: unhealthy
    health_before = await check_sales_monthly_health(
        db_session,
        tenant_id,
        start_month=previous_month,
        end_month=previous_month,
    )
    assert health_before.is_healthy is False

    # Repair
    await repair_missing_sales_monthly_months(db_session, tenant_id, [previous_month])

    # After repair: healthy
    health_after = await check_sales_monthly_health(
        db_session,
        tenant_id,
        start_month=previous_month,
        end_month=previous_month,
    )
    assert health_after.is_healthy is True


@pytest.mark.asyncio
async def test_health_check_excludes_current_open_month_from_gap_detection(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
) -> None:
    """AC2: Current open month is never flagged as a health failure."""
    customer = await _create_customer(db_session, tenant_id, "Open Month Customer")
    product = await _create_product(db_session, tenant_id, "Open Belt", "Belts")
    current_month = _month_start(datetime.now(tz=UTC).date())

    await _create_order(
        db_session,
        customer=customer,
        created_at=datetime.combine(current_month, datetime.min.time(), tzinfo=UTC),
        confirmed_at=datetime.combine(current_month, datetime.min.time(), tzinfo=UTC),
        status="confirmed",
        line_specs=[
            {
                "product": product,
                "quantity": "10.000",
                "unit_price": "5.00",
                "product_name_snapshot": "Open Belt",
                "product_category_snapshot": "Belts",
            }
        ],
    )
    await db_session.commit()
    # No refresh - current month should use live reads

    health = await check_sales_monthly_health(
        db_session,
        tenant_id,
        start_month=current_month,
        end_month=current_month,
    )

    # Current month should NOT be flagged as missing even without sales_monthly
    assert len(health.missing_months) == 0
    assert health.current_open_month == current_month


@pytest.mark.asyncio
async def test_health_check_returns_empty_for_future_window(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
) -> None:
    """Window with no closed months returns healthy with zero checked months."""
    future_start = date(2099, 1, 1)
    future_end = date(2099, 12, 1)

    health = await check_sales_monthly_health(
        db_session,
        tenant_id,
        start_month=future_start,
        end_month=future_end,
    )

    assert health.is_healthy is True
    assert health.checked_month_count == 0
    assert len(health.missing_months) == 0
