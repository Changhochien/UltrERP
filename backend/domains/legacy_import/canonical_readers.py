"""Raw legacy readers and staging iterators for canonical import flows."""

from __future__ import annotations

import uuid
from typing import Any, AsyncIterator, cast

from domains.legacy_import.canonical_common import _as_text, _coerce_row
from domains.legacy_import.staging import _quoted_identifier


async def _iter_query_rows(
    connection,
    query: str,
    *args: object,
) -> AsyncIterator[dict[str, object]]:
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
    connection,
    schema_name: str,
    batch_id: str,
    tenant_id: uuid.UUID,
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
            customer_type,
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
    connection,
    schema_name: str,
    batch_id: str,
    tenant_id: uuid.UUID,
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
			legacy_category,
			stock_kind,
			category_source,
            category_rule_id,
            category_confidence,
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
    connection,
    schema_name: str,
    batch_id: str,
    tenant_id: uuid.UUID,
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
    connection,
    schema_name: str,
    batch_id: str,
    tenant_id: uuid.UUID,
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
    connection,
    schema_name: str,
    tenant_id: uuid.UUID,
) -> AsyncIterator[tuple[str, str]]:
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
    connection,
    schema_name: str,
    tenant_id: uuid.UUID,
) -> dict[str, str]:
    result: dict[str, str] = {}
    async for legacy, target in _iter_product_mappings(connection, schema_name, tenant_id):
        result[legacy] = target
    return result


async def _fetch_sales_headers(
    connection,
    schema_name: str,
    batch_id: str,
    doc_numbers: frozenset[str] | None = None,
) -> list[dict[str, object]]:
    quoted_schema = _quoted_identifier(schema_name)
    where_clauses = ["_batch_id = $1"]
    query_args: list[object] = [batch_id]
    if doc_numbers:
        where_clauses.append("col_2 = ANY($2::text[])")
        query_args.append(sorted(doc_numbers))

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
        WHERE {' AND '.join(where_clauses)}
		ORDER BY col_2
		""",
        *query_args,
    )
    return [_coerce_row(row) for row in rows]


async def _fetch_sales_lines(
    connection,
    schema_name: str,
    batch_id: str,
    doc_numbers: frozenset[str] | None = None,
) -> list[dict[str, object]]:
    quoted_schema = _quoted_identifier(schema_name)
    where_clauses = ["dtx._batch_id = $1"]
    query_args: list[object] = [batch_id]
    if doc_numbers:
        where_clauses.append("dtx.col_2 = ANY($2::text[])")
        query_args.append(sorted(doc_numbers))

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
        WHERE {' AND '.join(where_clauses)}
		GROUP BY dtx.col_2, dtx.col_3, dtx.col_7, dtx.col_8, dtx.col_18,
			dtx.col_19, dtx.col_21, dtx.col_22, dtx.col_23, dtx.col_29,
			dtx.col_44, dtx.col_45, dtx._source_row_number
		ORDER BY dtx.col_2, dtx.col_3
		""",
        *query_args,
    )
    return [_coerce_row(row) for row in rows]


async def _fetch_purchase_headers(
    connection,
    schema_name: str,
    batch_id: str,
    doc_numbers: frozenset[str] | None = None,
) -> list[dict[str, object]]:
    quoted_schema = _quoted_identifier(schema_name)
    where_clauses = ["_batch_id = $1", "COALESCE(col_1, '') = '4'"]
    query_args: list[object] = [batch_id]
    if doc_numbers:
        where_clauses.append("col_2 = ANY($2::text[])")
        query_args.append(sorted(doc_numbers))

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
            col_48 AS must_pay_amount,
            CASE
                WHEN (COALESCE(col_17::numeric, 0) + COALESCE(col_19::numeric, 0)) <> 0
                    THEN (COALESCE(col_17::numeric, 0) + COALESCE(col_19::numeric, 0))
                ELSE col_49::numeric
            END AS total_amount,
			_source_row_number AS source_row_number
		FROM {quoted_schema}.tbsslipj
		WHERE {' AND '.join(where_clauses)}
		ORDER BY col_2
		""",
        *query_args,
    )
    return [_coerce_row(row) for row in rows]


async def _fetch_purchase_lines(
    connection,
    schema_name: str,
    batch_id: str,
    doc_numbers: frozenset[str] | None = None,
) -> list[dict[str, object]]:
    quoted_schema = _quoted_identifier(schema_name)
    where_clauses = ["_batch_id = $1", "COALESCE(col_1, '') = '4'"]
    query_args: list[object] = [batch_id]
    if doc_numbers:
        where_clauses.append("col_2 = ANY($2::text[])")
        query_args.append(sorted(doc_numbers))

    rows = await connection.fetch(
        f"""
		SELECT
			col_2 AS doc_number,
			col_3 AS line_number,
            col_4 AS receipt_date,
			col_6 AS product_code,
			col_7 AS product_name,
			col_16 AS warehouse_code,
			col_18 AS unit,
			col_19 AS foldprice,
			col_20 AS discount_multiplier,
			col_21 AS unit_price,
			col_22 AS qty,
			col_25 AS taxable,
			col_26 AS line_total,
			(col_21::numeric * col_22::numeric) AS extended_amount,
			_source_row_number AS source_row_number
		FROM {quoted_schema}.tbsslipdtj
        WHERE {' AND '.join(where_clauses)}
		ORDER BY col_2, col_3
		""",
        *query_args,
    )
    return [_coerce_row(row) for row in rows]