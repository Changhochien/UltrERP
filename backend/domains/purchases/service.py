"""Read models for supplier invoices and purchase history."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import cast

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from common.models.product import Product
from common.models.supplier import Supplier
from common.models.supplier_invoice import (
    SupplierInvoice,
    SupplierInvoiceLine,
    ProcurementMismatchStatus,
)
from common.tenant import DEFAULT_TENANT_ID, set_tenant


async def _load_supplier_name_map(
    session: AsyncSession,
    supplier_ids: set[uuid.UUID],
) -> dict[uuid.UUID, str]:
    if not supplier_ids:
        return {}
    result = await session.execute(
        select(Supplier.id, Supplier.name).where(Supplier.id.in_(supplier_ids))
    )
    return {row[0]: row[1] for row in result.all()}


async def _load_product_name_map(
    session: AsyncSession,
    product_ids: set[uuid.UUID],
) -> dict[uuid.UUID, str]:
    if not product_ids:
        return {}
    result = await session.execute(
        select(Product.id, Product.name).where(Product.id.in_(product_ids))
    )
    return {row[0]: row[1] for row in result.all()}


def _line_to_dict(line: SupplierInvoiceLine, product_names: dict[uuid.UUID, str]) -> dict:
    """Convert a supplier invoice line to dict including procurement lineage fields."""
    # Determine mismatch_status value
    mismatch_status = getattr(line, "mismatch_status", None)
    if mismatch_status is None:
        mismatch_status_str = ProcurementMismatchStatus.NOT_CHECKED.value
    elif isinstance(mismatch_status, ProcurementMismatchStatus):
        mismatch_status_str = mismatch_status.value
    else:
        mismatch_status_str = str(mismatch_status)

    return {
        "id": line.id,
        "line_number": line.line_number,
        "product_id": line.product_id,
        "product_code_snapshot": line.product_code_snapshot,
        "product_name": (
            product_names.get(line.product_id) if line.product_id is not None else None
        ),
        "description": line.description,
        "quantity": line.quantity,
        "unit_price": line.unit_price,
        "subtotal_amount": line.subtotal_amount,
        "tax_type": line.tax_type,
        "tax_rate": line.tax_rate,
        "tax_amount": line.tax_amount,
        "total_amount": line.total_amount,
        "created_at": line.created_at,
        # Procurement lineage references (Story 24-4)
        "rfq_item_id": getattr(line, "rfq_item_id", None),
        "supplier_quotation_item_id": getattr(line, "supplier_quotation_item_id", None),
        "purchase_order_line_id": getattr(line, "purchase_order_line_id", None),
        "goods_receipt_line_id": getattr(line, "goods_receipt_line_id", None),
        # Mismatch and tolerance-ready fields (Story 24-4)
        "reference_quantity": getattr(line, "reference_quantity", None),
        "reference_unit_price": getattr(line, "reference_unit_price", None),
        "reference_total_amount": getattr(line, "reference_total_amount", None),
        "quantity_variance": getattr(line, "quantity_variance", None),
        "unit_price_variance": getattr(line, "unit_price_variance", None),
        "total_amount_variance": getattr(line, "total_amount_variance", None),
        "quantity_variance_pct": getattr(line, "quantity_variance_pct", None),
        "unit_price_variance_pct": getattr(line, "unit_price_variance_pct", None),
        "total_amount_variance_pct": getattr(line, "total_amount_variance_pct", None),
        "comparison_basis_snapshot": getattr(line, "comparison_basis_snapshot", None),
        "mismatch_status": mismatch_status_str,
        "tolerance_rule_code": getattr(line, "tolerance_rule_code", None),
        "tolerance_rule_id": getattr(line, "tolerance_rule_id", None),
    }


def _has_lineage(line: SupplierInvoiceLine) -> bool:
    """Check if a line has any procurement lineage references."""
    return any([
        getattr(line, "rfq_item_id", None) is not None,
        getattr(line, "supplier_quotation_item_id", None) is not None,
        getattr(line, "purchase_order_line_id", None) is not None,
        getattr(line, "goods_receipt_line_id", None) is not None,
    ])


def _determine_lineage_state(line: SupplierInvoiceLine) -> str:
    """Determine the lineage state for a supplier invoice line.

    States:
    - linked: Has at least one procurement reference
    - unlinked_historical: No references (pre-procurement lineage)

    Note: missing_reference state is out of scope for v1; entity existence
    validation would require cross-domain queries that add latency.
    """
    if _has_lineage(line):
        return "linked"
    return "unlinked_historical"


def _build_lineage_response(line: SupplierInvoiceLine) -> dict:
    """Build the procurement lineage response for a line."""
    return {
        "rfq_item_id": getattr(line, "rfq_item_id", None),
        "supplier_quotation_item_id": getattr(line, "supplier_quotation_item_id", None),
        "purchase_order_line_id": getattr(line, "purchase_order_line_id", None),
        "goods_receipt_line_id": getattr(line, "goods_receipt_line_id", None),
        "lineage_state": _determine_lineage_state(line),
    }


def _build_mismatch_summary(line: SupplierInvoiceLine) -> dict | None:
    """Build the mismatch summary for a line if any mismatch data exists."""
    mismatch_status = getattr(line, "mismatch_status", None)
    if mismatch_status is None:
        mismatch_status_str = ProcurementMismatchStatus.NOT_CHECKED.value
    elif isinstance(mismatch_status, ProcurementMismatchStatus):
        mismatch_status_str = mismatch_status.value
    else:
        mismatch_status_str = str(mismatch_status)

    # Only return if there's actual mismatch data
    has_mismatch_data = any([
        getattr(line, "quantity_variance", None) is not None,
        getattr(line, "unit_price_variance", None) is not None,
        getattr(line, "total_amount_variance", None) is not None,
        getattr(line, "reference_quantity", None) is not None,
        getattr(line, "reference_unit_price", None) is not None,
        getattr(line, "reference_total_amount", None) is not None,
        mismatch_status_str != ProcurementMismatchStatus.NOT_CHECKED.value,
    ])

    if not has_mismatch_data:
        return None

    return {
        "mismatch_status": mismatch_status_str,
        "quantity_variance": getattr(line, "quantity_variance", None),
        "unit_price_variance": getattr(line, "unit_price_variance", None),
        "total_amount_variance": getattr(line, "total_amount_variance", None),
        "quantity_variance_pct": getattr(line, "quantity_variance_pct", None),
        "unit_price_variance_pct": getattr(line, "unit_price_variance_pct", None),
        "total_amount_variance_pct": getattr(line, "total_amount_variance_pct", None),
        "tolerance_rule_code": getattr(line, "tolerance_rule_code", None),
        "tolerance_rule_id": getattr(line, "tolerance_rule_id", None),
        "comparison_basis_snapshot": getattr(line, "comparison_basis_snapshot", None),
    }


async def get_supplier_invoice(
    session: AsyncSession,
    invoice_id: uuid.UUID,
    tenant_id: uuid.UUID | None = None,
    include_lineage: bool = False,
) -> dict | None:
    """Get a single supplier invoice with optional lineage data.

    Args:
        session: Database session
        invoice_id: Invoice UUID
        tenant_id: Tenant UUID (defaults to DEFAULT_TENANT_ID)
        include_lineage: If True, includes procurement lineage trace per line
    """
    tid = tenant_id or DEFAULT_TENANT_ID
    result = await session.execute(
        select(SupplierInvoice)
        .options(selectinload(SupplierInvoice.lines))
        .where(
            SupplierInvoice.id == invoice_id,
            SupplierInvoice.tenant_id == tid,
        )
    )
    invoice = cast(SupplierInvoice | None, result.scalar_one_or_none())
    if invoice is None:
        return None

    supplier_names = await _load_supplier_name_map(session, {invoice.supplier_id})
    product_names = await _load_product_name_map(
        session,
        {line.product_id for line in invoice.lines if line.product_id is not None},
    )

    lines_data = []
    for line in invoice.lines:
        line_dict = _line_to_dict(line, product_names)
        if include_lineage:
            line_dict["lineage"] = _build_lineage_response(line)
            line_dict["mismatch_summary"] = _build_mismatch_summary(line)
        lines_data.append(line_dict)

    return {
        "id": invoice.id,
        "supplier_id": invoice.supplier_id,
        "supplier_name": supplier_names.get(invoice.supplier_id, "Unknown supplier"),
        "invoice_number": invoice.invoice_number,
        "invoice_date": invoice.invoice_date,
        "currency_code": invoice.currency_code,
        "subtotal_amount": invoice.subtotal_amount,
        "tax_amount": invoice.tax_amount,
        "total_amount": invoice.total_amount,
        "remaining_payable_amount": getattr(invoice, "remaining_payable_amount", None),
        "status": invoice.status.value,
        "notes": invoice.notes,
        "legacy_header_snapshot": getattr(invoice, "legacy_header_snapshot", None),
        # Procurement lineage - header-level PO reference (Story 24-4)
        "purchase_order_id": getattr(invoice, "purchase_order_id", None),
        "created_at": invoice.created_at,
        "updated_at": invoice.updated_at,
        "lines": lines_data,
    }


async def list_supplier_invoices(
    session: AsyncSession,
    tenant_id: uuid.UUID | None = None,
    *,
    status_filter: str | None = None,
    supplier_id: uuid.UUID | None = None,
    page: int = 1,
    page_size: int = 20,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> tuple[list[dict], int, dict[str, int]]:
    tid = tenant_id or DEFAULT_TENANT_ID
    offset = (page - 1) * page_size
    order_columns = {
        "created_at": SupplierInvoice.created_at,
        "invoice_date": SupplierInvoice.invoice_date,
        "total_amount": SupplierInvoice.total_amount,
    }
    sort_column = order_columns.get(sort_by, SupplierInvoice.created_at)
    order_clause = sort_column.asc() if sort_order == "asc" else sort_column.desc()

    base_filters = [SupplierInvoice.tenant_id == tid]
    if supplier_id is not None:
        base_filters.append(SupplierInvoice.supplier_id == supplier_id)

    filters = list(base_filters)
    if status_filter is not None:
        filters.append(SupplierInvoice.status == status_filter)

    async with session.begin():
        await set_tenant(session, tid)

        count_result = await session.execute(
            select(func.count(SupplierInvoice.id)).where(*filters)
        )
        total = int(count_result.scalar() or 0)

        status_totals_result = await session.execute(
            select(SupplierInvoice.status, func.count(SupplierInvoice.id))
            .where(*base_filters)
            .group_by(SupplierInvoice.status)
        )
        status_totals = {
            (status.value if hasattr(status, "value") else str(status)): int(count)
            for status, count in status_totals_result.all()
        }
        for known_status in ("open", "paid", "voided"):
            status_totals.setdefault(known_status, 0)

        result = await session.execute(
            select(SupplierInvoice)
            .options(selectinload(SupplierInvoice.lines))
            .where(*filters)
            .order_by(order_clause)
            .offset(offset)
            .limit(page_size)
        )
        invoices = result.scalars().unique().all()
        supplier_names = await _load_supplier_name_map(
            session,
            {invoice.supplier_id for invoice in invoices},
        )

    items = [
        {
            "id": invoice.id,
            "supplier_id": invoice.supplier_id,
            "supplier_name": supplier_names.get(invoice.supplier_id, "Unknown supplier"),
            "invoice_number": invoice.invoice_number,
            "invoice_date": invoice.invoice_date,
            "currency_code": invoice.currency_code,
            "total_amount": invoice.total_amount,
            "remaining_payable_amount": getattr(invoice, "remaining_payable_amount", None),
            "status": invoice.status.value,
            "legacy_header_snapshot": getattr(invoice, "legacy_header_snapshot", None),
            # Procurement lineage - header-level PO reference (Story 24-4)
            "purchase_order_id": getattr(invoice, "purchase_order_id", None),
            "created_at": invoice.created_at,
            "updated_at": invoice.updated_at,
            "line_count": len(invoice.lines),
        }
        for invoice in invoices
    ]
    return items, total, status_totals


# ------------------------------------------------------------------
# Procurement Lineage Service (Story 24-4)
# ------------------------------------------------------------------


async def get_lineage_for_supplier_invoice(
    session: AsyncSession,
    invoice_id: uuid.UUID,
    tenant_id: uuid.UUID | None = None,
) -> dict | None:
    """Get full procurement lineage chain for a supplier invoice.

    Returns the lineage chain from RFQ through supplier quotation, PO,
    goods receipt, to supplier invoice for audit and three-way-match review.

    Note: This is a read-only service that traces lineage without implementing
    AP posting workflow or final three-way-match approval gate.
    """
    from common.models.supplier_invoice import SupplierInvoiceLine

    tid = tenant_id or DEFAULT_TENANT_ID

    # Load invoice with lines
    result = await session.execute(
        select(SupplierInvoice)
        .options(selectinload(SupplierInvoice.lines))
        .where(
            SupplierInvoice.id == invoice_id,
            SupplierInvoice.tenant_id == tid,
        )
    )
    invoice = cast(SupplierInvoice | None, result.scalar_one_or_none())
    if invoice is None:
        return None

    # Build lineage response for each line
    product_names = await _load_product_name_map(
        session,
        {line.product_id for line in invoice.lines if line.product_id is not None},
    )

    lines_data = []
    for line in invoice.lines:
        line_dict = _line_to_dict(line, product_names)
        line_dict["lineage"] = _build_lineage_response(line)
        line_dict["mismatch_summary"] = _build_mismatch_summary(line)
        lines_data.append(line_dict)

    # Build the response
    return {
        "supplier_invoice_id": invoice.id,
        "supplier_invoice_name": invoice.invoice_number,
        "purchase_order_id": getattr(invoice, "purchase_order_id", None),
        "line_count": len(invoice.lines),
        "lines": lines_data,
    }


def calculate_mismatch_variance(
    invoice_quantity: Decimal,
    invoice_unit_price: Decimal,
    invoice_total: Decimal,
    reference_quantity: Decimal | None,
    reference_unit_price: Decimal | None,
    reference_total: Decimal | None,
) -> dict:
    """Calculate variance fields between invoice and reference values.

    Used for three-way-match readiness (Story 24-4).
    Returns variance values and percentages.
    """
    result = {
        "quantity_variance": None,
        "unit_price_variance": None,
        "total_amount_variance": None,
        "quantity_variance_pct": None,
        "unit_price_variance_pct": None,
        "total_amount_variance_pct": None,
    }

    if reference_quantity is not None:
        result["quantity_variance"] = invoice_quantity - reference_quantity
        if reference_quantity != 0:
            result["quantity_variance_pct"] = (
                (invoice_quantity - reference_quantity) / reference_quantity
            ) * 100

    if reference_unit_price is not None:
        result["unit_price_variance"] = invoice_unit_price - reference_unit_price
        if reference_unit_price != 0:
            result["unit_price_variance_pct"] = (
                (invoice_unit_price - reference_unit_price) / reference_unit_price
            ) * 100

    if reference_total is not None:
        result["total_amount_variance"] = invoice_total - reference_total
        if reference_total != 0:
            result["total_amount_variance_pct"] = (
                (invoice_total - reference_total) / reference_total
            ) * 100

    return result
