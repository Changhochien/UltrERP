"""Inventory domain service — warehouse CRUD, stock transfers."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from sqlalchemy import case, func, literal, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from common.models.audit_log import AuditLog
from common.models.inventory_stock import InventoryStock
from common.models.product import Product
from common.models.reorder_alert import AlertStatus, ReorderAlert
from common.models.stock_adjustment import ReasonCode, StockAdjustment
from common.models.stock_transfer import StockTransferHistory
from common.models.supplier import Supplier
from common.models.supplier_order import SupplierOrder, SupplierOrderLine, SupplierOrderStatus
from common.models.warehouse import Warehouse


class InsufficientStockError(Exception):
    """Raised when a transfer exceeds available stock."""

    def __init__(self, available: int = 0, requested: int = 0) -> None:
        self.available = available
        self.requested = requested
        super().__init__(
            f"Insufficient stock: available={available}, requested={requested}",
        )


class TransferValidationError(Exception):
    """Raised for invalid transfer parameters."""


# ── Warehouse queries ──────────────────────────────────────────


async def list_warehouses(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    active_only: bool = True,
) -> list[Warehouse]:
    stmt = select(Warehouse).where(Warehouse.tenant_id == tenant_id).order_by(Warehouse.name)
    if active_only:
        stmt = stmt.where(Warehouse.is_active.is_(True))
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_warehouse(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    warehouse_id: uuid.UUID,
) -> Warehouse | None:
    stmt = select(Warehouse).where(
        Warehouse.id == warehouse_id,
        Warehouse.tenant_id == tenant_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_warehouse(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    name: str,
    code: str,
    location: str | None = None,
    address: str | None = None,
    contact_email: str | None = None,
) -> Warehouse:
    warehouse = Warehouse(
        tenant_id=tenant_id,
        name=name,
        code=code,
        location=location,
        address=address,
        contact_email=contact_email,
    )
    session.add(warehouse)
    await session.flush()
    return warehouse


# ── Stock transfer ─────────────────────────────────────────────


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

    # 7. Check reorder alerts for both warehouses
    await _check_reorder_alert(
        session,
        tenant_id=tenant_id,
        product_id=product_id,
        warehouse_id=from_warehouse_id,
        current_quantity=source_stock.quantity,
        reorder_point=source_stock.reorder_point,
    )
    await _check_reorder_alert(
        session,
        tenant_id=tenant_id,
        product_id=product_id,
        warehouse_id=to_warehouse_id,
        current_quantity=target_stock.quantity,
        reorder_point=target_stock.reorder_point,
    )

    await session.flush()
    return transfer


# ── Reorder alert helper ───────────────────────────────────────


async def _check_reorder_alert(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    current_quantity: int,
    reorder_point: int,
) -> None:
    """Create or resolve reorder alert based on stock level."""
    if reorder_point <= 0:
        return

    stmt = select(ReorderAlert).where(
        ReorderAlert.tenant_id == tenant_id,
        ReorderAlert.product_id == product_id,
        ReorderAlert.warehouse_id == warehouse_id,
    )
    result = await session.execute(stmt)
    alert = result.scalar_one_or_none()

    # NOTE: Alerts trigger at <= (proactive), while is_below_reorder
    # display flag uses strict < ("at reorder point" is not "below").
    if current_quantity <= reorder_point:
        if alert is None:
            alert = ReorderAlert(
                tenant_id=tenant_id,
                product_id=product_id,
                warehouse_id=warehouse_id,
                current_stock=current_quantity,
                reorder_point=reorder_point,
                status=AlertStatus.PENDING,
            )
            session.add(alert)
        else:
            alert.current_stock = current_quantity
            if alert.status == AlertStatus.RESOLVED:
                alert.status = AlertStatus.PENDING
    elif alert is not None and alert.status != AlertStatus.RESOLVED:
        alert.status = AlertStatus.RESOLVED
        alert.current_stock = current_quantity


# ── Reorder alert queries ─────────────────────────────────────


async def list_reorder_alerts(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    status_filter: str | None = None,
    warehouse_id: uuid.UUID | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """List reorder alerts with product/warehouse names."""
    from sqlalchemy import func as sqlfunc

    base_where = [ReorderAlert.tenant_id == tenant_id]
    if status_filter:
        base_where.append(ReorderAlert.status == AlertStatus(status_filter))
    if warehouse_id:
        base_where.append(ReorderAlert.warehouse_id == warehouse_id)

    # Count
    count_stmt = select(sqlfunc.count(ReorderAlert.id)).where(*base_where)
    count_result = await session.execute(count_stmt)
    total = count_result.scalar() or 0

    # Fetch with joins
    stmt = (
        select(
            ReorderAlert.id,
            ReorderAlert.product_id,
            Product.name.label("product_name"),
            ReorderAlert.warehouse_id,
            Warehouse.name.label("warehouse_name"),
            ReorderAlert.current_stock,
            ReorderAlert.reorder_point,
            ReorderAlert.status,
            ReorderAlert.created_at,
            ReorderAlert.acknowledged_at,
            ReorderAlert.acknowledged_by,
        )
        .join(Product, ReorderAlert.product_id == Product.id)
        .join(Warehouse, ReorderAlert.warehouse_id == Warehouse.id)
        .where(*base_where)
        .order_by(ReorderAlert.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await session.execute(stmt)
    rows = result.all()

    items = [
        {
            "id": row.id,
            "product_id": row.product_id,
            "product_name": row.product_name,
            "warehouse_id": row.warehouse_id,
            "warehouse_name": row.warehouse_name,
            "current_stock": row.current_stock,
            "reorder_point": row.reorder_point,
            "status": row.status.value if hasattr(row.status, "value") else row.status,
            "created_at": row.created_at,
            "acknowledged_at": row.acknowledged_at,
            "acknowledged_by": row.acknowledged_by,
        }
        for row in rows
    ]
    return items, total


async def acknowledge_alert(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    alert_id: uuid.UUID,
    *,
    actor_id: str,
) -> dict | None:
    """Acknowledge a reorder alert."""
    stmt = select(ReorderAlert).where(
        ReorderAlert.id == alert_id,
        ReorderAlert.tenant_id == tenant_id,
    )
    result = await session.execute(stmt)
    alert = result.scalar_one_or_none()

    if alert is None:
        return None

    if alert.status == AlertStatus.RESOLVED:
        return None

    now = datetime.now(tz=UTC)
    alert.status = AlertStatus.ACKNOWLEDGED
    alert.acknowledged_at = now
    alert.acknowledged_by = actor_id
    await session.flush()

    return {
        "id": alert.id,
        "status": alert.status.value,
        "acknowledged_at": now,
        "acknowledged_by": actor_id,
    }


# ── Stock queries ──────────────────────────────────────────────


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


# ── Stock adjustment ───────────────────────────────────────────


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
    adj_created = datetime.now(tz=UTC)
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

    # 6. Check reorder alerts
    await _check_reorder_alert(
        session,
        tenant_id=tenant_id,
        product_id=product_id,
        warehouse_id=warehouse_id,
        current_quantity=stock.quantity,
        reorder_point=stock.reorder_point,
    )

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


# ── Product detail ─────────────────────────────────────────────


async def get_product_detail(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    *,
    history_limit: int = 100,
    history_offset: int = 0,
) -> dict | None:
    """Return product with per-warehouse stock info and adjustment history."""
    # 1. Fetch product
    product_stmt = select(Product).where(
        Product.id == product_id,
        Product.tenant_id == tenant_id,
    )
    product_result = await session.execute(product_stmt)
    product = product_result.scalar_one_or_none()
    if product is None:
        return None

    # 2. Fetch warehouse stocks with warehouse name and last adjustment date
    last_adj_sq = (
        select(
            StockAdjustment.warehouse_id,
            StockAdjustment.product_id,
            func.max(StockAdjustment.created_at).label("last_adjusted"),
        )
        .where(
            StockAdjustment.tenant_id == tenant_id,
            StockAdjustment.product_id == product_id,
        )
        .group_by(StockAdjustment.warehouse_id, StockAdjustment.product_id)
        .subquery()
    )

    stock_stmt = (
        select(
            InventoryStock.warehouse_id,
            Warehouse.name.label("warehouse_name"),
            InventoryStock.quantity,
            InventoryStock.reorder_point,
            last_adj_sq.c.last_adjusted,
        )
        .join(Warehouse, InventoryStock.warehouse_id == Warehouse.id)
        .outerjoin(
            last_adj_sq,
            (InventoryStock.warehouse_id == last_adj_sq.c.warehouse_id)
            & (InventoryStock.product_id == last_adj_sq.c.product_id),
        )
        .where(
            InventoryStock.tenant_id == tenant_id,
            InventoryStock.product_id == product_id,
        )
        .order_by(Warehouse.name)
    )
    stock_result = await session.execute(stock_stmt)
    stock_rows = stock_result.all()

    warehouses = []
    total_stock = 0
    for row in stock_rows:
        total_stock += row.quantity
        warehouses.append(
            {
                "warehouse_id": row.warehouse_id,
                "warehouse_name": row.warehouse_name,
                "current_stock": row.quantity,
                "reorder_point": row.reorder_point,
                "is_below_reorder": (row.reorder_point > 0 and row.quantity < row.reorder_point),
                "last_adjusted": row.last_adjusted,
            }
        )

    # 3. Fetch adjustment history with pagination
    history_stmt = (
        select(StockAdjustment)
        .where(
            StockAdjustment.tenant_id == tenant_id,
            StockAdjustment.product_id == product_id,
        )
        .order_by(StockAdjustment.created_at.desc())
        .offset(history_offset)
        .limit(history_limit)
    )
    history_result = await session.execute(history_stmt)
    adjustments = history_result.scalars().all()

    history = [
        {
            "id": adj.id,
            "created_at": adj.created_at,
            "quantity_change": adj.quantity_change,
            "reason_code": adj.reason_code.value,
            "actor_id": adj.actor_id,
            "notes": adj.notes,
        }
        for adj in adjustments
    ]

    return {
        "id": product.id,
        "code": product.code,
        "name": product.name,
        "category": product.category,
        "status": product.status,
        "total_stock": total_stock,
        "warehouses": warehouses,
        "adjustment_history": history,
    }


# ── Product search ─────────────────────────────────────────────


async def search_products(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    query: str,
    *,
    warehouse_id: uuid.UUID | None = None,
    limit: int = 20,
) -> list[dict]:
    """Hybrid search: exact/prefix code → trigram → tsvector ranking."""
    q = query.strip()

    # Escape LIKE wildcards to prevent pattern injection
    q_like = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

    # Relevance scoring via CASE + trigram + tsvector
    exact_code = case(
        (func.lower(Product.code) == func.lower(q), literal(10.0)),
        else_=literal(0.0),
    )
    prefix_code = case(
        (Product.code.ilike(q_like + "%"), literal(5.0)),
        else_=literal(0.0),
    )
    trgm_score = func.similarity(Product.name, q)
    ts_rank_score = func.coalesce(
        func.ts_rank(
            Product.search_vector,
            func.plainto_tsquery("simple", q),
        ),
        literal(0.0),
    )
    code_trgm = func.similarity(Product.code, q)
    relevance = exact_code + prefix_code + trgm_score + ts_rank_score + code_trgm

    # Stock aggregation subquery
    stock_sq = select(
        InventoryStock.product_id,
        func.coalesce(func.sum(InventoryStock.quantity), 0).label(
            "total_stock",
        ),
    ).where(InventoryStock.tenant_id == tenant_id)
    if warehouse_id is not None:
        stock_sq = stock_sq.where(
            InventoryStock.warehouse_id == warehouse_id,
        )
    stock_sq = stock_sq.group_by(InventoryStock.product_id).subquery()

    # Main query
    stmt = (
        select(
            Product.id,
            Product.code,
            Product.name,
            Product.category,
            Product.status,
            func.coalesce(stock_sq.c.total_stock, 0).label("current_stock"),
            relevance.label("relevance"),
        )
        .outerjoin(stock_sq, Product.id == stock_sq.c.product_id)
        .where(Product.tenant_id == tenant_id)
        .where(
            (func.lower(Product.code) == func.lower(q))
            | (Product.code.ilike(q_like + "%"))
            | (func.similarity(Product.name, q) > 0.1)
            | (func.similarity(Product.code, q) > 0.1)
            | (
                Product.search_vector.op("@@")(
                    func.plainto_tsquery("simple", q),
                )
            )
        )
        .order_by(relevance.desc(), Product.code)
        .limit(limit)
    )

    result = await session.execute(stmt)
    rows = result.all()
    return [
        {
            "id": row.id,
            "code": row.code,
            "name": row.name,
            "category": row.category,
            "status": row.status,
            "current_stock": row.current_stock,
            "relevance": float(row.relevance),
        }
        for row in rows
    ]


# ── Supplier queries ──────────────────────────────────────────


async def list_suppliers(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    active_only: bool = True,
) -> list[dict]:
    """List suppliers with optional active filter."""
    stmt = select(Supplier).where(Supplier.tenant_id == tenant_id)
    if active_only:
        stmt = stmt.where(Supplier.is_active.is_(True))
    stmt = stmt.order_by(Supplier.name)

    result = await session.execute(stmt)
    suppliers = result.scalars().all()
    return [
        {
            "id": s.id,
            "tenant_id": s.tenant_id,
            "name": s.name,
            "contact_email": s.contact_email,
            "phone": s.phone,
            "address": s.address,
            "default_lead_time_days": s.default_lead_time_days,
            "is_active": s.is_active,
            "created_at": s.created_at,
        }
        for s in suppliers
    ]


# ── Supplier order creation ────────────────────────────────────


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
    # Generate order number
    order_number = f"PO-{datetime.now(tz=UTC).strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

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


# ── Supplier order queries ─────────────────────────────────────


async def _serialize_order(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    order_id: uuid.UUID,
) -> dict | None:
    """Fetch and serialize a supplier order with eager-loaded lines."""
    from sqlalchemy.orm import selectinload

    stmt = (
        select(SupplierOrder)
        .options(selectinload(SupplierOrder.lines))
        .where(
            SupplierOrder.id == order_id,
            SupplierOrder.tenant_id == tenant_id,
        )
    )
    result = await session.execute(stmt)
    order = result.scalar_one_or_none()

    if order is None:
        return None

    # Fetch supplier name
    supplier_stmt = select(Supplier.name).where(Supplier.id == order.supplier_id)
    supplier_result = await session.execute(supplier_stmt)
    supplier_name = supplier_result.scalar_one_or_none() or "Unknown"

    return {
        "id": order.id,
        "tenant_id": order.tenant_id,
        "supplier_id": order.supplier_id,
        "supplier_name": supplier_name,
        "order_number": order.order_number,
        "status": order.status.value,
        "order_date": order.order_date,
        "expected_arrival_date": order.expected_arrival_date,
        "received_date": order.received_date,
        "created_by": order.created_by,
        "created_at": order.created_at,
        "updated_at": order.updated_at,
        "lines": [
            {
                "id": line.id,
                "product_id": line.product_id,
                "warehouse_id": line.warehouse_id,
                "quantity_ordered": line.quantity_ordered,
                "quantity_received": line.quantity_received,
                "notes": line.notes,
            }
            for line in order.lines
        ],
    }


async def get_supplier_order(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    order_id: uuid.UUID,
) -> dict | None:
    """Fetch supplier order with line items."""
    return await _serialize_order(session, tenant_id, order_id)


async def list_supplier_orders(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    status_filter: str | None = None,
    supplier_id: uuid.UUID | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """List supplier orders with optional filters."""
    from sqlalchemy.orm import selectinload

    base_where = [SupplierOrder.tenant_id == tenant_id]
    if status_filter:
        base_where.append(SupplierOrder.status == SupplierOrderStatus(status_filter))
    if supplier_id:
        base_where.append(SupplierOrder.supplier_id == supplier_id)

    # Count
    count_stmt = select(func.count(SupplierOrder.id)).where(*base_where)
    count_result = await session.execute(count_stmt)
    total = count_result.scalar() or 0

    # Fetch with pagination
    stmt = (
        select(SupplierOrder)
        .options(selectinload(SupplierOrder.lines))
        .where(*base_where)
        .order_by(SupplierOrder.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await session.execute(stmt)
    orders = result.scalars().unique().all()

    # Batch-fetch supplier names
    supplier_ids = {o.supplier_id for o in orders}
    if supplier_ids:
        name_stmt = select(Supplier.id, Supplier.name).where(Supplier.id.in_(supplier_ids))
        name_result = await session.execute(name_stmt)
        supplier_names = {row[0]: row[1] for row in name_result.all()}
    else:
        supplier_names = {}

    items = [
        {
            "id": order.id,
            "supplier_id": order.supplier_id,
            "supplier_name": supplier_names.get(order.supplier_id, "Unknown"),
            "order_number": order.order_number,
            "status": order.status.value,
            "order_date": order.order_date,
            "expected_arrival_date": order.expected_arrival_date,
            "received_date": order.received_date,
            "created_by": order.created_by,
            "created_at": order.created_at,
            "updated_at": order.updated_at,
            "line_count": len(order.lines),
        }
        for order in orders
    ]

    return items, total


# ── Supplier order receipt (atomic) ────────────────────────────


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

        # 3. Resolve reorder alert if stock now sufficient
        await _check_reorder_alert(
            session,
            tenant_id=tenant_id,
            product_id=line.product_id,
            warehouse_id=line.warehouse_id,
            current_quantity=stock.quantity,
            reorder_point=stock.reorder_point,
        )

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


# ── Supplier order status update ──────────────────────────────


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
