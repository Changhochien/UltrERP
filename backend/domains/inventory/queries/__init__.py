"""
Inventory queries - read operations (side-effect free).

This module provides the query-side of the CQRS pattern for inventory.
"""

from __future__ import annotations

# Shared helpers from domain layer
from domains.inventory.domain import resolve_category_locale, serialize_category

# Import all queries from modular files
from domains.inventory.queries._category import (
    get_category,
    list_categories,
)
from domains.inventory.queries._product import (
    get_product_detail,
    get_product_audit_log,
    search_products,
)
from domains.inventory.queries._stock import (
    get_inventory_stocks,
    get_inventory_valuation,
    get_transfer,
    list_transfers,
    list_below_reorder_products,
)
from domains.inventory.queries._physical import (
    get_physical_count_session,
    list_physical_count_sessions,
)
from domains.inventory.queries._alerts import (
    list_reorder_alerts,
    list_reorder_suggestions,
)
from domains.inventory.queries._supplier import (
    get_supplier,
    get_supplier_order,
    get_top_customer,
    list_supplier_orders,
    list_suppliers,
)
from domains.inventory.queries._unit import (
    get_unit,
    list_units,
)
from domains.inventory.queries._warehouse import (
    get_warehouse,
    list_warehouses,
)
from domains.inventory.queries._analytics import (
    get_monthly_demand,
    get_monthly_demand_series,
    get_planning_support,
    get_sales_history,
    get_stock_history,
    get_stock_history_series,
)
from domains.inventory.queries._product_supplier import (
    get_product_supplier,
    list_product_suppliers,
)

__all__ = [
    # Category
    "get_category",
    "list_categories",
    # Warehouse
    "get_warehouse",
    "list_warehouses",
    # Product
    "get_product_detail",
    "get_product_audit_log",
    "search_products",
    # Unit of Measure
    "get_unit",
    "list_units",
    # Stock
    "get_inventory_stocks",
    "get_inventory_valuation",
    "get_transfer",
    "list_below_reorder_products",
    "list_transfers",
    # Physical count
    "get_physical_count_session",
    "list_physical_count_sessions",
    # Alerts
    "list_reorder_alerts",
    "list_reorder_suggestions",
    # Supplier
    "get_supplier",
    "get_supplier_order",
    "get_top_customer",
    "list_supplier_orders",
    "list_suppliers",
    # Analytics
    "get_monthly_demand",
    "get_monthly_demand_series",
    "get_planning_support",
    "get_sales_history",
    "get_stock_history",
    "get_stock_history_series",
    # Product-supplier
    "get_product_supplier",
    "list_product_suppliers",
    # Shared helpers
    "resolve_category_locale",
    "serialize_category",
]
