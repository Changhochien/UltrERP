from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from itertools import count

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.database import AsyncSessionLocal, engine
from common.models.order import Order
from common.models.order_line import OrderLine
from common.models.product import Product
from domains.customers.models import Customer
from domains.intelligence.service import get_revenue_diagnosis
from domains.product_analytics.models import SalesMonthly
from domains.product_analytics.service import refresh_sales_monthly_range

_BUSINESS_NUMBER_COUNTER = count(30_000_000)


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
    async with AsyncSessionLocal() as session:
        yield session
    await engine.dispose()


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
    confirmed_at: datetime,
    status: str,
    line_specs: list[dict[str, object]],
) -> Order:
    total_amount = Decimal("0.00")
    normalized_specs: list[dict[str, object]] = []
    for spec in line_specs:
        quantity = Decimal(str(spec["quantity"]))
        unit_price = Decimal(str(spec["unit_price"]))
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
        line = OrderLine(
            id=uuid.uuid4(),
            tenant_id=customer.tenant_id,
            order_id=order.id,
            product_id=product.id,
            line_number=index,
            quantity=spec["quantity"],
            list_unit_price=spec["unit_price"],
            unit_price=spec["unit_price"],
            unit_cost=None,
            discount_amount=Decimal("0.00"),
            tax_policy_code="standard",
            tax_type=1,
            tax_rate=Decimal("0.0000"),
            tax_amount=Decimal("0.00"),
            subtotal_amount=spec["line_total"],
            total_amount=spec["line_total"],
            description=str(spec.get("description") or product.name),
            product_name_snapshot=spec.get("product_name_snapshot"),
            product_category_snapshot=spec.get("product_category_snapshot"),
        )
        session.add(line)

    await session.flush()
    return order


@pytest.mark.asyncio
async def test_get_revenue_diagnosis_uses_aggregates_for_closed_months_and_snapshot_labels(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
) -> None:
    customer = await _create_customer(db_session, tenant_id, "Revenue Customer")
    alpha = await _create_product(db_session, tenant_id, "Live Alpha", "Live Belts")
    beta = await _create_product(db_session, tenant_id, "Live Beta", "Live Pulleys")
    current_month = _shift_months(_month_start(datetime.now(tz=UTC).date()), -1)
    prior_month = _shift_months(current_month, -1)

    await _create_order(
        db_session,
        customer=customer,
        created_at=datetime.combine(prior_month, datetime.min.time(), tzinfo=UTC),
        confirmed_at=datetime.combine(prior_month, datetime.min.time(), tzinfo=UTC),
        status="confirmed",
        line_specs=[
            {
                "product": alpha,
                "quantity": "10.000",
                "unit_price": "10.00",
                "product_name_snapshot": "Alpha Belt",
                "product_category_snapshot": "Belts",
            },
            {
                "product": beta,
                "quantity": "10.000",
                "unit_price": "10.00",
                "product_name_snapshot": "Beta Pulley",
                "product_category_snapshot": "Pulleys",
            },
        ],
    )
    await _create_order(
        db_session,
        customer=customer,
        created_at=datetime.combine(current_month, datetime.min.time(), tzinfo=UTC),
        confirmed_at=datetime.combine(current_month, datetime.min.time(), tzinfo=UTC),
        status="fulfilled",
        line_specs=[
            {
                "product": alpha,
                "quantity": "10.000",
                "unit_price": "12.00",
                "product_name_snapshot": "Alpha Belt",
                "product_category_snapshot": "Belts",
            },
            {
                "product": beta,
                "quantity": "5.000",
                "unit_price": "10.00",
                "product_name_snapshot": "Beta Pulley",
                "product_category_snapshot": "Pulleys",
            },
        ],
    )
    await db_session.commit()

    alpha.name = "Renamed Alpha"
    alpha.category = "Renamed Belts"
    beta.name = "Renamed Beta"
    beta.category = "Renamed Pulleys"
    await db_session.commit()

    await refresh_sales_monthly_range(
        db_session,
        tenant_id,
        start_month=prior_month,
        end_month=current_month,
    )

    result = await get_revenue_diagnosis(
        db_session,
        tenant_id,
        period="1m",
        anchor_month=current_month,
    )

    assert result.period == "1m"
    assert result.anchor_month == current_month
    assert result.summary.current_revenue == Decimal("170.00")
    assert result.summary.prior_revenue == Decimal("200.00")
    assert result.summary.revenue_delta == Decimal("-30.00")
    assert result.components.price_effect_total + result.components.volume_effect_total + result.components.mix_effect_total == Decimal("-30.00")
    assert result.window_is_partial is False
    assert result.data_basis == "aggregate_only"
    assert [driver.product_name for driver in result.drivers] == ["Beta Pulley", "Alpha Belt"]
    assert result.drivers[0].product_category_snapshot == "Pulleys"
    assert result.drivers[1].product_category_snapshot == "Belts"
    for driver in result.drivers:
        assert driver.price_effect + driver.volume_effect + driver.mix_effect == driver.revenue_delta
        assert driver.data_basis == "aggregate_only"
        assert driver.window_is_partial is False


@pytest.mark.asyncio
async def test_get_revenue_diagnosis_blends_closed_aggregate_history_with_live_current_month(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
) -> None:
    customer = await _create_customer(db_session, tenant_id, "Partial Window Customer")
    product = await _create_product(db_session, tenant_id, "Current Belt", "Belts")
    current_month = _month_start(datetime.now(tz=UTC).date())
    prior_month = _shift_months(current_month, -1)

    await _create_order(
        db_session,
        customer=customer,
        created_at=datetime.combine(prior_month, datetime.min.time(), tzinfo=UTC),
        confirmed_at=datetime.combine(prior_month, datetime.min.time(), tzinfo=UTC),
        status="confirmed",
        line_specs=[
            {
                "product": product,
                "quantity": "1.000",
                "unit_price": "30.00",
                "product_name_snapshot": "Current Belt",
                "product_category_snapshot": "Belts",
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
                "product_name_snapshot": "Current Belt",
                "product_category_snapshot": "Belts",
            }
        ],
    )
    await db_session.commit()

    await refresh_sales_monthly_range(
        db_session,
        tenant_id,
        start_month=prior_month,
        end_month=prior_month,
    )

    db_session.add(
        SalesMonthly(
            tenant_id=tenant_id,
            month_start=current_month,
            product_id=product.id,
            product_name_snapshot="Stale Belt",
            product_category_snapshot="Stale Category",
            quantity_sold=Decimal("99.000"),
            order_count=9,
            revenue=Decimal("999.00"),
            avg_unit_price=Decimal("10.09"),
        )
    )
    await db_session.commit()

    result = await get_revenue_diagnosis(
        db_session,
        tenant_id,
        period="1m",
        anchor_month=current_month,
    )

    assert result.window_is_partial is True
    assert result.data_basis == "aggregate_plus_live_current_month"
    assert result.summary.current_revenue == Decimal("80.00")
    assert result.summary.prior_revenue == Decimal("30.00")
    assert len(result.drivers) == 1
    assert result.drivers[0].product_name == "Current Belt"
    assert result.drivers[0].data_basis == "aggregate_plus_live_current_month"
    assert result.drivers[0].window_is_partial is True


@pytest.mark.asyncio
async def test_get_revenue_diagnosis_returns_zero_totals_for_empty_history(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
) -> None:
    result = await get_revenue_diagnosis(
        db_session,
        tenant_id,
        period="1m",
        anchor_month=date(2026, 4, 1),
    )

    assert result.summary.current_revenue == Decimal("0.00")
    assert result.summary.prior_revenue == Decimal("0.00")
    assert result.summary.revenue_delta == Decimal("0.00")
    assert result.components.price_effect_total == Decimal("0.00")
    assert result.components.volume_effect_total == Decimal("0.00")
    assert result.components.mix_effect_total == Decimal("0.00")
    assert result.drivers == []
