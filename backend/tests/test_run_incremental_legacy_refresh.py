from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

from domains.legacy_import.staging import LegacySourceConnectionSettings
from scripts import run_incremental_legacy_refresh as incremental
from scripts.legacy_refresh_common import RefreshBatchMode
from scripts.legacy_refresh_state import build_lane_state_paths, write_json_atomically
from scripts.run_legacy_refresh import (
    SUPPORTED_FULL_REFRESH_DOMAINS,
    LegacyRefreshExecution,
)

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


def _seed_incremental_state(tmp_path: Path) -> Path:
    summary_root = tmp_path / "ops"
    lane_paths = build_lane_state_paths(
        tenant_id=TENANT_ID,
        schema_name="raw_legacy",
        source_schema="public",
        summary_root=summary_root,
    )
    rebaseline = {
        "batch_id": "legacy-shadow-20260418T020304Z",
        "summary_path": str(summary_root / "shadow-refresh.json"),
        "validation_status": "passed",
        "blocking_issue_count": 0,
        "reconciliation_gap_count": 0,
        "reconciliation_threshold": 0,
        "final_disposition": "completed",
        "completed_at": "2026-04-18T02:05:00+00:00",
        "analyst_review_required": False,
        "promotion_readiness": True,
        "promotion_policy": {
            "classification": "eligible",
            "reason_codes": [],
        },
    }
    state_payload = {
        "state_version": 1,
        "contract_version": 1,
        "lane_key": "raw_legacy-00000000000000000000000000000001-public",
        "tenant_id": str(TENANT_ID),
        "schema_name": "raw_legacy",
        "source_schema": "public",
        "recorded_at": "2026-04-18T02:10:00+00:00",
        "current_shadow_candidate": rebaseline,
        "last_successful_shadow_candidate": rebaseline,
        "last_nightly_full_rebaseline": {**rebaseline, "recorded_at": "2026-04-18T02:10:00+00:00"},
        "latest_promoted_working_batch": None,
        "domains": {
            "parties": {
                "source_tables": ["tbscust"],
                "watermark_source": "source-change-ts|party-code",
                "cursor_components": ["source-change-ts", "party-code"],
                "replay_window": "replay-previous-cursor",
                "late_arriving_correction": "replay-by-party-code",
                "promotion_boundary": "shared-promotion-policy",
                "parent_child_batch_rule": "single-table",
                "last_successful_watermark": {
                    "source-change-ts": "2026-04-17T00:00:00+00:00",
                    "party-code": "P-000",
                },
                "last_successful_batch_id": rebaseline["batch_id"],
                "last_successful_recorded_at": "2026-04-18T02:10:00+00:00",
                "bootstrap_required": False,
            },
            "products": {
                "source_tables": ["tbsstock"],
                "watermark_source": "source-change-ts|product-code",
                "cursor_components": ["source-change-ts", "product-code"],
                "replay_window": "replay-previous-cursor",
                "late_arriving_correction": "replay-by-product-code",
                "promotion_boundary": "shared-promotion-policy",
                "parent_child_batch_rule": "single-table",
                "last_successful_watermark": {
                    "source-change-ts": "2026-04-17T00:00:00+00:00",
                    "product-code": "P-000",
                },
                "last_successful_batch_id": rebaseline["batch_id"],
                "last_successful_recorded_at": "2026-04-18T02:10:00+00:00",
                "bootstrap_required": False,
            },
            "warehouses": {
                "source_tables": ["tbsstkhouse"],
                "watermark_source": "source-change-ts|warehouse-code",
                "cursor_components": ["source-change-ts", "warehouse-code"],
                "replay_window": "replay-previous-cursor",
                "late_arriving_correction": "replay-by-warehouse-code",
                "promotion_boundary": "shared-promotion-policy",
                "parent_child_batch_rule": "single-table",
                "last_successful_watermark": {
                    "source-change-ts": "2026-04-17T00:00:00+00:00",
                    "warehouse-code": "W-00",
                },
                "last_successful_batch_id": rebaseline["batch_id"],
                "last_successful_recorded_at": "2026-04-18T02:10:00+00:00",
                "bootstrap_required": False,
            },
            "inventory": {
                "source_tables": ["tbsstkhouse", "tbsstock"],
                "watermark_source": "source-change-ts|warehouse-code|product-code",
                "cursor_components": [
                    "source-change-ts",
                    "warehouse-code",
                    "product-code",
                ],
                "replay_window": "replay-previous-cursor",
                "late_arriving_correction": "replay-warehouse-product-pair",
                "promotion_boundary": "shared-promotion-policy",
                "parent_child_batch_rule": "warehouse-product-pair",
                "last_successful_watermark": {
                    "source-change-ts": "2026-04-17T00:00:00+00:00",
                    "warehouse-code": "W-00",
                    "product-code": "P-000",
                },
                "last_successful_batch_id": rebaseline["batch_id"],
                "last_successful_recorded_at": "2026-04-18T02:10:00+00:00",
                "bootstrap_required": False,
            },
            "sales": {
                "source_tables": ["tbsslipx", "tbsslipdtx"],
                "watermark_source": "document-date|document-number|line-number",
                "cursor_components": [
                    "document-date",
                    "document-number",
                    "line-number",
                ],
                "replay_window": "replay-previous-cursor",
                "late_arriving_correction": "replay-full-sales-family",
                "promotion_boundary": "shared-promotion-policy",
                "parent_child_batch_rule": "header-and-line-pair",
                "last_successful_watermark": {
                    "document-date": "2026-04-17",
                    "document-number": "S-00000",
                    "line-number": 0,
                },
                "last_successful_batch_id": rebaseline["batch_id"],
                "last_successful_recorded_at": "2026-04-18T02:10:00+00:00",
                "bootstrap_required": False,
            },
            "purchase-invoices": {
                "source_tables": ["tbsslipj", "tbsslipdtj"],
                "watermark_source": "document-date|document-number|line-number",
                "cursor_components": [
                    "document-date",
                    "document-number",
                    "line-number",
                ],
                "replay_window": "replay-previous-cursor",
                "late_arriving_correction": "replay-full-purchase-family",
                "promotion_boundary": "shared-promotion-policy",
                "parent_child_batch_rule": "header-and-line-pair",
                "last_successful_watermark": {
                    "document-date": "2026-04-17",
                    "document-number": "P-00000",
                    "line-number": 0,
                },
                "last_successful_batch_id": rebaseline["batch_id"],
                "last_successful_recorded_at": "2026-04-18T02:10:00+00:00",
                "bootstrap_required": False,
            },
        },
    }
    write_json_atomically(lane_paths.incremental_state_path, state_payload)
    return summary_root


def test_build_incremental_batch_id_uses_utc_timestamp() -> None:
    now = datetime(2026, 4, 18, 2, 3, 4, tzinfo=timezone.utc)

    batch_id = incremental.build_incremental_batch_id("legacy-incremental", now=now)

    assert batch_id == "legacy-incremental-20260418T020304Z"


def test_run_incremental_legacy_refresh_tags_batch_mode_and_affected_domains(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """When every planned domain is no-op, the runner skips the full-refresh
    pipeline and emits a ``completed-no-op`` summary directly. This is the
    Story 15.24 replacement for the Story 15.23 placeholder that re-widened
    scope to every plan domain.
    """
    summary_root = _seed_incremental_state(tmp_path)
    captured: dict[str, object] = {}

    async def fake_run_legacy_refresh(**kwargs):
        captured.update(kwargs)
        raise AssertionError(
            "run_legacy_refresh should not be invoked when every domain is no-op"
        )

    monkeypatch.setattr(incremental, "run_legacy_refresh", fake_run_legacy_refresh)
    monkeypatch.setattr(
        incremental,
        "utc_now",
        lambda: datetime(2026, 4, 19, 3, 2, 1, tzinfo=timezone.utc),
    )

    result = asyncio.run(
        incremental.run_incremental_legacy_refresh(
            tenant_id=TENANT_ID,
            schema_name="raw_legacy",
            source_schema="public",
            lookback_days=10000,
            reconciliation_threshold=0,
            summary_root=summary_root,
            source_projection=incremental.explicit_no_delta_projection,
        )
    )

    assert result.exit_code == 0
    assert captured == {}
    assert result.summary["batch_mode"] == RefreshBatchMode.INCREMENTAL.value
    assert result.summary["affected_domains"] == []
    assert result.summary["final_disposition"] == "completed-no-op"
    assert set(result.summary["no_op_domains"]) == set(SUPPORTED_FULL_REFRESH_DOMAINS)
    assert result.summary["batch_id"] == "legacy-incremental-20260419T030201Z"


def test_run_incremental_legacy_refresh_requires_incremental_state(tmp_path: Path) -> None:
    summary_root = tmp_path / "ops"
    with pytest.raises(FileNotFoundError):
        asyncio.run(
            incremental.run_incremental_legacy_refresh(
                tenant_id=TENANT_ID,
                schema_name="raw_legacy",
                source_schema="public",
                lookback_days=10000,
                reconciliation_threshold=0,
                summary_root=summary_root,
                source_projection=incremental.explicit_no_delta_projection,
            )
        )


def test_dry_run_emits_plan_and_skips_pipeline(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    summary_root = _seed_incremental_state(tmp_path)
    called = False

    def fail_if_called(**_kwargs):
        nonlocal called
        called = True
        raise AssertionError("run_legacy_refresh must not be invoked on --dry-run")

    monkeypatch.setattr(incremental, "run_legacy_refresh", fail_if_called)

    def fail_if_schema_upgrade_called() -> None:
        raise AssertionError("schema upgrade must not run on --dry-run")

    monkeypatch.setattr(
        incremental,
        "ensure_legacy_refresh_schema_current",
        fail_if_schema_upgrade_called,
    )
    monkeypatch.setattr(
        incremental,
        "build_lane_state_paths",
        lambda **kwargs: build_lane_state_paths(
            tenant_id=kwargs["tenant_id"],
            schema_name=kwargs["schema_name"],
            source_schema=kwargs["source_schema"],
            summary_root=summary_root,
            state_root=kwargs.get("state_root"),
        ),
    )
    monkeypatch.setattr(
        incremental,
        "build_live_source_projection_for_lane",
        lambda **_kwargs: incremental.explicit_no_delta_projection,
    )

    exit_code = incremental.main(
        [
            "--tenant-id",
            str(TENANT_ID),
            "--schema",
            "raw_legacy",
            "--source-schema",
            "public",
            "--dry-run",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert called is False
    assert "domains" in captured.out


def test_main_auto_upgrades_schema_before_running_incremental_refresh(
    monkeypatch,
) -> None:
    calls: list[str] = []
    expected_result = LegacyRefreshExecution(
        exit_code=0,
        summary_path=Path("incremental-summary.json"),
        summary={"final_disposition": "completed"},
    )

    def fake_upgrade() -> None:
        calls.append("upgrade")

    def fake_asyncio_run(coro):
        calls.append("run")
        coro.close()
        return expected_result

    monkeypatch.setattr(
        incremental,
        "ensure_legacy_refresh_schema_current",
        fake_upgrade,
    )
    monkeypatch.setattr(
        incremental,
        "build_live_source_projection_for_lane",
        lambda **_kwargs: incremental.explicit_no_delta_projection,
    )
    monkeypatch.setattr(incremental.asyncio, "run", fake_asyncio_run)

    exit_code = incremental.main(
        [
            "--tenant-id",
            str(TENANT_ID),
            "--schema",
            "raw_legacy",
        ]
    )

    assert exit_code == 0
    assert calls == ["upgrade", "run"]


def test_main_defaults_incremental_lookback_to_zero(monkeypatch) -> None:
    captured: dict[str, object] = {}

    async def fake_run_incremental_legacy_refresh(**kwargs):
        captured.update(kwargs)
        return LegacyRefreshExecution(
            exit_code=0,
            summary_path=Path("incremental-summary.json"),
            summary={"final_disposition": "completed"},
        )

    monkeypatch.setattr(
        incremental,
        "ensure_legacy_refresh_schema_current",
        lambda: None,
    )
    monkeypatch.setattr(
        incremental,
        "build_live_source_projection_for_lane",
        lambda **_kwargs: incremental.explicit_no_delta_projection,
    )
    monkeypatch.setattr(
        incremental,
        "run_incremental_legacy_refresh",
        fake_run_incremental_legacy_refresh,
    )

    exit_code = incremental.main(
        [
            "--tenant-id",
            str(TENANT_ID),
            "--schema",
            "raw_legacy",
        ]
    )

    assert exit_code == 0
    assert captured["lookback_days"] == incremental.DEFAULT_INCREMENTAL_LOOKBACK_DAYS


def test_build_live_source_projection_for_lane_uses_nightly_rebaseline_anchor(
    monkeypatch,
    tmp_path: Path,
) -> None:
    summary_root = _seed_incremental_state(tmp_path)
    captured: dict[str, object] = {}
    sentinel = object()
    connection_settings = _connection_settings()

    def fake_build_live_source_projection(**kwargs):
        captured.update(kwargs)
        return sentinel

    monkeypatch.setattr(
        incremental,
        "build_live_source_projection",
        fake_build_live_source_projection,
    )

    projection = incremental.build_live_source_projection_for_lane(
        tenant_id=TENANT_ID,
        schema_name="raw_legacy",
        source_schema="public",
        summary_root=summary_root,
        connection_settings=connection_settings,
    )

    assert projection is sentinel
    assert captured["source_schema"] == "public"
    assert captured["connection_settings"] == connection_settings
    bootstrap_state = captured["bootstrap_rebaseline_state"]
    assert isinstance(bootstrap_state, dict)
    assert bootstrap_state["batch_id"] == "legacy-shadow-20260418T020304Z"


def test_planner_value_error_wrapped_with_remediation_hint(
    monkeypatch,
    tmp_path: Path,
) -> None:
    summary_root = _seed_incremental_state(tmp_path)

    def broken_planner(*, state):  # noqa: ARG001
        raise ValueError("contract_version missing")

    monkeypatch.setattr(incremental, "build_incremental_refresh_plan", broken_planner)

    with pytest.raises(ValueError, match="run_scheduled_legacy_shadow_refresh"):
        asyncio.run(
            incremental.run_incremental_legacy_refresh(
                tenant_id=TENANT_ID,
                schema_name="raw_legacy",
                source_schema="public",
                lookback_days=10000,
                reconciliation_threshold=0,
                summary_root=summary_root,
                source_projection=incremental.explicit_no_delta_projection,
            )
        )


def test_run_incremental_writes_delta_manifest_and_scopes_active_domains(
    monkeypatch,
    tmp_path: Path,
) -> None:
    summary_root = _seed_incremental_state(tmp_path)
    captured: dict = {}
    connection_settings = _connection_settings()

    async def fake_run_legacy_refresh(**kwargs):
        captured.update(kwargs)
        summary_path = (
            summary_root / f"{kwargs['batch_id']}-summary.json"
        )
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text("{}", encoding="utf-8")
        return LegacyRefreshExecution(
            exit_code=0,
            summary_path=summary_path,
            summary={
                "batch_id": kwargs["batch_id"],
                "batch_mode": kwargs["batch_mode"],
                "affected_domains": list(kwargs["affected_domains"]),
                "final_disposition": "completed",
            },
        )

    monkeypatch.setattr(incremental, "run_legacy_refresh", fake_run_legacy_refresh)
    monkeypatch.setattr(
        incremental,
        "utc_now",
        lambda: datetime(2026, 4, 19, 4, 3, 2, tzinfo=timezone.utc),
    )

    def projection(contract, watermark):
        if contract.name == "parties":
            return [
                {
                    "source-change-ts": "2026-04-18T03:00:00+00:00",
                    "party-code": "P-001",
                }
            ]
        return []

    asyncio.run(
        incremental.run_incremental_legacy_refresh(
            tenant_id=TENANT_ID,
            schema_name="raw_legacy",
            source_schema="public",
            lookback_days=10000,
            reconciliation_threshold=0,
            summary_root=summary_root,
            source_projection=projection,
            connection_settings=connection_settings,
        )
    )

    assert captured["batch_mode"] == RefreshBatchMode.INCREMENTAL.value
    assert captured["affected_domains"] == ("parties",)
    assert captured["connection_settings"] == connection_settings
    lane_paths = build_lane_state_paths(
        tenant_id=TENANT_ID,
        schema_name="raw_legacy",
        source_schema="public",
        summary_root=summary_root,
    )
    manifest_path = lane_paths.lane_root / (
        f"delta-manifest-{captured['batch_id']}.json"
    )
    assert manifest_path.exists()
    import json

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["batch_mode"] == "incremental"
    assert manifest["active_domains"] == ["parties"]
    assert "products" in manifest["no_op_domains"]
    assert manifest["domains"]["parties"]["changed_key_count"] == 1


def test_run_incremental_publishes_lane_state_and_advances_watermarks(
    monkeypatch,
    tmp_path: Path,
) -> None:
    summary_root = _seed_incremental_state(tmp_path)

    async def fake_run_legacy_refresh(**kwargs):
        summary_path = summary_root / f"{kwargs['batch_id']}-summary.json"
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text("{}", encoding="utf-8")
        return LegacyRefreshExecution(
            exit_code=0,
            summary_path=summary_path,
            summary={
                "batch_id": kwargs["batch_id"],
                "batch_mode": RefreshBatchMode.INCREMENTAL.value,
                "affected_domains": list(kwargs["affected_domains"]),
                "final_disposition": "completed",
                "promotion_gate_status": {
                    "validation": {
                        "status": "passed",
                        "blocking_issue_count": 0,
                    }
                },
                "reconciliation_gap_count": 0,
                "analyst_review_required": False,
                "promotion_readiness": True,
                "promotion_policy": {
                    "classification": "eligible",
                    "reason_codes": [],
                },
                "watermark_advanced": True,
                "advanced_domains": list(kwargs["affected_domains"]),
                "freshness_success": True,
            },
        )

    monkeypatch.setattr(incremental, "run_legacy_refresh", fake_run_legacy_refresh)
    monkeypatch.setattr(
        incremental,
        "utc_now",
        lambda: datetime(2026, 4, 19, 6, 5, 4, tzinfo=timezone.utc),
    )

    def projection(contract, watermark):
        if contract.name == "parties":
            return [
                {
                    "source-change-ts": "2026-04-18T03:00:00+00:00",
                    "party-code": "P-001",
                }
            ]
        return []

    result = asyncio.run(
        incremental.run_incremental_legacy_refresh(
            tenant_id=TENANT_ID,
            schema_name="raw_legacy",
            source_schema="public",
            lookback_days=10000,
            reconciliation_threshold=0,
            summary_root=summary_root,
            source_projection=projection,
            scheduler_run_id="job-123",
            started_at="2026-04-19T06:05:04+00:00",
        )
    )

    lane_paths = build_lane_state_paths(
        tenant_id=TENANT_ID,
        schema_name="raw_legacy",
        source_schema="public",
        summary_root=summary_root,
    )
    latest_run = json.loads(lane_paths.latest_run_path.read_text(encoding="utf-8"))
    latest_success = json.loads(
        lane_paths.latest_success_path.read_text(encoding="utf-8")
    )
    updated_state = json.loads(
        lane_paths.incremental_state_path.read_text(encoding="utf-8")
    )

    assert latest_run["scheduler_run_id"] == "job-123"
    assert latest_run["batch_id"] == result.summary["batch_id"]
    assert latest_run["watermark_advanced"] is True
    assert latest_run["advanced_domains"] == ["parties"]
    assert latest_success["batch_id"] == result.summary["batch_id"]
    assert updated_state["current_shadow_candidate"]["batch_id"] == result.summary["batch_id"]
    assert (
        updated_state["last_successful_shadow_candidate"]["batch_id"]
        == result.summary["batch_id"]
    )
    assert updated_state["domains"]["parties"]["last_successful_watermark"] == {
        "source-change-ts": "2026-04-18T03:00:00+00:00",
        "party-code": "P-001",
    }
    assert (
        updated_state["domains"]["parties"]["last_successful_batch_id"]
        == result.summary["batch_id"]
    )


def test_run_incremental_threads_entity_scope_and_last_successful_batch_ids(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """Story 15.25: the incremental runner must hand ``entity_scope`` and
    ``last_successful_batch_ids`` to ``run_legacy_refresh`` so scoped
    staging + carryforward can take effect downstream."""
    summary_root = _seed_incremental_state(tmp_path)
    captured: dict = {}

    async def fake_run_legacy_refresh(**kwargs):
        captured.update(kwargs)
        summary_path = (
            summary_root / f"{kwargs['batch_id']}-summary.json"
        )
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text("{}", encoding="utf-8")
        return LegacyRefreshExecution(
            exit_code=0,
            summary_path=summary_path,
            summary={
                "batch_id": kwargs["batch_id"],
                "batch_mode": kwargs["batch_mode"],
                "affected_domains": list(kwargs["affected_domains"]),
                "final_disposition": "completed",
            },
        )

    monkeypatch.setattr(incremental, "run_legacy_refresh", fake_run_legacy_refresh)
    monkeypatch.setattr(
        incremental,
        "utc_now",
        lambda: datetime(2026, 4, 19, 5, 4, 3, tzinfo=timezone.utc),
    )

    def projection(contract, watermark):
        if contract.name == "parties":
            return [
                {
                    "source-change-ts": "2026-04-18T03:00:00+00:00",
                    "party-code": "P-100",
                },
                {
                    "source-change-ts": "2026-04-18T03:00:05+00:00",
                    "party-code": "P-101",
                },
            ]
        return []

    asyncio.run(
        incremental.run_incremental_legacy_refresh(
            tenant_id=TENANT_ID,
            schema_name="raw_legacy",
            source_schema="public",
            lookback_days=10000,
            reconciliation_threshold=0,
            summary_root=summary_root,
            source_projection=projection,
        )
    )

    # Scope narrows to the only active domain (parties).
    assert captured["affected_domains"] == ("parties",)

    # entity_scope comes from the manifest and is keyed by contract name.
    # Each value is the per-domain manifest subsection containing the
    # closure keys the staging adapter will filter by.
    entity_scope = captured["entity_scope"]
    assert "parties" in entity_scope
    parties_scope = entity_scope["parties"]
    assert parties_scope["closure_count"] == 2
    closure_key_values = {
        closure["party-code"] for closure in parties_scope["closure_keys"]
    }
    assert closure_key_values == {"P-100", "P-101"}
    # Out-of-scope domains must not leak into entity_scope.
    assert "products" not in entity_scope
    assert "warehouses" not in entity_scope
    assert "inventory" not in entity_scope

    # last_successful_batch_ids is populated from the plan's baseline so
    # carryforward can target the prior successful rebaseline batch.
    last_ids = captured["last_successful_batch_ids"]
    assert "parties" in last_ids
    assert last_ids["parties"] == "legacy-shadow-20260418T020304Z"
    # Out-of-scope domains don't get a stale prior-batch pointer.
    assert "products" not in last_ids


def test_run_incremental_adds_dependent_master_batch_ids_for_sales_scope(
    monkeypatch,
    tmp_path: Path,
) -> None:
    summary_root = _seed_incremental_state(tmp_path)
    captured: dict = {}

    async def fake_run_legacy_refresh(**kwargs):
        captured.update(kwargs)
        summary_path = summary_root / f"{kwargs['batch_id']}-summary.json"
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text("{}", encoding="utf-8")
        return LegacyRefreshExecution(
            exit_code=0,
            summary_path=summary_path,
            summary={
                "batch_id": kwargs["batch_id"],
                "batch_mode": kwargs["batch_mode"],
                "affected_domains": list(kwargs["affected_domains"]),
                "final_disposition": "completed",
            },
        )

    monkeypatch.setattr(incremental, "run_legacy_refresh", fake_run_legacy_refresh)
    monkeypatch.setattr(
        incremental,
        "utc_now",
        lambda: datetime(2026, 4, 19, 5, 4, 3, tzinfo=timezone.utc),
    )

    def projection(contract, watermark):
        if contract.name != "sales":
            return []
        return [
            {
                "document-date": "2026-04-18",
                "document-number": "S-100",
                "document_number": "S-100",
                "line-number": 1,
            }
        ]

    asyncio.run(
        incremental.run_incremental_legacy_refresh(
            tenant_id=TENANT_ID,
            schema_name="raw_legacy",
            source_schema="public",
            lookback_days=10000,
            reconciliation_threshold=0,
            summary_root=summary_root,
            source_projection=projection,
        )
    )

    assert captured["affected_domains"] == ("sales",)
    last_ids = captured["last_successful_batch_ids"]
    assert last_ids["sales"] == "legacy-shadow-20260418T020304Z"
    assert last_ids["parties"] == "legacy-shadow-20260418T020304Z"
    assert last_ids["products"] == "legacy-shadow-20260418T020304Z"
    assert "warehouses" not in last_ids


def test_build_entity_scope_rejects_missing_required_domain() -> None:
    manifest = {
        "domains": {
            "sales": {
                "closure_keys": [],
            }
        }
    }

    with pytest.raises(ValueError, match="missing required domain 'parties'"):
        incremental._build_entity_scope(manifest, ("parties",))
