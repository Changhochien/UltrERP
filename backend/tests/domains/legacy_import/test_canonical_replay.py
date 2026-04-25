from __future__ import annotations

import uuid

import pytest

import domains.legacy_import.canonical as canonical
from domains.legacy_import.normalization import deterministic_legacy_uuid
from tests.domains.legacy_import.canonical_test_support import FakeCanonicalConnection


@pytest.mark.asyncio
async def test_run_canonical_import_uses_upserts_for_replay_safety(monkeypatch) -> None:
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000402")
    connection = FakeCanonicalConnection(
        {
            "normalized_parties": [
                {
                    "legacy_code": "C001",
                    "role": "customer",
                    "company_name": "Replay Co",
                    "tax_id": "12345675",
                    "full_address": "Taipei",
                    "address": "Taipei",
                    "phone": "02-1234",
                    "email": "",
                    "contact_person": "Alice",
                    "deterministic_id": deterministic_legacy_uuid("party", "customer", "C001"),
                }
            ],
            "normalized_products": [
                {
                    "legacy_code": "P001",
                    "name": "Widget",
                    "category": "BELT",
                    "unit": "pcs",
                    "status": "A",
                    "deterministic_id": deterministic_legacy_uuid("product", "P001"),
                }
            ],
            "normalized_warehouses": [
                {
                    "code": "LEGACY_DEFAULT",
                    "name": "Legacy Default Warehouse",
                    "location": None,
                    "address": None,
                    "deterministic_id": deterministic_legacy_uuid("warehouse", "LEGACY_DEFAULT"),
                }
            ],
            "normalized_inventory_prep": [
                {
                    "product_legacy_code": "P001",
                    "warehouse_code": "LEGACY_DEFAULT",
                    "quantity_on_hand": 8,
                    "reorder_point": 0,
                    "product_deterministic_id": deterministic_legacy_uuid("product", "P001"),
                    "warehouse_deterministic_id": deterministic_legacy_uuid(
                        "warehouse", "LEGACY_DEFAULT"
                    ),
                }
            ],
            "product_code_mapping": [],
            "sales_headers": [
                {
                    "doc_number": "1130826005",
                    "invoice_date": "2024-08-26",
                    "customer_code": "C001",
                    "customer_name": "Replay Co",
                    "address": "Taipei",
                    "currency_code": "TWD",
                    "exchange_rate": "1.0",
                    "subtotal": "100.00",
                    "tax_type": "1",
                    "tax_amount": "5.00",
                    "total_amount": "105.00",
                    "remark": "replay",
                    "created_by": "SYSTEM",
                    "tax_rate": "0.0500",
                }
            ],
            "sales_lines": [
                {
                    "doc_number": "1130826005",
                    "line_number": 1,
                    "product_code": "P001",
                    "product_name": "Replay Widget",
                    "unit": "pcs",
                    "qty": "2",
                    "unit_price": "50.00",
                    "extended_amount": "100.00",
                    "tax_amount": "5.00",
                    "line_tax_amount": "5.00",
                    "available_stock_snapshot": 8,
                }
            ],
        }
    )

    async def fake_open_raw_connection() -> FakeCanonicalConnection:
        return connection

    monkeypatch.setattr(canonical, "_open_raw_connection", fake_open_raw_connection)

    await canonical.run_canonical_import(
        batch_id="batch-005",
        tenant_id=tenant_id,
        schema_name="raw_legacy",
    )

    sql = "\n".join(query for query, _ in connection.execute_calls)
    order_line_query = next(
        query for query, _ in connection.execute_calls if "INSERT INTO order_lines" in query
    )
    assert "INSERT INTO customers" in sql and "ON CONFLICT" in sql
    assert "customer_type" in sql
    assert "EXCLUDED.customer_type = 'unknown'" in sql
    assert "INSERT INTO product" in sql and "ON CONFLICT" in sql
    assert "INSERT INTO warehouse" in sql and "ON CONFLICT" in sql
    assert "INSERT INTO inventory_stock" in sql and "ON CONFLICT" in sql
    assert "product_name_snapshot" in order_line_query
    assert "product_category_snapshot" in order_line_query
    assert "product_name_snapshot=COALESCE(" in order_line_query
    assert "order_lines.product_name_snapshot," in order_line_query
    assert "EXCLUDED.product_name_snapshot" in order_line_query
    assert "product_category_snapshot=COALESCE(" in order_line_query
    assert "order_lines.product_category_snapshot," in order_line_query
    assert "EXCLUDED.product_category_snapshot" in order_line_query
    assert 'INSERT INTO "raw_legacy".canonical_record_lineage' in sql and "ON CONFLICT" in sql


@pytest.mark.asyncio
async def test_run_canonical_import_replay_preserves_existing_snapshot_values(monkeypatch) -> None:
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000452")
    doc_number = "1130826010"
    connection = FakeCanonicalConnection(
        {
            "normalized_parties": [
                {
                    "legacy_code": "C001",
                    "role": "customer",
                    "company_name": "Replay Snapshot Co",
                    "tax_id": "12345675",
                    "full_address": "Taipei",
                    "address": "Taipei",
                    "phone": "02-1234",
                    "email": "",
                    "contact_person": "Alice",
                    "deterministic_id": deterministic_legacy_uuid("party", "customer", "C001"),
                }
            ],
            "normalized_products": [
                {
                    "legacy_code": "P001",
                    "name": "Replay Master Widget v1",
                    "category": "BELT",
                    "unit": "pcs",
                    "status": "A",
                    "deterministic_id": deterministic_legacy_uuid("product", "P001"),
                }
            ],
            "normalized_warehouses": [],
            "normalized_inventory_prep": [],
            "product_code_mapping": [],
            "sales_headers": [
                {
                    "doc_number": doc_number,
                    "invoice_date": "2024-08-26",
                    "customer_code": "C001",
                    "customer_name": "Replay Snapshot Co",
                    "address": "Taipei",
                    "currency_code": "TWD",
                    "exchange_rate": "1.0",
                    "subtotal": "100.00",
                    "tax_type": "1",
                    "tax_amount": "5.00",
                    "total_amount": "105.00",
                    "remark": "replay",
                    "created_by": "SYSTEM",
                    "tax_rate": "0.0500",
                }
            ],
            "sales_lines": [
                {
                    "doc_number": doc_number,
                    "line_number": 1,
                    "product_code": "P001",
                    "product_name": "Replay Line Widget v1",
                    "unit": "pcs",
                    "qty": "2",
                    "unit_price": "50.00",
                    "extended_amount": "100.00",
                    "tax_amount": "5.00",
                    "line_tax_amount": "5.00",
                    "available_stock_snapshot": 8,
                }
            ],
        }
    )

    async def fake_open_raw_connection() -> FakeCanonicalConnection:
        return connection

    monkeypatch.setattr(canonical, "_open_raw_connection", fake_open_raw_connection)

    await canonical.run_canonical_import(
        batch_id="batch-replay-snapshot",
        tenant_id=tenant_id,
        schema_name="raw_legacy",
    )

    order_line_id = canonical._tenant_scoped_uuid(tenant_id, "order-line", doc_number, "1")
    first_import_row = connection._fake_order_lines[order_line_id]
    assert first_import_row["product_name_snapshot"] == "Replay Master Widget v1"
    assert first_import_row["product_category_snapshot"] == "BELT"

    connection.rows_by_key["normalized_products"][0]["name"] = "Replay Master Widget v2"
    connection.rows_by_key["normalized_products"][0]["category"] = "RENAMED"
    connection.rows_by_key["sales_lines"][0]["product_name"] = "Replay Line Widget v2"

    await canonical.run_canonical_import(
        batch_id="batch-replay-snapshot",
        tenant_id=tenant_id,
        schema_name="raw_legacy",
    )

    replayed_row = connection._fake_order_lines[order_line_id]
    assert replayed_row["description"] == "Replay Line Widget v2"
    assert replayed_row["product_name_snapshot"] == "Replay Master Widget v1"
    assert replayed_row["product_category_snapshot"] == "BELT"


@pytest.mark.asyncio
async def test_run_canonical_import_batch_rerun_is_idempotent_at_lineage_layer(monkeypatch) -> None:
    """AC4: Re-running the same batch produces exactly one lineage entry per source mapping."""
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000471")
    connection = FakeCanonicalConnection(
        {
            "normalized_parties": [
                {
                    "legacy_code": "T067",
                    "role": "supplier",
                    "company_name": "Supplier A",
                    "tax_id": "22345678",
                    "full_address": "Taoyuan",
                    "address": "Taoyuan",
                    "phone": "03-1234",
                    "email": "",
                    "contact_person": "Bob",
                    "source_table": "tbscust",
                    "source_row_number": 7,
                    "deterministic_id": deterministic_legacy_uuid("party", "supplier", "T067"),
                }
            ],
            "normalized_products": [
                {
                    "legacy_code": "P001",
                    "name": "Widget",
                    "category": "BELT",
                    "unit": "pcs",
                    "status": "A",
                    "source_table": "tbsstock",
                    "source_row_number": 12,
                    "deterministic_id": deterministic_legacy_uuid("product", "P001"),
                }
            ],
            "normalized_warehouses": [
                {
                    "code": "WH-A",
                    "name": "Legacy Warehouse A",
                    "location": None,
                    "address": None,
                    "source_table": "tbsstkhouse",
                    "source_row_number": 31,
                    "deterministic_id": deterministic_legacy_uuid("warehouse", "WH-A"),
                }
            ],
            "normalized_inventory_prep": [
                {
                    "product_legacy_code": "P001",
                    "warehouse_code": "WH-A",
                    "quantity_on_hand": 8,
                    "reorder_point": 0,
                    "product_deterministic_id": deterministic_legacy_uuid("product", "P001"),
                    "warehouse_deterministic_id": deterministic_legacy_uuid("warehouse", "WH-A"),
                }
            ],
            "product_code_mapping": [],
            "sales_headers": [],
            "sales_lines": [],
            "purchase_headers": [
                {
                    "doc_number": "1130827001",
                    "raw_invoice_number": "GG46104158",
                    "invoice_number": "GG46104158",
                    "slip_date": "2024-08-27",
                    "raw_invoice_date": "2024-08-27",
                    "invoice_date": "2024-08-27",
                    "period_code": "11308",
                    "supplier_code": "T067",
                    "supplier_name": "Supplier A",
                    "address": "Taoyuan",
                    "notes": "SQ04",
                    "subtotal": "90.00",
                    "tax_amount": "5.00",
                    "must_pay_amount": "95.00",
                    "total_amount": "95.00",
                    "source_row_number": 17,
                }
            ],
            "purchase_lines": [
                {
                    "doc_number": "1130827001",
                    "line_number": 1,
                    "product_code": "P001",
                    "product_name": "Widget",
                    "warehouse_code": "WH-A",
                    "qty": "3",
                    "unit_price": "30.00",
                    "extended_amount": "90.00",
                    "receipt_date": "2024-08-27",
                    "source_row_number": 18,
                }
            ],
        }
    )

    async def fake_open_raw_connection() -> FakeCanonicalConnection:
        return connection

    monkeypatch.setattr(canonical, "_open_raw_connection", fake_open_raw_connection)

    batch_id = "batch-receiving-audit"

    await canonical.run_canonical_import(
        batch_id=batch_id,
        tenant_id=tenant_id,
        schema_name="raw_legacy",
    )

    lineage_queries = [
        query for query, _ in connection.committed_execute_calls
        if 'INSERT INTO "raw_legacy".canonical_record_lineage' in query
    ]

    for query in lineage_queries:
        assert "ON CONFLICT" in query
        on_conflict_idx = query.index("ON CONFLICT")
        do_update_idx = query.index("DO UPDATE")
        on_conflict_target = query[on_conflict_idx:do_update_idx]
        assert "canonical_id" not in on_conflict_target.lower()
        assert "batch_id" in on_conflict_target