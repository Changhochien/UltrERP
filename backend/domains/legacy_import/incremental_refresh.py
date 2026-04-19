"""Reviewed planner helpers for incremental legacy refresh replay."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from domains.legacy_import.incremental_state import (
    INCREMENTAL_CONTRACT_VERSION,
    WORKING_LANE_PROTECTION,
    _mapping,
    supported_incremental_domain_contracts,
)


def build_incremental_refresh_plan(
    *,
    state: Mapping[str, object] | None,
) -> dict[str, Any]:
    state_payload = _mapping(state)
    last_nightly_full_rebaseline = _mapping(state_payload.get("last_nightly_full_rebaseline"))
    domain_state_payload = _mapping(state_payload.get("domains"))

    domains: dict[str, dict[str, Any]] = {}
    for contract in supported_incremental_domain_contracts():
        domain_state = _mapping(domain_state_payload.get(contract.name))
        last_successful_watermark = _mapping(domain_state.get("last_successful_watermark"))
        if not last_successful_watermark and not last_nightly_full_rebaseline:
            raise ValueError(
                "Incremental refresh state is missing a nightly rebaseline for "
                f"bootstrap-required domain '{contract.name}'"
            )
        resume_mode = (
            "resume-from-last-successful-watermark"
            if last_successful_watermark
            else "bootstrap-from-nightly-rebaseline"
        )
        domains[contract.name] = {
            "source_tables": list(contract.source_tables),
            "watermark_source": contract.watermark_source,
            "cursor_components": list(contract.cursor_components),
            "replay_window": contract.replay_window,
            "late_arriving_correction": contract.late_arriving_correction,
            "promotion_boundary": contract.promotion_boundary,
            "parent_child_batch_rule": contract.parent_child_batch_rule,
            "resume_mode": resume_mode,
            "resume_from_watermark": deepcopy(last_successful_watermark),
            "last_successful_batch_id": domain_state.get("last_successful_batch_id"),
            "bootstrap_required": bool(
                domain_state.get("bootstrap_required", not last_successful_watermark)
            ),
        }

    return {
        "contract_version": INCREMENTAL_CONTRACT_VERSION,
        "current_shadow_candidate": deepcopy(state_payload.get("current_shadow_candidate")),
        "last_successful_shadow_candidate": deepcopy(
            state_payload.get("last_successful_shadow_candidate")
        ),
        "latest_promoted_working_batch": deepcopy(
            state_payload.get("latest_promoted_working_batch")
        ),
        "last_nightly_full_rebaseline": deepcopy(last_nightly_full_rebaseline),
        "watermark_advancement_rule": "advance-watermarks-only-after-eligible-candidate",
        "working_lane_protection": WORKING_LANE_PROTECTION,
        "domains": domains,
    }