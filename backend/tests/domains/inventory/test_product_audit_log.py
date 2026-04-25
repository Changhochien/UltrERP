from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from common.model_registry import register_all_models
from common.models.audit_log import AuditLog
from common.models.inventory_stock import InventoryStock
from common.models.product import Product
from common.models.warehouse import Warehouse
from domains.inventory._product_audit_support import get_product_audit_log
from tests.db import isolated_async_session

register_all_models()


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    async with isolated_async_session() as session:
        yield session


@pytest.fixture
def tenant_id() -> uuid.UUID:
    return uuid.uuid4()


async def _create_product(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    code: str,
    name: str,
) -> Product:
    product = Product(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        code=code,
        name=name,
        category="Hardware",
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
    *,
    product_id: uuid.UUID,
    warehouse_id: uuid.UUID,
) -> InventoryStock:
    stock = InventoryStock(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        product_id=product_id,
        warehouse_id=warehouse_id,
        quantity=10,
        reorder_point=5,
        safety_factor=1.0,
        lead_time_days=7,
    )
    session.add(stock)
    await session.flush()
    return stock


@pytest.mark.asyncio
async def test_get_product_audit_log_handles_multiple_stock_rows(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
) -> None:
    product = await _create_product(
        db_session,
        tenant_id,
        code="AUD-001",
        name="Audit Product",
    )
    primary_warehouse = await _create_warehouse(
        db_session,
        tenant_id,
        code="MAIN",
        name="Main",
    )
    overflow_warehouse = await _create_warehouse(
        db_session,
        tenant_id,
        code="OVER",
        name="Overflow",
    )
    primary_stock = await _create_inventory_stock(
        db_session,
        tenant_id,
        product_id=product.id,
        warehouse_id=primary_warehouse.id,
    )
    overflow_stock = await _create_inventory_stock(
        db_session,
        tenant_id,
        product_id=product.id,
        warehouse_id=overflow_warehouse.id,
    )

    base_time = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)
    db_session.add_all(
        [
            AuditLog(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                actor_id="user-1",
                actor_type="user",
                action="update",
                entity_type="inventory_stock",
                entity_id=str(primary_stock.id),
                before_state={"reorder_point": 5},
                after_state={"reorder_point": 8},
                created_at=base_time,
            ),
            AuditLog(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                actor_id="user-2",
                actor_type="user",
                action="update",
                entity_type="inventory_stock",
                entity_id=str(overflow_stock.id),
                before_state={"safety_factor": 1.0},
                after_state={"safety_factor": 1.5},
                created_at=base_time + timedelta(minutes=1),
            ),
            AuditLog(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                actor_id="user-3",
                actor_type="user",
                action="update",
                entity_type="product",
                entity_id=str(product.id),
                before_state={"status": "active"},
                after_state={"status": "inactive"},
                created_at=base_time + timedelta(minutes=2),
            ),
        ]
    )
    await db_session.flush()

    result = await get_product_audit_log(db_session, tenant_id, product.id)

    assert result["total"] == 3
    assert [item["field"] for item in result["items"]] == [
        "status",
        "safety_factor",
        "reorder_point",
    ]
    assert result["items"][0]["old_value"] == "active"
    assert result["items"][0]["new_value"] == "inactive"
    assert result["items"][1]["old_value"] == "1.0"
    assert result["items"][1]["new_value"] == "1.5"
    assert result["items"][2]["old_value"] == "5"
    assert result["items"][2]["new_value"] == "8"