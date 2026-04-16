from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.models.order_line import OrderLine
from common.models.product import Product
from domains.intelligence.service import get_customer_buying_behavior
from tests.domains.intelligence.test_service import (
    _create_customer_for_tenant,
    _create_order,
    _create_product_for_tenant,
    db_session,
)


def _shift_month_start(value: date, months: int) -> date:
    year = value.year
    month = value.month + months
    while month <= 0:
        year -= 1
        month += 12
    while month > 12:
        year += 1
        month -= 12
    return date(year, month, 1)


def _month_moment(months_ago: int) -> datetime:
    current_month = datetime.now(tz=UTC).date().replace(day=1)
    month_start = _shift_month_start(current_month, -months_ago)
    return datetime(month_start.year, month_start.month, 15, 12, 0, tzinfo=UTC)


async def _apply_line_snapshots(
    session: AsyncSession,
    order_id: uuid.UUID,
    snapshot_categories: list[str],
) -> None:
    lines = (
        await session.execute(
            select(OrderLine)
            .where(OrderLine.order_id == order_id)
            .order_by(OrderLine.line_number)
        )
    ).scalars().all()
    for line, category in zip(lines, snapshot_categories, strict=True):
        line.product_name_snapshot = line.description
        line.product_category_snapshot = category


@pytest.mark.asyncio
async def test_get_customer_buying_behavior_filters_by_customer_type_and_uses_snapshots(
    db_session: AsyncSession,
) -> None:
    tenant_id = uuid.uuid4()

    dealers = [
        await _create_customer_for_tenant(db_session, f"Dealer {index}", tenant_id, customer_type="dealer")
        for index in range(1, 7)
    ]
    end_users = [
        await _create_customer_for_tenant(db_session, f"End User {index}", tenant_id, customer_type="end_user")
        for index in range(1, 3)
    ]

    belts = await _create_product_for_tenant(db_session, "Alpha Belt", "Belts", tenant_id)
    pulleys = await _create_product_for_tenant(db_session, "Pulley Kit", "Pulleys", tenant_id)
    hoses = await _create_product_for_tenant(db_session, "Hydraulic Hose", "Hoses", tenant_id)
    adapters = await _create_product_for_tenant(db_session, "Adapter Kit", "Adapters", tenant_id)

    for customer in dealers[:3]:
        order = await _create_order(
            db_session,
            customer=customer,
            created_at=_month_moment(1),
            status="confirmed",
            lines=[(belts, Decimal("100.00")), (pulleys, Decimal("50.00"))],
            tenant_id=tenant_id,
        )
        await _apply_line_snapshots(db_session, order.id, ["Belts", "Pulleys"])

    for customer in dealers[3:5]:
        order = await _create_order(
            db_session,
            customer=customer,
            created_at=_month_moment(2),
            status="confirmed",
            lines=[(belts, Decimal("90.00"))],
            tenant_id=tenant_id,
        )
        await _apply_line_snapshots(db_session, order.id, ["Belts"])

    hose_only_order = await _create_order(
        db_session,
        customer=dealers[5],
        created_at=_month_moment(1),
        status="confirmed",
        lines=[(hoses, Decimal("70.00"))],
        tenant_id=tenant_id,
    )
    await _apply_line_snapshots(db_session, hose_only_order.id, ["Hoses"])

    await _create_order(
        db_session,
        customer=dealers[0],
        created_at=_month_moment(1),
        status="confirmed",
        lines=[(adapters, Decimal("40.00"))],
        tenant_id=tenant_id,
    )

    end_user_shared = await _create_order(
        db_session,
        customer=end_users[0],
        created_at=_month_moment(1),
        status="confirmed",
        lines=[(belts, Decimal("120.00")), (pulleys, Decimal("30.00"))],
        tenant_id=tenant_id,
    )
    await _apply_line_snapshots(db_session, end_user_shared.id, ["Belts", "Pulleys"])

    end_user_anchor = await _create_order(
        db_session,
        customer=end_users[1],
        created_at=_month_moment(2),
        status="confirmed",
        lines=[(belts, Decimal("110.00"))],
        tenant_id=tenant_id,
    )
    await _apply_line_snapshots(db_session, end_user_anchor.id, ["Belts"])

    belts.category = "Renamed Live Category"
    pulleys.category = "Renamed Live Pulleys"
    adapters.category = "Renamed Live Adapter"
    await db_session.flush()
    await db_session.commit()

    behavior = await get_customer_buying_behavior(
        db_session,
        tenant_id,
        customer_type="dealer",
        period="3m",
        limit=10,
    )

    assert behavior.customer_type == "dealer"
    assert behavior.customer_count == 6
    assert behavior.avg_revenue_per_customer == Decimal("116.67")
    assert behavior.avg_order_count_per_customer == Decimal("1.00")
    assert behavior.avg_categories_per_customer == Decimal("1.50")
    assert [category.category for category in behavior.top_categories] == ["Belts", "Pulleys", "Hoses"]
    assert "Renamed Live Adapter" not in [category.category for category in behavior.top_categories]
    assert behavior.top_categories[0].revenue == Decimal("480.00")
    assert behavior.top_categories[0].customer_count == 5
    assert behavior.cross_sell_opportunities[0].anchor_category == "Belts"
    assert behavior.cross_sell_opportunities[0].recommended_category == "Pulleys"
    assert behavior.cross_sell_opportunities[0].anchor_customer_count == 5
    assert behavior.cross_sell_opportunities[0].shared_customer_count == 3
    assert behavior.cross_sell_opportunities[0].outside_segment_anchor_customer_count == 2
    assert behavior.cross_sell_opportunities[0].outside_segment_shared_customer_count == 1
    assert behavior.cross_sell_opportunities[0].segment_penetration == Decimal("0.6000")
    assert behavior.cross_sell_opportunities[0].outside_segment_penetration == Decimal("0.5000")
    assert behavior.cross_sell_opportunities[0].lift_score == Decimal("1.2000")
    assert [pattern.month_start for pattern in behavior.buying_patterns] == sorted(
        pattern.month_start for pattern in behavior.buying_patterns
    )
    assert len(behavior.buying_patterns) == 3
    assert behavior.data_basis == "transactional_fallback"
    assert behavior.window_is_partial is False


@pytest.mark.asyncio
async def test_get_customer_buying_behavior_all_segment_nulls_lift_and_empty_state(
    db_session: AsyncSession,
) -> None:
    tenant_id = uuid.uuid4()
    dealers = [
        await _create_customer_for_tenant(db_session, f"Dealer All {index}", tenant_id, customer_type="dealer")
        for index in range(1, 6)
    ]
    end_users = [
        await _create_customer_for_tenant(db_session, f"End User All {index}", tenant_id, customer_type="end_user")
        for index in range(1, 3)
    ]

    belts = await _create_product_for_tenant(db_session, "Segment Belt", "Belts", tenant_id)
    pulleys = await _create_product_for_tenant(db_session, "Segment Pulley", "Pulleys", tenant_id)

    for customer in dealers[:3] + end_users[:1]:
        order = await _create_order(
            db_session,
            customer=customer,
            created_at=_month_moment(1),
            status="confirmed",
            lines=[(belts, Decimal("100.00")), (pulleys, Decimal("40.00"))],
            tenant_id=tenant_id,
        )
        await _apply_line_snapshots(db_session, order.id, ["Belts", "Pulleys"])

    for customer in dealers[3:] + end_users[1:]:
        order = await _create_order(
            db_session,
            customer=customer,
            created_at=_month_moment(2),
            status="confirmed",
            lines=[(belts, Decimal("80.00"))],
            tenant_id=tenant_id,
        )
        await _apply_line_snapshots(db_session, order.id, ["Belts"])

    await db_session.commit()

    behavior_all = await get_customer_buying_behavior(
        db_session,
        tenant_id,
        customer_type="all",
        period="3m",
        limit=10,
    )
    behavior_empty = await get_customer_buying_behavior(
        db_session,
        uuid.uuid4(),
        customer_type="dealer",
        period="3m",
        limit=10,
    )

    assert behavior_all.customer_type == "all"
    assert behavior_all.customer_count == 7
    assert behavior_all.cross_sell_opportunities[0].outside_segment_anchor_customer_count == 0
    assert behavior_all.cross_sell_opportunities[0].outside_segment_shared_customer_count == 0
    assert behavior_all.cross_sell_opportunities[0].outside_segment_penetration == Decimal("0.0000")
    assert behavior_all.cross_sell_opportunities[0].lift_score is None

    assert behavior_empty.customer_count == 0
    assert behavior_empty.avg_revenue_per_customer == Decimal("0.00")
    assert behavior_empty.avg_order_count_per_customer == Decimal("0.00")
    assert behavior_empty.avg_categories_per_customer == Decimal("0.00")
    assert behavior_empty.top_categories == []
    assert behavior_empty.cross_sell_opportunities == []
    assert len(behavior_empty.buying_patterns) == 3
    assert all(pattern.revenue == Decimal("0.00") for pattern in behavior_empty.buying_patterns)