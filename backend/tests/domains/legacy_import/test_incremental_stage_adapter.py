"""Unit tests for the scoped incremental staging adapter (Story 15.25)."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest

from domains.legacy_import.incremental_stage_adapter import (
    IncrementalLegacyStageSourceAdapter,
    IncrementalScopeError,
    _MAX_PUSHDOWN_PARAMETER_VALUES,
    _build_table_accept_sets,
    _FilteredLiveDiscoveredLegacyTable,
    _resolve_source_tables,
)
from domains.legacy_import.incremental_state import (
    supported_incremental_domain_contracts,
)
from domains.legacy_import.staging import (
    LegacySourceColumnMetadata,
    LegacySourceConnectionSettings,
    LiveDiscoveredLegacyTable,
    StageSourceDescriptor,
)


def _build_column_metadata(
    table_name: str, count: int
) -> tuple[LegacySourceColumnMetadata, ...]:
    return tuple(
        LegacySourceColumnMetadata(
            table_name=table_name,
            column_name=f"col_{i + 1}",
            ordinal_position=i + 1,
            data_type="text",
            udt_name="text",
            is_nullable=True,
        )
        for i in range(count)
    )


def _fake_connection_settings() -> LegacySourceConnectionSettings:
    return LegacySourceConnectionSettings(
        host="localhost",
        port=5432,
        user="legacy",
        password="",
        database="legacy",
    )


# ---------------------------------------------------------------------------
# _resolve_source_tables


def test_resolve_source_tables_unions_domains_and_preserves_order() -> None:
    contracts = {c.name: c for c in supported_incremental_domain_contracts()}
    tables, per_domain = _resolve_source_tables(("parties", "inventory"), contracts)

    # Inventory adds tbsstkhouse and tbsstock; parties contributes tbscust first.
    assert tables == ("tbscust", "tbsstkhouse", "tbsstock")
    assert per_domain["parties"] == ("tbscust",)
    assert per_domain["inventory"] == ("tbsstkhouse", "tbsstock")


def test_resolve_source_tables_rejects_unknown_domain() -> None:
    contracts = {c.name: c for c in supported_incremental_domain_contracts()}
    with pytest.raises(IncrementalScopeError, match="Unknown incremental domains"):
        _resolve_source_tables(("parties", "nope"), contracts)


# ---------------------------------------------------------------------------
# _build_table_accept_sets


def test_build_table_accept_sets_projects_closure_keys_into_positional_tuples() -> None:
    accept = _build_table_accept_sets(
        selected_domains=("parties",),
        per_domain_tables={"parties": ("tbscust",)},
        entity_scope={
            "parties": {
                "closure_keys": [
                    {"party-code": "P-001"},
                    {"party-code": "P-002"},
                ]
            }
        },
    )

    assert accept == {
        "tbscust": frozenset(
            {
                ((0, "P-001"),),
                ((0, "P-002"),),
            }
        )
    }


def test_build_table_accept_sets_joint_key_for_inventory() -> None:
    accept = _build_table_accept_sets(
        selected_domains=("inventory",),
        per_domain_tables={"inventory": ("tbsstkhouse", "tbsstock")},
        entity_scope={
            "inventory": {
                "closure_keys": [
                    {"product_code": "P-1", "warehouse_code": "W-1"},
                    {"product_code": "P-2", "warehouse_code": "W-2"},
                ]
            }
        },
    )

    # tbsstkhouse uses the joint (product_code, warehouse_code) tuple at
    # positions (0, 1); tbsstock pulls the product_code alone at position 0
    # so reference masters are carried forward.
    assert accept["tbsstkhouse"] == frozenset(
        {
            ((0, "P-1"), (1, "W-1")),
            ((0, "P-2"), (1, "W-2")),
        }
    )
    assert accept["tbsstock"] == frozenset(
        {
            ((0, "P-1"),),
            ((0, "P-2"),),
        }
    )


def test_build_table_accept_sets_rejects_missing_closure_keys() -> None:
    with pytest.raises(IncrementalScopeError, match="no closure_keys"):
        _build_table_accept_sets(
            selected_domains=("parties",),
            per_domain_tables={"parties": ("tbscust",)},
            entity_scope={"parties": {"closure_keys": []}},
        )


def test_build_table_accept_sets_rejects_missing_scope_entry() -> None:
    with pytest.raises(IncrementalScopeError, match="missing a scope entry"):
        _build_table_accept_sets(
            selected_domains=("parties",),
            per_domain_tables={"parties": ("tbscust",)},
            entity_scope={},
        )


def test_build_table_accept_sets_rejects_closure_key_missing_field() -> None:
    with pytest.raises(IncrementalScopeError, match="missing required field"):
        _build_table_accept_sets(
            selected_domains=("inventory",),
            per_domain_tables={"inventory": ("tbsstkhouse",)},
            entity_scope={
                "inventory": {
                    "closure_keys": [
                        {"product_code": "P-1"},  # missing warehouse_code
                    ]
                }
            },
        )


# ---------------------------------------------------------------------------
# _FilteredLiveDiscoveredLegacyTable


class _FakeInnerTable:
    """Minimal stand-in for LiveDiscoveredLegacyTable."""

    def __init__(
        self,
        *,
        table_name: str,
        rows: list[list[str]],
        column_count: int,
    ) -> None:
        self.table_name = table_name
        self.source_name = f"public.{table_name}"
        self._rows = rows
        self._column_count = column_count

    async def get_column_count(self) -> int:
        return self._column_count

    async def iter_rows(self) -> AsyncIterator[tuple[int, list[str]]]:
        for row_number, row in enumerate(self._rows, start=1):
            yield row_number, row


@pytest.mark.asyncio
async def test_filtered_table_keeps_only_matching_rows_and_resequences() -> None:
    inner = _FakeInnerTable(
        table_name="tbscust",
        rows=[
            ["P-001", "Alice"],
            ["P-999", "Excluded"],
            ["P-002", "Bob"],
            ["P-003", "Also-excluded"],
        ],
        column_count=2,
    )
    accepted: frozenset[tuple[tuple[int, str], ...]] = frozenset(
        {
            ((0, "P-001"),),
            ((0, "P-002"),),
        }
    )
    filtered = _FilteredLiveDiscoveredLegacyTable(
        inner,  # type: ignore[arg-type]
        accepted,
    )

    emitted: list[tuple[int, list[str]]] = []
    async for row_number, row in filtered.iter_rows():
        emitted.append((row_number, row))

    assert emitted == [
        (1, ["P-001", "Alice"]),
        (2, ["P-002", "Bob"]),
    ]
    # Expected row count is None because it can only be known post-filter.
    assert filtered.expected_row_count is None


@pytest.mark.asyncio
async def test_filtered_table_joint_key_requires_all_positions_to_match() -> None:
    inner = _FakeInnerTable(
        table_name="tbsstkhouse",
        rows=[
            ["P-1", "W-1", "100"],
            ["P-1", "W-2", "50"],  # product matches but not the pair
            ["P-2", "W-2", "25"],
            ["P-3", "W-3", "999"],  # neither matches
        ],
        column_count=3,
    )
    accepted: frozenset[tuple[tuple[int, str], ...]] = frozenset(
        {
            ((0, "P-1"), (1, "W-1")),
            ((0, "P-2"), (1, "W-2")),
        }
    )
    filtered = _FilteredLiveDiscoveredLegacyTable(
        inner,  # type: ignore[arg-type]
        accepted,
    )

    emitted = [row async for row in filtered.iter_rows()]

    assert emitted == [
        (1, ["P-1", "W-1", "100"]),
        (2, ["P-2", "W-2", "25"]),
    ]


# ---------------------------------------------------------------------------
# IncrementalLegacyStageSourceAdapter


class _InnerAdapterStub:
    """Stands in for LiveLegacyStageSourceAdapter inside the adapter."""

    def __init__(
        self,
        tables: list[LiveDiscoveredLegacyTable],
        source_descriptor: StageSourceDescriptor,
    ) -> None:
        self._tables = tables
        self.source_descriptor = source_descriptor
        self.discover_calls: list[dict[str, object]] = []
        self.closed = False

    async def discover_tables(
        self,
        *,
        required_tables,
        selected_tables=None,
    ):
        self.discover_calls.append(
            {
                "required_tables": tuple(required_tables),
                "selected_tables": tuple(selected_tables or ()),
            }
        )
        caller = tuple(selected_tables or ())
        if caller:
            return [t for t in self._tables if t.table_name in caller]
        return list(self._tables)

    async def close(self) -> None:
        self.closed = True


def _make_live_discovered_table(
    *, table_name: str, column_count: int = 2
) -> LiveDiscoveredLegacyTable:
    # The constructor requires columns and a query; give it realistic
    # values so the adapter can satisfy its isinstance() guard.
    columns = _build_column_metadata(table_name, column_count)
    return LiveDiscoveredLegacyTable(
        table_name=table_name,
        source_schema="public",
        columns=columns,
        query=f'SELECT * FROM "public"."{table_name}"',
        connection_settings=_fake_connection_settings(),
        expected_row_count=None,
    )


def test_adapter_rejects_empty_selected_domains() -> None:
    with pytest.raises(IncrementalScopeError, match="non-empty selected_domains"):
        IncrementalLegacyStageSourceAdapter(
            selected_domains=(),
            entity_scope={},
        )


@pytest.mark.asyncio
async def test_adapter_narrows_discovered_tables_to_selected_domain_scope(
    monkeypatch,
) -> None:
    # Build the adapter with parties only; inner stub returns tbscust AND a
    # spurious table that should be filtered out by the scoped selection.
    inner_tables = [
        _make_live_discovered_table(table_name="tbscust"),
        _make_live_discovered_table(table_name="tbsstock"),
    ]
    inner = _InnerAdapterStub(
        tables=inner_tables,
        source_descriptor=StageSourceDescriptor.live(
            database="legacy", schema_name="public"
        ),
    )

    adapter = IncrementalLegacyStageSourceAdapter(
        selected_domains=("parties",),
        entity_scope={
            "parties": {"closure_keys": [{"party-code": "P-001"}]},
        },
        connection_settings=_fake_connection_settings(),
    )
    monkeypatch.setattr(adapter, "_inner", inner)
    monkeypatch.setattr(adapter, "source_descriptor", inner.source_descriptor)

    discovered = await adapter.discover_tables(required_tables=("tbscust",))

    assert adapter.scoped_source_tables == ("tbscust",)
    assert [t.table_name for t in discovered] == ["tbscust"]
    # The scoped selection was passed to the inner adapter so it never even
    # asked about out-of-scope tables.
    assert inner.discover_calls[-1]["selected_tables"] == ("tbscust",)
    assert all(
        isinstance(t, _FilteredLiveDiscoveredLegacyTable) for t in discovered
    )


@pytest.mark.asyncio
async def test_adapter_rejects_caller_selection_outside_scope(monkeypatch) -> None:
    inner = _InnerAdapterStub(
        tables=[_make_live_discovered_table(table_name="tbscust")],
        source_descriptor=StageSourceDescriptor.live(
            database="legacy", schema_name="public"
        ),
    )
    adapter = IncrementalLegacyStageSourceAdapter(
        selected_domains=("parties",),
        entity_scope={"parties": {"closure_keys": [{"party-code": "P-001"}]}},
        connection_settings=_fake_connection_settings(),
    )
    monkeypatch.setattr(adapter, "_inner", inner)

    with pytest.raises(IncrementalScopeError, match="No scoped source tables"):
        await adapter.discover_tables(
            required_tables=("tbsstock",),
            selected_tables=("tbsstock",),
        )


@pytest.mark.asyncio
async def test_adapter_pushes_down_single_column_scope_to_live_query(
    monkeypatch,
) -> None:
    inner = _InnerAdapterStub(
        tables=[_make_live_discovered_table(table_name="tbsslipx", column_count=3)],
        source_descriptor=StageSourceDescriptor.live(
            database="legacy", schema_name="public"
        ),
    )
    adapter = IncrementalLegacyStageSourceAdapter(
        selected_domains=("sales",),
        entity_scope={
            "sales": {
                "closure_keys": [
                    {"document_number": "SO-002"},
                    {"document_number": "SO-001"},
                ]
            }
        },
        connection_settings=_fake_connection_settings(),
    )
    monkeypatch.setattr(adapter, "_inner", inner)

    discovered = await adapter.discover_tables(required_tables=("tbsslipx",))

    filtered = discovered[0]
    assert isinstance(filtered, _FilteredLiveDiscoveredLegacyTable)
    pushed_down = filtered._inner
    assert isinstance(pushed_down, LiveDiscoveredLegacyTable)
    assert 'WHERE "col_2" = ANY($1::text[])' in pushed_down.query
    assert pushed_down.query_parameters == (["SO-001", "SO-002"],)


@pytest.mark.asyncio
async def test_adapter_skips_pushdown_for_non_ascii_single_column_scope(
    monkeypatch,
) -> None:
    inner = _InnerAdapterStub(
        tables=[_make_live_discovered_table(table_name="tbsstock", column_count=3)],
        source_descriptor=StageSourceDescriptor.live(
            database="legacy", schema_name="public"
        ),
    )
    adapter = IncrementalLegacyStageSourceAdapter(
        selected_domains=("products",),
        entity_scope={
            "products": {
                "closure_keys": [
                    {"product-code": "17641-00 迅光"},
                    {"product-code": "0013"},
                ]
            }
        },
        connection_settings=_fake_connection_settings(),
    )
    monkeypatch.setattr(adapter, "_inner", inner)

    discovered = await adapter.discover_tables(required_tables=("tbsstock",))

    filtered = discovered[0]
    pushed_down = filtered._inner
    assert isinstance(pushed_down, LiveDiscoveredLegacyTable)
    assert pushed_down.query == 'SELECT * FROM "public"."tbsstock"'
    assert pushed_down.query_parameters == ()


@pytest.mark.asyncio
async def test_adapter_batches_large_single_column_pushdown_scope(
    monkeypatch,
) -> None:
    inner = _InnerAdapterStub(
        tables=[_make_live_discovered_table(table_name="tbsslipx", column_count=3)],
        source_descriptor=StageSourceDescriptor.live(
            database="legacy", schema_name="public"
        ),
    )
    closure_keys = [
        {"document_number": f"SO-{index:05d}"}
        for index in range(_MAX_PUSHDOWN_PARAMETER_VALUES + 3)
    ]
    adapter = IncrementalLegacyStageSourceAdapter(
        selected_domains=("sales",),
        entity_scope={
            "sales": {
                "closure_keys": closure_keys,
            }
        },
        connection_settings=_fake_connection_settings(),
    )
    monkeypatch.setattr(adapter, "_inner", inner)

    discovered = await adapter.discover_tables(required_tables=("tbsslipx",))

    filtered = discovered[0]
    pushed_down = filtered._inner
    assert isinstance(pushed_down, LiveDiscoveredLegacyTable)
    assert pushed_down.query_parameters == ()
    assert len(pushed_down.query_parameter_batches) == 2
    assert len(pushed_down.query_parameter_batches[0][0]) == _MAX_PUSHDOWN_PARAMETER_VALUES
    assert len(pushed_down.query_parameter_batches[1][0]) == 3
    assert pushed_down.copy_batch_size == _MAX_PUSHDOWN_PARAMETER_VALUES
