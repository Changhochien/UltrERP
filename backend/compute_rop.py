"""Compute and apply reorder points for all products using demand history."""
import asyncio
import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from common.models.inventory_stock import InventoryStock
from common.models.product import Product
from common.tenant import DEFAULT_TENANT_ID
from domains.inventory.reorder_point import (
    compute_reorder_points_preview,
    apply_reorder_points,
)

ENGINE_URL = "postgresql+asyncpg://ultr_erp@localhost:5432/ultr_erp"


async def main():
    engine = create_async_engine(ENGINE_URL)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with async_session() as s:
        tenant_id = DEFAULT_TENANT_ID

        print("Computing reorder points (demand_lookback=365, safety_factor=0.5)...")
        candidates, skipped = await compute_reorder_points_preview(
            s,
            tenant_id,
            safety_factor=0.5,
            demand_lookback_days=365,
            lead_time_lookback_days=365,
            warehouse_id=None,
        )

        print(f"Candidates (ROP can be computed): {len(candidates)}")
        print(f"Skipped (insufficient history): {len(skipped)}")

        # Show top candidates
        for c in candidates[:10]:
            print(f"  {c['product_name']} (ROP={c['reorder_point']}, "
                  f"avg_daily={c['avg_daily_usage']}, safety_stock={c['safety_stock']})")

        if skipped:
            print(f"\nSkipped (not enough demand history):")
            for sk in skipped[:5]:
                print(f"  {sk.get('product_name', sk['product_id'])}: {sk['skipped_reason']}")

        print(f"\nApplying {len(candidates)} reorder points...")

        # Build row format for apply_reorder_points
        selected = [
            {
                "product_id": c["product_id"],
                "warehouse_id": c["warehouse_id"],
                "reorder_point": c["reorder_point"],
            }
            for c in candidates
        ]

        result = await apply_reorder_points(
            s,
            tenant_id,
            selected,
            safety_factor=0.5,
            demand_lookback_days=365,
            lead_time_lookback_days=365,
        )

        print(f"Applied: {result['updated_count']}, skipped: {result['skipped_count']}")

        # Verify
        verify = await s.execute(
            select(InventoryStock).where(
                InventoryStock.tenant_id == tenant_id,
                InventoryStock.reorder_point > 0,
            ).limit(5)
        )
        rows = verify.scalars().all()
        print(f"\nProducts with reorder_point > 0: {len(rows)}")
        for r in rows:
            print(f"  warehouse={r.warehouse_id}, reorder_point={r.reorder_point}")

    await engine.dispose()


asyncio.run(main())
