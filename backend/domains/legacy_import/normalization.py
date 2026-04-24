"""Legacy master-data normalization helpers."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping, Sequence

from common.config import settings
from common.tenant import DEFAULT_TENANT_ID
from domains.legacy_import.shared import (
    coerce_mapping as _coerce_mapping,
)
from domains.legacy_import.shared import (
    execute_many as _execute_many,
)
from domains.legacy_import.staging import _open_raw_connection, _quoted_identifier
from scripts.legacy_refresh_common import RefreshBatchMode

_NAMESPACE = uuid.UUID("4e59177d-61e5-48f4-b1f8-6b2141739ab9")
_DEFAULT_WAREHOUSE_CODE = "LEGACY_DEFAULT"
_DEFAULT_WAREHOUSE_NAME = "Legacy Default Warehouse"
_KNOWN_WAREHOUSE_NAMES = {
    "A": "Legacy General Warehouse (總倉)",
}
_NON_MERCHANDISE_CATEGORY = "Non-Merchandise"
_NON_MERCHANDISE_CODE_PREFIXES = ("PK-",)
_NON_MERCHANDISE_NAME_TOKENS = (
    "運費",
    "郵寄",
    "到付",
    "折讓",
    "寄員客",
    "出貨單",
    "帳單本",
    "信封",
    "原廠碳粉",
    "原廠色帶",
    "報表紙",
    "紙套",
)
_BELT_SUPPLIES_NAME_TOKENS = ("現場接頭", "皮帶勾")
_VARIABLE_SPEED_NAME_TOKENS = ("變速皮帶", "變速帶")
_RIBBED_NAME_TOKENS = ("多溝", "POLY")
_TIMING_NAME_TOKENS = (
    "齒帶",
    "同步帶",
    "RPP",
    "HTD",
    "AT10",
    "AT20",
    "AT5",
    "T10",
    "T5",
    "OPEN",
)
_VEHICLE_NAME_TOKENS = ("機車帶", "凌風", "勁風", "豪邁", "歐風")
_V_BELT_NAME_TOKENS = (
    "三角皮帶",
    " SPA",
    " SPB",
    " SPC",
    " SPZ",
    " XPA",
    " XPB",
    " XPZ",
    "OH A-",
    "OH B-",
    "OH C-",
    "OH D-",
    "OH A",
    "OH B",
    "OH C",
    "OH D",
    "OH M",
    "阪東",
    "德國馬牌",
    "大山 K-",
    "大山 A",
    "大山 B",
    "大山 C",
    "大山皮帶",
    "第一 B",
    "外齒",
)
_V_BELT_SECTION_CONTEXT_TOKENS = ("皮帶", "耐油", "耐熱", "齒型", "大山", "三五", "三星")
_FLAT_SPECIALTY_NAME_TOKENS = (
    "牛皮",
    "平皮帶",
    "平面帶",
    "輸送帶",
    "片基帶",
    "廣角",
    "無端皮帶",
    "鐵氟龍帶",
    "花紋帶",
    "圓綠帶",
    "圓型橘色帶",
    "圓形橘色帶",
    "打孔帶",
    "關結帶",
    "V-LINK",
)
_VARIABLE_SPEED_CODE_PREFIXES = ("VB", "VD", "YM", "YK", "MF", "VS")
_RIBBED_CODE_PREFIXES = ("J4", "J5", "J6", "J8")
_RIBBED_SERIES_RE = re.compile(
    r"^(?:\d+(?:PK|PL|PJ)-|PK\d+-|J\d+(?:-|$)|\d+J(?:-|$)|\d+-J\d+)"
)
_TIMING_CODE_PREFIXES = (
    "RL",
    "RH",
    "XL",
    "MXL",
    "XH",
    "DXL",
    "DH",
    "DL",
    "S2M",
    "S3M",
    "S5M",
    "S8M",
    "S14M",
    "5GT",
    "8GT",
    "3GT",
    "14MGT",
    "8YU",
)
_TIMING_SERIES_RE = re.compile(
    r"^(?:(?:S)?\d{1,2}(?:\.\d+)?M(?:[-*]|$)|\d+XL(?:[-*]|$)"
    r"|\d+H(?:[-*]|$)|\d+GT(?:[-* ]|$)|\d+-\d+M(?:[-*]|$))"
)
_TIMING_PITCH_RE = re.compile(r"(?:^| )(?:S)?\d{1,2}(?:\.\d+)?M(?:[-*]|$)")
_TIMING_FAMILY_RE = re.compile(
    r"^(?:H\d+-|L(?:\d|-[0-9])|LS-|PU\d+(?:XL|L)|225L|240L|R240L|T2\.5|U10|YU\d+)"
)
_VEHICLE_CODE_PREFIXES = ("BMT", "MBT", "3NW", "3GF", "SRCV", "AVX", "17641")
_V_BELT_CODE_PREFIXES = (
    "PA",
    "PB",
    "PC",
    "PD",
    "SPA",
    "SPB",
    "SPC",
    "SPZ",
    "XPA",
    "XPB",
    "XPZ",
    "AO",
    "BO",
    "OB",
    "PSPA",
    "PSPB",
    "PSPC",
    "PSPZ",
    "P3V",
    "P5V",
    "RB",
    "LK",
    "LA",
    "LF",
    "LM",
    "LC",
    "MO",
    "XPC",
    "LINK",
)
_V_BELT_SPECIAL_CODE_PREFIXES = ("OA", "OM", "OC", "VA", "AA", "BB", "AX", "BR")
_V_BELT_FAMILY_RE = re.compile(r"^(?:FON|FOZ(?:\s|$)|FO037$)")
_FLAT_SPECIALTY_CODE_PREFIXES = (
    "TU",
    "VT",
    "LG",
    "A2LT",
    "T1",
    "LLN",
    "FL",
    "SE-",
    "LPS",
    "NVT",
    "HS",
    "PVC",
    "XVT",
    "CFL",
)
_FLAT_SPECIALTY_SERIES_RE = re.compile(r"^(?:\d+-TU\d+|[AB]-V-LINK|A-[23]LT(?:\s|-))")
_FLAT_SPECIALTY_FAMILY_RE = re.compile(
    r"^(?:F-\d|G-\d|FK(?:\s|[-]|$)|TS-|PV10|HAM-|S-\d|SP(?:100|180|250)|SE15|S250|TC20|ENU)"
)
_BELT_SUPPLIES_CODE_PREFIXES = ("PPPP",)
_V_BELT_SERIES_RE = re.compile(r"^(?:[358]V|[ABCDM]O?\d|HA\d)")
_V_BELT_SECTION_NAME_RE = re.compile(r"(?:LA|[ABCDE])-?\d+")
_CATEGORY_REVIEW_CONFIDENCE_THRESHOLD = Decimal("0.80")
_MATCHING_NOISE_TOKENS = ("進口",)
_MATCHING_TEXT_RE = re.compile(r"[^A-Z0-9\u4E00-\u9FFF]+")
_LEGACY_IMPORT_CONTROL_SCHEMA = "public"

#: Story 15.25: Master domains that normalization can carry forward from prior
#: successful batches. These domains are the foundational entities that
#: document domains (sales, purchase-invoices) depend on.
_MASTER_NORMALIZATION_DOMAINS = frozenset(
    {"parties", "products", "warehouses", "inventory"}
)

#: Story 15.25: Metadata for scoped incremental normalization.
#: Maps each master domain to (table_name, column_tuple, primary_key_columns).
#: This enables carryforward to rewrite batch_id in the correct table with
#: the correct composite key columns.
_INCREMENTAL_NORMALIZED_TABLE_META: dict[
    str, tuple[str, tuple[str, ...], tuple[str, ...]]
] = {
    "parties": (
        "normalized_parties",
        (
            "batch_id",
            "tenant_id",
            "deterministic_id",
            "legacy_code",
            "legacy_type",
            "role",
            "company_name",
            "short_name",
            "tax_id",
            "full_address",
            "address",
            "phone",
            "email",
            "contact_person",
            "is_active",
            "created_date",
            "updated_date",
            "customer_type",
            "source_table",
            "source_row_number",
        ),
        ("tenant_id", "role", "legacy_code"),
    ),
    "products": (
        "normalized_products",
        (
            "batch_id",
            "tenant_id",
            "deterministic_id",
            "legacy_code",
            "name",
            "category",
            "legacy_category",
            "stock_kind",
            "category_source",
            "category_rule_id",
            "category_confidence",
            "supplier_legacy_code",
            "supplier_deterministic_id",
            "origin",
            "unit",
            "status",
            "created_date",
            "last_sale_date",
            "avg_cost",
            "source_table",
            "source_row_number",
        ),
        ("tenant_id", "legacy_code"),
    ),
    "warehouses": (
        "normalized_warehouses",
        (
            "batch_id",
            "tenant_id",
            "deterministic_id",
            "legacy_code",
            "code",
            "name",
            "location",
            "address",
            "source_kind",
            "source_table",
            "source_row_number",
        ),
        ("tenant_id", "code"),
    ),
    "inventory": (
        "normalized_inventory_prep",
        (
            "batch_id",
            "tenant_id",
            "product_deterministic_id",
            "warehouse_deterministic_id",
            "product_legacy_code",
            "warehouse_code",
            "quantity_on_hand",
            "reorder_point",
            "source_table",
            "source_row_number",
        ),
        ("tenant_id", "product_legacy_code", "warehouse_code"),
    ),
}


@dataclass(slots=True, frozen=True)
class NormalizationBatchResult:
    batch_id: str
    schema_name: str
    party_count: int
    product_count: int
    warehouse_count: int
    inventory_count: int
    # Story 15.25: tracks which prior batch ids were used for carryforward
    reused_from_batch_ids: dict[str, int] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class CategoryDerivation:
    category: str | None
    source: str
    rule_id: str
    confidence: Decimal


def deterministic_legacy_uuid(kind: str, *parts: str) -> uuid.UUID:
    joined = ":".join(part.strip() for part in parts if part and part.strip())
    if not joined:
        raise ValueError(f"Cannot build deterministic UUID without parts for {kind}")
    return uuid.uuid5(_NAMESPACE, f"{kind}:{joined}")


def normalize_legacy_date(value: object | None) -> date | None:
    if value is None:
        return None

    raw = str(value).strip()
    if raw in {"", "0", "1900-01-01"}:
        return None

    if len(raw) == 10 and raw.isdigit():
        return date(int(raw[0:3]) + 1911, int(raw[3:5]), int(raw[5:7]))

    if len(raw) == 8 and raw.isdigit():
        return date(int(raw[0:2]) + 1911, int(raw[2:4]), int(raw[4:6]))

    if len(raw) == 10 and raw[4] == "-" and raw[7] == "-":
        return date.fromisoformat(raw)

    raise ValueError(f"Unsupported legacy date value: {raw}")


def _normalize_status(value: object | None) -> bool:
    raw = str(value or "").strip().upper()
    return raw in {"A", "ACTIVE", "1", "Y", "TRUE"}


def _normalize_text(value: object | None) -> str | None:
    raw = str(value or "").strip()
    return raw or None


def _normalize_decimal(value: object | None) -> Decimal | None:
    if value is None:
        return None
    raw = str(value).strip()
    if raw in {"", "0", "0.0", "0.00"}:
        return Decimal("0") if raw else None
    try:
        return Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError(f"Invalid decimal value: {raw}") from exc


def _normalize_warehouse_code(value: object | None) -> str:
    raw = str(value or "").strip()
    return raw or _DEFAULT_WAREHOUSE_CODE


def _warehouse_name_for_code(code: str) -> str:
    normalized_code = _normalize_warehouse_code(code)
    if normalized_code == _DEFAULT_WAREHOUSE_CODE:
        return _DEFAULT_WAREHOUSE_NAME
    return _KNOWN_WAREHOUSE_NAMES.get(normalized_code, f"Legacy Warehouse {normalized_code}")


def _contains_any_token(text: str, tokens: tuple[str, ...]) -> bool:
    return any(token in text for token in tokens)


def _starts_with_any_prefix(text: str, prefixes: tuple[str, ...]) -> bool:
    return any(text.startswith(prefix) for prefix in prefixes)


def _clean_product_text_for_matching(value: str) -> str:
    cleaned = _MATCHING_TEXT_RE.sub(" ", value.strip().upper())
    for token in _MATCHING_NOISE_TOKENS:
        cleaned = cleaned.replace(token, " ")
    return " ".join(cleaned.split())


def _category_derivation(
    category: str | None,
    source: str,
    rule_id: str,
    confidence: str,
) -> CategoryDerivation:
    return CategoryDerivation(
        category=category,
        source=source,
        rule_id=rule_id,
        confidence=Decimal(confidence),
    )


def _manual_override_derivation(category: str) -> CategoryDerivation:
    return _category_derivation(category, "manual_override", "manual-override", "1.00")


def _derive_product_category(
    legacy_code: str,
    name: str,
    *,
    legacy_category: str | None,
    stock_kind: str | None,
) -> CategoryDerivation:
    normalized_stock_kind = _normalize_text(stock_kind)
    if normalized_stock_kind == "6":
        return _category_derivation(
            _NON_MERCHANDISE_CATEGORY,
            "exclusion_rule",
            "stock-kind-non-merchandise",
            "1.00",
        )

    normalized_code = legacy_code.upper()
    raw_combined = f"{normalized_code} {name.upper()}".strip()
    cleaned_name = _clean_product_text_for_matching(name)
    combined = f"{normalized_code} {cleaned_name}".strip()

    if _starts_with_any_prefix(normalized_code, _NON_MERCHANDISE_CODE_PREFIXES):
        return _category_derivation(
            _NON_MERCHANDISE_CATEGORY,
            "exclusion_rule",
            "code-prefix-non-merchandise",
            "0.98",
        )

    if _contains_any_token(combined, _NON_MERCHANDISE_NAME_TOKENS):
        return _category_derivation(
            _NON_MERCHANDISE_CATEGORY,
            "exclusion_rule",
            "name-token-non-merchandise",
            "0.95",
        )

    if _starts_with_any_prefix(normalized_code, _BELT_SUPPLIES_CODE_PREFIXES):
        return _category_derivation(
            "Belt Supplies",
            "heuristic_rule",
            "code-prefix-belt-supplies",
            "0.98",
        )
    if "皮帶" in combined and _contains_any_token(cleaned_name, _BELT_SUPPLIES_NAME_TOKENS):
        return _category_derivation(
            "Belt Supplies",
            "heuristic_rule",
            "name-token-belt-supplies",
            "0.90",
        )

    if _starts_with_any_prefix(normalized_code, _VARIABLE_SPEED_CODE_PREFIXES):
        return _category_derivation(
            "Variable-Speed Belts",
            "heuristic_rule",
            "code-prefix-variable-speed-belts",
            "0.98",
        )
    if _contains_any_token(combined, _VARIABLE_SPEED_NAME_TOKENS):
        return _category_derivation(
            "Variable-Speed Belts",
            "heuristic_rule",
            "name-token-variable-speed-belts",
            "0.90",
        )

    if (
        _starts_with_any_prefix(normalized_code, _RIBBED_CODE_PREFIXES)
        or _RIBBED_SERIES_RE.match(normalized_code) is not None
        or any(token in combined for token in ("-J4", "-J5", "-J6", "-J8"))
    ):
        return _category_derivation(
            "Ribbed Belts",
            "heuristic_rule",
            "code-prefix-ribbed-belts",
            "0.98",
        )
    if _contains_any_token(combined, _RIBBED_NAME_TOKENS):
        return _category_derivation(
            "Ribbed Belts",
            "heuristic_rule",
            "name-token-ribbed-belts",
            "0.90",
        )

    if (
        _starts_with_any_prefix(normalized_code, _TIMING_CODE_PREFIXES)
        or _TIMING_SERIES_RE.match(normalized_code) is not None
        or _TIMING_PITCH_RE.search(raw_combined) is not None
        or _TIMING_FAMILY_RE.match(normalized_code) is not None
        or any(token in normalized_code for token in ("5GT", "8GT", "3GT", "14MGT", "RPP", "8YU"))
        or any(token in combined for token in ("5M-", "8M-", "14M-", "3M-"))
    ):
        return _category_derivation(
            "Timing Belts",
            "heuristic_rule",
            "code-prefix-timing-belts",
            "0.98",
        )
    if _contains_any_token(combined, _TIMING_NAME_TOKENS):
        return _category_derivation(
            "Timing Belts",
            "heuristic_rule",
            "name-token-timing-belts",
            "0.90",
        )

    if (
        _starts_with_any_prefix(normalized_code, _VEHICLE_CODE_PREFIXES)
    ):
        return _category_derivation(
            "Vehicle Belts",
            "heuristic_rule",
            "code-prefix-vehicle-belts",
            "0.98",
        )
    if _contains_any_token(combined, _VEHICLE_NAME_TOKENS):
        return _category_derivation(
            "Vehicle Belts",
            "heuristic_rule",
            "name-token-vehicle-belts",
            "0.90",
        )

    if (
        _starts_with_any_prefix(normalized_code, _V_BELT_CODE_PREFIXES)
        or _starts_with_any_prefix(normalized_code, _V_BELT_SPECIAL_CODE_PREFIXES)
        or _V_BELT_SERIES_RE.match(normalized_code) is not None
        or _V_BELT_FAMILY_RE.match(normalized_code) is not None
    ):
        return _category_derivation(
            "V-Belts",
            "heuristic_rule",
            "code-prefix-v-belts",
            "0.98",
        )
    if (
        _contains_any_token(combined, _V_BELT_NAME_TOKENS)
        or any(token in combined for token in ("3V", "5V", "8V"))
        or (
            _V_BELT_SECTION_NAME_RE.search(combined) is not None
            and any(token in combined for token in _V_BELT_SECTION_CONTEXT_TOKENS)
        )
    ):
        return _category_derivation(
            "V-Belts",
            "heuristic_rule",
            "name-token-v-belts",
            "0.90",
        )

    if (
        _starts_with_any_prefix(normalized_code, _FLAT_SPECIALTY_CODE_PREFIXES)
        or _FLAT_SPECIALTY_SERIES_RE.match(normalized_code) is not None
        or _FLAT_SPECIALTY_FAMILY_RE.match(normalized_code) is not None
    ):
        return _category_derivation(
            "Flat / Specialty Belts",
            "heuristic_rule",
            "code-prefix-flat-specialty-belts",
            "0.98",
        )
    if _contains_any_token(combined, _FLAT_SPECIALTY_NAME_TOKENS):
        return _category_derivation(
            "Flat / Specialty Belts",
            "heuristic_rule",
            "name-token-flat-specialty-belts",
            "0.90",
        )

    return _category_derivation(
        "Other Power Transmission",
        "fallback_rule",
        "fallback-other-power-transmission",
        "0.40",
    )


def _resolve_product_category(
    record: Mapping[str, object],
    *,
    category_overrides: Mapping[str, dict[str, object]] | None = None,
) -> CategoryDerivation:
    legacy_code = str(record.get("legacy_code") or "").strip()
    name = str(record.get("name") or legacy_code).strip()
    override = (category_overrides or {}).get(legacy_code)
    if override:
        override_category = _normalize_text(override.get("category"))
        if override_category:
            return _manual_override_derivation(override_category)

    legacy_category = _normalize_text(record.get("legacy_category"))
    stock_kind = _normalize_text(record.get("stock_kind"))
    return _derive_product_category(
        legacy_code,
        name,
        legacy_category=legacy_category,
        stock_kind=stock_kind,
    )


def _review_reason_for_derivation(derivation: CategoryDerivation) -> str | None:
    if derivation.source == "manual_override":
        return None
    if derivation.source == "fallback_rule":
        return "fallback_assignment"
    if derivation.source == "exclusion_rule":
        return "excluded_path"
    if derivation.confidence < _CATEGORY_REVIEW_CONFIDENCE_THRESHOLD:
        return "low_confidence"
    return None


def normalize_party_record(
    record: Mapping[str, object],
    batch_id: str,
    tenant_id: uuid.UUID,
) -> tuple:
    legacy_type = str(record.get("legacy_type") or "").strip()
    role = {"1": "supplier", "2": "customer"}.get(legacy_type, "unknown")
    legacy_code = str(record.get("legacy_code") or "").strip()
    if not legacy_code:
        raise ValueError("Party record missing legacy_code")

    company_name = str(
        record.get("company_name") or record.get("short_name") or legacy_code
    ).strip()
    short_name = str(record.get("short_name") or "").strip() or None
    full_address = str(record.get("full_address") or "").strip() or None
    address = str(record.get("address") or full_address or "").strip() or None
    email = str(record.get("email") or "").strip() or None
    contact_person = str(record.get("contact_person") or "").strip() or None
    phone = str(record.get("phone") or "").strip() or None
    tax_id = str(record.get("tax_id") or "").strip() or None
    return (
        batch_id,
        tenant_id,
        deterministic_legacy_uuid("party", role, legacy_code),
        legacy_code,
        legacy_type or None,
        role,
        company_name,
        short_name,
        tax_id,
        full_address,
        address,
        phone,
        email,
        contact_person,
        _normalize_status(record.get("status_code") or record.get("record_status")),
        normalize_legacy_date(record.get("created_date")),
        normalize_legacy_date(record.get("updated_date")),
        "unknown",
        "tbscust",
        int(record.get("source_row_number") or 0),
    )


def _normalize_product_record(
    record: Mapping[str, object],
    batch_id: str,
    tenant_id: uuid.UUID,
    *,
    category_derivation: CategoryDerivation | None = None,
) -> tuple:
    legacy_code = str(record.get("legacy_code") or "").strip()
    if not legacy_code:
        raise ValueError("Product record missing legacy_code")

    name = str(record.get("name") or legacy_code).strip()
    legacy_category = _normalize_text(record.get("legacy_category"))
    stock_kind = _normalize_text(record.get("stock_kind"))
    if category_derivation is None:
        category_derivation = _resolve_product_category(record)
    supplier_code = _normalize_text(record.get("supplier_code"))
    supplier_id = (
        deterministic_legacy_uuid("party", "supplier", supplier_code) if supplier_code else None
    )
    return (
        batch_id,
        tenant_id,
        deterministic_legacy_uuid("product", legacy_code),
        legacy_code,
        name,
        category_derivation.category,
        legacy_category,
        stock_kind,
        category_derivation.source,
        category_derivation.rule_id,
        category_derivation.confidence,
        supplier_code,
        supplier_id,
        _normalize_text(record.get("origin")),
        str(record.get("unit") or "pcs").strip() or "pcs",
        str(record.get("status") or "A").strip() or "A",
        normalize_legacy_date(record.get("created_date")),
        normalize_legacy_date(record.get("last_sale_date")),
        _normalize_decimal(record.get("avg_cost")),
        "tbsstock",
        int(record.get("source_row_number") or 0),
    )


def _normalized_warehouse_record(
    batch_id: str,
    tenant_id: uuid.UUID,
    warehouse_code: object | None,
    *,
    source_row_number: int,
) -> tuple:
    normalized_code = _normalize_warehouse_code(warehouse_code)
    warehouse_id = deterministic_legacy_uuid("warehouse", normalized_code)
    return (
        batch_id,
        tenant_id,
        warehouse_id,
        None,
        normalized_code,
        _warehouse_name_for_code(normalized_code),
        None,
        None,
        "legacy-stock",
        "tbsstkhouse",
        source_row_number,
    )


def _normalized_warehouse_records(
    inventory_rows: list[Mapping[str, object]],
    batch_id: str,
    tenant_id: uuid.UUID,
) -> list[tuple]:
    source_row_by_code: dict[str, int] = {}
    for row in inventory_rows:
        warehouse_code = _normalize_warehouse_code(row.get("warehouse_code"))
        source_row_by_code.setdefault(warehouse_code, int(row.get("source_row_number") or 0))

    return [
        _normalized_warehouse_record(
            batch_id,
            tenant_id,
            warehouse_code,
            source_row_number=source_row_by_code[warehouse_code],
        )
        for warehouse_code in sorted(source_row_by_code)
    ]


def _normalize_inventory_record(
    record: Mapping[str, object],
    batch_id: str,
    tenant_id: uuid.UUID,
) -> tuple:
    product_code = str(record.get("product_code") or "").strip()
    if not product_code:
        raise ValueError("Inventory record missing product_code")

    warehouse_code = _normalize_warehouse_code(record.get("warehouse_code"))
    warehouse_id = deterministic_legacy_uuid("warehouse", warehouse_code)
    return (
        batch_id,
        tenant_id,
        deterministic_legacy_uuid("product", product_code),
        warehouse_id,
        product_code,
        warehouse_code,
        _normalize_decimal(record.get("qty_on_hand")) or Decimal("0"),
        0,
        "tbsstkhouse",
        int(record.get("source_row_number") or 0),
    )


async def _fetch_category_overrides(
    connection,
    schema_name: str,
    tenant_id: uuid.UUID,
) -> dict[str, dict[str, object]]:
    quoted_schema = _quoted_identifier(schema_name)
    rows = await connection.fetch(
        f"""
        SELECT legacy_code, category, review_notes, approval_source, approved_by, approved_at
        FROM {quoted_schema}.product_category_override
        WHERE tenant_id = $1
        """,
        tenant_id,
    )
    return {
        str(_coerce_mapping(row)["legacy_code"]): _coerce_mapping(row)
        for row in rows
        if str(_coerce_mapping(row).get("legacy_code") or "").strip()
    }


async def _replace_product_category_review_candidates(
    connection,
    schema_name: str,
    batch_id: str,
    tenant_id: uuid.UUID,
    review_candidates: tuple[tuple[object, ...], ...],
) -> None:
    quoted_schema = _quoted_identifier(schema_name)
    review_rows = [
        (tenant_id, batch_id, *review_candidate) for review_candidate in review_candidates
    ]
    await _execute_many(
        connection,
        f"""
        INSERT INTO {quoted_schema}.product_category_review_candidates (
            tenant_id,
            batch_id,
            legacy_code,
            name,
            legacy_category,
            stock_kind,
            current_category,
            category_source,
            category_rule_id,
            category_confidence,
            review_reason,
            source_table,
            source_row_number
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
        ON CONFLICT (tenant_id, batch_id, legacy_code) DO UPDATE SET
            name = EXCLUDED.name,
            legacy_category = EXCLUDED.legacy_category,
            stock_kind = EXCLUDED.stock_kind,
            current_category = EXCLUDED.current_category,
            category_source = EXCLUDED.category_source,
            category_rule_id = EXCLUDED.category_rule_id,
            category_confidence = EXCLUDED.category_confidence,
            review_reason = EXCLUDED.review_reason,
            source_table = EXCLUDED.source_table,
            source_row_number = EXCLUDED.source_row_number,
            updated_at = NOW()
        """,
        review_rows,
    )


async def _ensure_staged_batch_ready(
    connection,
    schema_name: str,
    batch_id: str,
    tenant_id: uuid.UUID,
) -> None:
    rows = await connection.fetch(
        f"""
        SELECT runs.tenant_id, runs.status
        FROM {_LEGACY_IMPORT_CONTROL_SCHEMA}.legacy_import_runs AS runs
        WHERE runs.batch_id = $1
          AND runs.target_schema = $2
          AND EXISTS (
              SELECT 1
              FROM {_LEGACY_IMPORT_CONTROL_SCHEMA}.legacy_import_table_runs AS table_runs
              WHERE table_runs.run_id = runs.id
          )
        ORDER BY runs.started_at DESC, runs.created_at DESC
        LIMIT 1
        """,
        batch_id,
        schema_name,
    )
    if not rows:
        raise ValueError(
            f"No staged batch metadata found for batch {batch_id} in schema {schema_name}"
        )

    batch_metadata = _coerce_mapping(rows[0])
    batch_tenant = batch_metadata.get("tenant_id")
    batch_tenant_id = (
        batch_tenant
        if isinstance(batch_tenant, uuid.UUID)
        else uuid.UUID(str(batch_tenant))
    )
    batch_status = str(batch_metadata.get("status") or "").strip().lower()

    if batch_tenant_id != tenant_id:
        raise ValueError(
            f"Batch {batch_id} belongs to tenant {batch_tenant_id}, not {tenant_id}"
        )
    if batch_status != "completed":
        raise ValueError(
            f"Latest staged batch {batch_id} for tenant {tenant_id} is not completed"
        )


async def _ensure_normalized_tables(connection, schema_name: str) -> None:
    quoted_schema = _quoted_identifier(schema_name)
    quoted_products = _quoted_identifier("normalized_products")
    await connection.execute(
        f"""
		CREATE TABLE IF NOT EXISTS {quoted_schema}.normalized_parties (
			batch_id TEXT NOT NULL,
			tenant_id UUID NOT NULL,
			deterministic_id UUID NOT NULL,
			legacy_code TEXT NOT NULL,
			legacy_type TEXT,
			role TEXT NOT NULL,
			company_name TEXT NOT NULL,
			short_name TEXT,
			tax_id TEXT,
			full_address TEXT,
			address TEXT,
			phone TEXT,
			email TEXT,
			contact_person TEXT,
			is_active BOOLEAN NOT NULL,
			created_date DATE,
			updated_date DATE,
            customer_type TEXT NOT NULL,
			source_table TEXT NOT NULL,
			source_row_number INTEGER NOT NULL,
			PRIMARY KEY (tenant_id, batch_id, role, legacy_code)
		)
		"""
    )
    await connection.execute(
        "ALTER TABLE "
        f"{quoted_schema}.normalized_parties "
        "ADD COLUMN IF NOT EXISTS customer_type TEXT NOT NULL DEFAULT 'unknown'"
    )
    await connection.execute(
        f"""
		CREATE TABLE IF NOT EXISTS {quoted_schema}.normalized_products (
			batch_id TEXT NOT NULL,
			tenant_id UUID NOT NULL,
			deterministic_id UUID NOT NULL,
			legacy_code TEXT NOT NULL,
			name TEXT NOT NULL,
			category TEXT,
			legacy_category TEXT,
			stock_kind TEXT,
			category_source TEXT,
			supplier_legacy_code TEXT,
			supplier_deterministic_id UUID,
			origin TEXT,
			unit TEXT NOT NULL,
			status TEXT NOT NULL,
			created_date DATE,
			last_sale_date DATE,
			avg_cost NUMERIC(20, 4),
			source_table TEXT NOT NULL,
			source_row_number INTEGER NOT NULL,
			PRIMARY KEY (tenant_id, batch_id, legacy_code)
		)
		"""
    )
    await connection.execute(
        "ALTER TABLE "
        f"{quoted_schema}.{quoted_products} "
        "ADD COLUMN IF NOT EXISTS legacy_category TEXT"
    )
    await connection.execute(
        "ALTER TABLE "
        f"{quoted_schema}.{quoted_products} "
        "ADD COLUMN IF NOT EXISTS stock_kind TEXT"
    )
    await connection.execute(
        "ALTER TABLE "
        f"{quoted_schema}.{quoted_products} "
        "ADD COLUMN IF NOT EXISTS category_source TEXT"
    )
    await connection.execute(
        "ALTER TABLE "
        f"{quoted_schema}.{quoted_products} "
        "ADD COLUMN IF NOT EXISTS category_rule_id TEXT"
    )
    await connection.execute(
        "ALTER TABLE "
        f"{quoted_schema}.{quoted_products} "
        "ADD COLUMN IF NOT EXISTS category_confidence NUMERIC(5, 2)"
    )
    await connection.execute(
        f"""
		CREATE TABLE IF NOT EXISTS {quoted_schema}.normalized_warehouses (
			batch_id TEXT NOT NULL,
			tenant_id UUID NOT NULL,
			deterministic_id UUID NOT NULL,
			legacy_code TEXT,
			code TEXT NOT NULL,
			name TEXT NOT NULL,
			location TEXT,
			address TEXT,
			source_kind TEXT NOT NULL,
			source_table TEXT NOT NULL,
			source_row_number INTEGER NOT NULL,
			PRIMARY KEY (tenant_id, batch_id, code)
		)
		"""
    )
    await connection.execute(
        f"""
		CREATE TABLE IF NOT EXISTS {quoted_schema}.normalized_inventory_prep (
			batch_id TEXT NOT NULL,
			tenant_id UUID NOT NULL,
			product_deterministic_id UUID NOT NULL,
			warehouse_deterministic_id UUID NOT NULL,
			product_legacy_code TEXT NOT NULL,
			warehouse_code TEXT NOT NULL,
			quantity_on_hand NUMERIC(20, 4) NOT NULL,
			reorder_point INTEGER NOT NULL,
			source_table TEXT NOT NULL,
			source_row_number INTEGER NOT NULL,
			PRIMARY KEY (tenant_id, batch_id, product_legacy_code, warehouse_code)
		)
		"""
    )


async def _clear_batch_rows(
    connection,
    schema_name: str,
    batch_id: str,
    tenant_id: uuid.UUID,
) -> None:
    quoted_schema = _quoted_identifier(schema_name)
    for table_name in (
        "product_category_review_candidates",
        "normalized_inventory_prep",
        "normalized_warehouses",
        "normalized_products",
        "normalized_parties",
    ):
        quoted_table = _quoted_identifier(table_name)
        await connection.execute(
            f"DELETE FROM {quoted_schema}.{quoted_table} WHERE batch_id = $1 AND tenant_id = $2",
            batch_id,
            tenant_id,
        )


#: Story 15.25: Deletion order respects FK ordering for scoped batches.
#: Dependents must be deleted before their dependencies to avoid constraint
#: violations. This mirrors the ordering in _clear_batch_rows but scoped.
_SCOPED_DELETE_ORDER = (
    "normalized_inventory_prep",  # depends on products + warehouses
    "product_category_review_candidates",  # depends on products
    "normalized_warehouses",
    "normalized_products",
    "normalized_parties",
)


async def _clear_scoped_batch_rows(
    connection,
    schema_name: str,
    batch_id: str,
    tenant_id: uuid.UUID,
    scoped_domains: frozenset[str],
) -> None:
    """Story 15.25: Delete normalized rows for scoped domains only.

    Unlike ``_clear_batch_rows`` which deletes all normalized rows for the
    batch, this function only clears the tables corresponding to the domains
    in ``scoped_domains``. This enables incremental normalization to replace
    only the impacted domains while leaving unrelated domains untouched.

    Args:
        connection: Database connection.
        schema_name: Target schema.
        batch_id: Current batch id being processed.
        tenant_id: Tenant for scope.
        scoped_domains: Set of domain names to clear (subset of master domains).
    """
    quoted_schema = _quoted_identifier(schema_name)
    for table_name in _SCOPED_DELETE_ORDER:
        domain_for_table = _domain_for_normalized_table(table_name)
        if domain_for_table not in scoped_domains:
            continue
        quoted_table = _quoted_identifier(table_name)
        await connection.execute(
            f"DELETE FROM {quoted_schema}.{quoted_table} WHERE batch_id = $1 AND tenant_id = $2",
            batch_id,
            tenant_id,
        )


def _domain_for_normalized_table(table_name: str) -> str | None:
    """Return the master domain that owns a normalized table.

    Returns None if the table is not a scoped master-domain table.
    product_category_review_candidates is tied to the products domain.
    """
    mapping = {
        "normalized_parties": "parties",
        "normalized_products": "products",
        "normalized_warehouses": "warehouses",
        "normalized_inventory_prep": "inventory",
        "product_category_review_candidates": "products",
    }
    return mapping.get(table_name)


async def _carry_forward_prior_batch(
    connection,
    schema_name: str,
    domain: str,
    *,
    current_batch_id: str,
    prior_batch_id: str,
    tenant_id: uuid.UUID,
) -> int:
    """Story 15.25: Reuse normalized rows from the last successful prior batch.

    When incremental normalization scopes to a subset of domains, unchanged
    master entities that are still needed by the scoped batch (e.g., products
    required by a scoped sales invoice) must be available. Instead of forcing
    a full restage of unchanged data, this function copies rows from the
    prior successful batch into the current batch's normalized tables.

    The copy is an INSERT ... SELECT with NOT EXISTS on the composite key columns
    so rows already present in the current batch (from fresh staging) are not
    duplicated.

    Args:
        connection: Database connection.
        schema_name: Target schema.
        domain: Master domain being carried forward.
        current_batch_id: The incremental batch id receiving the carryforward.
        prior_batch_id: The last successful batch to copy from.
        tenant_id: Tenant scope.

    Returns:
        The number of rows copied from the prior batch.
    """
    if domain not in _INCREMENTAL_NORMALIZED_TABLE_META:
        return 0

    table_name, columns, key_columns = _INCREMENTAL_NORMALIZED_TABLE_META[domain]
    quoted_schema = _quoted_identifier(schema_name)
    quoted_table = _quoted_identifier(table_name)

    # Rewrite batch_id from prior to current; preserve all other columns.
    # Use NOT EXISTS so fresh-staged rows take precedence.
    select_columns = ["$1" if col == "batch_id" else f"prior.\"{col}\"" for col in columns]
    not_exists_conditions = [f'current."{kc}" = prior."{kc}"' for kc in key_columns]

    query = f"""
        INSERT INTO {quoted_schema}.{quoted_table} ({', '.join(f'"{c}"' for c in columns)})
        SELECT {', '.join(select_columns)}
        FROM {quoted_schema}.{quoted_table} AS prior
        WHERE prior.batch_id = $3
          AND prior.tenant_id = $2
          AND NOT EXISTS (
              SELECT 1
              FROM {quoted_schema}.{quoted_table} AS current
              WHERE {' AND '.join(not_exists_conditions)}
          )
    """

    result = await connection.execute(query, current_batch_id, tenant_id, prior_batch_id)

    # Parse INSERT N rows output.
    if result.startswith("INSERT 0 "):
        try:
            return int(result.split()[2])
        except (IndexError, ValueError):
            return 0
    return 0


async def _fetch_stage_rows(
    connection,
    schema_name: str,
    table_name: str,
    select_sql: str,
    batch_id: str,
):
    quoted_schema = _quoted_identifier(schema_name)
    quoted_table = _quoted_identifier(table_name)
    query = (
        f"SELECT {select_sql} FROM {quoted_schema}.{quoted_table} "
        f"WHERE _batch_id = $1 ORDER BY _source_row_number"
    )
    return await connection.fetch(query, batch_id)


async def _fetch_existing_synthetic_product_records(
    connection,
    schema_name: str,
    batch_id: str,
    tenant_id: uuid.UUID,
) -> list[tuple[object, ...]]:
    quoted_schema = _quoted_identifier(schema_name)
    quoted_table = _quoted_identifier("normalized_products")
    rows = await connection.fetch(
        f"""
        SELECT
            batch_id,
            tenant_id,
            deterministic_id,
            legacy_code,
            name,
            category,
            legacy_category,
            stock_kind,
            category_source,
            category_rule_id,
            category_confidence,
            supplier_legacy_code,
            supplier_deterministic_id,
            origin,
            unit,
            status,
            created_date,
            last_sale_date,
            avg_cost,
            source_table,
            source_row_number
        FROM {quoted_schema}.{quoted_table}
        WHERE batch_id = $1 AND tenant_id = $2 AND status = 'synthetic-review'
        ORDER BY legacy_code
        """,
        batch_id,
        tenant_id,
    )
    return [tuple(_coerce_mapping(row).values()) for row in rows]


async def _fetch_current_synthetic_review_codes(
    connection,
    schema_name: str,
    batch_id: str,
    tenant_id: uuid.UUID,
) -> set[str]:
    quoted_schema = _quoted_identifier(schema_name)
    rows = await connection.fetch(
        f"""
        SELECT legacy_code
        FROM {quoted_schema}.product_code_mapping
        WHERE tenant_id = $1
          AND last_seen_batch_id = $2
          AND approval_source = 'review-import'
          AND resolution_type = 'analyst_review'
          AND target_code = legacy_code
        """,
        tenant_id,
        batch_id,
    )
    return {
        legacy_code
        for row in rows
        for legacy_code in [str(_coerce_mapping(row).get("legacy_code") or "").strip()]
        if legacy_code
    }


def _validate_inventory_product_codes(
    product_rows: list[Mapping[str, object]],
    inventory_rows: list[Mapping[str, object]],
) -> None:
    known_product_codes = {
        str(row.get("legacy_code") or "").strip()
        for row in product_rows
        if str(row.get("legacy_code") or "").strip()
    }
    missing_codes = sorted(
        {
            product_code
            for row in inventory_rows
            for product_code in [str(row.get("product_code") or "").strip()]
            if product_code and product_code not in known_product_codes
        }
    )
    if missing_codes:
        missing_list = ", ".join(missing_codes)
        raise ValueError(
            "Inventory rows reference products missing from the staged product set: "
            f"{missing_list}"
        )


async def run_normalization(
    *,
    batch_id: str,
    tenant_id: uuid.UUID = DEFAULT_TENANT_ID,
    schema_name: str | None = None,
    # Story 15.25: incremental mode parameters
    batch_mode: str | RefreshBatchMode | None = None,
    selected_domains: Sequence[str] | None = None,
    entity_scope: Mapping[str, Mapping[str, Any]] | None = None,
    last_successful_batch_ids: Mapping[str, str] | None = None,
) -> NormalizationBatchResult:
    """Story 15.25: Normalize staged legacy data with optional incremental scope.

    In full-batch mode (the default), all domains are normalized from staged data.
    In incremental mode, only the domains in ``selected_domains`` are normalized,
    and unchanged master domains are carried forward from ``last_successful_batch_ids``.

    Args:
        batch_id: The batch identifier for this normalization run.
        tenant_id: Tenant scope for all operations.
        schema_name: Target raw schema (defaults to settings.legacy_import_schema).
        batch_mode: Either "full" (default) or "incremental". Raises ValueError for
            unknown values.
        selected_domains: Required for incremental mode; the domains to normalize.
            Must be non-empty when batch_mode="incremental".
        entity_scope: Per-domain manifest scope used by downstream adapters;
            accepted but not used by normalization itself (carried from manifest).
        last_successful_batch_ids: Map of domain -> prior batch id for carryforward.
            Used only in incremental mode to reuse unchanged master data.

    Returns:
        NormalizationBatchResult with counts and reused_from_batch_ids for
        incremental mode.

    Raises:
        ValueError: If batch_mode is unknown, incremental mode is selected but
            selected_domains is empty, or incremental-mode kwargs are passed
            to full mode.
    """
    resolved_schema = schema_name or settings.legacy_import_schema

    # Normalize batch_mode to enum or string.
    if batch_mode is None:
        mode: str = "full"
    elif isinstance(batch_mode, RefreshBatchMode):
        mode = batch_mode.value
    else:
        mode = str(batch_mode).strip().lower()

    if mode not in ("full", "incremental"):
        raise ValueError(f"unsupported batch_mode: {batch_mode!r}")

    # Story 15.25 AC2: incremental requires selected_domains.
    if mode == "incremental":
        if not selected_domains:
            raise ValueError(
                "non-empty selected_domains is required for incremental batch mode"
            )
        selected = tuple(selected_domains)
        # Story 15.25 Fix: Validate all requested domains against the known set.
        unknown_domains = set(selected) - _MASTER_NORMALIZATION_DOMAINS
        if unknown_domains:
            raise ValueError(
                f"Incremental mode does not support these domain names: {sorted(unknown_domains)}. "
                f"Supported domains are: {sorted(_MASTER_NORMALIZATION_DOMAINS)}"
            )
    else:
        # Story 15.25 AC5: reject incremental-mode kwargs in full mode.
        if selected_domains is not None:
            raise ValueError(
                "incremental-mode kwargs (selected_domains, entity_scope, "
                "last_successful_batch_ids) are not allowed in full batch mode"
            )
        selected = ("parties", "products", "warehouses", "inventory")

    connection = await _open_raw_connection()
    reused_from_batch_ids: dict[str, int] = {}

    try:
        await _ensure_staged_batch_ready(connection, resolved_schema, batch_id, tenant_id)
        async with connection.transaction():
            await _ensure_normalized_tables(connection, resolved_schema)

            # ----------------------------------------------------------------
            # Fetch and normalize staged rows for selected domains.
            # ----------------------------------------------------------------
            party_records: list[tuple] = []
            product_records: list[tuple] = []
            warehouse_records: list[tuple] = []
            inventory_records: list[tuple] = []
            product_review_candidates: list[tuple[object, ...]] = []

            if "parties" in selected:
                party_rows = await _fetch_stage_rows(
                    connection,
                    resolved_schema,
                    "tbscust",
                    """
				col_1 AS legacy_code,
				col_2 AS legacy_type,
				col_3 AS company_name,
				col_4 AS short_name,
				col_8 AS full_address,
				col_13 AS address,
				col_14 AS phone,
				col_17 AS email,
				col_18 AS contact_person,
				col_20 AS tax_id,
				col_21 AS created_date,
				col_57 AS updated_date,
				col_65 AS status_code,
				col_75 AS record_status,
				_source_row_number AS source_row_number
				""",
                    batch_id,
                )
                # Story 15.25 AC3: empty parties is tolerated in incremental mode
                # (carryforward will fill the gap).
                if not party_rows and mode == "full":
                    raise ValueError(f"No staged tbscust rows found for batch {batch_id}")
                party_records = [
                    normalize_party_record(row, batch_id, tenant_id)
                    for row in party_rows
                ]

            if "products" in selected:
                product_rows = await _fetch_stage_rows(
                    connection,
                    resolved_schema,
                    "tbsstock",
                    """
				col_1 AS legacy_code,
				col_3 AS name,
				col_5 AS legacy_category,
				col_7 AS stock_kind,
				col_8 AS supplier_code,
				col_9 AS origin,
				col_16 AS unit,
				col_29 AS created_date,
				col_30 AS last_sale_date,
				col_31 AS avg_cost,
				col_85 AS status,
				_source_row_number AS source_row_number
				""",
                    batch_id,
                )
                if not product_rows and mode == "full":
                    raise ValueError(f"No staged tbsstock rows found for batch {batch_id}")

                category_overrides = await _fetch_category_overrides(
                    connection,
                    resolved_schema,
                    tenant_id,
                )

                for row in product_rows:
                    category_derivation = _resolve_product_category(
                        row,
                        category_overrides=category_overrides,
                    )
                    product_records.append(
                        _normalize_product_record(
                            row,
                            batch_id,
                            tenant_id,
                            category_derivation=category_derivation,
                        )
                    )
                    review_reason = _review_reason_for_derivation(category_derivation)
                    if review_reason is not None:
                        product_review_candidates.append(
                            (
                                str(row.get("legacy_code") or "").strip(),
                                str(row.get("name") or "").strip(),
                                _normalize_text(row.get("legacy_category")),
                                _normalize_text(row.get("stock_kind")),
                                category_derivation.category,
                                category_derivation.source,
                                category_derivation.rule_id,
                                category_derivation.confidence,
                                review_reason,
                                "tbsstock",
                                int(row.get("source_row_number") or 0),
                            )
                        )

                synthetic_product_records = await _fetch_existing_synthetic_product_records(
                    connection,
                    resolved_schema,
                    batch_id,
                    tenant_id,
                )
                synthetic_review_codes = await _fetch_current_synthetic_review_codes(
                    connection,
                    resolved_schema,
                    batch_id,
                    tenant_id,
                )
                known_product_codes = {str(record[3]) for record in product_records}
                preserved_synthetic_records = [
                    record
                    for record in synthetic_product_records
                    if str(record[3]) not in known_product_codes
                    and str(record[3]) in synthetic_review_codes
                ]
            else:
                synthetic_product_records = []
                preserved_synthetic_records = []

            if "warehouses" in selected or "inventory" in selected:
                inventory_rows = await _fetch_stage_rows(
                    connection,
                    resolved_schema,
                    "tbsstkhouse",
                    """
				col_1 AS product_code,
				col_2 AS warehouse_code,
				col_7 AS qty_on_hand,
				_source_row_number AS source_row_number
				""",
                    batch_id,
                )
                if not inventory_rows and mode == "full":
                    raise ValueError(
                        f"No staged tbsstkhouse rows found for batch {batch_id}"
                    )

                # Validate product codes if both products and inventory are selected.
                if product_records and inventory_rows:
                    _validate_inventory_product_codes(product_rows, inventory_rows)

                if "warehouses" in selected:
                    warehouse_records = _normalized_warehouse_records(
                        inventory_rows,
                        batch_id,
                        tenant_id,
                    )
                if "inventory" in selected:
                    inventory_records = [
                        _normalize_inventory_record(row, batch_id, tenant_id)
                        for row in inventory_rows
                    ]

            # ----------------------------------------------------------------
            # Story 15.25: Clear and write normalized rows.
            # In incremental mode, only clear/write the scoped domains.
            # ----------------------------------------------------------------
            scoped_domains = frozenset(selected)

            if mode == "incremental":
                await _clear_scoped_batch_rows(
                    connection,
                    resolved_schema,
                    batch_id,
                    tenant_id,
                    scoped_domains,
                )
            else:
                await _clear_batch_rows(connection, resolved_schema, batch_id, tenant_id)

            # Write product review candidates (only if products are in scope).
            if "products" in selected and product_review_candidates:
                await _replace_product_category_review_candidates(
                    connection,
                    resolved_schema,
                    batch_id,
                    tenant_id,
                    tuple(product_review_candidates),
                )

            # Write normalized records for each scoped domain.
            if "parties" in selected and party_records:
                await connection.copy_records_to_table(
                    "normalized_parties",
                    schema_name=resolved_schema,
                    columns=(
                        "batch_id",
                        "tenant_id",
                        "deterministic_id",
                        "legacy_code",
                        "legacy_type",
                        "role",
                        "company_name",
                        "short_name",
                        "tax_id",
                        "full_address",
                        "address",
                        "phone",
                        "email",
                        "contact_person",
                        "is_active",
                        "created_date",
                        "updated_date",
                        "customer_type",
                        "source_table",
                        "source_row_number",
                    ),
                    records=party_records,
                )

            if "products" in selected and product_records:
                await connection.copy_records_to_table(
                    "normalized_products",
                    schema_name=resolved_schema,
                    columns=(
                        "batch_id",
                        "tenant_id",
                        "deterministic_id",
                        "legacy_code",
                        "name",
                        "category",
                        "legacy_category",
                        "stock_kind",
                        "category_source",
                        "category_rule_id",
                        "category_confidence",
                        "supplier_legacy_code",
                        "supplier_deterministic_id",
                        "origin",
                        "unit",
                        "status",
                        "created_date",
                        "last_sale_date",
                        "avg_cost",
                        "source_table",
                        "source_row_number",
                    ),
                    records=[*product_records, *preserved_synthetic_records],
                )

            if "warehouses" in selected and warehouse_records:
                await connection.copy_records_to_table(
                    "normalized_warehouses",
                    schema_name=resolved_schema,
                    columns=(
                        "batch_id",
                        "tenant_id",
                        "deterministic_id",
                        "legacy_code",
                        "code",
                        "name",
                        "location",
                        "address",
                        "source_kind",
                        "source_table",
                        "source_row_number",
                    ),
                    records=warehouse_records,
                )

            if "inventory" in selected and inventory_records:
                await connection.copy_records_to_table(
                    "normalized_inventory_prep",
                    schema_name=resolved_schema,
                    columns=(
                        "batch_id",
                        "tenant_id",
                        "product_deterministic_id",
                        "warehouse_deterministic_id",
                        "product_legacy_code",
                        "warehouse_code",
                        "quantity_on_hand",
                        "reorder_point",
                        "source_table",
                        "source_row_number",
                    ),
                    records=inventory_records,
                )

            # ----------------------------------------------------------------
            # Story 15.25 AC3: Carryforward from last successful batch.
            # Only carry forward master domains that were not freshly staged.
            # The carryforward rows contribute to the domain counts so operators
            # see the total rows in each normalized table for this batch.
            # ----------------------------------------------------------------
            carryforward_party_count = 0
            carryforward_product_count = 0
            carryforward_warehouse_count = 0
            carryforward_inventory_count = 0

            if mode == "incremental" and last_successful_batch_ids:
                for domain in _MASTER_NORMALIZATION_DOMAINS:
                    # Skip if domain was freshly staged (has rows).
                    has_fresh_staging = (
                        (domain == "parties" and party_records)
                        or (domain == "products" and product_records)
                        or (domain == "warehouses" and warehouse_records)
                        or (domain == "inventory" and inventory_records)
                    )
                    if has_fresh_staging:
                        continue

                    prior_batch = last_successful_batch_ids.get(domain)
                    if not prior_batch:
                        continue

                    copied = await _carry_forward_prior_batch(
                        connection,
                        resolved_schema,
                        domain,
                        current_batch_id=batch_id,
                        prior_batch_id=prior_batch,
                        tenant_id=tenant_id,
                    )
                    if copied > 0:
                        reused_from_batch_ids[domain] = copied
                        # Accumulate carryforward counts for result reporting.
                        if domain == "parties":
                            carryforward_party_count += copied
                        elif domain == "products":
                            carryforward_product_count += copied
                        elif domain == "warehouses":
                            carryforward_warehouse_count += copied
                        elif domain == "inventory":
                            carryforward_inventory_count += copied

    finally:
        await connection.close()

    return NormalizationBatchResult(
        batch_id=batch_id,
        schema_name=resolved_schema,
        party_count=len(party_records) + carryforward_party_count,
        product_count=len(product_records) + carryforward_product_count,
        warehouse_count=len(warehouse_records) + carryforward_warehouse_count,
        inventory_count=len(inventory_records) + carryforward_inventory_count,
        reused_from_batch_ids=reused_from_batch_ids,
    )
