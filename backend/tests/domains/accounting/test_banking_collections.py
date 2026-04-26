"""Tests for banking and collections (Epic 26 Story 26-5)."""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from common.models.banking import (
    BankAccount,
    BankTransaction,
    BankTransactionMatch,
    BankTransactionStatus,
    DunningNotice,
    DunningNoticeStatus,
)
from backend.domains.accounting.banking import (
    create_bank_account,
    create_dunning_notice,
    get_dunning_notices,
    get_overdue_invoices,
    get_unmatched_transactions,
    list_bank_accounts,
    match_transaction,
    reconcile_transaction,
    transition_dunning_notice,
)
from domains.customers.models import Customer
from domains.invoices.enums import BuyerType, InvoiceStatus
from domains.invoices.models import Invoice
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
async def customer(db: AsyncSession, tenant_id: uuid.UUID) -> Customer:
    """Create a customer for invoice-backed dunning tests."""
    customer = Customer(
        tenant_id=tenant_id,
        company_name="Overdue Customer Co",
        normalized_business_number="12345678",
        billing_address="123 Test Street",
        contact_name="Overdue Customer",
        contact_phone="0912345678",
        contact_email="overdue@example.com",
    )
    db.add(customer)
    await db.flush()
    return customer


@pytest.fixture
async def bank_account(db: AsyncSession, tenant_id: uuid.UUID) -> BankAccount:
    """Create a test bank account."""
    account = BankAccount(
        tenant_id=tenant_id,
        account_name="Main Checking",
        account_number="123-456-789",
        bank_name="Test Bank",
        currency_code="TWD",
        opening_balance=Decimal("100000"),
        current_balance=Decimal("100000"),
        created_by="test",
    )
    db.add(account)
    await db.flush()
    return account


@pytest.fixture
async def bank_transactions(
    db: AsyncSession, tenant_id: uuid.UUID, bank_account: BankAccount
) -> list[BankTransaction]:
    """Create test bank transactions."""
    transactions = []
    
    for i in range(3):
        tx = BankTransaction(
            tenant_id=tenant_id,
            bank_account_id=bank_account.id,
            transaction_date=date(2026, 3, 15 + i),
            description=f"Transaction {i + 1}",
            reference_number=f"REF-{i + 1:03d}",
            debit=Decimal("1000") if i % 2 == 0 else Decimal("0"),
            credit=Decimal("1000") if i % 2 == 1 else Decimal("0"),
            status=BankTransactionStatus.UNMATCHED,
        )
        db.add(tx)
        transactions.append(tx)
    
    await db.flush()
    return transactions


@pytest.fixture
async def overdue_invoice(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    customer: Customer,
) -> Invoice:
    """Create an overdue invoice for dunning tests."""
    invoice = Invoice(
        tenant_id=tenant_id,
        invoice_number="INV9001",
        invoice_date=date(2026, 1, 15),  # 90+ days ago
        customer_id=customer.id,
        buyer_type=BuyerType.B2B,
        buyer_identifier_snapshot=customer.normalized_business_number,
        status=InvoiceStatus.ISSUED,
        subtotal_amount=Decimal("5000"),
        tax_amount=Decimal("250"),
        total_amount=Decimal("5250"),
        currency_code="TWD",
    )
    db.add(invoice)
    await db.flush()
    return invoice


class TestBankAccountService:
    """Tests for bank account service."""

    async def test_create_bank_account(self, db: AsyncSession, tenant_id: uuid.UUID):
        """Test creating a bank account."""
        account = await create_bank_account(
            db, tenant_id,
            {
                "account_name": "Savings Account",
                "account_number": "SAV-001",
                "bank_name": "Bank A",
                "currency_code": "TWD",
                "opening_balance": Decimal("50000"),
            },
            created_by="test"
        )
        
        assert account.id is not None
        assert account.account_name == "Savings Account"
        assert account.account_number == "SAV-001"
        assert account.opening_balance == Decimal("50000")

    async def test_list_bank_accounts(
        self, db: AsyncSession, tenant_id: uuid.UUID, bank_account: BankAccount
    ):
        """Test listing bank accounts."""
        accounts = await list_bank_accounts(db, tenant_id)
        
        assert len(accounts) >= 1
        assert any(a.account_name == "Main Checking" for a in accounts)


class TestBankTransactionService:
    """Tests for bank transaction operations."""

    async def test_get_unmatched_transactions(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        bank_transactions: list[BankTransaction]
    ):
        """Test getting unmatched transactions."""
        unmatched = await get_unmatched_transactions(db, tenant_id)
        
        assert len(unmatched) >= 3
        assert all(t.status in [BankTransactionStatus.UNMATCHED, BankTransactionStatus.SUGGESTED] for t in unmatched)

    async def test_match_transaction(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        bank_transactions: list[BankTransaction]
    ):
        """Test matching a bank transaction to a payment."""
        tx = bank_transactions[0]
        payment_id = uuid.uuid4()
        
        match = await match_transaction(
            db, tenant_id, tx.id,
            voucher_type="Payment",
            voucher_id=payment_id,
            matched_amount=tx.debit,
            match_type="manual",
            reconciled_by="test"
        )
        
        assert match.id is not None
        assert match.voucher_type == "Payment"
        assert match.voucher_id == payment_id
        
        # Check transaction status updated
        await db.refresh(tx)
        assert tx.status == BankTransactionStatus.MATCHED

    async def test_reconcile_transaction(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        bank_transactions: list[BankTransaction]
    ):
        """Test reconciling a matched transaction."""
        tx = bank_transactions[0]
        tx.status = BankTransactionStatus.MATCHED
        await db.flush()
        
        success = await reconcile_transaction(db, tenant_id, tx.id, reconciled_by="test")
        
        assert success is True
        
        # Check transaction status
        await db.refresh(tx)
        assert tx.status == BankTransactionStatus.RECONCILED


class TestDunningService:
    """Tests for dunning notice operations."""

    async def test_get_overdue_invoices(
        self, db: AsyncSession, tenant_id: uuid.UUID, overdue_invoice: Invoice
    ):
        """Test getting overdue invoices."""
        overdue = await get_overdue_invoices(db, tenant_id, days_overdue=30)
        
        assert len(overdue) >= 1
        assert any(i.invoice_number == "INV9001" for i in overdue)

    async def test_create_dunning_notice(
        self, db: AsyncSession, tenant_id: uuid.UUID, overdue_invoice: Invoice
    ):
        """Test creating a dunning notice."""
        notice = await create_dunning_notice(
            db, tenant_id, overdue_invoice.id,
            {
                "notice_date": date.today(),
                "fee_amount": Decimal("500"),
                "interest_amount": Decimal("100"),
                "notice_text": "Please pay your overdue invoice.",
                "reminder_level": 1,
            },
            created_by="test"
        )
        
        assert notice.id is not None
        assert notice.notice_number.startswith("DUN-")
        assert notice.status == DunningNoticeStatus.DRAFT
        assert notice.fee_amount == Decimal("500")
        assert notice.interest_amount == Decimal("100")
        assert notice.outstanding_amount == Decimal("5250")
        assert notice.total_amount == Decimal("5850")

    async def test_transition_dunning_notice(
        self, db: AsyncSession, tenant_id: uuid.UUID, overdue_invoice: Invoice
    ):
        """Test dunning notice status transitions."""
        notice = await create_dunning_notice(
            db, tenant_id, overdue_invoice.id,
            {"notice_date": date.today()},
            created_by="test"
        )
        
        # Draft -> Open
        notice = await transition_dunning_notice(
            db, notice.id, tenant_id, DunningNoticeStatus.OPEN
        )
        assert notice.status == DunningNoticeStatus.OPEN
        
        # Open -> Resolved
        notice = await transition_dunning_notice(
            db, notice.id, tenant_id, DunningNoticeStatus.RESOLVED,
            outcome="paid", outcome_notes="Customer paid in full"
        )
        assert notice.status == DunningNoticeStatus.RESOLVED
        assert notice.outcome == "paid"
        assert notice.resolved_at is not None

    async def test_invalid_dunning_transition(
        self, db: AsyncSession, tenant_id: uuid.UUID, overdue_invoice: Invoice
    ):
        """Test that invalid status transitions raise errors."""
        notice = await create_dunning_notice(
            db, tenant_id, overdue_invoice.id,
            {"notice_date": date.today()},
            created_by="test"
        )
        
        # Try invalid transition: Draft -> Resolved (must go through Open)
        with pytest.raises(ValueError, match="Invalid transition"):
            await transition_dunning_notice(
                db, notice.id, tenant_id, DunningNoticeStatus.RESOLVED
            )

    async def test_get_dunning_notices(
        self, db: AsyncSession, tenant_id: uuid.UUID, overdue_invoice: Invoice
    ):
        """Test getting dunning notices with filters."""
        # Create a notice
        await create_dunning_notice(
            db, tenant_id, overdue_invoice.id,
            {"notice_date": date.today()},
            created_by="test"
        )
        
        # Get all notices
        notices = await get_dunning_notices(db, tenant_id)
        assert len(notices) >= 1
        
        # Get by status
        draft_notices = await get_dunning_notices(
            db, tenant_id, status=DunningNoticeStatus.DRAFT
        )
        assert all(n.status == DunningNoticeStatus.DRAFT for n in draft_notices)
