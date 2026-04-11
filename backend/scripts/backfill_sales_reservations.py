"""Backfill stock_adjustment records from legacy sales demand data.

Imports sales demand from tbsslipx (sales header) JOIN tbsslipdtx (sales lines).
This is the correct source for actual product demand — tbsslipdtx carries
593K sales-order lines with col_23 = signed quantity per line.

Column mapping:
  - tbslipx:    col_3 = invoice_date (from header)
  - tbsslipdtx: col_7 = product_code, col_23 = signed qty (+outbound/-return)

Usage:
    python -m scripts.backfill_sales_reservations --lookback 10000 --live
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from common.tenant import DEFAULT_TENANT_ID
from common.time import utc_now


WAREHOUSE_ID = uuid.UUID("e0e9028a-7d6c-5abd-976a-735586cedc34")
REASON_CODE = "SALES_RESERVATION"
ACTOR_ID = "backfill-script"


async def backfill(lookback_days: int = 180, dry_run: bool = True) -> None:
    engine = create_async_engine("postgresql+asyncpg://ultr_erp@localhost:5432/ultr_erp")
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    simulated_today = utc_now().date()
    cutoff = simulated_today - __import__("datetime").timedelta(days=lookback_days)
    print(f"Simulated today : {simulated_today}")
    print(f"Cutoff ({lookback_days}d): {cutoff}")
    print(f"Dry run         : {dry_run}")
    print()

    async with async_session() as s:
        # Fetch demand rows by joining sales header (tbslipx) to sales lines (tbsslipdtx).
        # - Date comes from the header: x.col_3 = invoice_date
        # - Quantity comes from the line: dtx.col_23 = signed qty (+outbound/-return)
        # - Product code comes from the line: dtx.col_7
        result = await s.execute(
            text("""
                SELECT
                    p.id                        AS product_id,
                    CAST(dtx.col_23 AS numeric) AS quantity,
                    x.col_3                      AS txn_date
                FROM raw_legacy.tbsslipx x
                JOIN raw_legacy.tbsslipdtx dtx ON dtx.col_2 = x.col_2
                JOIN public.product p ON p.code = dtx.col_7
                WHERE x.col_3 IS NOT NULL
                  AND x.col_3 <> ''
                  AND x.col_3 >= :cutoff
                  AND x.col_3 <= :today
                  AND dtx.col_23 IS NOT NULL
                  AND dtx.col_23 <> ''
                  AND CAST(dtx.col_23 AS numeric) != 0
                ORDER BY x.col_3
            """),
            {"cutoff": str(cutoff), "today": str(simulated_today)},
        )
        legacy_rows = result.fetchall()
        print(f"Legacy rows found: {len(legacy_rows)}")

        # Group by product_id and date (aggregate multiple line items per order into daily totals)
        daily: dict[tuple[uuid.UUID, date], float] = {}
        for row in legacy_rows:
            d = datetime.strptime(row.txn_date, "%Y-%m-%d").date()
            key = (row.product_id, d)
            daily[key] = daily.get(key, 0) + float(row.quantity)

        print(f"Daily aggregated entries: {len(daily)}")
        print()

        if dry_run:
            print("=== DRY RUN — no rows inserted ===")
            for (product_id, txn_date), qty in list(daily.items())[:10]:
                print(f"  {txn_date}  product_id={product_id}  qty={qty:.4f}")
            if len(daily) > 10:
                print(f"  ... and {len(daily) - 10} more rows")
            print()
            print("Run with dry_run=False to insert.")
            return

        # Insert one row per product_id + date combination
        inserted = 0
        for (product_id, txn_date), qty in daily.items():
            aware_dt = datetime(txn_date.year, txn_date.month, txn_date.day, tzinfo=timezone.utc)
            await s.execute(
                text("""
                    INSERT INTO public.stock_adjustment
                        (id, tenant_id, product_id, warehouse_id, quantity_change,
                         reason_code, actor_id, notes, created_at)
                    VALUES
                        (:id, :tenant_id, :product_id, :warehouse_id, :qty,
                         :reason_code, :actor_id, :notes, :created_at)
                """),
                {
                    "id": str(uuid.uuid4()),
                    "tenant_id": str(DEFAULT_TENANT_ID),
                    "product_id": str(product_id),
                    "warehouse_id": str(WAREHOUSE_ID),
                    "qty": -qty,  # negative = outbound
                    "reason_code": REASON_CODE,
                    "actor_id": ACTOR_ID,
                    "notes": "backfill from raw_legacy.tbslipx+tbsslipdtx",
                    "created_at": aware_dt,
                },
            )
            inserted += 1

        await s.commit()
        print(f"Inserted {inserted} rows into stock_adjustment.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--lookback", type=int, default=180)
    parser.add_argument("--live", action="store_true", help="Disable dry-run (actually insert rows)")
    args = parser.parse_args()

    asyncio.run(backfill(lookback_days=args.lookback, dry_run=not args.live))
