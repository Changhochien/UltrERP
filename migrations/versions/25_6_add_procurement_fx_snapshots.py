"""Add procurement FX snapshot fields for Epic 25 parity.

Revision ID: 25_6_procurement_fx
Revises: 25_4_commercial_profiles
Create Date: 2026-04-26
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "25_6_procurement_fx"
down_revision: Union[str, None] = "25_4_commercial_profiles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "procurement_supplier_quotations",
        sa.Column("conversion_rate", sa.Numeric(20, 10), nullable=True, server_default="1.0000000000"),
    )
    op.add_column(
        "procurement_supplier_quotations",
        sa.Column("conversion_effective_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "procurement_supplier_quotations",
        sa.Column("applied_rate_source", sa.String(50), nullable=True),
    )
    op.add_column(
        "procurement_supplier_quotations",
        sa.Column("currency_source", sa.String(50), nullable=True),
    )
    op.add_column(
        "procurement_supplier_quotations",
        sa.Column("base_subtotal_amount", sa.Numeric(14, 2), nullable=True),
    )
    op.add_column(
        "procurement_supplier_quotations",
        sa.Column("base_tax_amount", sa.Numeric(14, 2), nullable=True),
    )

    for column_name, column_type in (
        ("base_unit_price", sa.Numeric(14, 4)),
        ("base_subtotal_amount", sa.Numeric(14, 2)),
        ("base_tax_amount", sa.Numeric(14, 2)),
        ("base_total_amount", sa.Numeric(14, 2)),
    ):
        op.add_column(
            "procurement_supplier_quotation_items",
            sa.Column(column_name, column_type, nullable=True),
        )

    op.add_column(
        "procurement_purchase_orders",
        sa.Column("conversion_rate", sa.Numeric(20, 10), nullable=True, server_default="1.0000000000"),
    )
    op.add_column(
        "procurement_purchase_orders",
        sa.Column("conversion_effective_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "procurement_purchase_orders",
        sa.Column("applied_rate_source", sa.String(50), nullable=True),
    )
    op.add_column(
        "procurement_purchase_orders",
        sa.Column("currency_source", sa.String(50), nullable=True),
    )
    op.add_column(
        "procurement_purchase_orders",
        sa.Column("base_subtotal_amount", sa.Numeric(14, 2), nullable=True),
    )
    op.add_column(
        "procurement_purchase_orders",
        sa.Column("base_tax_amount", sa.Numeric(14, 2), nullable=True),
    )

    for column_name, column_type in (
        ("base_unit_price", sa.Numeric(14, 4)),
        ("base_subtotal_amount", sa.Numeric(14, 2)),
        ("base_tax_amount", sa.Numeric(14, 2)),
        ("base_total_amount", sa.Numeric(14, 2)),
    ):
        op.add_column(
            "procurement_purchase_order_items",
            sa.Column(column_name, column_type, nullable=True),
        )

    op.create_index(
        "ix_procurement_sq_currency",
        "procurement_supplier_quotations",
        ["tenant_id", "currency"],
    )
    op.create_index(
        "ix_procurement_po_currency",
        "procurement_purchase_orders",
        ["tenant_id", "currency"],
    )


def downgrade() -> None:
    op.drop_index("ix_procurement_po_currency", table_name="procurement_purchase_orders")
    op.drop_index("ix_procurement_sq_currency", table_name="procurement_supplier_quotations")

    for column_name in (
        "base_total_amount",
        "base_tax_amount",
        "base_subtotal_amount",
        "base_unit_price",
    ):
        op.drop_column("procurement_purchase_order_items", column_name)

    for column_name in (
        "base_tax_amount",
        "base_subtotal_amount",
        "currency_source",
        "applied_rate_source",
        "conversion_effective_date",
        "conversion_rate",
    ):
        op.drop_column("procurement_purchase_orders", column_name)

    for column_name in (
        "base_total_amount",
        "base_tax_amount",
        "base_subtotal_amount",
        "base_unit_price",
    ):
        op.drop_column("procurement_supplier_quotation_items", column_name)

    for column_name in (
        "base_tax_amount",
        "base_subtotal_amount",
        "currency_source",
        "applied_rate_source",
        "conversion_effective_date",
        "conversion_rate",
    ):
        op.drop_column("procurement_supplier_quotations", column_name)
