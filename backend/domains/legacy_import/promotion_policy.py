"""Shared promotion-policy classification for legacy shadow batches."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

SUCCESSFUL_REFRESH_DISPOSITIONS = frozenset({"completed", "completed-review-required"})


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
                f"{field_name} expected {expected_value} but {state_name} has {rendered_lane_value}"
            )
    return mismatches


class PromotionPolicyClassification(StrEnum):
    ELIGIBLE = "eligible"
    BLOCKED = "blocked"
    EXCEPTION_REQUIRED = "exception-required"


@dataclass(slots=True, frozen=True)
class PromotionPolicyDecision:
    classification: PromotionPolicyClassification
    reason_codes: tuple[str, ...]
    message: str
    batch_id: str | None
    summary_path: str | None
    validation_status: str
    blocking_issue_count: int | None
    reconciliation_gap_count: int | None
    reconciliation_threshold: int | None
    candidate_final_disposition: str | None
    promotion_readiness: bool
    analyst_review_required: bool
    override_allowed: bool
    gate_details: dict[str, Any]

    def as_record(self) -> dict[str, Any]:
        return {
            "classification": self.classification.value,
            "reason_codes": list(self.reason_codes),
            "message": self.message,
            "batch_id": self.batch_id,
            "summary_path": self.summary_path,
            "validation_status": self.validation_status,
            "blocking_issue_count": self.blocking_issue_count,
            "reconciliation_gap_count": self.reconciliation_gap_count,
            "reconciliation_threshold": self.reconciliation_threshold,
            "candidate_final_disposition": self.candidate_final_disposition,
            "promotion_readiness": self.promotion_readiness,
            "analyst_review_required": self.analyst_review_required,
            "override_allowed": self.override_allowed,
            "gate_details": self.gate_details,
        }


def _gate_details(
    *,
    validation_status: str,
    blocking_issue_count: int | None,
    reconciliation_gap_count: int | None,
    reconciliation_threshold: int | None,
    reconciliation_status: str | None,
    analyst_review_required: bool,
    analyst_review_status: str | None,
    promotion_readiness: bool,
    lock_active: bool,
) -> dict[str, Any]:
    return {
        "validation": {
            "status": validation_status,
            "blocking_issue_count": blocking_issue_count,
        },
        "reconciliation": {
            "status": reconciliation_status or "not-run",
            "gap_count": reconciliation_gap_count,
            "threshold": reconciliation_threshold,
        },
        "analyst_review": {
            "status": analyst_review_status or "not-run",
            "required": analyst_review_required,
        },
        "promotion_readiness": promotion_readiness,
        "lane": {
            "lock_active": lock_active,
        },
    }


def _decision(
    *,
    classification: PromotionPolicyClassification,
    reason_codes: tuple[str, ...],
    message: str,
    batch_id: str | None,
    summary_path: str | None,
    validation_status: str,
    blocking_issue_count: int | None,
    reconciliation_gap_count: int | None,
    reconciliation_threshold: int | None,
    candidate_final_disposition: str | None,
    promotion_readiness: bool,
    analyst_review_required: bool,
    override_allowed: bool,
    analyst_review_status: str | None,
    reconciliation_status: str | None,
    lock_active: bool,
) -> PromotionPolicyDecision:
    return PromotionPolicyDecision(
        classification=classification,
        reason_codes=reason_codes,
        message=message,
        batch_id=batch_id,
        summary_path=summary_path,
        validation_status=validation_status,
        blocking_issue_count=blocking_issue_count,
        reconciliation_gap_count=reconciliation_gap_count,
        reconciliation_threshold=reconciliation_threshold,
        candidate_final_disposition=candidate_final_disposition,
        promotion_readiness=promotion_readiness,
        analyst_review_required=analyst_review_required,
        override_allowed=override_allowed,
        gate_details=_gate_details(
            validation_status=validation_status,
            blocking_issue_count=blocking_issue_count,
            reconciliation_gap_count=reconciliation_gap_count,
            reconciliation_threshold=reconciliation_threshold,
            reconciliation_status=reconciliation_status,
            analyst_review_required=analyst_review_required,
            analyst_review_status=analyst_review_status,
            promotion_readiness=promotion_readiness,
            lock_active=lock_active,
        ),
    )


def evaluate_overlap_policy(
    *,
    batch_id: str,
    reconciliation_threshold: int,
) -> PromotionPolicyDecision:
    return _decision(
        classification=PromotionPolicyClassification.BLOCKED,
        reason_codes=("lane-unstable",),
        message=(
            f"Batch {batch_id} cannot be promoted while the lane still has "
            "an active scheduler lock."
        ),
        batch_id=batch_id,
        summary_path=None,
        validation_status="not-run",
        blocking_issue_count=0,
        reconciliation_gap_count=None,
        reconciliation_threshold=reconciliation_threshold,
        candidate_final_disposition=None,
        promotion_readiness=False,
        analyst_review_required=False,
        override_allowed=False,
        analyst_review_status=None,
        reconciliation_status=None,
        lock_active=True,
    )


def evaluate_promotion_policy(
    *,
    latest_success_state: Mapping[str, object] | None,
    summary: Mapping[str, object] | None,
    expected_lane_identity: Mapping[str, object] | None = None,
    lock_active: bool,
) -> PromotionPolicyDecision:
    candidate_state = _mapping(latest_success_state)
    summary_payload = _mapping(summary)

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
    if promotion_readiness is None:
        promotion_readiness = False
    analyst_review_required = _mapping_flag(
        candidate_state,
        "analyst_review_required",
        source_name="latest-success",
        errors=candidate_state_errors,
    )
    if analyst_review_required is None:
        analyst_review_required = False

    analyst_review_status: str | None = None
    reconciliation_status: str | None = None

    if not candidate_state:
        return _decision(
            classification=PromotionPolicyClassification.BLOCKED,
            reason_codes=("missing-candidate-state",),
            message="No latest successful shadow batch state exists for this lane.",
            batch_id=None,
            summary_path=None,
            validation_status="not-run",
            blocking_issue_count=None,
            reconciliation_gap_count=None,
            reconciliation_threshold=None,
            candidate_final_disposition=None,
            promotion_readiness=False,
            analyst_review_required=False,
            override_allowed=False,
            analyst_review_status=None,
            reconciliation_status=None,
            lock_active=lock_active,
        )

    if not batch_id:
        return _decision(
            classification=PromotionPolicyClassification.BLOCKED,
            reason_codes=("missing-candidate-batch-id",),
            message="The latest successful shadow batch state does not include a batch id.",
            batch_id=None,
            summary_path=summary_path,
            validation_status=validation_status,
            blocking_issue_count=blocking_issue_count,
            reconciliation_gap_count=reconciliation_gap_count,
            reconciliation_threshold=reconciliation_threshold,
            candidate_final_disposition=candidate_final_disposition,
            promotion_readiness=promotion_readiness,
            analyst_review_required=analyst_review_required,
            override_allowed=False,
            analyst_review_status=None,
            reconciliation_status=None,
            lock_active=lock_active,
        )

    if candidate_state_errors:
        return _decision(
            classification=PromotionPolicyClassification.BLOCKED,
            reason_codes=("invalid-candidate-state",),
            message=(
                f"Batch {batch_id} cannot be promoted because its candidate lane state "
                + "; ".join(candidate_state_errors)
                + "."
            ),
            batch_id=batch_id,
            summary_path=summary_path,
            validation_status=validation_status,
            blocking_issue_count=None,
            reconciliation_gap_count=None,
            reconciliation_threshold=None,
            candidate_final_disposition=candidate_final_disposition,
            promotion_readiness=False,
            analyst_review_required=analyst_review_required,
            override_allowed=False,
            analyst_review_status=None,
            reconciliation_status=None,
            lock_active=lock_active,
        )

    lane_identity_mismatches = _lane_identity_mismatches(
        _mapping(expected_lane_identity),
        candidate_state,
        state_name="candidate state",
    )
    if lane_identity_mismatches:
        return _decision(
            classification=PromotionPolicyClassification.BLOCKED,
            reason_codes=("candidate-lane-mismatch",),
            message=(
                f"Batch {batch_id} cannot be promoted because its candidate lane state "
                + "; ".join(lane_identity_mismatches)
                + "."
            ),
            batch_id=batch_id,
            summary_path=summary_path,
            validation_status=validation_status,
            blocking_issue_count=blocking_issue_count,
            reconciliation_gap_count=reconciliation_gap_count,
            reconciliation_threshold=reconciliation_threshold,
            candidate_final_disposition=candidate_final_disposition,
            promotion_readiness=False,
            analyst_review_required=analyst_review_required,
            override_allowed=False,
            analyst_review_status=None,
            reconciliation_status=None,
            lock_active=lock_active,
        )

    if candidate_final_disposition not in SUCCESSFUL_REFRESH_DISPOSITIONS:
        return _decision(
            classification=PromotionPolicyClassification.BLOCKED,
            reason_codes=("candidate-not-successful",),
            message=(
                f"Batch {batch_id} is not promotable because its last refresh disposition "
                f"was {candidate_final_disposition or 'unknown'}."
            ),
            batch_id=batch_id,
            summary_path=summary_path,
            validation_status=validation_status,
            blocking_issue_count=blocking_issue_count,
            reconciliation_gap_count=reconciliation_gap_count,
            reconciliation_threshold=reconciliation_threshold,
            candidate_final_disposition=candidate_final_disposition,
            promotion_readiness=promotion_readiness,
            analyst_review_required=analyst_review_required,
            override_allowed=False,
            analyst_review_status=None,
            reconciliation_status=None,
            lock_active=lock_active,
        )

    if not summary_path:
        return _decision(
            classification=PromotionPolicyClassification.BLOCKED,
            reason_codes=("missing-summary-path",),
            message=f"Batch {batch_id} cannot be promoted because its summary path is missing.",
            batch_id=batch_id,
            summary_path=None,
            validation_status=validation_status,
            blocking_issue_count=blocking_issue_count,
            reconciliation_gap_count=reconciliation_gap_count,
            reconciliation_threshold=reconciliation_threshold,
            candidate_final_disposition=candidate_final_disposition,
            promotion_readiness=promotion_readiness,
            analyst_review_required=analyst_review_required,
            override_allowed=False,
            analyst_review_status=None,
            reconciliation_status=None,
            lock_active=lock_active,
        )

    if not summary_payload:
        return _decision(
            classification=PromotionPolicyClassification.BLOCKED,
            reason_codes=("missing-summary-artifact",),
            message=f"Batch {batch_id} cannot be promoted because its summary artifact is missing.",
            batch_id=batch_id,
            summary_path=summary_path,
            validation_status=validation_status,
            blocking_issue_count=blocking_issue_count,
            reconciliation_gap_count=reconciliation_gap_count,
            reconciliation_threshold=reconciliation_threshold,
            candidate_final_disposition=candidate_final_disposition,
            promotion_readiness=promotion_readiness,
            analyst_review_required=analyst_review_required,
            override_allowed=False,
            analyst_review_status=None,
            reconciliation_status=None,
            lock_active=lock_active,
        )

    summary_batch_id = _as_text(summary_payload.get("batch_id"))
    if summary_batch_id != batch_id:
        return _decision(
            classification=PromotionPolicyClassification.BLOCKED,
            reason_codes=("candidate-summary-mismatch",),
            message=(
                f"Batch {batch_id} cannot be promoted because its summary artifact belongs "
                f"to {summary_batch_id or 'an unknown batch'}."
            ),
            batch_id=batch_id,
            summary_path=summary_path,
            validation_status=validation_status,
            blocking_issue_count=blocking_issue_count,
            reconciliation_gap_count=reconciliation_gap_count,
            reconciliation_threshold=reconciliation_threshold,
            candidate_final_disposition=candidate_final_disposition,
            promotion_readiness=promotion_readiness,
            analyst_review_required=analyst_review_required,
            override_allowed=False,
            analyst_review_status=None,
            reconciliation_status=None,
            lock_active=lock_active,
        )

    summary_identity_mismatches = _summary_identity_mismatches(candidate_state, summary_payload)
    if summary_identity_mismatches:
        return _decision(
            classification=PromotionPolicyClassification.BLOCKED,
            reason_codes=("candidate-summary-mismatch",),
            message=(
                f"Batch {batch_id} cannot be promoted because its summary artifact "
                + "; ".join(summary_identity_mismatches)
                + "."
            ),
            batch_id=batch_id,
            summary_path=summary_path,
            validation_status=validation_status,
            blocking_issue_count=blocking_issue_count,
            reconciliation_gap_count=reconciliation_gap_count,
            reconciliation_threshold=reconciliation_threshold,
            candidate_final_disposition=candidate_final_disposition,
            promotion_readiness=promotion_readiness,
            analyst_review_required=analyst_review_required,
            override_allowed=False,
            analyst_review_status=None,
            reconciliation_status=None,
            lock_active=lock_active,
        )

    promotion_gate_status = _mapping(summary_payload.get("promotion_gate_status"))
    validation_gate = _mapping(promotion_gate_status.get("validation"))
    reconciliation_gate = _mapping(promotion_gate_status.get("reconciliation"))
    analyst_gate = _mapping(promotion_gate_status.get("analyst_review"))

    gate_validation_status = _as_text(validation_gate.get("status"))
    summary_artifact_errors: list[str] = []
    gate_blocking_issue_count = _mapping_int(
        validation_gate,
        "blocking_issue_count",
        source_name="summary.validation",
        errors=summary_artifact_errors,
    )
    if gate_blocking_issue_count is not None:
        blocking_issue_count = gate_blocking_issue_count
    if gate_validation_status is None:
        summary_artifact_errors.append("summary.validation.status is required")
    else:
        validation_status = gate_validation_status

    gate_reconciliation_gap_count = _mapping_int(
        reconciliation_gate,
        "gap_count",
        source_name="summary.reconciliation",
        errors=summary_artifact_errors,
    )
    gate_reconciliation_threshold = _mapping_int(
        reconciliation_gate,
        "threshold",
        source_name="summary.reconciliation",
        errors=summary_artifact_errors,
    )
    reconciliation_status = _as_text(reconciliation_gate.get("status"))
    if gate_reconciliation_gap_count is not None:
        reconciliation_gap_count = gate_reconciliation_gap_count
    if gate_reconciliation_threshold is not None:
        reconciliation_threshold = gate_reconciliation_threshold
    if gate_blocking_issue_count is None:
        summary_artifact_errors.append("summary.validation.blocking_issue_count is required")
    if gate_reconciliation_gap_count is None and validation_status == "passed":
        summary_artifact_errors.append("summary.reconciliation.gap_count is required")
    if gate_reconciliation_threshold is None and validation_status == "passed":
        summary_artifact_errors.append("summary.reconciliation.threshold is required")

    summary_promotion_readiness = _mapping_flag(
        summary_payload,
        "promotion_readiness",
        source_name="summary",
        errors=summary_artifact_errors,
    )
    if summary_promotion_readiness is None:
        summary_artifact_errors.append("summary.promotion_readiness is required")
    else:
        promotion_readiness = summary_promotion_readiness

    summary_analyst_review_required = _mapping_flag(
        summary_payload,
        "analyst_review_required",
        source_name="summary",
        errors=summary_artifact_errors,
    )
    if summary_analyst_review_required is not None:
        analyst_review_required = summary_analyst_review_required
    analyst_review_status = _as_text(analyst_gate.get("status"))

    if summary_artifact_errors:
        return _decision(
            classification=PromotionPolicyClassification.BLOCKED,
            reason_codes=("invalid-summary-artifact",),
            message=(
                f"Batch {batch_id} cannot be promoted because its summary artifact is invalid: "
                + "; ".join(summary_artifact_errors)
                + "."
            ),
            batch_id=batch_id,
            summary_path=summary_path,
            validation_status=validation_status,
            blocking_issue_count=blocking_issue_count,
            reconciliation_gap_count=reconciliation_gap_count,
            reconciliation_threshold=reconciliation_threshold,
            candidate_final_disposition=candidate_final_disposition,
            promotion_readiness=False,
            analyst_review_required=analyst_review_required,
            override_allowed=False,
            analyst_review_status=analyst_review_status,
            reconciliation_status=reconciliation_status,
            lock_active=lock_active,
        )

    if lock_active:
        return _decision(
            classification=PromotionPolicyClassification.BLOCKED,
            reason_codes=("lane-unstable",),
            message=(
                f"Batch {batch_id} cannot be promoted while the lane still has "
                "an active scheduler lock."
            ),
            batch_id=batch_id,
            summary_path=summary_path,
            validation_status=validation_status,
            blocking_issue_count=blocking_issue_count,
            reconciliation_gap_count=reconciliation_gap_count,
            reconciliation_threshold=reconciliation_threshold,
            candidate_final_disposition=candidate_final_disposition,
            promotion_readiness=promotion_readiness,
            analyst_review_required=analyst_review_required,
            override_allowed=False,
            analyst_review_status=analyst_review_status,
            reconciliation_status=reconciliation_status,
            lock_active=lock_active,
        )

    if validation_status != "passed" or (blocking_issue_count or 0) > 0:
        return _decision(
            classification=PromotionPolicyClassification.BLOCKED,
            reason_codes=("validation",),
            message=(
                f"Batch {batch_id} cannot be promoted because validation is {validation_status} "
                f"with {blocking_issue_count or 0} blocking issues."
            ),
            batch_id=batch_id,
            summary_path=summary_path,
            validation_status=validation_status,
            blocking_issue_count=blocking_issue_count,
            reconciliation_gap_count=reconciliation_gap_count,
            reconciliation_threshold=reconciliation_threshold,
            candidate_final_disposition=candidate_final_disposition,
            promotion_readiness=promotion_readiness,
            analyst_review_required=analyst_review_required,
            override_allowed=False,
            analyst_review_status=analyst_review_status,
            reconciliation_status=reconciliation_status,
            lock_active=lock_active,
        )

    if (
        candidate_final_disposition == "completed-review-required"
        and analyst_review_status != "passed"
    ):
        analyst_review_required = True

    review_outstanding = (
        analyst_review_required or analyst_review_status == "review-required"
    )

    if reconciliation_status == "blocked" or (
        reconciliation_gap_count is not None
        and reconciliation_threshold is not None
        and reconciliation_gap_count > reconciliation_threshold
    ):
        return _decision(
            classification=PromotionPolicyClassification.BLOCKED,
            reason_codes=("reconciliation",),
            message=(
                f"Batch {batch_id} cannot be promoted because reconciliation reported "
                f"{reconciliation_gap_count or 0} gaps against a threshold of "
                f"{reconciliation_threshold if reconciliation_threshold is not None else 'unknown'}"
                "."
            ),
            batch_id=batch_id,
            summary_path=summary_path,
            validation_status=validation_status,
            blocking_issue_count=blocking_issue_count,
            reconciliation_gap_count=reconciliation_gap_count,
            reconciliation_threshold=reconciliation_threshold,
            candidate_final_disposition=candidate_final_disposition,
            promotion_readiness=promotion_readiness,
            analyst_review_required=analyst_review_required,
            override_allowed=False,
            analyst_review_status=analyst_review_status,
            reconciliation_status=reconciliation_status,
            lock_active=lock_active,
        )

    if not promotion_readiness and not review_outstanding:
        return _decision(
            classification=PromotionPolicyClassification.BLOCKED,
            reason_codes=("promotion-readiness",),
            message=(
                f"Batch {batch_id} is not marked promotion-ready in the refresh summary."
            ),
            batch_id=batch_id,
            summary_path=summary_path,
            validation_status=validation_status,
            blocking_issue_count=blocking_issue_count,
            reconciliation_gap_count=reconciliation_gap_count,
            reconciliation_threshold=reconciliation_threshold,
            candidate_final_disposition=candidate_final_disposition,
            promotion_readiness=False,
            analyst_review_required=analyst_review_required,
            override_allowed=False,
            analyst_review_status=analyst_review_status,
            reconciliation_status=reconciliation_status,
            lock_active=lock_active,
        )

    if review_outstanding:
        return _decision(
            classification=PromotionPolicyClassification.EXCEPTION_REQUIRED,
            reason_codes=("analyst-review",),
            message=(
                f"Batch {batch_id} requires an explicit operator exception "
                "because analyst review is still outstanding."
            ),
            batch_id=batch_id,
            summary_path=summary_path,
            validation_status=validation_status,
            blocking_issue_count=blocking_issue_count,
            reconciliation_gap_count=reconciliation_gap_count,
            reconciliation_threshold=reconciliation_threshold,
            candidate_final_disposition=candidate_final_disposition,
            promotion_readiness=promotion_readiness,
            analyst_review_required=True,
            override_allowed=True,
            analyst_review_status=analyst_review_status,
            reconciliation_status=reconciliation_status,
            lock_active=lock_active,
        )

    if not promotion_readiness:
        return _decision(
            classification=PromotionPolicyClassification.BLOCKED,
            reason_codes=("promotion-readiness",),
            message=f"Batch {batch_id} is not marked promotion-ready in the refresh summary.",
            batch_id=batch_id,
            summary_path=summary_path,
            validation_status=validation_status,
            blocking_issue_count=blocking_issue_count,
            reconciliation_gap_count=reconciliation_gap_count,
            reconciliation_threshold=reconciliation_threshold,
            candidate_final_disposition=candidate_final_disposition,
            promotion_readiness=False,
            analyst_review_required=analyst_review_required,
            override_allowed=False,
            analyst_review_status=analyst_review_status,
            reconciliation_status=reconciliation_status,
            lock_active=lock_active,
        )

    return _decision(
        classification=PromotionPolicyClassification.ELIGIBLE,
        reason_codes=(),
        message=f"Batch {batch_id} is eligible for automatic promotion.",
        batch_id=batch_id,
        summary_path=summary_path,
        validation_status=validation_status,
        blocking_issue_count=blocking_issue_count,
        reconciliation_gap_count=reconciliation_gap_count,
        reconciliation_threshold=reconciliation_threshold,
        candidate_final_disposition=candidate_final_disposition,
        promotion_readiness=True,
        analyst_review_required=False,
        override_allowed=False,
        analyst_review_status=analyst_review_status,
        reconciliation_status=reconciliation_status or "passed",
        lock_active=lock_active,
    )


def evaluate_promotion_policy_from_summary(
    *,
    summary: Mapping[str, object] | None,
    summary_path: str | None,
    lock_active: bool,
    expected_lane_identity: Mapping[str, object] | None = None,
) -> PromotionPolicyDecision:
    summary_payload = _mapping(summary)
    promotion_gate_status = _mapping(summary_payload.get("promotion_gate_status"))
    validation_gate = _mapping(promotion_gate_status.get("validation"))
    reconciliation_gate = _mapping(promotion_gate_status.get("reconciliation"))
    final_disposition = _as_text(summary_payload.get("final_disposition"))
    analyst_review_required = False
    try:
        analyst_review_required = _coerce_bool(summary_payload.get("analyst_review_required"))
    except (TypeError, ValueError):
        analyst_review_required = False
    if final_disposition not in SUCCESSFUL_REFRESH_DISPOSITIONS:
        final_disposition = (
            "completed-review-required"
            if analyst_review_required
            else "completed"
        )
    candidate_state = {
        "batch_id": summary_payload.get("batch_id"),
        "summary_path": summary_path,
        "tenant_id": summary_payload.get("tenant_id"),
        "schema_name": summary_payload.get("schema_name"),
        "source_schema": summary_payload.get("source_schema"),
        "validation_status": validation_gate.get("status"),
        "blocking_issue_count": validation_gate.get("blocking_issue_count"),
        "reconciliation_gap_count": reconciliation_gate.get("gap_count"),
        "reconciliation_threshold": reconciliation_gate.get("threshold"),
        "final_disposition": final_disposition,
        "analyst_review_required": analyst_review_required,
        "promotion_readiness": summary_payload.get("promotion_readiness"),
    }
    return evaluate_promotion_policy(
        latest_success_state=candidate_state,
        summary=summary_payload,
        expected_lane_identity=expected_lane_identity,
        lock_active=lock_active,
    )