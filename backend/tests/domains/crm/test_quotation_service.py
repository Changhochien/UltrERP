"""Focused quotation service tests for Story 23.3."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest

from common.errors import ValidationError
from domains.crm.schemas import (
    QuotationCreate,
    QuotationPartyKind,
    QuotationRevisionCreate,
    QuotationStatus,
    QuotationTransition,
)
from domains.crm.service import (
    create_quotation,
    create_quotation_revision,
    get_quotation,
    prepare_quotation_order_handoff,
    sync_quotation_order_coverage,
    transition_quotation_status,
)


def _quotation_payload(**overrides: object) -> QuotationCreate:
    defaults = {
        "quotation_to": QuotationPartyKind.LEAD,
        "party_name": "11111111-2222-3333-4444-555555555555",
        "transaction_date": date(2026, 4, 21),
        "valid_till": date(2026, 5, 21),
        "company": "UltrERP Taiwan",
        "currency": "twd",
        "contact_person": "",
        "contact_email": "",
        "contact_mobile": "",
        "job_title": "Procurement Manager",
        "territory": "North",
        "customer_group": "Industrial",
        "billing_address": "No. 1, Zhongshan Rd, Taipei",
        "shipping_address": "Warehouse 7, Taoyuan",
        "utm_source": "expo",
        "utm_medium": "field",
        "utm_campaign": "spring-2026",
        "utm_content": "booth-a3",
        "opportunity_id": uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"),
        "items": [
            {
                "item_name": "Rotor Assembly",
                "description": "24V industrial rotor",
                "quantity": "2",
                "unit_price": "12500.00",
            }
        ],
        "taxes": [
            {
                "description": "VAT",
                "rate": "5.00",
            }
        ],
        "terms_template": "standard-sales",
        "terms_and_conditions": "Net 30 days.",
        "auto_repeat_enabled": True,
        "auto_repeat_frequency": "monthly",
        "auto_repeat_until": date(2026, 12, 31),
        "notes": "Initial commercial offer.",
    }
    defaults.update(overrides)
    return QuotationCreate(**defaults)


class _FakeLead:
    def __init__(self, lead_id: str) -> None:
        self.id = uuid.UUID(lead_id)
        self.tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        self.lead_name = "Amy Chen"
        self.company_name = "Rotor Works"
        self.email_id = "amy@rotor.example"
        self.phone = "02-1234-5678"
        self.mobile_no = "0912-000-111"
        self.territory = "North"
        self.utm_source = "expo"
        self.utm_medium = "field"
        self.utm_campaign = "spring-2026"
        self.utm_content = "booth-a3"
        self.converted_customer_id: uuid.UUID | None = None


class _FakeQuotation:
    def __init__(
        self,
        *,
        quotation_id: uuid.UUID | None = None,
        status: QuotationStatus = QuotationStatus.DRAFT,
        valid_till: date | None = None,
        ordered_amount: Decimal = Decimal("0.00"),
        order_count: int = 0,
    ) -> None:
        self.id = quotation_id or uuid.uuid4()
        self.tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        self.quotation_to = QuotationPartyKind.LEAD
        self.party_name = "11111111-2222-3333-4444-555555555555"
        self.party_label = "Rotor Works"
        self.status = status
        self.transaction_date = date(2026, 4, 21)
        self.valid_till = valid_till or date(2026, 5, 21)
        self.company = "UltrERP Taiwan"
        self.currency = "TWD"
        self.subtotal = Decimal("25000.00")
        self.total_taxes = Decimal("1250.00")
        self.grand_total = Decimal("26250.00")
        self.base_grand_total = Decimal("26250.00")
        self.ordered_amount = ordered_amount
        self.order_count = order_count
        self.contact_person = "Amy Chen"
        self.contact_email = "amy@rotor.example"
        self.contact_mobile = "0912-000-111"
        self.job_title = "Procurement Manager"
        self.territory = "North"
        self.customer_group = "Industrial"
        self.billing_address = "No. 1, Zhongshan Rd, Taipei"
        self.shipping_address = "Warehouse 7, Taoyuan"
        self.utm_source = "expo"
        self.utm_medium = "field"
        self.utm_campaign = "spring-2026"
        self.utm_content = "booth-a3"
        self.items = [
            {
                "line_no": 1,
                "item_name": "Rotor Assembly",
                "item_code": "",
                "description": "24V industrial rotor",
                "quantity": "2.00",
                "unit_price": "12500.00",
                "amount": "25000.00",
            }
        ]
        self.taxes = [
            {
                "line_no": 1,
                "description": "VAT",
                "rate": "5.00",
                "tax_amount": "1250.00",
            }
        ]
        self.terms_template = "standard-sales"
        self.terms_and_conditions = "Net 30 days."
        self.opportunity_id = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
        self.amended_from = None
        self.revision_no = 0
        self.lost_reason = ""
        self.competitor_name = ""
        self.loss_notes = ""
        self.auto_repeat_enabled = True
        self.auto_repeat_frequency = "monthly"
        self.auto_repeat_until = date(2026, 12, 31)
        self.notes = "Initial commercial offer."
        self.version = 1
        self.created_at = datetime.now(tz=UTC)
        self.updated_at = datetime.now(tz=UTC)


class _FakeScalarResult:
    def __init__(self, value: object = None) -> None:
        self._value = value

    def scalar_one_or_none(self) -> object:
        return self._value

    def scalar(self) -> object:
        return self._value


class _FakeRowsResult:
    def __init__(self, rows: list[object]) -> None:
        self._rows = rows

    def all(self) -> list[object]:
        return list(self._rows)


class FakeSession:
    def __init__(self, execute_results: list[object] | None = None) -> None:
        self._execute_results = list(execute_results or [])
        self.added: list[Any] = []
        self.begin_calls = 0

    async def execute(self, stmt: object, params: object = None) -> object:
        if isinstance(params, dict) and "tid" in params:
            return _FakeScalarResult(None)
        if self._execute_results:
            return self._execute_results.pop(0)
        return _FakeScalarResult(None)

    def add(self, instance: object) -> None:
        self.added.append(instance)

    async def refresh(self, instance: object) -> None:
        now = datetime.now(tz=UTC)
        if getattr(instance, "id", None) is None:
            instance.id = uuid.uuid4()  # type: ignore[attr-defined]
        instance.updated_at = now  # type: ignore[attr-defined]

    def begin(self) -> "FakeSession":
        self.begin_calls += 1
        return self

    async def __aenter__(self) -> "FakeSession":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None


class TestCreateQuotation:
    @pytest.mark.asyncio
    async def test_create_quotation_derives_totals_and_party_defaults(self) -> None:
        session = FakeSession(execute_results=[_FakeScalarResult(_FakeLead("11111111-2222-3333-4444-555555555555"))])

        quotation = await create_quotation(session, _quotation_payload())

        assert quotation.status == QuotationStatus.DRAFT
        assert quotation.party_label == "Rotor Works"
        assert quotation.contact_person == "Amy Chen"
        assert quotation.subtotal == Decimal("25000.00")
        assert quotation.total_taxes == Decimal("1250.00")
        assert quotation.grand_total == Decimal("26250.00")
        assert quotation.base_grand_total == Decimal("26250.00")
        assert quotation.auto_repeat_enabled is True
        assert quotation.auto_repeat_frequency == "monthly"
        assert quotation.opportunity_id == uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")


class TestQuotationLifecycle:
    @pytest.mark.asyncio
    async def test_lost_transition_requires_reason(self) -> None:
        quotation = _FakeQuotation(status=QuotationStatus.OPEN)
        session = FakeSession(execute_results=[_FakeScalarResult(quotation)])

        with pytest.raises(ValidationError):
            await transition_quotation_status(
                session,
                quotation.id,
                QuotationTransition(status=QuotationStatus.LOST),
                tenant_id=quotation.tenant_id,
            )

    @pytest.mark.asyncio
    async def test_lost_transition_captures_competitor_context(self) -> None:
        quotation = _FakeQuotation(status=QuotationStatus.REPLIED)
        session = FakeSession(execute_results=[_FakeScalarResult(quotation)])

        updated = await transition_quotation_status(
            session,
            quotation.id,
            QuotationTransition(
                status=QuotationStatus.LOST,
                lost_reason="price",
                competitor_name="Acme Dynamics",
                loss_notes="Lost on delivery lead time.",
            ),
            tenant_id=quotation.tenant_id,
        )

        assert updated is quotation
        assert quotation.status == QuotationStatus.LOST
        assert quotation.lost_reason == "price"
        assert quotation.competitor_name == "Acme Dynamics"
        assert quotation.loss_notes == "Lost on delivery lead time."

    @pytest.mark.asyncio
    async def test_get_quotation_marks_expired_after_valid_till(self) -> None:
        quotation = _FakeQuotation(
            status=QuotationStatus.OPEN,
            valid_till=date.today() - timedelta(days=1),
        )
        session = FakeSession(execute_results=[_FakeScalarResult(quotation)])

        fetched = await get_quotation(session, quotation.id, tenant_id=quotation.tenant_id)

        assert fetched is quotation
        assert quotation.status == QuotationStatus.EXPIRED

    @pytest.mark.asyncio
    async def test_get_quotation_derives_partial_order_from_downstream_coverage(self) -> None:
        quotation = _FakeQuotation(
            status=QuotationStatus.REPLIED,
            ordered_amount=Decimal("10000.00"),
            order_count=1,
        )
        session = FakeSession(execute_results=[_FakeScalarResult(quotation)])

        fetched = await get_quotation(session, quotation.id, tenant_id=quotation.tenant_id)

        assert fetched is quotation
        assert quotation.status == QuotationStatus.PARTIALLY_ORDERED


class TestQuotationRevision:
    @pytest.mark.asyncio
    async def test_create_revision_preserves_lineage_and_commercial_context(self) -> None:
        quotation = _FakeQuotation(status=QuotationStatus.REPLIED)
        session = FakeSession(execute_results=[_FakeScalarResult(quotation)])

        revised = await create_quotation_revision(
            session,
            quotation.id,
            QuotationRevisionCreate(
                valid_till=date(2026, 6, 15),
                terms_and_conditions="Net 45 days.",
                notes="Reissued with updated validity.",
            ),
            tenant_id=quotation.tenant_id,
        )

        assert revised.id != quotation.id
        assert revised.status == QuotationStatus.DRAFT
        assert revised.amended_from == quotation.id
        assert revised.revision_no == quotation.revision_no + 1
        assert revised.party_name == quotation.party_name
        assert revised.items == quotation.items
        assert revised.valid_till == date(2026, 6, 15)
        assert revised.terms_and_conditions == "Net 45 days."
        assert revised.notes == "Reissued with updated validity."


class TestQuotationOrderHandoff:
    @pytest.mark.asyncio
    async def test_prepare_order_handoff_resolves_lead_to_existing_customer(self) -> None:
        lead = _FakeLead("11111111-2222-3333-4444-555555555555")
        lead.converted_customer_id = uuid.UUID("99999999-8888-7777-6666-555555555555")
        quotation = _FakeQuotation(status=QuotationStatus.REPLIED)
        quotation.quotation_to = QuotationPartyKind.LEAD
        quotation.party_name = str(lead.id)
        quotation.items = [
            {
                "line_no": 1,
                "product_id": "aaaaaaaa-1111-2222-3333-bbbbbbbbbbbb",
                "item_name": "Rotor Assembly",
                "item_code": "ROTOR-24V",
                "description": "24V industrial rotor",
                "quantity": "2.00",
                "unit_price": "12500.00",
                "amount": "25000.00",
            }
        ]
        session = FakeSession(
            execute_results=[
                _FakeScalarResult(quotation),
                _FakeScalarResult(lead),
            ]
        )

        handoff = await prepare_quotation_order_handoff(
            session,
            quotation.id,
            tenant_id=quotation.tenant_id,
        )

        assert handoff.quotation_id == quotation.id
        assert handoff.customer_id == lead.converted_customer_id
        assert handoff.source_quotation_id == quotation.id
        assert handoff.crm_context_snapshot["source_document_type"] == "quotation"
        assert handoff.lines[0].product_id == uuid.UUID("aaaaaaaa-1111-2222-3333-bbbbbbbbbbbb")
        assert handoff.lines[0].source_quotation_line_no == 1
        assert handoff.lines[0].quantity == Decimal("2.00")

    @pytest.mark.asyncio
    async def test_prepare_order_handoff_blocks_lead_without_customer_resolution(self) -> None:
        lead = _FakeLead("11111111-2222-3333-4444-555555555555")
        quotation = _FakeQuotation(status=QuotationStatus.REPLIED)
        quotation.quotation_to = QuotationPartyKind.LEAD
        quotation.party_name = str(lead.id)
        quotation.items = [
            {
                "line_no": 1,
                "product_id": "aaaaaaaa-1111-2222-3333-bbbbbbbbbbbb",
                "item_name": "Rotor Assembly",
                "item_code": "ROTOR-24V",
                "description": "24V industrial rotor",
                "quantity": "2.00",
                "unit_price": "12500.00",
                "amount": "25000.00",
            }
        ]
        session = FakeSession(
            execute_results=[
                _FakeScalarResult(quotation),
                _FakeScalarResult(lead),
            ]
        )

        with pytest.raises(ValidationError) as exc_info:
            await prepare_quotation_order_handoff(
                session,
                quotation.id,
                tenant_id=quotation.tenant_id,
            )

        assert exc_info.value.errors[0]["field"] == "party_name"


class TestQuotationOrderCoverage:
    @pytest.mark.asyncio
    async def test_sync_quotation_order_coverage_updates_counts_amounts_and_status(self) -> None:
        quotation = _FakeQuotation(status=QuotationStatus.OPEN)
        quotation.items = [
            {
                "line_no": 1,
                "item_name": "Rotor Assembly",
                "item_code": "ROTOR-24V",
                "description": "24V industrial rotor",
                "quantity": "4.00",
                "unit_price": "100.00",
                "amount": "400.00",
            },
            {
                "line_no": 2,
                "item_name": "Control Board",
                "item_code": "CTRL-01",
                "description": "Control board",
                "quantity": "2.00",
                "unit_price": "100.00",
                "amount": "200.00",
            },
        ]
        quotation.grand_total = Decimal("600.00")
        rows = [
            SimpleNamespace(
                order_id=uuid.uuid4(),
                order_number="ORD-20260422-AAAA1111",
                status="pending",
                total_amount=Decimal("200.00"),
                created_at=datetime.now(tz=UTC),
                source_quotation_line_no=1,
                quantity=Decimal("2.000"),
            ),
            SimpleNamespace(
                order_id=uuid.uuid4(),
                order_number="ORD-20260422-BBBB2222",
                status="confirmed",
                total_amount=Decimal("200.00"),
                created_at=datetime.now(tz=UTC),
                source_quotation_line_no=2,
                quantity=Decimal("2.000"),
            ),
        ]
        session = FakeSession(
            execute_results=[
                _FakeScalarResult(quotation),
                _FakeRowsResult(rows),
            ]
        )

        updated = await sync_quotation_order_coverage(session, quotation.id, tenant_id=quotation.tenant_id)

        assert updated is quotation
        assert quotation.order_count == 2
        assert quotation.ordered_amount == Decimal("400.00")
        assert quotation.status == QuotationStatus.PARTIALLY_ORDERED.value

    @pytest.mark.asyncio
    async def test_get_quotation_attaches_linked_orders_and_remaining_scope(self) -> None:
        quotation = _FakeQuotation(
            status=QuotationStatus.PARTIALLY_ORDERED,
            ordered_amount=Decimal("400.00"),
            order_count=2,
        )
        quotation.items = [
            {
                "line_no": 1,
                "item_name": "Rotor Assembly",
                "item_code": "ROTOR-24V",
                "description": "24V industrial rotor",
                "quantity": "4.00",
                "unit_price": "100.00",
                "amount": "400.00",
            },
            {
                "line_no": 2,
                "item_name": "Control Board",
                "item_code": "CTRL-01",
                "description": "Control board",
                "quantity": "2.00",
                "unit_price": "100.00",
                "amount": "200.00",
            },
        ]
        quotation.grand_total = Decimal("600.00")
        linked_order_id = uuid.uuid4()
        rows = [
            SimpleNamespace(
                order_id=linked_order_id,
                order_number="ORD-20260422-AAAA1111",
                status="pending",
                total_amount=Decimal("200.00"),
                created_at=datetime.now(tz=UTC),
                source_quotation_line_no=1,
                quantity=Decimal("2.000"),
            )
        ]
        session = FakeSession(
            execute_results=[
                _FakeScalarResult(quotation),
                _FakeRowsResult(rows),
            ]
        )

        fetched = await get_quotation(session, quotation.id, tenant_id=quotation.tenant_id)

        assert fetched is quotation
        assert fetched.linked_orders[0].order_id == linked_order_id
        assert fetched.linked_orders[0].linked_line_count == 1
        assert fetched.remaining_items[0].line_no == 1
        assert fetched.remaining_items[0].remaining_quantity == Decimal("2.000")
        assert fetched.remaining_items[1].line_no == 2
        assert fetched.remaining_items[1].remaining_quantity == Decimal("2.000")