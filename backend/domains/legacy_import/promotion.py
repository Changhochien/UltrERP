"""Promotion decision logic for moving a shadow batch into the working lane."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from domains.legacy_import.promotion_policy import (
    PromotionPolicyClassification,
    evaluate_promotion_policy,
)

PROMOTION_RESULT_PROMOTED = "promoted"
PROMOTION_RESULT_BLOCKED = "blocked"
PROMOTION_RESULT_NOOP = "noop"

SUCCESSFUL_REFRESH_DISPOSITIONS = frozenset({"completed", "completed-review-required"})
STRUCTURAL_BLOCKING_GATES = frozenset(
    {
        "missing-candidate-state",
        "missing-candidate-batch-id",
        "invalid-candidate-state",
        "candidate-lane-mismatch",
        "candidate-not-successful",
        "missing-summary-path",
        "missing-summary-artifact",
        "candidate-summary-mismatch",
        "invalid-summary-artifact",
    }
)


def _as_text(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _as_int(value: object | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError("boolean values are not valid integers")
    if isinstance(value, int):
        parsed = value
    elif isinstance(value, str):
        parsed = int(value.strip())
    else:
        raise ValueError("value is not a valid integer")
    if parsed < 0:
        raise ValueError("negative values are not valid counts")
    return parsed


def _as_bool(value: object | None) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "on"}:
            return True
        if normalized in {"false", "0", "no", "off", ""}:
            return False
    return bool(value)


def _coerce_bool(value: object | None) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in {0, 1}:
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "on"}:
            return True
        if normalized in {"false", "0", "no", "off"}:
            return False
    raise ValueError("value is not a valid boolean")


def _mapping(value: object | None) -> Mapping[str, object]:
    if isinstance(value, Mapping):
        return value
    return {}


def _mapping_text(mapping: Mapping[str, object], key: str) -> str | None:
    if key not in mapping:
        return None
    return _as_text(mapping.get(key))


def _mapping_bool(mapping: Mapping[str, object], key: str) -> bool | None:
    if key not in mapping:
        return None
    return _as_bool(mapping.get(key))


def _mapping_int(
    mapping: Mapping[str, object],
    key: str,
    *,
    source_name: str,
    errors: list[str],
) -> int | None:
    if key not in mapping:
        return None
    try:
        return _as_int(mapping.get(key))
    except (TypeError, ValueError):
        errors.append(f"{source_name}.{key} must be an integer")
        return None


def _mapping_flag(
    mapping: Mapping[str, object],
    key: str,
    *,
    source_name: str,
    errors: list[str],
) -> bool | None:
    if key not in mapping:
        return None
    try:
        return _coerce_bool(mapping.get(key))
    except (TypeError, ValueError):
        errors.append(f"{source_name}.{key} must be a boolean")
        return None


def _summary_identity_mismatches(
    candidate_state: Mapping[str, object],
    summary_payload: Mapping[str, object],
) -> list[str]:
    mismatches: list[str] = []
    for field_name in ("tenant_id", "schema_name", "source_schema"):
        candidate_value = _mapping_text(candidate_state, field_name)
        summary_value = _mapping_text(summary_payload, field_name)
        if candidate_value is None:
            mismatches.append(f"{field_name} missing from candidate state")
            continue
        if summary_value != candidate_value:
            rendered_summary_value = summary_value or "missing"
            mismatches.append(
                f"{field_name} expected {candidate_value} but summary has {rendered_summary_value}"
            )
    return mismatches


def _lane_identity_mismatches(
    expected_lane_identity: Mapping[str, object],
    lane_state: Mapping[str, object],
    *,
    state_name: str,
) -> list[str]:
    mismatches: list[str] = []
    for field_name in ("tenant_id", "schema_name", "source_schema"):
        expected_value = _mapping_text(expected_lane_identity, field_name)
        if expected_value is None:
            continue
        lane_value = _mapping_text(lane_state, field_name)
        if lane_value != expected_value:
            rendered_lane_value = lane_value or "missing"
            mismatches.append(
                f"{field_name} expected {expected_value} but {state_name} has "
                f"{rendered_lane_value}"
            )
    return mismatches


@dataclass(slots=True, frozen=True)
class PromotionDecision:
    promotion_result: str
    batch_id: str | None
    previous_batch_id: str | None
    evaluated_at: str
    promoted_at: str | None
    promoted_by: str
    summary_path: str | None
    validation_status: str
    blocking_issue_count: int | None
    reconciliation_gap_count: int | None
    reconciliation_threshold: int | None
    candidate_final_disposition: str | None
    promotion_readiness: bool
    analyst_review_required: bool
    blocking_gate: str | None
    message: str

    def _policy_classification(self) -> str:
        if self.blocking_gate == "analyst-review":
            return PromotionPolicyClassification.EXCEPTION_REQUIRED.value
        if self.promotion_result in {PROMOTION_RESULT_PROMOTED, PROMOTION_RESULT_NOOP}:
            return PromotionPolicyClassification.ELIGIBLE.value
        return PromotionPolicyClassification.BLOCKED.value

    def as_record(
        self,
        *,
        promotion_run_id: str,
        lane_key: str,
        tenant_id: str,
        schema_name: str,
        source_schema: str,
    ) -> dict[str, Any]:
        return {
            "state_version": 1,
            "promotion_run_id": promotion_run_id,
            "lane_key": lane_key,
            "tenant_id": tenant_id,
            "schema_name": schema_name,
            "source_schema": source_schema,
            "batch_id": self.batch_id,
            "previous_batch_id": self.previous_batch_id,
            "evaluated_at": self.evaluated_at,
            "promoted_at": self.promoted_at,
            "promoted_by": self.promoted_by,
            "summary_path": self.summary_path,
            "validation_status": self.validation_status,
            "blocking_issue_count": self.blocking_issue_count,
            "reconciliation_gap_count": self.reconciliation_gap_count,
            "reconciliation_threshold": self.reconciliation_threshold,
            "candidate_final_disposition": self.candidate_final_disposition,
            "promotion_readiness": self.promotion_readiness,
            "analyst_review_required": self.analyst_review_required,
            "promotion_result": self.promotion_result,
            "blocking_gate": self.blocking_gate,
            "promotion_policy_classification": self._policy_classification(),
            "promotion_policy_reason_codes": (
                [self.blocking_gate] if self.blocking_gate is not None else []
            ),
            "override_allowed": self.blocking_gate == "analyst-review",
            "message": self.message,
        }


def _decision(
    *,
    promotion_result: str,
    batch_id: str | None,
    previous_batch_id: str | None,
    evaluated_at: str,
    promoted_by: str,
    summary_path: str | None,
    validation_status: str,
    blocking_issue_count: int | None,
    reconciliation_gap_count: int | None,
    reconciliation_threshold: int | None,
    candidate_final_disposition: str | None,
    promotion_readiness: bool,
    analyst_review_required: bool,
    blocking_gate: str | None,
    message: str,
) -> PromotionDecision:
    return PromotionDecision(
        promotion_result=promotion_result,
        batch_id=batch_id,
        previous_batch_id=previous_batch_id,
        evaluated_at=evaluated_at,
        promoted_at=evaluated_at if promotion_result == PROMOTION_RESULT_PROMOTED else None,
        promoted_by=promoted_by,
        summary_path=summary_path,
        validation_status=validation_status,
        blocking_issue_count=blocking_issue_count,
        reconciliation_gap_count=reconciliation_gap_count,
        reconciliation_threshold=reconciliation_threshold,
        candidate_final_disposition=candidate_final_disposition,
        promotion_readiness=promotion_readiness,
        analyst_review_required=analyst_review_required,
        blocking_gate=blocking_gate,
        message=message,
    )


def evaluate_promotion(
    *,
    latest_success_state: Mapping[str, object] | None,
    summary: Mapping[str, object] | None,
    latest_promoted_state: Mapping[str, object] | None,
    expected_lane_identity: Mapping[str, object] | None = None,
    promoted_by: str,
    evaluated_at: str,
    lock_active: bool,
) -> PromotionDecision:
    candidate_state = _mapping(latest_success_state)
    promoted_state = _mapping(latest_promoted_state)
    summary_payload = _mapping(summary)

    previous_batch_id = _as_text(promoted_state.get("batch_id"))
    batch_id = _as_text(candidate_state.get("batch_id"))
    summary_path = _as_text(candidate_state.get("summary_path"))
    validation_status = _as_text(candidate_state.get("validation_status")) or "not-run"
    candidate_state_errors: list[str] = []
    blocking_issue_count = _mapping_int(
        candidate_state,
        "blocking_issue_count",
        source_name="latest-success",
        errors=candidate_state_errors,
    )
    reconciliation_gap_count = _mapping_int(
        candidate_state,
        "reconciliation_gap_count",
        source_name="latest-success",
        errors=candidate_state_errors,
    )
    reconciliation_threshold = _mapping_int(
        candidate_state,
        "reconciliation_threshold",
        source_name="latest-success",
        errors=candidate_state_errors,
    )
    candidate_final_disposition = _as_text(candidate_state.get("final_disposition"))
    promotion_readiness = _mapping_flag(
        candidate_state,
        "promotion_readiness",
        source_name="latest-success",
        errors=candidate_state_errors,
    )
    promotion_readiness = promotion_readiness if promotion_readiness is not None else False
    analyst_review_required = _mapping_flag(
        candidate_state,
        "analyst_review_required",
        source_name="latest-success",
        errors=candidate_state_errors,
    )
    analyst_review_required = (
        analyst_review_required if analyst_review_required is not None else False
    )

    if not candidate_state:
        return _decision(
            promotion_result=PROMOTION_RESULT_BLOCKED,
            batch_id=None,
            previous_batch_id=previous_batch_id,
            evaluated_at=evaluated_at,
            promoted_by=promoted_by,
            summary_path=None,
            validation_status="not-run",
            blocking_issue_count=None,
            reconciliation_gap_count=None,
            reconciliation_threshold=None,
            candidate_final_disposition=None,
            promotion_readiness=False,
            analyst_review_required=False,
            blocking_gate="missing-candidate-state",
            message="No latest successful shadow batch state exists for this lane.",
        )

    if not batch_id:
        return _decision(
            promotion_result=PROMOTION_RESULT_BLOCKED,
            batch_id=None,
            previous_batch_id=previous_batch_id,
            evaluated_at=evaluated_at,
            promoted_by=promoted_by,
            summary_path=summary_path,
            validation_status=validation_status,
            blocking_issue_count=blocking_issue_count,
            reconciliation_gap_count=reconciliation_gap_count,
            reconciliation_threshold=reconciliation_threshold,
            candidate_final_disposition=candidate_final_disposition,
            promotion_readiness=promotion_readiness,
            analyst_review_required=analyst_review_required,
            blocking_gate="missing-candidate-batch-id",
            message="The latest successful shadow batch state does not include a batch id.",
        )

    if candidate_state_errors:
        return _decision(
            promotion_result=PROMOTION_RESULT_BLOCKED,
            batch_id=batch_id,
            previous_batch_id=previous_batch_id,
            evaluated_at=evaluated_at,
            promoted_by=promoted_by,
            summary_path=summary_path,
            validation_status=validation_status,
            blocking_issue_count=None,
            reconciliation_gap_count=None,
            reconciliation_threshold=None,
            candidate_final_disposition=candidate_final_disposition,
            promotion_readiness=False,
            analyst_review_required=analyst_review_required,
            blocking_gate="invalid-candidate-state",
            message=(
                f"Batch {batch_id} cannot be promoted because its candidate lane state "
                + "; ".join(candidate_state_errors)
                + "."
            ),
        )

    lane_identity_mismatches = _lane_identity_mismatches(
        _mapping(expected_lane_identity),
        candidate_state,
        state_name="candidate state",
    )
    if lane_identity_mismatches:
        return _decision(
            promotion_result=PROMOTION_RESULT_BLOCKED,
            batch_id=batch_id,
            previous_batch_id=previous_batch_id,
            evaluated_at=evaluated_at,
            promoted_by=promoted_by,
            summary_path=summary_path,
            validation_status=validation_status,
            blocking_issue_count=blocking_issue_count,
            reconciliation_gap_count=reconciliation_gap_count,
            reconciliation_threshold=reconciliation_threshold,
            candidate_final_disposition=candidate_final_disposition,
            promotion_readiness=False,
            analyst_review_required=analyst_review_required,
            blocking_gate="candidate-lane-mismatch",
            message=(
                f"Batch {batch_id} cannot be promoted because its candidate lane state "
                + "; ".join(lane_identity_mismatches)
                + "."
            ),
        )

    promoted_state_identity_mismatches = _lane_identity_mismatches(
        _mapping(expected_lane_identity),
        promoted_state,
        state_name="current promoted state",
    )
    if promoted_state and promoted_state_identity_mismatches:
        return _decision(
            promotion_result=PROMOTION_RESULT_BLOCKED,
            batch_id=batch_id,
            previous_batch_id=previous_batch_id,
            evaluated_at=evaluated_at,
            promoted_by=promoted_by,
            summary_path=summary_path,
            validation_status=validation_status,
            blocking_issue_count=blocking_issue_count,
            reconciliation_gap_count=reconciliation_gap_count,
            reconciliation_threshold=reconciliation_threshold,
            candidate_final_disposition=candidate_final_disposition,
            promotion_readiness=False,
            analyst_review_required=analyst_review_required,
            blocking_gate="invalid-promoted-state",
            message=(
                f"Batch {batch_id} cannot be promoted because the current promoted state "
                + "; ".join(promoted_state_identity_mismatches)
                + "."
            ),
        )

    policy_decision = evaluate_promotion_policy(
        latest_success_state=candidate_state,
        summary=summary_payload,
        expected_lane_identity=expected_lane_identity,
        lock_active=lock_active,
    )
    batch_id = policy_decision.batch_id
    validation_status = policy_decision.validation_status
    blocking_issue_count = policy_decision.blocking_issue_count
    reconciliation_gap_count = policy_decision.reconciliation_gap_count
    reconciliation_threshold = policy_decision.reconciliation_threshold
    candidate_final_disposition = policy_decision.candidate_final_disposition
    promotion_readiness = policy_decision.promotion_readiness
    analyst_review_required = policy_decision.analyst_review_required
    blocking_gate = policy_decision.reason_codes[0] if policy_decision.reason_codes else None

    if previous_batch_id == batch_id and blocking_gate not in STRUCTURAL_BLOCKING_GATES:
        return _decision(
            promotion_result=PROMOTION_RESULT_NOOP,
            batch_id=batch_id,
            previous_batch_id=previous_batch_id,
            evaluated_at=evaluated_at,
            promoted_by=promoted_by,
            summary_path=summary_path,
            validation_status=validation_status,
            blocking_issue_count=blocking_issue_count,
            reconciliation_gap_count=reconciliation_gap_count,
            reconciliation_threshold=reconciliation_threshold,
            candidate_final_disposition=candidate_final_disposition,
            promotion_readiness=promotion_readiness,
            analyst_review_required=analyst_review_required,
            blocking_gate=None,
            message=f"Batch {batch_id} is already the active promoted working batch.",
        )

    if policy_decision.classification != PromotionPolicyClassification.ELIGIBLE:
        return _decision(
            promotion_result=PROMOTION_RESULT_BLOCKED,
            batch_id=batch_id,
            previous_batch_id=previous_batch_id,
            evaluated_at=evaluated_at,
            promoted_by=promoted_by,
            summary_path=summary_path,
            validation_status=validation_status,
            blocking_issue_count=blocking_issue_count,
            reconciliation_gap_count=reconciliation_gap_count,
            reconciliation_threshold=reconciliation_threshold,
            candidate_final_disposition=candidate_final_disposition,
            promotion_readiness=promotion_readiness,
            analyst_review_required=analyst_review_required,
            blocking_gate=blocking_gate,
            message=policy_decision.message,
        )

    return _decision(
        promotion_result=PROMOTION_RESULT_PROMOTED,
        batch_id=batch_id,
        previous_batch_id=previous_batch_id,
        evaluated_at=evaluated_at,
        promoted_by=promoted_by,
        summary_path=summary_path,
        validation_status=validation_status,
        blocking_issue_count=blocking_issue_count,
        reconciliation_gap_count=reconciliation_gap_count,
        reconciliation_threshold=reconciliation_threshold,
        candidate_final_disposition=candidate_final_disposition,
        promotion_readiness=True,
        analyst_review_required=False,
        blocking_gate=None,
        message=(
            f"Batch {batch_id} was promoted to the working lane"
            + (f" from {previous_batch_id}." if previous_batch_id is not None else ".")
        ),
    )