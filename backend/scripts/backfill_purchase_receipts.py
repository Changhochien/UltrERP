"""Backfill stock_adjustment records from legacy purchase receipt data.

Imports receiving audit rows from tbsslipj (purchase header) JOIN tbsslipdtj
(purchase lines). The standalone script intentionally mirrors canonical import's
deterministic receiving-adjustment IDs so reruns remain idempotent and safe even
if canonical later imports the same rows.

Usage:
    python -m scripts.backfill_purchase_receipts --lookback 10000 --live
"""

from __future__ import annotations

import asyncio
from datetime import timedelta

from common.database import AsyncSessionLocal
from common.tenant import DEFAULT_TENANT_ID
from common.time import utc_now
from scripts._legacy_stock_adjustments import (
    build_purchase_receipt_adjustments,
    fetch_product_by_code,
    fetch_product_mappings,
    fetch_purchase_receipt_rows,
    fetch_warehouse_by_code,
    upsert_stock_adjustments,
)


async def backfill(lookback_days: int = 180, dry_run: bool = True) -> None:
    simulated_today = utc_now().date()
    cutoff = simulated_today - timedelta(days=lookback_days)
    print(f"Simulated today : {simulated_today}")
    print(f"Cutoff ({lookback_days}d): {cutoff}")
    print(f"Dry run         : {dry_run}")
    print()

    async with AsyncSessionLocal() as session:
        product_mappings = await fetch_product_mappings(
            session,
            tenant_id=DEFAULT_TENANT_ID,
        )
        product_by_code = await fetch_product_by_code(
            session,
            tenant_id=DEFAULT_TENANT_ID,
        )
        warehouse_by_code = await fetch_warehouse_by_code(
            session,
            tenant_id=DEFAULT_TENANT_ID,
        )
        legacy_rows = await fetch_purchase_receipt_rows(
            session,
            cutoff=cutoff,
            today=simulated_today,
        )
        adjustments = build_purchase_receipt_adjustments(
            rows=legacy_rows,
            tenant_id=DEFAULT_TENANT_ID,
            product_by_code=product_by_code,
            warehouse_by_code=warehouse_by_code,
            product_mappings=product_mappings,
            fallback_day=simulated_today,
        )

        print(f"Legacy rows found: {len(legacy_rows)}")
        print(f"Receipt adjustments: {len(adjustments)}")
        print()

        if dry_run:
            print("=== DRY RUN — no rows inserted ===")
            for adjustment in adjustments[:10]:
                print(
                    "  "
                    f"{adjustment.created_at.date()} "
                    f"product_id={adjustment.product_id} "
                    f"warehouse_id={adjustment.warehouse_id} "
                    f"quantity_change={adjustment.quantity_change} "
                    f"notes={adjustment.notes}"
                )
            if len(adjustments) > 10:
                print(f"  ... and {len(adjustments) - 10} more rows")
            print()
            print("Run with dry_run=False to insert.")
            return

        upserted_row_count = await upsert_stock_adjustments(session, adjustments)

        await session.commit()
        print(f"Upserted {upserted_row_count} rows into stock_adjustment.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--lookback", type=int, default=180)
    parser.add_argument(
        "--live",
        action="store_true",
        help="Disable dry-run (actually insert rows)",
    )
    args = parser.parse_args()

    asyncio.run(backfill(lookback_days=args.lookback, dry_run=not args.live))