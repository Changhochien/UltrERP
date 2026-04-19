"""add supplier invoice tables

Revision ID: 9f2b6c4d1e77
Revises: 5b3a41527547
Create Date: 2026-04-05 23:59:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "9f2b6c4d1e77"
down_revision: str | None = "5b3a41527547"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    supplier_invoice_status_enum = postgresql.ENUM(
        "open",
        "paid",
        "voided",
        name="supplier_invoice_status_enum",
        create_type=False,
    )
    supplier_invoice_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "supplier_invoices",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("supplier_id", sa.Uuid(), nullable=False),
        sa.Column("invoice_number", sa.String(length=100), nullable=False),
        sa.Column("invoice_date", sa.Date(), nullable=False),
        sa.Column("currency_code", sa.String(length=3), nullable=False),
        sa.Column("subtotal_amount", sa.Numeric(precision=20, scale=2), nullable=False),
        sa.Column("tax_amount", sa.Numeric(precision=20, scale=2), nullable=False),
        sa.Column("total_amount", sa.Numeric(precision=20, scale=2), nullable=False),
        sa.Column("status", supplier_invoice_status_enum, nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["supplier_id"],
            ["supplier.id"],
            name="fk_supplier_invoices_supplier_id_supplier",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_supplier_invoices_tenant_id",
        "supplier_invoices",
        ["tenant_id"],
    )
    op.create_index(
        "ix_supplier_invoices_tenant_invoice_date",
        "supplier_invoices",
        ["tenant_id", "invoice_date"],
    )
    op.create_index(
        "uq_supplier_invoices_tenant_supplier_invoice_number",
        "supplier_invoices",
        ["tenant_id", "supplier_id", "invoice_number"],
        unique=True,
    )

    op.create_table(
        "supplier_invoice_lines",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("supplier_invoice_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=True),
        sa.Column("product_code_snapshot", sa.String(length=100), nullable=True),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=18, scale=3), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=20, scale=2), nullable=False),
        sa.Column("subtotal_amount", sa.Numeric(precision=20, scale=2), nullable=False),
        sa.Column("tax_type", sa.Integer(), nullable=False),
        sa.Column("tax_rate", sa.Numeric(precision=6, scale=4), nullable=False),
        sa.Column("tax_amount", sa.Numeric(precision=20, scale=2), nullable=False),
        sa.Column("total_amount", sa.Numeric(precision=20, scale=2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["product.id"],
            name="fk_supplier_invoice_lines_product_id_product",
        ),
        sa.ForeignKeyConstraint(
            ["supplier_invoice_id"],
            ["supplier_invoices.id"],
            name="fk_supplier_invoice_lines_invoice_id_supplier_invoices",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_supplier_invoice_lines_tenant_id",
        "supplier_invoice_lines",
        ["tenant_id"],
    )
    op.create_index(
        "uq_supplier_invoice_lines_invoice_id_line_number",
        "supplier_invoice_lines",
        ["supplier_invoice_id", "line_number"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "uq_supplier_invoice_lines_invoice_id_line_number",
        table_name="supplier_invoice_lines",
    )
    op.drop_index("ix_supplier_invoice_lines_tenant_id", table_name="supplier_invoice_lines")
    op.drop_table("supplier_invoice_lines")

    op.drop_index(
        "uq_supplier_invoices_tenant_supplier_invoice_number",
        table_name="supplier_invoices",
    )
    op.drop_index(
        "ix_supplier_invoices_tenant_invoice_date",
        table_name="supplier_invoices",
    )
    op.drop_index("ix_supplier_invoices_tenant_id", table_name="supplier_invoices")
    op.drop_table("supplier_invoices")

    op.execute("DROP TYPE IF EXISTS supplier_invoice_status_enum")