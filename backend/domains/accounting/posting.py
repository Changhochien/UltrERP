"""
Document Auto-Posting Service for Epic 26 Story 26-4.

Posts GL entries from supported commercial documents (invoices, payments)
using explicit, versioned posting rules.
"""
from __future__ import annotations

import uuid
from datetime import datetime, UTC
from decimal import Decimal
from typing import Any, TypedDict

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.common.events import DomainEvent, emit
from backend.common.models.account import Account
from backend.common.models.document import Document, DocumentStatus
from backend.common.models.fiscal_year import FiscalYear
from backend.common.models.gl_entry import GLEntry
from backend.common.models.invoice import Invoice, InvoiceStatus
from backend.common.models.journal_entry import JournalEntry, JournalEntryStatus
from backend.common.models.payment import Payment, PaymentStatus
from backend.common.models.posting_rule import (
    DocumentPostingState,
    DocumentType,
    PostingRule,
    PostingStatus,
)
from backend.common.models.supplier_invoice import SupplierInvoice, SupplierInvoiceStatus
from backend.common.models.supplier_payment import SupplierPayment, SupplierPaymentStatus
from backend.common.model_registry import model_registry
from backend.domains.accounting.service import create_gl_entries_from_lines


class DocumentFinalizedEvent(DomainEvent):
    """Fired when a document (invoice, payment, etc.) is finalized."""
    name: str = "document_finalized"
    document_type: str = ""
    document_id: uuid.UUID = field(default_factory=uuid.uuid4)
    tenant_id: uuid.UUID = field(default_factory=uuid.uuid4)
    actor_id: str = "system"
    base_amount: Decimal = Decimal("0")
    currency: str = "TWD"
    conversion_rate: Decimal = Decimal("1")
    tax_amount: Decimal = Decimal("0")


class DocumentVoidedEvent(DomainEvent):
    """Fired when a document is voided or cancelled."""
    name: str = "document_voided"
    document_type: str = ""
    document_id: uuid.UUID = field(default_factory=uuid.uuid4)
    tenant_id: uuid.UUID = field(default_factory=uuid.uuid4)
    actor_id: str = "system"


async def get_posting_rule(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    document_type: DocumentType
) -> PostingRule | None:
    """Get the active posting rule for a document type."""
    result = await session.execute(
        select(PostingRule).where(
            PostingRule.tenant_id == tenant_id,
            PostingRule.document_type == document_type,
            PostingRule.is_active == True
        )
    )
    return result.scalar_one_or_none()


async def ensure_posting_state(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    document_type: DocumentType,
    document_id: uuid.UUID
) -> DocumentPostingState:
    """Ensure a posting state exists for a document, creating if needed."""
    result = await session.execute(
        select(DocumentPostingState).where(
            DocumentPostingState.tenant_id == tenant_id,
            DocumentPostingState.document_type == document_type,
            DocumentPostingState.document_id == document_id
        )
    )
    state = result.scalar_one_or_none()
    
    if not state:
        state = DocumentPostingState(
            tenant_id=tenant_id,
            document_type=document_type,
            document_id=document_id,
            status=PostingStatus.NOT_CONFIGURED
        )
        session.add(state)
        await session.flush()
    
    return state


async def post_customer_invoice(
    session: AsyncSession,
    invoice: Invoice,
    tenant_id: uuid.UUID
) -> tuple[bool, str | None]:
    """Post GL entries for a customer invoice.
    
    Creates:
    - DR: Accounts Receivable (customer) -> base_total_amount
    - CR: Revenue/Sales -> base_subtotal
    - CR: Tax Payable -> base_tax_amount
    
    Returns (success, error_message).
    """
    from dataclasses import dataclass, field
    
    # Get posting rule
    rule = await get_posting_rule(session, tenant_id, DocumentType.CUSTOMER_INVOICE)
    
    # Ensure posting state exists
    state = await ensure_posting_state(session, tenant_id, DocumentType.CUSTOMER_INVOICE, invoice.id)
    
    # If no rule configured, mark as not configured and return
    if not rule:
        state.status = PostingStatus.NOT_CONFIGURED
        await session.flush()
        return False, "No posting rule configured for customer invoices"
    
    # Check if already posted
    if state.status == PostingStatus.POSTED:
        return False, "Invoice already posted"
    
    # Get fiscal year
    fiscal_year = await get_open_fiscal_year(session, tenant_id, invoice.invoice_date)
    if not fiscal_year:
        return False, "No open fiscal year for invoice date"
    
    # Get accounts from rule mappings
    mappings = rule.account_mappings
    receivable_account_id = mappings.get("receivable_account_id")
    revenue_account_id = mappings.get("revenue_account_id")
    tax_account_id = rule.tax_account_id
    
    if not receivable_account_id or not revenue_account_id:
        return False, "Posting rule missing required account mappings"
    
    # Create GL entries
    base_subtotal = invoice.base_subtotal_amount or Decimal("0")
    base_tax = invoice.base_tax_amount or Decimal("0")
    base_total = invoice.base_total_amount or Decimal("0")
    
    # DR: Accounts Receivable
    await create_gl_entry_from_posting(
        session=session,
        tenant_id=tenant_id,
        account_id=uuid.UUID(receivable_account_id) if isinstance(receivable_account_id, str) else receivable_account_id,
        debit=base_total,
        credit=Decimal("0"),
        posting_date=invoice.invoice_date,
        voucher_type="Customer Invoice",
        voucher_id=invoice.id,
        narration=f"Invoice {invoice.invoice_number}",
        fiscal_year_id=fiscal_year.id,
        reference_type="Invoice",
        reference_id=invoice.id,
        reference_number=invoice.invoice_number
    )
    
    # CR: Revenue
    await create_gl_entry_from_posting(
        session=session,
        tenant_id=tenant_id,
        account_id=uuid.UUID(revenue_account_id) if isinstance(revenue_account_id, str) else revenue_account_id,
        debit=Decimal("0"),
        credit=base_subtotal,
        posting_date=invoice.invoice_date,
        voucher_type="Customer Invoice",
        voucher_id=invoice.id,
        narration=f"Invoice {invoice.invoice_number}",
        fiscal_year_id=fiscal_year.id,
        reference_type="Invoice",
        reference_id=invoice.id,
        reference_number=invoice.invoice_number
    )
    
    # CR: Tax (if tax amount exists)
    if base_tax > 0 and tax_account_id:
        await create_gl_entry_from_posting(
            session=session,
            tenant_id=tenant_id,
            account_id=uuid.UUID(tax_account_id) if isinstance(tax_account_id, str) else tax_account_id,
            debit=Decimal("0"),
            credit=base_tax,
            posting_date=invoice.invoice_date,
            voucher_type="Customer Invoice",
            voucher_id=invoice.id,
            narration=f"Tax on Invoice {invoice.invoice_number}",
            fiscal_year_id=fiscal_year.id,
            reference_type="Invoice",
            reference_id=invoice.id,
            reference_number=invoice.invoice_number
        )
    
    # Update posting state
    state.status = PostingStatus.POSTED
    state.posting_rule_id = rule.id
    state.rule_version_at_posting = rule.version
    state.posted_at = datetime.now(UTC)
    await session.flush()
    
    return True, None


async def post_customer_payment(
    session: AsyncSession,
    payment: Payment,
    tenant_id: uuid.UUID
) -> tuple[bool, str | None]:
    """Post GL entries for a customer payment.
    
    Creates:
    - DR: Cash/Bank -> base_amount
    - CR: Accounts Receivable -> base_amount
    
    Returns (success, error_message).
    """
    # Get posting rule
    rule = await get_posting_rule(session, tenant_id, DocumentType.CUSTOMER_PAYMENT)
    
    # Ensure posting state exists
    state = await ensure_posting_state(session, tenant_id, DocumentType.CUSTOMER_PAYMENT, payment.id)
    
    if not rule:
        state.status = PostingStatus.NOT_CONFIGURED
        await session.flush()
        return False, "No posting rule configured for customer payments"
    
    if state.status == PostingStatus.POSTED:
        return False, "Payment already posted"
    
    # Get fiscal year
    fiscal_year = await get_open_fiscal_year(session, tenant_id, payment.payment_date)
    if not fiscal_year:
        return False, "No open fiscal year for payment date"
    
    # Get accounts
    mappings = rule.account_mappings
    bank_account_id = mappings.get("bank_account_id")
    receivable_account_id = mappings.get("receivable_account_id")
    
    if not bank_account_id or not receivable_account_id:
        return False, "Posting rule missing required account mappings"
    
    base_amount = payment.base_amount or Decimal("0")
    
    # DR: Cash/Bank
    await create_gl_entry_from_posting(
        session=session,
        tenant_id=tenant_id,
        account_id=uuid.UUID(bank_account_id) if isinstance(bank_account_id, str) else bank_account_id,
        debit=base_amount,
        credit=Decimal("0"),
        posting_date=payment.payment_date,
        voucher_type="Customer Payment",
        voucher_id=payment.id,
        narration=f"Payment {payment.payment_number or payment.id}",
        fiscal_year_id=fiscal_year.id,
        reference_type="Payment",
        reference_id=payment.id,
        reference_number=payment.payment_number
    )
    
    # CR: Accounts Receivable
    await create_gl_entry_from_posting(
        session=session,
        tenant_id=tenant_id,
        account_id=uuid.UUID(receivable_account_id) if isinstance(receivable_account_id, str) else receivable_account_id,
        debit=Decimal("0"),
        credit=base_amount,
        posting_date=payment.payment_date,
        voucher_type="Customer Payment",
        voucher_id=payment.id,
        narration=f"Payment {payment.payment_number or payment.id}",
        fiscal_year_id=fiscal_year.id,
        reference_type="Payment",
        reference_id=payment.id,
        reference_number=payment.payment_number
    )
    
    # Update state
    state.status = PostingStatus.POSTED
    state.posting_rule_id = rule.id
    state.rule_version_at_posting = rule.version
    state.posted_at = datetime.now(UTC)
    await session.flush()
    
    return True, None


async def post_supplier_invoice(
    session: AsyncSession,
    supplier_invoice: SupplierInvoice,
    tenant_id: uuid.UUID
) -> tuple[bool, str | None]:
    """Post GL entries for a supplier invoice."""
    rule = await get_posting_rule(session, tenant_id, DocumentType.SUPPLIER_INVOICE)
    state = await ensure_posting_state(session, tenant_id, DocumentType.SUPPLIER_INVOICE, supplier_invoice.id)
    
    if not rule:
        state.status = PostingStatus.NOT_CONFIGURED
        await session.flush()
        return False, "No posting rule configured for supplier invoices"
    
    if state.status == PostingStatus.POSTED:
        return False, "Supplier invoice already posted"
    
    fiscal_year = await get_open_fiscal_year(session, tenant_id, supplier_invoice.invoice_date)
    if not fiscal_year:
        return False, "No open fiscal year for invoice date"
    
    mappings = rule.account_mappings
    payable_account_id = mappings.get("payable_account_id")
    expense_account_id = mappings.get("expense_account_id")
    tax_account_id = rule.tax_account_id
    
    if not payable_account_id or not expense_account_id:
        return False, "Posting rule missing required account mappings"
    
    base_subtotal = supplier_invoice.base_subtotal_amount or Decimal("0")
    base_tax = supplier_invoice.base_tax_amount or Decimal("0")
    base_total = supplier_invoice.base_total_amount or Decimal("0")
    
    # DR: Expense
    await create_gl_entry_from_posting(
        session=session,
        tenant_id=tenant_id,
        account_id=uuid.UUID(expense_account_id) if isinstance(expense_account_id, str) else expense_account_id,
        debit=base_subtotal,
        credit=Decimal("0"),
        posting_date=supplier_invoice.invoice_date,
        voucher_type="Supplier Invoice",
        voucher_id=supplier_invoice.id,
        narration=f"Supplier Invoice {supplier_invoice.invoice_number}",
        fiscal_year_id=fiscal_year.id,
        reference_type="SupplierInvoice",
        reference_id=supplier_invoice.id,
        reference_number=supplier_invoice.invoice_number
    )
    
    # DR: Tax (if applicable)
    if base_tax > 0 and tax_account_id:
        await create_gl_entry_from_posting(
            session=session,
            tenant_id=tenant_id,
            account_id=uuid.UUID(tax_account_id) if isinstance(tax_account_id, str) else tax_account_id,
            debit=base_tax,
            credit=Decimal("0"),
            posting_date=supplier_invoice.invoice_date,
            voucher_type="Supplier Invoice",
            voucher_id=supplier_invoice.id,
            narration=f"Tax on Supplier Invoice {supplier_invoice.invoice_number}",
            fiscal_year_id=fiscal_year.id,
            reference_type="SupplierInvoice",
            reference_id=supplier_invoice.id,
            reference_number=supplier_invoice.invoice_number
        )
    
    # CR: Accounts Payable
    await create_gl_entry_from_posting(
        session=session,
        tenant_id=tenant_id,
        account_id=uuid.UUID(payable_account_id) if isinstance(payable_account_id, str) else payable_account_id,
        debit=Decimal("0"),
        credit=base_total,
        posting_date=supplier_invoice.invoice_date,
        voucher_type="Supplier Invoice",
        voucher_id=supplier_invoice.id,
        narration=f"Supplier Invoice {supplier_invoice.invoice_number}",
        fiscal_year_id=fiscal_year.id,
        reference_type="SupplierInvoice",
        reference_id=supplier_invoice.id,
        reference_number=supplier_invoice.invoice_number
    )
    
    state.status = PostingStatus.POSTED
    state.posting_rule_id = rule.id
    state.rule_version_at_posting = rule.version
    state.posted_at = datetime.now(UTC)
    await session.flush()
    
    return True, None


async def post_supplier_payment(
    session: AsyncSession,
    supplier_payment: SupplierPayment,
    tenant_id: uuid.UUID
) -> tuple[bool, str | None]:
    """Post GL entries for a supplier payment."""
    rule = await get_posting_rule(session, tenant_id, DocumentType.SUPPLIER_PAYMENT)
    state = await ensure_posting_state(session, tenant_id, DocumentType.SUPPLIER_PAYMENT, supplier_payment.id)
    
    if not rule:
        state.status = PostingStatus.NOT_CONFIGURED
        await session.flush()
        return False, "No posting rule configured for supplier payments"
    
    if state.status == PostingStatus.POSTED:
        return False, "Supplier payment already posted"
    
    fiscal_year = await get_open_fiscal_year(session, tenant_id, supplier_payment.payment_date)
    if not fiscal_year:
        return False, "No open fiscal year for payment date"
    
    mappings = rule.account_mappings
    bank_account_id = mappings.get("bank_account_id")
    payable_account_id = mappings.get("payable_account_id")
    
    if not bank_account_id or not payable_account_id:
        return False, "Posting rule missing required account mappings"
    
    base_amount = supplier_payment.base_amount or Decimal("0")
    
    # DR: Accounts Payable
    await create_gl_entry_from_posting(
        session=session,
        tenant_id=tenant_id,
        account_id=uuid.UUID(payable_account_id) if isinstance(payable_account_id, str) else payable_account_id,
        debit=base_amount,
        credit=Decimal("0"),
        posting_date=supplier_payment.payment_date,
        voucher_type="Supplier Payment",
        voucher_id=supplier_payment.id,
        narration=f"Payment {supplier_payment.payment_number or supplier_payment.id}",
        fiscal_year_id=fiscal_year.id,
        reference_type="SupplierPayment",
        reference_id=supplier_payment.id,
        reference_number=supplier_payment.payment_number
    )
    
    # CR: Cash/Bank
    await create_gl_entry_from_posting(
        session=session,
        tenant_id=tenant_id,
        account_id=uuid.UUID(bank_account_id) if isinstance(bank_account_id, str) else bank_account_id,
        debit=Decimal("0"),
        credit=base_amount,
        posting_date=supplier_payment.payment_date,
        voucher_type="Supplier Payment",
        voucher_id=supplier_payment.id,
        narration=f"Payment {supplier_payment.payment_number or supplier_payment.id}",
        fiscal_year_id=fiscal_year.id,
        reference_type="SupplierPayment",
        reference_id=supplier_payment.id,
        reference_number=supplier_payment.payment_number
    )
    
    state.status = PostingStatus.POSTED
    state.posting_rule_id = rule.id
    state.rule_version_at_posting = rule.version
    state.posted_at = datetime.now(UTC)
    await session.flush()
    
    return True, None


async def reverse_document_posting(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    document_type: DocumentType,
    document_id: uuid.UUID,
    reversal_date: datetime | None = None,
    reversal_narration: str | None = None
) -> tuple[bool, str | None]:
    """Reverse the posting for a document by creating reversing GL entries."""
    # Get the original posting state
    result = await session.execute(
        select(DocumentPostingState).where(
            DocumentPostingState.tenant_id == tenant_id,
            DocumentPostingState.document_type == document_type,
            DocumentPostingState.document_id == document_id
        )
    )
    state = result.scalar_one_or_none()
    
    if not state or state.status != PostingStatus.POSTED:
        return False, "No posting found to reverse"
    
    if reversal_date is None:
        reversal_date = datetime.now(UTC)
    
    # Get fiscal year for reversal date
    reversal_fiscal_year = await get_open_fiscal_year(session, tenant_id, reversal_date.date() if hasattr(reversal_date, 'date') else reversal_date)
    if not reversal_fiscal_year:
        return False, "No open fiscal year for reversal date"
    
    # Get the original GL entries
    result = await session.execute(
        select(GLEntry).where(
            GLEntry.tenant_id == tenant_id,
            GLEntry.voucher_type == document_type.value.title().replace("_", " "),
            GLEntry.voucher_id == document_id
        )
    )
    original_entries = result.scalars().all()
    
    if not original_entries:
        return False, "No GL entries found for reversal"
    
    # Create reversing entries
    for entry in original_entries:
        # Swap debit and credit for reversal
        await create_gl_entry_from_posting(
            session=session,
            tenant_id=tenant_id,
            account_id=entry.account_id,
            debit=entry.credit,  # Swap
            credit=entry.debit,  # Swap
            posting_date=reversal_date.date() if hasattr(reversal_date, 'date') else reversal_date,
            voucher_type=f"Reversal - {entry.voucher_type}",
            voucher_id=entry.voucher_id,
            narration=reversal_narration or f"Reversal: {entry.narration}",
            fiscal_year_id=reversal_fiscal_year.id,
            reference_type=entry.reference_type,
            reference_id=entry.reference_id,
            reference_number=entry.reference_number,
            is_reversal=True,
            reversed_entry_id=entry.id
        )
    
    # Create reversal state
    reversal_state = DocumentPostingState(
        tenant_id=tenant_id,
        document_type=document_type,
        document_id=document_id,
        status=PostingStatus.REVERSED,
        posting_rule_id=state.posting_rule_id,
        rule_version_at_posting=state.rule_version_at_posting,
        reverses_state_id=state.id,
        posted_at=datetime.now(UTC)
    )
    session.add(reversal_state)
    
    # Update original state
    state.status = PostingStatus.REVERSED
    state.reversed_by_state_id = reversal_state.id
    
    await session.flush()
    return True, None


# Helper functions

async def create_gl_entry_from_posting(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    account_id: uuid.UUID,
    debit: Decimal,
    credit: Decimal,
    posting_date: Any,
    voucher_type: str,
    voucher_id: uuid.UUID,
    narration: str,
    fiscal_year_id: uuid.UUID,
    reference_type: str | None = None,
    reference_id: uuid.UUID | None = None,
    reference_number: str | None = None,
    is_reversal: bool = False,
    reversed_entry_id: uuid.UUID | None = None
) -> GLEntry:
    """Create a GL entry for document posting."""
    # Validate posting date is a date, not datetime
    if hasattr(posting_date, 'date'):
        posting_date = posting_date.date()
    
    entry = GLEntry(
        tenant_id=tenant_id,
        account_id=account_id,
        posting_date=posting_date,
        debit=debit,
        credit=credit,
        fiscal_year_id=fiscal_year_id,
        voucher_type=voucher_type,
        voucher_id=voucher_id,
        voucher_number=reference_number,
        narration=narration,
        reference_type=reference_type,
        reference_id=reference_id,
        reference_number=reference_number,
        is_reversal=is_reversal,
        reversed_entry_id=reversed_entry_id,
        created_by="system"
    )
    session.add(entry)
    await session.flush()
    return entry


async def get_open_fiscal_year(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    target_date: Any
) -> FiscalYear | None:
    """Get the open fiscal year that contains the target date."""
    if hasattr(target_date, 'date'):
        target_date = target_date.date()
    
    result = await session.execute(
        select(FiscalYear).where(
            FiscalYear.tenant_id == tenant_id,
            FiscalYear.start_date <= target_date,
            FiscalYear.end_date >= target_date,
            FiscalYear.status == "open"
        )
    )
    return result.scalar_one_or_none()


async def get_document_posting_status(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    document_type: DocumentType,
    document_id: uuid.UUID
) -> PostingStatus:
    """Get the posting status for a document."""
    state = await ensure_posting_state(session, tenant_id, document_type, document_id)
    return PostingStatus(state.status)
