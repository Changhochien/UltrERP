"""Add procurement purchase orders and line items.

Revision ID: abc123def457
Revises: abc123def456
Create Date: 2026-04-23

"""
from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

import sqlalchemy as sa
from alembic import op
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
    JSON,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base

# revision identifiers, used by Alembic.
revision = "abc123def457"
down_revision = "abc123def456"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create procurement_purchase_orders table
    op.create_table(
        "procurement_purchase_orders",
        sa.Column("id", Uuid, primary_key=True, default=uuid.uuid4),
        sa.Column("tenant_id", Uuid, nullable=False, index=True),
        sa.Column("name", String(100), nullable=False, default=""),
        sa.Column("status", String(24), nullable=False, default="draft"),
        # Supplier
        sa.Column("supplier_id", Uuid, nullable=True),
        sa.Column("supplier_name", String(200), nullable=False, default=""),
        # Sourcing lineage
        sa.Column("rfq_id", Uuid, nullable=True),
        sa.Column("quotation_id", Uuid, nullable=True),
        sa.Column("award_id", Uuid, nullable=True),
        # Company
        sa.Column("company", String(200), nullable=False, default=""),
        sa.Column("currency", String(3), nullable=False, default="TWD"),
        # Dates
        sa.Column("transaction_date", Date, nullable=False),
        sa.Column("schedule_date", Date, nullable=True),
        # Pricing
        sa.Column("subtotal", Numeric(14, 2), nullable=False, default=Decimal("0.00")),
        sa.Column("total_taxes", Numeric(14, 2), nullable=False, default=Decimal("0.00")),
        sa.Column("grand_total", Numeric(14, 2), nullable=False, default=Decimal("0.00")),
        sa.Column("base_grand_total", Numeric(14, 2), nullable=False, default=Decimal("0.00")),
        # Taxes
        sa.Column("taxes", JSON, nullable=False, server_default="[]"),
        # Contact
        sa.Column("contact_person", String(120), nullable=False, default=""),
        sa.Column("contact_email", String(254), nullable=False, default=""),
        # Warehouse
        sa.Column("set_warehouse", String(120), nullable=False, default=""),
        # Terms
        sa.Column("terms_and_conditions", Text, nullable=False, default=""),
        sa.Column("notes", Text, nullable=False, default=""),
        # Progress
        sa.Column("per_received", Numeric(5, 2), nullable=False, default=Decimal("0.00")),
        sa.Column("per_billed", Numeric(5, 2), nullable=False, default=Decimal("0.00")),
        # Approval
        sa.Column("is_approved", Boolean, nullable=False, default=False),
        sa.Column("approved_by", String(120), nullable=False, default=""),
        sa.Column("approved_at", DateTime(timezone=True), nullable=True),
        # Timestamps
        sa.Column(
            "created_at",
            DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )

    # Create indexes for procurement_purchase_orders
    op.create_index(
        "ix_procurement_po_tenant_status",
        "procurement_purchase_orders",
        ["tenant_id", "status"],
    )
    op.create_index(
        "ix_procurement_po_tenant_supplier",
        "procurement_purchase_orders",
        ["tenant_id", "supplier_id"],
    )
    op.create_index(
        "ix_procurement_po_tenant_award",
        "procurement_purchase_orders",
        ["tenant_id", "award_id"],
    )

    # Create procurement_purchase_order_items table
    op.create_table(
        "procurement_purchase_order_items",
        sa.Column("id", Uuid, primary_key=True, default=uuid.uuid4),
        sa.Column("purchase_order_id", Uuid, nullable=False),
        sa.Column("tenant_id", Uuid, nullable=False, index=True),
        # Order
        sa.Column("idx", Integer, nullable=False, default=0),
        # Lineage
        sa.Column("quotation_item_id", Uuid, nullable=True),
        sa.Column("rfq_item_id", Uuid, nullable=True),
        # Item
        sa.Column("item_code", String(100), nullable=False, default=""),
        sa.Column("item_name", String(200), nullable=False, default=""),
        sa.Column("description", Text, nullable=False, default=""),
        # Quantity
        sa.Column("qty", Numeric(14, 3), nullable=False, default=Decimal("0")),
        sa.Column("uom", String(40), nullable=False, default=""),
        # Warehouse
        sa.Column("warehouse", String(120), nullable=False, default=""),
        # Pricing
        sa.Column("unit_rate", Numeric(14, 4), nullable=False, default=Decimal("0")),
        sa.Column("amount", Numeric(14, 2), nullable=False, default=Decimal("0.00")),
        # Tax
        sa.Column("tax_rate", Numeric(6, 3), nullable=False, default=Decimal("0")),
        sa.Column("tax_amount", Numeric(14, 2), nullable=False, default=Decimal("0.00")),
        sa.Column("tax_code", String(40), nullable=False, default=""),
        # Progress
        sa.Column("received_qty", Numeric(14, 3), nullable=False, default=Decimal("0")),
        sa.Column("billed_amount", Numeric(14, 2), nullable=False, default=Decimal("0.00")),
        # Timestamp
        sa.Column(
            "created_at",
            DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["purchase_order_id"],
            ["procurement_purchase_orders.id"],
            ondelete="CASCADE",
        ),
    )

    # Create index for purchase_order_items
    op.create_index(
        "ix_procurement_po_items_po",
        "procurement_purchase_order_items",
        ["purchase_order_id"],
    )

    # Add foreign key constraints for sourcing lineage (nullable FKs)
    op.create_foreign_key(
        "fk_po_rfq",
        "procurement_purchase_orders",
        "procurement_rfqs",
        ["rfq_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_po_quotation",
        "procurement_purchase_orders",
        "procurement_supplier_quotations",
        ["quotation_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_po_award",
        "procurement_purchase_orders",
        "procurement_awards",
        ["award_id"],
        ["id"],
    )

    # Add foreign keys for PO item lineage
    op.create_foreign_key(
        "fk_po_item_sq_item",
        "procurement_purchase_order_items",
        "procurement_supplier_quotation_items",
        ["quotation_item_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_po_item_rfq_item",
        "procurement_purchase_order_items",
        "procurement_rfq_items",
        ["rfq_item_id"],
        ["id"],
    )


def downgrade() -> None:
    # Drop foreign keys
    op.drop_constraint("fk_po_item_rfq_item", "procurement_purchase_order_items", type_="foreignkey")
    op.drop_constraint("fk_po_item_sq_item", "procurement_purchase_order_items", type_="foreignkey")
    op.drop_constraint("fk_po_award", "procurement_purchase_orders", type_="foreignkey")
    op.drop_constraint("fk_po_quotation", "procurement_purchase_orders", type_="foreignkey")
    op.drop_constraint("fk_po_rfq", "procurement_purchase_orders", type_="foreignkey")

    # Drop indexes
    op.drop_index("ix_procurement_po_items_po", "procurement_purchase_order_items")
    op.drop_index("ix_procurement_po_tenant_award", "procurement_purchase_orders")
    op.drop_index("ix_procurement_po_tenant_supplier", "procurement_purchase_orders")
    op.drop_index("ix_procurement_po_tenant_status", "procurement_purchase_orders")

    # Drop tables
    op.drop_table("procurement_purchase_order_items")
    op.drop_table("procurement_purchase_orders")
