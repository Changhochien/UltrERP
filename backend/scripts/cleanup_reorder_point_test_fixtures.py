"""Remove reorder-point integration test fixtures from the shared dev database."""

from __future__ import annotations

import asyncio

from sqlalchemy import delete, or_, select

from common.database import AsyncSessionLocal
from common.models.inventory_stock import InventoryStock
from common.models.product import Product
from common.models.reorder_alert import ReorderAlert
from common.models.stock_adjustment import StockAdjustment
from common.models.supplier import Supplier
from common.models.supplier_order import SupplierOrder, SupplierOrderLine
from common.models.warehouse import Warehouse

TEST_PRODUCT_NAMES = {
    "Confirm Test Product",
    "Fallback Product",
    "Multi Source Product",
    "Product With History",
    "Product Without History",
    "Supplier Default Fallback Product",
}

TEST_SUPPLIER_NAMES = {
    "History Supplier",
    "Supplier A",
    "Supplier B",
    "Supplier With Default",
}

TEST_WAREHOUSE_NAMES = {"ROP Test WH"}


async def main() -> None:
    async with AsyncSessionLocal() as session:
        product_ids = list(
            (await session.execute(select(Product.id).where(Product.name.in_(TEST_PRODUCT_NAMES)))).scalars()
        )
        warehouse_ids = list(
            (await session.execute(select(Warehouse.id).where(Warehouse.name.in_(TEST_WAREHOUSE_NAMES)))).scalars()
        )
        supplier_ids = list(
            (await session.execute(select(Supplier.id).where(Supplier.name.in_(TEST_SUPPLIER_NAMES)))).scalars()
        )

        if not product_ids and not warehouse_ids and not supplier_ids:
            print("No reorder-point test fixtures found.")
            return

        filters = []
        if product_ids:
            filters.append(SupplierOrderLine.product_id.in_(product_ids))
        if warehouse_ids:
            filters.append(SupplierOrderLine.warehouse_id.in_(warehouse_ids))

        order_ids: list = []
        if filters:
            order_ids = list(
                (await session.execute(
                    select(SupplierOrderLine.order_id).where(or_(*filters)).distinct()
                )).scalars()
            )

        if order_ids:
            await session.execute(delete(SupplierOrderLine).where(SupplierOrderLine.order_id.in_(order_ids)))
            await session.execute(delete(SupplierOrder).where(SupplierOrder.id.in_(order_ids)))

        stock_filters = []
        if product_ids:
            stock_filters.append(InventoryStock.product_id.in_(product_ids))
        if warehouse_ids:
            stock_filters.append(InventoryStock.warehouse_id.in_(warehouse_ids))
        if stock_filters:
            await session.execute(delete(InventoryStock).where(or_(*stock_filters)))

        adjustment_filters = []
        if product_ids:
            adjustment_filters.append(StockAdjustment.product_id.in_(product_ids))
        if warehouse_ids:
            adjustment_filters.append(StockAdjustment.warehouse_id.in_(warehouse_ids))
        if adjustment_filters:
            await session.execute(delete(StockAdjustment).where(or_(*adjustment_filters)))

        alert_filters = []
        if product_ids:
            alert_filters.append(ReorderAlert.product_id.in_(product_ids))
        if warehouse_ids:
            alert_filters.append(ReorderAlert.warehouse_id.in_(warehouse_ids))
        if alert_filters:
            await session.execute(delete(ReorderAlert).where(or_(*alert_filters)))

        if product_ids:
            await session.execute(delete(Product).where(Product.id.in_(product_ids)))

        if warehouse_ids:
            await session.execute(delete(Warehouse).where(Warehouse.id.in_(warehouse_ids)))

        if supplier_ids:
            await session.execute(delete(Supplier).where(Supplier.id.in_(supplier_ids)))

        await session.commit()

        print(
            {
                "deleted_products": len(product_ids),
                "deleted_warehouses": len(warehouse_ids),
                "deleted_suppliers": len(supplier_ids),
                "deleted_orders": len(order_ids),
            }
        )


if __name__ == "__main__":
    asyncio.run(main())