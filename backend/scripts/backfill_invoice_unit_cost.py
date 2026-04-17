"""Backfill historical invoice line unit_cost values from purchase history.

This command is intentionally conservative:
- only rows with invoice_lines.unit_cost IS NULL are candidates
- only purchase records on or before the invoice date are eligible
- same-day ties still prefer supplier invoices over supplier orders
- if the top-ranked historical candidates disagree on price, the row is skipped

Usage:
    cd backend && uv run python -m scripts.backfill_invoice_unit_cost
    cd backend && uv run python -m scripts.backfill_invoice_unit_cost --live
"""

from __future__ import annotations

import argparse
import asyncio

from common.database import AsyncSessionLocal
from common.tenant import DEFAULT_TENANT_ID
from domains.invoices.service import (
    InvoiceUnitCostBackfillPreview,
    backfill_missing_invoice_line_unit_costs,
)


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be a positive integer")
    return parsed


def _preview_message(preview: InvoiceUnitCostBackfillPreview) -> str:
    base = f"{preview.invoice_date} {preview.invoice_number} line={preview.line_number}"
    if preview.status == "updated":
        return f"{base} -> unit_cost={preview.unit_cost}"
    return f"{base} -> {preview.status}"


async def backfill(
    *,
    dry_run: bool = True,
    batch_size: int = 1000,
    max_candidates: int | None = None,
) -> None:
    async with AsyncSessionLocal() as session:
        try:
            summary = await backfill_missing_invoice_line_unit_costs(
                session,
                tenant_id=DEFAULT_TENANT_ID,
                dry_run=dry_run,
                batch_size=batch_size,
                max_candidates=max_candidates,
                commit_per_batch=not dry_run,
            )

            print(f"Dry run         : {dry_run}")
            print(f"Batch size      : {batch_size}")
            if max_candidates is not None:
                print(f"Candidate limit : {max_candidates}")
            print(f"Candidates      : {summary.candidate_count}")
            label = "Would update" if dry_run else "Updated"
            print(f"{label:<16}: {summary.updated_count}")
            print(f"Skipped         : {summary.skipped_count}")
            print(f"Unmatched       : {summary.unmatched_count}")
            print(f"Ambiguous       : {summary.ambiguous_count}")
            print()

            if summary.previews:
                print("Sample decisions:")
                for preview in summary.previews:
                    print(f"  {_preview_message(preview)}")
                if summary.candidate_count > len(summary.previews):
                    remaining = summary.candidate_count - len(summary.previews)
                    print(f"  ... and {remaining} more candidate rows")
            else:
                print("No candidate invoice lines found.")

            if dry_run:
                return

            await session.commit()
        except Exception:
            await session.rollback()
            raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--batch-size",
        type=_positive_int,
        default=1000,
        help="Number of candidate invoice lines to resolve per query batch.",
    )
    parser.add_argument(
        "--limit",
        type=_positive_int,
        default=None,
        help="Optional cap on how many candidate invoice lines to inspect in this run.",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Apply updates instead of running in dry-run mode.",
    )
    args = parser.parse_args()
    asyncio.run(
        backfill(
            dry_run=not args.live,
            batch_size=args.batch_size,
            max_candidates=args.limit,
        )
    )


if __name__ == "__main__":
    main()