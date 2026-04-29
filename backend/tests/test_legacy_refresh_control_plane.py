"""Tests for the legacy refresh admin control plane (Story 15.28).

AC1: Admin can trigger full rebaseline or incremental refresh.
AC2: Status API returns lane state, batch pointers, promotion-policy outcome.
AC3: Concurrent refresh blocked with lane-lock semantics.
AC4: Admin UI polls status surface for progress.
AC5: Durable worker boundary (not BackgroundTasks).
"""

from __future__ import annotations

import json
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest
import domains.legacy_import.routes as legacy_refresh_routes

from domains.legacy_import.staging import (
    LegacySourceCompatibilityError,
    LegacySourceConnectionSettings,
)
from domains.legacy_import.routes import (
    RefreshConflict,
    RefreshJobLaunched,
    RefreshLaneStatus,
    RefreshMode,
    RefreshTriggerRequest,
    _iso_now,
    _load_lane_status,
)
from scripts.legacy_refresh_common import RefreshDisposition
from scripts.legacy_refresh_state import (
    build_lane_state_paths,
    write_json_atomically,
)
from scripts.run_legacy_refresh import DEFAULT_SUMMARY_ROOT
from tests.domains.orders._helpers import (
    auth_header,
    http_get,
    http_post,
    setup_session,
    teardown_session,
    FakeAsyncSession,
)


# ── Fixtures ───────────────────────────────────────────────────

@pytest.fixture
def temp_lane(tmp_path: Path) -> tuple[Path, uuid.UUID, str, str]:
    """Create a temp lane directory with paths like the real state structure."""
    tenant_id = uuid.uuid4()
    schema_name = "test_schema"
    source_schema = "public"
    lane_paths = build_lane_state_paths(
        tenant_id=tenant_id,
        schema_name=schema_name,
        source_schema=source_schema,
        summary_root=tmp_path,
        state_root=tmp_path / "state",
    )
    lane_paths.lane_root.mkdir(parents=True, exist_ok=True)
    return tmp_path, tenant_id, schema_name, source_schema


@pytest.fixture
def completed_run(temp_lane: tuple[Path, uuid.UUID, str, str]) -> dict:
    """Write a completed run record to the lane's latest-run.json using the temp path."""
    tmp_path, tenant_id, schema_name, source_schema = temp_lane
    lane_paths = build_lane_state_paths(
        tenant_id=tenant_id,
        schema_name=schema_name,
        source_schema=source_schema,
        summary_root=tmp_path,
    )
    record = {
        "state_version": 1,
        "scheduler_run_id": str(uuid.uuid4()),
        "batch_id": "legacy-shadow-20240424T120000Z",
        "summary_path": str(tmp_path / "summary.json"),
        "started_at": "2024-04-24T12:00:00+00:00",
        "completed_at": "2024-04-24T12:05:00+00:00",
        "final_disposition": RefreshDisposition.COMPLETED.value,
        "exit_code": 0,
        "validation_status": "passed",
        "blocking_issue_count": 0,
        "reconciliation_gap_count": 0,
        "promotion_policy": {
            "classification": "eligible",
            "reason_codes": [],
        },
    }
    write_json_atomically(lane_paths.latest_run_path, record)
    write_json_atomically(lane_paths.latest_success_path, record)
    return record


class FakeRedis:
    def __init__(self, initial: dict[str, Any] | None = None):
        self.store = dict(initial or {})

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        self.store[key] = value

    async def get(self, key: str) -> str | None:
        return self.store.get(key)


def _test_connection_settings() -> LegacySourceConnectionSettings:
    return LegacySourceConnectionSettings(
        host="legacy-db.internal",
        port=5432,
        user="postgres",
        password="secret",
        database="cao50001",
        client_encoding="BIG5",
    )


@pytest.fixture(autouse=True)
def configured_legacy_source_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_load_runtime_legacy_source_connection_settings(*_args, **_kwargs):
        return _test_connection_settings()

    monkeypatch.setattr(
        legacy_refresh_routes,
        "load_runtime_legacy_source_connection_settings",
        fake_load_runtime_legacy_source_connection_settings,
    )


# ── AC1: Trigger endpoint ──────────────────────────────────────


@pytest.mark.asyncio
async def test_trigger_requires_admin_role():
    """Non-admin roles receive 403 Forbidden."""
    session = FakeAsyncSession()
    previous = setup_session(session)
    try:
        resp = await http_post(
            "/api/v1/admin/legacy-refresh/trigger",
            json={
                "tenant_id": str(uuid.uuid4()),
                "schema_name": "test_schema",
                "mode": "incremental",
            },
            headers=auth_header("finance"),
        )
        assert resp.status_code == 403
    finally:
        teardown_session(previous)


@pytest.mark.asyncio
async def test_trigger_requires_tenant_id():
    """Trigger request without tenant_id returns 422."""
    session = FakeAsyncSession()
    previous = setup_session(session)
    try:
        resp = await http_post(
            "/api/v1/admin/legacy-refresh/trigger",
            json={
                "schema_name": "test_schema",
                "mode": "incremental",
            },
        )
        assert resp.status_code == 422
    finally:
        teardown_session(previous)


@pytest.mark.asyncio
async def test_trigger_incremental_requires_bootstrap_state() -> None:
    """Incremental trigger is rejected until a full rebaseline seeds lane state."""
    session = FakeAsyncSession()
    previous = setup_session(session)
    try:
        resp = await http_post(
            "/api/v1/admin/legacy-refresh/trigger",
            json={
                "tenant_id": str(uuid.uuid4()),
                "schema_name": "test_schema",
                "source_schema": "public",
                "mode": "incremental",
                "lookback_days": 7,
                "reconciliation_threshold": 0,
            },
        )
        assert resp.status_code == 202
        data = resp.json()
        assert data["conflict"] == "incremental-bootstrap-required"
        assert "Run a full rebaseline" in data["detail"]
    finally:
        teardown_session(previous)


@pytest.mark.asyncio
async def test_trigger_full_rebaseline_mode_valid() -> None:
    """Trigger with valid full-rebaseline payload returns 202."""
    session = FakeAsyncSession()
    previous = setup_session(session)
    try:
        resp = await http_post(
            "/api/v1/admin/legacy-refresh/trigger",
            json={
                "tenant_id": str(uuid.uuid4()),
                "schema_name": "test_schema",
                "mode": "full-rebaseline",
            },
        )
        assert resp.status_code == 202
        data = resp.json()
        assert data["mode"] == "full-rebaseline"
    finally:
        teardown_session(previous)


@pytest.mark.asyncio
async def test_trigger_full_rebaseline_requires_legacy_source_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = FakeAsyncSession()
    previous = setup_session(session)

    async def fake_missing_runtime_legacy_source_connection_settings(*_args, **_kwargs):
        raise LegacySourceCompatibilityError(
            "Missing legacy source settings: LEGACY_DB_HOST, LEGACY_DB_USER"
        )

    monkeypatch.setattr(
        legacy_refresh_routes,
        "load_runtime_legacy_source_connection_settings",
        fake_missing_runtime_legacy_source_connection_settings,
    )
    try:
        resp = await http_post(
            "/api/v1/admin/legacy-refresh/trigger",
            json={
                "tenant_id": str(uuid.uuid4()),
                "schema_name": "test_schema",
                "mode": "full-rebaseline",
            },
        )
        assert resp.status_code == 202
        data = resp.json()
        assert data["conflict"] == "legacy-source-settings-missing"
        assert "LEGACY_DB_HOST" in data["detail"]
    finally:
        teardown_session(previous)


@pytest.mark.asyncio
async def test_trigger_passes_returned_batch_id_into_worker(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}
    tenant_id = uuid.uuid4()
    summary_root = Path(tempfile.mkdtemp())

    lane_paths = build_lane_state_paths(
        tenant_id=tenant_id,
        schema_name="test_schema",
        source_schema="public",
        summary_root=summary_root,
    )
    lane_paths.lane_root.mkdir(parents=True, exist_ok=True)
    write_json_atomically(
        lane_paths.incremental_state_path,
        {"bootstrap_required": False, "domains": {}},
    )

    async def fake_get_redis() -> FakeRedis:
        return FakeRedis()

    def fake_launch_incremental(**kwargs: Any):
        captured.update(kwargs)

        async def _noop() -> None:
            return None

        return _noop()

    def fake_create_task(coro: Any) -> None:
        coro.close()
        return None

    monkeypatch.setattr(legacy_refresh_routes, "_get_redis", fake_get_redis)
    monkeypatch.setattr(legacy_refresh_routes, "_launch_incremental", fake_launch_incremental)
    monkeypatch.setattr(legacy_refresh_routes.asyncio, "create_task", fake_create_task)
    monkeypatch.setattr(legacy_refresh_routes, "DEFAULT_SUMMARY_ROOT", summary_root)
    monkeypatch.setattr(
        legacy_refresh_routes,
        "build_incremental_plan_for_dry_run",
        lambda **kwargs: {"domains": {}, "bootstrap_required": False},
    )

    result = await legacy_refresh_routes.trigger_legacy_refresh(
        RefreshTriggerRequest(
            tenant_id=tenant_id,
            schema_name="test_schema",
            source_schema="public",
            mode=RefreshMode.INCREMENTAL,
        ),
        {"sub": "admin@example.com", "role": "admin"},
    )

    assert isinstance(result, RefreshJobLaunched)
    assert captured["batch_id"] == result.batch_id
    assert captured["launched_at"] == result.launched_at
    assert captured["connection_settings"] == _test_connection_settings()


@pytest.mark.asyncio
async def test_trigger_dry_run_flag_passed() -> None:
    """Trigger with dry_run=true is accepted."""
    session = FakeAsyncSession()
    previous = setup_session(session)
    try:
        resp = await http_post(
            "/api/v1/admin/legacy-refresh/trigger",
            json={
                "tenant_id": str(uuid.uuid4()),
                "schema_name": "test_schema",
                "mode": "full-rebaseline",
                "dry_run": True,
            },
        )
        assert resp.status_code == 202
    finally:
        teardown_session(previous)


# ── AC2: Status endpoint ───────────────────────────────────────


@pytest.mark.asyncio
async def test_status_returns_lane_state(temp_lane: tuple[Path, uuid.UUID, str, str]) -> None:
    """Status endpoint returns lane state with batch pointers."""
    tmp_path, tenant_id, schema_name, source_schema = temp_lane

    status = _load_lane_status(tenant_id, schema_name, source_schema, summary_root=tmp_path)

    assert isinstance(status, RefreshLaneStatus)
    assert status.tenant_id == str(tenant_id)
    assert status.schema_name == schema_name
    assert status.source_schema == source_schema
    assert status.lane_key == f"{schema_name}:{tenant_id}:{source_schema}"
    # No runs yet
    assert status.lane_locked is False
    assert status.latest_run is None
    assert status.latest_success is None
    assert status.latest_promoted is None


@pytest.mark.asyncio
async def test_status_returns_batch_pointers(
    temp_lane: tuple[Path, uuid.UUID, str, str],
    completed_run: dict,
) -> None:
    """Status returns latest_run, latest_success, and latest_promoted pointers."""
    tmp_path, tenant_id, schema_name, source_schema = temp_lane

    status = _load_lane_status(tenant_id, schema_name, source_schema, summary_root=tmp_path)

    assert status.latest_run is not None
    assert status.latest_run.batch_id == completed_run["batch_id"]
    assert status.latest_run.final_disposition == RefreshDisposition.COMPLETED.value
    assert status.latest_success is not None
    assert status.latest_success.batch_id == completed_run["batch_id"]
    assert status.latest_promoted is None  # No promotion yet


@pytest.mark.asyncio
async def test_status_returns_promotion_policy(
    temp_lane: tuple[Path, uuid.UUID, str, str],
    completed_run: dict,
) -> None:
    """Status surfaces promotion policy outcome."""
    tmp_path, tenant_id, schema_name, source_schema = temp_lane

    status = _load_lane_status(tenant_id, schema_name, source_schema, summary_root=tmp_path)

    assert status.promotion_eligible is True
    assert status.promotion_classification == "eligible"
    assert status.latest_run is not None
    assert status.latest_run.promotion_policy is not None
    assert status.latest_run.promotion_policy["classification"] == "eligible"


@pytest.mark.asyncio
async def test_status_returns_root_failure(
    temp_lane: tuple[Path, uuid.UUID, str, str],
) -> None:
    """Status surfaces root failure details for failed runs."""
    tmp_path, tenant_id, schema_name, source_schema = temp_lane
    lane_paths = build_lane_state_paths(
        tenant_id=tenant_id,
        schema_name=schema_name,
        source_schema=source_schema,
        summary_root=tmp_path,
    )

    # Write a failed run
    failed_record = {
        "batch_id": "legacy-shadow-20240424T130000Z",
        "final_disposition": RefreshDisposition.VALIDATION_BLOCKED.value,
        "exit_code": 1,
        "validation_status": "failed",
        "blocking_issue_count": 3,
        "promotion_policy": {"classification": "blocked", "reason_codes": ["validation_failed"]},
    }
    write_json_atomically(lane_paths.latest_run_path, failed_record)

    status = _load_lane_status(tenant_id, schema_name, source_schema, summary_root=tmp_path)

    assert status.root_failure is not None
    assert "validation blocked" in status.root_failure
    assert "3" in status.root_failure


@pytest.mark.asyncio
async def test_status_surfaces_incremental_scope_and_detailed_failure_reason(
    temp_lane: tuple[Path, uuid.UUID, str, str],
) -> None:
    tmp_path, tenant_id, schema_name, source_schema = temp_lane
    lane_paths = build_lane_state_paths(
        tenant_id=tenant_id,
        schema_name=schema_name,
        source_schema=source_schema,
        summary_root=tmp_path,
    )

    detailed_record = {
        "batch_id": "legacy-incremental-20240424T140000Z",
        "batch_mode": "incremental",
        "affected_domains": ["sales", "products"],
        "final_disposition": RefreshDisposition.RECONCILIATION_BLOCKED.value,
        "root_failed_step": "verify_reconciliation",
        "root_error_message": "Targeted reconciliation exceeded threshold",
        "rebaseline_reason": "Incremental reconciliation drift requires full rebaseline",
        "promotion_policy": {
            "classification": "blocked",
            "reason_codes": ["reconciliation"],
        },
    }
    write_json_atomically(lane_paths.latest_run_path, detailed_record)

    status = _load_lane_status(tenant_id, schema_name, source_schema, summary_root=tmp_path)

    assert status.current_batch_mode == "incremental"
    assert status.affected_domains == ["sales", "products"]
    assert status.root_failure == "verify_reconciliation: Targeted reconciliation exceeded threshold"
    assert status.blocked_reason == "Incremental reconciliation drift requires full rebaseline"


@pytest.mark.asyncio
async def test_status_endpoint_requires_auth() -> None:
    """Status endpoint returns 401 without authentication."""
    session = FakeAsyncSession()
    previous = setup_session(session)
    try:
        # No auth header - use httpx directly
        from httpx import ASGITransport, AsyncClient
        from app.main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.get(
                f"/api/v1/admin/legacy-refresh/status?tenant_id={uuid.uuid4()}&schema_name=test",
                headers={},
            )
        assert resp.status_code == 401
    finally:
        teardown_session(previous)


# ── AC3: Lane-lock concurrency ─────────────────────────────────


@pytest.mark.asyncio
async def test_trigger_conflict_when_lane_locked(temp_lane: tuple[Path, uuid.UUID, str, str]) -> None:
    """Trigger returns 409 Conflict when lane is already locked by another job."""
    tmp_path, tenant_id, schema_name, source_schema = temp_lane
    # Write the lock to DEFAULT_SUMMARY_ROOT so the API endpoint can find it
    lane_paths = build_lane_state_paths(
        tenant_id=tenant_id,
        schema_name=schema_name,
        source_schema=source_schema,
        summary_root=DEFAULT_SUMMARY_ROOT,
    )
    lane_paths.lane_root.mkdir(parents=True, exist_ok=True)

    # Simulate an existing lock
    existing_lock = {
        "scheduler_run_id": str(uuid.uuid4()),
        "batch_id": "legacy-shadow-existing",
        "started_at": _iso_now(),
    }
    write_json_atomically(lane_paths.lock_path, existing_lock)

    session = FakeAsyncSession()
    previous = setup_session(session)
    try:
        resp = await http_post(
            "/api/v1/admin/legacy-refresh/trigger",
            json={
                "tenant_id": str(tenant_id),
                "schema_name": schema_name,
                "source_schema": source_schema,
                "mode": "incremental",
            },
        )
        assert resp.status_code == 202
        data = resp.json()
        # AC3: Conflict response is returned, not a new job launch
        assert data.get("conflict") == "refresh-already-in-progress"
        assert "existing_lock" in data
    finally:
        # Clean up the entire lane directory to prevent test pollution
        import shutil
        try:
            shutil.rmtree(lane_paths.lane_root)
        except FileNotFoundError:
            pass
        teardown_session(previous)


# ── AC4: Status polling ────────────────────────────────────────


@pytest.mark.asyncio
async def test_status_polling_returns_current_job(
    temp_lane: tuple[Path, uuid.UUID, str, str],
) -> None:
    """Polling status returns current job metadata for the lane."""
    tmp_path, tenant_id, schema_name, source_schema = temp_lane
    lane_paths = build_lane_state_paths(
        tenant_id=tenant_id,
        schema_name=schema_name,
        source_schema=source_schema,
        summary_root=tmp_path,
    )

    # Simulate a running job via lock file
    running_job = {
        "scheduler_run_id": str(uuid.uuid4()),
        "batch_id": "legacy-shadow-running",
        "started_at": _iso_now(),
    }
    write_json_atomically(lane_paths.lock_path, running_job)

    status = _load_lane_status(tenant_id, schema_name, source_schema, summary_root=tmp_path)

    assert status.lane_locked is True
    assert status.current_job_id == running_job["scheduler_run_id"]
    assert status.lock_acquired_at == running_job["started_at"]


@pytest.mark.asyncio
async def test_get_job_status_prefers_sentinel_over_stale_redis(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid.uuid4()
    lane_paths = build_lane_state_paths(
        tenant_id=tenant_id,
        schema_name="test_schema",
        source_schema="public",
        summary_root=tmp_path,
    )
    lane_paths.lane_root.mkdir(parents=True, exist_ok=True)

    job_id = str(uuid.uuid4())
    redis_key = f"legacy-refresh:job:{job_id}"
    fake_redis = FakeRedis({
        redis_key: json.dumps({
            "job_id": job_id,
            "batch_id": "legacy-shadow-stale",
            "status": "queued",
            "actor_id": "admin@example.com",
        }),
    })
    sentinel_payload = {
        "job_id": job_id,
        "batch_id": "legacy-shadow-stale",
        "status": "completed",
        "final_disposition": RefreshDisposition.COMPLETED.value,
        "summary_path": str(tmp_path / "summary.json"),
        "completed_at": "2026-04-28T02:00:00+00:00",
    }
    write_json_atomically(lane_paths.lane_root / f".job-{job_id}.json", sentinel_payload)

    async def fake_get_redis() -> FakeRedis:
        return fake_redis

    monkeypatch.setattr(legacy_refresh_routes, "DEFAULT_SUMMARY_ROOT", tmp_path)
    monkeypatch.setattr(legacy_refresh_routes, "_get_redis", fake_get_redis)

    status = await legacy_refresh_routes.get_job_status(job_id)

    assert status["status"] == "completed"
    assert status["final_disposition"] == RefreshDisposition.COMPLETED.value
    assert status["summary_path"] == str(tmp_path / "summary.json")
    assert status["actor_id"] == "admin@example.com"


@pytest.mark.asyncio
async def test_status_ignores_stale_lane_lock(
    temp_lane: tuple[Path, uuid.UUID, str, str],
) -> None:
    """Status should not report a lock once the lane lock is stale."""
    tmp_path, tenant_id, schema_name, source_schema = temp_lane
    lane_paths = build_lane_state_paths(
        tenant_id=tenant_id,
        schema_name=schema_name,
        source_schema=source_schema,
        summary_root=tmp_path,
    )

    stale_started_at = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    write_json_atomically(
        lane_paths.lock_path,
        {
            "scheduler_run_id": str(uuid.uuid4()),
            "batch_id": "legacy-shadow-stale",
            "started_at": stale_started_at,
        },
    )

    status = _load_lane_status(tenant_id, schema_name, source_schema, summary_root=tmp_path)

    assert status.lane_locked is False
    assert status.current_job_id is None
    assert lane_paths.lock_path.exists() is False


@pytest.mark.asyncio
async def test_trigger_recovers_stale_lane_lock_before_conflict(
    temp_lane: tuple[Path, uuid.UUID, str, str],
) -> None:
    """Trigger should launch a new job when the existing lane lock is stale."""
    tmp_path, tenant_id, schema_name, source_schema = temp_lane
    lane_paths = build_lane_state_paths(
        tenant_id=tenant_id,
        schema_name=schema_name,
        source_schema=source_schema,
        summary_root=DEFAULT_SUMMARY_ROOT,
    )
    lane_paths.lane_root.mkdir(parents=True, exist_ok=True)

    stale_started_at = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    write_json_atomically(
        lane_paths.lock_path,
        {
            "scheduler_run_id": str(uuid.uuid4()),
            "batch_id": "legacy-shadow-stale",
            "started_at": stale_started_at,
        },
    )

    session = FakeAsyncSession()
    previous = setup_session(session)
    try:
        resp = await http_post(
            "/api/v1/admin/legacy-refresh/trigger",
            json={
                "tenant_id": str(tenant_id),
                "schema_name": schema_name,
                "source_schema": source_schema,
                "mode": "full-rebaseline",
            },
        )
        assert resp.status_code == 202
        data = resp.json()
        assert "conflict" not in data
        assert data["mode"] == "full-rebaseline"
        assert data["job_id"]
    finally:
        import shutil
        try:
            shutil.rmtree(lane_paths.lane_root)
        except FileNotFoundError:
            pass
        teardown_session(previous)


@pytest.mark.asyncio
async def test_recent_runs_endpoint_returns_job_records(
    temp_lane: tuple[Path, uuid.UUID, str, str],
    completed_run: dict,
) -> None:
    """Recent runs endpoint returns job records with status."""
    # Write the completed run to DEFAULT_SUMMARY_ROOT so the API can find it
    tmp_path, tenant_id, schema_name, source_schema = temp_lane
    lane_paths = build_lane_state_paths(
        tenant_id=tenant_id,
        schema_name=schema_name,
        source_schema=source_schema,
        summary_root=DEFAULT_SUMMARY_ROOT,
    )
    lane_paths.lane_root.mkdir(parents=True, exist_ok=True)

    # Create a unique completed record
    completed_record = {
        **completed_run,
        "batch_id": "legacy-shadow-completed-test",
        "started_at": "2099-04-24T12:00:00+00:00",
        "completed_at": "2099-04-24T12:05:00+00:00",
        "final_disposition": RefreshDisposition.COMPLETED.value,
    }
    write_json_atomically(lane_paths.latest_run_path, completed_record)
    write_json_atomically(lane_paths.latest_success_path, completed_record)

    session = FakeAsyncSession()
    previous = setup_session(session)
    try:
        resp = await http_get("/api/v1/admin/legacy-refresh/recent-runs?limit=50")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        # Find our completed run
        run = next((r for r in data if r["batch_id"] == "legacy-shadow-completed-test"), None)
        assert run is not None, f"Expected to find legacy-shadow-completed-test in {data}"
        assert "job_id" in run
        assert "batch_id" in run
        assert "final_disposition" in run
        assert run["final_disposition"] == RefreshDisposition.COMPLETED.value
    finally:
        # Clean up the entire lane directory to prevent test pollution
        import shutil
        try:
            shutil.rmtree(lane_paths.lane_root)
        except FileNotFoundError:
            pass
        teardown_session(previous)


@pytest.mark.asyncio
async def test_recent_runs_blocked_reason(
    temp_lane: tuple[Path, uuid.UUID, str, str],
) -> None:
    """Recent runs surfaces blocked reason for OVERLAP_BLOCKED dispositions."""
    tmp_path, tenant_id, schema_name, source_schema = temp_lane
    # Write to DEFAULT_SUMMARY_ROOT so the API can find it
    lane_paths = build_lane_state_paths(
        tenant_id=tenant_id,
        schema_name=schema_name,
        source_schema=source_schema,
        summary_root=DEFAULT_SUMMARY_ROOT,
    )
    lane_paths.lane_root.mkdir(parents=True, exist_ok=True)

    # Write a blocked run
    blocked_record = {
        "scheduler_run_id": str(uuid.uuid4()),
        "batch_id": "legacy-shadow-blocked",
        "started_at": "2099-04-24T14:00:00+00:00",
        "completed_at": "2099-04-24T14:00:01+00:00",
        "final_disposition": RefreshDisposition.OVERLAP_BLOCKED.value,
        "exit_code": 2,
        "promotion_policy": {"classification": "blocked", "reason_codes": ["overlap"]},
    }
    write_json_atomically(lane_paths.latest_run_path, blocked_record)

    session = FakeAsyncSession()
    previous = setup_session(session)
    try:
        resp = await http_get("/api/v1/admin/legacy-refresh/recent-runs?limit=50")
        assert resp.status_code == 200
        data = resp.json()
        run = next((r for r in data if r["batch_id"] == "legacy-shadow-blocked"), None)
        assert run is not None
        assert run["blocked"] is True
        assert "blocked_reason" in run
    finally:
        # Clean up the entire lane directory to prevent test pollution
        import shutil
        try:
            shutil.rmtree(lane_paths.lane_root)
        except FileNotFoundError:
            pass
        teardown_session(previous)


# ── AC5: Durable worker boundary ───────────────────────────────


def test_no_background_tasks_in_route_module() -> None:
    """Verify the routes module does not import or use FastAPI BackgroundTasks.

    AC5: The control plane launches work through asyncio.create_task (background
    tasks) rather than FastAPI BackgroundTasks, which would tie job lifecycle to
    the request scope and risk orphaned jobs on client disconnects.
    """
    import ast
    from pathlib import Path

    routes_path = Path(__file__).parent.parent / "domains" / "legacy_import" / "routes.py"
    source = routes_path.read_text()
    tree = ast.parse(source)

    background_task_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module == "fastapi":
                for alias in node.names:
                    if "background" in alias.name.lower() or "backgroundtasks" in alias.name.lower():
                        background_task_names.add(alias.name)
        elif isinstance(node, ast.Attribute):
            if "background" in node.attr.lower():
                background_task_names.add(node.attr)

    assert "BackgroundTasks" not in background_task_names, (
        "routes.py should not use FastAPI BackgroundTasks; "
        "use asyncio.create_task for durable execution boundary."
    )


def test_durable_launch_uses_asyncio_create_task() -> None:
    """Verify the trigger endpoint uses asyncio.create_task for job launch."""
    import ast
    from pathlib import Path

    routes_path = Path(__file__).parent.parent / "domains" / "legacy_import" / "routes.py"
    source = routes_path.read_text()
    tree = ast.parse(source)

    asyncio_create_task_found = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if (
                    node.func.attr == "create_task"
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "asyncio"
                ):
                    asyncio_create_task_found = True

    assert asyncio_create_task_found, (
        "Trigger endpoint must use asyncio.create_task for durable background execution."
    )


# ── Schema validation ──────────────────────────────────────────


def test_refresh_trigger_request_schema() -> None:
    """RefreshTriggerRequest validates required fields."""
    # Valid
    req = RefreshTriggerRequest(
        tenant_id=uuid.uuid4(),
        schema_name="my_schema",
        mode=RefreshMode.INCREMENTAL,
    )
    assert req.mode == RefreshMode.INCREMENTAL
    assert req.dry_run is False
    assert req.lookback_days == 0

    # Schema name required
    with pytest.raises(Exception):
        RefreshTriggerRequest(
            tenant_id=uuid.uuid4(),
            schema_name="",
            mode=RefreshMode.FULL_REBASELINE,
        )


def test_refresh_mode_enum() -> None:
    """RefreshMode enum has expected values."""
    assert RefreshMode.INCREMENTAL.value == "incremental"
    assert RefreshMode.FULL_REBASELINE.value == "full-rebaseline"


def test_batch_pointer_model() -> None:
    """BatchPointer model serializes nullable fields correctly."""
    from domains.legacy_import.routes import BatchPointer

    ptr = BatchPointer(
        batch_id="test-batch",
        summary_path="/tmp/summary.json",
        final_disposition=RefreshDisposition.COMPLETED.value,
        promotion_policy={"classification": "eligible"},
    )
    assert ptr.batch_id == "test-batch"
    assert ptr.promotion_policy is not None
    assert ptr.promotion_policy["classification"] == "eligible"
