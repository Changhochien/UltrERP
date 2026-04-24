"""Refresh closed historical sales_monthly aggregates for a tenant."""

from __future__ import annotations

import argparse
import asyncio
import json
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Sequence

from sqlalchemy import delete, func, select

from common.cli_args import parse_tenant_uuid
from common.database import AsyncSessionLocal
from common.models.order import Order
from common.order_reporting import commercially_committed_timestamp_expr
from common.tenant import DEFAULT_TENANT_ID
from domains.legacy_import.shared import DOMAIN_SALES
from domains.product_analytics.models import SalesMonthly
from domains.product_analytics.service import normalize_month_start, refresh_sales_monthly_range
from scripts.legacy_refresh_common import RefreshBatchMode


@dataclass(slots=True, frozen=True)
class SalesMonthlyHistoryRefreshResult:
    batch_mode: str
    affected_domains: tuple[str, ...]
    start_month: date | None
    end_month: date | None
    refreshed_month_count: int
    total_upserted_row_count: int
    total_deleted_row_count: int
    skipped_line_count: int
    cleared_row_count: int
    skipped_reason: str | None = None


def _normalize_batch_mode(batch_mode: str | RefreshBatchMode | None) -> RefreshBatchMode:
    if batch_mode is None:
        return RefreshBatchMode.FULL
    if isinstance(batch_mode, RefreshBatchMode):
        return batch_mode
    return RefreshBatchMode(batch_mode.lower())


def _current_month_start() -> date:
    return datetime.now(tz=UTC).date().replace(day=1)


def _previous_month_start(current_month_start: date) -> date:
    return (current_month_start - timedelta(days=1)).replace(day=1)


async def _fetch_earliest_order_timestamp(tenant_id: uuid.UUID) -> datetime | None:
    analytics_timestamp = commercially_committed_timestamp_expr()
    async with AsyncSessionLocal() as session:
        return (
            await session.execute(
                select(func.min(analytics_timestamp)).where(Order.tenant_id == tenant_id)
            )
        ).scalar_one_or_none()


async def _clear_tenant_sales_monthly_rows(tenant_id: uuid.UUID) -> int:
    async with AsyncSessionLocal() as session:
        async with session.begin():
            result = await session.execute(
                delete(SalesMonthly).where(SalesMonthly.tenant_id == tenant_id)
            )
        return result.rowcount or 0


async def _refresh_sales_monthly_window(
    tenant_id: uuid.UUID,
    *,
    start_month: date,
    end_month: date,
):
    async with AsyncSessionLocal() as session:
        return await refresh_sales_monthly_range(
            session,
            tenant_id,
            start_month=start_month,
            end_month=end_month,
        )


async def refresh_closed_sales_monthly_history(
    *,
    tenant_id: uuid.UUID,
    batch_mode: str | RefreshBatchMode | None = None,
    affected_domains: Sequence[str] | None = None,
) -> SalesMonthlyHistoryRefreshResult:
    normalized_batch_mode = _normalize_batch_mode(batch_mode)
    scoped_domains = tuple(affected_domains or ())

    if (
        normalized_batch_mode == RefreshBatchMode.INCREMENTAL
        and scoped_domains
        and DOMAIN_SALES not in scoped_domains
    ):
        return SalesMonthlyHistoryRefreshResult(
            batch_mode=normalized_batch_mode.value,
            affected_domains=scoped_domains,
            start_month=None,
            end_month=None,
            refreshed_month_count=0,
            total_upserted_row_count=0,
            total_deleted_row_count=0,
            skipped_line_count=0,
            cleared_row_count=0,
            skipped_reason="sales_domain_not_affected",
        )

    earliest_order_timestamp = await _fetch_earliest_order_timestamp(tenant_id)
    if earliest_order_timestamp is None:
        cleared_row_count = await _clear_tenant_sales_monthly_rows(tenant_id)
        return SalesMonthlyHistoryRefreshResult(
            batch_mode=normalized_batch_mode.value,
            affected_domains=scoped_domains,
            start_month=None,
            end_month=None,
            refreshed_month_count=0,
            total_upserted_row_count=0,
            total_deleted_row_count=0,
            skipped_line_count=0,
            cleared_row_count=cleared_row_count,
            skipped_reason="no_orders",
        )

    current_month_start = _current_month_start()
    start_month = normalize_month_start(earliest_order_timestamp.date())
    if start_month >= current_month_start:
        cleared_row_count = await _clear_tenant_sales_monthly_rows(tenant_id)
        return SalesMonthlyHistoryRefreshResult(
            batch_mode=normalized_batch_mode.value,
            affected_domains=scoped_domains,
            start_month=start_month,
            end_month=None,
            refreshed_month_count=0,
            total_upserted_row_count=0,
            total_deleted_row_count=0,
            skipped_line_count=0,
            cleared_row_count=cleared_row_count,
            skipped_reason="no_closed_months",
        )

    end_month = _previous_month_start(current_month_start)
    range_result = await _refresh_sales_monthly_window(
        tenant_id,
        start_month=start_month,
        end_month=end_month,
    )
    return SalesMonthlyHistoryRefreshResult(
        batch_mode=normalized_batch_mode.value,
        affected_domains=scoped_domains,
        start_month=start_month,
        end_month=end_month,
        refreshed_month_count=range_result.refreshed_month_count,
        total_upserted_row_count=sum(
            result.upserted_row_count for result in range_result.results
        ),
        total_deleted_row_count=sum(
            result.deleted_row_count for result in range_result.results
        ),
        skipped_line_count=sum(len(result.skipped_lines) for result in range_result.results),
        cleared_row_count=0,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="refresh-sales-monthly",
        description="Refresh closed historical sales_monthly aggregates for a tenant.",
    )
    parser.add_argument(
        "--tenant-id",
        type=parse_tenant_uuid,
        default=DEFAULT_TENANT_ID,
        help="Tenant UUID to refresh (defaults to DEFAULT_TENANT_ID).",
    )
    parser.add_argument(
        "--batch-mode",
        choices=[mode.value for mode in RefreshBatchMode],
        default=RefreshBatchMode.FULL.value,
        help="Execution scope hint used to decide whether the refresh should run.",
    )
    parser.add_argument(
        "--affected-domain",
        dest="affected_domains",
        action="append",
        default=[],
        help="Repeat to describe the domains touched by an incremental run.",
    )
    return parser


def _result_payload(result: SalesMonthlyHistoryRefreshResult) -> dict[str, object]:
    payload = asdict(result)
    payload["affected_domains"] = list(result.affected_domains)
    if result.start_month is not None:
        payload["start_month"] = result.start_month.isoformat()
    if result.end_month is not None:
        payload["end_month"] = result.end_month.isoformat()
    return payload


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    result = asyncio.run(
        refresh_closed_sales_monthly_history(
            tenant_id=args.tenant_id,
            batch_mode=args.batch_mode,
            affected_domains=tuple(args.affected_domains) or None,
        )
    )
    print(json.dumps(_result_payload(result), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())