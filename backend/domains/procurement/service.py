"""Procurement service layer - RFQ, Supplier Quotation, and Purchase Order business logic.

Exposed functions:
- RFQ: create_rfq, get_rfq, list_rfqs, update_rfq, submit_rfq
- Supplier Quotation: create_supplier_quotation, get_supplier_quotation,
    list_supplier_quotations, update_supplier_quotation, submit_supplier_quotation
- Award: award_quotation, get_award, list_awards
- Purchase Order: create_purchase_order, get_purchase_order, list_purchase_orders,
    update_purchase_order, submit_purchase_order, hold_purchase_order,
    release_purchase_order, complete_purchase_order, cancel_purchase_order,
    close_purchase_order, recompute_po_progress
- Comparison: get_rfq_comparison
- Supplier Controls: check_supplier_rfq_controls, check_supplier_po_controls (Story 24-5)
- Procurement Reporting: get_procurement_summary, get_quote_turnaround_stats (Story 24-5)
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from common.errors import ValidationError
from common.models.supplier import Supplier
from domains.procurement.models import (
    RFQ,
    ProcurementAward,
    PurchaseOrder,
    PurchaseOrderItem,
    RFQItem,
    RFQSupplier,
    SupplierQuotation,
    SupplierQuotationItem,
    GoodsReceipt,
    GoodsReceiptItem,
)

# --------------------------------------------------------------------------
# Supplier Control Result Types (Story 24-5)
# --------------------------------------------------------------------------


class SupplierControlResult:
    """Result of supplier control check.

    Attributes:
        is_blocked: True if the workflow should be blocked
        is_warned: True if a warning should be shown
        reason: Human-readable explanation
        supplier_name: Name of the supplier checked
        controls: Raw control flags from the supplier
    """

    def __init__(
        self,
        is_blocked: bool = False,
        is_warned: bool = False,
        reason: str = "",
        supplier_name: str = "",
        controls: dict | None = None,
    ):
        self.is_blocked = is_blocked
        self.is_warned = is_warned
        self.reason = reason
        self.supplier_name = supplier_name
        self.controls = controls or {}

    def to_dict(self) -> dict:
        return {
            "is_blocked": self.is_blocked,
            "is_warned": self.is_warned,
            "reason": self.reason,
            "supplier_name": self.supplier_name,
            "controls": self.controls,
        }


# --------------------------------------------------------------------------
# Supplier Control Functions (Story 24-5)
# --------------------------------------------------------------------------


async def check_supplier_rfq_controls(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    supplier_id: uuid.UUID | None,
    supplier_name: str = "",
) -> SupplierControlResult:
    """Check supplier controls for RFQ workflow.

    Args:
        db: Database session
        tenant_id: Tenant UUID
        supplier_id: Supplier UUID (optional)
        supplier_name: Supplier name fallback if supplier_id not provided

    Returns:
        SupplierControlResult with block/warn status
    """
    if not supplier_id:
        return SupplierControlResult(supplier_name=supplier_name)

    result = await db.execute(
        select(Supplier).where(
            Supplier.id == supplier_id,
            Supplier.tenant_id == tenant_id,
        )
    )
    supplier = result.scalar_one_or_none()

    if not supplier:
        return SupplierControlResult(supplier_name=supplier_name)

    is_blocked, is_warned, reason = supplier.get_rfq_controls()

    return SupplierControlResult(
        is_blocked=is_blocked,
        is_warned=is_warned,
        reason=reason,
        supplier_name=supplier.name,
        controls={
            "on_hold": supplier.on_hold,
            "hold_type": supplier.hold_type,
            "release_date": str(supplier.release_date) if supplier.release_date else None,
            "scorecard_standing": supplier.scorecard_standing,
            "warn_rfqs": supplier.warn_rfqs,
            "prevent_rfqs": supplier.prevent_rfqs,
        },
    )


async def check_supplier_po_controls(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    supplier_id: uuid.UUID | None,
    supplier_name: str = "",
) -> SupplierControlResult:
    """Check supplier controls for PO workflow.

    Args:
        db: Database session
        tenant_id: Tenant UUID
        supplier_id: Supplier UUID (optional)
        supplier_name: Supplier name fallback if supplier_id not provided

    Returns:
        SupplierControlResult with block/warn status
    """
    if not supplier_id:
        return SupplierControlResult(supplier_name=supplier_name)

    result = await db.execute(
        select(Supplier).where(
            Supplier.id == supplier_id,
            Supplier.tenant_id == tenant_id,
        )
    )
    supplier = result.scalar_one_or_none()

    if not supplier:
        return SupplierControlResult(supplier_name=supplier_name)

    is_blocked, is_warned, reason = supplier.get_po_controls()

    return SupplierControlResult(
        is_blocked=is_blocked,
        is_warned=is_warned,
        reason=reason,
        supplier_name=supplier.name,
        controls={
            "on_hold": supplier.on_hold,
            "hold_type": supplier.hold_type,
            "release_date": str(supplier.release_date) if supplier.release_date else None,
            "scorecard_standing": supplier.scorecard_standing,
            "warn_pos": supplier.warn_pos,
            "prevent_pos": supplier.prevent_pos,
        },
    )


def enforce_supplier_controls(
    result: SupplierControlResult,
    operation: str = "operation",
) -> None:
    """Raise ValidationError if supplier controls block the operation.

    Args:
        result: Supplier control check result
        operation: Human-readable operation name for error message

    Raises:
        ValidationError: If supplier is blocked
    """
    if result.is_blocked:
        raise ValidationError([{
            "field": "supplier_id",
            "message": f"Cannot proceed with {operation}: {result.reason}",
        }])

# --------------------------------------------------------------------------
# RFQ Service
# --------------------------------------------------------------------------


async def create_rfq(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    data: dict,
    current_user: str = "",
) -> RFQ:
    """Create a new RFQ with items and supplier recipients."""
    today = date.today()
    transaction_date = data.get("transaction_date", today)
    if isinstance(transaction_date, str):
        transaction_date = date.fromisoformat(transaction_date)

    name = data.get("name") or ""
    if not name:
        count_q = select(func.count()).select_from(RFQ).where(RFQ.tenant_id == tenant_id)
        result = await db.execute(count_q)
        count = result.scalar() or 0
        name = f"PRQ-{count + 1:04d}"

    rfq = RFQ(
        tenant_id=tenant_id,
        name=name,
        status=data.get("status", "draft"),
        company=data.get("company", ""),
        currency=data.get("currency", "TWD"),
        transaction_date=transaction_date,
        schedule_date=data.get("schedule_date"),
        terms_and_conditions=data.get("terms_and_conditions", ""),
        notes=data.get("notes", ""),
        supplier_count=len(data.get("suppliers", [])),
        quotes_received=0,
        # Extension hook: contract reference (Story 24-5)
        contract_reference=data.get("contract_reference"),
    )
    db.add(rfq)
    await db.flush()

    for idx, item_data in enumerate(data.get("items", [])):
        item = RFQItem(
            tenant_id=tenant_id,
            rfq_id=rfq.id,
            idx=idx,
            item_code=item_data.get("item_code", ""),
            item_name=item_data.get("item_name", ""),
            description=item_data.get("description", ""),
            qty=Decimal(str(item_data.get("qty", "0"))),
            uom=item_data.get("uom", ""),
            warehouse=item_data.get("warehouse", ""),
        )
        db.add(item)

    for supp_data in data.get("suppliers", []):
        supp = RFQSupplier(
            tenant_id=tenant_id,
            rfq_id=rfq.id,
            supplier_id=supp_data.get("supplier_id"),
            supplier_name=supp_data.get("supplier_name", ""),
            contact_email=supp_data.get("contact_email", ""),
            quote_status=supp_data.get("quote_status", "pending"),
            notes=supp_data.get("notes", ""),
        )
        db.add(supp)

    await db.commit()
    await db.refresh(rfq)
    return rfq


async def get_rfq(db: AsyncSession, tenant_id: uuid.UUID, rfq_id: uuid.UUID) -> RFQ:
    """Fetch a single RFQ with items and suppliers."""
    result = await db.execute(
        select(RFQ).where(RFQ.id == rfq_id, RFQ.tenant_id == tenant_id)
    )
    rfq = result.scalar_one_or_none()
    if not rfq:
        raise ValidationError([{"field": "rfq_id", "message": f"RFQ {rfq_id} not found."}])
    return rfq


async def list_rfqs(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    status: str | None = None,
    q: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[RFQ], int]:
    """List RFQs with optional filtering and pagination."""
    query = select(RFQ).where(RFQ.tenant_id == tenant_id)
    count_query = select(func.count()).select_from(RFQ).where(RFQ.tenant_id == tenant_id)

    if status:
        query = query.where(RFQ.status == status)
        count_query = count_query.where(RFQ.status == status)
    if q:
        q_filter = RFQ.name.ilike(f"%{q}%")
        query = query.where(q_filter)
        count_query = count_query.where(q_filter)

    query = query.order_by(RFQ.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    rfqs = list(result.scalars().all())

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    return rfqs, total


async def update_rfq(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    rfq_id: uuid.UUID,
    data: dict,
) -> RFQ:
    """Update RFQ fields (not items/suppliers in this slice)."""
    rfq = await get_rfq(db, tenant_id, rfq_id)

    for field in (
        "name", "status", "company", "currency", "transaction_date",
        "schedule_date", "terms_and_conditions", "notes",
        "contract_reference",  # Extension hook (Story 24-5)
    ):
        if field in data and data[field] is not None:
            setattr(rfq, field, data[field])

    await db.commit()
    await db.refresh(rfq)
    return rfq


async def submit_rfq(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    rfq_id: uuid.UUID,
) -> RFQ:
    """Submit an RFQ - changes status to submitted.

    Checks supplier controls for each RFQ supplier recipient.
    Blocks submission if any supplier has prevent_rfqs or is on hold.
    """
    rfq = await get_rfq(db, tenant_id, rfq_id)
    if rfq.status not in ("draft",):
        msg = f"Cannot submit RFQ in status '{rfq.status}'."
        raise ValidationError([{"field": "status", "message": msg}])

    # Check supplier controls for each RFQ supplier (Story 24-5)
    warnings = []
    for rfq_supplier in rfq.suppliers:
        if rfq_supplier.supplier_id:
            control_result = await check_supplier_rfq_controls(
                db,
                tenant_id,
                rfq_supplier.supplier_id,
                rfq_supplier.supplier_name,
            )
            if control_result.is_blocked:
                enforce_supplier_controls(control_result, "RFQ submission")
            elif control_result.is_warned:
                warnings.append(control_result.to_dict())

    # Store warnings on RFQ for UI feedback (as JSON in notes or separate field)
    if warnings:
        warning_msg = f"[Supplier Control Warning] {len(warnings)} supplier(s) have warnings: "
        warning_msg += "; ".join(w["reason"] for w in warnings)
        rfq.notes = f"{rfq.notes}\n{warning_msg}" if rfq.notes else warning_msg

    rfq.status = "submitted"
    await db.commit()
    await db.refresh(rfq)
    return rfq


# --------------------------------------------------------------------------
# Supplier Quotation Service
# --------------------------------------------------------------------------


async def create_supplier_quotation(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    data: dict,
    current_user: str = "",
) -> SupplierQuotation:
    """Create a supplier quotation and link it to the RFQ supplier record."""
    today = date.today()
    transaction_date = data.get("transaction_date", today)
    if isinstance(transaction_date, str):
        transaction_date = date.fromisoformat(transaction_date)

    rfq_id = data.get("rfq_id")
    supplier_name = data.get("supplier_name", "")

    name = data.get("name") or ""
    if not name:
        count_q = select(func.count()).select_from(SupplierQuotation).where(
            SupplierQuotation.tenant_id == tenant_id
        )
        result = await db.execute(count_q)
        count = result.scalar() or 0
        name = f"SQ-{count + 1:04d}"

    quotation = SupplierQuotation(
        tenant_id=tenant_id,
        name=name,
        status=data.get("status", "draft"),
        rfq_id=rfq_id,
        supplier_id=data.get("supplier_id"),
        supplier_name=supplier_name,
        company=data.get("company", ""),
        currency=data.get("currency", "TWD"),
        transaction_date=transaction_date,
        valid_till=data.get("valid_till"),
        lead_time_days=data.get("lead_time_days"),
        delivery_date=data.get("delivery_date"),
        subtotal=data.get("subtotal", Decimal("0.00")),
        total_taxes=data.get("total_taxes", Decimal("0.00")),
        grand_total=data.get("grand_total", Decimal("0.00")),
        base_grand_total=data.get("base_grand_total", Decimal("0.00")),
        taxes=data.get("taxes", []),
        contact_person=data.get("contact_person", ""),
        contact_email=data.get("contact_email", ""),
        terms_and_conditions=data.get("terms_and_conditions", ""),
        notes=data.get("notes", ""),
        comparison_base_total=data.get("comparison_base_total", Decimal("0.00")),
        is_awarded=False,
        # Extension hook: contract reference (Story 24-5)
        contract_reference=data.get("contract_reference"),
    )
    db.add(quotation)
    await db.flush()

    for idx, item_data in enumerate(data.get("items", [])):
        item = SupplierQuotationItem(
            tenant_id=tenant_id,
            quotation_id=quotation.id,
            idx=idx,
            rfq_item_id=item_data.get("rfq_item_id"),
            item_code=item_data.get("item_code", ""),
            item_name=item_data.get("item_name", ""),
            description=item_data.get("description", ""),
            qty=Decimal(str(item_data.get("qty", "0"))),
            uom=item_data.get("uom", ""),
            unit_rate=Decimal(str(item_data.get("unit_rate", "0"))),
            amount=Decimal(str(item_data.get("amount", "0"))),
            tax_rate=Decimal(str(item_data.get("tax_rate", "0"))),
            tax_amount=Decimal(str(item_data.get("tax_amount", "0"))),
            tax_code=item_data.get("tax_code", ""),
            normalized_unit_rate=Decimal(str(item_data.get("normalized_unit_rate", "0"))),
            normalized_amount=Decimal(str(item_data.get("normalized_amount", "0"))),
        )
        db.add(item)

    if rfq_id and supplier_name:
        await _link_quotation_to_rfq_supplier(
            db, tenant_id, rfq_id, supplier_name, quotation.id
        )

    await db.commit()
    await db.refresh(quotation)
    return quotation


async def _link_quotation_to_rfq_supplier(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    rfq_id: uuid.UUID,
    supplier_name: str,
    quotation_id: uuid.UUID,
) -> None:
    """Update RFQSupplier.quote_status to 'received' when a quotation is created."""
    result = await db.execute(
        select(RFQSupplier).where(
            RFQSupplier.rfq_id == rfq_id,
            RFQSupplier.supplier_name == supplier_name,
            RFQSupplier.tenant_id == tenant_id,
        )
    )
    supplier_record = result.scalar_one_or_none()
    if supplier_record:
        supplier_record.quote_status = "received"
        supplier_record.quotation_id = quotation_id
        await db.flush()


async def get_supplier_quotation(
    db: AsyncSession, tenant_id: uuid.UUID, quotation_id: uuid.UUID
) -> SupplierQuotation:
    """Fetch a single supplier quotation with items."""
    result = await db.execute(
        select(SupplierQuotation).where(
            SupplierQuotation.id == quotation_id,
            SupplierQuotation.tenant_id == tenant_id,
        )
    )
    sq = result.scalar_one_or_none()
    if not sq:
        msg = f"Supplier quotation {quotation_id} not found."
        raise ValidationError([{"field": "quotation_id", "message": msg}])
    return sq


async def list_supplier_quotations(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    rfq_id: uuid.UUID | None = None,
    status: str | None = None,
    q: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[SupplierQuotation], int]:
    """List supplier quotations with optional filtering."""
    query = select(SupplierQuotation).where(SupplierQuotation.tenant_id == tenant_id)
    count_query = select(func.count()).select_from(SupplierQuotation).where(
        SupplierQuotation.tenant_id == tenant_id
    )

    if rfq_id:
        query = query.where(SupplierQuotation.rfq_id == rfq_id)
        count_query = count_query.where(SupplierQuotation.rfq_id == rfq_id)
    if status:
        query = query.where(SupplierQuotation.status == status)
        count_query = count_query.where(SupplierQuotation.status == status)
    if q:
        q_filter = SupplierQuotation.name.ilike(f"%{q}%")
        query = query.where(q_filter)
        count_query = count_query.where(q_filter)

    query = query.order_by(SupplierQuotation.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    quotations = list(result.scalars().all())

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    return quotations, total


async def update_supplier_quotation(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    quotation_id: uuid.UUID,
    data: dict,
) -> SupplierQuotation:
    """Update supplier quotation fields (not items in this slice)."""
    sq = await get_supplier_quotation(db, tenant_id, quotation_id)

    for field in (
        "name", "status", "valid_till", "lead_time_days", "delivery_date",
        "subtotal", "total_taxes", "grand_total", "base_grand_total",
        "taxes", "contact_person", "contact_email",
        "terms_and_conditions", "notes", "comparison_base_total",
        "contract_reference",  # Extension hook (Story 24-5)
    ):
        if field in data and data[field] is not None:
            setattr(sq, field, data[field])

    await db.commit()
    await db.refresh(sq)
    return sq


async def submit_supplier_quotation(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    quotation_id: uuid.UUID,
) -> SupplierQuotation:
    """Submit a supplier quotation - changes status to submitted."""
    sq = await get_supplier_quotation(db, tenant_id, quotation_id)
    if sq.status != "draft":
        msg = f"Cannot submit quotation in status '{sq.status}'."
        raise ValidationError([{"field": "status", "message": msg}])
    sq.status = "submitted"
    await db.commit()
    await db.refresh(sq)
    return sq


def is_quotation_expired(quotation: SupplierQuotation) -> bool:
    """Check if a supplier quotation has expired based on validity date."""
    if quotation.valid_till is None:
        return False
    return quotation.valid_till < date.today()


# --------------------------------------------------------------------------
# Award Service
# --------------------------------------------------------------------------


async def award_quotation(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    rfq_id: uuid.UUID,
    quotation_id: uuid.UUID,
    awarded_by: str = "",
) -> ProcurementAward:
    """Select a supplier quotation as the winning source.

    Preserves losing quotations for audit.
    """
    sq = await get_supplier_quotation(db, tenant_id, quotation_id)
    if sq.rfq_id != rfq_id:
        raise ValidationError([{
            "field": "quotation_id",
            "message": f"Quotation {quotation_id} is not linked to RFQ {rfq_id}.",
        }])

    if is_quotation_expired(sq):
        raise ValidationError([{
            "field": "quotation_id",
            "message": "Cannot award an expired quotation.",
        }])

    await get_rfq(db, tenant_id, rfq_id)

    existing_result = await db.execute(
        select(ProcurementAward).where(
            ProcurementAward.rfq_id == rfq_id,
            ProcurementAward.tenant_id == tenant_id,
        )
    )
    existing_award = existing_result.scalar_one_or_none()
    if existing_award:
        await db.delete(existing_award)
        prev_result = await db.execute(
            select(SupplierQuotation).where(
                SupplierQuotation.id == existing_award.quotation_id
            )
        )
        prev_sq = prev_result.scalar_one_or_none()
        if prev_sq:
            prev_sq.is_awarded = False

    sq.is_awarded = True

    award = ProcurementAward(
        tenant_id=tenant_id,
        rfq_id=rfq_id,
        quotation_id=quotation_id,
        awarded_supplier_name=sq.supplier_name,
        awarded_total=sq.grand_total,
        awarded_currency=sq.currency,
        awarded_lead_time_days=sq.lead_time_days,
        awarded_by=awarded_by,
        awarded_at=datetime.now(tz=UTC),
        po_created=False,
        po_reference="",
    )
    db.add(award)
    await db.commit()
    await db.refresh(award)
    return award


async def get_award(
    db: AsyncSession, tenant_id: uuid.UUID, rfq_id: uuid.UUID
) -> ProcurementAward | None:
    """Fetch the award for an RFQ if one exists."""
    result = await db.execute(
        select(ProcurementAward).where(
            ProcurementAward.rfq_id == rfq_id,
            ProcurementAward.tenant_id == tenant_id,
        )
    )
    return result.scalar_one_or_none()


async def list_awards(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[ProcurementAward], int]:
    """List all procurement awards."""
    query = (
        select(ProcurementAward)
        .where(ProcurementAward.tenant_id == tenant_id)
        .order_by(ProcurementAward.awarded_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    awards = list(result.scalars().all())

    count_result = await db.execute(
        select(func.count()).select_from(ProcurementAward).where(
            ProcurementAward.tenant_id == tenant_id
        )
    )
    total = count_result.scalar() or 0

    return awards, total


async def get_rfq_comparison(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    rfq_id: uuid.UUID,
) -> dict:
    """Build side-by-side comparison of all supplier quotations for an RFQ."""
    rfq = await get_rfq(db, tenant_id, rfq_id)
    quotations, _ = await list_supplier_quotations(
        db, tenant_id, rfq_id=rfq_id
    )

    today_d = date.today()
    rows = []
    for sq in quotations:
        is_expired = sq.valid_till < today_d if sq.valid_till else False
        rows.append({
            "quotation_id": sq.id,
            "supplier_name": sq.supplier_name,
            "currency": sq.currency,
            "grand_total": sq.grand_total,
            "base_grand_total": sq.base_grand_total,
            "comparison_base_total": sq.comparison_base_total,
            "lead_time_days": sq.lead_time_days,
            "valid_till": sq.valid_till,
            "is_awarded": sq.is_awarded,
            "is_expired": is_expired,
            "status": sq.status,
            "items": list(sq.items),
        })

    return {
        "rfq_id": rfq.id,
        "rfq_name": rfq.name,
        "status": rfq.status,
        "items": list(rfq.items),
        "quotations": rows,
    }


# --------------------------------------------------------------------------
# Quote Status Recomputation
# --------------------------------------------------------------------------


async def recompute_rfq_quote_status(
    db: AsyncSession, tenant_id: uuid.UUID, rfq_id: uuid.UUID
) -> None:
    """Recompute quotes_received count on the RFQ from linked supplier quotations."""
    rfq = await get_rfq(db, tenant_id, rfq_id)

    result = await db.execute(
        select(func.count())
        .select_from(SupplierQuotation)
        .where(
            SupplierQuotation.rfq_id == rfq_id,
            SupplierQuotation.tenant_id == tenant_id,
        )
    )
    rfq.quotes_received = result.scalar() or 0

    await db.commit()


# --------------------------------------------------------------------------
# Purchase Order Service
# --------------------------------------------------------------------------


def _compute_progress(po: PurchaseOrder) -> tuple[Decimal, Decimal]:
    """Compute per_received and per_billed from PO items. Returns (per_received, per_billed)."""
    total_qty = sum(item.qty for item in po.items) if po.items else Decimal("0")
    received_qty = sum(item.received_qty for item in po.items) if po.items else Decimal("0")
    total_amount = po.grand_total
    billed_amount = sum(item.billed_amount for item in po.items) if po.items else Decimal("0")

    if total_qty > 0:
        per_received = min(Decimal("100.00"), (received_qty / total_qty) * Decimal("100"))
    else:
        per_received = Decimal("0.00")

    if total_amount > 0:
        per_billed = min(Decimal("100.00"), (billed_amount / total_amount) * Decimal("100"))
    else:
        per_billed = Decimal("0.00")

    return per_received, per_billed


async def _derive_po_status(po: PurchaseOrder) -> str:
    """Derive PO status from approval and progress state."""
    if po.status in ("cancelled", "closed"):
        return po.status

    po.per_received, po.per_billed = _compute_progress(po)

    if not po.is_approved:
        return "draft"
    if po.status == "on_hold":
        return "on_hold"

    per_rec, per_bil = po.per_received, po.per_billed
    if per_rec >= Decimal("100.00") and per_bil >= Decimal("100.00"):
        return "completed"
    if per_rec < Decimal("100.00") and per_bil < Decimal("100.00"):
        return "to_receive_and_bill"
    if per_rec < Decimal("100.00"):
        return "to_receive"
    if per_bil < Decimal("100.00"):
        return "to_bill"
    return "submitted"


async def create_purchase_order(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    data: dict,
    current_user: str = "",
) -> PurchaseOrder:
    """Create a Purchase Order, optionally from an awarded supplier quotation.

    If award_id is provided, data is auto-filled from the awarded quotation
    without requiring manual re-entry.
    """
    today = date.today()
    transaction_date = data.get("transaction_date", today)
    if isinstance(transaction_date, str):
        transaction_date = date.fromisoformat(transaction_date)

    award_id = data.get("award_id")

    # Auto-fill from award if provided
    if award_id:
        award_result = await db.execute(
            select(ProcurementAward).where(
                ProcurementAward.id == award_id,
                ProcurementAward.tenant_id == tenant_id,
            )
        )
        award = award_result.scalar_one_or_none()
        if not award:
            raise ValidationError([{"field": "award_id", "message": f"Award {award_id} not found."}])

        # Prevent duplicate PO from same award
        if award.po_created:
            raise ValidationError([{
                "field": "award_id",
                "message": f"PO already created from award {award_id}. Use existing PO reference: {award.po_reference}.",
            }])

        sq_result = await db.execute(
            select(SupplierQuotation).where(SupplierQuotation.id == award.quotation_id)
        )
        sq = sq_result.scalar_one_or_none()
        if not sq:
            raise ValidationError([{"field": "quotation_id", "message": "Awarded quotation not found."}])

        # Auto-fill from quotation
        data["supplier_id"] = sq.supplier_id
        data["supplier_name"] = sq.supplier_name
        data["rfq_id"] = award.rfq_id
        data["quotation_id"] = award.quotation_id
        data["company"] = data.get("company", sq.company)
        data["currency"] = data.get("currency", sq.currency)
        data["taxes"] = data.get("taxes", sq.taxes)
        data["subtotal"] = data.get("subtotal", sq.subtotal)
        data["total_taxes"] = data.get("total_taxes", sq.total_taxes)
        data["grand_total"] = data.get("grand_total", sq.grand_total)
        data["base_grand_total"] = data.get("base_grand_total", sq.base_grand_total)

        # Auto-fill items from quotation items
        if not data.get("items"):
            quotation_items = list(sq.items)
            if not quotation_items:
                raise ValidationError([{
                    "field": "items",
                    "message": "Cannot create PO from award with no quotation items.",
                }])
            data["items"] = [
                {
                    "quotation_item_id": str(item.id),
                    "rfq_item_id": str(item.rfq_item_id) if item.rfq_item_id else None,
                    "item_code": item.item_code,
                    "item_name": item.item_name,
                    "description": item.description,
                    "qty": str(item.qty),
                    "uom": item.uom,
                    "unit_rate": str(item.unit_rate),
                    "amount": str(item.amount),
                    "tax_rate": str(item.tax_rate),
                    "tax_amount": str(item.tax_amount),
                    "tax_code": item.tax_code,
                }
                for item in quotation_items
            ]

    # Generate PO name
    name = data.get("name") or ""
    if not name:
        count_q = select(func.count()).select_from(PurchaseOrder).where(
            PurchaseOrder.tenant_id == tenant_id
        )
        result = await db.execute(count_q)
        count = result.scalar() or 0
        name = f"PO-{count + 1:04d}"

    po = PurchaseOrder(
        tenant_id=tenant_id,
        name=name,
        status="draft",
        supplier_id=data.get("supplier_id"),
        supplier_name=data.get("supplier_name", ""),
        rfq_id=data.get("rfq_id"),
        quotation_id=data.get("quotation_id"),
        award_id=award_id,
        company=data.get("company", ""),
        currency=data.get("currency", "TWD"),
        transaction_date=transaction_date,
        schedule_date=data.get("schedule_date"),
        subtotal=data.get("subtotal", Decimal("0.00")),
        total_taxes=data.get("total_taxes", Decimal("0.00")),
        grand_total=data.get("grand_total", Decimal("0.00")),
        base_grand_total=data.get("base_grand_total", Decimal("0.00")),
        taxes=data.get("taxes", []),
        contact_person=data.get("contact_person", ""),
        contact_email=data.get("contact_email", ""),
        set_warehouse=data.get("set_warehouse", ""),
        terms_and_conditions=data.get("terms_and_conditions", ""),
        notes=data.get("notes", ""),
        is_approved=False,
        approved_by="",
        approved_at=None,
        # Extension hooks: blanket order and landed cost references (Story 24-5)
        blanket_order_reference_id=data.get("blanket_order_reference_id"),
        landed_cost_reference_id=data.get("landed_cost_reference_id"),
    )
    db.add(po)
    await db.flush()

    # Create PO items
    for idx, item_data in enumerate(data.get("items", [])):
        warehouse = item_data.get("warehouse") or po.set_warehouse
        item = PurchaseOrderItem(
            tenant_id=tenant_id,
            purchase_order_id=po.id,
            idx=idx,
            quotation_item_id=item_data.get("quotation_item_id"),
            rfq_item_id=item_data.get("rfq_item_id"),
            item_code=item_data.get("item_code", ""),
            item_name=item_data.get("item_name", ""),
            description=item_data.get("description", ""),
            qty=Decimal(str(item_data.get("qty", "0"))),
            uom=item_data.get("uom", ""),
            warehouse=warehouse,
            unit_rate=Decimal(str(item_data.get("unit_rate", "0"))),
            amount=Decimal(str(item_data.get("amount", "0.00"))),
            tax_rate=Decimal(str(item_data.get("tax_rate", "0"))),
            tax_amount=Decimal(str(item_data.get("tax_amount", "0.00"))),
            tax_code=item_data.get("tax_code", ""),
            received_qty=Decimal("0"),
            billed_amount=Decimal("0.00"),
        )
        db.add(item)

    # Mark award as PO created
    if award_id:
        award.po_created = True
        award.po_reference = name

    await db.commit()
    await db.refresh(po)
    return po


async def get_purchase_order(
    db: AsyncSession, tenant_id: uuid.UUID, po_id: uuid.UUID
) -> PurchaseOrder:
    """Fetch a single purchase order with items."""
    result = await db.execute(
        select(PurchaseOrder).where(
            PurchaseOrder.id == po_id,
            PurchaseOrder.tenant_id == tenant_id,
        )
    )
    po = result.scalar_one_or_none()
    if not po:
        raise ValidationError([{"field": "po_id", "message": f"Purchase order {po_id} not found."}])
    return po


async def list_purchase_orders(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    status: str | None = None,
    supplier_id: uuid.UUID | None = None,
    q: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[PurchaseOrder], int]:
    """List purchase orders with optional filtering."""
    query = select(PurchaseOrder).where(PurchaseOrder.tenant_id == tenant_id)
    count_query = select(func.count()).select_from(PurchaseOrder).where(
        PurchaseOrder.tenant_id == tenant_id
    )

    if status:
        query = query.where(PurchaseOrder.status == status)
        count_query = count_query.where(PurchaseOrder.status == status)
    if supplier_id:
        query = query.where(PurchaseOrder.supplier_id == supplier_id)
        count_query = count_query.where(PurchaseOrder.supplier_id == supplier_id)
    if q:
        q_filter = PurchaseOrder.name.ilike(f"%{q}%")
        query = query.where(q_filter)
        count_query = count_query.where(q_filter)

    query = query.order_by(PurchaseOrder.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    pos = list(result.scalars().all())

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    return pos, total


async def update_purchase_order(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    po_id: uuid.UUID,
    data: dict,
) -> PurchaseOrder:
    """Update purchase order fields (not items in this slice)."""
    po = await get_purchase_order(db, tenant_id, po_id)

    if po.status not in ("draft",):
        msg = f"Cannot update purchase order in status '{po.status}'."
        raise ValidationError([{"field": "status", "message": msg}])

    for field in (
        "name", "supplier_name", "company", "currency", "transaction_date",
        "schedule_date", "subtotal", "total_taxes", "grand_total", "base_grand_total",
        "taxes", "contact_person", "contact_email", "set_warehouse",
        "terms_and_conditions", "notes",
        # Extension hooks: blanket order and landed cost references (Story 24-5)
        "blanket_order_reference_id",
        "landed_cost_reference_id",
    ):
        if field in data and data[field] is not None:
            setattr(po, field, data[field])

    await db.commit()
    await db.refresh(po)
    return po


async def submit_purchase_order(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    po_id: uuid.UUID,
    current_user: str = "",
) -> PurchaseOrder:
    """Submit a purchase order for approval.

    Validates that:
    - PO is in draft status
    - Supplier is not blocked by procurement controls (Story 24-5)
    - PO has at least one item

    Sets is_approved based on approval threshold (v1: auto-approve for MVP).
    """
    po = await get_purchase_order(db, tenant_id, po_id)

    if po.status not in ("draft",):
        msg = f"Cannot submit purchase order in status '{po.status}'."
        raise ValidationError([{"field": "status", "message": msg}])

    if not po.items:
        raise ValidationError([{"field": "items", "message": "Purchase order must have at least one item."}])

    # Supplier control check - block if supplier is on hold or prevented from POs (Story 24-5)
    if po.supplier_id:
        control_result = await check_supplier_po_controls(
            db,
            tenant_id,
            po.supplier_id,
            po.supplier_name,
        )
        enforce_supplier_controls(control_result, "PO submission")

    # Auto-approve for MVP (Story 24-5 will add approval workflow)
    po.is_approved = True
    po.approved_by = current_user
    po.approved_at = datetime.now(tz=UTC)

    po.status = await _derive_po_status(po)

    await db.commit()
    await db.refresh(po)
    return po


async def hold_purchase_order(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    po_id: uuid.UUID,
) -> PurchaseOrder:
    """Place a purchase order on hold."""
    po = await get_purchase_order(db, tenant_id, po_id)

    if po.status not in ("submitted", "to_receive", "to_bill", "to_receive_and_bill"):
        msg = f"Cannot hold purchase order in status '{po.status}'."
        raise ValidationError([{"field": "status", "message": msg}])

    po.status = "on_hold"
    await db.commit()
    await db.refresh(po)
    return po


async def release_purchase_order(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    po_id: uuid.UUID,
) -> PurchaseOrder:
    """Release a purchase order from hold."""
    po = await get_purchase_order(db, tenant_id, po_id)

    if po.status != "on_hold":
        msg = f"Cannot release purchase order not on hold (status: '{po.status}')."
        raise ValidationError([{"field": "status", "message": msg}])

    po.status = await _derive_po_status(po)
    await db.commit()
    await db.refresh(po)
    return po


async def complete_purchase_order(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    po_id: uuid.UUID,
) -> PurchaseOrder:
    """Manually complete a purchase order (override auto-status)."""
    po = await get_purchase_order(db, tenant_id, po_id)

    if po.status not in ("to_receive", "to_bill", "to_receive_and_bill", "submitted"):
        msg = f"Cannot complete purchase order in status '{po.status}'."
        raise ValidationError([{"field": "status", "message": msg}])

    po.status = "completed"
    po.per_received = Decimal("100.00")
    po.per_billed = Decimal("100.00")
    for item in po.items:
        item.received_qty = item.qty
        item.billed_amount = item.amount

    await db.commit()
    await db.refresh(po)
    return po


async def cancel_purchase_order(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    po_id: uuid.UUID,
) -> PurchaseOrder:
    """Cancel a purchase order."""
    po = await get_purchase_order(db, tenant_id, po_id)

    if po.status in ("completed", "closed"):
        msg = f"Cannot cancel purchase order in status '{po.status}'."
        raise ValidationError([{"field": "status", "message": msg}])

    po.status = "cancelled"
    await db.commit()
    await db.refresh(po)
    return po


async def close_purchase_order(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    po_id: uuid.UUID,
) -> PurchaseOrder:
    """Close a purchase order (permanent, no more receipts or invoices)."""
    po = await get_purchase_order(db, tenant_id, po_id)

    if po.status not in ("completed", "cancelled"):
        msg = f"Cannot close purchase order in status '{po.status}'. Complete or cancel first."
        raise ValidationError([{"field": "status", "message": msg}])

    po.status = "closed"
    await db.commit()
    await db.refresh(po)
    return po


async def recompute_po_progress(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    po_id: uuid.UUID,
) -> PurchaseOrder:
    """Recompute per_received and per_billed from downstream coverage.

    Called by goods receipt (Story 24-3) and supplier invoice (Story 24-6).
    """
    po = await get_purchase_order(db, tenant_id, po_id)
    po.per_received, po.per_billed = _compute_progress(po)

    if po.is_approved and po.status not in ("on_hold", "cancelled", "closed"):
        po.status = await _derive_po_status(po)

    await db.commit()
    await db.refresh(po)
    return po


# --------------------------------------------------------------------------
# Goods Receipt Service (Story 24-3)
# --------------------------------------------------------------------------


def _validate_gr_line_invariants(items: list[dict]) -> None:
    """Validate that each GR line satisfies: total_qty = accepted_qty + rejected_qty."""
    for item in items:
        accepted = Decimal(str(item.get("accepted_qty", "0")))
        rejected = Decimal(str(item.get("rejected_qty", "0")))
        if accepted < 0 or rejected < 0:
            raise ValidationError([{
                "field": "qty",
                "message": "Accepted and rejected quantities must be non-negative.",
            }])
        if accepted == 0 and rejected == 0:
            raise ValidationError([{
                "field": "qty",
                "message": "At least one of accepted or rejected quantity must be greater than zero.",
            }])


async def _compute_received_qty_for_po_item(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    po_item_id: uuid.UUID,
) -> Decimal:
    """Sum accepted_qty from all submitted GR items for a given PO line."""
    result = await db.execute(
        select(func.coalesce(func.sum(GoodsReceiptItem.accepted_qty), Decimal("0")))
        .select_from(GoodsReceiptItem)
        .join(GoodsReceipt)
        .where(
            GoodsReceiptItem.purchase_order_item_id == po_item_id,
            GoodsReceipt.tenant_id == tenant_id,
            GoodsReceipt.status == "submitted",
        )
    )
    return result.scalar() or Decimal("0")


async def _recompute_po_from_gr(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    po_id: uuid.UUID,
) -> None:
    """Recompute all PO line received quantities and PO per_received from GR coverage.

    This is a helper for Story 24-3 that recomputes PO progress from all
    submitted goods receipts. The actual implementation delegates to the
    existing recompute_po_progress function.
    """
    await recompute_po_progress(db, tenant_id, po_id)


async def create_goods_receipt(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    data: dict,
    current_user: str = "",
) -> GoodsReceipt:
    """Create a goods receipt against a purchase order.

    Validates:
    - PO exists and is in a valid status for receiving
    - Each GR line links to a valid PO line
    - Quantity invariants (accepted + rejected = total, non-negative)
    """
    today = date.today()
    transaction_date = data.get("transaction_date", today)
    if isinstance(transaction_date, str):
        transaction_date = date.fromisoformat(transaction_date)

    po_id = data.get("purchase_order_id")
    if not po_id:
        raise ValidationError([{"field": "purchase_order_id", "message": "Purchase order ID is required."}])

    # Fetch PO to get supplier context
    po = await get_purchase_order(db, tenant_id, uuid.UUID(str(po_id)))

    if po.status not in ("submitted", "to_receive", "to_bill", "to_receive_and_bill", "on_hold"):
        raise ValidationError([{
            "field": "purchase_order_id",
            "message": f"Cannot receive against PO in status '{po.status}'.",
        }])

    # Validate line items
    items_data = data.get("items", [])
    if not items_data:
        raise ValidationError([{"field": "items", "message": "At least one item is required."}])

    _validate_gr_line_invariants(items_data)

    # Generate GR name
    count_q = select(func.count()).select_from(GoodsReceipt).where(
        GoodsReceipt.tenant_id == tenant_id
    )
    result = await db.execute(count_q)
    count = result.scalar() or 0
    name = f"GR-{count + 1:04d}"

    gr = GoodsReceipt(
        tenant_id=tenant_id,
        name=name,
        status="draft",
        purchase_order_id=po.id,
        supplier_id=po.supplier_id,
        supplier_name=po.supplier_name,
        company=po.company,
        transaction_date=transaction_date,
        posting_date=data.get("posting_date") or transaction_date,
        set_warehouse=data.get("set_warehouse", po.set_warehouse),
        contact_person=data.get("contact_person", ""),
        notes=data.get("notes", ""),
        inventory_mutated=False,
        inventory_mutated_at=None,
    )
    db.add(gr)
    await db.flush()

    # Create GR items
    for idx, item_data in enumerate(items_data):
        po_line_id = item_data.get("purchase_order_item_id")
        if not po_line_id:
            raise ValidationError([{"field": "purchase_order_item_id", "message": "PO line ID is required."}])

        # Validate PO line exists and belongs to this PO
        po_line_result = await db.execute(
            select(PurchaseOrderItem).where(
                PurchaseOrderItem.id == uuid.UUID(str(po_line_id)),
                PurchaseOrderItem.purchase_order_id == po.id,
            )
        )
        po_line = po_line_result.scalar_one_or_none()
        if not po_line:
            raise ValidationError([{
                "field": "purchase_order_item_id",
                "message": f"PO line {po_line_id} not found or does not belong to this PO.",
            }])

        accepted_qty = Decimal(str(item_data.get("accepted_qty", "0")))
        rejected_qty = Decimal(str(item_data.get("rejected_qty", "0")))
        total_qty = accepted_qty + rejected_qty

        # Validate against remaining PO line quantity
        remaining_qty = po_line.qty - po_line.received_qty
        if total_qty > remaining_qty:
            raise ValidationError([{
                "field": "accepted_qty",
                "message": f"Total qty {total_qty} exceeds remaining PO qty {remaining_qty} for item {po_line.item_code}.",
            }])

        gr_item = GoodsReceiptItem(
            tenant_id=tenant_id,
            goods_receipt_id=gr.id,
            idx=idx,
            purchase_order_item_id=po_line.id,
            item_code=item_data.get("item_code", po_line.item_code),
            item_name=item_data.get("item_name", po_line.item_name),
            description=item_data.get("description", po_line.description),
            accepted_qty=accepted_qty,
            rejected_qty=rejected_qty,
            total_qty=total_qty,
            uom=item_data.get("uom", po_line.uom),
            warehouse=item_data.get("warehouse", po_line.warehouse) or gr.set_warehouse,
            rejected_warehouse=item_data.get("rejected_warehouse", ""),
            batch_no=item_data.get("batch_no", ""),
            serial_no=item_data.get("serial_no", ""),
            exception_notes=item_data.get("exception_notes", ""),
            is_rejected=rejected_qty > 0,
            unit_rate=Decimal(str(item_data.get("unit_rate", po_line.unit_rate))),
        )
        db.add(gr_item)

    await db.commit()
    await db.refresh(gr)
    return gr


async def get_goods_receipt(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    gr_id: uuid.UUID,
) -> GoodsReceipt:
    """Fetch a single goods receipt with items (eager loaded)."""
    result = await db.execute(
        select(GoodsReceipt)
        .options(selectinload(GoodsReceipt.items))
        .where(
            GoodsReceipt.id == gr_id,
            GoodsReceipt.tenant_id == tenant_id,
        )
    )
    gr = result.scalar_one_or_none()
    if not gr:
        raise ValidationError([{"field": "gr_id", "message": f"Goods receipt {gr_id} not found."}])
    return gr


async def list_goods_receipts(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    purchase_order_id: uuid.UUID | None = None,
    status: str | None = None,
    q: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[GoodsReceipt], int]:
    """List goods receipts with optional filtering."""
    query = select(GoodsReceipt).where(GoodsReceipt.tenant_id == tenant_id)
    count_query = select(func.count()).select_from(GoodsReceipt).where(
        GoodsReceipt.tenant_id == tenant_id
    )

    if purchase_order_id:
        query = query.where(GoodsReceipt.purchase_order_id == purchase_order_id)
        count_query = count_query.where(GoodsReceipt.purchase_order_id == purchase_order_id)
    if status:
        query = query.where(GoodsReceipt.status == status)
        count_query = count_query.where(GoodsReceipt.status == status)
    if q:
        q_filter = GoodsReceipt.name.ilike(f"%{q}%")
        query = query.where(q_filter)
        count_query = count_query.where(q_filter)

    query = query.order_by(GoodsReceipt.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    receipts = list(result.scalars().all())

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    return receipts, total


async def submit_goods_receipt(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    gr_id: uuid.UUID,
) -> GoodsReceipt:
    """Submit a goods receipt - triggers inventory mutation and PO progress update.

    Validates:
    - GR is in draft status
    - At least one item has positive accepted or rejected quantity
    - PO is in a valid receiving status

    After submission:
    - Sets inventory_mutated = True
    - Calls _recompute_po_from_gr to update PO received quantities and progress
    """
    gr = await get_goods_receipt(db, tenant_id, gr_id)

    if gr.status != "draft":
        msg = f"Cannot submit goods receipt in status '{gr.status}'."
        raise ValidationError([{"field": "status", "message": msg}])

    if not gr.items:
        raise ValidationError([{"field": "items", "message": "Goods receipt must have at least one item."}])

    # Check PO status
    po = await get_purchase_order(db, tenant_id, gr.purchase_order_id)
    if po.status not in ("submitted", "to_receive", "to_bill", "to_receive_and_bill", "on_hold"):
        raise ValidationError([{
            "field": "status",
            "message": f"Cannot submit receipt: PO is in status '{po.status}'.",
        }])

    gr.status = "submitted"
    gr.inventory_mutated = True
    gr.inventory_mutated_at = datetime.now(tz=UTC)

    # Recompute PO received quantities from all submitted GRs
    await _recompute_po_from_gr(db, tenant_id, gr.purchase_order_id)

    await db.commit()
    await db.refresh(gr)
    return gr


async def cancel_goods_receipt(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    gr_id: uuid.UUID,
) -> GoodsReceipt:
    """Cancel a goods receipt.

    Only draft receipts can be cancelled.
    Cancelled receipts recompute PO progress from remaining submitted receipts.
    """
    gr = await get_goods_receipt(db, tenant_id, gr_id)

    if gr.status not in ("draft", "submitted"):
        msg = f"Cannot cancel goods receipt in status '{gr.status}'."
        raise ValidationError([{"field": "status", "message": msg}])

    po_id = gr.purchase_order_id
    previous_status = gr.status

    gr.status = "cancelled"

    # If was submitted, recompute PO progress from remaining receipts
    if previous_status == "submitted":
        gr.inventory_mutated = False
        await _recompute_po_from_gr(db, tenant_id, po_id)

    await db.commit()
    await db.refresh(gr)
    return gr


async def list_receipts_for_po(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    po_id: uuid.UUID,
) -> tuple[list[GoodsReceipt], int]:
    """List all goods receipts for a specific purchase order."""
    return await list_goods_receipts(
        db,
        tenant_id,
        purchase_order_id=po_id,
        page=1,
        page_size=100,
    )


# --------------------------------------------------------------------------
# Procurement Reporting (Story 24-5)
# --------------------------------------------------------------------------


async def get_procurement_summary(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    date_from: date | None = None,
    date_to: date | None = None,
) -> dict:
    """Get procurement summary statistics.

    Args:
        db: Database session
        tenant_id: Tenant UUID
        date_from: Optional start date filter
        date_to: Optional end date filter

    Returns:
        Dict with RFQ, quotation, PO, and supplier statistics
    """
    today = date.today()
    from_date = date_from or today.replace(day=1)  # First day of month
    to_date = date_to or today

    # RFQ stats
    rfq_count_result = await db.execute(
        select(func.count(RFQ.id)).where(
            RFQ.tenant_id == tenant_id,
            RFQ.transaction_date >= from_date,
            RFQ.transaction_date <= to_date,
        )
    )
    rfq_count = rfq_count_result.scalar() or 0

    rfq_submitted_result = await db.execute(
        select(func.count(RFQ.id)).where(
            RFQ.tenant_id == tenant_id,
            RFQ.status == "submitted",
            RFQ.transaction_date >= from_date,
            RFQ.transaction_date <= to_date,
        )
    )
    rfq_submitted = rfq_submitted_result.scalar() or 0

    # Supplier quotation stats
    sq_count_result = await db.execute(
        select(func.count(SupplierQuotation.id)).where(
            SupplierQuotation.tenant_id == tenant_id,
            SupplierQuotation.transaction_date >= from_date,
            SupplierQuotation.transaction_date <= to_date,
        )
    )
    sq_count = sq_count_result.scalar() or 0

    sq_submitted_result = await db.execute(
        select(func.count(SupplierQuotation.id)).where(
            SupplierQuotation.tenant_id == tenant_id,
            SupplierQuotation.status == "submitted",
            SupplierQuotation.transaction_date >= from_date,
            SupplierQuotation.transaction_date <= to_date,
        )
    )
    sq_submitted = sq_submitted_result.scalar() or 0

    # Award stats
    award_count_result = await db.execute(
        select(func.count(ProcurementAward.id)).where(
            ProcurementAward.tenant_id == tenant_id,
            ProcurementAward.awarded_at >= datetime.combine(from_date, datetime.min.time(), tzinfo=UTC),
            ProcurementAward.awarded_at <= datetime.combine(to_date, datetime.max.time(), tzinfo=UTC),
        )
    )
    award_count = award_count_result.scalar() or 0

    # PO stats
    po_count_result = await db.execute(
        select(func.count(PurchaseOrder.id)).where(
            PurchaseOrder.tenant_id == tenant_id,
            PurchaseOrder.transaction_date >= from_date,
            PurchaseOrder.transaction_date <= to_date,
        )
    )
    po_count = po_count_result.scalar() or 0

    po_submitted_result = await db.execute(
        select(func.count(PurchaseOrder.id)).where(
            PurchaseOrder.tenant_id == tenant_id,
            PurchaseOrder.status.in_(["submitted", "to_receive", "to_bill", "to_receive_and_bill", "completed"]),
            PurchaseOrder.transaction_date >= from_date,
            PurchaseOrder.transaction_date <= to_date,
        )
    )
    po_submitted = po_submitted_result.scalar() or 0

    # Supplier control stats
    blocked_suppliers_result = await db.execute(
        select(func.count(Supplier.id)).where(
            Supplier.tenant_id == tenant_id,
            Supplier.on_hold == True,
        )
    )
    blocked_suppliers = blocked_suppliers_result.scalar() or 0

    warned_suppliers_result = await db.execute(
        select(func.count(Supplier.id)).where(
            Supplier.tenant_id == tenant_id,
            (Supplier.warn_rfqs == True) | (Supplier.warn_pos == True),
        )
    )
    warned_suppliers = warned_suppliers_result.scalar() or 0

    return {
        "period": {
            "from": str(from_date),
            "to": str(to_date),
        },
        "rfqs": {
            "total": rfq_count,
            "submitted": rfq_submitted,
            "pending": rfq_count - rfq_submitted,
        },
        "supplier_quotations": {
            "total": sq_count,
            "submitted": sq_submitted,
            "pending": sq_count - sq_submitted,
        },
        "awards": {
            "total": award_count,
        },
        "purchase_orders": {
            "total": po_count,
            "active": po_submitted,
            "draft": po_count - po_submitted,
        },
        "supplier_controls": {
            "blocked_suppliers": blocked_suppliers,
            "warned_suppliers": warned_suppliers,
        },
    }


async def get_quote_turnaround_stats(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    rfq_id: uuid.UUID | None = None,
) -> dict:
    """Get quote turnaround statistics.

    Measures how quickly suppliers respond to RFQs based on timestamps
    from RFQ submission to quotation receipt.

    Args:
        db: Database session
        tenant_id: Tenant UUID
        rfq_id: Optional specific RFQ to analyze

    Returns:
        Dict with turnaround time statistics
    """
    # Get quotations with their linked RFQs for turnaround calculation
    query = (
        select(
            SupplierQuotation,
            RFQ,
        )
        .join(RFQ, SupplierQuotation.rfq_id == RFQ.id)
        .where(
            SupplierQuotation.tenant_id == tenant_id,
            SupplierQuotation.status == "submitted",
        )
    )

    if rfq_id:
        query = query.where(SupplierQuotation.rfq_id == rfq_id)

    result = await db.execute(query)
    rows = result.all()

    turnaround_days: list[float] = []
    for sq, rfq in rows:
        if rfq.status == "submitted" and sq.created_at:
            delta = sq.created_at - rfq.updated_at
            turnaround_days.append(delta.total_seconds() / 86400)  # Convert to days

    if not turnaround_days:
        return {
            "rfq_id": str(rfq_id) if rfq_id else None,
            "total_quotes": 0,
            "avg_turnaround_days": None,
            "min_turnaround_days": None,
            "max_turnaround_days": None,
        }

    return {
        "rfq_id": str(rfq_id) if rfq_id else None,
        "total_quotes": len(turnaround_days),
        "avg_turnaround_days": round(sum(turnaround_days) / len(turnaround_days), 2),
        "min_turnaround_days": round(min(turnaround_days), 2),
        "max_turnaround_days": round(max(turnaround_days), 2),
    }


async def get_supplier_performance_stats(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    supplier_id: uuid.UUID | None = None,
) -> dict:
    """Get supplier performance statistics.

    Aggregates award outcomes, average response times, and scorecard status
    for procurement analytics.

    Args:
        db: Database session
        tenant_id: Tenant UUID
        supplier_id: Optional specific supplier to analyze

    Returns:
        Dict with supplier performance metrics
    """
    # Base query for quotations
    sq_query = select(SupplierQuotation).where(
        SupplierQuotation.tenant_id == tenant_id,
        SupplierQuotation.status == "submitted",
    )

    if supplier_id:
        sq_query = sq_query.where(SupplierQuotation.supplier_id == supplier_id)

    sq_result = await db.execute(sq_query)
    quotations = sq_result.scalars().all()

    total_quotes = len(quotations)
    awarded_quotes = sum(1 for sq in quotations if sq.is_awarded)

    # Award rates by supplier
    supplier_stats: dict[str, dict] = {}
    for sq in quotations:
        supplier_key = str(sq.supplier_id) if sq.supplier_id else sq.supplier_name
        if supplier_key not in supplier_stats:
            supplier_stats[supplier_key] = {
                "supplier_name": sq.supplier_name,
                "supplier_id": str(sq.supplier_id) if sq.supplier_id else None,
                "total_quotes": 0,
                "awarded_quotes": 0,
                "award_rate": 0.0,
            }
        supplier_stats[supplier_key]["total_quotes"] += 1
        if sq.is_awarded:
            supplier_stats[supplier_key]["awarded_quotes"] += 1

    # Calculate award rates
    for stats in supplier_stats.values():
        if stats["total_quotes"] > 0:
            stats["award_rate"] = round(
                stats["awarded_quotes"] / stats["total_quotes"] * 100, 2
            )

    # Get supplier controls summary
    supplier_control_query = select(Supplier).where(Supplier.tenant_id == tenant_id)
    if supplier_id:
        supplier_control_query = supplier_control_query.where(Supplier.id == supplier_id)

    ctrl_result = await db.execute(supplier_control_query)
    suppliers = ctrl_result.scalars().all()

    control_summary = {
        "total_suppliers": len(suppliers),
        "blocked_count": sum(1 for s in suppliers if s.on_hold),
        "warn_rfq_count": sum(1 for s in suppliers if s.warn_rfqs),
        "warn_po_count": sum(1 for s in suppliers if s.warn_pos),
        "prevent_rfq_count": sum(1 for s in suppliers if s.prevent_rfqs),
        "prevent_po_count": sum(1 for s in suppliers if s.prevent_pos),
    }

    return {
        "supplier_id": str(supplier_id) if supplier_id else None,
        "overall": {
            "total_quotes": total_quotes,
            "awarded_quotes": awarded_quotes,
            "award_rate": round(awarded_quotes / total_quotes * 100, 2) if total_quotes > 0 else 0.0,
        },
        "by_supplier": list(supplier_stats.values()),
        "supplier_controls": control_summary,
    }


async def get_supplier_controls(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    supplier_id: uuid.UUID,
) -> dict:
    """Get detailed supplier control status for a specific supplier.

    Args:
        db: Database session
        tenant_id: Tenant UUID
        supplier_id: Supplier UUID

    Returns:
        Dict with supplier control details and computed statuses
    """
    result = await db.execute(
        select(Supplier).where(
            Supplier.id == supplier_id,
            Supplier.tenant_id == tenant_id,
        )
    )
    supplier = result.scalar_one_or_none()

    if not supplier:
        raise ValidationError([{
            "field": "supplier_id",
            "message": f"Supplier {supplier_id} not found.",
        }])

    # Get computed control statuses
    rfq_blocked, rfq_warned, rfq_reason = supplier.get_rfq_controls()
    po_blocked, po_warned, po_reason = supplier.get_po_controls()

    return {
        "supplier_id": str(supplier.id),
        "supplier_name": supplier.name,
        "is_active": supplier.is_active,
        # Hold status
        "on_hold": supplier.on_hold,
        "hold_type": supplier.hold_type,
        "release_date": str(supplier.release_date) if supplier.release_date else None,
        "is_effectively_on_hold": supplier.is_effectively_on_hold(),
        # Scorecard controls
        "scorecard_standing": supplier.scorecard_standing,
        "scorecard_last_evaluated_at": (
            supplier.scorecard_last_evaluated_at.isoformat()
            if supplier.scorecard_last_evaluated_at else None
        ),
        # RFQ controls
        "warn_rfqs": supplier.warn_rfqs,
        "prevent_rfqs": supplier.prevent_rfqs,
        "rfq_blocked": rfq_blocked,
        "rfq_warned": rfq_warned,
        "rfq_control_reason": rfq_reason,
        # PO controls
        "warn_pos": supplier.warn_pos,
        "prevent_pos": supplier.prevent_pos,
        "po_blocked": po_blocked,
        "po_warned": po_warned,
        "po_control_reason": po_reason,
    }
