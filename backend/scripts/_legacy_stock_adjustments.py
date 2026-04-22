from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from itertools import batched

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from common.models.stock_adjustment import ReasonCode, StockAdjustment
from domains.legacy_import.mapping import UNKNOWN_PRODUCT_CODE
from domains.legacy_import.normalization import (
    deterministic_legacy_uuid,
    normalize_legacy_date,
)

ACTOR_ID = "backfill-script"
CANONICAL_LEGACY_IMPORT_ACTOR_ID = "legacy_import"
LEGACY_SALES_REDUNDANT_WAREHOUSE_ID = uuid.UUID("e0e9028a-7d6c-5abd-976a-735586cedc34")
LEGACY_SALES_REDUNDANT_NOTE = "backfill from raw_legacy.tbsslipx+tbsslipdtx"


@dataclass(frozen=True, slots=True)
class StockAdjustmentPayload:
    id: uuid.UUID
    tenant_id: uuid.UUID
    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    quantity_change: int
    reason_code: str
    actor_id: str
    notes: str
    created_at: datetime
    transfer_id: uuid.UUID | None = None


@dataclass(frozen=True, slots=True)
class ReconciliationRow:
    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    expected_adjustment_sum: int
    actual_stock: int
    gap: int
    reason_breakdown: dict[str, int]


def tenant_scoped_uuid(tenant_id: uuid.UUID, kind: str, *parts: str) -> uuid.UUID:
    return deterministic_legacy_uuid(kind, str(tenant_id), *parts)


def _as_text(value: object | None) -> str:
    return str(value or "").strip()


def _as_decimal(value: object | None, *, source_identifier: str, field_name: str) -> Decimal:
    if isinstance(value, Decimal):
        return value

    text_value = _as_text(value)
    if not text_value:
        raise ValueError(f"{source_identifier} is missing {field_name}")

    try:
        return Decimal(text_value)
    except InvalidOperation as exc:
        raise ValueError(
            f"{source_identifier} has invalid {field_name}: {text_value!r}"
        ) from exc


def _as_legacy_day(value: object | None, *, source_identifier: str, field_name: str) -> date:
    parsed = normalize_legacy_date(value)
    if parsed is None:
        raise ValueError(f"{source_identifier} has invalid {field_name}: {_as_text(value)!r}")
    return parsed


def _format_decimal(value: Decimal) -> str:
    text = format(value.normalize(), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _day_start_utc(day: date) -> datetime:
    return datetime(day.year, day.month, day.day, tzinfo=UTC)


def _coerce_quantity_for_integer_schema(
    value: object | None,
    *,
    source_identifier: str,
    field_name: str,
) -> tuple[int, str | None]:
    decimal_value = _as_decimal(value, source_identifier=source_identifier, field_name=field_name)
    coerced_value = int(decimal_value)
    if decimal_value == decimal_value.to_integral_value():
        return coerced_value, None
    return coerced_value, f"coerced from {_format_decimal(decimal_value)} to {coerced_value}"


def _as_timestamp(day: date) -> datetime:
    return datetime(day.year, day.month, day.day, tzinfo=UTC)


def _resolve_product_id(
    product_code: object | None,
    *,
    source_identifier: str,
    product_by_code: dict[str, uuid.UUID],
    product_mappings: dict[str, str],
) -> tuple[uuid.UUID, str | None]:
    legacy_code = _as_text(product_code)
    mapped_code = product_mappings.get(legacy_code) or legacy_code
    product_id = product_by_code.get(mapped_code)
    if product_id is not None:
        return product_id, None

    unknown_product_id = product_by_code.get(UNKNOWN_PRODUCT_CODE)
    if unknown_product_id is not None:
        return unknown_product_id, f"UNKNOWN product {legacy_code}"

    raise ValueError(f"{source_identifier} cannot resolve product code {legacy_code!r}")


def _resolve_warehouse_id(
    warehouse_code: object | None,
    *,
    source_identifier: str,
    warehouse_by_code: dict[str, uuid.UUID],
) -> uuid.UUID:
    normalized_code = _as_text(warehouse_code)
    warehouse_id = warehouse_by_code.get(normalized_code)
    if warehouse_id is None:
        raise ValueError(
            f"{source_identifier} cannot resolve warehouse code {normalized_code!r}"
        )
    return warehouse_id


def build_sales_adjustments(
    *,
    rows: list[dict[str, object]],
    tenant_id: uuid.UUID,
    product_by_code: dict[str, uuid.UUID],
    warehouse_by_code: dict[str, uuid.UUID],
    product_mappings: dict[str, str],
) -> list[StockAdjustmentPayload]:
    aggregates: dict[tuple[uuid.UUID, uuid.UUID, date], tuple[Decimal, int]] = {}

    for row in rows:
        source_identifier = (
            "sales:"
            f"{_as_text(row.get('doc_number')) or '?'}:"
            f"{_as_text(row.get('line_number')) or '?'}"
        )
        product_id, product_note = _resolve_product_id(
            row.get("product_code"),
            source_identifier=source_identifier,
            product_by_code=product_by_code,
            product_mappings=product_mappings,
        )
        warehouse_id = _resolve_warehouse_id(
            row.get("warehouse_code"),
            source_identifier=source_identifier,
            warehouse_by_code=warehouse_by_code,
        )
        invoice_day = _as_legacy_day(
            row.get("invoice_date"),
            source_identifier=source_identifier,
            field_name="invoice_date",
        )
        signed_qty = _as_decimal(
            row.get("signed_qty"),
            source_identifier=source_identifier,
            field_name="signed_qty",
        )
        key = (product_id, warehouse_id, invoice_day)
        current_total, current_count = aggregates.get(key, (Decimal("0"), 0))
        aggregates[key] = (current_total + signed_qty, current_count + 1)

    payloads: list[StockAdjustmentPayload] = []
    for (product_id, warehouse_id, invoice_day), (signed_total, line_count) in sorted(
        aggregates.items(),
        key=lambda item: (str(item[0][0]), str(item[0][1]), item[0][2]),
    ):
        source_identifier = (
            f"sales:{product_id}:{warehouse_id}:{invoice_day.isoformat()}"
        )
        quantity_change, coercion_note = _coerce_quantity_for_integer_schema(
            signed_total,
            source_identifier=source_identifier,
            field_name="signed_qty_total",
        )
        note_parts = [
            f"Legacy sales backfill from tbsslipx/tbsslipdtx ({line_count} lines)"
        ]
        if coercion_note:
            note_parts.append(coercion_note)
        payloads.append(
            StockAdjustmentPayload(
                id=tenant_scoped_uuid(
                    tenant_id,
                    "legacy-sales-adjustment",
                    str(product_id),
                    str(warehouse_id),
                    invoice_day.isoformat(),
                ),
                tenant_id=tenant_id,
                product_id=product_id,
                warehouse_id=warehouse_id,
                quantity_change=-quantity_change,
                reason_code="SALES_RESERVATION",
                actor_id=ACTOR_ID,
                notes="; ".join(note_parts),
                created_at=_as_timestamp(invoice_day),
            )
        )

    return payloads


def build_stock_adjustment_upsert(
    payload: StockAdjustmentPayload | Sequence[StockAdjustmentPayload],
):
    payloads = [payload]
    if isinstance(payload, Sequence) and not isinstance(payload, StockAdjustmentPayload):
        payloads = list(payload)
    insert_stmt = insert(StockAdjustment).values(
        [
            {
                "id": item.id,
                "tenant_id": item.tenant_id,
                "product_id": item.product_id,
                "warehouse_id": item.warehouse_id,
                "quantity_change": item.quantity_change,
                "reason_code": item.reason_code,
                "actor_id": item.actor_id,
                "notes": item.notes,
                "transfer_id": item.transfer_id,
                "created_at": item.created_at,
            }
            for item in payloads
        ]
    )
    return insert_stmt.on_conflict_do_update(
        index_elements=[StockAdjustment.id],
        set_={
            "tenant_id": insert_stmt.excluded.tenant_id,
            "product_id": insert_stmt.excluded.product_id,
            "warehouse_id": insert_stmt.excluded.warehouse_id,
            "quantity_change": insert_stmt.excluded.quantity_change,
            "reason_code": insert_stmt.excluded.reason_code,
            "actor_id": insert_stmt.excluded.actor_id,
            "notes": insert_stmt.excluded.notes,
            "transfer_id": insert_stmt.excluded.transfer_id,
            "created_at": insert_stmt.excluded.created_at,
        },
    )


def collapse_stock_adjustments(
    adjustments: Sequence[StockAdjustmentPayload],
) -> list[StockAdjustmentPayload]:
    deduped_by_id: dict[uuid.UUID, StockAdjustmentPayload] = {}
    for adjustment in adjustments:
        deduped_by_id[adjustment.id] = adjustment
    return list(deduped_by_id.values())


async def upsert_stock_adjustments(
    session: AsyncSession,
    adjustments: Sequence[StockAdjustmentPayload],
    *,
    batch_size: int = 1000,
) -> int:
    collapsed_adjustments = collapse_stock_adjustments(adjustments)
    for batch in batched(collapsed_adjustments, batch_size):
        await session.execute(build_stock_adjustment_upsert(list(batch)))
    return len(collapsed_adjustments)


def _resolve_purchase_created_at(
    row: dict[str, object],
    *,
    fallback_day: date | None = None,
) -> datetime:
    receipt_date = normalize_legacy_date(row.get("receipt_date"))
    if receipt_date is not None:
        return _as_timestamp(receipt_date)

    invoice_date = normalize_legacy_date(row.get("invoice_date"))
    if invoice_date is not None:
        return _as_timestamp(invoice_date)

    if fallback_day is None:
        fallback_day = date.today()
    return _as_timestamp(fallback_day)


def build_purchase_receipt_adjustments(
    *,
    rows: list[dict[str, object]],
    tenant_id: uuid.UUID,
    product_by_code: dict[str, uuid.UUID],
    warehouse_by_code: dict[str, uuid.UUID],
    product_mappings: dict[str, str],
    fallback_day: date | None = None,
) -> list[StockAdjustmentPayload]:
    payloads: list[StockAdjustmentPayload] = []

    for row in rows:
        doc_number = _as_text(row.get("doc_number"))
        line_number = _as_text(row.get("line_number")) or "1"
        source_identifier = f"purchase:{doc_number}:{line_number}"
        product_id, product_note = _resolve_product_id(
            row.get("product_code"),
            source_identifier=source_identifier,
            product_by_code=product_by_code,
            product_mappings=product_mappings,
        )
        warehouse_id = _resolve_warehouse_id(
            row.get("warehouse_code"),
            source_identifier=source_identifier,
            warehouse_by_code=warehouse_by_code,
        )

        quantity_change, coercion_note = _coerce_quantity_for_integer_schema(
            row.get("qty"),
            source_identifier=source_identifier,
            field_name="qty",
        )
        note_parts = [f"Legacy import: invoice {doc_number}"]
        if product_note:
            note_parts.append(product_note)
        if coercion_note:
            note_parts.append(coercion_note)

        payloads.append(
            StockAdjustmentPayload(
                id=tenant_scoped_uuid(
                    tenant_id,
                    "legacy-receiving-adjustment",
                    f"{doc_number}:{line_number}",
                ),
                tenant_id=tenant_id,
                product_id=product_id,
                warehouse_id=warehouse_id,
                quantity_change=quantity_change,
                reason_code="SUPPLIER_DELIVERY",
                actor_id=CANONICAL_LEGACY_IMPORT_ACTOR_ID,
                notes="; ".join(note_parts),
                created_at=_resolve_purchase_created_at(
                    row,
                    fallback_day=fallback_day,
                ),
            )
        )

    return payloads


async def fetch_product_mappings(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    schema_name: str = "raw_legacy",
) -> dict[str, str]:
    result = await session.execute(
        text(
            f"""
            SELECT legacy_code, target_code
            FROM {schema_name}.product_code_mapping
            WHERE tenant_id = :tenant_id
            ORDER BY legacy_code
            """
        ),
        {"tenant_id": str(tenant_id)},
    )
    return {
        _as_text(row.legacy_code): _as_text(row.target_code)
        for row in result.fetchall()
        if _as_text(row.legacy_code)
    }


async def fetch_product_by_code(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, uuid.UUID]:
    result = await session.execute(
        text(
            """
            SELECT code, id
            FROM public.product
            WHERE tenant_id = :tenant_id
            ORDER BY code
            """
        ),
        {"tenant_id": str(tenant_id)},
    )
    return {
        _as_text(row.code): row.id
        for row in result.fetchall()
        if _as_text(row.code)
    }


async def fetch_warehouse_by_code(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, uuid.UUID]:
    result = await session.execute(
        text(
            """
            SELECT code, id
            FROM public.warehouse
            WHERE tenant_id = :tenant_id
            ORDER BY code
            """
        ),
        {"tenant_id": str(tenant_id)},
    )
    return {
        _as_text(row.code): row.id
        for row in result.fetchall()
        if _as_text(row.code)
    }


async def fetch_sales_rows(
    session: AsyncSession,
    *,
    cutoff: date,
    today: date,
) -> list[dict[str, object]]:
    result = await session.execute(
        text(
            """
            SELECT
                dtx.col_2 AS doc_number,
                dtx.col_3 AS line_number,
                dtx.col_7 AS product_code,
                dtx.col_15 AS warehouse_code,
                CAST(dtx.col_23 AS numeric) AS signed_qty,
                x.col_3 AS invoice_date
            FROM raw_legacy.tbsslipx x
            JOIN raw_legacy.tbsslipdtx dtx ON dtx.col_2 = x.col_2
            WHERE x.col_3 IS NOT NULL
              AND x.col_3 <> ''
              AND x.col_3 >= :cutoff
              AND x.col_3 <= :today
              AND dtx.col_23 IS NOT NULL
              AND dtx.col_23 <> ''
              AND CAST(dtx.col_23 AS numeric) != 0
            ORDER BY x.col_3, dtx.col_2, dtx.col_3
            """
        ),
        {"cutoff": str(cutoff), "today": str(today)},
    )
    return [dict(row._mapping) for row in result.fetchall()]


async def fetch_purchase_receipt_rows(
    session: AsyncSession,
    *,
    cutoff: date,
    today: date,
) -> list[dict[str, object]]:
    result = await session.execute(
        text(
            """
            SELECT
                dtj.col_2 AS doc_number,
                dtj.col_3 AS line_number,
                dtj.col_4 AS receipt_date,
                j.col_3 AS invoice_date,
                dtj.col_6 AS product_code,
                dtj.col_16 AS warehouse_code,
                CAST(dtj.col_22 AS numeric) AS qty
            FROM raw_legacy.tbsslipdtj dtj
            LEFT JOIN raw_legacy.tbsslipj j ON j.col_2 = dtj.col_2
            WHERE dtj.col_22 IS NOT NULL
              AND dtj.col_22 <> ''
              AND CAST(dtj.col_22 AS numeric) != 0
              AND COALESCE(NULLIF(dtj.col_4, ''), NULLIF(j.col_3, '')) IS NOT NULL
              AND COALESCE(NULLIF(dtj.col_4, ''), NULLIF(j.col_3, '')) >= :cutoff
              AND COALESCE(NULLIF(dtj.col_4, ''), NULLIF(j.col_3, '')) <= :today
            ORDER BY COALESCE(NULLIF(dtj.col_4, ''), NULLIF(j.col_3, '')), dtj.col_2, dtj.col_3
            """
        ),
        {"cutoff": str(cutoff), "today": str(today)},
    )
    return [dict(row._mapping) for row in result.fetchall()]


def build_reconciliation_rows(
    *,
    adjustment_rows: list[dict[str, object]],
    inventory_rows: list[dict[str, object]],
    ignored_reason_codes: set[str] | None = None,
) -> list[ReconciliationRow]:
    ignored_codes = {code.upper() for code in (ignored_reason_codes or set())}
    reason_breakdowns: dict[tuple[uuid.UUID, uuid.UUID], dict[str, int]] = {}

    for row in adjustment_rows:
        product_id = row["product_id"]
        warehouse_id = row["warehouse_id"]
        key = (product_id, warehouse_id)
        if key not in reason_breakdowns:
            reason_breakdowns[key] = {}
        reason_code = _as_text(row.get("reason_code")) or "UNKNOWN"
        if reason_code.upper() in ignored_codes:
            continue
        reason_breakdowns[key][reason_code] = reason_breakdowns[key].get(reason_code, 0) + int(
            row.get("quantity_total") or 0
        )

    inventory_totals = {
        (row["product_id"], row["warehouse_id"]): int(row.get("current_stock") or 0)
        for row in inventory_rows
    }
    keys = sorted(
        set(reason_breakdowns) | set(inventory_totals),
        key=lambda item: (str(item[0]), str(item[1])),
    )

    rows: list[ReconciliationRow] = []
    for product_id, warehouse_id in keys:
        breakdown = reason_breakdowns.get((product_id, warehouse_id), {})
        expected_adjustment_sum = sum(breakdown.values())
        actual_stock = inventory_totals.get((product_id, warehouse_id), 0)
        rows.append(
            ReconciliationRow(
                product_id=product_id,
                warehouse_id=warehouse_id,
                expected_adjustment_sum=expected_adjustment_sum,
                actual_stock=actual_stock,
                gap=expected_adjustment_sum - actual_stock,
                reason_breakdown=dict(sorted(breakdown.items())),
            )
        )

    return rows


def build_correction_adjustments(
    rows: Sequence[ReconciliationRow],
    *,
    tenant_id: uuid.UUID,
    as_of_day: date,
    min_abs_gap: int = 1,
) -> list[StockAdjustmentPayload]:
    corrections: list[StockAdjustmentPayload] = []
    for row in rows:
        if row.gap == 0 or abs(row.gap) < min_abs_gap:
            continue

        reason_summary = (
            ", ".join(
                f"{reason}={total}" for reason, total in sorted(row.reason_breakdown.items())
            )
            or "-"
        )
        corrections.append(
            StockAdjustmentPayload(
                id=tenant_scoped_uuid(
                    tenant_id,
                    "inventory-reconciliation-correction",
                    str(row.product_id),
                    str(row.warehouse_id),
                    as_of_day.isoformat(),
                ),
                tenant_id=tenant_id,
                product_id=row.product_id,
                warehouse_id=row.warehouse_id,
                quantity_change=-row.gap,
                reason_code=ReasonCode.CORRECTION.value,
                actor_id="reconciliation-plan",
                notes=(
                    "Inventory reconciliation correction proposal "
                    f"as of {as_of_day.isoformat()} "
                    f"(gap={row.gap}; expected_adjustment_sum={row.expected_adjustment_sum}; "
                    f"actual_stock={row.actual_stock}; reasons={reason_summary})"
                ),
                created_at=_day_start_utc(as_of_day),
            )
        )

    return corrections


def format_reconciliation_table(rows: list[ReconciliationRow]) -> str:
    headers = [
        "product_id",
        "warehouse_id",
        "expected_adjustment_sum",
        "actual_stock",
        "gap",
        "reason_breakdown",
    ]
    reason_cells = [
        ", ".join(f"{reason}={total}" for reason, total in row.reason_breakdown.items())
        or "-"
        for row in rows
    ]
    values = [
        [
            str(row.product_id),
            str(row.warehouse_id),
            str(row.expected_adjustment_sum),
            str(row.actual_stock),
            str(row.gap),
            reason_cells[index],
        ]
        for index, row in enumerate(rows)
    ]

    widths = [len(header) for header in headers]
    for value_row in values:
        for index, cell in enumerate(value_row):
            widths[index] = max(widths[index], len(cell))

    header_line = " | ".join(header.ljust(widths[index]) for index, header in enumerate(headers))
    separator_line = "-+-".join("-" * width for width in widths)
    data_lines = [
        " | ".join(cell.ljust(widths[index]) for index, cell in enumerate(value_row))
        for value_row in values
    ]
    return "\n".join([header_line, separator_line, *data_lines])


async def fetch_reconciliation_adjustment_rows(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> list[dict[str, object]]:
    result = await session.execute(
        text(
            """
            SELECT
                product_id,
                warehouse_id,
                reason_code,
                SUM(quantity_change) AS quantity_total
            FROM public.stock_adjustment
            WHERE tenant_id = :tenant_id
            GROUP BY product_id, warehouse_id, reason_code
            ORDER BY product_id, warehouse_id, reason_code
            """
        ),
        {"tenant_id": str(tenant_id)},
    )
    return [dict(row._mapping) for row in result.fetchall()]


async def fetch_reconciliation_inventory_rows(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> list[dict[str, object]]:
    result = await session.execute(
        text(
            """
            SELECT
                product_id,
                warehouse_id,
                SUM(quantity) AS current_stock
            FROM public.inventory_stock
            WHERE tenant_id = :tenant_id
            GROUP BY product_id, warehouse_id
            ORDER BY product_id, warehouse_id
            """
        ),
        {"tenant_id": str(tenant_id)},
    )
    return [dict(row._mapping) for row in result.fetchall()]


async def count_legacy_sales_redundancies(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> int:
    result = await session.execute(
        text(
            """
            SELECT COUNT(*) AS row_count
            FROM public.stock_adjustment
            WHERE tenant_id = :tenant_id
              AND reason_code = 'SALES_RESERVATION'
              AND actor_id = :actor_id
              AND warehouse_id = :warehouse_id
              AND notes = :notes
            """
        ),
        {
            "tenant_id": str(tenant_id),
            "actor_id": ACTOR_ID,
            "warehouse_id": str(LEGACY_SALES_REDUNDANT_WAREHOUSE_ID),
            "notes": LEGACY_SALES_REDUNDANT_NOTE,
        },
    )
    return int(result.scalar_one())


async def delete_legacy_sales_redundancies(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> int:
    result = await session.execute(
        text(
            """
            DELETE FROM public.stock_adjustment
            WHERE tenant_id = :tenant_id
              AND reason_code = 'SALES_RESERVATION'
              AND actor_id = :actor_id
              AND warehouse_id = :warehouse_id
              AND notes = :notes
            """
        ),
        {
            "tenant_id": str(tenant_id),
            "actor_id": ACTOR_ID,
            "warehouse_id": str(LEGACY_SALES_REDUNDANT_WAREHOUSE_ID),
            "notes": LEGACY_SALES_REDUNDANT_NOTE,
        },
    )
    return result.rowcount or 0

