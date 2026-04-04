"""Replace silent audit_log rules with trigger-based rejection.

Revision ID: qq777ss77t09
Revises: pp666rr66s98
Create Date: 2026-04-03

"""

from alembic import op

revision = "qq777ss77t09"
down_revision = "pp666rr66s98"
branch_labels = None
depends_on = None


IMMUTABLE_FUNCTION_SQL = """
CREATE OR REPLACE FUNCTION audit_log_reject_mutation()
RETURNS trigger AS $$
BEGIN
	RAISE EXCEPTION 'audit_log is append-only; % is not allowed', lower(TG_OP)
		USING ERRCODE = '55000';
END;
$$ LANGUAGE plpgsql;
"""


def upgrade() -> None:
	op.execute("DROP RULE IF EXISTS audit_log_no_delete ON audit_log;")
	op.execute("DROP RULE IF EXISTS audit_log_no_update ON audit_log;")
	op.execute("DROP TRIGGER IF EXISTS audit_log_immutable ON audit_log;")
	op.execute(IMMUTABLE_FUNCTION_SQL)
	op.execute(
		"""
		CREATE TRIGGER audit_log_immutable
		BEFORE UPDATE OR DELETE ON audit_log
		FOR EACH ROW
		EXECUTE FUNCTION audit_log_reject_mutation();
		"""
	)


def downgrade() -> None:
	op.execute("DROP TRIGGER IF EXISTS audit_log_immutable ON audit_log;")
	op.execute("DROP FUNCTION IF EXISTS audit_log_reject_mutation();")
	op.execute(
		"CREATE RULE audit_log_no_update AS ON UPDATE TO audit_log DO INSTEAD NOTHING;"
	)
	op.execute(
		"CREATE RULE audit_log_no_delete AS ON DELETE TO audit_log DO INSTEAD NOTHING;"
	)