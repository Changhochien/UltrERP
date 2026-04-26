"""Add posting rules and document posting state tables (Epic 26 Story 26-4)

Revision ID: aa1322719555zz
Revises: aa1322719554zz
Create Date: 2026-04-26

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'aa1322719555zz'
down_revision = 'aa1322719554zz'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create document_type_enum
    document_type_enum = postgresql.ENUM(
        'customer_invoice', 'customer_payment',
        'supplier_invoice', 'supplier_payment',
        'journal_entry',
        name='document_type_enum', create_type=False
    )
    document_type_enum.create(op.get_bind(), checkfirst=True)
    
    # Create posting_status_enum
    posting_status_enum = postgresql.ENUM(
        'not_applicable', 'not_configured', 'pending',
        'posted', 'failed', 'reversed',
        name='posting_status_enum', create_type=False
    )
    posting_status_enum.create(op.get_bind(), checkfirst=True)
    
    # Create posting_rules table
    op.create_table(
        'posting_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('document_type', document_type_enum, nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, default=1),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('account_mappings', postgresql.JSONB(), nullable=False, default=dict),
        sa.Column('tax_account_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('write_off_account_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('created_by', sa.String(100), nullable=True),
    )
    op.create_index('ix_posting_rules_tenant_doc_type', 'posting_rules', ['tenant_id', 'document_type'], unique=True)
    op.create_index('ix_posting_rules_is_active', 'posting_rules', ['tenant_id', 'is_active'])
    
    # Add foreign keys for accounts
    op.create_foreign_key(
        'fk_posting_rules_tax_account',
        'posting_rules', 'accounts',
        ['tax_account_id'], ['id']
    )
    op.create_foreign_key(
        'fk_posting_rules_write_off_account',
        'posting_rules', 'accounts',
        ['write_off_account_id'], ['id']
    )
    
    # Create document_posting_states table
    op.create_table(
        'document_posting_states',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('document_type', document_type_enum, nullable=False),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', posting_status_enum, nullable=False, server_default='not_configured'),
        sa.Column('posting_rule_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('rule_version_at_posting', sa.Integer(), nullable=True),
        sa.Column('gl_entry_ids', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('reversed_by_state_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('reverses_state_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('posted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_doc_posting_state_doc', 'document_posting_states', ['document_type', 'document_id'], unique=True)
    op.create_index('ix_doc_posting_state_tenant', 'document_posting_states', ['tenant_id'])
    
    # Add foreign key for self-references
    op.create_foreign_key(
        'fk_doc_posting_reversed_by',
        'document_posting_states', 'document_posting_states',
        ['reversed_by_state_id'], ['id']
    )
    op.create_foreign_key(
        'fk_doc_posting_reverses',
        'document_posting_states', 'document_posting_states',
        ['reverses_state_id'], ['id']
    )
    op.create_foreign_key(
        'fk_doc_posting_rule',
        'document_posting_states', 'posting_rules',
        ['posting_rule_id'], ['id']
    )
    
    # Add posting_status column to gl_entries for reversal tracking
    op.add_column('gl_entries', sa.Column('is_reversal', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('gl_entries', sa.Column('reversed_entry_id', postgresql.UUID(as_uuid=True), nullable=True))


def downgrade() -> None:
    # Remove columns from gl_entries
    op.drop_column('gl_entries', 'reversed_entry_id')
    op.drop_column('gl_entries', 'is_reversal')
    
    # Drop document_posting_states table
    op.drop_table('document_posting_states')
    
    # Drop posting_rules table
    op.drop_table('posting_rules')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS posting_status_enum')
    op.execute('DROP TYPE IF EXISTS document_type_enum')
