"""Focused opportunity service tests for Story 23.2."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import pytest

from common.errors import ValidationError
from domains.crm.schemas import (
    OpportunityCreate,
    OpportunityPartyKind,
    OpportunityStatus,
    OpportunityTransition,
)
from domains.crm.service import (
    create_opportunity,
    prepare_opportunity_quotation_handoff,
    transition_opportunity_status,
)


def _opportunity_payload(**overrides: object) -> OpportunityCreate:
    defaults = {
        "opportunity_title": "Rotor Works Expansion",
        "opportunity_from": OpportunityPartyKind.LEAD,
        "party_name": "11111111-2222-3333-4444-555555555555",
        "sales_stage": "qualification",
        "probability": 55,
        "expected_closing": date(2026, 5, 31),
        "currency": "twd",
        "opportunity_owner": "alice@sales.test",
        "territory": "North",
        "customer_group": "Industrial",
        "contact_person": "",
        "contact_email": "",
        "contact_mobile": "",
        "job_title": "Procurement Manager",
        "utm_source": "expo",
        "utm_medium": "field",
        "utm_campaign": "spring-2026",
        "utm_content": "booth-a3",
        "items": [
            {
                "item_name": "Rotor Assembly",
                "description": "24V industrial rotor",
                "quantity": "2",
                "unit_price": "12500.00",
            }
        ],
        "notes": "Priority expansion project.",
    }
    defaults.update(overrides)
    return OpportunityCreate(**defaults)


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


class _FakeCustomer:
    def __init__(self, customer_id: str) -> None:
        self.id = uuid.UUID(customer_id)
        self.tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        self.company_name = "Rotor Works"
        self.contact_name = "Amy Chen"
        self.contact_email = "amy@rotor.example"
        self.contact_phone = "02-1234-5678"


class _FakeOpportunity:
    def __init__(self, *, opportunity_id: uuid.UUID | None = None, status: OpportunityStatus = OpportunityStatus.OPEN) -> None:
        self.id = opportunity_id or uuid.uuid4()
        self.tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        self.opportunity_title = "Rotor Works Expansion"
        self.opportunity_from = OpportunityPartyKind.LEAD
        self.party_name = "11111111-2222-3333-4444-555555555555"
        self.party_label = "Rotor Works"
        self.status = status
        self.sales_stage = "proposal"
        self.probability = 70
        self.expected_closing = date(2026, 5, 31)
        self.currency = "TWD"
        self.opportunity_amount = Decimal("25000.00")
        self.base_opportunity_amount = Decimal("25000.00")
        self.opportunity_owner = "alice@sales.test"
        self.territory = "North"
        self.customer_group = "Industrial"
        self.contact_person = "Amy Chen"
        self.contact_email = "amy@rotor.example"
        self.contact_mobile = "0912-000-111"
        self.job_title = "Procurement Manager"
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
        self.notes = "Priority expansion project."
        self.lost_reason = ""
        self.competitor_name = ""
        self.loss_notes = ""
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


class TestCreateOpportunity:
    @pytest.mark.asyncio
    async def test_create_opportunity_links_to_lead_and_derives_amount(self) -> None:
        session = FakeSession(execute_results=[_FakeScalarResult(_FakeLead("11111111-2222-3333-4444-555555555555"))])

        opportunity = await create_opportunity(session, _opportunity_payload())

        assert opportunity.opportunity_from == OpportunityPartyKind.LEAD
        assert opportunity.party_label == "Rotor Works"
        assert opportunity.contact_person == "Amy Chen"
        assert opportunity.opportunity_amount == Decimal("25000.00")
        assert opportunity.base_opportunity_amount == Decimal("25000.00")
        assert len(opportunity.items) == 1
        assert session.begin_calls == 2

    @pytest.mark.asyncio
    async def test_create_opportunity_rejects_unknown_sales_stage(self) -> None:
        session = FakeSession()

        with pytest.raises(ValidationError) as exc_info:
            await create_opportunity(session, _opportunity_payload(sales_stage="mystery_stage"))

        assert exc_info.value.errors == [{"field": "sales_stage", "message": "Select a configured sales stage."}]

    @pytest.mark.asyncio
    async def test_create_opportunity_accepts_prospect_party_without_lookup(self) -> None:
        session = FakeSession()

        opportunity = await create_opportunity(
            session,
            _opportunity_payload(
                opportunity_from=OpportunityPartyKind.PROSPECT,
                party_name="Prospect Program Alpha",
            ),
        )

        assert opportunity.opportunity_from == OpportunityPartyKind.PROSPECT
        assert opportunity.party_name == "Prospect Program Alpha"
        assert opportunity.party_label == "Prospect Program Alpha"

    @pytest.mark.asyncio
    async def test_create_opportunity_rejects_missing_customer_party(self) -> None:
        session = FakeSession(execute_results=[_FakeScalarResult(None)])

        with pytest.raises(ValidationError) as exc_info:
            await create_opportunity(
                session,
                _opportunity_payload(
                    opportunity_from=OpportunityPartyKind.CUSTOMER,
                    party_name="99999999-8888-7777-6666-555555555555",
                ),
            )

        assert exc_info.value.errors == [{"field": "party_name", "message": "Customer party not found."}]


class TestOpportunityLifecycle:
    @pytest.mark.asyncio
    async def test_lost_transition_requires_reason(self) -> None:
        opportunity = _FakeOpportunity(status=OpportunityStatus.REPLIED)
        session = FakeSession(execute_results=[_FakeScalarResult(opportunity)])

        with pytest.raises(ValidationError):
            await transition_opportunity_status(
                session,
                opportunity.id,
                OpportunityTransition(status=OpportunityStatus.LOST),
                tenant_id=opportunity.tenant_id,
            )

    @pytest.mark.asyncio
    async def test_lost_transition_captures_competitor_context(self) -> None:
        opportunity = _FakeOpportunity(status=OpportunityStatus.REPLIED)
        session = FakeSession(execute_results=[_FakeScalarResult(opportunity)])

        updated = await transition_opportunity_status(
            session,
            opportunity.id,
            OpportunityTransition(
                status=OpportunityStatus.LOST,
                lost_reason="price",
                competitor_name="Acme Dynamics",
                loss_notes="Lost on delivery lead time.",
            ),
            tenant_id=opportunity.tenant_id,
        )

        assert updated is opportunity
        assert opportunity.status == OpportunityStatus.LOST
        assert opportunity.lost_reason == "price"
        assert opportunity.competitor_name == "Acme Dynamics"
        assert opportunity.loss_notes == "Lost on delivery lead time."
        assert session.begin_calls == 2

    @pytest.mark.asyncio
    async def test_prepare_quotation_handoff_promotes_status_and_returns_context(self) -> None:
        opportunity = _FakeOpportunity(status=OpportunityStatus.REPLIED)
        session = FakeSession(execute_results=[_FakeScalarResult(opportunity)])

        handoff = await prepare_opportunity_quotation_handoff(
            session,
            opportunity.id,
            tenant_id=opportunity.tenant_id,
        )

        assert opportunity.status == OpportunityStatus.QUOTATION
        assert handoff.party_label == "Rotor Works"
        assert handoff.items[0].item_name == "Rotor Assembly"
        assert handoff.currency == "TWD"
        assert session.begin_calls == 2