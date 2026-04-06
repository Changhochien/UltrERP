from __future__ import annotations

import json
import uuid
from typing import cast

import pytest

import domains.legacy_import.canonical as canonical
import domains.legacy_import.cli as cli
from domains.legacy_import.mapping import UNKNOWN_PRODUCT_CODE
from domains.legacy_import.normalization import deterministic_legacy_uuid


class FakeCanonicalTransaction:
    def __init__(self, connection: "FakeCanonicalConnection") -> None:
        self.connection = connection
        self.buffer: list[tuple[str, tuple[object, ...]]] = []

    async def __aenter__(self) -> "FakeCanonicalTransaction":
        self.connection.transaction_started = True
        self.connection.transaction_buffers.append(self.buffer)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        self.connection.transaction_buffers.pop()
        if exc_type is None:
            self.connection.transaction_committed = True
            if self.connection.transaction_buffers:
                self.connection.transaction_buffers[-1].extend(self.buffer)
            else:
                self.connection.committed_execute_calls.extend(self.buffer)
        else:
            self.connection.transaction_rolled_back = True
        return False


class FakeCanonicalConnection:
    def __init__(self, rows_by_key: dict[str, list[dict[str, object]]]) -> None:
        self.rows_by_key = rows_by_key
        self.execute_calls: list[tuple[str, tuple[object, ...]]] = []
        self.committed_execute_calls: list[tuple[str, tuple[object, ...]]] = []
        self.transaction_buffers: list[list[tuple[str, tuple[object, ...]]]] = []
        self.transaction_started = False
        self.transaction_committed = False
        self.transaction_rolled_back = False
        self.closed = False

    def transaction(self) -> FakeCanonicalTransaction:
        return FakeCanonicalTransaction(self)

    async def fetch(self, query: str, *args: object):
        if 'FROM "raw_legacy".normalized_parties' in query:
            return self.rows_by_key.get("normalized_parties", [])
        if 'FROM "raw_legacy".normalized_products' in query:
            return self.rows_by_key.get("normalized_products", [])
        if 'FROM "raw_legacy".normalized_warehouses' in query:
            return self.rows_by_key.get("normalized_warehouses", [])
        if 'FROM "raw_legacy".normalized_inventory_prep' in query:
            return self.rows_by_key.get("normalized_inventory_prep", [])
        if 'FROM "raw_legacy".product_code_mapping' in query:
            return self.rows_by_key.get("product_code_mapping", [])
        if 'FROM "raw_legacy".tbsslipx' in query:
            return self.rows_by_key.get("sales_headers", [])
        if 'FROM "raw_legacy".tbsslipdtx' in query:
            return self.rows_by_key.get("sales_lines", [])
        if 'FROM "raw_legacy".tbsslipj' in query:
            return self.rows_by_key.get("purchase_headers", [])
        if 'FROM "raw_legacy".tbsslipdtj' in query:
            return self.rows_by_key.get("purchase_lines", [])
        if 'FROM "raw_legacy".tbsprepay' in query:
            rows = self.rows_by_key.get("payment_headers", [])
            if "SELECT *" in query:
                return rows
            return [
                {
                    "source_row_number": row.get("_source_row_number"),
                    "source_identifier": row.get("col_2"),
                }
                for row in rows
            ]
        if 'FROM "raw_legacy".tbsspay' in query:
            rows = self.rows_by_key.get("payment_details", [])
            if "SELECT *" in query:
                return rows
            return [
                {
                    "source_row_number": row.get("_source_row_number"),
                    "source_identifier": row.get("col_2"),
                }
                for row in rows
            ]
        return []

    async def fetchrow(self, query: str, *args: object):
        rows = await self.fetch(query, *args)
        return rows[0] if rows else None

    async def fetchval(self, query: str, *args: object):
        if "MAX(attempt_number)" in query:
            return 0
        if "to_regclass" in query and "tbsslipj" in query:
            return "raw_legacy.tbsslipj" if "purchase_headers" in self.rows_by_key else None
        if "to_regclass" in query and "tbsslipdtj" in query:
            return "raw_legacy.tbsslipdtj" if "purchase_lines" in self.rows_by_key else None
        if "to_regclass" in query and "tbsprepay" in query:
            return "raw_legacy.tbsprepay" if "payment_headers" in self.rows_by_key else None
        if "to_regclass" in query and "tbsspay" in query:
            return "raw_legacy.tbsspay" if "payment_details" in self.rows_by_key else None
        return None

    async def execute(self, query: str, *args: object) -> str:
        call = (query, args)
        self.execute_calls.append(call)
        if self.transaction_buffers:
            self.transaction_buffers[-1].append(call)
        else:
            self.committed_execute_calls.append(call)
        return "OK"

    async def close(self) -> None:
        self.closed = True


def _find_query_index(execute_calls: list[tuple[str, tuple[object, ...]]], needle: str) -> int:
    for index, (query, _) in enumerate(execute_calls):
        if needle in query:
            return index
    raise AssertionError(f"Query not found: {needle}")


def _args_for_queries(
    execute_calls: list[tuple[str, tuple[object, ...]]],
    needle: str,
) -> list[tuple[object, ...]]:
    return [args for query, args in execute_calls if needle in query]


class RawPurchaseHeaderConnection:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = rows
        self.queries: list[str] = []

    async def fetch(self, query: str, *args: object):
        self.queries.append(query)
        return self.rows


@pytest.mark.asyncio
async def test_ensure_canonical_support_tables_create_run_lineage_and_holding_tables() -> None:
    connection = FakeCanonicalConnection({})

    await canonical._ensure_canonical_support_tables(connection, "raw_legacy")

    ddl = "\n".join(query for query, _ in connection.execute_calls)
    assert 'CREATE TABLE IF NOT EXISTS "raw_legacy".canonical_import_runs' in ddl
    assert 'CREATE TABLE IF NOT EXISTS "raw_legacy".canonical_import_step_runs' in ddl
    assert 'CREATE TABLE IF NOT EXISTS "raw_legacy".canonical_record_lineage' in ddl
    assert 'CREATE TABLE IF NOT EXISTS "raw_legacy".unsupported_history_holding' in ddl


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
                    "unit": "pcs",
                    "status": "A",
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
                    "qty": "3",
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

    assert result.customer_count == 1
    assert result.supplier_count == 1
    assert result.product_count == 2
    assert result.warehouse_count == 1
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

    order_line_args = next(
        args for query, args in connection.execute_calls if "INSERT INTO order_lines" in query
    )
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
            "sales_headers": [],
            "sales_lines": [],
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
    assert "INSERT INTO customers" in sql and "ON CONFLICT" in sql
    assert "INSERT INTO product" in sql and "ON CONFLICT" in sql
    assert "INSERT INTO warehouse" in sql and "ON CONFLICT" in sql
    assert "INSERT INTO inventory_stock" in sql and "ON CONFLICT" in sql
    assert 'INSERT INTO "raw_legacy".canonical_record_lineage' in sql and "ON CONFLICT" in sql


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
            "normalized_warehouses": [],
            "normalized_inventory_prep": [],
            "product_code_mapping": [],
            "sales_headers": [],
            "sales_lines": [],
            "purchase_headers": [
                {
                    "doc_number": "1130827001",
                    "invoice_number": "GG46104158",
                    "invoice_date": "2024-08-27",
                    "supplier_code": "T067",
                    "supplier_name": "Supplier A",
                    "address": "Taoyuan",
                    "notes": "SQ04",
                    "subtotal": "90.00",
                    "tax_amount": "5.00",
                    "total_amount": "95.00",
                    "source_row_number": 17,
                }
            ],
            "purchase_lines": [
                {
                    "doc_number": "1130827001",
                    "line_number": 1,
                    "product_code": "P001",
                    "qty": "3",
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
    assert supplier_invoice_args[9] == "SQ04"
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

    with pytest.raises(ValueError, match="missing customer"):
        await canonical.run_canonical_import(
            batch_id="batch-failure-observability",
            tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000413"),
            schema_name="raw_legacy",
        )

    failed_run_args = next(
        args
        for query, args in connection.committed_execute_calls
        if 'INSERT INTO "raw_legacy".canonical_import_runs' in query and args[5] == "failed"
    )
    failure_summary = json.loads(cast(str, failed_run_args[6]))
    assert failure_summary["customer_count"] == 1
    assert failure_summary["warehouse_count"] == 1

    failed_step_args = next(
        args
        for query, args in connection.committed_execute_calls
        if 'INSERT INTO "raw_legacy".canonical_import_step_runs' in query
        and args[1] == "sales_history"
        and args[3] == "failed"
    )
    assert "missing customer" in str(failed_step_args[4] or "").lower()


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
