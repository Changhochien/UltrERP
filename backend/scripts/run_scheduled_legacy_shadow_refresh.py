"""Run scheduled shadow refreshes and persist durable per-lane batch state."""

from __future__ import annotations

import argparse
import asyncio
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from common.time import utc_now
from domains.legacy_import.promotion_policy import evaluate_overlap_policy
from scripts.legacy_refresh_common import (
    RefreshDisposition,
    normalize_token,
    parse_non_negative_int,
    parse_tenant_uuid,
)
from scripts.legacy_refresh_state import (
    build_lane_state_paths,
    lane_key,
    read_json_file,
    remove_file_if_exists,
    write_json_atomically,
    write_lock_file_with_recovery,
)
from scripts.run_legacy_refresh import DEFAULT_SUMMARY_ROOT, run_legacy_refresh

DEFAULT_BATCH_PREFIX = "legacy-shadow"
DEFAULT_OVERLAP_EXIT_CODE = 2
SUCCESS_DISPOSITIONS = frozenset(
    {
        RefreshDisposition.COMPLETED.value,
        RefreshDisposition.COMPLETED_REVIEW_REQUIRED.value,
    }
)


@dataclass(slots=True, frozen=True)
class ScheduledShadowRefreshExecution:
    exit_code: int
    batch_id: str
    scheduler_run_id: str
    summary_path: Path | None
    latest_run_path: Path
    latest_success_path: Path
    state_record: dict[str, Any]
    latest_success_updated: bool


def _parse_batch_prefix(value: str) -> str:
    cleaned = normalize_token(value, default="")
    if not cleaned:
        raise argparse.ArgumentTypeError(
            "batch-prefix must contain at least one letter, number, dot, underscore, or dash"
        )
    return cleaned


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run-scheduled-legacy-shadow-refresh",
        description="Run a cron-safe shadow refresh and persist durable per-lane state.",
    )
    parser.add_argument(
        "--tenant-id",
        required=True,
        type=parse_tenant_uuid,
        help="Tenant UUID for the shadow refresh lane",
    )
    parser.add_argument(
        "--schema",
        required=True,
        help="Target raw schema name for the shadow refresh lane",
    )
    parser.add_argument(
        "--source-schema",
        default="public",
        help="Legacy source schema to stage from (default: public)",
    )
    parser.add_argument(
        "--lookback-days",
        type=parse_non_negative_int,
        default=10000,
        help="Lookback window passed to stock backfill steps (default: 10000)",
    )
    parser.add_argument(
        "--reconciliation-threshold",
        type=parse_non_negative_int,
        default=0,
        help="Allowed flagged reconciliation gaps before the run blocks (default: 0)",
    )
    parser.add_argument(
        "--batch-prefix",
        type=_parse_batch_prefix,
        default=DEFAULT_BATCH_PREFIX,
        help="Prefix used for immutable scheduled batch ids (default: legacy-shadow)",
    )
    return parser


def build_shadow_batch_id(
    batch_prefix: str,
    *,
    now: datetime | None = None,
) -> str:
    current = now or utc_now()
    normalized = current.astimezone(timezone.utc)
    return f"{batch_prefix}-{normalized.strftime('%Y%m%dT%H%M%SZ')}"


def _iso_now() -> str:
    return utc_now().isoformat()


def _build_state_record(
    *,
    scheduler_run_id: str,
    batch_id: str,
    tenant_id: uuid.UUID,
    schema_name: str,
    source_schema: str,
    started_at: str,
    completed_at: str,
    reconciliation_threshold: int,
    summary_path: Path | None,
    final_disposition: str,
    exit_code: int,
    validation_status: str,
    blocking_issue_count: int | None,
    reconciliation_gap_count: int | None,
    analyst_review_required: bool,
    promotion_readiness: bool,
    promotion_policy: dict[str, Any] | None = None,
    overlap_lock: dict[str, Any] | None = None,
) -> dict[str, Any]:
    record = {
        "state_version": 1,
        "scheduler_run_id": scheduler_run_id,
        "lane_key": lane_key(
            tenant_id=tenant_id,
            schema_name=schema_name,
            source_schema=source_schema,
        ),
        "tenant_id": str(tenant_id),
        "schema_name": schema_name,
        "source_schema": source_schema,
        "batch_id": batch_id,
        "summary_path": str(summary_path) if summary_path is not None else None,
        "started_at": started_at,
        "completed_at": completed_at,
        "final_disposition": final_disposition,
        "exit_code": exit_code,
        "validation_status": validation_status,
        "blocking_issue_count": blocking_issue_count,
        "reconciliation_gap_count": reconciliation_gap_count,
        "reconciliation_threshold": reconciliation_threshold,
        "analyst_review_required": analyst_review_required,
        "promotion_readiness": promotion_readiness,
    }
    if promotion_policy is not None:
        record["promotion_policy"] = promotion_policy
    if overlap_lock is not None:
        record["overlap_lock"] = overlap_lock
    return record


def _build_state_record_from_summary(
    *,
    scheduler_run_id: str,
    batch_id: str,
    tenant_id: uuid.UUID,
    schema_name: str,
    source_schema: str,
    started_at: str,
    completed_at: str,
    reconciliation_threshold: int,
    summary_path: Path,
    summary: dict[str, Any],
    exit_code: int,
) -> dict[str, Any]:
    validation_gate = summary.get("promotion_gate_status", {}).get("validation", {})
    return _build_state_record(
        scheduler_run_id=scheduler_run_id,
        batch_id=batch_id,
        tenant_id=tenant_id,
        schema_name=schema_name,
        source_schema=source_schema,
        started_at=started_at,
        completed_at=completed_at,
        reconciliation_threshold=reconciliation_threshold,
        summary_path=summary_path,
        final_disposition=summary.get("final_disposition", "failed"),
        exit_code=exit_code,
        validation_status=validation_gate.get("status") or "not-run",
        blocking_issue_count=validation_gate.get("blocking_issue_count"),
        reconciliation_gap_count=summary.get("reconciliation_gap_count"),
        analyst_review_required=bool(summary.get("analyst_review_required")),
        promotion_readiness=bool(summary.get("promotion_readiness")),
        promotion_policy=summary.get("promotion_policy"),
    )


def _format_metric(value: Any) -> str:
    return "n/a" if value is None else str(value)


def _print_operator_summary(result: ScheduledShadowRefreshExecution) -> None:
    updated_state_paths = [str(result.latest_run_path)]
    if result.latest_success_updated:
        updated_state_paths.append(str(result.latest_success_path))

    print(f"Scheduler run id: {result.scheduler_run_id}")
    print(f"Batch id: {result.batch_id}")
    print(
        f"Disposition: {result.state_record['final_disposition']} "
        f"(exit={result.exit_code})"
    )
    print(
        f"Validation: {result.state_record['validation_status']} "
        f"blocking_issue_count={_format_metric(result.state_record['blocking_issue_count'])}"
    )
    promotion_policy = result.state_record.get("promotion_policy")
    if isinstance(promotion_policy, dict):
        print(
            "Promotion policy: "
            f"{promotion_policy.get('classification', 'unknown')} "
            f"reason_codes={promotion_policy.get('reason_codes', [])}"
        )
    print(
        f"Reconciliation gaps: {_format_metric(result.state_record['reconciliation_gap_count'])} "
        f"(threshold={result.state_record['reconciliation_threshold']})"
    )
    print(
        "Summary artifact: "
        f"{result.state_record['summary_path'] or 'not-created'}"
    )
    print(f"State files updated: {', '.join(updated_state_paths)}")
    if not result.latest_success_updated:
        print(f"Latest success unchanged: {result.latest_success_path}")


async def run_scheduled_shadow_refresh(
    *,
    tenant_id: uuid.UUID,
    schema_name: str,
    source_schema: str,
    lookback_days: int,
    reconciliation_threshold: int,
    batch_prefix: str,
    summary_root: Path | None = None,
    state_root: Path | None = None,
) -> ScheduledShadowRefreshExecution:
    resolved_summary_root = summary_root or DEFAULT_SUMMARY_ROOT
    lane_paths = build_lane_state_paths(
        tenant_id=tenant_id,
        schema_name=schema_name,
        source_schema=source_schema,
        summary_root=resolved_summary_root,
        state_root=state_root,
    )
    latest_run_path = lane_paths.latest_run_path
    latest_success_path = lane_paths.latest_success_path
    lock_path = lane_paths.lock_path

    scheduler_run_id = str(uuid.uuid4())
    started_at = _iso_now()
    batch_id = build_shadow_batch_id(batch_prefix)
    lock_payload = {
        "scheduler_run_id": scheduler_run_id,
        "tenant_id": str(tenant_id),
        "schema_name": schema_name,
        "source_schema": source_schema,
        "batch_id": batch_id,
        "started_at": started_at,
    }

    lock_acquired = False
    try:
        try:
            write_lock_file_with_recovery(lock_path, lock_payload, now=utc_now())
            lock_acquired = True
        except FileExistsError:
            completed_at = _iso_now()
            promotion_policy = evaluate_overlap_policy(
                batch_id=batch_id,
                reconciliation_threshold=reconciliation_threshold,
            ).as_record()
            overlap_record = _build_state_record(
                scheduler_run_id=scheduler_run_id,
                batch_id=batch_id,
                tenant_id=tenant_id,
                schema_name=schema_name,
                source_schema=source_schema,
                started_at=started_at,
                completed_at=completed_at,
                reconciliation_threshold=reconciliation_threshold,
                summary_path=None,
                final_disposition=RefreshDisposition.OVERLAP_BLOCKED.value,
                exit_code=DEFAULT_OVERLAP_EXIT_CODE,
                validation_status="not-run",
                blocking_issue_count=None,
                reconciliation_gap_count=None,
                analyst_review_required=False,
                promotion_readiness=False,
                promotion_policy=promotion_policy,
                overlap_lock={
                    "path": str(lock_path),
                    "details": read_json_file(lock_path),
                },
            )
            write_json_atomically(latest_run_path, overlap_record)
            return ScheduledShadowRefreshExecution(
                exit_code=DEFAULT_OVERLAP_EXIT_CODE,
                batch_id=batch_id,
                scheduler_run_id=scheduler_run_id,
                summary_path=None,
                latest_run_path=latest_run_path,
                latest_success_path=latest_success_path,
                state_record=overlap_record,
                latest_success_updated=False,
            )

        refresh_execution = await run_legacy_refresh(
            batch_id=batch_id,
            tenant_id=tenant_id,
            schema_name=schema_name,
            source_schema=source_schema,
            lookback_days=lookback_days,
            reconciliation_threshold=reconciliation_threshold,
            summary_root=resolved_summary_root,
        )
        completed_at = _iso_now()
        state_record = _build_state_record_from_summary(
            scheduler_run_id=scheduler_run_id,
            batch_id=batch_id,
            tenant_id=tenant_id,
            schema_name=schema_name,
            source_schema=source_schema,
            started_at=started_at,
            completed_at=completed_at,
            reconciliation_threshold=reconciliation_threshold,
            summary_path=refresh_execution.summary_path,
            summary=refresh_execution.summary,
            exit_code=refresh_execution.exit_code,
        )
        write_json_atomically(latest_run_path, state_record)

        latest_success_updated = (
            state_record["final_disposition"] in SUCCESS_DISPOSITIONS
        )
        if latest_success_updated:
            write_json_atomically(latest_success_path, state_record)

        return ScheduledShadowRefreshExecution(
            exit_code=refresh_execution.exit_code,
            batch_id=batch_id,
            scheduler_run_id=scheduler_run_id,
            summary_path=refresh_execution.summary_path,
            latest_run_path=latest_run_path,
            latest_success_path=latest_success_path,
            state_record=state_record,
            latest_success_updated=latest_success_updated,
        )
    finally:
        if lock_acquired:
            remove_file_if_exists(lock_path)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    result = asyncio.run(
        run_scheduled_shadow_refresh(
            tenant_id=args.tenant_id,
            schema_name=args.schema,
            source_schema=args.source_schema,
            lookback_days=args.lookback_days,
            reconciliation_threshold=args.reconciliation_threshold,
            batch_prefix=args.batch_prefix,
        )
    )
    _print_operator_summary(result)
    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main())