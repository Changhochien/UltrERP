from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from common.database import get_db
from common.model_registry import register_all_models
from common.models.audit_log import AuditLog
from common.models.inventory_stock import InventoryStock
from common.models.product import Product
from common.models.warehouse import Warehouse
from tests.db import isolated_async_session
from tests.domains.orders._helpers import auth_header

register_all_models()

_MISSING_OVERRIDE = object()
_TEST_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    async with isolated_async_session() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    previous = app.dependency_overrides.get(get_db, _MISSING_OVERRIDE)

    async def override() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = override
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
        headers=auth_header(),
    ) as async_client:
        yield async_client

    if previous is _MISSING_OVERRIDE:
        app.dependency_overrides.pop(get_db, None)
    else:
        app.dependency_overrides[get_db] = previous


async def _create_product(
    session: AsyncSession,
    *,
    code: str,
    name: str,
) -> Product:
    product = Product(
        id=uuid.uuid4(),
        tenant_id=_TEST_TENANT_ID,
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
    *,
    code: str,
    name: str,
) -> Warehouse:
    warehouse = Warehouse(
        id=uuid.uuid4(),
        tenant_id=_TEST_TENANT_ID,
        code=code,
        name=name,
        is_active=True,
    )
    session.add(warehouse)
    await session.flush()
    return warehouse


async def _create_inventory_stock(
    session: AsyncSession,
    *,
    product_id: uuid.UUID,
    warehouse_id: uuid.UUID,
) -> InventoryStock:
    stock = InventoryStock(
        id=uuid.uuid4(),
        tenant_id=_TEST_TENANT_ID,
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
async def test_get_product_audit_log_endpoint_returns_sql_backed_audit_items(
    db_session: AsyncSession,
    client: AsyncClient,
) -> None:
    product = await _create_product(db_session, code="AUD-HTTP-001", name="Audit HTTP Product")
    main_warehouse = await _create_warehouse(db_session, code="MAIN", name="Main")
    backup_warehouse = await _create_warehouse(db_session, code="BACK", name="Backup")
    main_stock = await _create_inventory_stock(
        db_session,
        product_id=product.id,
        warehouse_id=main_warehouse.id,
    )
    backup_stock = await _create_inventory_stock(
        db_session,
        product_id=product.id,
        warehouse_id=backup_warehouse.id,
    )

    base_time = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)
    db_session.add_all(
        [
            AuditLog(
                id=uuid.uuid4(),
                tenant_id=_TEST_TENANT_ID,
                actor_id="user-1",
                actor_type="user",
                action="update",
                entity_type="inventory_stock",
                entity_id=str(main_stock.id),
                before_state={"reorder_point": 5},
                after_state={"reorder_point": 8},
                created_at=base_time,
            ),
            AuditLog(
                id=uuid.uuid4(),
                tenant_id=_TEST_TENANT_ID,
                actor_id="user-2",
                actor_type="user",
                action="update",
                entity_type="inventory_stock",
                entity_id=str(backup_stock.id),
                before_state={"safety_factor": 1.0},
                after_state={"safety_factor": 1.5},
                created_at=base_time + timedelta(minutes=1),
            ),
            AuditLog(
                id=uuid.uuid4(),
                tenant_id=_TEST_TENANT_ID,
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

    response = await client.get(f"/api/v1/inventory/products/{product.id}/audit-log")

    assert response.status_code == 200, response.json()
    body = response.json()
    assert body["total"] == 3
    assert [item["field"] for item in body["items"]] == [
        "status",
        "safety_factor",
        "reorder_point",
    ]
    assert body["items"][0]["old_value"] == "active"
    assert body["items"][0]["new_value"] == "inactive"
    assert body["items"][1]["old_value"] == "1.0"
    assert body["items"][1]["new_value"] == "1.5"
    assert body["items"][2]["old_value"] == "5"
    assert body["items"][2]["new_value"] == "8"