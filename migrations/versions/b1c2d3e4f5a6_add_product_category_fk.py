"""add product category foreign key

Revision ID: b1c2d3e4f5a6
Revises: a3d4e5f6b7c8
Create Date: 2026-04-18
"""

from __future__ import annotations

import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "b1c2d3e4f5a6"
down_revision = "a3d4e5f6b7c8"
branch_labels = None
depends_on = None


product_table = sa.table(
    "product",
    sa.column("id", postgresql.UUID(as_uuid=True)),
    sa.column("tenant_id", postgresql.UUID(as_uuid=True)),
    sa.column("category", sa.String(length=200)),
    sa.column("category_id", postgresql.UUID(as_uuid=True)),
)

category_table = sa.table(
    "category",
    sa.column("id", postgresql.UUID(as_uuid=True)),
    sa.column("tenant_id", postgresql.UUID(as_uuid=True)),
    sa.column("name", sa.String(length=200)),
    sa.column("is_active", sa.Boolean()),
)


def upgrade() -> None:
    op.add_column(
        "product",
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_product_category_id", "product", ["category_id"], unique=False)
    op.create_foreign_key(
        "fk_product_category_id_category",
        "product",
        "category",
        ["category_id"],
        ["id"],
    )

    connection = op.get_bind()

    connection.execute(
        sa.update(product_table)
        .where(sa.func.btrim(product_table.c.category) == "")
        .values(category=None)
    )

    rows = connection.execute(
        sa.select(
            product_table.c.tenant_id,
            sa.func.btrim(product_table.c.category).label("category_name"),
        )
        .where(product_table.c.category.is_not(None))
        .distinct()
    ).all()

    category_ids: dict[tuple[uuid.UUID, str], uuid.UUID] = {}
    for row in rows:
        tenant_id = row.tenant_id
        category_name = row.category_name
        if tenant_id is None or not category_name:
            continue

        lookup_key = (tenant_id, category_name.casefold())
        if lookup_key in category_ids:
            continue

        existing = connection.execute(
            sa.select(category_table.c.id, category_table.c.name)
            .where(
                category_table.c.tenant_id == tenant_id,
                sa.func.lower(category_table.c.name) == category_name.lower(),
            )
            .limit(1)
        ).first()
        if existing is not None:
            category_ids[lookup_key] = existing.id
            canonical_name = existing.name
        else:
            canonical_name = category_name
            category_id = uuid.uuid4()
            connection.execute(
                sa.insert(category_table).values(
                    id=category_id,
                    tenant_id=tenant_id,
                    name=canonical_name,
                    is_active=True,
                )
            )
            category_ids[lookup_key] = category_id

        connection.execute(
            sa.update(product_table)
            .where(
                product_table.c.tenant_id == tenant_id,
                sa.func.lower(sa.func.btrim(product_table.c.category)) == category_name.lower(),
            )
            .values(
                category_id=category_ids[lookup_key],
                category=canonical_name,
            )
        )


def downgrade() -> None:
    op.drop_constraint("fk_product_category_id_category", "product", type_="foreignkey")
    op.drop_index("ix_product_category_id", table_name="product")
    op.drop_column("product", "category_id")
