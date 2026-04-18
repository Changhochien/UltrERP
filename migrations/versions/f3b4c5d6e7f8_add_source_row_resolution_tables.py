"""add_source_row_resolution_tables

Revision ID: f3b4c5d6e7f8
Revises: ee6f8a7b3c1d
Create Date: 2026-04-18
"""

from collections.abc import Sequence

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "f3b4c5d6e7f8"
down_revision: str | Sequence[str] | None = "ee6f8a7b3c1d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
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
                    source_identifier,
                    source_row_number
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
        ADD PRIMARY KEY (
            batch_id,
            tenant_id,
            canonical_table,
            source_table,
            source_identifier,
            source_row_number
        );
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS raw_legacy.source_row_resolution (
            tenant_id UUID NOT NULL,
            batch_id TEXT NOT NULL,
            source_table TEXT NOT NULL,
            source_identifier TEXT NOT NULL,
            source_row_number INTEGER NOT NULL,
            domain_name TEXT NOT NULL,
            status TEXT NOT NULL,
            holding_id UUID,
            canonical_table TEXT,
            canonical_id UUID,
            notes TEXT,
            import_run_id UUID NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (
                tenant_id,
                batch_id,
                source_table,
                source_identifier,
                source_row_number
            ),
            CONSTRAINT source_row_resolution_status_check CHECK (
                status IN ('holding', 'resolved', 'failed', 'retrying', 'repaired')
            )
        );
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS raw_legacy.source_row_resolution_events (
            event_id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL,
            batch_id TEXT NOT NULL,
            source_table TEXT NOT NULL,
            source_identifier TEXT NOT NULL,
            source_row_number INTEGER NOT NULL,
            domain_name TEXT NOT NULL,
            previous_status TEXT,
            new_status TEXT NOT NULL,
            holding_id UUID,
            canonical_table TEXT,
            canonical_id UUID,
            notes TEXT,
            import_run_id UUID NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT source_row_resolution_events_status_check CHECK (
                (
                    previous_status IS NULL
                    OR previous_status IN ('holding', 'resolved', 'failed', 'retrying', 'repaired')
                )
                AND new_status IN ('holding', 'resolved', 'failed', 'retrying', 'repaired')
            )
        );
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS source_row_resolution_status_idx
        ON raw_legacy.source_row_resolution (tenant_id, batch_id, status);
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS source_row_resolution_events_lookup_idx
        ON raw_legacy.source_row_resolution_events (
            tenant_id,
            batch_id,
            source_table,
            source_identifier,
            source_row_number,
            created_at
        );
        """
    )
    op.execute(
        """
        DO $$
        DECLARE
            duplicate_count INTEGER;
            overlap_count INTEGER;
        BEGIN
            SELECT COUNT(*)
            INTO duplicate_count
            FROM (
                SELECT 1
                FROM raw_legacy.canonical_record_lineage
                WHERE canonical_table <> '__holding__'
                GROUP BY
                    tenant_id,
                    batch_id,
                    source_table,
                    source_identifier,
                    source_row_number
                HAVING COUNT(*) > 1
            ) AS duplicate_groups;

            IF duplicate_count > 0 THEN
                RAISE EXCEPTION
                    'source_row_resolution backfill found % ambiguous canonical lineage identities. Resolve duplicate canonical targets per (tenant_id, batch_id, source_table, source_identifier, source_row_number) before re-running this migration.',
                    duplicate_count;
            END IF;

            SELECT COUNT(*)
            INTO overlap_count
            FROM (
                SELECT 1
                FROM raw_legacy.unsupported_history_holding AS holding
                JOIN raw_legacy.canonical_record_lineage AS lineage
                    ON lineage.tenant_id = holding.tenant_id
                    AND lineage.batch_id = holding.batch_id
                    AND lineage.source_table = holding.source_table
                    AND lineage.source_identifier = holding.source_identifier
                    AND lineage.source_row_number = holding.source_row_number
                    AND lineage.canonical_table <> '__holding__'
            ) AS overlap_groups;

            IF overlap_count > 0 THEN
                RAISE EXCEPTION
                    'source_row_resolution backfill found % identities present in both unsupported_history_holding and canonical_record_lineage. Resolve the conflicting rows before re-running this migration.',
                    overlap_count;
            END IF;
        END
        $$;
        """
    )
    op.execute(
        """
        INSERT INTO raw_legacy.source_row_resolution (
            tenant_id,
            batch_id,
            source_table,
            source_identifier,
            source_row_number,
            domain_name,
            status,
            holding_id,
            canonical_table,
            canonical_id,
            notes,
            import_run_id,
            created_at,
            updated_at
        )
        SELECT
            holding.tenant_id,
            holding.batch_id,
            holding.source_table,
            holding.source_identifier,
            holding.source_row_number,
            holding.domain_name,
            'holding',
            holding.id,
            NULL,
            NULL,
            holding.notes,
            holding.import_run_id,
            holding.created_at,
            holding.updated_at
        FROM raw_legacy.unsupported_history_holding AS holding
        ON CONFLICT (
            tenant_id,
            batch_id,
            source_table,
            source_identifier,
            source_row_number
        ) DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO raw_legacy.source_row_resolution (
            tenant_id,
            batch_id,
            source_table,
            source_identifier,
            source_row_number,
            domain_name,
            status,
            holding_id,
            canonical_table,
            canonical_id,
            notes,
            import_run_id,
            created_at,
            updated_at
        )
        SELECT
            lineage.tenant_id,
            lineage.batch_id,
            lineage.source_table,
            lineage.source_identifier,
            lineage.source_row_number,
            CASE
                WHEN lineage.source_table IN ('tbsprepay', 'tbsspay') THEN 'payment_history'
                WHEN lineage.source_table = 'tbsslipdtj' THEN 'receiving_audit'
                ELSE lineage.canonical_table
            END,
            'resolved',
            NULL,
            lineage.canonical_table,
            lineage.canonical_id,
            NULL,
            lineage.import_run_id,
            lineage.created_at,
            lineage.created_at
        FROM raw_legacy.canonical_record_lineage AS lineage
        WHERE lineage.canonical_table <> '__holding__'
        ON CONFLICT (
            tenant_id,
            batch_id,
            source_table,
            source_identifier,
            source_row_number
        ) DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO raw_legacy.source_row_resolution_events (
            event_id,
            tenant_id,
            batch_id,
            source_table,
            source_identifier,
            source_row_number,
            domain_name,
            previous_status,
            new_status,
            holding_id,
            canonical_table,
            canonical_id,
            notes,
            import_run_id,
            created_at
        )
        SELECT
            (
                SUBSTR(md5(CONCAT_WS(
                    '|',
                    'source-resolution-backfill',
                    'holding',
                    holding.tenant_id::text,
                    holding.batch_id,
                    holding.source_table,
                    holding.source_identifier,
                    holding.source_row_number::text,
                    holding.id::text,
                    holding.import_run_id::text
                )), 1, 8)
                || '-'
                || SUBSTR(md5(CONCAT_WS(
                    '|',
                    'source-resolution-backfill',
                    'holding',
                    holding.tenant_id::text,
                    holding.batch_id,
                    holding.source_table,
                    holding.source_identifier,
                    holding.source_row_number::text,
                    holding.id::text,
                    holding.import_run_id::text
                )), 9, 4)
                || '-'
                || SUBSTR(md5(CONCAT_WS(
                    '|',
                    'source-resolution-backfill',
                    'holding',
                    holding.tenant_id::text,
                    holding.batch_id,
                    holding.source_table,
                    holding.source_identifier,
                    holding.source_row_number::text,
                    holding.id::text,
                    holding.import_run_id::text
                )), 13, 4)
                || '-'
                || SUBSTR(md5(CONCAT_WS(
                    '|',
                    'source-resolution-backfill',
                    'holding',
                    holding.tenant_id::text,
                    holding.batch_id,
                    holding.source_table,
                    holding.source_identifier,
                    holding.source_row_number::text,
                    holding.id::text,
                    holding.import_run_id::text
                )), 17, 4)
                || '-'
                || SUBSTR(md5(CONCAT_WS(
                    '|',
                    'source-resolution-backfill',
                    'holding',
                    holding.tenant_id::text,
                    holding.batch_id,
                    holding.source_table,
                    holding.source_identifier,
                    holding.source_row_number::text,
                    holding.id::text,
                    holding.import_run_id::text
                )), 21, 12)
            )::uuid,
            holding.tenant_id,
            holding.batch_id,
            holding.source_table,
            holding.source_identifier,
            holding.source_row_number,
            holding.domain_name,
            NULL,
            'holding',
            holding.id,
            NULL,
            NULL,
            holding.notes,
            holding.import_run_id,
            holding.created_at
        FROM raw_legacy.unsupported_history_holding AS holding
        ON CONFLICT (event_id) DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO raw_legacy.source_row_resolution_events (
            event_id,
            tenant_id,
            batch_id,
            source_table,
            source_identifier,
            source_row_number,
            domain_name,
            previous_status,
            new_status,
            holding_id,
            canonical_table,
            canonical_id,
            notes,
            import_run_id,
            created_at
        )
        SELECT
            (
                SUBSTR(md5(CONCAT_WS(
                    '|',
                    'source-resolution-backfill',
                    'resolved',
                    lineage.tenant_id::text,
                    lineage.batch_id,
                    lineage.source_table,
                    lineage.source_identifier,
                    lineage.source_row_number::text,
                    lineage.canonical_table,
                    lineage.canonical_id::text,
                    lineage.import_run_id::text
                )), 1, 8)
                || '-'
                || SUBSTR(md5(CONCAT_WS(
                    '|',
                    'source-resolution-backfill',
                    'resolved',
                    lineage.tenant_id::text,
                    lineage.batch_id,
                    lineage.source_table,
                    lineage.source_identifier,
                    lineage.source_row_number::text,
                    lineage.canonical_table,
                    lineage.canonical_id::text,
                    lineage.import_run_id::text
                )), 9, 4)
                || '-'
                || SUBSTR(md5(CONCAT_WS(
                    '|',
                    'source-resolution-backfill',
                    'resolved',
                    lineage.tenant_id::text,
                    lineage.batch_id,
                    lineage.source_table,
                    lineage.source_identifier,
                    lineage.source_row_number::text,
                    lineage.canonical_table,
                    lineage.canonical_id::text,
                    lineage.import_run_id::text
                )), 13, 4)
                || '-'
                || SUBSTR(md5(CONCAT_WS(
                    '|',
                    'source-resolution-backfill',
                    'resolved',
                    lineage.tenant_id::text,
                    lineage.batch_id,
                    lineage.source_table,
                    lineage.source_identifier,
                    lineage.source_row_number::text,
                    lineage.canonical_table,
                    lineage.canonical_id::text,
                    lineage.import_run_id::text
                )), 17, 4)
                || '-'
                || SUBSTR(md5(CONCAT_WS(
                    '|',
                    'source-resolution-backfill',
                    'resolved',
                    lineage.tenant_id::text,
                    lineage.batch_id,
                    lineage.source_table,
                    lineage.source_identifier,
                    lineage.source_row_number::text,
                    lineage.canonical_table,
                    lineage.canonical_id::text,
                    lineage.import_run_id::text
                )), 21, 12)
            )::uuid,
            lineage.tenant_id,
            lineage.batch_id,
            lineage.source_table,
            lineage.source_identifier,
            lineage.source_row_number,
            CASE
                WHEN lineage.source_table IN ('tbsprepay', 'tbsspay') THEN 'payment_history'
                WHEN lineage.source_table = 'tbsslipdtj' THEN 'receiving_audit'
                ELSE lineage.canonical_table
            END,
            NULL,
            'resolved',
            NULL,
            lineage.canonical_table,
            lineage.canonical_id,
            NULL,
            lineage.import_run_id,
            lineage.created_at
        FROM raw_legacy.canonical_record_lineage AS lineage
        WHERE lineage.canonical_table <> '__holding__'
        ON CONFLICT (event_id) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS raw_legacy.source_row_resolution_events;
        """
    )
    op.execute(
        """
        DROP TABLE IF EXISTS raw_legacy.source_row_resolution;
        """
    )
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
                    'Downgrade cannot restore the previous canonical_record_lineage PK because % duplicate tuples exist once source_row_number is removed. Deduplicate before downgrading.',
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
        ADD PRIMARY KEY (
            batch_id,
            tenant_id,
            canonical_table,
            source_table,
            source_identifier
        );
        """
    )