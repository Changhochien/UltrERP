"""Evaluate the latest successful shadow batch and advance the working-lane pointer."""

from __future__ import annotations

import argparse
import asyncio
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from common.cli_args import normalize_token, parse_tenant_uuid
from common.time import utc_now
from domains.legacy_import.promotion import (
    PROMOTION_RESULT_BLOCKED,
    PROMOTION_RESULT_NOOP,
    PROMOTION_RESULT_PROMOTED,
    PromotionDecision,
    _as_text,
    _lane_identity_mismatches,
    evaluate_promotion,
)
from scripts.legacy_refresh_state import (
    build_lane_state_paths,
    lane_key,
    read_json_file,
    read_json_file_with_error,
    recover_stale_lock,
    remove_file_if_exists,
    write_json_atomically,
    write_lock_file_with_recovery,
)
from scripts.run_legacy_refresh import DEFAULT_SUMMARY_ROOT

DEFAULT_PROMOTED_BY = "SYSTEM"
EXCEPTION_REQUIRED_CLASSIFICATION = "exception-required"


@dataclass(slots=True, frozen=True)
class LegacyPromotionExecution:
    exit_code: int
    promotion_run_id: str
    candidate_batch_id: str | None
    result_path: Path | None
    latest_promoted_path: Path
    result_record: dict[str, object]
    latest_promoted_updated: bool


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run-legacy-promotion",
        description=(
            "Evaluate the latest successful shadow batch and update the "
            "working-lane promotion pointer."
        ),
    )
    parser.add_argument(
        "--tenant-id",
        required=True,
        type=parse_tenant_uuid,
        help="Tenant UUID for the lane being promoted",
    )
    parser.add_argument(
        "--schema",
        required=True,
        help="Target raw schema name for the lane being promoted",
    )
    parser.add_argument(
        "--source-schema",
        default="public",
        help="Legacy source schema for the lane (default: public)",
    )
    parser.add_argument(
        "--promoted-by",
        default=DEFAULT_PROMOTED_BY,
        help="Actor identity recorded for the promotion decision (default: SYSTEM)",
    )
    parser.add_argument(
        "--allow-exception-override",
        action="store_true",
        help="Allow an operator to advance an exception-required batch with audit metadata",
    )
    parser.add_argument(
        "--override-rationale",
        help="Required rationale when allowing an exception override",
    )
    parser.add_argument(
        "--override-scope",
        help="Required scope when allowing an exception override",
    )
    return parser


def _iso_now() -> str:
    return utc_now().isoformat()


def _text_value(record: dict[str, object] | None, key: str) -> str | None:
    """Return only real non-empty text fields from dict-keyed state."""
    if not isinstance(record, Mapping):
        return None
    value = record.get(key)
    if not isinstance(value, str):
        return None
    return _as_text(value)


def _promotion_result_path(
    *,
    result_root: Path,
    batch_id: str | None,
    promotion_run_id: str,
) -> Path:
    timestamp = utc_now().strftime("%Y%m%dT%H%M%SZ")
    batch_token = normalize_token(batch_id or "no-candidate")
    return result_root / f"{timestamp}-{batch_token}-{promotion_run_id}.json"


def _promotion_override_path(
    *,
    overrides_root: Path,
    batch_id: str | None,
    promotion_run_id: str,
) -> Path:
    timestamp = utc_now().strftime("%Y%m%dT%H%M%SZ")
    batch_token = normalize_token(batch_id or "no-candidate")
    return overrides_root / f"{timestamp}-{batch_token}-{promotion_run_id}.json"


def _require_override_text(value: str | None, *, field_name: str) -> str:
    text = (value or "").strip()
    if not text:
        raise ValueError(f"{field_name} is required when allow_exception_override is enabled")
    return text


def _normalize_promoted_by(value: str | None) -> str:
    text = (value or "").strip()
    return text or DEFAULT_PROMOTED_BY


def _require_override_actor(value: str) -> str:
    if value.upper() == DEFAULT_PROMOTED_BY:
        raise ValueError(
            "promoted_by must identify the approving operator when "
            "allow_exception_override is enabled"
        )
    return value


def _promotion_mode(decision: PromotionDecision) -> str:
    if decision.promotion_result == PROMOTION_RESULT_PROMOTED:
        return "automatic"
    if decision.promotion_result == PROMOTION_RESULT_NOOP:
        return "noop"
    return "blocked"


def _decorate_result_record(
    record: dict[str, object],
    *,
    decision: PromotionDecision,
    promotion_mode: str,
    override_applied: bool = False,
    override_record_path: Path | None = None,
    override_rationale: str | None = None,
    override_scope: str | None = None,
) -> dict[str, object]:
    record["promotion_mode"] = promotion_mode
    record["override_applied"] = override_applied
    record["override_record_path"] = (
        str(override_record_path) if override_record_path is not None else None
    )
    record["override_rationale"] = override_rationale
    record["override_scope"] = override_scope
    if override_applied:
        record["promotion_policy_classification"] = EXCEPTION_REQUIRED_CLASSIFICATION
        record["promotion_policy_reason_codes"] = ["analyst-review"]
        record["override_allowed"] = True
    elif decision.blocking_gate == "analyst-review":
        record["promotion_policy_classification"] = EXCEPTION_REQUIRED_CLASSIFICATION
        record["promotion_policy_reason_codes"] = ["analyst-review"]
    return record


def _write_failure_result(
    *,
    result_path: Path,
    decision: PromotionDecision,
    promotion_run_id: str,
    tenant_id: uuid.UUID,
    schema_name: str,
    source_schema: str,
    write_error: Exception,
) -> tuple[Path | None, dict[str, object]]:
    failure_decision = PromotionDecision(
        promotion_result=PROMOTION_RESULT_BLOCKED,
        batch_id=decision.batch_id,
        previous_batch_id=decision.previous_batch_id,
        evaluated_at=decision.evaluated_at,
        promoted_at=None,
        promoted_by=decision.promoted_by,
        summary_path=decision.summary_path,
        validation_status=decision.validation_status,
        blocking_issue_count=decision.blocking_issue_count,
        reconciliation_gap_count=decision.reconciliation_gap_count,
        reconciliation_threshold=decision.reconciliation_threshold,
        candidate_final_disposition=decision.candidate_final_disposition,
        promotion_readiness=False,
        analyst_review_required=decision.analyst_review_required,
        blocking_gate="promotion-write-failure",
        message=(
            f"Batch {decision.batch_id or 'unknown'} could not advance the "
            f"working-lane pointer: {write_error}"
        ),
    )
    failure_record = failure_decision.as_record(
        promotion_run_id=promotion_run_id,
        lane_key=lane_key(
            tenant_id=tenant_id,
            schema_name=schema_name,
            source_schema=source_schema,
        ),
        tenant_id=str(tenant_id),
        schema_name=schema_name,
        source_schema=source_schema,
    )
    _decorate_result_record(
        failure_record,
        decision=failure_decision,
        promotion_mode="failed-write",
    )
    try:
        write_json_atomically(result_path, failure_record)
    except Exception:
        return None, failure_record
    return result_path, failure_record


def _build_write_failure_execution(
    *,
    result_path: Path,
    decision: PromotionDecision,
    promotion_run_id: str,
    tenant_id: uuid.UUID,
    schema_name: str,
    source_schema: str,
    write_error: Exception,
    latest_promoted_path: Path,
    cleanup_result_path: Path | None = None,
    cleanup_override_path: Path | None = None,
) -> LegacyPromotionExecution:
    failure_path, failure_record = _write_failure_result(
        result_path=result_path,
        decision=decision,
        promotion_run_id=promotion_run_id,
        tenant_id=tenant_id,
        schema_name=schema_name,
        source_schema=source_schema,
        write_error=write_error,
    )
    if cleanup_override_path is not None:
        try:
            cleanup_override_path.unlink(missing_ok=True)
        except OSError:
            pass
    if failure_path is None and cleanup_result_path is not None:
        try:
            cleanup_result_path.unlink(missing_ok=True)
        except OSError:
            pass
    return LegacyPromotionExecution(
        exit_code=1,
        promotion_run_id=promotion_run_id,
        candidate_batch_id=decision.batch_id,
        result_path=failure_path,
        latest_promoted_path=latest_promoted_path,
        result_record=failure_record,
        latest_promoted_updated=False,
    )


def _build_invalid_promoted_state_execution(
    *,
    result_path: Path,
    promotion_run_id: str,
    latest_promoted_path: Path,
    latest_success_state: dict[str, object] | None,
    tenant_id: uuid.UUID,
    schema_name: str,
    source_schema: str,
    promoted_by: str,
    evaluated_at: str,
    error_message: str,
) -> LegacyPromotionExecution:
    decision = PromotionDecision(
        promotion_result=PROMOTION_RESULT_BLOCKED,
        batch_id=_text_value(latest_success_state, "batch_id"),
        previous_batch_id=None,
        evaluated_at=evaluated_at,
        promoted_at=None,
        promoted_by=promoted_by,
        summary_path=_text_value(latest_success_state, "summary_path"),
        validation_status=_text_value(latest_success_state, "validation_status") or "not-run",
        blocking_issue_count=None,
        reconciliation_gap_count=None,
        reconciliation_threshold=None,
        candidate_final_disposition=_text_value(latest_success_state, "final_disposition"),
        promotion_readiness=False,
        analyst_review_required=False,
        blocking_gate="invalid-promoted-state",
        message=(
            "The current promoted state is invalid and must be repaired before "
            f"automatic promotion can continue: {error_message}"
        ),
    )
    result_record = decision.as_record(
        promotion_run_id=promotion_run_id,
        lane_key=lane_key(
            tenant_id=tenant_id,
            schema_name=schema_name,
            source_schema=source_schema,
        ),
        tenant_id=str(tenant_id),
        schema_name=schema_name,
        source_schema=source_schema,
    )
    _decorate_result_record(result_record, decision=decision, promotion_mode="blocked")
    try:
        write_json_atomically(result_path, result_record)
    except Exception as exc:
        return _build_write_failure_execution(
            result_path=result_path,
            decision=decision,
            promotion_run_id=promotion_run_id,
            tenant_id=tenant_id,
            schema_name=schema_name,
            source_schema=source_schema,
            write_error=exc,
            latest_promoted_path=latest_promoted_path,
        )
    return LegacyPromotionExecution(
        exit_code=1,
        promotion_run_id=promotion_run_id,
        candidate_batch_id=decision.batch_id,
        result_path=result_path,
        latest_promoted_path=latest_promoted_path,
        result_record=result_record,
        latest_promoted_updated=False,
    )


def _build_blocked_execution(
    *,
    result_path: Path,
    promotion_run_id: str,
    latest_promoted_path: Path,
    latest_success_state: dict[str, object] | None,
    previous_batch_id: str | None,
    tenant_id: uuid.UUID,
    schema_name: str,
    source_schema: str,
    promoted_by: str,
    evaluated_at: str,
    blocking_gate: str,
    message: str,
) -> LegacyPromotionExecution:
    decision = PromotionDecision(
        promotion_result=PROMOTION_RESULT_BLOCKED,
        batch_id=_text_value(latest_success_state, "batch_id"),
        previous_batch_id=previous_batch_id,
        evaluated_at=evaluated_at,
        promoted_at=None,
        promoted_by=promoted_by,
        summary_path=_text_value(latest_success_state, "summary_path"),
        validation_status=_text_value(latest_success_state, "validation_status") or "not-run",
        blocking_issue_count=None,
        reconciliation_gap_count=None,
        reconciliation_threshold=None,
        candidate_final_disposition=_text_value(latest_success_state, "final_disposition"),
        promotion_readiness=False,
        analyst_review_required=False,
        blocking_gate=blocking_gate,
        message=message,
    )
    result_record = decision.as_record(
        promotion_run_id=promotion_run_id,
        lane_key=lane_key(
            tenant_id=tenant_id,
            schema_name=schema_name,
            source_schema=source_schema,
        ),
        tenant_id=str(tenant_id),
        schema_name=schema_name,
        source_schema=source_schema,
    )
    _decorate_result_record(result_record, decision=decision, promotion_mode="blocked")
    try:
        write_json_atomically(result_path, result_record)
    except Exception as exc:
        return _build_write_failure_execution(
            result_path=result_path,
            decision=decision,
            promotion_run_id=promotion_run_id,
            tenant_id=tenant_id,
            schema_name=schema_name,
            source_schema=source_schema,
            write_error=exc,
            latest_promoted_path=latest_promoted_path,
        )
    return LegacyPromotionExecution(
        exit_code=1,
        promotion_run_id=promotion_run_id,
        candidate_batch_id=decision.batch_id,
        result_path=result_path,
        latest_promoted_path=latest_promoted_path,
        result_record=result_record,
        latest_promoted_updated=False,
    )


def _validate_promoted_state(
    promoted_state: object | None,
    *,
    tenant_id: uuid.UUID,
    schema_name: str,
    source_schema: str,
) -> tuple[dict[str, object] | None, str | None]:
    if promoted_state is None:
        return None, None
    if not isinstance(promoted_state, Mapping):
        return None, "current promoted state must be a JSON object"
    normalized_state = dict(promoted_state)
    batch_id = _text_value(normalized_state, "batch_id")
    if batch_id is None:
        return None, "current promoted state is missing batch_id"
    promotion_result = _text_value(normalized_state, "promotion_result")
    if promotion_result != PROMOTION_RESULT_PROMOTED:
        rendered_promotion_result = promotion_result or "missing"
        return None, (
            "current promoted state has promotion_result "
            f"{rendered_promotion_result} instead of promoted"
        )
    expected_identity = {
        "tenant_id": str(tenant_id),
        "schema_name": schema_name,
        "source_schema": source_schema,
    }
    mismatches = _lane_identity_mismatches(
        expected_lane_identity=expected_identity,
        lane_state=normalized_state,
        state_name="current promoted state",
    )
    if mismatches:
        return None, "; ".join(mismatches)
    required_text_fields = (
        "promoted_at",
        "promoted_by",
        "summary_path",
        "validation_status",
    )
    for field_name in required_text_fields:
        if _text_value(normalized_state, field_name) is None:
            return None, f"current promoted state is missing {field_name}"
    required_int_fields = (
        "blocking_issue_count",
        "reconciliation_gap_count",
        "reconciliation_threshold",
    )
    for field_name in required_int_fields:
        field_value = normalized_state.get(field_name)
        if not isinstance(field_value, int) or isinstance(field_value, bool) or field_value < 0:
            return None, f"current promoted state has invalid {field_name}"
    return normalized_state, None


def _load_validated_promoted_state(
    *,
    latest_promoted_path: Path,
    tenant_id: uuid.UUID,
    schema_name: str,
    source_schema: str,
) -> tuple[dict[str, object] | None, str | None]:
    promoted_state, promoted_error = read_json_file_with_error(latest_promoted_path)
    if promoted_error is not None:
        return None, promoted_error
    if promoted_state is None and latest_promoted_path.exists():
        return None, "current promoted state must be a JSON object"
    return _validate_promoted_state(
        promoted_state,
        tenant_id=tenant_id,
        schema_name=schema_name,
        source_schema=source_schema,
    )


def _load_json_object_with_error(
    path: Path | None,
    *,
    subject: str,
) -> tuple[dict[str, object] | None, str | None]:
    if path is None:
        return None, None
    payload, payload_error = read_json_file_with_error(path)
    if payload_error is not None:
        return None, payload_error
    if payload is None and path.exists():
        return None, f"{subject} must be a JSON object"
    if payload is not None and not isinstance(payload, Mapping):
        return None, f"{subject} must be a JSON object"
    if payload is None:
        return None, None
    return dict(payload), None


def _print_operator_summary(result: LegacyPromotionExecution) -> None:
    print(f"Promotion run id: {result.promotion_run_id}")
    print(f"Candidate batch: {result.candidate_batch_id or 'none'}")
    print(
        f"Promotion result: {result.result_record['promotion_result']} "
        f"(exit={result.exit_code})"
    )
    print(
        "Policy classification: "
        f"{result.result_record.get('promotion_policy_classification', 'unknown')}"
    )
    if result.result_record.get("blocking_gate"):
        print(f"Blocking gate: {result.result_record['blocking_gate']}")
    if result.result_record.get("override_record_path"):
        print(f"Override record: {result.result_record['override_record_path']}")
    print(f"Message: {result.result_record['message']}")
    print(f"Summary artifact: {result.result_record.get('summary_path') or 'not-available'}")
    print(f"Latest promoted state: {result.latest_promoted_path}")
    print(
        "Promotion result artifact: "
        f"{result.result_path if result.result_path is not None else 'not-written'}"
    )


async def run_legacy_promotion(
    *,
    tenant_id: uuid.UUID,
    schema_name: str,
    source_schema: str,
    summary_root: Path | None = None,
    state_root: Path | None = None,
    promoted_by: str = DEFAULT_PROMOTED_BY,
    allow_exception_override: bool = False,
    override_rationale: str | None = None,
    override_scope: str | None = None,
) -> LegacyPromotionExecution:
    promoted_by = _normalize_promoted_by(promoted_by)
    if allow_exception_override:
        override_rationale = _require_override_text(
            override_rationale,
            field_name="override_rationale",
        )
        override_scope = _require_override_text(
            override_scope,
            field_name="override_scope",
        )
        promoted_by = _require_override_actor(promoted_by)
    elif override_rationale is not None or override_scope is not None:
        raise ValueError(
            "allow_exception_override must be enabled when override metadata is provided"
        )

    resolved_summary_root = summary_root or DEFAULT_SUMMARY_ROOT
    lane_paths = build_lane_state_paths(
        tenant_id=tenant_id,
        schema_name=schema_name,
        source_schema=source_schema,
        summary_root=resolved_summary_root,
        state_root=state_root,
    )
    evaluation_time = utc_now()
    evaluated_at = evaluation_time.isoformat()
    promotion_run_id = str(uuid.uuid4())

    try:
        write_lock_file_with_recovery(
            lane_paths.promotion_lock_path,
            {
                "promotion_run_id": promotion_run_id,
                "acquired_at": evaluated_at,
                "tenant_id": str(tenant_id),
                "schema_name": schema_name,
                "source_schema": source_schema,
            },
            now=evaluation_time,
        )
    except FileExistsError:
        latest_success_state = read_json_file(lane_paths.latest_success_path)
        result_path = _promotion_result_path(
            result_root=lane_paths.promotion_results_root,
            batch_id=_text_value(latest_success_state, "batch_id"),
            promotion_run_id=promotion_run_id,
        )
        return _build_blocked_execution(
            result_path=result_path,
            promotion_run_id=promotion_run_id,
            latest_promoted_path=lane_paths.latest_promoted_path,
            latest_success_state=latest_success_state,
            previous_batch_id=None,
            tenant_id=tenant_id,
            schema_name=schema_name,
            source_schema=source_schema,
            promoted_by=promoted_by,
            evaluated_at=evaluated_at,
            blocking_gate="promotion-in-progress",
            message=(
                "Another promotion run already holds the lane lock. Wait for it to finish "
                "before retrying automatic promotion."
            ),
        )

    try:
        recover_stale_lock(lane_paths.lock_path, now=evaluation_time)
        latest_success_state, latest_success_error = _load_json_object_with_error(
            lane_paths.latest_success_path,
            subject="latest successful shadow batch state",
        )
        previous_latest_promoted, latest_promoted_error = _load_validated_promoted_state(
            latest_promoted_path=lane_paths.latest_promoted_path,
            tenant_id=tenant_id,
            schema_name=schema_name,
            source_schema=source_schema,
        )
        result_path = _promotion_result_path(
            result_root=lane_paths.promotion_results_root,
            batch_id=_text_value(latest_success_state, "batch_id"),
            promotion_run_id=promotion_run_id,
        )
        if latest_success_error is not None:
            return _build_blocked_execution(
                result_path=result_path,
                promotion_run_id=promotion_run_id,
                latest_promoted_path=lane_paths.latest_promoted_path,
                latest_success_state=latest_success_state,
                previous_batch_id=_text_value(previous_latest_promoted, "batch_id"),
                tenant_id=tenant_id,
                schema_name=schema_name,
                source_schema=source_schema,
                promoted_by=promoted_by,
                evaluated_at=evaluated_at,
                blocking_gate="invalid-candidate-state",
                message=(
                    "The latest successful shadow batch state is invalid and must be repaired "
                    f"before automatic promotion can continue: {latest_success_error}"
                ),
            )
        if latest_promoted_error is not None:
            return _build_invalid_promoted_state_execution(
                result_path=result_path,
                promotion_run_id=promotion_run_id,
                latest_promoted_path=lane_paths.latest_promoted_path,
                latest_success_state=latest_success_state,
                tenant_id=tenant_id,
                schema_name=schema_name,
                source_schema=source_schema,
                promoted_by=promoted_by,
                evaluated_at=evaluated_at,
                error_message=latest_promoted_error,
            )
        summary_path = None
        if isinstance(latest_success_state, Mapping):
            summary_path_value = latest_success_state.get("summary_path")
            if summary_path_value is not None:
                summary_path = Path(str(summary_path_value))
        summary, summary_error = _load_json_object_with_error(
            summary_path,
            subject="candidate summary artifact",
        )
        if summary_error is not None:
            return _build_blocked_execution(
                result_path=result_path,
                promotion_run_id=promotion_run_id,
                latest_promoted_path=lane_paths.latest_promoted_path,
                latest_success_state=latest_success_state,
                previous_batch_id=_text_value(previous_latest_promoted, "batch_id"),
                tenant_id=tenant_id,
                schema_name=schema_name,
                source_schema=source_schema,
                promoted_by=promoted_by,
                evaluated_at=evaluated_at,
                blocking_gate="invalid-summary-artifact",
                message=(
                    "The candidate summary artifact is invalid and must be repaired before "
                    f"automatic promotion can continue: {summary_error}"
                ),
            )

        decision = evaluate_promotion(
            latest_success_state=latest_success_state,
            summary=summary,
            latest_promoted_state=previous_latest_promoted,
            expected_lane_identity={
                "tenant_id": str(tenant_id),
                "schema_name": schema_name,
                "source_schema": source_schema,
            },
            promoted_by=promoted_by,
            evaluated_at=evaluated_at,
            lock_active=lane_paths.lock_path.exists(),
        )
        comparison_decision = decision
        override_record_path: Path | None = None
        override_record: dict[str, object] | None = None
        if (
            decision.promotion_result == PROMOTION_RESULT_BLOCKED
            and decision.blocking_gate == "analyst-review"
            and allow_exception_override
        ):
            override_record_path = _promotion_override_path(
                overrides_root=lane_paths.promotion_overrides_root,
                batch_id=decision.batch_id,
                promotion_run_id=promotion_run_id,
            )
            override_record = {
                "state_version": 1,
                "promotion_run_id": promotion_run_id,
                "lane_key": lane_key(
                    tenant_id=tenant_id,
                    schema_name=schema_name,
                    source_schema=source_schema,
                ),
                "tenant_id": str(tenant_id),
                "schema_name": schema_name,
                "source_schema": source_schema,
                "batch_id": decision.batch_id,
                "summary_path": decision.summary_path,
                "policy_classification": EXCEPTION_REQUIRED_CLASSIFICATION,
                "reason_codes": ["analyst-review"],
                "approved_by": promoted_by,
                "approved_at": evaluated_at,
                "override_rationale": override_rationale,
                "override_scope": override_scope,
            }
            decision = PromotionDecision(
                promotion_result=PROMOTION_RESULT_PROMOTED,
                batch_id=decision.batch_id,
                previous_batch_id=decision.previous_batch_id,
                evaluated_at=decision.evaluated_at,
                promoted_at=decision.evaluated_at,
                promoted_by=promoted_by,
                summary_path=decision.summary_path,
                validation_status=decision.validation_status,
                blocking_issue_count=decision.blocking_issue_count,
                reconciliation_gap_count=decision.reconciliation_gap_count,
                reconciliation_threshold=decision.reconciliation_threshold,
                candidate_final_disposition=decision.candidate_final_disposition,
                promotion_readiness=decision.promotion_readiness,
                analyst_review_required=True,
                blocking_gate=None,
                message=(
                    f"Batch {decision.batch_id} advanced via operator exception override "
                    f"by {promoted_by}."
                ),
            )
        comparison_record = comparison_decision.as_record(
            promotion_run_id=promotion_run_id,
            lane_key=lane_key(
                tenant_id=tenant_id,
                schema_name=schema_name,
                source_schema=source_schema,
            ),
            tenant_id=str(tenant_id),
            schema_name=schema_name,
            source_schema=source_schema,
        )
        result_record = decision.as_record(
            promotion_run_id=promotion_run_id,
            lane_key=lane_key(
                tenant_id=tenant_id,
                schema_name=schema_name,
                source_schema=source_schema,
            ),
            tenant_id=str(tenant_id),
            schema_name=schema_name,
            source_schema=source_schema,
        )
        _decorate_result_record(
            result_record,
            decision=decision,
            promotion_mode=(
                "exception-override"
                if override_record is not None
                else _promotion_mode(decision)
            ),
            override_applied=override_record is not None,
            override_record_path=override_record_path,
            override_rationale=override_rationale if override_record is not None else None,
            override_scope=override_scope if override_record is not None else None,
        )
        result_path = _promotion_result_path(
            result_root=lane_paths.promotion_results_root,
            batch_id=decision.batch_id,
            promotion_run_id=promotion_run_id,
        )

        commit_lock_acquired = False
        try:
            if decision.promotion_result in {
                PROMOTION_RESULT_PROMOTED,
                PROMOTION_RESULT_NOOP,
            }:
                try:
                    write_lock_file_with_recovery(
                        lane_paths.lock_path,
                        {
                            "promotion_run_id": promotion_run_id,
                            "acquired_at": evaluated_at,
                            "mode": (
                                "promotion-commit"
                                if decision.promotion_result == PROMOTION_RESULT_PROMOTED
                                else "promotion-noop-check"
                            ),
                        },
                        now=utc_now(),
                    )
                except FileExistsError:
                    return _build_blocked_execution(
                        result_path=result_path,
                        promotion_run_id=promotion_run_id,
                        latest_promoted_path=lane_paths.latest_promoted_path,
                        latest_success_state=latest_success_state,
                        previous_batch_id=_text_value(previous_latest_promoted, "batch_id"),
                        tenant_id=tenant_id,
                        schema_name=schema_name,
                        source_schema=source_schema,
                        promoted_by=promoted_by,
                        evaluated_at=evaluated_at,
                        blocking_gate="lane-unstable",
                        message=(
                            "The lane is currently locked by the scheduler. Re-run promotion "
                            "after the refresh lock clears."
                        ),
                    )
                commit_lock_acquired = True

                # Both PROMOTED and NOOP re-validate the promoted pointer under lock.
                current_latest_promoted, current_promoted_error = _load_validated_promoted_state(
                    latest_promoted_path=lane_paths.latest_promoted_path,
                    tenant_id=tenant_id,
                    schema_name=schema_name,
                    source_schema=source_schema,
                )
                if current_promoted_error is not None:
                    return _build_invalid_promoted_state_execution(
                        result_path=result_path,
                        promotion_run_id=promotion_run_id,
                        latest_promoted_path=lane_paths.latest_promoted_path,
                        latest_success_state=latest_success_state,
                        tenant_id=tenant_id,
                        schema_name=schema_name,
                        source_schema=source_schema,
                        promoted_by=promoted_by,
                        evaluated_at=evaluated_at,
                        error_message=current_promoted_error,
                    )
                if current_latest_promoted != previous_latest_promoted:
                    return _build_blocked_execution(
                        result_path=result_path,
                        promotion_run_id=promotion_run_id,
                        latest_promoted_path=lane_paths.latest_promoted_path,
                        latest_success_state=latest_success_state,
                        previous_batch_id=_text_value(current_latest_promoted, "batch_id"),
                        tenant_id=tenant_id,
                        schema_name=schema_name,
                        source_schema=source_schema,
                        promoted_by=promoted_by,
                        evaluated_at=evaluated_at,
                        blocking_gate="promoted-state-changed",
                        message=(
                            "The current promoted pointer changed while promotion was being "
                            "finalized. Re-run promotion against the live working-lane state."
                        ),
                    )

            if decision.promotion_result in {
                PROMOTION_RESULT_PROMOTED,
                PROMOTION_RESULT_NOOP,
            }:
                (
                    refreshed_latest_success,
                    refreshed_latest_success_error,
                ) = _load_json_object_with_error(
                    lane_paths.latest_success_path,
                    subject="latest successful shadow batch state",
                )
                if refreshed_latest_success_error is not None:
                    return _build_blocked_execution(
                        result_path=result_path,
                        promotion_run_id=promotion_run_id,
                        latest_promoted_path=lane_paths.latest_promoted_path,
                        latest_success_state=refreshed_latest_success,
                        previous_batch_id=_text_value(previous_latest_promoted, "batch_id"),
                        tenant_id=tenant_id,
                        schema_name=schema_name,
                        source_schema=source_schema,
                        promoted_by=promoted_by,
                        evaluated_at=evaluated_at,
                        blocking_gate="invalid-candidate-state",
                        message=(
                            "The latest successful shadow batch state became invalid while "
                            "promotion "
                            f"was being finalized: {refreshed_latest_success_error}"
                        ),
                    )
                refreshed_summary_path = None
                if isinstance(refreshed_latest_success, Mapping):
                    refreshed_summary_path_value = refreshed_latest_success.get("summary_path")
                    if refreshed_summary_path_value is not None:
                        refreshed_summary_path = Path(str(refreshed_summary_path_value))
                refreshed_summary, refreshed_summary_error = _load_json_object_with_error(
                    refreshed_summary_path,
                    subject="candidate summary artifact",
                )
                if refreshed_summary_error is not None:
                    return _build_blocked_execution(
                        result_path=result_path,
                        promotion_run_id=promotion_run_id,
                        latest_promoted_path=lane_paths.latest_promoted_path,
                        latest_success_state=refreshed_latest_success,
                        previous_batch_id=_text_value(previous_latest_promoted, "batch_id"),
                        tenant_id=tenant_id,
                        schema_name=schema_name,
                        source_schema=source_schema,
                        promoted_by=promoted_by,
                        evaluated_at=evaluated_at,
                        blocking_gate="invalid-summary-artifact",
                        message=(
                            "The candidate summary artifact became invalid while promotion "
                            "was being "
                            f"finalized: {refreshed_summary_error}"
                        ),
                    )
                refreshed_decision = evaluate_promotion(
                    latest_success_state=refreshed_latest_success,
                    summary=refreshed_summary,
                    latest_promoted_state=previous_latest_promoted,
                    expected_lane_identity={
                        "tenant_id": str(tenant_id),
                        "schema_name": schema_name,
                        "source_schema": source_schema,
                    },
                    promoted_by=promoted_by,
                    evaluated_at=evaluated_at,
                    lock_active=False,
                )
                refreshed_record = refreshed_decision.as_record(
                    promotion_run_id=promotion_run_id,
                    lane_key=lane_key(
                        tenant_id=tenant_id,
                        schema_name=schema_name,
                        source_schema=source_schema,
                    ),
                    tenant_id=str(tenant_id),
                    schema_name=schema_name,
                    source_schema=source_schema,
                )
                if refreshed_record != comparison_record:
                    return _build_blocked_execution(
                        result_path=result_path,
                        promotion_run_id=promotion_run_id,
                        latest_promoted_path=lane_paths.latest_promoted_path,
                        latest_success_state=refreshed_latest_success,
                        previous_batch_id=_text_value(previous_latest_promoted, "batch_id"),
                        tenant_id=tenant_id,
                        schema_name=schema_name,
                        source_schema=source_schema,
                        promoted_by=promoted_by,
                        evaluated_at=evaluated_at,
                        blocking_gate="candidate-state-changed",
                        message=(
                            "The latest successful shadow batch changed while promotion was "
                            "being evaluated. Re-run promotion against the current candidate."
                        ),
                    )

            if decision.promotion_result == PROMOTION_RESULT_NOOP:
                try:
                    write_json_atomically(result_path, result_record)
                except Exception as exc:
                    return _build_write_failure_execution(
                        result_path=result_path,
                        decision=decision,
                        promotion_run_id=promotion_run_id,
                        tenant_id=tenant_id,
                        schema_name=schema_name,
                        source_schema=source_schema,
                        write_error=exc,
                        latest_promoted_path=lane_paths.latest_promoted_path,
                    )
                return LegacyPromotionExecution(
                    exit_code=0,
                    promotion_run_id=promotion_run_id,
                    candidate_batch_id=decision.batch_id,
                    result_path=result_path,
                    latest_promoted_path=lane_paths.latest_promoted_path,
                    result_record=result_record,
                    latest_promoted_updated=False,
                )

            if decision.promotion_result == PROMOTION_RESULT_PROMOTED:
                if override_record is not None and override_record_path is not None:
                    try:
                        write_json_atomically(override_record_path, override_record)
                    except Exception as exc:
                        return _build_write_failure_execution(
                            result_path=result_path,
                            decision=decision,
                            promotion_run_id=promotion_run_id,
                            tenant_id=tenant_id,
                            schema_name=schema_name,
                            source_schema=source_schema,
                            write_error=exc,
                            latest_promoted_path=lane_paths.latest_promoted_path,
                            cleanup_override_path=override_record_path,
                        )
                try:
                    write_json_atomically(result_path, result_record)
                except Exception as exc:
                    return _build_write_failure_execution(
                        result_path=result_path,
                        decision=decision,
                        promotion_run_id=promotion_run_id,
                        tenant_id=tenant_id,
                        schema_name=schema_name,
                        source_schema=source_schema,
                        write_error=exc,
                        latest_promoted_path=lane_paths.latest_promoted_path,
                        cleanup_result_path=result_path,
                        cleanup_override_path=override_record_path,
                    )

                try:
                    write_json_atomically(lane_paths.latest_promoted_path, result_record)
                except Exception as exc:
                    return _build_write_failure_execution(
                        result_path=result_path,
                        decision=decision,
                        promotion_run_id=promotion_run_id,
                        tenant_id=tenant_id,
                        schema_name=schema_name,
                        source_schema=source_schema,
                        write_error=exc,
                        latest_promoted_path=lane_paths.latest_promoted_path,
                        cleanup_result_path=result_path,
                        cleanup_override_path=override_record_path,
                    )

                return LegacyPromotionExecution(
                    exit_code=0,
                    promotion_run_id=promotion_run_id,
                    candidate_batch_id=decision.batch_id,
                    result_path=result_path,
                    latest_promoted_path=lane_paths.latest_promoted_path,
                    result_record=result_record,
                    latest_promoted_updated=True,
                )

            try:
                write_json_atomically(result_path, result_record)
            except Exception as exc:
                return _build_write_failure_execution(
                    result_path=result_path,
                    decision=decision,
                    promotion_run_id=promotion_run_id,
                    tenant_id=tenant_id,
                    schema_name=schema_name,
                    source_schema=source_schema,
                    write_error=exc,
                    latest_promoted_path=lane_paths.latest_promoted_path,
                )
            return LegacyPromotionExecution(
                exit_code=0 if decision.promotion_result == PROMOTION_RESULT_NOOP else 1,
                promotion_run_id=promotion_run_id,
                candidate_batch_id=decision.batch_id,
                result_path=result_path,
                latest_promoted_path=lane_paths.latest_promoted_path,
                result_record=result_record,
                latest_promoted_updated=False,
            )
        finally:
            if commit_lock_acquired:
                remove_file_if_exists(lane_paths.lock_path)
    finally:
        remove_file_if_exists(lane_paths.promotion_lock_path)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    result = asyncio.run(
        run_legacy_promotion(
            tenant_id=args.tenant_id,
            schema_name=args.schema,
            source_schema=args.source_schema,
            promoted_by=args.promoted_by,
            allow_exception_override=args.allow_exception_override,
            override_rationale=args.override_rationale,
            override_scope=args.override_scope,
        )
    )
    _print_operator_summary(result)
    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main())