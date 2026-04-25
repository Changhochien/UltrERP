"""Tests for intelligence customer product profile service."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from itertools import count
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.models.order import Order
from common.models.order_line import OrderLine
from common.models.product import Product
from common.tenant import DEFAULT_TENANT_ID
from domains.customers.models import Customer
import domains.intelligence.service as intelligence_service
from domains.intelligence.schemas import CategoryTrend, CategoryTrends
from domains.intelligence.service import (
    get_category_trends,
    get_customer_product_profile,
    get_customer_risk_signals,
    get_market_opportunities,
    get_product_affinity_map,
    get_prospect_gaps,
)
from tests.db import isolated_async_session

TENANT = DEFAULT_TENANT_ID
_BUSINESS_NUMBER_COUNTER = count(10_000_000)


def test_service_facade_reexports_extracted_entrypoints() -> None:
    from domains.intelligence.services.affinity import get_product_affinity_map as affinity_entrypoint
    from domains.intelligence.services.buying_behavior import get_customer_buying_behavior as buying_behavior_entrypoint
    from domains.intelligence.services.category_trends import get_category_trends as category_trends_entrypoint
    from domains.intelligence.services.customer_profile import (
        build_empty_customer_product_profile as empty_profile_entrypoint,
    )
    from domains.intelligence.services.customer_profile import (
        get_customer_product_profile as customer_profile_entrypoint,
    )
    from domains.intelligence.services.market_opportunities import (
        get_market_opportunities as market_opportunities_entrypoint,
    )
    from domains.intelligence.services.product_performance import (
        get_product_performance as product_performance_entrypoint,
    )
    from domains.intelligence.services.prospect_gaps import get_prospect_gaps as prospect_gaps_entrypoint
    from domains.intelligence.services.revenue_diagnosis import (
        get_revenue_diagnosis as revenue_diagnosis_entrypoint,
    )
    from domains.intelligence.services.risk_signals import get_customer_risk_signals as risk_signals_entrypoint

    assert intelligence_service.build_empty_customer_product_profile is empty_profile_entrypoint
    assert intelligence_service.get_category_trends is category_trends_entrypoint
    assert intelligence_service.get_customer_buying_behavior is buying_behavior_entrypoint
    assert intelligence_service.get_customer_product_profile is customer_profile_entrypoint
    assert intelligence_service.get_customer_risk_signals is risk_signals_entrypoint
    assert intelligence_service.get_market_opportunities is market_opportunities_entrypoint
    assert intelligence_service.get_product_affinity_map is affinity_entrypoint
    assert intelligence_service.get_product_performance is product_performance_entrypoint
    assert intelligence_service.get_prospect_gaps is prospect_gaps_entrypoint
    assert intelligence_service.get_revenue_diagnosis is revenue_diagnosis_entrypoint


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


async def _create_customer(session: AsyncSession, company_name: str) -> Customer:
    customer = await _create_customer_for_tenant(session, company_name, TENANT)
    return customer


async def _create_customer_for_tenant(
    session: AsyncSession,
    company_name: str,
    tenant_id: uuid.UUID,
    *,
    customer_type: str = "dealer",
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
        customer_type=customer_type,
        status="active",
        version=1,
    )
    session.add(customer)
    await session.flush()
    return customer


async def _create_product(session: AsyncSession, name: str, category: str | None) -> Product:
    product = await _create_product_for_tenant(session, name, category, TENANT)
    return product


async def _create_product_for_tenant(
    session: AsyncSession,
    name: str,
    category: str | None,
    tenant_id: uuid.UUID,
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
    confirmed_at: datetime | None = None,
    status: str,
    lines: list[tuple[Product, Decimal]],
    tenant_id: uuid.UUID | None = None,
) -> Order:
    resolved_tenant_id = tenant_id or customer.tenant_id
    total_amount = sum((line_total for _product, line_total in lines), Decimal("0.00"))
    order = Order(
        id=uuid.uuid4(),
        tenant_id=resolved_tenant_id,
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
        confirmed_at=confirmed_at if confirmed_at is not None else (created_at if status != "pending" else None),
    )
    session.add(order)
    await session.flush()

    for index, (product, line_total) in enumerate(lines, start=1):
        line = OrderLine(
            id=uuid.uuid4(),
            tenant_id=resolved_tenant_id,
            order_id=order.id,
            product_id=product.id,
            line_number=index,
            quantity=Decimal("1.000"),
            list_unit_price=line_total,
            unit_price=line_total,
            unit_cost=None,
            discount_amount=Decimal("0.00"),
            tax_policy_code="standard",
            tax_type=1,
            tax_rate=Decimal("0.0000"),
            tax_amount=Decimal("0.00"),
            subtotal_amount=line_total,
            total_amount=line_total,
            description=product.name,
        )
        session.add(line)

    await session.flush()
    return order


async def _seed_affinity_orders(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    product_a: Product,
    product_b: Product,
    now: datetime,
    shared_count: int,
    a_only_count: int,
    b_only_count: int,
    prefix: str,
) -> None:
    customers: list[Customer] = []
    orders: list[Order] = []
    order_lines: list[OrderLine] = []
    line_total = Decimal("10.00")

    def build_customer(company_name: str) -> Customer:
        customer = Customer(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            company_name=company_name,
            normalized_business_number=f"{next(_BUSINESS_NUMBER_COUNTER):08d}",
            billing_address="Taipei",
            contact_name="Owner",
            contact_phone="0912345678",
            contact_email=f"{uuid.uuid4().hex[:8]}@example.com",
            credit_limit=Decimal("100000.00"),
            customer_type="dealer",
            status="active",
            version=1,
        )
        customers.append(customer)
        return customer

    def build_order(customer: Customer, created_at: datetime, products: tuple[Product, ...]) -> None:
        order_id = uuid.uuid4()
        total_amount = line_total * len(products)
        orders.append(
            Order(
                id=order_id,
                tenant_id=tenant_id,
                customer_id=customer.id,
                order_number=f"ORD-{uuid.uuid4().hex[:8].upper()}",
                status="confirmed",
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
                confirmed_at=created_at,
            )
        )

        for index, product in enumerate(products, start=1):
            order_lines.append(
                OrderLine(
                    id=uuid.uuid4(),
                    tenant_id=tenant_id,
                    order_id=order_id,
                    product_id=product.id,
                    line_number=index,
                    quantity=Decimal("1.000"),
                    list_unit_price=line_total,
                    unit_price=line_total,
                    unit_cost=None,
                    discount_amount=Decimal("0.00"),
                    tax_policy_code="standard",
                    tax_type=1,
                    tax_rate=Decimal("0.0000"),
                    tax_amount=Decimal("0.00"),
                    subtotal_amount=line_total,
                    total_amount=line_total,
                    description=product.name,
                )
            )

    for index in range(shared_count):
        customer = build_customer(f"{prefix} Shared {index}")
        build_order(customer, now - timedelta(days=10), (product_a, product_b))

    for index in range(a_only_count):
        customer = build_customer(f"{prefix} A Only {index}")
        build_order(customer, now - timedelta(days=9), (product_a,))

    for index in range(b_only_count):
        customer = build_customer(f"{prefix} B Only {index}")
        build_order(customer, now - timedelta(days=8), (product_b,))

    session.add_all(customers)
    session.add_all(orders)
    session.add_all(order_lines)
    await session.flush()


@pytest.mark.asyncio
async def test_get_customer_product_profile_returns_rollup_metrics(db_session: AsyncSession) -> None:
    customer = await _create_customer(db_session, "Acme Trading")
    printer_ink = await _create_product(db_session, "Printer Ink", "Supplies")
    toner = await _create_product(db_session, "Laser Toner", "Supplies")
    labels = await _create_product(db_session, "Shipping Labels", "Office")
    now = datetime.now(tz=UTC)

    await _create_order(
        db_session,
        customer=customer,
        created_at=now - timedelta(days=20),
        status="confirmed",
        lines=[
            (printer_ink, Decimal("200.00")),
            (labels, Decimal("100.00")),
        ],
    )
    await _create_order(
        db_session,
        customer=customer,
        created_at=now - timedelta(days=80),
        status="shipped",
        lines=[(toner, Decimal("150.00"))],
    )
    await _create_order(
        db_session,
        customer=customer,
        created_at=now - timedelta(days=140),
        status="fulfilled",
        lines=[(labels, Decimal("120.00"))],
    )
    await _create_order(
        db_session,
        customer=customer,
        created_at=now - timedelta(days=400),
        status="confirmed",
        lines=[(labels, Decimal("90.00"))],
    )
    await db_session.commit()

    profile = await get_customer_product_profile(db_session, customer.id, TENANT)

    assert profile.company_name == "Acme Trading"
    assert profile.total_revenue_12m == Decimal("570.00")
    assert profile.order_count_12m == 3
    assert profile.order_count_6m == 3
    assert profile.order_count_3m == 2
    assert profile.order_count_prior_12m == 1
    assert profile.order_count_prior_3m == 1
    assert profile.frequency_trend == "increasing"
    assert profile.avg_order_value == Decimal("190.00")
    assert profile.avg_order_value_prior == Decimal("90.00")
    assert profile.aov_trend == "increasing"
    assert profile.last_order_date == (now - timedelta(days=20)).date()
    assert profile.days_since_last_order == 20
    assert profile.is_dormant is False
    assert profile.new_categories == ["Supplies"]
    assert profile.confidence == "medium"
    assert profile.activity_basis == "confirmed_or_later_orders"
    assert profile.top_categories[0].category == "Supplies"
    assert profile.top_categories[0].revenue == Decimal("350.00")
    assert profile.top_products[0].product_name == "Shipping Labels"
    assert profile.top_products[0].order_count == 2


@pytest.mark.asyncio
async def test_get_customer_product_profile_returns_empty_profile_without_orders(db_session: AsyncSession) -> None:
    customer = await _create_customer(db_session, "Quiet Account")
    await db_session.commit()

    profile = await get_customer_product_profile(db_session, customer.id, TENANT)

    assert profile.company_name == "Quiet Account"
    assert profile.total_revenue_12m == Decimal("0.00")
    assert profile.order_count_12m == 0
    assert profile.top_categories == []
    assert profile.top_products == []
    assert profile.is_dormant is True
    assert profile.confidence == "low"
    assert profile.activity_basis == "confirmed_or_later_orders"


@pytest.mark.asyncio
async def test_get_customer_product_profile_raises_for_missing_customer(db_session: AsyncSession) -> None:
    with pytest.raises(ValueError, match="Customer not found"):
        await get_customer_product_profile(db_session, uuid.uuid4(), TENANT)


@pytest.mark.asyncio
async def test_get_product_affinity_map_uses_customer_level_overlap_and_sorting(
    db_session: AsyncSession,
) -> None:
    tenant_id = uuid.uuid4()
    customer_one = await _create_customer_for_tenant(db_session, "Alpha Office", tenant_id)
    customer_two = await _create_customer_for_tenant(db_session, "Bravo Print", tenant_id)
    customer_three = await _create_customer_for_tenant(db_session, "Charlie Ship", tenant_id)
    customer_four = await _create_customer_for_tenant(db_session, "Delta Supply", tenant_id)
    printer_ink = await _create_product_for_tenant(db_session, "Printer Ink", "Supplies", tenant_id)
    toner = await _create_product_for_tenant(db_session, "Laser Toner", "Supplies", tenant_id)
    labels = await _create_product_for_tenant(db_session, "Shipping Labels", "Office", tenant_id)
    now = datetime.now(tz=UTC)

    await _create_order(
        db_session,
        customer=customer_one,
        created_at=now - timedelta(days=10),
        status="confirmed",
        lines=[(printer_ink, Decimal("100.00"))],
        tenant_id=tenant_id,
    )
    await _create_order(
        db_session,
        customer=customer_one,
        created_at=now - timedelta(days=9),
        status="shipped",
        lines=[(toner, Decimal("80.00"))],
        tenant_id=tenant_id,
    )
    await _create_order(
        db_session,
        customer=customer_two,
        created_at=now - timedelta(days=8),
        status="fulfilled",
        lines=[(printer_ink, Decimal("100.00")), (toner, Decimal("80.00"))],
        tenant_id=tenant_id,
    )
    await _create_order(
        db_session,
        customer=customer_three,
        created_at=now - timedelta(days=7),
        status="confirmed",
        lines=[(printer_ink, Decimal("100.00")), (labels, Decimal("40.00"))],
        tenant_id=tenant_id,
    )
    await _create_order(
        db_session,
        customer=customer_four,
        created_at=now - timedelta(days=6),
        status="confirmed",
        lines=[(toner, Decimal("80.00")), (labels, Decimal("40.00"))],
        tenant_id=tenant_id,
    )
    await db_session.commit()

    affinity_map = await get_product_affinity_map(db_session, tenant_id, min_shared=1, limit=10)

    assert affinity_map.total == 3
    assert affinity_map.min_shared == 1
    assert affinity_map.limit == 10
    assert len(affinity_map.pairs) == 3
    top_pair = affinity_map.pairs[0]
    assert {top_pair.product_a_name, top_pair.product_b_name} == {"Laser Toner", "Printer Ink"}
    assert top_pair.shared_customer_count == 2
    assert top_pair.customer_count_a == 3
    assert top_pair.customer_count_b == 3
    assert top_pair.shared_order_count == 1
    assert top_pair.overlap_pct == pytest.approx(66.67, abs=0.01)
    assert top_pair.affinity_score == pytest.approx(0.5, abs=0.0001)
    assert "Bundle pitch recommended" in top_pair.pitch_hint
    assert {
        frozenset((pair.product_a_name, pair.product_b_name))
        for pair in affinity_map.pairs
    } == {
        frozenset(("Laser Toner", "Printer Ink")),
        frozenset(("Printer Ink", "Shipping Labels")),
        frozenset(("Laser Toner", "Shipping Labels")),
    }


@pytest.mark.asyncio
async def test_get_product_affinity_map_is_tenant_isolated(db_session: AsyncSession) -> None:
    tenant_id = uuid.uuid4()
    other_tenant = uuid.uuid4()
    customer = await _create_customer_for_tenant(db_session, "Tenant A", tenant_id)
    product_a = await _create_product_for_tenant(db_session, "Core Paper", "Office", tenant_id)
    product_b = await _create_product_for_tenant(db_session, "Staples", "Office", tenant_id)
    now = datetime.now(tz=UTC)

    await _create_order(
        db_session,
        customer=customer,
        created_at=now - timedelta(days=5),
        status="confirmed",
        lines=[(product_a, Decimal("20.00")), (product_b, Decimal("10.00"))],
        tenant_id=tenant_id,
    )

    tenant_b_business_number = await _next_business_number(db_session, other_tenant)
    tenant_b_customer = Customer(
        id=uuid.uuid4(),
        tenant_id=other_tenant,
        company_name="Tenant B",
        normalized_business_number=tenant_b_business_number,
        billing_address="Kaohsiung",
        contact_name="Owner",
        contact_phone="0911222333",
        contact_email=f"{uuid.uuid4().hex[:8]}@tenant-b.example.com",
        credit_limit=Decimal("100000.00"),
        status="active",
        version=1,
    )
    tenant_b_product_a = Product(
        id=uuid.uuid4(),
        tenant_id=other_tenant,
        code=f"P-{uuid.uuid4().hex[:6].upper()}",
        name="Forklift Battery",
        category="Warehouse",
        status="active",
        unit="pcs",
    )
    tenant_b_product_b = Product(
        id=uuid.uuid4(),
        tenant_id=other_tenant,
        code=f"P-{uuid.uuid4().hex[:6].upper()}",
        name="Forklift Charger",
        category="Warehouse",
        status="active",
        unit="pcs",
    )
    db_session.add_all([tenant_b_customer, tenant_b_product_a, tenant_b_product_b])
    await db_session.flush()
    tenant_b_order = Order(
        id=uuid.uuid4(),
        tenant_id=other_tenant,
        customer_id=tenant_b_customer.id,
        order_number=f"ORD-{uuid.uuid4().hex[:8].upper()}",
        status="confirmed",
        payment_terms_code="NET_30",
        payment_terms_days=30,
        subtotal_amount=Decimal("250.00"),
        discount_amount=Decimal("0.00"),
        discount_percent=Decimal("0.0000"),
        tax_amount=Decimal("0.00"),
        total_amount=Decimal("250.00"),
        notes=None,
        created_by="test-suite",
        created_at=now - timedelta(days=4),
        updated_at=now - timedelta(days=4),
        confirmed_at=now - timedelta(days=4),
    )
    db_session.add(tenant_b_order)
    await db_session.flush()
    db_session.add_all([
        OrderLine(
            id=uuid.uuid4(),
            tenant_id=other_tenant,
            order_id=tenant_b_order.id,
            product_id=tenant_b_product_a.id,
            line_number=1,
            quantity=Decimal("1.000"),
            list_unit_price=Decimal("200.00"),
            unit_price=Decimal("200.00"),
            unit_cost=None,
            discount_amount=Decimal("0.00"),
            tax_policy_code="standard",
            tax_type=1,
            tax_rate=Decimal("0.0000"),
            tax_amount=Decimal("0.00"),
            subtotal_amount=Decimal("200.00"),
            total_amount=Decimal("200.00"),
            description=tenant_b_product_a.name,
        ),
        OrderLine(
            id=uuid.uuid4(),
            tenant_id=other_tenant,
            order_id=tenant_b_order.id,
            product_id=tenant_b_product_b.id,
            line_number=2,
            quantity=Decimal("1.000"),
            list_unit_price=Decimal("50.00"),
            unit_price=Decimal("50.00"),
            unit_cost=None,
            discount_amount=Decimal("0.00"),
            tax_policy_code="standard",
            tax_type=1,
            tax_rate=Decimal("0.0000"),
            tax_amount=Decimal("0.00"),
            subtotal_amount=Decimal("50.00"),
            total_amount=Decimal("50.00"),
            description=tenant_b_product_b.name,
        ),
    ])
    await db_session.commit()

    affinity_map = await get_product_affinity_map(db_session, tenant_id, min_shared=1, limit=10)

    assert affinity_map.total == 1
    assert len(affinity_map.pairs) == 1
    assert {affinity_map.pairs[0].product_a_name, affinity_map.pairs[0].product_b_name} == {
        "Core Paper",
        "Staples",
    }


@pytest.mark.asyncio
async def test_get_product_affinity_map_returns_empty_without_orders(db_session: AsyncSession) -> None:
    tenant_id = uuid.uuid4()
    affinity_map = await get_product_affinity_map(db_session, tenant_id, min_shared=2, limit=5)

    assert affinity_map == affinity_map.model_copy(update={"computed_at": affinity_map.computed_at})
    assert affinity_map.pairs == []
    assert affinity_map.total == 0
    assert affinity_map.min_shared == 2
    assert affinity_map.limit == 5


@pytest.mark.asyncio
async def test_get_product_affinity_map_orders_near_ties_by_rounded_score_then_shared_customers(
    db_session: AsyncSession,
) -> None:
    tenant_id = uuid.uuid4()
    now = datetime.now(tz=UTC)
    pair_one_a = await _create_product_for_tenant(db_session, "Pair One A", "Office", tenant_id)
    pair_one_b = await _create_product_for_tenant(db_session, "Pair One B", "Office", tenant_id)
    pair_two_a = await _create_product_for_tenant(db_session, "Pair Two A", "Office", tenant_id)
    pair_two_b = await _create_product_for_tenant(db_session, "Pair Two B", "Office", tenant_id)

    async def seed_pair(
        prefix: str,
        product_a: Product,
        product_b: Product,
        *,
        shared_count: int,
        a_only_count: int,
        b_only_count: int,
    ) -> None:
        for index in range(shared_count):
            customer = await _create_customer_for_tenant(db_session, f"{prefix} Shared {index}", tenant_id)
            await _create_order(
                db_session,
                customer=customer,
                created_at=now - timedelta(days=10),
                status="confirmed",
                lines=[(product_a, Decimal("10.00")), (product_b, Decimal("10.00"))],
                tenant_id=tenant_id,
            )
        for index in range(a_only_count):
            customer = await _create_customer_for_tenant(db_session, f"{prefix} A Only {index}", tenant_id)
            await _create_order(
                db_session,
                customer=customer,
                created_at=now - timedelta(days=9),
                status="confirmed",
                lines=[(product_a, Decimal("10.00"))],
                tenant_id=tenant_id,
            )
        for index in range(b_only_count):
            customer = await _create_customer_for_tenant(db_session, f"{prefix} B Only {index}", tenant_id)
            await _create_order(
                db_session,
                customer=customer,
                created_at=now - timedelta(days=8),
                status="confirmed",
                lines=[(product_b, Decimal("10.00"))],
                tenant_id=tenant_id,
            )

    await seed_pair(
        "Pair One",
        pair_one_a,
        pair_one_b,
        shared_count=100,
        a_only_count=98,
        b_only_count=99,
    )
    await seed_pair(
        "Pair Two",
        pair_two_a,
        pair_two_b,
        shared_count=101,
        a_only_count=99,
        b_only_count=100,
    )
    await db_session.commit()

    affinity_map = await get_product_affinity_map(db_session, tenant_id, min_shared=1, limit=1)

    assert affinity_map.total == 2
    assert len(affinity_map.pairs) == 1
    top_pair = affinity_map.pairs[0]
    assert {top_pair.product_a_name, top_pair.product_b_name} == {"Pair Two A", "Pair Two B"}
    assert top_pair.shared_customer_count == 101
    assert top_pair.affinity_score == pytest.approx(0.3367, abs=0.0001)


@pytest.mark.asyncio
async def test_get_product_affinity_map_emits_half_up_affinity_scores_at_rounding_boundaries(
    db_session: AsyncSession,
) -> None:
    tenant_id = uuid.uuid4()
    now = datetime.now(tz=UTC)
    product_a = await _create_product_for_tenant(db_session, "Boundary A", "Office", tenant_id)
    product_b = await _create_product_for_tenant(db_session, "Boundary B", "Office", tenant_id)

    await _seed_affinity_orders(
        db_session,
        tenant_id=tenant_id,
        product_a=product_a,
        product_b=product_b,
        now=now,
        shared_count=1333,
        a_only_count=1333,
        b_only_count=1334,
        prefix="Boundary",
    )
    await db_session.commit()

    affinity_map = await get_product_affinity_map(db_session, tenant_id, min_shared=1, limit=10)

    assert affinity_map.total == 1
    assert len(affinity_map.pairs) == 1
    assert affinity_map.pairs[0].shared_customer_count == 1333
    assert affinity_map.pairs[0].affinity_score == pytest.approx(0.3333, abs=0.0001)


@pytest.mark.asyncio
async def test_get_category_trends_returns_ranked_period_metrics(db_session: AsyncSession) -> None:
    tenant_id = uuid.uuid4()
    now = datetime.now(tz=UTC)
    customer_one = await _create_customer_for_tenant(db_session, "Alpha Office", tenant_id)
    customer_two = await _create_customer_for_tenant(db_session, "Bravo Print", tenant_id)
    customer_three = await _create_customer_for_tenant(db_session, "Charlie Retail", tenant_id)
    customer_four = await _create_customer_for_tenant(db_session, "Delta Sales", tenant_id)
    supplies_one = await _create_product_for_tenant(db_session, "Printer Ink", "Supplies", tenant_id)
    supplies_two = await _create_product_for_tenant(db_session, "Laser Toner", "Supplies", tenant_id)
    office_product = await _create_product_for_tenant(db_session, "Desk Tray", "Office", tenant_id)
    display_product = await _create_product_for_tenant(db_session, "LED Panel", "Displays", tenant_id)
    uncategorized = await _create_product_for_tenant(db_session, "Mystery Item", None, tenant_id)

    await _create_order(
        db_session,
        customer=customer_one,
        created_at=now - timedelta(days=20),
        status="confirmed",
        lines=[(supplies_one, Decimal("120.00"))],
        tenant_id=tenant_id,
    )
    await _create_order(
        db_session,
        customer=customer_two,
        created_at=now - timedelta(days=15),
        status="fulfilled",
        lines=[(supplies_two, Decimal("180.00"))],
        tenant_id=tenant_id,
    )
    await _create_order(
        db_session,
        customer=customer_one,
        created_at=now - timedelta(days=120),
        status="shipped",
        lines=[(supplies_one, Decimal("100.00"))],
        tenant_id=tenant_id,
    )
    await _create_order(
        db_session,
        customer=customer_three,
        created_at=now - timedelta(days=110),
        status="confirmed",
        lines=[(office_product, Decimal("150.00"))],
        tenant_id=tenant_id,
    )
    await _create_order(
        db_session,
        customer=customer_four,
        created_at=now - timedelta(days=12),
        status="confirmed",
        lines=[(display_product, Decimal("90.00")), (uncategorized, Decimal("5.00"))],
        tenant_id=tenant_id,
    )
    await db_session.commit()

    trends = await get_category_trends(db_session, tenant_id, period="last_90d")

    assert trends.period == "last_90d"
    assert [trend.category for trend in trends.trends] == ["Supplies", "Office", "Displays"]

    supplies = trends.trends[0]
    assert supplies.current_period_revenue == Decimal("300.00")
    assert supplies.prior_period_revenue == Decimal("100.00")
    assert supplies.revenue_delta_pct == pytest.approx(200.0, abs=0.01)
    assert supplies.current_period_orders == 2
    assert supplies.prior_period_orders == 1
    assert supplies.customer_count == 2
    assert supplies.prior_customer_count == 1
    assert supplies.new_customer_count == 1
    assert supplies.churned_customer_count == 0
    assert supplies.trend == "growing"
    assert [product.product_name for product in supplies.top_products] == ["Laser Toner", "Printer Ink"]

    office = trends.trends[1]
    assert office.current_period_revenue == Decimal("0.00")
    assert office.prior_period_revenue == Decimal("150.00")
    assert office.revenue_delta_pct == pytest.approx(-100.0, abs=0.01)
    assert office.trend == "declining"
    assert office.churned_customer_count == 1

    displays = trends.trends[2]
    assert displays.revenue_delta_pct is None
    assert displays.trend_context == "newly_active"
    assert displays.new_customer_count == 1
    assert displays.trend == "stable"


@pytest.mark.asyncio
async def test_get_category_trends_excludes_non_merchandise_rows(db_session: AsyncSession) -> None:
    tenant_id = uuid.uuid4()
    now = datetime.now(tz=UTC)
    customer = await _create_customer_for_tenant(db_session, "Belt Buyer", tenant_id)
    belt_product = await _create_product_for_tenant(db_session, "Drive Belt", "V-Belts", tenant_id)
    freight_product = await _create_product_for_tenant(
        db_session,
        "Freight Charge",
        "Non-Merchandise",
        tenant_id,
    )

    await _create_order(
        db_session,
        customer=customer,
        created_at=now - timedelta(days=7),
        status="confirmed",
        lines=[
            (belt_product, Decimal("120.00")),
            (freight_product, Decimal("15.00")),
        ],
        tenant_id=tenant_id,
    )
    await db_session.commit()

    trends = await get_category_trends(db_session, tenant_id, period="last_30d")

    assert [trend.category for trend in trends.trends] == ["V-Belts"]
    assert trends.trends[0].current_period_revenue == Decimal("120.00")


@pytest.mark.asyncio
async def test_get_category_trends_excludes_future_rows_and_ranks_newly_active_by_current_revenue(
    db_session: AsyncSession,
) -> None:
    tenant_id = uuid.uuid4()
    now = datetime.now(tz=UTC)
    customer = await _create_customer_for_tenant(db_session, "Forecast Retail", tenant_id)
    alpha = await _create_product_for_tenant(db_session, "Alpha Product", "Alpha", tenant_id)
    zulu = await _create_product_for_tenant(db_session, "Zulu Product", "Zulu", tenant_id)

    await _create_order(
        db_session,
        customer=customer,
        created_at=now - timedelta(days=10),
        status="confirmed",
        lines=[(zulu, Decimal("200.00"))],
        tenant_id=tenant_id,
    )
    await _create_order(
        db_session,
        customer=customer,
        created_at=now - timedelta(days=12),
        status="confirmed",
        lines=[(alpha, Decimal("100.00"))],
        tenant_id=tenant_id,
    )
    await _create_order(
        db_session,
        customer=customer,
        created_at=now + timedelta(days=2),
        status="confirmed",
        lines=[(alpha, Decimal("900.00"))],
        tenant_id=tenant_id,
    )
    await db_session.commit()

    trends = await get_category_trends(db_session, tenant_id, period="last_30d")

    assert [trend.category for trend in trends.trends] == ["Zulu", "Alpha"]
    assert trends.trends[0].current_period_revenue == Decimal("200.00")
    assert trends.trends[1].current_period_revenue == Decimal("100.00")


@pytest.mark.asyncio
async def test_get_category_trends_uses_confirmation_time_for_committed_orders(
    db_session: AsyncSession,
) -> None:
    tenant_id = uuid.uuid4()
    now = datetime.now(tz=UTC)
    customer = await _create_customer_for_tenant(db_session, "Timing Buyer", tenant_id)
    product = await _create_product_for_tenant(db_session, "Printer Ink", "Supplies", tenant_id)

    await _create_order(
        db_session,
        customer=customer,
        created_at=now - timedelta(days=45),
        confirmed_at=now - timedelta(days=5),
        status="confirmed",
        lines=[(product, Decimal("120.00"))],
        tenant_id=tenant_id,
    )
    await _create_order(
        db_session,
        customer=customer,
        created_at=now - timedelta(days=4),
        status="pending",
        lines=[(product, Decimal("900.00"))],
        tenant_id=tenant_id,
    )
    await db_session.commit()

    trends = await get_category_trends(db_session, tenant_id, period="last_30d")

    assert len(trends.trends) == 1
    assert trends.trends[0].category == "Supplies"
    assert trends.trends[0].current_period_revenue == Decimal("120.00")
    assert trends.trends[0].current_period_orders == 1
    assert trends.trends[0].customer_count == 1


@pytest.mark.asyncio
async def test_get_category_trends_is_tenant_isolated(db_session: AsyncSession) -> None:
    tenant_id = uuid.uuid4()
    other_tenant = uuid.uuid4()
    customer = await _create_customer_for_tenant(db_session, "Tenant A", tenant_id)
    product = await _create_product_for_tenant(db_session, "Printer Ink", "Supplies", tenant_id)
    now = datetime.now(tz=UTC)

    await _create_order(
        db_session,
        customer=customer,
        created_at=now - timedelta(days=10),
        status="confirmed",
        lines=[(product, Decimal("75.00"))],
        tenant_id=tenant_id,
    )

    other_customer = await _create_customer_for_tenant(db_session, "Tenant B", other_tenant)
    other_product = await _create_product_for_tenant(db_session, "Forklift Battery", "Warehouse", other_tenant)
    await _create_order(
        db_session,
        customer=other_customer,
        created_at=now - timedelta(days=8),
        status="confirmed",
        lines=[(other_product, Decimal("500.00"))],
        tenant_id=other_tenant,
    )
    await db_session.commit()

    trends = await get_category_trends(db_session, tenant_id, period="last_30d")

    assert [trend.category for trend in trends.trends] == ["Supplies"]


@pytest.mark.asyncio
async def test_get_category_trends_returns_empty_without_orders(db_session: AsyncSession) -> None:
    tenant_id = uuid.uuid4()

    trends = await get_category_trends(db_session, tenant_id, period="last_30d")

    assert trends.period == "last_30d"
    assert trends.trends == []


@pytest.mark.asyncio
async def test_get_customer_risk_signals_classifies_and_sorts_accounts(db_session: AsyncSession) -> None:
    tenant_id = uuid.uuid4()
    now = datetime.now(tz=UTC)
    dormant = await _create_customer_for_tenant(db_session, "Dormant Co", tenant_id)
    at_risk = await _create_customer_for_tenant(db_session, "At Risk Co", tenant_id)
    growing = await _create_customer_for_tenant(db_session, "Growing Co", tenant_id)
    stable = await _create_customer_for_tenant(db_session, "Stable Co", tenant_id)
    new_account = await _create_customer_for_tenant(db_session, "New Co", tenant_id)

    supplies = await _create_product_for_tenant(db_session, "Printer Ink", "Supplies", tenant_id)
    office = await _create_product_for_tenant(db_session, "Desk Tray", "Office", tenant_id)
    display = await _create_product_for_tenant(db_session, "LED Panel", "Displays", tenant_id)

    await _create_order(
        db_session,
        customer=dormant,
        created_at=now - timedelta(days=80),
        status="confirmed",
        lines=[(supplies, Decimal("300.00"))],
        tenant_id=tenant_id,
    )
    await _create_order(
        db_session,
        customer=dormant,
        created_at=now - timedelta(days=430),
        status="confirmed",
        lines=[(office, Decimal("400.00"))],
        tenant_id=tenant_id,
    )

    await _create_order(
        db_session,
        customer=at_risk,
        created_at=now - timedelta(days=30),
        status="confirmed",
        lines=[(supplies, Decimal("80.00"))],
        tenant_id=tenant_id,
    )
    await _create_order(
        db_session,
        customer=at_risk,
        created_at=now - timedelta(days=400),
        status="confirmed",
        lines=[(supplies, Decimal("250.00")), (office, Decimal("50.00"))],
        tenant_id=tenant_id,
    )

    await _create_order(
        db_session,
        customer=growing,
        created_at=now - timedelta(days=20),
        status="confirmed",
        lines=[(supplies, Decimal("260.00")), (display, Decimal("60.00"))],
        tenant_id=tenant_id,
    )
    await _create_order(
        db_session,
        customer=growing,
        created_at=now - timedelta(days=390),
        status="confirmed",
        lines=[(supplies, Decimal("120.00"))],
        tenant_id=tenant_id,
    )

    await _create_order(
        db_session,
        customer=stable,
        created_at=now - timedelta(days=15),
        status="confirmed",
        lines=[(office, Decimal("220.00"))],
        tenant_id=tenant_id,
    )
    await _create_order(
        db_session,
        customer=stable,
        created_at=now - timedelta(days=380),
        status="confirmed",
        lines=[(office, Decimal("200.00"))],
        tenant_id=tenant_id,
    )

    await _create_order(
        db_session,
        customer=new_account,
        created_at=now - timedelta(days=25),
        status="confirmed",
        lines=[(display, Decimal("90.00"))],
        tenant_id=tenant_id,
    )
    await db_session.commit()

    risk_signals = await get_customer_risk_signals(db_session, tenant_id, status_filter="all", limit=50)

    assert [customer.company_name for customer in risk_signals.customers] == [
        "Dormant Co",
        "At Risk Co",
        "Growing Co",
        "Stable Co",
        "New Co",
    ]

    dormant_signal = risk_signals.customers[0]
    assert dormant_signal.status == "dormant"
    assert dormant_signal.days_since_last_order == 80
    assert "dormant_60d" in dormant_signal.reason_codes

    at_risk_signal = risk_signals.customers[1]
    assert at_risk_signal.status == "at_risk"
    assert at_risk_signal.revenue_delta_pct == pytest.approx(-73.3, abs=0.1)
    assert "category_contraction" in at_risk_signal.reason_codes
    assert at_risk_signal.products_contracted_from == ["Office"]

    growing_signal = risk_signals.customers[2]
    assert growing_signal.status == "growing"
    assert growing_signal.products_expanded_into == ["Displays"]
    assert "revenue up 167%" in growing_signal.signals

    stable_signal = risk_signals.customers[3]
    assert stable_signal.status == "stable"

    new_signal = risk_signals.customers[4]
    assert new_signal.status == "new"
    assert "new_account_90d" in new_signal.reason_codes


@pytest.mark.asyncio
async def test_get_customer_risk_signals_filters_and_limits(db_session: AsyncSession) -> None:
    tenant_id = uuid.uuid4()
    now = datetime.now(tz=UTC)
    customer = await _create_customer_for_tenant(db_session, "Growing Co", tenant_id)
    product = await _create_product_for_tenant(db_session, "Printer Ink", "Supplies", tenant_id)

    await _create_order(
        db_session,
        customer=customer,
        created_at=now - timedelta(days=20),
        status="confirmed",
        lines=[(product, Decimal("240.00"))],
        tenant_id=tenant_id,
    )
    await _create_order(
        db_session,
        customer=customer,
        created_at=now - timedelta(days=390),
        status="confirmed",
        lines=[(product, Decimal("100.00"))],
        tenant_id=tenant_id,
    )
    await db_session.commit()

    risk_signals = await get_customer_risk_signals(db_session, tenant_id, status_filter="growing", limit=1)

    assert risk_signals.total == 1
    assert len(risk_signals.customers) == 1
    assert risk_signals.customers[0].status == "growing"


@pytest.mark.asyncio
async def test_get_customer_risk_signals_is_tenant_isolated(db_session: AsyncSession) -> None:
    tenant_id = uuid.uuid4()
    other_tenant = uuid.uuid4()
    now = datetime.now(tz=UTC)
    customer = await _create_customer_for_tenant(db_session, "Tenant A", tenant_id)
    product = await _create_product_for_tenant(db_session, "Printer Ink", "Supplies", tenant_id)
    other_customer = await _create_customer_for_tenant(db_session, "Tenant B", other_tenant)
    other_product = await _create_product_for_tenant(db_session, "Forklift Battery", "Warehouse", other_tenant)

    await _create_order(
        db_session,
        customer=customer,
        created_at=now - timedelta(days=30),
        status="confirmed",
        lines=[(product, Decimal("120.00"))],
        tenant_id=tenant_id,
    )
    await _create_order(
        db_session,
        customer=other_customer,
        created_at=now - timedelta(days=20),
        status="confirmed",
        lines=[(other_product, Decimal("900.00"))],
        tenant_id=other_tenant,
    )
    await db_session.commit()

    risk_signals = await get_customer_risk_signals(db_session, tenant_id, status_filter="all", limit=50)

    assert [customer.company_name for customer in risk_signals.customers] == ["Tenant A"]


@pytest.mark.asyncio
async def test_get_customer_risk_signals_marks_no_order_customers_dormant_and_suppresses_sparse_expansion(
    db_session: AsyncSession,
) -> None:
    tenant_id = uuid.uuid4()
    now = datetime.now(tz=UTC)
    no_order = await _create_customer_for_tenant(db_session, "No Order Co", tenant_id)
    sparse = await _create_customer_for_tenant(db_session, "Sparse Co", tenant_id)
    product = await _create_product_for_tenant(db_session, "Printer Ink", "Supplies", tenant_id)

    await _create_order(
        db_session,
        customer=sparse,
        created_at=now - timedelta(days=100),
        status="confirmed",
        lines=[(product, Decimal("120.00"))],
        tenant_id=tenant_id,
    )
    await _create_order(
        db_session,
        customer=sparse,
        created_at=now - timedelta(days=40),
        status="confirmed",
        lines=[(product, Decimal("80.00"))],
        tenant_id=tenant_id,
    )
    await db_session.commit()

    risk_signals = await get_customer_risk_signals(db_session, tenant_id, status_filter="all", limit=50)
    by_name = {customer.company_name: customer for customer in risk_signals.customers}

    assert by_name["No Order Co"].status == "dormant"
    assert by_name["Sparse Co"].products_expanded_into == []
    assert by_name["Sparse Co"].products_contracted_from == []
    assert "sparse_prior_history" in by_name["Sparse Co"].reason_codes


@pytest.mark.asyncio
async def test_get_prospect_gaps_returns_ranked_non_buyers_for_category(db_session: AsyncSession) -> None:
    tenant_id = uuid.uuid4()
    now = datetime.now(tz=UTC)
    buyer_one = await _create_customer_for_tenant(db_session, "Electro Buyer A", tenant_id)
    buyer_two = await _create_customer_for_tenant(db_session, "Electro Buyer B", tenant_id)
    warm = await _create_customer_for_tenant(db_session, "Warm Prospect", tenant_id)
    cold = await _create_customer_for_tenant(db_session, "Cold Prospect", tenant_id)

    electronics = await _create_product_for_tenant(db_session, "LED Panel", "Electronics", tenant_id)
    supplies = await _create_product_for_tenant(db_session, "Printer Ink", "Supplies", tenant_id)
    accessories = await _create_product_for_tenant(db_session, "Cable Set", "Accessories", tenant_id)
    office = await _create_product_for_tenant(db_session, "Desk Tray", "Office", tenant_id)

    await _create_order(
        db_session,
        customer=buyer_one,
        created_at=now - timedelta(days=25),
        status="confirmed",
        lines=[(electronics, Decimal("300.00")), (supplies, Decimal("80.00"))],
        tenant_id=tenant_id,
    )
    await _create_order(
        db_session,
        customer=buyer_two,
        created_at=now - timedelta(days=35),
        status="confirmed",
        lines=[(electronics, Decimal("200.00")), (accessories, Decimal("60.00"))],
        tenant_id=tenant_id,
    )
    await _create_order(
        db_session,
        customer=warm,
        created_at=now - timedelta(days=20),
        status="confirmed",
        lines=[(supplies, Decimal("180.00")), (accessories, Decimal("120.00"))],
        tenant_id=tenant_id,
    )
    await _create_order(
        db_session,
        customer=warm,
        created_at=now - timedelta(days=70),
        status="confirmed",
        lines=[(supplies, Decimal("150.00"))],
        tenant_id=tenant_id,
    )
    await _create_order(
        db_session,
        customer=cold,
        created_at=now - timedelta(days=45),
        status="confirmed",
        lines=[(office, Decimal("90.00"))],
        tenant_id=tenant_id,
    )
    await db_session.commit()

    gaps = await get_prospect_gaps(db_session, tenant_id, category="Electronics", limit=20)

    assert gaps.target_category == "Electronics"
    assert gaps.existing_buyers_count == 2
    assert gaps.target_category_revenue == Decimal("500.00")
    assert gaps.prospects_count == 2
    assert [prospect.company_name for prospect in gaps.prospects] == ["Warm Prospect", "Cold Prospect"]
    assert gaps.prospects[0].affinity_score > gaps.prospects[1].affinity_score
    assert "adjacent_category_support" in gaps.prospects[0].reason_codes
    assert "adjacent_category" in gaps.prospects[0].tags
    assert gaps.prospects[0].score_components.adjacent_category_support > 0
    assert gaps.prospects[0].score_components.breadth_similarity > 0
    assert gaps.prospects[0].score_components.recency_factor > 0
    prospect_payload = gaps.prospects[0].model_dump(mode="json")
    assert "score_components" in prospect_payload
    assert prospect_payload["confidence"] in {"high", "medium", "low"}
    assert "contact_phone" not in prospect_payload
    assert "contact_email" not in prospect_payload


@pytest.mark.asyncio
async def test_get_prospect_gaps_excludes_zero_order_customers_and_caps_limit(db_session: AsyncSession) -> None:
    tenant_id = uuid.uuid4()
    now = datetime.now(tz=UTC)
    buyer = await _create_customer_for_tenant(db_session, "Buyer", tenant_id)
    active = await _create_customer_for_tenant(db_session, "Active Prospect", tenant_id)
    inactive = await _create_customer_for_tenant(db_session, "No Orders", tenant_id)
    electronics = await _create_product_for_tenant(db_session, "LED Panel", "Electronics", tenant_id)
    supplies = await _create_product_for_tenant(db_session, "Printer Ink", "Supplies", tenant_id)

    await _create_order(
        db_session,
        customer=buyer,
        created_at=now - timedelta(days=15),
        status="confirmed",
        lines=[(electronics, Decimal("220.00"))],
        tenant_id=tenant_id,
    )
    await _create_order(
        db_session,
        customer=active,
        created_at=now - timedelta(days=25),
        status="confirmed",
        lines=[(supplies, Decimal("90.00"))],
        tenant_id=tenant_id,
    )
    await db_session.commit()

    gaps = await get_prospect_gaps(db_session, tenant_id, category="Electronics", limit=999)

    assert gaps.prospects_count == 1
    assert len(gaps.prospects) == 1
    assert gaps.prospects[0].company_name == "Active Prospect"
    assert inactive.company_name not in [prospect.company_name for prospect in gaps.prospects]


@pytest.mark.asyncio
async def test_get_prospect_gaps_is_tenant_isolated(db_session: AsyncSession) -> None:
    tenant_id = uuid.uuid4()
    other_tenant = uuid.uuid4()
    now = datetime.now(tz=UTC)
    buyer = await _create_customer_for_tenant(db_session, "Buyer", tenant_id)
    prospect = await _create_customer_for_tenant(db_session, "Prospect", tenant_id)
    other_customer = await _create_customer_for_tenant(db_session, "Other Prospect", other_tenant)
    electronics = await _create_product_for_tenant(db_session, "LED Panel", "Electronics", tenant_id)
    supplies = await _create_product_for_tenant(db_session, "Printer Ink", "Supplies", tenant_id)
    other_supplies = await _create_product_for_tenant(db_session, "Forklift Battery", "Supplies", other_tenant)

    await _create_order(
        db_session,
        customer=buyer,
        created_at=now - timedelta(days=20),
        status="confirmed",
        lines=[(electronics, Decimal("300.00"))],
        tenant_id=tenant_id,
    )
    await _create_order(
        db_session,
        customer=prospect,
        created_at=now - timedelta(days=25),
        status="confirmed",
        lines=[(supplies, Decimal("140.00"))],
        tenant_id=tenant_id,
    )
    await _create_order(
        db_session,
        customer=other_customer,
        created_at=now - timedelta(days=25),
        status="confirmed",
        lines=[(other_supplies, Decimal("900.00"))],
        tenant_id=other_tenant,
    )
    await db_session.commit()

    gaps = await get_prospect_gaps(db_session, tenant_id, category="Electronics", limit=20)

    assert [prospect.company_name for prospect in gaps.prospects] == ["Prospect"]


@pytest.mark.asyncio
async def test_get_prospect_gaps_uses_all_adjacent_categories_and_skips_excluded_only_customers(
    db_session: AsyncSession,
) -> None:
    tenant_id = uuid.uuid4()
    now = datetime.now(tz=UTC)
    buyer = await _create_customer_for_tenant(db_session, "Buyer", tenant_id)
    adjacent_prospect = await _create_customer_for_tenant(db_session, "Adjacent Prospect", tenant_id)
    excluded_only = await _create_customer_for_tenant(db_session, "Service Only", tenant_id)

    electronics = await _create_product_for_tenant(db_session, "LED Panel", "Electronics", tenant_id)
    cat_a = await _create_product_for_tenant(db_session, "Cable Set", "Accessories", tenant_id)
    cat_b = await _create_product_for_tenant(db_session, "Printer Ink", "Supplies", tenant_id)
    cat_c = await _create_product_for_tenant(db_session, "Desk Tray", "Office", tenant_id)
    cat_d = await _create_product_for_tenant(db_session, "Router", "Networking", tenant_id)
    service = await _create_product_for_tenant(db_session, "Install Fee", "Services", tenant_id)

    await _create_order(
        db_session,
        customer=buyer,
        created_at=now - timedelta(days=20),
        status="confirmed",
        lines=[
            (electronics, Decimal("200.00")),
            (cat_a, Decimal("20.00")),
            (cat_b, Decimal("20.00")),
            (cat_c, Decimal("20.00")),
            (cat_d, Decimal("20.00")),
        ],
        tenant_id=tenant_id,
    )
    await _create_order(
        db_session,
        customer=adjacent_prospect,
        created_at=now - timedelta(days=15),
        status="confirmed",
        lines=[(cat_d, Decimal("120.00"))],
        tenant_id=tenant_id,
    )
    await _create_order(
        db_session,
        customer=excluded_only,
        created_at=now - timedelta(days=10),
        status="confirmed",
        lines=[(service, Decimal("90.00"))],
        tenant_id=tenant_id,
    )
    await db_session.commit()

    gaps = await get_prospect_gaps(db_session, tenant_id, category="Electronics", limit=20)

    assert [prospect.company_name for prospect in gaps.prospects] == ["Adjacent Prospect"]
    assert "adjacent_category" in gaps.prospects[0].tags


@pytest.mark.asyncio
async def test_get_prospect_gaps_filters_by_customer_type(db_session: AsyncSession) -> None:
    tenant_id = uuid.uuid4()
    now = datetime.now(tz=UTC)
    dealer_buyer = await _create_customer_for_tenant(
        db_session,
        "Dealer Buyer",
        tenant_id,
        customer_type="dealer",
    )
    dealer_prospect = await _create_customer_for_tenant(
        db_session,
        "Dealer Prospect",
        tenant_id,
        customer_type="dealer",
    )
    end_user_buyer = await _create_customer_for_tenant(
        db_session,
        "End User Buyer",
        tenant_id,
        customer_type="end_user",
    )
    end_user_prospect = await _create_customer_for_tenant(
        db_session,
        "End User Prospect",
        tenant_id,
        customer_type="end_user",
    )

    target_category = await _create_product_for_tenant(db_session, "Target Belt", "Supplies", tenant_id)
    adjacent_category = await _create_product_for_tenant(db_session, "Adjacent Belt", "V-Belts", tenant_id)

    await _create_order(
        db_session,
        customer=dealer_buyer,
        created_at=now - timedelta(days=10),
        status="confirmed",
        lines=[(target_category, Decimal("250.00")), (adjacent_category, Decimal("120.00"))],
        tenant_id=tenant_id,
    )
    await _create_order(
        db_session,
        customer=dealer_prospect,
        created_at=now - timedelta(days=15),
        status="confirmed",
        lines=[(adjacent_category, Decimal("180.00"))],
        tenant_id=tenant_id,
    )
    await _create_order(
        db_session,
        customer=end_user_buyer,
        created_at=now - timedelta(days=12),
        status="confirmed",
        lines=[(target_category, Decimal("90.00")), (adjacent_category, Decimal("50.00"))],
        tenant_id=tenant_id,
    )
    await _create_order(
        db_session,
        customer=end_user_prospect,
        created_at=now - timedelta(days=18),
        status="confirmed",
        lines=[(adjacent_category, Decimal("70.00"))],
        tenant_id=tenant_id,
    )
    await db_session.commit()

    dealer_gaps = await get_prospect_gaps(
        db_session,
        tenant_id,
        category="Supplies",
        customer_type="dealer",
        limit=20,
    )
    end_user_gaps = await get_prospect_gaps(
        db_session,
        tenant_id,
        category="Supplies",
        customer_type="end_user",
        limit=20,
    )

    assert dealer_gaps.existing_buyers_count == 1
    assert [prospect.company_name for prospect in dealer_gaps.prospects] == ["Dealer Prospect"]
    assert end_user_gaps.existing_buyers_count == 1
    assert [prospect.company_name for prospect in end_user_gaps.prospects] == ["End User Prospect"]


@pytest.mark.asyncio
async def test_get_prospect_gaps_allows_all_customer_types(db_session: AsyncSession) -> None:
    tenant_id = uuid.uuid4()
    now = datetime.now(tz=UTC)
    dealer_buyer = await _create_customer_for_tenant(
        db_session,
        "Dealer Buyer",
        tenant_id,
        customer_type="dealer",
    )
    dealer_prospect = await _create_customer_for_tenant(
        db_session,
        "Dealer Prospect",
        tenant_id,
        customer_type="dealer",
    )
    end_user_buyer = await _create_customer_for_tenant(
        db_session,
        "End User Buyer",
        tenant_id,
        customer_type="end_user",
    )
    end_user_prospect = await _create_customer_for_tenant(
        db_session,
        "End User Prospect",
        tenant_id,
        customer_type="end_user",
    )

    target_category = await _create_product_for_tenant(db_session, "Target Belt", "Supplies", tenant_id)
    adjacent_category = await _create_product_for_tenant(db_session, "Adjacent Belt", "V-Belts", tenant_id)

    await _create_order(
        db_session,
        customer=dealer_buyer,
        created_at=now - timedelta(days=10),
        status="confirmed",
        lines=[(target_category, Decimal("250.00")), (adjacent_category, Decimal("120.00"))],
        tenant_id=tenant_id,
    )
    await _create_order(
        db_session,
        customer=dealer_prospect,
        created_at=now - timedelta(days=15),
        status="confirmed",
        lines=[(adjacent_category, Decimal("180.00"))],
        tenant_id=tenant_id,
    )
    await _create_order(
        db_session,
        customer=end_user_buyer,
        created_at=now - timedelta(days=12),
        status="confirmed",
        lines=[(target_category, Decimal("90.00")), (adjacent_category, Decimal("50.00"))],
        tenant_id=tenant_id,
    )
    await _create_order(
        db_session,
        customer=end_user_prospect,
        created_at=now - timedelta(days=18),
        status="confirmed",
        lines=[(adjacent_category, Decimal("70.00"))],
        tenant_id=tenant_id,
    )
    await db_session.commit()

    all_gaps = await get_prospect_gaps(
        db_session,
        tenant_id,
        category="Supplies",
        customer_type="all",
        limit=20,
    )

    assert all_gaps.existing_buyers_count == 2
    assert [prospect.company_name for prospect in all_gaps.prospects] == [
        "Dealer Prospect",
        "End User Prospect",
    ]


@pytest.mark.asyncio
async def test_get_prospect_gaps_filters_target_revenue_and_adjacency_by_customer_type(
    db_session: AsyncSession,
) -> None:
    tenant_id = uuid.uuid4()
    now = datetime.now(tz=UTC)
    dealer_buyer = await _create_customer_for_tenant(
        db_session,
        "Dealer Buyer",
        tenant_id,
        customer_type="dealer",
    )
    dealer_prospect = await _create_customer_for_tenant(
        db_session,
        "Dealer Prospect",
        tenant_id,
        customer_type="dealer",
    )
    end_user_buyer = await _create_customer_for_tenant(
        db_session,
        "End User Buyer",
        tenant_id,
        customer_type="end_user",
    )

    supplies = await _create_product_for_tenant(db_session, "Target Belt", "Supplies", tenant_id)
    v_belts = await _create_product_for_tenant(db_session, "Dealer Adjacent", "V-Belts", tenant_id)
    hoses = await _create_product_for_tenant(db_session, "End User Adjacent", "Hoses", tenant_id)

    await _create_order(
        db_session,
        customer=dealer_buyer,
        created_at=now - timedelta(days=10),
        status="confirmed",
        lines=[(supplies, Decimal("250.00")), (v_belts, Decimal("100.00"))],
        tenant_id=tenant_id,
    )
    await _create_order(
        db_session,
        customer=dealer_prospect,
        created_at=now - timedelta(days=15),
        status="confirmed",
        lines=[(hoses, Decimal("180.00"))],
        tenant_id=tenant_id,
    )
    await _create_order(
        db_session,
        customer=end_user_buyer,
        created_at=now - timedelta(days=12),
        status="confirmed",
        lines=[(supplies, Decimal("90.00")), (hoses, Decimal("50.00"))],
        tenant_id=tenant_id,
    )
    await db_session.commit()

    dealer_gaps = await get_prospect_gaps(
        db_session,
        tenant_id,
        category="Supplies",
        customer_type="dealer",
        limit=20,
    )

    assert dealer_gaps.target_category_revenue == Decimal("250.00")
    assert dealer_gaps.existing_buyers_count == 1
    assert [prospect.company_name for prospect in dealer_gaps.prospects] == ["Dealer Prospect"]
    assert dealer_gaps.prospects[0].score_components.adjacent_category_support == 0
    assert "adjacent_category_support" not in dealer_gaps.prospects[0].reason_codes


@pytest.mark.asyncio
async def test_get_market_opportunities_emits_concentration_and_growth_signals(db_session: AsyncSession) -> None:
    tenant_id = uuid.uuid4()
    now = datetime.now(tz=UTC)
    major = await _create_customer_for_tenant(db_session, "Acme Corp", tenant_id)
    minor = await _create_customer_for_tenant(db_session, "Beta Stores", tenant_id)
    electronics = await _create_product_for_tenant(db_session, "LED Panel", "Electronics", tenant_id)
    supplies = await _create_product_for_tenant(db_session, "Printer Ink", "Supplies", tenant_id)

    await _create_order(
        db_session,
        customer=major,
        created_at=now - timedelta(days=20),
        status="confirmed",
        lines=[(electronics, Decimal("600.00"))],
        tenant_id=tenant_id,
    )
    await _create_order(
        db_session,
        customer=minor,
        created_at=now - timedelta(days=18),
        status="confirmed",
        lines=[(electronics, Decimal("200.00")), (supplies, Decimal("100.00"))],
        tenant_id=tenant_id,
    )
    await _create_order(
        db_session,
        customer=major,
        created_at=now - timedelta(days=130),
        status="confirmed",
        lines=[(electronics, Decimal("200.00"))],
        tenant_id=tenant_id,
    )
    await _create_order(
        db_session,
        customer=minor,
        created_at=now - timedelta(days=125),
        status="confirmed",
        lines=[(electronics, Decimal("100.00"))],
        tenant_id=tenant_id,
    )
    await db_session.commit()

    opportunities = await get_market_opportunities(db_session, tenant_id, period="last_90d")

    assert opportunities.deferred_signal_types == ["new_product_adoption", "churn_risk"]
    assert opportunities.signals[0].signal_type == "concentration_risk"
    assert opportunities.signals[0].severity == "alert"
    assert opportunities.signals[0].support_counts == {
        "customers_considered": 2,
        "prior_customers_considered": 2,
    }
    assert opportunities.signals[0].source_period == "last_90d"
    assert opportunities.signals[1].signal_type == "concentration_risk"
    assert opportunities.signals[1].severity == "alert"
    assert opportunities.signals[1].support_counts == {
        "customers_considered": 2,
        "prior_customers_considered": 2,
    }
    assert opportunities.signals[1].source_period == "last_90d"
    assert opportunities.signals[2].signal_type == "category_growth"
    assert opportunities.signals[2].severity == "warning"
    assert opportunities.signals[2].support_counts == {
        "current_period_orders": 2,
        "prior_period_orders": 2,
        "current_customer_count": 2,
        "prior_customer_count": 2,
    }
    assert opportunities.signals[2].source_period == "last_90d"


@pytest.mark.asyncio
async def test_get_market_opportunities_counts_zero_value_customers_in_support_counts(
    db_session: AsyncSession,
) -> None:
    tenant_id = uuid.uuid4()
    now = datetime.now(tz=UTC)
    major = await _create_customer_for_tenant(db_session, "Anchor Account", tenant_id)
    zero_value = await _create_customer_for_tenant(db_session, "Discounted Account", tenant_id)
    electronics = await _create_product_for_tenant(db_session, "LED Panel", "Electronics", tenant_id)

    await _create_order(
        db_session,
        customer=major,
        created_at=now - timedelta(days=12),
        status="confirmed",
        lines=[(electronics, Decimal("600.00"))],
        tenant_id=tenant_id,
    )
    await _create_order(
        db_session,
        customer=zero_value,
        created_at=now - timedelta(days=11),
        status="confirmed",
        lines=[(electronics, Decimal("0.00"))],
        tenant_id=tenant_id,
    )
    await _create_order(
        db_session,
        customer=major,
        created_at=now - timedelta(days=120),
        status="confirmed",
        lines=[(electronics, Decimal("200.00"))],
        tenant_id=tenant_id,
    )
    await _create_order(
        db_session,
        customer=zero_value,
        created_at=now - timedelta(days=118),
        status="confirmed",
        lines=[(electronics, Decimal("0.00"))],
        tenant_id=tenant_id,
    )
    await db_session.commit()

    opportunities = await get_market_opportunities(db_session, tenant_id, period="last_90d")

    concentration_signal = next(
        signal for signal in opportunities.signals if signal.signal_type == "concentration_risk"
    )
    assert concentration_signal.support_counts == {
        "customers_considered": 2,
        "prior_customers_considered": 2,
    }


@pytest.mark.asyncio
async def test_get_market_opportunities_returns_empty_for_zero_revenue_tenant(db_session: AsyncSession) -> None:
    tenant_id = uuid.uuid4()

    opportunities = await get_market_opportunities(db_session, tenant_id, period="last_30d")

    assert opportunities.signals == []
    assert opportunities.deferred_signal_types == ["new_product_adoption", "churn_risk"]


@pytest.mark.asyncio
async def test_get_market_opportunities_filters_growth_signals_after_support_floor(db_session: AsyncSession) -> None:
    tenant_id = uuid.uuid4()
    now = datetime.now(tz=UTC)
    customer = await _create_customer_for_tenant(db_session, "Acme Corp", tenant_id)
    product = await _create_product_for_tenant(db_session, "LED Panel", "Electronics", tenant_id)

    await _create_order(
        db_session,
        customer=customer,
        created_at=now - timedelta(days=20),
        status="confirmed",
        lines=[(product, Decimal("600.00"))],
        tenant_id=tenant_id,
    )
    await db_session.commit()

    with patch(
        "domains.intelligence.services.market_opportunities.load_category_trends",
        new_callable=AsyncMock,
        return_value=[
            CategoryTrend(
                category="A",
                current_period_revenue=Decimal("300.00"),
                prior_period_revenue=Decimal("100.00"),
                revenue_delta_pct=200.0,
                current_period_orders=1,
                prior_period_orders=1,
                order_delta_pct=0.0,
                customer_count=1,
                prior_customer_count=1,
                new_customer_count=0,
                churned_customer_count=0,
                top_products=[],
                trend="growing",
                trend_context=None,
                activity_basis="confirmed_or_later_orders",
            ),
            CategoryTrend(
                category="B",
                current_period_revenue=Decimal("250.00"),
                prior_period_revenue=Decimal("100.00"),
                revenue_delta_pct=150.0,
                current_period_orders=1,
                prior_period_orders=1,
                order_delta_pct=0.0,
                customer_count=1,
                prior_customer_count=1,
                new_customer_count=0,
                churned_customer_count=0,
                top_products=[],
                trend="growing",
                trend_context=None,
                activity_basis="confirmed_or_later_orders",
            ),
            CategoryTrend(
                category="C",
                current_period_revenue=Decimal("200.00"),
                prior_period_revenue=Decimal("220.00"),
                revenue_delta_pct=-9.1,
                current_period_orders=2,
                prior_period_orders=2,
                order_delta_pct=0.0,
                customer_count=2,
                prior_customer_count=2,
                new_customer_count=0,
                churned_customer_count=0,
                top_products=[],
                trend="declining",
                trend_context=None,
                activity_basis="confirmed_or_later_orders",
            ),
            CategoryTrend(
                category="D",
                current_period_revenue=Decimal("180.00"),
                prior_period_revenue=Decimal("100.00"),
                revenue_delta_pct=80.0,
                current_period_orders=2,
                prior_period_orders=1,
                order_delta_pct=100.0,
                customer_count=2,
                prior_customer_count=1,
                new_customer_count=0,
                churned_customer_count=0,
                top_products=[],
                trend="growing",
                trend_context=None,
                activity_basis="confirmed_or_later_orders",
            ),
        ],
    ):
        opportunities = await get_market_opportunities(db_session, tenant_id, period="last_90d")

    assert any(signal.signal_type == "category_growth" and signal.headline.startswith("D revenue up") for signal in opportunities.signals)
    assert all("revenue up -" not in signal.headline for signal in opportunities.signals)