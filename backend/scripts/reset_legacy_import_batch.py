"""Batch-scoped reset helper for legacy import rehearsals."""

from __future__ import annotations

import argparse
import asyncio
import uuid
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from common.database import AsyncSessionLocal
from common.tenant import DEFAULT_TENANT_ID

DEFAULT_SCHEMA_NAME = "raw_legacy"
LINEAGED_DELETE_ORDER = (
    "invoice_lines",
    "order_lines",
    "supplier_invoice_lines",
    "stock_adjustment",
    "invoices",
    "orders",
    "supplier_invoices",
    "inventory_stock",
    "customers",
    "supplier",
    "product",
    "warehouse",
)
EXTRA_SLICES = {
    "sales_backfill": {
        "actor_id": "backfill-script",
        "reason_code": "SALES_RESERVATION",
        "description": "tenant-scoped sales backfill rows (not batch-scoped)",
    },
}


@dataclass(frozen=True, slots=True)
class ResetPlanItem:
    label: str
    count: int
    description: str
    batch_scoped: bool


def build_reset_plan(
    *,
    lineage_counts: dict[str, int],
    resolution_state_count: int,
    resolution_event_count: int,
    holding_count: int,
    lineage_count: int,
    step_run_count: int,
    run_count: int,
    extra_counts: dict[str, int],
    include_sales_backfill: bool,
) -> list[ResetPlanItem]:
    items: list[ResetPlanItem] = []

    for table_name in LINEAGED_DELETE_ORDER:
        count = lineage_counts.get(table_name, 0)
        if count:
            items.append(
                ResetPlanItem(
                    label=table_name,
                    count=count,
                    description=f"lineaged canonical rows from {table_name}",
                    batch_scoped=True,
                )
            )

        if table_name == "stock_adjustment":
            if include_sales_backfill and extra_counts.get("sales_backfill", 0):
                items.append(
                    ResetPlanItem(
                        label="sales_backfill",
                        count=extra_counts["sales_backfill"],
                        description=EXTRA_SLICES["sales_backfill"]["description"],
                        batch_scoped=False,
                    )
                )

    control_items = [
        (
            "source_row_resolution_events",
            resolution_event_count,
            "batch-scoped source-resolution event rows",
        ),
        (
            "source_row_resolution",
            resolution_state_count,
            "batch-scoped source-resolution state rows",
        ),
        ("unsupported_history_holding", holding_count, "batch-scoped unsupported-history rows"),
        ("canonical_record_lineage", lineage_count, "batch-scoped lineage rows"),
        ("canonical_import_step_runs", step_run_count, "batch-scoped step-run rows"),
        ("canonical_import_runs", run_count, "batch-scoped import-run rows"),
    ]
    for label, count, description in control_items:
        if count:
            items.append(
                ResetPlanItem(
                    label=label,
                    count=count,
                    description=description,
                    batch_scoped=True,
                )
            )

    return items


async def _fetch_lineage_counts(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    batch_id: str,
    schema_name: str,
) -> dict[str, int]:
    result = await session.execute(
        text(
            f"""
            SELECT canonical_table, COUNT(*) AS row_count
            FROM {schema_name}.canonical_record_lineage
            WHERE tenant_id = :tenant_id AND batch_id = :batch_id
            GROUP BY canonical_table
            ORDER BY canonical_table
            """
        ),
        {"tenant_id": str(tenant_id), "batch_id": batch_id},
    )
    return {str(row.canonical_table): int(row.row_count) for row in result.all()}


async def _fetch_control_counts(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    batch_id: str,
    schema_name: str,
) -> tuple[int, int, int, int, int, int]:
    resolution_event_result = await session.execute(
        text(
            f"""
            SELECT COUNT(*)
            FROM {schema_name}.source_row_resolution_events
            WHERE tenant_id = :tenant_id AND batch_id = :batch_id
            """
        ),
        {"tenant_id": str(tenant_id), "batch_id": batch_id},
    )
    resolution_state_result = await session.execute(
        text(
            f"""
            SELECT COUNT(*)
            FROM {schema_name}.source_row_resolution
            WHERE tenant_id = :tenant_id AND batch_id = :batch_id
            """
        ),
        {"tenant_id": str(tenant_id), "batch_id": batch_id},
    )
    holding_result = await session.execute(
        text(
            f"""
            SELECT COUNT(*)
            FROM {schema_name}.unsupported_history_holding
            WHERE tenant_id = :tenant_id AND batch_id = :batch_id
            """
        ),
        {"tenant_id": str(tenant_id), "batch_id": batch_id},
    )
    lineage_result = await session.execute(
        text(
            f"""
            SELECT COUNT(*)
            FROM {schema_name}.canonical_record_lineage
            WHERE tenant_id = :tenant_id AND batch_id = :batch_id
            """
        ),
        {"tenant_id": str(tenant_id), "batch_id": batch_id},
    )
    step_run_result = await session.execute(
        text(
            f"""
            SELECT COUNT(*)
            FROM {schema_name}.canonical_import_step_runs
            WHERE run_id IN (
                SELECT id
                FROM {schema_name}.canonical_import_runs
                WHERE tenant_id = :tenant_id AND batch_id = :batch_id
            )
            """
        ),
        {"tenant_id": str(tenant_id), "batch_id": batch_id},
    )
    run_result = await session.execute(
        text(
            f"""
            SELECT COUNT(*)
            FROM {schema_name}.canonical_import_runs
            WHERE tenant_id = :tenant_id AND batch_id = :batch_id
            """
        ),
        {"tenant_id": str(tenant_id), "batch_id": batch_id},
    )
    return (
        int(resolution_state_result.scalar_one()),
        int(resolution_event_result.scalar_one()),
        int(holding_result.scalar_one()),
        int(lineage_result.scalar_one()),
        int(step_run_result.scalar_one()),
        int(run_result.scalar_one()),
    )


async def _fetch_extra_counts(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for label, config in EXTRA_SLICES.items():
        result = await session.execute(
            text(
                """
                SELECT COUNT(*)
                FROM stock_adjustment
                WHERE tenant_id = :tenant_id
                  AND actor_id = :actor_id
                  AND reason_code = :reason_code
                """
            ),
            {
                "tenant_id": str(tenant_id),
                "actor_id": config["actor_id"],
                "reason_code": config["reason_code"],
            },
        )
        counts[label] = int(result.scalar_one())
    return counts


async def _delete_lineaged_table(
    session: AsyncSession,
    *,
    table_name: str,
    tenant_id: uuid.UUID,
    batch_id: str,
    schema_name: str,
) -> int:
    result = await session.execute(
        text(
            f"""
            DELETE FROM {table_name}
            WHERE id IN (
                SELECT canonical_id
                FROM {schema_name}.canonical_record_lineage
                WHERE tenant_id = :tenant_id
                  AND batch_id = :batch_id
                  AND canonical_table = :canonical_table
            )
            """
        ),
        {
            "tenant_id": str(tenant_id),
            "batch_id": batch_id,
            "canonical_table": table_name,
        },
    )
    return result.rowcount or 0


async def _delete_extra_slice(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    label: str,
) -> int:
    config = EXTRA_SLICES[label]
    result = await session.execute(
        text(
            """
            DELETE FROM stock_adjustment
            WHERE tenant_id = :tenant_id
              AND actor_id = :actor_id
              AND reason_code = :reason_code
            """
        ),
        {
            "tenant_id": str(tenant_id),
            "actor_id": config["actor_id"],
            "reason_code": config["reason_code"],
        },
    )
    return result.rowcount or 0


async def reset_legacy_import_batch(
    *,
    batch_id: str,
    tenant_id: uuid.UUID = DEFAULT_TENANT_ID,
    schema_name: str = DEFAULT_SCHEMA_NAME,
    include_sales_backfill: bool = False,
    dry_run: bool = True,
) -> None:
    async with AsyncSessionLocal() as session:
        lineage_counts = await _fetch_lineage_counts(
            session,
            tenant_id=tenant_id,
            batch_id=batch_id,
            schema_name=schema_name,
        )
        (
            resolution_state_count,
            resolution_event_count,
            holding_count,
            lineage_count,
            step_run_count,
            run_count,
        ) = await _fetch_control_counts(
            session,
            tenant_id=tenant_id,
            batch_id=batch_id,
            schema_name=schema_name,
        )
        extra_counts = await _fetch_extra_counts(session, tenant_id=tenant_id)
        plan = build_reset_plan(
            lineage_counts=lineage_counts,
            resolution_state_count=resolution_state_count,
            resolution_event_count=resolution_event_count,
            holding_count=holding_count,
            lineage_count=lineage_count,
            step_run_count=step_run_count,
            run_count=run_count,
            extra_counts=extra_counts,
            include_sales_backfill=include_sales_backfill,
        )

        print(f"Batch ID                : {batch_id}")
        print(f"Schema                  : {schema_name}")
        print(f"Tenant ID               : {tenant_id}")
        print(f"Dry run                 : {dry_run}")
        print(f"Include sales backfill  : {include_sales_backfill}")
        print()

        if not plan:
            print("Nothing to reset for the selected batch and options.")
            await session.rollback()
            return

        for item in plan:
            scope = "batch" if item.batch_scoped else "tenant"
            print(f"- {item.label}: {item.count} rows [{scope}] — {item.description}")

        if dry_run:
            await session.rollback()
            return

        for table_name in LINEAGED_DELETE_ORDER:
            if lineage_counts.get(table_name, 0):
                deleted = await _delete_lineaged_table(
                    session,
                    table_name=table_name,
                    tenant_id=tenant_id,
                    batch_id=batch_id,
                    schema_name=schema_name,
                )
                print(f"Deleted {deleted} rows from {table_name}.")

            if table_name == "stock_adjustment":
                if include_sales_backfill and extra_counts.get("sales_backfill", 0):
                    deleted = await _delete_extra_slice(
                        session,
                        tenant_id=tenant_id,
                        label="sales_backfill",
                    )
                    print(f"Deleted {deleted} sales backfill rows.")

        if resolution_event_count:
            deleted = await session.execute(
                text(
                    f"""
                    DELETE FROM {schema_name}.source_row_resolution_events
                    WHERE tenant_id = :tenant_id AND batch_id = :batch_id
                    """
                ),
                {"tenant_id": str(tenant_id), "batch_id": batch_id},
            )
            print(f"Deleted {deleted.rowcount or 0} source_row_resolution_events rows.")

        if resolution_state_count:
            deleted = await session.execute(
                text(
                    f"""
                    DELETE FROM {schema_name}.source_row_resolution
                    WHERE tenant_id = :tenant_id AND batch_id = :batch_id
                    """
                ),
                {"tenant_id": str(tenant_id), "batch_id": batch_id},
            )
            print(f"Deleted {deleted.rowcount or 0} source_row_resolution rows.")

        if holding_count:
            deleted = await session.execute(
                text(
                    f"""
                    DELETE FROM {schema_name}.unsupported_history_holding
                    WHERE tenant_id = :tenant_id AND batch_id = :batch_id
                    """
                ),
                {"tenant_id": str(tenant_id), "batch_id": batch_id},
            )
            print(f"Deleted {deleted.rowcount or 0} unsupported_history_holding rows.")

        if lineage_count:
            deleted = await session.execute(
                text(
                    f"""
                    DELETE FROM {schema_name}.canonical_record_lineage
                    WHERE tenant_id = :tenant_id AND batch_id = :batch_id
                    """
                ),
                {"tenant_id": str(tenant_id), "batch_id": batch_id},
            )
            print(f"Deleted {deleted.rowcount or 0} canonical_record_lineage rows.")

        if step_run_count:
            deleted = await session.execute(
                text(
                    f"""
                    DELETE FROM {schema_name}.canonical_import_step_runs
                    WHERE run_id IN (
                        SELECT id
                        FROM {schema_name}.canonical_import_runs
                        WHERE tenant_id = :tenant_id AND batch_id = :batch_id
                    )
                    """
                ),
                {"tenant_id": str(tenant_id), "batch_id": batch_id},
            )
            print(f"Deleted {deleted.rowcount or 0} canonical_import_step_runs rows.")

        if run_count:
            deleted = await session.execute(
                text(
                    f"""
                    DELETE FROM {schema_name}.canonical_import_runs
                    WHERE tenant_id = :tenant_id AND batch_id = :batch_id
                    """
                ),
                {"tenant_id": str(tenant_id), "batch_id": batch_id},
            )
            print(f"Deleted {deleted.rowcount or 0} canonical_import_runs rows.")

        await session.commit()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Batch-scoped reset helper for legacy import rehearsals. Dry-run by default."
    )
    parser.add_argument("--batch-id", required=True, help="Legacy batch id to reset.")
    parser.add_argument(
        "--tenant-id",
        default=str(DEFAULT_TENANT_ID),
        help="Tenant UUID to reset (defaults to DEFAULT_TENANT_ID).",
    )
    parser.add_argument(
        "--schema-name",
        default=DEFAULT_SCHEMA_NAME,
        help="Schema that stores canonical lineage and import control tables.",
    )
    parser.add_argument(
        "--include-sales-backfill",
        action="store_true",
        help="Also delete tenant-scoped sales backfill rows created by Story 18.2.",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Persist the reset. Dry-run is the default.",
    )
    args = parser.parse_args()

    asyncio.run(
        reset_legacy_import_batch(
            batch_id=args.batch_id,
            tenant_id=uuid.UUID(args.tenant_id),
            schema_name=args.schema_name,
            include_sales_backfill=args.include_sales_backfill,
            dry_run=not args.live,
        )
    )


if __name__ == "__main__":
    main()