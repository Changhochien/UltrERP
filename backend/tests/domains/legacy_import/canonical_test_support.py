from __future__ import annotations

import uuid
from typing import cast


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
        self.fetch_queries: list[tuple[str, tuple[object, ...]]] = []
        self.fetchval_queries: list[tuple[str, tuple[object, ...]]] = []
        self.transaction_buffers: list[list[tuple[str, tuple[object, ...]]]] = []
        self.transaction_started = False
        self.transaction_committed = False
        self.transaction_rolled_back = False
        self.closed = False
        self._fake_customers: dict[tuple[object, object], dict] = {}
        self._fake_suppliers: dict[tuple[object, object], dict] = {}
        self._fake_categories: dict[tuple[object, str], dict[str, object]] = {}
        self._fake_stock_adjustments: dict[uuid.UUID, dict[str, object]] = {}
        self._fake_lineage_rows: dict[tuple[object, ...], dict[str, object]] = {}
        self._fake_order_lines: dict[uuid.UUID, dict[str, object]] = {}
        self._fake_resolution_rows: dict[tuple[object, ...], dict[str, object]] = {}
        self._fake_resolution_events: list[dict[str, object]] = []
        self._fake_holding_rows: dict[tuple[object, ...], dict[str, object]] = {}

    @staticmethod
    def _filter_doc_number_rows(
        rows: list[dict[str, object]],
        args: tuple[object, ...],
    ) -> list[dict[str, object]]:
        if len(args) < 2 or not isinstance(args[1], list):
            return rows

        doc_numbers = {str(value) for value in args[1]}
        return [row for row in rows if str(row.get("doc_number")) in doc_numbers]

    def transaction(self) -> FakeCanonicalTransaction:
        return FakeCanonicalTransaction(self)

    async def fetch(self, query: str, *args: object):
        self.fetch_queries.append((query, args))
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
            return self._filter_doc_number_rows(self.rows_by_key.get("sales_headers", []), args)
        if 'FROM "raw_legacy".tbsslipdtx' in query:
            return self._filter_doc_number_rows(self.rows_by_key.get("sales_lines", []), args)
        if 'FROM "raw_legacy".tbsslipj' in query:
            return self._filter_doc_number_rows(self.rows_by_key.get("purchase_headers", []), args)
        if 'FROM "raw_legacy".tbsslipdtj' in query:
            return self._filter_doc_number_rows(self.rows_by_key.get("purchase_lines", []), args)
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
        if "INSERT INTO customers" in query and "RETURNING id" in query:
            call = (query, args)
            self.execute_calls.append(call)
            if self.transaction_buffers:
                self.transaction_buffers[-1].append(call)
            else:
                self.committed_execute_calls.append(call)
            customer_id, tenant_id, company_name, business_number = args[0], args[1], args[2], args[3]
            existing = self._fake_customers.get((tenant_id, business_number))
            if existing is None:
                existing = {"id": customer_id, "company_name": company_name}
            else:
                existing = {
                    "id": existing["id"],
                    "company_name": company_name,
                }
            self._fake_customers[(tenant_id, business_number)] = existing
            return dict(existing)
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
        self.fetchval_queries.append((query, args))
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
        if "INSERT INTO customers" in query:
            c_id, ten, co, bn = args[0], args[1], args[2], args[3]
            self._fake_customers[(ten, bn)] = {"id": c_id, "company_name": co}
        elif "INSERT INTO category (" in query:
            category_id, tenant_id, name = args[0], args[1], args[2]
            key = (tenant_id, str(name).casefold())
            existing = self._fake_categories.get(key)
            if existing is None:
                self._fake_categories[key] = {"id": category_id, "name": name}
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