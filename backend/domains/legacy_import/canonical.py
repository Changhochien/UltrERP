"""Canonical historical import helpers for legacy ERP batches."""

from __future__ import annotations

import json
import re
import uuid
import zlib
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any, AsyncIterable, AsyncIterator, Mapping, cast

from common.config import settings
from common.tenant import DEFAULT_TENANT_ID
from domains.legacy_import.mapping import UNKNOWN_PRODUCT_CODE
from domains.legacy_import.normalization import deterministic_legacy_uuid, normalize_legacy_date
from domains.legacy_import.staging import _open_raw_connection, _quoted_identifier

_DIGITS_ONLY_RE = re.compile(r"\D+")


@dataclass(slots=True, frozen=True)
class CanonicalImportResult:
    batch_id: str
    schema_name: str
    attempt_number: int
    customer_count: int
    product_count: int
    warehouse_count: int
    inventory_count: int
    order_count: int
    order_line_count: int
    invoice_count: int
    invoice_line_count: int
    holding_count: int
    lineage_count: int
    supplier_count: int = 0
    supplier_invoice_count: int = 0
    supplier_invoice_line_count: int = 0


def _coerce_row(row: Mapping[str, object] | object) -> dict[str, object]:
    if isinstance(row, Mapping):
        return {str(key): value for key, value in row.items()}
    if hasattr(row, "items"):
        mapping_row = cast(Mapping[str, object], row)
        return {str(key): value for key, value in mapping_row.items()}
    raise TypeError(f"Unsupported row payload: {type(row)!r}")


def _as_text(value: object | None) -> str:
    return str(value or "").strip()


def _as_int(value: object | None, default: int = 0) -> int:
    text = _as_text(value)
    if not text:
        return default
    return int(text)


def _as_decimal(value: object | None, default: str | None = "0") -> Decimal | None:
    text = _as_text(value)
    if not text:
        return Decimal(default) if default is not None else None
    try:
        return Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"Invalid decimal value: {text}") from exc


def _as_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _as_legacy_date(value: object | None) -> date | None:
    text = _as_text(value)
    if not text:
        return None
    return normalize_legacy_date(text)


def _as_timestamp(day: date | None) -> datetime:
    resolved_day = day or date.today()
    return datetime.combine(resolved_day, time.min, tzinfo=UTC)


def _normalized_business_number(tax_id: object | None, legacy_code: object | None) -> str:
    tax_digits = _DIGITS_ONLY_RE.sub("", _as_text(tax_id))
    if len(tax_digits) == 8:
        return tax_digits

    legacy_digits = _DIGITS_ONLY_RE.sub("", _as_text(legacy_code))
    if legacy_digits:
        return legacy_digits[-8:].zfill(8)

    legacy_text = _as_text(legacy_code) or "legacy-party"
    checksum = zlib.crc32(legacy_text.encode("utf-8")) % 100_000_000
    return f"{checksum:08d}"


def _currency_code(value: object | None) -> str:
    raw = _as_text(value).upper()
    if raw in {"", "0001", "NTD", "TWD"}:
        return "TWD"
    return raw[:3]


def _compact_snapshot(snapshot: dict[str, object | None]) -> dict[str, object]:
    return {key: value for key, value in snapshot.items() if value not in (None, "")}


def _build_sales_header_snapshot(header: dict[str, object]) -> dict[str, object]:
    return _compact_snapshot(
        {
            "source_table": "tbsslipx",
            "legacy_doc_number": _as_text(header.get("doc_number")),
            "invoice_date_raw": _as_text(header.get("invoice_date")),
            "customer_code": _as_text(header.get("customer_code")),
            "customer_name": _as_text(header.get("customer_name")),
            "address": _as_text(header.get("address")),
            "currency_code": _as_text(header.get("currency_code")),
            "exchange_rate": _as_text(header.get("exchange_rate")),
            "tax_type": _as_text(header.get("tax_type")),
            "tax_rate": _as_text(header.get("tax_rate")),
            "period_code": _as_text(header.get("period_code")),
            "source_status": _as_text(header.get("source_status")),
            "remark": _as_text(header.get("remark")),
            "created_by": _as_text(header.get("created_by")),
        }
    )


def _build_purchase_header_snapshot(header: dict[str, object]) -> dict[str, object]:
    raw_invoice_number = _as_text(header.get("raw_invoice_number"))
    raw_invoice_date = _as_text(header.get("raw_invoice_date"))
    return _compact_snapshot(
        {
            "source_table": "tbsslipj",
            "legacy_doc_number": _as_text(header.get("doc_number")),
            "supplier_code": _as_text(header.get("supplier_code")),
            "supplier_name": _as_text(header.get("supplier_name")),
            "address": _as_text(header.get("address")),
            "currency_code": _as_text(header.get("currency_code")),
            "period_code": _as_text(header.get("period_code")),
            "tax_rate": _as_text(header.get("tax_rate")),
            "raw_invoice_number": raw_invoice_number,
            "resolved_invoice_number": _as_text(header.get("invoice_number")),
            "invoice_number_source": "legacy_invoice_number" if raw_invoice_number else "doc_number",
            "raw_invoice_date": raw_invoice_date,
            "resolved_invoice_date": _as_text(header.get("invoice_date")),
            "invoice_date_source": "legacy_invoice_date" if raw_invoice_date else "slip_date",
            "slip_date": _as_text(header.get("slip_date")),
            "notes": _as_text(header.get("notes")),
        }
    )


def _tax_policy_code(tax_amount: Decimal) -> tuple[str, int, Decimal]:
    if tax_amount > Decimal("0"):
        return ("standard", 1, Decimal("0.05"))
    return ("exempt", 3, Decimal("0.00"))


def _tenant_scoped_uuid(tenant_id: uuid.UUID, kind: str, *parts: str) -> uuid.UUID:
    return deterministic_legacy_uuid(kind, str(tenant_id), *parts)


def _step_row_count(step_name: str, counts: Mapping[str, int]) -> int:
    if step_name == "sales_history":
        return counts.get("order_line_count", 0) + counts.get("invoice_line_count", 0)
    if step_name == "purchase_history":
        return counts.get("supplier_invoice_count", 0) + counts.get(
            "supplier_invoice_line_count", 0
        )
    if step_name == "unsupported_history":
        return counts.get("holding_count", 0)

    step_to_count_key = {
        "customers": "customer_count",
        "suppliers": "supplier_count",
        "products": "product_count",
        "warehouses": "warehouse_count",
        "inventory": "inventory_count",
    }
    return counts.get(step_to_count_key.get(step_name, ""), 0)


async def _ensure_canonical_support_tables(connection, schema_name: str) -> None:
    quoted_schema = _quoted_identifier(schema_name)
    await connection.execute(
        f"""
		CREATE TABLE IF NOT EXISTS {quoted_schema}.canonical_import_runs (
			id UUID PRIMARY KEY,
			tenant_id UUID NOT NULL,
			batch_id TEXT NOT NULL,
			source_schema TEXT NOT NULL,
			attempt_number INTEGER NOT NULL,
			status TEXT NOT NULL,
			summary JSONB,
			error_message TEXT,
			started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
			completed_at TIMESTAMPTZ,
			created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
			UNIQUE (tenant_id, batch_id, attempt_number)
		)
		"""
    )
    await connection.execute(
        f"""
		CREATE TABLE IF NOT EXISTS {quoted_schema}.canonical_import_step_runs (
			run_id UUID NOT NULL REFERENCES {quoted_schema}.canonical_import_runs(id),
			step_name TEXT NOT NULL,
			row_count INTEGER NOT NULL DEFAULT 0,
			status TEXT NOT NULL,
			error_message TEXT,
			started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
			completed_at TIMESTAMPTZ,
			PRIMARY KEY (run_id, step_name)
		)
		"""
    )
    await connection.execute(
        f"""
		CREATE TABLE IF NOT EXISTS {quoted_schema}.canonical_record_lineage (
			tenant_id UUID NOT NULL,
			batch_id TEXT NOT NULL,
			canonical_table TEXT NOT NULL,
			canonical_id UUID NOT NULL,
			source_table TEXT NOT NULL,
			source_identifier TEXT NOT NULL,
			source_row_number INTEGER NOT NULL,
			import_run_id UUID NOT NULL,
			created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
			PRIMARY KEY (
				tenant_id,
				batch_id,
				canonical_table,
				canonical_id,
				source_table,
				source_identifier
			)
		)
		"""
    )
    await connection.execute(
        f"""
		CREATE TABLE IF NOT EXISTS {quoted_schema}.unsupported_history_holding (
			id UUID PRIMARY KEY,
			tenant_id UUID NOT NULL,
			batch_id TEXT NOT NULL,
			domain_name TEXT NOT NULL,
			source_table TEXT NOT NULL,
			source_identifier TEXT NOT NULL,
			source_row_number INTEGER NOT NULL,
			payload JSONB NOT NULL,
			notes TEXT,
			import_run_id UUID NOT NULL,
			created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
			updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
			UNIQUE (tenant_id, batch_id, source_table, source_identifier, source_row_number)
		)
		"""
    )


async def _next_attempt_number(
    connection, schema_name: str, batch_id: str, tenant_id: uuid.UUID
) -> int:
    quoted_schema = _quoted_identifier(schema_name)
    value = await connection.fetchval(
        f"""
		SELECT COALESCE(MAX(attempt_number), 0)
		FROM {quoted_schema}.canonical_import_runs
		WHERE tenant_id = $1 AND batch_id = $2
		""",
        tenant_id,
        batch_id,
    )
    return int(value or 0) + 1


async def _upsert_run_row(
    connection,
    schema_name: str,
    run_id: uuid.UUID,
    tenant_id: uuid.UUID,
    batch_id: str,
    attempt_number: int,
    status: str,
    summary: dict[str, int] | None,
    error_message: str | None,
) -> None:
    quoted_schema = _quoted_identifier(schema_name)
    await connection.execute(
        f"""
		INSERT INTO {quoted_schema}.canonical_import_runs (
			id,
			tenant_id,
			batch_id,
			source_schema,
			attempt_number,
			status,
			summary,
			error_message,
			started_at,
			completed_at
		)
        VALUES (
            $1,
            $2,
            $3,
            $4,
            $5,
            $6,
            $7::jsonb,
            $8,
            NOW(),
            CASE
                WHEN $6 = 'completed' OR $6 = 'failed' THEN NOW()
                ELSE NULL
            END
        )
		ON CONFLICT (tenant_id, batch_id, attempt_number) DO UPDATE SET
			status = EXCLUDED.status,
			summary = EXCLUDED.summary,
			error_message = EXCLUDED.error_message,
			completed_at = EXCLUDED.completed_at
		""",
        run_id,
        tenant_id,
        batch_id,
        schema_name,
        attempt_number,
        status,
        json.dumps(summary or {}),
        error_message,
    )


async def _upsert_step_row(
    connection,
    schema_name: str,
    run_id: uuid.UUID,
    step_name: str,
    row_count: int,
    status: str,
    error_message: str | None = None,
) -> None:
    quoted_schema = _quoted_identifier(schema_name)
    await connection.execute(
        f"""
		INSERT INTO {quoted_schema}.canonical_import_step_runs (
			run_id,
			step_name,
			row_count,
			status,
			error_message,
			started_at,
			completed_at
		)
        VALUES (
            $1,
            $2,
            $3,
            $4,
            $5,
            NOW(),
            CASE
                WHEN $4 = 'completed' OR $4 = 'failed' THEN NOW()
                ELSE NULL
            END
        )
		ON CONFLICT (run_id, step_name) DO UPDATE SET
			row_count = EXCLUDED.row_count,
			status = EXCLUDED.status,
			error_message = EXCLUDED.error_message,
			completed_at = EXCLUDED.completed_at
		""",
        run_id,
        step_name,
        row_count,
        status,
        error_message,
    )


async def _upsert_lineage(
    connection,
    schema_name: str,
    run_id: uuid.UUID,
    tenant_id: uuid.UUID,
    batch_id: str,
    canonical_table: str,
    canonical_id: uuid.UUID,
    source_table: str,
    source_identifier: str,
    source_row_number: int,
) -> None:
    quoted_schema = _quoted_identifier(schema_name)
    await connection.execute(
        f"""
		INSERT INTO {quoted_schema}.canonical_record_lineage (
			tenant_id,
			batch_id,
			canonical_table,
			canonical_id,
			source_table,
			source_identifier,
			source_row_number,
			import_run_id
		)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        ON CONFLICT (
            tenant_id,
            batch_id,
            canonical_table,
            canonical_id,
            source_table,
            source_identifier
        )
		DO UPDATE SET
			source_row_number = EXCLUDED.source_row_number,
			import_run_id = EXCLUDED.import_run_id
		""",
        tenant_id,
        batch_id,
        canonical_table,
        canonical_id,
        source_table,
        source_identifier,
        source_row_number,
        run_id,
    )


async def _upsert_holding_row(
    connection,
    schema_name: str,
    run_id: uuid.UUID,
    tenant_id: uuid.UUID,
    batch_id: str,
    domain_name: str,
    source_table: str,
    source_identifier: str,
    source_row_number: int,
    payload: dict[str, object],
    notes: str,
) -> None:
    quoted_schema = _quoted_identifier(schema_name)
    holding_id = _tenant_scoped_uuid(
        tenant_id,
        "unsupported-history",
        domain_name,
        source_table,
        source_identifier,
        str(source_row_number),
    )
    await connection.execute(
        f"""
		INSERT INTO {quoted_schema}.unsupported_history_holding (
			id,
			tenant_id,
			batch_id,
			domain_name,
			source_table,
			source_identifier,
			source_row_number,
			payload,
			notes,
			import_run_id,
			updated_at
		)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9, $10, NOW())
        ON CONFLICT (
            tenant_id,
            batch_id,
            source_table,
            source_identifier,
            source_row_number
        ) DO UPDATE SET
			domain_name = EXCLUDED.domain_name,
			payload = EXCLUDED.payload,
			notes = EXCLUDED.notes,
			import_run_id = EXCLUDED.import_run_id,
			updated_at = NOW()
		""",
        holding_id,
        tenant_id,
        batch_id,
        domain_name,
        source_table,
        source_identifier,
        source_row_number,
        json.dumps(payload),
        notes,
        run_id,
    )


async def _table_exists(connection, schema_name: str, table_name: str) -> bool:
    quoted_schema = _quoted_identifier(schema_name)
    value = await connection.fetchval(f"SELECT to_regclass('{quoted_schema}.{table_name}')")
    return bool(value)


async def _iter_query_rows(
    connection,
    query: str,
    *args: object,
) -> AsyncIterator[dict[str, object]]:
    # Prefer server-side cursor when available — streams rows without loading
    # all into memory. Falls back to fetch() for non-transactional connections.
    cursor = getattr(connection, "cursor", None)
    if callable(cursor):
        async with connection.transaction():
            cursor_iter = cast(Any, cursor)(query, *args)
            async for row in cursor_iter:
                yield _coerce_row(row)
        return

    rows = await connection.fetch(query, *args)
    for row in rows:
        yield _coerce_row(row)


async def _iter_normalized_parties(
    connection, schema_name: str, batch_id: str, tenant_id: uuid.UUID
) -> AsyncIterator[dict[str, object]]:
    quoted_schema = _quoted_identifier(schema_name)
    async for row in _iter_query_rows(
        connection,
        f"""
		SELECT
			deterministic_id,
			legacy_code,
			role,
			company_name,
			short_name,
			tax_id,
			full_address,
			address,
			phone,
			email,
			contact_person,
			source_table,
			source_row_number
		FROM {quoted_schema}.normalized_parties
		WHERE batch_id = $1 AND tenant_id = $2
		ORDER BY role, legacy_code
		""",
        batch_id,
        tenant_id,
    ):
        yield row


async def _iter_normalized_products(
    connection, schema_name: str, batch_id: str, tenant_id: uuid.UUID
) -> AsyncIterator[dict[str, object]]:
    quoted_schema = _quoted_identifier(schema_name)
    async for row in _iter_query_rows(
        connection,
        f"""
		SELECT
			deterministic_id,
			legacy_code,
			name,
			category,
			unit,
			status,
			source_table,
			source_row_number
		FROM {quoted_schema}.normalized_products
		WHERE batch_id = $1 AND tenant_id = $2
		ORDER BY legacy_code
		""",
        batch_id,
        tenant_id,
    ):
        yield row


async def _iter_normalized_warehouses(
    connection, schema_name: str, batch_id: str, tenant_id: uuid.UUID
) -> AsyncIterator[dict[str, object]]:
    quoted_schema = _quoted_identifier(schema_name)
    async for row in _iter_query_rows(
        connection,
        f"""
		SELECT
			deterministic_id,
			code,
			name,
			location,
			address,
			source_table,
			source_row_number
		FROM {quoted_schema}.normalized_warehouses
		WHERE batch_id = $1 AND tenant_id = $2
		ORDER BY code
		""",
        batch_id,
        tenant_id,
    ):
        yield row


async def _iter_normalized_inventory(
    connection, schema_name: str, batch_id: str, tenant_id: uuid.UUID
) -> AsyncIterator[dict[str, object]]:
    quoted_schema = _quoted_identifier(schema_name)
    async for row in _iter_query_rows(
        connection,
        f"""
		SELECT
			product_deterministic_id,
			warehouse_deterministic_id,
			product_legacy_code,
			warehouse_code,
			quantity_on_hand,
			reorder_point,
			source_table,
			source_row_number
		FROM {quoted_schema}.normalized_inventory_prep
		WHERE batch_id = $1 AND tenant_id = $2
		ORDER BY product_legacy_code, warehouse_code
		""",
        batch_id,
        tenant_id,
    ):
        yield row


async def _iter_product_mappings(
    connection, schema_name: str, tenant_id: uuid.UUID,
) -> AsyncIterator[tuple[str, str]]:
    """Yield (legacy_code, target_code) pairs — streaming, memory-efficient."""
    quoted_schema = _quoted_identifier(schema_name)
    async for row in _iter_query_rows(
        connection,
        f"""
		SELECT legacy_code, target_code
		FROM {quoted_schema}.product_code_mapping
		WHERE tenant_id = $1
		ORDER BY legacy_code
		""",
        tenant_id,
    ):
        legacy = _as_text(row.get("legacy_code"))
        target = _as_text(row.get("target_code"))
        if legacy:
            yield legacy, target


async def _fetch_product_mappings(
    connection, schema_name: str, tenant_id: uuid.UUID
) -> dict[str, str]:
    """Build product code mapping dict by streaming rows (memory-efficient)."""
    result: dict[str, str] = {}
    async for legacy, target in _iter_product_mappings(connection, schema_name, tenant_id):
        result[legacy] = target
    return result


async def _fetch_sales_headers(
    connection, schema_name: str, batch_id: str
) -> list[dict[str, object]]:
    quoted_schema = _quoted_identifier(schema_name)
    rows = await connection.fetch(
        f"""
		SELECT
			col_2 AS doc_number,
			col_3 AS invoice_date,
			col_7 AS customer_code,
			col_8 AS customer_name,
			col_9 AS address,
			col_10 AS currency_code,
			col_12 AS exchange_rate,
			col_17 AS subtotal,
			col_18 AS tax_type,
			col_19 AS tax_amount,
			col_24 AS total_amount,
			col_30 AS remark,
            col_31 AS period_code,
			col_32 AS created_by,
            col_80 AS source_status,
			col_85 AS tax_rate,
			_source_row_number AS source_row_number
		FROM {quoted_schema}.tbsslipx
		WHERE _batch_id = $1
		ORDER BY col_2
		""",
        batch_id,
    )
    return [_coerce_row(row) for row in rows]


async def _fetch_sales_lines(
    connection, schema_name: str, batch_id: str
) -> list[dict[str, object]]:
    quoted_schema = _quoted_identifier(schema_name)
    rows = await connection.fetch(
        f"""
		SELECT
			dtx.col_2 AS doc_number,
			dtx.col_3 AS line_number,
			dtx.col_7 AS product_code,
			dtx.col_8 AS product_name,
			dtx.col_18 AS unit,
			dtx.col_19 AS list_unit_price,
			dtx.col_21 AS unit_price,
			dtx.col_22 AS line_tax_amount,
			dtx.col_23 AS qty,
			dtx.col_29 AS extended_amount,
			dtx.col_44 AS original_list_price,
			dtx.col_45 AS original_discount_ratio,
			dtx._source_row_number AS source_row_number,
			COALESCE(SUM(inv.quantity_on_hand), 0) AS available_stock_snapshot
		FROM {quoted_schema}.tbsslipdtx dtx
		LEFT JOIN {quoted_schema}.normalized_inventory_prep inv
			ON inv.product_legacy_code = dtx.col_7
			AND inv.batch_id = dtx._batch_id
		WHERE dtx._batch_id = $1
		GROUP BY dtx.col_2, dtx.col_3, dtx.col_7, dtx.col_8, dtx.col_18,
			dtx.col_19, dtx.col_21, dtx.col_22, dtx.col_23, dtx.col_29,
			dtx.col_44, dtx.col_45, dtx._source_row_number
		ORDER BY dtx.col_2, dtx.col_3
		""",
        batch_id,
    )
    return [_coerce_row(row) for row in rows]


async def _fetch_purchase_headers(
    connection, schema_name: str, batch_id: str
) -> list[dict[str, object]]:
    quoted_schema = _quoted_identifier(schema_name)
    rows = await connection.fetch(
        f"""
		SELECT
			col_2 AS doc_number,
            col_3 AS slip_date,
            col_30 AS period_code,
            col_42 AS raw_invoice_number,
            col_62 AS raw_invoice_date,
            col_78 AS tax_rate,
            CASE
                WHEN COALESCE(col_42, '') <> '' THEN col_42
                ELSE col_2
            END AS invoice_number,
            CASE
                WHEN COALESCE(col_62, '') NOT IN ('', '1900-01-01') THEN col_62
                ELSE col_3
            END AS invoice_date,
			col_7 AS supplier_code,
			col_8 AS supplier_name,
			col_9 AS address,
            col_10 AS currency_code,
			col_17 AS subtotal,
			col_19 AS tax_amount,
            col_29 AS notes,
			col_49 AS total_amount,
			_source_row_number AS source_row_number
		FROM {quoted_schema}.tbsslipj
		WHERE _batch_id = $1
		ORDER BY col_2
		""",
        batch_id,
    )
    return [_coerce_row(row) for row in rows]


async def _fetch_purchase_lines(
    connection, schema_name: str, batch_id: str
) -> list[dict[str, object]]:
    quoted_schema = _quoted_identifier(schema_name)
    rows = await connection.fetch(
        f"""
		SELECT
			col_2 AS doc_number,
			col_3 AS line_number,
			col_6 AS product_code,
			col_19 AS unit_price,
			col_20 AS discount_multiplier,
			col_21 AS foldprice,
			col_22 AS qty,
			(col_19::numeric * col_20::numeric * col_22::numeric) AS extended_amount,
			_source_row_number AS source_row_number
		FROM {quoted_schema}.tbsslipdtj
		WHERE _batch_id = $1
		ORDER BY col_2, col_3
		""",
        batch_id,
    )
    return [_coerce_row(row) for row in rows]


async def _import_customers(
    connection,
    schema_name: str,
    run_id: uuid.UUID,
    tenant_id: uuid.UUID,
    batch_id: str,
    party_rows: AsyncIterable[dict[str, object]],
) -> tuple[int, int, dict[str, uuid.UUID], dict[str, str]]:
    count = 0
    lineage_count = 0
    customer_by_code: dict[str, uuid.UUID] = {}
    business_number_by_code: dict[str, str] = {}
    async for row in party_rows:
        if _as_text(row.get("role")) != "customer":
            continue
        legacy_code = _as_text(row.get("legacy_code"))
        customer_id = _tenant_scoped_uuid(tenant_id, "party", "customer", legacy_code)
        business_number = _normalized_business_number(row.get("tax_id"), legacy_code)
        company_name = _as_text(row.get("company_name")) or legacy_code
        contact_name = (
            _as_text(row.get("contact_person"))
            or _as_text(row.get("company_name"))
            or legacy_code
        )
        contact_phone = _as_text(row.get("phone")) or "N/A"
        contact_email = _as_text(row.get("email")) or "N/A"
        billing_address = _as_text(row.get("address")) or _as_text(row.get("full_address")) or "N/A"
        # Truncate phone to column limit
        if contact_phone and len(contact_phone) > 30:
            contact_phone = contact_phone[:30]
        await connection.execute(
            """
			INSERT INTO customers (
				id,
				tenant_id,
				company_name,
				normalized_business_number,
				billing_address,
				contact_name,
				contact_phone,
				contact_email,
				credit_limit,
				status,
				version,
				created_at,
				updated_at
			)
			VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, 1, NOW(), NOW())
			ON CONFLICT (tenant_id, normalized_business_number) DO UPDATE SET
				company_name = EXCLUDED.company_name,
				billing_address = EXCLUDED.billing_address,
				contact_name = EXCLUDED.contact_name,
				contact_phone = EXCLUDED.contact_phone,
				contact_email = EXCLUDED.contact_email,
				status = EXCLUDED.status,
				updated_at = NOW()
			""",
            customer_id,
            tenant_id,
            company_name,
            business_number,
            billing_address,
            contact_name,
            contact_phone,
            contact_email,
            Decimal("0.00"),
            "active",
        )
        # Resolve actual customer_id: ON CONFLICT may have reused an existing row
        # Always look up by BN to get the actual persisted id
        actual_row = await connection.fetchrow(
            "SELECT id FROM customers WHERE tenant_id = $1 AND normalized_business_number = $2",
            tenant_id,
            business_number,
        )
        if actual_row is None:
            raise ValueError(
                f"No customer found for BN {business_number} after INSERT — "
                "check ON CONFLICT constraint or tenant_id mismatch"
            )
        actual_customer_id = actual_row["id"]
        await _upsert_lineage(
            connection,
            schema_name,
            run_id,
            tenant_id,
            batch_id,
            "customers",
            actual_customer_id,
            _as_text(row.get("source_table")) or "tbscust",
            legacy_code,
            _as_int(row.get("source_row_number")),
        )
        customer_by_code[legacy_code] = actual_customer_id
        business_number_by_code[legacy_code] = business_number
        count += 1
        lineage_count += 1
    return count, lineage_count, customer_by_code, business_number_by_code


async def _import_suppliers(
    connection,
    schema_name: str,
    run_id: uuid.UUID,
    tenant_id: uuid.UUID,
    batch_id: str,
    party_rows: AsyncIterable[dict[str, object]],
) -> tuple[int, int, dict[str, uuid.UUID]]:
    count = 0
    lineage_count = 0
    supplier_by_code: dict[str, uuid.UUID] = {}
    async for row in party_rows:
        if _as_text(row.get("role")) != "supplier":
            continue
        legacy_code = _as_text(row.get("legacy_code"))
        supplier_id = _tenant_scoped_uuid(tenant_id, "party", "supplier", legacy_code)
        await connection.execute(
            """
			INSERT INTO supplier (
				id,
				tenant_id,
				name,
				contact_email,
				phone,
				address,
				default_lead_time_days,
				is_active,
				created_at
			)
			VALUES ($1, $2, $3, $4, $5, $6, NULL, TRUE, NOW())
			ON CONFLICT (id) DO UPDATE SET
				name = EXCLUDED.name,
				contact_email = EXCLUDED.contact_email,
				phone = EXCLUDED.phone,
				address = EXCLUDED.address,
				default_lead_time_days = EXCLUDED.default_lead_time_days,
				is_active = EXCLUDED.is_active
			""",
            supplier_id,
            tenant_id,
            _as_text(row.get("company_name")) or legacy_code,
            _as_text(row.get("email")) or None,
            _as_text(row.get("phone")) or None,
            _as_text(row.get("address")) or _as_text(row.get("full_address")) or None,
        )
        await _upsert_lineage(
            connection,
            schema_name,
            run_id,
            tenant_id,
            batch_id,
            "supplier",
            supplier_id,
            _as_text(row.get("source_table")) or "tbscust",
            legacy_code,
            _as_int(row.get("source_row_number")),
        )
        supplier_by_code[legacy_code] = supplier_id
        count += 1
        lineage_count += 1
    return count, lineage_count, supplier_by_code


async def _import_products(
    connection,
    schema_name: str,
    run_id: uuid.UUID,
    tenant_id: uuid.UUID,
    batch_id: str,
    product_rows: AsyncIterable[dict[str, object]],
) -> tuple[int, int, dict[str, uuid.UUID]]:
    count = 0
    lineage_count = 0
    product_by_code: dict[str, uuid.UUID] = {}
    unknown_product_present = False

    async def _upsert_product_row(row: dict[str, object]) -> None:
        nonlocal count, lineage_count, unknown_product_present
        legacy_code = _as_text(row.get("legacy_code"))
        if legacy_code == UNKNOWN_PRODUCT_CODE:
            unknown_product_present = True
        product_id = _tenant_scoped_uuid(tenant_id, "product", legacy_code)
        status = (
            "inactive"
            if legacy_code == UNKNOWN_PRODUCT_CODE
            else (
                "active"
                if _as_text(row.get("status")) in {"A", "ACTIVE", "placeholder", "PLACEHOLDER"}
                else "inactive"
            )
        )
        await connection.execute(
            """
			INSERT INTO product (
				id,
				tenant_id,
				code,
				name,
				category,
				description,
				unit,
				status,
				search_vector,
				created_at,
				updated_at
			)
			VALUES (
				$1::uuid, $2::uuid, $3::varchar, $4::varchar, $5::varchar, $6::text,
				$7::varchar, $8::varchar,
                to_tsvector(
                    'simple',
                    coalesce($3::text, '')
                    || ' '
                    || coalesce($4::text, '')
                    || ' '
                    || coalesce($5::text, '')
                ),
				NOW(), NOW()
			)
			ON CONFLICT (id) DO UPDATE SET
				code = EXCLUDED.code,
				name = EXCLUDED.name,
				category = EXCLUDED.category,
				description = EXCLUDED.description,
				unit = EXCLUDED.unit,
				status = EXCLUDED.status,
				search_vector = EXCLUDED.search_vector,
				updated_at = NOW()
			""",
            product_id,
            tenant_id,
            legacy_code,
            _as_text(row.get("name")) or legacy_code,
            _as_text(row.get("category")) or None,
            _as_text(row.get("description")) if row.get("description") else None,
            _as_text(row.get("unit")) or "pcs",
            status,
        )
        await _upsert_lineage(
            connection,
            schema_name,
            run_id,
            tenant_id,
            batch_id,
            "product",
            product_id,
            _as_text(row.get("source_table")) or "tbsstock",
            legacy_code,
            _as_int(row.get("source_row_number")),
        )
        product_by_code[legacy_code] = product_id
        count += 1
        lineage_count += 1

    async for row in product_rows:
        await _upsert_product_row(row)

    if not unknown_product_present:
        await _upsert_product_row(
            {
                "legacy_code": UNKNOWN_PRODUCT_CODE,
                "name": "Unknown Product",
                "category": None,
                "unit": "unknown",
                "status": "placeholder",
                "source_table": "product_code_mapping",
                "source_row_number": 0,
            }
        )

    return count, lineage_count, product_by_code


async def _import_warehouses(
    connection,
    schema_name: str,
    run_id: uuid.UUID,
    tenant_id: uuid.UUID,
    batch_id: str,
    warehouse_rows: AsyncIterable[dict[str, object]],
) -> tuple[int, int, dict[str, uuid.UUID]]:
    count = 0
    lineage_count = 0
    warehouse_by_code: dict[str, uuid.UUID] = {}
    async for row in warehouse_rows:
        code = _as_text(row.get("code"))
        warehouse_id = _tenant_scoped_uuid(tenant_id, "warehouse", code)
        await connection.execute(
            """
			INSERT INTO warehouse (
				id,
				tenant_id,
				name,
				code,
				location,
				address,
				contact_email,
				is_active,
				created_at
			)
			VALUES ($1, $2, $3, $4, $5, $6, $7, TRUE, NOW())
			ON CONFLICT (id) DO UPDATE SET
				name = EXCLUDED.name,
				code = EXCLUDED.code,
				location = EXCLUDED.location,
				address = EXCLUDED.address,
				contact_email = EXCLUDED.contact_email,
				is_active = EXCLUDED.is_active
			""",
            warehouse_id,
            tenant_id,
            _as_text(row.get("name")) or code,
            code,
            _as_text(row.get("location")) or None,
            _as_text(row.get("address")) or None,
            None,
        )
        await _upsert_lineage(
            connection,
            schema_name,
            run_id,
            tenant_id,
            batch_id,
            "warehouse",
            warehouse_id,
            _as_text(row.get("source_table")) or "normalized_warehouses",
            code,
            _as_int(row.get("source_row_number")),
        )
        warehouse_by_code[code] = warehouse_id
        count += 1
        lineage_count += 1
    return count, lineage_count, warehouse_by_code


async def _import_inventory(
    connection,
    schema_name: str,
    run_id: uuid.UUID,
    tenant_id: uuid.UUID,
    batch_id: str,
    inventory_rows: AsyncIterable[dict[str, object]],
    product_by_code: dict[str, uuid.UUID],
    warehouse_by_code: dict[str, uuid.UUID],
) -> tuple[int, int]:
    count = 0
    lineage_count = 0
    async for row in inventory_rows:
        product_code = _as_text(row.get("product_legacy_code"))
        warehouse_code = _as_text(row.get("warehouse_code"))
        product_id = product_by_code.get(product_code)
        warehouse_id = warehouse_by_code.get(warehouse_code)
        if product_id is None or warehouse_id is None:
            raise ValueError(
                "Inventory dependency missing for "
                f"product={product_code} warehouse={warehouse_code}"
            )
        inventory_id = _tenant_scoped_uuid(
            tenant_id,
            "inventory-stock",
            product_code,
            warehouse_code,
        )
        await connection.execute(
            """
			INSERT INTO inventory_stock (
				id,
				tenant_id,
				product_id,
				warehouse_id,
				quantity,
				reorder_point,
				updated_at
			)
			VALUES ($1, $2, $3, $4, $5, $6, NOW())
			ON CONFLICT (id) DO UPDATE SET
				quantity = EXCLUDED.quantity,
				reorder_point = EXCLUDED.reorder_point,
				updated_at = NOW()
			""",
            inventory_id,
            tenant_id,
            product_id,
            warehouse_id,
            int(_as_decimal(row.get("quantity_on_hand"))),
            _as_int(row.get("reorder_point")),
        )
        await _upsert_lineage(
            connection,
            schema_name,
            run_id,
            tenant_id,
            batch_id,
            "inventory_stock",
            inventory_id,
            _as_text(row.get("source_table")) or "tbsstkhouse",
            f"{product_code}:{warehouse_code}",
            _as_int(row.get("source_row_number")),
        )
        count += 1
        lineage_count += 1
    return count, lineage_count


async def _import_sales_history(
    connection,
    schema_name: str,
    run_id: uuid.UUID,
    tenant_id: uuid.UUID,
    batch_id: str,
    headers: list[dict[str, object]],
    lines: list[dict[str, object]],
    customer_by_code: dict[str, uuid.UUID],
    business_number_by_code: dict[str, str],
    product_by_code: dict[str, uuid.UUID],
    product_mappings: dict[str, str],
) -> tuple[int, int, int, int, int]:
    lines_by_doc: dict[str, list[dict[str, object]]] = {}
    for row in lines:
        lines_by_doc.setdefault(_as_text(row.get("doc_number")), []).append(row)

    order_count = 0
    order_line_count = 0
    invoice_count = 0
    invoice_line_count = 0
    lineage_count = 0

    for header in headers:
        doc_number = _as_text(header.get("doc_number"))
        customer_code = _as_text(header.get("customer_code"))
        customer_id = customer_by_code.get(customer_code)
        if customer_id is None:
            continue

        invoice_date = _as_legacy_date(header.get("invoice_date"))
        created_at = _as_timestamp(invoice_date)
        order_id = _tenant_scoped_uuid(tenant_id, "order", doc_number)
        invoice_id = _tenant_scoped_uuid(tenant_id, "invoice", doc_number)
        legacy_header_snapshot = _build_sales_header_snapshot(header)

        await connection.execute(
            """
			INSERT INTO orders (
				id,
				tenant_id,
				customer_id,
				order_number,
				status,
				payment_terms_code,
				payment_terms_days,
				subtotal_amount,
				tax_amount,
				total_amount,
				invoice_id,
				notes,
                legacy_header_snapshot,
				created_by,
				created_at,
				updated_at,
				confirmed_at
			)
            VALUES (
                $1,
                $2,
                $3,
                $4,
                'confirmed',
                'NET_30',
                30,
                $5,
                $6,
                $7,
                NULL,
                $8,
                $9::json,
                $10,
                $11,
                $11,
                $11
            )
			ON CONFLICT (id) DO UPDATE SET
				customer_id = EXCLUDED.customer_id,
				order_number = EXCLUDED.order_number,
				status = EXCLUDED.status,
				subtotal_amount = EXCLUDED.subtotal_amount,
				tax_amount = EXCLUDED.tax_amount,
				total_amount = EXCLUDED.total_amount,
				notes = EXCLUDED.notes,
                legacy_header_snapshot = EXCLUDED.legacy_header_snapshot,
				created_by = EXCLUDED.created_by,
				updated_at = NOW(),
				confirmed_at = EXCLUDED.confirmed_at
			""",
            order_id,
            tenant_id,
            customer_id,
            doc_number,
            _as_decimal(header.get("subtotal"), "0.00"),
            _as_decimal(header.get("tax_amount"), "0.00"),
            _as_decimal(header.get("total_amount"), "0.00"),
            _as_text(header.get("remark")) or None,
            json.dumps(legacy_header_snapshot),
            _as_text(header.get("created_by")) or "legacy-import",
            created_at,
        )
        await _upsert_lineage(
            connection,
            schema_name,
            run_id,
            tenant_id,
            batch_id,
            "orders",
            order_id,
            "tbsslipx",
            doc_number,
            _as_int(header.get("source_row_number")),
        )
        order_count += 1
        lineage_count += 1

        await connection.execute(
            """
			INSERT INTO invoices (
				id,
				tenant_id,
				invoice_number,
				invoice_date,
				customer_id,
				buyer_type,
				buyer_identifier_snapshot,
				currency_code,
				subtotal_amount,
				tax_amount,
				total_amount,
				status,
				version,
                legacy_header_snapshot,
				order_id,
				created_at,
				updated_at
			)
            VALUES ($1, $2, $3, $4, $5, 'b2b', $6, $7, $8, $9, $10, 'issued', 1, $11::json, $12, $13, $13)
			ON CONFLICT (id) DO UPDATE SET
				invoice_number = EXCLUDED.invoice_number,
				invoice_date = EXCLUDED.invoice_date,
				customer_id = EXCLUDED.customer_id,
				buyer_type = EXCLUDED.buyer_type,
				buyer_identifier_snapshot = EXCLUDED.buyer_identifier_snapshot,
				currency_code = EXCLUDED.currency_code,
				subtotal_amount = EXCLUDED.subtotal_amount,
				tax_amount = EXCLUDED.tax_amount,
				total_amount = EXCLUDED.total_amount,
				status = EXCLUDED.status,
                legacy_header_snapshot = EXCLUDED.legacy_header_snapshot,
				order_id = EXCLUDED.order_id,
				updated_at = NOW()
			""",
            invoice_id,
            tenant_id,
            doc_number,
            invoice_date,
            customer_id,
            business_number_by_code.get(customer_code) or "00000000",
            _currency_code(header.get("currency_code")),
            _as_decimal(header.get("subtotal"), "0.00"),
            _as_decimal(header.get("tax_amount"), "0.00"),
            _as_decimal(header.get("total_amount"), "0.00"),
            json.dumps(legacy_header_snapshot),
            order_id,
            created_at,
        )
        await connection.execute(
            """
			UPDATE orders
			SET invoice_id = $1, updated_at = NOW()
			WHERE id = $2 AND tenant_id = $3
			""",
            invoice_id,
            order_id,
            tenant_id,
        )
        await _upsert_lineage(
            connection,
            schema_name,
            run_id,
            tenant_id,
            batch_id,
            "invoices",
            invoice_id,
            "tbsslipx",
            doc_number,
            _as_int(header.get("source_row_number")),
        )
        invoice_count += 1
        lineage_count += 1

        for line in sorted(
            lines_by_doc.get(doc_number, []), key=lambda item: _as_int(item.get("line_number"), 0)
        ):
            legacy_product_code = _as_text(line.get("product_code"))
            mapped_product_code = product_mappings.get(legacy_product_code) or legacy_product_code
            if mapped_product_code not in product_by_code:
                mapped_product_code = UNKNOWN_PRODUCT_CODE
            product_id = product_by_code.get(mapped_product_code)
            if product_id is None:
                raise ValueError(
                    "Sales line "
                    f"{doc_number}:{_as_int(line.get('line_number'))} "
                    f"cannot resolve product {legacy_product_code}"
                )

            line_number = _as_int(line.get("line_number"), 1)
            # col_21 = discounted/actual unit price; col_19 = foldprice (may be pre-adjusted)
            list_unit_price = _as_decimal(line.get("list_unit_price"), "0.00")
            unit_price = _as_decimal(line.get("unit_price"), "0.00")
            extended_amount = _as_decimal(line.get("extended_amount"), "0.00")
            # col_23 = actual quantity
            quantity = _as_decimal(line.get("qty"), "0")
            # Check for pre-adjusted foldprice: sexp1/col_44 holds original list when
            # foldprice was already set to the post-discount price (fnewprice * fdisper)
            original_list_price = _as_decimal(line.get("original_list_price"), None)
            original_discount_ratio = _as_decimal(line.get("original_discount_ratio"), None)
            if (
                original_list_price is not None
                and original_discount_ratio is not None
                and original_list_price > list_unit_price
                and Decimal("0") < original_discount_ratio < Decimal("1")
            ):
                # foldprice was pre-adjusted; use sexp1 as the true original list price
                actual_list_price = original_list_price
            else:
                actual_list_price = list_unit_price
            # Discount per unit: original list - unit (always >= 0)
            discount_amount = max(
                Decimal("0.00"),
                (actual_list_price - unit_price).quantize(Decimal("0.01")),
            )
            subtotal = extended_amount  # already the discounted subtotal
            # col_22 = line tax amount, col_23 = qty, col_29 = subtotal
            # Derive effective tax rate: rate = line_tax / subtotal
            line_tax_amount = _as_decimal(line.get("line_tax_amount"), "0.00")
            line_total = subtotal + line_tax_amount
            # Clamp BEFORE quantizing to avoid rounding overflow; max(0, ...) handles bad data
            MAX_TAX_RATE = Decimal("99.9999")
            MIN_TAX_RATE = Decimal("0.0000")
            raw_rate = (
                (line_tax_amount / extended_amount * Decimal("100"))
                if extended_amount
                else Decimal("0")
            )
            tax_rate = max(MIN_TAX_RATE, min(raw_rate, MAX_TAX_RATE)).quantize(Decimal("0.0001"))
            tax_policy_code = "standard" if line_tax_amount > 0 else "exempt"
            tax_type = 1 if line_tax_amount > 0 else 3
            order_line_id = _tenant_scoped_uuid(
                tenant_id,
                "order-line",
                doc_number,
                str(line_number),
            )
            invoice_line_id = _tenant_scoped_uuid(
                tenant_id, "invoice-line", doc_number, str(line_number)
            )


            await connection.execute(
                """
				INSERT INTO order_lines (
					id,
					tenant_id,
					order_id,
					product_id,
					line_number,
					quantity,
					list_unit_price,
					unit_price,
					discount_amount,
					tax_policy_code,
					tax_type,
					tax_rate,
					tax_amount,
					subtotal_amount,
					total_amount,
					description,
					available_stock_snapshot,
					backorder_note,
					created_at
				)
                VALUES (
                    $1,
                    $2,
                    $3,
                    $4,
                    $5,
                    $6,
                    $7,
                    $8,
                    $9,
                    $10,
                    $11,
                    $12,
                    $13,
                    $14,
                    $15,
                    $16,
                    $17,
                    $18,
                    NOW()
                )
				ON CONFLICT (id) DO UPDATE SET
					product_id = EXCLUDED.product_id,
					line_number = EXCLUDED.line_number,
					quantity = EXCLUDED.quantity,
					list_unit_price = EXCLUDED.list_unit_price,
					unit_price = EXCLUDED.unit_price,
					discount_amount = EXCLUDED.discount_amount,
					tax_policy_code = EXCLUDED.tax_policy_code,
					tax_type = EXCLUDED.tax_type,
					tax_rate = EXCLUDED.tax_rate,
					tax_amount = EXCLUDED.tax_amount,
					subtotal_amount = EXCLUDED.subtotal_amount,
					total_amount = EXCLUDED.total_amount,
					description = EXCLUDED.description,
					available_stock_snapshot = EXCLUDED.available_stock_snapshot
				""",
                order_line_id,
                tenant_id,
                order_id,
                product_id,
                line_number,
                quantity,
                actual_list_price,
                unit_price,
                discount_amount,
                tax_policy_code,
                tax_type,
                tax_rate,
                line_tax_amount,
                subtotal,
                line_total,
                _as_text(line.get("product_name")) or legacy_product_code,
                _as_decimal(line.get("available_stock_snapshot"), "0"),
                None,  # backorder_note: legacy import does not calculate backorder status
            )
            await _upsert_lineage(
                connection,
                schema_name,
                run_id,
                tenant_id,
                batch_id,
                "order_lines",
                order_line_id,
                "tbsslipdtx",
                f"{doc_number}:{line_number}",
                _as_int(line.get("source_row_number")),
            )
            order_line_count += 1
            lineage_count += 1

            await connection.execute(
                """
				INSERT INTO invoice_lines (
					id,
					invoice_id,
					tenant_id,
					line_number,
					product_id,
					product_code_snapshot,
					description,
					quantity,
					unit_price,
					subtotal_amount,
					tax_type,
					tax_rate,
					tax_amount,
					total_amount,
					zero_tax_rate_reason,
					created_at
				)
				VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, NULL, NOW())
				ON CONFLICT (id) DO UPDATE SET
					invoice_id = EXCLUDED.invoice_id,
					line_number = EXCLUDED.line_number,
					product_id = EXCLUDED.product_id,
					product_code_snapshot = EXCLUDED.product_code_snapshot,
					description = EXCLUDED.description,
					quantity = EXCLUDED.quantity,
					unit_price = EXCLUDED.unit_price,
					subtotal_amount = EXCLUDED.subtotal_amount,
					tax_type = EXCLUDED.tax_type,
					tax_rate = EXCLUDED.tax_rate,
					tax_amount = EXCLUDED.tax_amount,
					total_amount = EXCLUDED.total_amount
				""",
                invoice_line_id,
                invoice_id,
                tenant_id,
                line_number,
                product_id,
                legacy_product_code,
                _as_text(line.get("product_name")) or legacy_product_code,
                quantity,
                unit_price,
                subtotal,
                tax_type,
                tax_rate,
                line_tax_amount,
                line_total,
            )
            await _upsert_lineage(
                connection,
                schema_name,
                run_id,
                tenant_id,
                batch_id,
                "invoice_lines",
                invoice_line_id,
                "tbsslipdtx",
                f"{doc_number}:{line_number}",
                _as_int(line.get("source_row_number")),
            )
            invoice_line_count += 1
            lineage_count += 1

        # Recalculate order and invoice totals from the inserted lines
        # to correct discrepancies between tbsslipx header totals and actual line sums
        line_totals = await connection.fetch(
            """
            SELECT
                SUM(subtotal_amount) AS subtotal,
                SUM(tax_amount) AS tax,
                SUM(total_amount) AS total
            FROM order_lines
            WHERE tenant_id = $1 AND order_id = $2
            """,
            tenant_id,
            order_id,
        )
        if line_totals and line_totals[0]:
            row = line_totals[0]
            recalc_subtotal = row["subtotal"] or Decimal("0.00")
            recalc_tax = row["tax"] or Decimal("0.00")
            recalc_total = row["total"] or Decimal("0.00")
            await connection.execute(
                """
                UPDATE orders
                SET subtotal_amount = $1, tax_amount = $2, total_amount = $3, updated_at = NOW()
                WHERE id = $4
                """,
                recalc_subtotal,
                recalc_tax,
                recalc_total,
                order_id,
            )
            await connection.execute(
                """
                UPDATE invoices
                SET subtotal_amount = $1, tax_amount = $2, total_amount = $3, updated_at = NOW()
                WHERE id = $4
                """,
                recalc_subtotal,
                recalc_tax,
                recalc_total,
                invoice_id,
            )

    return order_count, order_line_count, invoice_count, invoice_line_count, lineage_count


def _allocate_tax_amounts(
    subtotals: list[Decimal],
    total_tax_amount: Decimal,
) -> list[Decimal]:
    if not subtotals:
        return []

    total_tax_amount = _as_money(total_tax_amount)
    if total_tax_amount == Decimal("0.00"):
        return [Decimal("0.00")] * len(subtotals)

    subtotal_total = sum(subtotals, Decimal("0.00"))
    if subtotal_total == Decimal("0.00"):
        allocations = [Decimal("0.00")] * len(subtotals)
        allocations[-1] = total_tax_amount
        return allocations

    allocations: list[Decimal] = []
    running_total = Decimal("0.00")
    for index, subtotal in enumerate(subtotals):
        if index == len(subtotals) - 1:
            allocation = total_tax_amount - running_total
        else:
            allocation = _as_money((total_tax_amount * subtotal) / subtotal_total)
            running_total += allocation
        allocations.append(_as_money(allocation))
    return allocations


async def _import_purchase_history(
    connection,
    schema_name: str,
    run_id: uuid.UUID,
    tenant_id: uuid.UUID,
    batch_id: str,
    headers: list[dict[str, object]],
    lines: list[dict[str, object]],
    supplier_by_code: dict[str, uuid.UUID],
    product_by_code: dict[str, uuid.UUID],
    product_mappings: dict[str, str],
) -> tuple[int, int, int]:
    lines_by_doc: dict[str, list[dict[str, object]]] = {}
    for row in lines:
        lines_by_doc.setdefault(_as_text(row.get("doc_number")), []).append(row)

    invoice_count = 0
    invoice_line_count = 0
    lineage_count = 0

    for header in headers:
        doc_number = _as_text(header.get("doc_number"))
        if not doc_number:
            raise ValueError("Purchase header is missing doc_number")
        invoice_number = _as_text(header.get("invoice_number")) or doc_number
        if not invoice_number:
            raise ValueError(f"Purchase header {doc_number} is missing invoice_number")
        supplier_code = _as_text(header.get("supplier_code"))
        supplier_id = supplier_by_code.get(supplier_code)
        if supplier_id is None:
            raise ValueError(
                f"Purchase header {doc_number} references missing supplier {supplier_code}"
            )

        invoice_date = _as_legacy_date(header.get("invoice_date"))
        if invoice_date is None:
            raise ValueError(f"Purchase header {doc_number} is missing invoice_date")

        created_at = _as_timestamp(invoice_date)
        supplier_invoice_id = _tenant_scoped_uuid(tenant_id, "supplier-invoice", doc_number)
        tax_amount = _as_money(_as_decimal(header.get("tax_amount"), "0.00"))
        legacy_header_snapshot = _build_purchase_header_snapshot(header)

        await connection.execute(
            """
			INSERT INTO supplier_invoices (
				id,
				tenant_id,
				supplier_id,
				invoice_number,
				invoice_date,
				currency_code,
				subtotal_amount,
				tax_amount,
				total_amount,
				status,
				notes,
                legacy_header_snapshot,
				created_at,
				updated_at
			)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, 'open', $10, $11::json, $12, $12)
			ON CONFLICT (id) DO UPDATE SET
				supplier_id = EXCLUDED.supplier_id,
				invoice_number = EXCLUDED.invoice_number,
				invoice_date = EXCLUDED.invoice_date,
				currency_code = EXCLUDED.currency_code,
				subtotal_amount = EXCLUDED.subtotal_amount,
				tax_amount = EXCLUDED.tax_amount,
				total_amount = EXCLUDED.total_amount,
				status = EXCLUDED.status,
				notes = EXCLUDED.notes,
                legacy_header_snapshot = EXCLUDED.legacy_header_snapshot,
				updated_at = NOW()
			""",
            supplier_invoice_id,
            tenant_id,
            supplier_id,
            invoice_number,
            invoice_date,
            _currency_code(header.get("currency_code")),
            _as_money(_as_decimal(header.get("subtotal"), "0.00")),
            tax_amount,
            _as_money(_as_decimal(header.get("total_amount"), "0.00")),
            _as_text(header.get("notes")) or None,
            json.dumps(legacy_header_snapshot),
            created_at,
        )
        await _upsert_lineage(
            connection,
            schema_name,
            run_id,
            tenant_id,
            batch_id,
            "supplier_invoices",
            supplier_invoice_id,
            "tbsslipj",
            doc_number,
            _as_int(header.get("source_row_number")),
        )
        invoice_count += 1
        lineage_count += 1

        header_lines = sorted(
            lines_by_doc.get(doc_number, []), key=lambda item: _as_int(item.get("line_number"), 0)
        )
        line_subtotals = [
            _as_money(_as_decimal(line.get("extended_amount"), "0.00"))
            for line in header_lines
        ]
        line_tax_amounts = _allocate_tax_amounts(line_subtotals, tax_amount)

        for line, line_tax_amount in zip(header_lines, line_tax_amounts, strict=False):
            legacy_product_code = _as_text(line.get("product_code"))
            mapped_product_code = product_mappings.get(legacy_product_code) or legacy_product_code
            if mapped_product_code not in product_by_code:
                mapped_product_code = UNKNOWN_PRODUCT_CODE
            product_id = product_by_code.get(mapped_product_code)
            if product_id is None:
                raise ValueError(
                    "Purchase line "
                    f"{doc_number}:{_as_int(line.get('line_number'))} "
                    f"cannot resolve product {legacy_product_code}"
                )

            line_number = _as_int(line.get("line_number"), 1)
            quantity = _as_decimal(line.get("qty"), "0")
            unit_price = _as_money(_as_decimal(line.get("unit_price"), "0.00"))
            subtotal = _as_money(_as_decimal(line.get("extended_amount"), "0.00"))
            line_total = _as_money(subtotal + line_tax_amount)
            _, tax_type, tax_rate = _tax_policy_code(line_tax_amount)
            supplier_invoice_line_id = _tenant_scoped_uuid(
                tenant_id,
                "supplier-invoice-line",
                doc_number,
                str(line_number),
            )

            await connection.execute(
                """
				INSERT INTO supplier_invoice_lines (
					id,
					supplier_invoice_id,
					tenant_id,
					line_number,
					product_id,
					product_code_snapshot,
					description,
					quantity,
					unit_price,
					subtotal_amount,
					tax_type,
					tax_rate,
					tax_amount,
					total_amount,
					created_at
				)
				VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, NOW())
				ON CONFLICT (id) DO UPDATE SET
					supplier_invoice_id = EXCLUDED.supplier_invoice_id,
					line_number = EXCLUDED.line_number,
					product_id = EXCLUDED.product_id,
					product_code_snapshot = EXCLUDED.product_code_snapshot,
					description = EXCLUDED.description,
					quantity = EXCLUDED.quantity,
					unit_price = EXCLUDED.unit_price,
					subtotal_amount = EXCLUDED.subtotal_amount,
					tax_type = EXCLUDED.tax_type,
					tax_rate = EXCLUDED.tax_rate,
					tax_amount = EXCLUDED.tax_amount,
					total_amount = EXCLUDED.total_amount
				""",
                supplier_invoice_line_id,
                supplier_invoice_id,
                tenant_id,
                line_number,
                product_id,
                legacy_product_code,
                legacy_product_code,
                quantity,
                unit_price,
                subtotal,
                tax_type,
                tax_rate,
                line_tax_amount,
                line_total,
            )
            await _upsert_lineage(
                connection,
                schema_name,
                run_id,
                tenant_id,
                batch_id,
                "supplier_invoice_lines",
                supplier_invoice_line_id,
                "tbsslipdtj",
                f"{doc_number}:{line_number}",
                _as_int(line.get("source_row_number")),
            )
            invoice_line_count += 1
            lineage_count += 1

    return invoice_count, invoice_line_count, lineage_count


async def _hold_payment_adjacent_history(
    connection,
    schema_name: str,
    run_id: uuid.UUID,
    tenant_id: uuid.UUID,
    batch_id: str,
) -> int:
    quoted_schema = _quoted_identifier(schema_name)
    total = 0
    for table_name in ("tbsprepay", "tbsspay"):
        if not await _table_exists(connection, schema_name, table_name):
            continue
        async for raw_row in _iter_query_rows(
            connection,
            f"""
			SELECT *
			FROM {quoted_schema}.{table_name}
			WHERE _batch_id = $1
			ORDER BY _source_row_number
			""",
            batch_id,
        ):
            source_identifier = (
                _as_text(raw_row.get("col_2"))
                or f"{table_name}:{_as_int(raw_row.get('_source_row_number'))}"
            )
            await _upsert_holding_row(
                connection,
                schema_name,
                run_id,
                tenant_id,
                batch_id,
                "payment_history",
                table_name,
                source_identifier,
                _as_int(raw_row.get("_source_row_number")),
                raw_row,
                (
                    "Payment-adjacent legacy rows are preserved in holding "
                    "until a verified payment mapping is defined."
                ),
            )
            total += 1
    return total


async def run_canonical_import(
    *,
    batch_id: str,
    tenant_id: uuid.UUID = DEFAULT_TENANT_ID,
    schema_name: str | None = None,
) -> CanonicalImportResult:
    resolved_schema = schema_name or settings.legacy_import_schema
    connection = await _open_raw_connection()
    run_id = uuid.uuid4()
    attempt_number = 1
    step_outcomes: list[tuple[str, int, str, str | None]] = []
    counts: dict[str, int] = {
        "customer_count": 0,
        "supplier_count": 0,
        "product_count": 0,
        "warehouse_count": 0,
        "inventory_count": 0,
        "order_count": 0,
        "order_line_count": 0,
        "invoice_count": 0,
        "invoice_line_count": 0,
        "supplier_invoice_count": 0,
        "supplier_invoice_line_count": 0,
        "holding_count": 0,
        "lineage_count": 0,
    }
    current_step: str | None = None
    try:
        await _ensure_canonical_support_tables(connection, resolved_schema)
        attempt_number = await _next_attempt_number(
            connection, resolved_schema, batch_id, tenant_id
        )

        product_mappings = await _fetch_product_mappings(connection, resolved_schema, tenant_id)

        async with connection.transaction():
            await _upsert_run_row(
                connection,
                resolved_schema,
                run_id,
                tenant_id,
                batch_id,
                attempt_number,
                "running",
                counts,
                None,
            )

            current_step = "customers"
            (
                counts["customer_count"],
                customer_lineage_count,
                customer_by_code,
                business_number_by_code,
            ) = await _import_customers(
                connection,
                resolved_schema,
                run_id,
                tenant_id,
                batch_id,
                _iter_normalized_parties(connection, resolved_schema, batch_id, tenant_id),
            )
            counts["lineage_count"] += customer_lineage_count
            step_outcomes.append(("customers", counts["customer_count"], "completed", None))
            await _upsert_step_row(
                connection,
                resolved_schema,
                run_id,
                "customers",
                counts["customer_count"],
                "completed",
            )

            current_step = "suppliers"
            (
                counts["supplier_count"],
                supplier_lineage_count,
                supplier_by_code,
            ) = await _import_suppliers(
                connection,
                resolved_schema,
                run_id,
                tenant_id,
                batch_id,
                _iter_normalized_parties(connection, resolved_schema, batch_id, tenant_id),
            )
            counts["lineage_count"] += supplier_lineage_count
            step_outcomes.append(("suppliers", counts["supplier_count"], "completed", None))
            await _upsert_step_row(
                connection,
                resolved_schema,
                run_id,
                "suppliers",
                counts["supplier_count"],
                "completed",
            )

            current_step = "products"
            (
                counts["product_count"],
                product_lineage_count,
                product_by_code,
            ) = await _import_products(
                connection,
                resolved_schema,
                run_id,
                tenant_id,
                batch_id,
                _iter_normalized_products(connection, resolved_schema, batch_id, tenant_id),
            )
            counts["lineage_count"] += product_lineage_count
            step_outcomes.append(("products", counts["product_count"], "completed", None))
            await _upsert_step_row(
                connection,
                resolved_schema,
                run_id,
                "products",
                counts["product_count"],
                "completed",
            )

            current_step = "warehouses"
            (
                counts["warehouse_count"],
                warehouse_lineage_count,
                warehouse_by_code,
            ) = await _import_warehouses(
                connection,
                resolved_schema,
                run_id,
                tenant_id,
                batch_id,
                _iter_normalized_warehouses(connection, resolved_schema, batch_id, tenant_id),
            )
            counts["lineage_count"] += warehouse_lineage_count
            step_outcomes.append(("warehouses", counts["warehouse_count"], "completed", None))
            await _upsert_step_row(
                connection,
                resolved_schema,
                run_id,
                "warehouses",
                counts["warehouse_count"],
                "completed",
            )

            current_step = "inventory"
            counts["inventory_count"], inventory_lineage_count = await _import_inventory(
                connection,
                resolved_schema,
                run_id,
                tenant_id,
                batch_id,
                _iter_normalized_inventory(connection, resolved_schema, batch_id, tenant_id),
                product_by_code,
                warehouse_by_code,
            )
            counts["lineage_count"] += inventory_lineage_count
            step_outcomes.append(("inventory", counts["inventory_count"], "completed", None))
            await _upsert_step_row(
                connection,
                resolved_schema,
                run_id,
                "inventory",
                counts["inventory_count"],
                "completed",
            )

            current_step = "sales_history"
            (
                counts["order_count"],
                counts["order_line_count"],
                counts["invoice_count"],
                counts["invoice_line_count"],
                sales_lineage_count,
            ) = await _import_sales_history(
                connection,
                resolved_schema,
                run_id,
                tenant_id,
                batch_id,
                await _fetch_sales_headers(connection, resolved_schema, batch_id),
                await _fetch_sales_lines(connection, resolved_schema, batch_id),
                customer_by_code,
                business_number_by_code,
                product_by_code,
                product_mappings,
            )
            counts["lineage_count"] += sales_lineage_count
            step_outcomes.append(
                (
                    "sales_history",
                    counts["order_line_count"] + counts["invoice_line_count"],
                    "completed",
                    None,
                )
            )
            await _upsert_step_row(
                connection,
                resolved_schema,
                run_id,
                "sales_history",
                counts["order_line_count"] + counts["invoice_line_count"],
                "completed",
            )

            current_step = "purchase_history"
            (
                counts["supplier_invoice_count"],
                counts["supplier_invoice_line_count"],
                purchase_lineage_count,
            ) = await _import_purchase_history(
                connection,
                resolved_schema,
                run_id,
                tenant_id,
                batch_id,
                (
                    await _fetch_purchase_headers(connection, resolved_schema, batch_id)
                    if await _table_exists(connection, resolved_schema, "tbsslipj")
                    else []
                ),
                (
                    await _fetch_purchase_lines(connection, resolved_schema, batch_id)
                    if await _table_exists(connection, resolved_schema, "tbsslipdtj")
                    else []
                ),
                supplier_by_code,
                product_by_code,
                product_mappings,
            )
            counts["lineage_count"] += purchase_lineage_count
            step_outcomes.append(
                (
                    "purchase_history",
                    counts["supplier_invoice_count"] + counts["supplier_invoice_line_count"],
                    "completed",
                    None,
                )
            )
            await _upsert_step_row(
                connection,
                resolved_schema,
                run_id,
                "purchase_history",
                counts["supplier_invoice_count"] + counts["supplier_invoice_line_count"],
                "completed",
            )

            current_step = "unsupported_history"
            payment_holding_count = await _hold_payment_adjacent_history(
                connection,
                resolved_schema,
                run_id,
                tenant_id,
                batch_id,
            )
            counts["holding_count"] = payment_holding_count
            step_outcomes.append(
                ("unsupported_history", counts["holding_count"], "completed", None)
            )
            await _upsert_step_row(
                connection,
                resolved_schema,
                run_id,
                "unsupported_history",
                counts["holding_count"],
                "completed",
            )

            await _upsert_run_row(
                connection,
                resolved_schema,
                run_id,
                tenant_id,
                batch_id,
                attempt_number,
                "completed",
                counts,
                None,
            )
            current_step = None

        return CanonicalImportResult(
            batch_id=batch_id,
            schema_name=resolved_schema,
            attempt_number=attempt_number,
            customer_count=counts["customer_count"],
            supplier_count=counts["supplier_count"],
            product_count=counts["product_count"],
            warehouse_count=counts["warehouse_count"],
            inventory_count=counts["inventory_count"],
            order_count=counts["order_count"],
            order_line_count=counts["order_line_count"],
            invoice_count=counts["invoice_count"],
            invoice_line_count=counts["invoice_line_count"],
            supplier_invoice_count=counts["supplier_invoice_count"],
            supplier_invoice_line_count=counts["supplier_invoice_line_count"],
            holding_count=counts["holding_count"],
            lineage_count=counts["lineage_count"],
        )
    except Exception as exc:
        if current_step is not None:
            step_outcomes.append(
                (
                    current_step,
                    _step_row_count(current_step, counts),
                    "failed",
                    str(exc),
                )
            )
        failure_summary = dict(counts)
        async with connection.transaction():
            await _upsert_run_row(
                connection,
                resolved_schema,
                run_id,
                tenant_id,
                batch_id,
                attempt_number,
                "failed",
                failure_summary,
                str(exc),
            )
            for step_name, row_count, status, error_message in step_outcomes:
                await _upsert_step_row(
                    connection,
                    resolved_schema,
                    run_id,
                    step_name,
                    row_count,
                    status,
                    error_message,
                )
        raise
    finally:
        await connection.close()
