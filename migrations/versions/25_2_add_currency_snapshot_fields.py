"""Add currency snapshot fields to commercial documents for Story 25-2.

This migration adds:
- Document-level currency snapshot fields (conversion_rate, effective_date, rate_source)
- Base amount fields for headers and lines
- Line-level base amount fields where applicable

These fields enable Epic 25 multi-currency support without changing existing behavior
for base-currency documents (conversion_rate = 1, base amounts = transaction amounts).
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON


revision = "25_2_doc_currency"
down_revision = "25_1_currency_masters"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # === Order: Add currency and conversion fields ===
    op.add_column(
        "orders",
        sa.Column("currency_code", sa.String(3), nullable=True, server_default="TWD"),
    )
    op.add_column(
        "orders",
        sa.Column("conversion_rate", sa.Numeric(20, 10), nullable=True, server_default="1.0000000000"),
    )
    op.add_column(
        "orders",
        sa.Column("conversion_effective_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column("applied_rate_source", sa.String(50), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column("base_subtotal_amount", sa.Numeric(20, 2), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column("base_discount_amount", sa.Numeric(20, 2), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column("base_tax_amount", sa.Numeric(20, 2), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column("base_total_amount", sa.Numeric(20, 2), nullable=True),
    )

    # === Order Line: Add base amount fields ===
    op.add_column(
        "order_lines",
        sa.Column("base_unit_price", sa.Numeric(20, 2), nullable=True),
    )
    op.add_column(
        "order_lines",
        sa.Column("base_subtotal_amount", sa.Numeric(20, 2), nullable=True),
    )
    op.add_column(
        "order_lines",
        sa.Column("base_tax_amount", sa.Numeric(20, 2), nullable=True),
    )
    op.add_column(
        "order_lines",
        sa.Column("base_total_amount", sa.Numeric(20, 2), nullable=True),
    )

    # === Quotation: Add conversion rate and line-level base fields ===
    op.add_column(
        "crm_quotations",
        sa.Column("conversion_rate", sa.Numeric(20, 10), nullable=True, server_default="1.0000000000"),
    )
    op.add_column(
        "crm_quotations",
        sa.Column("conversion_effective_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "crm_quotations",
        sa.Column("applied_rate_source", sa.String(50), nullable=True),
    )
    op.add_column(
        "crm_quotations",
        sa.Column("base_subtotal", sa.Numeric(14, 2), nullable=True),
    )
    op.add_column(
        "crm_quotations",
        sa.Column("base_total_taxes", sa.Numeric(14, 2), nullable=True),
    )

    # === CRM Quotation Line Items (stored in JSON): Add base amount tracking ===
    # Note: Quotation items are stored as JSON. We'll add base amount fields to the line structure
    # The base_grand_total already exists, we need to ensure line-level base amounts are computed

    # === Invoice: Add conversion rate and base amount fields ===
    op.add_column(
        "invoices",
        sa.Column("conversion_rate", sa.Numeric(20, 10), nullable=True, server_default="1.0000000000"),
    )
    op.add_column(
        "invoices",
        sa.Column("conversion_effective_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "invoices",
        sa.Column("applied_rate_source", sa.String(50), nullable=True),
    )
    op.add_column(
        "invoices",
        sa.Column("base_subtotal_amount", sa.Numeric(20, 2), nullable=True),
    )
    op.add_column(
        "invoices",
        sa.Column("base_tax_amount", sa.Numeric(20, 2), nullable=True),
    )
    op.add_column(
        "invoices",
        sa.Column("base_total_amount", sa.Numeric(20, 2), nullable=True),
    )

    # === Invoice Line: Add base amount fields ===
    op.add_column(
        "invoice_lines",
        sa.Column("base_unit_price", sa.Numeric(20, 2), nullable=True),
    )
    op.add_column(
        "invoice_lines",
        sa.Column("base_subtotal_amount", sa.Numeric(20, 2), nullable=True),
    )
    op.add_column(
        "invoice_lines",
        sa.Column("base_tax_amount", sa.Numeric(20, 2), nullable=True),
    )
    op.add_column(
        "invoice_lines",
        sa.Column("base_total_amount", sa.Numeric(20, 2), nullable=True),
    )

    # === Supplier Invoice: Add conversion rate and base amount fields ===
    op.add_column(
        "supplier_invoices",
        sa.Column("conversion_rate", sa.Numeric(20, 10), nullable=True, server_default="1.0000000000"),
    )
    op.add_column(
        "supplier_invoices",
        sa.Column("conversion_effective_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "supplier_invoices",
        sa.Column("applied_rate_source", sa.String(50), nullable=True),
    )
    op.add_column(
        "supplier_invoices",
        sa.Column("base_subtotal_amount", sa.Numeric(20, 2), nullable=True),
    )
    op.add_column(
        "supplier_invoices",
        sa.Column("base_tax_amount", sa.Numeric(20, 2), nullable=True),
    )
    op.add_column(
        "supplier_invoices",
        sa.Column("base_total_amount", sa.Numeric(20, 2), nullable=True),
    )
    op.add_column(
        "supplier_invoices",
        sa.Column("remaining_base_payable_amount", sa.Numeric(20, 2), nullable=True),
    )

    # === Supplier Invoice Line: Add base amount fields ===
    op.add_column(
        "supplier_invoice_lines",
        sa.Column("base_unit_price", sa.Numeric(20, 2), nullable=True),
    )
    op.add_column(
        "supplier_invoice_lines",
        sa.Column("base_subtotal_amount", sa.Numeric(20, 2), nullable=True),
    )
    op.add_column(
        "supplier_invoice_lines",
        sa.Column("base_tax_amount", sa.Numeric(20, 2), nullable=True),
    )
    op.add_column(
        "supplier_invoice_lines",
        sa.Column("base_total_amount", sa.Numeric(20, 2), nullable=True),
    )

    # === Customer Payment: Add conversion rate and base amount fields ===
    op.add_column(
        "payments",
        sa.Column("currency_code", sa.String(3), nullable=True, server_default="TWD"),
    )
    op.add_column(
        "payments",
        sa.Column("conversion_rate", sa.Numeric(20, 10), nullable=True, server_default="1.0000000000"),
    )
    op.add_column(
        "payments",
        sa.Column("conversion_effective_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "payments",
        sa.Column("applied_rate_source", sa.String(50), nullable=True),
    )
    op.add_column(
        "payments",
        sa.Column("base_amount", sa.Numeric(20, 2), nullable=True),
    )

    # === Supplier Payment: Add conversion rate and base amount fields ===
    op.add_column(
        "supplier_payments",
        sa.Column("conversion_rate", sa.Numeric(20, 10), nullable=True, server_default="1.0000000000"),
    )
    op.add_column(
        "supplier_payments",
        sa.Column("conversion_effective_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "supplier_payments",
        sa.Column("applied_rate_source", sa.String(50), nullable=True),
    )
    op.add_column(
        "supplier_payments",
        sa.Column("base_amount", sa.Numeric(20, 2), nullable=True),
    )

    # === Supplier Payment Allocation: Add base amount fields ===
    op.add_column(
        "supplier_payment_allocations",
        sa.Column("base_applied_amount", sa.Numeric(20, 2), nullable=True),
    )

    # === Add indexes for currency lookups ===
    op.create_index(
        "ix_orders_currency",
        "orders",
        ["tenant_id", "currency_code"],
    )
    op.create_index(
        "ix_payments_currency",
        "payments",
        ["tenant_id", "currency_code"],
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_orders_currency", table_name="orders")
    op.drop_index("ix_payments_currency", table_name="payments")

    # Supplier Payment Allocation
    op.drop_column("supplier_payment_allocations", "base_applied_amount")

    # Supplier Payment
    op.drop_column("supplier_payments", "base_amount")
    op.drop_column("supplier_payments", "applied_rate_source")
    op.drop_column("supplier_payments", "conversion_effective_date")
    op.drop_column("supplier_payments", "conversion_rate")

    # Customer Payment
    op.drop_column("payments", "base_amount")
    op.drop_column("payments", "applied_rate_source")
    op.drop_column("payments", "conversion_effective_date")
    op.drop_column("payments", "conversion_rate")
    op.drop_column("payments", "currency_code")

    # Supplier Invoice Line
    op.drop_column("supplier_invoice_lines", "base_total_amount")
    op.drop_column("supplier_invoice_lines", "base_tax_amount")
    op.drop_column("supplier_invoice_lines", "base_subtotal_amount")
    op.drop_column("supplier_invoice_lines", "base_unit_price")

    # Supplier Invoice
    op.drop_column("supplier_invoices", "remaining_base_payable_amount")
    op.drop_column("supplier_invoices", "base_total_amount")
    op.drop_column("supplier_invoices", "base_tax_amount")
    op.drop_column("supplier_invoices", "base_subtotal_amount")
    op.drop_column("supplier_invoices", "applied_rate_source")
    op.drop_column("supplier_invoices", "conversion_effective_date")
    op.drop_column("supplier_invoices", "conversion_rate")

    # Invoice Line
    op.drop_column("invoice_lines", "base_total_amount")
    op.drop_column("invoice_lines", "base_tax_amount")
    op.drop_column("invoice_lines", "base_subtotal_amount")
    op.drop_column("invoice_lines", "base_unit_price")

    # Invoice
    op.drop_column("invoices", "base_total_amount")
    op.drop_column("invoices", "base_tax_amount")
    op.drop_column("invoices", "base_subtotal_amount")
    op.drop_column("invoices", "applied_rate_source")
    op.drop_column("invoices", "conversion_effective_date")
    op.drop_column("invoices", "conversion_rate")

    # Quotation
    op.drop_column("crm_quotations", "base_total_taxes")
    op.drop_column("crm_quotations", "base_subtotal")
    op.drop_column("crm_quotations", "applied_rate_source")
    op.drop_column("crm_quotations", "conversion_effective_date")
    op.drop_column("crm_quotations", "conversion_rate")

    # Order Line
    op.drop_column("order_lines", "base_total_amount")
    op.drop_column("order_lines", "base_tax_amount")
    op.drop_column("order_lines", "base_subtotal_amount")
    op.drop_column("order_lines", "base_unit_price")

    # Order
    op.drop_column("orders", "base_total_amount")
    op.drop_column("orders", "base_tax_amount")
    op.drop_column("orders", "base_discount_amount")
    op.drop_column("orders", "base_subtotal_amount")
    op.drop_column("orders", "applied_rate_source")
    op.drop_column("orders", "conversion_effective_date")
    op.drop_column("orders", "conversion_rate")
    op.drop_column("orders", "currency_code")
