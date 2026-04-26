"""Tests for document auto-posting (Epic 26 Story 26-4)."""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.models.account import Account, AccountRootType, AccountType, _ROOT_TYPE_TO_REPORT_TYPE
from common.models.fiscal_year import FiscalYear, FiscalYearStatus
from common.models.gl_entry import GLEntry
from common.models.posting_rule import (
    DocumentType,
    PostingRule,
    PostingStatus,
)
from common.models.supplier_invoice import SupplierInvoiceStatus
from backend.domains.accounting.posting import (
    ensure_posting_state,
    get_document_posting_status,
    get_open_fiscal_year,
    get_posting_rule,
    post_customer_invoice,
    post_supplier_invoice,
    reverse_document_posting,
)
from tests.db import isolated_async_session


@pytest_asyncio.fixture
async def db() -> AsyncSession:
    """Provide an isolated database session for each test."""
    async with isolated_async_session() as session:
        yield session


@pytest.fixture
async def tenant_id(db: AsyncSession) -> uuid.UUID:
    """Get or create a test tenant."""
    from common.database import DEFAULT_TENANT_ID
    return DEFAULT_TENANT_ID


@pytest.fixture
async def fiscal_year(db: AsyncSession, tenant_id: uuid.UUID) -> FiscalYear:
    """Create an open fiscal year for testing."""
    fy = FiscalYear(
        tenant_id=tenant_id,
        label="FY2026",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        status=FiscalYearStatus.OPEN.value,
    )
    db.add(fy)
    await db.flush()
    return fy


@pytest.fixture
async def accounts(db: AsyncSession, tenant_id: uuid.UUID) -> dict[str, Account]:
    """Create test accounts for posting."""
    accounts = {}
    
    # Asset accounts
    cash = Account(
        tenant_id=tenant_id,
        account_number="1110",
        account_name="Cash",
        root_type=AccountRootType.ASSET,
        report_type=_ROOT_TYPE_TO_REPORT_TYPE[AccountRootType.ASSET],
        account_type=AccountType.CASH,
        is_group=False,
    )
    db.add(cash)
    accounts["cash"] = cash
    
    receivable = Account(
        tenant_id=tenant_id,
        account_number="1120",
        account_name="Accounts Receivable",
        root_type=AccountRootType.ASSET,
        report_type=_ROOT_TYPE_TO_REPORT_TYPE[AccountRootType.ASSET],
        account_type=AccountType.RECEIVABLE,
        is_group=False,
    )
    db.add(receivable)
    accounts["receivable"] = receivable
    
    payable = Account(
        tenant_id=tenant_id,
        account_number="2110",
        account_name="Accounts Payable",
        root_type=AccountRootType.LIABILITY,
        report_type=_ROOT_TYPE_TO_REPORT_TYPE[AccountRootType.LIABILITY],
        account_type=AccountType.PAYABLE,
        is_group=False,
    )
    db.add(payable)
    accounts["payable"] = payable
    
    revenue = Account(
        tenant_id=tenant_id,
        account_number="4100",
        account_name="Sales Revenue",
        root_type=AccountRootType.INCOME,
        report_type=_ROOT_TYPE_TO_REPORT_TYPE[AccountRootType.INCOME],
        account_type=AccountType.SALES,
        is_group=False,
    )
    db.add(revenue)
    accounts["revenue"] = revenue
    
    expense = Account(
        tenant_id=tenant_id,
        account_number="5100",
        account_name="Operating Expenses",
        root_type=AccountRootType.EXPENSE,
        report_type=_ROOT_TYPE_TO_REPORT_TYPE[AccountRootType.EXPENSE],
        account_type=AccountType.EXPENSE,
        is_group=False,
    )
    db.add(expense)
    accounts["expense"] = expense
    
    tax = Account(
        tenant_id=tenant_id,
        account_number="2150",
        account_name="Tax Payable",
        root_type=AccountRootType.LIABILITY,
        report_type=_ROOT_TYPE_TO_REPORT_TYPE[AccountRootType.LIABILITY],
        account_type=AccountType.TAX_LIABILITY,
        is_group=False,
    )
    db.add(tax)
    accounts["tax"] = tax
    
    await db.flush()
    return accounts


@pytest.fixture
async def posting_rule(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    accounts: dict[str, Account]
) -> PostingRule:
    """Create a posting rule for customer invoices."""
    rule = PostingRule(
        tenant_id=tenant_id,
        document_type=DocumentType.CUSTOMER_INVOICE,
        version=1,
        description="Standard customer invoice posting",
        account_mappings={
            "receivable_account_id": str(accounts["receivable"].id),
            "revenue_account_id": str(accounts["revenue"].id),
        },
        tax_account_id=accounts["tax"].id,
        is_active=True,
        created_by="test",
    )
    db.add(rule)
    await db.flush()
    return rule


@pytest.fixture
async def supplier_posting_rule(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    accounts: dict[str, Account]
) -> PostingRule:
    """Create a posting rule for supplier invoices."""
    rule = PostingRule(
        tenant_id=tenant_id,
        document_type=DocumentType.SUPPLIER_INVOICE,
        version=1,
        description="Standard supplier invoice posting",
        account_mappings={
            "payable_account_id": str(accounts["payable"].id),
            "expense_account_id": str(accounts["expense"].id),
        },
        tax_account_id=accounts["tax"].id,
        is_active=True,
        created_by="test",
    )
    db.add(rule)
    await db.flush()
    return rule


class TestPostingRuleService:
    """Tests for posting rule service functions."""

    async def test_get_posting_rule_returns_active_rule(
        self, db: AsyncSession, posting_rule: PostingRule, tenant_id: uuid.UUID
    ):
        """Test that get_posting_rule returns the active rule."""
        rule = await get_posting_rule(
            db, tenant_id, DocumentType.CUSTOMER_INVOICE
        )
        assert rule is not None
        assert rule.id == posting_rule.id
        assert rule.is_active is True

    async def test_get_posting_rule_returns_none_for_missing(
        self, db: AsyncSession, tenant_id: uuid.UUID
    ):
        """Test that get_posting_rule returns None when no rule exists."""
        rule = await get_posting_rule(
            db, tenant_id, DocumentType.CUSTOMER_PAYMENT
        )
        assert rule is None

    async def test_ensure_posting_state_creates_new_state(
        self, db: AsyncSession, tenant_id: uuid.UUID
    ):
        """Test that ensure_posting_state creates a new state if none exists."""
        document_id = uuid.uuid4()
        
        state = await ensure_posting_state(
            db, tenant_id, DocumentType.CUSTOMER_INVOICE, document_id
        )
        
        assert state is not None
        assert state.document_id == document_id
        assert state.status == PostingStatus.NOT_CONFIGURED

    async def test_get_document_posting_status_returns_not_configured(
        self, db: AsyncSession, tenant_id: uuid.UUID
    ):
        """Test that document without rule returns not_configured status."""
        document_id = uuid.uuid4()
        
        status = await get_document_posting_status(
            db, tenant_id, DocumentType.CUSTOMER_INVOICE, document_id
        )
        
        assert status == PostingStatus.NOT_CONFIGURED


class TestCustomerInvoicePosting:
    """Tests for customer invoice posting."""

    async def test_post_customer_invoice_creates_gl_entries(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        fiscal_year: FiscalYear,
        accounts: dict[str, Account],
        posting_rule: PostingRule,
    ):
        """Test that posting a customer invoice creates GL entries."""
        # Create a test invoice
        invoice = SimpleNamespace(
            id=uuid.uuid4(),
            invoice_number="INV-001",
            invoice_date=date(2026, 3, 15),
            base_subtotal_amount=Decimal("1000"),
            base_tax_amount=Decimal("50"),
            base_total_amount=Decimal("1050"),
        )
        
        # Post the invoice
        success, error = await post_customer_invoice(db, invoice, tenant_id)
        
        assert success is True
        assert error is None
        
        # Check posting state
        state = await ensure_posting_state(
            db, tenant_id, DocumentType.CUSTOMER_INVOICE, invoice.id
        )
        assert state.status == PostingStatus.POSTED
        assert state.posting_rule_id == posting_rule.id
        assert len(state.gl_entry_ids) == 3
        
        # Check GL entries were created
        result = await db.execute(
            select(GLEntry).where(
                GLEntry.tenant_id == tenant_id,
                GLEntry.voucher_type == "Customer Invoice",
                GLEntry.source_type == "Invoice",
                GLEntry.source_id == invoice.id,
            )
        )
        gl_entries = result.scalars().all()
        
        assert len(gl_entries) == 3  # Receivable, Revenue, Tax
        
        # Verify debits = credits
        total_debit = sum(e.debit for e in gl_entries)
        total_credit = sum(e.credit for e in gl_entries)
        assert total_debit == total_credit

    async def test_post_invoice_without_rule_returns_not_configured(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        fiscal_year: FiscalYear,
    ):
        """Test that posting without a rule returns not_configured."""
        invoice = SimpleNamespace(
            id=uuid.uuid4(),
            invoice_number="INV-002",
            invoice_date=date(2026, 3, 15),
            base_subtotal_amount=Decimal("1000"),
            base_tax_amount=Decimal("50"),
            base_total_amount=Decimal("1050"),
        )
        
        success, error = await post_customer_invoice(db, invoice, tenant_id)
        
        assert success is False
        assert "No posting rule configured" in error

    async def test_get_open_fiscal_year_returns_correct_fiscal_year(
        self, db: AsyncSession, tenant_id: uuid.UUID, fiscal_year: FiscalYear
    ):
        """Test that get_open_fiscal_year returns the correct fiscal year."""
        fy = await get_open_fiscal_year(
            db, tenant_id, date(2026, 6, 15)
        )
        
        assert fy is not None
        assert fy.id == fiscal_year.id
        assert fy.status == FiscalYearStatus.OPEN


class TestReversal:
    """Tests for document reversal."""

    async def test_reverse_document_posting_creates_reversing_entries(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        fiscal_year: FiscalYear,
        accounts: dict[str, Account],
        posting_rule: PostingRule,
    ):
        """Test that reversal creates reversing GL entries."""
        # Create and post an invoice
        invoice = SimpleNamespace(
            id=uuid.uuid4(),
            invoice_number="INV-003",
            invoice_date=date(2026, 3, 15),
            base_subtotal_amount=Decimal("1000"),
            base_tax_amount=Decimal("50"),
            base_total_amount=Decimal("1050"),
        )
        
        await post_customer_invoice(db, invoice, tenant_id)
        
        # Reverse the posting
        success, error = await reverse_document_posting(
            db, tenant_id, DocumentType.CUSTOMER_INVOICE, invoice.id
        )
        
        assert success is True
        assert error is None
        
        # Check posting state is now reversed
        state = await ensure_posting_state(
            db, tenant_id, DocumentType.CUSTOMER_INVOICE, invoice.id
        )
        assert state.status == PostingStatus.REVERSED
        
        # Check GL entries include reversals
        result = await db.execute(
            select(GLEntry).where(
                GLEntry.tenant_id == tenant_id,
                GLEntry.source_type == "Invoice",
                GLEntry.source_id == invoice.id
            )
        )
        gl_entries = result.scalars().all()
        
        # Should have 6 entries: 3 original + 3 reversals
        assert len(gl_entries) == 6
        
        # Verify reversals have swapped debit/credit
        reversals = [e for e in gl_entries if e.is_reversal]
        assert len(reversals) == 3


class TestSupplierInvoicePosting:
    """Tests for supplier invoice posting."""

    async def test_post_supplier_invoice_creates_gl_entries(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        fiscal_year: FiscalYear,
        accounts: dict[str, Account],
        supplier_posting_rule: PostingRule,
    ):
        """Test that posting a supplier invoice creates GL entries."""
        # Create a test supplier invoice
        supplier_invoice = SimpleNamespace(
            id=uuid.uuid4(),
            invoice_number="SI-001",
            invoice_date=date(2026, 3, 15),
            base_subtotal_amount=Decimal("800"),
            base_tax_amount=Decimal("40"),
            base_total_amount=Decimal("840"),
        )
        
        # Post the supplier invoice
        success, error = await post_supplier_invoice(db, supplier_invoice, tenant_id)
        
        assert success is True
        assert error is None
        
        # Check GL entries were created
        result = await db.execute(
            select(GLEntry).where(
                GLEntry.tenant_id == tenant_id,
                GLEntry.voucher_type == "Supplier Invoice",
                GLEntry.source_type == "SupplierInvoice",
                GLEntry.source_id == supplier_invoice.id,
            )
        )
        gl_entries = result.scalars().all()
        
        assert len(gl_entries) == 3  # Expense, Tax, Payable
        
        # Verify debits = credits
        total_debit = sum(e.debit for e in gl_entries)
        total_credit = sum(e.credit for e in gl_entries)
        assert total_debit == total_credit
