"""Convert tenant_id columns from varchar(50) to uuid

Revision ID: gg777ii77j09
Revises: ff666hh66i98
Create Date: 2025-07-17

"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = "gg777ii77j09"
down_revision: str | None = "ff666hh66i98"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Tables that need tenant_id converted from String(50) to UUID
_TABLES = [
	"warehouse",
	"product",
	"inventory_stock",
	"stock_adjustment",
	"stock_transfer_history",
	"reorder_alert",
	"supplier",
	"supplier_order",
	"audit_log",
]


def upgrade() -> None:
	for table in _TABLES:
		op.execute(
			f"ALTER TABLE {table} "
			f"ALTER COLUMN tenant_id TYPE uuid USING tenant_id::uuid"
		)


def downgrade() -> None:
	for table in _TABLES:
		op.execute(
			f"ALTER TABLE {table} "
			f"ALTER COLUMN tenant_id TYPE varchar(50) USING tenant_id::text"
		)
