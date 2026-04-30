"""Run a reviewed incremental legacy refresh batch.

Story 15.23 introduces this entry point to split the legacy-refresh command surface
into a full-rebaseline surface (``run_scheduled_legacy_shadow_refresh`` /
``run_legacy_refresh``) and a scoped incremental surface.

Scope of Story 15.23 is intentionally minimal:
- Load the incremental lane state written by the reviewed scheduler.
- Build the incremental refresh plan using the existing
  ``domains.legacy_import.incremental_refresh.build_incremental_refresh_plan``
  helper; this asserts the nightly rebaseline / last-successful watermark contract
  from Story 15.19.
- Delegate execution to ``run_legacy_refresh`` with ``batch_mode="incremental"``
  and ``affected_domains`` taken from the plan so summary and lane-state artifacts
  are tagged consistently. Execution semantics are unchanged; scoped staging /
  normalize / canonical writes land in Stories 15.25 / 15.26.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from collections.abc import Mapping, Sequence
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from domains.legacy_import.delta_discovery import (
    DeltaDiscoveryResult,
    SourceProjection,
    build_delta_manifest,
    discover_delta,
)
from domains.legacy_import.incremental_refresh import build_incremental_refresh_plan
from domains.legacy_import.incremental_state import (
    record_incremental_candidate_result,
)
from domains.legacy_import.live_delta_projection import build_live_source_projection
from domains.legacy_import.shared import (
    DOMAIN_INVENTORY,
    DOMAIN_PARTIES,
    DOMAIN_PRODUCTS,
    DOMAIN_PURCHASE_INVOICES,
    DOMAIN_SALES,
    DOMAIN_WAREHOUSES,
)
from domains.legacy_import.staging import LegacySourceConnectionSettings
from scripts.legacy_refresh_common import (
    RefreshBatchMode,
    RefreshDisposition,
    build_timestamped_batch_id,
    parse_batch_prefix,
    parse_non_negative_int,
    parse_tenant_uuid,
)
from scripts.legacy_refresh_state import (
    build_lane_state_paths,
    lane_key,
    read_json_file,
    write_json_atomically,
)
from scripts.legacy_runtime_schema import ensure_legacy_refresh_schema_current
from scripts.run_legacy_refresh import (
    DEFAULT_SUMMARY_ROOT,
    LegacyRefreshExecution,
    run_legacy_refresh,
)

DEFAULT_INCREMENTAL_LOOKBACK_DAYS = 0
DEFAULT_BATCH_PREFIX = "legacy-incremental"
_INCREMENTAL_SUCCESS_DISPOSITIONS = frozenset(
    {
        RefreshDisposition.COMPLETED.value,
        RefreshDisposition.COMPLETED_REVIEW_REQUIRED.value,
        RefreshDisposition.COMPLETED_NO_OP.value,
    }
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)

_INCREMENTAL_MASTER_DOMAIN_DEPENDENCIES: dict[str, tuple[str, ...]] = {
    DOMAIN_SALES: (DOMAIN_PARTIES, DOMAIN_PRODUCTS),
    DOMAIN_PURCHASE_INVOICES: (
        DOMAIN_PARTIES,
        DOMAIN_PRODUCTS,
        DOMAIN_WAREHOUSES,
    ),
    DOMAIN_INVENTORY: (DOMAIN_PRODUCTS, DOMAIN_WAREHOUSES),
}


class MissingSourceProjectionError(RuntimeError):
    """Raised when no concrete source projection is supplied.

    Story 15.25 provides the concrete incremental live-source adapter, so the
    silent ``_empty_source_projection`` stub from Story 15.24 is removed. The
    caller must now always supply a ``source_projection`` -- either the live
    adapter's projection callable or an explicit fixture for tests. This
    prevents incremental runs from silently resolving every domain to no-op
    because of a missing projection wiring.
    """


def explicit_no_delta_projection(
    contract: Any, resume_from_watermark: Mapping[str, Any] | None
) -> list[Mapping[str, Any]]:
    """Explicit "produce zero delta rows" projection.

    Story 15.24 inlined this as a silent default inside
    ``run_incremental_legacy_refresh``. Story 15.25 removes the silent
    fallback and exposes this as a *named* opt-in. Callers that genuinely
    want a no-delta run (dry-run rehearsal, the CLI bridge until Story 15.27
    wires the live delta adapter, or a focused unit test) must import and
    pass this callable explicitly. The import site is then auditable.
    """

    _ = (contract, resume_from_watermark)
    return []


def delta_manifest_path(lane_root: Path, batch_id: str) -> Path:
    return lane_root / f"delta-manifest-{batch_id}.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run-incremental-legacy-refresh",
        description=(
            "Run a scoped incremental legacy refresh using the reviewed incremental "
            "lane state. Story 15.23 introduces this entry point; scoped execution "
            "semantics land in Stories 15.25 / 15.26."
        ),
    )
    parser.add_argument(
        "--tenant-id",
        required=True,
        type=parse_tenant_uuid,
        help="Tenant UUID for the incremental refresh lane",
    )
    parser.add_argument(
        "--schema",
        required=True,
        help="Target raw schema name for the incremental lane",
    )
    parser.add_argument(
        "--source-schema",
        default="public",
        help="Legacy source schema to stage from (default: public)",
    )
    parser.add_argument(
        "--lookback-days",
        type=parse_non_negative_int,
        default=DEFAULT_INCREMENTAL_LOOKBACK_DAYS,
        help=(
            "Optional backfill replay window for incremental repair runs. Real "
            "incremental backfills use delta-scoped document numbers, so the "
            f"default is {DEFAULT_INCREMENTAL_LOOKBACK_DAYS}."
        ),
    )
    parser.add_argument(
        "--reconciliation-threshold",
        type=parse_non_negative_int,
        default=0,
        help="Allowed flagged reconciliation gaps before the run blocks (default: 0)",
    )
    parser.add_argument(
        "--batch-prefix",
        type=parse_batch_prefix,
        default=DEFAULT_BATCH_PREFIX,
        help="Prefix used for immutable incremental batch ids (default: legacy-incremental)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Emit the incremental refresh plan as JSON and exit without invoking "
            "downstream staging / normalize / canonical steps."
        ),
    )
    parser.add_argument(
        "--skip-schema-upgrade",
        action="store_true",
        help="Skip the automatic Alembic upgrade preflight before the routine starts.",
    )
    return parser


def build_incremental_batch_id(
    batch_prefix: str,
    *,
    now: datetime | None = None,
) -> str:
    current = now or utc_now()
    return build_timestamped_batch_id(batch_prefix, now=current)


def _build_incremental_state_record_from_summary(
    *,
    scheduler_run_id: str,
    batch_id: str,
    tenant_id: uuid.UUID,
    schema_name: str,
    source_schema: str,
    started_at: str,
    completed_at: str,
    reconciliation_threshold: int,
    summary_path: Path,
    summary: Mapping[str, Any],
    exit_code: int,
) -> dict[str, Any]:
    validation_gate = (
        summary.get("promotion_gate_status", {}).get("validation", {})
        if isinstance(summary.get("promotion_gate_status"), Mapping)
        else {}
    )
    validation_status = (
        validation_gate.get("status") if isinstance(validation_gate, Mapping) else None
    )
    return {
        "state_version": 1,
        "scheduler_run_id": scheduler_run_id,
        "lane_key": lane_key(
            tenant_id=tenant_id,
            schema_name=schema_name,
            source_schema=source_schema,
        ),
        "tenant_id": str(tenant_id),
        "schema_name": schema_name,
        "source_schema": source_schema,
        "batch_id": batch_id,
        "summary_path": str(summary_path),
        "started_at": started_at,
        "completed_at": completed_at,
        "final_disposition": summary.get("final_disposition", RefreshDisposition.FAILED.value),
        "exit_code": exit_code,
        "validation_status": validation_status or "not-run",
        "blocking_issue_count": validation_gate.get("blocking_issue_count")
        if isinstance(validation_gate, Mapping)
        else None,
        "reconciliation_gap_count": summary.get("reconciliation_gap_count"),
        "reconciliation_threshold": reconciliation_threshold,
        "analyst_review_required": bool(summary.get("analyst_review_required")),
        "promotion_readiness": bool(summary.get("promotion_readiness")),
        "promotion_policy": summary.get("promotion_policy"),
        "batch_mode": summary.get("batch_mode", RefreshBatchMode.INCREMENTAL.value),
        "affected_domains": list(summary.get("affected_domains") or []),
        "summary_valid": validation_status == "passed",
        "freshness_success": bool(summary.get("freshness_success")),
        "watermark_advanced": bool(summary.get("watermark_advanced")),
        "advanced_domains": list(summary.get("advanced_domains") or []),
        "root_failed_step": summary.get("root_failed_step"),
        "root_error_message": summary.get("root_error_message"),
        "requires_rebaseline": bool(summary.get("requires_rebaseline")),
        "rebaseline_reason": summary.get("rebaseline_reason"),
    }


def _extract_committed_watermarks(
    manifest: Mapping[str, Any],
    advanced_domains: Sequence[str],
) -> dict[str, Mapping[str, object]]:
    manifest_domains = manifest.get("domains")
    if not isinstance(manifest_domains, Mapping):
        return {}

    committed: dict[str, Mapping[str, object]] = {}
    for domain_name in advanced_domains:
        domain_entry = manifest_domains.get(domain_name)
        if not isinstance(domain_entry, Mapping):
            continue
        watermark = domain_entry.get("watermark_out_proposed")
        if isinstance(watermark, Mapping):
            committed[domain_name] = deepcopy(dict(watermark))
    return committed


def _publish_incremental_lane_state(
    *,
    lane_paths: Any,
    scheduler_run_id: str,
    batch_id: str,
    tenant_id: uuid.UUID,
    schema_name: str,
    source_schema: str,
    started_at: str,
    reconciliation_threshold: int,
    summary_path: Path,
    summary: Mapping[str, Any],
    exit_code: int,
    manifest: Mapping[str, Any],
) -> None:
    completed_at = utc_now().isoformat()
    state_record = _build_incremental_state_record_from_summary(
        scheduler_run_id=scheduler_run_id,
        batch_id=batch_id,
        tenant_id=tenant_id,
        schema_name=schema_name,
        source_schema=source_schema,
        started_at=started_at,
        completed_at=completed_at,
        reconciliation_threshold=reconciliation_threshold,
        summary_path=summary_path,
        summary=summary,
        exit_code=exit_code,
    )
    write_json_atomically(lane_paths.latest_run_path, state_record)

    if state_record["final_disposition"] in _INCREMENTAL_SUCCESS_DISPOSITIONS:
        write_json_atomically(lane_paths.latest_success_path, state_record)

    incremental_state = _load_incremental_state(lane_paths.incremental_state_path)
    committed_watermarks = _extract_committed_watermarks(
        manifest,
        state_record.get("advanced_domains") or [],
    )
    next_incremental_state = record_incremental_candidate_result(
        state=incremental_state,
        candidate_state=state_record,
        latest_promoted_state=read_json_file(lane_paths.latest_promoted_path),
        committed_watermarks=committed_watermarks or None,
        advance_watermarks=bool(state_record.get("watermark_advanced")),
        recorded_at=completed_at,
    )
    write_json_atomically(lane_paths.incremental_state_path, next_incremental_state)


def _load_incremental_state(incremental_state_path: Path) -> dict[str, Any]:
    state = read_json_file(incremental_state_path)
    if state is None:
        raise FileNotFoundError(
            "No incremental lane state found at "
            f"{incremental_state_path}. Run a full rebaseline via "
            "run_scheduled_legacy_shadow_refresh first so the scheduler can "
            "reseed the incremental lane state."
        )
    return state


def _load_incremental_plan(incremental_state_path: Path) -> dict[str, Any]:
    lane_state = _load_incremental_state(incremental_state_path)
    try:
        return build_incremental_refresh_plan(state=lane_state)
    except ValueError as exc:
        raise ValueError(
            "Incremental lane state is invalid and must be repaired before an "
            "incremental refresh can run. Re-run the full rebaseline via "
            "run_scheduled_legacy_shadow_refresh to reseed the lane state. "
            f"Planner error: {exc}"
        ) from exc


def build_live_source_projection_for_lane(
    *,
    tenant_id: uuid.UUID,
    schema_name: str,
    source_schema: str,
    summary_root: Path | None = None,
    state_root: Path | None = None,
    connection_settings: LegacySourceConnectionSettings | None = None,
) -> SourceProjection:
    plan = build_incremental_plan_for_dry_run(
        tenant_id=tenant_id,
        schema_name=schema_name,
        source_schema=source_schema,
        summary_root=summary_root,
        state_root=state_root,
    )
    bootstrap_rebaseline_state = plan.get("last_nightly_full_rebaseline")
    if not isinstance(bootstrap_rebaseline_state, Mapping):
        bootstrap_rebaseline_state = None
    return build_live_source_projection(
        source_schema=source_schema,
        bootstrap_rebaseline_state=bootstrap_rebaseline_state,
        connection_settings=connection_settings,
    )


def _require_source_projection(
    source_projection: SourceProjection | None,
) -> SourceProjection:
    """Enforce that a concrete ``source_projection`` is supplied (Story 15.25).

    Story 15.24 accepted ``None`` and silently substituted an empty projection.
    Story 15.25 removes that footgun: without a projection there is no safe
    default -- the incremental run would otherwise silently record every
    domain as no-op even though real deltas exist.
    """

    if source_projection is None:
        raise MissingSourceProjectionError(
            "run_incremental_legacy_refresh requires an explicit "
            "source_projection callable. Pass the live delta-discovery "
            "projection (or a fixture for tests); the silent empty "
            "fallback from Story 15.24 has been removed."
        )
    return source_projection


def _domain_entry(
    domains_mapping: Mapping[str, Any],
    domain: str,
    *,
    required: bool = False,
) -> Mapping[str, Any] | None:
    """Extract and validate a per-domain entry from a domains mapping.

    Returns the entry if it is a Mapping, or None if it is absent and
    ``required=False``. Raises ValueError if the entry is present but not
    a Mapping and ``required=True``.
    """
    entry = domains_mapping.get(domain)
    if entry is None:
        return None
    if not isinstance(entry, Mapping):
        if required:
            raise ValueError(
                f"Domain '{domain}' exists in manifest but is not a Mapping; "
                "cannot propagate scope downstream."
            )
        return None
    return entry


def _build_entity_scope(
    manifest: Mapping[str, Any],
    affected_domains: Sequence[str],
) -> dict[str, Mapping[str, Any]]:
    """Extract per-domain closure-key entries from the manifest.

    The returned mapping is the exact shape consumed by the scoped staging
    adapter and scoped normalizer: each key is a domain name and each value
    is a mapping containing at least ``closure_keys``.
    """

    manifest_domains = manifest.get("domains")
    if not isinstance(manifest_domains, Mapping):
        raise ValueError(
            "Delta manifest is missing its 'domains' mapping; cannot build "
            "entity scope for the incremental refresh."
        )

    scope: dict[str, Mapping[str, Any]] = {}
    for domain in affected_domains:
        entry = _domain_entry(manifest_domains, domain, required=True)
        if entry is None:
            raise ValueError(
                f"Delta manifest is missing required domain '{domain}'; cannot "
                "build entity scope for the incremental refresh."
            )
        scope[domain] = entry
    return scope


def _build_last_successful_batch_ids(
    plan: Mapping[str, Any],
    affected_domains: Sequence[str],
) -> dict[str, str]:
    """Extract per-domain ``last_successful_batch_id`` from the plan.

    Active document and inventory domains also need the prior normalized
    master snapshots they depend on. Missing values (e.g. first-ever incremental run
    post-bootstrap) are omitted rather than recorded as empty strings so the
    normalization carryforward step can detect "no prior batch" cleanly.
    """

    plan_domains = plan.get("domains")
    if not isinstance(plan_domains, Mapping):
        return {}
    scoped_domains: list[str] = []
    seen_domains: set[str] = set()
    for domain in affected_domains:
        if domain not in seen_domains:
            seen_domains.add(domain)
            scoped_domains.append(domain)
        for dependency in _INCREMENTAL_MASTER_DOMAIN_DEPENDENCIES.get(domain, ()):
            if dependency in seen_domains:
                continue
            seen_domains.add(dependency)
            scoped_domains.append(dependency)

    result: dict[str, str] = {}
    for domain in scoped_domains:
        entry = _domain_entry(plan_domains, domain, required=False)
        if entry is None:
            continue
        prior = entry.get("last_successful_batch_id")
        if prior:
            result[domain] = str(prior)
    return result


async def run_incremental_legacy_refresh(
    *,
    tenant_id: uuid.UUID,
    schema_name: str,
    source_schema: str,
    lookback_days: int,
    reconciliation_threshold: int,
    batch_prefix: str = DEFAULT_BATCH_PREFIX,
    summary_root: Path | None = None,
    state_root: Path | None = None,
    source_projection: SourceProjection | None = None,
    batch_id: str | None = None,
    scheduler_run_id: str | None = None,
    started_at: str | None = None,
    connection_settings: LegacySourceConnectionSettings | None = None,
) -> LegacyRefreshExecution:
    resolved_summary_root = summary_root or DEFAULT_SUMMARY_ROOT
    resolved_scheduler_run_id = scheduler_run_id or str(uuid.uuid4())
    resolved_started_at = started_at or utc_now().isoformat()
    lane_paths = build_lane_state_paths(
        tenant_id=tenant_id,
        schema_name=schema_name,
        source_schema=source_schema,
        summary_root=resolved_summary_root,
        state_root=state_root,
    )

    source_projection_fn = _require_source_projection(source_projection)
    plan = _load_incremental_plan(lane_paths.incremental_state_path)
    discovery = await asyncio.to_thread(
        discover_delta,
        plan=plan,
        source_projection=source_projection_fn,
    )
    # Story 15.24: ``affected_domains`` is strictly the active-domain set
    # returned by delta discovery. ``no-op`` domains are excluded from the
    # downstream scope so unrelated watermarks do not advance.
    affected_domains: tuple[str, ...] = discovery.active_domains

    batch_id = batch_id or build_incremental_batch_id(batch_prefix)

    manifest = build_delta_manifest(
        run_id=str(uuid.uuid4()),
        batch_id=batch_id,
        tenant_id=tenant_id,
        schema_name=schema_name,
        source_schema=source_schema,
        recorded_at=utc_now().isoformat(),
        plan=plan,
        discovery=discovery,
    )
    write_json_atomically(
        delta_manifest_path(lane_paths.lane_root, batch_id),
        manifest,
    )

    if not affected_domains:
        # Every planned domain is no-op — skip downstream execution entirely
        # and write a no-op summary so operator tooling sees a first-class
        # completed run. Watermarks are held in place (manifest records
        # ``watermark_out_proposed == watermark_in`` for no-op domains).
        summary_path = resolved_summary_root / f"{batch_id}-summary.json"
        summary = {
            "batch_id": batch_id,
            "batch_mode": RefreshBatchMode.INCREMENTAL.value,
            "affected_domains": [],
            "planned_domains": list(discovery.planned_domains),
            "no_op_domains": list(discovery.no_op_domains),
            "final_disposition": RefreshDisposition.COMPLETED_NO_OP.value,
            "delta_manifest_path": str(
                delta_manifest_path(lane_paths.lane_root, batch_id)
            ),
        }
        write_json_atomically(summary_path, summary)
        _publish_incremental_lane_state(
            lane_paths=lane_paths,
            scheduler_run_id=resolved_scheduler_run_id,
            batch_id=batch_id,
            tenant_id=tenant_id,
            schema_name=schema_name,
            source_schema=source_schema,
            started_at=resolved_started_at,
            reconciliation_threshold=reconciliation_threshold,
            summary_path=summary_path,
            summary=summary,
            exit_code=0,
            manifest=manifest,
        )
        return LegacyRefreshExecution(
            exit_code=0,
            summary_path=summary_path,
            summary=summary,
        )

    refresh_kwargs = {
        "batch_id": batch_id,
        "tenant_id": tenant_id,
        "schema_name": schema_name,
        "source_schema": source_schema,
        "lookback_days": lookback_days,
        "reconciliation_threshold": reconciliation_threshold,
        "summary_root": resolved_summary_root,
        "batch_mode": RefreshBatchMode.INCREMENTAL,
        "affected_domains": affected_domains,
        "entity_scope": _build_entity_scope(manifest, affected_domains),
        "last_successful_batch_ids": _build_last_successful_batch_ids(plan, affected_domains),
    }
    if connection_settings is not None:
        refresh_kwargs["connection_settings"] = connection_settings
    result = await run_legacy_refresh(**refresh_kwargs)
    _publish_incremental_lane_state(
        lane_paths=lane_paths,
        scheduler_run_id=resolved_scheduler_run_id,
        batch_id=batch_id,
        tenant_id=tenant_id,
        schema_name=schema_name,
        source_schema=source_schema,
        started_at=resolved_started_at,
        reconciliation_threshold=reconciliation_threshold,
        summary_path=result.summary_path,
        summary=result.summary,
        exit_code=result.exit_code,
        manifest=manifest,
    )
    return result


def build_incremental_discovery_for_dry_run(
    *,
    tenant_id: uuid.UUID,
    schema_name: str,
    source_schema: str,
    summary_root: Path | None = None,
    state_root: Path | None = None,
    source_projection: SourceProjection | None = None,
) -> tuple[dict[str, Any], DeltaDiscoveryResult]:
    resolved_summary_root = summary_root or DEFAULT_SUMMARY_ROOT
    lane_paths = build_lane_state_paths(
        tenant_id=tenant_id,
        schema_name=schema_name,
        source_schema=source_schema,
        summary_root=resolved_summary_root,
        state_root=state_root,
    )
    source_projection_fn = _require_source_projection(source_projection)
    plan = _load_incremental_plan(lane_paths.incremental_state_path)
    discovery = discover_delta(
        plan=plan,
        source_projection=source_projection_fn,
    )
    return plan, discovery


def build_incremental_plan_for_dry_run(
    *,
    tenant_id: uuid.UUID,
    schema_name: str,
    source_schema: str,
    summary_root: Path | None = None,
    state_root: Path | None = None,
) -> dict[str, Any]:
    resolved_summary_root = summary_root or DEFAULT_SUMMARY_ROOT
    lane_paths = build_lane_state_paths(
        tenant_id=tenant_id,
        schema_name=schema_name,
        source_schema=source_schema,
        summary_root=resolved_summary_root,
        state_root=state_root,
    )
    return _load_incremental_plan(lane_paths.incremental_state_path)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    cli_source_projection = build_live_source_projection_for_lane(
        tenant_id=args.tenant_id,
        schema_name=args.schema,
        source_schema=args.source_schema,
    )
    if args.dry_run:
        plan, discovery = build_incremental_discovery_for_dry_run(
            tenant_id=args.tenant_id,
            schema_name=args.schema,
            source_schema=args.source_schema,
            source_projection=cli_source_projection,
        )
        manifest_preview = build_delta_manifest(
            run_id="dry-run",
            batch_id="dry-run",
            tenant_id=args.tenant_id,
            schema_name=args.schema,
            source_schema=args.source_schema,
            recorded_at=utc_now().isoformat(),
            plan=plan,
            discovery=discovery,
        )
        json.dump(
            {"plan": plan, "manifest_preview": manifest_preview},
            sys.stdout,
            indent=2,
            sort_keys=True,
            default=str,
        )
        sys.stdout.write("\n")
        return 0
    if not args.skip_schema_upgrade:
        ensure_legacy_refresh_schema_current()
    result = asyncio.run(
        run_incremental_legacy_refresh(
            tenant_id=args.tenant_id,
            schema_name=args.schema,
            source_schema=args.source_schema,
            lookback_days=args.lookback_days,
            reconciliation_threshold=args.reconciliation_threshold,
            batch_prefix=args.batch_prefix,
            source_projection=cli_source_projection,
        )
    )
    print(f"Incremental legacy refresh summary: {result.summary_path}")
    print(
        f"Disposition: {result.summary['final_disposition']} "
        f"(exit={result.exit_code})"
    )
    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
