"""normalize SALES_RESERVATION reason code enum label

Revision ID: 15d9e4c2b7a1
Revises: 14c8d2e6f1a3
Create Date: 2026-04-19

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "15d9e4c2b7a1"
down_revision = "14c8d2e6f1a3"
branch_labels = None
depends_on = None


def _enum_labels(enum_name: str) -> set[str]:
    rows = op.get_bind().execute(
        sa.text(
            """
            SELECT enumlabel
            FROM pg_enum
            JOIN pg_type ON pg_enum.enumtypid = pg_type.oid
            WHERE pg_type.typname = :enum_name
            ORDER BY enumsortorder
            """
        ),
        {"enum_name": enum_name},
    )
    return {str(row[0]) for row in rows}


def upgrade() -> None:
    labels = _enum_labels("reason_code_enum")
    with op.get_context().autocommit_block():
        if "sales_reservation" in labels and "SALES_RESERVATION" not in labels:
            op.execute(
                "ALTER TYPE reason_code_enum RENAME VALUE 'sales_reservation' TO 'SALES_RESERVATION'"
            )
        elif "SALES_RESERVATION" not in labels:
            op.execute(
                "ALTER TYPE reason_code_enum ADD VALUE IF NOT EXISTS 'SALES_RESERVATION'"
            )


def downgrade() -> None:
    labels = _enum_labels("reason_code_enum")
    with op.get_context().autocommit_block():
        if "SALES_RESERVATION" in labels and "sales_reservation" not in labels:
            op.execute(
                "ALTER TYPE reason_code_enum RENAME VALUE 'SALES_RESERVATION' TO 'sales_reservation'"
            )