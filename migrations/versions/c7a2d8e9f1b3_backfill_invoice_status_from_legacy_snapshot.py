"""backfill invoice status from legacy_header_snapshot

Revision ID: c7a2d8e9f1b3
Revises: b8f3d7e4a1c2
Create Date: 2026-04-11

Corrects invoice status for imported records where source_status was
captured in legacy_header_snapshot but was not mapped to the
canonical status during import.
"""

from __future__ import annotations

from alembic import op


revision = "c7a2d8e9f1b3"
down_revision = "b8f3d7e4a1c2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Update invoice status based on legacy_header_snapshot.source_status.

    Only updates rows where:
    - legacy_header_snapshot is not null
    - source_status is not null and not empty
    - current status is 'issued' (the incorrectly-set default)
    """
    op.execute(
        """
        UPDATE invoices
        SET status = CASE
            WHEN UPPER(TRIM(legacy_header_snapshot->>'source_status'))
                IN ('A', 'PAID', 'CLEARED', 'CLOSED', 'DONE', '2')
                THEN 'paid'
            WHEN UPPER(TRIM(legacy_header_snapshot->>'source_status'))
                IN ('3', 'VOID', 'VOIDED', 'CANCELLED', 'CANCEL')
                THEN 'voided'
            WHEN UPPER(TRIM(legacy_header_snapshot->>'source_status'))
                IN ('1', 'N', 'ACTIVE', 'ISSUED', 'OPEN', '')
                THEN 'issued'
            ELSE status
        END
        WHERE legacy_header_snapshot IS NOT NULL
          AND (legacy_header_snapshot->>'source_status') IS NOT NULL
          AND status = 'issued'
        """
    )


def downgrade() -> None:
    """Revert: set all invoices with legacy snapshots back to issued."""
    op.execute(
        """
        UPDATE invoices
        SET status = 'issued'
        WHERE legacy_header_snapshot IS NOT NULL
          AND (legacy_header_snapshot->>'source_status') IS NOT NULL
          AND status IN ('paid', 'voided')
        """
    )
