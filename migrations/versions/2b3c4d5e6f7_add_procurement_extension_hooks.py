"""Add procurement extension hooks (Story 24-5).

This migration adds nullable reference fields for later procurement capabilities:
- RFQ and SupplierQuotation: contract_reference
- PurchaseOrder: blanket_order_reference_id, landed_cost_reference_id

Revision ID: 2b3c4d5e6f7
Revises: 1a2b3c4d5e6f
Create Date: 2026-04-24
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = "2b3c4d5e6f7"
down_revision = "1a2b3c4d5e6f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add contract_reference to RFQ
    op.add_column(
        "procurement_rfqs",
        sa.Column("contract_reference", sa.String(200), nullable=True),
    )

    # Add contract_reference to SupplierQuotation
    op.add_column(
        "procurement_supplier_quotations",
        sa.Column("contract_reference", sa.String(200), nullable=True),
    )

    # Add extension references to PurchaseOrder
    op.add_column(
        "procurement_purchase_orders",
        sa.Column(
            "blanket_order_reference_id",
            sa.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.add_column(
        "procurement_purchase_orders",
        sa.Column(
            "landed_cost_reference_id",
            sa.UUID(as_uuid=True),
            nullable=True,
        ),
    )

    # Add indexes for common queries
    op.create_index(
        "ix_procurement_rfqs_contract",
        "procurement_rfqs",
        ["tenant_id", "contract_reference"],
        unique=False,
    )
    op.create_index(
        "ix_procurement_sq_contract",
        "procurement_supplier_quotations",
        ["tenant_id", "contract_reference"],
        unique=False,
    )
    op.create_index(
        "ix_procurement_po_blanket",
        "procurement_purchase_orders",
        ["tenant_id", "blanket_order_reference_id"],
        unique=False,
    )
    op.create_index(
        "ix_procurement_po_landed_cost",
        "procurement_purchase_orders",
        ["tenant_id", "landed_cost_reference_id"],
        unique=False,
    )


def downgrade() -> None:
    # Remove indexes
    op.drop_index("ix_procurement_po_landed_cost", table_name="procurement_purchase_orders")
    op.drop_index("ix_procurement_po_blanket", table_name="procurement_purchase_orders")
    op.drop_index("ix_procurement_sq_contract", table_name="procurement_supplier_quotations")
    op.drop_index("ix_procurement_rfqs_contract", table_name="procurement_rfqs")

    # Remove columns
    op.drop_column("procurement_purchase_orders", "landed_cost_reference_id")
    op.drop_column("procurement_purchase_orders", "blanket_order_reference_id")
    op.drop_column("procurement_supplier_quotations", "contract_reference")
    op.drop_column("procurement_rfqs", "contract_reference")
