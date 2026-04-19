"""change_lineage_pk_to_batch_id_first

Revision ID: ee6f8a7b3c1d
Revises: d3e8f9a1b2c4
Create Date: 2026-04-18
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "ee6f8a7b3c1d"
down_revision: str | Sequence[str] | None = "d3e8f9a1b2c4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _table_exists(schema_name: str, table_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return inspector.has_table(table_name, schema=schema_name)


def upgrade() -> None:
    if not _table_exists("raw_legacy", "canonical_record_lineage"):
        return

    op.execute(
        """
        DO $$
        DECLARE
            duplicate_count INTEGER;
        BEGIN
            SELECT COUNT(*)
            INTO duplicate_count
            FROM (
                SELECT 1
                FROM raw_legacy.canonical_record_lineage
                GROUP BY
                    batch_id,
                    tenant_id,
                    canonical_table,
                    source_table,
                    source_identifier
                HAVING COUNT(*) > 1
            ) AS duplicate_groups;

            IF duplicate_count > 0 THEN
                RAISE EXCEPTION
                    'PK migration would create duplicate key violations in raw_legacy.canonical_record_lineage. Found % duplicate tuples. Deduplicate before re-running this migration.',
                    duplicate_count;
            END IF;
        END
        $$;
        """
    )
    op.execute(
        """
        ALTER TABLE raw_legacy.canonical_record_lineage
        DROP CONSTRAINT IF EXISTS canonical_record_lineage_pkey,
        ADD PRIMARY KEY (batch_id, tenant_id, canonical_table, source_table, source_identifier);
        """
    )


def downgrade() -> None:
    if not _table_exists("raw_legacy", "canonical_record_lineage"):
        return

    op.execute(
        """
        ALTER TABLE raw_legacy.canonical_record_lineage
        DROP CONSTRAINT IF EXISTS canonical_record_lineage_pkey,
        ADD PRIMARY KEY (tenant_id, batch_id, canonical_table, canonical_id, source_table, source_identifier);
        """
    )
