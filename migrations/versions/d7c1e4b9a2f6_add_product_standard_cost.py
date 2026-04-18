"""add product standard_cost

Revision ID: d7c1e4b9a2f6
Revises: d3e8f9a1b2c4
Create Date: 2026-04-18

"""

from alembic import op
import sqlalchemy as sa


revision = "d7c1e4b9a2f6"
down_revision = "d3e8f9a1b2c4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    column_names = {column["name"] for column in inspector.get_columns("product")}
    if "standard_cost" not in column_names:
        op.add_column(
            "product",
            sa.Column("standard_cost", sa.Numeric(precision=19, scale=4), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    column_names = {column["name"] for column in inspector.get_columns("product")}
    if "standard_cost" in column_names:
        op.drop_column("product", "standard_cost")
