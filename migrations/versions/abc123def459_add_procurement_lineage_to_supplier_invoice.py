"""Add procurement lineage and mismatch fields to supplier invoice.

Story 24-4: Procurement Lineage and Three-Way-Match Readiness
Adds stable UUID references and mismatch/tolerance fields to supplier_invoices
and supplier_invoice_lines for later three-way-match and AP posting workflows.

This migration is additive only - no existing data is modified.
"""

from __future__ import annotations

import uuid
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers
revision = "abc123def459"
down_revision = "abc123def458"  # Previous procurement migration
branch_labels = ()
depends_on = ()


def upgrade() -> None:
    # ------------------------------------------------------------------
    # Supplier Invoice Header - add purchase_order_id for navigation
    # ------------------------------------------------------------------
    op.add_column(
        "supplier_invoices",
        sa.Column("purchase_order_id", UUID(as_uuid=True), nullable=True, index=True),
    )

    # ------------------------------------------------------------------
    # Supplier Invoice Lines - add procurement lineage references
    # ------------------------------------------------------------------
    op.add_column(
        "supplier_invoice_lines",
        sa.Column("rfq_item_id", UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "supplier_invoice_lines",
        sa.Column("supplier_quotation_item_id", UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "supplier_invoice_lines",
        sa.Column("purchase_order_line_id", UUID(as_uuid=True), nullable=True, index=True),
    )
    op.add_column(
        "supplier_invoice_lines",
        sa.Column("goods_receipt_line_id", UUID(as_uuid=True), nullable=True, index=True),
    )

    # ------------------------------------------------------------------
    # Supplier Invoice Lines - add mismatch and tolerance-ready fields
    # ------------------------------------------------------------------
    op.add_column(
        "supplier_invoice_lines",
        sa.Column("reference_quantity", sa.Numeric(18, 3), nullable=True),
    )
    op.add_column(
        "supplier_invoice_lines",
        sa.Column("reference_unit_price", sa.Numeric(20, 2), nullable=True),
    )
    op.add_column(
        "supplier_invoice_lines",
        sa.Column("reference_total_amount", sa.Numeric(20, 2), nullable=True),
    )
    op.add_column(
        "supplier_invoice_lines",
        sa.Column("quantity_variance", sa.Numeric(18, 3), nullable=True),
    )
    op.add_column(
        "supplier_invoice_lines",
        sa.Column("unit_price_variance", sa.Numeric(20, 2), nullable=True),
    )
    op.add_column(
        "supplier_invoice_lines",
        sa.Column("total_amount_variance", sa.Numeric(20, 2), nullable=True),
    )
    op.add_column(
        "supplier_invoice_lines",
        sa.Column("quantity_variance_pct", sa.Numeric(8, 4), nullable=True),
    )
    op.add_column(
        "supplier_invoice_lines",
        sa.Column("unit_price_variance_pct", sa.Numeric(8, 4), nullable=True),
    )
    op.add_column(
        "supplier_invoice_lines",
        sa.Column("total_amount_variance_pct", sa.Numeric(8, 4), nullable=True),
    )
    op.add_column(
        "supplier_invoice_lines",
        sa.Column("comparison_basis_snapshot", sa.JSON(), nullable=True),
    )

    # ------------------------------------------------------------------
    # Add mismatch_status enum type and column
    # ------------------------------------------------------------------
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'procurement_mismatch_status_enum') THEN
                CREATE TYPE procurement_mismatch_status_enum AS ENUM (
                    'not_checked',
                    'within_tolerance',
                    'outside_tolerance',
                    'review_required'
                );
            END IF;
        END$$;
        """
    )

    op.add_column(
        "supplier_invoice_lines",
        sa.Column(
            "mismatch_status",
            sa.Enum(
                "not_checked",
                "within_tolerance",
                "outside_tolerance",
                "review_required",
                name="procurement_mismatch_status_enum",
            ),
            nullable=False,
            server_default="not_checked",
        ),
    )

    # ------------------------------------------------------------------
    # Tolerance rule references
    # ------------------------------------------------------------------
    op.add_column(
        "supplier_invoice_lines",
        sa.Column("tolerance_rule_code", sa.String(50), nullable=True),
    )
    op.add_column(
        "supplier_invoice_lines",
        sa.Column("tolerance_rule_id", UUID(as_uuid=True), nullable=True),
    )


def downgrade() -> None:
    # Remove columns from supplier_invoice_lines
    op.drop_column("supplier_invoice_lines", "tolerance_rule_id")
    op.drop_column("supplier_invoice_lines", "tolerance_rule_code")
    op.drop_column("supplier_invoice_lines", "mismatch_status")
    op.drop_column("supplier_invoice_lines", "comparison_basis_snapshot")
    op.drop_column("supplier_invoice_lines", "total_amount_variance_pct")
    op.drop_column("supplier_invoice_lines", "unit_price_variance_pct")
    op.drop_column("supplier_invoice_lines", "quantity_variance_pct")
    op.drop_column("supplier_invoice_lines", "total_amount_variance")
    op.drop_column("supplier_invoice_lines", "unit_price_variance")
    op.drop_column("supplier_invoice_lines", "quantity_variance")
    op.drop_column("supplier_invoice_lines", "reference_total_amount")
    op.drop_column("supplier_invoice_lines", "reference_unit_price")
    op.drop_column("supplier_invoice_lines", "reference_quantity")
    op.drop_column("supplier_invoice_lines", "goods_receipt_line_id")
    op.drop_column("supplier_invoice_lines", "purchase_order_line_id")
    op.drop_column("supplier_invoice_lines", "supplier_quotation_item_id")
    op.drop_column("supplier_invoice_lines", "rfq_item_id")

    # Remove column from supplier_invoices
    op.drop_column("supplier_invoices", "purchase_order_id")

    # Drop enum type
    op.execute("DROP TYPE IF EXISTS procurement_mismatch_status_enum;")
