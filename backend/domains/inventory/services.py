"""Inventory domain service — warehouse CRUD, stock transfers."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import and_, asc, case, desc, distinct, func, literal, or_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from common.models.product import Product
from common.models.supplier_invoice import SupplierInvoice, SupplierInvoiceLine
from common.time import utc_now
from domains.inventory._alert_support import (
    _compute_severity,
)
from domains.inventory._product_supplier_support import (
    _batch_get_product_suppliers,
    _load_product_supplier_explicit_row,
    _product_supplier_table_exists,
    _serialize_product_supplier_association,
)
from domains.inventory._product_audit_support import get_product_audit_log
from domains.inventory._supplier_order_support import _serialize_order
from domains.inventory.commands._category import (
    create_category,
    set_category_status,
    update_category,
)
from domains.inventory.commands._alerts import (
    _create_reorder_suggestion_orders_with_supplier_loader,
    acknowledge_alert,
    dismiss_alert,
    snooze_alert,
)
from domains.inventory.commands._product import (
    create_product as _create_product_command,
    set_product_status as _set_product_status_command,
    update_product as _update_product_command,
)
from domains.inventory.commands._physical import (
    approve_physical_count_session as _approve_physical_count_session_command,
    create_physical_count_session as _create_physical_count_session_command,
    submit_physical_count_session as _submit_physical_count_session_command,
    update_physical_count_line as _update_physical_count_line_command,
)
from domains.inventory.commands._product_supplier import (
    create_product_supplier,
    delete_product_supplier,
    update_product_supplier,
)
from domains.inventory.commands._stock import (
    create_stock_adjustment,
    transfer_stock,
    update_stock_settings,
)
from domains.inventory.commands._supplier import (
    create_supplier,
    create_supplier_order,
    receive_supplier_order,
    set_supplier_status,
    update_supplier,
    update_supplier_order_status,
)
from domains.inventory.commands._unit import (
    create_unit,
    seed_default_units,
    set_unit_status,
    update_unit,
)
from domains.inventory.commands._warehouse import create_warehouse
from domains.inventory.domain import (
    DEFAULT_UNIT_OF_MEASURE_SEEDS,
    InsufficientStockError,
    PhysicalCountConflictError,
    PhysicalCountNotFoundError,
    PhysicalCountStateError,
    TransferValidationError,
)
from domains.inventory.queries._product_supplier import (
    get_product_supplier,
    list_product_suppliers,
)
from domains.inventory.queries._alerts import (
    _list_reorder_suggestions_with_supplier_loader,
    list_reorder_alerts,
)
from domains.inventory.queries._analytics import (
    _get_monthly_demand_with_now_provider,
    get_monthly_demand_series as _get_monthly_demand_series_query,
    get_planning_support as _get_planning_support_query,
    get_sales_history as _get_sales_history_query,
    get_stock_history as _get_stock_history_query,
    get_stock_history_series as _get_stock_history_series_query,
)
from domains.inventory.queries._physical import (
    get_physical_count_session as _get_physical_count_session_query,
    list_physical_count_sessions as _list_physical_count_sessions_query,
)
from domains.inventory.queries._category import get_category, list_categories
from domains.inventory.queries._product import (
    get_product_detail,
    search_products,
)
from domains.inventory.queries._stock import (
    _list_below_reorder_products_with_supplier_loader,
    get_inventory_stocks,
    get_inventory_valuation,
    get_transfer,
    list_transfers,
)
from domains.inventory.queries._supplier import (
    get_supplier,
    get_supplier_order,
    get_top_customer,
    list_supplier_orders,
    list_suppliers,
)
from domains.inventory.queries._unit import get_unit, list_units
from domains.inventory.queries._warehouse import get_warehouse, list_warehouses

if TYPE_CHECKING:
    from domains.inventory.schemas import (
        ProductCreate,
        ProductUpdate,
        SupplierCreate,
        SupplierUpdate,
    )


async def create_product(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    data: "ProductCreate",
) -> Product:
    return await _create_product_command(session, tenant_id, data)


async def update_product(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    data: "ProductUpdate",
) -> Product | None:
    return await _update_product_command(session, tenant_id, product_id, data)


async def set_product_status(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    status: str,
) -> Product | None:
    return await _set_product_status_command(session, tenant_id, product_id, status)


async def create_physical_count_session(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    warehouse_id: uuid.UUID,
    actor_id: str,
) -> dict[str, object | None]:
    return await _create_physical_count_session_command(
        session,
        tenant_id,
        warehouse_id=warehouse_id,
        actor_id=actor_id,
    )


async def list_physical_count_sessions(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    warehouse_id: uuid.UUID | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict[str, object | None]], int]:
    return await _list_physical_count_sessions_query(
        session,
        tenant_id,
        warehouse_id=warehouse_id,
        status=status,
        limit=limit,
        offset=offset,
    )


async def get_physical_count_session(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    session_id: uuid.UUID,
) -> dict[str, object | None] | None:
    return await _get_physical_count_session_query(session, tenant_id, session_id)


async def update_physical_count_line(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    session_id: uuid.UUID,
    line_id: uuid.UUID,
    *,
    counted_qty: int,
    notes: str | None,
) -> dict[str, object | None]:
    return await _update_physical_count_line_command(
        session,
        tenant_id,
        session_id,
        line_id,
        counted_qty=counted_qty,
        notes=notes,
    )


async def submit_physical_count_session(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    session_id: uuid.UUID,
    *,
    actor_id: str,
) -> dict[str, object | None]:
    return await _submit_physical_count_session_command(
        session,
        tenant_id,
        session_id,
        actor_id=actor_id,
    )


async def approve_physical_count_session(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    session_id: uuid.UUID,
    *,
    actor_id: str,
) -> dict[str, object | None]:
    return await _approve_physical_count_session_command(
        session,
        tenant_id,
        session_id,
        actor_id=actor_id,
    )


async def list_reorder_suggestions(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    warehouse_id: uuid.UUID | None = None,
) -> tuple[list[dict], int]:
    return await _list_reorder_suggestions_with_supplier_loader(
        session,
        tenant_id,
        warehouse_id=warehouse_id,
        product_supplier_loader=_batch_get_product_suppliers,
    )


async def create_reorder_suggestion_orders(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    items: list[dict],
    actor_id: str,
) -> dict:
    return await _create_reorder_suggestion_orders_with_supplier_loader(
        session,
        tenant_id,
        items=items,
        actor_id=actor_id,
        product_supplier_loader=_batch_get_product_suppliers,
    )


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
    return await _get_stock_history_query(
        session,
        tenant_id,
        product_id,
        warehouse_id,
        start_date=start_date,
        end_date=end_date,
        granularity=granularity,
        _max_range_days=_max_range_days,
    )


async def get_stock_history_series(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    stock_id: uuid.UUID,
    *,
    start_date: str,  # YYYY-MM-DD
    end_date: str,    # YYYY-MM-DD
) -> dict:
    return await _get_stock_history_series_query(
        session,
        tenant_id,
        stock_id,
        start_date=start_date,
        end_date=end_date,
    )


# ── Monthly demand ──────────────────────────────────────────────


async def get_monthly_demand(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    *,
    months: int = 12,
    include_current_month: bool = True,
) -> dict:
    return await _get_monthly_demand_with_now_provider(
        session,
        tenant_id,
        product_id,
        months=months,
        include_current_month=include_current_month,
        now_provider=utc_now,
    )


async def get_monthly_demand_series(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    *,
    start_month: str,  # YYYY-MM
    end_month: str,    # YYYY-MM
) -> dict:
    return await _get_monthly_demand_series_query(
        session,
        tenant_id,
        product_id,
        start_month=start_month,
        end_month=end_month,
    )


async def get_planning_support(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    *,
    months: int = 12,
    include_current_month: bool = True,
) -> dict | None:
    return await _get_planning_support_query(
        session,
        tenant_id,
        product_id,
        months=months,
        include_current_month=include_current_month,
    )


# ── Sales history ────────────────────────────────────────────────


async def get_sales_history(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    *,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    return await _get_sales_history_query(
        session,
        tenant_id,
        product_id,
        limit=limit,
        offset=offset,
    )


