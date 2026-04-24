"""Unit tests for the scoped incremental normalization branch (Story 15.25)."""

from __future__ import annotations

import uuid

import pytest

from domains.legacy_import import normalization
from domains.legacy_import.normalization import (
    _INCREMENTAL_NORMALIZED_TABLE_META,
    _MASTER_NORMALIZATION_DOMAINS,
    NormalizationBatchResult,
    _carry_forward_prior_batch,
    _clear_scoped_batch_rows,
)
from scripts.legacy_refresh_common import RefreshBatchMode
from tests.domains.legacy_import.test_normalization import (
    FakeNormalizationConnection,
)

TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000321")


# ---------------------------------------------------------------------------
# Dispatcher validation


@pytest.mark.asyncio
async def test_run_normalization_rejects_unknown_batch_mode() -> None:
    with pytest.raises(ValueError, match="unsupported batch_mode"):
        await normalization.run_normalization(
            batch_id="batch-x",
            tenant_id=TENANT_ID,
            schema_name="raw_legacy",
            batch_mode="unknown",
        )


@pytest.mark.asyncio
async def test_run_normalization_incremental_rejects_invalid_domain_names() -> None:
    with pytest.raises(ValueError, match="does not support these domain names"):
        await normalization.run_normalization(
            batch_id="batch-x",
            tenant_id=TENANT_ID,
            schema_name="raw_legacy",
            batch_mode="incremental",
            selected_domains=("invalid_xyz",),
        )


@pytest.mark.asyncio
async def test_run_normalization_incremental_requires_selected_domains() -> None:
    with pytest.raises(ValueError, match="non-empty selected_domains"):
        await normalization.run_normalization(
            batch_id="batch-x",
            tenant_id=TENANT_ID,
            schema_name="raw_legacy",
            batch_mode="incremental",
        )


@pytest.mark.asyncio
async def test_run_normalization_full_rejects_incremental_kwargs() -> None:
    with pytest.raises(ValueError, match="incremental-mode kwargs"):
        await normalization.run_normalization(
            batch_id="batch-x",
            tenant_id=TENANT_ID,
            schema_name="raw_legacy",
            batch_mode="full",
            selected_domains=("parties",),
        )


@pytest.mark.asyncio
async def test_run_normalization_full_rejects_entity_scope_without_selected_domains() -> None:
    with pytest.raises(ValueError, match="incremental-mode kwargs"):
        await normalization.run_normalization(
            batch_id="batch-x",
            tenant_id=TENANT_ID,
            schema_name="raw_legacy",
            batch_mode="full",
            entity_scope={"parties": {"closure_keys": [{"party-code": "P-001"}]}},
        )


# ---------------------------------------------------------------------------
# NormalizationBatchResult default


def test_normalization_batch_result_defaults_reused_from_batch_ids_to_empty() -> None:
    result = NormalizationBatchResult(
        batch_id="batch-x",
        schema_name="raw_legacy",
        party_count=0,
        product_count=0,
        warehouse_count=0,
        inventory_count=0,
    )
    assert result.reused_from_batch_ids == {}


# ---------------------------------------------------------------------------
# _INCREMENTAL_NORMALIZED_TABLE_META shape


def test_table_meta_covers_all_master_domains() -> None:
    assert _MASTER_NORMALIZATION_DOMAINS == frozenset(
        {"parties", "products", "warehouses", "inventory"}
    )
    for domain in _MASTER_NORMALIZATION_DOMAINS:
        table, columns, keys = _INCREMENTAL_NORMALIZED_TABLE_META[domain]
        assert table and isinstance(columns, tuple) and isinstance(keys, tuple)
        # Every key column must appear in the column tuple.
        for key in keys:
            assert key in columns
        # The core carryforward rewrite columns must exist.
        assert "batch_id" in columns
        assert "tenant_id" in columns


# ---------------------------------------------------------------------------
# _clear_scoped_batch_rows


class _RecordingConnection:
    """Minimal connection stub that records each execute() call in order."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []
        self.execute_return: str = "DELETE 0"

    async def execute(self, query: str, *args: object) -> str:
        self.calls.append((query, args))
        return self.execute_return

    @property
    def queries(self) -> list[str]:
        return [q for q, _ in self.calls]


@pytest.mark.asyncio
async def test_clear_scoped_batch_rows_only_touches_in_scope_domains() -> None:
    conn = _RecordingConnection()
    await _clear_scoped_batch_rows(
        conn,
        "raw_legacy",
        "batch-x",
        TENANT_ID,
        frozenset({"parties"}),
    )

    # Only the parties table was cleared.
    assert len(conn.calls) == 1
    assert "normalized_parties" in conn.queries[0]
    assert conn.calls[0][1] == ("batch-x", TENANT_ID)


@pytest.mark.asyncio
async def test_clear_scoped_batch_rows_honours_fk_ordering() -> None:
    conn = _RecordingConnection()
    await _clear_scoped_batch_rows(
        conn,
        "raw_legacy",
        "batch-x",
        TENANT_ID,
        frozenset({"parties", "products", "warehouses", "inventory"}),
    )

    queries = conn.queries
    # Inventory first, then review candidates (tied to products), then
    # warehouses, products, parties.
    def _position(needle: str) -> int:
        for i, q in enumerate(queries):
            if needle in q:
                return i
        raise AssertionError(f"Missing delete for {needle}: {queries}")

    assert _position("normalized_inventory_prep") < _position(
        "product_category_review_candidates"
    )
    assert _position("product_category_review_candidates") < _position(
        "normalized_warehouses"
    )
    assert _position("normalized_warehouses") < _position("normalized_products")
    assert _position("normalized_products") < _position("normalized_parties")


# ---------------------------------------------------------------------------
# _carry_forward_prior_batch


@pytest.mark.asyncio
async def test_carry_forward_prior_batch_parses_insert_rowcount() -> None:
    conn = _RecordingConnection()
    conn.execute_return = "INSERT 0 42"

    copied = await _carry_forward_prior_batch(
        conn,
        "raw_legacy",
        "parties",
        current_batch_id="batch-new",
        prior_batch_id="batch-prev",
        tenant_id=TENANT_ID,
    )

    assert copied == 42
    assert len(conn.calls) == 1
    query, args = conn.calls[0]
    # Bind order: current_batch_id=$1, tenant_id=$2, prior_batch_id=$3.
    assert args == ("batch-new", TENANT_ID, "batch-prev")
    assert "INSERT INTO" in query
    assert "normalized_parties" in query
    # Check WHERE clause uses the correct parameter positions.
    assert "prior.batch_id = $3" in query
    assert "prior.tenant_id = $2" in query
    assert "NOT EXISTS" in query
    # Parties uses (tenant_id, role, legacy_code) composite key.
    assert 'current."tenant_id" = prior."tenant_id"' in query
    assert 'current."role" = prior."role"' in query
    assert 'current."legacy_code" = prior."legacy_code"' in query


@pytest.mark.asyncio
async def test_carry_forward_prior_batch_uses_all_composite_key_columns() -> None:
    conn = _RecordingConnection()

    await _carry_forward_prior_batch(
        conn,
        "raw_legacy",
        "inventory",
        current_batch_id="batch-new",
        prior_batch_id="batch-prev",
        tenant_id=TENANT_ID,
    )

    query, _args = conn.calls[0]
    # Inventory uses (tenant_id, product_legacy_code, warehouse_code) composite key.
    assert 'current."tenant_id" = prior."tenant_id"' in query
    assert (
        'current."product_legacy_code" = prior."product_legacy_code"'
        in query
    )
    assert (
        'current."warehouse_code" = prior."warehouse_code"'
        in query
    )


@pytest.mark.asyncio
async def test_carry_forward_prior_batch_returns_zero_for_unexpected_status() -> None:
    conn = _RecordingConnection()
    conn.execute_return = "unexpected"

    copied = await _carry_forward_prior_batch(
        conn,
        "raw_legacy",
        "inventory",
        current_batch_id="batch-new",
        prior_batch_id="batch-prev",
        tenant_id=TENANT_ID,
    )

    assert copied == 0


@pytest.mark.asyncio
async def test_incremental_carryforward_verifies_call_args(monkeypatch) -> None:
    """Verify _carry_forward_prior_batch is called with correct domain names."""
    connection = FakeNormalizationConnection(
        {"tbscust": [], "tbsstock": [], "tbsstkhouse": []},
        stage_run_rows=[
            {
                "tenant_id": TENANT_ID,
                "status": "completed",
                "batch_id": "batch-inc",
                "target_schema": "raw_legacy",
            }
        ],
    )

    async def fake_open_raw_connection() -> FakeNormalizationConnection:
        return connection

    recorded_calls: list[dict[str, object]] = []

    async def fake_carry_forward_prior_batch(
        _conn,
        _schema,
        domain,
        *,
        current_batch_id: str,
        prior_batch_id: str,
        tenant_id: uuid.UUID,
    ) -> int:
        recorded_calls.append(
            {
                "domain": domain,
                "current_batch_id": current_batch_id,
                "prior_batch_id": prior_batch_id,
                "tenant_id": tenant_id,
            }
        )
        return 0

    monkeypatch.setattr(normalization, "_open_raw_connection", fake_open_raw_connection)
    monkeypatch.setattr(
        normalization,
        "_carry_forward_prior_batch",
        fake_carry_forward_prior_batch,
    )

    await normalization.run_normalization(
        batch_id="batch-inc",
        tenant_id=TENANT_ID,
        schema_name="raw_legacy",
        batch_mode="incremental",
        selected_domains=("parties", "products"),
        last_successful_batch_ids={
            "parties": "batch-prev-parties",
            "products": "batch-prev-products",
            "warehouses": "batch-prev-warehouses",
            "inventory": "batch-prev-inventory",
        },
    )

    # Verify the domains passed to carry_forward match the valid master domains.
    # Carryforward is called for all master domains that don't have fresh staging
    # and have an entry in last_successful_batch_ids.
    recorded_domains = {call["domain"] for call in recorded_calls}
    assert recorded_domains == _MASTER_NORMALIZATION_DOMAINS

    # Verify prior_batch_ids are correctly routed per domain.
    for call in recorded_calls:
        domain = call["domain"]
        prior_batch = call["prior_batch_id"]
        assert (
            prior_batch == f"batch-prev-{domain}"
        ), f"Expected prior_batch_id for {domain} to be batch-prev-{domain}, got {prior_batch}"


# ---------------------------------------------------------------------------
# _run_normalization_incremental smoke (empty stage tolerated)


@pytest.mark.asyncio
async def test_incremental_sales_scope_reuses_dependent_master_snapshots(
    monkeypatch,
) -> None:
    """In full mode empty stage raises; in incremental mode it is tolerated."""
    connection = FakeNormalizationConnection(
        {"tbscust": [], "tbsstock": [], "tbsstkhouse": []},
        stage_run_rows=[
            {
                "tenant_id": TENANT_ID,
                "status": "completed",
                "batch_id": "batch-inc",
                "target_schema": "raw_legacy",
            }
        ],
    )

    async def fake_open_raw_connection() -> FakeNormalizationConnection:
        return connection

    async def fake_carry_forward_prior_batch(
        _conn,
        _schema,
        domain,
        *,
        current_batch_id,  # noqa: ARG001
        prior_batch_id,  # noqa: ARG001
        tenant_id,  # noqa: ARG001
    ) -> int:
        return {"parties": 3, "products": 7}[domain]

    monkeypatch.setattr(normalization, "_open_raw_connection", fake_open_raw_connection)
    monkeypatch.setattr(
        normalization,
        "_carry_forward_prior_batch",
        fake_carry_forward_prior_batch,
    )

    result = await normalization.run_normalization(
        batch_id="batch-inc",
        tenant_id=TENANT_ID,
        schema_name="raw_legacy",
        batch_mode=RefreshBatchMode.INCREMENTAL,
        selected_domains=("parties", "products"),
        last_successful_batch_ids={
            "parties": "batch-prev",
            "products": "batch-prev",
        },
    )

    assert result.batch_id == "batch-inc"
    # No staged rows, but carryforward records reuse counts per domain.
    assert result.party_count == 3
    assert result.product_count == 7
    assert result.warehouse_count == 0
    assert result.inventory_count == 0
    assert result.reused_from_batch_ids == {"parties": 3, "products": 7}
    # Normalized copies stay untouched because no staged rows produced records.
    copy_tables = {call["table_name"] for call in connection.copy_calls}
    assert "normalized_parties" not in copy_tables
    assert "normalized_products" not in copy_tables


@pytest.mark.asyncio
async def test_incremental_scopes_clear_to_selected_domains(monkeypatch) -> None:
    """Verify scoped clear fires only for the in-scope domains."""
    connection = FakeNormalizationConnection(
        {"tbscust": [], "tbsstock": [], "tbsstkhouse": []},
        stage_run_rows=[
            {
                "tenant_id": TENANT_ID,
                "status": "completed",
                "batch_id": "batch-inc",
                "target_schema": "raw_legacy",
            }
        ],
    )

    async def fake_open_raw_connection() -> FakeNormalizationConnection:
        return connection

    async def fake_carry_forward_prior_batch(*_a, **_kw) -> int:
        return 0

    monkeypatch.setattr(normalization, "_open_raw_connection", fake_open_raw_connection)
    monkeypatch.setattr(
        normalization,
        "_carry_forward_prior_batch",
        fake_carry_forward_prior_batch,
    )

    await normalization.run_normalization(
        batch_id="batch-inc",
        tenant_id=TENANT_ID,
        schema_name="raw_legacy",
        batch_mode="incremental",
        selected_domains=("parties",),
    )

    delete_queries = [
        query
        for query, _args in connection.execute_calls
        if query.startswith("DELETE FROM")
    ]
    # Only parties was cleared, not products/warehouses/inventory or reviews.
    assert any("normalized_parties" in q for q in delete_queries)
    assert not any("normalized_products" in q for q in delete_queries)
    assert not any("normalized_warehouses" in q for q in delete_queries)
    assert not any("normalized_inventory_prep" in q for q in delete_queries)
    assert not any(
        "product_category_review_candidates" in q for q in delete_queries
    )
