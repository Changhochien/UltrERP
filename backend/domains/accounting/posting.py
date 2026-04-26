"""
Document Auto-Posting Service for Epic 26 Story 26-4.

Posts GL entries from supported commercial documents (invoices, payments)
using explicit, versioned posting rules.
"""
from __future__ import annotations

import uuid
from dataclasses import field
from datetime import datetime, UTC
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.events import DomainEvent, emit
from common.models.fiscal_year import FiscalYear
from common.models.fiscal_year import FiscalYearStatus
from common.models.gl_entry import GLEntry, GLEntryType
from common.models.posting_rule import (
    DocumentPostingState,
    DocumentType,
    PostingRule,
    PostingStatus,
)
from common.models.supplier_invoice import SupplierInvoice, SupplierInvoiceStatus
from common.models.supplier_payment import SupplierPayment, SupplierPaymentStatus
from domains.invoices.models import Invoice
from domains.payments.models import Payment


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


def _account_mapping_id(value: str | uuid.UUID | None) -> uuid.UUID | None:
    if value is None:
        return None
    return uuid.UUID(value) if isinstance(value, str) else value


def _decimal_amount(value: Decimal | None) -> Decimal:
    return value or Decimal("0")


def _payment_reference(payment: Payment | SupplierPayment) -> str:
    return (
        getattr(payment, "payment_number", None)
        or getattr(payment, "payment_ref", None)
        or getattr(payment, "reference_number", None)
        or str(payment.id)
    )


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
    base_subtotal = _decimal_amount(invoice.base_subtotal_amount)
    base_tax = _decimal_amount(invoice.base_tax_amount)
    base_total = _decimal_amount(invoice.base_total_amount)
    created_entries: list[GLEntry] = []
    
    # DR: Accounts Receivable
    created_entries.append(await create_gl_entry_from_posting(
        session=session,
        tenant_id=tenant_id,
        account_id=_account_mapping_id(receivable_account_id),
        debit=base_total,
        credit=Decimal("0"),
        posting_date=invoice.invoice_date,
        fiscal_year_label=fiscal_year.label,
        entry_type=GLEntryType.CUSTOMER_INVOICE,
        voucher_type="Customer Invoice",
        voucher_number=invoice.invoice_number,
        source_type="Invoice",
        source_id=invoice.id,
        remark=f"Invoice {invoice.invoice_number}",
    ))
    
    # CR: Revenue
    created_entries.append(await create_gl_entry_from_posting(
        session=session,
        tenant_id=tenant_id,
        account_id=_account_mapping_id(revenue_account_id),
        debit=Decimal("0"),
        credit=base_subtotal,
        posting_date=invoice.invoice_date,
        fiscal_year_label=fiscal_year.label,
        entry_type=GLEntryType.CUSTOMER_INVOICE,
        voucher_type="Customer Invoice",
        voucher_number=invoice.invoice_number,
        source_type="Invoice",
        source_id=invoice.id,
        remark=f"Invoice {invoice.invoice_number}",
    ))
    
    # CR: Tax (if tax amount exists)
    if base_tax > 0 and tax_account_id:
        created_entries.append(await create_gl_entry_from_posting(
            session=session,
            tenant_id=tenant_id,
            account_id=_account_mapping_id(tax_account_id),
            debit=Decimal("0"),
            credit=base_tax,
            posting_date=invoice.invoice_date,
            fiscal_year_label=fiscal_year.label,
            entry_type=GLEntryType.CUSTOMER_INVOICE,
            voucher_type="Customer Invoice",
            voucher_number=invoice.invoice_number,
            source_type="Invoice",
            source_id=invoice.id,
            remark=f"Tax on Invoice {invoice.invoice_number}",
        ))
    
    # Update posting state
    state.status = PostingStatus.POSTED
    state.posting_rule_id = rule.id
    state.rule_version_at_posting = rule.version
    state.gl_entry_ids = [str(entry.id) for entry in created_entries]
    state.error_message = None
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
    
    base_amount = _decimal_amount(payment.base_amount)
    payment_reference = _payment_reference(payment)
    created_entries: list[GLEntry] = []
    
    # DR: Cash/Bank
    created_entries.append(await create_gl_entry_from_posting(
        session=session,
        tenant_id=tenant_id,
        account_id=_account_mapping_id(bank_account_id),
        debit=base_amount,
        credit=Decimal("0"),
        posting_date=payment.payment_date,
        fiscal_year_label=fiscal_year.label,
        entry_type=GLEntryType.CUSTOMER_PAYMENT,
        voucher_type="Customer Payment",
        voucher_number=payment_reference,
        source_type="Payment",
        source_id=payment.id,
        remark=f"Payment {payment_reference}",
    ))
    
    # CR: Accounts Receivable
    created_entries.append(await create_gl_entry_from_posting(
        session=session,
        tenant_id=tenant_id,
        account_id=_account_mapping_id(receivable_account_id),
        debit=Decimal("0"),
        credit=base_amount,
        posting_date=payment.payment_date,
        fiscal_year_label=fiscal_year.label,
        entry_type=GLEntryType.CUSTOMER_PAYMENT,
        voucher_type="Customer Payment",
        voucher_number=payment_reference,
        source_type="Payment",
        source_id=payment.id,
        remark=f"Payment {payment_reference}",
    ))
    
    # Update state
    state.status = PostingStatus.POSTED
    state.posting_rule_id = rule.id
    state.rule_version_at_posting = rule.version
    state.gl_entry_ids = [str(entry.id) for entry in created_entries]
    state.error_message = None
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
    
    base_subtotal = _decimal_amount(supplier_invoice.base_subtotal_amount)
    base_tax = _decimal_amount(supplier_invoice.base_tax_amount)
    base_total = _decimal_amount(supplier_invoice.base_total_amount)
    created_entries: list[GLEntry] = []
    
    # DR: Expense
    created_entries.append(await create_gl_entry_from_posting(
        session=session,
        tenant_id=tenant_id,
        account_id=_account_mapping_id(expense_account_id),
        debit=base_subtotal,
        credit=Decimal("0"),
        posting_date=supplier_invoice.invoice_date,
        fiscal_year_label=fiscal_year.label,
        entry_type=GLEntryType.SUPPLIER_INVOICE,
        voucher_type="Supplier Invoice",
        voucher_number=supplier_invoice.invoice_number,
        source_type="SupplierInvoice",
        source_id=supplier_invoice.id,
        remark=f"Supplier Invoice {supplier_invoice.invoice_number}",
    ))
    
    # DR: Tax (if applicable)
    if base_tax > 0 and tax_account_id:
        created_entries.append(await create_gl_entry_from_posting(
            session=session,
            tenant_id=tenant_id,
            account_id=_account_mapping_id(tax_account_id),
            debit=base_tax,
            credit=Decimal("0"),
            posting_date=supplier_invoice.invoice_date,
            fiscal_year_label=fiscal_year.label,
            entry_type=GLEntryType.SUPPLIER_INVOICE,
            voucher_type="Supplier Invoice",
            voucher_number=supplier_invoice.invoice_number,
            source_type="SupplierInvoice",
            source_id=supplier_invoice.id,
            remark=f"Tax on Supplier Invoice {supplier_invoice.invoice_number}",
        ))
    
    # CR: Accounts Payable
    created_entries.append(await create_gl_entry_from_posting(
        session=session,
        tenant_id=tenant_id,
        account_id=_account_mapping_id(payable_account_id),
        debit=Decimal("0"),
        credit=base_total,
        posting_date=supplier_invoice.invoice_date,
        fiscal_year_label=fiscal_year.label,
        entry_type=GLEntryType.SUPPLIER_INVOICE,
        voucher_type="Supplier Invoice",
        voucher_number=supplier_invoice.invoice_number,
        source_type="SupplierInvoice",
        source_id=supplier_invoice.id,
        remark=f"Supplier Invoice {supplier_invoice.invoice_number}",
    ))
    
    state.status = PostingStatus.POSTED
    state.posting_rule_id = rule.id
    state.rule_version_at_posting = rule.version
    state.gl_entry_ids = [str(entry.id) for entry in created_entries]
    state.error_message = None
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
    
    base_amount = _decimal_amount(supplier_payment.base_amount)
    payment_reference = _payment_reference(supplier_payment)
    created_entries: list[GLEntry] = []
    
    # DR: Accounts Payable
    created_entries.append(await create_gl_entry_from_posting(
        session=session,
        tenant_id=tenant_id,
        account_id=_account_mapping_id(payable_account_id),
        debit=base_amount,
        credit=Decimal("0"),
        posting_date=supplier_payment.payment_date,
        fiscal_year_label=fiscal_year.label,
        entry_type=GLEntryType.SUPPLIER_PAYMENT,
        voucher_type="Supplier Payment",
        voucher_number=payment_reference,
        source_type="SupplierPayment",
        source_id=supplier_payment.id,
        remark=f"Payment {payment_reference}",
    ))
    
    # CR: Cash/Bank
    created_entries.append(await create_gl_entry_from_posting(
        session=session,
        tenant_id=tenant_id,
        account_id=_account_mapping_id(bank_account_id),
        debit=Decimal("0"),
        credit=base_amount,
        posting_date=supplier_payment.payment_date,
        fiscal_year_label=fiscal_year.label,
        entry_type=GLEntryType.SUPPLIER_PAYMENT,
        voucher_type="Supplier Payment",
        voucher_number=payment_reference,
        source_type="SupplierPayment",
        source_id=supplier_payment.id,
        remark=f"Payment {payment_reference}",
    ))
    
    state.status = PostingStatus.POSTED
    state.posting_rule_id = rule.id
    state.rule_version_at_posting = rule.version
    state.gl_entry_ids = [str(entry.id) for entry in created_entries]
    state.error_message = None
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
    gl_entry_ids = [
        uuid.UUID(entry_id) if isinstance(entry_id, str) else entry_id
        for entry_id in state.gl_entry_ids
    ]
    if not gl_entry_ids:
        return False, "No GL entries found for reversal"

    result = await session.execute(
        select(GLEntry).where(
            and_(
                GLEntry.tenant_id == tenant_id,
                GLEntry.id.in_(gl_entry_ids),
            )
        )
    )
    original_entries = result.scalars().all()
    
    if not original_entries:
        return False, "No GL entries found for reversal"
    
    reversal_entries: list[GLEntry] = []
    
    # Update original state
    state.status = PostingStatus.REVERSED
    state.error_message = None
    state.posted_at = datetime.now(UTC)

    # Create reversing entries
    for entry in original_entries:
        reversal_entry = await create_gl_entry_from_posting(
            session=session,
            tenant_id=tenant_id,
            account_id=entry.account_id,
            debit=entry.credit,
            credit=entry.debit,
            posting_date=reversal_date.date() if hasattr(reversal_date, 'date') else reversal_date,
            fiscal_year_label=reversal_fiscal_year.label,
            entry_type=entry.entry_type,
            voucher_type=f"Reversal - {entry.voucher_type}",
            voucher_number=entry.voucher_number,
            source_type=entry.source_type,
            source_id=entry.source_id,
            remark=reversal_narration or f"Reversal: {entry.remark or entry.voucher_number}",
            reverses_id=entry.id,
        )
        entry.reversed_by_id = reversal_entry.id
        reversal_entries.append(reversal_entry)

    state.gl_entry_ids = [
        *state.gl_entry_ids,
        *(str(entry.id) for entry in reversal_entries),
    ]

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
    fiscal_year_label: str,
    entry_type: GLEntryType | str,
    voucher_type: str,
    voucher_number: str,
    source_type: str | None = None,
    source_id: uuid.UUID | None = None,
    remark: str | None = None,
    reverses_id: uuid.UUID | None = None,
) -> GLEntry:
    """Create a GL entry for document posting."""
    # Validate posting date is a date, not datetime
    if hasattr(posting_date, 'date'):
        posting_date = posting_date.date()
    
    entry = GLEntry(
        tenant_id=tenant_id,
        account_id=account_id,
        posting_date=posting_date,
        fiscal_year=fiscal_year_label,
        debit=debit,
        credit=credit,
        entry_type=entry_type,
        voucher_type=voucher_type,
        voucher_number=voucher_number,
        source_type=source_type,
        source_id=source_id,
        remark=remark,
        reverses_id=reverses_id,
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
            FiscalYear.status == FiscalYearStatus.OPEN.value
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
