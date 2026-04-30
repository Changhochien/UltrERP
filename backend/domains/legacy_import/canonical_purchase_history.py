"""Purchase history import logic for canonical legacy batches."""

from __future__ import annotations

import json
import uuid
from decimal import Decimal

from domains.legacy_import.canonical_common import (
    _as_decimal,
    _as_int,
    _as_legacy_date,
    _as_money,
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

_LEGACY_RECEIVING_SOURCE = "tbsslipdtj"
_PURCHASE_HISTORY_HEADER_BATCH_SIZE = 1_000
_PURCHASE_HISTORY_LINE_BATCH_SIZE = 5_000

_SUPPLIER_INVOICE_UPSERT_QUERY = """
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
                remaining_payable_amount,
                conversion_rate,
                conversion_effective_date,
                applied_rate_source,
                currency_source,
                payment_terms_source,
                base_subtotal_amount,
                base_tax_amount,
                base_total_amount,
                remaining_base_payable_amount,
                status,
                notes,
                legacy_header_snapshot,
                created_at,
                updated_at
            )
            VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                $11, $12, $13, $14, $15, $16, $17, $18, $19,
                $20, $21, $22::json, $23, $23
            )
            ON CONFLICT (id) DO UPDATE SET
                supplier_id = EXCLUDED.supplier_id,
                invoice_number = EXCLUDED.invoice_number,
                invoice_date = EXCLUDED.invoice_date,
                currency_code = EXCLUDED.currency_code,
                subtotal_amount = EXCLUDED.subtotal_amount,
                tax_amount = EXCLUDED.tax_amount,
                total_amount = EXCLUDED.total_amount,
                remaining_payable_amount = EXCLUDED.remaining_payable_amount,
                conversion_rate = EXCLUDED.conversion_rate,
                conversion_effective_date = EXCLUDED.conversion_effective_date,
                applied_rate_source = EXCLUDED.applied_rate_source,
                currency_source = EXCLUDED.currency_source,
                payment_terms_source = EXCLUDED.payment_terms_source,
                base_subtotal_amount = EXCLUDED.base_subtotal_amount,
                base_tax_amount = EXCLUDED.base_tax_amount,
                base_total_amount = EXCLUDED.base_total_amount,
                remaining_base_payable_amount = EXCLUDED.remaining_base_payable_amount,
                status = EXCLUDED.status,
                notes = EXCLUDED.notes,
                legacy_header_snapshot = EXCLUDED.legacy_header_snapshot,
                updated_at = NOW()
            """

_SUPPLIER_INVOICE_LINE_UPSERT_QUERY = """
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
                    base_unit_price,
                    base_subtotal_amount,
                    base_tax_amount,
                    base_total_amount,
                    created_at
                )
                VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                    $11, $12, $13, $14, $15, $16, $17, $18, NOW()
                )
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
                    total_amount = EXCLUDED.total_amount,
                    base_unit_price = EXCLUDED.base_unit_price,
                    base_subtotal_amount = EXCLUDED.base_subtotal_amount,
                    base_tax_amount = EXCLUDED.base_tax_amount,
                    base_total_amount = EXCLUDED.base_total_amount
                """


def _tenant_scoped_uuid(tenant_id: uuid.UUID, kind: str, *parts: str) -> uuid.UUID:
    return deterministic_legacy_uuid(kind, str(tenant_id), *parts)


def _map_purchase_invoice_status(must_pay_amount: object | None) -> str:
    return "open" if _as_money(_as_decimal(must_pay_amount, "0.00")) > 0 else "paid"


def _resolve_purchase_invoice_total(
    subtotal_amount: object | None,
    tax_amount: object | None,
    must_pay_amount: object | None,
    line_total_amount: object | None = None,
) -> Decimal:
    gross_total = _as_money(_as_decimal(subtotal_amount, "0.00") + _as_decimal(tax_amount, "0.00"))
    if gross_total != 0:
        return gross_total
    line_total = _as_money(_as_decimal(line_total_amount, "0.00"))
    if line_total != 0:
        return line_total
    return _as_money(_as_decimal(must_pay_amount, "0.00"))


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
            "must_pay_amount": _as_text(header.get("must_pay_amount")),
            "raw_invoice_number": raw_invoice_number,
            "resolved_invoice_number": _as_text(header.get("invoice_number")),
            "invoice_number_source": (
                "legacy_invoice_number" if raw_invoice_number else "doc_number"
            ),
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


async def _flush_purchase_history_rows(
    connection,
    schema_name: str,
    run_id: uuid.UUID,
    tenant_id: uuid.UUID,
    batch_id: str,
    invoice_rows: list[tuple[object, ...]],
    invoice_line_rows: list[tuple[object, ...]],
    pending_lineage: list[PendingLineageResolution],
) -> None:
    if invoice_rows:
        await execute_many(connection, _SUPPLIER_INVOICE_UPSERT_QUERY, invoice_rows)
        invoice_rows.clear()

    if invoice_line_rows:
        await execute_many(connection, _SUPPLIER_INVOICE_LINE_UPSERT_QUERY, invoice_line_rows)
        invoice_line_rows.clear()

    if pending_lineage:
        await _flush_lineage_resolutions(
            connection,
            schema_name,
            run_id,
            tenant_id,
            batch_id,
            pending_lineage,
        )
        pending_lineage.clear()


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
    invoice_rows: list[tuple[object, ...]] = []
    invoice_line_rows: list[tuple[object, ...]] = []
    pending_lineage: list[PendingLineageResolution] = []

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
        header_lines = sorted(
            lines_by_doc.get(doc_number, []), key=lambda item: _as_int(item.get("line_number"), 0)
        )
        tax_amount = _as_money(_as_decimal(header.get("tax_amount"), "0.00"))
        subtotal_amount = _as_money(_as_decimal(header.get("subtotal"), "0.00"))
        remaining_payable_amount = _as_money(_as_decimal(header.get("must_pay_amount"), "0.00"))
        line_total_amount = _as_money(
            sum(
                (_as_decimal(line.get("extended_amount"), "0.00") for line in header_lines),
                Decimal("0.00"),
            )
        )
        total_amount = _resolve_purchase_invoice_total(
            header.get("subtotal"),
            header.get("tax_amount"),
            header.get("must_pay_amount"),
            line_total_amount,
        )
        supplier_invoice_status = _map_purchase_invoice_status(header.get("must_pay_amount"))
        legacy_header_snapshot = _build_purchase_header_snapshot(header)

        invoice_rows.append(
            (
                supplier_invoice_id,
                tenant_id,
                supplier_id,
                invoice_number,
                invoice_date,
                _currency_code(header.get("currency_code")),
                subtotal_amount,
                tax_amount,
                total_amount,
                remaining_payable_amount,
                Decimal("1.0000000000"),
                invoice_date,
                "identity",
                "legacy_compatibility",
                "legacy_compatibility",
                subtotal_amount,
                tax_amount,
                total_amount,
                remaining_payable_amount,
                supplier_invoice_status,
                _as_text(header.get("notes")) or None,
                json.dumps(legacy_header_snapshot),
                created_at,
            )
        )
        pending_lineage.append(
            PendingLineageResolution(
                canonical_table="supplier_invoices",
                canonical_id=supplier_invoice_id,
                source_table="tbsslipj",
                source_identifier=doc_number,
                source_row_number=_as_int(header.get("source_row_number")),
            )
        )
        invoice_count += 1
        lineage_count += 1

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

            invoice_line_rows.append(
                (
                    supplier_invoice_line_id,
                    supplier_invoice_id,
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
                    unit_price,
                    subtotal,
                    line_tax_amount,
                    line_total,
                )
            )
            pending_lineage.append(
                PendingLineageResolution(
                    canonical_table="supplier_invoice_lines",
                    canonical_id=supplier_invoice_line_id,
                    source_table=_LEGACY_RECEIVING_SOURCE,
                    source_identifier=f"{doc_number}:{line_number}",
                    source_row_number=_as_int(line.get("source_row_number")),
                )
            )
            invoice_line_count += 1
            lineage_count += 1

        if (
            len(invoice_rows) >= _PURCHASE_HISTORY_HEADER_BATCH_SIZE
            or len(invoice_line_rows) >= _PURCHASE_HISTORY_LINE_BATCH_SIZE
        ):
            await _flush_purchase_history_rows(
                connection,
                schema_name,
                run_id,
                tenant_id,
                batch_id,
                invoice_rows,
                invoice_line_rows,
                pending_lineage,
            )

    await _flush_purchase_history_rows(
        connection,
        schema_name,
        run_id,
        tenant_id,
        batch_id,
        invoice_rows,
        invoice_line_rows,
        pending_lineage,
    )
    return invoice_count, invoice_line_count, lineage_count