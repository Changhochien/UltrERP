from __future__ import annotations

from domains.legacy_import import promotion


def _candidate_state(
    *,
    batch_id: str = "legacy-shadow-20260418T020304Z",
    summary_path: str = "/tmp/summary.json",
    tenant_id: str = "00000000-0000-0000-0000-000000000001",
    schema_name: str = "raw_legacy",
    source_schema: str = "public",
    validation_status: str = "passed",
    blocking_issue_count: int = 0,
    reconciliation_gap_count: int = 0,
    reconciliation_threshold: int = 0,
    final_disposition: str = "completed",
    analyst_review_required: bool = False,
    promotion_readiness: bool = True,
) -> dict[str, object]:
    return {
        "batch_id": batch_id,
        "summary_path": summary_path,
        "tenant_id": tenant_id,
        "schema_name": schema_name,
        "source_schema": source_schema,
        "validation_status": validation_status,
        "blocking_issue_count": blocking_issue_count,
        "reconciliation_gap_count": reconciliation_gap_count,
        "reconciliation_threshold": reconciliation_threshold,
        "final_disposition": final_disposition,
        "analyst_review_required": analyst_review_required,
        "promotion_readiness": promotion_readiness,
    }


def _summary(
    *,
    batch_id: str = "legacy-shadow-20260418T020304Z",
    tenant_id: str = "00000000-0000-0000-0000-000000000001",
    schema_name: str = "raw_legacy",
    source_schema: str = "public",
    validation_status: str = "passed",
    blocking_issue_count: int = 0,
    analyst_review_status: str = "passed",
    reconciliation_status: str = "passed",
    reconciliation_gap_count: int = 0,
    reconciliation_threshold: int = 0,
    analyst_review_required: bool = False,
    promotion_readiness: bool = True,
) -> dict[str, object]:
    return {
        "batch_id": batch_id,
        "tenant_id": tenant_id,
        "schema_name": schema_name,
        "source_schema": source_schema,
        "analyst_review_required": analyst_review_required,
        "promotion_readiness": promotion_readiness,
        "promotion_gate_status": {
            "validation": {
                "status": validation_status,
                "blocking_issue_count": blocking_issue_count,
            },
            "analyst_review": {
                "status": analyst_review_status,
            },
            "reconciliation": {
                "status": reconciliation_status,
                "gap_count": reconciliation_gap_count,
                "threshold": reconciliation_threshold,
            },
        },
    }


def test_evaluate_promotion_promotes_eligible_candidate() -> None:
    decision = promotion.evaluate_promotion(
        latest_success_state=_candidate_state(),
        summary=_summary(),
        latest_promoted_state={"batch_id": "legacy-shadow-20260417T020304Z"},
        promoted_by="SYSTEM",
        evaluated_at="2026-04-18T02:30:00+00:00",
        lock_active=False,
    )

    assert decision.promotion_result == promotion.PROMOTION_RESULT_PROMOTED
    assert decision.batch_id == "legacy-shadow-20260418T020304Z"
    assert decision.previous_batch_id == "legacy-shadow-20260417T020304Z"
    assert decision.blocking_gate is None


def test_evaluate_promotion_blocks_when_validation_fails() -> None:
    decision = promotion.evaluate_promotion(
        latest_success_state=_candidate_state(validation_status="blocked", blocking_issue_count=2),
        summary=_summary(validation_status="blocked", blocking_issue_count=2),
        latest_promoted_state=None,
        promoted_by="SYSTEM",
        evaluated_at="2026-04-18T02:30:00+00:00",
        lock_active=False,
    )

    assert decision.promotion_result == promotion.PROMOTION_RESULT_BLOCKED
    assert decision.blocking_gate == "validation"


def test_evaluate_promotion_blocks_when_analyst_review_is_outstanding() -> None:
    decision = promotion.evaluate_promotion(
        latest_success_state=_candidate_state(
            final_disposition="completed-review-required",
            analyst_review_required=True,
            promotion_readiness=False,
        ),
        summary=_summary(
            analyst_review_status="review-required",
            analyst_review_required=True,
            promotion_readiness=False,
        ),
        latest_promoted_state=None,
        promoted_by="SYSTEM",
        evaluated_at="2026-04-18T02:30:00+00:00",
        lock_active=False,
    )

    assert decision.promotion_result == promotion.PROMOTION_RESULT_BLOCKED
    assert decision.blocking_gate == "analyst-review"


def test_evaluate_promotion_returns_noop_for_current_promoted_batch() -> None:
    decision = promotion.evaluate_promotion(
        latest_success_state=_candidate_state(),
        summary=_summary(),
        latest_promoted_state={"batch_id": "legacy-shadow-20260418T020304Z"},
        promoted_by="SYSTEM",
        evaluated_at="2026-04-18T02:30:00+00:00",
        lock_active=True,
    )

    assert decision.promotion_result == promotion.PROMOTION_RESULT_NOOP
    assert decision.blocking_gate is None


def test_evaluate_promotion_blocks_when_lane_is_unstable() -> None:
    decision = promotion.evaluate_promotion(
        latest_success_state=_candidate_state(),
        summary=_summary(),
        latest_promoted_state={"batch_id": "legacy-shadow-20260417T020304Z"},
        promoted_by="SYSTEM",
        evaluated_at="2026-04-18T02:30:00+00:00",
        lock_active=True,
    )

    assert decision.promotion_result == promotion.PROMOTION_RESULT_BLOCKED
    assert decision.blocking_gate == "lane-unstable"


def test_evaluate_promotion_uses_explicit_false_summary_flags() -> None:
    decision = promotion.evaluate_promotion(
        latest_success_state=_candidate_state(
            analyst_review_required=True,
            promotion_readiness=True,
        ),
        summary=_summary(
            analyst_review_required=False,
            promotion_readiness=False,
        ),
        latest_promoted_state={"batch_id": "legacy-shadow-20260417T020304Z"},
        promoted_by="SYSTEM",
        evaluated_at="2026-04-18T02:30:00+00:00",
        lock_active=False,
    )

    assert decision.promotion_result == promotion.PROMOTION_RESULT_BLOCKED
    assert decision.blocking_gate == "promotion-readiness"
    assert decision.analyst_review_required is False


def test_evaluate_promotion_blocks_when_summary_lane_identity_mismatches() -> None:
    decision = promotion.evaluate_promotion(
        latest_success_state=_candidate_state(),
        summary=_summary(tenant_id="00000000-0000-0000-0000-000000000999"),
        latest_promoted_state={"batch_id": "legacy-shadow-20260417T020304Z"},
        promoted_by="SYSTEM",
        evaluated_at="2026-04-18T02:30:00+00:00",
        lock_active=False,
    )

    assert decision.promotion_result == promotion.PROMOTION_RESULT_BLOCKED
    assert decision.blocking_gate == "candidate-summary-mismatch"


def test_evaluate_promotion_blocks_when_summary_lane_identity_is_missing() -> None:
    summary = _summary()
    summary.pop("tenant_id")

    decision = promotion.evaluate_promotion(
        latest_success_state=_candidate_state(),
        summary=summary,
        latest_promoted_state={"batch_id": "legacy-shadow-20260417T020304Z"},
        promoted_by="SYSTEM",
        evaluated_at="2026-04-18T02:30:00+00:00",
        lock_active=False,
    )

    assert decision.promotion_result == promotion.PROMOTION_RESULT_BLOCKED
    assert decision.blocking_gate == "candidate-summary-mismatch"


def test_evaluate_promotion_blocks_when_candidate_lane_identity_is_missing() -> None:
    candidate_state = _candidate_state()
    candidate_state.pop("tenant_id")

    decision = promotion.evaluate_promotion(
        latest_success_state=candidate_state,
        summary=_summary(),
        latest_promoted_state={"batch_id": "legacy-shadow-20260417T020304Z"},
        promoted_by="SYSTEM",
        evaluated_at="2026-04-18T02:30:00+00:00",
        lock_active=False,
    )

    assert decision.promotion_result == promotion.PROMOTION_RESULT_BLOCKED
    assert decision.blocking_gate == "candidate-summary-mismatch"


def test_evaluate_promotion_blocks_when_candidate_numeric_fields_are_invalid() -> None:
    decision = promotion.evaluate_promotion(
        latest_success_state=_candidate_state(blocking_issue_count="not-a-number"),
        summary=_summary(),
        latest_promoted_state={"batch_id": "legacy-shadow-20260417T020304Z"},
        promoted_by="SYSTEM",
        evaluated_at="2026-04-18T02:30:00+00:00",
        lock_active=False,
    )

    assert decision.promotion_result == promotion.PROMOTION_RESULT_BLOCKED
    assert decision.blocking_gate == "invalid-candidate-state"


def test_evaluate_promotion_blocks_when_candidate_numeric_fields_are_boolean() -> None:
    decision = promotion.evaluate_promotion(
        latest_success_state=_candidate_state(blocking_issue_count=False),
        summary=_summary(),
        latest_promoted_state={"batch_id": "legacy-shadow-20260417T020304Z"},
        promoted_by="SYSTEM",
        evaluated_at="2026-04-18T02:30:00+00:00",
        lock_active=False,
    )

    assert decision.promotion_result == promotion.PROMOTION_RESULT_BLOCKED
    assert decision.blocking_gate == "invalid-candidate-state"


def test_evaluate_promotion_blocks_when_summary_numeric_fields_are_invalid() -> None:
    summary = _summary()
    summary["promotion_gate_status"]["reconciliation"]["gap_count"] = "not-a-number"

    decision = promotion.evaluate_promotion(
        latest_success_state=_candidate_state(),
        summary=summary,
        latest_promoted_state={"batch_id": "legacy-shadow-20260417T020304Z"},
        promoted_by="SYSTEM",
        evaluated_at="2026-04-18T02:30:00+00:00",
        lock_active=False,
    )

    assert decision.promotion_result == promotion.PROMOTION_RESULT_BLOCKED
    assert decision.blocking_gate == "invalid-summary-artifact"


def test_evaluate_promotion_blocks_when_summary_numeric_fields_are_boolean() -> None:
    summary = _summary()
    summary["promotion_gate_status"]["reconciliation"]["gap_count"] = True

    decision = promotion.evaluate_promotion(
        latest_success_state=_candidate_state(),
        summary=summary,
        latest_promoted_state={"batch_id": "legacy-shadow-20260417T020304Z"},
        promoted_by="SYSTEM",
        evaluated_at="2026-04-18T02:30:00+00:00",
        lock_active=False,
    )

    assert decision.promotion_result == promotion.PROMOTION_RESULT_BLOCKED
    assert decision.blocking_gate == "invalid-summary-artifact"


def test_evaluate_promotion_blocks_when_summary_boolean_fields_are_invalid() -> None:
    summary = _summary()
    summary["promotion_readiness"] = "maybe"

    decision = promotion.evaluate_promotion(
        latest_success_state=_candidate_state(),
        summary=summary,
        latest_promoted_state={"batch_id": "legacy-shadow-20260417T020304Z"},
        promoted_by="SYSTEM",
        evaluated_at="2026-04-18T02:30:00+00:00",
        lock_active=False,
    )

    assert decision.promotion_result == promotion.PROMOTION_RESULT_BLOCKED
    assert decision.blocking_gate == "invalid-summary-artifact"


def test_evaluate_promotion_blocks_when_summary_boolean_fields_are_empty_strings() -> None:
    summary = _summary()
    summary["promotion_readiness"] = ""

    decision = promotion.evaluate_promotion(
        latest_success_state=_candidate_state(),
        summary=summary,
        latest_promoted_state={"batch_id": "legacy-shadow-20260417T020304Z"},
        promoted_by="SYSTEM",
        evaluated_at="2026-04-18T02:30:00+00:00",
        lock_active=False,
    )

    assert decision.promotion_result == promotion.PROMOTION_RESULT_BLOCKED
    assert decision.blocking_gate == "invalid-summary-artifact"


def test_evaluate_promotion_blocks_when_summary_validation_status_is_missing() -> None:
    summary = _summary()
    summary["promotion_gate_status"]["validation"].pop("status")

    decision = promotion.evaluate_promotion(
        latest_success_state=_candidate_state(),
        summary=summary,
        latest_promoted_state={"batch_id": "legacy-shadow-20260417T020304Z"},
        promoted_by="SYSTEM",
        evaluated_at="2026-04-18T02:30:00+00:00",
        lock_active=False,
    )

    assert decision.promotion_result == promotion.PROMOTION_RESULT_BLOCKED
    assert decision.blocking_gate == "invalid-summary-artifact"


def test_evaluate_promotion_blocks_when_summary_promotion_readiness_is_missing() -> None:
    summary = _summary()
    summary.pop("promotion_readiness")

    decision = promotion.evaluate_promotion(
        latest_success_state=_candidate_state(),
        summary=summary,
        latest_promoted_state={"batch_id": "legacy-shadow-20260417T020304Z"},
        promoted_by="SYSTEM",
        evaluated_at="2026-04-18T02:30:00+00:00",
        lock_active=False,
    )

    assert decision.promotion_result == promotion.PROMOTION_RESULT_BLOCKED
    assert decision.blocking_gate == "invalid-summary-artifact"


def test_evaluate_promotion_blocks_when_candidate_numeric_fields_are_fractional() -> None:
    decision = promotion.evaluate_promotion(
        latest_success_state=_candidate_state(blocking_issue_count=1.5),
        summary=_summary(),
        latest_promoted_state={"batch_id": "legacy-shadow-20260417T020304Z"},
        promoted_by="SYSTEM",
        evaluated_at="2026-04-18T02:30:00+00:00",
        lock_active=False,
    )

    assert decision.promotion_result == promotion.PROMOTION_RESULT_BLOCKED
    assert decision.blocking_gate == "invalid-candidate-state"


def test_evaluate_promotion_blocks_review_required_disposition_without_explicit_pass() -> None:
    summary = _summary()
    summary["promotion_gate_status"]["analyst_review"] = {}

    decision = promotion.evaluate_promotion(
        latest_success_state=_candidate_state(
            final_disposition="completed-review-required",
            analyst_review_required=False,
        ),
        summary=summary,
        latest_promoted_state={"batch_id": "legacy-shadow-20260417T020304Z"},
        promoted_by="SYSTEM",
        evaluated_at="2026-04-18T02:30:00+00:00",
        lock_active=False,
    )

    assert decision.promotion_result == promotion.PROMOTION_RESULT_BLOCKED
    assert decision.blocking_gate == "analyst-review"


def test_evaluate_promotion_blocks_noop_when_candidate_lane_identity_mismatches() -> None:
    decision = promotion.evaluate_promotion(
        latest_success_state=_candidate_state(),
        summary=_summary(),
        latest_promoted_state={
            "batch_id": "legacy-shadow-20260418T020304Z",
            "tenant_id": "00000000-0000-0000-0000-000000000001",
            "schema_name": "raw_legacy",
            "source_schema": "public",
        },
        expected_lane_identity={
            "tenant_id": "00000000-0000-0000-0000-000000000999",
            "schema_name": "raw_legacy",
            "source_schema": "public",
        },
        promoted_by="SYSTEM",
        evaluated_at="2026-04-18T02:30:00+00:00",
        lock_active=False,
    )

    assert decision.promotion_result == promotion.PROMOTION_RESULT_BLOCKED
    assert decision.blocking_gate == "candidate-lane-mismatch"