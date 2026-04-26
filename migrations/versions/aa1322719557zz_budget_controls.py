"""Add budget tables (Epic 26 Story 26-6)

Revision ID: aa1322719557zz
Revises: aa1322719556zz
Create Date: 2026-04-26

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'aa1322719557zz'
down_revision = 'aa1322719556zz'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enums
    budget_status_enum = postgresql.ENUM(
        'draft', 'submitted', 'cancelled',
        name='budget_status_enum', create_type=False
    )
    budget_status_enum.create(op.get_bind(), checkfirst=True)
    
    budget_check_action_enum = postgresql.ENUM(
        'ignore', 'warn', 'stop',
        name='budget_check_action_enum', create_type=False
    )
    budget_check_action_enum.create(op.get_bind(), checkfirst=True)
    
    # Create budgets table
    op.create_table(
        'budgets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('budget_number', sa.String(50), nullable=False, unique=True),
        sa.Column('budget_name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('fiscal_year', sa.String(20), nullable=False),
        sa.Column('scope_type', sa.String(50), nullable=True),
        sa.Column('scope_ref', sa.String(255), nullable=True),
        sa.Column('status', budget_status_enum, nullable=False, server_default='draft'),
        sa.Column('expense_action', budget_check_action_enum, nullable=False, server_default='warn'),
        sa.Column('revision_of_budget_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_latest', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('total_amount', sa.Numeric(20, 6), nullable=False),
        sa.Column('currency_code', sa.String(3), nullable=False, server_default='TWD'),
        sa.Column('submitted_by', sa.String(100), nullable=True),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancelled_by', sa.String(100), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_budgets_tenant_year', 'budgets', ['tenant_id', 'fiscal_year'])
    op.create_index('ix_budgets_tenant_scope', 'budgets', ['tenant_id', 'scope_type', 'scope_ref'])
    
    # Add self-reference for revision
    op.create_foreign_key(
        'fk_budget_revision',
        'budgets', 'budgets',
        ['revision_of_budget_id'], ['id']
    )
    
    # Create budget_periods table
    op.create_table(
        'budget_periods',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('budget_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('budgets.id'), nullable=False),
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date(), nullable=False),
        sa.Column('period_name', sa.String(50), nullable=False),
        sa.Column('allocated_amount', sa.Numeric(20, 6), nullable=False),
        sa.Column('distribution_type', sa.String(20), nullable=False, server_default='manual'),
        sa.Column('revision_of_period_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_budget_period_budget', 'budget_periods', ['budget_id'])
    op.create_index('ix_budget_period_tenant_budget_month', 'budget_periods', ['tenant_id', 'budget_id', 'period_start'], unique=True)
    
    # Create budget_account_allocations table
    op.create_table(
        'budget_account_allocations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('budget_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('budgets.id'), nullable=False),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('accounts.id'), nullable=False),
        sa.Column('action', budget_check_action_enum, nullable=False, server_default='warn'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_budget_account_budget', 'budget_account_allocations', ['budget_id'])
    op.create_index('ix_budget_account_account', 'budget_account_allocations', ['account_id'])


def downgrade() -> None:
    op.drop_table('budget_account_allocations')
    op.drop_table('budget_periods')
    op.drop_table('budgets')
    
    op.execute('DROP TYPE IF EXISTS budget_check_action_enum')
    op.execute('DROP TYPE IF EXISTS budget_status_enum')
