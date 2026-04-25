from __future__ import annotations

import uuid

import pytest

import domains.legacy_import.canonical as canonical
from common.models.stock_adjustment import ReasonCode
from domains.legacy_import.normalization import deterministic_legacy_uuid
from tests.domains.legacy_import.canonical_test_support import (
    FakeCanonicalConnection,
    _args_for_queries,
)


@pytest.mark.asyncio
async def test_run_canonical_import_imports_legacy_receiving_audit_records(
    monkeypatch,
) -> None:
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000416")
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
                    "email": "ap@supplier.test",
                    "contact_person": "Betty",
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

    await canonical.run_canonical_import(
        batch_id="batch-receiving-audit",
        tenant_id=tenant_id,
        schema_name="raw_legacy",
    )

    adjustment_query = next(
        query for query, _ in connection.execute_calls if "INSERT INTO stock_adjustment" in query
    )
    adjustment_args = next(
        args for query, args in connection.execute_calls if "INSERT INTO stock_adjustment" in query
    )
    assert "ON CONFLICT (id) DO NOTHING" in adjustment_query
    assert adjustment_args[1] == tenant_id
    assert adjustment_args[4] == 3
    assert adjustment_args[5] == ReasonCode.SUPPLIER_DELIVERY
    assert adjustment_args[6] == "legacy_import"
    assert adjustment_args[7] == "Legacy import: invoice 1130827001"
    assert adjustment_args[9] == canonical._as_timestamp(canonical._as_legacy_date("2024-08-27"))
    assert len(_args_for_queries(connection.execute_calls, "INSERT INTO inventory_stock")) == 1

    lineage_args = _args_for_queries(
        connection.execute_calls,
        'INSERT INTO "raw_legacy".canonical_record_lineage',
    )
    assert any(
        args[1] == "batch-receiving-audit"
        and args[2] == "stock_adjustment"
        and args[4] == "tbsslipdtj"
        and args[5] == "1130827001:1"
        for args in lineage_args
    )


@pytest.mark.asyncio
async def test_run_canonical_import_receiving_audit_routes_blank_doc_number_to_holding(
    monkeypatch,
) -> None:
    """Blank doc_number rows are routed to holding to prevent UUID collisions."""
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000416")
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
                    "email": "ap@supplier.test",
                    "contact_person": "Betty",
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
            "normalized_inventory_prep": [],
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
                    "col_1": "4",
                    "doc_number": "",
                    "line_number": 3,
                    "product_code": "P001",
                    "product_name": "Widget",
                    "warehouse_code": "WH-A",
                    "qty": "3",
                    "unit_price": "30.00",
                    "extended_amount": "90.00",
                    "receipt_date": "2024-08-27",
                }
            ],
        }
    )

    async def fake_open_raw_connection() -> FakeCanonicalConnection:
        return connection

    monkeypatch.setattr(canonical, "_open_raw_connection", fake_open_raw_connection)

    await canonical.run_canonical_import(
        batch_id="batch-receiving-blank-doc",
        tenant_id=tenant_id,
        schema_name="raw_legacy",
    )

    assert not any(
        "INSERT INTO stock_adjustment" in query
        for query, _ in connection.execute_calls
    )

    holding_calls = [
        args
        for query, args in connection.execute_calls
        if 'INSERT INTO "raw_legacy".unsupported_history_holding' in query
        and "tbsslipdtj" in args
    ]
    assert len(holding_calls) == 1

    holding_args = holding_calls[0]
    assert holding_args[5] == ":3"
    assert "row_id=3" in holding_args[8]


@pytest.mark.asyncio
async def test_run_canonical_import_receiving_audit_coerces_fractional_quantity(
    monkeypatch,
) -> None:
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000430")
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
                    "email": "ap@supplier.test",
                    "contact_person": "Betty",
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
                    "doc_number": "1070307001",
                    "invoice_date": "2018-03-07",
                    "supplier_code": "T067",
                    "supplier_name": "Supplier A",
                    "address": "Taoyuan",
                    "subtotal": "0.00",
                    "tax_amount": "0.00",
                    "must_pay_amount": "0.00",
                    "total_amount": "0.00",
                    "source_row_number": 17,
                }
            ],
            "purchase_lines": [
                {
                    "doc_number": "1070307001",
                    "line_number": 1,
                    "product_code": "P001",
                    "product_name": "Widget",
                    "warehouse_code": "WH-A",
                    "qty": "4.10000000",
                    "unit_price": "30.00",
                    "extended_amount": "123.00",
                    "receipt_date": "2018-03-07",
                    "source_row_number": 18,
                }
            ],
        }
    )

    async def fake_open_raw_connection() -> FakeCanonicalConnection:
        return connection

    monkeypatch.setattr(canonical, "_open_raw_connection", fake_open_raw_connection)

    await canonical.run_canonical_import(
        batch_id="batch-receiving-audit-fractional",
        tenant_id=tenant_id,
        schema_name="raw_legacy",
    )

    adjustment_args = next(
        args for query, args in connection.execute_calls if "INSERT INTO stock_adjustment" in query
    )
    assert adjustment_args[4] == 4
    assert "coerced from 4.1 to 4" in adjustment_args[7]


@pytest.mark.asyncio
async def test_run_canonical_import_legacy_receiving_audit_falls_back_to_header_date(
    monkeypatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000417")
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
                    "email": "ap@supplier.test",
                    "contact_person": "Betty",
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
            "normalized_inventory_prep": [],
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
                    "receipt_date": "1900-01-01",
                    "source_row_number": 18,
                }
            ],
        }
    )

    async def fake_open_raw_connection() -> FakeCanonicalConnection:
        return connection

    monkeypatch.setattr(canonical, "_open_raw_connection", fake_open_raw_connection)

    with caplog.at_level("WARNING"):
        await canonical.run_canonical_import(
            batch_id="batch-receiving-fallback",
            tenant_id=tenant_id,
            schema_name="raw_legacy",
        )

    adjustment_args = next(
        args for query, args in connection.execute_calls if "INSERT INTO stock_adjustment" in query
    )
    assert adjustment_args[9] == canonical._as_timestamp(canonical._as_legacy_date("2024-08-27"))
    assert "falling back to header invoice_date" in caplog.text


@pytest.mark.asyncio
async def test_run_canonical_import_replays_legacy_receiving_audit_idempotently(
    monkeypatch,
) -> None:
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000418")
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
                    "email": "ap@supplier.test",
                    "contact_person": "Betty",
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
            "normalized_inventory_prep": [],
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
                    "receipt_date": "1900-01-01",
                    "source_row_number": 18,
                }
            ],
        }
    )

    async def fake_open_raw_connection() -> FakeCanonicalConnection:
        return connection

    monkeypatch.setattr(canonical, "_open_raw_connection", fake_open_raw_connection)

    await canonical.run_canonical_import(
        batch_id="batch-receiving-replay",
        tenant_id=tenant_id,
        schema_name="raw_legacy",
    )
    await canonical.run_canonical_import(
        batch_id="batch-receiving-replay",
        tenant_id=tenant_id,
        schema_name="raw_legacy",
    )

    assert len(connection._fake_stock_adjustments) == 1
    receiving_lineage = [
        key for key in connection._fake_lineage_rows if key[2] == "stock_adjustment"
    ]
    assert len(receiving_lineage) == 1