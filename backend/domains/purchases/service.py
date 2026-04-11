"""Read models for supplier invoices and purchase history."""

from __future__ import annotations

import uuid
from typing import cast

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from common.models.product import Product
from common.models.supplier import Supplier
from common.models.supplier_invoice import SupplierInvoice
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


async def get_supplier_invoice(
    session: AsyncSession,
    invoice_id: uuid.UUID,
    tenant_id: uuid.UUID | None = None,
) -> dict | None:
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
        "created_at": invoice.created_at,
        "updated_at": invoice.updated_at,
        "lines": [
            {
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
            }
            for line in invoice.lines
        ],
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
            "created_at": invoice.created_at,
            "updated_at": invoice.updated_at,
            "line_count": len(invoice.lines),
        }
        for invoice in invoices
    ]
    return items, total, status_totals