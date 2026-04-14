from __future__ import annotations

import uuid
from datetime import date

import pytest

from domains.legacy_import import cli, normalization
from domains.legacy_import.normalization import (
    NormalizationBatchResult,
    deterministic_legacy_uuid,
    normalize_legacy_date,
    normalize_party_record,
)


class FakeNormalizationTransaction:
    def __init__(self, connection: "FakeNormalizationConnection") -> None:
        self.connection = connection

    async def __aenter__(self) -> "FakeNormalizationTransaction":
        self.connection.transaction_started = True
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        if exc_type is None:
            self.connection.transaction_committed = True
        else:
            self.connection.transaction_rolled_back = True
        return False


class FakeNormalizationConnection:
    def __init__(self, staged_rows: dict[str, list[dict[str, object]]]) -> None:
        self.staged_rows = staged_rows
        self.execute_calls: list[tuple[str, tuple[object, ...]]] = []
        self.copy_calls: list[dict[str, object]] = []
        self.transaction_started = False
        self.transaction_committed = False
        self.transaction_rolled_back = False
        self.closed = False

    def transaction(self) -> FakeNormalizationTransaction:
        return FakeNormalizationTransaction(self)

    async def execute(self, query: str, *args: object) -> str:
        self.execute_calls.append((query, args))
        return "OK"

    async def fetch(self, query: str, batch_id: str):
        for table_name, rows in self.staged_rows.items():
            if f'FROM "raw_legacy"."{table_name}"' in query:
                return rows
        return []

    async def copy_records_to_table(
        self,
        table_name: str,
        *,
        schema_name: str | None = None,
        columns: tuple[str, ...] | list[str] | None = None,
        records: object,
    ) -> str:
        rows = list(records)
        self.copy_calls.append(
            {
                "table_name": table_name,
                "schema_name": schema_name,
                "columns": tuple(columns or ()),
                "rows": rows,
            }
        )
        return f"COPY {len(rows)}"

    async def close(self) -> None:
        self.closed = True


def test_normalize_legacy_date_handles_known_formats() -> None:
    assert normalize_legacy_date("1900-01-01") is None
    assert normalize_legacy_date("2025-04-07") == date(2025, 4, 7)
    assert normalize_legacy_date("1130826001") == date(2024, 8, 26)
    assert normalize_legacy_date("88032642") == date(1999, 3, 26)


def test_normalize_legacy_date_rejects_unknown_format() -> None:
    with pytest.raises(ValueError, match="Unsupported legacy date value"):
        normalize_legacy_date("11308")


def test_normalize_party_record_preserves_role_and_deterministic_identity() -> None:
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    record = {
        "legacy_code": "1149",
        "legacy_type": "1",
        "company_name": "聯泰興",
        "short_name": "聯泰",
        "full_address": "300 新竹市...",
        "address": "新竹市...",
        "phone": "03-1234567",
        "email": "",
        "contact_person": "王先生",
        "tax_id": "12603075",
        "created_date": "2025-04-07",
        "updated_date": "2019-08-14",
        "status_code": "A",
        "record_status": "A",
        "source_row_number": 10,
    }

    row = normalize_party_record(record, "batch-002", tenant_id)

    assert row[0] == "batch-002"
    assert row[1] == tenant_id
    assert row[2] == deterministic_legacy_uuid("party", "supplier", "1149")
    assert row[5] == "supplier"
    assert row[14] is True
    assert row[15] == date(2025, 4, 7)
    assert row[16] == date(2019, 8, 14)


def test_normalize_party_record_supports_customer_role() -> None:
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    row = normalize_party_record(
        {
            "legacy_code": "C001",
            "legacy_type": "2",
            "company_name": "客戶甲",
            "status_code": "A",
            "source_row_number": 5,
        },
        "batch-002",
        tenant_id,
    )

    assert row[2] == deterministic_legacy_uuid("party", "customer", "C001")
    assert row[5] == "customer"


def test_derive_product_category_prefers_legacy_class_when_present() -> None:
    category, source = normalization._derive_product_category(
        "P001",
        "Widget",
        legacy_category="Industrial Components",
        stock_kind="0",
    )

    assert category == "Industrial Components"
    assert source == "legacy_class"


def test_derive_product_category_flags_non_merchandise_from_stock_kind() -> None:
    category, source = normalization._derive_product_category(
        "0013",
        "郵寄運費",
        legacy_category=None,
        stock_kind="6",
    )

    assert category == "Non-Merchandise"
    assert source == "legacy_stock_kind"


def test_derive_product_category_uses_code_and_name_heuristics() -> None:
    timing_category, timing_source = normalization._derive_product_category(
        "RL225*19M/M",
        "225L*19M/M",
        legacy_category=None,
        stock_kind="0",
    )
    v_belt_category, v_belt_source = normalization._derive_product_category(
        "PC096",
        "三角皮帶 C-96",
        legacy_category=None,
        stock_kind="0",
    )

    assert timing_category == "Timing Belts"
    assert timing_source == "derived_from_code_name"
    assert v_belt_category == "V-Belts"
    assert v_belt_source == "derived_from_code_name"


@pytest.mark.asyncio
async def test_ensure_normalized_tables_use_tenant_scoped_primary_keys() -> None:
    connection = FakeNormalizationConnection({})

    await normalization._ensure_normalized_tables(connection, "raw_legacy")

    ddl = "\n".join(query for query, _ in connection.execute_calls)
    assert "PRIMARY KEY (tenant_id, batch_id, role, legacy_code)" in ddl
    assert "PRIMARY KEY (tenant_id, batch_id, legacy_code)" in ddl
    assert "PRIMARY KEY (tenant_id, batch_id, code)" in ddl
    assert "PRIMARY KEY (tenant_id, batch_id, product_legacy_code, warehouse_code)" in ddl


@pytest.mark.asyncio
async def test_run_normalization_is_tenant_scoped_and_transactional(monkeypatch) -> None:
    connection = FakeNormalizationConnection(
        {
            "tbscust": [
                {
                    "legacy_code": "C001",
                    "legacy_type": "2",
                    "company_name": "客戶甲",
                    "short_name": "客甲",
                    "full_address": "台北市",
                    "address": "台北市",
                    "phone": "02-1234",
                    "email": "",
                    "contact_person": "陳小姐",
                    "tax_id": "12345678",
                    "created_date": "2025-04-07",
                    "updated_date": "2025-04-07",
                    "status_code": "A",
                    "record_status": "A",
                    "source_row_number": 1,
                }
            ],
            "tbsstock": [
                {
                    "legacy_code": "PC096",
                    "name": "三角皮帶 C-96",
                    "legacy_category": None,
                    "stock_kind": "0",
                    "supplier_code": "C001",
                    "origin": "TW",
                    "unit": "條",
                    "created_date": "2025-04-07",
                    "last_sale_date": "2025-04-07",
                    "avg_cost": "12.50",
                    "status": "A",
                    "source_row_number": 2,
                }
            ],
            "tbsstkhouse": [
                {
                    "product_code": "P001",
                    "warehouse_code": "A",
                    "qty_on_hand": "8.0000",
                    "source_row_number": 3,
                }
            ],
        }
    )
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000321")

    async def fake_open_raw_connection() -> FakeNormalizationConnection:
        return connection

    monkeypatch.setattr(normalization, "_open_raw_connection", fake_open_raw_connection)

    result = await normalization.run_normalization(
        batch_id="batch-002",
        tenant_id=tenant_id,
        schema_name="raw_legacy",
    )

    delete_calls = [
        (query, args)
        for query, args in connection.execute_calls
        if query.startswith('DELETE FROM "raw_legacy".')
    ]
    assert delete_calls
    assert all(args == ("batch-002", tenant_id) for _, args in delete_calls)
    assert connection.transaction_started is True
    assert connection.transaction_committed is True
    assert connection.transaction_rolled_back is False
    assert connection.closed is True
    assert result.party_count == 1
    assert result.product_count == 1
    assert result.warehouse_count == 1
    assert result.inventory_count == 1

    product_copy = next(
        call for call in connection.copy_calls if call["table_name"] == "normalized_products"
    )
    warehouse_copy = next(
        call for call in connection.copy_calls if call["table_name"] == "normalized_warehouses"
    )
    inventory_copy = next(
        call for call in connection.copy_calls if call["table_name"] == "normalized_inventory_prep"
    )

    product_record = dict(zip(product_copy["columns"], product_copy["rows"][0], strict=False))
    assert warehouse_copy["rows"][0][4] == "A"
    assert inventory_copy["rows"][0][5] == "A"
    assert product_record["legacy_code"] == "PC096"
    assert product_record["category"] == "V-Belts"
    assert product_record["legacy_category"] is None
    assert product_record["stock_kind"] == "0"
    assert product_record["category_source"] == "derived_from_code_name"


@pytest.mark.asyncio
async def test_run_normalization_does_not_clear_rows_before_stage_validation(monkeypatch) -> None:
    connection = FakeNormalizationConnection(
        {
            "tbscust": [],
            "tbsstock": [],
            "tbsstkhouse": [],
        }
    )

    async def fake_open_raw_connection() -> FakeNormalizationConnection:
        return connection

    monkeypatch.setattr(normalization, "_open_raw_connection", fake_open_raw_connection)

    with pytest.raises(ValueError, match="No staged tbscust rows found"):
        await normalization.run_normalization(batch_id="missing-batch")

    assert not any(
        query.startswith('DELETE FROM "raw_legacy".') for query, _ in connection.execute_calls
    )
    assert connection.copy_calls == []
    assert connection.transaction_started is True
    assert connection.transaction_rolled_back is True
    assert connection.closed is True


def test_normalize_cli_invokes_normalization(monkeypatch, capsys) -> None:
    async def fake_run_normalization(**kwargs):
        assert kwargs["batch_id"] == "batch-002"
        return NormalizationBatchResult(
            batch_id="batch-002",
            schema_name="raw_legacy",
            party_count=10,
            product_count=20,
            warehouse_count=1,
            inventory_count=20,
        )

    monkeypatch.setattr(cli, "run_normalization", fake_run_normalization)

    result = cli.main(["normalize", "--batch-id", "batch-002"])
    output = capsys.readouterr().out

    assert result == 0
    assert "Normalized batch batch-002" in output
    assert "warehouses=1" in output
