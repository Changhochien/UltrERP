"""Sales history import logic for canonical legacy batches."""

from __future__ import annotations

from collections.abc import Iterable
import json
import uuid
from decimal import Decimal

from domains.legacy_import.canonical_common import (
    _as_decimal,
    _as_int,
    _as_legacy_date,
    _as_text,
    _as_timestamp,
    _compact_snapshot,
    _currency_code,
)
from domains.legacy_import.canonical_persistence import (
    PendingLineageResolution,
    _flush_lineage_resolutions,
)
from domains.legacy_import.mapping import UNKNOWN_PRODUCT_CODE
from domains.legacy_import.normalization import deterministic_legacy_uuid
from domains.legacy_import.shared import execute_many

_SALES_HISTORY_HEADER_BATCH_SIZE = 1_000
_SALES_HISTORY_LINE_BATCH_SIZE = 5_000
_SALES_HISTORY_ARRAY_BATCH_SIZE = 5_000


def _tenant_scoped_uuid(tenant_id: uuid.UUID, kind: str, *parts: str) -> uuid.UUID:
    return deterministic_legacy_uuid(kind, str(tenant_id), *parts)


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


def _map_legacy_status_to_canonical(source_status: str) -> str:
    raw = source_status.strip().upper()
    if raw in {"", "1", "N", "ACTIVE", "ISSUED", "OPEN"}:
        return "issued"
    if raw in {"A", "PAID", "CLEARED", "CLOSED", "DONE", "2"}:
        return "paid"
    if raw in {"3", "VOID", "VOIDED", "CANCELLED", "CANCEL"}:
        return "voided"
    return "issued"


def _map_legacy_order_status(source_status: str) -> str:
    return (
        "cancelled"
        if _map_legacy_status_to_canonical(source_status) == "voided"
        else "fulfilled"
    )


def _resolve_order_line_product_snapshots(
    line: dict[str, object],
    *,
    legacy_product_code: str,
    mapped_product_code: str,
    product_snapshot_by_code: dict[str, dict[str, str | None]],
) -> tuple[str, str | None]:
    product_snapshot = product_snapshot_by_code.get(mapped_product_code, {})
    fallback_name = _as_text(line.get("product_name")) or legacy_product_code or mapped_product_code
    fallback_category = (
        _as_text(line.get("product_category_snapshot"))
        or _as_text(line.get("product_category"))
        or _as_text(line.get("legacy_category"))
        or None
    )
    master_name = product_snapshot.get("name")
    master_category = product_snapshot.get("category")

    if mapped_product_code == UNKNOWN_PRODUCT_CODE:
        return (
            fallback_name or master_name or mapped_product_code,
            fallback_category or master_category,
        )

    return (
        master_name or fallback_name or mapped_product_code,
        master_category or fallback_category,
    )


def _iter_uuid_batches(values: list[uuid.UUID]) -> Iterable[list[uuid.UUID]]:
    unique_values = list(dict.fromkeys(values))
    for index in range(0, len(unique_values), _SALES_HISTORY_ARRAY_BATCH_SIZE):
        yield unique_values[index : index + _SALES_HISTORY_ARRAY_BATCH_SIZE]


async def _link_orders_to_invoices(
    connection,
    tenant_id: uuid.UUID,
    order_invoice_links: list[tuple[uuid.UUID, uuid.UUID]],
) -> None:
    unique_links = list(dict(order_invoice_links).items())
    for index in range(0, len(unique_links), _SALES_HISTORY_ARRAY_BATCH_SIZE):
        link_batch = unique_links[index : index + _SALES_HISTORY_ARRAY_BATCH_SIZE]
        await connection.execute(
            """
            UPDATE orders AS order_target
            SET invoice_id = link.invoice_id, updated_at = NOW()
            FROM UNNEST($1::UUID[], $2::UUID[]) AS link (order_id, invoice_id)
            WHERE order_target.id = link.order_id
                AND order_target.tenant_id = $3
            """,
            [order_id for order_id, invoice_id in link_batch],
            [invoice_id for order_id, invoice_id in link_batch],
            tenant_id,
        )


async def _refresh_order_totals(
    connection,
    tenant_id: uuid.UUID,
    order_ids: list[uuid.UUID],
) -> None:
    for order_id_batch in _iter_uuid_batches(order_ids):
        await connection.execute(
            """
            WITH imported_orders AS (
                SELECT UNNEST($2::UUID[]) AS order_id
            ),
            line_totals AS (
                SELECT
                    order_id,
                    SUM(subtotal_amount) AS subtotal,
                    SUM(tax_amount) AS tax,
                    SUM(total_amount) AS total
                FROM order_lines
                WHERE tenant_id = $1 AND order_id = ANY($2::UUID[])
                GROUP BY order_id
            )
            UPDATE orders AS order_target
            SET subtotal_amount = COALESCE(line_totals.subtotal, 0.00),
                tax_amount = COALESCE(line_totals.tax, 0.00),
                total_amount = COALESCE(line_totals.total, 0.00),
                updated_at = NOW()
            FROM imported_orders
            LEFT JOIN line_totals ON line_totals.order_id = imported_orders.order_id
            WHERE order_target.tenant_id = $1
                AND order_target.id = imported_orders.order_id
            """,
            tenant_id,
            order_id_batch,
        )


async def _refresh_invoice_totals(
    connection,
    tenant_id: uuid.UUID,
    invoice_ids: list[uuid.UUID],
) -> None:
    for invoice_id_batch in _iter_uuid_batches(invoice_ids):
        await connection.execute(
            """
            WITH imported_invoices AS (
                SELECT UNNEST($2::UUID[]) AS invoice_id
            ),
            line_totals AS (
                SELECT
                    invoice_id,
                    SUM(subtotal_amount) AS subtotal,
                    SUM(tax_amount) AS tax,
                    SUM(total_amount) AS total
                FROM invoice_lines
                WHERE tenant_id = $1 AND invoice_id = ANY($2::UUID[])
                GROUP BY invoice_id
            )
            UPDATE invoices AS invoice_target
            SET subtotal_amount = COALESCE(line_totals.subtotal, 0.00),
                tax_amount = COALESCE(line_totals.tax, 0.00),
                total_amount = COALESCE(line_totals.total, 0.00),
                updated_at = NOW()
            FROM imported_invoices
            LEFT JOIN line_totals ON line_totals.invoice_id = imported_invoices.invoice_id
            WHERE invoice_target.tenant_id = $1
                AND invoice_target.id = imported_invoices.invoice_id
            """,
            tenant_id,
            invoice_id_batch,
        )


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
    product_snapshot_by_code: dict[str, dict[str, str | None]],
    product_mappings: dict[str, str],
) -> tuple[int, int, int, int, int]:
    order_upsert_query = """
            INSERT INTO orders (
                id,
                tenant_id,
                customer_id,
                order_number,
                status,
                payment_terms_code,
                payment_terms_days,
                subtotal_amount,
                discount_amount,
                discount_percent,
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
                $5,
                'NET_30',
                30,
                $6,
                0.00,
                0.0000,
                $7,
                $8,
                NULL,
                $9,
                $10::json,
                $11,
                $12,
                $12,
                $12
            )
            ON CONFLICT (id) DO UPDATE SET
                customer_id = EXCLUDED.customer_id,
                order_number = EXCLUDED.order_number,
                status = EXCLUDED.status,
                subtotal_amount = EXCLUDED.subtotal_amount,
                discount_amount = EXCLUDED.discount_amount,
                discount_percent = EXCLUDED.discount_percent,
                tax_amount = EXCLUDED.tax_amount,
                total_amount = EXCLUDED.total_amount,
                notes = EXCLUDED.notes,
                legacy_header_snapshot = EXCLUDED.legacy_header_snapshot,
                created_by = EXCLUDED.created_by,
                updated_at = NOW(),
                confirmed_at = EXCLUDED.confirmed_at
            """
    invoice_upsert_query = """
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
            VALUES (
                $1,
                $2,
                $3,
                $4,
                $5,
                'b2b',
                $6,
                $7,
                $8,
                $9,
                $10,
                $11,
                1,
                $12::json,
                $13,
                $14,
                $14
            )
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
            """
    order_line_upsert_query = """
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
                    product_name_snapshot,
                    product_category_snapshot,
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
                    $19,
                    $20,
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
                    product_name_snapshot=COALESCE(
                        order_lines.product_name_snapshot,
                        EXCLUDED.product_name_snapshot
                    ),
                    product_category_snapshot=COALESCE(
                        order_lines.product_category_snapshot,
                        EXCLUDED.product_category_snapshot
                    ),
                    available_stock_snapshot = EXCLUDED.available_stock_snapshot
                """
    invoice_line_upsert_query = """
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
                """

    lines_by_doc: dict[str, list[dict[str, object]]] = {}
    for row in lines:
        lines_by_doc.setdefault(_as_text(row.get("doc_number")), []).append(row)

    order_count = 0
    order_line_count = 0
    invoice_count = 0
    invoice_line_count = 0
    lineage_count = 0
    pending_lineage: list[PendingLineageResolution] = []
    order_rows: list[tuple[object, ...]] = []
    invoice_rows: list[tuple[object, ...]] = []
    order_line_rows: list[tuple[object, ...]] = []
    invoice_line_rows: list[tuple[object, ...]] = []
    order_invoice_links: list[tuple[uuid.UUID, uuid.UUID]] = []
    order_total_ids: list[uuid.UUID] = []
    invoice_total_ids: list[uuid.UUID] = []

    async def flush_sales_rows() -> None:
        if not order_rows:
            return

        await execute_many(connection, order_upsert_query, order_rows)
        await execute_many(connection, invoice_upsert_query, invoice_rows)
        await _link_orders_to_invoices(connection, tenant_id, order_invoice_links)
        await execute_many(connection, order_line_upsert_query, order_line_rows)
        await execute_many(connection, invoice_line_upsert_query, invoice_line_rows)
        await _refresh_order_totals(connection, tenant_id, order_total_ids)
        await _refresh_invoice_totals(connection, tenant_id, invoice_total_ids)

        order_rows.clear()
        invoice_rows.clear()
        order_line_rows.clear()
        invoice_line_rows.clear()
        order_invoice_links.clear()
        order_total_ids.clear()
        invoice_total_ids.clear()

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
        order_status = _map_legacy_order_status(_as_text(header.get("source_status")))
        legacy_header_snapshot = _build_sales_header_snapshot(header)

        order_rows.append(
            (
                order_id,
                tenant_id,
                customer_id,
                doc_number,
                order_status,
                _as_decimal(header.get("subtotal"), "0.00"),
                _as_decimal(header.get("tax_amount"), "0.00"),
                _as_decimal(header.get("total_amount"), "0.00"),
                _as_text(header.get("remark")) or None,
                json.dumps(legacy_header_snapshot),
                _as_text(header.get("created_by")) or "legacy-import",
                created_at,
            )
        )
        pending_lineage.append(
            PendingLineageResolution(
                canonical_table="orders",
                canonical_id=order_id,
                source_table="tbsslipx",
                source_identifier=doc_number,
                source_row_number=_as_int(header.get("source_row_number")),
            )
        )
        order_count += 1
        lineage_count += 1

        invoice_rows.append(
            (
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
                _map_legacy_status_to_canonical(_as_text(header.get("source_status"))),
                json.dumps(legacy_header_snapshot),
                order_id,
                created_at,
            )
        )
        order_invoice_links.append((order_id, invoice_id))
        order_total_ids.append(order_id)
        invoice_total_ids.append(invoice_id)
        pending_lineage.append(
            PendingLineageResolution(
                canonical_table="invoices",
                canonical_id=invoice_id,
                source_table="tbsslipx",
                source_identifier=doc_number,
                source_row_number=_as_int(header.get("source_row_number")),
            )
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

            (
                product_name_snapshot,
                product_category_snapshot,
            ) = _resolve_order_line_product_snapshots(
                line,
                legacy_product_code=legacy_product_code,
                mapped_product_code=mapped_product_code,
                product_snapshot_by_code=product_snapshot_by_code,
            )

            line_number = _as_int(line.get("line_number"), 1)
            list_unit_price = _as_decimal(line.get("list_unit_price"), "0.00")
            unit_price = _as_decimal(line.get("unit_price"), "0.00")
            extended_amount = _as_decimal(line.get("extended_amount"), "0.00")
            quantity = _as_decimal(line.get("qty"), "0")
            original_list_price = _as_decimal(line.get("original_list_price"), None)
            original_discount_ratio = _as_decimal(line.get("original_discount_ratio"), None)
            if (
                original_list_price is not None
                and original_discount_ratio is not None
                and original_list_price > list_unit_price
                and Decimal("0") < original_discount_ratio < Decimal("1")
            ):
                actual_list_price = original_list_price
            else:
                actual_list_price = list_unit_price
            discount_amount = max(
                Decimal("0.00"),
                (actual_list_price - unit_price).quantize(Decimal("0.01")),
            )
            subtotal = extended_amount
            line_tax_amount = _as_decimal(line.get("line_tax_amount"), "0.00")
            line_total = subtotal + line_tax_amount
            max_tax_rate = Decimal("99.9999")
            min_tax_rate = Decimal("0.0000")
            raw_rate = (
                (line_tax_amount / extended_amount * Decimal("100"))
                if extended_amount
                else Decimal("0")
            )
            tax_rate = max(min_tax_rate, min(raw_rate, max_tax_rate)).quantize(Decimal("0.0001"))
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

            order_line_rows.append(
                (
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
                    product_name_snapshot,
                    product_category_snapshot,
                    _as_decimal(line.get("available_stock_snapshot"), "0"),
                    None,
                )
            )
            pending_lineage.append(
                PendingLineageResolution(
                    canonical_table="order_lines",
                    canonical_id=order_line_id,
                    source_table="tbsslipdtx",
                    source_identifier=f"{doc_number}:{line_number}",
                    source_row_number=_as_int(line.get("source_row_number")),
                )
            )
            order_line_count += 1
            lineage_count += 1

            invoice_line_rows.append(
                (
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
            )
            pending_lineage.append(
                PendingLineageResolution(
                    canonical_table="invoice_lines",
                    canonical_id=invoice_line_id,
                    source_table="tbsslipdtx",
                    source_identifier=f"{doc_number}:{line_number}",
                    source_row_number=_as_int(line.get("source_row_number")),
                )
            )
            invoice_line_count += 1
            lineage_count += 1

        if (
            len(order_rows) >= _SALES_HISTORY_HEADER_BATCH_SIZE
            or len(order_line_rows) >= _SALES_HISTORY_LINE_BATCH_SIZE
        ):
            await flush_sales_rows()

    await flush_sales_rows()
    await _flush_lineage_resolutions(
        connection,
        schema_name,
        run_id,
        tenant_id,
        batch_id,
        pending_lineage,
    )
    return order_count, order_line_count, invoice_count, invoice_line_count, lineage_count