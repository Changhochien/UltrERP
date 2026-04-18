from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from common.database import AsyncSessionLocal, engine
from common.models.inventory_stock import InventoryStock
from common.models.product import Product
from common.models.warehouse import Warehouse
from domains.inventory import services as inventory_services


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
    await engine.dispose()


@pytest.fixture
def tenant_id() -> uuid.UUID:
    return uuid.uuid4()


async def _create_product(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    code: str,
    name: str,
    category: str = "Hardware",
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
    *,
    product_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    quantity: int,
    reorder_point: int,
    on_order_qty: int = 0,
    in_transit_qty: int = 0,
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
    )
    session.add(stock)
    await session.flush()
    return stock


@pytest.mark.asyncio
async def test_list_below_reorder_products_filters_strictly_and_honors_warehouse_scope(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    main_warehouse = await _create_warehouse(
        db_session,
        tenant_id,
        code="MAIN",
        name="主倉",
    )
    overflow_warehouse = await _create_warehouse(
        db_session,
        tenant_id,
        code="OVER",
        name="Overflow",
    )
    below_product = await _create_product(
        db_session,
        tenant_id,
        code="LOW-001",
        name="螺絲組",
    )
    at_point_product = await _create_product(
        db_session,
        tenant_id,
        code="LOW-002",
        name="Washer Set",
    )
    second_below_product = await _create_product(
        db_session,
        tenant_id,
        code="LOW-003",
        name="Clamp",
    )

    await _create_inventory_stock(
        db_session,
        tenant_id,
        product_id=below_product.id,
        warehouse_id=main_warehouse.id,
        quantity=3,
        reorder_point=8,
        on_order_qty=2,
        in_transit_qty=1,
    )
    await _create_inventory_stock(
        db_session,
        tenant_id,
        product_id=at_point_product.id,
        warehouse_id=main_warehouse.id,
        quantity=8,
        reorder_point=8,
    )
    await _create_inventory_stock(
        db_session,
        tenant_id,
        product_id=second_below_product.id,
        warehouse_id=overflow_warehouse.id,
        quantity=1,
        reorder_point=4,
    )

    async def fake_get_product_supplier(
        _session: AsyncSession,
        _tenant_id: uuid.UUID,
        product_id: uuid.UUID,
    ) -> dict | None:
        if product_id == below_product.id:
            return {"name": "北聯供應"}
        return None

    monkeypatch.setattr(inventory_services, "get_product_supplier", fake_get_product_supplier)

    items, total = await inventory_services.list_below_reorder_products(db_session, tenant_id)

    assert total == 2
    product_ids = {item["product_id"] for item in items}
    assert product_ids == {below_product.id, second_below_product.id}

    first_row = next(item for item in items if item["product_id"] == below_product.id)
    assert first_row["shortage_qty"] == 5
    assert first_row["default_supplier"] == "北聯供應"
    assert first_row["on_order_qty"] == 2
    assert first_row["in_transit_qty"] == 1

    filtered_items, filtered_total = await inventory_services.list_below_reorder_products(
        db_session,
        tenant_id,
        warehouse_id=overflow_warehouse.id,
    )
    assert filtered_total == 1
    assert filtered_items[0]["product_id"] == second_below_product.id
    assert filtered_items[0]["default_supplier"] is None