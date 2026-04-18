"""Run the reviewed end-to-end live refresh workflow for a legacy batch."""

from __future__ import annotations

import argparse
import asyncio
import json
import uuid
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from common.config import PROJECT_ROOT
from common.time import utc_now
from domains.legacy_import.canonical import run_canonical_import
from domains.legacy_import.mapping import (
    export_product_mapping_review,
    import_product_mapping_review,
    run_product_mapping_seed,
)
from domains.legacy_import.normalization import run_normalization
from domains.legacy_import.promotion_policy import evaluate_promotion_policy_from_summary
from domains.legacy_import.staging import run_live_stage_import
from domains.legacy_import.validation import validate_import_batch
from scripts.backfill_purchase_receipts import backfill as backfill_purchase_receipts
from scripts.backfill_sales_reservations import backfill as backfill_sales_reservations
from scripts.legacy_refresh_common import (
    RefreshDisposition,
    RefreshGateStatus,
    RefreshStepStatus,
    normalize_token,
    parse_non_negative_int,
    parse_tenant_uuid,
)
from scripts.verify_reconciliation import verify as verify_reconciliation

DEFAULT_SUMMARY_ROOT = PROJECT_ROOT / "_bmad-output" / "operations" / "legacy-refresh"
STEP_ORDER = (
    "live-stage",
    "normalize",
    "map-products",
    "export-product-review",
    "import-product-review",
    "canonical-import",
    "validate-import",
    "backfill_purchase_receipts",
    "backfill_sales_reservations",
    "verify_reconciliation",
)
STEP_INDEX: dict[str, int] = {name: idx for idx, name in enumerate(STEP_ORDER)}


@dataclass(slots=True, frozen=True)
class LegacyRefreshExecution:
    exit_code: int
    summary_path: Path
    summary: dict[str, Any]


class _RefreshAbort(Exception):
    def __init__(self, exit_code: int) -> None:
        super().__init__()
        self.exit_code = exit_code


def _failure_reason(step_name: str) -> str:
    return f"aborted-after-{step_name}-failure"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run-legacy-refresh",
        description="Run the reviewed live refresh workflow for a legacy batch.",
    )
    parser.add_argument("--batch-id", required=True, help="Deterministic batch identifier")
    parser.add_argument(
        "--tenant-id",
        required=True,
        type=parse_tenant_uuid,
        help="Tenant UUID for the refresh run",
    )
    parser.add_argument(
        "--schema",
        required=True,
        help="Target raw schema name for staging and import phases",
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
        "--review-input",
        type=Path,
        help="Approved product review CSV to import before canonical import",
    )
    parser.add_argument(
        "--approved-by",
        help="Operator or analyst identifier recorded for review imports",
    )
    return parser


def _artifact_token(value: str) -> str:
    return normalize_token(value)


def _iso_now() -> str:
    return utc_now().isoformat()


def _build_step_records() -> list[dict[str, Any]]:
    return [
        {
            "name": step_name,
            "status": RefreshStepStatus.PENDING.value,
            "started_at": None,
            "completed_at": None,
            "details": {},
            "error": None,
        }
        for step_name in STEP_ORDER
    ]


def _step_index(step_name: str) -> int:
    return STEP_INDEX[step_name]


def _start_step(step: dict[str, Any]) -> None:
    step["status"] = RefreshStepStatus.RUNNING.value
    step["started_at"] = _iso_now()


def _complete_step(
    step: dict[str, Any],
    *,
    details: dict[str, Any] | None = None,
    status: str = RefreshStepStatus.COMPLETED.value,
) -> None:
    step["status"] = status
    step["completed_at"] = _iso_now()
    step["details"] = details or {}


def _skip_step(step: dict[str, Any], *, reason: str) -> None:
    step["status"] = RefreshStepStatus.SKIPPED.value
    step["completed_at"] = _iso_now()
    step["details"] = {"reason": reason}


def _fail_step(step: dict[str, Any], *, error: str) -> None:
    step["status"] = RefreshStepStatus.FAILED.value
    step["completed_at"] = _iso_now()
    step["error"] = error


def _mark_pending_steps_skipped(
    step_records: list[dict[str, Any]],
    *,
    after_step: str,
    reason: str,
) -> None:
    for step in step_records[_step_index(after_step) + 1 :]:
        if step["status"] == RefreshStepStatus.PENDING.value:
            _skip_step(step, reason=reason)


def _complete_named_step(
    summary: dict[str, Any],
    steps_by_name: dict[str, dict[str, Any]],
    step_name: str,
    *,
    details: dict[str, Any] | None = None,
    status: str = RefreshStepStatus.COMPLETED.value,
) -> None:
    _complete_step(steps_by_name[step_name], details=details, status=status)
    summary["last_completed_step"] = step_name


def _abort_refresh(
    summary: dict[str, Any],
    step_records: list[dict[str, Any]],
    steps_by_name: dict[str, dict[str, Any]],
    *,
    step_name: str,
    error: str,
    partial_state_preserved: bool,
) -> None:
    _fail_step(steps_by_name[step_name], error=error)
    summary["failed_step"] = step_name
    summary["final_disposition"] = RefreshDisposition.FAILED.value
    summary["exit_code"] = 1
    summary["partial_state_preserved"] = partial_state_preserved
    _mark_pending_steps_skipped(
        step_records,
        after_step=step_name,
        reason=_failure_reason(step_name),
    )
    raise _RefreshAbort(1)


async def _execute_step(
    summary: dict[str, Any],
    step_records: list[dict[str, Any]],
    steps_by_name: dict[str, dict[str, Any]],
    step_name: str,
    operation: Callable[[], Awaitable[Any]],
    *,
    partial_state_preserved: bool,
    details_factory: Callable[[Any], dict[str, Any]] | None = None,
    complete_on_success: bool = True,
) -> Any:
    _start_step(steps_by_name[step_name])
    try:
        result = await operation()
    except Exception as exc:
        _abort_refresh(
            summary,
            step_records,
            steps_by_name,
            step_name=step_name,
            error=str(exc),
            partial_state_preserved=partial_state_preserved,
        )

    if complete_on_success:
        _complete_named_step(
            summary,
            steps_by_name,
            step_name,
            details=details_factory(result) if details_factory is not None else None,
        )
    return result


async def _run_named_operation(
    step_name: str,
    operation: Callable[[], Awaitable[None]],
) -> tuple[str, Exception | None]:
    try:
        await operation()
    except Exception as exc:
        return step_name, exc
    return step_name, None


def _summary_path_for_run(
    *,
    summary_root: Path,
    schema_name: str,
    tenant_id: uuid.UUID,
    batch_id: str,
    run_id: str,
) -> Path:
    timestamp = utc_now().strftime("%Y%m%dT%H%M%SZ")
    file_name = (
        f"{_artifact_token(schema_name)}-"
        f"{_artifact_token(str(tenant_id))}-"
        f"{_artifact_token(batch_id)}-"
        f"refresh-{timestamp}-{run_id}.json"
    )
    return summary_root / file_name


def _review_export_path_for_batch(
    *,
    summary_root: Path,
    schema_name: str,
    tenant_id: uuid.UUID,
    batch_id: str,
) -> Path:
    file_name = (
        f"{_artifact_token(schema_name)}-"
        f"{_artifact_token(str(tenant_id))}-"
        f"{_artifact_token(batch_id)}-product-review.csv"
    )
    return summary_root / "product-review" / file_name


def _initial_summary(
    *,
    batch_id: str,
    tenant_id: uuid.UUID,
    schema_name: str,
    source_schema: str,
    run_id: str,
    reconciliation_threshold: int,
    review_input_path: Path | None,
) -> dict[str, Any]:
    return {
        "batch_id": batch_id,
        "tenant_id": str(tenant_id),
        "schema_name": schema_name,
        "source_schema": source_schema,
        "orchestrator_run_id": run_id,
        "started_at": _iso_now(),
        "completed_at": None,
        "steps": _build_step_records(),
        "canonical_attempt_number": None,
        "validation_json_path": None,
        "validation_markdown_path": None,
        "reconciliation_gap_count": None,
        "reconciliation_threshold_used": reconciliation_threshold,
        "analyst_review_required": False,
        "analyst_review_supplied": review_input_path is not None,
        "analyst_review_imported": False,
        "analyst_review_export_path": None,
        "approved_review_input_path": (
            str(review_input_path) if review_input_path is not None else None
        ),
        "promotion_readiness": False,
        "promotion_gate_status": {
            "analyst_review": {
                "status": RefreshGateStatus.PENDING.value,
                "required": False,
                "outstanding": False,
                "unknown_count": None,
                "supplied": review_input_path is not None,
                "imported": False,
                "export_path": None,
            },
            "validation": {
                "status": RefreshGateStatus.PENDING.value,
                "blocking_issue_count": None,
                "json_path": None,
                "markdown_path": None,
            },
            "reconciliation": {
                "status": RefreshGateStatus.PENDING.value,
                "gap_count": None,
                "threshold": reconciliation_threshold,
            },
            "promotion_ready": False,
        },
        "partial_state_preserved": False,
        "correction_proposals_path": None,
        "final_disposition": RefreshDisposition.RUNNING.value,
        "exit_code": None,
        "failed_step": None,
        "last_completed_step": None,
    }


def _set_gate_status(summary: dict[str, Any], gate: str, **values: Any) -> None:
    summary["promotion_gate_status"][gate].update(values)


def _write_summary(summary_path: Path, summary: dict[str, Any]) -> None:
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


async def run_legacy_refresh(
    *,
    batch_id: str,
    tenant_id: uuid.UUID,
    schema_name: str,
    source_schema: str,
    lookback_days: int,
    reconciliation_threshold: int,
    review_input_path: Path | None = None,
    approved_by: str | None = None,
    summary_root: Path | None = None,
) -> LegacyRefreshExecution:
    if review_input_path is not None and not approved_by:
        raise ValueError("approved_by is required when review_input_path is provided")

    resolved_summary_root = summary_root or DEFAULT_SUMMARY_ROOT
    run_id = str(uuid.uuid4())
    summary = _initial_summary(
        batch_id=batch_id,
        tenant_id=tenant_id,
        schema_name=schema_name,
        source_schema=source_schema,
        run_id=run_id,
        reconciliation_threshold=reconciliation_threshold,
        review_input_path=review_input_path,
    )
    step_records = summary["steps"]
    steps_by_name = {step["name"]: step for step in step_records}
    summary_path = _summary_path_for_run(
        summary_root=resolved_summary_root,
        schema_name=schema_name,
        tenant_id=tenant_id,
        batch_id=batch_id,
        run_id=run_id,
    )

    try:
        try:
            await _execute_step(
                summary,
                step_records,
                steps_by_name,
                "live-stage",
                lambda: run_live_stage_import(
                    batch_id=batch_id,
                    source_schema=source_schema,
                    selected_tables=(),
                    tenant_id=tenant_id,
                    schema_name=schema_name,
                ),
                partial_state_preserved=False,
                details_factory=lambda result: {
                    "table_count": len(result.tables),
                    "source": result.source_display_name,
                },
            )

            await _execute_step(
                summary,
                step_records,
                steps_by_name,
                "normalize",
                lambda: run_normalization(
                    batch_id=batch_id,
                    tenant_id=tenant_id,
                    schema_name=schema_name,
                ),
                partial_state_preserved=True,
                details_factory=lambda result: {
                    "party_count": result.party_count,
                    "product_count": result.product_count,
                    "warehouse_count": result.warehouse_count,
                    "inventory_count": result.inventory_count,
                },
            )

            mapping_result = await _execute_step(
                summary,
                step_records,
                steps_by_name,
                "map-products",
                lambda: run_product_mapping_seed(
                    batch_id=batch_id,
                    tenant_id=tenant_id,
                    schema_name=schema_name,
                ),
                partial_state_preserved=True,
                details_factory=lambda result: {
                    "mapping_count": result.mapping_count,
                    "candidate_count": result.candidate_count,
                    "unknown_count": result.unknown_count,
                    "orphan_code_count": result.orphan_code_count,
                    "orphan_row_count": result.orphan_row_count,
                },
            )

            unresolved_mappings = mapping_result.unknown_count > 0
            summary["analyst_review_required"] = (
                unresolved_mappings and review_input_path is None
            )
            _set_gate_status(
                summary,
                "analyst_review",
                required=unresolved_mappings,
                outstanding=unresolved_mappings and review_input_path is None,
                unknown_count=mapping_result.unknown_count,
            )

            export_step = steps_by_name["export-product-review"]
            if unresolved_mappings and review_input_path is None:
                review_export_path = _review_export_path_for_batch(
                    summary_root=resolved_summary_root,
                    schema_name=schema_name,
                    tenant_id=tenant_id,
                    batch_id=batch_id,
                )
                export_result = await _execute_step(
                    summary,
                    step_records,
                    steps_by_name,
                    "export-product-review",
                    lambda: export_product_mapping_review(
                        batch_id=batch_id,
                        output_path=review_export_path,
                        tenant_id=tenant_id,
                        schema_name=schema_name,
                    ),
                    partial_state_preserved=True,
                    details_factory=lambda result: {
                        "exported_row_count": result.exported_row_count,
                        "output_path": str(result.output_path),
                    },
                )
                summary["analyst_review_export_path"] = str(export_result.output_path)
                _set_gate_status(
                    summary,
                    "analyst_review",
                    status=RefreshGateStatus.REVIEW_REQUIRED.value,
                    export_path=str(export_result.output_path),
                )
            else:
                export_reason = (
                    "approved review input supplied"
                    if review_input_path is not None
                    else "no unresolved mappings"
                )
                _skip_step(export_step, reason=export_reason)

            import_step = steps_by_name["import-product-review"]
            if review_input_path is not None:
                await _execute_step(
                    summary,
                    step_records,
                    steps_by_name,
                    "import-product-review",
                    lambda: import_product_mapping_review(
                        batch_id=batch_id,
                        input_path=review_input_path,
                        approved_by=approved_by,
                        tenant_id=tenant_id,
                        schema_name=schema_name,
                    ),
                    partial_state_preserved=True,
                    details_factory=lambda result: {
                        "input_path": str(result.input_path),
                        "applied_decision_count": result.applied_decision_count,
                        "approved_by": approved_by,
                    },
                )
                summary["analyst_review_imported"] = True
                _set_gate_status(
                    summary,
                    "analyst_review",
                    status=RefreshGateStatus.REVIEW_IMPORTED.value,
                    imported=True,
                )
            else:
                _skip_step(import_step, reason="no approved review input")
                if not unresolved_mappings:
                    _set_gate_status(
                        summary,
                        "analyst_review",
                        status=RefreshGateStatus.PASSED.value,
                    )

            canonical_result = await _execute_step(
                summary,
                step_records,
                steps_by_name,
                "canonical-import",
                lambda: run_canonical_import(
                    batch_id=batch_id,
                    tenant_id=tenant_id,
                    schema_name=schema_name,
                ),
                partial_state_preserved=True,
                details_factory=lambda result: {
                    "attempt_number": result.attempt_number,
                    "lineage_count": result.lineage_count,
                    "holding_count": result.holding_count,
                },
            )
            summary["canonical_attempt_number"] = canonical_result.attempt_number

            validation_result = await _execute_step(
                summary,
                step_records,
                steps_by_name,
                "validate-import",
                lambda: validate_import_batch(
                    batch_id=batch_id,
                    tenant_id=tenant_id,
                    schema_name=schema_name,
                    attempt_number=canonical_result.attempt_number,
                ),
                partial_state_preserved=True,
                complete_on_success=False,
            )

            validation_details = {
                "status": validation_result.report.status,
                "blocking_issue_count": validation_result.report.blocking_issue_count,
                "json_path": str(validation_result.json_path),
                "markdown_path": str(validation_result.markdown_path),
                "scope_key": validation_result.report.replay.scope_key,
            }
            summary["validation_json_path"] = str(validation_result.json_path)
            summary["validation_markdown_path"] = str(validation_result.markdown_path)
            _set_gate_status(
                summary,
                "validation",
                status=validation_result.report.status,
                blocking_issue_count=validation_result.report.blocking_issue_count,
                json_path=str(validation_result.json_path),
                markdown_path=str(validation_result.markdown_path),
            )
            if validation_result.report.status == RefreshGateStatus.BLOCKED.value:
                _complete_named_step(
                    summary,
                    steps_by_name,
                    "validate-import",
                    details=validation_details,
                    status=RefreshStepStatus.BLOCKED.value,
                )
                summary["final_disposition"] = RefreshDisposition.VALIDATION_BLOCKED.value
                summary["exit_code"] = 1
                summary["promotion_readiness"] = False
                _set_gate_status(
                    summary,
                    "reconciliation",
                    status=RefreshGateStatus.NOT_RUN.value,
                )
                _mark_pending_steps_skipped(
                    step_records,
                    after_step="validate-import",
                    reason=RefreshDisposition.VALIDATION_BLOCKED.value,
                )
                return LegacyRefreshExecution(1, summary_path, summary)

            _complete_named_step(
                summary,
                steps_by_name,
                "validate-import",
                details=validation_details,
            )

            backfill_purchase_step = steps_by_name["backfill_purchase_receipts"]
            backfill_sales_step = steps_by_name["backfill_sales_reservations"]
            _start_step(backfill_purchase_step)
            _start_step(backfill_sales_step)
            backfill_details = {"lookback_days": lookback_days, "dry_run": False}
            backfill_results = await asyncio.gather(
                _run_named_operation(
                    "backfill_purchase_receipts",
                    lambda: backfill_purchase_receipts(
                        lookback_days=lookback_days,
                        dry_run=False,
                        tenant_id=tenant_id,
                    ),
                ),
                _run_named_operation(
                    "backfill_sales_reservations",
                    lambda: backfill_sales_reservations(
                        lookback_days=lookback_days,
                        dry_run=False,
                        tenant_id=tenant_id,
                    ),
                ),
            )

            failures = [result for result in backfill_results if result[1] is not None]
            for completed_step_name, error in backfill_results:
                if error is None:
                    _complete_named_step(
                        summary,
                        steps_by_name,
                        completed_step_name,
                        details=backfill_details,
                    )

            if failures:
                failed_step_name, failed_exc = failures[0]
                _fail_step(steps_by_name[failed_step_name], error=str(failed_exc))
                summary["failed_step"] = failed_step_name
                summary["final_disposition"] = RefreshDisposition.FAILED.value
                summary["exit_code"] = 1
                summary["partial_state_preserved"] = True
                _mark_pending_steps_skipped(
                    step_records,
                    after_step=failed_step_name,
                    reason=_failure_reason(failed_step_name),
                )
                return LegacyRefreshExecution(1, summary_path, summary)

            reconciliation_gap_count = await _execute_step(
                summary,
                step_records,
                steps_by_name,
                "verify_reconciliation",
                lambda: verify_reconciliation(tenant_id=tenant_id),
                partial_state_preserved=True,
                complete_on_success=False,
            )

            summary["reconciliation_gap_count"] = reconciliation_gap_count
            _set_gate_status(
                summary,
                "reconciliation",
                gap_count=reconciliation_gap_count,
                status=(
                    RefreshGateStatus.BLOCKED.value
                    if reconciliation_gap_count > reconciliation_threshold
                    else RefreshGateStatus.PASSED.value
                ),
            )
            reconciliation_details = {
                "gap_count": reconciliation_gap_count,
                "threshold": reconciliation_threshold,
            }
            if reconciliation_gap_count > reconciliation_threshold:
                _complete_named_step(
                    summary,
                    steps_by_name,
                    "verify_reconciliation",
                    details=reconciliation_details,
                    status=RefreshStepStatus.BLOCKED.value,
                )
                summary["final_disposition"] = (
                    RefreshDisposition.RECONCILIATION_BLOCKED.value
                )
                summary["exit_code"] = 1
                summary["promotion_readiness"] = False
                return LegacyRefreshExecution(1, summary_path, summary)

            _complete_named_step(
                summary,
                steps_by_name,
                "verify_reconciliation",
                details=reconciliation_details,
            )
            summary["promotion_readiness"] = not summary["analyst_review_required"]
            summary["final_disposition"] = (
                RefreshDisposition.COMPLETED_REVIEW_REQUIRED.value
                if summary["analyst_review_required"]
                else RefreshDisposition.COMPLETED.value
            )
            summary["exit_code"] = 0
            return LegacyRefreshExecution(0, summary_path, summary)
        except _RefreshAbort as abort:
            return LegacyRefreshExecution(abort.exit_code, summary_path, summary)
    finally:
        summary["completed_at"] = _iso_now()
        summary["promotion_gate_status"]["promotion_ready"] = summary[
            "promotion_readiness"
        ]
        summary["promotion_policy"] = evaluate_promotion_policy_from_summary(
            summary=summary,
            summary_path=str(summary_path),
            lock_active=False,
        ).as_record()
        _write_summary(summary_path, summary)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.review_input is None and args.approved_by is not None:
        parser.error("--approved-by requires --review-input")
    if args.review_input is not None and args.approved_by is None:
        parser.error("--approved-by is required when --review-input is provided")

    execution = run_legacy_refresh(
        batch_id=args.batch_id,
        tenant_id=args.tenant_id,
        schema_name=args.schema,
        source_schema=args.source_schema,
        lookback_days=args.lookback_days,
        reconciliation_threshold=args.reconciliation_threshold,
        review_input_path=args.review_input,
        approved_by=args.approved_by,
    )
    result = asyncio.run(execution)
    print(f"Legacy refresh summary: {result.summary_path}")
    print(
        f"Disposition: {result.summary['final_disposition']} "
        f"(exit={result.exit_code})"
    )
    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main())