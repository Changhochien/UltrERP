"""Receiving-audit and payment-adjacent helpers for canonical legacy imports."""

from __future__ import annotations

import logging
import uuid
from datetime import date, datetime

from common.models.stock_adjustment import ReasonCode
from domains.legacy_import.canonical_common import (
    _as_decimal,
    _as_int,
    _as_text,
    _as_timestamp,
    _table_exists,
    _try_as_legacy_date,
)
from domains.legacy_import.canonical_persistence import (
    PendingLineageResolution,
    _flush_lineage_resolutions,
    _try_upsert_holding_and_lineage,
)
from domains.legacy_import.canonical_readers import _iter_query_rows
from domains.legacy_import.mapping import UNKNOWN_PRODUCT_CODE
from domains.legacy_import.normalization import deterministic_legacy_uuid
from domains.legacy_import.shared import resolve_row_identity as _resolve_row_identity
from domains.legacy_import.staging import _quoted_identifier

_LOGGER = logging.getLogger(__name__)

LEGACY_RECEIVING_SOURCE = "tbsslipdtj"

# Mutable run-scoped accumulator reset by canonical.py at the start of each run.
_receiving_date_fallback_counts: dict[str, int] = {}


def _tenant_scoped_uuid(tenant_id: uuid.UUID, kind: str, *parts: str) -> uuid.UUID:
    return deterministic_legacy_uuid(kind, str(tenant_id), *parts)


def _coerce_quantity_for_integer_schema(
    value: object | None,
    *,
    field_name: str,
) -> tuple[int, str | None]:
    quantity = _as_decimal(value, "0")
    if quantity is None:
        return 0, None
    if quantity == quantity.to_integral_value():
        return int(quantity), None

    coerced = int(quantity)
    return coerced, f"{field_name} coerced from {quantity.normalize()} to {coerced}"


def _derive_legacy_receiving_batch_fallback_day(
    headers: list[dict[str, object]],
    lines: list[dict[str, object]],
) -> date | None:
    candidates = []
    for header in headers:
        day = _try_as_legacy_date(header.get("invoice_date"))
        if day is not None:
            candidates.append(day)
    for line in lines:
        day = _try_as_legacy_date(line.get("receipt_date"))
        if day is not None:
            candidates.append(day)
    return max(candidates) if candidates else None


def _resolve_legacy_receiving_created_at(
    line: dict[str, object],
    header: dict[str, object] | None,
    batch_fallback_day: date | None,
) -> datetime:
    source_identifier = (
        f"{_as_text(line.get('doc_number'))}:{_as_int(line.get('line_number'), 1)}"
    )

    line_day = _try_as_legacy_date(line.get("receipt_date"))
    if line_day is not None:
        return _as_timestamp(line_day)

    if header is not None:
        header_day = _try_as_legacy_date(header.get("invoice_date"))
        if header_day is not None:
            _LOGGER.warning(
                "Legacy receiving line %s has sentinel/missing receipt_date; "
                "falling back to header invoice_date",
                source_identifier,
            )
            _receiving_date_fallback_counts["receiving_date_fallback_receipt_to_invoice"] += 1
            return _as_timestamp(header_day)

    if batch_fallback_day is not None:
        _LOGGER.warning(
            "Legacy receiving line %s has no usable row/header date; "
            "falling back to batch-scoped legacy date %s",
            source_identifier,
            batch_fallback_day.isoformat(),
        )
        _receiving_date_fallback_counts["receiving_date_fallback_to_batch"] += 1
        return _as_timestamp(batch_fallback_day)

    _LOGGER.warning(
        "Legacy receiving line %s has sentinel/missing receipt_date and no "
        "header fallback; using import-day timestamp",
        source_identifier,
    )
    _receiving_date_fallback_counts["receiving_date_fallback_to_import_day"] += 1
    return _as_timestamp(None)


async def _import_legacy_receiving_audit(
    connection,
    schema_name: str,
    run_id: uuid.UUID,
    tenant_id: uuid.UUID,
    batch_id: str,
    headers: list[dict[str, object]],
    lines: list[dict[str, object]],
    product_by_code: dict[str, uuid.UUID],
    warehouse_by_code: dict[str, uuid.UUID],
    product_mappings: dict[str, str],
) -> tuple[int, int, int, int]:
    count = 0
    lineage_count = 0
    holding_count = 0
    pending_lineage: list[PendingLineageResolution] = []
    headers_by_doc = {
        _as_text(header.get("doc_number")): header
        for header in headers
        if _as_text(header.get("doc_number"))
    }
    batch_fallback_day = _derive_legacy_receiving_batch_fallback_day(headers, lines)

    for line in lines:
        doc_number = _as_text(line.get("doc_number"))
        line_number = _as_int(line.get("line_number"), 1)
        source_row_number = _as_int(line.get("source_row_number"))

        row_identity = _resolve_row_identity(source_row_number, line_number)
        if not doc_number:
            ok = await _try_upsert_holding_and_lineage(
                connection,
                schema_name,
                run_id,
                tenant_id,
                batch_id,
                "receiving_audit",
                LEGACY_RECEIVING_SOURCE,
                f":{line_number}",
                source_row_number,
                row_identity,
                line,
                f"Blank doc_number held (row_id={row_identity}); UUID collision prevented.",
            )
            if ok:
                holding_count += 1
            continue

        source_identifier = f"{doc_number}:{line_number}"

        legacy_product_code = _as_text(line.get("product_code"))
        mapped_product_code = product_mappings.get(legacy_product_code) or legacy_product_code
        if mapped_product_code not in product_by_code:
            mapped_product_code = UNKNOWN_PRODUCT_CODE
        product_id = product_by_code.get(mapped_product_code)
        if product_id is None:
            raise ValueError(
                "Receiving audit line "
                f"{source_identifier} cannot resolve product {legacy_product_code}"
            )

        warehouse_code = _as_text(line.get("warehouse_code"))
        warehouse_id = warehouse_by_code.get(warehouse_code)
        if warehouse_id is None:
            raise ValueError(
                "Receiving audit line "
                f"{source_identifier} cannot resolve warehouse {warehouse_code}"
            )

        stock_adjustment_id = _tenant_scoped_uuid(
            tenant_id,
            "legacy-receiving-adjustment",
            source_identifier,
        )
        created_at = _resolve_legacy_receiving_created_at(
            line,
            headers_by_doc.get(doc_number),
            batch_fallback_day,
        )
        quantity_change, quantity_note = _coerce_quantity_for_integer_schema(
            line.get("qty"),
            field_name=f"Receiving audit line {source_identifier} quantity",
        )
        notes = f"Legacy import: invoice {doc_number}"
        if quantity_note:
            notes = f"{notes}; {quantity_note}"

        await connection.execute(
            """
			INSERT INTO stock_adjustment (
				id,
				tenant_id,
				product_id,
				warehouse_id,
				quantity_change,
				reason_code,
				actor_id,
				notes,
				transfer_id,
				created_at
			)
			VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            ON CONFLICT (id) DO NOTHING
			""",
            stock_adjustment_id,
            tenant_id,
            product_id,
            warehouse_id,
            quantity_change,
            ReasonCode.SUPPLIER_DELIVERY.value,
            "legacy_import",
            notes,
            None,
            created_at,
        )
        pending_lineage.append(
            PendingLineageResolution(
                canonical_table="stock_adjustment",
                canonical_id=stock_adjustment_id,
                source_table=LEGACY_RECEIVING_SOURCE,
                source_identifier=source_identifier,
                source_row_number=_as_int(line.get("source_row_number")),
            )
        )
        count += 1
        lineage_count += 1

    await _flush_lineage_resolutions(
        connection,
        schema_name,
        run_id,
        tenant_id,
        batch_id,
        pending_lineage,
    )
    fallback_count = sum(_receiving_date_fallback_counts.values())
    return count, lineage_count, holding_count, fallback_count


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
            source_row_number = _as_int(raw_row.get("_source_row_number"))
            ok = await _try_upsert_holding_and_lineage(
                connection,
                schema_name,
                run_id,
                tenant_id,
                batch_id,
                "payment_history",
                table_name,
                source_identifier,
                source_row_number,
                source_row_number,
                raw_row,
                (
                    "Payment-adjacent legacy rows are preserved in holding "
                    "until a verified payment mapping is defined."
                ),
            )
            if ok:
                total += 1
    return total