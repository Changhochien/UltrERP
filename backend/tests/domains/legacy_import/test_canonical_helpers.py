from __future__ import annotations

import uuid

import pytest

import domains.legacy_import.canonical as canonical
import domains.legacy_import.source_resolution as source_resolution
from domains.legacy_import.canonical_common import _lineage_record_query_for_holding
from tests.domains.legacy_import.canonical_test_support import (
    FakeCanonicalConnection,
    QueryCaptureConnection,
    RawPurchaseHeaderConnection,
)


def test_build_product_master_snapshot_preserves_category_provenance() -> None:
    snapshot = canonical._build_product_master_snapshot(
        {
            "legacy_code": "PC096",
            "name": "三角皮帶 C-96",
            "category": "V-Belts",
            "legacy_category": None,
            "stock_kind": "0",
            "category_source": "heuristic_rule",
            "category_rule_id": "code-prefix-v-belts",
            "category_confidence": "0.98",
            "unit": "條",
            "status": "A",
            "source_table": "tbsstock",
            "source_row_number": 12,
        }
    )

    assert snapshot == {
        "legacy_code": "PC096",
        "name": "三角皮帶 C-96",
        "category": "V-Belts",
        "stock_kind": "0",
        "category_source": "heuristic_rule",
        "category_rule_id": "code-prefix-v-belts",
        "category_confidence": "0.98",
        "unit": "條",
        "status": "A",
        "source_table": "tbsstock",
        "source_row_number": 12,
    }


@pytest.mark.asyncio
async def test_iter_normalized_parties_selects_customer_type() -> None:
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000499")
    connection = QueryCaptureConnection(
        [
            {
                "legacy_code": "C001",
                "role": "customer",
                "customer_type": "dealer",
            }
        ]
    )

    rows = [
        row
        async for row in canonical._iter_normalized_parties(
            connection,
            "raw_legacy",
            "batch-customer-type",
            tenant_id,
        )
    ]

    assert connection.last_query is not None
    assert "customer_type" in connection.last_query
    assert rows == [{"legacy_code": "C001", "role": "customer", "customer_type": "dealer"}]


@pytest.mark.asyncio
async def test_try_upsert_holding_and_lineage_rolls_back_with_savepoint(
    monkeypatch,
) -> None:
    connection = FakeCanonicalConnection({})

    async def fail_holding_row(*args, **kwargs) -> None:
        raise ValueError("boom")

    monkeypatch.setattr(source_resolution, "hold_source_row", fail_holding_row)

    result = await canonical._try_upsert_holding_and_lineage(
        connection,
        "raw_legacy",
        uuid.uuid4(),
        uuid.UUID("00000000-0000-0000-0000-000000000599"),
        "batch-savepoint",
        "payment_history",
        "tbsspay",
        "PAY-001",
        17,
        17,
        {"col_2": "PAY-001"},
        "holding test",
    )

    assert result is False
    assert connection.committed_execute_calls == []
    assert connection._fake_resolution_rows == {}
    assert connection._fake_holding_rows == {}
    assert not any(query.strip() == "ROLLBACK" for query, _ in connection.execute_calls)


@pytest.mark.asyncio
async def test_flush_lineage_resolutions_uses_executemany_when_available() -> None:
    connection = FakeCanonicalConnection({})
    run_id = uuid.uuid4()
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000612")

    await canonical._flush_lineage_resolutions(
        connection,
        "raw_legacy",
        run_id,
        tenant_id,
        "batch-lineage",
        [
            canonical.PendingLineageResolution(
                canonical_table="orders",
                canonical_id=uuid.uuid4(),
                source_table="tbsslipx",
                source_identifier="SO-001",
                source_row_number=1,
            ),
            canonical.PendingLineageResolution(
                canonical_table="orders",
                canonical_id=uuid.uuid4(),
                source_table="tbsslipx",
                source_identifier="SO-002",
                source_row_number=2,
            ),
        ],
    )

    lineage_batches = [
        rows
        for query, rows in connection.executemany_calls
        if 'INSERT INTO "raw_legacy".canonical_record_lineage' in query
    ]
    assert len(lineage_batches) == 1
    assert [row[5] for row in lineage_batches[0]] == ["SO-001", "SO-002"]
    assert any(
        'INSERT INTO "raw_legacy".source_row_resolution' in query
        for query, _ in connection.executemany_calls
    )
    assert connection._fake_resolution_rows[
        (tenant_id, "batch-lineage", "tbsslipx", "SO-001", 1)
    ]["status"] == source_resolution.STATUS_RESOLVED
    assert connection._fake_resolution_rows[
        (tenant_id, "batch-lineage", "tbsslipx", "SO-002", 2)
    ]["status"] == source_resolution.STATUS_RESOLVED


@pytest.mark.asyncio
async def test_ensure_canonical_support_tables_create_run_lineage_and_holding_tables() -> None:
    connection = FakeCanonicalConnection({})

    await canonical._ensure_canonical_support_tables(connection, "raw_legacy")

    ddl = "\n".join(query for query, _ in connection.execute_calls)
    normalized_ddl = " ".join(ddl.split())
    assert 'CREATE TABLE IF NOT EXISTS "raw_legacy".canonical_import_runs' in ddl
    assert 'CREATE TABLE IF NOT EXISTS "raw_legacy".canonical_import_step_runs' in ddl
    assert 'CREATE TABLE IF NOT EXISTS "raw_legacy".canonical_record_lineage' in ddl
    assert 'CREATE TABLE IF NOT EXISTS "raw_legacy".unsupported_history_holding' in ddl
    assert 'CREATE TABLE IF NOT EXISTS "raw_legacy".source_row_resolution' in ddl
    assert 'CREATE TABLE IF NOT EXISTS "raw_legacy".source_row_resolution_events' in ddl
    assert (
        'CREATE INDEX IF NOT EXISTS canonical_record_lineage_source_identity '
        'ON "raw_legacy".canonical_record_lineage'
    ) in normalized_ddl


def test_holding_lineage_query_conflicts_on_canonical_table() -> None:
    normalized_query = " ".join(_lineage_record_query_for_holding("raw_legacy").split())

    assert (
        "ON CONFLICT ( batch_id, tenant_id, canonical_table, source_table, "
        "source_identifier, source_row_number )"
    ) in normalized_query


@pytest.mark.asyncio
async def test_fetch_purchase_headers_prefers_invoice_number_and_invoice_date() -> None:
    connection = RawPurchaseHeaderConnection(
        [
            {
                "doc_number": "1130827001",
                "invoice_number": "GG46104158",
                "invoice_date": "2024-08-26",
                "supplier_code": "T067",
                "supplier_name": "Supplier A",
                "address": "Taoyuan",
                "currency_code": "0001",
                "subtotal": "90.00",
                "tax_amount": "5.00",
                "notes": "SQ04",
                "total_amount": "95.00",
                "source_row_number": 17,
            }
        ]
    )

    rows = await canonical._fetch_purchase_headers(connection, "raw_legacy", "batch-ap")

    assert connection.queries
    assert "AS invoice_number" in connection.queries[0]
    assert "col_42" in connection.queries[0]
    assert "col_62" in connection.queries[0]
    assert "COALESCE(col_1, '') = '4'" in connection.queries[0]
    assert rows == [
        {
            "doc_number": "1130827001",
            "invoice_number": "GG46104158",
            "invoice_date": "2024-08-26",
            "supplier_code": "T067",
            "supplier_name": "Supplier A",
            "address": "Taoyuan",
            "currency_code": "0001",
            "subtotal": "90.00",
            "tax_amount": "5.00",
            "notes": "SQ04",
            "total_amount": "95.00",
            "source_row_number": 17,
        }
    ]


@pytest.mark.asyncio
async def test_fetch_sales_headers_applies_doc_number_scope_in_sql() -> None:
    connection = RawPurchaseHeaderConnection([])

    await canonical._fetch_sales_headers(
        connection,
        "raw_legacy",
        "batch-sales",
        frozenset({"DOC-001", "DOC-002"}),
    )

    assert connection.queries
    assert "col_2 = ANY($2::text[])" in connection.queries[0]


@pytest.mark.asyncio
async def test_fetch_purchase_headers_applies_doc_number_scope_in_sql() -> None:
    connection = RawPurchaseHeaderConnection([])

    await canonical._fetch_purchase_headers(
        connection,
        "raw_legacy",
        "batch-ap",
        frozenset({"PO-001", "PO-002"}),
    )

    assert connection.queries
    assert "col_2 = ANY($2::text[])" in connection.queries[0]


@pytest.mark.asyncio
async def test_fetch_purchase_lines_selects_receipt_date_and_filters_purchase_invoices() -> None:
    connection = RawPurchaseHeaderConnection(
        [
            {
                "doc_number": "1130827001",
                "line_number": 1,
                "receipt_date": "2024-08-27",
                "product_code": "P001",
                "warehouse_code": "WH-A",
                "qty": "3",
                "source_row_number": 18,
            }
        ]
    )

    rows = await canonical._fetch_purchase_lines(connection, "raw_legacy", "batch-ap")

    assert connection.queries
    assert "col_4 AS receipt_date" in connection.queries[0]
    assert "COALESCE(col_1, '') = '4'" in connection.queries[0]
    assert rows[0]["receipt_date"] == "2024-08-27"


@pytest.mark.asyncio
async def test_fetch_purchase_lines_applies_doc_number_scope_in_sql() -> None:
    connection = RawPurchaseHeaderConnection([])

    await canonical._fetch_purchase_lines(
        connection,
        "raw_legacy",
        "batch-ap",
        frozenset({"PO-001", "PO-002"}),
    )

    assert connection.queries
    assert "col_2 = ANY($2::text[])" in connection.queries[0]


@pytest.mark.asyncio
async def test_build_entity_scope_closure_keys_extracts_correctly() -> None:
    entity_scope = {
        "sales": {
            "closure_keys": [
                {"document_number": "DOC-001"},
                {"document_number": "DOC-002"},
            ]
        },
        "purchase-invoices": {
            "closure_keys": [{"document_number": "PO-001"}]
        },
        "products": {
            "closure_keys": [
                {"product-code": "P001"},
                {"product_code": "P002"},
            ]
        },
    }

    result = canonical._build_entity_scope_closure_keys(entity_scope)

    assert "sales" in result
    assert result["sales"] == frozenset({"DOC-001", "DOC-002"})
    assert result["purchase-invoices"] == frozenset({"PO-001"})
    assert result["products"] == frozenset({"P001", "P002"})


@pytest.mark.asyncio
async def test_filter_sales_headers_by_scope_includes_matching() -> None:
    headers = [
        {"doc_number": "DOC-001"},
        {"doc_number": "DOC-002"},
        {"doc_number": "DOC-003"},
    ]
    scope_keys = {"sales": frozenset({"DOC-001", "DOC-002"})}

    result = canonical._filter_sales_headers_by_scope(headers, scope_keys)

    assert len(result) == 2
    assert all(header["doc_number"] in {"DOC-001", "DOC-002"} for header in result)


@pytest.mark.asyncio
async def test_filter_sales_headers_by_scope_empty_scope_returns_all() -> None:
    headers = [
        {"doc_number": "DOC-001"},
        {"doc_number": "DOC-002"},
    ]

    result = canonical._filter_sales_headers_by_scope(headers, {})

    assert len(result) == 2


@pytest.mark.asyncio
async def test_filter_sales_lines_preserves_full_family() -> None:
    lines = [
        {"doc_number": "DOC-001", "line_number": 1},
        {"doc_number": "DOC-001", "line_number": 2},
        {"doc_number": "DOC-002", "line_number": 1},
        {"doc_number": "DOC-003", "line_number": 1},
    ]
    scoped_doc_numbers = frozenset({"DOC-001", "DOC-002"})

    result = canonical._filter_sales_lines_by_scope(lines, scoped_doc_numbers)

    assert len(result) == 3
    doc_001_lines = [line for line in result if line["doc_number"] == "DOC-001"]
    assert len(doc_001_lines) == 2
    assert any(line["line_number"] == 1 for line in doc_001_lines)
    assert any(line["line_number"] == 2 for line in doc_001_lines)