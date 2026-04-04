"""Add immutability rules to audit_log table.

Revision ID: nn444pp44q76
Revises: mm333oo33p65
Create Date: 2025-08-01

"""

from alembic import op

revision = "nn444pp44q76"
down_revision = "mm333oo33p65"
branch_labels = None
depends_on = None


def upgrade() -> None:
	op.execute(
		"CREATE RULE audit_log_no_update AS ON UPDATE TO audit_log DO INSTEAD NOTHING;"
	)
	op.execute(
		"CREATE RULE audit_log_no_delete AS ON DELETE TO audit_log DO INSTEAD NOTHING;"
	)


def downgrade() -> None:
	op.execute("DROP RULE IF EXISTS audit_log_no_delete ON audit_log;")
	op.execute("DROP RULE IF EXISTS audit_log_no_update ON audit_log;")
