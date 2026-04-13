"""Remove reorder-point integration test fixtures from the shared dev database."""

from __future__ import annotations

import asyncio

from sqlalchemy import text

from common.database import AsyncSessionLocal

TEST_PRODUCT_NAMES = [
    "Confirm Test Product",
    "Fallback Product",
    "Multi Source Product",
    "Product With History",
    "Product Without History",
    "Supplier Default Fallback Product",
]

TEST_SUPPLIER_NAMES = [
    "History Supplier",
    "Supplier A",
    "Supplier B",
    "Supplier With Default",
]

TEST_WAREHOUSE_NAME = "ROP Test WH"


async def _count_remaining(session) -> dict[str, list[tuple[str, int]]]:
    products = (
        await session.execute(
            text(
                "select name, count(*)::int from product where name = any(:names) group by name order by name"
            ),
            {"names": TEST_PRODUCT_NAMES},
        )
    ).all()
    warehouses = (
        await session.execute(
            text(
                "select name, count(*)::int from warehouse where name = :name group by name"
            ),
            {"name": TEST_WAREHOUSE_NAME},
        )
    ).all()
    suppliers = (
        await session.execute(
            text(
                "select name, count(*)::int from supplier where name = any(:names) group by name order by name"
            ),
            {"names": TEST_SUPPLIER_NAMES},
        )
    ).all()
    return {
        "products": [(name, count) for name, count in products],
        "warehouses": [(name, count) for name, count in warehouses],
        "suppliers": [(name, count) for name, count in suppliers],
    }


async def main() -> None:
    async with AsyncSessionLocal() as session:
        before = await _count_remaining(session)
        if not before["products"] and not before["warehouses"] and not before["suppliers"]:
            print("No reorder-point test fixtures found.")
            return

        params = {
            "names": TEST_PRODUCT_NAMES,
            "supplier_names": TEST_SUPPLIER_NAMES,
            "warehouse": TEST_WAREHOUSE_NAME,
        }

        await session.execute(
            text(
                """
                with target_products as (select id from product where name = any(:names)),
                     target_warehouses as (select id from warehouse where name = :warehouse)
                delete from supplier_order_line
                where product_id in (select id from target_products)
                   or warehouse_id in (select id from target_warehouses)
                """
            ),
            params,
        )
        await session.execute(
            text(
                """
                with target_products as (select id from product where name = any(:names))
                delete from order_lines where product_id in (select id from target_products)
                """
            ),
            params,
        )
        await session.execute(
            text(
                """
                with target_products as (select id from product where name = any(:names)),
                     target_warehouses as (select id from warehouse where name = :warehouse)
                delete from inventory_stock
                where product_id in (select id from target_products)
                   or warehouse_id in (select id from target_warehouses)
                """
            ),
            params,
        )
        await session.execute(
            text(
                """
                with target_products as (select id from product where name = any(:names)),
                     target_warehouses as (select id from warehouse where name = :warehouse)
                delete from stock_adjustment
                where product_id in (select id from target_products)
                   or warehouse_id in (select id from target_warehouses)
                """
            ),
            params,
        )
        await session.execute(
            text(
                "delete from reorder_alert where product_id in (select id from product where name = any(:names))"
            ),
            params,
        )
        await session.execute(
            text(
                "delete from supplier_order where supplier_id in (select id from supplier where name = any(:supplier_names))"
            ),
            params,
        )
        await session.execute(text("delete from product where name = any(:names)"), params)
        await session.execute(text("delete from warehouse where name = :warehouse"), params)
        await session.execute(text("delete from supplier where name = any(:supplier_names)"), params)

        await session.commit()

    async with AsyncSessionLocal() as session:
        after = await _count_remaining(session)

    print({"before": before, "after": after})


if __name__ == "__main__":
    asyncio.run(main())
