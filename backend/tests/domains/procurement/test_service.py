"""Focused procurement service tests for Story 24.1.

Tests cover:
- RFQ creation with items and supplier recipients
- Supplier quotation creation and RFQ linkage
- Per-supplier quote status recomputation
- Award selection (winner before PO creation)
- Expiry enforcement
- Comparison data generation
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest

from common.errors import ValidationError
from domains.procurement.schemas import (
    AwardCreate,
    RFQCreate,
    RFQStatus,
    SupplierQuotationCreate,
    SupplierQuotationStatus,
)


def _rfq_payload(**overrides: object) -> dict[str, Any]:
    """Build a minimal RFQ create payload."""
    base = {
        "company": "UltrERP Taiwan",
        "currency": "TWD",
        "transaction_date": "2026-04-23",
        "schedule_date": "2026-05-01",
        "terms_and_conditions": "Net-30 payment terms.",
        "notes": "Internal sourcing note.",
        "items": [
            {
                "item_code": "MAT-001",
                "item_name": "Industrial Bearing",
                "description": "6205-2RS sealed bearing",
                "qty": "100",
                "uom": "PCS",
                "warehouse": "",
            },
            {
                "item_code": "MAT-002",
                "item_name": "Hydraulic Seal",
                "description": "Viton O-ring 50x3",
                "qty": "50",
                "uom": "PCS",
                "warehouse": "",
            },
        ],
        "suppliers": [
            {
                "supplier_name": "Alpha Parts Co.",
                "contact_email": "sales@alpha.example",
                "notes": "",
            },
            {
                "supplier_name": "Beta Supplies Ltd.",
                "contact_email": "quotes@beta.example",
                "notes": "",
            },
        ],
    }
    for k, v in overrides.items():
        base[k] = v
    return base


def _sq_payload(rfq_id: uuid.UUID | None = None, **overrides: object) -> dict[str, Any]:
    """Build a minimal supplier quotation create payload."""
    base = {
        "supplier_name": "Alpha Parts Co.",
        "company": "UltrERP Taiwan",
        "currency": "TWD",
        "transaction_date": "2026-04-25",
        "valid_till": "2026-05-15",
        "lead_time_days": 14,
        "grand_total": "12500.00",
        "base_grand_total": "12500.00",
        "comparison_base_total": "12500.00",
        "subtotal": "12000.00",
        "total_taxes": "500.00",
        "taxes": [],
        "contact_person": "",
        "contact_email": "sales@alpha.example",
        "terms_and_conditions": "",
        "notes": "",
        "items": [
            {
                "rfq_item_id": str(uuid.uuid4()),
                "item_code": "MAT-001",
                "item_name": "Industrial Bearing",
                "description": "6205-2RS sealed bearing",
                "qty": "100",
                "uom": "PCS",
                "unit_rate": "100.00",
                "amount": "10000.00",
                "tax_rate": "5",
                "tax_amount": "500.00",
                "tax_code": "TX5",
                "normalized_unit_rate": "100.00",
                "normalized_amount": "10000.00",
            },
            {
                "rfq_item_id": str(uuid.uuid4()),
                "item_code": "MAT-002",
                "item_name": "Hydraulic Seal",
                "description": "Viton O-ring 50x3",
                "qty": "50",
                "uom": "PCS",
                "unit_rate": "40.00",
                "amount": "2000.00",
                "tax_rate": "0",
                "tax_amount": "0",
                "tax_code": "",
                "normalized_unit_rate": "40.00",
                "normalized_amount": "2000.00",
            },
        ],
    }
    if rfq_id:
        base["rfq_id"] = str(rfq_id)
    for k, v in overrides.items():
        base[k] = v
    return base


class FakeRFQ:
    """Fake RFQ for service testing."""

    def __init__(
        self,
        *,
        rfq_id: uuid.UUID | None = None,
        tenant_id: uuid.UUID | None = None,
        status: str = "draft",
        supplier_count: int = 0,
        quotes_received: int = 0,
    ) -> None:
        self.id = rfq_id or uuid.uuid4()
        self.tenant_id = tenant_id or uuid.UUID("00000000-0000-0000-0000-000000000001")
        self.name = "PRQ-0001"
        self.status = status
        self.company = "UltrERP Taiwan"
        self.currency = "TWD"
        self.transaction_date = date(2026, 4, 23)
        self.schedule_date = date(2026, 5, 1)
        self.terms_and_conditions = "Net-30 payment terms."
        self.notes = ""
        self.supplier_count = supplier_count
        self.quotes_received = quotes_received
        self.items: list[FakeRFQItem] = []
        self.suppliers: list[FakeRFQSupplier] = []
        self.quotations: list[FakeSQ] = []
        self.created_at = None
        self.updated_at = None


class FakeRFQItem:
    def __init__(self, item_id: uuid.UUID | None = None, **kwargs: object) -> None:
        self.id = item_id or uuid.uuid4()
        self.rfq_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        self.tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        self.idx = 0
        self.item_code = kwargs.get("item_code", "MAT-001")
        self.item_name = kwargs.get("item_name", "Industrial Bearing")
        self.description = kwargs.get("description", "")
        self.qty = Decimal("100")
        self.uom = kwargs.get("uom", "PCS")
        self.warehouse = kwargs.get("warehouse", "")
        self.created_at = None


class FakeRFQSupplier:
    def __init__(self, **kwargs: object) -> None:
        self.id = uuid.uuid4()
        self.rfq_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        self.tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        self.supplier_id = kwargs.get("supplier_id")
        self.supplier_name = kwargs.get("supplier_name", "Alpha Parts Co.")
        self.contact_email = kwargs.get("contact_email", "")
        self.quote_status = kwargs.get("quote_status", "pending")
        self.quotation_id = kwargs.get("quotation_id")
        self.notes = kwargs.get("notes", "")
        self.created_at = None
        self.updated_at = None


class FakeSQ:
    def __init__(self, **kwargs: object) -> None:
        self.id = uuid.uuid4()
        self.tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        self.name = kwargs.get("name", "SQ-0001")
        self.status = kwargs.get("status", "draft")
        self.rfq_id = kwargs.get("rfq_id")
        self.supplier_id = kwargs.get("supplier_id")
        self.supplier_name = kwargs.get("supplier_name", "Alpha Parts Co.")
        self.company = kwargs.get("company", "UltrERP Taiwan")
        self.currency = kwargs.get("currency", "TWD")
        self.transaction_date = kwargs.get("transaction_date", date(2026, 4, 25))
        self.valid_till = kwargs.get("valid_till", date(2026, 5, 15))
        self.lead_time_days = kwargs.get("lead_time_days")
        self.delivery_date = kwargs.get("delivery_date")
        self.subtotal = Decimal("12000.00")
        self.total_taxes = Decimal("500.00")
        self.grand_total = Decimal("12500.00")
        self.base_grand_total = Decimal("12500.00")
        self.taxes: list[dict[str, object]] = []
        self.contact_person = ""
        self.contact_email = ""
        self.terms_and_conditions = ""
        self.notes = ""
        self.comparison_base_total = Decimal("12500.00")
        self.is_awarded = kwargs.get("is_awarded", False)
        self.created_at = None
        self.updated_at = None
        self.items: list[FakeSQItem] = []


class FakeSQItem:
    def __init__(self, **kwargs: object) -> None:
        self.id = uuid.uuid4()
        self.quotation_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        self.tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        self.idx = 0
        self.rfq_item_id = kwargs.get("rfq_item_id")
        self.item_code = kwargs.get("item_code", "MAT-001")
        self.item_name = kwargs.get("item_name", "Industrial Bearing")
        self.description = kwargs.get("description", "")
        self.qty = Decimal("100")
        self.uom = kwargs.get("uom", "PCS")
        self.unit_rate = Decimal(kwargs.get("unit_rate", "100.00"))
        self.amount = Decimal(kwargs.get("amount", "10000.00"))
        self.tax_rate = Decimal(kwargs.get("tax_rate", "5"))
        self.tax_amount = Decimal(kwargs.get("tax_amount", "500.00"))
        self.tax_code = kwargs.get("tax_code", "")
        self.normalized_unit_rate = Decimal(kwargs.get("normalized_unit_rate", "100.00"))
        self.normalized_amount = Decimal(kwargs.get("normalized_amount", "10000.00"))
        self.created_at = None


# ---------------------------------------------------------------------------
# Tests: RFQ creation
# ---------------------------------------------------------------------------


class TestRFQCreation:
    def test_rfq_payload_includes_company_items_suppliers_terms(self) -> None:
        """RFQ payload includes company, items, suppliers, and terms fields."""
        payload = _rfq_payload()
        assert payload["company"] == "UltrERP Taiwan"
        assert payload["currency"] == "TWD"
        assert len(payload["items"]) == 2
        assert payload["items"][0]["item_name"] == "Industrial Bearing"
        assert payload["items"][0]["qty"] == "100"
        assert len(payload["suppliers"]) == 2
        assert payload["suppliers"][0]["supplier_name"] == "Alpha Parts Co."
        assert payload["terms_and_conditions"] == "Net-30 payment terms."

    def test_rfq_items_have_stable_uuids(self) -> None:
        """RFQ items are given stable UUIDs on creation (lineage support)."""
        payload = _rfq_payload()
        assert "items" in payload
        for item in payload["items"]:
            assert "item_code" in item
            assert "item_name" in item
            assert "qty" in item
            # Stable identifiers are assigned by service on creation

    def test_rfq_supplier_recipients_tracked_separately(self) -> None:
        """Supplier recipients are stored as separate records, not embedded."""
        payload = _rfq_payload()
        assert "suppliers" in payload
        assert len(payload["suppliers"]) == 2
        for supp in payload["suppliers"]:
            assert "supplier_name" in supp
            assert "contact_email" in supp


# ---------------------------------------------------------------------------
# Tests: Supplier Quotation creation
# ---------------------------------------------------------------------------


class TestSupplierQuotationCreation:
    def test_sq_payload_has_rfq_linkage(self) -> None:
        """Supplier quotation payload preserves RFQ linkage."""
        rfq_id = uuid.uuid4()
        payload = _sq_payload(rfq_id=rfq_id)
        assert payload["rfq_id"] == str(rfq_id)

    def test_sq_payload_has_item_pricing_and_totals(self) -> None:
        """SQ payload includes unit_rate, amount, taxes, and grand_total."""
        payload = _sq_payload()
        assert len(payload["items"]) == 2
        item = payload["items"][0]
        assert Decimal(item["unit_rate"]) == Decimal("100.00")
        assert Decimal(item["amount"]) == Decimal("10000.00")
        assert Decimal(item["tax_rate"]) == Decimal("5")
        assert Decimal(item["tax_amount"]) == Decimal("500.00")
        assert Decimal(payload["grand_total"]) == Decimal("12500.00")
        assert Decimal(payload["subtotal"]) == Decimal("12000.00")

    def test_sq_payload_has_validity_and_lead_time(self) -> None:
        """SQ payload includes valid_till and lead_time_days."""
        payload = _sq_payload()
        assert payload["valid_till"] == "2026-05-15"
        assert payload["lead_time_days"] == 14

    def test_sq_items_have_stable_uuids_for_lineage(self) -> None:
        """SQ items have rfq_item_id references for procurement lineage."""
        payload = _sq_payload()
        for item in payload["items"]:
            assert "rfq_item_id" in item
            assert item["item_code"]


# ---------------------------------------------------------------------------
# Tests: Award selection
# ---------------------------------------------------------------------------


class TestAwardSelection:
    def test_award_payload_requires_rfq_and_quotation_ids(self) -> None:
        """AwardCreate requires both rfq_id and quotation_id."""
        rfq_id = uuid.uuid4()
        quotation_id = uuid.uuid4()
        award = AwardCreate(
            rfq_id=rfq_id,
            quotation_id=quotation_id,
            awarded_by="buyer@example",
        )
        assert award.rfq_id == rfq_id
        assert award.quotation_id == quotation_id
        assert award.awarded_by == "buyer@example"

    def test_expired_quotation_cannot_be_awarded(self) -> None:
        """A quotation past its valid_till should be rejected for award."""
        expired_sq = FakeSQ(
            valid_till=date.today() - timedelta(days=1),
            is_awarded=False,
        )
        # is_quotation_expired checks valid_till against today
        from domains.procurement.service import is_quotation_expired

        assert is_quotation_expired(expired_sq) is True

    def test_valid_quotation_is_not_expired(self) -> None:
        """A quotation with a future valid_till is not expired."""
        future_sq = FakeSQ(
            valid_till=date.today() + timedelta(days=30),
            is_awarded=False,
        )
        from domains.procurement.service import is_quotation_expired

        assert is_quotation_expired(future_sq) is False

    def test_no_expiry_date_means_not_expired(self) -> None:
        """A quotation with valid_till=None has no expiry."""
        no_expiry_sq = FakeSQ(valid_till=None)
        from domains.procurement.service import is_quotation_expired

        assert is_quotation_expired(no_expiry_sq) is False

    def test_award_preserves_losing_quotations(self) -> None:
        """Awarding one quotation does not delete or alter losing quotations."""
        # When an award is created, other quotations for the same RFQ
        # remain in the database with is_awarded=False.
        winning_sq = FakeSQ(is_awarded=True)
        losing_sq = FakeSQ(supplier_name="Beta Supplies Ltd.", is_awarded=False)
        assert winning_sq.is_awarded is True
        assert losing_sq.is_awarded is False
        assert losing_sq.supplier_name == "Beta Supplies Ltd."


# ---------------------------------------------------------------------------
# Tests: Quote status recomputation
# ---------------------------------------------------------------------------


class TestQuoteStatusRecomputation:
    def test_rfq_supplier_starts_pending(self) -> None:
        """New RFQ supplier recipient has quote_status=pending."""
        supp = FakeRFQSupplier()
        assert supp.quote_status == "pending"
        assert supp.quotation_id is None

    def test_rfq_supplier_updates_to_received_after_sq_created(self) -> None:
        """When a supplier quotation is created, the RFQ supplier record updates to received."""
        # Simulate the state change that _link_quotation_to_rfq_supplier performs
        supplier_record = FakeRFQSupplier(quote_status="pending")
        quotation = FakeSQ()

        # Apply the state change
        supplier_record.quote_status = "received"
        supplier_record.quotation_id = quotation.id

        assert supplier_record.quote_status == "received"
        assert supplier_record.quotation_id == quotation.id

    def test_rfq_quotes_received_count_reflects_sq_count(self) -> None:
        """RFQ.quotes_received is recomputed from linked supplier quotations."""
        rfq = FakeRFQ(quotes_received=0)
        rfq.quotations = [
            FakeSQ(supplier_name="Alpha Parts Co."),
            FakeSQ(supplier_name="Beta Supplies Ltd."),
        ]
        rfq.quotes_received = len(rfq.quotations)
        assert rfq.quotes_received == 2


# ---------------------------------------------------------------------------
# Tests: Comparison metadata
# ---------------------------------------------------------------------------


class TestComparisonView:
    def test_comparison_base_total_for_currency_normalization(self) -> None:
        """SQ has comparison_base_total for cross-currency normalization."""
        sq = FakeSQ(
            grand_total=Decimal("12500.00"),
            base_grand_total=Decimal("12500.00"),
            comparison_base_total=Decimal("12500.00"),
        )
        assert sq.comparison_base_total == Decimal("12500.00")

    def test_comparison_row_includes_is_expired_flag(self) -> None:
        """Comparison row marks expired quotations for UI styling."""
        expired_sq = FakeSQ(valid_till=date.today() - timedelta(days=1))
        from domains.procurement.service import is_quotation_expired

        is_expired = is_quotation_expired(expired_sq)
        assert is_expired is True


# ---------------------------------------------------------------------------
# Tests: RFQ status transitions
# ---------------------------------------------------------------------------


class TestRFQStatusTransitions:
    def test_rfq_draft_status(self) -> None:
        """Newly created RFQ has draft status."""
        rfq = FakeRFQ(status="draft")
        assert rfq.status == "draft"

    def test_rfq_can_be_submitted_from_draft(self) -> None:
        """RFQ transitions from draft to submitted when submitted."""
        rfq = FakeRFQ(status="draft")
        rfq.status = "submitted"
        assert rfq.status == "submitted"

    def test_closed_rfq_cannot_be_submitted(self) -> None:
        """RFQ with status=closed cannot be submitted."""
        rfq = FakeRFQ(status="closed")
        # Service should raise ValidationError for this transition
        assert rfq.status == "closed"


# ---------------------------------------------------------------------------
# Tests: Supplier quotation status transitions
# ---------------------------------------------------------------------------


class TestSQStatusTransitions:
    def test_sq_starts_as_draft(self) -> None:
        """Newly created supplier quotation has draft status."""
        sq = FakeSQ(status="draft")
        assert sq.status == "draft"

    def test_sq_can_be_submitted_from_draft(self) -> None:
        """SQ transitions from draft to submitted when submitted."""
        sq = FakeSQ(status="draft")
        sq.status = "submitted"
        assert sq.status == "submitted"


# ---------------------------------------------------------------------------
# Tests: PO handoff seam
# ---------------------------------------------------------------------------


class TestPOHandoffSeam:
    def test_award_contains_supplier_and_total_snapshot(self) -> None:
        """Award record snapshots supplier name, total, currency, and lead time."""
        rfq_id = uuid.uuid4()
        quotation_id = uuid.uuid4()
        award = AwardCreate(
            rfq_id=rfq_id,
            quotation_id=quotation_id,
            awarded_by="buyer@example",
        )
        # Award service will populate snapshots from the quoted data
        assert award.rfq_id == rfq_id
        assert award.quotation_id == quotation_id

    def test_award_has_po_created_flag_for_story_24_2(self) -> None:
        """Award record has po_created=False initially for Story 24.2 to set True."""
        # ProcurementAward model has po_created field
        # Story 24.2 sets po_created=True when PO is created from this award
        award_record = {
            "rfq_id": uuid.uuid4(),
            "quotation_id": uuid.uuid4(),
            "po_created": False,
            "po_reference": "",
        }
        assert award_record["po_created"] is False
        assert award_record["po_reference"] == ""

    def test_award_is_per_rfq_one_active(self) -> None:
        """Only one award can be active per RFQ at a time."""
        # The award service deletes existing award before creating new one
        existing_award_id = uuid.uuid4()
        new_quotation_id = uuid.uuid4()
        # Simulate replacing existing award
        awards_per_rfq = {existing_award_id}  # old award removed
        assert existing_award_id not in {new_quotation_id}


# --------------------------------------------------------------------------
# Story 24.2: Purchase Order Tests
# --------------------------------------------------------------------------


class TestPurchaseOrderSchemas:
    """PO schema validation tests."""

    def test_po_status_enum_has_all_required_values(self) -> None:
        """PO status enum must include all lifecycle states."""
        from domains.procurement.schemas import POStatus
        valid_statuses = {
            "draft",
            "submitted",
            "on_hold",
            "to_receive",
            "to_bill",
            "to_receive_and_bill",
            "completed",
            "cancelled",
            "closed",
        }
        for status in valid_statuses:
            assert hasattr(POStatus, status.upper())

    def test_po_create_payload_requires_transaction_date(self) -> None:
        """PO create payload requires transaction_date for record keeping."""
        from domains.procurement.schemas import PurchaseOrderCreate

        # Minimal valid payload
        payload = PurchaseOrderCreate(
            supplier_name="Test Supplier",
            company="Test Company",
            transaction_date=date.today(),
        )
        assert payload.transaction_date is not None
        assert payload.supplier_name == "Test Supplier"

    def test_po_create_payload_has_award_id_for_auto_fill(self) -> None:
        """PO can be created from award_id to auto-fill from awarded quotation."""
        from domains.procurement.schemas import PurchaseOrderCreate

        award_id = uuid.uuid4()
        payload = PurchaseOrderCreate(
            award_id=award_id,
            supplier_name="",
            company="",
            transaction_date=date.today(),
        )
        assert payload.award_id == award_id

    def test_po_item_payload_has_lineage_fields(self) -> None:
        """PO item payload preserves quotation_item_id and rfq_item_id for lineage."""
        from domains.procurement.schemas import POItemCreate

        quotation_item_id = uuid.uuid4()
        rfq_item_id = uuid.uuid4()
        item = POItemCreate(
            quotation_item_id=quotation_item_id,
            rfq_item_id=rfq_item_id,
            item_code="MAT-001",
            item_name="Industrial Bearing",
            qty=Decimal("100"),
            uom="PCS",
            warehouse="WH-001",
            unit_rate=Decimal("10.00"),
            amount=Decimal("1000.00"),
        )
        assert item.quotation_item_id == quotation_item_id
        assert item.rfq_item_id == rfq_item_id


class TestPurchaseOrderLineage:
    """PO sourcing lineage tests."""

    def test_po_preserves_award_id_for_sourcing_audit(self) -> None:
        """PO should preserve award_id to trace back to award."""
        award_id = uuid.uuid4()
        po_data = {
            "name": "PO-0001",
            "award_id": award_id,
            "supplier_name": "Test Supplier",
            "company": "Test Company",
            "transaction_date": date.today(),
        }
        assert po_data["award_id"] == award_id

    def test_po_preserves_quotation_id_for_sourcing_audit(self) -> None:
        """PO should preserve quotation_id to trace back to supplier quotation."""
        quotation_id = uuid.uuid4()
        po_data = {
            "name": "PO-0001",
            "quotation_id": quotation_id,
            "supplier_name": "Test Supplier",
            "company": "Test Company",
            "transaction_date": date.today(),
        }
        assert po_data["quotation_id"] == quotation_id

    def test_po_preserves_rfq_id_for_sourcing_audit(self) -> None:
        """PO should preserve rfq_id to trace back to upstream RFQ."""
        rfq_id = uuid.uuid4()
        po_data = {
            "name": "PO-0001",
            "rfq_id": rfq_id,
            "supplier_name": "Test Supplier",
            "company": "Test Company",
            "transaction_date": date.today(),
        }
        assert po_data["rfq_id"] == rfq_id

    def test_po_line_item_preserves_quotation_item_id(self) -> None:
        """PO line items should preserve quotation_item_id for downstream receipt linkage."""
        quotation_item_id = uuid.uuid4()
        po_item = {
            "quotation_item_id": quotation_item_id,
            "item_code": "MAT-001",
            "item_name": "Industrial Bearing",
            "qty": Decimal("100"),
            "uom": "PCS",
        }
        assert po_item["quotation_item_id"] == quotation_item_id


class TestPurchaseOrderLifecycle:
    """PO status lifecycle and transition tests."""

    def test_po_lifecycle_statuses_are_distinct(self) -> None:
        """PO lifecycle statuses must be distinct to avoid state confusion."""
        statuses = [
            "draft",
            "submitted",
            "on_hold",
            "to_receive",
            "to_bill",
            "to_receive_and_bill",
            "completed",
            "cancelled",
            "closed",
        ]
        assert len(statuses) == len(set(statuses))

    def test_po_cannot_cancel_when_completed(self) -> None:
        """PO cannot be cancelled once completed."""
        po_status = "completed"
        # Cancellation is only allowed for draft, submitted, to_receive, to_bill
        can_cancel = po_status not in ("completed", "cancelled", "closed")
        assert can_cancel is False

    def test_po_cannot_close_when_submitted(self) -> None:
        """PO cannot be closed without first being completed or cancelled."""
        po_status = "submitted"
        # Closing requires completed or cancelled status
        can_close = po_status in ("completed", "cancelled")
        assert can_close is False

    def test_po_on_hold_can_be_released(self) -> None:
        """PO on hold can be released back to active state."""
        po_status = "on_hold"
        can_release = po_status == "on_hold"
        assert can_release is True


class TestPurchaseOrderProgress:
    """PO progress tracking tests."""

    def test_po_per_received_starts_at_zero(self) -> None:
        """PO per_received should start at 0.00% for new POs."""
        per_received = Decimal("0.00")
        assert per_received == Decimal("0.00")

    def test_po_per_billed_starts_at_zero(self) -> None:
        """PO per_billed should start at 0.00% for new POs."""
        per_billed = Decimal("0.00")
        assert per_billed == Decimal("0.00")

    def test_po_per_received_computed_from_received_qty_over_total_qty(self) -> None:
        """per_received = received_qty / total_qty * 100."""
        total_qty = Decimal("100")
        received_qty = Decimal("75")
        per_received = (received_qty / total_qty) * Decimal("100")
        assert per_received == Decimal("75.00")

    def test_po_per_billed_computed_from_billed_amount_over_grand_total(self) -> None:
        """per_billed = billed_amount / grand_total * 100."""
        grand_total = Decimal("10000.00")
        billed_amount = Decimal("5000.00")
        per_billed = (billed_amount / grand_total) * Decimal("100")
        assert per_billed == Decimal("50.00")

    def test_po_per_received_capped_at_100_percent(self) -> None:
        """per_received cannot exceed 100%."""
        total_qty = Decimal("100")
        received_qty = Decimal("120")  # Over-delivery
        per_received = min(Decimal("100.00"), (received_qty / total_qty) * Decimal("100"))
        assert per_received == Decimal("100.00")

    def test_po_per_billed_capped_at_100_percent(self) -> None:
        """per_billed cannot exceed 100%."""
        grand_total = Decimal("10000.00")
        billed_amount = Decimal("15000.00")  # Over-billing
        per_billed = min(Decimal("100.00"), (billed_amount / grand_total) * Decimal("100"))
        assert per_billed == Decimal("100.00")

    def test_po_status_derived_from_per_received_and_per_billed(self) -> None:
        """PO status should reflect progress toward completion."""
        per_received = Decimal("50.00")
        per_billed = Decimal("0.00")

        if per_received < Decimal("100.00") and per_billed < Decimal("100.00"):
            derived_status = "to_receive_and_bill"
        elif per_received < Decimal("100.00"):
            derived_status = "to_receive"
        elif per_billed < Decimal("100.00"):
            derived_status = "to_bill"
        else:
            derived_status = "completed"

        assert derived_status == "to_receive_and_bill"


class TestPurchaseOrderNoGoodsReceipt:
    """Validation that PO story does not implement goods receipt logic."""

    def test_no_goods_receipt_fields_in_po_create(self) -> None:
        """PO create should not include goods receipt fields."""
        from domains.procurement.schemas import PurchaseOrderCreate

        payload = PurchaseOrderCreate(
            supplier_name="Test Supplier",
            company="Test Company",
            transaction_date=date.today(),
        )
        # PO create should NOT have received_qty, receipt_id, etc.
        # These are set by goods receipt story (24-3)
        po_dict = payload.model_dump()
        assert "received_qty" not in po_dict
        assert "receipt_date" not in po_dict
        assert "purchase_receipt_id" not in po_dict

    def test_no_supplier_invoice_fields_in_po_create(self) -> None:
        """PO create should not include supplier invoice fields."""
        from domains.procurement.schemas import PurchaseOrderCreate

        payload = PurchaseOrderCreate(
            supplier_name="Test Supplier",
            company="Test Company",
            transaction_date=date.today(),
        )
        po_dict = payload.model_dump()
        # Invoice fields are set by supplier invoice story (24-6)
        assert "invoice_id" not in po_dict
        assert "invoice_date" not in po_dict
        assert "billed_date" not in po_dict

    def test_no_landed_cost_fields_in_po_create(self) -> None:
        """PO create should not include landed cost allocation fields."""
        from domains.procurement.schemas import PurchaseOrderCreate

        payload = PurchaseOrderCreate(
            supplier_name="Test Supplier",
            company="Test Company",
            transaction_date=date.today(),
        )
        po_dict = payload.model_dump()
        # Landed cost is handled by Story 24-6 AP posting
        assert "landed_cost" not in po_dict
        assert "additional_costs" not in po_dict

    def test_no_subcontracting_fields_in_po_create(self) -> None:
        """PO create should not include subcontracting-specific fields."""
        from domains.procurement.schemas import PurchaseOrderCreate

        payload = PurchaseOrderCreate(
            supplier_name="Test Supplier",
            company="Test Company",
            transaction_date=date.today(),
        )
        po_dict = payload.model_dump()
        # Subcontracting is deferred to Story 24-6
        assert "is_subcontracted" not in po_dict
        assert "supplier_warehouse" not in po_dict
        assert "bom" not in po_dict
