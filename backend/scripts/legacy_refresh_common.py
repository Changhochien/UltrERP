"""Shared helpers and status enums for legacy refresh scripts."""

from __future__ import annotations

from enum import StrEnum

from common.cli_args import normalize_token, parse_non_negative_int, parse_tenant_uuid


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
    COMPLETED_REVIEW_REQUIRED = "completed-review-required"
    OVERLAP_BLOCKED = "overlap-blocked"