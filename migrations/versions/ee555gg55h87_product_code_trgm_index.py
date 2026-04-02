"""add product code trigram index for partial search

Revision ID: ee555gg55h87
Revises: dd444ff44f76
Create Date: 2026-07-10 14:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "ee555gg55h87"
down_revision: str | None = "dd444ff44f76"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
	op.execute(
		"CREATE INDEX ix_product_code_trgm ON product "
		"USING GIN (code gin_trgm_ops)"
	)


def downgrade() -> None:
	op.drop_index("ix_product_code_trgm", table_name="product")
