"""
PostingRule and DocumentPostingState models for Epic 26 Story 26-4.
Defines explicit, versioned posting rules for document auto-posting.
"""
from __future__ import annotations

import uuid
from datetime import datetime, UTC
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.database import Base

if TYPE_CHECKING:
    pass


def _enum_values(enum_cls: type[Enum]) -> list[str]:
    return [member.value for member in enum_cls]


class DocumentType(str, Enum):
    """Supported document types for auto-posting."""
    CUSTOMER_INVOICE = "customer_invoice"
    CUSTOMER_PAYMENT = "customer_payment"
    SUPPLIER_INVOICE = "supplier_invoice"
    SUPPLIER_PAYMENT = "supplier_payment"
    JOURNAL_ENTRY = "journal_entry"


class PostingStatus(str, Enum):
    """Posting status for documents."""
    NOT_APPLICABLE = "not_applicable"
    NOT_CONFIGURED = "not_configured"
    PENDING = "pending"
    POSTED = "posted"
    FAILED = "failed"
    REVERSED = "reversed"


class PostingRule(Base):
    """Posting rule configuration for a document type.
    
    A posting rule defines which GL accounts to post to for a specific
    document type. Rules are versioned and applied prospectively.
    """
    __tablename__ = "posting_rules"
    __table_args__ = (
        Index("ix_posting_rules_tenant_doc_type", "tenant_id", "document_type", unique=True),
        Index("ix_posting_rules_is_active", "tenant_id", "is_active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    document_type: Mapped[str] = mapped_column(
        SAEnum(DocumentType, name="document_type_enum", values_callable=_enum_values),
        nullable=False
    )
    version: Mapped[int] = mapped_column(default=1)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    # Account mappings (JSON for flexibility)
    # Example: {"debit_accounts": [{"type": "receivable", "account_id": "uuid"}], "credit_accounts": [...]}
    account_mappings: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    
    # Tax account mapping (for invoice tax posting)
    tax_account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=True
    )
    
    # Write-off account for payment reconciliation differences
    write_off_account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=True
    )
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    created_by: Mapped[str | None] = mapped_column(String(100), nullable=True)


class DocumentPostingState(Base):
    """Tracks the posting state of a commercial document.
    
    Each document that participates in auto-posting has one posting state record
    that links the document to its GL entries and posting rule version.
    """
    __tablename__ = "document_posting_states"
    __table_args__ = (
        Index("ix_doc_posting_state_doc", "document_type", "document_id", unique=True),
        Index("ix_doc_posting_state_tenant", "tenant_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    document_type: Mapped[str] = mapped_column(
        SAEnum(DocumentType, name="document_type_enum", values_callable=_enum_values),
        nullable=False
    )
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    
    status: Mapped[str] = mapped_column(
        SAEnum(PostingStatus, name="posting_status_enum", values_callable=_enum_values),
        nullable=False,
        default=PostingStatus.NOT_CONFIGURED
    )
    
    # Reference to the posting rule version used
    posting_rule_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("posting_rules.id"), nullable=True
    )
    rule_version_at_posting: Mapped[int | None] = mapped_column(default=None)
    
    # GL entry references (JSON array of GL entry IDs)
    gl_entry_ids: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    
    # Reversal reference (points to the reversing posting state)
    reversed_by_state_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_posting_states.id"), nullable=True
    )
    reverses_state_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_posting_states.id"), nullable=True
    )
    
    # Error message if posting failed
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )
    
    # Relationships
    posting_rule: Mapped["PostingRule | None"] = relationship(
        "PostingRule", foreign_keys=[posting_rule_id]
    )
