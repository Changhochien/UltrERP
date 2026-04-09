"""Direct SQL ROP computation — fast, no Python iteration over products."""
import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

ENGINE_URL = "postgresql+asyncpg://ultr_erp@localhost:5432/ultr_erp"
TENANT_ID = "00000000-0000-0000-0000-000000000001"
WAREHOUSE_ID = "e0e9028a-7d6c-5abd-976a-735586cedc34"
DEMAND_LOOKBACK_DAYS = 365
SAFETY_FACTOR = 0.5
DEFAULT_LEAD_TIME = 7  # days


async def main():
    engine = create_async_engine(ENGINE_URL)
    async with engine.connect() as conn:
        # Compute avg daily usage per product+warehouse from stock_adjustment
        # avg_daily = SUM(ABS(quantity_change)) / DEMAND_LOOKBACK_DAYS
        # Only for products with >= 2 demand events (MIN_DEMAND_EVENTS)
        sql = text(f"""
            WITH daily_usage AS (
                SELECT
                    sa.product_id,
                    sa.warehouse_id,
                    SUM(ABS(sa.quantity_change)) AS total_qty,
                    COUNT(sa.id) AS event_count
                FROM stock_adjustment sa
                WHERE sa.tenant_id = :tenant_id
                  AND sa.reason_code = 'sales_reservation'
                  AND sa.created_at >= NOW() - INTERVAL '{DEMAND_LOOKBACK_DAYS} days'
                GROUP BY sa.product_id, sa.warehouse_id
                HAVING COUNT(sa.id) >= 2
            ),
            enriched AS (
                SELECT
                    du.product_id,
                    du.warehouse_id,
                    du.total_qty,
                    du.event_count,
                    du.total_qty::float / {DEMAND_LOOKBACK_DAYS} AS avg_daily,
                    CASE
                        WHEN du.total_qty::float / {DEMAND_LOOKBACK_DAYS} * {DEFAULT_LEAD_TIME} * (1 + {SAFETY_FACTOR}) < 1
                        THEN 1
                        ELSE ROUND(du.total_qty::float / {DEMAND_LOOKBACK_DAYS} * {DEFAULT_LEAD_TIME} * (1 + {SAFETY_FACTOR}))
                    END AS reorder_point
                FROM daily_usage du
            )
            UPDATE inventory_stock AS i
            SET reorder_point = e.reorder_point
            FROM enriched e
            WHERE i.product_id = e.product_id
              AND i.warehouse_id = e.warehouse_id
              AND i.tenant_id = :tenant_id
            RETURNING
                (SELECT p.code FROM product p WHERE p.id = e.product_id) AS product_code,
                e.reorder_point,
                e.avg_daily
        """)

        result = await conn.execute(sql, {"tenant_id": TENANT_ID})
        rows = result.fetchall()
        await conn.commit()

        print(f"Updated {len(rows)} products with reorder_point:")
        for r in rows[:20]:
            print(f"  {r[0]}: ROP={r[1]}, avg_daily={r[2]:.2f}")
        if len(rows) > 20:
            print(f"  ... and {len(rows) - 20} more")

        # Summary
        total_with_rop = await conn.execute(
            text("SELECT COUNT(*) FROM inventory_stock WHERE tenant_id = :t AND reorder_point > 0"),
            {"t": TENANT_ID}
        )
        print(f"\nTotal inventory_stock rows with reorder_point > 0: {total_with_rop.scalar()}")

    await engine.dispose()


asyncio.run(main())
