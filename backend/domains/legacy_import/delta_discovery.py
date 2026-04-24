"""Reviewed delta discovery and delta-manifest helpers for incremental refresh.

Story 15.24 introduces the source-side discovery layer consumed by
``scripts.run_incremental_legacy_refresh``. The discovery layer:

- projects, per domain, only rows whose cursor exceeds the last successful
  watermark (using a caller-supplied ``source_projection`` callable so this
  module stays pure and unit-testable);
- applies the reviewed replay window and late-arriving correction rules from
  ``IncrementalDomainContract``;
- expands the discovered keys via the reviewed parent/child batch rule
  (``warehouse-product-pair`` → distinct ``(warehouse_code, product_code)``
  tuples; ``header-and-line-pair`` → full document family keyed by
  ``document_number``; ``single-table`` → no expansion);
- marks domains with zero changed keys after replay expansion as ``no-op`` so
  downstream scoped execution may skip them without advancing unrelated
  watermarks.

The delta manifest is the source of truth for later staging, normalization,
canonical import, validation, and backfill scope. Downstream stories
(15.25 / 15.26 / 15.27) must consume the manifest rather than re-discover from
raw source.

Discovery queries are read-only: they never advance any watermark. Watermark
advancement happens only after downstream steps confirm durable processing.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Literal
from uuid import UUID as UUIDType

from domains.legacy_import.incremental_state import (
    INCREMENTAL_CONTRACT_VERSION,
    IncrementalDomainContract,
    supported_incremental_domain_contracts,
)

DELTA_MANIFEST_VERSION = 1

#: Cached lookup of supported incremental domain contracts by name.
_SUPPORTED_CONTRACTS_BY_NAME: dict[str, IncrementalDomainContract] = {
    c.name: c for c in supported_incremental_domain_contracts()
}

#: A callable invoked per-domain to project changed source rows.
#:
#: Arguments:
#:   contract: the reviewed :class:`IncrementalDomainContract`
#:   resume_from_watermark: the last successful watermark payload, or ``None``
#:       when the domain is bootstrapping from the nightly rebaseline.
#:
#: Returns an iterable of source-row mappings. Each mapping must contain at
#: least the cursor components named by ``contract.cursor_components`` plus any
#: extra keys required by the domain's ``parent_child_batch_rule`` (for example
#: ``warehouse_code`` / ``product_code`` for inventory, ``document_number`` for
#: sales and purchase-invoices).
SourceProjection = Callable[
    [IncrementalDomainContract, Mapping[str, Any] | None], Iterable[Mapping[str, Any]]
]


@dataclass(slots=True, frozen=True)
class DomainDelta:
    name: str
    status: Literal["active", "no-op", "bootstrap"]
    resume_mode: str
    changed_keys: tuple[dict[str, Any], ...]
    closure_keys: tuple[dict[str, Any], ...]
    closure_count: int
    parent_child_batch_rule: str
    replay_window: str
    watermark_in: Mapping[str, Any] | None
    watermark_out_proposed: Mapping[str, Any] | None


@dataclass(slots=True, frozen=True)
class DeltaDiscoveryResult:
    batch_mode: Literal["incremental"]
    planned_domains: tuple[str, ...]
    domains: tuple[DomainDelta, ...]
    active_domains: tuple[str, ...] = field(default=())
    no_op_domains: tuple[str, ...] = field(default=())


def _cursor_key(
    contract: IncrementalDomainContract,
    row: Mapping[str, Any],
) -> dict[str, Any]:
    """Extract cursor component values for auditing purposes."""

    return {component: row.get(component) for component in contract.cursor_components}


def discover_delta(
    *,
    plan: Mapping[str, Any],
    source_projection: SourceProjection,
) -> DeltaDiscoveryResult:
    """Run the reviewed per-domain delta discovery against a plan.

    This is pure: ``source_projection`` is the only boundary to the legacy
    source. It receives the reviewed contract and the ``resume_from_watermark``
    taken from the plan, and must return rows whose cursor components strictly
    exceed that watermark within the reviewed replay window. The reviewed
    replay window / late-arriving correction rules live inside the projection
    callable (which is where source queries can express them declaratively)
    but are echoed on the manifest via the contract metadata.
    """

    planned_domains = tuple(plan["domains"].keys())
    domain_deltas: list[DomainDelta] = []
    active: list[str] = []
    no_op: list[str] = []

    for domain_name in planned_domains:
        contract = _SUPPORTED_CONTRACTS_BY_NAME.get(domain_name)
        if contract is None:
            raise ValueError(
                f"Plan references unknown incremental domain '{domain_name}'"
            )
        domain_plan = plan["domains"][domain_name]
        resume_mode_val = domain_plan.get("resume_mode", "unknown")
        resume_from = domain_plan.get("resume_from_watermark")
        rows = list(source_projection(contract, resume_from))

        # Single-pass: collect changed_keys, max cursor, and closure keys together.
        changed_keys_list: list[dict[str, Any]] = []
        best_cursor: tuple[Any, ...] | None = None
        best_row: Mapping[str, Any] | None = None
        closure_list: list[dict[str, Any]] = []

        rule = contract.parent_child_batch_rule
        seen: set[Any] = set()

        for row in rows:
            changed_keys_list.append(_cursor_key(contract, row))
            if contract.cursor_components:
                candidate = tuple(row.get(c) for c in contract.cursor_components)
                if not any(v is None for v in candidate) and (
                    best_cursor is None or candidate > best_cursor
                ):
                    best_cursor = candidate
                    best_row = row

            # Track unique closure keys based on batch rule
            if rule == "single-table":
                entity_comp = contract.cursor_components[-1]
                entity_val = row.get(entity_comp)
                if entity_val not in seen:
                    seen.add(entity_val)
                    closure_list.append({entity_comp: entity_val})

            elif rule == "warehouse-product-pair":
                sig = (row.get("warehouse_code"), row.get("product_code"))
                if sig not in seen:
                    seen.add(sig)
                    closure_list.append({"warehouse_code": sig[0], "product_code": sig[1]})

            elif rule == "header-and-line-pair":
                doc_num = row.get("document_number")
                if doc_num not in seen:
                    seen.add(doc_num)
                    closure_list.append({"document_number": doc_num})

            else:
                raise ValueError(
                    f"Unsupported parent_child_batch_rule '{rule}' for domain '{domain_name}'"
                )

        changed_keys = tuple(changed_keys_list)
        closure_keys = tuple(closure_list)
        watermark_out = (
            _cursor_key(contract, best_row) if best_row else deepcopy(resume_from)
        )

        if not rows:
            status: Literal["active", "no-op", "bootstrap"] = "no-op"
        elif resume_mode_val == "bootstrap-from-nightly-rebaseline":
            status = "bootstrap"
        else:
            status = "active"

        if status == "no-op":
            no_op.append(domain_name)
        else:
            active.append(domain_name)

        domain_deltas.append(
            DomainDelta(
                name=domain_name,
                status=status,
                resume_mode=resume_mode_val,
                changed_keys=changed_keys,
                closure_keys=closure_keys,
                closure_count=len(closure_keys),
                parent_child_batch_rule=contract.parent_child_batch_rule,
                replay_window=contract.replay_window,
                watermark_in=deepcopy(resume_from),
                watermark_out_proposed=watermark_out,
            )
        )

    return DeltaDiscoveryResult(
        batch_mode="incremental",
        planned_domains=planned_domains,
        domains=tuple(domain_deltas),
        active_domains=tuple(active),
        no_op_domains=tuple(no_op),
    )


def build_delta_manifest(
    *,
    run_id: str,
    batch_id: str,
    tenant_id: UUIDType,
    schema_name: str,
    source_schema: str,
    recorded_at: str,
    plan: Mapping[str, Any],
    discovery: DeltaDiscoveryResult,
) -> dict[str, Any]:
    """Build the append-only delta manifest recorded before canonical writes."""

    domain_entries: dict[str, dict[str, Any]] = {}
    for delta in discovery.domains:
        domain_entries[delta.name] = {
            "status": delta.status,
            "resume_mode": delta.resume_mode,
            "parent_child_batch_rule": delta.parent_child_batch_rule,
            "replay_window": delta.replay_window,
            "changed_key_count": len(delta.changed_keys),
            "changed_keys": list(delta.changed_keys),
            "closure_count": delta.closure_count,
            "closure_keys": list(delta.closure_keys),
            "watermark_in": delta.watermark_in,
            "watermark_out_proposed": delta.watermark_out_proposed,
        }

    return {
        "manifest_version": DELTA_MANIFEST_VERSION,
        "contract_version": INCREMENTAL_CONTRACT_VERSION,
        "run_id": run_id,
        "batch_id": batch_id,
        "batch_mode": discovery.batch_mode,
        "tenant_id": str(tenant_id),
        "schema_name": schema_name,
        "source_schema": source_schema,
        "recorded_at": recorded_at,
        "planned_domains": list(discovery.planned_domains),
        "active_domains": list(discovery.active_domains),
        "no_op_domains": list(discovery.no_op_domains),
        "domains": domain_entries,
    }
