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
from domains.product_analytics.service import (
    backfill_sales_monthly_history,
    check_sales_monthly_health,
    normalize_month_start,
    refresh_sales_monthly_range,
    repair_missing_sales_monthly_months,
)
from scripts.legacy_refresh_common import RefreshBatchMode

DEFAULT_INCREMENTAL_ROLLING_CLOSED_MONTHS = 3


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


def _subtract_months(month_start: date, month_count: int) -> date:
    month_index = month_start.year * 12 + (month_start.month - 1) - month_count
    year, month_offset = divmod(month_index, 12)
    return date(year, month_offset + 1, 1)


def _rolling_closed_month_window(
    current_month_start: date,
    *,
    rolling_closed_months: int,
) -> tuple[date, date]:
    if rolling_closed_months < 1:
        raise ValueError("rolling_closed_months must be at least 1")

    end_month = _previous_month_start(current_month_start)
    start_month = _subtract_months(current_month_start, rolling_closed_months)
    return start_month, end_month


async def refresh_closed_sales_monthly_history(
    *,
    tenant_id: uuid.UUID,
    batch_mode: str | RefreshBatchMode | None = None,
    affected_domains: Sequence[str] | None = None,
    rolling_closed_months: int | None = None,
) -> SalesMonthlyHistoryRefreshResult:
    normalized_batch_mode = _normalize_batch_mode(batch_mode)
    scoped_domains = tuple(affected_domains or ())

    if rolling_closed_months is not None and rolling_closed_months < 1:
        raise ValueError("rolling_closed_months must be at least 1")

    if (
        rolling_closed_months is None
        and normalized_batch_mode == RefreshBatchMode.INCREMENTAL
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
    if rolling_closed_months is not None:
        start_month, end_month = _rolling_closed_month_window(
            current_month_start,
            rolling_closed_months=rolling_closed_months,
        )
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
            skipped_line_count=sum(
                len(result.skipped_lines) for result in range_result.results
            ),
            cleared_row_count=0,
        )

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


# --- Health Check --- #


@dataclass(slots=True, frozen=True)
class SalesMonthlyHealthCheckResult:
    tenant_id: uuid.UUID
    window_start: date | None
    window_end: date | None
    is_healthy: bool
    missing_months: tuple[dict[str, object], ...]
    checked_month_count: int
    current_open_month: date


async def run_health_check(
    tenant_id: uuid.UUID,
    *,
    start_month: date | None = None,
    end_month: date | None = None,
) -> SalesMonthlyHealthCheckResult:
    async with AsyncSessionLocal() as session:
        health = await check_sales_monthly_health(
            session,
            tenant_id,
            start_month=start_month,
            end_month=end_month,
        )
    return SalesMonthlyHealthCheckResult(
        tenant_id=health.tenant_id,
        window_start=health.window_start,
        window_end=health.window_end,
        is_healthy=health.is_healthy,
        missing_months=tuple(
            {
                "month_start": m.month_start.isoformat(),
                "transactional_order_count": m.transactional_order_count,
                "transactional_revenue": str(m.transactional_revenue),
            }
            for m in health.missing_months
        ),
        checked_month_count=health.checked_month_count,
        current_open_month=health.current_open_month,
    )


# --- Repair Missing Months --- #


@dataclass(slots=True, frozen=True)
class SalesMonthlyRepairResult:
    tenant_id: uuid.UUID
    repaired_months: tuple[str, ...]
    refreshed_month_count: int
    total_upserted_row_count: int
    total_deleted_row_count: int
    skipped_line_count: int
    idemponent: bool


async def run_repair_missing(
    tenant_id: uuid.UUID,
    missing_months: list[date],
) -> SalesMonthlyRepairResult:
    async with AsyncSessionLocal() as session:
        range_result = await repair_missing_sales_monthly_months(
            session,
            tenant_id,
            missing_months,
        )
    return SalesMonthlyRepairResult(
        tenant_id=tenant_id,
        repaired_months=tuple(m.month_start.isoformat() for m in missing_months),
        refreshed_month_count=range_result.refreshed_month_count,
        total_upserted_row_count=sum(
            r.upserted_row_count for r in range_result.results
        ),
        total_deleted_row_count=sum(
            r.deleted_row_count for r in range_result.results
        ),
        skipped_line_count=sum(len(r.skipped_lines) for r in range_result.results),
        idemponent=True,
    )


# --- Bounded Historical Backfill --- #


@dataclass(slots=True, frozen=True)
class SalesMonthlyBackfillResult:
    tenant_id: uuid.UUID
    start_month: date
    end_month: date
    refreshed_month_count: int
    total_upserted_row_count: int
    total_deleted_row_count: int
    skipped_line_count: int
    bounded: bool


async def run_bounded_backfill(
    tenant_id: uuid.UUID,
    *,
    start_month: date,
    end_month: date | None = None,
) -> SalesMonthlyBackfillResult:
    async with AsyncSessionLocal() as session:
        range_result = await backfill_sales_monthly_history(
            session,
            tenant_id,
            start_month=start_month,
            end_month=end_month,
        )

    if range_result.results:
        first_month = range_result.results[0].month_start
        last_month = range_result.results[-1].month_start
    else:
        first_month = start_month
        last_month = end_month or _current_month_start()

    return SalesMonthlyBackfillResult(
        tenant_id=tenant_id,
        start_month=first_month,
        end_month=last_month,
        refreshed_month_count=range_result.refreshed_month_count,
        total_upserted_row_count=sum(
            r.upserted_row_count for r in range_result.results
        ),
        total_deleted_row_count=sum(
            r.deleted_row_count for r in range_result.results
        ),
        skipped_line_count=sum(len(r.skipped_lines) for r in range_result.results),
        bounded=end_month is not None,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="refresh-sales-monthly",
        description="Manage closed historical sales_monthly aggregates for a tenant.",
    )
    parser.add_argument(
        "--tenant-id",
        type=parse_tenant_uuid,
        default=DEFAULT_TENANT_ID,
        help="Tenant UUID (defaults to DEFAULT_TENANT_ID).",
    )
    subparsers = parser.add_subparsers(dest="mode", required=True)

    # Refresh subcommand (legacy compatibility)
    refresh_parser = subparsers.add_parser(
        "refresh",
        help="Refresh closed historical sales_monthly aggregates.",
    )
    refresh_parser.add_argument(
        "--batch-mode",
        choices=[mode.value for mode in RefreshBatchMode],
        default=RefreshBatchMode.FULL.value,
        help="Execution scope hint.",
    )
    refresh_parser.add_argument(
        "--affected-domain",
        dest="affected_domains",
        action="append",
        default=[],
        help="Repeat to describe the domains touched by an incremental run.",
    )
    refresh_parser.add_argument(
        "--rolling-closed-months",
        type=int,
        default=None,
        help=(
            "Refresh only the most recent N closed months instead of the full historical "
            "range. Recommended for nightly upkeep after the initial backfill."
        ),
    )

    # Health check subcommand
    health_parser = subparsers.add_parser(
        "health",
        help="Check closed-month snapshot coverage health.",
    )
    health_parser.add_argument(
        "--start-month",
        type=lambda s: date.fromisoformat(s),
        default=None,
        help="Start month (YYYY-MM-DD). Defaults to end-month or 3 months ago.",
    )
    health_parser.add_argument(
        "--end-month",
        type=lambda s: date.fromisoformat(s),
        default=None,
        help="End month (YYYY-MM-DD). Defaults to last closed month.",
    )

    # Repair missing months subcommand
    repair_parser = subparsers.add_parser(
        "repair",
        help="Repair only missing closed months (idempotent).",
    )
    repair_parser.add_argument(
        "--missing-month",
        dest="missing_months",
        action="append",
        type=lambda s: date.fromisoformat(s),
        required=True,
        help="Month to repair (YYYY-MM-DD). Repeat for multiple months.",
    )

    # Bounded backfill subcommand
    backfill_parser = subparsers.add_parser(
        "backfill",
        help="Backfill a bounded historical range.",
    )
    backfill_parser.add_argument(
        "--start-month",
        type=lambda s: date.fromisoformat(s),
        required=True,
        help="Start month (YYYY-MM-DD).",
    )
    backfill_parser.add_argument(
        "--end-month",
        type=lambda s: date.fromisoformat(s),
        default=None,
        help="End month (YYYY-MM-DD). Defaults to last closed month.",
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


def _health_payload(result: SalesMonthlyHealthCheckResult) -> dict[str, object]:
    return {
        "mode": "health",
        "tenant_id": str(result.tenant_id),
        "window_start": result.window_start.isoformat() if result.window_start else None,
        "window_end": result.window_end.isoformat() if result.window_end else None,
        "is_healthy": result.is_healthy,
        "missing_months": list(result.missing_months),
        "checked_month_count": result.checked_month_count,
        "current_open_month": result.current_open_month.isoformat(),
        "data_gap_acknowledged": not result.is_healthy,
    }


def _repair_payload(result: SalesMonthlyRepairResult) -> dict[str, object]:
    return {
        "mode": "repair",
        "tenant_id": str(result.tenant_id),
        "repaired_months": list(result.repaired_months),
        "refreshed_month_count": result.refreshed_month_count,
        "total_upserted_row_count": result.total_upserted_row_count,
        "total_deleted_row_count": result.total_deleted_row_count,
        "skipped_line_count": result.skipped_line_count,
        "idempotent": result.idempotent,
    }


def _backfill_payload(result: SalesMonthlyBackfillResult) -> dict[str, object]:
    return {
        "mode": "backfill",
        "tenant_id": str(result.tenant_id),
        "start_month": result.start_month.isoformat(),
        "end_month": result.end_month.isoformat(),
        "refreshed_month_count": result.refreshed_month_count,
        "total_upserted_row_count": result.total_upserted_row_count,
        "total_deleted_row_count": result.total_deleted_row_count,
        "skipped_line_count": result.skipped_line_count,
        "bounded": result.bounded,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.mode == "health":
        result = asyncio.run(
            run_health_check(
                tenant_id=args.tenant_id,
                start_month=args.start_month,
                end_month=args.end_month,
            )
        )
        print(json.dumps(_health_payload(result), indent=2, sort_keys=True))
        return 0

    elif args.mode == "repair":
        result = asyncio.run(
            run_repair_missing(
                tenant_id=args.tenant_id,
                missing_months=args.missing_months,
            )
        )
        print(json.dumps(_repair_payload(result), indent=2, sort_keys=True))
        return 0

    elif args.mode == "backfill":
        result = asyncio.run(
            run_bounded_backfill(
                tenant_id=args.tenant_id,
                start_month=args.start_month,
                end_month=args.end_month,
            )
        )
        print(json.dumps(_backfill_payload(result), indent=2, sort_keys=True))
        return 0

    else:
        # Legacy refresh mode (args.mode == "refresh" or default)
        result = asyncio.run(
            refresh_closed_sales_monthly_history(
                tenant_id=args.tenant_id,
                batch_mode=getattr(args, "batch_mode", None),
                affected_domains=tuple(getattr(args, "affected_domains", []) or None),
                rolling_closed_months=getattr(args, "rolling_closed_months", None),
            )
        )
        print(json.dumps(_result_payload(result), indent=2, sort_keys=True))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())