from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

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

    async def fetch(self, query: str, *args: object):
        for table_name, rows in self.staged_rows.items():
            if f'FROM "raw_legacy"."{table_name}"' in query:
                return rows
        if 'FROM "raw_legacy".product_category_override' in query:
            return self.staged_rows.get("product_category_override", [])
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
    assert row[17] == "unknown"


def test_derive_product_category_prefers_family_rules_over_legacy_class() -> None:
    derivation = normalization._derive_product_category(
        "P001",
        "三角皮帶 C-240",
        legacy_category="Industrial Components",
        stock_kind="0",
    )

    assert derivation.category == "V-Belts"
    assert derivation.source == "heuristic_rule"
    assert derivation.rule_id == "name-token-v-belts"
    assert derivation.confidence == Decimal("0.90")


def test_derive_product_category_flags_non_merchandise_from_stock_kind() -> None:
    derivation = normalization._derive_product_category(
        "0013",
        "郵寄運費",
        legacy_category=None,
        stock_kind="6",
    )

    assert derivation.category == "Non-Merchandise"
    assert derivation.source == "exclusion_rule"
    assert derivation.rule_id == "stock-kind-non-merchandise"
    assert derivation.confidence == Decimal("1.00")


def test_derive_product_category_uses_code_and_name_heuristics() -> None:
    timing_derivation = normalization._derive_product_category(
        "RL225*19M/M",
        "225L*19M/M",
        legacy_category=None,
        stock_kind="0",
    )
    v_belt_derivation = normalization._derive_product_category(
        "PC096",
        "三角皮帶 C-96",
        legacy_category=None,
        stock_kind="0",
    )

    assert timing_derivation.category == "Timing Belts"
    assert timing_derivation.source == "heuristic_rule"
    assert timing_derivation.rule_id == "code-prefix-timing-belts"
    assert timing_derivation.confidence == Decimal("0.98")
    assert v_belt_derivation.category == "V-Belts"
    assert v_belt_derivation.source == "heuristic_rule"
    assert v_belt_derivation.rule_id == "code-prefix-v-belts"
    assert v_belt_derivation.confidence == Decimal("0.98")


def test_derive_product_category_routes_belt_joint_supplies_to_belt_supplies() -> None:
    derivation = normalization._derive_product_category(
        "PPPP0",
        "皮帶現場接頭",
        legacy_category=None,
        stock_kind="0",
    )

    assert derivation.category == "Belt Supplies"
    assert derivation.source == "heuristic_rule"
    assert derivation.rule_id == "code-prefix-belt-supplies"
    assert derivation.confidence == Decimal("0.98")


def test_derive_product_category_handles_story_v_belt_examples() -> None:
    spa_derivation = normalization._derive_product_category(
        "SPA-1432 OH",
        "SPA-1432 OH",
        legacy_category=None,
        stock_kind="0",
    )
    xpb_derivation = normalization._derive_product_category(
        "XPB-2410 進口",
        "XPB-2410 進口",
        legacy_category=None,
        stock_kind="0",
    )

    assert spa_derivation.category == "V-Belts"
    assert spa_derivation.source == "heuristic_rule"
    assert spa_derivation.rule_id == "code-prefix-v-belts"
    assert spa_derivation.confidence == Decimal("0.98")
    assert xpb_derivation.category == "V-Belts"
    assert xpb_derivation.source == "heuristic_rule"
    assert xpb_derivation.rule_id == "code-prefix-v-belts"
    assert xpb_derivation.confidence == Decimal("0.98")


def test_derive_product_category_handles_ribbed_pk_series_examples() -> None:
    derivation = normalization._derive_product_category(
        "5PK-1060",
        "BAANDO 5PK-1060",
        legacy_category=None,
        stock_kind="0",
    )

    assert derivation.category == "Ribbed Belts"
    assert derivation.source == "heuristic_rule"
    assert derivation.rule_id == "code-prefix-ribbed-belts"
    assert derivation.confidence == Decimal("0.98")

    j_series_derivation = normalization._derive_product_category(
        "J10-120",
        "J10-120 進口",
        legacy_category=None,
        stock_kind="0",
    )
    reverse_j_series_derivation = normalization._derive_product_category(
        "200-J10",
        "200-J10",
        legacy_category=None,
        stock_kind="0",
    )

    assert j_series_derivation.category == "Ribbed Belts"
    assert j_series_derivation.source == "heuristic_rule"
    assert j_series_derivation.rule_id == "code-prefix-ribbed-belts"
    assert j_series_derivation.confidence == Decimal("0.98")
    assert reverse_j_series_derivation.category == "Ribbed Belts"
    assert reverse_j_series_derivation.source == "heuristic_rule"
    assert reverse_j_series_derivation.rule_id == "code-prefix-ribbed-belts"
    assert reverse_j_series_derivation.confidence == Decimal("0.98")


def test_derive_product_category_handles_numeric_timing_series_examples() -> None:
    m_pitch_derivation = normalization._derive_product_category(
        "11M-1400-3RS",
        "冷卻水塔 11M-1400-3R",
        legacy_category=None,
        stock_kind="0",
    )
    xl_derivation = normalization._derive_product_category(
        "228XL*15M/M",
        "228XL*15M/M時規皮帶",
        legacy_category=None,
        stock_kind="0",
    )

    assert m_pitch_derivation.category == "Timing Belts"
    assert m_pitch_derivation.source == "heuristic_rule"
    assert m_pitch_derivation.rule_id == "code-prefix-timing-belts"
    assert m_pitch_derivation.confidence == Decimal("0.98")
    assert xl_derivation.category == "Timing Belts"
    assert xl_derivation.source == "heuristic_rule"
    assert xl_derivation.rule_id == "code-prefix-timing-belts"
    assert xl_derivation.confidence == Decimal("0.98")

    spaced_gt_derivation = normalization._derive_product_category(
        "2GT 200*4M/M",
        "2GT 200*4M/M",
        legacy_category=None,
        stock_kind="0",
    )
    xh_derivation = normalization._derive_product_category(
        "XH560*70M/M",
        "XH560*70M/M",
        legacy_category=None,
        stock_kind="0",
    )
    dashed_pitch_derivation = normalization._derive_product_category(
        "1040-8M*25M/M",
        "1040-8M*25M/M",
        legacy_category=None,
        stock_kind="0",
    )

    assert spaced_gt_derivation.category == "Timing Belts"
    assert spaced_gt_derivation.source == "heuristic_rule"
    assert spaced_gt_derivation.rule_id == "code-prefix-timing-belts"
    assert spaced_gt_derivation.confidence == Decimal("0.98")
    assert xh_derivation.category == "Timing Belts"
    assert xh_derivation.source == "heuristic_rule"
    assert xh_derivation.rule_id == "code-prefix-timing-belts"
    assert xh_derivation.confidence == Decimal("0.98")
    assert dashed_pitch_derivation.category == "Timing Belts"
    assert dashed_pitch_derivation.source == "heuristic_rule"
    assert dashed_pitch_derivation.rule_id == "code-prefix-timing-belts"
    assert dashed_pitch_derivation.confidence == Decimal("0.98")


def test_derive_product_category_handles_classic_special_v_belt_examples() -> None:
    oa_derivation = normalization._derive_product_category(
        "OA024-6",
        "耐熱皮帶 A-24",
        legacy_category=None,
        stock_kind="0",
    )
    bb_derivation = normalization._derive_product_category(
        "BB096",
        "大山雙B-96 [OH]",
        legacy_category=None,
        stock_kind="0",
    )

    assert oa_derivation.category == "V-Belts"
    assert oa_derivation.source == "heuristic_rule"
    assert oa_derivation.rule_id == "code-prefix-v-belts"
    assert oa_derivation.confidence == Decimal("0.98")
    assert bb_derivation.category == "V-Belts"
    assert bb_derivation.source == "heuristic_rule"
    assert bb_derivation.rule_id == "code-prefix-v-belts"
    assert bb_derivation.confidence == Decimal("0.98")

    oc_derivation = normalization._derive_product_category(
        "OC067-P",
        "OH C-67",
        legacy_category=None,
        stock_kind="0",
    )
    br_derivation = normalization._derive_product_category(
        "BR119",
        "外齒 B-119",
        legacy_category=None,
        stock_kind="0",
    )
    vendor_derivation = normalization._derive_product_category(
        "N3 PC040 大山",
        "大山皮帶 C-40-3",
        legacy_category=None,
        stock_kind="0",
    )

    assert oc_derivation.category == "V-Belts"
    assert oc_derivation.source == "heuristic_rule"
    assert oc_derivation.rule_id == "code-prefix-v-belts"
    assert oc_derivation.confidence == Decimal("0.98")
    assert br_derivation.category == "V-Belts"
    assert br_derivation.source == "heuristic_rule"
    assert br_derivation.rule_id == "code-prefix-v-belts"
    assert br_derivation.confidence == Decimal("0.98")
    assert vendor_derivation.category == "V-Belts"
    assert vendor_derivation.source == "heuristic_rule"
    assert vendor_derivation.rule_id == "name-token-v-belts"
    assert vendor_derivation.confidence == Decimal("0.90")


def test_derive_product_category_handles_specialty_belt_families() -> None:
    lps_derivation = normalization._derive_product_category(
        "LPS 10*1030",
        "LPS-14 10*1030",
        legacy_category=None,
        stock_kind="0",
    )
    tu6_derivation = normalization._derive_product_category(
        "9-TU6 10*600",
        "TU6 10*600M/M",
        legacy_category=None,
        stock_kind="0",
    )
    round_belt_derivation = normalization._derive_product_category(
        "圓綠帶 10*1945",
        "圓綠帶 10*1945",
        legacy_category=None,
        stock_kind="0",
    )

    assert lps_derivation.category == "Flat / Specialty Belts"
    assert lps_derivation.source == "heuristic_rule"
    assert lps_derivation.rule_id == "code-prefix-flat-specialty-belts"
    assert lps_derivation.confidence == Decimal("0.98")
    assert tu6_derivation.category == "Flat / Specialty Belts"
    assert tu6_derivation.source == "heuristic_rule"
    assert tu6_derivation.rule_id == "code-prefix-flat-specialty-belts"
    assert tu6_derivation.confidence == Decimal("0.98")
    assert round_belt_derivation.category == "Flat / Specialty Belts"
    assert round_belt_derivation.source == "heuristic_rule"
    assert round_belt_derivation.rule_id == "name-token-flat-specialty-belts"
    assert round_belt_derivation.confidence == Decimal("0.90")

    a2lt_derivation = normalization._derive_product_category(
        "A-2LT 30*650",
        "A-2LT 30*650",
        legacy_category=None,
        stock_kind="0",
    )

    assert a2lt_derivation.category == "Flat / Specialty Belts"
    assert a2lt_derivation.source == "heuristic_rule"
    assert a2lt_derivation.rule_id == "code-prefix-flat-specialty-belts"
    assert a2lt_derivation.confidence == Decimal("0.98")


def test_derive_product_category_handles_variable_speed_name_variants() -> None:
    derivation = normalization._derive_product_category(
        "1922V 338 OH",
        "變速帶 1922V338",
        legacy_category=None,
        stock_kind="0",
    )

    assert derivation.category == "Variable-Speed Belts"
    assert derivation.source == "heuristic_rule"
    assert derivation.rule_id == "name-token-variable-speed-belts"
    assert derivation.confidence == Decimal("0.90")


@pytest.mark.asyncio
async def test_ensure_normalized_tables_use_tenant_scoped_primary_keys() -> None:
    connection = FakeNormalizationConnection({})

    await normalization._ensure_normalized_tables(connection, "raw_legacy")

    ddl = "\n".join(query for query, _ in connection.execute_calls)
    assert (
        'ALTER TABLE "raw_legacy"."normalized_products" '
        'ADD COLUMN IF NOT EXISTS legacy_category TEXT' in ddl
    )
    assert (
        'ALTER TABLE "raw_legacy"."normalized_products" '
        'ADD COLUMN IF NOT EXISTS stock_kind TEXT' in ddl
    )
    assert (
        'ALTER TABLE "raw_legacy"."normalized_products" '
        'ADD COLUMN IF NOT EXISTS category_source TEXT' in ddl
    )
    assert (
        'ALTER TABLE "raw_legacy"."normalized_products" '
        'ADD COLUMN IF NOT EXISTS category_rule_id TEXT' in ddl
    )
    assert (
        'ALTER TABLE "raw_legacy"."normalized_products" '
        'ADD COLUMN IF NOT EXISTS category_confidence NUMERIC(5, 2)' in ddl
    )
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
    assert product_record["category_source"] == "heuristic_rule"
    assert product_record["category_rule_id"] == "code-prefix-v-belts"
    assert product_record["category_confidence"] == Decimal("0.98")


@pytest.mark.asyncio
async def test_run_normalization_applies_category_overrides_and_records_review_candidates(
    monkeypatch,
) -> None:
    connection = FakeNormalizationConnection(
        {
            "tbscust": [
                {
                    "legacy_code": "S001",
                    "legacy_type": "1",
                    "company_name": "Supplier One",
                    "status_code": "A",
                    "record_status": "A",
                    "source_row_number": 1,
                }
            ],
            "tbsstock": [
                {
                    "legacy_code": "PC096",
                    "name": "三角皮帶 C-96",
                    "legacy_category": "Industrial Components",
                    "stock_kind": "0",
                    "supplier_code": "S001",
                    "origin": "TW",
                    "unit": "條",
                    "created_date": "2025-04-07",
                    "last_sale_date": "2025-04-07",
                    "avg_cost": "12.50",
                    "status": "A",
                    "source_row_number": 2,
                },
                {
                    "legacy_code": "SHIP01",
                    "name": "郵寄運費",
                    "legacy_category": None,
                    "stock_kind": "6",
                    "supplier_code": "S001",
                    "origin": "TW",
                    "unit": "式",
                    "created_date": "2025-04-07",
                    "last_sale_date": "2025-04-07",
                    "avg_cost": "0",
                    "status": "A",
                    "source_row_number": 3,
                },
            ],
            "tbsstkhouse": [
                {
                    "product_code": "PC096",
                    "warehouse_code": "A",
                    "qty_on_hand": "8.0000",
                    "source_row_number": 4,
                }
            ],
            "product_category_override": [
                {
                    "legacy_code": "PC096",
                    "category": "Timing Belts",
                    "review_notes": "Legacy catalog corrected by analyst.",
                    "approval_source": "review-import",
                    "approved_by": "analyst@example.com",
                }
            ],
        }
    )

    async def fake_open_raw_connection() -> FakeNormalizationConnection:
        return connection

    monkeypatch.setattr(normalization, "_open_raw_connection", fake_open_raw_connection)

    await normalization.run_normalization(
        batch_id="batch-override",
        tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000321"),
        schema_name="raw_legacy",
    )

    product_copy = next(
        call for call in connection.copy_calls if call["table_name"] == "normalized_products"
    )
    product_records = [
        dict(zip(product_copy["columns"], row, strict=False)) for row in product_copy["rows"]
    ]
    overridden_record = next(
        record for record in product_records if record["legacy_code"] == "PC096"
    )
    excluded_record = next(
        record for record in product_records if record["legacy_code"] == "SHIP01"
    )

    assert overridden_record["category"] == "Timing Belts"
    assert overridden_record["category_source"] == "manual_override"
    assert overridden_record["category_rule_id"] == "manual-override"
    assert overridden_record["category_confidence"] == Decimal("1.00")
    assert excluded_record["category"] == "Non-Merchandise"

    review_candidate_inserts = [
        args
        for query, args in connection.execute_calls
        if 'INSERT INTO "raw_legacy".product_category_review_candidates' in query
    ]
    assert review_candidate_inserts
    assert any("SHIP01" in args for args in review_candidate_inserts)
    assert any("excluded_path" in args for args in review_candidate_inserts)
    assert not any("PC096" in args for args in review_candidate_inserts)


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
