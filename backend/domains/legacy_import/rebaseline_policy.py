"""Policy helper for choosing scheduled incremental runs versus full rebaselines."""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from typing import Any

from scripts.legacy_refresh_common import RefreshBatchMode, coerce_refresh_batch_mode


class RebaselineReason(StrEnum):
    NEW_LANE = "new-lane"
    SCHEMA_CHANGE_LEGACY = "schema-change-legacy"
    SCHEMA_CHANGE_CANONICAL = "schema-change-canonical"
    LOGIC_CHANGE_MAPPING = "logic-change-mapping"
    LOGIC_CHANGE_NORMALIZATION = "logic-change-normalization"
    LOGIC_CHANGE_CANONICAL = "logic-change-canonical"
    STALE_WATERMARK = "stale-watermark"
    DRIFT = "drift"
    REPLAY_TRUST_FAILURE = "replay-trust-failure"
    OPERATOR_REQUEST = "operator-request"


@dataclass(slots=True, frozen=True)
class RebaselinePolicyConfig:
    default_schedule_mode: RefreshBatchMode | str = RefreshBatchMode.INCREMENTAL
    rebaseline_cadence_days: int = 7
    reconciliation_drift_threshold: int = 0
    force_rebaseline: bool = False
    legacy_schema_signature: str | None = None
    canonical_schema_signature: str | None = None
    mapping_logic_version: str | None = "mapping-v1"
    normalization_logic_version: str | None = "normalization-v1"
    canonical_logic_version: str | None = "canonical-v1"
    replay_trust_ok: bool = True

    def __post_init__(self) -> None:
        default_mode = coerce_refresh_batch_mode(self.default_schedule_mode)
        if default_mode is not RefreshBatchMode.INCREMENTAL:
            raise ValueError(
                "Scheduled refresh configuration cannot set full refresh as the default daily mode."
            )
        if self.rebaseline_cadence_days < 1:
            raise ValueError("rebaseline_cadence_days must be at least 1")
        if self.reconciliation_drift_threshold < 0:
            raise ValueError("reconciliation_drift_threshold must be non-negative")
        object.__setattr__(self, "default_schedule_mode", default_mode)

    def as_record(self) -> dict[str, Any]:
        return {
            "default_schedule_mode": self.default_schedule_mode.value,
            "rebaseline_cadence_days": self.rebaseline_cadence_days,
            "reconciliation_drift_threshold": self.reconciliation_drift_threshold,
            "force_rebaseline": self.force_rebaseline,
            "legacy_schema_signature": self.legacy_schema_signature,
            "canonical_schema_signature": self.canonical_schema_signature,
            "mapping_logic_version": self.mapping_logic_version,
            "normalization_logic_version": self.normalization_logic_version,
            "canonical_logic_version": self.canonical_logic_version,
            "replay_trust_ok": self.replay_trust_ok,
        }


@dataclass(slots=True, frozen=True)
class RebaselinePolicyDecision:
    batch_mode: RefreshBatchMode
    rebaseline_reason: RebaselineReason | None
    details: dict[str, Any]

    def as_record(self) -> dict[str, Any]:
        return {
            "batch_mode": self.batch_mode.value,
            "rebaseline_reason": (
                self.rebaseline_reason.value if self.rebaseline_reason is not None else None
            ),
            "details": dict(self.details),
        }


def _mapping(value: Mapping[str, object] | None) -> Mapping[str, object]:
    if isinstance(value, Mapping):
        return value
    return {}


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
    return int(value)


def _as_datetime(value: object | None) -> datetime | None:
    text = _as_text(value)
    if text is None:
        return None
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _lane_matches(
    state: Mapping[str, object] | None,
    *,
    tenant_id: uuid.UUID,
    schema_name: str,
    source_schema: str,
) -> bool:
    payload = _mapping(state)
    if not payload:
        return False
    return (
        _as_text(payload.get("tenant_id")) == str(tenant_id)
        and _as_text(payload.get("schema_name")) == schema_name
        and _as_text(payload.get("source_schema")) == source_schema
    )


def _field_changed(
    state: Mapping[str, object] | None,
    field_name: str,
    current_value: str | None,
) -> bool:
    if current_value is None:
        return False
    previous_value = _as_text(_mapping(state).get(field_name))
    return previous_value != current_value


def _contains_document_domains(state: Mapping[str, object] | None) -> bool:
    affected_domains = _mapping(state).get("affected_domains")
    if not isinstance(affected_domains, list):
        return False
    return any(domain in {"sales", "purchase-invoices"} for domain in affected_domains)


def _rebaseline_anchor_time(
    nightly_rebaseline_state: Mapping[str, object] | None,
    latest_success_state: Mapping[str, object] | None,
) -> datetime | None:
    for candidate in (nightly_rebaseline_state, latest_success_state):
        payload = _mapping(candidate)
        if not payload:
            continue
        for field_name in ("completed_at", "recorded_at", "started_at"):
            parsed = _as_datetime(payload.get(field_name))
            if parsed is not None:
                return parsed
    return None


def _incremental_state_looks_consistent(
    incremental_state: Mapping[str, object] | None,
    *,
    tenant_id: uuid.UUID,
    schema_name: str,
    source_schema: str,
) -> bool:
    payload = _mapping(incremental_state)
    if not payload:
        return False
    if not _lane_matches(
        payload,
        tenant_id=tenant_id,
        schema_name=schema_name,
        source_schema=source_schema,
    ):
        return False
    domains = payload.get("domains")
    return isinstance(domains, Mapping) and bool(domains)


def _decision(
    *,
    batch_mode: RefreshBatchMode,
    rebaseline_reason: RebaselineReason | None,
    details: dict[str, Any],
) -> RebaselinePolicyDecision:
    return RebaselinePolicyDecision(
        batch_mode=batch_mode,
        rebaseline_reason=rebaseline_reason,
        details=details,
    )


def evaluate_rebaseline_policy(
    *,
    tenant_id: uuid.UUID,
    schema_name: str,
    source_schema: str,
    latest_success_state: Mapping[str, object] | None,
    incremental_state: Mapping[str, object] | None,
    nightly_rebaseline_state: Mapping[str, object] | None,
    config: RebaselinePolicyConfig,
    now: datetime | None = None,
) -> RebaselinePolicyDecision:
    current_time = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    latest_success = _mapping(latest_success_state)
    nightly_rebaseline = _mapping(nightly_rebaseline_state)

    if config.force_rebaseline:
        return _decision(
            batch_mode=RefreshBatchMode.FULL,
            rebaseline_reason=RebaselineReason.OPERATOR_REQUEST,
            details={
                "trigger": RebaselineReason.OPERATOR_REQUEST.value,
                "config": config.as_record(),
            },
        )

    if not latest_success:
        return _decision(
            batch_mode=RefreshBatchMode.FULL,
            rebaseline_reason=RebaselineReason.NEW_LANE,
            details={
                "trigger": RebaselineReason.NEW_LANE.value,
                "config": config.as_record(),
            },
        )

    if _field_changed(
        latest_success,
        "legacy_schema_signature",
        config.legacy_schema_signature,
    ):
        return _decision(
            batch_mode=RefreshBatchMode.FULL,
            rebaseline_reason=RebaselineReason.SCHEMA_CHANGE_LEGACY,
            details={"trigger": RebaselineReason.SCHEMA_CHANGE_LEGACY.value},
        )

    if _field_changed(
        latest_success,
        "canonical_schema_signature",
        config.canonical_schema_signature,
    ):
        return _decision(
            batch_mode=RefreshBatchMode.FULL,
            rebaseline_reason=RebaselineReason.SCHEMA_CHANGE_CANONICAL,
            details={"trigger": RebaselineReason.SCHEMA_CHANGE_CANONICAL.value},
        )

    if _field_changed(
        latest_success,
        "mapping_logic_version",
        config.mapping_logic_version,
    ):
        return _decision(
            batch_mode=RefreshBatchMode.FULL,
            rebaseline_reason=RebaselineReason.LOGIC_CHANGE_MAPPING,
            details={"trigger": RebaselineReason.LOGIC_CHANGE_MAPPING.value},
        )

    if _field_changed(
        latest_success,
        "normalization_logic_version",
        config.normalization_logic_version,
    ):
        return _decision(
            batch_mode=RefreshBatchMode.FULL,
            rebaseline_reason=RebaselineReason.LOGIC_CHANGE_NORMALIZATION,
            details={"trigger": RebaselineReason.LOGIC_CHANGE_NORMALIZATION.value},
        )

    if _field_changed(
        latest_success,
        "canonical_logic_version",
        config.canonical_logic_version,
    ):
        return _decision(
            batch_mode=RefreshBatchMode.FULL,
            rebaseline_reason=RebaselineReason.LOGIC_CHANGE_CANONICAL,
            details={"trigger": RebaselineReason.LOGIC_CHANGE_CANONICAL.value},
        )

    if not config.replay_trust_ok and _contains_document_domains(latest_success):
        return _decision(
            batch_mode=RefreshBatchMode.FULL,
            rebaseline_reason=RebaselineReason.REPLAY_TRUST_FAILURE,
            details={"trigger": RebaselineReason.REPLAY_TRUST_FAILURE.value},
        )

    if not _incremental_state_looks_consistent(
        incremental_state,
        tenant_id=tenant_id,
        schema_name=schema_name,
        source_schema=source_schema,
    ):
        return _decision(
            batch_mode=RefreshBatchMode.FULL,
            rebaseline_reason=RebaselineReason.STALE_WATERMARK,
            details={"trigger": RebaselineReason.STALE_WATERMARK.value},
        )

    anchor_time = _rebaseline_anchor_time(nightly_rebaseline, latest_success)
    if anchor_time is None or current_time - anchor_time >= timedelta(
        days=config.rebaseline_cadence_days
    ):
        return _decision(
            batch_mode=RefreshBatchMode.FULL,
            rebaseline_reason=RebaselineReason.STALE_WATERMARK,
            details={
                "trigger": RebaselineReason.STALE_WATERMARK.value,
                "rebaseline_cadence_days": config.rebaseline_cadence_days,
            },
        )

    reconciliation_gap_count = _as_int(latest_success.get("reconciliation_gap_count")) or 0
    if reconciliation_gap_count > config.reconciliation_drift_threshold:
        return _decision(
            batch_mode=RefreshBatchMode.FULL,
            rebaseline_reason=RebaselineReason.DRIFT,
            details={
                "trigger": RebaselineReason.DRIFT.value,
                "reconciliation_gap_count": reconciliation_gap_count,
                "reconciliation_drift_threshold": config.reconciliation_drift_threshold,
            },
        )

    return _decision(
        batch_mode=RefreshBatchMode.INCREMENTAL,
        rebaseline_reason=None,
        details={
            "trigger": "incremental-default",
            "config": config.as_record(),
        },
    )
