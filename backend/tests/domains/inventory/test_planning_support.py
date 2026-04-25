from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from itertools import count

import pytest
import pytest_asyncio
from freezegun import freeze_time
from httpx import ASGITransport
from httpx import AsyncClient as HttpxAsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from common.database import get_db
from common.models.inventory_stock import InventoryStock
from common.models.order import Order
from common.models.order_line import OrderLine
from common.models.product import Product
from common.models.warehouse import Warehouse
from domains.customers.models import Customer
from domains.inventory.reorder_point import compute_reorder_points_preview
from domains.inventory import routes as inventory_routes
from domains.inventory.services import get_planning_support
from domains.product_analytics.service import refresh_sales_monthly
from tests.db import isolated_async_session
from tests.domains.orders._helpers import make_test_token

_BUSINESS_NUMBER_COUNTER = count(30_000_000)
_MISSING_OVERRIDE = object()


def _month_start(value: date) -> date:
    return value.replace(day=1)


def _shift_months(value: date, months: int) -> date:
    month_index = (value.year * 12 + value.month - 1) + months
    year = month_index // 12
    month = month_index % 12 + 1
    return date(year, month, 1)


def _auth_header(tenant_id: uuid.UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {make_test_token(tenant_id=str(tenant_id))}"}


def _override_db(session: AsyncSession) -> object:
    async def _override():
        yield session

    previous = app.dependency_overrides.get(get_db, _MISSING_OVERRIDE)
    app.dependency_overrides[get_db] = _override
    return previous


def _restore_db(previous: object) -> None:
    if previous is _MISSING_OVERRIDE:
        app.dependency_overrides.pop(get_db, None)
    else:
        app.dependency_overrides[get_db] = previous


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    async with isolated_async_session() as session:
        yield session


@pytest.fixture
def tenant_id() -> uuid.UUID:
    return uuid.uuid4()


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
        contact_name="Planner",
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
    *,
    code: str,
    name: str,
    category: str,
) -> Product:
    product = Product(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        code=code,
        name=name,
        category=category,
        status="active",
        unit="pcs",
    )
    session.add(product)
    await session.flush()
    return product


async def _create_warehouse(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    code: str,
    name: str,
) -> Warehouse:
    warehouse = Warehouse(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        code=code,
        name=name,
        is_active=True,
    )
    session.add(warehouse)
    await session.flush()
    return warehouse


async def _create_inventory_stock(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    *,
    quantity: int,
    reorder_point: int,
    on_order_qty: int,
    in_transit_qty: int,
    reserved_qty: int,
) -> InventoryStock:
    stock = InventoryStock(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        product_id=product_id,
        warehouse_id=warehouse_id,
        quantity=quantity,
        reorder_point=reorder_point,
        on_order_qty=on_order_qty,
        in_transit_qty=in_transit_qty,
        reserved_qty=reserved_qty,
    )
    session.add(stock)
    await session.flush()
    return stock


async def _create_order(
    session: AsyncSession,
    *,
    customer: Customer,
    product: Product,
    confirmed_at: datetime,
    status: str,
    quantity: str,
    unit_price: str,
) -> Order:
    quantity_decimal = Decimal(quantity)
    unit_price_decimal = Decimal(unit_price)
    line_total = quantity_decimal * unit_price_decimal

    order = Order(
        id=uuid.uuid4(),
        tenant_id=customer.tenant_id,
        customer_id=customer.id,
        order_number=f"ORD-{uuid.uuid4().hex[:8].upper()}",
        status=status,
        payment_terms_code="NET_30",
        payment_terms_days=30,
        subtotal_amount=line_total,
        discount_amount=Decimal("0.00"),
        discount_percent=Decimal("0.0000"),
        tax_amount=Decimal("0.00"),
        total_amount=line_total,
        notes=None,
        created_by="test-suite",
        created_at=confirmed_at,
        updated_at=confirmed_at,
        confirmed_at=confirmed_at,
    )
    session.add(order)
    await session.flush()

    line = OrderLine(
        id=uuid.uuid4(),
        tenant_id=customer.tenant_id,
        order_id=order.id,
        product_id=product.id,
        line_number=1,
        quantity=quantity_decimal,
        list_unit_price=unit_price_decimal,
        unit_price=unit_price_decimal,
        unit_cost=None,
        discount_amount=Decimal("0.00"),
        tax_policy_code="standard",
        tax_type=1,
        tax_rate=Decimal("0.0000"),
        tax_amount=Decimal("0.00"),
        subtotal_amount=line_total,
        total_amount=line_total,
        description=product.name,
        product_name_snapshot=product.name,
        product_category_snapshot=product.category,
    )
    session.add(line)
    await session.flush()
    return order


@pytest.mark.asyncio
@freeze_time("2026-04-15T09:00:00Z")
async def test_get_planning_support_blends_closed_aggregate_with_live_current_month(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
) -> None:
    customer = await _create_customer(db_session, tenant_id, "Planner Customer")
    product = await _create_product(
        db_session,
        tenant_id,
        code="PLAN-001",
        name="Planning Belt",
        category="Belts",
    )
    main_warehouse = await _create_warehouse(
        db_session,
        tenant_id,
        code="MAIN",
        name="Main Warehouse",
    )
    overflow_warehouse = await _create_warehouse(
        db_session,
        tenant_id,
        code="OVER",
        name="Overflow Warehouse",
    )

    await _create_inventory_stock(
        db_session,
        tenant_id,
        product.id,
        main_warehouse.id,
        quantity=20,
        reorder_point=18,
        on_order_qty=6,
        in_transit_qty=3,
        reserved_qty=2,
    )
    await _create_inventory_stock(
        db_session,
        tenant_id,
        product.id,
        overflow_warehouse.id,
        quantity=8,
        reorder_point=4,
        on_order_qty=1,
        in_transit_qty=0,
        reserved_qty=1,
    )

    current_month = _month_start(datetime.now(tz=UTC).date())
    previous_month = _shift_months(current_month, -1)

    await _create_order(
        db_session,
        customer=customer,
        product=product,
        confirmed_at=datetime(2026, 3, 12, 10, 0, tzinfo=UTC),
        status="confirmed",
        quantity="12.000",
        unit_price="35.00",
    )
    await _create_order(
        db_session,
        customer=customer,
        product=product,
        confirmed_at=datetime(2026, 4, 10, 11, 0, tzinfo=UTC),
        status="shipped",
        quantity="5.000",
        unit_price="40.00",
    )
    await db_session.commit()

    await refresh_sales_monthly(db_session, tenant_id, previous_month)

    result = await get_planning_support(
        db_session,
        tenant_id,
        product.id,
        months=2,
        include_current_month=True,
    )

    assert result is not None
    assert [item["month"] for item in result["items"]] == ["2026-03", "2026-04"]
    assert [item["quantity"] for item in result["items"]] == [Decimal("12.000"), Decimal("5.000")]
    assert [item["source"] for item in result["items"]] == ["aggregated", "live"]
    assert result["avg_monthly_quantity"] == Decimal("8.500")
    assert result["peak_monthly_quantity"] == Decimal("12.000")
    assert result["low_monthly_quantity"] == Decimal("5.000")
    assert result["seasonality_index"] == Decimal("1.412")
    assert result["above_average_months"] == ["2026-03"]
    assert result["history_months_used"] == 2
    assert result["current_month_live_quantity"] == Decimal("5.000")
    assert result["reorder_point"] == 22
    assert result["on_order_qty"] == 7
    assert result["in_transit_qty"] == 3
    assert result["reserved_qty"] == 3
    assert result["data_basis"] == "aggregated_plus_live_current_month"
    assert result["advisory_only"] is True
    assert result["data_gap"] is False
    assert result["window"] == {
        "start_month": "2026-03",
        "end_month": "2026-04",
        "includes_current_month": True,
        "is_partial": True,
    }


@pytest.mark.asyncio
@freeze_time("2026-04-15T09:00:00Z")
async def test_get_planning_support_sums_snapshot_grain_rows_within_each_month(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
) -> None:
    customer = await _create_customer(db_session, tenant_id, "Snapshot Customer")
    product = await _create_product(
        db_session,
        tenant_id,
        code="PLAN-SNAPSHOT",
        name="Planning Belt",
        category="Belts",
    )
    warehouse = await _create_warehouse(
        db_session,
        tenant_id,
        code="MAIN",
        name="Main Warehouse",
    )
    await _create_inventory_stock(
        db_session,
        tenant_id,
        product.id,
        warehouse.id,
        quantity=24,
        reorder_point=10,
        on_order_qty=2,
        in_transit_qty=1,
        reserved_qty=3,
    )

    previous_month = _shift_months(_month_start(datetime.now(tz=UTC).date()), -1)

    await _create_order(
        db_session,
        customer=customer,
        product=product,
        confirmed_at=datetime(2026, 3, 5, 9, 0, tzinfo=UTC),
        status="confirmed",
        quantity="7.000",
        unit_price="22.00",
    )

    product.name = "Planning Strap"
    product.category = "Accessories"
    await db_session.flush()

    await _create_order(
        db_session,
        customer=customer,
        product=product,
        confirmed_at=datetime(2026, 3, 18, 15, 0, tzinfo=UTC),
        status="shipped",
        quantity="4.000",
        unit_price="25.00",
    )
    await _create_order(
        db_session,
        customer=customer,
        product=product,
        confirmed_at=datetime(2026, 4, 3, 11, 0, tzinfo=UTC),
        status="fulfilled",
        quantity="2.000",
        unit_price="27.00",
    )

    product.name = "Planning Strap v2"
    product.category = "Straps"
    await db_session.flush()

    await _create_order(
        db_session,
        customer=customer,
        product=product,
        confirmed_at=datetime(2026, 4, 11, 13, 0, tzinfo=UTC),
        status="confirmed",
        quantity="3.000",
        unit_price="29.00",
    )
    await db_session.commit()

    await refresh_sales_monthly(db_session, tenant_id, previous_month)

    result = await get_planning_support(
        db_session,
        tenant_id,
        product.id,
        months=2,
        include_current_month=True,
    )

    assert result is not None
    assert [item["month"] for item in result["items"]] == ["2026-03", "2026-04"]
    assert [item["quantity"] for item in result["items"]] == [Decimal("11.000"), Decimal("5.000")]
    assert [item["source"] for item in result["items"]] == ["aggregated", "live"]
    assert result["avg_monthly_quantity"] == Decimal("8.000")
    assert result["peak_monthly_quantity"] == Decimal("11.000")
    assert result["low_monthly_quantity"] == Decimal("5.000")
    assert result["seasonality_index"] == Decimal("1.375")
    assert result["above_average_months"] == ["2026-03"]
    assert result["current_month_live_quantity"] == Decimal("5.000")


@pytest.mark.asyncio
@freeze_time("2026-04-15T09:00:00Z")
async def test_get_planning_support_falls_back_when_closed_month_snapshots_are_missing(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
) -> None:
    customer = await _create_customer(db_session, tenant_id, "Fallback Planner Customer")
    product = await _create_product(
        db_session,
        tenant_id,
        code="PLAN-FALLBACK",
        name="Fallback Belt",
        category="Belts",
    )
    warehouse = await _create_warehouse(
        db_session,
        tenant_id,
        code="MAIN",
        name="Main Warehouse",
    )
    await _create_inventory_stock(
        db_session,
        tenant_id,
        product.id,
        warehouse.id,
        quantity=14,
        reorder_point=9,
        on_order_qty=2,
        in_transit_qty=1,
        reserved_qty=3,
    )

    await _create_order(
        db_session,
        customer=customer,
        product=product,
        confirmed_at=datetime(2026, 2, 7, 10, 0, tzinfo=UTC),
        status="confirmed",
        quantity="4.000",
        unit_price="11.00",
    )
    await _create_order(
        db_session,
        customer=customer,
        product=product,
        confirmed_at=datetime(2026, 3, 8, 14, 0, tzinfo=UTC),
        status="shipped",
        quantity="6.000",
        unit_price="12.00",
    )
    await db_session.commit()

    result = await get_planning_support(
        db_session,
        tenant_id,
        product.id,
        months=2,
        include_current_month=False,
    )

    assert result is not None
    assert [item["month"] for item in result["items"]] == ["2026-02", "2026-03"]
    assert [item["quantity"] for item in result["items"]] == [Decimal("4.000"), Decimal("6.000")]
    assert [item["source"] for item in result["items"]] == ["aggregated", "aggregated"]
    assert result["avg_monthly_quantity"] == Decimal("5.000")
    assert result["peak_monthly_quantity"] == Decimal("6.000")
    assert result["low_monthly_quantity"] == Decimal("4.000")
    assert result["seasonality_index"] == Decimal("1.200")
    assert result["above_average_months"] == ["2026-03"]
    assert result["history_months_used"] == 2
    assert result["current_month_live_quantity"] is None
    assert result["reorder_point"] == 9
    assert result["on_order_qty"] == 2
    assert result["in_transit_qty"] == 1
    assert result["reserved_qty"] == 3
    assert result["data_basis"] == "aggregated_only"
    assert result["advisory_only"] is True
    assert result["data_gap"] is False


@pytest.mark.asyncio
@freeze_time("2026-04-15T09:00:00Z")
async def test_reorder_preview_surfaces_shared_history_as_advisory_context(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
) -> None:
    customer = await _create_customer(db_session, tenant_id, "Preview Customer")
    product = await _create_product(
        db_session,
        tenant_id,
        code="PLAN-PREVIEW",
        name="Preview Belt",
        category="Belts",
    )
    warehouse = await _create_warehouse(
        db_session,
        tenant_id,
        code="MAIN",
        name="Main Warehouse",
    )
    await _create_inventory_stock(
        db_session,
        tenant_id,
        product.id,
        warehouse.id,
        quantity=10,
        reorder_point=8,
        on_order_qty=2,
        in_transit_qty=0,
        reserved_qty=1,
    )

    previous_month = _shift_months(_month_start(datetime.now(tz=UTC).date()), -1)
    await _create_order(
        db_session,
        customer=customer,
        product=product,
        confirmed_at=datetime(2026, 3, 7, 10, 0, tzinfo=UTC),
        status="confirmed",
        quantity="7.000",
        unit_price="30.00",
    )
    await _create_order(
        db_session,
        customer=customer,
        product=product,
        confirmed_at=datetime(2026, 4, 8, 14, 0, tzinfo=UTC),
        status="shipped",
        quantity="3.000",
        unit_price="30.00",
    )
    await db_session.commit()

    await refresh_sales_monthly(db_session, tenant_id, previous_month)

    preview_rows, skipped_rows = await compute_reorder_points_preview(
        db_session,
        tenant_id,
    )

    assert not any(row["product_id"] == product.id for row in preview_rows)

    skipped_row = next(row for row in skipped_rows if row["product_id"] == product.id)
    assert skipped_row["skipped_reason"] == "insufficient_history"
    assert skipped_row["shared_history_context"] == {
        "advisory_only": True,
        "data_basis": "aggregated_plus_live_current_month",
        "history_months_used": 12,
        "avg_monthly_quantity": pytest.approx(0.8333333333, rel=1e-6),
        "seasonality_index": pytest.approx(8.403, rel=1e-6),
        "current_month_live_quantity": 3.0,
    }


@pytest.mark.asyncio
@freeze_time("2026-04-15T09:00:00Z")
async def test_planning_support_endpoint_returns_aggregate_only_window(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
) -> None:
    customer = await _create_customer(db_session, tenant_id, "Route Customer")
    product = await _create_product(
        db_session,
        tenant_id,
        code="PLAN-ROUTE",
        name="Route Belt",
        category="Belts",
    )
    warehouse = await _create_warehouse(
        db_session,
        tenant_id,
        code="MAIN",
        name="Main Warehouse",
    )
    await _create_inventory_stock(
        db_session,
        tenant_id,
        product.id,
        warehouse.id,
        quantity=16,
        reorder_point=9,
        on_order_qty=2,
        in_transit_qty=1,
        reserved_qty=4,
    )

    previous_month = _shift_months(_month_start(datetime.now(tz=UTC).date()), -1)
    await _create_order(
        db_session,
        customer=customer,
        product=product,
        confirmed_at=datetime(2026, 3, 6, 9, 0, tzinfo=UTC),
        status="fulfilled",
        quantity="7.000",
        unit_price="22.00",
    )
    await db_session.commit()
    await refresh_sales_monthly(db_session, tenant_id, previous_month)

    previous = _override_db(db_session)
    try:
        transport = ASGITransport(app=app)
        async with HttpxAsyncClient(
            transport=transport,
            base_url="http://test",
            headers=_auth_header(tenant_id),
        ) as client:
            response = await client.get(
                f"/api/v1/inventory/products/{product.id}/planning-support?months=1&include_current_month=false"
            )
    finally:
        _restore_db(previous)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["items"] == [{"month": "2026-03", "quantity": "7.000", "source": "aggregated"}]
    assert body["avg_monthly_quantity"] == "7.000"
    assert body["peak_monthly_quantity"] == "7.000"
    assert body["low_monthly_quantity"] == "7.000"
    assert body["seasonality_index"] == "1.000"
    assert body["above_average_months"] == []
    assert body["history_months_used"] == 1
    assert body["current_month_live_quantity"] is None
    assert body["reorder_point"] == 9
    assert body["on_order_qty"] == 2
    assert body["in_transit_qty"] == 1
    assert body["reserved_qty"] == 4
    assert body["data_basis"] == "aggregated_only"
    assert body["advisory_only"] is True
    assert body["data_gap"] is False
    assert body["window"] == {
        "start_month": "2026-03",
        "end_month": "2026-03",
        "includes_current_month": False,
        "is_partial": False,
    }


@pytest.mark.asyncio
async def test_planning_support_endpoint_returns_403_when_feature_disabled(
    monkeypatch: pytest.MonkeyPatch,
    tenant_id: uuid.UUID,
) -> None:
    transport = ASGITransport(app=app)
    async with HttpxAsyncClient(
        transport=transport,
        base_url="http://test",
        headers=_auth_header(tenant_id),
    ) as client:
        monkeypatch.setattr(inventory_routes.settings, "inventory_planning_support_enabled", False)
        response = await client.get(f"/api/v1/inventory/products/{uuid.uuid4()}/planning-support")

    assert response.status_code == 403
    assert response.json() == {"detail": "Planning support is disabled"}


@pytest.mark.asyncio
@freeze_time("2026-04-15T09:00:00Z")
async def test_get_planning_support_returns_data_gap_without_guessing(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
) -> None:
    product = await _create_product(
        db_session,
        tenant_id,
        code="PLAN-EMPTY",
        name="No History Belt",
        category="Belts",
    )
    warehouse = await _create_warehouse(
        db_session,
        tenant_id,
        code="MAIN",
        name="Main Warehouse",
    )
    await _create_inventory_stock(
        db_session,
        tenant_id,
        product.id,
        warehouse.id,
        quantity=6,
        reorder_point=5,
        on_order_qty=0,
        in_transit_qty=0,
        reserved_qty=1,
    )
    await db_session.commit()

    result = await get_planning_support(
        db_session,
        tenant_id,
        product.id,
        months=6,
        include_current_month=True,
    )

    assert result is not None
    assert result["items"] == []
    assert result["avg_monthly_quantity"] is None
    assert result["peak_monthly_quantity"] is None
    assert result["low_monthly_quantity"] is None
    assert result["seasonality_index"] is None
    assert result["above_average_months"] == []
    assert result["history_months_used"] == 0
    assert result["current_month_live_quantity"] == Decimal("0.000")
    assert result["data_basis"] == "no_history"
    assert result["advisory_only"] is True
    assert result["data_gap"] is True