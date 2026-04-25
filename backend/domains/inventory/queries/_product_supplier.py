"""Product-supplier queries — read operations that fetch product-supplier data."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import and_, desc, asc, select, literal
from sqlalchemy.ext.asyncio import AsyncSession
from common.models.product_supplier import ProductSupplier

# Re-export helpers for internal use
from domains.inventory._product_supplier_support import (
    _serialize_product_supplier_association,
    _is_missing_product_supplier_table,
    _product_supplier_table_exists,
    _load_product_supplier_explicit_row,
)


async def list_product_suppliers(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
) -> list[dict[str, Any]]:
    """List all supplier associations for a product."""
    from common.models.product_supplier import ProductSupplier
    from common.models.supplier import Supplier

    stmt = (
        select(ProductSupplier, Supplier.name)
        .join(
            Supplier,
            and_(
                Supplier.id == ProductSupplier.supplier_id,
                Supplier.tenant_id == tenant_id,
            ),
        )
        .where(
            ProductSupplier.tenant_id == tenant_id,
            ProductSupplier.product_id == product_id,
        )
        .order_by(desc(ProductSupplier.is_default), asc(Supplier.name))
    )
    result = await session.execute(stmt)
    return [
        _serialize_product_supplier_association(association, supplier_name)
        for association, supplier_name in result.all()
    ]


async def get_product_supplier(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
) -> dict | None:
    """Return the explicit default supplier for a product, else most-recent fallback.

    Explicit product-supplier associations are the primary source of truth.
    When no explicit default exists, falls back to the most-recent supplier
    heuristic based on supplier orders and invoices.
    """
    from common.models.supplier import Supplier
    from common.models.supplier_invoice import SupplierInvoice, SupplierInvoiceLine
    from common.models.supplier_order import SupplierOrder, SupplierOrderLine
    from sqlalchemy import func

    # Try explicit default first
    explicit_stmt = (
        select(
            Supplier.id,
            Supplier.name,
            ProductSupplier.unit_cost,
            func.coalesce(
                ProductSupplier.lead_time_days,
                Supplier.default_lead_time_days,
            ).label("effective_lead_time_days"),
        )
        .join(
            Supplier,
            and_(
                Supplier.id == ProductSupplier.supplier_id,
                Supplier.tenant_id == tenant_id,
            ),
        )
        .where(
            ProductSupplier.tenant_id == tenant_id,
            ProductSupplier.product_id == product_id,
            ProductSupplier.is_default.is_(True),
        )
        .limit(1)
    )
    explicit_row = await _load_product_supplier_explicit_row(session, explicit_stmt)

    if explicit_row is not None:
        return {
            "supplier_id": explicit_row.id,
            "name": explicit_row.name,
            "unit_cost": (
                float(explicit_row.unit_cost) if explicit_row.unit_cost is not None else None
            ),
            "default_lead_time_days": explicit_row.effective_lead_time_days,
        }

    # Fallback to most recent supplier from orders/invoices
    supplier_sources = (
        select(
            SupplierOrder.supplier_id.label("supplier_id"),
            SupplierOrder.received_date.label("effective_date"),
            SupplierOrderLine.unit_price.label("unit_cost"),
            literal(0).label("source_priority"),
        )
        .join(SupplierOrder, SupplierOrder.id == SupplierOrderLine.order_id)
        .where(
            SupplierOrder.tenant_id == tenant_id,
            SupplierOrderLine.product_id == product_id,
            SupplierOrder.received_date.isnot(None),
        )
        .union_all(
            select(
                SupplierInvoice.supplier_id.label("supplier_id"),
                SupplierInvoice.invoice_date.label("effective_date"),
                SupplierInvoiceLine.unit_price.label("unit_cost"),
                literal(1).label("source_priority"),
            )
            .join(
                SupplierInvoice,
                SupplierInvoice.id == SupplierInvoiceLine.supplier_invoice_id,
            )
            .where(
                SupplierInvoice.tenant_id == tenant_id,
                SupplierInvoiceLine.product_id == product_id,
                SupplierInvoiceLine.unit_price.isnot(None),
            )
        )
        .subquery()
    )

    stmt = (
        select(
            Supplier.id,
            Supplier.name,
            Supplier.default_lead_time_days,
            supplier_sources.c.unit_cost,
        )
        .join(supplier_sources, Supplier.id == supplier_sources.c.supplier_id)
        .where(Supplier.tenant_id == tenant_id)
        .order_by(
            supplier_sources.c.effective_date.desc(),
            supplier_sources.c.source_priority.desc(),
        )
        .limit(1)
    )
    result = await session.execute(stmt)
    row = result.first()

    if row is None:
        return None

    return {
        "supplier_id": row.id,
        "name": row.name,
        "unit_cost": float(row.unit_cost) if row.unit_cost is not None else None,
        "default_lead_time_days": row.default_lead_time_days,
    }
