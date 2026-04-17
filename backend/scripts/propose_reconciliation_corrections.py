"""Generate correction proposals from inventory reconciliation gaps."""

from __future__ import annotations

import argparse
import asyncio
import csv
import uuid
from datetime import date
from pathlib import Path

from sqlalchemy import text

from common.database import AsyncSessionLocal
from common.tenant import DEFAULT_TENANT_ID
from common.time import utc_now
from scripts._legacy_stock_adjustments import (
    build_correction_adjustments,
    build_reconciliation_rows,
    fetch_reconciliation_adjustment_rows,
    fetch_reconciliation_inventory_rows,
)

DEFAULT_REVIEW_ONLY_CATEGORIES = ("6",)


def classify_candidate(
    *,
    product_code: str,
    product_name: str,
    category: str | None,
    review_only_categories: set[str],
) -> tuple[str, str | None]:
    normalized_category = (category or "").strip()
    if normalized_category and normalized_category in review_only_categories:
        return (
            "review_only",
            f"category {normalized_category} is configured as non-merchandise review-only",
        )
    return "actionable", None


async def _fetch_product_metadata(
    *,
    tenant_id: uuid.UUID,
) -> dict[uuid.UUID, dict[str, str | None]]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                """
                SELECT id, code, name, category
                FROM product
                WHERE tenant_id = :tenant_id
                """
            ),
            {"tenant_id": str(tenant_id)},
        )
    return {
        row.id: {
            "product_code": row.code,
            "product_name": row.name,
            "category": row.category,
        }
        for row in result.all()
    }


def _reason_breakdown_text(reason_breakdown: dict[str, int]) -> str:
    return ", ".join(
        f"{reason}={total}" for reason, total in sorted(reason_breakdown.items())
    ) or "-"


def _write_csv(
    path: Path,
    *,
    candidate_rows,
    corrections_by_key,
    as_of_day: date,
) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "product_code",
                "product_name",
                "category",
                "disposition",
                "review_reason",
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
            ],
        )
        writer.writeheader()
        for candidate in candidate_rows:
            row = candidate["row"]
            correction = corrections_by_key.get((row.product_id, row.warehouse_id))
            writer.writerow(
                {
                    "product_code": candidate["product_code"],
                    "product_name": candidate["product_name"],
                    "category": candidate["category"] or "",
                    "disposition": candidate["disposition"],
                    "review_reason": candidate["review_reason"] or "",
                    "approval_action": "",
                    "product_id": row.product_id,
                    "warehouse_id": row.warehouse_id,
                    "gap": row.gap,
                    "expected_adjustment_sum": row.expected_adjustment_sum,
                    "actual_stock": row.actual_stock,
                    "proposed_quantity_change": correction.quantity_change if correction else "",
                    "correction_id": correction.id if correction else "",
                    "reason_breakdown": _reason_breakdown_text(row.reason_breakdown),
                    "as_of_day": as_of_day.isoformat(),
                }
            )


async def propose_corrections(
    *,
    tenant_id: uuid.UUID = DEFAULT_TENANT_ID,
    min_abs_gap: int = 1,
    limit: int = 25,
    csv_path: str | None = None,
    as_of_day: date | None = None,
    review_only_categories: set[str] | None = None,
) -> None:
    resolved_day = as_of_day or utc_now().date()
    resolved_review_only_categories = review_only_categories or set(DEFAULT_REVIEW_ONLY_CATEGORIES)

    async with AsyncSessionLocal() as session:
        adjustment_rows = await fetch_reconciliation_adjustment_rows(
            session,
            tenant_id=tenant_id,
        )
        inventory_rows = await fetch_reconciliation_inventory_rows(
            session,
            tenant_id=tenant_id,
        )

    reconciliation_rows = build_reconciliation_rows(
        adjustment_rows=adjustment_rows,
        inventory_rows=inventory_rows,
    )
    proposed_rows = [
        row for row in reconciliation_rows if row.gap != 0 and abs(row.gap) >= min_abs_gap
    ]
    proposed_rows.sort(key=lambda row: (-abs(row.gap), str(row.product_id), str(row.warehouse_id)))
    metadata_by_product_id = await _fetch_product_metadata(tenant_id=tenant_id)

    candidate_rows = []
    actionable_rows = []
    review_only_rows = []
    for row in proposed_rows:
        metadata = metadata_by_product_id.get(
            row.product_id,
            {"product_code": "", "product_name": "", "category": None},
        )
        disposition, review_reason = classify_candidate(
            product_code=metadata["product_code"] or "",
            product_name=metadata["product_name"] or "",
            category=metadata["category"],
            review_only_categories=resolved_review_only_categories,
        )
        candidate = {
            "row": row,
            "product_code": metadata["product_code"] or "",
            "product_name": metadata["product_name"] or "",
            "category": metadata["category"],
            "disposition": disposition,
            "review_reason": review_reason,
        }
        candidate_rows.append(candidate)
        if disposition == "actionable":
            actionable_rows.append(candidate)
        else:
            review_only_rows.append(candidate)

    corrections = build_correction_adjustments(
        [candidate["row"] for candidate in actionable_rows],
        tenant_id=tenant_id,
        as_of_day=resolved_day,
        min_abs_gap=min_abs_gap,
    )
    corrections_by_key = {
        (correction.product_id, correction.warehouse_id): correction for correction in corrections
    }

    print(f"As of day          : {resolved_day.isoformat()}")
    print(f"Minimum abs gap    : {min_abs_gap}")
    print(f"Total gap rows     : {sum(1 for row in reconciliation_rows if row.gap != 0)}")
    print(f"Actionable rows    : {len(actionable_rows)}")
    print(f"Review-only rows   : {len(review_only_rows)}")
    print(f"Review-only cats   : {', '.join(sorted(resolved_review_only_categories)) or '-'}")
    print()

    for candidate in actionable_rows[:limit]:
        row = candidate["row"]
        correction = corrections_by_key[(row.product_id, row.warehouse_id)]
        print(
            "- "
            f"product={candidate['product_code'] or row.product_id} "
            f"warehouse={row.warehouse_id} gap={row.gap} "
            f"proposed_quantity_change={correction.quantity_change} "
            f"reasons={_reason_breakdown_text(row.reason_breakdown)}"
        )

    if review_only_rows:
        print()
        print("Review-only rows")
        for candidate in review_only_rows[:limit]:
            row = candidate["row"]
            print(
                "- "
                f"product={candidate['product_code'] or row.product_id} "
                f"warehouse={row.warehouse_id} gap={row.gap} "
                f"reason={candidate['review_reason']}"
            )

    if csv_path and candidate_rows:
        output_path = Path(csv_path)
        _write_csv(
            output_path,
            candidate_rows=candidate_rows,
            corrections_by_key=corrections_by_key,
            as_of_day=resolved_day,
        )
        print()
        print(f"Wrote CSV plan to  : {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate deterministic CORRECTION proposals from reconciliation gaps."
    )
    parser.add_argument(
        "--tenant-id",
        default=str(DEFAULT_TENANT_ID),
        help="Tenant UUID to analyze (defaults to DEFAULT_TENANT_ID).",
    )
    parser.add_argument(
        "--min-abs-gap",
        type=int,
        default=1,
        help="Only include rows whose absolute reconciliation gap is at least this value.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=25,
        help="Maximum number of proposal rows to print to stdout.",
    )
    parser.add_argument(
        "--csv",
        help="Optional CSV path for the full correction proposal set.",
    )
    parser.add_argument(
        "--as-of-day",
        help="ISO date used in deterministic correction IDs and proposal notes.",
    )
    parser.add_argument(
        "--review-only-category",
        action="append",
        default=list(DEFAULT_REVIEW_ONLY_CATEGORIES),
        help=(
            "Product category code to treat as review-only rather than actionable. "
            "Repeatable; defaults to category 6."
        ),
    )
    args = parser.parse_args()

    asyncio.run(
        propose_corrections(
            tenant_id=uuid.UUID(args.tenant_id),
            min_abs_gap=args.min_abs_gap,
            limit=args.limit,
            csv_path=args.csv,
            as_of_day=date.fromisoformat(args.as_of_day) if args.as_of_day else None,
            review_only_categories={value.strip() for value in args.review_only_category if value},
        )
    )


if __name__ == "__main__":
    main()