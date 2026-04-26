"""Add payment terms template and schedule tables for Story 25-3.

Revision ID: 25_3_payment_terms
Revises: 25_2_doc_currency
Create Date: 2026-04-26

This migration adds:
- PaymentTermsTemplate: Reusable payment term definitions
- PaymentTermsTemplateDetail: Installment schedule rows
- PaymentSchedule: Generated schedule rows on commercial documents
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = "25_3_payment_terms"
down_revision: Union[str, None] = "25_2_doc_currency"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # === Payment Terms Template ===
    op.create_table(
        "payment_terms_templates",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("template_name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "allocate_payment_based_on_payment_terms",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("legacy_code", sa.String(length=20), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "template_name", name="uq_payment_terms_templates_tenant_name"),
    )
    op.create_index(
        "ix_payment_terms_templates_active",
        "payment_terms_templates",
        ["tenant_id", "is_active"],
    )

    # === Payment Terms Template Detail ===
    op.create_table(
        "payment_terms_template_details",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("template_id", UUID(as_uuid=True), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column(
            "invoice_portion",
            sa.Numeric(precision=6, scale=2),
            nullable=False,
            server_default=sa.text("100.00"),
        ),
        sa.Column("credit_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("credit_months", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("discount_percent", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column("discount_validity_days", sa.Integer(), nullable=True),
        sa.Column("mode_of_payment", sa.String(length=50), nullable=True),
        sa.Column("description", sa.String(length=200), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["payment_terms_templates.id"],
            name="fk_payment_terms_template_details_template",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("template_id", "row_number", name="ix_payment_terms_template_details_template_row"),
    )

    # === Payment Schedule ===
    op.create_table(
        "payment_schedules",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("document_type", sa.String(length=50), nullable=False),
        sa.Column("document_id", UUID(as_uuid=True), nullable=False),
        sa.Column("template_id", UUID(as_uuid=True), nullable=True),
        sa.Column("template_detail_id", UUID(as_uuid=True), nullable=True),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column(
            "invoice_portion",
            sa.Numeric(precision=6, scale=2),
            nullable=False,
            server_default=sa.text("100.00"),
        ),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("payment_amount", sa.Numeric(precision=20, scale=2), nullable=False),
        sa.Column("outstanding_amount", sa.Numeric(precision=20, scale=2), nullable=False),
        sa.Column(
            "paid_amount",
            sa.Numeric(precision=20, scale=2),
            nullable=False,
            server_default=sa.text("0.00"),
        ),
        sa.Column("discount_percent", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column("discount_validity_days", sa.Integer(), nullable=True),
        sa.Column("discount_amount", sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column(
            "is_paid",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("paid_date", sa.Date(), nullable=True),
        sa.Column("mode_of_payment", sa.String(length=50), nullable=True),
        sa.Column("description", sa.String(length=200), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["payment_terms_templates.id"],
            name="fk_payment_schedules_template",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["template_detail_id"],
            ["payment_terms_template_details.id"],
            name="fk_payment_schedules_template_detail",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_payment_schedules_tenant_document",
        "payment_schedules",
        ["tenant_id", "document_type", "document_id"],
    )
    op.create_index(
        "ix_payment_schedules_due_date",
        "payment_schedules",
        ["tenant_id", "due_date"],
    )


def downgrade() -> None:
    op.drop_table("payment_schedules")
    op.drop_table("payment_terms_template_details")
    op.drop_table("payment_terms_templates")
