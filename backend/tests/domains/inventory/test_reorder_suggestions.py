from __future__ import annotations

from datetime import date
from decimal import Decimal
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.database import AsyncSessionLocal, engine
from common.model_registry import register_all_models
from common.models.inventory_stock import InventoryStock
from common.models.product import Product
from common.models.supplier import Supplier
from common.models.supplier_order import SupplierOrder, SupplierOrderLine
from common.models.warehouse import Warehouse
from domains.inventory import services as inventory_services

register_all_models()


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
    quantity: int,
    reorder_point: int,
    target_stock_qty: int,
    on_order_qty: int = 0,
    in_transit_qty: int = 0,
    reserved_qty: int = 0,
) -> InventoryStock:
    stock = InventoryStock(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        product_id=product_id,
        warehouse_id=warehouse_id,
        quantity=quantity,
        reorder_point=reorder_point,
        target_stock_qty=target_stock_qty,
        on_order_qty=on_order_qty,
        in_transit_qty=in_transit_qty,
        reserved_qty=reserved_qty,
    )
    session.add(stock)
    await session.flush()
    return stock


async def _create_supplier(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    name: str,
    lead_time_days: int = 7,
) -> Supplier:
    supplier = Supplier(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name=name,
        default_lead_time_days=lead_time_days,
        is_active=True,
    )
    session.add(supplier)
    await session.flush()
    return supplier


async def _create_received_supplier_order(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    supplier_id: uuid.UUID,
    product_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    unit_price: Decimal,
) -> SupplierOrder:
    order = SupplierOrder(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        supplier_id=supplier_id,
        order_number=f"PO-{uuid.uuid4().hex[:8].upper()}",
        status="received",
        order_date=date(2026, 4, 1),
        received_date=date(2026, 4, 3),
        created_by="tests",
    )
    session.add(order)
    await session.flush()

    line = SupplierOrderLine(
        id=uuid.uuid4(),
        order_id=order.id,
        product_id=product_id,
        warehouse_id=warehouse_id,
        quantity_ordered=12,
        unit_price=unit_price,
        quantity_received=12,
    )
    session.add(line)
    await session.flush()
    return order


@pytest.mark.asyncio
async def test_list_reorder_suggestions_uses_target_stock_formula_and_supplier_hint(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
) -> None:
    product = await _create_product(db_session, tenant_id, code="ROP-001", name="Rotor")
    warehouse = await _create_warehouse(db_session, tenant_id, code="MAIN", name="Main Warehouse")
    supplier = await _create_supplier(db_session, tenant_id, name="Acme Supply", lead_time_days=6)
    await _create_inventory_stock(
        db_session,
        tenant_id,
        product_id=product.id,
        warehouse_id=warehouse.id,
        quantity=5,
        reorder_point=10,
        target_stock_qty=30,
        on_order_qty=4,
        in_transit_qty=3,
        reserved_qty=2,
    )
    await _create_received_supplier_order(
        db_session,
        tenant_id,
        supplier_id=supplier.id,
        product_id=product.id,
        warehouse_id=warehouse.id,
        unit_price=Decimal("12.50"),
    )

    items, total = await inventory_services.list_reorder_suggestions(db_session, tenant_id)

    assert total == 1
    item = items[0]
    assert item["product_id"] == product.id
    assert item["product_code"] == product.code
    assert item["warehouse_id"] == warehouse.id
    assert item["inventory_position"] == 10
    assert item["target_stock_qty"] == 30
    assert item["suggested_qty"] == 20
    assert item["supplier_hint"]["supplier_id"] == supplier.id
    assert item["supplier_hint"]["name"] == supplier.name
    assert item["supplier_hint"]["default_lead_time_days"] == 6


@pytest.mark.asyncio
async def test_list_reorder_suggestions_falls_back_to_reorder_point_shortfall(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
) -> None:
    product = await _create_product(db_session, tenant_id, code="ROP-002", name="Bracket")
    warehouse = await _create_warehouse(db_session, tenant_id, code="OVER", name="Overflow")
    await _create_inventory_stock(
        db_session,
        tenant_id,
        product_id=product.id,
        warehouse_id=warehouse.id,
        quantity=4,
        reorder_point=12,
        target_stock_qty=0,
        on_order_qty=1,
        reserved_qty=2,
    )

    items, total = await inventory_services.list_reorder_suggestions(db_session, tenant_id)

    assert total == 1
    item = items[0]
    assert item["inventory_position"] == 3
    assert item["target_stock_qty"] is None
    assert item["suggested_qty"] == 9
    assert item["supplier_hint"] is None


@pytest.mark.asyncio
async def test_create_reorder_suggestion_orders_groups_by_supplier_and_returns_unresolved_rows(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    product_a = await _create_product(db_session, tenant_id, code="ROP-101", name="Valve")
    product_b = await _create_product(db_session, tenant_id, code="ROP-102", name="Bearing")
    product_c = await _create_product(db_session, tenant_id, code="ROP-103", name="Coupler")
    warehouse = await _create_warehouse(db_session, tenant_id, code="MAIN", name="Main Warehouse")
    supplier = await _create_supplier(db_session, tenant_id, name="Beta Supply", lead_time_days=4)

    for product in (product_a, product_b, product_c):
        await _create_inventory_stock(
            db_session,
            tenant_id,
            product_id=product.id,
            warehouse_id=warehouse.id,
            quantity=2,
            reorder_point=10,
            target_stock_qty=15,
        )

    async def fake_batch_get_product_suppliers(
        _session: AsyncSession,
        _tenant_id: uuid.UUID,
        product_ids: list[uuid.UUID],
    ) -> dict[uuid.UUID, dict | None]:
        mapping: dict[uuid.UUID, dict | None] = {product_id: None for product_id in product_ids}
        for product_id in (product_a.id, product_b.id):
            mapping[product_id] = {
                "supplier_id": supplier.id,
                "name": supplier.name,
                "unit_cost": 8.25,
                "default_lead_time_days": supplier.default_lead_time_days,
            }
        return mapping

    monkeypatch.setattr(
        inventory_services,
        "_batch_get_product_suppliers",
        fake_batch_get_product_suppliers,
    )

    result = await inventory_services.create_reorder_suggestion_orders(
        db_session,
        tenant_id,
        items=[
            {"product_id": product_a.id, "warehouse_id": warehouse.id, "suggested_qty": 5},
            {"product_id": product_b.id, "warehouse_id": warehouse.id, "suggested_qty": 7},
            {"product_id": product_c.id, "warehouse_id": warehouse.id, "suggested_qty": 6},
        ],
        actor_id="planner",
    )

    assert len(result["created_orders"]) == 1
    assert len(result["unresolved_rows"]) == 1
    created = result["created_orders"][0]
    assert created["supplier_id"] == supplier.id
    assert created["line_count"] == 2
    assert result["unresolved_rows"][0]["product_id"] == product_c.id
    assert result["unresolved_rows"][0]["product_code"] == product_c.code

    order = await db_session.get(SupplierOrder, created["order_id"])
    assert order is not None
    assert order.supplier_id == supplier.id

    lines = list(
        (
            await db_session.execute(
                select(SupplierOrderLine).where(SupplierOrderLine.order_id == order.id)
            )
        ).scalars().all()
    )
    assert len(lines) == 2
    assert {line.product_id for line in lines} == {product_a.id, product_b.id}
