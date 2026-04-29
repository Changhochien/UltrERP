"""Admin-authenticated legacy-refresh control plane routes.

Story 15.28 exposes lane-aware trigger and status endpoints for the legacy
refresh pipeline under the reviewed admin-route namespace.

AC1: Admin can trigger full rebaseline or incremental refresh.
AC2: Status API returns lane state, batch pointers, promotion-policy outcome.
AC3: Concurrent refresh blocked with lane-lock semantics.
AC4: Admin UI polls status surface for progress.
AC5: Durable worker boundary (not BackgroundTasks).
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Annotated, Any

import redis.asyncio as redis
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select

from common.auth import require_role
from common.config import settings
from common.database import AsyncSessionLocal
from domains.settings.models import AppSetting
from scripts.legacy_refresh_common import RefreshDisposition
from scripts.legacy_refresh_state import (
    build_lane_state_paths,
    remove_file_if_exists,
    read_json_file,
    read_json_file_with_error,
    recover_stale_lock,
    write_json_atomically,
    write_lock_file_with_recovery,
)
from scripts.run_incremental_legacy_refresh import (
    build_incremental_plan_for_dry_run,
    build_incremental_batch_id,
    build_live_source_projection_for_lane,
    run_incremental_legacy_refresh,
)
from scripts.run_legacy_refresh import DEFAULT_SUMMARY_ROOT
from scripts.run_scheduled_legacy_shadow_refresh import (
    build_shadow_batch_id,
    run_scheduled_shadow_refresh,
)
from domains.legacy_import.staging import (
    LegacySourceCompatibilityError,
    LegacySourceConnectionSettings,
    load_runtime_legacy_source_connection_settings,
)

logger = logging.getLogger(__name__)
_PROCESS_STARTED_AT = datetime.now(timezone.utc)
_ACTIVE_JOB_STATUSES = {"queued", "running"}
_ORPHANED_JOB_FAILURE = "worker interrupted by server restart"


class RefreshMode(str, Enum):
    FULL_REBASELINE = "full-rebaseline"
    INCREMENTAL = "incremental"


class RefreshTriggerRequest(BaseModel):
    """Request payload for triggering a legacy refresh job.

    The trigger is idempotent with respect to concurrent requests for the same
    lane: the lane-lock semantics ensure exactly one job is launched while
    others receive a 409 Conflict response.
    """

    tenant_id: uuid.UUID
    schema_name: str = Field(min_length=1)
    source_schema: str = Field(default="public")
    mode: RefreshMode
    dry_run: bool = False
    lookback_days: int = Field(default=0, ge=0)
    reconciliation_threshold: int = Field(default=0, ge=0)


class RefreshJobLaunched(BaseModel):
    """Response when a refresh job is successfully launched."""

    job_id: str
    lane_key: str
    mode: RefreshMode
    batch_id: str
    launched_at: str
    status: str = "queued"


class RefreshConflict(BaseModel):
    """Response when a refresh job is blocked due to a concurrent lane lock."""

    lane_key: str
    conflict: str = "refresh-already-in-progress"
    detail: str
    existing_lock: dict[str, Any] | None = None


class BatchPointer(BaseModel):
    """Immutable snapshot of a batch execution result."""

    batch_id: str | None = None
    summary_path: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    final_disposition: str | None = None
    exit_code: int | None = None
    validation_status: str | None = None
    blocking_issue_count: int | None = None
    reconciliation_gap_count: int | None = None
    promotion_policy: dict[str, Any] | None = None


class RefreshLaneStatus(BaseModel):
    """Lane-aware status response surfaced to the admin UI.

    Returns enough state for operators to diagnose lane health without shell access.
    """

    lane_key: str
    tenant_id: str
    schema_name: str
    source_schema: str

    # Lane lock state
    lane_locked: bool
    current_job_id: str | None = None
    lock_acquired_at: str | None = None

    # Batch pointers
    latest_run: BatchPointer | None = None
    latest_success: BatchPointer | None = None
    latest_promoted: BatchPointer | None = None

    # Derived state
    current_batch_mode: str | None = None
    promotion_eligible: bool = False
    promotion_classification: str | None = None

    # Domain-level state (simplified)
    affected_domains: list[str] = Field(default_factory=list)

    # Root failure details
    root_failure: str | None = None
    blocked_reason: str | None = None

    # Artifact paths
    incremental_state_path: str | None = None
    nightly_rebaseline_path: str | None = None
    summary_root: str | None = None


class RefreshJobRecord(BaseModel):
    """Simplified job record for recent-runs listing."""

    job_id: str
    batch_id: str
    mode: str
    started_at: str
    completed_at: str | None = None
    final_disposition: str
    validation_status: str | None = None
    promotion_eligible: bool = False
    blocked: bool = False
    blocked_reason: str | None = None


class RefreshLanesResponse(BaseModel):
    """List of all lanes with their current status."""

    lanes: list[RefreshLaneStatus]


router = APIRouter(
    prefix="/admin/legacy-refresh",
    tags=["legacy-refresh"],
    dependencies=[Depends(require_role("admin", "owner"))],
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_REDIS_JOB_PREFIX = "legacy-refresh:job:"
_REDIS_JOB_TTL = 86_400  # 24 hours
_NULL_SENTINEL = "__NULL__"


class RedisJobCacheUnavailable(RuntimeError):
    """Raised when the optional Redis job cache is not configured."""


async def _load_runtime_redis_url() -> str | None:
    fallback = settings.redis_url
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(AppSetting).where(AppSetting.key == "redis_url")
            )
            row = result.scalar_one_or_none()
    except Exception:
        row = None

    if row is not None:
        if row.value == _NULL_SENTINEL:
            return None
        fallback = row.value

    if fallback is None:
        return None

    resolved = str(fallback).strip()
    return resolved or None


async def _get_redis() -> redis.Redis:
    """Return an async Redis client for legacy refresh job metadata."""
    from app.main import app as fastapi_app

    redis_url = await _load_runtime_redis_url()
    if redis_url is None:
        raise RedisJobCacheUnavailable("Redis URL is not configured")

    cached_client = getattr(fastapi_app.state, "legacy_refresh_redis", None)
    cached_url = getattr(fastapi_app.state, "legacy_refresh_redis_url", None)
    if cached_client is not None and cached_url == redis_url:
        return cached_client

    if cached_client is not None and cached_url != redis_url:
        try:
            await cached_client.aclose()
        except Exception:
            logger.debug("Failed to close stale legacy refresh Redis client", exc_info=True)

    fastapi_app.state.legacy_refresh_redis = redis.from_url(
        redis_url,
        encoding="utf-8",
        decode_responses=True,
    )
    fastapi_app.state.legacy_refresh_redis_url = redis_url
    return fastapi_app.state.legacy_refresh_redis


async def _write_redis_job(
    r: redis.Redis,
    job_id: str,
    payload: dict[str, Any],
) -> None:
    key = f"{_REDIS_JOB_PREFIX}{job_id}"
    await r.set(key, json.dumps(payload), ex=_REDIS_JOB_TTL)


async def _read_redis_job(
    r: redis.Redis,
    job_id: str,
) -> dict[str, Any] | None:
    key = f"{_REDIS_JOB_PREFIX}{job_id}"
    raw = await r.get(key)
    if raw is None:
        return None
    return json.loads(raw)


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _job_sentinel_path(lane_root: Path, job_id: str) -> Path:
    return lane_root / f".job-{job_id}.json"


def _parse_refresh_timestamp(value: object | None) -> datetime | None:
    if not isinstance(value, str):
        return None
    candidate = value.strip()
    if not candidate:
        return None
    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _resolve_job_started_at(job_payload: dict[str, Any], sentinel_path: Path) -> datetime | None:
    started_at = _parse_refresh_timestamp(job_payload.get("started_at"))
    if started_at is not None:
        return started_at

    launched_at = _parse_refresh_timestamp(job_payload.get("launched_at"))
    if launched_at is not None:
        return launched_at

    try:
        return datetime.fromtimestamp(sentinel_path.stat().st_mtime, tz=timezone.utc)
    except FileNotFoundError:
        return None


def _mark_job_interrupted(sentinel_path: Path, job_payload: dict[str, Any]) -> None:
    if str(job_payload.get("status", "")).strip().lower() not in _ACTIVE_JOB_STATUSES:
        return

    write_json_atomically(
        sentinel_path,
        {
            **job_payload,
            "status": "completed",
            "completed_at": _iso_now(),
            "exit_code": 1,
            "final_disposition": RefreshDisposition.FAILED.value,
            "root_failure": _ORPHANED_JOB_FAILURE,
        },
    )


def _reconcile_orphaned_lane_state(lane_root: Path) -> int:
    reconciled = 0
    lock_path = lane_root / "scheduler.lock"

    lock_payload = read_json_file(lock_path)
    if isinstance(lock_payload, dict):
        lock_started_at = _parse_refresh_timestamp(lock_payload.get("started_at"))
        if lock_started_at is None:
            try:
                lock_started_at = datetime.fromtimestamp(lock_path.stat().st_mtime, tz=timezone.utc)
            except FileNotFoundError:
                lock_started_at = None
        if lock_started_at is not None and lock_started_at < _PROCESS_STARTED_AT:
            remove_file_if_exists(lock_path)

    for sentinel_path in lane_root.glob(".job-*.json"):
        job_payload = read_json_file(sentinel_path)
        if not isinstance(job_payload, dict):
            continue
        if str(job_payload.get("status", "")).strip().lower() not in _ACTIVE_JOB_STATUSES:
            continue

        job_started_at = _resolve_job_started_at(job_payload, sentinel_path)
        if job_started_at is None or job_started_at >= _PROCESS_STARTED_AT:
            continue

        _mark_job_interrupted(sentinel_path, job_payload)
        reconciled += 1

    return reconciled


def reconcile_orphaned_legacy_refresh_state(summary_root: Path | None = None) -> int:
    state_root = (summary_root or DEFAULT_SUMMARY_ROOT) / "state"
    if not state_root.exists():
        return 0

    reconciled = 0
    for lane_dir in state_root.iterdir():
        if not lane_dir.is_dir():
            continue
        reconciled += _reconcile_orphaned_lane_state(lane_dir)
    return reconciled


async def _persist_job_metadata(
    job_id: str,
    lane_root: Path,
    payload: dict[str, Any],
) -> None:
    write_json_atomically(_job_sentinel_path(lane_root, job_id), payload)
    try:
        r = await _get_redis()
        await _write_redis_job(r, job_id, payload)
    except RedisJobCacheUnavailable:
        return
    except Exception:
        logger.warning(
            "Redis unavailable: failed to sync job metadata for job_id=%s. "
            "Sentinel file remains the source of truth.",
            job_id,
        )


def _read_matching_latest_run(
    lane_paths: Any,
    batch_id: str,
) -> dict[str, Any] | None:
    raw = read_json_file(lane_paths.latest_run_path)
    if not isinstance(raw, dict):
        return None
    if raw.get("batch_id") != batch_id:
        return None
    return raw


def _derive_root_failure(latest_run_raw: dict[str, Any], latest_run: BatchPointer | None) -> str | None:
    root_failure: str | None = None
    root_failed_step = latest_run_raw.get("root_failed_step")
    root_error_message = latest_run_raw.get("root_error_message")
    if root_error_message:
        root_failure = (
            f"{root_failed_step}: {root_error_message}"
            if root_failed_step
            else str(root_error_message)
        )
    if root_failure is None and latest_run is not None and latest_run.final_disposition in (
        RefreshDisposition.FAILED.value,
        RefreshDisposition.VALIDATION_BLOCKED.value,
    ):
        if latest_run.blocking_issue_count and latest_run.blocking_issue_count > 0:
            root_failure = (
                f"validation blocked: {latest_run.blocking_issue_count} "
                "blocking issues"
            )
        elif latest_run.final_disposition == RefreshDisposition.FAILED.value:
            root_failure = "refresh execution failed"
    return root_failure


def _derive_blocked_reason(latest_run_raw: dict[str, Any], latest_run: BatchPointer | None) -> str | None:
    blocked_reason: str | None = None
    rebaseline_reason = latest_run_raw.get("rebaseline_reason")
    if isinstance(rebaseline_reason, str) and rebaseline_reason.strip():
        blocked_reason = rebaseline_reason.strip()
    if blocked_reason is None and latest_run is not None:
        disp = latest_run.final_disposition
        if disp == RefreshDisposition.OVERLAP_BLOCKED.value:
            blocked_reason = "concurrent refresh blocked"
        elif disp == RefreshDisposition.VALIDATION_BLOCKED.value:
            blocked_reason = "validation threshold exceeded"
    return blocked_reason


def _enrich_job_metadata_from_latest_run(
    job_meta: dict[str, Any],
    latest_run_raw: dict[str, Any] | None,
) -> dict[str, Any]:
    if latest_run_raw is None:
        return job_meta

    promotion_policy = latest_run_raw.get("promotion_policy")
    latest_run = BatchPointer(
        batch_id=latest_run_raw.get("batch_id"),
        summary_path=latest_run_raw.get("summary_path"),
        started_at=latest_run_raw.get("started_at"),
        completed_at=latest_run_raw.get("completed_at"),
        final_disposition=latest_run_raw.get("final_disposition"),
        exit_code=latest_run_raw.get("exit_code"),
        validation_status=latest_run_raw.get("validation_status"),
        blocking_issue_count=latest_run_raw.get("blocking_issue_count"),
        reconciliation_gap_count=latest_run_raw.get("reconciliation_gap_count"),
        promotion_policy=promotion_policy if isinstance(promotion_policy, dict) else None,
    )

    enriched = {
        **job_meta,
        "summary_path": latest_run.summary_path,
        "started_at": latest_run.started_at or job_meta.get("started_at"),
        "completed_at": latest_run.completed_at or job_meta.get("completed_at"),
        "final_disposition": latest_run.final_disposition,
        "exit_code": latest_run.exit_code,
        "validation_status": latest_run.validation_status,
        "blocking_issue_count": latest_run.blocking_issue_count,
        "reconciliation_gap_count": latest_run.reconciliation_gap_count,
        "promotion_policy": latest_run.promotion_policy,
        "blocked_reason": _derive_blocked_reason(latest_run_raw, latest_run),
        "root_failure": _derive_root_failure(latest_run_raw, latest_run),
        "status": "completed",
      }
    return {key: value for key, value in enriched.items() if value is not None}


def _read_job_sentinel(job_id: str) -> dict[str, Any] | None:
    state_root = DEFAULT_SUMMARY_ROOT / "state"
    if not state_root.exists():
        return None

    for lane_dir in state_root.iterdir():
        if not lane_dir.is_dir():
            continue
        _reconcile_orphaned_lane_state(lane_dir)
        sentinel_path = _job_sentinel_path(lane_dir, job_id)
        if sentinel_path.exists():
            raw = read_json_file(sentinel_path)
            if raw:
                return raw
    return None


def _load_lane_status(
    tenant_id: uuid.UUID,
    schema_name: str,
    source_schema: str,
    summary_root: Path | None = None,
) -> RefreshLaneStatus:
    lane_paths = build_lane_state_paths(
        tenant_id=tenant_id,
        schema_name=schema_name,
        source_schema=source_schema,
        summary_root=summary_root or DEFAULT_SUMMARY_ROOT,
    )
    lane_key = f"{schema_name}:{tenant_id}:{source_schema}"
    _reconcile_orphaned_lane_state(lane_paths.lane_root)

    # Check lock
    lock_payload: dict[str, Any] | None = None
    lock_acquired_at: str | None = None
    lane_locked = False
    recover_stale_lock(lane_paths.lock_path)
    try:
        lock_payload = read_json_file(lane_paths.lock_path)
        if lock_payload:
            lane_locked = True
            lock_acquired_at = lock_payload.get("started_at")
    except FileNotFoundError:
        pass

    def _load_pointer(p: Path) -> BatchPointer | None:
        raw, err = read_json_file_with_error(p)
        if err is not None:
            return None
        if raw is None:
            return None
        pp = raw.get("promotion_policy")
        return BatchPointer(
            batch_id=raw.get("batch_id"),
            summary_path=raw.get("summary_path"),
            started_at=raw.get("started_at"),
            completed_at=raw.get("completed_at"),
            final_disposition=raw.get("final_disposition"),
            exit_code=raw.get("exit_code"),
            validation_status=raw.get("validation_status"),
            blocking_issue_count=raw.get("blocking_issue_count"),
            reconciliation_gap_count=raw.get("reconciliation_gap_count"),
            promotion_policy=pp if isinstance(pp, dict) else None,
        )

    latest_run_raw, latest_run_err = read_json_file_with_error(lane_paths.latest_run_path)
    if latest_run_err is not None or latest_run_raw is None:
        latest_run_raw = {}

    latest_run = _load_pointer(lane_paths.latest_run_path)
    latest_success = _load_pointer(lane_paths.latest_success_path)
    latest_promoted = _load_pointer(lane_paths.latest_promoted_path)

    # Promotion eligibility
    promotion_eligible = False
    promotion_classification: str | None = None
    for ptr in (latest_run, latest_success):
        if ptr is not None and ptr.promotion_policy:
            classification = ptr.promotion_policy.get("classification")
            if classification == "eligible":
                promotion_eligible = True
                promotion_classification = classification
                break
            elif classification is not None:
                promotion_classification = classification

    root_failure = _derive_root_failure(latest_run_raw, latest_run)

    blocked_reason = _derive_blocked_reason(latest_run_raw, latest_run)

    # Current batch mode from latest run
    current_batch_mode: str | None = None
    if isinstance(latest_run_raw, dict):
        raw_batch_mode = latest_run_raw.get("batch_mode")
        if isinstance(raw_batch_mode, str) and raw_batch_mode.strip():
            current_batch_mode = raw_batch_mode.strip()
    if current_batch_mode is None and latest_run is not None:
        if latest_run.batch_id:
            if "shadow" in latest_run.batch_id or "full" in latest_run.batch_id:
                current_batch_mode = "full-rebaseline"
            elif "incremental" in latest_run.batch_id:
                current_batch_mode = "incremental"

    affected_domains: list[str] = []
    if isinstance(latest_run_raw, dict):
        raw_affected_domains = latest_run_raw.get("affected_domains")
        if isinstance(raw_affected_domains, list):
            affected_domains = [
                str(domain).strip()
                for domain in raw_affected_domains
                if str(domain).strip()
            ]

    return RefreshLaneStatus(
        lane_key=lane_key,
        tenant_id=str(tenant_id),
        schema_name=schema_name,
        source_schema=source_schema,
        lane_locked=lane_locked,
        current_job_id=lock_payload.get("scheduler_run_id") if lock_payload else None,
        lock_acquired_at=lock_acquired_at,
        latest_run=latest_run,
        latest_success=latest_success,
        latest_promoted=latest_promoted,
        current_batch_mode=current_batch_mode,
        promotion_eligible=promotion_eligible,
        promotion_classification=promotion_classification,
        affected_domains=affected_domains,
        root_failure=root_failure,
        blocked_reason=blocked_reason,
        incremental_state_path=str(lane_paths.incremental_state_path)
        if lane_paths.incremental_state_path.exists()
        else None,
        nightly_rebaseline_path=str(lane_paths.nightly_rebaseline_path)
        if lane_paths.nightly_rebaseline_path.exists()
        else None,
        summary_root=str(DEFAULT_SUMMARY_ROOT),
    )


# ---------------------------------------------------------------------------
# AC1: Trigger endpoints
# ---------------------------------------------------------------------------

async def _launch_full_rebaseline(
    tenant_id: uuid.UUID,
    schema_name: str,
    source_schema: str,
    lookback_days: int,
    reconciliation_threshold: int,
    job_id: str,
    batch_id: str,
    launched_at: str,
    connection_settings: LegacySourceConnectionSettings,
) -> None:
    """Durable worker: launch full rebaseline via subprocess.

    This function runs in a background asyncio task, off the request thread.
    It writes a sentinel file atomically so the status API can report progress.
    """
    lock_payload = {
        "scheduler_run_id": job_id,
        "tenant_id": str(tenant_id),
        "schema_name": schema_name,
        "source_schema": source_schema,
        "batch_id": batch_id,
        "started_at": launched_at,
    }

    lane_paths = build_lane_state_paths(
        tenant_id=tenant_id,
        schema_name=schema_name,
        source_schema=source_schema,
        summary_root=DEFAULT_SUMMARY_ROOT,
    )

    # Acquire lane lock
    try:
        now = datetime.now(timezone.utc)
        write_lock_file_with_recovery(lane_paths.lock_path, lock_payload, now=now)
    except FileExistsError:
        return  # Another job holds the lock

    try:
        # Write job metadata for status polling
        job_meta = {
            "job_id": job_id,
            "batch_id": batch_id,
            "mode": RefreshMode.FULL_REBASELINE.value,
            "tenant_id": str(tenant_id),
            "schema_name": schema_name,
            "source_schema": source_schema,
            "launched_at": launched_at,
            "started_at": launched_at,
            "status": "running",
        }
        await _persist_job_metadata(job_id, lane_paths.lane_root, job_meta)

        try:
            result = await run_scheduled_shadow_refresh(
                tenant_id=tenant_id,
                schema_name=schema_name,
                source_schema=source_schema,
                lookback_days=lookback_days,
                reconciliation_threshold=reconciliation_threshold,
                batch_prefix="legacy-shadow",
                summary_root=DEFAULT_SUMMARY_ROOT,
                scheduler_run_id=job_id,
                started_at=launched_at,
                batch_id=batch_id,
                lock_already_held=True,
                connection_settings=connection_settings,
            )
            job_meta["status"] = "completed"
            job_meta["exit_code"] = result.exit_code
            job_meta["completed_at"] = _iso_now()
            job_meta = _enrich_job_metadata_from_latest_run(
                job_meta,
                _read_matching_latest_run(lane_paths, batch_id),
            )
            if result.exit_code != 0 and "final_disposition" not in job_meta:
                job_meta["final_disposition"] = RefreshDisposition.FAILED.value
            await _persist_job_metadata(job_id, lane_paths.lane_root, job_meta)
        except asyncio.CancelledError:
            cancelled_meta = {
                **job_meta,
                "status": "completed",
                "completed_at": _iso_now(),
                "exit_code": 1,
                "final_disposition": RefreshDisposition.FAILED.value,
                "root_failure": "worker cancelled before completion",
            }
            await _persist_job_metadata(job_id, lane_paths.lane_root, cancelled_meta)
            raise
        except Exception as exc:
            logger.exception("Legacy full rebaseline worker failed for job_id=%s", job_id)
            failure_meta = {
                **job_meta,
                "status": "completed",
                "completed_at": _iso_now(),
                "exit_code": 1,
                "final_disposition": RefreshDisposition.FAILED.value,
                "root_failure": str(exc),
            }
            await _persist_job_metadata(job_id, lane_paths.lane_root, failure_meta)
    finally:
        try:
            lane_paths.lock_path.unlink()
        except FileNotFoundError:
            pass


async def _launch_incremental(
    tenant_id: uuid.UUID,
    schema_name: str,
    source_schema: str,
    lookback_days: int,
    reconciliation_threshold: int,
    job_id: str,
    batch_id: str,
    launched_at: str,
    connection_settings: LegacySourceConnectionSettings,
) -> None:
    """Durable worker: launch incremental refresh via subprocess.

    This function runs in a background asyncio task, off the request thread.
    """
    lane_paths = build_lane_state_paths(
        tenant_id=tenant_id,
        schema_name=schema_name,
        source_schema=source_schema,
        summary_root=DEFAULT_SUMMARY_ROOT,
    )

    lock_payload = {
        "scheduler_run_id": job_id,
        "tenant_id": str(tenant_id),
        "schema_name": schema_name,
        "source_schema": source_schema,
        "batch_id": batch_id,
        "started_at": launched_at,
    }

    try:
        now = datetime.now(timezone.utc)
        write_lock_file_with_recovery(lane_paths.lock_path, lock_payload, now=now)
    except FileExistsError:
        return  # Another job holds the lock

    try:
        job_meta = {
            "job_id": job_id,
            "batch_id": batch_id,
            "mode": RefreshMode.INCREMENTAL.value,
            "tenant_id": str(tenant_id),
            "schema_name": schema_name,
            "source_schema": source_schema,
            "launched_at": launched_at,
            "started_at": launched_at,
            "status": "running",
        }
        await _persist_job_metadata(job_id, lane_paths.lane_root, job_meta)

        try:
            source_projection = build_live_source_projection_for_lane(
                tenant_id=tenant_id,
                schema_name=schema_name,
                source_schema=source_schema,
                connection_settings=connection_settings,
            )
            result = await run_incremental_legacy_refresh(
                tenant_id=tenant_id,
                schema_name=schema_name,
                source_schema=source_schema,
                lookback_days=lookback_days,
                reconciliation_threshold=reconciliation_threshold,
                batch_prefix="legacy-incremental",
                batch_id=batch_id,
                source_projection=source_projection,
                scheduler_run_id=job_id,
                started_at=job_meta["started_at"],
                connection_settings=connection_settings,
            )
            job_meta["status"] = "completed"
            job_meta["exit_code"] = result.exit_code
            job_meta["completed_at"] = _iso_now()
            job_meta = _enrich_job_metadata_from_latest_run(
                job_meta,
                _read_matching_latest_run(lane_paths, batch_id),
            )
            if result.exit_code != 0 and "final_disposition" not in job_meta:
                job_meta["final_disposition"] = RefreshDisposition.FAILED.value
            await _persist_job_metadata(job_id, lane_paths.lane_root, job_meta)
        except asyncio.CancelledError:
            cancelled_meta = {
                **job_meta,
                "status": "completed",
                "completed_at": _iso_now(),
                "exit_code": 1,
                "final_disposition": RefreshDisposition.FAILED.value,
                "root_failure": "worker cancelled before completion",
            }
            await _persist_job_metadata(job_id, lane_paths.lane_root, cancelled_meta)
            raise
        except Exception as exc:
            logger.exception("Legacy incremental refresh worker failed for job_id=%s", job_id)
            failure_meta = {
                **job_meta,
                "status": "completed",
                "completed_at": _iso_now(),
                "exit_code": 1,
                "final_disposition": RefreshDisposition.FAILED.value,
                "root_failure": str(exc),
            }
            await _persist_job_metadata(job_id, lane_paths.lane_root, failure_meta)
    finally:
        try:
            lane_paths.lock_path.unlink()
        except FileNotFoundError:
            pass


@router.post(
    "/trigger",
    response_model=RefreshJobLaunched | RefreshConflict,
    status_code=202,
    summary="Trigger a legacy refresh job (full rebaseline or incremental)",
    description=(
        "Launches a durable refresh job for the specified lane. "
        "If a job is already in progress for the same lane, returns 409 Conflict "
        "without launching overlapping work (AC3)."
    ),
)
async def trigger_legacy_refresh(
    request: RefreshTriggerRequest,
    current_user: Annotated[dict, Depends(require_role("admin", "owner"))],
) -> RefreshJobLaunched | RefreshConflict:
    """AC1: Trigger a full rebaseline or incremental refresh job.

    The job is handed to a durable background task rather than keeping
    the request thread open (AC5).
    """
    job_id = str(uuid.uuid4())
    lane_key = f"{request.schema_name}:{request.tenant_id}:{request.source_schema}"

    lane_paths = build_lane_state_paths(
        tenant_id=request.tenant_id,
        schema_name=request.schema_name,
        source_schema=request.source_schema,
        summary_root=DEFAULT_SUMMARY_ROOT,
    )

    # Check for concurrent lane lock (AC3)
    _reconcile_orphaned_lane_state(lane_paths.lane_root)
    recover_stale_lock(lane_paths.lock_path)
    existing_lock = read_json_file(lane_paths.lock_path)
    if existing_lock is not None:
        return RefreshConflict(
            lane_key=lane_key,
            detail=(
                f"A refresh job is already in progress for this lane "
                f"(job_id={existing_lock.get('scheduler_run_id', 'unknown')}). "
                "Wait for it to complete or cancel it before launching a new one."
            ),
            existing_lock=existing_lock,
        )

    if request.mode == RefreshMode.INCREMENTAL:
        try:
            build_incremental_plan_for_dry_run(
                tenant_id=request.tenant_id,
                schema_name=request.schema_name,
                source_schema=request.source_schema,
                summary_root=DEFAULT_SUMMARY_ROOT,
            )
        except FileNotFoundError as exc:
            return RefreshConflict(
                lane_key=lane_key,
                conflict="incremental-bootstrap-required",
                detail=str(exc),
            )
        except ValueError as exc:
            return RefreshConflict(
                lane_key=lane_key,
                conflict="incremental-state-invalid",
                detail=str(exc),
            )

    try:
        connection_settings = await load_runtime_legacy_source_connection_settings()
    except LegacySourceCompatibilityError as exc:
        return RefreshConflict(
            lane_key=lane_key,
            conflict="legacy-source-settings-missing",
            detail=str(exc),
        )

    batch_id = (
        build_shadow_batch_id("legacy-shadow")
        if request.mode == RefreshMode.FULL_REBASELINE
        else build_incremental_batch_id("legacy-incremental")
    )

    launched_at = _iso_now()

    # Write job metadata to Redis for status polling (AC4, AC5)
    try:
        r = await _get_redis()
        await _write_redis_job(r, job_id, {
            "job_id": job_id,
            "batch_id": batch_id,
            "mode": request.mode.value,
            "tenant_id": str(request.tenant_id),
            "schema_name": request.schema_name,
            "source_schema": request.source_schema,
            "dry_run": request.dry_run,
            "lookback_days": request.lookback_days,
            "reconciliation_threshold": request.reconciliation_threshold,
            "actor_id": current_user.get("sub", "unknown"),
            "actor_role": current_user.get("role"),
            "launched_at": launched_at,
            "status": "queued",
        })
    except RedisJobCacheUnavailable:
        pass
    except Exception:
        logger.warning(
            "Redis unavailable: failed to write job metadata for job_id=%s, lane_key=%s. "
            "Falling back to lane-state files for status.",
            job_id,
            lane_key,
        )

    # Launch durable background worker (AC5: not BackgroundTasks)
    if request.mode == RefreshMode.FULL_REBASELINE:
        asyncio.create_task(
            _launch_full_rebaseline(
                tenant_id=request.tenant_id,
                schema_name=request.schema_name,
                source_schema=request.source_schema,
                lookback_days=request.lookback_days,
                reconciliation_threshold=request.reconciliation_threshold,
                job_id=job_id,
                batch_id=batch_id,
                launched_at=launched_at,
                connection_settings=connection_settings,
            )
        )
    else:
        asyncio.create_task(
            _launch_incremental(
                tenant_id=request.tenant_id,
                schema_name=request.schema_name,
                source_schema=request.source_schema,
                lookback_days=request.lookback_days,
                reconciliation_threshold=request.reconciliation_threshold,
                job_id=job_id,
                batch_id=batch_id,
                launched_at=launched_at,
                connection_settings=connection_settings,
            )
        )

    return RefreshJobLaunched(
        job_id=job_id,
        lane_key=lane_key,
        mode=request.mode,
        batch_id=batch_id,
        launched_at=launched_at,
        status="queued",
    )


# ---------------------------------------------------------------------------
# AC2: Status endpoint
# ---------------------------------------------------------------------------

@router.get(
    "/status",
    response_model=RefreshLaneStatus,
    summary="Get legacy refresh lane status",
    description=(
        "Returns the current state of the specified lane, including lane lock status, "
        "batch pointers (latest run, latest success, latest promoted), "
        "promotion policy outcome, and root failure details (AC2)."
    ),
)
async def get_lane_status(
    tenant_id: uuid.UUID,
    schema_name: str = Query(..., min_length=1),
    source_schema: str = Query(default="public"),
) -> RefreshLaneStatus:
    """AC2: Return lane state, batch pointers, promotion policy outcome."""
    return _load_lane_status(tenant_id, schema_name, source_schema)


@router.get(
    "/lanes",
    response_model=RefreshLanesResponse,
    summary="List all legacy refresh lanes",
    description="Returns status for all lanes that have been touched by the refresh pipeline.",
)
async def list_lanes() -> RefreshLanesResponse:
    """Return status for all known lanes.

    Lanes are discovered by scanning the state root for subdirectories.
    """
    state_root = DEFAULT_SUMMARY_ROOT / "state"
    if not state_root.exists():
        return RefreshLanesResponse(lanes=[])

    lanes: list[RefreshLaneStatus] = []
    for lane_dir in state_root.iterdir():
        if not lane_dir.is_dir():
            continue
        # Lane dir names encode the lane key: schema_name-tenant_id-source_schema
        parts = lane_dir.name.rsplit("-", 2)
        if len(parts) != 3:
            continue
        try:
            schema_name, tenant_str, source_schema = parts
            tid = uuid.UUID(tenant_str)
            status = _load_lane_status(tid, schema_name, source_schema)
            lanes.append(status)
        except (ValueError, OSError):
            continue

    return RefreshLanesResponse(lanes=lanes)


@router.get(
    "/jobs/{job_id}",
    summary="Get refresh job status by job ID",
    description="Returns the current status of a specific refresh job (AC4).",
)
async def get_job_status(
    job_id: str,
) -> dict[str, Any]:
    """AC4: Poll job status by job ID.

    First checks Redis for live job metadata, then falls back to lane-state files.
    """
    redis_job: dict[str, Any] | None = None
    try:
        r = await _get_redis()
        redis_job = await _read_redis_job(r, job_id)
    except RedisJobCacheUnavailable:
        pass
    except Exception:
        logger.warning(
            "Redis unavailable: failed to read job metadata for job_id=%s. "
            "Falling back to lane-state file scan.",
            job_id,
        )

    sentinel_job = _read_job_sentinel(job_id)
    if redis_job and sentinel_job:
        return {
            **redis_job,
            **sentinel_job,
        }
    if sentinel_job:
        return sentinel_job
    if redis_job:
        return redis_job

    raise HTTPException(status_code=404, detail="Job not found")


@router.get(
    "/recent-runs",
    response_model=list[RefreshJobRecord],
    summary="List recent refresh runs",
    description="Returns the most recent refresh run records for all lanes (AC2, AC4).",
)
async def get_recent_runs(
    limit: int = Query(default=10, ge=1, le=50),
) -> list[RefreshJobRecord]:
    """AC2: Surface recent runs for operator diagnostics."""
    state_root = DEFAULT_SUMMARY_ROOT / "state"
    if not state_root.exists():
        return []

    records: list[RefreshJobRecord] = []
    for lane_dir in state_root.iterdir():
        if not lane_dir.is_dir():
            continue
        run_path = lane_dir / "latest-run.json"
        raw, _ = read_json_file_with_error(run_path)
        if raw is None:
            continue

        disp = raw.get("final_disposition", "")
        blocked = disp in (
            RefreshDisposition.OVERLAP_BLOCKED.value,
            RefreshDisposition.VALIDATION_BLOCKED.value,
        )
        blocked_reason: str | None = None
        if blocked:
            if disp == RefreshDisposition.OVERLAP_BLOCKED.value:
                blocked_reason = "concurrent refresh blocked"
            elif disp == RefreshDisposition.VALIDATION_BLOCKED.value:
                blocked_reason = "validation threshold exceeded"

        pp = raw.get("promotion_policy")
        promotion_eligible = (
            isinstance(pp, dict) and pp.get("classification") == "eligible"
        )

        records.append(RefreshJobRecord(
            job_id=raw.get("scheduler_run_id", raw.get("batch_id", "")),
            batch_id=raw.get("batch_id", ""),
            mode="full-rebaseline"
            if "shadow" in raw.get("batch_id", "")
            else "incremental",
            started_at=raw.get("started_at", ""),
            completed_at=raw.get("completed_at"),
            final_disposition=disp,
            validation_status=raw.get("validation_status"),
            promotion_eligible=promotion_eligible,
            blocked=blocked,
            blocked_reason=blocked_reason,
        ))

    # Sort by started_at descending
    records.sort(key=lambda r: r.started_at, reverse=True)
    return records[:limit]
