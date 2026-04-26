"""Add bank accounts, bank transactions, and dunning notices (Epic 26 Story 26-5)

Revision ID: aa1322719556zz
Revises: aa1322719555zz
Create Date: 2026-04-26

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'aa1322719556zz'
down_revision = 'aa1322719555zz'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create bank_tx_status_enum
    bank_tx_status_enum = postgresql.ENUM(
        'unmatched', 'suggested', 'matched', 'reconciled', 'excluded',
        name='bank_tx_status_enum', create_type=False
    )
    bank_tx_status_enum.create(op.get_bind(), checkfirst=True)
    
    # Create dunning_status_enum
    dunning_status_enum = postgresql.ENUM(
        'draft', 'open', 'resolved', 'cancelled',
        name='dunning_status_enum', create_type=False
    )
    dunning_status_enum.create(op.get_bind(), checkfirst=True)
    
    # Create bank_accounts table
    op.create_table(
        'bank_accounts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('account_name', sa.String(255), nullable=False),
        sa.Column('account_number', sa.String(100), nullable=False),
        sa.Column('bank_name', sa.String(255), nullable=True),
        sa.Column('bank_code', sa.String(50), nullable=True),
        sa.Column('currency_code', sa.String(3), nullable=False, server_default='TWD'),
        sa.Column('opening_balance', sa.Numeric(20, 6), nullable=False, server_default='0'),
        sa.Column('current_balance', sa.Numeric(20, 6), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('created_by', sa.String(100), nullable=True),
    )
    op.create_index('ix_bank_accounts_tenant', 'bank_accounts', ['tenant_id'])
    op.create_index('ix_bank_accounts_tenant_account_number', 'bank_accounts', ['tenant_id', 'account_number'], unique=True)
    
    # Create bank_transactions table
    op.create_table(
        'bank_transactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('bank_account_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('bank_accounts.id'), nullable=False),
        sa.Column('import_batch_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('import_file_name', sa.String(500), nullable=True),
        sa.Column('import_row_number', sa.Integer(), nullable=True),
        sa.Column('imported_by', sa.String(100), nullable=True),
        sa.Column('imported_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('transaction_date', sa.Date(), nullable=False),
        sa.Column('value_date', sa.Date(), nullable=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('reference_number', sa.String(255), nullable=True),
        sa.Column('debit', sa.Numeric(20, 6), nullable=False, server_default='0'),
        sa.Column('credit', sa.Numeric(20, 6), nullable=False, server_default='0'),
        sa.Column('signed_amount', sa.Numeric(20, 6), nullable=True),
        sa.Column('currency_code', sa.String(3), nullable=False, server_default='TWD'),
        sa.Column('base_amount', sa.Numeric(20, 6), nullable=True),
        sa.Column('status', bank_tx_status_enum, nullable=False, server_default='unmatched'),
        sa.Column('suggestions', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_bank_tx_tenant_date', 'bank_transactions', ['tenant_id', 'transaction_date'])
    op.create_index('ix_bank_tx_tenant_bank', 'bank_transactions', ['tenant_id', 'bank_account_id'])
    op.create_index('ix_bank_tx_status', 'bank_transactions', ['tenant_id', 'status'])
    
    # Create bank_transaction_matches table
    op.create_table(
        'bank_transaction_matches',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('bank_transaction_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('bank_transactions.id'), nullable=False),
        sa.Column('voucher_type', sa.String(50), nullable=False),
        sa.Column('voucher_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('matched_amount', sa.Numeric(20, 6), nullable=False),
        sa.Column('match_type', sa.String(20), nullable=False, server_default='manual'),
        sa.Column('match_confidence', sa.Numeric(5, 2), nullable=True),
        sa.Column('reference_matched', sa.String(255), nullable=True),
        sa.Column('is_reconciled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('reconciled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reconciled_by', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_bank_tx_match_tx', 'bank_transaction_matches', ['bank_transaction_id'])
    op.create_index('ix_bank_tx_match_voucher', 'bank_transaction_matches', ['voucher_type', 'voucher_id'])
    
    # Create dunning_notices table
    op.create_table(
        'dunning_notices',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('invoice_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('invoices.id'), nullable=True),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('notice_number', sa.String(50), nullable=False, unique=True),
        sa.Column('notice_date', sa.Date(), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('status', dunning_status_enum, nullable=False, server_default='draft'),
        sa.Column('outstanding_amount', sa.Numeric(20, 6), nullable=False),
        sa.Column('fee_amount', sa.Numeric(20, 6), nullable=False, server_default='0'),
        sa.Column('interest_amount', sa.Numeric(20, 6), nullable=False, server_default='0'),
        sa.Column('total_amount', sa.Numeric(20, 6), nullable=False),
        sa.Column('notice_text', sa.Text(), nullable=False),
        sa.Column('reminder_level', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('outcome', sa.String(50), nullable=True),
        sa.Column('outcome_notes', sa.Text(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_by', sa.String(100), nullable=True),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_dunning_tenant_status', 'dunning_notices', ['tenant_id', 'status'])
    op.create_index('ix_dunning_customer', 'dunning_notices', ['tenant_id', 'customer_id'])
    
    # Add foreign key for customer
    op.create_foreign_key(
        'fk_dunning_customer',
        'dunning_notices', 'customers',
        ['customer_id'], ['id']
    )


def downgrade() -> None:
    op.drop_table('dunning_notices')
    op.drop_table('bank_transaction_matches')
    op.drop_table('bank_transactions')
    op.drop_table('bank_accounts')
    
    op.execute('DROP TYPE IF EXISTS dunning_status_enum')
    op.execute('DROP TYPE IF EXISTS bank_tx_status_enum')
