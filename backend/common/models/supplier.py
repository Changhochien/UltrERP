"""Supplier model with procurement controls (Story 24-5)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.database import Base

if TYPE_CHECKING:
    from common.models.payment_terms import PaymentTermsTemplate


class Supplier(Base):
    __tablename__ = "supplier"
    __table_args__ = (
        # Index for filtering active suppliers
        Index("ix_supplier_tenant_active", "tenant_id", "is_active"),
        Index("ix_supplier_default_currency", "tenant_id", "default_currency_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True,
    )
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    contact_email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(50))
    address: Mapped[str | None] = mapped_column(String(500))
    default_lead_time_days: Mapped[int | None] = mapped_column(Integer)
    legacy_master_snapshot: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    # ─────────────────────────────────────────────────────────────
    # Procurement Hold Controls (Story 24-5)
    # ─────────────────────────────────────────────────────────────
    # Hold state: if True, supplier is blocked from RFQ/PO creation
    on_hold: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
    )
    # Hold type: e.g., "quality", "payment", "compliance", "manual"
    hold_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True,
    )
    # Future-date release: supplier auto-releases on this date
    # Deterministic enforcement in procurement workflows
    release_date: Mapped[date | None] = mapped_column(
        Date, nullable=True,
    )

    # ─────────────────────────────────────────────────────────────
    # Commercial Profile Defaults (Story 25-4)
    # ─────────────────────────────────────────────────────────────
    default_currency_code: Mapped[str | None] = mapped_column(String(3), nullable=True)
    payment_terms_template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "payment_terms_templates.id",
            name="fk_supplier_payment_terms_template",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    # Relationships
    payment_terms_template: Mapped[PaymentTermsTemplate | None] = relationship()

    # ─────────────────────────────────────────────────────────────
    # Supplier Scorecard Fields (Story 24-5)
    # ─────────────────────────────────────────────────────────────
    # Standing: e.g., "active", "preferred", "warning", "blocked"
    scorecard_standing: Mapped[str | None] = mapped_column(
        String(30), nullable=True,
    )
    # Last evaluation timestamp
    scorecard_last_evaluated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    # RFQ control flags
    warn_rfqs: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
    )
    prevent_rfqs: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
    )
    # PO control flags
    warn_pos: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
    )
    prevent_pos: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
    )

    # ─────────────────────────────────────────────────────────────
    # Subcontractor Flag (Story 24-5, used by Story 24-6)
    # ─────────────────────────────────────────────────────────────
    # If True, this supplier can be used in subcontracting workflows
    is_subcontractor: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
    )

    # ─────────────────────────────────────────────────────────────
    # Helper methods for supplier control checks (Story 24-5)
    # ─────────────────────────────────────────────────────────────

    def is_effectively_on_hold(self, check_date: date | None = None) -> bool:
        """Check if supplier is effectively on hold.

        A supplier is on hold if:
        - on_hold is True, OR
        - release_date is set and check_date >= release_date

        Args:
            check_date: Date to check against (defaults to today)
        """
        if self.on_hold:
            return True
        if self.release_date is not None:
            effective_date = check_date or date.today()
            return effective_date >= self.release_date
        return False

    def get_rfq_controls(self) -> tuple[bool, bool, str]:
        """Get RFQ warning and blocking status.

        Returns:
            Tuple of (is_blocked, is_warned, reason)
        """
        if self.prevent_rfqs:
            return True, False, f"Supplier '{self.name}' is blocked from RFQs by scorecard policy."
        if self.is_effectively_on_hold():
            hold_reason = f" (type: {self.hold_type})" if self.hold_type else ""
            return True, False, f"Supplier '{self.name}' is on hold{hold_reason}."
        if self.warn_rfqs:
            return False, True, f"Supplier '{self.name}' has RFQ warnings. Review scorecard."
        return False, False, ""

    def get_po_controls(self) -> tuple[bool, bool, str]:
        """Get PO warning and blocking status.

        Returns:
            Tuple of (is_blocked, is_warned, reason)
        """
        if self.prevent_pos:
            return True, False, f"Supplier '{self.name}' is blocked from POs by scorecard policy."
        if self.is_effectively_on_hold():
            hold_reason = f" (type: {self.hold_type})" if self.hold_type else ""
            return True, False, f"Supplier '{self.name}' is on hold{hold_reason}."
        if self.warn_pos:
            return False, True, f"Supplier '{self.name}' has PO warnings. Review scorecard."
        return False, False, ""
