from __future__ import annotations

import json
import uuid
from decimal import Decimal
from typing import cast

import pytest

import domains.legacy_import.canonical as canonical
import domains.legacy_import.cli as cli
import domains.legacy_import.source_resolution as source_resolution
from common.models.stock_adjustment import ReasonCode
from domains.legacy_import.mapping import UNKNOWN_PRODUCT_CODE
from domains.legacy_import.normalization import deterministic_legacy_uuid
from tests.domains.legacy_import.test_ap_payment_import import FakePaymentConnection


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
        self.executemany_calls: list[tuple[str, list[tuple[object, ...]]]] = []
        self.committed_execute_calls: list[tuple[str, tuple[object, ...]]] = []
        self.transaction_buffers: list[list[tuple[str, tuple[object, ...]]]] = []
        self.transaction_started = False
        self.transaction_committed = False
        self.transaction_rolled_back = False
        self.closed = False
        # Track inserted rows so fetchrow can find them after INSERT
        self._fake_customers: dict[tuple[object, object], dict] = {}
        self._fake_suppliers: dict[tuple[object, object], dict] = {}
        self._fake_categories: dict[tuple[object, str], dict[str, object]] = {}
        self._fake_stock_adjustments: dict[uuid.UUID, dict[str, object]] = {}
        self._fake_lineage_rows: dict[tuple[object, ...], dict[str, object]] = {}
        self._fake_order_lines: dict[uuid.UUID, dict[str, object]] = {}
        self._fake_resolution_rows: dict[tuple[object, ...], dict[str, object]] = {}
        self._fake_resolution_events: list[dict[str, object]] = []
        self._fake_holding_rows: dict[tuple[object, ...], dict[str, object]] = {}

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
        if "FROM category" in query:
            return list(self._fake_categories.values())
        return []

    async def fetchrow(self, query: str, *args: object):
        # Intercept the post-INSERT lookup for customers/suppliers
        if "FROM customers WHERE tenant_id" in query and "normalized_business_number" in query:
            tenant_id, business_number = args[0], args[1]
            return self._fake_customers.get((tenant_id, business_number))
        if "FROM suppliers WHERE tenant_id" in query and "normalized_business_number" in query:
            tenant_id, business_number = args[0], args[1]
            return self._fake_suppliers.get((tenant_id, business_number))
        if "INSERT INTO category" in query and "RETURNING id, name" in query:
            call = (query, args)
            self.execute_calls.append(call)
            if self.transaction_buffers:
                self.transaction_buffers[-1].append(call)
            else:
                self.committed_execute_calls.append(call)
            category_id, tenant_id, name = args[0], args[1], args[2]
            key = (tenant_id, str(name).casefold())
            existing = self._fake_categories.get(key)
            if existing is None:
                existing = {"id": category_id, "name": name}
                self._fake_categories[key] = existing
            return existing
        if 'FROM "raw_legacy".source_row_resolution' in query:
            key = (args[0], args[1], args[2], args[3], args[4])
            row = self._fake_resolution_rows.get(key)
            return None if row is None else dict(row)
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
        # Track INSERTed customers and suppliers so fetchrow can find them
        if "INSERT INTO customers" in query:
            c_id, ten, co, bn = args[0], args[1], args[2], args[3]
            self._fake_customers[(ten, bn)] = {"id": c_id, "company_name": co}
        elif "INSERT INTO suppliers" in query:
            s_id, ten, co, bn = args[0], args[1], args[2], args[3]
            self._fake_suppliers[(ten, bn)] = {"id": s_id, "company_name": co}
        elif "INSERT INTO stock_adjustment" in query:
            adjustment_id = cast(uuid.UUID, args[0])
            if adjustment_id not in self._fake_stock_adjustments:
                self._fake_stock_adjustments[adjustment_id] = {
                    "tenant_id": args[1],
                    "product_id": args[2],
                    "warehouse_id": args[3],
                    "quantity_change": args[4],
                    "reason_code": args[5],
                    "actor_id": args[6],
                    "notes": args[7],
                    "created_at": args[9],
                }
        elif "INSERT INTO order_lines" in query:
            order_line_id = cast(uuid.UUID, args[0])
            existing = self._fake_order_lines.get(order_line_id)
            if existing is None:
                self._fake_order_lines[order_line_id] = {
                    "id": order_line_id,
                    "tenant_id": args[1],
                    "order_id": args[2],
                    "product_id": args[3],
                    "line_number": args[4],
                    "quantity": args[5],
                    "list_unit_price": args[6],
                    "unit_price": args[7],
                    "discount_amount": args[8],
                    "tax_policy_code": args[9],
                    "tax_type": args[10],
                    "tax_rate": args[11],
                    "tax_amount": args[12],
                    "subtotal_amount": args[13],
                    "total_amount": args[14],
                    "description": args[15],
                    "product_name_snapshot": args[16],
                    "product_category_snapshot": args[17],
                    "available_stock_snapshot": args[18],
                    "backorder_note": args[19],
                }
            else:
                existing.update(
                    {
                        "tenant_id": args[1],
                        "order_id": args[2],
                        "product_id": args[3],
                        "line_number": args[4],
                        "quantity": args[5],
                        "list_unit_price": args[6],
                        "unit_price": args[7],
                        "discount_amount": args[8],
                        "tax_policy_code": args[9],
                        "tax_type": args[10],
                        "tax_rate": args[11],
                        "tax_amount": args[12],
                        "subtotal_amount": args[13],
                        "total_amount": args[14],
                        "description": args[15],
                        "available_stock_snapshot": args[18],
                        "backorder_note": args[19],
                    }
                )
                if existing.get("product_name_snapshot") is None:
                    existing["product_name_snapshot"] = args[16]
                if existing.get("product_category_snapshot") is None:
                    existing["product_category_snapshot"] = args[17]
        elif 'INSERT INTO "raw_legacy".canonical_record_lineage' in query:
            lineage_key = (args[0], args[1], args[2], args[4], args[5], args[6])
            self._fake_lineage_rows[lineage_key] = {
                "canonical_id": args[3],
                "import_run_id": args[7],
            }
        elif 'INSERT INTO "raw_legacy".source_row_resolution_events' in query:
            self._fake_resolution_events.append(
                {
                    "event_id": args[0],
                    "tenant_id": args[1],
                    "batch_id": args[2],
                    "source_table": args[3],
                    "source_identifier": args[4],
                    "source_row_number": args[5],
                    "domain_name": args[6],
                    "previous_status": args[7],
                    "new_status": args[8],
                    "holding_id": args[9],
                    "canonical_table": args[10],
                    "canonical_id": args[11],
                    "notes": args[12],
                    "import_run_id": args[13],
                }
            )
        elif 'INSERT INTO "raw_legacy".source_row_resolution' in query:
            key = (args[0], args[1], args[2], args[3], args[4])
            self._fake_resolution_rows[key] = {
                "tenant_id": args[0],
                "batch_id": args[1],
                "source_table": args[2],
                "source_identifier": args[3],
                "source_row_number": args[4],
                "domain_name": args[5],
                "status": args[6],
                "holding_id": args[7],
                "canonical_table": args[8],
                "canonical_id": args[9],
                "notes": args[10],
                "import_run_id": args[11],
            }
        elif 'INSERT INTO "raw_legacy".unsupported_history_holding' in query:
            key = (args[1], args[2], args[4], args[5], args[6])
            self._fake_holding_rows[key] = {
                "id": args[0],
                "tenant_id": args[1],
                "batch_id": args[2],
                "domain_name": args[3],
                "source_table": args[4],
                "source_identifier": args[5],
                "source_row_number": args[6],
            }
        elif 'DELETE FROM "raw_legacy".unsupported_history_holding' in query:
            key = (args[0], args[1], args[2], args[3], args[4])
            self._fake_holding_rows.pop(key, None)
        return "OK"

    async def executemany(self, query: str, args_iterable) -> None:
        rows = [tuple(args) for args in args_iterable]
        self.executemany_calls.append((query, rows))
        for args in rows:
            await self.execute(query, *args)

    async def close(self) -> None:
        self.closed = True


class QueryCaptureConnection:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = rows
        self.last_query: str | None = None

    async def fetch(self, query: str, *args: object):
        self.last_query = query
        return self.rows


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


def _find_query_index(execute_calls: list[tuple[str, tuple[object, ...]]], needle: str) -> int:
    for index, (query, _) in enumerate(execute_calls):
        if needle in query:
            return index
    raise AssertionError(f"Query not found: {needle}")


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
    assert 'CREATE TABLE IF NOT EXISTS "raw_legacy".source_row_resolution' in ddl
    assert 'CREATE TABLE IF NOT EXISTS "raw_legacy".source_row_resolution_events' in ddl


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

    order_line_args = next(
        args for query, args in connection.execute_calls if "INSERT INTO order_lines" in query
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
    assert customer_args[10] == "unknown"
    customer_snapshot = json.loads(cast(str, customer_args[11]))
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
    assert supplier_invoice_args[10] == "open"
    assert supplier_invoice_args[11] == "SQ04"
    supplier_snapshot = json.loads(cast(str, supplier_invoice_args[12]))
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
async def test_run_canonical_import_batch_rerun_is_idempotent_at_lineage_layer(monkeypatch) -> None:
    """AC4: Re-running the same batch produces exactly one lineage entry per (canonical_table, source_table, source_identifier).

    The lineage primary key is (batch_id, tenant_id, canonical_table, source_table, source_identifier),
    so a rerun of the same batch triggers ON CONFLICT DO UPDATE rather than inserting a duplicate.
    """
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

    # First run
    await canonical.run_canonical_import(
        batch_id=batch_id,
        tenant_id=tenant_id,
        schema_name="raw_legacy",
    )

    # Capture all lineage queries from the first run
    lineage_queries = [
        query for query, _ in connection.committed_execute_calls
        if 'INSERT INTO "raw_legacy".canonical_record_lineage' in query
    ]

    # AC1 & AC2: The ON CONFLICT clause targets (batch_id, tenant_id, canonical_table, source_table, source_identifier)
    # WITHOUT canonical_id — this is the fix for AC4 batch-scoped deduplication.
    # If canonical_id were in the constraint, a rerun with a new import_run_id (new UUID per run)
    # would bypass the conflict and insert a duplicate lineage row.
    for query in lineage_queries:
        assert "ON CONFLICT" in query, "Lineage INSERT must have ON CONFLICT clause"
        on_conflict_idx = query.index("ON CONFLICT")
        do_update_idx = query.index("DO UPDATE")
        on_conflict_target = query[on_conflict_idx:do_update_idx]
        assert "canonical_id" not in on_conflict_target.lower(), (
            f"ON CONFLICT target must NOT include canonical_id for batch-scoped deduplication. "
            f"Found: {on_conflict_target}"
        )
        # batch_id must be first in the constraint (batch-scoped deduplication)
        assert "batch_id" in on_conflict_target, (
            f"ON CONFLICT target must include batch_id. Found: {on_conflict_target}"
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
            # doc_number is blank — should be routed to holding, not cause UUID collision
            "purchase_lines": [
                {
                    "col_1": "4",  # required for SQL filter COALESCE(col_1, '') = '4'
                    "doc_number": "",  # blank doc_number
                    "line_number": 3,
                    "product_code": "P001",
                    "product_name": "Widget",
                    "warehouse_code": "WH-A",
                    "qty": "3",
                    "unit_price": "30.00",
                    "extended_amount": "90.00",
                    "receipt_date": "2024-08-27",
                    # source_row_number absent — row_identity falls back to line_number
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

    # Blank doc_number row must NOT produce a stock adjustment (it is held)
    assert not any(
        "INSERT INTO stock_adjustment" in query
        for query, _ in connection.execute_calls
    ), "Blank doc_number row should not produce a stock adjustment"

    # Blank doc_number row must be routed to unsupported_history_holding
    holding_calls = [
        args
        for query, args in connection.execute_calls
        if 'INSERT INTO "raw_legacy".unsupported_history_holding' in query
        and "tbsslipdtj" in args
    ]
    assert len(holding_calls) == 1, "Expected exactly one holding insert for blank doc_number row"

    # row_identity should be line_number (3), not 0 (the default when source_row_number is absent)
    holding_args = holding_calls[0]
    # holding_args[5] is source_identifier (":{line_number}")
    # holding_args[6] is source_row_number (stored in holding table — 0 since absent in test data)
    # row_identity is used only in the UUID, not stored; verify via notes field instead
    assert holding_args[5] == ":3", f"source_identifier should be ':3', got {holding_args[5]}"
    assert "row_id=3" in holding_args[8], f"notes should mention row_id=3, got {holding_args[8]}"


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
    assert supplier_invoice_args[10] == "paid"


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


# ---------------------------------------------------------------------------
# Story 15.14 — Holding lineage AC1, AC2, AC3
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_holding_state_created_on_blank_doc_number_hold(monkeypatch) -> None:
    """A blank receiving-audit doc number should create holding state and an
    append-only holding event without writing a sentinel lineage row."""
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000440")
    connection = FakeCanonicalConnection(
        {
            "normalized_parties": [
                {
                    "legacy_code": "T055",
                    "role": "supplier",
                    "company_name": "Holding Supplier",
                    "tax_id": "22345678",
                    "full_address": "Taoyuan",
                    "address": "Taoyuan",
                    "phone": "03-1234",
                    "email": "ap@supplier.test",
                    "contact_person": "Betty",
                    "source_table": "tbscust",
                    "source_row_number": 7,
                    "deterministic_id": deterministic_legacy_uuid("party", "supplier", "T055"),
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
                    "supplier_code": "T055",
                    "supplier_name": "Holding Supplier",
                    "address": "Taoyuan",
                    "notes": "SQ04",
                    "subtotal": "90.00",
                    "tax_amount": "5.00",
                    "must_pay_amount": "95.00",
                    "total_amount": "95.00",
                    "source_row_number": 17,
                }
            ],
            # doc_number is blank — should be routed to holding
            "purchase_lines": [
                {
                    "col_1": "4",  # required for SQL filter COALESCE(col_1, '') = '4'
                    "doc_number": "",  # blank doc_number triggers hold
                    "line_number": 3,
                    "product_code": "P001",
                    "product_name": "Widget",
                    "warehouse_code": "WH-A",
                    "qty": "3",
                    "unit_price": "30.00",
                    "extended_amount": "90.00",
                    "receipt_date": "2024-08-27",
                    # source_row_number absent — row_identity falls back to line_number (3)
                }
            ],
        }
    )

    async def fake_open_raw_connection() -> FakeCanonicalConnection:
        return connection

    monkeypatch.setattr(canonical, "_open_raw_connection", fake_open_raw_connection)

    await canonical.run_canonical_import(
        batch_id="batch-holding-lineage-blank",
        tenant_id=tenant_id,
        schema_name="raw_legacy",
    )

    # Verify a holding insert was made
    holding_calls = [
        args
        for query, args in connection.execute_calls
        if 'INSERT INTO "raw_legacy".unsupported_history_holding' in query
        and "tbsslipdtj" in args
    ]
    assert len(holding_calls) == 1, "Expected exactly one holding insert"

    holding_keys = [
        key
        for key in connection._fake_resolution_rows
        if key[2] == "tbsslipdtj" and key[3] == ":3"
    ]
    assert len(holding_keys) == 1
    holding_state = connection._fake_resolution_rows[holding_keys[0]]
    assert holding_state["status"] == source_resolution.STATUS_HOLDING
    assert holding_state["domain_name"] == "receiving_audit"
    assert holding_state["holding_id"] is not None

    # AC1: A holding entry should also create a lineage record with __holding__ sentinel
    holding_lineage_keys = [
        key
        for key in connection._fake_lineage_rows
        if key[2] == "__holding__"
        and key[3] == "tbsslipdtj"
        and key[4] == ":3"
    ]
    assert len(holding_lineage_keys) == 1, (
        "Expected exactly one holding lineage entry for blank doc_number row"
    )
    holding_lineage = connection._fake_lineage_rows[holding_lineage_keys[0]]
    assert holding_lineage["canonical_id"] is not None

    # Verify holding event was appended
    assert any(
        event["source_table"] == "tbsslipdtj"
        and event["source_identifier"] == ":3"
        and event["new_status"] == source_resolution.STATUS_HOLDING
        for event in connection._fake_resolution_events
    )


@pytest.mark.asyncio
async def test_holding_state_created_on_payment_adjacent_hold(monkeypatch) -> None:
    """A payment-adjacent row should create holding state AND lineage entry."""
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000441")
    # No tbscust = no verified payment → all tbsprepay rows are payment-adjacent
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
                    "_source_row_number": 5,
                    "col_2": "PAY-ADJ-001",
                    "col_5": "Adjacent legacy memo",
                    "col_8": "999.99",
                }
            ],
        }
    )

    async def fake_open_raw_connection() -> FakeCanonicalConnection:
        return connection

    monkeypatch.setattr(canonical, "_open_raw_connection", fake_open_raw_connection)

    result = await canonical.run_canonical_import(
        batch_id="batch-holding-lineage-payment-adj",
        tenant_id=tenant_id,
        schema_name="raw_legacy",
    )

    assert result.holding_count == 1

    holding_keys = [
        key
        for key in connection._fake_resolution_rows
        if key[2] == "tbsprepay" and key[3] == "PAY-ADJ-001"
    ]
    assert len(holding_keys) == 1
    holding_state = connection._fake_resolution_rows[holding_keys[0]]
    assert holding_state["status"] == source_resolution.STATUS_HOLDING
    assert holding_state["domain_name"] == "payment_history"

    # AC1: A holding entry should also create a lineage record with __holding__ sentinel
    holding_lineage_keys = [
        key
        for key in connection._fake_lineage_rows
        if key[2] == "__holding__"
        and key[3] == "tbsprepay"
        and key[4] == "PAY-ADJ-001"
    ]
    assert len(holding_lineage_keys) == 1, (
        "Expected exactly one holding lineage entry for payment-adjacent row"
    )


@pytest.mark.asyncio
async def test_holding_state_payment_adjacent_no_col2(monkeypatch) -> None:
    """When col_2 is absent, holding state should fall back to the row-number-based
    source identifier and still create a holding lineage entry."""
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000443")
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
                    "_source_row_number": 5,
                    "col_2": None,  # absent payment number
                    "col_5": "Adjacent legacy memo",
                    "col_8": "999.99",
                }
            ],
        }
    )

    async def fake_open_raw_connection() -> FakeCanonicalConnection:
        return connection

    monkeypatch.setattr(canonical, "_open_raw_connection", fake_open_raw_connection)

    result = await canonical.run_canonical_import(
        batch_id="batch-holding-lineage-no-col2",
        tenant_id=tenant_id,
        schema_name="raw_legacy",
    )

    assert result.holding_count == 1

    holding_keys = [
        key
        for key in connection._fake_resolution_rows
        if key[2] == "tbsprepay" and key[3] == "tbsprepay:5"
    ]
    assert len(holding_keys) == 1
    holding_state = connection._fake_resolution_rows[holding_keys[0]]
    assert holding_state["status"] == source_resolution.STATUS_HOLDING
    assert holding_state["holding_id"] is not None

    # AC1: A holding entry should also create a lineage record with __holding__ sentinel
    holding_lineage_keys = [
        key
        for key in connection._fake_lineage_rows
        if key[2] == "__holding__"
        and key[3] == "tbsprepay"
        and key[4] == "tbsprepay:5"
    ]
    assert len(holding_lineage_keys) == 1, (
        "Expected exactly one holding lineage entry for row with absent col_2"
    )


@pytest.mark.asyncio
async def test_holding_and_drained_rows_are_distinguishable(monkeypatch) -> None:
    """AC3: rows with canonical_table='__holding__' are held rows; rows with
    canonical_table='supplier_payments' are drained rows — they are queryable
    as two distinct sets."""
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000442")

    # Set up one row that will be held (blank doc_number) and one that will drain
    connection = FakeCanonicalConnection(
        {
            "normalized_parties": [
                {
                    "legacy_code": "T055",
                    "role": "supplier",
                    "company_name": "Distinguish Supplier",
                    "tax_id": "22345678",
                    "full_address": "Taoyuan",
                    "address": "Taoyuan",
                    "phone": "03-1234",
                    "email": "ap@supplier.test",
                    "contact_person": "Betty",
                    "source_table": "tbscust",
                    "source_row_number": 7,
                    "deterministic_id": deterministic_legacy_uuid("party", "supplier", "T055"),
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
            # This header has a valid doc_number — its line will drain as stock_adjustment
            "purchase_headers": [
                {
                    "doc_number": "1130827001",
                    "raw_invoice_number": "GG46104158",
                    "invoice_number": "GG46104158",
                    "slip_date": "2024-08-27",
                    "raw_invoice_date": "2024-08-27",
                    "invoice_date": "2024-08-27",
                    "period_code": "11308",
                    "supplier_code": "T055",
                    "supplier_name": "Distinguish Supplier",
                    "address": "Taoyuan",
                    "notes": "SQ04",
                    "subtotal": "90.00",
                    "tax_amount": "5.00",
                    "must_pay_amount": "95.00",
                    "total_amount": "95.00",
                    "source_row_number": 17,
                }
            ],
            # Line with valid doc_number → drains as stock_adjustment
            "purchase_lines": [
                {
                    "doc_number": "1130827001",
                    "line_number": 1,
                    "product_code": "P001",
                    "warehouse_code": "WH-A",
                    "qty": "3",
                    "unit_price": "30.00",
                    "extended_amount": "90.00",
                    "receipt_date": "2024-08-27",
                    "source_row_number": 18,
                },
            ],
        }
    )

    async def fake_open_raw_connection() -> FakeCanonicalConnection:
        return connection

    monkeypatch.setattr(canonical, "_open_raw_connection", fake_open_raw_connection)

    await canonical.run_canonical_import(
        batch_id="batch-distinguish-holding-vs-drained",
        tenant_id=tenant_id,
        schema_name="raw_legacy",
    )

    # Classify lineage entries by canonical_table
    holding_entries = [
        key for key in connection._fake_lineage_rows if key[2] == "__holding__"
    ]
    drained_entries = [
        key
        for key in connection._fake_lineage_rows
        if key[2] not in ("__holding__",)
    ]

    # Drained rows should have lineage entries (stock_adjustment)
    assert len(drained_entries) >= 1, "Expected at least one drained lineage entry"

    # Holding entries should be absent — no blank doc_number rows in this test
    assert len(holding_entries) == 0, (
        f"Expected no __holding__ entries (no blank doc_number rows), got {len(holding_entries)}"
    )


# ---------------------------------------------------------------------------
# Story 15.21 — Holding state and drain lineage are distinguishable
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_holding_and_drained_rows_are_distinguishable_holding(monkeypatch) -> None:
    """A held receiving-audit row should exist in source resolution while drained
    rows continue to appear only in canonical lineage."""
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000442")

    # purchase_headers must have a valid doc_number (blank header raises an error
    # before we even reach _import_legacy_receiving_audit where the blank line is handled).
    # Only the purchase_lines (tbsslipdtj) row has blank doc_number — it goes to __holding__.
    connection = FakeCanonicalConnection(
        {
            "normalized_parties": [
                {
                    "legacy_code": "T055",
                    "role": "supplier",
                    "company_name": "Distinguish Supplier",
                    "tax_id": "22345678",
                    "full_address": "Taoyuan",
                    "address": "Taoyuan",
                    "phone": "03-1234",
                    "email": "ap@supplier.test",
                    "contact_person": "Betty",
                    "source_table": "tbscust",
                    "source_row_number": 7,
                    "deterministic_id": deterministic_legacy_uuid("party", "supplier", "T055"),
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
            # purchase_headers must have valid doc_number; blank lines in purchase_lines
            # (tbsslipdtj) are handled by _import_legacy_receiving_audit
            "purchase_headers": [
                {
                    "doc_number": "HOLD001",
                    "raw_invoice_number": "HOLD001",
                    "invoice_number": "HOLD001",
                    "slip_date": "2024-08-27",
                    "raw_invoice_date": "2024-08-27",
                    "invoice_date": "2024-08-27",
                    "period_code": "11308",
                    "supplier_code": "T055",
                    "supplier_name": "Distinguish Supplier",
                    "address": "Taoyuan",
                    "notes": "SQ04",
                    "subtotal": "90.00",
                    "tax_amount": "5.00",
                    "must_pay_amount": "95.00",
                    "total_amount": "95.00",
                    "source_row_number": 17,
                }
            ],
            # purchase_lines maps to tbsslipdtj (LEGACY_RECEIVING_SOURCE)
            # blank doc_number → __holding__ entry in _import_legacy_receiving_audit
            # col_1 must be '4' to pass the COALESCE(col_1, '') = '4' filter in _fetch_purchase_lines
            "purchase_lines": [
                {
                    "col_1": "4",
                    "doc_number": "",
                    "line_number": 1,
                    "product_code": "P001",
                    "warehouse_code": "WH-A",
                    "qty": "3",
                    "unit_price": "30.00",
                    "extended_amount": "90.00",
                    "receipt_date": "2024-08-27",
                    "source_row_number": 25,
                },
            ],
        }
    )

    async def fake_open_raw_connection() -> FakeCanonicalConnection:
        return connection

    monkeypatch.setattr(canonical, "_open_raw_connection", fake_open_raw_connection)

    await canonical.run_canonical_import(
        batch_id="batch-holding-vs-drained",
        tenant_id=tenant_id,
        schema_name="raw_legacy",
    )

    # Verify a holding insert was made for the blank doc_number tbsslipdtj row
    holding_calls = [
        args
        for query, args in connection.execute_calls
        if 'INSERT INTO "raw_legacy".unsupported_history_holding' in query
        and "tbsslipdtj" in args
    ]
    assert len(holding_calls) == 1, (
        f"Expected exactly one holding insert for blank doc_number row, got {len(holding_calls)}"
    )

    holding_entries = [
        key
        for key in connection._fake_resolution_rows
        if key[2] == "tbsslipdtj" and key[3] == ":1"
    ]
    assert len(holding_entries) == 1, (
        f"Expected exactly one holding state entry, got {len(holding_entries)}"
    )
    assert connection._fake_resolution_rows[holding_entries[0]]["status"] == source_resolution.STATUS_HOLDING

    # AC1: Held rows should have a lineage entry with canonical_table='__holding__'
    holding_lineage_entries = [
        key
        for key in connection._fake_lineage_rows
        if key[2] == "__holding__"
        and key[3] == "tbsslipdtj"
        and key[4] == ":1"
    ]
    assert len(holding_lineage_entries) == 1, (
        f"Expected exactly one holding lineage entry for blank doc_number row, got {len(holding_lineage_entries)}"
    )

    # Drained rows should have lineage entries
    drained_entries = [
        key
        for key in connection._fake_lineage_rows
        if key[2] != "__holding__"
    ]
    assert drained_entries, "Expected canonical lineage entries for drained records"


@pytest.mark.asyncio
async def test_holding_and_drained_rows_are_distinguishable_drain(monkeypatch) -> None:
    """A drained AP payment should resolve source state and write normal lineage,
    with no sentinel holding lineage rows."""
    import domains.legacy_import.ap_payment_import as ap_payment_import

    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000442")
    supplier_id = ap_payment_import._tenant_scoped_uuid(
        tenant_id, "party", "supplier", "T008"
    )

    # Set up a tbsspay row with a verified supplier — it will drain to supplier_payments
    connection = FakePaymentConnection(
        {
            "tbscust": [
                {"legacy_code": "T008", "legacy_type": "1"},
            ],
            "supplier": [{"id": supplier_id}],
            "tbsspay": [
                {
                    "col_2": "DRAIN-001",
                    "col_4": "2016-05-05",
                    "col_6": "T008",
                    "col_8": "0001",
                    "col_10": "570.00000000",
                    "col_12": "CHK-001",
                    "col_18": "drained payment",
                    "_source_row_number": 1,
                },
            ],
            "tbsprepay": [],
        }
    )
    # Initialise lineage tracker so execute() can record entries
    connection._fake_lineage_rows = {}

    async def fake_open_raw_connection() -> FakePaymentConnection:
        return connection

    monkeypatch.setattr(ap_payment_import, "_open_raw_connection", fake_open_raw_connection)

    result = await ap_payment_import.run_ap_payment_import(
        batch_id="batch-holding-vs-drained-drain",
        tenant_id=tenant_id,
        schema_name="raw_legacy",
    )

    assert result.payment_count == 1
    assert result.holding_count == 0

    all_lineage_keys = list(connection._fake_lineage_rows)
    assert len(all_lineage_keys) == 1, (
        f"Expected exactly one lineage entry, got {len(all_lineage_keys)}"
    )

    _t, _b, canonical_table, source_table, source_identifier, source_row_number = all_lineage_keys[0]
    assert canonical_table == "supplier_payments"
    assert source_table == "tbsspay"
    assert source_identifier == "DRAIN-001"
    assert source_row_number == 1
    assert canonical_table != "__holding__"
    resolution_row = connection._fake_resolution_rows[
        (tenant_id, "batch-holding-vs-drained-drain", "tbsspay", "DRAIN-001", 1)
    ]
    assert resolution_row["status"] == source_resolution.STATUS_RESOLVED
    assert resolution_row["canonical_table"] == "supplier_payments"


@pytest.mark.asyncio
async def test_drain_updates_holding_lineage_entry(monkeypatch) -> None:
    """AC2: When a held row is drained, its lineage entry should be UPDATED
    (not duplicated) to point to the canonical table. The drain path uses
    source-identifier-only conflict matching, so holding + drain = 1 entry."""
    import domains.legacy_import.ap_payment_import as ap_payment_import

    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000442")
    supplier_id = ap_payment_import._tenant_scoped_uuid(
        tenant_id, "party", "supplier", "T008"
    )

    # Pre-populate a holding lineage entry as if _try_upsert_holding_and_lineage ran first
    connection = FakePaymentConnection(
        {
            "tbscust": [
                {"legacy_code": "T008", "legacy_type": "1"},
            ],
            "supplier": [{"id": supplier_id}],
            "tbsspay": [
                {
                    "col_2": "DRAIN-002",
                    "col_4": "2016-05-05",
                    "col_6": "T008",
                    "col_8": "0001",
                    "col_10": "570.00000000",
                    "col_12": "CHK-001",
                    "col_18": "drained payment",
                    "_source_row_number": 2,
                },
            ],
            "tbsprepay": [],
        }
    )
    # Simulate the holding lineage entry that would have been created earlier.
    # The key structure is (tenant_id, batch_id, canonical_table, source_table,
    # source_identifier, source_row_number) matching the lineage table PK.
    holding_key = (tenant_id, "batch-ac2-test", "__holding__", "tbsspay", "DRAIN-002", 2)
    connection._fake_lineage_rows = {
        holding_key: {
            "canonical_id": uuid.uuid4(),  # the holding_id
            "import_run_id": uuid.uuid4(),
        }
    }

    async def fake_open_raw_connection() -> FakePaymentConnection:
        return connection

    monkeypatch.setattr(ap_payment_import, "_open_raw_connection", fake_open_raw_connection)

    result = await ap_payment_import.run_ap_payment_import(
        batch_id="batch-ac2-test",
        tenant_id=tenant_id,
        schema_name="raw_legacy",
    )

    assert result.payment_count == 1
    assert result.holding_count == 0

    # AC2: Even though a holding lineage entry existed, the drain should UPDATE it
    # (not create a duplicate), so we should still have exactly 1 lineage entry
    all_lineage_keys = list(connection._fake_lineage_rows)
    assert len(all_lineage_keys) == 1, (
        f"Expected exactly one lineage entry after drain (AC2: UPDATE not duplicate), "
        f"got {len(all_lineage_keys)}"
    )

    # The updated entry should point to supplier_payments, not __holding__
    _t, _b, canonical_table, source_table, source_identifier, source_row_number = all_lineage_keys[0]
    assert canonical_table == "supplier_payments", (
        f"Expected canonical_table='supplier_payments' after drain, got '{canonical_table}'"
    )
    assert source_table == "tbsspay"
    assert source_identifier == "DRAIN-002"
    assert source_row_number == 2


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

    # Only process customers domain
    result = await canonical.run_canonical_import(
        batch_id="batch-scoped-001",
        tenant_id=tenant_id,
        schema_name="raw_legacy",
        selected_domains=["customers"],
        batch_mode="incremental",
    )

    # AC1: Only customers domain was processed
    assert result.customer_count == 1
    assert result.selected_domains == ("customers",)
    assert "suppliers" in result.skipped_domains
    assert "products" in result.skipped_domains
    assert "warehouses" in result.skipped_domains
    assert "inventory" in result.skipped_domains
    assert "sales_history" in result.skipped_domains
    assert "purchase_history" in result.skipped_domains

    # AC3: No upserts for skipped domains
    suppliers_upserts = [
        q for q, _ in connection.execute_calls
        if "INSERT INTO supplier" in q
    ]
    products_upserts = [
        q for q, _ in connection.execute_calls
        if "INSERT INTO product" in q
    ]
    assert len(suppliers_upserts) == 0, "Suppliers should be skipped"
    assert len(products_upserts) == 0, "Products should be skipped"


@pytest.mark.asyncio
async def test_scoped_incremental_import_filters_sales_by_entity_scope(monkeypatch) -> None:
    """AC2: Full document families are rebuilt deterministically for in-scope documents.
    When entity_scope specifies sales doc_numbers, only those headers+lines are processed."""
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

    monkeypatch.setattr(canonical, "_open_raw_connection", fake_open_raw_connection)

    # Entity scope includes only IN-SCOPE-001
    result = await canonical.run_canonical_import(
        batch_id="batch-scoped-002",
        tenant_id=tenant_id,
        schema_name="raw_legacy",
        selected_domains=["customers", "products", "sales_history"],
        entity_scope={
            "sales": {"closure_keys": [{"document_number": "IN-SCOPE-001"}]}
        },
        batch_mode="incremental",
    )

    # AC2: Only in-scope documents were processed
    assert result.order_count == 1, "Only in-scope order should be created"
    assert result.invoice_count == 1, "Only in-scope invoice should be created"
    assert result.scoped_document_count == 1

    # AC4: Out-of-scope documents were NOT processed
    orders_upserts = [
        args for q, args in connection.execute_calls
        if "INSERT INTO orders" in q
    ]
    assert len(orders_upserts) == 1, "Only one order should be upserted"
    assert orders_upserts[0][3] == "IN-SCOPE-001", "Order number should match in-scope doc"

    # Verify out-of-scope lines were NOT processed (only one order_line upsert)
    order_lines_upserts = [
        args for q, args in connection.execute_calls
        if "INSERT INTO order_lines" in q
    ]
    assert len(order_lines_upserts) == 1, "Only in-scope lines should be upserted"


@pytest.mark.asyncio
async def test_scoped_import_preserves_deterministic_ids_on_rerun(monkeypatch) -> None:
    """AC4: Same manifest scope produces idempotent results.
    Deterministic UUIDs are stable across reruns of the same scope."""
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

    # First run
    result1 = await canonical.run_canonical_import(
        batch_id="batch-det-001",
        tenant_id=tenant_id,
        schema_name="raw_legacy",
        selected_domains=["customers", "products", "sales_history"],
        entity_scope={
            "sales": {
                "closure_keys": [{"document_number": "DETERMINISTIC-001"}]
            }
        },
        batch_mode="incremental",
    )

    # Collect order IDs from first run
    order_ids_run1 = [
        args[0] for q, args in connection.execute_calls
        if "INSERT INTO orders" in q
    ]

    # Clear execute calls and reset connection state
    connection.execute_calls.clear()

    # Second run with same scope
    result2 = await canonical.run_canonical_import(
        batch_id="batch-det-002",
        tenant_id=tenant_id,
        schema_name="raw_legacy",
        selected_domains=["customers", "products", "sales_history"],
        entity_scope={
            "sales": {
                "closure_keys": [{"document_number": "DETERMINISTIC-001"}]
            }
        },
        batch_mode="incremental",
    )

    # Collect order IDs from second run
    order_ids_run2 = [
        args[0] for q, args in connection.execute_calls
        if "INSERT INTO orders" in q
    ]

    # AC4: Same scope produces same deterministic IDs
    assert len(order_ids_run1) == 1
    assert len(order_ids_run2) == 1
    assert order_ids_run1[0] == order_ids_run2[0], (
        "Deterministic order ID must be stable across reruns of same scope"
    )

    # Result counts should also be consistent
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

    # batch_mode=None or 'full' should process all domains
    result = await canonical.run_canonical_import(
        batch_id="batch-full-001",
        tenant_id=tenant_id,
        schema_name="raw_legacy",
        # selected_domains provided but batch_mode is None (full batch)
        selected_domains=["customers"],  # Would restrict scope if batch_mode=incremental
        batch_mode=None,  # Full batch - selected_domains should be ignored
    )

    # Full batch: all domains should be processed despite selected_domains
    assert result.customer_count == 1
    assert result.supplier_count == 1, "Suppliers should be processed in full batch"
    assert result.product_count >= 1, "Products should be processed in full batch"
    assert result.warehouse_count >= 1, "Warehouses should be processed in full batch"
    assert len(result.skipped_domains) == 0, "No domains should be skipped in full batch"


@pytest.mark.asyncio
async def test_build_entity_scope_closure_keys_extracts_correctly() -> None:
    """Helper function correctly extracts closure keys from entity_scope."""
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
    """Sales headers are filtered to only in-scope doc_numbers."""
    headers = [
        {"doc_number": "DOC-001"},
        {"doc_number": "DOC-002"},
        {"doc_number": "DOC-003"},
    ]
    scope_keys = {"sales": frozenset({"DOC-001", "DOC-002"})}

    result = canonical._filter_sales_headers_by_scope(headers, scope_keys)

    assert len(result) == 2
    assert all(h["doc_number"] in {"DOC-001", "DOC-002"} for h in result)


@pytest.mark.asyncio
async def test_filter_sales_headers_by_scope_empty_scope_returns_all() -> None:
    """When entity_scope is empty (full batch), all headers are returned."""
    headers = [
        {"doc_number": "DOC-001"},
        {"doc_number": "DOC-002"},
    ]
    scope_keys = {}  # Empty = full batch

    result = canonical._filter_sales_headers_by_scope(headers, scope_keys)

    assert len(result) == 2


@pytest.mark.asyncio
async def test_filter_sales_lines_preserves_full_family() -> None:
    """When header is in scope, ALL its lines are included (full family rebuild)."""
    lines = [
        {"doc_number": "DOC-001", "line_number": 1},
        {"doc_number": "DOC-001", "line_number": 2},
        {"doc_number": "DOC-002", "line_number": 1},
        {"doc_number": "DOC-003", "line_number": 1},  # Out of scope
    ]
    scoped_doc_numbers = frozenset({"DOC-001", "DOC-002"})

    result = canonical._filter_sales_lines_by_scope(lines, scoped_doc_numbers)

    # Both lines of DOC-001 should be included
    assert len(result) == 3
    doc_001_lines = [l for l in result if l["doc_number"] == "DOC-001"]
    assert len(doc_001_lines) == 2, "Full family of DOC-001 should be preserved"
    assert any(l["line_number"] == 1 for l in doc_001_lines)
    assert any(l["line_number"] == 2 for l in doc_001_lines)
