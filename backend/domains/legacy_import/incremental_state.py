"""Incremental refresh watermark contract and durable lane-state helpers."""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from scripts.legacy_refresh_state import lane_key

INCREMENTAL_CONTRACT_VERSION = 1
INCREMENTAL_STATE_VERSION = 1
ELIGIBLE_PROMOTION_CLASSIFICATION = "eligible"
WORKING_LANE_PROTECTION = (
    "advance-latest-promoted-only-after-shared-promotion-eligibility"
)


@dataclass(slots=True, frozen=True)
class IncrementalDomainContract:
    name: str
    source_tables: tuple[str, ...]
    watermark_source: str
    cursor_components: tuple[str, ...]
    replay_window: str
    late_arriving_correction: str
    promotion_boundary: str
    parent_child_batch_rule: str


SUPPORTED_INCREMENTAL_DOMAIN_CONTRACTS = (
    IncrementalDomainContract(
        name="parties",
        source_tables=("tbscust",),
        watermark_source=(
            "source-change-ts|party-code from the reviewed incremental source adapter "
            "projection for tbscust"
        ),
        cursor_components=("source-change-ts", "party-code"),
        replay_window=(
            "replay the previous successful tbscust cursor window plus the current "
            "cursor range"
        ),
        late_arriving_correction=(
            "replay by party code and keep the batch shadow-only until downstream "
            "sales and purchase validations stay clean"
        ),
        promotion_boundary=(
            "candidate stays shadow-only until the shared promotion policy evaluates "
            "the combined lane summary"
        ),
        parent_child_batch_rule="single-table",
    ),
    IncrementalDomainContract(
        name="products",
        source_tables=("tbsstock",),
        watermark_source=(
            "source-change-ts|product-code from the reviewed incremental source adapter "
            "projection for tbsstock"
        ),
        cursor_components=("source-change-ts", "product-code"),
        replay_window=(
            "replay the previous successful product cursor window plus the current "
            "cursor range"
        ),
        late_arriving_correction=(
            "replay by product code and require the shared product-mapping and "
            "validation surfaces to stay green before promotion"
        ),
        promotion_boundary=(
            "candidate stays shadow-only until the shared promotion policy evaluates "
            "the combined lane summary"
        ),
        parent_child_batch_rule="single-table",
    ),
    IncrementalDomainContract(
        name="warehouses",
        source_tables=("tbsstkhouse",),
        watermark_source=(
            "source-change-ts|warehouse-code from the reviewed incremental source "
            "adapter projection for tbsstkhouse"
        ),
        cursor_components=("source-change-ts", "warehouse-code"),
        replay_window=(
            "replay the previous successful warehouse cursor window plus the current "
            "cursor range"
        ),
        late_arriving_correction=(
            "replay by warehouse code and keep inventory-derived batches shadow-only "
            "until downstream inventory checks pass"
        ),
        promotion_boundary=(
            "candidate stays shadow-only until the shared promotion policy evaluates "
            "the combined lane summary"
        ),
        parent_child_batch_rule="single-table",
    ),
    IncrementalDomainContract(
        name="inventory",
        source_tables=("tbsstkhouse", "tbsstock"),
        watermark_source=(
            "source-change-ts|warehouse-code|product-code from the reviewed incremental "
            "source adapter projection for warehouse inventory snapshots"
        ),
        cursor_components=("source-change-ts", "warehouse-code", "product-code"),
        replay_window=(
            "replay the previous successful inventory cursor window and include any "
            "warehouse-product pair whose parent product row reappears"
        ),
        late_arriving_correction=(
            "late-arriving stock corrections replay the full warehouse-product tuple "
            "and never bypass nightly rebaseline verification"
        ),
        promotion_boundary=(
            "candidate stays shadow-only until the shared promotion policy evaluates "
            "the combined lane summary"
        ),
        parent_child_batch_rule="warehouse-product-pair",
    ),
    IncrementalDomainContract(
        name="sales",
        source_tables=("tbsslipx", "tbsslipdtx"),
        watermark_source=(
            "document-date|document-number|line-number cursor from the reviewed "
            "incremental source adapter for tbsslipx/tbsslipdtx"
        ),
        cursor_components=("document-date", "document-number", "line-number"),
        replay_window=(
            "replay the previous successful sales document window and include the full "
            "header+line family whenever any sales row reappears"
        ),
        late_arriving_correction=(
            "late-arriving sales corrections replay the whole sales document family and "
            "reuse the reviewed reconciliation and stock backfill surfaces"
        ),
        promotion_boundary=(
            "candidate stays shadow-only until the shared promotion policy evaluates "
            "the combined lane summary"
        ),
        parent_child_batch_rule="header-and-line-pair",
    ),
    IncrementalDomainContract(
        name="purchase-invoices",
        source_tables=("tbsslipj", "tbsslipdtj"),
        watermark_source=(
            "document-date|document-number|line-number cursor from the reviewed "
            "incremental source adapter for tbsslipj/tbsslipdtj"
        ),
        cursor_components=("document-date", "document-number", "line-number"),
        replay_window=(
            "replay the previous successful purchase document window and include the "
            "full header+line family whenever any purchase row reappears"
        ),
        late_arriving_correction=(
            "late-arriving purchase corrections replay the whole receipt family and keep "
            "the lane shadow-only until shared validation stays clean"
        ),
        promotion_boundary=(
            "candidate stays shadow-only until the shared promotion policy evaluates "
            "the combined lane summary"
        ),
        parent_child_batch_rule="header-and-line-pair",
    ),
)

_COMMON_BATCH_METADATA_FIELDS = (
    "batch_id",
    "summary_path",
    "validation_status",
    "blocking_issue_count",
    "reconciliation_gap_count",
    "reconciliation_threshold",
)
_SHADOW_CANDIDATE_METADATA_FIELDS = (
    *_COMMON_BATCH_METADATA_FIELDS,
    "completed_at",
    "final_disposition",
    "analyst_review_required",
    "promotion_readiness",
)
_PROMOTED_BATCH_METADATA_FIELDS = (
    *_COMMON_BATCH_METADATA_FIELDS,
    "promoted_at",
    "promoted_by",
    "promotion_result",
)


def supported_incremental_domain_contracts() -> tuple[IncrementalDomainContract, ...]:
    return SUPPORTED_INCREMENTAL_DOMAIN_CONTRACTS


def _mapping(value: object | None) -> dict[str, Any] | None:
    if isinstance(value, Mapping):
        return dict(value)
    return None


def _batch_metadata(
    state: Mapping[str, object] | None,
    *,
    fields: tuple[str, ...],
) -> dict[str, Any] | None:
    payload = _mapping(state)
    if payload is None:
        return None
    return {field: payload.get(field) for field in fields}


def _shadow_candidate_metadata(
    candidate_state: Mapping[str, object] | None,
) -> dict[str, Any] | None:
    candidate = _batch_metadata(
        candidate_state,
        fields=_SHADOW_CANDIDATE_METADATA_FIELDS,
    )
    if candidate is None:
        return None
    candidate["promotion_policy"] = deepcopy(
        _mapping(_mapping(candidate_state).get("promotion_policy"))
    )
    return candidate


def _promoted_batch_metadata(promoted_state: Mapping[str, object] | None) -> dict[str, Any] | None:
    return _batch_metadata(
        promoted_state,
        fields=_PROMOTED_BATCH_METADATA_FIELDS,
    )


def _rebaseline_metadata(
    latest_success_state: Mapping[str, object] | None,
    *,
    recorded_at: str,
) -> dict[str, Any] | None:
    latest_success = _shadow_candidate_metadata(latest_success_state)
    if latest_success is None:
        return None
    latest_success["recorded_at"] = recorded_at
    return latest_success


def _candidate_is_promotion_eligible(
    candidate_state: Mapping[str, object] | None,
) -> bool:
    candidate = _mapping(candidate_state)
    if candidate is None:
        return False

    promotion_policy = _mapping(candidate.get("promotion_policy"))
    return (
        promotion_policy is not None
        and promotion_policy.get("classification") == ELIGIBLE_PROMOTION_CLASSIFICATION
    )


def _bootstrap_domain_state(contract: IncrementalDomainContract) -> dict[str, Any]:
    return {
        "source_tables": list(contract.source_tables),
        "watermark_source": contract.watermark_source,
        "cursor_components": list(contract.cursor_components),
        "replay_window": contract.replay_window,
        "late_arriving_correction": contract.late_arriving_correction,
        "promotion_boundary": contract.promotion_boundary,
        "parent_child_batch_rule": contract.parent_child_batch_rule,
        "last_successful_watermark": None,
        "last_successful_batch_id": None,
        "last_successful_recorded_at": None,
        "bootstrap_required": True,
    }


def reseed_incremental_state_from_full_refresh(
    *,
    tenant_id: uuid.UUID,
    schema_name: str,
    source_schema: str,
    latest_success_state: Mapping[str, object] | None,
    latest_promoted_state: Mapping[str, object] | None,
    recorded_at: str,
) -> dict[str, Any]:
    return {
        "state_version": INCREMENTAL_STATE_VERSION,
        "contract_version": INCREMENTAL_CONTRACT_VERSION,
        "lane_key": lane_key(
            tenant_id=tenant_id,
            schema_name=schema_name,
            source_schema=source_schema,
        ),
        "tenant_id": str(tenant_id),
        "schema_name": schema_name,
        "source_schema": source_schema,
        "recorded_at": recorded_at,
        "current_shadow_candidate": _shadow_candidate_metadata(latest_success_state),
        "last_successful_shadow_candidate": _shadow_candidate_metadata(
            latest_success_state
        ),
        "latest_promoted_working_batch": _promoted_batch_metadata(latest_promoted_state),
        "last_nightly_full_rebaseline": _rebaseline_metadata(
            latest_success_state,
            recorded_at=recorded_at,
        ),
        "domains": {
            contract.name: _bootstrap_domain_state(contract)
            for contract in SUPPORTED_INCREMENTAL_DOMAIN_CONTRACTS
        },
    }


def record_incremental_candidate_result(
    *,
    state: Mapping[str, object],
    candidate_state: Mapping[str, object] | None,
    latest_promoted_state: Mapping[str, object] | None,
    committed_watermarks: Mapping[str, Mapping[str, object]] | None,
    advance_watermarks: bool,
    recorded_at: str,
) -> dict[str, Any]:
    next_state = deepcopy(state)
    domains = next_state.setdefault("domains", {})
    current_shadow_candidate = _shadow_candidate_metadata(candidate_state)
    next_state["recorded_at"] = recorded_at
    next_state["current_shadow_candidate"] = current_shadow_candidate
    next_state["latest_promoted_working_batch"] = _promoted_batch_metadata(
        latest_promoted_state
    )

    candidate_is_eligible = _candidate_is_promotion_eligible(candidate_state)
    if current_shadow_candidate is not None and candidate_is_eligible:
        next_state["last_successful_shadow_candidate"] = _shadow_candidate_metadata(
            candidate_state
        )

    if (
        not advance_watermarks
        or committed_watermarks is None
        or not candidate_is_eligible
    ):
        return next_state

    last_successful_shadow_candidate = _mapping(
        next_state.get("last_successful_shadow_candidate")
    )
    for domain_name, watermark in committed_watermarks.items():
        domain_state = domains.get(domain_name)
        if not isinstance(domain_state, dict):
            continue
        domain_state["last_successful_watermark"] = deepcopy(dict(watermark))
        domain_state["last_successful_batch_id"] = (
            last_successful_shadow_candidate or {}
        ).get("batch_id")
        domain_state["last_successful_recorded_at"] = recorded_at
        domain_state["bootstrap_required"] = False

    return next_state
