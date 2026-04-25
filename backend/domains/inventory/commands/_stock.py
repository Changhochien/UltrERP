"""Stock commands — transfer_stock, create_stock_adjustment."""

from __future__ import annotations

import uuid
from decimal import Decimal, ROUND_HALF_UP
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from common.events import StockChangedEvent, emit
from common.models.audit_log import AuditLog
from common.models.inventory_stock import InventoryStock
from common.models.stock_adjustment import ReasonCode, StockAdjustment
from common.models.stock_transfer import StockTransferHistory
from common.time import utc_now
from domains.inventory.domain import InsufficientStockError, TransferValidationError

if TYPE_CHECKING:
    pass

_VALUATION_AMOUNT_QUANT = Decimal("0.0001")


def _quantize_valuation_amount(value: Decimal | int | float | None) -> Decimal:
    return Decimal(str(value or "0")).quantize(_VALUATION_AMOUNT_QUANT, rounding=ROUND_HALF_UP)
async def transfer_stock(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    from_warehouse_id: uuid.UUID,
    to_warehouse_id: uuid.UUID,
    product_id: uuid.UUID,
    quantity: int,
    actor_id: str,
    notes: str | None = None,
) -> StockTransferHistory:
    """Execute an atomic inter-warehouse stock transfer."""
    if from_warehouse_id == to_warehouse_id:
        raise TransferValidationError(
            "Source and destination warehouse must be different",
        )
    if quantity <= 0:
        raise TransferValidationError("Quantity must be positive")

    # 1. Lock source inventory row (FOR UPDATE)
    source_stmt = (
        select(InventoryStock)
        .where(
            InventoryStock.tenant_id == tenant_id,
            InventoryStock.product_id == product_id,
            InventoryStock.warehouse_id == from_warehouse_id,
        )
        .with_for_update()
    )
    source_result = await session.execute(source_stmt)
    source_stock = source_result.scalar_one_or_none()

    if source_stock is None:
        raise InsufficientStockError(available=0, requested=quantity)
    if source_stock.quantity < quantity:
        raise InsufficientStockError(
            available=source_stock.quantity,
            requested=quantity,
        )

    # 2. Get or create target inventory row
    target_stmt = (
        select(InventoryStock)
        .where(
            InventoryStock.tenant_id == tenant_id,
            InventoryStock.product_id == product_id,
            InventoryStock.warehouse_id == to_warehouse_id,
        )
        .with_for_update()
    )
    target_result = await session.execute(target_stmt)
    target_stock = target_result.scalar_one_or_none()

    if target_stock is None:
        target_stock = InventoryStock(
            tenant_id=tenant_id,
            product_id=product_id,
            warehouse_id=to_warehouse_id,
            quantity=0,
            reorder_point=0,
        )
        session.add(target_stock)
        try:
            await session.flush()
        except IntegrityError:
            await session.rollback()
            target_result = await session.execute(target_stmt)
            target_stock = target_result.scalar_one()

    # 3. Update quantities
    before_source = source_stock.quantity
    before_target = target_stock.quantity
    source_stock.quantity -= quantity
    target_stock.quantity += quantity

    # 4. Record transfer history
    transfer = StockTransferHistory(
        tenant_id=tenant_id,
        product_id=product_id,
        from_warehouse_id=from_warehouse_id,
        to_warehouse_id=to_warehouse_id,
        quantity=quantity,
        actor_id=actor_id,
        notes=notes,
    )
    session.add(transfer)
    await session.flush()

    # 5. Create adjustment records (outbound + inbound)
    adj_out = StockAdjustment(
        tenant_id=tenant_id,
        product_id=product_id,
        warehouse_id=from_warehouse_id,
        quantity_change=-quantity,
        reason_code=ReasonCode.TRANSFER_OUT,
        actor_id=actor_id,
        transfer_id=transfer.id,
        notes=notes,
    )
    adj_in = StockAdjustment(
        tenant_id=tenant_id,
        product_id=product_id,
        warehouse_id=to_warehouse_id,
        quantity_change=quantity,
        reason_code=ReasonCode.TRANSFER_IN,
        actor_id=actor_id,
        transfer_id=transfer.id,
        notes=notes,
    )
    session.add_all([adj_out, adj_in])

    # 6. Audit log
    audit = AuditLog(
        tenant_id=tenant_id,
        actor_id=actor_id,
        action="stock_transfer",
        entity_type="stock_transfer_history",
        entity_id=str(transfer.id),
        before_state={
            "source_quantity": before_source,
            "target_quantity": before_target,
        },
        after_state={
            "source_quantity": source_stock.quantity,
            "target_quantity": target_stock.quantity,
        },
        correlation_id=str(transfer.id),
        notes=notes,
    )
    session.add(audit)

    # 7. Emit stock changed events for both warehouses
    await emit(StockChangedEvent(
        tenant_id=tenant_id,
        product_id=product_id,
        warehouse_id=from_warehouse_id,
        before_quantity=before_source,
        after_quantity=source_stock.quantity,
        reorder_point=source_stock.reorder_point,
        actor_id=actor_id,
    ), session)
    await emit(StockChangedEvent(
        tenant_id=tenant_id,
        product_id=product_id,
        warehouse_id=to_warehouse_id,
        before_quantity=before_target,
        after_quantity=target_stock.quantity,
        reorder_point=target_stock.reorder_point,
        actor_id=actor_id,
    ), session)

    await session.flush()
    return transfer


async def create_stock_adjustment(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    product_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    quantity_change: int,
    reason_code: ReasonCode,
    actor_id: str,
    notes: str | None = None,
) -> dict:
    """Atomically adjust stock and record adjustment + audit + reorder alert."""
    if quantity_change == 0:
        raise TransferValidationError("Quantity change must be non-zero")

    # 1. Lock inventory row
    stock_stmt = (
        select(InventoryStock)
        .where(
            InventoryStock.tenant_id == tenant_id,
            InventoryStock.product_id == product_id,
            InventoryStock.warehouse_id == warehouse_id,
        )
        .with_for_update()
    )
    stock_result = await session.execute(stock_stmt)
    stock = stock_result.scalar_one_or_none()

    if stock is None:
        if quantity_change < 0:
            raise InsufficientStockError(available=0, requested=abs(quantity_change))
        stock = InventoryStock(
            tenant_id=tenant_id,
            product_id=product_id,
            warehouse_id=warehouse_id,
            quantity=0,
            reorder_point=0,
        )
        session.add(stock)
        await session.flush()

    # 2. Validate sufficient stock for removals
    if quantity_change < 0 and stock.quantity < abs(quantity_change):
        raise InsufficientStockError(
            available=stock.quantity,
            requested=abs(quantity_change),
        )

    # 3. Update stock
    before_qty = stock.quantity
    stock.quantity += quantity_change

    # 4. Record adjustment
    adj_id = uuid.uuid4()
    adj_created = utc_now()
    adjustment = StockAdjustment(
        id=adj_id,
        tenant_id=tenant_id,
        product_id=product_id,
        warehouse_id=warehouse_id,
        quantity_change=quantity_change,
        reason_code=reason_code,
        actor_id=actor_id,
        notes=notes,
        created_at=adj_created,
    )
    session.add(adjustment)
    await session.flush()

    # 5. Audit log
    audit = AuditLog(
        tenant_id=tenant_id,
        actor_id=actor_id,
        action="stock_adjustment",
        entity_type="stock_adjustment",
        entity_id=str(adj_id),
        before_state={"quantity": before_qty},
        after_state={"quantity": stock.quantity},
        correlation_id=str(adj_id),
        notes=notes,
    )
    session.add(audit)

    # 6. Emit stock changed event
    await emit(StockChangedEvent(
        tenant_id=tenant_id,
        product_id=product_id,
        warehouse_id=warehouse_id,
        before_quantity=before_qty,
        after_quantity=stock.quantity,
        reorder_point=stock.reorder_point,
        actor_id=actor_id,
    ), session)

    await session.flush()

    return {
        "id": adj_id,
        "product_id": product_id,
        "warehouse_id": warehouse_id,
        "quantity_change": quantity_change,
        "reason_code": reason_code.value,
        "actor_id": actor_id,
        "notes": notes,
        "updated_stock": stock.quantity,
        "created_at": adj_created,
    }


async def update_stock_settings(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    stock_id: uuid.UUID,
    *,
    reorder_point: int | None = None,
    safety_factor: float | None = None,
    lead_time_days: int | None = None,
    policy_type: str | None = None,
    target_stock_qty: int | None = None,
    on_order_qty: int | None = None,
    in_transit_qty: int | None = None,
    reserved_qty: int | None = None,
    planning_horizon_days: int | None = None,
    review_cycle_days: int | None = None,
) -> InventoryStock | None:
    """Update replenishment settings for a stock record."""
    stmt = select(InventoryStock).where(
        InventoryStock.id == stock_id,
        InventoryStock.tenant_id == tenant_id,
    )
    result = await session.execute(stmt)
    stock = result.scalar_one_or_none()
    if stock is None:
        return None

    if reorder_point is not None:
        stock.reorder_point = reorder_point
    if safety_factor is not None:
        stock.safety_factor = safety_factor
    if lead_time_days is not None:
        stock.lead_time_days = lead_time_days
    if policy_type is not None:
        stock.policy_type = policy_type
    if target_stock_qty is not None:
        stock.target_stock_qty = target_stock_qty
    if on_order_qty is not None:
        stock.on_order_qty = on_order_qty
    if in_transit_qty is not None:
        stock.in_transit_qty = in_transit_qty
    if reserved_qty is not None:
        stock.reserved_qty = reserved_qty
    if planning_horizon_days is not None:
        stock.planning_horizon_days = planning_horizon_days
    if review_cycle_days is not None:
        stock.review_cycle_days = review_cycle_days

    await session.flush()
    return stock
