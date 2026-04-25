"""Tests for stock history service behavior."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from common.models.inventory_stock import InventoryStock
from common.models.product import Product
from common.models.stock_adjustment import ReasonCode, StockAdjustment
from common.models.warehouse import Warehouse
from domains.inventory.services import get_stock_history, get_stock_history_series
from tests.db import isolated_async_session


@pytest_asyncio.fixture
async def db_session():
    async with isolated_async_session() as session:
        yield session


@pytest.fixture
def tenant_id() -> uuid.UUID:
    return uuid.uuid4()


async def _seed_stock_history_slice(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> tuple[Product, Warehouse]:
    warehouse = Warehouse(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name="History Warehouse",
        code=f"HWH{uuid.uuid4().hex[:6].upper()}",
        is_active=True,
    )
    product = Product(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        code=f"HIST-{uuid.uuid4().hex[:6].upper()}",
        name="History Product",
        category="Test",
        status="active",
    )
    stock = InventoryStock(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        product_id=product.id,
        warehouse_id=warehouse.id,
        quantity=826,
        reorder_point=25,
    )
    adjustments = [
        StockAdjustment(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            product_id=product.id,
            warehouse_id=warehouse.id,
            quantity_change=40033,
            reason_code=ReasonCode.SUPPLIER_DELIVERY,
            actor_id="legacy_import",
            notes="Legacy import: receipts",
            created_at=datetime(2026, 1, 10, tzinfo=UTC),
        ),
        StockAdjustment(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            product_id=product.id,
            warehouse_id=warehouse.id,
            quantity_change=-40710,
            reason_code=ReasonCode.SALES_RESERVATION,
            actor_id="backfill-script",
            notes="Legacy sales backfill",
            created_at=datetime(2026, 2, 5, tzinfo=UTC),
        ),
        StockAdjustment(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            product_id=product.id,
            warehouse_id=warehouse.id,
            quantity_change=1503,
            reason_code=ReasonCode.CORRECTION,
            actor_id="reconciliation-apply",
            notes="Approved inventory reconciliation correction by hcchang as of 2026-04-17",
            created_at=datetime(2026, 4, 17, tzinfo=UTC),
        ),
    ]

    session.add_all([warehouse, product, stock, *adjustments])
    await session.flush()
    return product, warehouse


async def _seed_dense_stock_history_slice(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> InventoryStock:
    warehouse = Warehouse(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name="Dense History Warehouse",
        code=f"DWH{uuid.uuid4().hex[:6].upper()}",
        is_active=True,
    )
    product = Product(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        code=f"DENSE-{uuid.uuid4().hex[:6].upper()}",
        name="Dense History Product",
        category="Test",
        status="active",
    )
    stock = InventoryStock(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        product_id=product.id,
        warehouse_id=warehouse.id,
        quantity=8,
        reorder_point=5,
    )
    adjustments = [
        StockAdjustment(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            product_id=product.id,
            warehouse_id=warehouse.id,
            quantity_change=10,
            reason_code=ReasonCode.SUPPLIER_DELIVERY,
            actor_id="warehouse-user",
            created_at=datetime(2026, 1, 1, 8, 0, tzinfo=UTC),
        ),
        StockAdjustment(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            product_id=product.id,
            warehouse_id=warehouse.id,
            quantity_change=-2,
            reason_code=ReasonCode.SALES_RESERVATION,
            actor_id="sales-user",
            created_at=datetime(2026, 1, 3, 8, 0, tzinfo=UTC),
        ),
    ]

    session.add_all([warehouse, product, stock, *adjustments])
    await session.flush()
    return stock


@pytest.mark.asyncio
async def test_get_stock_history_hides_reconciliation_apply_adjustments_from_visible_points(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
) -> None:
    product, warehouse = await _seed_stock_history_slice(db_session, tenant_id=tenant_id)

    result = await get_stock_history(
        db_session,
        tenant_id,
        product.id,
        warehouse.id,
        start_date=datetime(2026, 1, 1, tzinfo=UTC),
        granularity="event",
    )

    assert result["current_stock"] == 826
    assert [point["reason_code"] for point in result["points"]] == [
        ReasonCode.SUPPLIER_DELIVERY.value,
        ReasonCode.SALES_RESERVATION.value,
    ]
    assert all(
        "Approved inventory reconciliation correction" not in (point["notes"] or "")
        for point in result["points"]
    )
    assert result["points"][-1]["running_stock"] == 826


@pytest.mark.asyncio
async def test_get_stock_history_series_carries_stock_through_zero_filled_days(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
) -> None:
    stock = await _seed_dense_stock_history_slice(db_session, tenant_id=tenant_id)

    result = await get_stock_history_series(
        db_session,
        tenant_id,
        stock.id,
        start_date="2026-01-01",
        end_date="2026-01-04",
    )

    assert [point["bucket_start"] for point in result["points"]] == [
        "2026-01-01",
        "2026-01-02",
        "2026-01-03",
        "2026-01-04",
    ]
    assert [point["value"] for point in result["points"]] == [10.0, 10.0, 8.0, 8.0]
    assert [point["is_zero_filled"] for point in result["points"]] == [False, True, False, True]
    assert result["range"]["bucket"] == "day"