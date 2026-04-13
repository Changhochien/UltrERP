"""Apply an approved subset of reconciliation correction proposals from CSV."""

from __future__ import annotations

import argparse
import asyncio
import csv
import uuid
from datetime import UTC, date, datetime
from pathlib import Path

from common.database import AsyncSessionLocal
from common.models.stock_adjustment import ReasonCode
from common.tenant import DEFAULT_TENANT_ID
from scripts._legacy_stock_adjustments import (
    StockAdjustmentPayload,
    tenant_scoped_uuid,
    upsert_stock_adjustments,
)

REQUIRED_COLUMNS = {
    "disposition",
    "approval_action",
    "product_id",
    "warehouse_id",
    "gap",
    "expected_adjustment_sum",
    "actual_stock",
    "proposed_quantity_change",
    "correction_id",
    "reason_breakdown",
    "as_of_day",
}


def load_correction_candidates(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing:
            missing_text = ", ".join(sorted(missing))
            raise ValueError(
                "Correction CSV is missing required columns: "
                f"{missing_text}. Regenerate it with the latest "
                "propose_reconciliation_corrections.py exporter."
            )
        return [dict(row) for row in reader]


def select_approved_candidates(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    approved: list[dict[str, str]] = []
    for row in rows:
        action = (row.get("approval_action") or "").strip().lower()
        if not action:
            continue
        if action != "apply":
            product_label = row.get("product_code") or row.get("product_id")
            raise ValueError(
                f"Unsupported approval_action {action!r} for product {product_label}"
            )
        if (row.get("disposition") or "").strip() != "actionable":
            product_label = row.get("product_code") or row.get("product_id")
            raise ValueError(
                f"Row {product_label} is {row.get('disposition')!r} and cannot be auto-applied"
            )
        approved.append(row)
    return approved


def build_approved_corrections(
    rows: list[dict[str, str]],
    *,
    tenant_id: uuid.UUID,
    approved_by: str,
) -> list[StockAdjustmentPayload]:
    payloads: list[StockAdjustmentPayload] = []
    for row in rows:
        product_id = uuid.UUID(row["product_id"])
        warehouse_id = uuid.UUID(row["warehouse_id"])
        as_of_day = date.fromisoformat(row["as_of_day"])
        expected_id = tenant_scoped_uuid(
            tenant_id,
            "inventory-reconciliation-correction",
            str(product_id),
            str(warehouse_id),
            as_of_day.isoformat(),
        )
        supplied_id = uuid.UUID(row["correction_id"])
        if supplied_id != expected_id:
            product_label = row.get("product_code") or str(product_id)
            raise ValueError(
                "Correction id mismatch for product "
                f"{product_label}: {supplied_id} != {expected_id}"
            )

        payloads.append(
            StockAdjustmentPayload(
                id=expected_id,
                tenant_id=tenant_id,
                product_id=product_id,
                warehouse_id=warehouse_id,
                quantity_change=int(row["proposed_quantity_change"]),
                reason_code=ReasonCode.CORRECTION.value,
                actor_id="reconciliation-apply",
                notes=(
                    f"Approved inventory reconciliation correction by {approved_by} "
                    f"as of {as_of_day.isoformat()} "
                    f"(gap={row['gap']}; expected_adjustment_sum={row['expected_adjustment_sum']}; "
                    f"actual_stock={row['actual_stock']}; reasons={row['reason_breakdown']})"
                ),
                created_at=datetime(
                    as_of_day.year,
                    as_of_day.month,
                    as_of_day.day,
                    tzinfo=UTC,
                ),
            )
        )
    return payloads


async def apply_corrections(
    *,
    csv_path: str,
    approved_by: str,
    tenant_id: uuid.UUID = DEFAULT_TENANT_ID,
    dry_run: bool = True,
) -> None:
    candidates = load_correction_candidates(Path(csv_path))
    approved_rows = select_approved_candidates(candidates)
    payloads = build_approved_corrections(
        approved_rows,
        tenant_id=tenant_id,
        approved_by=approved_by,
    )

    print(f"CSV rows            : {len(candidates)}")
    print(f"Approved rows       : {len(approved_rows)}")
    print(f"Dry run             : {dry_run}")

    for payload in payloads[:20]:
        print(
            "- "
            f"product={payload.product_id} warehouse={payload.warehouse_id} "
            f"quantity_change={payload.quantity_change} id={payload.id}"
        )

    if dry_run or not payloads:
        return

    async with AsyncSessionLocal() as session:
        await upsert_stock_adjustments(session, payloads)
        await session.commit()
    print(f"Applied {len(payloads)} correction rows.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Apply an approved subset of reconciliation correction proposals from CSV."
    )
    parser.add_argument(
        "--csv",
        required=True,
        help="Proposal CSV generated by propose_reconciliation_corrections.py",
    )
    parser.add_argument(
        "--approved-by",
        required=True,
        help="Operator identity recorded in correction notes",
    )
    parser.add_argument(
        "--tenant-id",
        default=str(DEFAULT_TENANT_ID),
        help="Tenant UUID to apply corrections for (defaults to DEFAULT_TENANT_ID).",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Persist approved corrections. Dry-run is the default.",
    )
    args = parser.parse_args()

    asyncio.run(
        apply_corrections(
            csv_path=args.csv,
            approved_by=args.approved_by,
            tenant_id=uuid.UUID(args.tenant_id),
            dry_run=not args.live,
        )
    )


if __name__ == "__main__":
    main()