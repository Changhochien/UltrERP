"""add product category review tables

Revision ID: 9b2f3c4d5e6f
Revises: 1c2d3e4f5a6b
Create Date: 2026-04-14 16:30:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op


revision: str = "9b2f3c4d5e6f"
down_revision: str | None = "1c2d3e4f5a6b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "CREATE TABLE raw_legacy.product_category_override ("
        "    id uuid NOT NULL DEFAULT gen_random_uuid(),"
        "    tenant_id uuid NOT NULL,"
        "    legacy_code varchar(100) NOT NULL,"
        "    category varchar(100) NOT NULL,"
        "    review_notes text,"
        "    approval_source varchar(50),"
        "    approved_by varchar(255),"
        "    approved_at timestamptz,"
        "    first_seen_batch_id varchar(100),"
        "    last_seen_batch_id varchar(100),"
        "    created_at timestamptz NOT NULL DEFAULT now(),"
        "    updated_at timestamptz DEFAULT now(),"
        "    PRIMARY KEY (id)"
        ")"
    )
    op.execute(
        "CREATE UNIQUE INDEX ix_pco_tenant_legacy "
        "ON raw_legacy.product_category_override (tenant_id, legacy_code)"
    )
    op.execute(
        "CREATE INDEX ix_pco_tenant_batch "
        "ON raw_legacy.product_category_override (tenant_id, last_seen_batch_id)"
    )

    op.execute(
        "CREATE TABLE raw_legacy.product_category_review_candidates ("
        "    id uuid NOT NULL DEFAULT gen_random_uuid(),"
        "    tenant_id uuid NOT NULL,"
        "    batch_id varchar(100) NOT NULL,"
        "    legacy_code varchar(100) NOT NULL,"
        "    name varchar(255),"
        "    legacy_category varchar(255),"
        "    stock_kind varchar(20),"
        "    current_category varchar(100),"
        "    category_source varchar(50),"
        "    category_rule_id varchar(100),"
        "    category_confidence numeric(5,2),"
        "    review_reason varchar(50) NOT NULL,"
        "    source_table varchar(100),"
        "    source_row_number integer,"
        "    created_at timestamptz NOT NULL DEFAULT now(),"
        "    updated_at timestamptz DEFAULT now(),"
        "    PRIMARY KEY (id)"
        ")"
    )
    op.execute(
        "CREATE UNIQUE INDEX ix_pcrc_tenant_batch_legacy "
        "ON raw_legacy.product_category_review_candidates (tenant_id, batch_id, legacy_code)"
    )
    op.execute(
        "CREATE INDEX ix_pcrc_tenant_batch_reason "
        "ON raw_legacy.product_category_review_candidates (tenant_id, batch_id, review_reason)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS raw_legacy.ix_pcrc_tenant_batch_reason")
    op.execute("DROP INDEX IF EXISTS raw_legacy.ix_pcrc_tenant_batch_legacy")
    op.execute("DROP TABLE IF EXISTS raw_legacy.product_category_review_candidates")
    op.execute("DROP INDEX IF EXISTS raw_legacy.ix_pco_tenant_batch")
    op.execute("DROP INDEX IF EXISTS raw_legacy.ix_pco_tenant_legacy")
    op.execute("DROP TABLE IF EXISTS raw_legacy.product_category_override")