from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from domains.legacy_import.rebaseline_policy import (
    RebaselinePolicyConfig,
    RebaselineReason,
    evaluate_rebaseline_policy,
)
from scripts.legacy_refresh_common import RefreshBatchMode

TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _state(**overrides):
    payload = {
        "tenant_id": str(TENANT_ID),
        "schema_name": "raw_legacy",
        "source_schema": "public",
        "batch_id": "legacy-shadow-20260418T020304Z",
        "batch_mode": "full",
        "affected_domains": ["sales"],
        "completed_at": "2026-04-18T02:05:00+00:00",
        "legacy_schema_signature": "legacy-v1",
        "canonical_schema_signature": "canonical-v1",
        "mapping_logic_version": "mapping-v1",
        "normalization_logic_version": "normalization-v1",
        "canonical_logic_version": "canonical-v1",
        "reconciliation_gap_count": 0,
    }
    payload.update(overrides)
    return payload


def _incremental_state(**overrides):
    payload = {
        "tenant_id": str(TENANT_ID),
        "schema_name": "raw_legacy",
        "source_schema": "public",
        "domains": {
            "sales": {"bootstrap_required": False},
        },
        "recorded_at": "2026-04-18T02:05:00+00:00",
    }
    payload.update(overrides)
    return payload


def test_rebaseline_policy_config_rejects_full_default_schedule_mode() -> None:
    with pytest.raises(ValueError, match="full refresh as the default daily mode"):
        RebaselinePolicyConfig(default_schedule_mode=RefreshBatchMode.FULL)


@pytest.mark.parametrize(
    (
        "latest_success_state",
        "incremental_state",
        "nightly_rebaseline_state",
        "config",
        "expected_reason",
    ),
    [
        (
            None,
            None,
            None,
            RebaselinePolicyConfig(),
            RebaselineReason.NEW_LANE,
        ),
        (
            _state(legacy_schema_signature="legacy-v0"),
            _incremental_state(),
            _state(),
            RebaselinePolicyConfig(legacy_schema_signature="legacy-v1"),
            RebaselineReason.SCHEMA_CHANGE_LEGACY,
        ),
        (
            _state(canonical_schema_signature="canonical-v0"),
            _incremental_state(),
            _state(),
            RebaselinePolicyConfig(canonical_schema_signature="canonical-v1"),
            RebaselineReason.SCHEMA_CHANGE_CANONICAL,
        ),
        (
            _state(mapping_logic_version="mapping-v0"),
            _incremental_state(),
            _state(),
            RebaselinePolicyConfig(),
            RebaselineReason.LOGIC_CHANGE_MAPPING,
        ),
        (
            _state(normalization_logic_version="normalization-v0"),
            _incremental_state(),
            _state(),
            RebaselinePolicyConfig(),
            RebaselineReason.LOGIC_CHANGE_NORMALIZATION,
        ),
        (
            _state(canonical_logic_version="canonical-v0"),
            _incremental_state(),
            _state(),
            RebaselinePolicyConfig(),
            RebaselineReason.LOGIC_CHANGE_CANONICAL,
        ),
        (
            _state(),
            None,
            _state(),
            RebaselinePolicyConfig(),
            RebaselineReason.STALE_WATERMARK,
        ),
        (
            _state(completed_at="2026-04-01T02:05:00+00:00"),
            _incremental_state(),
            _state(completed_at="2026-04-01T02:05:00+00:00"),
            RebaselinePolicyConfig(rebaseline_cadence_days=7),
            RebaselineReason.STALE_WATERMARK,
        ),
        (
            _state(reconciliation_gap_count=3),
            _incremental_state(),
            _state(),
            RebaselinePolicyConfig(reconciliation_drift_threshold=0),
            RebaselineReason.DRIFT,
        ),
        (
            _state(affected_domains=["sales"]),
            _incremental_state(),
            _state(),
            RebaselinePolicyConfig(replay_trust_ok=False),
            RebaselineReason.REPLAY_TRUST_FAILURE,
        ),
        (
            _state(),
            _incremental_state(),
            _state(),
            RebaselinePolicyConfig(force_rebaseline=True),
            RebaselineReason.OPERATOR_REQUEST,
        ),
    ],
)
def test_rebaseline_policy_triggers_full_rebaseline_for_documented_reasons(
    latest_success_state,
    incremental_state,
    nightly_rebaseline_state,
    config,
    expected_reason,
) -> None:
    decision = evaluate_rebaseline_policy(
        tenant_id=TENANT_ID,
        schema_name="raw_legacy",
        source_schema="public",
        latest_success_state=latest_success_state,
        incremental_state=incremental_state,
        nightly_rebaseline_state=nightly_rebaseline_state,
        config=config,
        now=datetime(2026, 4, 18, 2, 30, 0, tzinfo=timezone.utc),
    )

    assert decision.batch_mode is RefreshBatchMode.FULL
    assert decision.rebaseline_reason is expected_reason


def test_rebaseline_policy_defaults_to_incremental_when_triggers_clear() -> None:
    decision = evaluate_rebaseline_policy(
        tenant_id=TENANT_ID,
        schema_name="raw_legacy",
        source_schema="public",
        latest_success_state=_state(batch_mode="incremental", affected_domains=["parties"]),
        incremental_state=_incremental_state(),
        nightly_rebaseline_state=_state(),
        config=RebaselinePolicyConfig(),
        now=datetime(2026, 4, 18, 2, 30, 0, tzinfo=timezone.utc),
    )

    assert decision.batch_mode is RefreshBatchMode.INCREMENTAL
    assert decision.rebaseline_reason is None
