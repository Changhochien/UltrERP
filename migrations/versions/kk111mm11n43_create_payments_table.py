"""Create payments table.

Revision ID: kk111mm11n43
Revises: jj000ll00m32
Create Date: 2025-01-01 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "kk111mm11n43"
down_revision = "jj000ll00m32"
branch_labels = None
depends_on = None


def upgrade() -> None:
	op.create_table(
		"payments",
		sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
		sa.Column("tenant_id", UUID(as_uuid=True), nullable=False, index=True),
		sa.Column(
			"invoice_id",
			UUID(as_uuid=True),
			sa.ForeignKey("invoices.id", name="fk_payments_invoice_id_invoices", ondelete="RESTRICT"),
			nullable=True,
		),
		sa.Column(
			"customer_id",
			UUID(as_uuid=True),
			sa.ForeignKey("customers.id", name="fk_payments_customer_id_customers", ondelete="RESTRICT"),
			nullable=False,
		),
		sa.Column("payment_ref", sa.String(20), nullable=False),
		sa.Column("amount", sa.Numeric(20, 2), nullable=False),
		sa.Column("payment_method", sa.String(20), nullable=False),
		sa.Column("payment_date", sa.Date, nullable=False),
		sa.Column("reference_number", sa.String(100), nullable=True),
		sa.Column("notes", sa.Text, nullable=True),
		sa.Column("created_by", sa.String(100), nullable=False),
		sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
		sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
	)
	op.create_index(
		"uq_payments_tenant_payment_ref",
		"payments",
		["tenant_id", "payment_ref"],
		unique=True,
	)
	op.create_index(
		"ix_payments_tenant_invoice",
		"payments",
		["tenant_id", "invoice_id"],
	)
	op.create_index(
		"ix_payments_tenant_customer",
		"payments",
		["tenant_id", "customer_id"],
	)
	op.create_index(
		"ix_payments_tenant_date",
		"payments",
		["tenant_id", "payment_date"],
	)


def downgrade() -> None:
	op.drop_index("ix_payments_tenant_date", table_name="payments")
	op.drop_index("ix_payments_tenant_customer", table_name="payments")
	op.drop_index("ix_payments_tenant_invoice", table_name="payments")
	op.drop_index("uq_payments_tenant_payment_ref", table_name="payments")
	op.drop_table("payments")
