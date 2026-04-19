from __future__ import annotations

import uuid

import pytest

import domains.legacy_import.incremental_refresh as incremental_refresh
import domains.legacy_import.incremental_state as incremental_state
from scripts.legacy_refresh_state import build_lane_state_paths

TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _latest_success_state(*, batch_id: str) -> dict[str, object]:
    return {
        "state_version": 1,
        "batch_id": batch_id,
        "summary_path": f"/tmp/{batch_id}-summary.json",
        "tenant_id": str(TENANT_ID),
        "schema_name": "raw_legacy",
        "source_schema": "public",
        "completed_at": "2026-04-18T02:03:04+00:00",
        "final_disposition": "completed",
        "validation_status": "passed",
        "blocking_issue_count": 0,
        "reconciliation_gap_count": 0,
        "reconciliation_threshold": 0,
        "analyst_review_required": False,
        "promotion_readiness": True,
        "promotion_policy": {
            "classification": "eligible",
            "reason_codes": [],
        },
    }


def _promoted_state(*, batch_id: str) -> dict[str, object]:
    return {
        "batch_id": batch_id,
        "tenant_id": str(TENANT_ID),
        "schema_name": "raw_legacy",
        "source_schema": "public",
        "promoted_at": "2026-04-18T02:05:00+00:00",
        "promoted_by": "SYSTEM",
        "summary_path": f"/tmp/{batch_id}-summary.json",
        "validation_status": "passed",
        "blocking_issue_count": 0,
        "reconciliation_gap_count": 0,
        "reconciliation_threshold": 0,
        "promotion_result": "promoted",
    }


def test_build_lane_state_paths_exposes_incremental_contract_files(tmp_path) -> None:
    lane_paths = build_lane_state_paths(
        tenant_id=TENANT_ID,
        schema_name="raw_legacy",
        source_schema="public",
        summary_root=tmp_path / "ops",
    )

    assert lane_paths.incremental_state_path == lane_paths.lane_root / "incremental-state.json"
    assert lane_paths.nightly_rebaseline_path == (
        lane_paths.lane_root / "nightly-full-rebaseline.json"
    )


def test_supported_incremental_domain_contracts_stay_within_reviewed_tables() -> None:
    contracts = incremental_state.supported_incremental_domain_contracts()

    assert [contract.name for contract in contracts] == [
        "parties",
        "products",
        "warehouses",
        "inventory",
        "sales",
        "purchase-invoices",
    ]
    assert {
        table
        for contract in contracts
        for table in contract.source_tables
    } <= {"tbscust", "tbsstock", "tbsstkhouse", "tbsslipx", "tbsslipdtx", "tbsslipj", "tbsslipdtj"}
    sales_contract = next(contract for contract in contracts if contract.name == "sales")
    assert sales_contract.source_tables == ("tbsslipx", "tbsslipdtx")
    assert sales_contract.parent_child_batch_rule == "header-and-line-pair"


def test_reseed_incremental_state_from_full_refresh_tracks_rebaseline_and_bootstrap() -> None:
    state = incremental_state.reseed_incremental_state_from_full_refresh(
        tenant_id=TENANT_ID,
        schema_name="raw_legacy",
        source_schema="public",
        latest_success_state=_latest_success_state(batch_id="legacy-shadow-20260418T020304Z"),
        latest_promoted_state=_promoted_state(batch_id="legacy-shadow-20260417T020304Z"),
        recorded_at="2026-04-18T02:10:00+00:00",
    )

    assert state["current_shadow_candidate"]["batch_id"] == "legacy-shadow-20260418T020304Z"
    assert state["last_successful_shadow_candidate"]["batch_id"] == (
        "legacy-shadow-20260418T020304Z"
    )
    assert state["latest_promoted_working_batch"]["batch_id"] == "legacy-shadow-20260417T020304Z"
    assert state["last_nightly_full_rebaseline"]["batch_id"] == "legacy-shadow-20260418T020304Z"
    assert set(state["domains"]) == {
        "parties",
        "products",
        "warehouses",
        "inventory",
        "sales",
        "purchase-invoices",
    }
    assert all(
        domain_state["last_successful_watermark"] is None
        and domain_state["bootstrap_required"] is True
        for domain_state in state["domains"].values()
    )


def test_record_incremental_candidate_result_keeps_prior_watermarks_when_blocked() -> None:
    initial_state = incremental_state.reseed_incremental_state_from_full_refresh(
        tenant_id=TENANT_ID,
        schema_name="raw_legacy",
        source_schema="public",
        latest_success_state=_latest_success_state(batch_id="legacy-shadow-20260418T020304Z"),
        latest_promoted_state=_promoted_state(batch_id="legacy-shadow-20260417T020304Z"),
        recorded_at="2026-04-18T02:10:00+00:00",
    )
    initial_state["domains"]["sales"]["last_successful_watermark"] = {
        "cursor": ["2026-04-18T02:00:00+00:00", "SO-000123", 4],
        "recorded_at": "2026-04-18T02:00:05+00:00",
    }
    initial_state["domains"]["sales"]["last_successful_batch_id"] = "inc-eligible-001"
    initial_state["domains"]["sales"]["bootstrap_required"] = False
    initial_state["last_successful_shadow_candidate"] = {
        "batch_id": "inc-eligible-001",
        "summary_path": "/tmp/inc-eligible-001-summary.json",
    }

    updated_state = incremental_state.record_incremental_candidate_result(
        state=initial_state,
        candidate_state={
            "batch_id": "inc-blocked-002",
            "summary_path": "/tmp/inc-blocked-002-summary.json",
            "promotion_policy": {
                "classification": "blocked",
                "reason_codes": ["reconciliation"],
            },
        },
        latest_promoted_state=_promoted_state(batch_id="legacy-shadow-20260417T020304Z"),
        committed_watermarks={
            "sales": {
                "cursor": ["2026-04-18T02:30:00+00:00", "SO-000200", 1],
                "recorded_at": "2026-04-18T02:30:05+00:00",
            }
        },
        advance_watermarks=False,
        recorded_at="2026-04-18T02:31:00+00:00",
    )

    assert updated_state["current_shadow_candidate"]["batch_id"] == "inc-blocked-002"
    assert updated_state["domains"]["sales"]["last_successful_watermark"] == {
        "cursor": ["2026-04-18T02:00:00+00:00", "SO-000123", 4],
        "recorded_at": "2026-04-18T02:00:05+00:00",
    }
    assert updated_state["domains"]["sales"]["last_successful_batch_id"] == "inc-eligible-001"
    assert updated_state["last_successful_shadow_candidate"] == {
        "batch_id": "inc-eligible-001",
        "summary_path": "/tmp/inc-eligible-001-summary.json",
    }
    assert updated_state["latest_promoted_working_batch"]["batch_id"] == (
        "legacy-shadow-20260417T020304Z"
    )


@pytest.mark.parametrize(
    ("classification", "reason_codes"),
    [
        ("blocked", ["reconciliation"]),
        ("exception-required", ["analyst-review"]),
    ],
)
def test_record_incremental_candidate_result_requires_eligible_candidate_to_advance(
    classification: str,
    reason_codes: list[str],
) -> None:
    initial_state = incremental_state.reseed_incremental_state_from_full_refresh(
        tenant_id=TENANT_ID,
        schema_name="raw_legacy",
        source_schema="public",
        latest_success_state=_latest_success_state(batch_id="legacy-shadow-20260418T020304Z"),
        latest_promoted_state=_promoted_state(batch_id="legacy-shadow-20260417T020304Z"),
        recorded_at="2026-04-18T02:10:00+00:00",
    )
    initial_state["domains"]["sales"]["last_successful_watermark"] = {
        "cursor": ["2026-04-18T02:00:00+00:00", "SO-000123", 4],
        "recorded_at": "2026-04-18T02:00:05+00:00",
    }
    initial_state["domains"]["sales"]["last_successful_batch_id"] = "inc-eligible-001"
    initial_state["domains"]["sales"]["bootstrap_required"] = False
    initial_state["last_successful_shadow_candidate"] = {
        "batch_id": "inc-eligible-001",
        "summary_path": "/tmp/inc-eligible-001-summary.json",
    }

    updated_state = incremental_state.record_incremental_candidate_result(
        state=initial_state,
        candidate_state={
            "batch_id": "inc-unsafe-002",
            "summary_path": "/tmp/inc-unsafe-002-summary.json",
            "promotion_policy": {
                "classification": classification,
                "reason_codes": reason_codes,
            },
        },
        latest_promoted_state=_promoted_state(batch_id="legacy-shadow-20260417T020304Z"),
        committed_watermarks={
            "sales": {
                "cursor": ["2026-04-18T02:30:00+00:00", "SO-000200", 1],
                "recorded_at": "2026-04-18T02:30:05+00:00",
            }
        },
        advance_watermarks=True,
        recorded_at="2026-04-18T02:31:00+00:00",
    )

    assert updated_state["current_shadow_candidate"]["batch_id"] == "inc-unsafe-002"
    assert updated_state["domains"]["sales"]["last_successful_watermark"] == {
        "cursor": ["2026-04-18T02:00:00+00:00", "SO-000123", 4],
        "recorded_at": "2026-04-18T02:00:05+00:00",
    }
    assert updated_state["domains"]["sales"]["last_successful_batch_id"] == "inc-eligible-001"
    assert updated_state["last_successful_shadow_candidate"] == {
        "batch_id": "inc-eligible-001",
        "summary_path": "/tmp/inc-eligible-001-summary.json",
    }


def test_build_incremental_refresh_plan_resumes_from_last_successful_watermark() -> None:
    state = incremental_state.reseed_incremental_state_from_full_refresh(
        tenant_id=TENANT_ID,
        schema_name="raw_legacy",
        source_schema="public",
        latest_success_state=_latest_success_state(batch_id="legacy-shadow-20260418T020304Z"),
        latest_promoted_state=_promoted_state(batch_id="legacy-shadow-20260417T020304Z"),
        recorded_at="2026-04-18T02:10:00+00:00",
    )
    state["domains"]["sales"]["last_successful_watermark"] = {
        "cursor": ["2026-04-18T02:00:00+00:00", "SO-000123", 4],
        "recorded_at": "2026-04-18T02:00:05+00:00",
    }
    state["domains"]["sales"]["last_successful_batch_id"] = "inc-eligible-001"
    state["domains"]["sales"]["bootstrap_required"] = False

    plan = incremental_refresh.build_incremental_refresh_plan(state=state)

    assert plan["latest_promoted_working_batch"]["batch_id"] == "legacy-shadow-20260417T020304Z"
    assert plan["last_successful_shadow_candidate"]["batch_id"] == (
        "legacy-shadow-20260418T020304Z"
    )
    assert plan["domains"]["sales"]["resume_mode"] == "resume-from-last-successful-watermark"
    assert plan["domains"]["sales"]["resume_from_watermark"] == {
        "cursor": ["2026-04-18T02:00:00+00:00", "SO-000123", 4],
        "recorded_at": "2026-04-18T02:00:05+00:00",
    }
    assert plan["domains"]["purchase-invoices"]["resume_mode"] == (
        "bootstrap-from-nightly-rebaseline"
    )
    assert plan["working_lane_protection"] == (
        "advance-latest-promoted-only-after-shared-promotion-eligibility"
    )


def test_build_incremental_refresh_plan_requires_bootstrap_anchor() -> None:
    state = incremental_state.reseed_incremental_state_from_full_refresh(
        tenant_id=TENANT_ID,
        schema_name="raw_legacy",
        source_schema="public",
        latest_success_state=_latest_success_state(batch_id="legacy-shadow-20260418T020304Z"),
        latest_promoted_state=_promoted_state(batch_id="legacy-shadow-20260417T020304Z"),
        recorded_at="2026-04-18T02:10:00+00:00",
    )
    state["last_nightly_full_rebaseline"] = None

    with pytest.raises(ValueError, match="missing a nightly rebaseline"):
        incremental_refresh.build_incremental_refresh_plan(state=state)