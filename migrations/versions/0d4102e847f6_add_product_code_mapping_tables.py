"""add product code mapping tables

Revision ID: 0d4102e847f6
Revises: 84a7c8f1d2ab
Create Date: 2026-04-06 12:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0d4102e847f6"
down_revision: str | None = "84a7c8f1d2ab"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "CREATE TABLE raw_legacy.product_code_mapping ("
        "    id uuid NOT NULL DEFAULT gen_random_uuid(),"
        "    tenant_id uuid NOT NULL,"
        "    legacy_code varchar(100) NOT NULL,"
        "    target_code varchar(100),"
        "    resolution_type varchar(50) NOT NULL DEFAULT 'unresolved',"
        "    confidence numeric(5,2),"
        "    affected_row_count integer DEFAULT 0,"
        "    source_field varchar(100),"
        "    first_seen_batch_id varchar(100),"
        "    last_seen_batch_id varchar(100),"
        "    review_notes text,"
        "    approval_source varchar(50),"
        "    approved_by varchar(255),"
        "    approved_at timestamptz,"
        "    created_at timestamptz NOT NULL DEFAULT now(),"
        "    updated_at timestamptz DEFAULT now(),"
        "    PRIMARY KEY (id)"
        ")"
    )
    op.execute(
        "CREATE UNIQUE INDEX ix_pcm_tenant_legacy "
        "ON raw_legacy.product_code_mapping (tenant_id, legacy_code)"
    )
    op.execute(
        "CREATE INDEX ix_pcm_tenant_batch "
        "ON raw_legacy.product_code_mapping (tenant_id, last_seen_batch_id)"
    )

    op.execute(
        "CREATE TABLE raw_legacy.product_code_mapping_candidates ("
        "    id uuid NOT NULL DEFAULT gen_random_uuid(),"
        "    tenant_id uuid NOT NULL,"
        "    batch_id varchar(100) NOT NULL,"
        "    legacy_code varchar(100) NOT NULL,"
        "    candidate_code varchar(100),"
        "    confidence numeric(5,2),"
        "    heuristic varchar(100),"
        "    candidate_rank integer,"
        "    review_notes text,"
        "    created_at timestamptz NOT NULL DEFAULT now(),"
        "    PRIMARY KEY (id)"
        ")"
    )
    op.execute(
        "CREATE UNIQUE INDEX ix_pmc_tenant_batch_legacy_candidate "
        "ON raw_legacy.product_code_mapping_candidates "
        "(tenant_id, batch_id, legacy_code, candidate_code)"
    )
    op.execute(
        "CREATE INDEX ix_pmc_tenant_batch "
        "ON raw_legacy.product_code_mapping_candidates (tenant_id, batch_id)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS raw_legacy.ix_pmc_tenant_batch")
    op.execute("DROP INDEX IF EXISTS raw_legacy.ix_pmc_tenant_batch_legacy_candidate")
    op.execute("DROP TABLE IF EXISTS raw_legacy.product_code_mapping_candidates")
    op.execute("DROP INDEX IF EXISTS raw_legacy.ix_pcm_tenant_batch")
    op.execute("DROP INDEX IF EXISTS raw_legacy.ix_pcm_tenant_legacy")
    op.execute("DROP TABLE IF EXISTS raw_legacy.product_code_mapping")
