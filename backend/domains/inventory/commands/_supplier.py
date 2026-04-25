"""Supplier commands — write operations that modify supplier state."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.errors import ValidationError
from common.models.audit_log import AuditLog
from common.models.inventory_stock import InventoryStock
from common.models.stock_adjustment import ReasonCode, StockAdjustment
from common.models.supplier_order import SupplierOrderStatus

if TYPE_CHECKING:
    from common.models.supplier import Supplier
    from common.models.supplier_order import SupplierOrder
    from domains.inventory.schemas import SupplierCreate, SupplierUpdate
    from pydantic import BaseModel

# Re-export helpers for internal use
from domains.inventory._supplier_order_support import _serialize_order


def _payload_value(data: Any, field: str) -> Any:
    if isinstance(data, dict):
        return data.get(field)
    return getattr(data, field, None)


def _normalize_optional_text(value: Any) -> str | None:
    if value is None:
        return None

    normalized = str(value).strip()
    return normalized or None


def _normalize_supplier_payload(
    data: Any,
) -> tuple[str, str | None, str | None, str | None, int | None]:
    """Normalize supplier payload and preserve the legacy service contract."""
    name = (_normalize_optional_text(_payload_value(data, "name")) or "")
    contact_email = _normalize_optional_text(_payload_value(data, "contact_email"))
    phone = _normalize_optional_text(_payload_value(data, "phone"))
    address = _normalize_optional_text(_payload_value(data, "address"))
    lead_time_value = _payload_value(data, "default_lead_time_days")
    default_lead_time_days = int(lead_time_value) if lead_time_value is not None else None

    errors: list[dict[str, str | tuple[str, ...]]] = []
    if not name:
        errors.append({"loc": ("name",), "msg": "name cannot be blank", "type": "value_error"})
    if default_lead_time_days is not None and default_lead_time_days < 0:
        errors.append(
            {
                "loc": ("default_lead_time_days",),
                "msg": "default_lead_time_days must be greater than or equal to 0",
                "type": "value_error",
            }
        )
    if errors:
        raise ValidationError(errors)

    return name, contact_email, phone, address, default_lead_time_days


async def create_supplier(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    data: "SupplierCreate",
) -> Supplier:
    """Create a new supplier."""
    from common.models.supplier import Supplier

    name, contact_email, phone, address, default_lead_time_days = _normalize_supplier_payload(data)

    supplier = Supplier(
        tenant_id=tenant_id,
        name=name,
        contact_email=contact_email,
        phone=phone,
        address=address,
        default_lead_time_days=default_lead_time_days,
        is_active=True,
    )
    session.add(supplier)
    await session.flush()
    return supplier


async def update_supplier(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    supplier_id: uuid.UUID,
    data: "SupplierUpdate",
) -> Supplier | None:
    """Update an existing supplier."""
    from common.models.supplier import Supplier

    stmt = select(Supplier).where(
        Supplier.id == supplier_id,
        Supplier.tenant_id == tenant_id,
    )
    result = await session.execute(stmt)
    supplier = result.scalar_one_or_none()
    if supplier is None:
        return None

    name, contact_email, phone, address, default_lead_time_days = _normalize_supplier_payload(data)
    supplier.name = name
    supplier.contact_email = contact_email
    supplier.phone = phone
    supplier.address = address
    supplier.default_lead_time_days = default_lead_time_days
    await session.flush()
    return supplier


async def set_supplier_status(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    supplier_id: uuid.UUID,
    *,
    is_active: bool,
) -> Supplier | None:
    """Set supplier active status."""
    from common.models.supplier import Supplier

    stmt = select(Supplier).where(
        Supplier.id == supplier_id,
        Supplier.tenant_id == tenant_id,
    )
    result = await session.execute(stmt)
    supplier = result.scalar_one_or_none()
    if supplier is None:
        return None

    supplier.is_active = is_active
    await session.flush()
    return supplier


async def create_supplier_order(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    supplier_id: uuid.UUID,
    order_date: date,
    expected_arrival_date: date | None,
    lines: list[dict],
    actor_id: str,
) -> dict:
    """Create a new supplier order with line items."""
    from common.models.supplier_order import SupplierOrder, SupplierOrderLine
    from common.time import utc_now

    # Generate order number
    order_number = f"PO-{utc_now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

    order = SupplierOrder(
        tenant_id=tenant_id,
        supplier_id=supplier_id,
        order_number=order_number,
        order_date=order_date,
        expected_arrival_date=expected_arrival_date,
        created_by=actor_id,
        status=SupplierOrderStatus.PENDING,
    )
    session.add(order)
    await session.flush()

    for line_data in lines:
        line = SupplierOrderLine(
            order_id=order.id,
            product_id=line_data["product_id"],
            warehouse_id=line_data["warehouse_id"],
            quantity_ordered=line_data["quantity_ordered"],
            unit_price=line_data.get("unit_price"),
            notes=line_data.get("notes"),
        )
        session.add(line)

    await session.flush()

    # Audit log
    audit = AuditLog(
        tenant_id=tenant_id,
        actor_id=actor_id,
        action="create_supplier_order",
        entity_type="supplier_order",
        entity_id=str(order.id),
        after_state={
            "order_number": order.order_number,
            "supplier_id": str(supplier_id),
            "status": order.status.value,
            "line_count": len(lines),
        },
        correlation_id=str(order.id),
    )
    session.add(audit)
    await session.flush()

    return await _serialize_order(session, tenant_id, order.id)


async def receive_supplier_order(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    order_id: uuid.UUID,
    *,
    received_quantities: dict[str, int] | None = None,
    received_date: date | None = None,
    actor_id: str,
) -> dict | None:
    """
    Atomically receive supplier order:
    1. Lock order and inventory rows
    2. Update inventory stock for each line
    3. Create stock adjustments (supplier_delivery)
    4. Resolve reorder alerts if stock restored
    5. Update order status
    """
    from common.events import StockChangedEvent, emit
    from common.models.supplier_order import SupplierOrder, SupplierOrderLine
    from common.time import utc_now
    from sqlalchemy.orm import selectinload

    if received_quantities is None:
        received_quantities = {}

    if received_date is None:
        received_date = date.today()

    # Lock and fetch order with lines
    order_stmt = (
        select(SupplierOrder)
        .options(selectinload(SupplierOrder.lines))
        .where(
            SupplierOrder.id == order_id,
            SupplierOrder.tenant_id == tenant_id,
        )
        .with_for_update()
    )
    order_result = await session.execute(order_stmt)
    order = order_result.scalar_one_or_none()

    if order is None:
        return None

    # Idempotency: if already fully received, return current state
    if order.status == SupplierOrderStatus.RECEIVED:
        return await _serialize_order(session, tenant_id, order_id)

    # Cannot receive cancelled orders
    if order.status == SupplierOrderStatus.CANCELLED:
        msg = "Cannot receive a cancelled order"
        raise ValueError(msg)

    # Process each line
    all_fully_received = True
    for line in order.lines:
        remaining_qty = line.quantity_ordered - line.quantity_received
        if remaining_qty <= 0:
            continue

        # Determine quantity to receive for this line
        line_id_str = str(line.id)
        if received_quantities:
            # When explicit quantities provided, only receive specified lines
            if line_id_str not in received_quantities:
                all_fully_received = False
                continue
            receive_qty = received_quantities[line_id_str]
        else:
            # When no quantities specified, receive full remaining for all lines
            receive_qty = remaining_qty

        if receive_qty <= 0:
            all_fully_received = False
            continue

        if receive_qty > remaining_qty:
            msg = (
                f"Cannot receive {receive_qty} units; "
                f"only {remaining_qty} remaining for line {line.id}"
            )
            raise ValueError(msg)

        # 1. Lock and update inventory stock
        stock_stmt = (
            select(InventoryStock)
            .where(
                InventoryStock.tenant_id == tenant_id,
                InventoryStock.product_id == line.product_id,
                InventoryStock.warehouse_id == line.warehouse_id,
            )
            .with_for_update()
        )
        stock_result = await session.execute(stock_stmt)
        stock = stock_result.scalar_one_or_none()

        if stock is None:
            stock = InventoryStock(
                tenant_id=tenant_id,
                product_id=line.product_id,
                warehouse_id=line.warehouse_id,
                quantity=0,
                reorder_point=0,
            )
            session.add(stock)
            await session.flush()

        before_qty = stock.quantity
        stock.quantity += receive_qty

        # 2. Record adjustment
        adj = StockAdjustment(
            tenant_id=tenant_id,
            product_id=line.product_id,
            warehouse_id=line.warehouse_id,
            quantity_change=receive_qty,
            reason_code=ReasonCode.SUPPLIER_DELIVERY,
            actor_id=actor_id,
            notes=f"From supplier order {order.order_number}",
        )
        session.add(adj)

        # 3. Emit stock changed event
        await emit(StockChangedEvent(
            tenant_id=tenant_id,
            product_id=line.product_id,
            warehouse_id=line.warehouse_id,
            before_quantity=before_qty,
            after_quantity=stock.quantity,
            reorder_point=stock.reorder_point,
            actor_id=actor_id,
        ), session)

        # 4. Update line
        line.quantity_received += receive_qty

        # 5. Audit log per line
        audit = AuditLog(
            tenant_id=tenant_id,
            actor_id=actor_id,
            action="receive_supplier_order_line",
            entity_type="supplier_order_line",
            entity_id=str(line.id),
            before_state={"quantity": before_qty},
            after_state={"quantity": stock.quantity},
            correlation_id=str(order_id),
            notes=f"Received {receive_qty} units; order {order.order_number}",
        )
        session.add(audit)

        # Check if this line is fully received
        if line.quantity_received < line.quantity_ordered:
            all_fully_received = False

    # Update order status
    if all_fully_received:
        order.status = SupplierOrderStatus.RECEIVED
        order.received_date = received_date
    else:
        order.status = SupplierOrderStatus.PARTIALLY_RECEIVED

    await session.flush()
    return await _serialize_order(session, tenant_id, order_id)


async def update_supplier_order_status(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    order_id: uuid.UUID,
    *,
    new_status: str,
    actor_id: str,
    notes: str | None = None,
) -> dict | None:
    """Update supplier order status (pending → confirmed → shipped, etc.)."""
    from common.models.supplier_order import SupplierOrder
    from common.models.audit_log import AuditLog

    stmt = (
        select(SupplierOrder)
        .where(
            SupplierOrder.id == order_id,
            SupplierOrder.tenant_id == tenant_id,
        )
        .with_for_update()
    )
    result = await session.execute(stmt)
    order = result.scalar_one_or_none()

    if order is None:
        return None

    # Validate status transition
    ALLOWED_TRANSITIONS: dict[SupplierOrderStatus, set[SupplierOrderStatus]] = {
        SupplierOrderStatus.PENDING: {SupplierOrderStatus.CONFIRMED, SupplierOrderStatus.CANCELLED},
        SupplierOrderStatus.CONFIRMED: {SupplierOrderStatus.SHIPPED, SupplierOrderStatus.CANCELLED},
        SupplierOrderStatus.SHIPPED: {SupplierOrderStatus.CANCELLED},
    }
    new_status_enum = SupplierOrderStatus(new_status)
    allowed = ALLOWED_TRANSITIONS.get(order.status, set())
    if new_status_enum not in allowed:
        raise ValueError(
            f"Cannot transition from {order.status.value} to {new_status}. "
            f"Allowed: {', '.join(s.value for s in allowed) or 'none'}"
        )

    old_status = order.status.value
    order.status = new_status_enum
    await session.flush()

    # Audit log
    audit = AuditLog(
        tenant_id=tenant_id,
        actor_id=actor_id,
        action="update_supplier_order_status",
        entity_type="supplier_order",
        entity_id=str(order_id),
        before_state={"status": old_status},
        after_state={"status": new_status},
        correlation_id=str(order_id),
        notes=notes,
    )
    session.add(audit)
    await session.flush()

    return await _serialize_order(session, tenant_id, order_id)
