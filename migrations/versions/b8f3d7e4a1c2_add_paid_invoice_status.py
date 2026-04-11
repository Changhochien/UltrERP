"""add paid invoice status and migrate existing data

Revision ID: b8f3d7e4a1c2
Revises: a9c3d7e4f1b2
Create Date: 2026-04-11
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "b8f3d7e4a1c2"
down_revision = "a9c3d7e4f1b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create the enum type with all three values (issued, paid, voided)
    invoice_status_enum = sa.Enum("issued", "paid", "voided", name="invoice_status_enum", create_constraint=True)
    invoice_status_enum.create(op.get_bind(), checkfirst=True)

    # Alter the status column to use the enum type
    op.execute("ALTER TABLE invoices ALTER COLUMN status TYPE invoice_status_enum USING status::text::invoice_status_enum")


def downgrade() -> None:
    # Change back to varchar
    op.execute("ALTER TABLE invoices ALTER COLUMN status TYPE VARCHAR(20) USING status::text")
    # Drop the enum type
    op.execute("DROP TYPE IF EXISTS invoice_status_enum")
