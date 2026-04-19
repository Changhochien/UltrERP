"""Shared lane-state helpers for legacy refresh workflows."""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from common.cli_args import normalize_token

LOCK_STALE_AFTER = timedelta(hours=6)


@dataclass(slots=True, frozen=True)
class LegacyRefreshLanePaths:
    lane_root: Path
    latest_run_path: Path
    latest_success_path: Path
    latest_promoted_path: Path
    incremental_state_path: Path
    nightly_rebaseline_path: Path
    lock_path: Path
    promotion_lock_path: Path
    promotion_results_root: Path
    promotion_overrides_root: Path


def lane_key(*, tenant_id: uuid.UUID, schema_name: str, source_schema: str) -> str:
    return "-".join(
        (
            normalize_token(schema_name),
            normalize_token(str(tenant_id)),
            normalize_token(source_schema),
        )
    )


def build_lane_state_paths(
    *,
    tenant_id: uuid.UUID,
    schema_name: str,
    source_schema: str,
    summary_root: Path,
    state_root: Path | None = None,
) -> LegacyRefreshLanePaths:
    resolved_state_root = state_root or (summary_root / "state")
    lane_root = resolved_state_root / lane_key(
        tenant_id=tenant_id,
        schema_name=schema_name,
        source_schema=source_schema,
    )
    return LegacyRefreshLanePaths(
        lane_root=lane_root,
        latest_run_path=lane_root / "latest-run.json",
        latest_success_path=lane_root / "latest-success.json",
        latest_promoted_path=lane_root / "latest-promoted.json",
        incremental_state_path=lane_root / "incremental-state.json",
        nightly_rebaseline_path=lane_root / "nightly-full-rebaseline.json",
        lock_path=lane_root / "scheduler.lock",
        promotion_lock_path=lane_root / "promotion.lock",
        promotion_results_root=lane_root / "promotion-results",
        promotion_overrides_root=lane_root / "promotion-overrides",
    )


def read_json_file(path: Path) -> dict[str, Any] | None:
    result, _ = read_json_file_with_error(path)
    return result


def read_json_file_with_error(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except FileNotFoundError:
        return None, None
    except UnicodeDecodeError as exc:
        return None, str(exc)
    except json.JSONDecodeError as exc:
        return None, (
            f"invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"
        )
    except OSError as exc:
        return None, str(exc)


def write_json_atomically(target_path: Path, payload: dict[str, Any]) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temp_path_str = tempfile.mkstemp(
        prefix=f".{target_path.stem}-",
        suffix=".tmp",
        dir=target_path.parent,
    )
    temp_path = Path(temp_path_str)
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, target_path)
    except Exception:
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass
        raise


def write_lock_file(lock_path: Path, payload: dict[str, Any]) -> None:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass
        raise


def _parse_lock_timestamp(value: object | None) -> datetime | None:
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


def recover_stale_lock(
    lock_path: Path,
    *,
    now: datetime | None = None,
    stale_after: timedelta = LOCK_STALE_AFTER,
) -> bool:
    lock_payload = read_json_file(lock_path)
    lock_started_at = None
    if isinstance(lock_payload, dict):
        lock_started_at = _parse_lock_timestamp(lock_payload.get("acquired_at"))
        if lock_started_at is None:
            lock_started_at = _parse_lock_timestamp(lock_payload.get("started_at"))
    if lock_started_at is None:
        try:
            stat_result = lock_path.stat()
        except FileNotFoundError:
            return False
        lock_started_at = datetime.fromtimestamp(stat_result.st_mtime, tz=timezone.utc)

    current_time = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if current_time - lock_started_at < stale_after:
        return False

    remove_file_if_exists(lock_path)
    return True


def write_lock_file_with_recovery(
    lock_path: Path,
    payload: dict[str, Any],
    *,
    now: datetime | None = None,
    stale_after: timedelta = LOCK_STALE_AFTER,
) -> bool:
    try:
        write_lock_file(lock_path, payload)
        return False
    except FileExistsError:
        if not recover_stale_lock(lock_path, now=now, stale_after=stale_after):
            raise
        write_lock_file(lock_path, payload)
        return True


def remove_file_if_exists(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass