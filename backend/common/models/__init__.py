"""Common ORM models shared across domains."""

from common.database import Base
from common.models.account import Account
from common.models.approval_request import ApprovalRequest
from common.models.audit_log import AuditLog
from common.models.category import Category
from common.models.fiscal_year import FiscalYear
from common.models.gl_entry import GLEntry
from common.models.inventory_stock import InventoryStock
from common.models.journal_entry import JournalEntry
from common.models.journal_entry_line import JournalEntryLine
from common.models.legacy_import import LegacyImportRun, LegacyImportTableRun
from common.models.order import Order
from common.models.order_line import OrderLine
from common.models.physical_count_line import PhysicalCountLine
from common.models.physical_count_session import PhysicalCountSession, PhysicalCountSessionStatus
from common.models.posting_rule import DocumentPostingState, DocumentType, PostingRule, PostingStatus
from common.models.product import Product
from common.models.product_supplier import ProductSupplier
from common.models.reorder_alert import ReorderAlert
from common.models.stock_adjustment import ReasonCode, StockAdjustment
from common.models.stock_transfer import StockTransferHistory
from common.models.supplier import Supplier
from common.models.supplier_invoice import SupplierInvoice, SupplierInvoiceLine
from common.models.supplier_order import SupplierOrder, SupplierOrderLine
from common.models.supplier_payment import SupplierPayment, SupplierPaymentAllocation
from common.models.unit_of_measure import UnitOfMeasure
from common.models.user import User
from common.models.warehouse import Warehouse
from domains.invoices.models import Invoice
from domains.payments.models import Payment

__all__ = [
	"Base",
	"Account",
	"ApprovalRequest",
	"AuditLog",
	"Category",
	"FiscalYear",
	"GLEntry",
	"InventoryStock",
	"Invoice",
	"JournalEntry",
	"JournalEntryLine",
	"LegacyImportRun",
	"LegacyImportTableRun",
	"Order",
	"OrderLine",
	"Payment",
	"PhysicalCountLine",
	"PhysicalCountSession",
	"PhysicalCountSessionStatus",
	"PostingRule",
	"PostingStatus",
	"DocumentType",
	"DocumentPostingState",
	"Product",
	"ProductSupplier",
	"ReasonCode",
	"ReorderAlert",
	"StockAdjustment",
	"StockTransferHistory",
	"Supplier",
	"SupplierInvoice",
	"SupplierInvoiceLine",
	"SupplierPayment",
	"SupplierPaymentAllocation",
	"SupplierOrder",
	"SupplierOrderLine",
	"UnitOfMeasure",
	"User",
	"Warehouse",
]
