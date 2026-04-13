"""Legacy master-data normalization helpers."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Mapping

from common.config import settings
from common.tenant import DEFAULT_TENANT_ID
from domains.legacy_import.staging import _open_raw_connection, _quoted_identifier

_NAMESPACE = uuid.UUID("4e59177d-61e5-48f4-b1f8-6b2141739ab9")
_DEFAULT_WAREHOUSE_CODE = "LEGACY_DEFAULT"
_DEFAULT_WAREHOUSE_NAME = "Legacy Default Warehouse"
_KNOWN_WAREHOUSE_NAMES = {
    "A": "Legacy General Warehouse (總倉)",
}


@dataclass(slots=True, frozen=True)
class NormalizationBatchResult:
    batch_id: str
    schema_name: str
    party_count: int
    product_count: int
    warehouse_count: int
    inventory_count: int


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
        "tbscust",
        int(record.get("source_row_number") or 0),
    )


def _normalize_product_record(
    record: Mapping[str, object],
    batch_id: str,
    tenant_id: uuid.UUID,
) -> tuple:
    legacy_code = str(record.get("legacy_code") or "").strip()
    if not legacy_code:
        raise ValueError("Product record missing legacy_code")

    supplier_code = str(record.get("supplier_code") or "").strip() or None
    supplier_id = (
        deterministic_legacy_uuid("party", "supplier", supplier_code) if supplier_code else None
    )
    return (
        batch_id,
        tenant_id,
        deterministic_legacy_uuid("product", legacy_code),
        legacy_code,
        str(record.get("name") or legacy_code).strip(),
        str(record.get("category") or "").strip() or None,
        supplier_code,
        supplier_id,
        str(record.get("origin") or "").strip() or None,
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


async def _ensure_normalized_tables(connection, schema_name: str) -> None:
    quoted_schema = _quoted_identifier(schema_name)
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
			source_table TEXT NOT NULL,
			source_row_number INTEGER NOT NULL,
			PRIMARY KEY (tenant_id, batch_id, role, legacy_code)
		)
		"""
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


async def run_normalization(
    *,
    batch_id: str,
    tenant_id: uuid.UUID = DEFAULT_TENANT_ID,
    schema_name: str | None = None,
) -> NormalizationBatchResult:
    resolved_schema = schema_name or settings.legacy_import_schema
    connection = await _open_raw_connection()
    try:
        async with connection.transaction():
            await _ensure_normalized_tables(connection, resolved_schema)

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
            if not party_rows:
                raise ValueError(f"No staged tbscust rows found for batch {batch_id}")

            product_rows = await _fetch_stage_rows(
                connection,
                resolved_schema,
                "tbsstock",
                """
				col_1 AS legacy_code,
				col_3 AS name,
				col_7 AS category,
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
            if not product_rows:
                raise ValueError(f"No staged tbsstock rows found for batch {batch_id}")

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
            if not inventory_rows:
                raise ValueError(f"No staged tbsstkhouse rows found for batch {batch_id}")

            party_records = [normalize_party_record(row, batch_id, tenant_id) for row in party_rows]
            product_records = [
                _normalize_product_record(row, batch_id, tenant_id) for row in product_rows
            ]
            warehouse_records = _normalized_warehouse_records(
                inventory_rows,
                batch_id,
                tenant_id,
            )
            inventory_records = [
                _normalize_inventory_record(row, batch_id, tenant_id) for row in inventory_rows
            ]

            await _clear_batch_rows(connection, resolved_schema, batch_id, tenant_id)

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
                    "source_table",
                    "source_row_number",
                ),
                records=party_records,
            )
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
                records=product_records,
            )
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
    finally:
        await connection.close()

    return NormalizationBatchResult(
        batch_id=batch_id,
        schema_name=resolved_schema,
        party_count=len(party_records),
        product_count=len(product_records),
        warehouse_count=len(warehouse_records),
        inventory_count=len(inventory_records),
    )
