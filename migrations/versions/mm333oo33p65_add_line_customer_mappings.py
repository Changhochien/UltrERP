"""Add LINE customer mappings table.

Revision ID: mm333oo33p65
Revises: ll222nn22o54
Create Date: 2025-08-01

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "mm333oo33p65"
down_revision = "ll222nn22o54"
branch_labels = None
depends_on = None


def upgrade() -> None:
	op.create_table(
		"line_customer_mappings",
		sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
		sa.Column("tenant_id", UUID(as_uuid=True), nullable=False, index=True),
		sa.Column("line_user_id", sa.String(64), nullable=False),
		sa.Column(
			"customer_id",
			UUID(as_uuid=True),
			sa.ForeignKey("customers.id", name="fk_line_mapping_customer_id", ondelete="CASCADE"),
			nullable=False,
		),
		sa.Column("display_name", sa.String(200), nullable=True),
		sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
		sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
	)
	op.create_index(
		"uq_line_mapping_tenant_user",
		"line_customer_mappings",
		["tenant_id", "line_user_id"],
		unique=True,
	)


def downgrade() -> None:
	op.drop_table("line_customer_mappings")
