from __future__ import annotations

import json
import uuid
from decimal import Decimal
from typing import cast

import pytest

import domains.legacy_import.canonical as canonical
import domains.legacy_import.cli as cli
from domains.legacy_import.mapping import UNKNOWN_PRODUCT_CODE
from domains.legacy_import.normalization import deterministic_legacy_uuid
from tests.domains.legacy_import.canonical_test_support import (
    FakeCanonicalConnection,
    _args_for_queries,
    _find_query_index,
)


@pytest.mark.asyncio
async def test_run_canonical_import_orders_dependencies_and_holding(
    monkeypatch,
) -> None:
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000401")
    connection = FakeCanonicalConnection(
        {
            "normalized_parties": [
                {
                    "legacy_code": "C001",
                    "role": "customer",
                    "company_name": "Acme Co",
                    "tax_id": "12345675",
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
                    "company_name": "Supplier A",
                    "tax_id": "22345678",
                    "full_address": "Taoyuan",
                    "address": "Taoyuan",
                    "phone": "03-1234",
                    "email": "supplier@example.test",
                    "contact_person": "Betty",
                    "deterministic_id": deterministic_legacy_uuid("party", "supplier", "T067"),
                },
            ],
            "normalized_products": [
                {
                    "legacy_code": "P001",
                    "name": "Widget",
                    "category": "BELT",
                    "legacy_category": "Legacy Belt",
                    "stock_kind": "0",
                    "category_source": "manual_override",
                    "category_rule_id": "manual-override",
                    "category_confidence": "1.00",
                    "unit": "pcs",
                    "status": "A",
                    "source_table": "tbsstock",
                    "source_row_number": 12,
                    "deterministic_id": deterministic_legacy_uuid("product", "P001"),
                },
                {
                    "legacy_code": UNKNOWN_PRODUCT_CODE,
                    "name": "Unknown Product",
                    "category": None,
                    "unit": "unknown",
                    "status": "placeholder",
                    "deterministic_id": deterministic_legacy_uuid("product", UNKNOWN_PRODUCT_CODE),
                },
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
            "product_code_mapping": [
                {
                    "legacy_code": "RB052-6",
                    "target_code": UNKNOWN_PRODUCT_CODE,
                    "resolution_type": "unknown",
                }
            ],
            "sales_headers": [
                {
                    "doc_number": "1130826001",
                    "invoice_date": "2024-08-26",
                    "customer_code": "C001",
                    "customer_name": "Acme Co",
                    "address": "Taipei",
                    "currency_code": "TWD",
                    "exchange_rate": "1.0",
                    "subtotal": "100.00",
                    "tax_type": "1",
                    "tax_amount": "5.00",
                    "total_amount": "105.00",
                    "remark": "legacy note",
                    "created_by": "SYSTEM",
                    "tax_rate": "0.0500",
                }
            ],
            "sales_lines": [
                {
                    "doc_number": "1130826001",
                    "line_number": 1,
                    "product_code": "RB052-6",
                    "product_name": "Variant belt",
                    "product_category": "Legacy Belt",
                    "unit": "pcs",
                    "qty": "2",
                    "unit_price": "50.00",
                    "extended_amount": "100.00",
                    "tax_amount": "5.00",
                }
            ],
            "purchase_headers": [
                {
                    "doc_number": "1130827001",
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
                    "doc_number": "1130827001",
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

    monkeypatch.setattr(canonical, "_open_raw_connection", fake_open_raw_connection)

    result = await canonical.run_canonical_import(
        batch_id="batch-004",
        tenant_id=tenant_id,
        schema_name="raw_legacy",
    )

    normalized_party_fetches = [
        query for query, _ in connection.fetch_queries
        if 'FROM "raw_legacy".normalized_parties' in query
    ]

    assert result.customer_count == 1
    assert result.supplier_count == 1
    assert result.product_count == 2
    assert result.warehouse_count == 1
    assert len(normalized_party_fetches) == 1
    assert result.inventory_count == 1
    assert result.order_count == 1
    assert result.order_line_count == 1
    assert result.invoice_count == 1
    assert result.invoice_line_count == 1
    assert result.supplier_invoice_count == 1
    assert result.supplier_invoice_line_count == 1
    assert result.holding_count == 0
    assert result.lineage_count >= 10
    assert connection.transaction_started is True
    assert connection.transaction_committed is True
    assert connection.transaction_rolled_back is False
    assert connection.closed is True

    assert _find_query_index(connection.execute_calls, "INSERT INTO customers") < _find_query_index(
        connection.execute_calls,
        "INSERT INTO supplier",
    )
    assert _find_query_index(connection.execute_calls, "INSERT INTO supplier") < _find_query_index(
        connection.execute_calls,
        "INSERT INTO category (",
    )
    assert _find_query_index(connection.execute_calls, "INSERT INTO category (") < _find_query_index(
        connection.execute_calls,
        "INSERT INTO category_translation (",
    )
    assert _find_query_index(connection.execute_calls, "INSERT INTO category_translation (") < _find_query_index(
        connection.execute_calls,
        "INSERT INTO product",
    )
    assert _find_query_index(connection.execute_calls, "INSERT INTO product") < _find_query_index(
        connection.execute_calls,
        "INSERT INTO warehouse",
    )
    assert _find_query_index(connection.execute_calls, "INSERT INTO warehouse") < _find_query_index(
        connection.execute_calls,
        "INSERT INTO inventory_stock",
    )
    assert _find_query_index(
        connection.execute_calls, "INSERT INTO inventory_stock"
    ) < _find_query_index(
        connection.execute_calls,
        "INSERT INTO orders",
    )
    assert any("INSERT INTO category (" in query for query, _ in connection.executemany_calls)
    assert any(
        "INSERT INTO category_translation" in query for query, _ in connection.executemany_calls
    )
    assert any("INSERT INTO product" in query for query, _ in connection.executemany_calls)
    assert any("INSERT INTO warehouse" in query for query, _ in connection.executemany_calls)
    assert any("INSERT INTO inventory_stock" in query for query, _ in connection.executemany_calls)

    order_line_args = next(
        args for query, args in connection.execute_calls if "INSERT INTO order_lines" in query
    )
    order_line_query = next(
        query for query, _ in connection.execute_calls if "INSERT INTO order_lines" in query
    )
    customer_args = next(
        args for query, args in connection.execute_calls if "INSERT INTO customers" in query
    )
    supplier_args = next(
        args for query, args in connection.execute_calls if "INSERT INTO supplier" in query
    )
    product_args = next(
        args for query, args in connection.execute_calls if "INSERT INTO product" in query
    )
    order_query, order_args = next(
        (query, args) for query, args in connection.execute_calls if "INSERT INTO orders" in query
    )
    invoice_args = next(
        args for query, args in connection.execute_calls if "INSERT INTO invoices" in query
    )
    assert customer_args[9] == Decimal("0.0000")
    assert customer_args[11] == "unknown"
    customer_snapshot = json.loads(cast(str, customer_args[12]))
    supplier_snapshot = json.loads(cast(str, supplier_args[6]))
    product_snapshot = json.loads(cast(str, product_args[9]))
    assert order_args[4] == "fulfilled"
    assert "discount_amount" in order_query
    assert "discount_percent" in order_query
    assert "0.00" in order_query
    assert "0.0000" in order_query
    assert invoice_args[10] == "issued"
    order_snapshot = json.loads(cast(str, order_args[9]))
    invoice_snapshot = json.loads(cast(str, invoice_args[11]))
    assert customer_snapshot["legacy_code"] == "C001"
    assert supplier_snapshot["role"] == "supplier"
    assert product_args[5] is not None
    assert product_snapshot["legacy_code"] == "P001"
    assert product_snapshot["legacy_category"] == "Legacy Belt"
    assert product_snapshot["category_source"] == "manual_override"
    assert product_snapshot["category_rule_id"] == "manual-override"
    assert product_snapshot["category_confidence"] == "1.00"
    assert order_snapshot["source_table"] == "tbsslipx"
    assert order_snapshot["legacy_doc_number"] == "1130826001"
    assert invoice_snapshot["customer_code"] == "C001"
    assert order_line_args[15] == "Variant belt"
    assert order_line_args[16] == "Variant belt"
    assert order_line_args[17] == "Legacy Belt"
    assert "EXCLUDED.product_name_snapshot,\n                    )" not in order_line_query
    assert "EXCLUDED.product_category_snapshot,\n                    )" not in order_line_query
    assert (
        canonical._tenant_scoped_uuid(tenant_id, "product", UNKNOWN_PRODUCT_CODE) in order_line_args
    )
    assert any(
        "INSERT INTO supplier_invoices" in query
        for query, _ in connection.execute_calls
    )
    assert any(
        "INSERT INTO supplier_invoice_lines" in query
        for query, _ in connection.execute_calls
    )
    assert any(
        'INSERT INTO "raw_legacy".canonical_record_lineage' in query
        for query, _ in connection.execute_calls
    )
    lineage_args = _args_for_queries(
        connection.execute_calls,
        'INSERT INTO "raw_legacy".canonical_record_lineage',
    )
    assert any(
        args[1] == "batch-004"
        and args[2] == "orders"
        and args[4] == "tbsslipx"
        and args[5] == "1130826001"
        for args in lineage_args
    )
    assert any(
        args[1] == "batch-004"
        and args[2] == "order_lines"
        and args[4] == "tbsslipdtx"
        and args[5] == "1130826001:1"
        for args in lineage_args
    )
    assert any(
        args[1] == "batch-004"
        and args[2] == "supplier_invoices"
        and args[4] == "tbsslipj"
        and args[5] == "1130827001"
        for args in lineage_args
    )
    assert any(
        args[1] == "batch-004"
        and args[2] == "supplier_invoice_lines"
        and args[4] == "tbsslipdtj"
        and args[5] == "1130827001:1"
        for args in lineage_args
    )


@pytest.mark.asyncio
async def test_run_canonical_import_preadjusted_pricing_uses_original_list_price(
    monkeypatch,
) -> None:
    """When foldprice was pre-adjusted to the discounted price, sexp1/sexp2 hold the
    original list price and discount ratio. The import must use sexp1 as the true
    list price so discount_amount = sexp1 - unit_price > 0."""
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000420")
    connection = FakeCanonicalConnection(
        {
            "normalized_parties": [
                {
                    "legacy_code": "C001",
                    "role": "customer",
                    "company_name": "Discount Test Co",
                    "tax_id": "12345675",
                    "full_address": "Taipei",
                    "address": "Taipei",
                    "phone": "02-1234",
                    "email": "",
                    "contact_person": "Bob",
                    "deterministic_id": deterministic_legacy_uuid("party", "customer", "C001"),
                }
            ],
            "normalized_products": [
                {
                    "legacy_code": "PC096",
                    "name": "三角皮帶 C-96",
                    "category": "BELT",
                    "unit": "條",
                    "status": "A",
                    "deterministic_id": deterministic_legacy_uuid("product", "PC096"),
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
            "sales_headers": [
                {
                    "doc_number": "1140610009",
                    "invoice_date": "2025-06-10",
                    "customer_code": "C001",
                    "customer_name": "Discount Test Co",
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
            # Line 1: foldprice pre-adjusted to 254.0 (= unit_price after discount).
            # sexp1=506.9, sexp2=0.5011 indicate the original list was 506.9 with ~50% disc.
            # Expected: list_unit_price=506.9, unit_price=254.0, discount_amount=252.90
            "sales_lines": [
                {
                    "doc_number": "1140610009",
                    "line_number": 1,
                    "product_code": "PC096",
                    "product_name": "三角皮帶 C-96",
                    "unit": "條",
                    "qty": "6",
                    "list_unit_price": "254.00000000",
                    "unit_price": "254.00000000",
                    "extended_amount": "1524.00000000",
                    "original_list_price": "506.9",
                    "original_discount_ratio": "0.5011",
                    "tax_amount": "126.72",
                    "line_tax_amount": "126.72",
                }
            ],
            "purchase_headers": [],
            "purchase_lines": [],
        }
    )

    async def fake_open_raw_connection() -> FakeCanonicalConnection:
        return connection

    monkeypatch.setattr(canonical, "_open_raw_connection", fake_open_raw_connection)

    result = await canonical.run_canonical_import(
        batch_id="batch-discount-fix",
        tenant_id=tenant_id,
        schema_name="raw_legacy",
    )

    assert result.order_count == 1
    assert result.order_line_count == 1

    order_line_args = next(
        args
        for query, args in connection.execute_calls
        if "INSERT INTO order_lines" in query
    )
    # Position 6 = actual_list_price, 7 = unit_price, 8 = discount_amount
    from decimal import Decimal
    assert order_line_args[6] == Decimal("506.9")
    assert order_line_args[7] == Decimal("254.0")
    assert order_line_args[8] == Decimal("252.90")


@pytest.mark.asyncio
async def test_run_canonical_import_stamps_normalized_product_snapshots(monkeypatch) -> None:
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000421")
    connection = FakeCanonicalConnection(
        {
            "normalized_parties": [
                {
                    "legacy_code": "C001",
                    "role": "customer",
                    "company_name": "Snapshot Co",
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
                    "name": "Master Widget",
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
                    "doc_number": "1130826002",
                    "invoice_date": "2024-08-26",
                    "customer_code": "C001",
                    "customer_name": "Snapshot Co",
                    "address": "Taipei",
                    "currency_code": "TWD",
                    "exchange_rate": "1.0",
                    "subtotal": "100.00",
                    "tax_type": "1",
                    "tax_amount": "5.00",
                    "total_amount": "105.00",
                    "remark": "snapshot",
                    "created_by": "SYSTEM",
                    "tax_rate": "0.0500",
                }
            ],
            "sales_lines": [
                {
                    "doc_number": "1130826002",
                    "line_number": 1,
                    "product_code": "P001",
                    "product_name": "Invoice line widget",
                    "unit": "pcs",
                    "qty": "2",
                    "unit_price": "50.00",
                    "extended_amount": "100.00",
                    "tax_amount": "5.00",
                    "line_tax_amount": "5.00",
                    "available_stock_snapshot": 7,
                }
            ],
            "purchase_headers": [],
            "purchase_lines": [],
        }
    )

    async def fake_open_raw_connection() -> FakeCanonicalConnection:
        return connection

    monkeypatch.setattr(canonical, "_open_raw_connection", fake_open_raw_connection)

    result = await canonical.run_canonical_import(
        batch_id="batch-snapshot",
        tenant_id=tenant_id,
        schema_name="raw_legacy",
    )

    assert result.order_line_count == 1

    order_line_args = next(
        args for query, args in connection.execute_calls if "INSERT INTO order_lines" in query
    )
    assert order_line_args[15] == "Invoice line widget"
    assert order_line_args[16] == "Master Widget"
    assert order_line_args[17] == "BELT"


@pytest.mark.asyncio
async def test_run_canonical_import_uses_tenant_scoped_live_ids(monkeypatch) -> None:
    normalized_customer_id = deterministic_legacy_uuid("party", "customer", "C001")

    async def run_for_tenant(tenant_id: uuid.UUID) -> tuple[FakeCanonicalConnection, uuid.UUID]:
        connection = FakeCanonicalConnection(
            {
                "normalized_parties": [
                    {
                        "legacy_code": "C001",
                        "role": "customer",
                        "company_name": "Tenant Scoped Co",
                        "tax_id": "12345675",
                        "full_address": "Taipei",
                        "address": "Taipei",
                        "phone": "02-1234",
                        "email": "",
                        "contact_person": "Alice",
                        "deterministic_id": normalized_customer_id,
                    }
                ],
                "normalized_products": [],
                "normalized_warehouses": [],
                "normalized_inventory_prep": [],
                "product_code_mapping": [],
                "sales_headers": [],
                "sales_lines": [],
            }
        )

        async def fake_open_raw_connection() -> FakeCanonicalConnection:
            return connection

        monkeypatch.setattr(canonical, "_open_raw_connection", fake_open_raw_connection)
        await canonical.run_canonical_import(
            batch_id="batch-tenant-scope",
            tenant_id=tenant_id,
            schema_name="raw_legacy",
        )
        customer_args = next(
            args for query, args in connection.execute_calls if "INSERT INTO customers" in query
        )
        return connection, cast(uuid.UUID, customer_args[0])

    _, tenant_a_customer_id = await run_for_tenant(
        uuid.UUID("00000000-0000-0000-0000-000000000410")
    )
    _, tenant_b_customer_id = await run_for_tenant(
        uuid.UUID("00000000-0000-0000-0000-000000000411")
    )

    assert tenant_a_customer_id != normalized_customer_id
    assert tenant_b_customer_id != normalized_customer_id
    assert tenant_a_customer_id != tenant_b_customer_id


@pytest.mark.asyncio
async def test_run_canonical_import_preserves_full_payment_holding_payload(
    monkeypatch,
) -> None:
    connection = FakeCanonicalConnection(
        {
            "normalized_parties": [],
            "normalized_products": [],
            "normalized_warehouses": [],
            "normalized_inventory_prep": [],
            "product_code_mapping": [],
            "sales_headers": [],
            "sales_lines": [],
            "payment_headers": [
                {
                    "_source_row_number": 11,
                    "col_2": "PAY-001",
                    "col_5": "Legacy memo",
                    "col_8": "123.45",
                }
            ],
        }
    )

    async def fake_open_raw_connection() -> FakeCanonicalConnection:
        return connection

    monkeypatch.setattr(canonical, "_open_raw_connection", fake_open_raw_connection)

    result = await canonical.run_canonical_import(
        batch_id="batch-payment-holding",
        tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000412"),
        schema_name="raw_legacy",
    )

    assert result.holding_count == 1
    holding_args = next(
        args
        for query, args in connection.execute_calls
        if 'INSERT INTO "raw_legacy".unsupported_history_holding' in query
        and args[3] == "payment_history"
        and args[4] == "tbsprepay"
    )
    payload = json.loads(cast(str, holding_args[7]))
    assert payload["col_2"] == "PAY-001"
    assert payload["col_5"] == "Legacy memo"
    assert payload["col_8"] == "123.45"


@pytest.mark.asyncio
async def test_run_canonical_import_imports_purchase_history_into_supplier_invoices(
    monkeypatch,
) -> None:
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000414")
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
                    "code": "LEGACY_DEFAULT",
                    "name": "Legacy Default Warehouse",
                    "location": None,
                    "address": None,
                    "source_table": "tbsstkhouse",
                    "source_row_number": 31,
                    "deterministic_id": deterministic_legacy_uuid("warehouse", "LEGACY_DEFAULT"),
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
                    "warehouse_code": "LEGACY_DEFAULT",
                    "qty": "3",
                    "receipt_date": "2024-08-27",
                    "unit_price": "30.00",
                    "extended_amount": "90.00",
                    "source_row_number": 18,
                }
            ],
        }
    )

    async def fake_open_raw_connection() -> FakeCanonicalConnection:
        return connection

    monkeypatch.setattr(canonical, "_open_raw_connection", fake_open_raw_connection)

    result = await canonical.run_canonical_import(
        batch_id="batch-purchase-ap",
        tenant_id=tenant_id,
        schema_name="raw_legacy",
    )

    assert result.holding_count == 0
    assert any("INSERT INTO supplier" in query for query, _ in connection.execute_calls)
    assert any("INSERT INTO supplier_invoices" in query for query, _ in connection.execute_calls)
    supplier_invoice_args = next(
        args for query, args in connection.execute_calls if "INSERT INTO supplier_invoices" in query
    )
    assert supplier_invoice_args[3] == "GG46104158"
    assert str(supplier_invoice_args[8]) == "95.00"
    assert str(supplier_invoice_args[9]) == "95.00"
    assert str(supplier_invoice_args[18]) == "95.00"
    assert supplier_invoice_args[19] == "open"
    assert supplier_invoice_args[20] == "SQ04"
    supplier_snapshot = json.loads(cast(str, supplier_invoice_args[21]))
    assert supplier_snapshot["source_table"] == "tbsslipj"
    assert supplier_snapshot["must_pay_amount"] == "95.00"
    assert supplier_snapshot["invoice_number_source"] == "legacy_invoice_number"
    assert any(
        "INSERT INTO supplier_invoice_lines" in query for query, _ in connection.execute_calls
    )
    assert not any(
        'INSERT INTO "raw_legacy".unsupported_history_holding' in query and "tbsslipj" in args
        for query, args in connection.execute_calls
    )
    assert not any(
        'INSERT INTO "raw_legacy".unsupported_history_holding' in query and "tbsslipdtj" in args
        for query, args in connection.execute_calls
    )


@pytest.mark.asyncio
async def test_run_canonical_import_uses_purchase_line_total_when_header_total_is_zero(
    monkeypatch,
) -> None:
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000415")
    connection = FakeCanonicalConnection(
        {
            "normalized_parties": [
                {
                    "legacy_code": "T001",
                    "role": "supplier",
                    "company_name": "Supplier Zero Header",
                    "tax_id": "12345678",
                    "full_address": "Taipei",
                    "address": "Taipei",
                    "phone": "02-1111",
                    "email": "",
                    "contact_person": "Zero",
                    "source_table": "tbscust",
                    "source_row_number": 1,
                    "deterministic_id": deterministic_legacy_uuid("party", "supplier", "T001"),
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
                    "code": "LEGACY_DEFAULT",
                    "name": "Legacy Default Warehouse",
                    "location": None,
                    "address": None,
                    "source_table": "tbsstkhouse",
                    "source_row_number": 31,
                    "deterministic_id": deterministic_legacy_uuid("warehouse", "LEGACY_DEFAULT"),
                }
            ],
            "normalized_inventory_prep": [],
            "product_code_mapping": [],
            "sales_headers": [],
            "sales_lines": [],
            "purchase_headers": [
                {
                    "doc_number": "89052201",
                    "invoice_number": "89052201",
                    "slip_date": "2000-05-22",
                    "invoice_date": "2000-05-22",
                    "supplier_code": "T001",
                    "supplier_name": "Supplier Zero Header",
                    "address": "Taipei",
                    "subtotal": "0.00",
                    "tax_amount": "0.00",
                    "must_pay_amount": "0.00",
                    "total_amount": "0.00",
                    "source_row_number": 21,
                }
            ],
            "purchase_lines": [
                {
                    "doc_number": "89052201",
                    "line_number": 1,
                    "product_code": "P001",
                    "warehouse_code": "LEGACY_DEFAULT",
                    "qty": "1",
                    "receipt_date": "2000-05-22",
                    "unit_price": "12.04",
                    "extended_amount": "12.04",
                    "source_row_number": 22,
                }
            ],
        }
    )

    async def fake_open_raw_connection() -> FakeCanonicalConnection:
        return connection

    monkeypatch.setattr(canonical, "_open_raw_connection", fake_open_raw_connection)

    result = await canonical.run_canonical_import(
        batch_id="batch-purchase-line-fallback",
        tenant_id=tenant_id,
        schema_name="raw_legacy",
    )

    assert result.holding_count == 0
    supplier_invoice_args = next(
        args for query, args in connection.execute_calls if "INSERT INTO supplier_invoices" in query
    )
    assert supplier_invoice_args[3] == "89052201"
    assert str(supplier_invoice_args[8]) == "12.04"
    assert str(supplier_invoice_args[9]) == "0.00"
    assert str(supplier_invoice_args[17]) == "12.04"
    assert supplier_invoice_args[19] == "paid"


@pytest.mark.asyncio
async def test_run_canonical_import_persists_failed_run_and_step_records(
    monkeypatch,
) -> None:
    connection = FakeCanonicalConnection(
        {
            "normalized_parties": [
                {
                    "legacy_code": "C001",
                    "role": "customer",
                    "company_name": "Failure Probe Co",
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
            "normalized_inventory_prep": [],
            "product_code_mapping": [],
            "sales_headers": [
                {
                    "doc_number": "1130826999",
                    "invoice_date": "2024-08-26",
                    "customer_code": "MISSING",
                    "customer_name": "Missing Customer",
                    "address": "Taipei",
                    "currency_code": "TWD",
                    "exchange_rate": "1.0",
                    "subtotal": "100.00",
                    "tax_type": "1",
                    "tax_amount": "5.00",
                    "total_amount": "105.00",
                    "remark": "legacy note",
                    "created_by": "SYSTEM",
                    "tax_rate": "0.0500",
                    "source_row_number": 99,
                }
            ],
            "sales_lines": [],
        }
    )

    async def fake_open_raw_connection() -> FakeCanonicalConnection:
        return connection

    monkeypatch.setattr(canonical, "_open_raw_connection", fake_open_raw_connection)

    # Missing customer is now skipped silently instead of raising
    result = await canonical.run_canonical_import(
        batch_id="batch-failure-observability",
        tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000413"),
        schema_name="raw_legacy",
    )
    assert result.batch_id == "batch-failure-observability"
    assert result.customer_count == 1

    # Verify customer and warehouse were still imported
    customer_args = next(
        args for query, args in connection.execute_calls if "INSERT INTO customers" in query
    )
    assert customer_args[2] == "Failure Probe Co"

    # Verify no sales order was inserted (customer_code "MISSING" not found)
    assert not any(
        "INSERT INTO sales_orders" in query for query, _ in connection.execute_calls
    )

    # Verify no holding record was created for the skipped order (skip-only, no hold)
    holding_calls = [
        (query, args)
        for query, args in connection.execute_calls
        if 'INSERT INTO "raw_legacy".unsupported_history_holding' in query
    ]
    assert len(holding_calls) == 0


def test_canonical_import_cli_invokes_service(monkeypatch, capsys) -> None:
    async def fake_run_canonical_import(**kwargs):
        assert kwargs["batch_id"] == "batch-004"
        return canonical.CanonicalImportResult(
            batch_id="batch-004",
            schema_name="raw_legacy",
            attempt_number=3,
            customer_count=1,
            product_count=2,
            warehouse_count=1,
            inventory_count=1,
            order_count=1,
            order_line_count=1,
            invoice_count=1,
            invoice_line_count=1,
            holding_count=2,
            lineage_count=8,
        )

    monkeypatch.setattr(cli, "run_canonical_import", fake_run_canonical_import, raising=False)

    result = cli.main(["canonical-import", "--batch-id", "batch-004"])
    output = capsys.readouterr().out

    assert result == 0
    assert "Canonical imported batch batch-004" in output
    assert "attempt=3" in output
    assert "orders=1" in output
    assert "holding=2" in output
