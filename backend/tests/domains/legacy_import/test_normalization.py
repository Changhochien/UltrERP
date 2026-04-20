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
    def __init__(
        self,
        staged_rows: dict[str, list[dict[str, object]]],
        *,
        stage_run_rows: list[dict[str, object]] | None = None,
    ) -> None:
        self.staged_rows = staged_rows
        self.stage_run_rows = stage_run_rows or []
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
        if "legacy_import_runs AS runs" in query:
            batch_id = args[0] if args else None
            schema_name = args[1] if len(args) > 1 else None
            return [
                row
                for row in self.stage_run_rows
                if row.get("batch_id") == batch_id and row.get("target_schema") == schema_name
            ][:1]
        for table_name, rows in self.staged_rows.items():
            if f'FROM "raw_legacy"."{table_name}"' in query:
                batch_id = args[0] if args else None
                return [
                    row for row in rows if row.get("_batch_id", batch_id) == batch_id
                ]
        if 'FROM "raw_legacy".product_category_override' in query:
            tenant_id = args[0] if args else None
            return [
                row
                for row in self.staged_rows.get("product_category_override", [])
                if row.get("tenant_id", tenant_id) == tenant_id
            ]
        if 'FROM "raw_legacy".product_code_mapping' in query:
            tenant_id = args[0] if args else None
            batch_id = args[1] if len(args) > 1 else None
            return [
                row
                for row in self.staged_rows.get("product_code_mapping", [])
                if row.get("tenant_id", tenant_id) == tenant_id
                and row.get("last_seen_batch_id", batch_id) == batch_id
                and row.get("approval_source") == "review-import"
                and row.get("resolution_type") == "analyst_review"
                and row.get("target_code") == row.get("legacy_code")
            ]
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


def test_derive_product_category_routes_consumables_and_belt_hooks_out_of_fallback() -> None:
    pk_derivation = normalization._derive_product_category(
        "PK-FILM-20U",
        "FILM-20U",
        legacy_category=None,
        stock_kind="0",
    )
    toner_derivation = normalization._derive_product_category(
        "011",
        "Brother MFC-2770原廠碳粉",
        legacy_category=None,
        stock_kind="0",
    )
    paper_derivation = normalization._derive_product_category(
        "9 1/2*11*1P白中1刀",
        "電腦連續報表紙",
        legacy_category=None,
        stock_kind="0",
    )
    hook_derivation = normalization._derive_product_category(
        "003",
        "皮帶勾",
        legacy_category=None,
        stock_kind="0",
    )

    assert pk_derivation.category == "Non-Merchandise"
    assert pk_derivation.source == "exclusion_rule"
    assert pk_derivation.rule_id == "code-prefix-non-merchandise"
    assert pk_derivation.confidence == Decimal("0.98")
    assert toner_derivation.category == "Non-Merchandise"
    assert toner_derivation.source == "exclusion_rule"
    assert toner_derivation.rule_id == "name-token-non-merchandise"
    assert toner_derivation.confidence == Decimal("0.95")
    assert paper_derivation.category == "Non-Merchandise"
    assert paper_derivation.source == "exclusion_rule"
    assert paper_derivation.rule_id == "name-token-non-merchandise"
    assert paper_derivation.confidence == Decimal("0.95")
    assert hook_derivation.category == "Belt Supplies"
    assert hook_derivation.source == "heuristic_rule"
    assert hook_derivation.rule_id == "name-token-belt-supplies"
    assert hook_derivation.confidence == Decimal("0.90")


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
    s2m_derivation = normalization._derive_product_category(
        "S2M-144*4M/M",
        "S2M-144*4M/M",
        legacy_category=None,
        stock_kind="0",
    )
    s_pitch_derivation = normalization._derive_product_category(
        "S4.5-450*11",
        "04.5M-450*11M/M",
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
    assert s2m_derivation.category == "Timing Belts"
    assert s2m_derivation.source == "heuristic_rule"
    assert s2m_derivation.rule_id == "code-prefix-timing-belts"
    assert s2m_derivation.confidence == Decimal("0.98")
    assert s_pitch_derivation.category == "Timing Belts"
    assert s_pitch_derivation.source == "heuristic_rule"
    assert s_pitch_derivation.rule_id == "code-prefix-timing-belts"
    assert s_pitch_derivation.confidence == Decimal("0.98")


def test_derive_product_category_handles_h_l_and_t_timing_families() -> None:
    h_series_derivation = normalization._derive_product_category(
        "H4-2030",
        "H4-2030",
        legacy_category=None,
        stock_kind="0",
    )
    l_series_derivation = normalization._derive_product_category(
        "L10F 50*1790",
        "L10F 50*1790",
        legacy_category=None,
        stock_kind="0",
    )
    l_dash_derivation = normalization._derive_product_category(
        "L-500 180*600",
        "L-500 180*600",
        legacy_category=None,
        stock_kind="0",
    )
    t2_5_derivation = normalization._derive_product_category(
        "T2.5*160*4M/M",
        "T2.5*160*4M/M",
        legacy_category=None,
        stock_kind="0",
    )
    u10_derivation = normalization._derive_product_category(
        "U10AG140*770",
        "140*2*770",
        legacy_category=None,
        stock_kind="0",
    )

    assert h_series_derivation.category == "Timing Belts"
    assert h_series_derivation.source == "heuristic_rule"
    assert h_series_derivation.rule_id == "code-prefix-timing-belts"
    assert h_series_derivation.confidence == Decimal("0.98")
    assert l_series_derivation.category == "Timing Belts"
    assert l_series_derivation.source == "heuristic_rule"
    assert l_series_derivation.rule_id == "code-prefix-timing-belts"
    assert l_series_derivation.confidence == Decimal("0.98")
    assert l_dash_derivation.category == "Timing Belts"
    assert l_dash_derivation.source == "heuristic_rule"
    assert l_dash_derivation.rule_id == "code-prefix-timing-belts"
    assert l_dash_derivation.confidence == Decimal("0.98")
    assert t2_5_derivation.category == "Timing Belts"
    assert t2_5_derivation.source == "heuristic_rule"
    assert t2_5_derivation.rule_id == "code-prefix-timing-belts"
    assert t2_5_derivation.confidence == Decimal("0.98")
    assert u10_derivation.category == "Timing Belts"
    assert u10_derivation.source == "heuristic_rule"
    assert u10_derivation.rule_id == "code-prefix-timing-belts"
    assert u10_derivation.confidence == Decimal("0.98")


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
    f_series_derivation = normalization._derive_product_category(
        "F-1 12*1005",
        "F-1 12*1005MM",
        legacy_category=None,
        stock_kind="0",
    )
    g_series_derivation = normalization._derive_product_category(
        "G-1 30*3000",
        "G-1 30*3000M/M",
        legacy_category=None,
        stock_kind="0",
    )
    fk_derivation = normalization._derive_product_category(
        "FK 120*2195",
        "平面 120*2195 直切",
        legacy_category=None,
        stock_kind="0",
    )
    ts_derivation = normalization._derive_product_category(
        "TS-55 25*780",
        "TS-55 25*780",
        legacy_category=None,
        stock_kind="0",
    )
    pv10_derivation = normalization._derive_product_category(
        "PV10 100*1622",
        "PV10 100*1622",
        legacy_category=None,
        stock_kind="0",
    )
    tc20_derivation = normalization._derive_product_category(
        "TC20 25*1253",
        "TC20/25EF 25*1253",
        legacy_category=None,
        stock_kind="0",
    )
    enu_derivation = normalization._derive_product_category(
        "ENU 45*5985",
        "ENU-50A 450*5985",
        legacy_category=None,
        stock_kind="0",
    )

    assert a2lt_derivation.category == "Flat / Specialty Belts"
    assert a2lt_derivation.source == "heuristic_rule"
    assert a2lt_derivation.rule_id == "code-prefix-flat-specialty-belts"
    assert a2lt_derivation.confidence == Decimal("0.98")
    assert f_series_derivation.category == "Flat / Specialty Belts"
    assert f_series_derivation.source == "heuristic_rule"
    assert f_series_derivation.rule_id == "code-prefix-flat-specialty-belts"
    assert f_series_derivation.confidence == Decimal("0.98")
    assert g_series_derivation.category == "Flat / Specialty Belts"
    assert g_series_derivation.source == "heuristic_rule"
    assert g_series_derivation.rule_id == "code-prefix-flat-specialty-belts"
    assert g_series_derivation.confidence == Decimal("0.98")
    assert fk_derivation.category == "Flat / Specialty Belts"
    assert fk_derivation.source == "heuristic_rule"
    assert fk_derivation.rule_id == "code-prefix-flat-specialty-belts"
    assert fk_derivation.confidence == Decimal("0.98")
    assert ts_derivation.category == "Flat / Specialty Belts"
    assert ts_derivation.source == "heuristic_rule"
    assert ts_derivation.rule_id == "code-prefix-flat-specialty-belts"
    assert ts_derivation.confidence == Decimal("0.98")
    assert pv10_derivation.category == "Flat / Specialty Belts"
    assert pv10_derivation.source == "heuristic_rule"
    assert pv10_derivation.rule_id == "code-prefix-flat-specialty-belts"
    assert pv10_derivation.confidence == Decimal("0.98")
    assert tc20_derivation.category == "Flat / Specialty Belts"
    assert tc20_derivation.source == "heuristic_rule"
    assert tc20_derivation.rule_id == "code-prefix-flat-specialty-belts"
    assert tc20_derivation.confidence == Decimal("0.98")
    assert enu_derivation.category == "Flat / Specialty Belts"
    assert enu_derivation.source == "heuristic_rule"
    assert enu_derivation.rule_id == "code-prefix-flat-specialty-belts"
    assert enu_derivation.confidence == Decimal("0.98")


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


def test_derive_product_category_handles_standardized_vehicle_and_v_belt_families() -> None:
    avx_derivation = normalization._derive_product_category(
        "AVX-10*625M/M",
        "AVX-10*625M/M",
        legacy_category=None,
        stock_kind="0",
    )
    xpc_derivation = normalization._derive_product_category(
        "XPC-2500",
        "XPC-2500 OPTI",
        legacy_category=None,
        stock_kind="0",
    )
    link_derivation = normalization._derive_product_category(
        "LINK-A",
        "鱗片帶 A 型",
        legacy_category=None,
        stock_kind="0",
    )
    section_name_derivation = normalization._derive_product_category(
        "LB125-P",
        "皮帶 B-125",
        legacy_category=None,
        stock_kind="0",
    )
    heat_resistant_derivation = normalization._derive_product_category(
        "OLA065-3",
        "三星 耐熱 LA-65",
        legacy_category=None,
        stock_kind="0",
    )
    banded_derivation = normalization._derive_product_category(
        "HA1000 16*1368",
        "保力皮帶 16*1368",
        legacy_category=None,
        stock_kind="0",
    )
    mbt_derivation = normalization._derive_product_category(
        "MBT-778*21.9",
        "4CW-778*21.9",
        legacy_category=None,
        stock_kind="0",
    )
    oem_vehicle_derivation = normalization._derive_product_category(
        "17641-00",
        "4CW- 迅光",
        legacy_category=None,
        stock_kind="0",
    )

    assert avx_derivation.category == "Vehicle Belts"
    assert avx_derivation.source == "heuristic_rule"
    assert avx_derivation.rule_id == "code-prefix-vehicle-belts"
    assert avx_derivation.confidence == Decimal("0.98")
    assert mbt_derivation.category == "Vehicle Belts"
    assert mbt_derivation.source == "heuristic_rule"
    assert mbt_derivation.rule_id == "code-prefix-vehicle-belts"
    assert mbt_derivation.confidence == Decimal("0.98")
    assert oem_vehicle_derivation.category == "Vehicle Belts"
    assert oem_vehicle_derivation.source == "heuristic_rule"
    assert oem_vehicle_derivation.rule_id == "code-prefix-vehicle-belts"
    assert oem_vehicle_derivation.confidence == Decimal("0.98")
    assert xpc_derivation.category == "V-Belts"
    assert xpc_derivation.source == "heuristic_rule"
    assert xpc_derivation.rule_id == "code-prefix-v-belts"
    assert xpc_derivation.confidence == Decimal("0.98")
    assert link_derivation.category == "V-Belts"
    assert link_derivation.source == "heuristic_rule"
    assert link_derivation.rule_id == "code-prefix-v-belts"
    assert link_derivation.confidence == Decimal("0.98")
    assert section_name_derivation.category == "V-Belts"
    assert section_name_derivation.source == "heuristic_rule"
    assert section_name_derivation.rule_id == "name-token-v-belts"
    assert section_name_derivation.confidence == Decimal("0.90")
    assert heat_resistant_derivation.category == "V-Belts"
    assert heat_resistant_derivation.source == "heuristic_rule"
    assert heat_resistant_derivation.rule_id == "name-token-v-belts"
    assert heat_resistant_derivation.confidence == Decimal("0.90")
    assert banded_derivation.category == "V-Belts"
    assert banded_derivation.source == "heuristic_rule"
    assert banded_derivation.rule_id == "code-prefix-v-belts"
    assert banded_derivation.confidence == Decimal("0.98")


def test_derive_product_category_handles_grounded_remaining_family_tails() -> None:
    vs_derivation = normalization._derive_product_category(
        "VS-16*573",
        "VS-16*573",
        legacy_category=None,
        stock_kind="0",
    )
    ham_derivation = normalization._derive_product_category(
        "HAM-25*5425MM",
        "HAM-25*5425M/M",
        legacy_category=None,
        stock_kind="0",
    )
    yu_derivation = normalization._derive_product_category(
        "YU145-22",
        "145YU-22",
        legacy_category=None,
        stock_kind="0",
    )
    ls_derivation = normalization._derive_product_category(
        "LS-2 18*2337",
        "LS-2 18*2337",
        legacy_category=None,
        stock_kind="0",
    )
    pu_l_derivation = normalization._derive_product_category(
        "PU210L*13M/M",
        "210L*1325M/M-PU",
        legacy_category=None,
        stock_kind="0",
    )
    pu_xl_derivation = normalization._derive_product_category(
        "PU210XL*25M/M",
        "210XL*25M/M-PU",
        legacy_category=None,
        stock_kind="0",
    )
    imperial_l_derivation = normalization._derive_product_category(
        "225L*13M/M PU",
        "鋼絲 225L*13M/M",
        legacy_category=None,
        stock_kind="0",
    )
    r240_derivation = normalization._derive_product_category(
        "R240L*23R",
        "240L*23M/M 紅(厚)",
        legacy_category=None,
        stock_kind="0",
    )
    fon_derivation = normalization._derive_product_category(
        "FON 5*435",
        "FON 5*435",
        legacy_category=None,
        stock_kind="0",
    )
    foz_derivation = normalization._derive_product_category(
        "FOZ 8*560",
        "FOZ 8*560",
        legacy_category=None,
        stock_kind="0",
    )
    fo037_derivation = normalization._derive_product_category(
        "FO037",
        "OH FM-37",
        legacy_category=None,
        stock_kind="0",
    )

    assert vs_derivation.category == "Variable-Speed Belts"
    assert vs_derivation.source == "heuristic_rule"
    assert vs_derivation.rule_id == "code-prefix-variable-speed-belts"
    assert vs_derivation.confidence == Decimal("0.98")
    assert ham_derivation.category == "Flat / Specialty Belts"
    assert ham_derivation.source == "heuristic_rule"
    assert ham_derivation.rule_id == "code-prefix-flat-specialty-belts"
    assert ham_derivation.confidence == Decimal("0.98")
    assert yu_derivation.category == "Timing Belts"
    assert yu_derivation.source == "heuristic_rule"
    assert yu_derivation.rule_id == "code-prefix-timing-belts"
    assert yu_derivation.confidence == Decimal("0.98")
    assert ls_derivation.category == "Timing Belts"
    assert ls_derivation.source == "heuristic_rule"
    assert ls_derivation.rule_id == "code-prefix-timing-belts"
    assert ls_derivation.confidence == Decimal("0.98")
    assert pu_l_derivation.category == "Timing Belts"
    assert pu_l_derivation.source == "heuristic_rule"
    assert pu_l_derivation.rule_id == "code-prefix-timing-belts"
    assert pu_l_derivation.confidence == Decimal("0.98")
    assert pu_xl_derivation.category == "Timing Belts"
    assert pu_xl_derivation.source == "heuristic_rule"
    assert pu_xl_derivation.rule_id == "code-prefix-timing-belts"
    assert pu_xl_derivation.confidence == Decimal("0.98")
    assert imperial_l_derivation.category == "Timing Belts"
    assert imperial_l_derivation.source == "heuristic_rule"
    assert imperial_l_derivation.rule_id == "code-prefix-timing-belts"
    assert imperial_l_derivation.confidence == Decimal("0.98")
    assert r240_derivation.category == "Timing Belts"
    assert r240_derivation.source == "heuristic_rule"
    assert r240_derivation.rule_id == "code-prefix-timing-belts"
    assert r240_derivation.confidence == Decimal("0.98")
    assert fon_derivation.category == "V-Belts"
    assert fon_derivation.source == "heuristic_rule"
    assert fon_derivation.rule_id == "code-prefix-v-belts"
    assert fon_derivation.confidence == Decimal("0.98")
    assert foz_derivation.category == "V-Belts"
    assert foz_derivation.source == "heuristic_rule"
    assert foz_derivation.rule_id == "code-prefix-v-belts"
    assert foz_derivation.confidence == Decimal("0.98")
    assert fo037_derivation.category == "V-Belts"
    assert fo037_derivation.source == "heuristic_rule"
    assert fo037_derivation.rule_id == "code-prefix-v-belts"
    assert fo037_derivation.confidence == Decimal("0.98")


def test_derive_product_category_handles_habasit_tangential_family_codes() -> None:
    s_family_derivation = normalization._derive_product_category(
        "S-2 20*630MM",
        "S-2 20*630M/M",
        legacy_category=None,
        stock_kind="0",
    )
    sp_family_derivation = normalization._derive_product_category(
        "SP180/23 20*1105",
        "SP180/23 20*1105",
        legacy_category=None,
        stock_kind="0",
    )
    se15_derivation = normalization._derive_product_category(
        "SE15LL 15*1630",
        "SE15LL 15*1630",
        legacy_category=None,
        stock_kind="0",
    )
    s250_derivation = normalization._derive_product_category(
        "S250 25*1778",
        "S250 25*1778",
        legacy_category=None,
        stock_kind="0",
    )

    assert s_family_derivation.category == "Flat / Specialty Belts"
    assert s_family_derivation.source == "heuristic_rule"
    assert s_family_derivation.rule_id == "code-prefix-flat-specialty-belts"
    assert s_family_derivation.confidence == Decimal("0.98")
    assert sp_family_derivation.category == "Flat / Specialty Belts"
    assert sp_family_derivation.source == "heuristic_rule"
    assert sp_family_derivation.rule_id == "code-prefix-flat-specialty-belts"
    assert sp_family_derivation.confidence == Decimal("0.98")
    assert se15_derivation.category == "Flat / Specialty Belts"
    assert se15_derivation.source == "heuristic_rule"
    assert se15_derivation.rule_id == "code-prefix-flat-specialty-belts"
    assert se15_derivation.confidence == Decimal("0.98")
    assert s250_derivation.category == "Flat / Specialty Belts"
    assert s250_derivation.source == "heuristic_rule"
    assert s250_derivation.rule_id == "code-prefix-flat-specialty-belts"
    assert s250_derivation.confidence == Decimal("0.98")


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
                    "product_code": "PC096",
                    "warehouse_code": "A",
                    "qty_on_hand": "8.0000",
                    "source_row_number": 3,
                }
            ],
        },
        stage_run_rows=[
            {
                "tenant_id": uuid.UUID("00000000-0000-0000-0000-000000000321"),
                "status": "completed",
                "batch_id": "batch-002",
                "target_schema": "raw_legacy",
            }
        ],
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
async def test_run_normalization_rejects_stage_batches_for_other_tenants(monkeypatch) -> None:
    requested_tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000321")
    connection = FakeNormalizationConnection(
        {
            "tbscust": [],
            "tbsstock": [],
            "tbsstkhouse": [],
        },
        stage_run_rows=[
            {
                "tenant_id": uuid.UUID("00000000-0000-0000-0000-000000000999"),
                "status": "completed",
                "batch_id": "batch-002",
                "target_schema": "raw_legacy",
            }
        ],
    )

    async def fake_open_raw_connection() -> FakeNormalizationConnection:
        return connection

    monkeypatch.setattr(normalization, "_open_raw_connection", fake_open_raw_connection)

    with pytest.raises(ValueError, match="belongs to tenant"):
        await normalization.run_normalization(
            batch_id="batch-002",
            tenant_id=requested_tenant_id,
            schema_name="raw_legacy",
        )

    assert connection.transaction_started is False
    assert connection.copy_calls == []
    assert connection.closed is True


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
                    "tenant_id": uuid.UUID("00000000-0000-0000-0000-000000000321"),
                }
            ],
        },
        stage_run_rows=[
            {
                "tenant_id": uuid.UUID("00000000-0000-0000-0000-000000000321"),
                "status": "completed",
                "batch_id": "batch-override",
                "target_schema": "raw_legacy",
            }
        ],
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
        },
        stage_run_rows=[
            {
                "tenant_id": uuid.UUID("00000000-0000-0000-0000-000000000001"),
                "status": "completed",
                "batch_id": "missing-batch",
                "target_schema": "raw_legacy",
            }
        ],
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


@pytest.mark.asyncio
async def test_run_normalization_preserves_existing_synthetic_products(monkeypatch) -> None:
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000321")
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
                    "legacy_category": None,
                    "stock_kind": "0",
                    "supplier_code": "S001",
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
                    "product_code": "PC096",
                    "warehouse_code": "A",
                    "qty_on_hand": "8.0000",
                    "source_row_number": 4,
                }
            ],
            "normalized_products": [
                {
                    "batch_id": "batch-synthetic",
                    "tenant_id": tenant_id,
                    "deterministic_id": deterministic_legacy_uuid("product", "RB052-6"),
                    "legacy_code": "RB052-6",
                    "name": "RB052-6",
                    "category": None,
                    "legacy_category": None,
                    "stock_kind": None,
                    "category_source": "product_code_mapping_review",
                    "category_rule_id": None,
                    "category_confidence": None,
                    "supplier_legacy_code": None,
                    "supplier_deterministic_id": None,
                    "origin": None,
                    "unit": "unknown",
                    "status": "synthetic-review",
                    "created_date": None,
                    "last_sale_date": None,
                    "avg_cost": None,
                    "source_table": "product_code_mapping_review",
                    "source_row_number": 99,
                }
            ],
            "product_code_mapping": [
                {
                    "tenant_id": tenant_id,
                    "last_seen_batch_id": "batch-synthetic",
                    "legacy_code": "RB052-6",
                    "target_code": "RB052-6",
                    "approval_source": "review-import",
                    "resolution_type": "analyst_review",
                }
            ],
        },
        stage_run_rows=[
            {
                "tenant_id": tenant_id,
                "status": "completed",
                "batch_id": "batch-synthetic",
                "target_schema": "raw_legacy",
            }
        ],
    )

    async def fake_open_raw_connection() -> FakeNormalizationConnection:
        return connection

    monkeypatch.setattr(normalization, "_open_raw_connection", fake_open_raw_connection)

    await normalization.run_normalization(
        batch_id="batch-synthetic",
        tenant_id=tenant_id,
        schema_name="raw_legacy",
    )

    product_copy = next(
        call for call in connection.copy_calls if call["table_name"] == "normalized_products"
    )
    copied_rows = [dict(zip(product_copy["columns"], row, strict=False)) for row in product_copy["rows"]]

    assert {row["legacy_code"] for row in copied_rows} == {"PC096", "RB052-6"}
    synthetic_row = next(row for row in copied_rows if row["legacy_code"] == "RB052-6")
    assert synthetic_row["status"] == "synthetic-review"
    assert synthetic_row["source_table"] == "product_code_mapping_review"
    assert synthetic_row["unit"] == "unknown"


@pytest.mark.asyncio
async def test_run_normalization_drops_stale_synthetic_products_without_self_target_review(
    monkeypatch,
) -> None:
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000321")
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
                    "legacy_category": None,
                    "stock_kind": "0",
                    "supplier_code": "S001",
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
                    "product_code": "PC096",
                    "warehouse_code": "A",
                    "qty_on_hand": "8.0000",
                    "source_row_number": 4,
                }
            ],
            "normalized_products": [
                {
                    "batch_id": "batch-synthetic",
                    "tenant_id": tenant_id,
                    "deterministic_id": deterministic_legacy_uuid("product", "RB052-6"),
                    "legacy_code": "RB052-6",
                    "name": "RB052-6",
                    "category": None,
                    "legacy_category": None,
                    "stock_kind": None,
                    "category_source": "product_code_mapping_review",
                    "category_rule_id": None,
                    "category_confidence": None,
                    "supplier_legacy_code": None,
                    "supplier_deterministic_id": None,
                    "origin": None,
                    "unit": "unknown",
                    "status": "synthetic-review",
                    "created_date": None,
                    "last_sale_date": None,
                    "avg_cost": None,
                    "source_table": "product_code_mapping_review",
                    "source_row_number": 99,
                }
            ],
            "product_code_mapping": [
                {
                    "tenant_id": tenant_id,
                    "last_seen_batch_id": "batch-synthetic",
                    "legacy_code": "RB052-6",
                    "target_code": "RB052",
                    "approval_source": "review-import",
                    "resolution_type": "analyst_review",
                }
            ],
        },
        stage_run_rows=[
            {
                "tenant_id": tenant_id,
                "status": "completed",
                "batch_id": "batch-synthetic",
                "target_schema": "raw_legacy",
            }
        ],
    )

    async def fake_open_raw_connection() -> FakeNormalizationConnection:
        return connection

    monkeypatch.setattr(normalization, "_open_raw_connection", fake_open_raw_connection)

    await normalization.run_normalization(
        batch_id="batch-synthetic",
        tenant_id=tenant_id,
        schema_name="raw_legacy",
    )

    product_copy = next(
        call for call in connection.copy_calls if call["table_name"] == "normalized_products"
    )
    copied_rows = [dict(zip(product_copy["columns"], row, strict=False)) for row in product_copy["rows"]]

    assert {row["legacy_code"] for row in copied_rows} == {"PC096"}


@pytest.mark.asyncio
async def test_run_normalization_rejects_inventory_rows_without_matching_product(
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
                    "legacy_category": None,
                    "stock_kind": "0",
                    "supplier_code": "S001",
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
        },
        stage_run_rows=[
            {
                "tenant_id": uuid.UUID("00000000-0000-0000-0000-000000000321"),
                "status": "completed",
                "batch_id": "batch-002",
                "target_schema": "raw_legacy",
            }
        ],
    )

    async def fake_open_raw_connection() -> FakeNormalizationConnection:
        return connection

    monkeypatch.setattr(normalization, "_open_raw_connection", fake_open_raw_connection)

    with pytest.raises(
        ValueError,
        match="Inventory rows reference products missing from the staged product set: P001",
    ):
        await normalization.run_normalization(
            batch_id="batch-002",
            tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000321"),
            schema_name="raw_legacy",
        )

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
