"""Inventory domain service — warehouse CRUD, stock transfers."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import and_, asc, case, desc, distinct, func, literal, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from common.errors import DuplicateProductCodeError, ValidationError
from common.events import StockChangedEvent, emit
from common.models.audit_log import AuditLog
from common.models.inventory_stock import InventoryStock
from common.models.product import Product
from common.models.reorder_alert import AlertStatus, ReorderAlert
from common.models.stock_adjustment import ReasonCode, StockAdjustment
from common.models.stock_transfer import StockTransferHistory
from common.models.supplier import Supplier
from common.models.supplier_invoice import SupplierInvoice, SupplierInvoiceLine
from common.models.supplier_order import SupplierOrder, SupplierOrderLine, SupplierOrderStatus
from common.models.warehouse import Warehouse
from common.time import today, utc_now
from domains.product_analytics.service import read_sales_monthly_range


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


_PLANNING_QUANTITY_QUANT = Decimal("0.001")
_PLANNING_INDEX_QUANT = Decimal("0.001")
_ZERO_QUANTITY = Decimal("0.000")


def _shift_months(value: date, months: int) -> date:
    month_index = (value.year * 12 + value.month - 1) + months
    year = month_index // 12
    month = month_index % 12 + 1
    return date(year, month, 1)


def _iter_month_starts(start_month: date, end_month: date) -> list[date]:
    month_starts: list[date] = []
    cursor = start_month
    while cursor <= end_month:
        month_starts.append(cursor)
        cursor = _shift_months(cursor, 1)
    return month_starts


def _format_month(month_start: date) -> str:
    return month_start.strftime("%Y-%m")


def _quantize_quantity(value: Decimal | int | float | None) -> Decimal:
    return Decimal(str(value or "0")).quantize(_PLANNING_QUANTITY_QUANT, rounding=ROUND_HALF_UP)


def _quantize_index(value: Decimal) -> Decimal:
    return value.quantize(_PLANNING_INDEX_QUANT, rounding=ROUND_HALF_UP)


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


def _normalize_optional_product_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _normalize_product_payload(
    data: object,
) -> tuple[str, str, str | None, str | None, str]:
    code = str(getattr(data, "code", "")).strip()
    name = str(getattr(data, "name", "")).strip()
    unit = str(getattr(data, "unit", "")).strip()
    category = _normalize_optional_product_text(getattr(data, "category", None))
    description = _normalize_optional_product_text(getattr(data, "description", None))

    errors: list[dict[str, str | tuple[str, ...]]] = []
    if not code:
        errors.append({"loc": ("code",), "msg": "code cannot be blank", "type": "value_error"})
    if not name:
        errors.append({"loc": ("name",), "msg": "name cannot be blank", "type": "value_error"})
    if not unit:
        errors.append({"loc": ("unit",), "msg": "unit cannot be blank", "type": "value_error"})
    if errors:
        raise ValidationError(errors)

    return code, name, category, description, unit


async def _find_product_by_code(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    code: str,
    *,
    exclude_product_id: uuid.UUID | None = None,
) -> Product | None:
    stmt = select(Product).where(
        Product.tenant_id == tenant_id,
        func.lower(Product.code) == code.lower(),
    )
    if exclude_product_id is not None:
        stmt = stmt.where(Product.id != exclude_product_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


# ── Product creation ───────────────────────────────────────────


async def create_product(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    data: "ProductCreate",
) -> Product:
    """Create a new product for a tenant."""
    code, name, category, description, unit = _normalize_product_payload(data)

    # Check for duplicate code within tenant
    row = await _find_product_by_code(session, tenant_id, code)
    if row is not None:
        raise DuplicateProductCodeError(existing_id=row.id, existing_code=row.code)

    product = Product(
        tenant_id=tenant_id,
        code=code,
        name=name,
        category=category,
        description=description,
        unit=unit,
        status="active",
        search_vector=func.to_tsvector("simple", name + " " + code),
    )
    try:
        session.add(product)
        await session.flush()
    except IntegrityError:
        await session.rollback()
        # Race condition: another request inserted the same code between our
        # pre-check and insert. Query for the conflicting product and raise
        # DuplicateProductCodeError so the route returns a proper 409.
        existing = await _find_product_by_code(session, tenant_id, code)
        if existing is not None:
            raise DuplicateProductCodeError(existing_id=existing.id, existing_code=existing.code)
        raise
    return product


async def update_product(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    data: "ProductUpdate",
) -> Product | None:
    """Update an existing product for a tenant."""
    code, name, category, description, unit = _normalize_product_payload(data)

    stmt = select(Product).where(
        Product.id == product_id,
        Product.tenant_id == tenant_id,
    )
    result = await session.execute(stmt)
    product = result.scalar_one_or_none()
    if product is None:
        return None

    existing = await _find_product_by_code(
        session,
        tenant_id,
        code,
        exclude_product_id=product.id,
    )
    if existing is not None:
        raise DuplicateProductCodeError(existing_id=existing.id, existing_code=existing.code)

    code_or_name_changed = product.code != code or product.name != name
    product.code = code
    product.name = name
    product.category = category
    product.description = description
    product.unit = unit
    if code_or_name_changed:
        product.search_vector = func.to_tsvector("simple", name + " " + code)

    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        existing = await _find_product_by_code(
            session,
            tenant_id,
            code,
            exclude_product_id=product_id,
        )
        if existing is not None:
            raise DuplicateProductCodeError(existing_id=existing.id, existing_code=existing.code)
        raise

    return product


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


# ── Reorder alert helper ───────────────────────────────────────


def _compute_severity(current_stock: int, reorder_point: int) -> str:
    """Compute alert severity based on stock level."""
    if current_stock == 0:
        return "CRITICAL"
    if reorder_point > 0 and current_stock < reorder_point * 0.25:
        return "CRITICAL"
    if current_stock < reorder_point:
        return "WARNING"
    return "INFO"


def _release_expired_snooze(alert: ReorderAlert, *, now) -> None:
    if (
        alert.status == AlertStatus.SNOOZED
        and alert.snoozed_until is not None
        and alert.snoozed_until <= now
    ):
        alert.status = AlertStatus.PENDING
        alert.snoozed_until = None
        alert.snoozed_by = None


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

    now = utc_now()

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
        severity = _compute_severity(current_quantity, reorder_point)
        if alert is None:
            alert = ReorderAlert(
                tenant_id=tenant_id,
                product_id=product_id,
                warehouse_id=warehouse_id,
                current_stock=current_quantity,
                reorder_point=reorder_point,
                status=AlertStatus.PENDING,
                severity=severity,
            )
            session.add(alert)
        else:
            previous_stock = alert.current_stock
            _release_expired_snooze(alert, now=now)
            alert.current_stock = current_quantity
            alert.severity = severity
            # Only collapse RESOLVED → PENDING; preserve ACKNOWLEDGED
            if alert.status == AlertStatus.RESOLVED:
                alert.status = AlertStatus.PENDING
            elif alert.status == AlertStatus.DISMISSED and previous_stock > reorder_point:
                alert.status = AlertStatus.PENDING
                alert.dismissed_at = None
                alert.dismissed_by = None
            # ACKNOWLEDGED stays acknowledged — do not demote
    elif alert is not None:
        _release_expired_snooze(alert, now=now)
        alert.current_stock = current_quantity
        if alert.status in {AlertStatus.PENDING, AlertStatus.SNOOZED}:
            # Only active alerts auto-resolve when stock is restored.
            # ACKNOWLEDGED alerts require explicit resolution or a real supplier delivery.
            alert.status = AlertStatus.RESOLVED
            alert.snoozed_until = None
            alert.snoozed_by = None
    # If alert is ACKNOWLEDGED and stock is above threshold: do nothing (keep acknowledged)


# ── Reorder alert queries ─────────────────────────────────────


async def list_reorder_alerts(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    status_filter: str | None = None,
    warehouse_id: uuid.UUID | None = None,
    sort_by: str = "severity",
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """List reorder alerts with product/warehouse names."""
    from sqlalchemy import func as sqlfunc

    now = utc_now()

    base_where = [ReorderAlert.tenant_id == tenant_id]
    if status_filter:
        if status_filter == AlertStatus.PENDING.value:
            base_where.append(
                or_(
                    ReorderAlert.status == AlertStatus.PENDING,
                    and_(
                        ReorderAlert.status == AlertStatus.SNOOZED,
                        ReorderAlert.snoozed_until.is_not(None),
                        ReorderAlert.snoozed_until <= now,
                    ),
                )
            )
        elif status_filter == AlertStatus.SNOOZED.value:
            base_where.append(ReorderAlert.status == AlertStatus.SNOOZED)
            base_where.append(
                or_(
                    ReorderAlert.snoozed_until.is_(None),
                    ReorderAlert.snoozed_until > now,
                )
            )
        else:
            base_where.append(ReorderAlert.status == AlertStatus(status_filter))
    if warehouse_id:
        base_where.append(ReorderAlert.warehouse_id == warehouse_id)

    # Count
    count_stmt = select(sqlfunc.count(ReorderAlert.id)).where(*base_where)
    count_result = await session.execute(count_stmt)
    total = count_result.scalar() or 0

    # Days-until-stockout expression: current_stock / GREATEST(avg_daily_usage_estimate, 0.001)
    # avg_daily_usage_estimate = reorder_point / 14 (2-week lead time at 0.5 safety factor proxy)
    days_until_stockout = ReorderAlert.current_stock / func.greatest(
        ReorderAlert.reorder_point / 14.0, 0.001,
    )

    # Severity tier ordering: CRITICAL=1, WARNING=2, INFO=3
    severity_order = case(
        (ReorderAlert.severity == "CRITICAL", 1),
        (ReorderAlert.severity == "WARNING", 2),
        else_=3,
    )

    # Apply sort
    if sort_by == "created_at":
        order_col = ReorderAlert.created_at.desc()
    elif sort_by == "current_stock":
        order_col = ReorderAlert.current_stock.asc()
    else:
        # Default: severity tier, then days_until_stockout ascending (most urgent first)
        order_col = [severity_order.asc(), days_until_stockout.asc()]

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
            ReorderAlert.severity,
            ReorderAlert.created_at,
            ReorderAlert.acknowledged_at,
            ReorderAlert.acknowledged_by,
            ReorderAlert.snoozed_until,
            ReorderAlert.snoozed_by,
            ReorderAlert.dismissed_at,
            ReorderAlert.dismissed_by,
        )
        .join(Product, ReorderAlert.product_id == Product.id)
        .join(Warehouse, ReorderAlert.warehouse_id == Warehouse.id)
        .where(*base_where)
        .order_by(*order_col if isinstance(order_col, list) else (order_col,))
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
            "status": (
                AlertStatus.PENDING.value
                if (
                    row.status == AlertStatus.SNOOZED
                    and row.snoozed_until is not None
                    and row.snoozed_until <= now
                )
                else (row.status.value if hasattr(row.status, "value") else row.status)
            ),
            "severity": row.severity,
            "created_at": row.created_at,
            "acknowledged_at": row.acknowledged_at,
            "acknowledged_by": row.acknowledged_by,
            "snoozed_until": row.snoozed_until,
            "snoozed_by": row.snoozed_by,
            "dismissed_at": row.dismissed_at,
            "dismissed_by": row.dismissed_by,
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

    _release_expired_snooze(alert, now=utc_now())

    if alert.status in {AlertStatus.RESOLVED, AlertStatus.DISMISSED}:
        return None

    now = utc_now()
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


async def snooze_alert(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    alert_id: uuid.UUID,
    *,
    actor_id: str,
    duration_minutes: int,
) -> dict | None:
    """Snooze a reorder alert for the requested duration."""
    stmt = select(ReorderAlert).where(
        ReorderAlert.id == alert_id,
        ReorderAlert.tenant_id == tenant_id,
    )
    result = await session.execute(stmt)
    alert = result.scalar_one_or_none()

    if alert is None:
        return None

    _release_expired_snooze(alert, now=utc_now())

    if alert.status in {AlertStatus.RESOLVED, AlertStatus.DISMISSED}:
        return None

    now = utc_now()
    snoozed_until = now + timedelta(minutes=duration_minutes)
    alert.status = AlertStatus.SNOOZED
    alert.snoozed_until = snoozed_until
    alert.snoozed_by = actor_id
    await session.flush()

    return {
        "id": alert.id,
        "status": alert.status.value,
        "snoozed_until": snoozed_until,
        "snoozed_by": actor_id,
    }


async def dismiss_alert(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    alert_id: uuid.UUID,
    *,
    actor_id: str,
) -> dict | None:
    """Dismiss a reorder alert until stock recovers and breaches again."""
    stmt = select(ReorderAlert).where(
        ReorderAlert.id == alert_id,
        ReorderAlert.tenant_id == tenant_id,
    )
    result = await session.execute(stmt)
    alert = result.scalar_one_or_none()

    if alert is None:
        return None

    _release_expired_snooze(alert, now=utc_now())

    if alert.status in {AlertStatus.RESOLVED, AlertStatus.DISMISSED}:
        return None

    now = utc_now()
    alert.status = AlertStatus.DISMISSED
    alert.dismissed_at = now
    alert.dismissed_by = actor_id
    alert.snoozed_until = None
    alert.snoozed_by = None
    await session.flush()

    return {
        "id": alert.id,
        "status": alert.status.value,
        "dismissed_at": now,
        "dismissed_by": actor_id,
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
            InventoryStock.id.label("stock_id"),
            InventoryStock.warehouse_id,
            Warehouse.name.label("warehouse_name"),
            InventoryStock.quantity,
            InventoryStock.reorder_point,
            InventoryStock.safety_factor,
            InventoryStock.lead_time_days,
            InventoryStock.policy_type,
            InventoryStock.target_stock_qty,
            InventoryStock.on_order_qty,
            InventoryStock.in_transit_qty,
            InventoryStock.reserved_qty,
            InventoryStock.planning_horizon_days,
            InventoryStock.review_cycle_days,
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
                "stock_id": row.stock_id,
                "warehouse_id": row.warehouse_id,
                "warehouse_name": row.warehouse_name,
                "current_stock": row.quantity,
                "reorder_point": row.reorder_point,
                "safety_factor": row.safety_factor,
                "lead_time_days": row.lead_time_days,
                "policy_type": row.policy_type,
                "target_stock_qty": row.target_stock_qty,
                "on_order_qty": row.on_order_qty,
                "in_transit_qty": row.in_transit_qty,
                "reserved_qty": row.reserved_qty,
                "planning_horizon_days": row.planning_horizon_days,
                "review_cycle_days": row.review_cycle_days,
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
        "description": product.description,
        "unit": product.unit,
        "status": product.status,
        "legacy_master_snapshot": getattr(product, "legacy_master_snapshot", None),
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
    offset: int = 0,
    sort_by: str = "code",
    sort_dir: str = "asc",
) -> tuple[list[dict], int]:
    """Hybrid search: exact/prefix code → trigram → tsvector ranking."""
    q = query.strip()
    search_query = func.plainto_tsquery("simple", q) if q else None

    # Escape LIKE wildcards to prevent pattern injection
    q_like = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

    exact_code_match = func.lower(Product.code) == func.lower(q)
    prefix_code_match = Product.code.ilike(q_like + "%", escape="\\")
    name_prefix_match = Product.name.ilike(q_like + "%", escape="\\")
    name_contains_match = Product.name.ilike("%" + q_like + "%", escape="\\")
    text_search_match = (
        Product.search_vector.op("@@")(search_query) if search_query is not None else None
    )

    # Relevance scoring via CASE + trigram + tsvector
    exact_code = case(
        (exact_code_match, literal(10.0)),
        else_=literal(0.0),
    )
    prefix_code = case(
        (prefix_code_match, literal(5.0)),
        else_=literal(0.0),
    )
    trgm_score = func.similarity(Product.name, q)
    ts_rank_score = func.coalesce(
        func.ts_rank(
            Product.search_vector,
            search_query,
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
    )

    def build_broader_conditions():
        return (
            fast_match
            | name_contains_match
            | text_search_match
            | (relevance >= literal(0.35))
        )

    def apply_pagination(s, limit_val, offset_val):
        return s.limit(limit_val).offset(offset_val)

    def apply_order_by(s):
        """Apply user sort; fall back to code for tie-breaking."""
        dir_fn = desc if sort_dir == "desc" else asc
        if sort_by == "name":
            return s.order_by(dir_fn(Product.name), asc(Product.code))
        elif sort_by == "current_stock":
            return s.order_by(dir_fn(text("current_stock")), asc(Product.code))
        elif sort_by == "category":
            return s.order_by(dir_fn(Product.category), asc(Product.code))
        elif sort_by == "status":
            return s.order_by(dir_fn(Product.status), asc(Product.code))
        else:
            return s.order_by(dir_fn(Product.code))

    if q:
        # Phase 1: fast B-tree-indexed matches only.
        fast_match = (
            exact_code_match
            | prefix_code_match
            | name_prefix_match
        )
        fast_stmt = apply_pagination(
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
            .where(fast_match)
            .order_by(relevance.desc(), Product.code),
            limit,
            offset,
        )
        fast_result = await session.execute(apply_order_by(fast_stmt))
        fast_rows = fast_result.all()

        # Phase 2: only compute trigram/tsvector if fast results are insufficient.
        if len(fast_rows) < limit:
            broader_stmt = apply_pagination(
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
                .where(build_broader_conditions()),
                limit,
                offset,
            )
            broader_result = await session.execute(apply_order_by(broader_stmt))
            seen_ids = {row.id for row in fast_rows}
            rows = fast_rows + [
                row for row in broader_result.all() if row.id not in seen_ids
            ]
        else:
            rows = fast_rows

        # Total count: count distinct products matching the broader conditions
        count_stmt = select(func.count(distinct(Product.id))).select_from(
            Product
        ).outerjoin(stock_sq, Product.id == stock_sq.c.product_id).where(
            Product.tenant_id == tenant_id
        ).where(build_broader_conditions())
        total_result = await session.execute(count_stmt)
        total = total_result.scalar() or 0
    else:
        base_conditions = [Product.tenant_id == tenant_id]
        count_sq = select(
            InventoryStock.product_id,
        ).where(InventoryStock.tenant_id == tenant_id)
        if warehouse_id is not None:
            count_sq = count_sq.where(InventoryStock.warehouse_id == warehouse_id)
        count_sq = count_sq.subquery()
        count_stmt = (
            select(func.count(distinct(Product.id)))
            .select_from(Product)
            .outerjoin(count_sq, Product.id == count_sq.c.product_id)
            .where(*base_conditions)
        )
        total_result = await session.execute(count_stmt)
        total = total_result.scalar() or 0

        rows_stmt = apply_pagination(
            apply_order_by(stmt.where(Product.tenant_id == tenant_id)),
            limit,
            offset,
        )
        result = await session.execute(rows_stmt)
        rows = result.all()

    serialized = [
        {
            "id": row.id,
            "code": row.code,
            "name": row.name,
            "category": row.category,
            "status": row.status,
            "current_stock": row.current_stock,
            "relevance": float(row.relevance) if row.relevance is not None else 0.0,
        }
        for row in rows
    ]
    return serialized, total


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
            "legacy_master_snapshot": getattr(s, "legacy_master_snapshot", None),
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
                "unit_price": getattr(line, "unit_price", None),
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
        received_date = today()

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


# ── Stock history ───────────────────────────────────────────────


async def get_stock_history(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    *,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    granularity: str = "event",
    _max_range_days: int = 730,
) -> dict:
    """Return stock history for a product+warehouse.

    - ``granularity='event'``: one row per adjustment event
    - ``granularity='daily'``: one row per day, aggregated

    ``running_stock`` at each point is computed by back-calculating the
    initial stock from the current quantity and applying adjustments forward.
    """
    from collections import Counter

    from common.time import utc_now

    # Cap start_date to at most _max_range_days ago to avoid loading huge histories
    effective_start = start_date
    if effective_start is None:
        effective_start = utc_now() - __import__("datetime").timedelta(days=_max_range_days)

    # 1. Get current stock quantity and reorder point
    stock_stmt = select(InventoryStock).where(
        InventoryStock.tenant_id == tenant_id,
        InventoryStock.product_id == product_id,
        InventoryStock.warehouse_id == warehouse_id,
    )
    stock_result = await session.execute(stock_stmt)
    stock = stock_result.scalar_one_or_none()

    current_stock = stock.quantity if stock else 0
    reorder_point = stock.reorder_point if stock else 0
    configured_safety_factor = stock.safety_factor if stock and stock.safety_factor > 0 else 0.5
    configured_lead_time_days = stock.lead_time_days if stock and stock.lead_time_days > 0 else None

    # 2. Fetch adjustments ordered ASC
    adj_where = [
        StockAdjustment.tenant_id == tenant_id,
        StockAdjustment.product_id == product_id,
        StockAdjustment.warehouse_id == warehouse_id,
    ]
    if effective_start:
        adj_where.append(StockAdjustment.created_at >= effective_start)
    if end_date:
        adj_where.append(StockAdjustment.created_at <= end_date)

    adj_stmt = (
        select(StockAdjustment)
        .where(*adj_where)
        .order_by(StockAdjustment.created_at.asc())
    )
    adj_result = await session.execute(adj_stmt)
    adjustments = list(adj_result.scalars().all())

    total_adjustment = sum(adj.quantity_change for adj in adjustments)
    initial_stock = current_stock - total_adjustment

    # 3. Build running stock
    running = initial_stock
    points: list[dict] = []

    if granularity == "daily":
        # Group by date, sum quantity_change, pick dominant reason_code
        by_date: dict[str, dict] = {}
        for adj in adjustments:
            day_key = adj.created_at.date().isoformat()
            if day_key not in by_date:
                by_date[day_key] = {"quantity_change": 0, "reason_codes": Counter(), "notes": None}
            by_date[day_key]["quantity_change"] += adj.quantity_change
            by_date[day_key]["reason_codes"][adj.reason_code.value] += 1
            if by_date[day_key]["notes"] is None and adj.notes:
                by_date[day_key]["notes"] = adj.notes

        for day_key, info in sorted(by_date.items()):
            running += info["quantity_change"]
            dominant_rc = (
                info["reason_codes"].most_common(1)[0][0]
                if info["reason_codes"]
                else "unknown"
            )
            points.append({
                "date": datetime.fromisoformat(day_key),
                "quantity_change": info["quantity_change"],
                "reason_code": dominant_rc,
                "running_stock": running,
                "notes": info["notes"],
            })
    else:
        # event-level granularity
        for adj in adjustments:
            running += adj.quantity_change
            points.append({
                "date": adj.created_at,
                "quantity_change": adj.quantity_change,
                "reason_code": adj.reason_code.value,
                "running_stock": running,
                "notes": adj.notes,
            })

    # 4. Fetch metadata from reorder point helpers (avg_daily_usage, lead_time, safety_stock)
    try:
        from domains.inventory.reorder_point import (
            get_average_daily_usage,
            get_lead_time_days,
        )

        avg_daily, _mov_count = await get_average_daily_usage(
            session, tenant_id, product_id, warehouse_id, lookback_days=90,
        )
        if configured_lead_time_days is not None:
            lead_time_days = configured_lead_time_days
        else:
            lead_time_days, _lt_source = await get_lead_time_days(
                session, tenant_id, product_id, warehouse_id, lookback_days=180,
            )
        safety_stock = (
            round(avg_daily * configured_safety_factor * lead_time_days, 2)
            if avg_daily and lead_time_days
            else None
        )
    except Exception:
        avg_daily = None
        lead_time_days = None
        safety_stock = None

    return {
        "points": points,
        "current_stock": current_stock,
        "reorder_point": reorder_point,
        "avg_daily_usage": round(avg_daily, 4) if avg_daily else None,
        "lead_time_days": lead_time_days,
        "safety_stock": safety_stock,
    }


# ── Stock settings update ───────────────────────────────────────


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


# ── Monthly demand ──────────────────────────────────────────────


async def get_monthly_demand(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
) -> dict:
    """Return 12-month rolling monthly totals for sales_reservation reason code."""
    twelve_months_ago = utc_now().replace(day=1) - __import__("datetime").timedelta(days=365)

    month_expr = func.date_trunc("month", StockAdjustment.created_at).label("month")
    stmt = (
        select(
            month_expr,
            func.sum(StockAdjustment.quantity_change).label("total_qty"),
        )
        .where(
            StockAdjustment.tenant_id == tenant_id,
            StockAdjustment.product_id == product_id,
            StockAdjustment.reason_code == ReasonCode.SALES_RESERVATION,
            StockAdjustment.created_at >= twelve_months_ago,
        )
        .group_by(month_expr)
        .order_by(month_expr)
    )
    result = await session.execute(stmt)
    rows = result.all()

    items = [
        {
            "month": row.month.strftime("%Y-%m"),
            "total_qty": int(row.total_qty or 0),
        }
        for row in rows
    ]
    total = sum(item["total_qty"] for item in items)
    return {"items": items, "total": total}


async def get_planning_support(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    *,
    months: int = 12,
    include_current_month: bool = True,
) -> dict | None:
    current_month_start = utc_now().date().replace(day=1)
    end_month = current_month_start if include_current_month else _shift_months(current_month_start, -1)
    start_month = _shift_months(end_month, -(months - 1))
    requested_months = _iter_month_starts(start_month, end_month)
    includes_current_month = include_current_month and current_month_start in requested_months

    monthly_result = await read_sales_monthly_range(
        session,
        tenant_id,
        start_month=start_month,
        end_month=end_month,
    )
    monthly_points = {
        item.month_start: item
        for item in monthly_result.items
        if item.product_id == product_id
    }

    product_exists = await session.scalar(
        select(Product.id).where(
            Product.id == product_id,
            Product.tenant_id == tenant_id,
        )
    )
    if product_exists is None:
        return None

    stock_context_row = (
        await session.execute(
            select(
                func.coalesce(func.sum(InventoryStock.reorder_point), 0).label("reorder_point"),
                func.coalesce(func.sum(InventoryStock.on_order_qty), 0).label("on_order_qty"),
                func.coalesce(func.sum(InventoryStock.in_transit_qty), 0).label("in_transit_qty"),
                func.coalesce(func.sum(InventoryStock.reserved_qty), 0).label("reserved_qty"),
            ).where(
                InventoryStock.tenant_id == tenant_id,
                InventoryStock.product_id == product_id,
            )
        )
    ).one()

    current_month_live_quantity = None
    if includes_current_month:
        current_month_live_quantity = _ZERO_QUANTITY
        current_month_point = monthly_points.get(current_month_start)
        if current_month_point is not None:
            current_month_live_quantity = _quantize_quantity(current_month_point.quantity_sold)

    if not monthly_points:
        return {
            "product_id": product_id,
            "items": [],
            "avg_monthly_quantity": None,
            "peak_monthly_quantity": None,
            "low_monthly_quantity": None,
            "seasonality_index": None,
            "above_average_months": [],
            "history_months_used": 0,
            "current_month_live_quantity": current_month_live_quantity,
            "reorder_point": int(stock_context_row.reorder_point or 0),
            "on_order_qty": int(stock_context_row.on_order_qty or 0),
            "in_transit_qty": int(stock_context_row.in_transit_qty or 0),
            "reserved_qty": int(stock_context_row.reserved_qty or 0),
            "data_basis": "no_history",
            "advisory_only": True,
            "data_gap": True,
            "window": {
                "start_month": _format_month(start_month),
                "end_month": _format_month(end_month),
                "includes_current_month": includes_current_month,
                "is_partial": includes_current_month,
            },
        }

    items: list[dict[str, object]] = []
    for month_start in requested_months:
        point = monthly_points.get(month_start)
        quantity = _quantize_quantity(point.quantity_sold if point is not None else _ZERO_QUANTITY)
        items.append(
            {
                "month": _format_month(month_start),
                "quantity": quantity,
                "source": "live" if month_start == current_month_start and includes_current_month else "aggregated",
            }
        )

    quantities = [item["quantity"] for item in items]
    total_quantity = sum(quantities, start=_ZERO_QUANTITY)
    avg_monthly_quantity = _quantize_quantity(total_quantity / Decimal(len(items)))
    peak_monthly_quantity = max(quantities)
    low_monthly_quantity = min(quantities)
    seasonality_index = (
        _quantize_index(peak_monthly_quantity / avg_monthly_quantity)
        if avg_monthly_quantity > 0
        else Decimal("0.000")
    )
    above_average_months = [
        str(item["month"])
        for item in items
        if item["quantity"] > avg_monthly_quantity
    ]

    if includes_current_month and start_month == current_month_start:
        data_basis = "live_current_month_only"
    elif includes_current_month:
        data_basis = "aggregated_plus_live_current_month"
    else:
        data_basis = "aggregated_only"

    return {
        "product_id": product_id,
        "items": items,
        "avg_monthly_quantity": avg_monthly_quantity,
        "peak_monthly_quantity": peak_monthly_quantity,
        "low_monthly_quantity": low_monthly_quantity,
        "seasonality_index": seasonality_index,
        "above_average_months": above_average_months,
        "history_months_used": len(items),
        "current_month_live_quantity": current_month_live_quantity,
        "reorder_point": int(stock_context_row.reorder_point or 0),
        "on_order_qty": int(stock_context_row.on_order_qty or 0),
        "in_transit_qty": int(stock_context_row.in_transit_qty or 0),
        "reserved_qty": int(stock_context_row.reserved_qty or 0),
        "data_basis": data_basis,
        "advisory_only": True,
        "data_gap": False,
        "window": {
            "start_month": _format_month(start_month),
            "end_month": _format_month(end_month),
            "includes_current_month": includes_current_month,
            "is_partial": includes_current_month,
        },
    }


# ── Sales history ────────────────────────────────────────────────


async def get_sales_history(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    *,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """Return paginated sales history (all reason codes) for a product."""
    count_stmt = select(func.count(StockAdjustment.id)).where(
        StockAdjustment.tenant_id == tenant_id,
        StockAdjustment.product_id == product_id,
    )
    count_result = await session.execute(count_stmt)
    total = count_result.scalar() or 0

    stmt = (
        select(StockAdjustment)
        .where(
            StockAdjustment.tenant_id == tenant_id,
            StockAdjustment.product_id == product_id,
        )
        .order_by(StockAdjustment.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await session.execute(stmt)
    adjustments = result.scalars().all()

    items = [
        {
            "date": adj.created_at,
            "quantity_change": adj.quantity_change,
            "reason_code": adj.reason_code.value,
            "actor_id": adj.actor_id,
        }
        for adj in adjustments
    ]
    return {"items": items, "total": total}


# ── Top customer ─────────────────────────────────────────────────


async def get_top_customer(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
) -> dict | None:
    """Return the customer who has ordered the most of this product (by quantity)."""
    from common.models.order import Order
    from common.models.order_line import OrderLine
    from domains.customers.models import Customer

    stmt = (
        select(
            Customer.id.label("customer_id"),
            Customer.company_name.label("customer_name"),
            func.sum(OrderLine.quantity).label("total_qty"),
        )
        .join(Order, Order.id == OrderLine.order_id)
        .join(Customer, Customer.id == Order.customer_id)
        .where(
            Order.tenant_id == tenant_id,
            OrderLine.product_id == product_id,
        )
        .group_by(Customer.id, Customer.company_name)
        .order_by(func.sum(OrderLine.quantity).desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    row = result.first()

    if row is None:
        return None
    return {
        "customer_id": row.customer_id,
        "customer_name": row.customer_name,
        "total_qty": int(row.total_qty or 0),
    }


# ── Product supplier ──────────────────────────────────────────────


async def get_product_supplier(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
) -> dict | None:
    """Return the most-recent supplier for a product, with unit cost and lead time.

    Resolves via supplier_order_line → supplier_order: picks the supplier
    with the most recently received order lines for this product.
    Returns null if no supplier orders exist.
    """
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


# ── Product audit log ─────────────────────────────────────────


async def get_product_audit_log(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """Fetch audit log entries for a product.

    Returns entries for both inventory_stock field changes
    (reorder_point, safety_factor, lead_time_days) and product status changes.
    Each field that changed becomes a separate entry.
    """
    # Subquery: all inventory_stock ids for this product
    stock_ids_sq = (
        select(InventoryStock.id)
        .where(
            InventoryStock.tenant_id == tenant_id,
            InventoryStock.product_id == product_id,
        )
        .subquery()
    )

    # Query audit_log for inventory_stock field changes
    # or product status changes, unioned and ordered by created_at DESC
    stock_logs = (
        select(
            AuditLog.id,
            AuditLog.created_at,
            AuditLog.actor_id,
            AuditLog.before_state,
            AuditLog.after_state,
            AuditLog.entity_type,
        )
        .where(
            AuditLog.tenant_id == tenant_id,
            AuditLog.entity_type == "inventory_stock",
            AuditLog.entity_id.in_(select(stock_ids_sq)),
        )
    )

    product_logs = (
        select(
            AuditLog.id,
            AuditLog.created_at,
            AuditLog.actor_id,
            AuditLog.before_state,
            AuditLog.after_state,
            AuditLog.entity_type,
        )
        .where(
            AuditLog.tenant_id == tenant_id,
            AuditLog.entity_type == "product",
            AuditLog.entity_id == str(product_id),
        )
    )

    # Count total before pagination
    all_union = stock_logs.union(product_logs).subquery()
    count_stmt = select(func.count()).select_from(all_union)
    count_result = await session.execute(count_stmt)
    total = count_result.scalar() or 0

    # Fetch with LIMIT/OFFSET ordered by created_at DESC
    fetch_stmt = (
        select(
            AuditLog.id,
            AuditLog.created_at,
            AuditLog.actor_id,
            AuditLog.before_state,
            AuditLog.after_state,
            AuditLog.entity_type,
        )
        .where(
            AuditLog.tenant_id == tenant_id,
            AuditLog.entity_type.in_(["inventory_stock", "product"]),
            (
                AuditLog.entity_type == "inventory_stock"
                & AuditLog.entity_id.in_(select(stock_ids_sq))
            )
            | (AuditLog.entity_type == "product" & AuditLog.entity_id == str(product_id)),
        )
        .order_by(AuditLog.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await session.execute(fetch_stmt)
    rows = result.all()

    items = []
    for row in rows:
        before = row.before_state or {}
        after = row.after_state or {}

        if row.entity_type == "inventory_stock":
            # before_state/after_state contain {reorder_point, safety_factor, lead_time_days, ...}
            # Create one entry per changed field
            for field in ("reorder_point", "safety_factor", "lead_time_days"):
                old_val = before.get(field)
                new_val = after.get(field)
                if old_val is not None or new_val is not None:
                    items.append(
                        {
                            "id": row.id,
                            "created_at": row.created_at,
                            "actor_id": row.actor_id,
                            "field": field,
                            "old_value": str(old_val) if old_val is not None else None,
                            "new_value": str(new_val) if new_val is not None else None,
                        }
                    )
        elif row.entity_type == "product":
            # before_state/after_state contain {status, ...}
            old_status = before.get("status")
            new_status = after.get("status")
            if old_status is not None or new_status is not None:
                items.append(
                    {
                        "id": row.id,
                        "created_at": row.created_at,
                        "actor_id": row.actor_id,
                        "field": "status",
                        "old_value": str(old_status) if old_status is not None else None,
                        "new_value": str(new_status) if new_status is not None else None,
                    }
                )

    # Sort combined items by created_at DESC
    items.sort(key=lambda x: x["created_at"], reverse=True)

    return {"items": items, "total": total}
