from __future__ import annotations

import uuid

import pytest

import domains.legacy_import.canonical as canonical
from domains.legacy_import.normalization import deterministic_legacy_uuid
from tests.domains.legacy_import.canonical_test_support import FakeCanonicalConnection


# ---------------------------------------------------------------------------
# Story 15.26 — Scoped Incremental Canonical Import
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scoped_incremental_import_skips_domains_not_in_scope(monkeypatch) -> None:
    """AC1: When selected_domains is provided with batch_mode=incremental,
    only the specified domains are processed."""
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000001526")
    connection = FakeCanonicalConnection(
        {
            "normalized_parties": [
                {
                    "legacy_code": "C001",
                    "role": "customer",
                    "company_name": "Scoped Customer",
                    "tax_id": "12345678",
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
            "normalized_inventory_prep": [],
            "product_code_mapping": [],
            "sales_headers": [],
            "sales_lines": [],
            "purchase_headers": [],
            "purchase_lines": [],
        }
    )

    async def fake_open_raw_connection() -> FakeCanonicalConnection:
        return connection

    monkeypatch.setattr(canonical, "_open_raw_connection", fake_open_raw_connection)

    result = await canonical.run_canonical_import(
        batch_id="batch-scoped-001",
        tenant_id=tenant_id,
        schema_name="raw_legacy",
        selected_domains=["customers"],
        batch_mode="incremental",
    )

    assert result.customer_count == 1
    assert result.selected_domains == ("customers",)
    assert "suppliers" in result.skipped_domains
    assert "products" in result.skipped_domains
    assert "warehouses" in result.skipped_domains
    assert "inventory" in result.skipped_domains
    assert "sales_history" in result.skipped_domains
    assert "purchase_history" in result.skipped_domains

    suppliers_upserts = [
        query for query, _ in connection.execute_calls
        if "INSERT INTO supplier" in query
    ]
    products_upserts = [
        query for query, _ in connection.execute_calls
        if "INSERT INTO product" in query
    ]
    assert len(suppliers_upserts) == 0
    assert len(products_upserts) == 0
    assert not any(
        'FROM "raw_legacy".tbsslipx' in query
        or 'FROM "raw_legacy".tbsslipdtx' in query
        or 'FROM "raw_legacy".tbsslipj' in query
        or 'FROM "raw_legacy".tbsslipdtj' in query
        for query, _ in connection.fetch_queries
    )
    assert not any(
        'FROM "raw_legacy".product_code_mapping' in query
        for query, _ in connection.fetch_queries
    )
    assert not any(
        "tbsslipj" in query or "tbsslipdtj" in query
        for query, _ in connection.fetchval_queries
    )


@pytest.mark.asyncio
async def test_scoped_incremental_import_filters_sales_by_entity_scope(monkeypatch) -> None:
    """AC2: Full document families are rebuilt deterministically for in-scope documents."""
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000001527")
    connection = FakeCanonicalConnection(
        {
            "normalized_parties": [
                {
                    "legacy_code": "C001",
                    "role": "customer",
                    "company_name": "Scoped Customer",
                    "tax_id": "12345678",
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
            "normalized_warehouses": [],
            "normalized_inventory_prep": [],
            "product_code_mapping": [],
            "sales_headers": [
                {
                    "doc_number": "IN-SCOPE-001",
                    "invoice_date": "2024-08-26",
                    "customer_code": "C001",
                    "customer_name": "Scoped Customer",
                    "address": "Taipei",
                    "currency_code": "TWD",
                    "exchange_rate": "1.0",
                    "subtotal": "100.00",
                    "tax_type": "1",
                    "tax_amount": "5.00",
                    "total_amount": "105.00",
                    "remark": "in scope",
                    "created_by": "SYSTEM",
                    "tax_rate": "0.0500",
                },
                {
                    "doc_number": "OUT-OF-SCOPE-002",
                    "invoice_date": "2024-08-27",
                    "customer_code": "C001",
                    "customer_name": "Scoped Customer",
                    "address": "Taipei",
                    "currency_code": "TWD",
                    "exchange_rate": "1.0",
                    "subtotal": "200.00",
                    "tax_type": "1",
                    "tax_amount": "10.00",
                    "total_amount": "210.00",
                    "remark": "out of scope",
                    "created_by": "SYSTEM",
                    "tax_rate": "0.0500",
                },
            ],
            "sales_lines": [
                {
                    "doc_number": "IN-SCOPE-001",
                    "line_number": 1,
                    "product_code": "P001",
                    "product_name": "Widget",
                    "unit": "pcs",
                    "qty": "2",
                    "unit_price": "50.00",
                    "extended_amount": "100.00",
                    "tax_amount": "5.00",
                },
                {
                    "doc_number": "OUT-OF-SCOPE-002",
                    "line_number": 1,
                    "product_code": "P001",
                    "product_name": "Widget",
                    "unit": "pcs",
                    "qty": "4",
                    "unit_price": "50.00",
                    "extended_amount": "200.00",
                    "tax_amount": "10.00",
                },
            ],
            "purchase_headers": [],
            "purchase_lines": [],
        }
    )

    async def fake_open_raw_connection() -> FakeCanonicalConnection:
        return connection

    def fail_sales_header_filter(*args, **kwargs):
        raise AssertionError("sales header filter should be skipped when SQL is already scoped")

    def fail_sales_line_filter(*args, **kwargs):
        raise AssertionError("sales line filter should be skipped when SQL is already scoped")

    monkeypatch.setattr(canonical, "_open_raw_connection", fake_open_raw_connection)
    monkeypatch.setattr(canonical, "_filter_sales_headers_by_scope", fail_sales_header_filter)
    monkeypatch.setattr(canonical, "_filter_sales_lines_by_scope", fail_sales_line_filter)

    result = await canonical.run_canonical_import(
        batch_id="batch-scoped-002",
        tenant_id=tenant_id,
        schema_name="raw_legacy",
        selected_domains=["customers", "products", "sales_history"],
        entity_scope={"sales": {"closure_keys": [{"document_number": "IN-SCOPE-001"}]}},
        batch_mode="incremental",
    )

    assert result.order_count == 1
    assert result.invoice_count == 1
    assert result.scoped_document_count == 1

    orders_upserts = [
        args for query, args in connection.execute_calls
        if "INSERT INTO orders" in query
    ]
    assert len(orders_upserts) == 1
    assert orders_upserts[0][3] == "IN-SCOPE-001"

    order_lines_upserts = [
        args for query, args in connection.execute_calls
        if "INSERT INTO order_lines" in query
    ]
    assert len(order_lines_upserts) == 1


@pytest.mark.asyncio
async def test_scoped_receiving_only_run_skips_purchase_history_line_filter(monkeypatch) -> None:
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000001531")
    connection = FakeCanonicalConnection(
        {
            "normalized_parties": [],
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
            "normalized_inventory_prep": [],
            "product_code_mapping": [],
            "sales_headers": [],
            "sales_lines": [],
            "purchase_headers": [
                {
                    "doc_number": "RECV-001",
                    "invoice_date": "2024-08-27",
                    "supplier_code": "T067",
                    "supplier_name": "Supplier A",
                    "address": "Taoyuan",
                    "subtotal": "90.00",
                    "tax_amount": "0.00",
                    "total_amount": "90.00",
                }
            ],
            "purchase_lines": [
                {
                    "doc_number": "RECV-001",
                    "line_number": 1,
                    "product_code": "P001",
                    "warehouse_code": "LEGACY_DEFAULT",
                    "qty": "3",
                    "receipt_date": "2024-08-27",
                    "unit_price": "30.00",
                    "extended_amount": "90.00",
                }
            ],
        }
    )

    async def fake_open_raw_connection() -> FakeCanonicalConnection:
        return connection

    def fail_if_purchase_history_filter_runs(*args, **kwargs):
        raise AssertionError("purchase-history line filter should be skipped")

    monkeypatch.setattr(canonical, "_open_raw_connection", fake_open_raw_connection)
    monkeypatch.setattr(
        canonical,
        "_filter_purchase_lines_by_scope",
        fail_if_purchase_history_filter_runs,
    )

    result = await canonical.run_canonical_import(
        batch_id="batch-scoped-recv-only",
        tenant_id=tenant_id,
        schema_name="raw_legacy",
        selected_domains=["products", "warehouses", "receiving_audit"],
        batch_mode="incremental",
    )

    assert result.supplier_invoice_count == 0
    stock_adjustment_upserts = [
        args for query, args in connection.execute_calls
        if "INSERT INTO stock_adjustment" in query
    ]
    assert len(stock_adjustment_upserts) == 1


@pytest.mark.asyncio
async def test_scoped_import_preserves_deterministic_ids_on_rerun(monkeypatch) -> None:
    """AC4: Same manifest scope produces idempotent results."""
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000001528")
    connection = FakeCanonicalConnection(
        {
            "normalized_parties": [
                {
                    "legacy_code": "C001",
                    "role": "customer",
                    "company_name": "Deterministic Customer",
                    "tax_id": "12345678",
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
            "normalized_warehouses": [],
            "normalized_inventory_prep": [],
            "product_code_mapping": [],
            "sales_headers": [
                {
                    "doc_number": "DETERMINISTIC-001",
                    "invoice_date": "2024-08-26",
                    "customer_code": "C001",
                    "customer_name": "Deterministic Customer",
                    "address": "Taipei",
                    "currency_code": "TWD",
                    "exchange_rate": "1.0",
                    "subtotal": "100.00",
                    "tax_type": "1",
                    "tax_amount": "5.00",
                    "total_amount": "105.00",
                    "remark": "",
                    "created_by": "SYSTEM",
                    "tax_rate": "0.0500",
                }
            ],
            "sales_lines": [
                {
                    "doc_number": "DETERMINISTIC-001",
                    "line_number": 1,
                    "product_code": "P001",
                    "product_name": "Widget",
                    "unit": "pcs",
                    "qty": "2",
                    "unit_price": "50.00",
                    "extended_amount": "100.00",
                    "tax_amount": "5.00",
                }
            ],
            "purchase_headers": [],
            "purchase_lines": [],
        }
    )

    async def fake_open_raw_connection() -> FakeCanonicalConnection:
        return connection

    monkeypatch.setattr(canonical, "_open_raw_connection", fake_open_raw_connection)

    result1 = await canonical.run_canonical_import(
        batch_id="batch-det-001",
        tenant_id=tenant_id,
        schema_name="raw_legacy",
        selected_domains=["customers", "products", "sales_history"],
        entity_scope={"sales": {"closure_keys": [{"document_number": "DETERMINISTIC-001"}]}},
        batch_mode="incremental",
    )

    order_ids_run1 = [
        args[0] for query, args in connection.execute_calls
        if "INSERT INTO orders" in query
    ]

    connection.execute_calls.clear()

    result2 = await canonical.run_canonical_import(
        batch_id="batch-det-002",
        tenant_id=tenant_id,
        schema_name="raw_legacy",
        selected_domains=["customers", "products", "sales_history"],
        entity_scope={"sales": {"closure_keys": [{"document_number": "DETERMINISTIC-001"}]}},
        batch_mode="incremental",
    )

    order_ids_run2 = [
        args[0] for query, args in connection.execute_calls
        if "INSERT INTO orders" in query
    ]

    assert len(order_ids_run1) == 1
    assert len(order_ids_run2) == 1
    assert order_ids_run1[0] == order_ids_run2[0]

    assert result1.order_count == result2.order_count
    assert result1.invoice_count == result2.invoice_count
    assert result1.order_line_count == result2.order_line_count


@pytest.mark.asyncio
async def test_scoped_import_full_batch_mode_processes_all_domains(monkeypatch) -> None:
    """Full batch behavior preserved when batch_mode is not 'incremental'."""
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000001529")
    connection = FakeCanonicalConnection(
        {
            "normalized_parties": [
                {
                    "legacy_code": "C001",
                    "role": "customer",
                    "company_name": "Full Batch Customer",
                    "tax_id": "12345678",
                    "full_address": "Taipei",
                    "address": "Taipei",
                    "phone": "02-1234",
                    "email": "",
                    "contact_person": "Alice",
                    "deterministic_id": deterministic_legacy_uuid("party", "customer", "C001"),
                },
                {
                    "legacy_code": "T067",
                    "role": "supplier",
                    "company_name": "Full Batch Supplier",
                    "tax_id": "22345678",
                    "full_address": "Taoyuan",
                    "address": "Taoyuan",
                    "phone": "03-1234",
                    "email": "",
                    "contact_person": "Betty",
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
            "normalized_inventory_prep": [],
            "product_code_mapping": [],
            "sales_headers": [],
            "sales_lines": [],
            "purchase_headers": [],
            "purchase_lines": [],
        }
    )

    async def fake_open_raw_connection() -> FakeCanonicalConnection:
        return connection

    monkeypatch.setattr(canonical, "_open_raw_connection", fake_open_raw_connection)

    result = await canonical.run_canonical_import(
        batch_id="batch-full-001",
        tenant_id=tenant_id,
        schema_name="raw_legacy",
        selected_domains=["customers"],
        batch_mode=None,
    )

    assert result.customer_count == 1
    assert result.supplier_count == 1
    assert result.product_count >= 1
    assert result.warehouse_count >= 1
    assert len(result.skipped_domains) == 0