"""
Bank Reconciliation and Collections Service for Epic 26 Story 26-5.
"""
from __future__ import annotations

import csv
import uuid
from datetime import date, datetime, UTC
from decimal import Decimal
from io import StringIO
from typing import Any, TypedDict

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.common.models.banking import (
    BankAccount,
    BankTransaction,
    BankTransactionMatch,
    BankTransactionStatus,
    DunningNotice,
    DunningNoticeStatus,
)
from backend.common.models.invoice import Invoice, InvoiceStatus
from backend.common.models.payment import Payment, PaymentStatus


class BankTransactionSuggestion(TypedDict):
    """A suggested match for a bank transaction."""
    voucher_type: str
    voucher_id: str
    amount: Decimal
    reference: str | None
    date: date
    confidence: Decimal
    description: str


# ============================================================
# Bank Account Service
# ============================================================

async def create_bank_account(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    data: dict[str, Any],
    created_by: str | None = None
) -> BankAccount:
    """Create a new bank account."""
    account = BankAccount(
        tenant_id=tenant_id,
        account_name=data["account_name"],
        account_number=data["account_number"],
        bank_name=data.get("bank_name"),
        bank_code=data.get("bank_code"),
        currency_code=data.get("currency_code", "TWD"),
        opening_balance=data.get("opening_balance", Decimal("0")),
        current_balance=data.get("opening_balance", Decimal("0")),
        is_active=data.get("is_active", True),
        notes=data.get("notes"),
        created_by=created_by,
    )
    session.add(account)
    await session.flush()
    return account


async def list_bank_accounts(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    is_active: bool | None = None
) -> list[BankAccount]:
    """List bank accounts for a tenant."""
    query = select(BankAccount).where(BankAccount.tenant_id == tenant_id)
    if is_active is not None:
        query = query.where(BankAccount.is_active == is_active)
    result = await session.execute(query.order_by(BankAccount.account_name))
    return list(result.scalars().all())


async def get_bank_account(
    session: AsyncSession,
    bank_account_id: uuid.UUID,
    tenant_id: uuid.UUID
) -> BankAccount | None:
    """Get a bank account by ID."""
    result = await session.execute(
        select(BankAccount).where(
            BankAccount.id == bank_account_id,
            BankAccount.tenant_id == tenant_id
        )
    )
    return result.scalar_one_or_none()


# ============================================================
# Bank Transaction Import Service
# ============================================================

async def import_bank_transactions_csv(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    bank_account_id: uuid.UUID,
    csv_content: str,
    import_metadata: dict[str, Any],
    imported_by: str | None = None
) -> tuple[list[BankTransaction], list[dict]]:
    """Import bank transactions from CSV content.
    
    CSV format expected:
    - date, description, reference, debit, credit (or amount with sign)
    - First row should be headers
    
    Returns (imported_transactions, errors).
    """
    transactions = []
    errors = []
    batch_id = uuid.uuid4()
    
    reader = csv.DictReader(StringIO(csv_content))
    
    for row_num, row in enumerate(reader, start=2):  # Start at 2 (after header)
        try:
            # Parse date
            date_str = row.get("date", "").strip()
            if not date_str:
                errors.append({"row": row_num, "error": "Missing date"})
                continue
            
            transaction_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            
            # Parse amount
            debit = Decimal("0")
            credit = Decimal("0")
            signed_amount = None
            
            if "amount" in row:
                amount = Decimal(row["amount"].strip())
                if amount >= 0:
                    debit = amount
                else:
                    credit = abs(amount)
                signed_amount = amount
            else:
                if row.get("debit"):
                    debit = Decimal(row["debit"].strip())
                if row.get("credit"):
                    credit = Decimal(row["credit"].strip())
            
            tx = BankTransaction(
                tenant_id=tenant_id,
                bank_account_id=bank_account_id,
                import_batch_id=batch_id,
                import_file_name=import_metadata.get("file_name"),
                import_row_number=row_num,
                imported_by=imported_by,
                transaction_date=transaction_date,
                value_date=transaction_date,
                description=row.get("description", "").strip(),
                reference_number=row.get("reference", "").strip() or None,
                debit=debit,
                credit=credit,
                signed_amount=signed_amount,
                currency_code=import_metadata.get("currency_code", "TWD"),
                status=BankTransactionStatus.UNMATCHED,
                suggestions=[],
            )
            session.add(tx)
            transactions.append(tx)
            
        except Exception as e:
            errors.append({"row": row_num, "error": str(e)})
    
    await session.flush()
    return transactions, errors


# ============================================================
# Bank Transaction Matching Service
# ============================================================

async def get_unmatched_transactions(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    bank_account_id: uuid.UUID | None = None
) -> list[BankTransaction]:
    """Get all unmatched bank transactions."""
    query = select(BankTransaction).where(
        BankTransaction.tenant_id == tenant_id,
        BankTransaction.status.in_([
            BankTransactionStatus.UNMATCHED,
            BankTransactionStatus.SUGGESTED
        ])
    )
    if bank_account_id:
        query = query.where(BankTransaction.bank_account_id == bank_account_id)
    
    result = await session.execute(query.order_by(BankTransaction.transaction_date))
    return list(result.scalars().all())


async def get_transaction_suggestions(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    transaction: BankTransaction
) -> list[BankTransactionSuggestion]:
    """Generate match suggestions for a bank transaction.
    
    Searches payments and journal entries for potential matches.
    """
    suggestions = []
    amount = transaction.debit if transaction.debit > 0 else transaction.credit
    
    # Search for matching payments by reference
    payment_query = select(Payment).where(
        Payment.tenant_id == tenant_id,
        Payment.status == PaymentStatus.MATCHED,
    )
    payments = (await session.execute(payment_query)).scalars().all()
    
    for payment in payments:
        payment_amount = payment.base_amount or payment.amount
        
        # Check for reference match
        if transaction.reference_number and payment.payment_number:
            if transaction.reference_number.lower() in payment.payment_number.lower():
                suggestions.append(BankTransactionSuggestion(
                    voucher_type="Payment",
                    voucher_id=str(payment.id),
                    amount=payment_amount,
                    reference=payment.payment_number,
                    date=payment.payment_date,
                    confidence=Decimal("90"),
                    description=f"Payment {payment.payment_number}"
                ))
        
        # Check for amount match
        if abs(payment_amount - amount) < Decimal("0.01"):
            if not any(s["voucher_id"] == str(payment.id) for s in suggestions):
                suggestions.append(BankTransactionSuggestion(
                    voucher_type="Payment",
                    voucher_id=str(payment.id),
                    amount=payment_amount,
                    reference=payment.payment_number,
                    date=payment.payment_date,
                    confidence=Decimal("80"),
                    description=f"Payment {payment.payment_number} (amount match)"
                ))
    
    return suggestions


async def match_transaction(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    transaction_id: uuid.UUID,
    voucher_type: str,
    voucher_id: uuid.UUID,
    matched_amount: Decimal,
    match_type: str = "manual",
    match_confidence: Decimal = Decimal("100"),
    reconciled_by: str | None = None
) -> BankTransactionMatch:
    """Create a match between a bank transaction and a voucher."""
    match = BankTransactionMatch(
        tenant_id=tenant_id,
        bank_transaction_id=transaction_id,
        voucher_type=voucher_type,
        voucher_id=voucher_id,
        matched_amount=matched_amount,
        match_type=match_type,
        match_confidence=match_confidence,
        is_reconciled=False,
        reconciled_by=reconciled_by,
    )
    session.add(match)
    
    # Update transaction status
    result = await session.execute(
        select(BankTransaction).where(
            BankTransaction.id == transaction_id,
            BankTransaction.tenant_id == tenant_id
        )
    )
    transaction = result.scalar_one_or_none()
    if transaction:
        transaction.status = BankTransactionStatus.MATCHED
    
    await session.flush()
    return match


async def reconcile_transaction(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    transaction_id: uuid.UUID,
    reconciled_by: str | None = None
) -> bool:
    """Reconcile a matched bank transaction."""
    result = await session.execute(
        select(BankTransaction).where(
            BankTransaction.id == transaction_id,
            BankTransaction.tenant_id == tenant_id
        )
    )
    transaction = result.scalar_one_or_none()
    
    if not transaction:
        return False
    
    transaction.status = BankTransactionStatus.RECONCILED
    
    # Mark all matches as reconciled
    await session.execute(
        select(BankTransactionMatch).where(
            BankTransactionMatch.bank_transaction_id == transaction_id,
            BankTransactionMatch.tenant_id == tenant_id
        )
    )
    matches = (await session.execute(
        select(BankTransactionMatch).where(
            BankTransactionMatch.bank_transaction_id == transaction_id,
            BankTransactionMatch.tenant_id == tenant_id
        )
    )).scalars().all()
    
    for match in matches:
        match.is_reconciled = True
        match.reconciled_at = datetime.now(UTC)
        match.reconciled_by = reconciled_by
    
    await session.flush()
    return True


# ============================================================
# Dunning Service
# ============================================================

async def get_overdue_invoices(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    days_overdue: int = 30
) -> list[Invoice]:
    """Get invoices that are overdue by the specified number of days."""
    from datetime import timedelta
    
    cutoff_date = date.today() - timedelta(days=days_overdue)
    
    result = await session.execute(
        select(Invoice).where(
            Invoice.tenant_id == tenant_id,
            Invoice.status == InvoiceStatus.SUBMITTED,
            Invoice.invoice_date <= cutoff_date
        )
    )
    return list(result.scalars().all())


async def create_dunning_notice(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    invoice_id: uuid.UUID,
    data: dict[str, Any],
    created_by: str | None = None
) -> DunningNotice:
    """Create a dunning notice for an overdue invoice."""
    # Get invoice
    result = await session.execute(
        select(Invoice).where(
            Invoice.id == invoice_id,
            Invoice.tenant_id == tenant_id
        )
    )
    invoice = result.scalar_one_or_none()
    
    if not invoice:
        raise ValueError("Invoice not found")
    
    # Calculate amounts
    outstanding = invoice.base_total_amount or Decimal("0")
    fee = data.get("fee_amount", Decimal("0"))
    interest = data.get("interest_amount", Decimal("0"))
    total = outstanding + fee + interest
    
    # Generate notice number
    notice_count = (await session.execute(
        select(func.count(DunningNotice.id)).where(
            DunningNotice.tenant_id == tenant_id
        )
    )).scalar() or 0
    
    notice_number = f"DUN-{datetime.now(UTC).strftime('%Y%m')}-{notice_count + 1:04d}"
    
    notice = DunningNotice(
        tenant_id=tenant_id,
        invoice_id=invoice_id,
        customer_id=invoice.customer_id,
        notice_number=notice_number,
        notice_date=data.get("notice_date", date.today()),
        due_date=data.get("due_date"),
        status=DunningNoticeStatus.DRAFT,
        outstanding_amount=outstanding,
        fee_amount=fee,
        interest_amount=interest,
        total_amount=total,
        notice_text=data.get("notice_text", ""),
        reminder_level=data.get("reminder_level", 1),
        created_by=created_by,
    )
    session.add(notice)
    await session.flush()
    return notice


async def get_dunning_notices(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    status: DunningNoticeStatus | None = None,
    customer_id: uuid.UUID | None = None
) -> list[DunningNotice]:
    """Get dunning notices with optional filters."""
    query = select(DunningNotice).where(DunningNotice.tenant_id == tenant_id)
    
    if status:
        query = query.where(DunningNotice.status == status)
    if customer_id:
        query = query.where(DunningNotice.customer_id == customer_id)
    
    result = await session.execute(query.order_by(DunningNotice.notice_date.desc()))
    return list(result.scalars().all())


async def transition_dunning_notice(
    session: AsyncSession,
    notice_id: uuid.UUID,
    tenant_id: uuid.UUID,
    new_status: DunningNoticeStatus,
    outcome: str | None = None,
    outcome_notes: str | None = None,
    updated_by: str | None = None
) -> DunningNotice:
    """Transition a dunning notice to a new status.
    
    Valid transitions:
    - Draft -> Open
    - Open -> Resolved
    - Open -> Cancelled
    - Draft -> Cancelled
    """
    valid_transitions = {
        DunningNoticeStatus.DRAFT: [DunningNoticeStatus.OPEN, DunningNoticeStatus.CANCELLED],
        DunningNoticeStatus.OPEN: [DunningNoticeStatus.RESOLVED, DunningNoticeStatus.CANCELLED],
        DunningNoticeStatus.RESOLVED: [],
        DunningNoticeStatus.CANCELLED: [],
    }
    
    result = await session.execute(
        select(DunningNotice).where(
            DunningNotice.id == notice_id,
            DunningNotice.tenant_id == tenant_id
        )
    )
    notice = result.scalar_one_or_none()
    
    if not notice:
        raise ValueError("Dunning notice not found")
    
    current_status = DunningNoticeStatus(notice.status)
    
    if new_status not in valid_transitions.get(current_status, []):
        raise ValueError(f"Invalid transition from {current_status.value} to {new_status.value}")
    
    notice.status = new_status
    
    if new_status == DunningNoticeStatus.RESOLVED:
        notice.outcome = outcome
        notice.outcome_notes = outcome_notes
        notice.resolved_at = datetime.now(UTC)
        notice.resolved_by = updated_by
    
    await session.flush()
    return notice
