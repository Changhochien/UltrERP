"""Explicit ORM model registry for metadata registration side effects."""

from __future__ import annotations

from importlib import import_module

MODEL_MODULES = (
	"common.models.account",
	"common.models.approval_request",
	"common.models.audit_log",
	"common.models.banking",
	"common.models.budget",
	"common.models.category",
	"common.models.fiscal_year",
	"common.models.gl_entry",
	"common.models.inventory_stock",
	"common.models.journal_entry",
	"common.models.journal_entry_line",
	"common.models.legacy_import",
	"common.models.order",
	"common.models.order_line",
	"common.models.payment_terms",
	"common.models.physical_count_line",
	"common.models.physical_count_session",
	"common.models.posting_rule",
	"common.models.product",
	"common.models.product_supplier",
	"common.models.reorder_alert",
	"common.models.stock_adjustment",
	"common.models.stock_transfer",
	"common.models.supplier",
	"common.models.supplier_invoice",
	"common.models.supplier_order",
	"common.models.supplier_payment",
	"common.models.unit_of_measure",
	"common.models.currency",
	"common.models.user",
	"common.models.warehouse",
	"domains.customers.models",
	"domains.invoices.models",
	"domains.line.models",
	"domains.payments.models",
	"domains.product_analytics.models",
	"domains.settings.models",
)


def register_all_models() -> None:
	for module_path in MODEL_MODULES:
		import_module(module_path)
