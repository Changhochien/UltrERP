"""Common ORM models shared across domains."""

from common.models.approval_request import ApprovalRequest
from common.models.audit_log import AuditLog
from common.models.inventory_stock import InventoryStock
from common.models.legacy_import import LegacyImportRun, LegacyImportTableRun
from common.models.line_customer_mapping import LineCustomerMapping
from common.models.order import Order
from common.models.order_line import OrderLine
from common.models.product import Product
from common.models.reorder_alert import ReorderAlert
from common.models.stock_adjustment import ReasonCode, StockAdjustment
from common.models.stock_transfer import StockTransferHistory
from common.models.supplier import Supplier
from common.models.supplier_invoice import SupplierInvoice, SupplierInvoiceLine
from common.models.supplier_order import SupplierOrder, SupplierOrderLine
from common.models.supplier_payment import SupplierPayment, SupplierPaymentAllocation
from common.models.user import User
from common.models.warehouse import Warehouse
from domains.customers.models import Customer
from domains.invoices.models import EguiSubmission, Invoice, InvoiceLine, InvoiceNumberRange
from domains.payments.models import Payment
from domains.product_analytics.models import SalesMonthly
from domains.settings.models import AppSetting

__all__ = [
	"ApprovalRequest",
	"AppSetting",
	"AuditLog",
	"Customer",
	"EguiSubmission",
	"InventoryStock",
	"Invoice",
	"InvoiceLine",
	"InvoiceNumberRange",
	"LegacyImportRun",
	"LegacyImportTableRun",
	"LineCustomerMapping",
	"Order",
	"OrderLine",
	"Payment",
	"Product",
	"ReasonCode",
	"ReorderAlert",
	"SalesMonthly",
	"StockAdjustment",
	"StockTransferHistory",
	"Supplier",
	"SupplierInvoice",
	"SupplierInvoiceLine",
	"SupplierPayment",
	"SupplierPaymentAllocation",
	"SupplierOrder",
	"SupplierOrderLine",
	"User",
	"Warehouse",
]
