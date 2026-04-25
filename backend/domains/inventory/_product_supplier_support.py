"""Private product-supplier helpers shared across inventory modules."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import and_, func, literal, select
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession

from common.models.product_supplier import ProductSupplier
from common.models.supplier import Supplier
from common.models.supplier_invoice import SupplierInvoice, SupplierInvoiceLine
from common.models.supplier_order import SupplierOrder, SupplierOrderLine


def _serialize_product_supplier_association(
    association: ProductSupplier,
    supplier_name: str,
) -> dict[str, Any]:
    return {
        "id": association.id,
        "product_id": association.product_id,
        "supplier_id": association.supplier_id,
        "supplier_name": supplier_name,
        "unit_cost": float(association.unit_cost) if association.unit_cost is not None else None,
        "lead_time_days": association.lead_time_days,
        "is_default": association.is_default,
        "created_at": association.created_at,
        "updated_at": association.updated_at,
    }


async def _batch_get_product_suppliers(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_ids: list[uuid.UUID],
) -> dict[uuid.UUID, dict | None]:
    unique_product_ids = list(dict.fromkeys(product_ids))
    if not unique_product_ids:
        return {}

    supplier_sources = (
        select(
            SupplierOrderLine.product_id.label("product_id"),
            SupplierOrder.supplier_id.label("supplier_id"),
            SupplierOrder.received_date.label("effective_date"),
            SupplierOrderLine.unit_price.label("unit_cost"),
            SupplierOrderLine.id.label("source_row_id"),
            literal(0).label("source_priority"),
        )
        .join(SupplierOrder, SupplierOrder.id == SupplierOrderLine.order_id)
        .where(
            SupplierOrder.tenant_id == tenant_id,
            SupplierOrderLine.product_id.in_(unique_product_ids),
            SupplierOrder.received_date.isnot(None),
            SupplierOrderLine.unit_price.isnot(None),
        )
        .union_all(
            select(
                SupplierInvoiceLine.product_id.label("product_id"),
                SupplierInvoice.supplier_id.label("supplier_id"),
                SupplierInvoice.invoice_date.label("effective_date"),
                SupplierInvoiceLine.unit_price.label("unit_cost"),
                SupplierInvoiceLine.id.label("source_row_id"),
                literal(1).label("source_priority"),
            )
            .join(
                SupplierInvoice,
                SupplierInvoice.id == SupplierInvoiceLine.supplier_invoice_id,
            )
            .where(
                SupplierInvoice.tenant_id == tenant_id,
                SupplierInvoiceLine.product_id.in_(unique_product_ids),
                SupplierInvoiceLine.unit_price.isnot(None),
            )
        )
        .subquery()
    )

    fallback_ranked = (
        select(
            supplier_sources.c.product_id,
            supplier_sources.c.supplier_id,
            Supplier.name.label("name"),
            Supplier.default_lead_time_days.label("default_lead_time_days"),
            supplier_sources.c.unit_cost,
            func.row_number().over(
                partition_by=supplier_sources.c.product_id,
                order_by=(
                    supplier_sources.c.effective_date.desc(),
                    supplier_sources.c.source_priority.desc(),
                    supplier_sources.c.source_row_id.desc(),
                ),
            ).label("row_number"),
        )
        .join(
            Supplier,
            and_(
                Supplier.id == supplier_sources.c.supplier_id,
                Supplier.tenant_id == tenant_id,
            ),
        )
        .subquery()
    )

    fallback_candidates = select(
        fallback_ranked.c.product_id,
        fallback_ranked.c.supplier_id,
        fallback_ranked.c.name,
        fallback_ranked.c.unit_cost,
        fallback_ranked.c.default_lead_time_days,
        literal(1).label("candidate_priority"),
    ).where(fallback_ranked.c.row_number == 1)

    explicit_candidates = (
        select(
            ProductSupplier.product_id.label("product_id"),
            Supplier.id.label("supplier_id"),
            Supplier.name.label("name"),
            ProductSupplier.unit_cost.label("unit_cost"),
            func.coalesce(
                ProductSupplier.lead_time_days,
                Supplier.default_lead_time_days,
            ).label("default_lead_time_days"),
            literal(0).label("candidate_priority"),
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
            ProductSupplier.product_id.in_(unique_product_ids),
            ProductSupplier.is_default.is_(True),
        )
    )

    def _ranked_stmt(candidate_select):
        explicit_or_fallback = candidate_select.subquery("explicit_or_fallback")
        ranked_candidates = (
            select(
                explicit_or_fallback.c.product_id,
                explicit_or_fallback.c.supplier_id,
                explicit_or_fallback.c.name,
                explicit_or_fallback.c.unit_cost,
                explicit_or_fallback.c.default_lead_time_days,
                func.row_number().over(
                    partition_by=explicit_or_fallback.c.product_id,
                    order_by=(explicit_or_fallback.c.candidate_priority.asc(),),
                ).label("row_number"),
            )
            .select_from(explicit_or_fallback)
            .subquery()
        )
        return select(
            ranked_candidates.c.product_id,
            ranked_candidates.c.supplier_id,
            ranked_candidates.c.name,
            ranked_candidates.c.unit_cost,
            ranked_candidates.c.default_lead_time_days,
        ).where(ranked_candidates.c.row_number == 1)

    supplier_map: dict[uuid.UUID, dict | None] = {
        product_id: None for product_id in unique_product_ids
    }

    candidates = (
        explicit_candidates.union_all(fallback_candidates)
        if await _product_supplier_table_exists(session)
        else fallback_candidates
    )
    result = await session.execute(_ranked_stmt(candidates))

    for row in result.all():
        supplier_map[row.product_id] = {
            "supplier_id": row.supplier_id,
            "name": row.name,
            "unit_cost": float(row.unit_cost) if row.unit_cost is not None else None,
            "default_lead_time_days": row.default_lead_time_days,
        }
    return supplier_map


def _is_missing_product_supplier_table(exc: ProgrammingError) -> bool:
    return "product_supplier" in str(exc).lower()


async def _product_supplier_table_exists(session: AsyncSession) -> bool:
    session_info = getattr(session, "info", None)
    cached = session_info.get("product_supplier_table_exists") if isinstance(session_info, dict) else None
    if isinstance(cached, bool):
        return cached

    result = await session.execute(select(func.to_regclass("product_supplier")))
    exists = result.scalar_one_or_none() is not None
    if isinstance(session_info, dict):
        session_info["product_supplier_table_exists"] = exists
    return exists


async def _load_product_supplier_explicit_row(session: AsyncSession, explicit_stmt):
    try:
        return (await session.execute(explicit_stmt)).first()
    except ProgrammingError as exc:
        if _is_missing_product_supplier_table(exc):
            return None
        raise