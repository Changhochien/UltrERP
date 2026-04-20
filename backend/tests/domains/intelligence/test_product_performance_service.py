from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest
import pytest_asyncio
from freezegun import freeze_time
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.models.order_line import OrderLine
from domains.intelligence.service import get_product_performance
from domains.product_analytics.models import SalesMonthly
from tests.db import isolated_async_session
from tests.domains.intelligence.test_service import (
    _create_customer_for_tenant,
    _create_order,
    _create_product_for_tenant,
)


def _month_start(value: date) -> date:
    return value.replace(day=1)


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    async with isolated_async_session() as session:
        yield session


@pytest.fixture
def tenant_id() -> uuid.UUID:
    return uuid.uuid4()


async def _create_monthly_point(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    product_id: uuid.UUID,
    month_start: date,
    product_name_snapshot: str,
    product_category_snapshot: str,
    quantity_sold: str,
    revenue: str,
    order_count: int = 1,
) -> None:
    quantity = Decimal(quantity_sold)
    revenue_decimal = Decimal(revenue)
    avg_unit_price = (
        (revenue_decimal / quantity).quantize(Decimal("0.01"))
        if quantity > 0
        else Decimal("0.00")
    )
    session.add(
        SalesMonthly(
            tenant_id=tenant_id,
            month_start=_month_start(month_start),
            product_id=product_id,
            product_name_snapshot=product_name_snapshot,
            product_category_snapshot=product_category_snapshot,
            quantity_sold=quantity,
            order_count=order_count,
            revenue=revenue_decimal,
            avg_unit_price=avg_unit_price,
        )
    )
    await session.flush()


async def _apply_line_snapshots(
    session: AsyncSession,
    order_id: uuid.UUID,
    *,
    product_name_snapshot: str,
    product_category_snapshot: str,
) -> None:
    lines = (
        await session.execute(
            select(OrderLine)
            .where(OrderLine.order_id == order_id)
            .order_by(OrderLine.line_number)
        )
    ).scalars().all()
    for line in lines:
        line.product_name_snapshot = product_name_snapshot
        line.product_category_snapshot = product_category_snapshot


@pytest.mark.asyncio
@freeze_time("2026-04-16T10:00:00Z")
async def test_get_product_performance_assigns_lifecycle_precedence_and_ordering(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
) -> None:
    grow_id = uuid.uuid4()
    mature_id = uuid.uuid4()
    stable_id = uuid.uuid4()
    new_id = uuid.uuid4()
    declining_id = uuid.uuid4()
    eol_id = uuid.uuid4()

    await _create_monthly_point(
        db_session,
        tenant_id,
        product_id=grow_id,
        month_start=date(2025, 3, 1),
        product_name_snapshot="Grow Belt Legacy",
        product_category_snapshot="Belts",
        quantity_sold="10.000",
        revenue="100.00",
    )
    await _create_monthly_point(
        db_session,
        tenant_id,
        product_id=grow_id,
        month_start=date(2026, 3, 1),
        product_name_snapshot="Grow Belt Prime",
        product_category_snapshot="Premium Belts",
        quantity_sold="16.000",
        revenue="160.00",
    )

    await _create_monthly_point(
        db_session,
        tenant_id,
        product_id=mature_id,
        month_start=date(2024, 4, 1),
        product_name_snapshot="Mature Belt",
        product_category_snapshot="Belts",
        quantity_sold="1.000",
        revenue="10.00",
    )
    await _create_monthly_point(
        db_session,
        tenant_id,
        product_id=mature_id,
        month_start=date(2025, 3, 1),
        product_name_snapshot="Mature Belt",
        product_category_snapshot="Belts",
        quantity_sold="10.000",
        revenue="100.00",
    )
    await _create_monthly_point(
        db_session,
        tenant_id,
        product_id=mature_id,
        month_start=date(2026, 3, 1),
        product_name_snapshot="Mature Belt",
        product_category_snapshot="Belts",
        quantity_sold="11.000",
        revenue="110.00",
    )

    await _create_monthly_point(
        db_session,
        tenant_id,
        product_id=stable_id,
        month_start=date(2025, 3, 1),
        product_name_snapshot="Stable Belt",
        product_category_snapshot="Belts",
        quantity_sold="10.000",
        revenue="100.00",
    )
    await _create_monthly_point(
        db_session,
        tenant_id,
        product_id=stable_id,
        month_start=date(2026, 2, 1),
        product_name_snapshot="Stable Belt",
        product_category_snapshot="Belts",
        quantity_sold="10.000",
        revenue="100.00",
    )

    await _create_monthly_point(
        db_session,
        tenant_id,
        product_id=new_id,
        month_start=date(2026, 2, 1),
        product_name_snapshot="New Belt",
        product_category_snapshot="Launch",
        quantity_sold="9.000",
        revenue="90.00",
    )

    await _create_monthly_point(
        db_session,
        tenant_id,
        product_id=declining_id,
        month_start=date(2025, 1, 1),
        product_name_snapshot="Decline Belt",
        product_category_snapshot="Belts",
        quantity_sold="10.000",
        revenue="100.00",
    )
    await _create_monthly_point(
        db_session,
        tenant_id,
        product_id=declining_id,
        month_start=date(2026, 3, 1),
        product_name_snapshot="Decline Belt",
        product_category_snapshot="Belts",
        quantity_sold="6.000",
        revenue="60.00",
    )

    await _create_monthly_point(
        db_session,
        tenant_id,
        product_id=eol_id,
        month_start=date(2025, 3, 1),
        product_name_snapshot="End Belt",
        product_category_snapshot="Legacy",
        quantity_sold="10.000",
        revenue="100.00",
    )
    await db_session.commit()

    result = await get_product_performance(db_session, tenant_id, limit=10)

    assert result.data_basis == "aggregate_only"
    assert result.window_is_partial is False
    assert result.total == 6
    assert result.current_window.start_month == date(2025, 4, 1)
    assert result.current_window.end_month == date(2026, 3, 1)
    assert result.prior_window.start_month == date(2024, 4, 1)
    assert result.prior_window.end_month == date(2025, 3, 1)

    assert [row.product_name for row in result.products] == [
        "Grow Belt Prime",
        "Mature Belt",
        "Stable Belt",
        "New Belt",
        "Decline Belt",
        "End Belt",
    ]

    by_stage = {row.lifecycle_stage: row for row in result.products}

    assert by_stage["growing"].product_id == grow_id
    assert by_stage["growing"].product_category_snapshot == "Premium Belts"
    assert by_stage["growing"].current_period.revenue == Decimal("160.00")
    assert by_stage["growing"].prior_period.revenue == Decimal("100.00")
    assert by_stage["growing"].stage_reasons[0] == "rule:growing"

    assert by_stage["mature"].product_id == mature_id
    assert by_stage["mature"].months_on_sale == 24
    assert by_stage["mature"].stage_reasons[0] == "rule:mature"

    assert by_stage["stable"].product_id == stable_id
    assert by_stage["stable"].months_on_sale == 12
    assert by_stage["stable"].stage_reasons[0] == "rule:stable"

    assert by_stage["new"].product_id == new_id
    assert by_stage["new"].first_sale_month == date(2026, 2, 1)
    assert by_stage["new"].stage_reasons[0] == "rule:new"

    assert by_stage["declining"].product_id == declining_id
    assert by_stage["declining"].current_period.revenue == Decimal("60.00")
    assert by_stage["declining"].prior_period.revenue == Decimal("100.00")
    assert by_stage["declining"].stage_reasons[0] == "rule:declining"

    assert by_stage["end_of_life"].product_id == eol_id
    assert by_stage["end_of_life"].current_period.revenue == Decimal("0.00")
    assert by_stage["end_of_life"].prior_period.revenue == Decimal("100.00")
    assert by_stage["end_of_life"].last_sale_month == date(2025, 3, 1)
    assert by_stage["end_of_life"].stage_reasons[0] == "rule:end_of_life"


@pytest.mark.asyncio
@freeze_time("2026-04-16T10:00:00Z")
async def test_get_product_performance_returns_empty_state_without_sales(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
) -> None:
    result = await get_product_performance(db_session, tenant_id)

    assert result.products == []
    assert result.total == 0
    assert result.data_basis == "aggregate_only"
    assert result.window_is_partial is False
    assert result.current_window.start_month == date(2025, 4, 1)
    assert result.current_window.end_month == date(2026, 3, 1)


@pytest.mark.asyncio
@freeze_time("2026-04-16T10:00:00Z")
async def test_get_product_performance_uses_full_history_and_latest_snapshot_timestamp(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
) -> None:
    customer = await _create_customer_for_tenant(db_session, "Portfolio Customer", tenant_id)
    product = await _create_product_for_tenant(db_session, "Portfolio Belt", "Belts", tenant_id)

    historical_order = await _create_order(
        db_session,
        customer=customer,
        created_at=date(2023, 1, 15),
        status="confirmed",
        lines=[(product, Decimal("30.00"))],
        tenant_id=tenant_id,
    )
    await _apply_line_snapshots(
        db_session,
        historical_order.id,
        product_name_snapshot="Original Belt",
        product_category_snapshot="Belts",
    )

    prior_order = await _create_order(
        db_session,
        customer=customer,
        created_at=date(2025, 3, 10),
        status="confirmed",
        lines=[(product, Decimal("100.00"))],
        tenant_id=tenant_id,
    )
    await _apply_line_snapshots(
        db_session,
        prior_order.id,
        product_name_snapshot="Prior Belt",
        product_category_snapshot="Belts",
    )

    earlier_current_order = await _create_order(
        db_session,
        customer=customer,
        created_at=date(2026, 3, 5),
        status="confirmed",
        lines=[(product, Decimal("55.00"))],
        tenant_id=tenant_id,
    )
    await _apply_line_snapshots(
        db_session,
        earlier_current_order.id,
        product_name_snapshot="Zulu Belt",
        product_category_snapshot="Zulu Category",
    )

    latest_current_order = await _create_order(
        db_session,
        customer=customer,
        created_at=date(2026, 3, 20),
        status="confirmed",
        lines=[(product, Decimal("55.00"))],
        tenant_id=tenant_id,
    )
    await _apply_line_snapshots(
        db_session,
        latest_current_order.id,
        product_name_snapshot="Alpha Belt",
        product_category_snapshot="Alpha Category",
    )

    await _create_monthly_point(
        db_session,
        tenant_id,
        product_id=product.id,
        month_start=date(2025, 3, 1),
        product_name_snapshot="Prior Belt",
        product_category_snapshot="Belts",
        quantity_sold="10.000",
        revenue="100.00",
    )
    await _create_monthly_point(
        db_session,
        tenant_id,
        product_id=product.id,
        month_start=date(2026, 3, 1),
        product_name_snapshot="Zulu Belt",
        product_category_snapshot="Zulu Category",
        quantity_sold="5.000",
        revenue="55.00",
    )
    await _create_monthly_point(
        db_session,
        tenant_id,
        product_id=product.id,
        month_start=date(2026, 3, 1),
        product_name_snapshot="Alpha Belt",
        product_category_snapshot="Alpha Category",
        quantity_sold="5.000",
        revenue="55.00",
    )
    await db_session.commit()

    result = await get_product_performance(db_session, tenant_id, limit=10)

    assert result.total == 1
    row = result.products[0]
    assert row.product_id == product.id
    assert row.product_name == "Alpha Belt"
    assert row.product_category_snapshot == "Alpha Category"
    assert row.first_sale_month == date(2023, 1, 1)
    assert row.last_sale_month == date(2026, 3, 1)
    assert row.months_on_sale == 39
    assert row.lifecycle_stage == "mature"
    assert row.stage_reasons[0] == "rule:mature"


@pytest.mark.asyncio
@freeze_time("2026-04-16T10:00:00Z")
async def test_get_product_performance_treats_first_closed_month_as_new(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
) -> None:
    customer = await _create_customer_for_tenant(db_session, "Launch Customer", tenant_id)
    product = await _create_product_for_tenant(db_session, "Launch Belt", "Launch", tenant_id)

    launch_order = await _create_order(
        db_session,
        customer=customer,
        created_at=date(2025, 4, 10),
        status="confirmed",
        lines=[(product, Decimal("90.00"))],
        tenant_id=tenant_id,
    )
    await _apply_line_snapshots(
        db_session,
        launch_order.id,
        product_name_snapshot="Launch Belt",
        product_category_snapshot="Launch",
    )

    await _create_monthly_point(
        db_session,
        tenant_id,
        product_id=product.id,
        month_start=date(2025, 4, 1),
        product_name_snapshot="Launch Belt",
        product_category_snapshot="Launch",
        quantity_sold="9.000",
        revenue="90.00",
    )
    await db_session.commit()

    result = await get_product_performance(db_session, tenant_id, limit=10)

    assert result.total == 1
    row = result.products[0]
    assert row.product_id == product.id
    assert row.first_sale_month == date(2025, 4, 1)
    assert row.lifecycle_stage == "new"
    assert row.stage_reasons[0] == "rule:new"