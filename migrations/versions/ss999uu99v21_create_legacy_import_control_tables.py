"""Create legacy import control tables.

Revision ID: ss999uu99v21
Revises: rr888tt88u10
Create Date: 2026-04-05

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "ss999uu99v21"
down_revision: str | None = "rr888tt88u10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
	op.execute("CREATE SCHEMA IF NOT EXISTS raw_legacy")
	op.create_table(
		"legacy_import_runs",
		sa.Column("id", sa.Uuid(), nullable=False),
		sa.Column("tenant_id", sa.Uuid(), nullable=False),
		sa.Column("batch_id", sa.String(length=120), nullable=False),
		sa.Column("source_path", sa.Text(), nullable=False),
		sa.Column("target_schema", sa.String(length=63), nullable=False, server_default=sa.text("'raw_legacy'")),
		sa.Column("requested_tables", sa.JSON(), nullable=True),
		sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'running'")),
		sa.Column("error_message", sa.Text(), nullable=True),
		sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
		sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
		sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
		sa.PrimaryKeyConstraint("id"),
		sa.UniqueConstraint("tenant_id", "batch_id", name="uq_legacy_import_runs_tenant_batch"),
	)
	op.create_index("ix_legacy_import_runs_tenant_id", "legacy_import_runs", ["tenant_id"])
	op.create_table(
		"legacy_import_table_runs",
		sa.Column("id", sa.Uuid(), nullable=False),
		sa.Column("run_id", sa.Uuid(), nullable=False),
		sa.Column("table_name", sa.String(length=120), nullable=False),
		sa.Column("source_file", sa.Text(), nullable=False),
		sa.Column("expected_row_count", sa.Integer(), nullable=True),
		sa.Column("loaded_row_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
		sa.Column("column_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
		sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'running'")),
		sa.Column("error_message", sa.Text(), nullable=True),
		sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
		sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
		sa.ForeignKeyConstraint(["run_id"], ["legacy_import_runs.id"], name="fk_legacy_import_table_runs_run_id_legacy_import_runs"),
		sa.PrimaryKeyConstraint("id"),
		sa.UniqueConstraint("run_id", "table_name", name="uq_legacy_import_table_runs_run_table"),
	)
	op.create_index("ix_legacy_import_table_runs_run_id", "legacy_import_table_runs", ["run_id"])


def downgrade() -> None:
	op.drop_index("ix_legacy_import_table_runs_run_id", table_name="legacy_import_table_runs")
	op.drop_table("legacy_import_table_runs")
	op.drop_index("ix_legacy_import_runs_tenant_id", table_name="legacy_import_runs")
	op.drop_table("legacy_import_runs")
	op.execute("DROP SCHEMA IF EXISTS raw_legacy CASCADE")