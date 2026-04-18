"""Report inventory reconciliation gaps between stock adjustments and current stock.

This script is intentionally read-only. It compares the net quantity from
stock_adjustment against the current inventory_stock snapshot and flags any
non-zero gaps for operator review.
"""

from __future__ import annotations

import asyncio
import uuid

from common.database import AsyncSessionLocal
from common.tenant import DEFAULT_TENANT_ID
from scripts._legacy_stock_adjustments import (
    build_reconciliation_rows,
    fetch_reconciliation_adjustment_rows,
    fetch_reconciliation_inventory_rows,
    format_reconciliation_table,
)


async def verify(tenant_id: uuid.UUID = DEFAULT_TENANT_ID) -> int:
    async with AsyncSessionLocal() as session:
        adjustment_rows = await fetch_reconciliation_adjustment_rows(
            session,
            tenant_id=tenant_id,
        )
        inventory_rows = await fetch_reconciliation_inventory_rows(
            session,
            tenant_id=tenant_id,
        )

    rows = build_reconciliation_rows(
        adjustment_rows=adjustment_rows,
        inventory_rows=inventory_rows,
    )
    flagged_rows = [row for row in rows if row.gap != 0]

    print(f"Adjustment groups : {len(adjustment_rows)}")
    print(f"Inventory groups  : {len(inventory_rows)}")
    print(f"Flagged gaps      : {len(flagged_rows)}")
    print()

    if not flagged_rows:
        print("No reconciliation gaps found.")
        return 0

    print(format_reconciliation_table(flagged_rows))
    return len(flagged_rows)


if __name__ == "__main__":
    asyncio.run(verify())