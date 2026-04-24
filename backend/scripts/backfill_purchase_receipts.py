"""Backfill stock_adjustment records from legacy purchase receipt data.

Imports receiving audit rows from tbsslipj (purchase header) JOIN tbsslipdtj
(purchase lines). The standalone script intentionally mirrors canonical import's
deterministic receiving-adjustment IDs so reruns remain idempotent and safe even
if canonical later imports the same rows.

Story 15.27: Supports target-aware incremental refresh when entity_scope is provided.
For full rebaseline runs, uses the full lookback window. For incremental runs,
uses the scoped closure keys to narrow the backfill to affected entities (AC2).

Usage:
    python -m scripts.backfill_purchase_receipts --lookback 10000 --live
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Sequence
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


async def backfill(
    lookback_days: int = 180,
    dry_run: bool = True,
    tenant_id: uuid.UUID = DEFAULT_TENANT_ID,
    # Story 15.27: Target-aware incremental scope parameters (AC2).
    entity_scope: dict[str, dict[str, object]] | None = None,
    affected_domains: Sequence[str] | None = None,
) -> dict[str, object]:
    """Backfill purchase receipts with target-aware incremental support.

    Returns a summary dict with backfill statistics.
    """
    simulated_today = utc_now().date()
    cutoff = simulated_today - timedelta(days=lookback_days)
    print(f"Simulated today : {simulated_today}")
    print(f"Cutoff ({lookback_days}d): {cutoff}")
    print(f"Dry run         : {dry_run}")

    # Story 15.27: Determine if this is an incremental run (AC2).
    is_incremental = entity_scope is not None or affected_domains is not None
    scoped_domains = list(affected_domains) if affected_domains else []
    scope_closure_keys: dict[str, list[str]] = {}
    if entity_scope:
        for domain, scope_data in entity_scope.items():
            closure_keys = scope_data.get("closure_keys")
            if closure_keys and isinstance(closure_keys, list):
                scope_closure_keys[domain] = closure_keys
    print(f"Batch mode      : {'incremental' if is_incremental else 'full'}")
    if is_incremental:
        print(f"Affected domains: {', '.join(scoped_domains) if scoped_domains else 'none'}")
        print(f"Scoped entities : {sum(len(v) for v in scope_closure_keys.values())}")
    print()

    result: dict[str, object] = {
        "lookback_days": lookback_days,
        "dry_run": dry_run,
        "batch_mode": "incremental" if is_incremental else "full",
        "affected_domains": scoped_domains,
        "scoped_entity_count": sum(len(v) for v in scope_closure_keys.values()),
    }

    async with AsyncSessionLocal() as session:
        product_mappings = await fetch_product_mappings(
            session,
            tenant_id=tenant_id,
        )
        product_by_code = await fetch_product_by_code(
            session,
            tenant_id=tenant_id,
        )
        warehouse_by_code = await fetch_warehouse_by_code(
            session,
            tenant_id=tenant_id,
        )
        legacy_rows = await fetch_purchase_receipt_rows(
            session,
            cutoff=cutoff,
            today=simulated_today,
            # Story 15.27: Pass scope for incremental filtering (AC2).
            entity_scope=entity_scope,
            affected_domains=affected_domains,
        )
        adjustments = build_purchase_receipt_adjustments(
            rows=legacy_rows,
            tenant_id=tenant_id,
            product_by_code=product_by_code,
            warehouse_by_code=warehouse_by_code,
            product_mappings=product_mappings,
            fallback_day=simulated_today,
        )

        print(f"Legacy rows found: {len(legacy_rows)}")
        print(f"Receipt adjustments: {len(adjustments)}")
        result["legacy_rows_found"] = len(legacy_rows)
        result["adjustments_count"] = len(adjustments)
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
        result["upserted_count"] = upserted_row_count

    return result


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