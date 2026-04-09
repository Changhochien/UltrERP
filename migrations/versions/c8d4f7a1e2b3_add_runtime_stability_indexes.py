"""add runtime stability indexes

Revision ID: c8d4f7a1e2b3
Revises: 9f2b6c4d1e77
Create Date: 2026-04-07 12:00:00.000000
"""

from alembic import op

revision: str = "c8d4f7a1e2b3"
down_revision: str | None = "9f2b6c4d1e77"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
            "ix_reorder_alert_tenant_status_warehouse "
            "ON reorder_alert (tenant_id, status, warehouse_id)"
        )
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
            "ix_audit_log_tenant_entity_created_at "
            "ON audit_log (tenant_id, entity_type, entity_id, created_at)"
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_audit_log_tenant_entity_created_at")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_reorder_alert_tenant_status_warehouse")