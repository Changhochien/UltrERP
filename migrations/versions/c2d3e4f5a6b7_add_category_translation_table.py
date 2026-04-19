"""add category translation table

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-04-18
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "c2d3e4f5a6b7"
down_revision = "b1c2d3e4f5a6"
branch_labels = None
depends_on = None


category_table = sa.table(
    "category",
    sa.column("id", postgresql.UUID(as_uuid=True)),
    sa.column("name", sa.String(length=200)),
)

category_translation_table = sa.table(
    "category_translation",
    sa.column("id", postgresql.UUID(as_uuid=True)),
    sa.column("category_id", postgresql.UUID(as_uuid=True)),
    sa.column("locale", sa.String(length=10)),
    sa.column("name", sa.String(length=200)),
)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "category_translation" not in existing_tables:
        op.create_table(
            "category_translation",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("locale", sa.String(length=10), nullable=False),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.ForeignKeyConstraint(["category_id"], ["category.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "uq_category_translation_category_locale",
            "category_translation",
            ["category_id", "locale"],
            unique=True,
        )
        op.create_index(
            "ix_category_translation_locale",
            "category_translation",
            ["locale"],
            unique=False,
        )

    rows = bind.execute(
        sa.select(category_table.c.id, category_table.c.name)
    ).all()
    existing_en_ids = {
        row[0]
        for row in bind.execute(
            sa.select(category_translation_table.c.category_id).where(
                category_translation_table.c.locale == "en"
            )
        ).all()
    }

    for category_id, name in rows:
        if category_id in existing_en_ids or not name:
            continue
        bind.execute(
            sa.insert(category_translation_table).values(
                id=sa.text("gen_random_uuid()"),
                category_id=category_id,
                locale="en",
                name=name,
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    if "category_translation" in existing_tables:
        op.drop_index("ix_category_translation_locale", table_name="category_translation")
        op.drop_index("uq_category_translation_category_locale", table_name="category_translation")
        op.drop_table("category_translation")
