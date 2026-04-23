"""Add procurement goods receipt tables (Story 24-3).

Revision ID: abc123def458
Revises: abc123def457
Create Date: 2026-04-23
"""

from __future__ import annotations

import uuid
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON


# revision identifiers, used by Alembic.
revision = "abc123def458"
down_revision = "abc123def457"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create goods_receipts table
    op.create_table(
        "procurement_goods_receipts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("name", sa.String(100), nullable=False, default=""),
        sa.Column("status", sa.String(24), nullable=False, default="draft"),
        sa.Column(
            "purchase_order_id",
            UUID(as_uuid=True),
            sa.ForeignKey("procurement_purchase_orders.id"),
            nullable=False,
        ),
        sa.Column("supplier_id", UUID(as_uuid=True), nullable=True),
        sa.Column("supplier_name", sa.String(200), nullable=False, default=""),
        sa.Column("company", sa.String(200), nullable=False, default=""),
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("posting_date", sa.Date(), nullable=True),
        sa.Column("set_warehouse", sa.String(120), nullable=False, default=""),
        sa.Column("contact_person", sa.String(120), nullable=False, default=""),
        sa.Column("notes", sa.Text(), nullable=False, default=""),
        sa.Column("inventory_mutated", sa.Boolean(), nullable=False, default=False),
        sa.Column("inventory_mutated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # Add indexes
    op.create_index(
        "ix_procurement_gr_tenant_status",
        "procurement_goods_receipts",
        ["tenant_id", "status"],
    )
    op.create_index(
        "ix_procurement_gr_tenant_po",
        "procurement_goods_receipts",
        ["tenant_id", "purchase_order_id"],
    )
    op.create_index(
        "ix_procurement_gr_tenant_supplier",
        "procurement_goods_receipts",
        ["tenant_id", "supplier_id"],
    )

    # Create goods_receipt_items table
    op.create_table(
        "procurement_goods_receipt_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column(
            "goods_receipt_id",
            UUID(as_uuid=True),
            sa.ForeignKey("procurement_goods_receipts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("idx", sa.Integer(), nullable=False, default=0),
        sa.Column(
            "purchase_order_item_id",
            UUID(as_uuid=True),
            sa.ForeignKey("procurement_purchase_order_items.id"),
            nullable=False,
        ),
        sa.Column("item_code", sa.String(100), nullable=False, default=""),
        sa.Column("item_name", sa.String(200), nullable=False, default=""),
        sa.Column("description", sa.Text(), nullable=False, default=""),
        sa.Column("accepted_qty", sa.Numeric(14, 3), nullable=False, default=0),
        sa.Column("rejected_qty", sa.Numeric(14, 3), nullable=False, default=0),
        sa.Column("total_qty", sa.Numeric(14, 3), nullable=False, default=0),
        sa.Column("uom", sa.String(40), nullable=False, default=""),
        sa.Column("warehouse", sa.String(120), nullable=False, default=""),
        sa.Column("rejected_warehouse", sa.String(120), nullable=False, default=""),
        sa.Column("batch_no", sa.String(100), nullable=False, default=""),
        sa.Column("serial_no", sa.String(100), nullable=False, default=""),
        sa.Column("exception_notes", sa.Text(), nullable=False, default=""),
        sa.Column("is_rejected", sa.Boolean(), nullable=False, default=False),
        sa.Column("unit_rate", sa.Numeric(14, 4), nullable=False, default=0),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # Add indexes
    op.create_index(
        "ix_procurement_gr_items_receipt",
        "procurement_goods_receipt_items",
        ["goods_receipt_id"],
    )
    op.create_index(
        "ix_procurement_gr_items_po_line",
        "procurement_goods_receipt_items",
        ["purchase_order_item_id"],
    )


def downgrade() -> None:
    op.drop_table("procurement_goods_receipt_items")
    op.drop_table("procurement_goods_receipts")
