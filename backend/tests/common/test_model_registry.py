from __future__ import annotations

from common.database import metadata

EXPECTED_REGISTERED_TABLES = {
    "app_settings",
    "approval_requests",
    "audit_log",
    "category",
    "customers",
    "egui_submissions",
    "inventory_stock",
    "invoice_lines",
    "invoice_number_ranges",
    "invoices",
    "legacy_import_runs",
    "legacy_import_table_runs",
    "line_customer_mappings",
    "order_lines",
    "orders",
    "payments",
    "physical_count_line",
    "physical_count_session",
    "product",
    "reorder_alert",
    "sales_monthly",
    "stock_adjustment",
    "stock_transfer_history",
    "supplier",
    "supplier_invoice_lines",
    "supplier_invoices",
    "supplier_order",
    "supplier_order_line",
    "supplier_payment_allocations",
    "supplier_payments",
    "unit_of_measure",
    "users",
    "warehouse",
}


def test_model_registry_registers_domain_tables_for_metadata() -> None:
    from common.model_registry import register_all_models

    register_all_models()

    assert set(metadata.tables) == EXPECTED_REGISTERED_TABLES


def test_common_models_exports_only_common_owned_symbols() -> None:
    import common.models as common_models

    assert not hasattr(common_models, "Customer")
    assert not hasattr(common_models, "Invoice")
    assert not hasattr(common_models, "InvoiceLine")
    assert not hasattr(common_models, "InvoiceNumberRange")
    assert not hasattr(common_models, "Payment")
    assert not hasattr(common_models, "SalesMonthly")
    assert not hasattr(common_models, "AppSetting")
    assert not hasattr(common_models, "LineCustomerMapping")