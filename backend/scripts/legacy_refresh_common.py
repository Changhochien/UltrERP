"""Shared helpers and status enums for legacy refresh scripts."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum

from common.cli_args import normalize_token, parse_non_negative_int, parse_tenant_uuid

DEFAULT_BATCH_PREFIX = "legacy-shadow"


def build_timestamped_batch_id(
    prefix: str = DEFAULT_BATCH_PREFIX,
    batch_id: str | None = None,
    timestamp: datetime | None = None,
    now: datetime | None = None,  # Alias for timestamp
) -> str:
    """Build a deterministic or custom batch ID with optional timestamp suffix.

    If batch_id is provided, return it as-is.
    Otherwise, generate a timestamped ID in the format: {prefix}-{YYYYMMDD}T{HHMMSS}Z.
    """
    if batch_id:
        return batch_id
    ts = timestamp or now or datetime.now(timezone.utc)
    return f"{prefix}-{ts.strftime('%Y%m%dT%H%M%S')}Z"


def parse_batch_prefix(value: str | None) -> str:
    """Parse and validate a batch prefix string."""
    if value is None:
        return DEFAULT_BATCH_PREFIX
    normalized = normalize_token(value)
    if not normalized:
        return DEFAULT_BATCH_PREFIX
    # Sanitize: only allow alphanumeric, dash, underscore
    import re
    sanitized = re.sub(r"[^a-zA-Z0-9_-]", "-", normalized)
    return sanitized or DEFAULT_BATCH_PREFIX


class RefreshBatchMode(StrEnum):
    """Batch execution mode for legacy refresh runs."""

    FULL = "full"
    INCREMENTAL = "incremental"
    REBASELINE = "rebaseline"


def coerce_refresh_batch_mode(value: str | RefreshBatchMode) -> RefreshBatchMode:
    """Convert a string to RefreshBatchMode, accepting common aliases."""
    if isinstance(value, RefreshBatchMode):
        return value
    normalized = value.strip().lower()
    if normalized in ("full", "nightly", "shadow"):
        return RefreshBatchMode.FULL
    if normalized in ("incremental", "delta"):
        return RefreshBatchMode.INCREMENTAL
    if normalized == "rebaseline":
        return RefreshBatchMode.REBASELINE
    raise ValueError(f"Unknown refresh batch mode: {value!r}")


class RefreshStepStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"
    BLOCKED = "blocked"


class RefreshGateStatus(StrEnum):
    PENDING = "pending"
    PASSED = "passed"
    BLOCKED = "blocked"
    REVIEW_REQUIRED = "review-required"
    REVIEW_IMPORTED = "review-imported"
    NOT_RUN = "not-run"


class RefreshDisposition(StrEnum):
    RUNNING = "running"
    FAILED = "failed"
    VALIDATION_BLOCKED = "validation-blocked"
    RECONCILIATION_BLOCKED = "reconciliation-blocked"
    COMPLETED = "completed"
    COMPLETED_NO_OP = "completed-no-op"
    COMPLETED_REVIEW_REQUIRED = "completed-review-required"
    OVERLAP_BLOCKED = "overlap-blocked"