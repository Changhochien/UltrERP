"""
Inventory commands - write operations (mutate state, emit events).

This module provides the command-side of the CQRS pattern for inventory.
"""

from __future__ import annotations

# Import all commands from modular files
from domains.inventory.commands._warehouse import create_warehouse
from domains.inventory.commands._category import (
    create_category,
    set_category_status,
    update_category,
)
from domains.inventory.commands._product import (
    create_product,
    update_product,
    set_product_status,
)
from domains.inventory.commands._stock import (
    InsufficientStockError,
    TransferValidationError,
    transfer_stock,
    create_stock_adjustment,
    update_stock_settings,
)
from domains.inventory.commands._unit import (
    seed_default_units,
    create_unit,
    set_unit_status,
    update_unit,
)
from domains.inventory.commands._physical import (
    PhysicalCountConflictError,
    PhysicalCountNotFoundError,
    PhysicalCountStateError,
    create_physical_count_session,
    update_physical_count_line,
    submit_physical_count_session,
    approve_physical_count_session,
)
from domains.inventory.commands._alerts import (
    acknowledge_alert,
    snooze_alert,
    dismiss_alert,
    create_reorder_suggestion_orders,
)
from domains.inventory.commands._supplier import (
    create_supplier,
    update_supplier,
    set_supplier_status,
    create_supplier_order,
    receive_supplier_order,
    update_supplier_order_status,
)
from domains.inventory.commands._product_supplier import (
    create_product_supplier,
    update_product_supplier,
    delete_product_supplier,
)

__all__ = [
    # Warehouse
    "create_warehouse",
    # Category
    "create_category",
    "update_category",
    "set_category_status",
    # Stock
    "transfer_stock",
    "create_stock_adjustment",
    "InsufficientStockError",
    "TransferValidationError",
    "update_stock_settings",
    # Product
    "create_product",
    "update_product",
    "set_product_status",
    # Unit of Measure
    "seed_default_units",
    "create_unit",
    "update_unit",
    "set_unit_status",
    # Physical count
    "create_physical_count_session",
    "update_physical_count_line",
    "submit_physical_count_session",
    "approve_physical_count_session",
    "PhysicalCountNotFoundError",
    "PhysicalCountConflictError",
    "PhysicalCountStateError",
    # Alerts
    "acknowledge_alert",
    "snooze_alert",
    "dismiss_alert",
    "create_reorder_suggestion_orders",
    # Product-supplier
    "create_product_supplier",
    "delete_product_supplier",
    "update_product_supplier",
    # Supplier
    "create_supplier",
    "update_supplier",
    "set_supplier_status",
    "create_supplier_order",
    "receive_supplier_order",
    "update_supplier_order_status",
]
