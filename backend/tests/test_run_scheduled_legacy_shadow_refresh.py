from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

import domains.legacy_import.incremental_state as incremental_state
from domains.legacy_import.staging import LegacySourceConnectionSettings
from scripts import run_scheduled_legacy_shadow_refresh as scheduled
from scripts.run_legacy_refresh import LegacyRefreshExecution

TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _connection_settings() -> LegacySourceConnectionSettings:
    return LegacySourceConnectionSettings(
        host="legacy-db.internal",
        port=5432,
        user="postgres",
        password="secret",
        database="cao50001",
        client_encoding="BIG5",
    )


def _build_execution(
    summary_root: Path,
    *,
    batch_id: str,
    final_disposition: str,
    exit_code: int,
    validation_status: str,
    blocking_issue_count: int | None,
    reconciliation_gap_count: int | None,
    analyst_review_required: bool,
    promotion_readiness: bool,
    summary_name: str,
) -> LegacyRefreshExecution:
    summary_path = summary_root / summary_name
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text("{}\n", encoding="utf-8")
    if final_disposition == "completed-review-required":
        promotion_policy = {
            "classification": "exception-required",
            "reason_codes": ["analyst-review"],
        }
    elif validation_status != "passed" or (blocking_issue_count or 0) > 0:
        promotion_policy = {
            "classification": "blocked",
            "reason_codes": ["validation"],
        }
    elif reconciliation_gap_count not in {None, 0}:
        promotion_policy = {
            "classification": "blocked",
            "reason_codes": ["reconciliation"],
        }
    else:
        promotion_policy = {
            "classification": "eligible",
            "reason_codes": [],
        }
    return LegacyRefreshExecution(
        exit_code=exit_code,
        summary_path=summary_path,
        summary={
            "batch_id": batch_id,
            "final_disposition": final_disposition,
            "reconciliation_gap_count": reconciliation_gap_count,
            "analyst_review_required": analyst_review_required,
            "promotion_readiness": promotion_readiness,
            "promotion_policy": promotion_policy,
            "promotion_gate_status": {
                "validation": {
                    "status": validation_status,
                    "blocking_issue_count": blocking_issue_count,
                }
            },
        },
    )


def test_build_shadow_batch_id_uses_utc_timestamp() -> None:
    now = datetime(2026, 4, 18, 2, 3, 4, tzinfo=timezone.utc)

    batch_id = scheduled.build_shadow_batch_id("legacy-shadow", now=now)

    assert batch_id == "legacy-shadow-20260418T020304Z"
    assert scheduled.build_shadow_batch_id(
        "legacy-shadow",
        now=now.replace(second=5),
    ) != batch_id


def test_run_scheduled_shadow_refresh_updates_latest_run_and_latest_success(
    monkeypatch,
    tmp_path: Path,
) -> None:
    summary_root = tmp_path / "ops"
    fixed_now = datetime(2026, 4, 18, 2, 3, 4, tzinfo=timezone.utc)
    batch_id = "legacy-shadow-20260418T020304Z"
    refresh_execution = _build_execution(
        summary_root,
        batch_id=batch_id,
        final_disposition="completed",
        exit_code=0,
        validation_status="passed",
        blocking_issue_count=0,
        reconciliation_gap_count=0,
        analyst_review_required=False,
        promotion_readiness=True,
        summary_name="refresh-success.json",
    )

    monkeypatch.setattr(scheduled, "utc_now", lambda: fixed_now)

    async def fake_run_legacy_refresh(**kwargs):
        assert kwargs == {
            "batch_id": batch_id,
            "tenant_id": TENANT_ID,
            "schema_name": "raw_legacy",
            "source_schema": "public",
            "lookback_days": 10000,
            "reconciliation_threshold": 0,
            "summary_root": summary_root,
        }
        return refresh_execution

    monkeypatch.setattr(scheduled, "run_legacy_refresh", fake_run_legacy_refresh)

    result = asyncio.run(
        scheduled.run_scheduled_shadow_refresh(
            tenant_id=TENANT_ID,
            schema_name="raw_legacy",
            source_schema="public",
            lookback_days=10000,
            reconciliation_threshold=0,
            batch_prefix="legacy-shadow",
            summary_root=summary_root,
        )
    )

    latest_run = json.loads(result.latest_run_path.read_text(encoding="utf-8"))
    latest_success = json.loads(result.latest_success_path.read_text(encoding="utf-8"))

    assert result.exit_code == 0
    assert result.latest_success_updated is True
    assert latest_run == latest_success
    assert latest_run["scheduler_run_id"] == result.scheduler_run_id
    assert latest_run["batch_id"] == batch_id
    assert latest_run["summary_path"] == str(refresh_execution.summary_path)
    assert latest_run["final_disposition"] == "completed"
    assert latest_run["validation_status"] == "passed"
    assert latest_run["blocking_issue_count"] == 0
    assert latest_run["reconciliation_gap_count"] == 0
    assert latest_run["analyst_review_required"] is False
    assert latest_run["promotion_readiness"] is True
    assert latest_run["promotion_policy"]["classification"] == "eligible"
    assert latest_run["promotion_policy"]["reason_codes"] == []


def test_run_scheduled_shadow_refresh_forwards_connection_settings(
    monkeypatch,
    tmp_path: Path,
) -> None:
    summary_root = tmp_path / "ops"
    fixed_now = datetime(2026, 4, 18, 2, 3, 4, tzinfo=timezone.utc)
    batch_id = "legacy-shadow-20260418T020304Z"
    refresh_execution = _build_execution(
        summary_root,
        batch_id=batch_id,
        final_disposition="completed",
        exit_code=0,
        validation_status="passed",
        blocking_issue_count=0,
        reconciliation_gap_count=0,
        analyst_review_required=False,
        promotion_readiness=True,
        summary_name="refresh-success.json",
    )
    connection_settings = _connection_settings()
    captured: dict[str, object] = {}

    monkeypatch.setattr(scheduled, "utc_now", lambda: fixed_now)

    async def fake_run_legacy_refresh(**kwargs):
        captured.update(kwargs)
        return refresh_execution

    monkeypatch.setattr(scheduled, "run_legacy_refresh", fake_run_legacy_refresh)

    asyncio.run(
        scheduled.run_scheduled_shadow_refresh(
            tenant_id=TENANT_ID,
            schema_name="raw_legacy",
            source_schema="public",
            lookback_days=10000,
            reconciliation_threshold=0,
            batch_prefix="legacy-shadow",
            summary_root=summary_root,
            connection_settings=connection_settings,
        )
    )

    assert captured["connection_settings"] == connection_settings


def test_completed_review_required_still_advances_latest_success(
    monkeypatch,
    tmp_path: Path,
) -> None:
    summary_root = tmp_path / "ops"
    fixed_now = datetime(2026, 4, 18, 2, 5, 0, tzinfo=timezone.utc)
    batch_id = "legacy-shadow-20260418T020500Z"
    refresh_execution = _build_execution(
        summary_root,
        batch_id=batch_id,
        final_disposition="completed-review-required",
        exit_code=0,
        validation_status="passed",
        blocking_issue_count=0,
        reconciliation_gap_count=0,
        analyst_review_required=True,
        promotion_readiness=False,
        summary_name="refresh-review-required.json",
    )

    monkeypatch.setattr(scheduled, "utc_now", lambda: fixed_now)

    async def fake_run_legacy_refresh(**kwargs):
        return refresh_execution

    monkeypatch.setattr(scheduled, "run_legacy_refresh", fake_run_legacy_refresh)

    result = asyncio.run(
        scheduled.run_scheduled_shadow_refresh(
            tenant_id=TENANT_ID,
            schema_name="raw_legacy",
            source_schema="public",
            lookback_days=10000,
            reconciliation_threshold=0,
            batch_prefix="legacy-shadow",
            summary_root=summary_root,
        )
    )

    latest_success = json.loads(result.latest_success_path.read_text(encoding="utf-8"))
    lane_paths = scheduled.build_lane_state_paths(
        tenant_id=TENANT_ID,
        schema_name="raw_legacy",
        source_schema="public",
        summary_root=summary_root,
    )

    assert result.exit_code == 0
    assert result.latest_success_updated is True
    assert latest_success["final_disposition"] == "completed-review-required"
    assert latest_success["analyst_review_required"] is True
    assert latest_success["promotion_readiness"] is False
    assert latest_success["promotion_policy"]["classification"] == "exception-required"
    assert latest_success["promotion_policy"]["reason_codes"] == ["analyst-review"]
    assert lane_paths.incremental_state_path.exists() is False
    assert lane_paths.nightly_rebaseline_path.exists() is False


def test_successful_full_refresh_reseeds_incremental_state_and_rebaseline_reference(
    monkeypatch,
    tmp_path: Path,
) -> None:
    summary_root = tmp_path / "ops"
    fixed_now = datetime(2026, 4, 18, 2, 7, 0, tzinfo=timezone.utc)
    batch_id = "legacy-shadow-20260418T020700Z"
    refresh_execution = _build_execution(
        summary_root,
        batch_id=batch_id,
        final_disposition="completed",
        exit_code=0,
        validation_status="passed",
        blocking_issue_count=0,
        reconciliation_gap_count=0,
        analyst_review_required=False,
        promotion_readiness=True,
        summary_name="refresh-rebaseline.json",
    )

    monkeypatch.setattr(scheduled, "utc_now", lambda: fixed_now)

    async def fake_run_legacy_refresh(**kwargs):
        return refresh_execution

    monkeypatch.setattr(scheduled, "run_legacy_refresh", fake_run_legacy_refresh)

    result = asyncio.run(
        scheduled.run_scheduled_shadow_refresh(
            tenant_id=TENANT_ID,
            schema_name="raw_legacy",
            source_schema="public",
            lookback_days=10000,
            reconciliation_threshold=0,
            batch_prefix="legacy-shadow",
            summary_root=summary_root,
        )
    )

    lane_paths = scheduled.build_lane_state_paths(
        tenant_id=TENANT_ID,
        schema_name="raw_legacy",
        source_schema="public",
        summary_root=summary_root,
    )
    incremental_snapshot = json.loads(
        lane_paths.incremental_state_path.read_text(encoding="utf-8")
    )
    nightly_rebaseline = json.loads(
        lane_paths.nightly_rebaseline_path.read_text(encoding="utf-8")
    )

    assert result.latest_success_updated is True
    assert nightly_rebaseline["batch_id"] == batch_id
    assert incremental_snapshot["current_shadow_candidate"]["batch_id"] == batch_id
    assert incremental_snapshot["last_successful_shadow_candidate"]["batch_id"] == batch_id
    assert incremental_snapshot["last_nightly_full_rebaseline"]["batch_id"] == batch_id
    assert incremental_snapshot["latest_promoted_working_batch"] is None
    assert set(incremental_snapshot["domains"]) == {
        contract.name for contract in incremental_state.supported_incremental_domain_contracts()
    }
    assert all(
        domain_state["bootstrap_required"] is True
        and domain_state["last_successful_watermark"] is None
        for domain_state in incremental_snapshot["domains"].values()
    )


@pytest.mark.parametrize(
    (
        "disposition",
        "validation_status",
        "blocking_issue_count",
        "reconciliation_gap_count",
    ),
    [
        ("failed", "not-run", None, None),
        ("validation-blocked", "blocked", 2, None),
        ("reconciliation-blocked", "passed", 0, 3),
    ],
)
def test_unsuccessful_runs_update_latest_run_without_replacing_latest_success(
    monkeypatch,
    tmp_path: Path,
    disposition: str,
    validation_status: str,
    blocking_issue_count: int | None,
    reconciliation_gap_count: int | None,
) -> None:
    summary_root = tmp_path / "ops"

    success_now = datetime(2026, 4, 18, 2, 10, 0, tzinfo=timezone.utc)
    success_batch_id = "legacy-shadow-20260418T021000Z"
    success_execution = _build_execution(
        summary_root,
        batch_id=success_batch_id,
        final_disposition="completed",
        exit_code=0,
        validation_status="passed",
        blocking_issue_count=0,
        reconciliation_gap_count=0,
        analyst_review_required=False,
        promotion_readiness=True,
        summary_name="refresh-initial-success.json",
    )
    monkeypatch.setattr(scheduled, "utc_now", lambda: success_now)

    async def fake_success(**kwargs):
        return success_execution

    monkeypatch.setattr(scheduled, "run_legacy_refresh", fake_success)
    first_result = asyncio.run(
        scheduled.run_scheduled_shadow_refresh(
            tenant_id=TENANT_ID,
            schema_name="raw_legacy",
            source_schema="public",
            lookback_days=10000,
            reconciliation_threshold=0,
            batch_prefix="legacy-shadow",
            summary_root=summary_root,
        )
    )
    expected_success = json.loads(
        first_result.latest_success_path.read_text(encoding="utf-8")
    )

    failure_now = datetime(2026, 4, 18, 2, 11, 0, tzinfo=timezone.utc)
    failure_batch_id = "legacy-shadow-20260418T021100Z"
    failure_execution = _build_execution(
        summary_root,
        batch_id=failure_batch_id,
        final_disposition=disposition,
        exit_code=1,
        validation_status=validation_status,
        blocking_issue_count=blocking_issue_count,
        reconciliation_gap_count=reconciliation_gap_count,
        analyst_review_required=False,
        promotion_readiness=False,
        summary_name=f"refresh-{disposition}.json",
    )
    monkeypatch.setattr(scheduled, "utc_now", lambda: failure_now)

    async def fake_failure(**kwargs):
        return failure_execution

    monkeypatch.setattr(scheduled, "run_legacy_refresh", fake_failure)
    second_result = asyncio.run(
        scheduled.run_scheduled_shadow_refresh(
            tenant_id=TENANT_ID,
            schema_name="raw_legacy",
            source_schema="public",
            lookback_days=10000,
            reconciliation_threshold=0,
            batch_prefix="legacy-shadow",
            summary_root=summary_root,
        )
    )

    latest_run = json.loads(second_result.latest_run_path.read_text(encoding="utf-8"))
    latest_success = json.loads(
        second_result.latest_success_path.read_text(encoding="utf-8")
    )

    assert second_result.exit_code == 1
    assert second_result.latest_success_updated is False
    assert latest_run["batch_id"] == failure_batch_id
    assert latest_run["final_disposition"] == disposition
    assert latest_success == expected_success


def test_failed_refresh_persists_detailed_failure_fields(
    monkeypatch,
    tmp_path: Path,
) -> None:
    summary_root = tmp_path / "ops"
    fixed_now = datetime(2026, 4, 18, 2, 12, 0, tzinfo=timezone.utc)
    batch_id = "legacy-shadow-20260418T021200Z"
    refresh_execution = _build_execution(
        summary_root,
        batch_id=batch_id,
        final_disposition="failed",
        exit_code=1,
        validation_status="pending",
        blocking_issue_count=None,
        reconciliation_gap_count=None,
        analyst_review_required=False,
        promotion_readiness=False,
        summary_name="refresh-detailed-failure.json",
    )
    refresh_execution.summary.update(
        {
            "root_failed_step": "live-stage",
            "root_error_message": "Missing legacy source settings: LEGACY_DB_HOST",
            "rebaseline_reason": (
                "Step live-stage failed: Missing legacy source settings: LEGACY_DB_HOST"
            ),
            "batch_mode": "full-rebaseline",
            "affected_domains": ["sales"],
        }
    )

    monkeypatch.setattr(scheduled, "utc_now", lambda: fixed_now)

    async def fake_failure(**kwargs):
        return refresh_execution

    monkeypatch.setattr(scheduled, "run_legacy_refresh", fake_failure)

    result = asyncio.run(
        scheduled.run_scheduled_shadow_refresh(
            tenant_id=TENANT_ID,
            schema_name="raw_legacy",
            source_schema="public",
            lookback_days=10000,
            reconciliation_threshold=0,
            batch_prefix="legacy-shadow",
            summary_root=summary_root,
        )
    )

    latest_run = json.loads(result.latest_run_path.read_text(encoding="utf-8"))

    assert latest_run["root_failed_step"] == "live-stage"
    assert latest_run["root_error_message"] == "Missing legacy source settings: LEGACY_DB_HOST"
    assert latest_run["rebaseline_reason"] == (
        "Step live-stage failed: Missing legacy source settings: LEGACY_DB_HOST"
    )
    assert latest_run["batch_mode"] == "full-rebaseline"
    assert latest_run["affected_domains"] == ["sales"]


def test_overlap_preserves_previous_latest_success(monkeypatch, tmp_path: Path) -> None:
    summary_root = tmp_path / "ops"

    success_now = datetime(2026, 4, 18, 2, 20, 0, tzinfo=timezone.utc)
    success_batch_id = "legacy-shadow-20260418T022000Z"
    success_execution = _build_execution(
        summary_root,
        batch_id=success_batch_id,
        final_disposition="completed",
        exit_code=0,
        validation_status="passed",
        blocking_issue_count=0,
        reconciliation_gap_count=0,
        analyst_review_required=False,
        promotion_readiness=True,
        summary_name="refresh-overlap-baseline.json",
    )

    monkeypatch.setattr(scheduled, "utc_now", lambda: success_now)

    async def fake_success(**kwargs):
        return success_execution

    monkeypatch.setattr(scheduled, "run_legacy_refresh", fake_success)
    first_result = asyncio.run(
        scheduled.run_scheduled_shadow_refresh(
            tenant_id=TENANT_ID,
            schema_name="raw_legacy",
            source_schema="public",
            lookback_days=10000,
            reconciliation_threshold=0,
            batch_prefix="legacy-shadow",
            summary_root=summary_root,
        )
    )
    expected_success = json.loads(
        first_result.latest_success_path.read_text(encoding="utf-8")
    )

    lock_path = first_result.latest_run_path.parent / "scheduler.lock"
    lock_path.write_text(
        json.dumps(
            {
                "scheduler_run_id": "existing-run",
                "batch_id": "legacy-shadow-existing",
                "started_at": "2026-04-18T02:19:00+00:00",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    overlap_now = datetime(2026, 4, 18, 2, 21, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(scheduled, "utc_now", lambda: overlap_now)

    async def fail_if_called(**kwargs):
        raise AssertionError("run_legacy_refresh should not run when a lock exists")

    monkeypatch.setattr(scheduled, "run_legacy_refresh", fail_if_called)
    second_result = asyncio.run(
        scheduled.run_scheduled_shadow_refresh(
            tenant_id=TENANT_ID,
            schema_name="raw_legacy",
            source_schema="public",
            lookback_days=10000,
            reconciliation_threshold=0,
            batch_prefix="legacy-shadow",
            summary_root=summary_root,
        )
    )

    latest_run = json.loads(second_result.latest_run_path.read_text(encoding="utf-8"))
    latest_success = json.loads(
        second_result.latest_success_path.read_text(encoding="utf-8")
    )

    assert second_result.exit_code == scheduled.DEFAULT_OVERLAP_EXIT_CODE
    assert second_result.latest_success_updated is False
    assert latest_run["final_disposition"] == "overlap-blocked"
    assert latest_run["summary_path"] is None
    assert latest_run["promotion_policy"]["classification"] == "blocked"
    assert latest_run["promotion_policy"]["reason_codes"] == ["lane-unstable"]
    assert latest_run["overlap_lock"]["path"] == str(lock_path)
    assert latest_success == expected_success


def test_stale_scheduler_lock_is_recovered_before_refresh(
    monkeypatch,
    tmp_path: Path,
) -> None:
    summary_root = tmp_path / "ops"
    fixed_now = datetime(2026, 4, 18, 2, 40, 0, tzinfo=timezone.utc)
    batch_id = "legacy-shadow-20260418T024000Z"
    refresh_execution = _build_execution(
        summary_root,
        batch_id=batch_id,
        final_disposition="completed",
        exit_code=0,
        validation_status="passed",
        blocking_issue_count=0,
        reconciliation_gap_count=0,
        analyst_review_required=False,
        promotion_readiness=True,
        summary_name="refresh-stale-lock.json",
    )
    lane_root = (
        summary_root
        / "state"
        / "raw_legacy-00000000-0000-0000-0000-000000000001-public"
    )
    lock_path = lane_root / "scheduler.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(
        json.dumps(
            {
                "scheduler_run_id": "stale-run",
                "batch_id": "legacy-shadow-stale",
                "started_at": "2026-04-17T18:00:00+00:00",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(scheduled, "utc_now", lambda: fixed_now)

    async def fake_run_legacy_refresh(**kwargs):
        return refresh_execution

    monkeypatch.setattr(scheduled, "run_legacy_refresh", fake_run_legacy_refresh)

    result = asyncio.run(
        scheduled.run_scheduled_shadow_refresh(
            tenant_id=TENANT_ID,
            schema_name="raw_legacy",
            source_schema="public",
            lookback_days=10000,
            reconciliation_threshold=0,
            batch_prefix="legacy-shadow",
            summary_root=summary_root,
        )
    )

    latest_run = json.loads(result.latest_run_path.read_text(encoding="utf-8"))

    assert result.exit_code == 0
    assert result.latest_success_updated is True
    assert latest_run["batch_id"] == batch_id
    assert lock_path.exists() is False


def test_shadow_refresh_only_writes_inside_shadow_artifact_tree(
    monkeypatch,
    tmp_path: Path,
) -> None:
    summary_root = tmp_path / "ops"
    fixed_now = datetime(2026, 4, 18, 2, 30, 0, tzinfo=timezone.utc)
    batch_id = "legacy-shadow-20260418T023000Z"
    refresh_execution = _build_execution(
        summary_root,
        batch_id=batch_id,
        final_disposition="completed",
        exit_code=0,
        validation_status="passed",
        blocking_issue_count=0,
        reconciliation_gap_count=0,
        analyst_review_required=False,
        promotion_readiness=True,
        summary_name="refresh-shadow-only.json",
    )

    monkeypatch.setattr(scheduled, "utc_now", lambda: fixed_now)

    async def fake_run_legacy_refresh(**kwargs):
        return refresh_execution

    monkeypatch.setattr(scheduled, "run_legacy_refresh", fake_run_legacy_refresh)

    result = asyncio.run(
        scheduled.run_scheduled_shadow_refresh(
            tenant_id=TENANT_ID,
            schema_name="raw_legacy",
            source_schema="public",
            lookback_days=10000,
            reconciliation_threshold=0,
            batch_prefix="legacy-shadow",
            summary_root=summary_root,
        )
    )

    written_files = {
        path.relative_to(tmp_path).as_posix()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    lane_paths = scheduled.build_lane_state_paths(
        tenant_id=TENANT_ID,
        schema_name="raw_legacy",
        source_schema="public",
        summary_root=summary_root,
    )

    assert written_files == {
        refresh_execution.summary_path.relative_to(tmp_path).as_posix(),
        result.latest_run_path.relative_to(tmp_path).as_posix(),
        result.latest_success_path.relative_to(tmp_path).as_posix(),
        lane_paths.incremental_state_path.relative_to(tmp_path).as_posix(),
        lane_paths.nightly_rebaseline_path.relative_to(tmp_path).as_posix(),
    }
    assert all("promotion" not in path for path in written_files)
    assert all("approval" not in path for path in written_files)