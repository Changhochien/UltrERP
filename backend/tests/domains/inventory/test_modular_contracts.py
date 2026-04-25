from __future__ import annotations

import inspect
import uuid
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from common.models.inventory_stock import InventoryStock
from common.models.product import Product
from common.models.stock_adjustment import ReasonCode, StockAdjustment
from common.models.warehouse import Warehouse
from domains.inventory import commands, queries, services
from tests.db import isolated_async_session


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    async with isolated_async_session() as session:
        yield session


@pytest.fixture
def tenant_id() -> uuid.UUID:
    return uuid.uuid4()


def test_command_exception_identity_matches_services() -> None:
    assert commands.InsufficientStockError is services.InsufficientStockError
    assert commands.TransferValidationError is services.TransferValidationError
    assert commands.PhysicalCountNotFoundError is services.PhysicalCountNotFoundError
    assert commands.PhysicalCountConflictError is services.PhysicalCountConflictError
    assert commands.PhysicalCountStateError is services.PhysicalCountStateError


def test_public_modular_signatures_match_services() -> None:
    for module in (commands, queries):
        for name in getattr(module, "__all__", []):
            if not hasattr(services, name):
                continue
            module_value = getattr(module, name)
            services_value = getattr(services, name)
            if inspect.isclass(module_value) or inspect.isclass(services_value):
                continue
            if not callable(module_value) or not callable(services_value):
                continue
            assert str(inspect.signature(module_value)) == str(
                inspect.signature(services_value)
            ), name


async def _seed_dense_stock_history_slice(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> InventoryStock:
    warehouse = Warehouse(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name="Dense History Warehouse",
        code=f"DHW{uuid.uuid4().hex[:6].upper()}",
    )
    product = Product(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        code=f"DH-{uuid.uuid4().hex[:6].upper()}",
        name="Dense History Product",
        unit="pcs",
        status="active",
    )
    stock = InventoryStock(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        product_id=product.id,
        warehouse_id=warehouse.id,
        quantity=8,
        reorder_point=0,
    )
    session.add_all([warehouse, product, stock])
    await session.flush()

    session.add_all(
        [
            StockAdjustment(
                tenant_id=tenant_id,
                product_id=product.id,
                warehouse_id=warehouse.id,
                quantity_change=10,
                reason_code=ReasonCode.SALES_RESERVATION,
                actor_id="seed",
                created_at=datetime(2026, 1, 1, 2, 0, tzinfo=UTC),
            ),
            StockAdjustment(
                tenant_id=tenant_id,
                product_id=product.id,
                warehouse_id=warehouse.id,
                quantity_change=-2,
                reason_code=ReasonCode.SALES_RESERVATION,
                actor_id="seed",
                created_at=datetime(2026, 1, 3, 2, 0, tzinfo=UTC),
            ),
        ]
    )
    await session.flush()
    return stock


@pytest.mark.asyncio
async def test_queries_stock_history_series_matches_services(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
) -> None:
    stock = await _seed_dense_stock_history_slice(db_session, tenant_id=tenant_id)

    modular = await queries.get_stock_history_series(
        db_session,
        tenant_id,
        stock.id,
        start_date="2026-01-01",
        end_date="2026-01-04",
    )
    legacy = await services.get_stock_history_series(
        db_session,
        tenant_id,
        stock.id,
        start_date="2026-01-01",
        end_date="2026-01-04",
    )

    assert modular == legacy