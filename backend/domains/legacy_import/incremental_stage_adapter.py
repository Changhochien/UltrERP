"""Incremental live-stage adapter that projects only delta-manifest scope.

Story 15.25 introduces this adapter so scoped incremental refresh runs stage
only the source rows whose entity keys appear in the delta manifest's closure
set for the requested domains. It shares row parsing, encoding, and
error-handling contracts with
:class:`domains.legacy_import.staging.LiveLegacyStageSourceAdapter` by
composing the live adapter verbatim -- there is no divergent parsing path.

The adapter:

* Narrows the discovered-table set to only the source tables referenced by the
  selected domains' :class:`IncrementalDomainContract.source_tables`.
* Wraps each discovered ``LiveDiscoveredLegacyTable`` with a positional
  row filter derived from the manifest's ``closure_keys`` so rows outside the
  scoped entity set are excluded during staging.
* Fails loudly when ``selected_domains`` is empty or any requested domain has
  no closure keys -- the caller must skip staging entirely in that case. This
  prevents the adapter from silently falling back to a full-schema projection.

Supported closure-key column mapping (positional index into the serialized
source row, zero-based) mirrors the ``col_N`` numbering already used by
``run_normalization``. Keeping the mapping centralized here means the source
column numbering contract is documented in one place.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Mapping, Sequence
from typing import Any

from domains.legacy_import.incremental_state import (
    IncrementalDomainContract,
    supported_incremental_domain_contracts,
)
from domains.legacy_import.staging import (
    LegacySourceConnectionSettings,
    LegacyStageSourceAdapter,
    LiveDiscoveredLegacyTable,
    LiveLegacyStageSourceAdapter,
    StageSourceDescriptor,
    StageSourceTable,
    build_legacy_source_text_query,
)

#: Maps (domain_name, source_table) to the list of
#: (positional_index, closure_key_field) pairs used to match each closure-key
#: entry against a staged source row. ``positional_index`` is zero-based and
#: indexes into the serialized live-source row (equivalent to ``col_{N+1}`` in
#: the staged schema). ``closure_key_field`` is the key name that appears in
#: the manifest's ``closure_keys`` entries.
#:
#: The mapping mirrors the column numbering already used by
#: :func:`domains.legacy_import.normalization.run_normalization` so scoped
#: staging and scoped normalization agree on which positional column holds each
#: entity key.
_INCREMENTAL_TABLE_KEY_COLUMNS: dict[tuple[str, str], tuple[tuple[int, str], ...]] = {
    ("parties", "tbscust"): ((0, "party-code"),),
    ("products", "tbsstock"): ((0, "product-code"),),
    ("warehouses", "tbsstkhouse"): ((1, "warehouse-code"),),
    ("inventory", "tbsstkhouse"): ((0, "product_code"), (1, "warehouse_code")),
    # Inventory closure also references the product master row so the product
    # supplier / metadata stays available during downstream normalization.
    ("inventory", "tbsstock"): ((0, "product_code"),),
    ("sales", "tbsslipx"): ((1, "document_number"),),
    ("sales", "tbsslipdtx"): ((1, "document_number"),),
    ("purchase-invoices", "tbsslipj"): ((1, "document_number"),),
    ("purchase-invoices", "tbsslipdtj"): ((1, "document_number"),),
}

_MAX_PUSHDOWN_PARAMETER_VALUES = 5_000


class IncrementalScopeError(ValueError):
    """Raised when the incremental scope is missing or malformed.

    The caller (``run_incremental_legacy_refresh``) must skip staging entirely
    rather than recover from this exception; a silent fallback to full-schema
    staging would violate the Story 15.25 scope contract.
    """


class _FilteredLiveDiscoveredLegacyTable:
    """Wraps a :class:`LiveDiscoveredLegacyTable` with a positional row filter.

    The inner table's parsing, encoding, and transaction handling are reused
    verbatim; only the emitted rows are narrowed. Row numbers are re-sequenced
    so downstream staging records see a contiguous ``source_row_number``.
    """

    __slots__ = ("_accepted_patterns", "_inner")

    def __init__(
        self,
        inner: LiveDiscoveredLegacyTable,
        accepted_values: frozenset[tuple[tuple[int, str], ...]],
    ) -> None:
        self._inner = inner
        # ``accepted_values`` is a set of ordered
        # ``((index, value), (index, value), ...)`` tuples. Compile that into
        # per-index-pattern membership sets so each row does O(pattern_count)
        # lookups rather than scanning every accepted tuple.
        accepted_patterns: dict[tuple[int, ...], set[tuple[str, ...]]] = {}
        for accepted in accepted_values:
            indexes = tuple(index for index, _ in accepted)
            values = tuple(value for _, value in accepted)
            accepted_patterns.setdefault(indexes, set()).add(values)
        self._accepted_patterns = tuple(
            (indexes, frozenset(values))
            for indexes, values in accepted_patterns.items()
        )

    @property
    def table_name(self) -> str:
        return self._inner.table_name

    @property
    def expected_row_count(self) -> int | None:
        # Row count cannot be determined up-front without executing the
        # filter; leave unset so staging does not attempt a row-count
        # reconciliation against the (unfiltered) source manifest.
        return None

    @property
    def source_name(self) -> str:
        return self._inner.source_name

    @property
    def copy_batch_size(self) -> int | None:
        return self._inner.copy_batch_size

    async def get_column_count(self) -> int:
        return await self._inner.get_column_count()

    async def iter_rows(self) -> AsyncIterator[tuple[int, list[str]]]:
        emitted = 0
        async for _row_number, row in self._inner.iter_rows():
            if self._row_matches(row):
                emitted += 1
                yield emitted, row

    def _row_matches(self, row: list[str]) -> bool:
        for indexes, accepted_values in self._accepted_patterns:
            if any(index >= len(row) for index in indexes):
                continue
            if tuple(row[index] for index in indexes) in accepted_values:
                return True
        return False


def _resolve_source_tables(
    selected_domains: Sequence[str],
    contracts: Mapping[str, IncrementalDomainContract],
) -> tuple[tuple[str, ...], dict[str, tuple[str, ...]]]:
    unknown = [name for name in selected_domains if name not in contracts]
    if unknown:
        raise IncrementalScopeError(
            "Unknown incremental domains for scoped staging: " + ", ".join(unknown)
        )

    per_domain_tables: dict[str, tuple[str, ...]] = {
        name: contracts[name].source_tables for name in selected_domains
    }
    union: list[str] = []
    seen: set[str] = set()
    for tables in per_domain_tables.values():
        for table in tables:
            if table not in seen:
                seen.add(table)
                union.append(table)
    return tuple(union), per_domain_tables


def _build_table_accept_sets(
    *,
    selected_domains: Sequence[str],
    per_domain_tables: Mapping[str, Sequence[str]],
    entity_scope: Mapping[str, Mapping[str, Any]],
) -> dict[str, frozenset[tuple[tuple[int, str], ...]]]:
    """Build per-table positional-value accept sets from the manifest scope.

    ``entity_scope`` maps each domain name to the manifest's domain entry,
    which must carry a ``closure_keys`` list (e.g. the output of
    :func:`delta_discovery.build_delta_manifest`). Each closure entry yields
    one accepted positional tuple per ``(domain, table)`` mapping registered
    in ``_INCREMENTAL_TABLE_KEY_COLUMNS``.
    """

    per_table: dict[str, set[tuple[tuple[int, str], ...]]] = {}
    for domain in selected_domains:
        domain_scope = entity_scope.get(domain)
        if not isinstance(domain_scope, Mapping):
            raise IncrementalScopeError(
                f"entity_scope is missing a scope entry for domain '{domain}'"
            )
        closure_keys = domain_scope.get("closure_keys")
        if not isinstance(closure_keys, Sequence) or not closure_keys:
            raise IncrementalScopeError(
                f"Domain '{domain}' has no closure_keys; the caller must skip "
                "scoped staging entirely for this domain rather than invoke "
                "the adapter with an empty scope."
            )

        for table in per_domain_tables[domain]:
            column_mapping = _INCREMENTAL_TABLE_KEY_COLUMNS.get((domain, table))
            if column_mapping is None:
                raise IncrementalScopeError(
                    f"No positional column mapping registered for "
                    f"({domain}, {table}); update "
                    "_INCREMENTAL_TABLE_KEY_COLUMNS before enabling this scope."
                )

            accept_set = per_table.setdefault(table, set())
            for key_entry in closure_keys:
                if not isinstance(key_entry, Mapping):
                    raise IncrementalScopeError(
                        f"Closure key for domain '{domain}' must be a mapping; "
                        f"got {type(key_entry).__name__}"
                    )
                try:
                    accepted = tuple(
                        (index, str(key_entry[field]))
                        for index, field in column_mapping
                    )
                except KeyError as exc:
                    missing = exc.args[0] if exc.args else ""
                    raise IncrementalScopeError(
                        f"Closure key for domain '{domain}' is missing "
                        f"required field '{missing}' for table '{table}'"
                    ) from exc
                accept_set.add(accepted)

    return {table: frozenset(entries) for table, entries in per_table.items()}


def _maybe_push_down_live_scope(
    table: LiveDiscoveredLegacyTable,
    accepted_values: frozenset[tuple[tuple[int, str], ...]],
) -> LiveDiscoveredLegacyTable:
    single_column_entries: list[tuple[int, str]] = []
    for accepted in accepted_values:
        if len(accepted) != 1:
            return table
        single_column_entries.append(accepted[0])

    if not single_column_entries:
        return table

    column_indexes = {index for index, _ in single_column_entries}
    if len(column_indexes) != 1:
        return table

    column_index = next(iter(column_indexes))
    if column_index < 0 or column_index >= len(table.columns):
        raise IncrementalScopeError(
            f"Accepted scope index {column_index} is out of range for "
            f"{table.source_name}"
        )

    filter_column_name = table.columns[column_index].column_name
    filter_values = sorted({value for _, value in single_column_entries})
    if not filter_values:
        return table
    if any(not value.isascii() for value in filter_values):
        return table

    query_parameter_batches: tuple[tuple[object, ...], ...] = ()
    query_parameters: tuple[object, ...] = (filter_values,)
    if len(filter_values) > _MAX_PUSHDOWN_PARAMETER_VALUES:
        query_parameters = ()
        query_parameter_batches = tuple(
            (filter_values[start : start + _MAX_PUSHDOWN_PARAMETER_VALUES],)
            for start in range(0, len(filter_values), _MAX_PUSHDOWN_PARAMETER_VALUES)
        )

    return LiveDiscoveredLegacyTable(
        table_name=table.table_name,
        source_schema=table.source_schema,
        columns=table.columns,
        query=build_legacy_source_text_query(
            schema_name=table.source_schema,
            table_name=table.table_name,
            columns=table.columns,
            filter_column_name=filter_column_name,
        ),
        connection_settings=table.connection_settings,
        expected_row_count=table.expected_row_count,
        query_parameters=query_parameters,
        query_parameter_batches=query_parameter_batches,
        copy_batch_size=(
            _MAX_PUSHDOWN_PARAMETER_VALUES if query_parameter_batches else None
        ),
    )


class IncrementalLegacyStageSourceAdapter:
    """Live-source adapter that projects only the delta-manifest scope.

    Parameters mirror :class:`LiveLegacyStageSourceAdapter` for connection
    setup; scope is supplied via ``selected_domains`` and ``entity_scope``.
    """

    def __init__(
        self,
        *,
        selected_domains: Sequence[str],
        entity_scope: Mapping[str, Mapping[str, Any]],
        source_schema: str = "public",
        connection_settings: LegacySourceConnectionSettings | None = None,
    ) -> None:
        selected = tuple(dict.fromkeys(selected_domains))
        if not selected:
            raise IncrementalScopeError(
                "IncrementalLegacyStageSourceAdapter requires a non-empty "
                "selected_domains list; the caller must skip scoped staging "
                "entirely when no domain is active."
            )

        contracts = {
            contract.name: contract
            for contract in supported_incremental_domain_contracts()
        }
        source_tables, per_domain_tables = _resolve_source_tables(selected, contracts)
        accept_sets = _build_table_accept_sets(
            selected_domains=selected,
            per_domain_tables=per_domain_tables,
            entity_scope=entity_scope,
        )

        self._selected_domains = selected
        self._source_tables = source_tables
        self._accept_sets = accept_sets
        self._inner = LiveLegacyStageSourceAdapter(
            source_schema=source_schema,
            connection_settings=connection_settings,
        )
        self.source_descriptor: StageSourceDescriptor = self._inner.source_descriptor

    @property
    def selected_domains(self) -> tuple[str, ...]:
        return self._selected_domains

    @property
    def scoped_source_tables(self) -> tuple[str, ...]:
        return self._source_tables

    async def discover_tables(
        self,
        *,
        required_tables: Sequence[str],
        selected_tables: Sequence[str] | None = None,
    ) -> list[StageSourceTable]:
        # ``selected_tables`` from the caller is intersected with the scoped
        # source tables; callers typically pass ``()`` (auto-detect) so the
        # adapter expresses the full scoped set.
        caller_selection = tuple(selected_tables or ())
        if caller_selection:
            intersection = tuple(
                table for table in self._source_tables if table in caller_selection
            )
            if not intersection:
                raise IncrementalScopeError(
                    "No scoped source tables match the caller's selected_tables; "
                    f"scope={self._source_tables}, caller={caller_selection}"
                )
            scoped = intersection
        else:
            scoped = self._source_tables

        discovered = await self._inner.discover_tables(
            required_tables=required_tables,
            selected_tables=scoped,
        )

        filtered: list[StageSourceTable] = []
        for table in discovered:
            accept = self._accept_sets.get(table.table_name)
            if not accept:
                # Defensive: should never happen because scoped == keys of
                # _accept_sets by construction, but keep the failure explicit.
                raise IncrementalScopeError(
                    f"Discovered table '{table.table_name}' has no accept "
                    "set; scope/manifest mismatch"
                )
            if not isinstance(table, LiveDiscoveredLegacyTable):
                raise IncrementalScopeError(
                    "IncrementalLegacyStageSourceAdapter expects the inner "
                    "adapter to yield LiveDiscoveredLegacyTable instances; "
                    f"got {type(table).__name__}"
                )
            filtered.append(
                _FilteredLiveDiscoveredLegacyTable(
                    _maybe_push_down_live_scope(table, accept),
                    accept,
                )
            )
        return filtered

    async def close(self) -> None:
        await self._inner.close()


# Typing aid: the incremental adapter satisfies the staging protocol.
_: type[LegacyStageSourceAdapter] = IncrementalLegacyStageSourceAdapter  # type: ignore[assignment,misc]
