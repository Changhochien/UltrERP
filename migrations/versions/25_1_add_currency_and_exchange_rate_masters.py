"""Add currency and exchange rate master tables.

Revision ID: 25_1_add_currency_and_exchange_rate_masters
Revises: latest
Create Date: 2026-04-26

This migration adds the currency and exchange rate master tables for Epic 25
multi-currency foundation. These tables provide:
- Tenant-scoped currency master with code, symbol, precision, and active state
- Exchange rate master with effective-date lookup support

The migration is designed to be backward compatible with existing currency_code
fields on transactional documents.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "25_1_currency_masters"
down_revision: Union[str, None] = "abc123def460"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create currencies table
    op.create_table(
        "currencies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=3), nullable=False),
        sa.Column("symbol", sa.String(length=10), nullable=False),
        sa.Column("decimal_places", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_base_currency", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for currencies
    op.create_index(
        "ix_currencies_tenant_active",
        "currencies",
        ["tenant_id", "is_active"],
        unique=False,
    )
    op.create_index(
        "uq_currencies_tenant_code",
        "currencies",
        ["tenant_id", "code"],
        unique=True,
    )
    op.create_index(
        "uq_currencies_one_base_per_tenant",
        "currencies",
        ["tenant_id"],
        unique=True,
        postgresql_where=sa.text("is_base_currency"),
    )

    # Create exchange_rates table
    op.create_table(
        "exchange_rates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_currency_code", sa.String(length=3), nullable=False),
        sa.Column("target_currency_code", sa.String(length=3), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column(
            "rate",
            sa.Numeric(precision=20, scale=10),
            nullable=False,
        ),
        sa.Column("is_inverse", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("rate_source", sa.String(length=50), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "source_currency_code <> target_currency_code",
            name="ck_exchange_rates_distinct_currency_pair",
        ),
        sa.CheckConstraint("rate > 0", name="ck_exchange_rates_positive_rate"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for exchange_rates
    op.create_index(
        "ix_exchange_rates_tenant_source_target_date",
        "exchange_rates",
        ["tenant_id", "source_currency_code", "target_currency_code", "effective_date"],
        unique=False,
    )
    op.create_index(
        "uq_exchange_rates_tenant_source_target_date",
        "exchange_rates",
        ["tenant_id", "source_currency_code", "target_currency_code", "effective_date"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("exchange_rates")
    op.drop_table("currencies")
