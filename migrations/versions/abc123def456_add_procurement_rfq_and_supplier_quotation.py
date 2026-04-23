"""add procurement rfq and supplier quotation

Revision ID: abc123def456
Revises: 7b9d2c4e6f1a
Create Date: 2026-04-23 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "abc123def456"
down_revision: str | None = "7b9d2c4e6f1a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # procurement_rfqs
    # ------------------------------------------------------------------
    op.create_table(
        "procurement_rfqs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="draft"),
        sa.Column("company", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="TWD"),
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("schedule_date", sa.Date(), nullable=True),
        sa.Column("terms_and_conditions", sa.Text(), nullable=False, server_default=""),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("supplier_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("quotes_received", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_procurement_rfqs_tenant_id", "procurement_rfqs", ["tenant_id"])
    op.create_index("ix_procurement_rfqs_tenant_status", "procurement_rfqs", ["tenant_id", "status"])
    op.create_index("ix_procurement_rfqs_tenant_schedule_date", "procurement_rfqs", ["tenant_id", "schedule_date"])

    # ------------------------------------------------------------------
    # procurement_rfq_items
    # ------------------------------------------------------------------
    op.create_table(
        "procurement_rfq_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("rfq_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("idx", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("item_code", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("item_name", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("qty", sa.Numeric(precision=14, scale=3), nullable=False, server_default="0"),
        sa.Column("uom", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("warehouse", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["rfq_id"], ["procurement_rfqs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_procurement_rfq_items_rfq", "procurement_rfq_items", ["rfq_id"])
    op.create_index("ix_procurement_rfq_items_tenant", "procurement_rfq_items", ["tenant_id"])

    # ------------------------------------------------------------------
    # procurement_rfq_suppliers
    # ------------------------------------------------------------------
    op.create_table(
        "procurement_rfq_suppliers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("rfq_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("supplier_id", sa.Uuid(), nullable=True),
        sa.Column("supplier_name", sa.String(length=200), nullable=False),
        sa.Column("contact_email", sa.String(length=254), nullable=False, server_default=""),
        sa.Column("quote_status", sa.String(length=24), nullable=False, server_default="pending"),
        sa.Column("quotation_id", sa.Uuid(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["rfq_id"], ["procurement_rfqs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_procurement_rfq_suppliers_rfq", "procurement_rfq_suppliers", ["rfq_id"])
    op.create_index("ix_procurement_rfq_suppliers_supplier", "procurement_rfq_suppliers", ["tenant_id", "supplier_id"])

    # ------------------------------------------------------------------
    # procurement_supplier_quotations
    # ------------------------------------------------------------------
    op.create_table(
        "procurement_supplier_quotations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="draft"),
        sa.Column("rfq_id", sa.Uuid(), nullable=True),
        sa.Column("supplier_id", sa.Uuid(), nullable=True),
        sa.Column("supplier_name", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("company", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="TWD"),
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("valid_till", sa.Date(), nullable=True),
        sa.Column("lead_time_days", sa.Integer(), nullable=True),
        sa.Column("delivery_date", sa.Date(), nullable=True),
        sa.Column("subtotal", sa.Numeric(precision=14, scale=2), nullable=False, server_default="0"),
        sa.Column("total_taxes", sa.Numeric(precision=14, scale=2), nullable=False, server_default="0"),
        sa.Column("grand_total", sa.Numeric(precision=14, scale=2), nullable=False, server_default="0"),
        sa.Column("base_grand_total", sa.Numeric(precision=14, scale=2), nullable=False, server_default="0"),
        sa.Column("taxes", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("contact_person", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("contact_email", sa.String(length=254), nullable=False, server_default=""),
        sa.Column("terms_and_conditions", sa.Text(), nullable=False, server_default=""),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("comparison_base_total", sa.Numeric(precision=14, scale=2), nullable=False, server_default="0"),
        sa.Column("is_awarded", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["rfq_id"], ["procurement_rfqs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_procurement_sq_tenant_id", "procurement_supplier_quotations", ["tenant_id"])
    op.create_index("ix_procurement_sq_tenant_status", "procurement_supplier_quotations", ["tenant_id", "status"])
    op.create_index("ix_procurement_sq_tenant_rfq", "procurement_supplier_quotations", ["tenant_id", "rfq_id"])
    op.create_index("ix_procurement_sq_tenant_supplier", "procurement_supplier_quotations", ["tenant_id", "supplier_id"])
    op.create_index("ix_procurement_sq_tenant_validity", "procurement_supplier_quotations", ["tenant_id", "valid_till"])

    # ------------------------------------------------------------------
    # procurement_supplier_quotation_items
    # ------------------------------------------------------------------
    op.create_table(
        "procurement_supplier_quotation_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("quotation_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("idx", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rfq_item_id", sa.Uuid(), nullable=True),
        sa.Column("item_code", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("item_name", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("qty", sa.Numeric(precision=14, scale=3), nullable=False, server_default="0"),
        sa.Column("uom", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("unit_rate", sa.Numeric(precision=14, scale=4), nullable=False, server_default="0"),
        sa.Column("amount", sa.Numeric(precision=14, scale=2), nullable=False, server_default="0"),
        sa.Column("tax_rate", sa.Numeric(precision=6, scale=3), nullable=False, server_default="0"),
        sa.Column("tax_amount", sa.Numeric(precision=14, scale=2), nullable=False, server_default="0"),
        sa.Column("tax_code", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("normalized_unit_rate", sa.Numeric(precision=14, scale=4), nullable=False, server_default="0"),
        sa.Column("normalized_amount", sa.Numeric(precision=14, scale=2), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["quotation_id"], ["procurement_supplier_quotations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_procurement_sq_items_quotation", "procurement_supplier_quotation_items", ["quotation_id"])
    op.create_index("ix_procurement_sq_items_tenant", "procurement_supplier_quotation_items", ["tenant_id"])

    # ------------------------------------------------------------------
    # procurement_awards
    # ------------------------------------------------------------------
    op.create_table(
        "procurement_awards",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("rfq_id", sa.Uuid(), nullable=False),
        sa.Column("quotation_id", sa.Uuid(), nullable=False),
        sa.Column("awarded_supplier_name", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("awarded_total", sa.Numeric(precision=14, scale=2), nullable=False, server_default="0"),
        sa.Column("awarded_currency", sa.String(length=3), nullable=False, server_default="TWD"),
        sa.Column("awarded_lead_time_days", sa.Integer(), nullable=True),
        sa.Column("awarded_by", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("awarded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("po_created", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("po_reference", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["rfq_id"], ["procurement_rfqs.id"]),
        sa.ForeignKeyConstraint(["quotation_id"], ["procurement_supplier_quotations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_procurement_awards_rfq", "procurement_awards", ["rfq_id"])
    op.create_index("ix_procurement_awards_tenant", "procurement_awards", ["tenant_id", "rfq_id"])


def downgrade() -> None:
    op.drop_table("procurement_awards")
    op.drop_table("procurement_supplier_quotation_items")
    op.drop_table("procurement_supplier_quotations")
    op.drop_table("procurement_rfq_suppliers")
    op.drop_table("procurement_rfq_items")
    op.drop_table("procurement_rfqs")
