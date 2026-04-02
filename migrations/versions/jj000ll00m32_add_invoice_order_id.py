"""Add order_id to invoices table.

Revision ID: jj000ll00m32
Revises: ii999kk99l21
Create Date: 2025-01-01 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "jj000ll00m32"
down_revision = "ii999kk99l21"
branch_labels = None
depends_on = None


def upgrade() -> None:
	op.add_column(
		"invoices",
		sa.Column(
			"order_id",
			UUID(as_uuid=True),
			sa.ForeignKey("orders.id", name="fk_invoices_order_id_orders", ondelete="SET NULL"),
			nullable=True,
		),
	)
	op.create_index("ix_invoices_order_id", "invoices", ["order_id"])


def downgrade() -> None:
	op.drop_index("ix_invoices_order_id", table_name="invoices")
	op.drop_column("invoices", "order_id")
