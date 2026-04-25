"""Add subcontracting tables (Story 24-6).

Revision ID: abc123def460
Revises: 2b3c4d5e6f7
Create Date: 2026-04-24
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "abc123def460"
down_revision: Union[str, None] = "2b3c4d5e6f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add subcontractor flag to supplier table
    op.add_column(
        "supplier",
        sa.Column("is_subcontractor", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )

    # Add subcontracting metadata to purchase_order table
    op.add_column(
        "procurement_purchase_orders",
        sa.Column("is_subcontracted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "procurement_purchase_orders",
        sa.Column("finished_goods_item_code", sa.String(100), nullable=True),
    )
    op.add_column(
        "procurement_purchase_orders",
        sa.Column("finished_goods_item_name", sa.String(200), nullable=True),
    )
    op.add_column(
        "procurement_purchase_orders",
        sa.Column("expected_subcontracted_qty", sa.Numeric(14, 3), nullable=True),
    )

    # Create subcontracting_material_transfers table
    op.create_table(
        "procurement_subcontracting_material_transfers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("purchase_order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("supplier_name", sa.String(200), nullable=False),
        sa.Column("company", sa.String(200), nullable=False),
        sa.Column("transfer_date", sa.Date(), nullable=False),
        sa.Column("shipped_date", sa.Date(), nullable=True),
        sa.Column("received_date", sa.Date(), nullable=True),
        sa.Column("source_warehouse", sa.String(120), nullable=False),
        sa.Column("contact_person", sa.String(120), nullable=False),
        sa.Column("contact_email", sa.String(254), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_subcontracting_mt_tenant_status", "procurement_subcontracting_material_transfers", ["tenant_id", "status"])
    op.create_index("ix_subcontracting_mt_tenant_po", "procurement_subcontracting_material_transfers", ["tenant_id", "purchase_order_id"])
    op.create_index("ix_subcontracting_mt_tenant_supplier", "procurement_subcontracting_material_transfers", ["tenant_id", "supplier_id"])
    op.create_foreign_key(
        "fk_subcontracting_mt_po",
        "procurement_subcontracting_material_transfers",
        "procurement_purchase_orders",
        ["purchase_order_id"],
        ["id"],
    )

    # Create subcontracting_material_transfer_items table
    op.create_table(
        "procurement_subcontracting_material_transfer_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("material_transfer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("idx", sa.Integer(), nullable=False),
        sa.Column("item_code", sa.String(100), nullable=False),
        sa.Column("item_name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("qty", sa.Numeric(14, 3), nullable=False),
        sa.Column("uom", sa.String(40), nullable=False),
        sa.Column("warehouse", sa.String(120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_subcontracting_mt_items_transfer", "procurement_subcontracting_material_transfer_items", ["material_transfer_id"])
    op.create_foreign_key(
        "fk_subcontracting_mt_item_transfer",
        "procurement_subcontracting_material_transfer_items",
        "procurement_subcontracting_material_transfers",
        ["material_transfer_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Create subcontracting_receipts table
    op.create_table(
        "procurement_subcontracting_receipts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("purchase_order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("supplier_name", sa.String(200), nullable=False),
        sa.Column("company", sa.String(200), nullable=False),
        sa.Column("receipt_date", sa.Date(), nullable=False),
        sa.Column("posting_date", sa.Date(), nullable=True),
        sa.Column("set_warehouse", sa.String(120), nullable=False),
        sa.Column("contact_person", sa.String(120), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("inventory_mutated", sa.Boolean(), nullable=False),
        sa.Column("inventory_mutated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_subcontracting_receipt_tenant_status", "procurement_subcontracting_receipts", ["tenant_id", "status"])
    op.create_index("ix_subcontracting_receipt_tenant_po", "procurement_subcontracting_receipts", ["tenant_id", "purchase_order_id"])
    op.create_index("ix_subcontracting_receipt_tenant_supplier", "procurement_subcontracting_receipts", ["tenant_id", "supplier_id"])
    op.create_foreign_key(
        "fk_subcontracting_receipt_po",
        "procurement_subcontracting_receipts",
        "procurement_purchase_orders",
        ["purchase_order_id"],
        ["id"],
    )

    # Create subcontracting_receipt_items table
    op.create_table(
        "procurement_subcontracting_receipt_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subcontracting_receipt_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("idx", sa.Integer(), nullable=False),
        sa.Column("item_code", sa.String(100), nullable=False),
        sa.Column("item_name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("accepted_qty", sa.Numeric(14, 3), nullable=False),
        sa.Column("rejected_qty", sa.Numeric(14, 3), nullable=False),
        sa.Column("total_qty", sa.Numeric(14, 3), nullable=False),
        sa.Column("uom", sa.String(40), nullable=False),
        sa.Column("warehouse", sa.String(120), nullable=False),
        sa.Column("unit_rate", sa.Numeric(14, 4), nullable=False),
        sa.Column("exception_notes", sa.Text(), nullable=False),
        sa.Column("is_rejected", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_subcontracting_receipt_items_receipt", "procurement_subcontracting_receipt_items", ["subcontracting_receipt_id"])
    op.create_foreign_key(
        "fk_subcontracting_receipt_item_receipt",
        "procurement_subcontracting_receipt_items",
        "procurement_subcontracting_receipts",
        ["subcontracting_receipt_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Create subcontracting_receipt_material_refs table
    op.create_table(
        "procurement_subcontracting_receipt_material_refs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subcontracting_receipt_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("material_transfer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_subcontracting_receipt_ref_receipt", "procurement_subcontracting_receipt_material_refs", ["subcontracting_receipt_id"])
    op.create_index("ix_subcontracting_receipt_ref_transfer", "procurement_subcontracting_receipt_material_refs", ["material_transfer_id"])
    op.create_foreign_key(
        "fk_receipt_ref_receipt",
        "procurement_subcontracting_receipt_material_refs",
        "procurement_subcontracting_receipts",
        ["subcontracting_receipt_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_receipt_ref_transfer",
        "procurement_subcontracting_receipt_material_refs",
        "procurement_subcontracting_material_transfers",
        ["material_transfer_id"],
        ["id"],
    )


def downgrade() -> None:
    # Drop subcontracting_receipt_material_refs
    op.drop_constraint("fk_receipt_ref_transfer", "procurement_subcontracting_receipt_material_refs", type_="foreignkey")
    op.drop_constraint("fk_receipt_ref_receipt", "procurement_subcontracting_receipt_material_refs", type_="foreignkey")
    op.drop_index("ix_subcontracting_receipt_ref_transfer", "procurement_subcontracting_receipt_material_refs")
    op.drop_index("ix_subcontracting_receipt_ref_receipt", "procurement_subcontracting_receipt_material_refs")
    op.drop_table("procurement_subcontracting_receipt_material_refs")

    # Drop subcontracting_receipt_items
    op.drop_constraint("fk_subcontracting_receipt_item_receipt", "procurement_subcontracting_receipt_items", type_="foreignkey")
    op.drop_index("ix_subcontracting_receipt_items_receipt", "procurement_subcontracting_receipt_items")
    op.drop_table("procurement_subcontracting_receipt_items")

    # Drop subcontracting_receipts
    op.drop_constraint("fk_subcontracting_receipt_po", "procurement_subcontracting_receipts", type_="foreignkey")
    op.drop_index("ix_subcontracting_receipt_tenant_supplier", "procurement_subcontracting_receipts")
    op.drop_index("ix_subcontracting_receipt_tenant_po", "procurement_subcontracting_receipts")
    op.drop_index("ix_subcontracting_receipt_tenant_status", "procurement_subcontracting_receipts")
    op.drop_table("procurement_subcontracting_receipts")

    # Drop subcontracting_material_transfer_items
    op.drop_constraint("fk_subcontracting_mt_item_transfer", "procurement_subcontracting_material_transfer_items", type_="foreignkey")
    op.drop_index("ix_subcontracting_mt_items_transfer", "procurement_subcontracting_material_transfer_items")
    op.drop_table("procurement_subcontracting_material_transfer_items")

    # Drop subcontracting_material_transfers
    op.drop_constraint("fk_subcontracting_mt_po", "procurement_subcontracting_material_transfers", type_="foreignkey")
    op.drop_index("ix_subcontracting_mt_tenant_supplier", "procurement_subcontracting_material_transfers")
    op.drop_index("ix_subcontracting_mt_tenant_po", "procurement_subcontracting_material_transfers")
    op.drop_index("ix_subcontracting_mt_tenant_status", "procurement_subcontracting_material_transfers")
    op.drop_table("procurement_subcontracting_material_transfers")

    # Remove subcontracting metadata from purchase_order
    op.drop_column("procurement_purchase_orders", "expected_subcontracted_qty")
    op.drop_column("procurement_purchase_orders", "finished_goods_item_name")
    op.drop_column("procurement_purchase_orders", "finished_goods_item_code")
    op.drop_column("procurement_purchase_orders", "is_subcontracted")

    # Remove subcontractor flag from supplier
    op.drop_column("supplier", "is_subcontractor")
