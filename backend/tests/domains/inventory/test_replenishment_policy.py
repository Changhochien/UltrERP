"""Focused tests for policy-aware replenishment calculations."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pytest
import pytest_asyncio

from common.models.inventory_stock import InventoryStock
from common.models.product import Product
from common.models.stock_adjustment import ReasonCode, StockAdjustment
from common.models.warehouse import Warehouse
from domains.inventory.reorder_point import (
    apply_reorder_points,
    compute_reorder_point_preview_row,
    compute_reorder_points_preview,
)
from tests.db import isolated_async_session


@pytest_asyncio.fixture
async def db_session():
    async with isolated_async_session() as session:
        yield session


@pytest.fixture
def tenant_id() -> uuid.UUID:
    return uuid.uuid4()


async def _seed_stock(
    session,
    *,
    tenant_id: uuid.UUID,
    quantity: int = 5,
    reorder_point: int = 0,
    safety_factor: float = 0.0,
    lead_time_days: int = 0,
    review_cycle_days: int = 0,
) -> tuple[Product, Warehouse, InventoryStock]:
    warehouse = Warehouse(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name=f"ROP Test WH {uuid.uuid4().hex[:6]}",
        code=f"RWH{uuid.uuid4().hex[:6].upper()}",
        is_active=True,
    )
    product = Product(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        code=f"SKU{uuid.uuid4().hex[:6].upper()}",
        name="Policy Test Product",
        category="Test",
        status="active",
    )
    stock = InventoryStock(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        product_id=product.id,
        warehouse_id=warehouse.id,
        quantity=quantity,
        reorder_point=reorder_point,
        safety_factor=safety_factor,
        lead_time_days=lead_time_days,
        review_cycle_days=review_cycle_days,
    )

    session.add_all([warehouse, product, stock])
    await session.flush()
    return product, warehouse, stock


async def _add_sales_history(
    session,
    *,
    tenant_id: uuid.UUID,
    product_id,
    warehouse_id,
    quantities: list[int],
) -> None:
    for offset, quantity in enumerate(quantities, start=1):
        session.add(
            StockAdjustment(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                product_id=product_id,
                warehouse_id=warehouse_id,
                quantity_change=-quantity,
                reason_code=ReasonCode.SALES_RESERVATION,
                actor_id="test-actor",
                created_at=datetime.now() - timedelta(days=offset * 10),
            )
        )
    await session.flush()


@pytest.mark.asyncio
async def test_preview_uses_review_cycle_for_target_stock_and_order_qty(db_session, tenant_id):
    product, warehouse, _stock = await _seed_stock(
        db_session,
        tenant_id=tenant_id,
        quantity=5,
    )
    await _add_sales_history(
        db_session,
        tenant_id=tenant_id,
        product_id=product.id,
        warehouse_id=warehouse.id,
        quantities=[9, 9],
    )

    preview = await compute_reorder_point_preview_row(
        db_session,
        tenant_id,
        product.id,
        warehouse.id,
        safety_factor=0.5,
        review_cycle_days=85,
        lead_time_days_override=7,
        current_quantity=5,
    )

    assert preview["skipped_reason"] is None
    assert preview["avg_daily_usage"] == 0.2
    assert preview["reorder_point"] == 2
    assert preview["target_stock_level"] == 19
    assert preview["suggested_order_qty"] == 14


@pytest.mark.asyncio
async def test_preview_prefers_persisted_overrides_for_batch_compute(db_session, tenant_id):
    product, warehouse, _stock = await _seed_stock(
        db_session,
        tenant_id=tenant_id,
        safety_factor=0.8,
        lead_time_days=12,
        review_cycle_days=60,
    )
    await _add_sales_history(
        db_session,
        tenant_id=tenant_id,
        product_id=product.id,
        warehouse_id=warehouse.id,
        quantities=[9, 9],
    )

    candidates, skipped = await compute_reorder_points_preview(
        db_session,
        tenant_id,
        safety_factor=0.5,
        demand_lookback_days=90,
        lead_time_lookback_days=180,
        warehouse_id=warehouse.id,
    )

    assert skipped == []
    assert len(candidates) == 1

    candidate = candidates[0]
    assert candidate["lead_time_source"] == "manual_override"
    assert candidate["lead_time_days"] == 12
    assert candidate["review_cycle_days"] == 60
    assert candidate["safety_factor"] == 0.8
    assert candidate["reorder_point"] == 4
    assert candidate["target_stock_level"] == 16


@pytest.mark.asyncio
async def test_apply_persists_replenishment_settings(db_session, tenant_id):
    product, warehouse, stock = await _seed_stock(
        db_session,
        tenant_id=tenant_id,
        quantity=5,
    )

    result = await apply_reorder_points(
        db_session,
        tenant_id,
        selected_rows=[
            {
                "product_id": product.id,
                "warehouse_id": warehouse.id,
                "reorder_point": 2,
                "safety_factor": 0.5,
                "lead_time_days": 7,
                "review_cycle_days": 85,
            }
        ],
        safety_factor=0.5,
        demand_lookback_days=90,
        lead_time_lookback_days=180,
    )

    await db_session.refresh(stock)

    assert result["updated_count"] == 1
    assert stock.reorder_point == 2
    assert stock.safety_factor == 0.5
    assert stock.lead_time_days == 7
    assert stock.review_cycle_days == 85
