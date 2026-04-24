from __future__ import annotations

import uuid
from collections.abc import Mapping
from copy import deepcopy
from typing import Any

import pytest

from domains.legacy_import.delta_discovery import (
    DELTA_MANIFEST_VERSION,
    build_delta_manifest,
    discover_delta,
)
from domains.legacy_import.incremental_refresh import build_incremental_refresh_plan
from domains.legacy_import.incremental_state import (
    reseed_incremental_state_from_full_refresh,
)

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
        "promotion_policy": {"classification": "eligible", "reason_codes": []},
    }


def _bootstrap_state() -> dict[str, Any]:
    return reseed_incremental_state_from_full_refresh(
        tenant_id=TENANT_ID,
        schema_name="raw_legacy",
        source_schema="public",
        latest_success_state=_latest_success_state(batch_id="legacy-full-20260418T020000Z"),
        latest_promoted_state=None,
        recorded_at="2026-04-18T02:04:00+00:00",
    )


def _advance_domain_watermark(
    state: dict[str, Any],
    *,
    domain: str,
    watermark: Mapping[str, Any],
) -> dict[str, Any]:
    state["domains"][domain]["last_successful_watermark"] = dict(watermark)
    state["domains"][domain]["bootstrap_required"] = False
    return state


def test_discover_delta_marks_domains_with_no_changes_as_no_op() -> None:
    state = _bootstrap_state()
    plan = build_incremental_refresh_plan(state=state)

    discovery = discover_delta(
        plan=plan,
        source_projection=lambda contract, watermark: [],
    )

    assert discovery.batch_mode == "incremental"
    assert discovery.active_domains == ()
    assert set(discovery.no_op_domains) == set(plan["domains"].keys())
    for domain in discovery.domains:
        assert domain.status == "no-op"
        assert domain.changed_keys == ()
        assert domain.closure_keys == ()
        assert domain.closure_count == 0


def test_discover_delta_flags_bootstrap_resume_mode_for_first_run() -> None:
    state = _bootstrap_state()
    plan = build_incremental_refresh_plan(state=state)

    def projection(contract, watermark):
        if contract.name == "parties":
            return [{"source-change-ts": "2026-04-18T02:05:00+00:00", "party-code": "P001"}]
        return []

    discovery = discover_delta(plan=plan, source_projection=projection)

    parties = next(domain for domain in discovery.domains if domain.name == "parties")
    assert parties.status == "bootstrap"
    assert parties.resume_mode == "bootstrap-from-nightly-rebaseline"
    assert parties.changed_keys == (
        {"source-change-ts": "2026-04-18T02:05:00+00:00", "party-code": "P001"},
    )


def test_discover_delta_applies_header_and_line_closure_for_sales() -> None:
    state = _bootstrap_state()
    state = _advance_domain_watermark(
        state,
        domain="sales",
        watermark={
            "document-date": "2026-04-17",
            "document-number": "S000000",
            "line-number": 0,
        },
    )
    plan = build_incremental_refresh_plan(state=state)

    def projection(contract, watermark):
        if contract.name == "sales":
            return [
                {
                    "document-date": "2026-04-18",
                    "document-number": "S000001",
                    "line-number": 1,
                    "document_number": "S000001",
                },
                {
                    "document-date": "2026-04-18",
                    "document-number": "S000001",
                    "line-number": 2,
                    "document_number": "S000001",
                },
                {
                    "document-date": "2026-04-18",
                    "document-number": "S000002",
                    "line-number": 1,
                    "document_number": "S000002",
                },
            ]
        return []

    discovery = discover_delta(plan=plan, source_projection=projection)

    sales = next(domain for domain in discovery.domains if domain.name == "sales")
    assert sales.status == "active"
    assert sales.resume_mode == "resume-from-last-successful-watermark"
    assert sales.closure_count == 2
    assert sales.closure_keys == (
        {"document_number": "S000001"},
        {"document_number": "S000002"},
    )
    assert sales.watermark_in == {
        "document-date": "2026-04-17",
        "document-number": "S000000",
        "line-number": 0,
    }
    assert sales.watermark_out_proposed == {
        "document-date": "2026-04-18",
        "document-number": "S000002",
        "line-number": 1,
    }


def test_discover_delta_applies_warehouse_product_closure_for_inventory() -> None:
    state = _bootstrap_state()
    state = _advance_domain_watermark(
        state,
        domain="inventory",
        watermark={
            "source-change-ts": "2026-04-17T00:00:00+00:00",
            "warehouse-code": "W0",
            "product-code": "P0",
        },
    )
    plan = build_incremental_refresh_plan(state=state)

    def projection(contract, watermark):
        if contract.name == "inventory":
            return [
                {
                    "source-change-ts": "2026-04-18T01:00:00+00:00",
                    "warehouse-code": "W1",
                    "product-code": "P1",
                    "warehouse_code": "W1",
                    "product_code": "P1",
                },
                {
                    "source-change-ts": "2026-04-18T01:05:00+00:00",
                    "warehouse-code": "W1",
                    "product-code": "P1",
                    "warehouse_code": "W1",
                    "product_code": "P1",
                },
                {
                    "source-change-ts": "2026-04-18T01:10:00+00:00",
                    "warehouse-code": "W2",
                    "product-code": "P1",
                    "warehouse_code": "W2",
                    "product_code": "P1",
                },
            ]
        return []

    discovery = discover_delta(plan=plan, source_projection=projection)

    inventory = next(
        domain for domain in discovery.domains if domain.name == "inventory"
    )
    assert inventory.closure_count == 2
    assert inventory.closure_keys == (
        {"warehouse_code": "W1", "product_code": "P1"},
        {"warehouse_code": "W2", "product_code": "P1"},
    )


def test_discover_delta_keeps_single_table_rule_for_parties() -> None:
    state = _bootstrap_state()
    state = _advance_domain_watermark(
        state,
        domain="parties",
        watermark={"source-change-ts": "2026-04-17T00:00:00+00:00", "party-code": "P0"},
    )
    plan = build_incremental_refresh_plan(state=state)

    def projection(contract, watermark):
        if contract.name == "parties":
            return [
                {"source-change-ts": "2026-04-18T01:00:00+00:00", "party-code": "P1"},
                {"source-change-ts": "2026-04-18T01:05:00+00:00", "party-code": "P1"},
                {"source-change-ts": "2026-04-18T01:10:00+00:00", "party-code": "P2"},
            ]
        return []

    discovery = discover_delta(plan=plan, source_projection=projection)
    parties = next(domain for domain in discovery.domains if domain.name == "parties")

    assert parties.closure_count == 2


def test_discover_delta_rejects_unknown_domain_in_plan() -> None:
    state = _bootstrap_state()
    plan = build_incremental_refresh_plan(state=state)
    plan["domains"]["bogus"] = {
        "resume_mode": "resume-from-last-successful-watermark",
        "resume_from_watermark": {"source-change-ts": "2026-04-18", "bogus-code": "X"},
    }

    with pytest.raises(ValueError, match="unknown incremental domain 'bogus'"):
        discover_delta(plan=plan, source_projection=lambda contract, watermark: [])


def test_build_delta_manifest_shape_is_append_only_and_audit_ready() -> None:
    state = _bootstrap_state()
    state = _advance_domain_watermark(
        state,
        domain="parties",
        watermark={"source-change-ts": "2026-04-17T00:00:00+00:00", "party-code": "P0"},
    )
    plan = build_incremental_refresh_plan(state=state)

    def projection(contract, watermark):
        if contract.name == "parties":
            return [
                {"source-change-ts": "2026-04-18T01:00:00+00:00", "party-code": "P1"}
            ]
        return []

    discovery = discover_delta(plan=plan, source_projection=projection)
    manifest = build_delta_manifest(
        run_id="run-1",
        batch_id="legacy-incremental-20260418T020000Z",
        tenant_id=TENANT_ID,
        schema_name="raw_legacy",
        source_schema="public",
        recorded_at="2026-04-18T02:05:00+00:00",
        plan=plan,
        discovery=discovery,
    )

    assert manifest["manifest_version"] == DELTA_MANIFEST_VERSION
    assert manifest["batch_mode"] == "incremental"
    assert manifest["batch_id"] == "legacy-incremental-20260418T020000Z"
    assert "parties" in manifest["active_domains"]
    assert manifest["planned_domains"] == list(plan["domains"].keys())
    parties_entry = manifest["domains"]["parties"]
    assert parties_entry["status"] == "active"
    assert parties_entry["changed_key_count"] == 1
    assert parties_entry["closure_count"] == 1
    assert parties_entry["watermark_in"] == {
        "source-change-ts": "2026-04-17T00:00:00+00:00",
        "party-code": "P0",
    }
    assert parties_entry["watermark_out_proposed"] == {
        "source-change-ts": "2026-04-18T01:00:00+00:00",
        "party-code": "P1",
    }


def test_build_delta_manifest_preserves_no_op_domains_separately() -> None:
    state = _bootstrap_state()
    state = _advance_domain_watermark(
        state,
        domain="parties",
        watermark={"source-change-ts": "2026-04-17T00:00:00+00:00", "party-code": "P0"},
    )
    state = _advance_domain_watermark(
        state,
        domain="products",
        watermark={"source-change-ts": "2026-04-17T00:00:00+00:00", "product-code": "P0"},
    )
    plan = build_incremental_refresh_plan(state=state)

    def projection(contract, watermark):
        if contract.name == "parties":
            return [
                {"source-change-ts": "2026-04-18T01:00:00+00:00", "party-code": "P1"}
            ]
        return []

    discovery = discover_delta(plan=plan, source_projection=projection)
    manifest = build_delta_manifest(
        run_id="run-2",
        batch_id="legacy-incremental-20260418T020500Z",
        tenant_id=TENANT_ID,
        schema_name="raw_legacy",
        source_schema="public",
        recorded_at="2026-04-18T02:05:00+00:00",
        plan=plan,
        discovery=discovery,
    )

    assert "parties" in manifest["active_domains"]
    assert "products" in manifest["no_op_domains"]
    assert manifest["domains"]["products"]["status"] == "no-op"
    assert manifest["domains"]["products"]["changed_key_count"] == 0
    # No-op domain's watermark_out must not advance beyond its watermark_in.
    assert (
        manifest["domains"]["products"]["watermark_out_proposed"]
        == manifest["domains"]["products"]["watermark_in"]
    )


def test_discover_delta_does_not_mutate_plan() -> None:
    """AC1: Verify discovery is read-only and does not advance any watermark."""
    state = _bootstrap_state()
    state = _advance_domain_watermark(
        state,
        domain="parties",
        watermark={"source-change-ts": "2026-04-17T00:00:00+00:00", "party-code": "P0"},
    )
    plan = build_incremental_refresh_plan(state=state)
    # Capture plan snapshot before discovery
    parties_watermark_before = deepcopy(
        plan["domains"]["parties"]["resume_from_watermark"]
    )

    def projection(contract, watermark):
        if contract.name == "parties":
            return [
                {"source-change-ts": "2026-04-18T01:00:00+00:00", "party-code": "P1"}
            ]
        return []

    discover_delta(plan=plan, source_projection=projection)

    # Plan watermarks must be unchanged after discovery
    assert (
        plan["domains"]["parties"]["resume_from_watermark"] == parties_watermark_before
    )


def test_discover_delta_applies_header_and_line_closure_for_purchase_invoices() -> None:
    """AC2: Purchase-invoices should expand to full document families via document_number."""
    state = _bootstrap_state()
    state = _advance_domain_watermark(
        state,
        domain="purchase-invoices",
        watermark={
            "document-date": "2026-04-17",
            "document-number": "PI000000",
            "line-number": 0,
        },
    )
    plan = build_incremental_refresh_plan(state=state)

    def projection(contract, watermark):
        if contract.name == "purchase-invoices":
            return [
                {
                    "document-date": "2026-04-18",
                    "document-number": "PI000001",
                    "line-number": 1,
                    "document_number": "PI000001",
                },
                {
                    "document-date": "2026-04-18",
                    "document-number": "PI000001",
                    "line-number": 2,
                    "document_number": "PI000001",
                },
                {
                    "document-date": "2026-04-18",
                    "document-number": "PI000001",
                    "line-number": 3,
                    "document_number": "PI000001",
                },
                {
                    "document-date": "2026-04-18",
                    "document-number": "PI000002",
                    "line-number": 1,
                    "document_number": "PI000002",
                },
            ]
        return []

    discovery = discover_delta(plan=plan, source_projection=projection)

    pi = next(
        domain for domain in discovery.domains if domain.name == "purchase-invoices"
    )
    assert pi.status == "active"
    assert pi.parent_child_batch_rule == "header-and-line-pair"
    assert pi.closure_count == 2
    assert pi.closure_keys == (
        {"document_number": "PI000001"},
        {"document_number": "PI000002"},
    )


def test_manifest_includes_parent_child_batch_rule_and_replay_window() -> None:
    """AC3: Manifest domain entries must include replay_window and parent_child_batch_rule."""
    state = _bootstrap_state()
    state = _advance_domain_watermark(
        state,
        domain="inventory",
        watermark={
            "source-change-ts": "2026-04-17T00:00:00+00:00",
            "warehouse-code": "W0",
            "product-code": "P0",
        },
    )
    plan = build_incremental_refresh_plan(state=state)

    def projection(contract, watermark):
        if contract.name == "inventory":
            return [
                {
                    "source-change-ts": "2026-04-18T01:00:00+00:00",
                    "warehouse-code": "W1",
                    "product-code": "P1",
                    "warehouse_code": "W1",
                    "product_code": "P1",
                }
            ]
        return []

    discovery = discover_delta(plan=plan, source_projection=projection)
    manifest = build_delta_manifest(
        run_id="run-ac3",
        batch_id="legacy-incremental-20260418T030000Z",
        tenant_id=TENANT_ID,
        schema_name="raw_legacy",
        source_schema="public",
        recorded_at="2026-04-18T03:00:00+00:00",
        plan=plan,
        discovery=discovery,
    )

    inventory_entry = manifest["domains"]["inventory"]
    assert "replay_window" in inventory_entry
    assert "parent_child_batch_rule" in inventory_entry
    assert inventory_entry["parent_child_batch_rule"] == "warehouse-product-pair"
    assert "replay" in inventory_entry["replay_window"].lower()


def test_discover_delta_is_deterministic_on_rerun() -> None:
    """AC5: Same source projection must produce identical delta discovery on rerun."""
    state = _bootstrap_state()
    state = _advance_domain_watermark(
        state,
        domain="parties",
        watermark={"source-change-ts": "2026-04-17T00:00:00+00:00", "party-code": "P0"},
    )
    state = _advance_domain_watermark(
        state,
        domain="products",
        watermark={"source-change-ts": "2026-04-17T00:00:00+00:00", "product-code": "P0"},
    )
    plan = build_incremental_refresh_plan(state=state)

    def projection(contract, watermark):
        if contract.name == "parties":
            return [
                {"source-change-ts": "2026-04-18T01:00:00+00:00", "party-code": "P1"},
                {"source-change-ts": "2026-04-18T01:05:00+00:00", "party-code": "P2"},
            ]
        if contract.name == "products":
            return []
        return []

    first_run = discover_delta(plan=plan, source_projection=projection)
    second_run = discover_delta(plan=plan, source_projection=projection)

    # Results must be structurally identical
    assert first_run.batch_mode == second_run.batch_mode
    assert first_run.planned_domains == second_run.planned_domains
    assert first_run.active_domains == second_run.active_domains
    assert first_run.no_op_domains == second_run.no_op_domains
    for first_domain, second_domain in zip(
        first_run.domains, second_run.domains, strict=True
    ):
        assert first_domain.name == second_domain.name
        assert first_domain.status == second_domain.status
        assert first_domain.resume_mode == second_domain.resume_mode
        assert first_domain.changed_keys == second_domain.changed_keys
        assert first_domain.closure_keys == second_domain.closure_keys
        assert first_domain.closure_count == second_domain.closure_count
        assert first_domain.watermark_in == second_domain.watermark_in
        assert (
            first_domain.watermark_out_proposed
            == second_domain.watermark_out_proposed
        )
