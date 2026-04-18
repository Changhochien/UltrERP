from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

from scripts import run_legacy_promotion as promotion_script
from scripts.legacy_refresh_state import (
    LegacyRefreshLanePaths,
    build_lane_state_paths,
    write_json_atomically,
)

TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _summary_payload(
    *,
    batch_id: str,
    tenant_id: str = str(TENANT_ID),
    schema_name: str = "raw_legacy",
    source_schema: str = "public",
    validation_status: str = "passed",
    blocking_issue_count: int = 0,
    analyst_review_status: str = "passed",
    analyst_review_required: bool = False,
    reconciliation_status: str = "passed",
    reconciliation_gap_count: int = 0,
    reconciliation_threshold: int = 0,
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


def _latest_success_state(
    *,
    batch_id: str,
    summary_path: Path,
    summary: dict[str, object],
) -> dict[str, object]:
    return {
        "state_version": 1,
        "batch_id": batch_id,
        "summary_path": str(summary_path),
        "tenant_id": str(TENANT_ID),
        "schema_name": "raw_legacy",
        "source_schema": "public",
        "final_disposition": "completed-review-required"
        if summary.get("analyst_review_required")
        else "completed",
        "validation_status": summary["promotion_gate_status"]["validation"]["status"],
        "blocking_issue_count": summary["promotion_gate_status"]["validation"][
            "blocking_issue_count"
        ],
        "reconciliation_gap_count": summary["promotion_gate_status"]["reconciliation"][
            "gap_count"
        ],
        "reconciliation_threshold": summary["promotion_gate_status"]["reconciliation"][
            "threshold"
        ],
        "analyst_review_required": summary.get("analyst_review_required", False),
        "promotion_readiness": summary.get("promotion_readiness", False),
    }


def _promoted_state(
    *,
    batch_id: str,
    message: str | None = None,
    previous_batch_id: str | None = None,
) -> dict[str, object]:
    record: dict[str, object] = {
        "batch_id": batch_id,
        "tenant_id": str(TENANT_ID),
        "schema_name": "raw_legacy",
        "source_schema": "public",
        "promoted_at": "2026-04-17T03:00:00+00:00",
        "promoted_by": "SYSTEM",
        "summary_path": "/tmp/previous-summary.json",
        "validation_status": "passed",
        "blocking_issue_count": 0,
        "reconciliation_gap_count": 0,
        "reconciliation_threshold": 0,
        "promotion_result": "promoted",
    }
    if previous_batch_id is not None:
        record["previous_batch_id"] = previous_batch_id
    if message is not None:
        record["message"] = message
    return record


def _prepare_lane(
    tmp_path: Path,
    *,
    batch_id: str,
    summary_payload: dict[str, object],
) -> tuple[Path, LegacyRefreshLanePaths]:
    summary_root = tmp_path / "ops"
    lane_paths = build_lane_state_paths(
        tenant_id=TENANT_ID,
        schema_name="raw_legacy",
        source_schema="public",
        summary_root=summary_root,
    )
    summary_path = summary_root / f"{batch_id}-summary.json"
    write_json_atomically(summary_path, summary_payload)
    write_json_atomically(
        lane_paths.latest_success_path,
        _latest_success_state(
            batch_id=batch_id,
            summary_path=summary_path,
            summary=summary_payload,
        ),
    )
    return summary_root, lane_paths


def test_run_legacy_promotion_updates_latest_promoted_for_eligible_candidate(
    monkeypatch,
    tmp_path: Path,
) -> None:
    fixed_now = datetime(2026, 4, 18, 3, 0, 0, tzinfo=timezone.utc)
    batch_id = "legacy-shadow-20260418T020304Z"
    summary_root, lane_paths = _prepare_lane(
        tmp_path,
        batch_id=batch_id,
        summary_payload=_summary_payload(batch_id=batch_id),
    )
    write_json_atomically(
        lane_paths.latest_promoted_path,
        _promoted_state(batch_id="legacy-shadow-20260417T020304Z"),
    )

    monkeypatch.setattr(promotion_script, "utc_now", lambda: fixed_now)

    result = asyncio.run(
        promotion_script.run_legacy_promotion(
            tenant_id=TENANT_ID,
            schema_name="raw_legacy",
            source_schema="public",
            summary_root=summary_root,
        )
    )

    latest_promoted = json.loads(lane_paths.latest_promoted_path.read_text(encoding="utf-8"))
    promotion_result = json.loads(result.result_path.read_text(encoding="utf-8"))

    assert result.exit_code == 0
    assert result.latest_promoted_updated is True
    assert latest_promoted["batch_id"] == batch_id
    assert latest_promoted["previous_batch_id"] == "legacy-shadow-20260417T020304Z"
    assert latest_promoted["promotion_result"] == "promoted"
    assert promotion_result == latest_promoted


def test_run_legacy_promotion_blocks_and_preserves_previous_pointer(
    monkeypatch,
    tmp_path: Path,
) -> None:
    fixed_now = datetime(2026, 4, 18, 3, 5, 0, tzinfo=timezone.utc)
    batch_id = "legacy-shadow-20260418T020500Z"
    summary_root, lane_paths = _prepare_lane(
        tmp_path,
        batch_id=batch_id,
        summary_payload=_summary_payload(
            batch_id=batch_id,
            analyst_review_status="review-required",
            analyst_review_required=True,
            promotion_readiness=False,
        ),
    )
    write_json_atomically(
        lane_paths.latest_promoted_path,
        _promoted_state(batch_id="legacy-shadow-20260417T020304Z"),
    )

    monkeypatch.setattr(promotion_script, "utc_now", lambda: fixed_now)

    result = asyncio.run(
        promotion_script.run_legacy_promotion(
            tenant_id=TENANT_ID,
            schema_name="raw_legacy",
            source_schema="public",
            summary_root=summary_root,
        )
    )

    latest_promoted = json.loads(lane_paths.latest_promoted_path.read_text(encoding="utf-8"))
    promotion_result = json.loads(result.result_path.read_text(encoding="utf-8"))

    assert result.exit_code == 1
    assert result.latest_promoted_updated is False
    assert latest_promoted["batch_id"] == "legacy-shadow-20260417T020304Z"
    assert promotion_result["promotion_result"] == "blocked"
    assert promotion_result["blocking_gate"] == "analyst-review"


def test_run_legacy_promotion_allows_exception_override_with_durable_record(
    monkeypatch,
    tmp_path: Path,
) -> None:
    fixed_now = datetime(2026, 4, 18, 3, 7, 0, tzinfo=timezone.utc)
    batch_id = "legacy-shadow-20260418T020700Z"
    summary_root, lane_paths = _prepare_lane(
        tmp_path,
        batch_id=batch_id,
        summary_payload=_summary_payload(
            batch_id=batch_id,
            analyst_review_status="review-required",
            analyst_review_required=True,
            promotion_readiness=False,
        ),
    )
    write_json_atomically(
        lane_paths.latest_promoted_path,
        _promoted_state(batch_id="legacy-shadow-20260417T020304Z"),
    )

    monkeypatch.setattr(promotion_script, "utc_now", lambda: fixed_now)

    result = asyncio.run(
        promotion_script.run_legacy_promotion(
            tenant_id=TENANT_ID,
            schema_name="raw_legacy",
            source_schema="public",
            summary_root=summary_root,
            promoted_by="owner@example.com",
            allow_exception_override=True,
            override_rationale="Reviewed the unresolved mappings and approved cutover.",
            override_scope="single batch cutover for raw_legacy/public",
        )
    )

    latest_promoted = json.loads(lane_paths.latest_promoted_path.read_text(encoding="utf-8"))
    promotion_result = json.loads(result.result_path.read_text(encoding="utf-8"))
    override_record_path = Path(promotion_result["override_record_path"])
    override_record = json.loads(override_record_path.read_text(encoding="utf-8"))

    assert result.exit_code == 0
    assert result.latest_promoted_updated is True
    assert latest_promoted["promotion_result"] == "promoted"
    assert latest_promoted["promotion_mode"] == "exception-override"
    assert latest_promoted["promotion_policy_classification"] == "exception-required"
    assert latest_promoted["override_applied"] is True
    assert latest_promoted["override_record_path"] == str(override_record_path)
    assert latest_promoted["override_rationale"] == (
        "Reviewed the unresolved mappings and approved cutover."
    )
    assert latest_promoted["override_scope"] == "single batch cutover for raw_legacy/public"
    assert promotion_result == latest_promoted
    assert override_record["batch_id"] == batch_id
    assert override_record["approved_by"] == "owner@example.com"
    assert override_record["approved_at"] == fixed_now.isoformat()
    assert override_record["override_rationale"] == (
        "Reviewed the unresolved mappings and approved cutover."
    )
    assert override_record["override_scope"] == "single batch cutover for raw_legacy/public"


def test_run_legacy_promotion_does_not_override_reconciliation_block(
    monkeypatch,
    tmp_path: Path,
) -> None:
    fixed_now = datetime(2026, 4, 18, 3, 7, 30, tzinfo=timezone.utc)
    batch_id = "legacy-shadow-20260418T020730Z"
    summary_root, lane_paths = _prepare_lane(
        tmp_path,
        batch_id=batch_id,
        summary_payload=_summary_payload(
            batch_id=batch_id,
            analyst_review_status="review-required",
            analyst_review_required=True,
            reconciliation_status="blocked",
            reconciliation_gap_count=2,
            reconciliation_threshold=0,
            promotion_readiness=False,
        ),
    )
    previous_pointer = _promoted_state(batch_id="legacy-shadow-20260417T020304Z")
    write_json_atomically(lane_paths.latest_promoted_path, previous_pointer)

    monkeypatch.setattr(promotion_script, "utc_now", lambda: fixed_now)

    result = asyncio.run(
        promotion_script.run_legacy_promotion(
            tenant_id=TENANT_ID,
            schema_name="raw_legacy",
            source_schema="public",
            summary_root=summary_root,
            promoted_by="owner@example.com",
            allow_exception_override=True,
            override_rationale="Reviewed the unresolved mappings and approved cutover.",
            override_scope="single batch cutover for raw_legacy/public",
        )
    )

    latest_promoted = json.loads(lane_paths.latest_promoted_path.read_text(encoding="utf-8"))
    promotion_result = json.loads(result.result_path.read_text(encoding="utf-8"))

    assert result.exit_code == 1
    assert result.latest_promoted_updated is False
    assert latest_promoted == previous_pointer
    assert promotion_result["promotion_result"] == "blocked"
    assert promotion_result["blocking_gate"] == "reconciliation"
    assert promotion_result["override_record_path"] is None


def test_run_legacy_promotion_requires_override_metadata(
    monkeypatch,
    tmp_path: Path,
) -> None:
    fixed_now = datetime(2026, 4, 18, 3, 8, 0, tzinfo=timezone.utc)
    batch_id = "legacy-shadow-20260418T020800Z"
    summary_root, _lane_paths = _prepare_lane(
        tmp_path,
        batch_id=batch_id,
        summary_payload=_summary_payload(
            batch_id=batch_id,
            analyst_review_status="review-required",
            analyst_review_required=True,
            promotion_readiness=False,
        ),
    )

    monkeypatch.setattr(promotion_script, "utc_now", lambda: fixed_now)

    with pytest.raises(ValueError, match="override_rationale"):
        asyncio.run(
            promotion_script.run_legacy_promotion(
                tenant_id=TENANT_ID,
                schema_name="raw_legacy",
                source_schema="public",
                summary_root=summary_root,
                promoted_by="owner@example.com",
                allow_exception_override=True,
                override_scope="single batch cutover for raw_legacy/public",
            )
        )


@pytest.mark.parametrize("promoted_by", ["", "   ", "SYSTEM", "system", " System "])
def test_run_legacy_promotion_rejects_reserved_override_actor_identities(
    monkeypatch,
    tmp_path: Path,
    promoted_by: str,
) -> None:
    fixed_now = datetime(2026, 4, 18, 3, 8, 30, tzinfo=timezone.utc)
    batch_id = "legacy-shadow-20260418T020830Z"
    summary_root, _lane_paths = _prepare_lane(
        tmp_path,
        batch_id=batch_id,
        summary_payload=_summary_payload(
            batch_id=batch_id,
            analyst_review_status="review-required",
            analyst_review_required=True,
            promotion_readiness=False,
        ),
    )

    monkeypatch.setattr(promotion_script, "utc_now", lambda: fixed_now)

    with pytest.raises(ValueError, match="promoted_by must identify"):
        asyncio.run(
            promotion_script.run_legacy_promotion(
                tenant_id=TENANT_ID,
                schema_name="raw_legacy",
                source_schema="public",
                summary_root=summary_root,
                promoted_by=promoted_by,
                allow_exception_override=True,
                override_rationale="Reviewed the unresolved mappings and approved cutover.",
                override_scope="single batch cutover for raw_legacy/public",
            )
        )


def test_run_legacy_promotion_returns_noop_for_already_promoted_batch(
    monkeypatch,
    tmp_path: Path,
) -> None:
    fixed_now = datetime(2026, 4, 18, 3, 10, 0, tzinfo=timezone.utc)
    batch_id = "legacy-shadow-20260418T021000Z"
    summary_root, lane_paths = _prepare_lane(
        tmp_path,
        batch_id=batch_id,
        summary_payload=_summary_payload(batch_id=batch_id),
    )
    existing_pointer = _promoted_state(batch_id=batch_id, message="already active")
    write_json_atomically(lane_paths.latest_promoted_path, existing_pointer)

    monkeypatch.setattr(promotion_script, "utc_now", lambda: fixed_now)

    result = asyncio.run(
        promotion_script.run_legacy_promotion(
            tenant_id=TENANT_ID,
            schema_name="raw_legacy",
            source_schema="public",
            summary_root=summary_root,
        )
    )

    latest_promoted = json.loads(lane_paths.latest_promoted_path.read_text(encoding="utf-8"))
    promotion_result = json.loads(result.result_path.read_text(encoding="utf-8"))

    assert result.exit_code == 0
    assert result.latest_promoted_updated is False
    assert latest_promoted == existing_pointer
    assert promotion_result["promotion_result"] == "noop"


def test_run_legacy_promotion_blocks_when_candidate_state_is_missing(
    monkeypatch,
    tmp_path: Path,
) -> None:
    fixed_now = datetime(2026, 4, 18, 3, 15, 0, tzinfo=timezone.utc)
    summary_root = tmp_path / "ops"
    lane_paths = build_lane_state_paths(
        tenant_id=TENANT_ID,
        schema_name="raw_legacy",
        source_schema="public",
        summary_root=summary_root,
    )

    monkeypatch.setattr(promotion_script, "utc_now", lambda: fixed_now)

    result = asyncio.run(
        promotion_script.run_legacy_promotion(
            tenant_id=TENANT_ID,
            schema_name="raw_legacy",
            source_schema="public",
            summary_root=summary_root,
        )
    )

    assert result.exit_code == 1
    assert result.latest_promoted_updated is False
    assert not lane_paths.latest_promoted_path.exists()
    promotion_result = json.loads(result.result_path.read_text(encoding="utf-8"))
    assert promotion_result["promotion_result"] == "blocked"
    assert promotion_result["blocking_gate"] == "missing-candidate-state"


def test_run_legacy_promotion_restores_previous_pointer_when_write_fails(
    monkeypatch,
    tmp_path: Path,
) -> None:
    fixed_now = datetime(2026, 4, 18, 3, 20, 0, tzinfo=timezone.utc)
    batch_id = "legacy-shadow-20260418T022000Z"
    summary_root, lane_paths = _prepare_lane(
        tmp_path,
        batch_id=batch_id,
        summary_payload=_summary_payload(batch_id=batch_id),
    )
    previous_pointer = _promoted_state(
        batch_id="legacy-shadow-20260417T020304Z",
        message="previous stable batch",
    )
    write_json_atomically(lane_paths.latest_promoted_path, previous_pointer)

    monkeypatch.setattr(promotion_script, "utc_now", lambda: fixed_now)

    original_write_json_atomically = promotion_script.write_json_atomically

    def flaky_write(target_path: Path, payload: dict[str, object]) -> None:
        if target_path == lane_paths.latest_promoted_path:
            raise OSError("cannot update latest-promoted pointer")
        original_write_json_atomically(target_path, payload)

    monkeypatch.setattr(promotion_script, "write_json_atomically", flaky_write)

    result = asyncio.run(
        promotion_script.run_legacy_promotion(
            tenant_id=TENANT_ID,
            schema_name="raw_legacy",
            source_schema="public",
            summary_root=summary_root,
        )
    )

    latest_promoted = json.loads(lane_paths.latest_promoted_path.read_text(encoding="utf-8"))
    promotion_result = json.loads(result.result_path.read_text(encoding="utf-8"))

    assert result.exit_code == 1
    assert result.latest_promoted_updated is False
    assert latest_promoted == previous_pointer
    assert promotion_result["blocking_gate"] == "promotion-write-failure"


def test_run_legacy_promotion_removes_override_record_when_result_write_fails(
    monkeypatch,
    tmp_path: Path,
) -> None:
    fixed_now = datetime(2026, 4, 18, 3, 22, 0, tzinfo=timezone.utc)
    batch_id = "legacy-shadow-20260418T022200Z"
    summary_root, lane_paths = _prepare_lane(
        tmp_path,
        batch_id=batch_id,
        summary_payload=_summary_payload(
            batch_id=batch_id,
            analyst_review_status="review-required",
            analyst_review_required=True,
            promotion_readiness=False,
        ),
    )
    previous_pointer = _promoted_state(batch_id="legacy-shadow-20260417T020304Z")
    write_json_atomically(lane_paths.latest_promoted_path, previous_pointer)

    monkeypatch.setattr(promotion_script, "utc_now", lambda: fixed_now)

    original_write_json_atomically = promotion_script.write_json_atomically

    def flaky_write(target_path: Path, payload: dict[str, object]) -> None:
        if target_path.parent == lane_paths.promotion_results_root:
            raise OSError("cannot write promotion result artifact")
        original_write_json_atomically(target_path, payload)

    monkeypatch.setattr(promotion_script, "write_json_atomically", flaky_write)

    result = asyncio.run(
        promotion_script.run_legacy_promotion(
            tenant_id=TENANT_ID,
            schema_name="raw_legacy",
            source_schema="public",
            summary_root=summary_root,
            promoted_by="owner@example.com",
            allow_exception_override=True,
            override_rationale="Reviewed the unresolved mappings and approved cutover.",
            override_scope="single batch cutover for raw_legacy/public",
        )
    )

    latest_promoted = json.loads(lane_paths.latest_promoted_path.read_text(encoding="utf-8"))

    assert result.exit_code == 1
    assert result.latest_promoted_updated is False
    assert result.result_path is None
    assert latest_promoted == previous_pointer
    assert list(lane_paths.promotion_overrides_root.glob("*.json")) == []


def test_run_legacy_promotion_removes_override_record_when_pointer_write_fails(
    monkeypatch,
    tmp_path: Path,
) -> None:
    fixed_now = datetime(2026, 4, 18, 3, 23, 0, tzinfo=timezone.utc)
    batch_id = "legacy-shadow-20260418T022300Z"
    summary_root, lane_paths = _prepare_lane(
        tmp_path,
        batch_id=batch_id,
        summary_payload=_summary_payload(
            batch_id=batch_id,
            analyst_review_status="review-required",
            analyst_review_required=True,
            promotion_readiness=False,
        ),
    )
    previous_pointer = _promoted_state(
        batch_id="legacy-shadow-20260417T020304Z",
        message="previous stable batch",
    )
    write_json_atomically(lane_paths.latest_promoted_path, previous_pointer)

    monkeypatch.setattr(promotion_script, "utc_now", lambda: fixed_now)

    original_write_json_atomically = promotion_script.write_json_atomically

    def flaky_write(target_path: Path, payload: dict[str, object]) -> None:
        if target_path == lane_paths.latest_promoted_path:
            raise OSError("cannot update latest-promoted pointer")
        original_write_json_atomically(target_path, payload)

    monkeypatch.setattr(promotion_script, "write_json_atomically", flaky_write)

    result = asyncio.run(
        promotion_script.run_legacy_promotion(
            tenant_id=TENANT_ID,
            schema_name="raw_legacy",
            source_schema="public",
            summary_root=summary_root,
            promoted_by="owner@example.com",
            allow_exception_override=True,
            override_rationale="Reviewed the unresolved mappings and approved cutover.",
            override_scope="single batch cutover for raw_legacy/public",
        )
    )

    latest_promoted = json.loads(lane_paths.latest_promoted_path.read_text(encoding="utf-8"))
    promotion_result = json.loads(result.result_path.read_text(encoding="utf-8"))

    assert result.exit_code == 1
    assert result.latest_promoted_updated is False
    assert latest_promoted == previous_pointer
    assert promotion_result["blocking_gate"] == "promotion-write-failure"
    assert list(lane_paths.promotion_overrides_root.glob("*.json")) == []


def test_run_legacy_promotion_returns_controlled_failure_when_blocked_artifact_write_fails(
    monkeypatch,
    tmp_path: Path,
) -> None:
    fixed_now = datetime(2026, 4, 18, 3, 25, 0, tzinfo=timezone.utc)
    batch_id = "legacy-shadow-20260418T022500Z"
    summary_root, lane_paths = _prepare_lane(
        tmp_path,
        batch_id=batch_id,
        summary_payload=_summary_payload(
            batch_id=batch_id,
            analyst_review_status="review-required",
            analyst_review_required=True,
            promotion_readiness=False,
        ),
    )
    previous_pointer = _promoted_state(batch_id="legacy-shadow-20260417T020304Z")
    write_json_atomically(lane_paths.latest_promoted_path, previous_pointer)

    monkeypatch.setattr(promotion_script, "utc_now", lambda: fixed_now)

    original_write_json_atomically = promotion_script.write_json_atomically

    def flaky_write(target_path: Path, payload: dict[str, object]) -> None:
        if target_path.parent == lane_paths.promotion_results_root:
            raise OSError("cannot write promotion result artifact")
        original_write_json_atomically(target_path, payload)

    monkeypatch.setattr(promotion_script, "write_json_atomically", flaky_write)

    result = asyncio.run(
        promotion_script.run_legacy_promotion(
            tenant_id=TENANT_ID,
            schema_name="raw_legacy",
            source_schema="public",
            summary_root=summary_root,
        )
    )

    latest_promoted = json.loads(lane_paths.latest_promoted_path.read_text(encoding="utf-8"))

    assert result.exit_code == 1
    assert result.latest_promoted_updated is False
    assert result.result_path is None
    assert latest_promoted == previous_pointer
    assert result.result_record["blocking_gate"] == "promotion-write-failure"


def test_run_legacy_promotion_blocks_when_summary_lane_identity_is_missing(
    monkeypatch,
    tmp_path: Path,
) -> None:
    fixed_now = datetime(2026, 4, 18, 3, 30, 0, tzinfo=timezone.utc)
    batch_id = "legacy-shadow-20260418T023000Z"
    summary_payload = _summary_payload(batch_id=batch_id)
    summary_payload.pop("tenant_id")
    summary_root, lane_paths = _prepare_lane(
        tmp_path,
        batch_id=batch_id,
        summary_payload=summary_payload,
    )
    previous_pointer = _promoted_state(batch_id="legacy-shadow-20260417T020304Z")
    write_json_atomically(lane_paths.latest_promoted_path, previous_pointer)

    monkeypatch.setattr(promotion_script, "utc_now", lambda: fixed_now)

    result = asyncio.run(
        promotion_script.run_legacy_promotion(
            tenant_id=TENANT_ID,
            schema_name="raw_legacy",
            source_schema="public",
            summary_root=summary_root,
        )
    )

    latest_promoted = json.loads(lane_paths.latest_promoted_path.read_text(encoding="utf-8"))
    promotion_result = json.loads(result.result_path.read_text(encoding="utf-8"))

    assert result.exit_code == 1
    assert result.latest_promoted_updated is False
    assert latest_promoted == previous_pointer
    assert promotion_result["blocking_gate"] == "candidate-summary-mismatch"


def test_run_legacy_promotion_preserves_previous_pointer_when_promoted_result_write_fails(
    monkeypatch,
    tmp_path: Path,
) -> None:
    fixed_now = datetime(2026, 4, 18, 3, 35, 0, tzinfo=timezone.utc)
    batch_id = "legacy-shadow-20260418T023500Z"
    summary_root, lane_paths = _prepare_lane(
        tmp_path,
        batch_id=batch_id,
        summary_payload=_summary_payload(batch_id=batch_id),
    )
    previous_pointer = _promoted_state(
        batch_id="legacy-shadow-20260417T020304Z",
        message="previous stable batch",
    )
    write_json_atomically(lane_paths.latest_promoted_path, previous_pointer)

    monkeypatch.setattr(promotion_script, "utc_now", lambda: fixed_now)

    original_write_json_atomically = promotion_script.write_json_atomically
    result_write_count = 0

    def flaky_write(target_path: Path, payload: dict[str, object]) -> None:
        nonlocal result_write_count
        if target_path.parent == lane_paths.promotion_results_root:
            result_write_count += 1
            if result_write_count == 1:
                raise OSError("cannot write promotion result artifact")
        original_write_json_atomically(target_path, payload)

    monkeypatch.setattr(promotion_script, "write_json_atomically", flaky_write)

    result = asyncio.run(
        promotion_script.run_legacy_promotion(
            tenant_id=TENANT_ID,
            schema_name="raw_legacy",
            source_schema="public",
            summary_root=summary_root,
        )
    )

    latest_promoted = json.loads(lane_paths.latest_promoted_path.read_text(encoding="utf-8"))
    promotion_result = json.loads(result.result_path.read_text(encoding="utf-8"))

    assert result.exit_code == 1
    assert result.latest_promoted_updated is False
    assert latest_promoted == previous_pointer
    assert promotion_result["blocking_gate"] == "promotion-write-failure"


def test_run_legacy_promotion_blocks_cross_lane_candidate_state(
    monkeypatch,
    tmp_path: Path,
) -> None:
    fixed_now = datetime(2026, 4, 18, 3, 40, 0, tzinfo=timezone.utc)
    batch_id = "legacy-shadow-20260418T024000Z"
    foreign_tenant_id = "00000000-0000-0000-0000-000000000999"
    summary_root, lane_paths = _prepare_lane(
        tmp_path,
        batch_id=batch_id,
        summary_payload=_summary_payload(batch_id=batch_id, tenant_id=foreign_tenant_id),
    )
    latest_success_state = json.loads(lane_paths.latest_success_path.read_text(encoding="utf-8"))
    latest_success_state["tenant_id"] = foreign_tenant_id
    write_json_atomically(lane_paths.latest_success_path, latest_success_state)

    monkeypatch.setattr(promotion_script, "utc_now", lambda: fixed_now)

    result = asyncio.run(
        promotion_script.run_legacy_promotion(
            tenant_id=TENANT_ID,
            schema_name="raw_legacy",
            source_schema="public",
            summary_root=summary_root,
        )
    )

    promotion_result = json.loads(result.result_path.read_text(encoding="utf-8"))

    assert result.exit_code == 1
    assert result.latest_promoted_updated is False
    assert promotion_result["blocking_gate"] == "candidate-lane-mismatch"


def test_run_legacy_promotion_removes_stale_promoted_artifact_when_pointer_write_fails(
    monkeypatch,
    tmp_path: Path,
) -> None:
    fixed_now = datetime(2026, 4, 18, 3, 45, 0, tzinfo=timezone.utc)
    batch_id = "legacy-shadow-20260418T024500Z"
    summary_root, lane_paths = _prepare_lane(
        tmp_path,
        batch_id=batch_id,
        summary_payload=_summary_payload(batch_id=batch_id),
    )
    previous_pointer = _promoted_state(
        batch_id="legacy-shadow-20260417T020304Z",
        message="previous stable batch",
    )
    write_json_atomically(lane_paths.latest_promoted_path, previous_pointer)

    monkeypatch.setattr(promotion_script, "utc_now", lambda: fixed_now)

    original_write_json_atomically = promotion_script.write_json_atomically
    result_write_count = 0

    def flaky_write(target_path: Path, payload: dict[str, object]) -> None:
        nonlocal result_write_count
        if target_path.parent == lane_paths.promotion_results_root:
            result_write_count += 1
            if result_write_count == 1:
                original_write_json_atomically(target_path, payload)
                return
            raise OSError("cannot rewrite promotion result artifact")
        if target_path == lane_paths.latest_promoted_path:
            raise OSError("cannot update latest-promoted pointer")
        original_write_json_atomically(target_path, payload)

    monkeypatch.setattr(promotion_script, "write_json_atomically", flaky_write)

    result = asyncio.run(
        promotion_script.run_legacy_promotion(
            tenant_id=TENANT_ID,
            schema_name="raw_legacy",
            source_schema="public",
            summary_root=summary_root,
        )
    )

    latest_promoted = json.loads(lane_paths.latest_promoted_path.read_text(encoding="utf-8"))

    assert result.exit_code == 1
    assert result.latest_promoted_updated is False
    assert result.result_path is None
    assert latest_promoted == previous_pointer
    assert list(lane_paths.promotion_results_root.glob("*.json")) == []


def test_run_legacy_promotion_blocks_when_latest_promoted_state_is_invalid_json(
    monkeypatch,
    tmp_path: Path,
) -> None:
    fixed_now = datetime(2026, 4, 18, 3, 50, 0, tzinfo=timezone.utc)
    batch_id = "legacy-shadow-20260418T025000Z"
    summary_root, lane_paths = _prepare_lane(
        tmp_path,
        batch_id=batch_id,
        summary_payload=_summary_payload(batch_id=batch_id),
    )
    lane_paths.latest_promoted_path.parent.mkdir(parents=True, exist_ok=True)
    lane_paths.latest_promoted_path.write_text("{not-json", encoding="utf-8")

    monkeypatch.setattr(promotion_script, "utc_now", lambda: fixed_now)

    result = asyncio.run(
        promotion_script.run_legacy_promotion(
            tenant_id=TENANT_ID,
            schema_name="raw_legacy",
            source_schema="public",
            summary_root=summary_root,
        )
    )

    promotion_result = json.loads(result.result_path.read_text(encoding="utf-8"))

    assert result.exit_code == 1
    assert result.latest_promoted_updated is False
    assert promotion_result["blocking_gate"] == "invalid-promoted-state"
    assert lane_paths.latest_promoted_path.read_text(encoding="utf-8") == "{not-json"


def test_run_legacy_promotion_blocks_when_latest_promoted_state_is_json_null(
    monkeypatch,
    tmp_path: Path,
) -> None:
    fixed_now = datetime(2026, 4, 18, 3, 52, 0, tzinfo=timezone.utc)
    batch_id = "legacy-shadow-20260418T025200Z"
    summary_root, lane_paths = _prepare_lane(
        tmp_path,
        batch_id=batch_id,
        summary_payload=_summary_payload(batch_id=batch_id),
    )
    lane_paths.latest_promoted_path.parent.mkdir(parents=True, exist_ok=True)
    lane_paths.latest_promoted_path.write_text("null", encoding="utf-8")

    monkeypatch.setattr(promotion_script, "utc_now", lambda: fixed_now)

    result = asyncio.run(
        promotion_script.run_legacy_promotion(
            tenant_id=TENANT_ID,
            schema_name="raw_legacy",
            source_schema="public",
            summary_root=summary_root,
        )
    )

    promotion_result = json.loads(result.result_path.read_text(encoding="utf-8"))

    assert result.exit_code == 1
    assert result.latest_promoted_updated is False
    assert promotion_result["blocking_gate"] == "invalid-promoted-state"


def test_run_legacy_promotion_blocks_when_latest_promoted_state_is_structurally_invalid(
    monkeypatch,
    tmp_path: Path,
) -> None:
    fixed_now = datetime(2026, 4, 18, 3, 55, 0, tzinfo=timezone.utc)
    batch_id = "legacy-shadow-20260418T025500Z"
    summary_root, lane_paths = _prepare_lane(
        tmp_path,
        batch_id=batch_id,
        summary_payload=_summary_payload(batch_id=batch_id),
    )
    write_json_atomically(lane_paths.latest_promoted_path, {})

    monkeypatch.setattr(promotion_script, "utc_now", lambda: fixed_now)

    result = asyncio.run(
        promotion_script.run_legacy_promotion(
            tenant_id=TENANT_ID,
            schema_name="raw_legacy",
            source_schema="public",
            summary_root=summary_root,
        )
    )

    promotion_result = json.loads(result.result_path.read_text(encoding="utf-8"))

    assert result.exit_code == 1
    assert result.latest_promoted_updated is False
    assert promotion_result["blocking_gate"] == "invalid-promoted-state"


def test_run_legacy_promotion_blocks_when_latest_promoted_state_is_not_promoted(
    monkeypatch,
    tmp_path: Path,
) -> None:
    fixed_now = datetime(2026, 4, 18, 4, 0, 0, tzinfo=timezone.utc)
    batch_id = "legacy-shadow-20260418T030000Z"
    summary_root, lane_paths = _prepare_lane(
        tmp_path,
        batch_id=batch_id,
        summary_payload=_summary_payload(batch_id=batch_id),
    )
    write_json_atomically(
        lane_paths.latest_promoted_path,
        {
            "batch_id": "legacy-shadow-20260417T020304Z",
            "tenant_id": str(TENANT_ID),
            "schema_name": "raw_legacy",
            "source_schema": "public",
            "promotion_result": "blocked",
        },
    )

    monkeypatch.setattr(promotion_script, "utc_now", lambda: fixed_now)

    result = asyncio.run(
        promotion_script.run_legacy_promotion(
            tenant_id=TENANT_ID,
            schema_name="raw_legacy",
            source_schema="public",
            summary_root=summary_root,
        )
    )

    promotion_result = json.loads(result.result_path.read_text(encoding="utf-8"))

    assert result.exit_code == 1
    assert result.latest_promoted_updated is False
    assert promotion_result["blocking_gate"] == "invalid-promoted-state"


def test_run_legacy_promotion_blocks_when_latest_promoted_state_has_non_string_batch_id(
    monkeypatch,
    tmp_path: Path,
) -> None:
    fixed_now = datetime(2026, 4, 18, 4, 2, 0, tzinfo=timezone.utc)
    batch_id = "legacy-shadow-20260418T030200Z"
    summary_root, lane_paths = _prepare_lane(
        tmp_path,
        batch_id=batch_id,
        summary_payload=_summary_payload(batch_id=batch_id),
    )
    invalid_pointer = _promoted_state(batch_id="legacy-shadow-20260417T020304Z")
    invalid_pointer["batch_id"] = {"corrupt": "value"}
    write_json_atomically(lane_paths.latest_promoted_path, invalid_pointer)

    monkeypatch.setattr(promotion_script, "utc_now", lambda: fixed_now)

    result = asyncio.run(
        promotion_script.run_legacy_promotion(
            tenant_id=TENANT_ID,
            schema_name="raw_legacy",
            source_schema="public",
            summary_root=summary_root,
        )
    )

    promotion_result = json.loads(result.result_path.read_text(encoding="utf-8"))

    assert result.exit_code == 1
    assert result.latest_promoted_updated is False
    assert promotion_result["blocking_gate"] == "invalid-promoted-state"


def test_run_legacy_promotion_blocks_when_latest_promoted_state_is_not_utf8(
    monkeypatch,
    tmp_path: Path,
) -> None:
    fixed_now = datetime(2026, 4, 18, 4, 5, 0, tzinfo=timezone.utc)
    batch_id = "legacy-shadow-20260418T030500Z"
    summary_root, lane_paths = _prepare_lane(
        tmp_path,
        batch_id=batch_id,
        summary_payload=_summary_payload(batch_id=batch_id),
    )
    lane_paths.latest_promoted_path.parent.mkdir(parents=True, exist_ok=True)
    lane_paths.latest_promoted_path.write_bytes(b"\xff\xfe\x00\x00")

    monkeypatch.setattr(promotion_script, "utc_now", lambda: fixed_now)

    result = asyncio.run(
        promotion_script.run_legacy_promotion(
            tenant_id=TENANT_ID,
            schema_name="raw_legacy",
            source_schema="public",
            summary_root=summary_root,
        )
    )

    promotion_result = json.loads(result.result_path.read_text(encoding="utf-8"))

    assert result.exit_code == 1
    assert result.latest_promoted_updated is False
    assert promotion_result["blocking_gate"] == "invalid-promoted-state"


def test_run_legacy_promotion_blocks_when_promotion_lock_is_held(
    monkeypatch,
    tmp_path: Path,
) -> None:
    fixed_now = datetime(2026, 4, 18, 4, 10, 0, tzinfo=timezone.utc)
    batch_id = "legacy-shadow-20260418T031000Z"
    summary_root, lane_paths = _prepare_lane(
        tmp_path,
        batch_id=batch_id,
        summary_payload=_summary_payload(batch_id=batch_id),
    )
    lane_paths.promotion_lock_path.parent.mkdir(parents=True, exist_ok=True)
    lane_paths.promotion_lock_path.write_text("locked", encoding="utf-8")

    monkeypatch.setattr(promotion_script, "utc_now", lambda: fixed_now)

    result = asyncio.run(
        promotion_script.run_legacy_promotion(
            tenant_id=TENANT_ID,
            schema_name="raw_legacy",
            source_schema="public",
            summary_root=summary_root,
        )
    )

    promotion_result = json.loads(result.result_path.read_text(encoding="utf-8"))

    assert result.exit_code == 1
    assert result.latest_promoted_updated is False
    assert promotion_result["blocking_gate"] == "promotion-in-progress"


def test_run_legacy_promotion_recovers_stale_promotion_lock(
    monkeypatch,
    tmp_path: Path,
) -> None:
    fixed_now = datetime(2026, 4, 18, 4, 20, 0, tzinfo=timezone.utc)
    batch_id = "legacy-shadow-20260418T032000Z"
    summary_root, lane_paths = _prepare_lane(
        tmp_path,
        batch_id=batch_id,
        summary_payload=_summary_payload(batch_id=batch_id),
    )
    write_json_atomically(
        lane_paths.latest_promoted_path,
        _promoted_state(batch_id="legacy-shadow-20260417T032000Z"),
    )
    lane_paths.promotion_lock_path.parent.mkdir(parents=True, exist_ok=True)
    lane_paths.promotion_lock_path.write_text(
        json.dumps(
            {
                "promotion_run_id": "stale-run",
                "acquired_at": "2026-04-17T20:00:00+00:00",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(promotion_script, "utc_now", lambda: fixed_now)

    result = asyncio.run(
        promotion_script.run_legacy_promotion(
            tenant_id=TENANT_ID,
            schema_name="raw_legacy",
            source_schema="public",
            summary_root=summary_root,
        )
    )

    latest_promoted = json.loads(lane_paths.latest_promoted_path.read_text(encoding="utf-8"))

    assert result.exit_code == 0
    assert result.latest_promoted_updated is True
    assert latest_promoted["batch_id"] == batch_id
    assert lane_paths.promotion_lock_path.exists() is False


def test_run_legacy_promotion_recovers_stale_scheduler_lock_before_evaluation(
    monkeypatch,
    tmp_path: Path,
) -> None:
    fixed_now = datetime(2026, 4, 18, 4, 25, 0, tzinfo=timezone.utc)
    batch_id = "legacy-shadow-20260418T032500Z"
    summary_root, lane_paths = _prepare_lane(
        tmp_path,
        batch_id=batch_id,
        summary_payload=_summary_payload(batch_id=batch_id),
    )
    write_json_atomically(
        lane_paths.latest_promoted_path,
        _promoted_state(batch_id="legacy-shadow-20260417T032500Z"),
    )
    lane_paths.lock_path.parent.mkdir(parents=True, exist_ok=True)
    lane_paths.lock_path.write_text(
        json.dumps(
            {
                "scheduler_run_id": "stale-scheduler",
                "started_at": "2026-04-17T20:00:00+00:00",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(promotion_script, "utc_now", lambda: fixed_now)

    result = asyncio.run(
        promotion_script.run_legacy_promotion(
            tenant_id=TENANT_ID,
            schema_name="raw_legacy",
            source_schema="public",
            summary_root=summary_root,
        )
    )

    latest_promoted = json.loads(lane_paths.latest_promoted_path.read_text(encoding="utf-8"))

    assert result.exit_code == 0
    assert result.latest_promoted_updated is True
    assert latest_promoted["batch_id"] == batch_id
    assert lane_paths.lock_path.exists() is False


def test_run_legacy_promotion_blocks_when_latest_success_state_is_not_utf8(
    monkeypatch,
    tmp_path: Path,
) -> None:
    fixed_now = datetime(2026, 4, 18, 4, 12, 0, tzinfo=timezone.utc)
    summary_root = tmp_path / "ops"
    lane_paths = build_lane_state_paths(
        tenant_id=TENANT_ID,
        schema_name="raw_legacy",
        source_schema="public",
        summary_root=summary_root,
    )
    lane_paths.latest_success_path.parent.mkdir(parents=True, exist_ok=True)
    lane_paths.latest_success_path.write_bytes(b"\xff\xfe\x00\x00")

    monkeypatch.setattr(promotion_script, "utc_now", lambda: fixed_now)

    result = asyncio.run(
        promotion_script.run_legacy_promotion(
            tenant_id=TENANT_ID,
            schema_name="raw_legacy",
            source_schema="public",
            summary_root=summary_root,
        )
    )

    promotion_result = json.loads(result.result_path.read_text(encoding="utf-8"))

    assert result.exit_code == 1
    assert result.latest_promoted_updated is False
    assert promotion_result["blocking_gate"] == "invalid-candidate-state"


def test_run_legacy_promotion_blocks_when_latest_success_state_is_not_an_object(
    monkeypatch,
    tmp_path: Path,
) -> None:
    fixed_now = datetime(2026, 4, 18, 4, 13, 0, tzinfo=timezone.utc)
    summary_root = tmp_path / "ops"
    lane_paths = build_lane_state_paths(
        tenant_id=TENANT_ID,
        schema_name="raw_legacy",
        source_schema="public",
        summary_root=summary_root,
    )
    lane_paths.latest_success_path.parent.mkdir(parents=True, exist_ok=True)
    lane_paths.latest_success_path.write_text("[]", encoding="utf-8")

    monkeypatch.setattr(promotion_script, "utc_now", lambda: fixed_now)

    result = asyncio.run(
        promotion_script.run_legacy_promotion(
            tenant_id=TENANT_ID,
            schema_name="raw_legacy",
            source_schema="public",
            summary_root=summary_root,
        )
    )

    promotion_result = json.loads(result.result_path.read_text(encoding="utf-8"))

    assert result.exit_code == 1
    assert result.latest_promoted_updated is False
    assert promotion_result["blocking_gate"] == "invalid-candidate-state"


def test_run_legacy_promotion_blocks_when_summary_artifact_is_invalid_json(
    monkeypatch,
    tmp_path: Path,
) -> None:
    fixed_now = datetime(2026, 4, 18, 4, 14, 0, tzinfo=timezone.utc)
    batch_id = "legacy-shadow-20260418T031400Z"
    summary_root, lane_paths = _prepare_lane(
        tmp_path,
        batch_id=batch_id,
        summary_payload=_summary_payload(batch_id=batch_id),
    )
    summary_path = Path(
        json.loads(lane_paths.latest_success_path.read_text(encoding="utf-8"))["summary_path"]
    )
    summary_path.write_text("{bad-json", encoding="utf-8")

    monkeypatch.setattr(promotion_script, "utc_now", lambda: fixed_now)

    result = asyncio.run(
        promotion_script.run_legacy_promotion(
            tenant_id=TENANT_ID,
            schema_name="raw_legacy",
            source_schema="public",
            summary_root=summary_root,
        )
    )

    promotion_result = json.loads(result.result_path.read_text(encoding="utf-8"))

    assert result.exit_code == 1
    assert result.latest_promoted_updated is False
    assert promotion_result["blocking_gate"] == "invalid-summary-artifact"


def test_run_legacy_promotion_blocks_when_candidate_state_changes_after_evaluation(
    monkeypatch,
    tmp_path: Path,
) -> None:
    fixed_now = datetime(2026, 4, 18, 4, 15, 0, tzinfo=timezone.utc)
    batch_id = "legacy-shadow-20260418T031500Z"
    summary_root, lane_paths = _prepare_lane(
        tmp_path,
        batch_id=batch_id,
        summary_payload=_summary_payload(batch_id=batch_id),
    )
    previous_pointer = _promoted_state(
        batch_id="legacy-shadow-20260417T020304Z",
        message="previous stable batch",
    )
    write_json_atomically(lane_paths.latest_promoted_path, previous_pointer)

    monkeypatch.setattr(promotion_script, "utc_now", lambda: fixed_now)

    original_evaluate_promotion = promotion_script.evaluate_promotion

    def mutate_latest_success_after_evaluation(*args, **kwargs):
        decision = original_evaluate_promotion(*args, **kwargs)
        latest_success_state = json.loads(
            lane_paths.latest_success_path.read_text(encoding="utf-8")
        )
        latest_success_state["batch_id"] = "legacy-shadow-20260418T031501Z"
        write_json_atomically(lane_paths.latest_success_path, latest_success_state)
        return decision

    monkeypatch.setattr(
        promotion_script,
        "evaluate_promotion",
        mutate_latest_success_after_evaluation,
    )

    result = asyncio.run(
        promotion_script.run_legacy_promotion(
            tenant_id=TENANT_ID,
            schema_name="raw_legacy",
            source_schema="public",
            summary_root=summary_root,
        )
    )

    latest_promoted = json.loads(lane_paths.latest_promoted_path.read_text(encoding="utf-8"))
    promotion_result = json.loads(result.result_path.read_text(encoding="utf-8"))

    assert result.exit_code == 1
    assert result.latest_promoted_updated is False
    assert latest_promoted == previous_pointer
    assert promotion_result["blocking_gate"] == "candidate-state-changed"


def test_run_legacy_promotion_blocks_when_same_candidate_gates_change_after_evaluation(
    monkeypatch,
    tmp_path: Path,
) -> None:
    fixed_now = datetime(2026, 4, 18, 4, 17, 0, tzinfo=timezone.utc)
    batch_id = "legacy-shadow-20260418T031700Z"
    summary_root, lane_paths = _prepare_lane(
        tmp_path,
        batch_id=batch_id,
        summary_payload=_summary_payload(batch_id=batch_id),
    )
    previous_pointer = _promoted_state(
        batch_id="legacy-shadow-20260417T020304Z",
        message="previous stable batch",
    )
    write_json_atomically(lane_paths.latest_promoted_path, previous_pointer)

    monkeypatch.setattr(promotion_script, "utc_now", lambda: fixed_now)

    original_evaluate_promotion = promotion_script.evaluate_promotion

    def mutate_same_candidate_after_evaluation(*args, **kwargs):
        decision = original_evaluate_promotion(*args, **kwargs)
        latest_success_state = json.loads(
            lane_paths.latest_success_path.read_text(encoding="utf-8")
        )
        latest_success_state["final_disposition"] = "failed"
        latest_success_state["promotion_readiness"] = False
        write_json_atomically(lane_paths.latest_success_path, latest_success_state)
        return decision

    monkeypatch.setattr(
        promotion_script,
        "evaluate_promotion",
        mutate_same_candidate_after_evaluation,
    )

    result = asyncio.run(
        promotion_script.run_legacy_promotion(
            tenant_id=TENANT_ID,
            schema_name="raw_legacy",
            source_schema="public",
            summary_root=summary_root,
        )
    )

    latest_promoted = json.loads(lane_paths.latest_promoted_path.read_text(encoding="utf-8"))
    promotion_result = json.loads(result.result_path.read_text(encoding="utf-8"))

    assert result.exit_code == 1
    assert result.latest_promoted_updated is False
    assert latest_promoted == previous_pointer
    assert promotion_result["blocking_gate"] == "candidate-state-changed"


def test_run_legacy_promotion_blocks_when_noop_candidate_state_changes_after_evaluation(
    monkeypatch,
    tmp_path: Path,
) -> None:
    fixed_now = datetime(2026, 4, 18, 4, 20, 0, tzinfo=timezone.utc)
    batch_id = "legacy-shadow-20260418T032000Z"
    summary_root, lane_paths = _prepare_lane(
        tmp_path,
        batch_id=batch_id,
        summary_payload=_summary_payload(batch_id=batch_id),
    )
    current_pointer = _promoted_state(batch_id=batch_id, message="already active")
    write_json_atomically(lane_paths.latest_promoted_path, current_pointer)

    monkeypatch.setattr(promotion_script, "utc_now", lambda: fixed_now)

    original_evaluate_promotion = promotion_script.evaluate_promotion

    def mutate_latest_success_after_noop_evaluation(*args, **kwargs):
        decision = original_evaluate_promotion(*args, **kwargs)
        latest_success_state = json.loads(
            lane_paths.latest_success_path.read_text(encoding="utf-8")
        )
        latest_success_state["batch_id"] = "legacy-shadow-20260418T032001Z"
        write_json_atomically(lane_paths.latest_success_path, latest_success_state)
        return decision

    monkeypatch.setattr(
        promotion_script,
        "evaluate_promotion",
        mutate_latest_success_after_noop_evaluation,
    )

    result = asyncio.run(
        promotion_script.run_legacy_promotion(
            tenant_id=TENANT_ID,
            schema_name="raw_legacy",
            source_schema="public",
            summary_root=summary_root,
        )
    )

    latest_promoted = json.loads(lane_paths.latest_promoted_path.read_text(encoding="utf-8"))
    promotion_result = json.loads(result.result_path.read_text(encoding="utf-8"))

    assert result.exit_code == 1
    assert result.latest_promoted_updated is False
    assert latest_promoted == current_pointer
    assert promotion_result["blocking_gate"] == "candidate-state-changed"


def test_run_legacy_promotion_blocks_when_promoted_pointer_changes_before_commit(
    monkeypatch,
    tmp_path: Path,
) -> None:
    fixed_now = datetime(2026, 4, 18, 4, 30, 0, tzinfo=timezone.utc)
    batch_id = "legacy-shadow-20260418T033000Z"
    summary_root, lane_paths = _prepare_lane(
        tmp_path,
        batch_id=batch_id,
        summary_payload=_summary_payload(batch_id=batch_id),
    )
    previous_pointer = _promoted_state(
        batch_id="legacy-shadow-20260417T033000Z",
        message="stable baseline",
    )
    drifted_pointer = _promoted_state(
        batch_id="legacy-shadow-20260418T032959Z",
        message="manual drift",
    )
    write_json_atomically(lane_paths.latest_promoted_path, previous_pointer)

    monkeypatch.setattr(promotion_script, "utc_now", lambda: fixed_now)

    original_evaluate_promotion = promotion_script.evaluate_promotion
    evaluation_calls = 0

    def mutate_promoted_pointer_after_first_evaluation(*args, **kwargs):
        nonlocal evaluation_calls
        decision = original_evaluate_promotion(*args, **kwargs)
        evaluation_calls += 1
        if evaluation_calls == 1:
            write_json_atomically(lane_paths.latest_promoted_path, drifted_pointer)
        return decision

    monkeypatch.setattr(
        promotion_script,
        "evaluate_promotion",
        mutate_promoted_pointer_after_first_evaluation,
    )

    result = asyncio.run(
        promotion_script.run_legacy_promotion(
            tenant_id=TENANT_ID,
            schema_name="raw_legacy",
            source_schema="public",
            summary_root=summary_root,
        )
    )

    latest_promoted = json.loads(lane_paths.latest_promoted_path.read_text(encoding="utf-8"))
    promotion_result = json.loads(result.result_path.read_text(encoding="utf-8"))

    assert result.exit_code == 1
    assert result.latest_promoted_updated is False
    assert latest_promoted == drifted_pointer
    assert promotion_result["blocking_gate"] == "promoted-state-changed"


def test_run_legacy_promotion_blocks_when_noop_pointer_changes_before_commit(
    monkeypatch,
    tmp_path: Path,
) -> None:
    fixed_now = datetime(2026, 4, 18, 4, 32, 0, tzinfo=timezone.utc)
    batch_id = "legacy-shadow-20260418T033200Z"
    summary_root, lane_paths = _prepare_lane(
        tmp_path,
        batch_id=batch_id,
        summary_payload=_summary_payload(batch_id=batch_id),
    )
    current_pointer = _promoted_state(batch_id=batch_id, message="already active")
    drifted_pointer = _promoted_state(
        batch_id="legacy-shadow-20260418T033159Z",
        message="manual drift",
    )
    write_json_atomically(lane_paths.latest_promoted_path, current_pointer)

    monkeypatch.setattr(promotion_script, "utc_now", lambda: fixed_now)

    original_evaluate_promotion = promotion_script.evaluate_promotion
    evaluation_calls = 0

    def mutate_noop_pointer_after_first_evaluation(*args, **kwargs):
        nonlocal evaluation_calls
        decision = original_evaluate_promotion(*args, **kwargs)
        evaluation_calls += 1
        if evaluation_calls == 1:
            write_json_atomically(lane_paths.latest_promoted_path, drifted_pointer)
        return decision

    monkeypatch.setattr(
        promotion_script,
        "evaluate_promotion",
        mutate_noop_pointer_after_first_evaluation,
    )

    result = asyncio.run(
        promotion_script.run_legacy_promotion(
            tenant_id=TENANT_ID,
            schema_name="raw_legacy",
            source_schema="public",
            summary_root=summary_root,
        )
    )

    latest_promoted = json.loads(lane_paths.latest_promoted_path.read_text(encoding="utf-8"))
    promotion_result = json.loads(result.result_path.read_text(encoding="utf-8"))

    assert result.exit_code == 1
    assert result.latest_promoted_updated is False
    assert latest_promoted == drifted_pointer
    assert promotion_result["blocking_gate"] == "promoted-state-changed"