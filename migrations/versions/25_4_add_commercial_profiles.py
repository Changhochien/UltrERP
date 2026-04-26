"""Add commercial profile defaults to customer and supplier for Story 25-4.

Revision ID: 25_4_commercial_profiles
Revises: 25_3_payment_terms
Create Date: 2026-04-26

This migration adds:
- default_currency_code on customer and supplier
- payment_terms_template_id on customer and supplier
- currency_source and payment_terms_source on commercial documents
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = "25_4_commercial_profiles"
down_revision: Union[str, None] = "25_3_payment_terms"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # === Customer: Add commercial profile defaults ===
    op.add_column(
        "customers",
        sa.Column("default_currency_code", sa.String(length=3), nullable=True),
    )
    op.add_column(
        "customers",
        sa.Column(
            "payment_terms_template_id",
            UUID(as_uuid=True),
            nullable=True,
        ),
    )

    # Add foreign key for payment_terms_template_id on customers
    op.create_foreign_key(
        "fk_customers_payment_terms_template",
        "customers",
        "payment_terms_templates",
        ["payment_terms_template_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # === Supplier: Add commercial profile defaults ===
    op.add_column(
        "supplier",
        sa.Column("default_currency_code", sa.String(length=3), nullable=True),
    )
    op.add_column(
        "supplier",
        sa.Column(
            "payment_terms_template_id",
            UUID(as_uuid=True),
            nullable=True,
        ),
    )

    # Add foreign key for payment_terms_template_id on supplier
    op.create_foreign_key(
        "fk_supplier_payment_terms_template",
        "supplier",
        "payment_terms_templates",
        ["payment_terms_template_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # === Orders: Add source metadata fields ===
    op.add_column(
        "orders",
        sa.Column("currency_source", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column("payment_terms_source", sa.String(length=50), nullable=True),
    )

    # === CRM Quotations: Add source metadata fields ===
    op.add_column(
        "crm_quotations",
        sa.Column("currency_source", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "crm_quotations",
        sa.Column("payment_terms_source", sa.String(length=50), nullable=True),
    )

    # === Invoices: Add source metadata fields ===
    op.add_column(
        "invoices",
        sa.Column("currency_source", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "invoices",
        sa.Column("payment_terms_source", sa.String(length=50), nullable=True),
    )

    # === Supplier Invoices: Add source metadata fields ===
    op.add_column(
        "supplier_invoices",
        sa.Column("currency_source", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "supplier_invoices",
        sa.Column("payment_terms_source", sa.String(length=50), nullable=True),
    )

    # === Add indexes ===
    op.create_index(
        "ix_customers_default_currency",
        "customers",
        ["tenant_id", "default_currency_code"],
    )
    op.create_index(
        "ix_supplier_default_currency",
        "supplier",
        ["tenant_id", "default_currency_code"],
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_supplier_default_currency", table_name="supplier")
    op.drop_index("ix_customers_default_currency", table_name="customers")

    # Drop foreign keys
    op.drop_constraint("fk_supplier_payment_terms_template", "supplier", type_="foreignkey")
    op.drop_constraint("fk_customers_payment_terms_template", "customers", type_="foreignkey")

    # Drop columns from supplier invoices
    op.drop_column("supplier_invoices", "payment_terms_source")
    op.drop_column("supplier_invoices", "currency_source")

    # Drop columns from invoices
    op.drop_column("invoices", "payment_terms_source")
    op.drop_column("invoices", "currency_source")

    # Drop columns from quotations
    op.drop_column("crm_quotations", "payment_terms_source")
    op.drop_column("crm_quotations", "currency_source")

    # Drop columns from orders
    op.drop_column("orders", "payment_terms_source")
    op.drop_column("orders", "currency_source")

    # Drop columns from supplier
    op.drop_column("supplier", "payment_terms_template_id")
    op.drop_column("supplier", "default_currency_code")

    # Drop columns from customers
    op.drop_column("customers", "payment_terms_template_id")
    op.drop_column("customers", "default_currency_code")
