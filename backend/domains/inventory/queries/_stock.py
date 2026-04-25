"""Stock queries — valuation, stocks, transfers."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
import uuid
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import and_, asc, desc, func, or_, select
from sqlalchemy.orm import aliased
from sqlalchemy.ext.asyncio import AsyncSession

from common.models.inventory_stock import InventoryStock
from common.models.product import Product
from common.models.stock_transfer import StockTransferHistory
from common.models.supplier_order import SupplierOrder, SupplierOrderLine
from common.models.warehouse import Warehouse
from domains.inventory._product_supplier_support import _batch_get_product_suppliers

_ProductSupplierLoader = Callable[
    [AsyncSession, uuid.UUID, list[uuid.UUID]],
    Awaitable[dict[uuid.UUID, dict | None]],
]

_VALUATION_AMOUNT_QUANT = Decimal("0.0001")
_STANDARD_COST_QUANT = Decimal("0.0001")


def _quantize_valuation_amount(value: Decimal | int | float | None) -> Decimal:
    return Decimal(str(value or "0")).quantize(_VALUATION_AMOUNT_QUANT, rounding=ROUND_HALF_UP)


def _normalize_standard_cost(value: object | None) -> Decimal | None:
    if value is None or value == "":
        return None

    standard_cost = value if isinstance(value, Decimal) else Decimal(str(value))
    if standard_cost < 0:
        return None
    return standard_cost.quantize(_STANDARD_COST_QUANT, rounding=ROUND_HALF_UP)


def _resolve_inventory_valuation_cost(
    row: object,
) -> tuple[Decimal | None, str]:
    standard_cost = _normalize_standard_cost(getattr(row, "standard_cost", None))
    if standard_cost is not None:
        return standard_cost, "standard_cost"

    latest_purchase_cost = _normalize_standard_cost(getattr(row, "latest_purchase_unit_cost", None))
    if latest_purchase_cost is not None:
        return latest_purchase_cost, "latest_purchase"

    return None, "missing"


def _serialize_inventory_valuation_row(row: object) -> dict:
    quantity = int(getattr(row, "quantity", 0) or 0)
    unit_cost, cost_source = _resolve_inventory_valuation_cost(row)
    extended_value = _quantize_valuation_amount(
        Decimal(quantity) * (unit_cost or Decimal("0"))
    )

    return {
        "product_id": getattr(row, "product_id"),
        "product_code": getattr(row, "product_code"),
        "product_name": getattr(row, "product_name"),
        "category": getattr(row, "category", None),
        "warehouse_id": getattr(row, "warehouse_id"),
        "warehouse_name": getattr(row, "warehouse_name"),
        "quantity": quantity,
        "unit_cost": unit_cost,
        "extended_value": extended_value,
        "cost_source": cost_source,
    }


async def get_inventory_valuation(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    warehouse_id: uuid.UUID | None = None,
) -> dict:
    latest_purchase_ranked = (
        select(
            SupplierOrderLine.product_id.label("product_id"),
            SupplierOrderLine.unit_price.label("unit_cost"),
            SupplierOrder.received_date.label("received_date"),
            func.row_number().over(
                partition_by=SupplierOrderLine.product_id,
                order_by=(
                    SupplierOrder.received_date.desc(),
                    SupplierOrder.created_at.desc(),
                    SupplierOrderLine.id.desc(),
                ),
            ).label("row_number"),
        )
        .join(SupplierOrder, SupplierOrder.id == SupplierOrderLine.order_id)
        .where(
            SupplierOrder.tenant_id == tenant_id,
            SupplierOrder.received_date.isnot(None),
            SupplierOrderLine.unit_price.isnot(None),
        )
        .subquery()
    )

    latest_purchase = (
        select(
            latest_purchase_ranked.c.product_id,
            latest_purchase_ranked.c.unit_cost,
            latest_purchase_ranked.c.received_date,
        )
        .where(latest_purchase_ranked.c.row_number == 1)
        .subquery()
    )

    stmt = (
        select(
            InventoryStock.product_id,
            Product.code.label("product_code"),
            Product.name.label("product_name"),
            Product.category,
            Product.standard_cost,
            InventoryStock.warehouse_id,
            Warehouse.name.label("warehouse_name"),
            InventoryStock.quantity.label("quantity"),
            latest_purchase.c.unit_cost.label("latest_purchase_unit_cost"),
        )
        .join(Product, Product.id == InventoryStock.product_id)
        .join(Warehouse, Warehouse.id == InventoryStock.warehouse_id)
        .outerjoin(latest_purchase, latest_purchase.c.product_id == InventoryStock.product_id)
        .where(
            InventoryStock.tenant_id == tenant_id,
            Product.tenant_id == tenant_id,
            Warehouse.tenant_id == tenant_id,
        )
        .order_by(Warehouse.name, Product.code)
    )
    if warehouse_id is not None:
        stmt = stmt.where(InventoryStock.warehouse_id == warehouse_id)

    result = await session.execute(stmt)
    rows = result.all()

    items: list[dict] = []
    warehouse_totals: dict[uuid.UUID, dict] = {}
    grand_total_value = Decimal("0")
    grand_total_quantity = 0

    for row in rows:
        item = _serialize_inventory_valuation_row(row)
        items.append(item)

        warehouse_total = warehouse_totals.setdefault(
            item["warehouse_id"],
            {
                "warehouse_id": item["warehouse_id"],
                "warehouse_name": item["warehouse_name"],
                "total_quantity": 0,
                "total_value": Decimal("0"),
                "row_count": 0,
            },
        )
        warehouse_total["total_quantity"] = int(warehouse_total["total_quantity"]) + item["quantity"]  # noqa: E501
        warehouse_total["total_value"] = _quantize_valuation_amount(
            Decimal(str(warehouse_total["total_value"])) + item["extended_value"]
        )
        warehouse_total["row_count"] = int(warehouse_total["row_count"]) + 1

        grand_total_quantity += item["quantity"]
        grand_total_value = _quantize_valuation_amount(grand_total_value + item["extended_value"])

    return {
        "items": items,
        "warehouse_totals": list(warehouse_totals.values()),
        "grand_total_value": grand_total_value,
        "grand_total_quantity": grand_total_quantity,
        "total_rows": len(items),
    }


async def get_inventory_stocks(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    *,
    warehouse_id: uuid.UUID | None = None,
) -> list[InventoryStock]:
    """Get stock levels for a product, optionally filtered by warehouse."""
    stmt = select(InventoryStock).where(
        InventoryStock.tenant_id == tenant_id,
        InventoryStock.product_id == product_id,
    )
    if warehouse_id is not None:
        stmt = stmt.where(InventoryStock.warehouse_id == warehouse_id)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def list_transfers(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    product_id: uuid.UUID | None = None,
    warehouse_id: uuid.UUID | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    source_warehouse = aliased(Warehouse)
    destination_warehouse = aliased(Warehouse)

    where_conditions = [StockTransferHistory.tenant_id == tenant_id]
    if product_id is not None:
        where_conditions.append(StockTransferHistory.product_id == product_id)
    if warehouse_id is not None:
        where_conditions.append(
            or_(
                StockTransferHistory.from_warehouse_id == warehouse_id,
                StockTransferHistory.to_warehouse_id == warehouse_id,
            )
        )

    count_stmt = select(func.count(StockTransferHistory.id)).where(*where_conditions)
    count_result = await session.execute(count_stmt)
    total = count_result.scalar() or 0

    stmt = (
        select(
            StockTransferHistory.id.label("id"),
            StockTransferHistory.tenant_id.label("tenant_id"),
            StockTransferHistory.product_id.label("product_id"),
            Product.code.label("product_code"),
            Product.name.label("product_name"),
            StockTransferHistory.from_warehouse_id.label("from_warehouse_id"),
            source_warehouse.name.label("from_warehouse_name"),
            source_warehouse.code.label("from_warehouse_code"),
            StockTransferHistory.to_warehouse_id.label("to_warehouse_id"),
            destination_warehouse.name.label("to_warehouse_name"),
            destination_warehouse.code.label("to_warehouse_code"),
            StockTransferHistory.quantity.label("quantity"),
            StockTransferHistory.actor_id.label("actor_id"),
            StockTransferHistory.notes.label("notes"),
            StockTransferHistory.created_at.label("created_at"),
        )
        .join(Product, Product.id == StockTransferHistory.product_id)
        .join(source_warehouse, source_warehouse.id == StockTransferHistory.from_warehouse_id)
        .join(
            destination_warehouse,
            destination_warehouse.id == StockTransferHistory.to_warehouse_id,
        )
        .where(*where_conditions)
        .order_by(desc(StockTransferHistory.created_at), desc(StockTransferHistory.id))
        .offset(offset)
        .limit(limit)
    )
    result = await session.execute(stmt)
    return [dict(row) for row in result.mappings().all()], total


async def get_transfer(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    transfer_id: uuid.UUID,
) -> dict[str, Any] | None:
    source_warehouse = aliased(Warehouse)
    destination_warehouse = aliased(Warehouse)
    stmt = (
        select(
            StockTransferHistory.id.label("id"),
            StockTransferHistory.tenant_id.label("tenant_id"),
            StockTransferHistory.product_id.label("product_id"),
            Product.code.label("product_code"),
            Product.name.label("product_name"),
            StockTransferHistory.from_warehouse_id.label("from_warehouse_id"),
            source_warehouse.name.label("from_warehouse_name"),
            source_warehouse.code.label("from_warehouse_code"),
            StockTransferHistory.to_warehouse_id.label("to_warehouse_id"),
            destination_warehouse.name.label("to_warehouse_name"),
            destination_warehouse.code.label("to_warehouse_code"),
            StockTransferHistory.quantity.label("quantity"),
            StockTransferHistory.actor_id.label("actor_id"),
            StockTransferHistory.notes.label("notes"),
            StockTransferHistory.created_at.label("created_at"),
        )
        .join(Product, Product.id == StockTransferHistory.product_id)
        .join(source_warehouse, source_warehouse.id == StockTransferHistory.from_warehouse_id)
        .join(
            destination_warehouse,
            destination_warehouse.id == StockTransferHistory.to_warehouse_id,
        )
        .where(
            StockTransferHistory.id == transfer_id,
            StockTransferHistory.tenant_id == tenant_id,
        )
    )
    result = await session.execute(stmt)
    row = result.mappings().one_or_none()
    return dict(row) if row is not None else None


def _serialize_below_reorder_report_row(
    row: object,
    *,
    default_supplier: str | None,
) -> dict:
    current_stock = int(getattr(row, "current_stock", 0) or 0)
    reorder_point = int(getattr(row, "reorder_point", 0) or 0)

    return {
        "product_id": getattr(row, "product_id"),
        "product_code": getattr(row, "product_code"),
        "product_name": getattr(row, "product_name"),
        "category": getattr(row, "category", None),
        "warehouse_id": getattr(row, "warehouse_id"),
        "warehouse_name": getattr(row, "warehouse_name"),
        "current_stock": current_stock,
        "reorder_point": reorder_point,
        "shortage_qty": max(0, reorder_point - current_stock),
        "on_order_qty": int(getattr(row, "on_order_qty", 0) or 0),
        "in_transit_qty": int(getattr(row, "in_transit_qty", 0) or 0),
        "default_supplier": default_supplier,
    }


async def _list_below_reorder_products_with_supplier_loader(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    warehouse_id: uuid.UUID | None = None,
    product_supplier_loader: _ProductSupplierLoader,
) -> tuple[list[dict], int]:
    stmt = (
        select(
            InventoryStock.product_id,
            Product.code.label("product_code"),
            Product.name.label("product_name"),
            Product.category,
            InventoryStock.warehouse_id,
            Warehouse.name.label("warehouse_name"),
            InventoryStock.quantity.label("current_stock"),
            InventoryStock.reorder_point,
            InventoryStock.on_order_qty,
            InventoryStock.in_transit_qty,
        )
        .join(Product, Product.id == InventoryStock.product_id)
        .join(Warehouse, Warehouse.id == InventoryStock.warehouse_id)
        .where(
            InventoryStock.tenant_id == tenant_id,
            Product.tenant_id == tenant_id,
            Warehouse.tenant_id == tenant_id,
            Product.status == "active",
            InventoryStock.reorder_point > 0,
            InventoryStock.quantity < InventoryStock.reorder_point,
        )
        .order_by(Warehouse.name, Product.code)
    )
    if warehouse_id is not None:
        stmt = stmt.where(InventoryStock.warehouse_id == warehouse_id)

    result = await session.execute(stmt)
    rows = result.all()

    product_ids = [row.product_id for row in rows]
    supplier_map = await product_supplier_loader(session, tenant_id, product_ids)

    items: list[dict] = []
    for row in rows:
        supplier_hint = supplier_map.get(row.product_id)
        items.append(
            _serialize_below_reorder_report_row(
                row,
                default_supplier=(
                    str(supplier_hint.get("name"))
                    if supplier_hint is not None and supplier_hint.get("name")
                    else None
                ),
            )
        )

    return items, len(items)


async def list_below_reorder_products(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    warehouse_id: uuid.UUID | None = None,
) -> tuple[list[dict], int]:
    return await _list_below_reorder_products_with_supplier_loader(
        session,
        tenant_id,
        warehouse_id=warehouse_id,
        product_supplier_loader=_batch_get_product_suppliers,
    )
