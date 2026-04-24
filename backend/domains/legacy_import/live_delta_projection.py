"""Live legacy-source projection for incremental delta discovery."""

from __future__ import annotations

import asyncio
import re
from collections.abc import Mapping
from datetime import UTC, date, datetime, timedelta
from typing import Any

from domains.legacy_import.delta_discovery import SourceProjection
from domains.legacy_import.incremental_state import IncrementalDomainContract
from domains.legacy_import.shared import (
    DOMAIN_INVENTORY,
    DOMAIN_PARTIES,
    DOMAIN_PRODUCTS,
    DOMAIN_PURCHASE_INVOICES,
    DOMAIN_SALES,
    DOMAIN_WAREHOUSES,
)
from domains.legacy_import.staging import (
    LegacySourceConnectionSettings,
    _open_legacy_source_connection,
)

_IDENTIFIER_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_EXCEL_SERIAL_EPOCH = datetime(1899, 12, 30, tzinfo=UTC)
_DEFAULT_CHANGE_TS = datetime(1900, 1, 1, tzinfo=UTC)
_MAX_EXCEL_SERIAL = 2_958_465


def _quoted_identifier(value: str) -> str:
    if not _IDENTIFIER_RE.fullmatch(value):
        raise ValueError(f"Unsafe SQL identifier: {value}")
    return f'"{value}"'


def _column_ref(alias: str, column_name: str) -> str:
    return f"{alias}.{_quoted_identifier(column_name)}"


def _parse_iso_datetime(value: object | None) -> datetime | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _parse_iso_date(value: object | None) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    parsed = _parse_iso_datetime(value)
    if parsed is not None:
        return parsed.date()
    text = str(value).strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _bootstrap_anchor(
    bootstrap_rebaseline_state: Mapping[str, Any] | None,
) -> datetime | None:
    if not isinstance(bootstrap_rebaseline_state, Mapping):
        return None
    for field_name in ("completed_at", "recorded_at", "started_at"):
        parsed = _parse_iso_datetime(bootstrap_rebaseline_state.get(field_name))
        if parsed is not None:
            return parsed
    return None


def _change_ts_expression(
    alias: str,
    *,
    timestamp_column: str | None = None,
    modify_column: str | None = None,
    date_column: str | None = None,
) -> str:
    parts: list[str] = []
    if timestamp_column is not None:
        timestamp_ref = _column_ref(alias, timestamp_column)
        parts.append(
            "CASE "
            f"WHEN NULLIF({timestamp_ref}::text, '') IS NOT NULL "
            f"AND length({timestamp_ref}::text) >= 14 "
            f"AND substr({timestamp_ref}::text, 1, 4) BETWEEN '1900' AND '9999' "
            "THEN to_timestamp(substr("
            f"{timestamp_ref}::text, 1, 14), 'YYYYMMDDHH24MISS') + "
            "(COALESCE(NULLIF(substr("
            f"{timestamp_ref}::text, 15, 6), ''), '0')::numeric * interval '0.000001 second') "
            "END"
        )
    if modify_column is not None:
        modify_ref = _column_ref(alias, modify_column)
        parts.append(
            f"CASE WHEN {modify_ref} IS NOT NULL AND {modify_ref} > 0 "
            f"AND {modify_ref} <= {_MAX_EXCEL_SERIAL} "
            f"THEN TIMESTAMP '1899-12-30 00:00:00' + ({modify_ref} * interval '1 day') END"
        )
    if date_column is not None:
        date_ref = _column_ref(alias, date_column)
        parts.append(
            f"CASE WHEN {date_ref} IS NOT NULL THEN {date_ref}::timestamp END"
        )
    parts.append("TIMESTAMP '1900-01-01 00:00:00'")
    return f"COALESCE({', '.join(parts)})"


def _master_cursor_clause(
    *,
    change_ts_expr: str,
    code_exprs: tuple[str, ...],
    watermark: Mapping[str, Any] | None,
    timestamp_key: str,
    code_keys: tuple[str, ...],
    bootstrap_anchor: datetime | None,
) -> tuple[str, list[object]]:
    params: list[object] = []
    if isinstance(watermark, Mapping):
        watermark_ts = _parse_iso_datetime(watermark.get(timestamp_key))
        if watermark_ts is not None:
            params.append(watermark_ts)
            rendered = ["($1::timestamptz AT TIME ZONE 'UTC')"]
            for index, key in enumerate(code_keys, start=2):
                params.append(str(watermark.get(key, "")))
                rendered.append(f"${index}")
            row_expr = ", ".join((change_ts_expr, *code_exprs))
            return f"WHERE ({row_expr}) > ({', '.join(rendered)})", params
    if bootstrap_anchor is not None:
        params.append(bootstrap_anchor)
        return f"WHERE {change_ts_expr} > ($1::timestamptz AT TIME ZONE 'UTC')", params
    return "", params


def _document_cursor_clause(
    *,
    header_alias: str,
    detail_alias: str,
    watermark: Mapping[str, Any] | None,
    bootstrap_anchor: datetime | None,
    header_change_ts_expr: str,
) -> tuple[str, str, list[object]]:
    params: list[object] = []
    if isinstance(watermark, Mapping):
        document_date = _parse_iso_date(watermark.get("document-date"))
        if document_date is not None:
            params.extend(
                (
                    document_date,
                    str(watermark.get("document-number", "")),
                    int(watermark.get("line-number", 0)),
                )
            )
            header_where = (
                f"WHERE ({_column_ref(header_alias, 'dtslipdate')}, "
                f"{_column_ref(header_alias, 'sslipno')}, 0) > ($1::date, $2, $3)"
            )
            detail_where = (
                f"WHERE ({_column_ref(detail_alias, 'dtslipdate')}, "
                f"{_column_ref(detail_alias, 'sslipno')}, {_column_ref(detail_alias, 'iidno')}) "
                "> ($1::date, $2, $3)"
            )
            return header_where, detail_where, params
    if bootstrap_anchor is not None:
        params.append(bootstrap_anchor)
        anchor_expr = "($1::timestamptz AT TIME ZONE 'UTC')"
        header_where = f"WHERE {header_change_ts_expr} > {anchor_expr}"
        detail_where = f"WHERE {header_change_ts_expr} > {anchor_expr}"
        return header_where, detail_where, params
    return "", "", params


async def _fetch_records(
    *,
    query: str,
    parameters: list[object],
    connection_settings: LegacySourceConnectionSettings | None,
):
    connection = await _open_legacy_source_connection(connection_settings)
    try:
        return await connection.fetch(query, *parameters)
    finally:
        await connection.close()


def _change_dt(value: object | None) -> datetime | None:
    if isinstance(value, datetime):
        return value.astimezone(UTC) if value.tzinfo is not None else value.replace(tzinfo=UTC)
    if value is None:
        return None
    digits = "".join(ch for ch in str(value).strip() if ch.isdigit())
    if len(digits) >= 14:
        base = datetime.strptime(digits[:14], "%Y%m%d%H%M%S").replace(tzinfo=UTC)
        if len(digits) == 14:
            return base
        fraction = digits[14:20].ljust(6, "0")[:6]
        return base.replace(microsecond=int(fraction))
    try:
        serial = float(value)
    except (TypeError, ValueError):
        return None
    if serial <= 0:
        return None
    return _EXCEL_SERIAL_EPOCH + timedelta(days=serial)


def _format_change_ts(value: object | None) -> str:
    if isinstance(value, str):
        parsed = _parse_iso_datetime(value)
        if parsed is not None:
            return parsed.isoformat(timespec="microseconds")
        return _DEFAULT_CHANGE_TS.isoformat(timespec="microseconds")
    parsed_value = value if isinstance(value, datetime) else _change_dt(value)
    return (parsed_value or _DEFAULT_CHANGE_TS).astimezone(UTC).isoformat(timespec="microseconds")


async def _project_parties(
    *,
    source_schema: str,
    watermark: Mapping[str, Any] | None,
    bootstrap_anchor: datetime | None,
    connection_settings: LegacySourceConnectionSettings | None,
) -> list[Mapping[str, Any]]:
    quoted_schema = _quoted_identifier(source_schema)
    change_ts_expr = _change_ts_expression(
        "src",
        timestamp_column="stimestamp",
        modify_column="dtmodify",
        date_column="dtcreatedate",
    )
    where_clause, parameters = _master_cursor_clause(
        change_ts_expr=change_ts_expr,
        code_exprs=(_column_ref("src", "scustno"),),
        watermark=watermark,
        timestamp_key="source-change-ts",
        code_keys=("party-code",),
        bootstrap_anchor=bootstrap_anchor,
    )
    query = f"""
        SELECT
            ({change_ts_expr})::text AS change_ts_text,
            EXTRACT(EPOCH FROM {change_ts_expr}) AS change_ts_epoch,
            {_column_ref('src', 'scustno')} AS party_code
        FROM {quoted_schema}.{_quoted_identifier('tbscust')} AS src
        {where_clause}
        ORDER BY change_ts_epoch, party_code
    """
    rows = await _fetch_records(query=query, parameters=parameters, connection_settings=connection_settings)
    return [
        {
            "source-change-ts": _format_change_ts(row["change_ts_text"]),
            "party-code": party_code,
        }
        for row in rows
        if (party_code := str(row["party_code"] or "").strip())
    ]


async def _project_products(
    *,
    source_schema: str,
    watermark: Mapping[str, Any] | None,
    bootstrap_anchor: datetime | None,
    connection_settings: LegacySourceConnectionSettings | None,
) -> list[Mapping[str, Any]]:
    quoted_schema = _quoted_identifier(source_schema)
    change_ts_expr = _change_ts_expression(
        "src",
        timestamp_column="stimestamp",
        modify_column="dtmodify",
        date_column="dtindate",
    )
    where_clause, parameters = _master_cursor_clause(
        change_ts_expr=change_ts_expr,
        code_exprs=(_column_ref("src", "sstkno"),),
        watermark=watermark,
        timestamp_key="source-change-ts",
        code_keys=("product-code",),
        bootstrap_anchor=bootstrap_anchor,
    )
    query = f"""
        SELECT
            ({change_ts_expr})::text AS change_ts_text,
            EXTRACT(EPOCH FROM {change_ts_expr}) AS change_ts_epoch,
            {_column_ref('src', 'sstkno')} AS product_code
        FROM {quoted_schema}.{_quoted_identifier('tbsstock')} AS src
        {where_clause}
        ORDER BY change_ts_epoch, product_code
    """
    rows = await _fetch_records(query=query, parameters=parameters, connection_settings=connection_settings)
    return [
        {
            "source-change-ts": _format_change_ts(row["change_ts_text"]),
            "product-code": product_code,
        }
        for row in rows
        if (product_code := str(row["product_code"] or "").strip())
    ]


async def _project_warehouses(
    *,
    source_schema: str,
    watermark: Mapping[str, Any] | None,
    bootstrap_anchor: datetime | None,
    connection_settings: LegacySourceConnectionSettings | None,
) -> list[Mapping[str, Any]]:
    quoted_schema = _quoted_identifier(source_schema)
    change_ts_expr = _change_ts_expression("src", timestamp_column="stimestamp")
    where_clause, parameters = _master_cursor_clause(
        change_ts_expr=change_ts_expr,
        code_exprs=(_column_ref("src", "shouseno"),),
        watermark=watermark,
        timestamp_key="source-change-ts",
        code_keys=("warehouse-code",),
        bootstrap_anchor=bootstrap_anchor,
    )
    query = f"""
        SELECT
            ({change_ts_expr})::text AS change_ts_text,
            EXTRACT(EPOCH FROM {change_ts_expr}) AS change_ts_epoch,
            {_column_ref('src', 'shouseno')} AS warehouse_code
        FROM {quoted_schema}.{_quoted_identifier('tbsstkhouse')} AS src
        {where_clause}
        ORDER BY change_ts_epoch, warehouse_code
    """
    rows = await _fetch_records(query=query, parameters=parameters, connection_settings=connection_settings)
    return [
        {
            "source-change-ts": _format_change_ts(row["change_ts_text"]),
            "warehouse-code": warehouse_code,
        }
        for row in rows
        if (warehouse_code := str(row["warehouse_code"] or "").strip())
    ]


async def _project_inventory(
    *,
    source_schema: str,
    watermark: Mapping[str, Any] | None,
    bootstrap_anchor: datetime | None,
    connection_settings: LegacySourceConnectionSettings | None,
) -> list[Mapping[str, Any]]:
    quoted_schema = _quoted_identifier(source_schema)
    house_change_ts = _change_ts_expression("house", timestamp_column="stimestamp")
    stock_change_ts = _change_ts_expression(
        "stock",
        timestamp_column="stimestamp",
        modify_column="dtmodify",
        date_column="dtindate",
    )
    house_where, house_params = _master_cursor_clause(
        change_ts_expr=house_change_ts,
        code_exprs=(_column_ref("house", "shouseno"), _column_ref("house", "sstkno")),
        watermark=watermark,
        timestamp_key="source-change-ts",
        code_keys=("warehouse-code", "product-code"),
        bootstrap_anchor=bootstrap_anchor,
    )
    stock_where, stock_params = _master_cursor_clause(
        change_ts_expr=stock_change_ts,
        code_exprs=(_column_ref("house", "shouseno"), _column_ref("stock", "sstkno")),
        watermark=watermark,
        timestamp_key="source-change-ts",
        code_keys=("warehouse-code", "product-code"),
        bootstrap_anchor=bootstrap_anchor,
    )
    stock_where_rendered = stock_where
    if house_params and stock_params:
        for index in range(len(stock_params), 0, -1):
            stock_where_rendered = stock_where_rendered.replace(
                f"${index}",
                f"${index + len(house_params)}",
            )
    query = f"""
        SELECT *
        FROM (
            SELECT
                ({house_change_ts})::text AS change_ts_text,
                EXTRACT(EPOCH FROM {house_change_ts}) AS change_ts_epoch,
                {_column_ref('house', 'shouseno')} AS warehouse_code,
                {_column_ref('house', 'sstkno')} AS product_code
            FROM {quoted_schema}.{_quoted_identifier('tbsstkhouse')} AS house
            {house_where}

            UNION

            SELECT
                ({stock_change_ts})::text AS change_ts_text,
                EXTRACT(EPOCH FROM {stock_change_ts}) AS change_ts_epoch,
                {_column_ref('house', 'shouseno')} AS warehouse_code,
                {_column_ref('stock', 'sstkno')} AS product_code
            FROM {quoted_schema}.{_quoted_identifier('tbsstock')} AS stock
            INNER JOIN {quoted_schema}.{_quoted_identifier('tbsstkhouse')} AS house
                ON {_column_ref('house', 'sstkno')} = {_column_ref('stock', 'sstkno')}
            {stock_where_rendered}
        ) AS inventory_delta
        ORDER BY change_ts_epoch, warehouse_code, product_code
    """
    rows = await _fetch_records(
        query=query,
        parameters=[*house_params, *stock_params],
        connection_settings=connection_settings,
    )
    return [
        {
            "source-change-ts": _format_change_ts(row["change_ts_text"]),
            "warehouse-code": warehouse_code,
            "product-code": product_code,
            "warehouse_code": warehouse_code,
            "product_code": product_code,
        }
        for row in rows
        if (warehouse_code := str(row["warehouse_code"] or "").strip())
        and (product_code := str(row["product_code"] or "").strip())
    ]


async def _project_documents(
    *,
    source_schema: str,
    header_table: str,
    detail_table: str,
    watermark: Mapping[str, Any] | None,
    bootstrap_anchor: datetime | None,
    connection_settings: LegacySourceConnectionSettings | None,
) -> list[Mapping[str, Any]]:
    quoted_schema = _quoted_identifier(source_schema)
    header_change_ts = _change_ts_expression(
        "header",
        timestamp_column="stimestamp",
        modify_column="dtmodify",
        date_column="dtslipdate",
    )
    header_where, detail_where, parameters = _document_cursor_clause(
        header_alias="header",
        detail_alias="detail",
        watermark=watermark,
        bootstrap_anchor=bootstrap_anchor,
        header_change_ts_expr=header_change_ts,
    )
    query = f"""
        SELECT document_date, document_number, line_number
        FROM (
            SELECT
                {_column_ref('header', 'dtslipdate')} AS document_date,
                {_column_ref('header', 'sslipno')} AS document_number,
                0 AS line_number
            FROM {quoted_schema}.{_quoted_identifier(header_table)} AS header
            {header_where}

            UNION

            SELECT
                {_column_ref('detail', 'dtslipdate')} AS document_date,
                {_column_ref('detail', 'sslipno')} AS document_number,
                {_column_ref('detail', 'iidno')} AS line_number
            FROM {quoted_schema}.{_quoted_identifier(detail_table)} AS detail
            INNER JOIN {quoted_schema}.{_quoted_identifier(header_table)} AS header
                ON {_column_ref('header', 'skind')} = {_column_ref('detail', 'skind')}
                AND {_column_ref('header', 'sslipno')} = {_column_ref('detail', 'sslipno')}
            {detail_where}
        ) AS document_delta
        ORDER BY document_date, document_number, line_number
    """
    rows = await _fetch_records(query=query, parameters=parameters, connection_settings=connection_settings)
    return [
        {
            "document-date": str(row["document_date"]),
            "document-number": document_number,
            "line-number": int(row["line_number"]),
            "document_number": document_number,
        }
        for row in rows
        if (document_number := str(row["document_number"] or "").strip())
    ]


def build_live_source_projection(
    *,
    source_schema: str,
    bootstrap_rebaseline_state: Mapping[str, Any] | None = None,
    connection_settings: LegacySourceConnectionSettings | None = None,
) -> SourceProjection:
    anchor = _bootstrap_anchor(bootstrap_rebaseline_state)

    def project(
        contract: IncrementalDomainContract,
        resume_from_watermark: Mapping[str, Any] | None,
    ) -> list[Mapping[str, Any]]:
        if contract.name == DOMAIN_PARTIES:
            return asyncio.run(
                _project_parties(
                    source_schema=source_schema,
                    watermark=resume_from_watermark,
                    bootstrap_anchor=anchor,
                    connection_settings=connection_settings,
                )
            )
        if contract.name == DOMAIN_PRODUCTS:
            return asyncio.run(
                _project_products(
                    source_schema=source_schema,
                    watermark=resume_from_watermark,
                    bootstrap_anchor=anchor,
                    connection_settings=connection_settings,
                )
            )
        if contract.name == DOMAIN_WAREHOUSES:
            return asyncio.run(
                _project_warehouses(
                    source_schema=source_schema,
                    watermark=resume_from_watermark,
                    bootstrap_anchor=anchor,
                    connection_settings=connection_settings,
                )
            )
        if contract.name == DOMAIN_INVENTORY:
            return asyncio.run(
                _project_inventory(
                    source_schema=source_schema,
                    watermark=resume_from_watermark,
                    bootstrap_anchor=anchor,
                    connection_settings=connection_settings,
                )
            )
        if contract.name == DOMAIN_SALES:
            return asyncio.run(
                _project_documents(
                    source_schema=source_schema,
                    header_table="tbsslipx",
                    detail_table="tbsslipdtx",
                    watermark=resume_from_watermark,
                    bootstrap_anchor=anchor,
                    connection_settings=connection_settings,
                )
            )
        if contract.name == DOMAIN_PURCHASE_INVOICES:
            return asyncio.run(
                _project_documents(
                    source_schema=source_schema,
                    header_table="tbsslipj",
                    detail_table="tbsslipdtj",
                    watermark=resume_from_watermark,
                    bootstrap_anchor=anchor,
                    connection_settings=connection_settings,
                )
            )
        raise ValueError(f"Unsupported incremental domain '{contract.name}'")

    return project