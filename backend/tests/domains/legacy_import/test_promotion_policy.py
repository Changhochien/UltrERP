from __future__ import annotations

from domains.legacy_import import promotion_policy


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
    final_disposition: str = "completed",
) -> dict[str, object]:
    return {
        "batch_id": batch_id,
        "tenant_id": tenant_id,
        "schema_name": schema_name,
        "source_schema": source_schema,
        "final_disposition": final_disposition,
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


def test_evaluate_promotion_policy_marks_clean_candidate_eligible() -> None:
    decision = promotion_policy.evaluate_promotion_policy(
        latest_success_state=_candidate_state(),
        summary=_summary(),
        expected_lane_identity={
            "tenant_id": "00000000-0000-0000-0000-000000000001",
            "schema_name": "raw_legacy",
            "source_schema": "public",
        },
        lock_active=False,
    )

    assert decision.classification == promotion_policy.PromotionPolicyClassification.ELIGIBLE
    assert decision.reason_codes == ()
    assert decision.override_allowed is False


def test_evaluate_promotion_policy_marks_analyst_review_as_exception_required() -> None:
    decision = promotion_policy.evaluate_promotion_policy(
        latest_success_state=_candidate_state(
            final_disposition="completed-review-required",
            analyst_review_required=True,
            promotion_readiness=False,
        ),
        summary=_summary(
            final_disposition="completed-review-required",
            analyst_review_status="review-required",
            analyst_review_required=True,
            promotion_readiness=False,
        ),
        expected_lane_identity={
            "tenant_id": "00000000-0000-0000-0000-000000000001",
            "schema_name": "raw_legacy",
            "source_schema": "public",
        },
        lock_active=False,
    )

    assert (
        decision.classification
        == promotion_policy.PromotionPolicyClassification.EXCEPTION_REQUIRED
    )
    assert decision.reason_codes == ("analyst-review",)
    assert decision.override_allowed is True


def test_evaluate_promotion_policy_blocks_validation_failures() -> None:
    decision = promotion_policy.evaluate_promotion_policy(
        latest_success_state=_candidate_state(validation_status="blocked", blocking_issue_count=2),
        summary=_summary(validation_status="blocked", blocking_issue_count=2),
        expected_lane_identity={
            "tenant_id": "00000000-0000-0000-0000-000000000001",
            "schema_name": "raw_legacy",
            "source_schema": "public",
        },
        lock_active=False,
    )

    assert decision.classification == promotion_policy.PromotionPolicyClassification.BLOCKED
    assert decision.reason_codes == ("validation",)
    assert decision.override_allowed is False


def test_evaluate_promotion_policy_keeps_reconciliation_blocked_with_review() -> None:
    decision = promotion_policy.evaluate_promotion_policy(
        latest_success_state=_candidate_state(
            final_disposition="completed-review-required",
            analyst_review_required=True,
            reconciliation_gap_count=3,
            reconciliation_threshold=0,
            promotion_readiness=False,
        ),
        summary=_summary(
            final_disposition="completed-review-required",
            analyst_review_status="review-required",
            analyst_review_required=True,
            reconciliation_status="blocked",
            reconciliation_gap_count=3,
            reconciliation_threshold=0,
            promotion_readiness=False,
        ),
        expected_lane_identity={
            "tenant_id": "00000000-0000-0000-0000-000000000001",
            "schema_name": "raw_legacy",
            "source_schema": "public",
        },
        lock_active=False,
    )

    assert decision.classification == promotion_policy.PromotionPolicyClassification.BLOCKED
    assert decision.reason_codes == ("reconciliation",)
    assert decision.override_allowed is False


def test_evaluate_promotion_policy_from_summary_reuses_same_classification() -> None:
    decision = promotion_policy.evaluate_promotion_policy_from_summary(
        summary=_summary(),
        summary_path="/tmp/summary.json",
        lock_active=False,
    )

    assert decision.classification == promotion_policy.PromotionPolicyClassification.ELIGIBLE
    assert decision.gate_details["reconciliation"]["threshold"] == 0