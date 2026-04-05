"""add supplier payment tables

Revision ID: 84a7c8f1d2ab
Revises: 9f2b6c4d1e77
Create Date: 2026-04-06 01:58:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "84a7c8f1d2ab"
down_revision: str | None = "9f2b6c4d1e77"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    supplier_payment_kind_enum = sa.Enum(
        "prepayment",
        "special_payment",
        "adjustment",
        name="supplier_payment_kind_enum",
        create_constraint=True,
    )
    supplier_payment_kind_enum.create(op.get_bind(), checkfirst=True)

    supplier_payment_status_enum = sa.Enum(
        "unapplied",
        "partially_applied",
        "applied",
        "voided",
        name="supplier_payment_status_enum",
        create_constraint=True,
    )
    supplier_payment_status_enum.create(op.get_bind(), checkfirst=True)

    supplier_payment_allocation_kind_enum = sa.Enum(
        "invoice_settlement",
        "prepayment_application",
        "reversal",
        name="supplier_payment_allocation_kind_enum",
        create_constraint=True,
    )
    supplier_payment_allocation_kind_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "supplier_payments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("supplier_id", sa.Uuid(), nullable=False),
        sa.Column("payment_number", sa.String(length=100), nullable=False),
        sa.Column("payment_kind", supplier_payment_kind_enum, nullable=False),
        sa.Column("status", supplier_payment_status_enum, nullable=False),
        sa.Column("currency_code", sa.String(length=3), nullable=False),
        sa.Column("payment_date", sa.Date(), nullable=False),
        sa.Column("gross_amount", sa.Numeric(precision=20, scale=2), nullable=False),
        sa.Column("payment_method", sa.String(length=50), nullable=True),
        sa.Column("reference_number", sa.String(length=100), nullable=True),
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
            name="fk_supplier_payments_supplier_id_supplier",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_supplier_payments_tenant_id", "supplier_payments", ["tenant_id"])
    op.create_index(
        "ix_supplier_payments_tenant_payment_date",
        "supplier_payments",
        ["tenant_id", "payment_date"],
    )
    op.create_index(
        "ix_supplier_payments_tenant_status",
        "supplier_payments",
        ["tenant_id", "status"],
    )
    op.create_index(
        "uq_supplier_payments_tenant_supplier_payment_number",
        "supplier_payments",
        ["tenant_id", "supplier_id", "payment_number"],
        unique=True,
    )

    op.create_table(
        "supplier_payment_allocations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("supplier_payment_id", sa.Uuid(), nullable=False),
        sa.Column("supplier_invoice_id", sa.Uuid(), nullable=False),
        sa.Column("allocation_date", sa.Date(), nullable=False),
        sa.Column("applied_amount", sa.Numeric(precision=20, scale=2), nullable=False),
        sa.Column("allocation_kind", supplier_payment_allocation_kind_enum, nullable=False),
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
            ["supplier_invoice_id"],
            ["supplier_invoices.id"],
            name="fk_supplier_payment_allocations_invoice_id_supplier_invoices",
        ),
        sa.ForeignKeyConstraint(
            ["supplier_payment_id"],
            ["supplier_payments.id"],
            name="fk_supplier_payment_allocations_payment_id_supplier_payments",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_supplier_payment_allocations_tenant_id",
        "supplier_payment_allocations",
        ["tenant_id"],
    )
    op.create_index(
        "ix_supplier_payment_allocations_tenant_invoice",
        "supplier_payment_allocations",
        ["tenant_id", "supplier_invoice_id"],
    )
    op.create_index(
        "ix_supplier_payment_allocations_tenant_payment",
        "supplier_payment_allocations",
        ["tenant_id", "supplier_payment_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_supplier_payment_allocations_tenant_payment",
        table_name="supplier_payment_allocations",
    )
    op.drop_index(
        "ix_supplier_payment_allocations_tenant_invoice",
        table_name="supplier_payment_allocations",
    )
    op.drop_index(
        "ix_supplier_payment_allocations_tenant_id",
        table_name="supplier_payment_allocations",
    )
    op.drop_table("supplier_payment_allocations")

    op.drop_index(
        "uq_supplier_payments_tenant_supplier_payment_number",
        table_name="supplier_payments",
    )
    op.drop_index("ix_supplier_payments_tenant_status", table_name="supplier_payments")
    op.drop_index(
        "ix_supplier_payments_tenant_payment_date",
        table_name="supplier_payments",
    )
    op.drop_index("ix_supplier_payments_tenant_id", table_name="supplier_payments")
    op.drop_table("supplier_payments")

    supplier_payment_allocation_kind_enum = sa.Enum(
        "invoice_settlement",
        "prepayment_application",
        "reversal",
        name="supplier_payment_allocation_kind_enum",
        create_constraint=True,
    )
    supplier_payment_allocation_kind_enum.drop(op.get_bind(), checkfirst=True)

    supplier_payment_status_enum = sa.Enum(
        "unapplied",
        "partially_applied",
        "applied",
        "voided",
        name="supplier_payment_status_enum",
        create_constraint=True,
    )
    supplier_payment_status_enum.drop(op.get_bind(), checkfirst=True)

    supplier_payment_kind_enum = sa.Enum(
        "prepayment",
        "special_payment",
        "adjustment",
        name="supplier_payment_kind_enum",
        create_constraint=True,
    )
    supplier_payment_kind_enum.drop(op.get_bind(), checkfirst=True)