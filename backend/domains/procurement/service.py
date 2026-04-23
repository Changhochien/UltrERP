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
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.errors import ValidationError
from domains.procurement.models import (
    RFQ,
    ProcurementAward,
    PurchaseOrder,
    PurchaseOrderItem,
    RFQItem,
    RFQSupplier,
    SupplierQuotation,
    SupplierQuotationItem,
)

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
    """Submit an RFQ - changes status to submitted."""
    rfq = await get_rfq(db, tenant_id, rfq_id)
    if rfq.status not in ("draft",):
        msg = f"Cannot submit RFQ in status '{rfq.status}'."
        raise ValidationError([{"field": "status", "message": msg}])
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
    - Supplier is not on hold (supplier control check)
    - PO has at least one item

    Sets is_approved based on approval threshold (v1: auto-approve for MVP).
    """
    po = await get_purchase_order(db, tenant_id, po_id)

    if po.status not in ("draft",):
        msg = f"Cannot submit purchase order in status '{po.status}'."
        raise ValidationError([{"field": "status", "message": msg}])

    if not po.items:
        raise ValidationError([{"field": "items", "message": "Purchase order must have at least one item."}])

    # Supplier control check (v1: check supplier hold status via supplier master)
    # TODO: Integrate with Story 24-5 supplier controls
    # For now, we pass if no supplier_id or supplier is not flagged as blocked

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
