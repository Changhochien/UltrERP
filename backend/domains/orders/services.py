"""Order domain services — create, list, get orders."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, date, datetime

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from common.errors import ValidationError as ServiceValidationError
from common.models.audit_log import AuditLog
from common.models.inventory_stock import InventoryStock
from common.models.order import Order
from common.models.order_line import OrderLine
from common.models.warehouse import Warehouse
from common.tenant import DEFAULT_TENANT_ID, set_tenant
from domains.invoices.tax import TaxPolicyCode, aggregate_invoice_totals, calculate_line_amounts
from domains.orders.schemas import (
    ALLOWED_TRANSITIONS,
    PAYMENT_TERMS_CONFIG,
    OrderCreate,
    OrderStatus,
)

logger = logging.getLogger(__name__)

TENANT_ID = DEFAULT_TENANT_ID
ACTOR_ID = str(DEFAULT_TENANT_ID)


async def check_stock_availability(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
) -> dict:
    """Return available stock per warehouse for a product."""
    stmt = (
        select(
            InventoryStock.warehouse_id,
            Warehouse.name.label("warehouse_name"),
            InventoryStock.quantity,
        )
        .join(Warehouse, InventoryStock.warehouse_id == Warehouse.id)
        .where(
            InventoryStock.tenant_id == tenant_id,
            InventoryStock.product_id == product_id,
        )
        .order_by(Warehouse.name)
    )

    async with session.begin():
        await set_tenant(session, tenant_id)
        result = await session.execute(stmt)
        rows = result.all()

    warehouses = []
    total = 0
    for row in rows:
        warehouses.append(
            {
                "warehouse_id": row.warehouse_id,
                "warehouse_name": row.warehouse_name,
                "available": row.quantity,
            }
        )
        total += row.quantity

    return {
        "product_id": product_id,
        "warehouses": warehouses,
        "total_available": total,
    }


async def create_order(
    session: AsyncSession,
    data: OrderCreate,
    tenant_id: uuid.UUID | None = None,
) -> Order:
    tid = tenant_id or TENANT_ID

    # Validate customer exists
    from domains.customers.models import Customer

    async with session.begin():
        await set_tenant(session, tid)

        result = await session.execute(
            select(Customer).where(
                Customer.id == data.customer_id,
                Customer.tenant_id == tid,
            )
        )
        customer = result.scalar_one_or_none()
        if customer is None:
            raise HTTPException(
                status_code=422,
                detail=[
                    {"field": "customer_id", "message": "Customer does not exist."},
                ],
            )

        # Validate products exist
        from common.models.product import Product

        product_ids = [line.product_id for line in data.lines]
        result = await session.execute(
            select(Product.id).where(
                Product.id.in_(product_ids),
                Product.tenant_id == tid,
            )
        )
        found_ids = {row for row in result.scalars().all()}
        missing = [str(pid) for pid in product_ids if pid not in found_ids]
        if missing:
            raise HTTPException(
                status_code=422,
                detail=[
                    {"field": "lines", "message": f"Products not found: {', '.join(missing)}"},
                ],
            )

        # Generate order number (12 hex chars ≈ 281 trillion combos/day)
        order_number = (
            f"ORD-{datetime.now(tz=UTC).strftime('%Y%m%d')}-{uuid.uuid4().hex[:12].upper()}"
        )

        # Resolve payment terms
        terms_config = PAYMENT_TERMS_CONFIG[data.payment_terms_code]

        order = Order(
            tenant_id=tid,
            customer_id=data.customer_id,
            order_number=order_number,
            status=OrderStatus.PENDING.value,
            payment_terms_code=data.payment_terms_code.value,
            payment_terms_days=int(terms_config["days"]),
            notes=data.notes,
            created_by=ACTOR_ID,
        )
        session.add(order)
        try:
            await session.flush()
        except IntegrityError:
            raise HTTPException(
                status_code=409,
                detail="Order number collision — please retry.",
            )

        # Create line items with tax calculation and stock snapshot
        line_amounts_list = []
        for idx, line_data in enumerate(data.lines, start=1):
            try:
                policy_code = TaxPolicyCode(line_data.tax_policy_code)
            except ValueError:
                raise HTTPException(
                    status_code=422,
                    detail=[
                        {
                            "field": f"lines[{idx - 1}].tax_policy_code",
                            "message": f"Invalid tax policy code: {line_data.tax_policy_code}",
                        },
                    ],
                )

            amounts = calculate_line_amounts(
                quantity=line_data.quantity,
                unit_price=line_data.unit_price,
                policy_code=policy_code,
            )
            line_amounts_list.append(amounts)

            # Stock availability snapshot (read-only, no reservation)
            stock_stmt = select(func.coalesce(func.sum(InventoryStock.quantity), 0)).where(
                InventoryStock.tenant_id == tid,
                InventoryStock.product_id == line_data.product_id,
            )
            stock_result = await session.execute(stock_stmt)
            total_available = int(stock_result.scalar())

            backorder_note = None
            if line_data.quantity > total_available:
                backorder_qty = line_data.quantity - total_available
                backorder_note = f"Backorder: {backorder_qty} units"

            order_line = OrderLine(
                tenant_id=tid,
                order_id=order.id,
                product_id=line_data.product_id,
                line_number=idx,
                quantity=line_data.quantity,
                unit_price=line_data.unit_price,
                tax_policy_code=line_data.tax_policy_code,
                tax_type=amounts.tax_type,
                tax_rate=amounts.tax_rate,
                tax_amount=amounts.tax_amount,
                subtotal_amount=amounts.subtotal,
                total_amount=amounts.total_amount,
                description=line_data.description,
                available_stock_snapshot=total_available,
                backorder_note=backorder_note,
            )
            session.add(order_line)

        await session.flush()

        # Aggregate totals
        totals = aggregate_invoice_totals(line_amounts_list)
        order.subtotal_amount = totals["subtotal_amount"]
        order.tax_amount = totals["tax_amount"]
        order.total_amount = totals["total_amount"]

        # Audit log
        audit = AuditLog(
            tenant_id=tid,
            actor_id=ACTOR_ID,
            action="ORDER_CREATED",
            entity_type="order",
            entity_id=str(order.id),
            after_state={
                "order_number": order.order_number,
                "customer_id": str(data.customer_id),
                "status": OrderStatus.PENDING.value,
                "line_count": len(data.lines),
                "total_amount": str(order.total_amount),
            },
            correlation_id=str(order.id),
        )
        session.add(audit)
        await session.flush()

    # Reload with relationships
    return await get_order(session, order.id, tid)


async def confirm_order(
    session: AsyncSession,
    order_id: uuid.UUID,
    tenant_id: uuid.UUID | None = None,
    actor_id: str = ACTOR_ID,
) -> Order:
    """Confirm an order and auto-generate an invoice atomically."""
    from domains.customers.models import Customer
    from domains.invoices.enums import BuyerType
    from domains.invoices.schemas import InvoiceCreate, InvoiceCreateLine
    from domains.invoices.service import _create_invoice_core, normalize_buyer_identifier

    tid = tenant_id or TENANT_ID

    async with session.begin():
        await set_tenant(session, tid)

        # Fetch order with lines + FOR UPDATE lock
        result = await session.execute(
            select(Order)
            .options(selectinload(Order.lines))
            .where(Order.id == order_id, Order.tenant_id == tid)
            .with_for_update()
        )
        order = result.scalar_one_or_none()
        if order is None:
            raise HTTPException(status_code=404, detail="Order not found")

        # Validate status
        if order.status != OrderStatus.PENDING.value:
            raise HTTPException(
                status_code=409,
                detail=f"Order is '{order.status}', not '{OrderStatus.PENDING.value}'",
            )

        # Validate lines
        if not order.lines:
            raise HTTPException(status_code=409, detail="Order has no line items")

        # Prevent duplicate invoice
        if order.invoice_id is not None:
            raise HTTPException(status_code=409, detail="Order already has an invoice")

        # Look up product codes for invoice lines
        from common.models.product import Product

        line_product_ids = [line.product_id for line in order.lines]
        result = await session.execute(
            select(Product.id, Product.code).where(Product.id.in_(line_product_ids))
        )
        product_code_map = {row.id: row.code for row in result.all()}

        # Validate customer
        result = await session.execute(
            select(Customer).where(
                Customer.id == order.customer_id,
                Customer.tenant_id == tid,
            )
        )
        customer = result.scalar_one_or_none()
        if customer is None:
            raise HTTPException(status_code=409, detail="Customer no longer exists")

        # Build InvoiceCreate from order
        buyer_type = BuyerType.B2B
        buyer_identifier = customer.normalized_business_number or ""
        if not buyer_identifier:
            buyer_type = BuyerType.B2C

        try:
            buyer_identifier_normalized = normalize_buyer_identifier(
                buyer_type, buyer_identifier if buyer_type == BuyerType.B2B else None
            )
        except ValueError:
            logger.warning(
                "Customer %s has invalid business_number %r; falling back to B2C",
                customer.id,
                buyer_identifier,
            )
            buyer_identifier_normalized = "0000000000"
            buyer_type = BuyerType.B2C

        invoice_data = InvoiceCreate(
            customer_id=order.customer_id,
            invoice_date=date.today(),
            buyer_type=buyer_type,
            buyer_identifier=buyer_identifier if buyer_type == BuyerType.B2B else None,
            lines=[
                InvoiceCreateLine(
                    product_id=line.product_id,
                    product_code=product_code_map.get(line.product_id),
                    description=line.description,
                    quantity=line.quantity,
                    unit_price=line.unit_price,
                    unit_cost=getattr(line, "unit_cost", None),
                    tax_policy_code=TaxPolicyCode(line.tax_policy_code),
                )
                for line in order.lines
            ],
        )

        # Create invoice within this transaction (no nested begin)
        try:
            invoice = await _create_invoice_core(
                session, invoice_data, tid, buyer_identifier_normalized
            )
        except ServiceValidationError as e:
            raise HTTPException(status_code=409, detail=e.errors)
        invoice.order_id = order.id

        # Update order
        now = datetime.now(tz=UTC)
        order.status = OrderStatus.CONFIRMED.value
        order.confirmed_at = now
        order.invoice_id = invoice.id

        # Audit logs
        order_audit = AuditLog(
            tenant_id=tid,
            actor_id=actor_id,
            action="ORDER_STATUS_CHANGED",
            entity_type="order",
            entity_id=str(order.id),
            before_state={"status": OrderStatus.PENDING.value},
            after_state={
                "status": OrderStatus.CONFIRMED.value,
                "invoice_id": str(invoice.id),
            },
            correlation_id=str(order.id),
        )
        session.add(order_audit)

        invoice_audit = AuditLog(
            tenant_id=tid,
            actor_id=actor_id,
            action="INVOICE_CREATED",
            entity_type="invoice",
            entity_id=str(invoice.id),
            after_state={
                "invoice_number": invoice.invoice_number,
                "order_id": str(order.id),
                "total_amount": str(invoice.total_amount),
            },
            correlation_id=str(order.id),
        )
        session.add(invoice_audit)
        await session.flush()

    return order


async def update_order_status(
    session: AsyncSession,
    order_id: uuid.UUID,
    new_status: str | OrderStatus,
    tenant_id: uuid.UUID | None = None,
    actor_id: str = ACTOR_ID,
) -> Order:
    """Transition order to a new status via state machine."""
    tid = tenant_id or TENANT_ID

    # Normalize to OrderStatus enum
    try:
        target = OrderStatus(new_status)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid status: {new_status}")

    # Delegate confirmed transition to confirm_order (handles invoice creation)
    if target is OrderStatus.CONFIRMED:
        return await confirm_order(session, order_id, tenant_id=tid, actor_id=actor_id)

    async with session.begin():
        await set_tenant(session, tid)

        result = await session.execute(
            select(Order)
            .where(Order.id == order_id, Order.tenant_id == tid)
            .options(selectinload(Order.lines), selectinload(Order.customer))
            .with_for_update()
        )
        order = result.scalar_one_or_none()
        if order is None:
            raise HTTPException(status_code=404, detail="Order not found")

        try:
            current = OrderStatus(order.status)
        except ValueError:
            raise HTTPException(status_code=409, detail=f"Unknown current status: {order.status}")

        if target not in ALLOWED_TRANSITIONS.get(current, frozenset()):
            raise HTTPException(
                status_code=409,
                detail=f"Cannot transition from '{order.status}' to '{target.value}'",
            )

        old_status = order.status
        order.status = target.value

        audit = AuditLog(
            tenant_id=tid,
            actor_id=actor_id,
            action="ORDER_STATUS_CHANGED",
            entity_type="order",
            entity_id=str(order.id),
            before_state={"status": old_status},
            after_state={"status": target.value},
            correlation_id=str(order.id),
        )
        session.add(audit)
        await session.flush()

    return order


async def list_orders(
    session: AsyncSession,
    tenant_id: uuid.UUID | None = None,
    *,
    status: str | None = None,
    customer_id: uuid.UUID | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Order], int]:
    tid = tenant_id or TENANT_ID

    filters = [Order.tenant_id == tid]
    if status:
        filters.append(Order.status == status)
    if customer_id:
        filters.append(Order.customer_id == customer_id)

    # Count
    count_stmt = select(func.count()).select_from(Order).where(*filters)

    # Fetch page
    offset = (page - 1) * page_size
    stmt = (
        select(Order)
        .where(*filters)
        .order_by(Order.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )

    async with session.begin():
        await set_tenant(session, tid)
        result = await session.execute(count_stmt)
        total = result.scalar() or 0
        result = await session.execute(stmt)
        orders = list(result.scalars().all())

    return orders, total


async def get_order(
    session: AsyncSession,
    order_id: uuid.UUID,
    tenant_id: uuid.UUID | None = None,
) -> Order:
    tid = tenant_id or TENANT_ID

    stmt = (
        select(Order)
        .where(Order.id == order_id, Order.tenant_id == tid)
        .options(
            selectinload(Order.lines),
            selectinload(Order.customer),
        )
    )

    async with session.begin():
        await set_tenant(session, tid)
        result = await session.execute(stmt)
        order = result.scalar_one_or_none()

    if order is None:
        raise HTTPException(status_code=404, detail="Order not found.")
    return order
