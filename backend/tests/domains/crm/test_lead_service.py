"""Focused lead service tests for Story 23.1.

These tests lock the first CRM slice to lead persistence, cross-table duplicate
guidance, lifecycle enforcement, opportunity handoff, and customer conversion
without requiring a real database.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest

from common.errors import DuplicateLeadConflictError, ValidationError
from domains.crm.schemas import (
    LeadCreate,
    LeadQualificationStatus,
    LeadStatus,
)
from domains.crm.service import (
    create_lead,
    convert_lead_to_customer,
    handoff_lead_to_opportunity,
    transition_lead_status,
)
from domains.customers.schemas import CustomerCreate


def _valid_payload(**overrides: object) -> LeadCreate:
    defaults = {
        "lead_name": "Alice Prospect",
        "company_name": "Prospect Labs",
        "email_id": "alice@prospect.test",
        "phone": "02-2345-6789",
        "mobile_no": "0912-345-678",
        "territory": "Taipei",
        "lead_owner": "sales.owner@test",
        "source": "website",
        "qualification_status": LeadQualificationStatus.IN_PROCESS,
        "annual_revenue": Decimal("1250000.00"),
        "no_of_employees": 15,
        "industry": "Manufacturing",
        "market_segment": "SMB",
        "utm_source": "google",
        "utm_medium": "cpc",
        "utm_campaign": "spring-launch",
        "utm_content": "hero-banner",
        "notes": "Interested in industrial supplies.",
    }
    defaults.update(overrides)
    return LeadCreate(**defaults)  # type: ignore[arg-type]


class _FakeLead:
    def __init__(
        self,
        *,
        lead_id: uuid.UUID | None = None,
        status: LeadStatus = LeadStatus.LEAD,
        qualification_status: LeadQualificationStatus = LeadQualificationStatus.IN_PROCESS,
    ) -> None:
        self.id = lead_id or uuid.uuid4()
        self.tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        self.lead_name = "Alice Prospect"
        self.company_name = "Prospect Labs"
        self.normalized_company_name = "prospectlabs"
        self.email_id = "alice@prospect.test"
        self.normalized_email_id = "alice@prospect.test"
        self.phone = "02-2345-6789"
        self.mobile_no = "0912-345-678"
        self.normalized_phone = "0223456789"
        self.normalized_mobile_no = "0912345678"
        self.territory = "Taipei"
        self.lead_owner = "sales.owner@test"
        self.source = "website"
        self.status = status
        self.qualification_status = qualification_status
        self.qualified_by = "sales.owner@test"
        self.annual_revenue = Decimal("1250000.00")
        self.no_of_employees = 15
        self.industry = "Manufacturing"
        self.market_segment = "SMB"
        self.utm_source = "google"
        self.utm_medium = "cpc"
        self.utm_campaign = "spring-launch"
        self.utm_content = "hero-banner"
        self.notes = "Interested in industrial supplies."
        self.converted_customer_id = None
        self.converted_at = None
        self.version = 1
        self.created_at = datetime.now(tz=UTC)
        self.updated_at = datetime.now(tz=UTC)


class _FakeCustomer:
    def __init__(self, customer_id: uuid.UUID | None = None) -> None:
        self.id = customer_id or uuid.uuid4()
        self.company_name = "Prospect Labs"


class _FakeScalarResult:
    def __init__(self, value: object = None) -> None:
        self._value = value

    def scalar_one_or_none(self) -> object:
        return self._value


class _FakeScalarsResult:
    def __init__(self, values: list[object] | None = None) -> None:
        self._values = values or []

    def all(self) -> list[object]:
        return list(self._values)


class _FakeListResult:
    def __init__(self, values: list[object]) -> None:
        self._values = values

    def scalars(self) -> _FakeScalarsResult:
        return _FakeScalarsResult(self._values)


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
        if getattr(instance, "version", None) is None:
            instance.version = 1  # type: ignore[attr-defined]
        if getattr(instance, "created_at", None) is None:
            instance.created_at = now  # type: ignore[attr-defined]
        instance.updated_at = now  # type: ignore[attr-defined]

    def begin(self) -> "FakeSession":
        self.begin_calls += 1
        return self

    async def __aenter__(self) -> "FakeSession":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None


class TestCreateLead:
    @pytest.mark.asyncio
    async def test_create_lead_persists_defaults_when_no_duplicates_exist(self) -> None:
        session = FakeSession(execute_results=[_FakeListResult([]), _FakeListResult([])])

        lead = await create_lead(session, _valid_payload())  # type: ignore[arg-type]

        assert lead.lead_name == "Alice Prospect"
        assert lead.status == LeadStatus.LEAD
        assert lead.qualification_status == LeadQualificationStatus.IN_PROCESS
        assert len(session.added) == 1

    @pytest.mark.asyncio
    async def test_create_lead_raises_structured_duplicate_conflict(self) -> None:
        existing_lead = _FakeLead()
        existing_customer = _FakeCustomer(uuid.UUID("22222222-3333-4444-5555-666666666666"))
        session = FakeSession(
            execute_results=[
                _FakeListResult([existing_lead]),
                _FakeListResult([existing_customer]),
            ]
        )

        with pytest.raises(DuplicateLeadConflictError) as exc_info:
            await create_lead(session, _valid_payload())  # type: ignore[arg-type]

        candidates = exc_info.value.candidates
        assert len(candidates) == 2
        assert {candidate["kind"] for candidate in candidates} == {"lead", "customer"}
        assert {candidate["matched_on"] for candidate in candidates} >= {"company_name"}

    @pytest.mark.asyncio
    async def test_create_lead_detects_customer_duplicate_when_company_punctuation_differs(self) -> None:
        existing_customer = _FakeCustomer(uuid.UUID("33333333-4444-5555-6666-777777777777"))
        existing_customer.company_name = "Prospect, Labs"
        session = FakeSession(
            execute_results=[
                _FakeListResult([]),
                _FakeListResult([existing_customer]),
            ]
        )

        with pytest.raises(DuplicateLeadConflictError) as exc_info:
            await create_lead(session, _valid_payload())  # type: ignore[arg-type]

        assert exc_info.value.candidates == [
            {
                "kind": "customer",
                "id": str(existing_customer.id),
                "label": "Prospect, Labs",
                "matched_on": "company_name",
            }
        ]


class TestLeadLifecycle:
    @pytest.mark.asyncio
    async def test_invalid_transition_is_rejected(self) -> None:
        lead = _FakeLead(status=LeadStatus.LEAD)
        session = FakeSession(execute_results=[_FakeScalarResult(lead)])

        with pytest.raises(ValidationError):
            await transition_lead_status(
                session,
                lead.id,
                LeadStatus.QUOTATION,
                tenant_id=lead.tenant_id,
            )

    @pytest.mark.asyncio
    async def test_valid_transition_opens_write_transaction(self) -> None:
        lead = _FakeLead(status=LeadStatus.LEAD)
        session = FakeSession(execute_results=[_FakeScalarResult(lead)])

        updated = await transition_lead_status(
            session,
            lead.id,
            LeadStatus.OPEN,
            tenant_id=lead.tenant_id,
        )

        assert updated is lead
        assert lead.status == LeadStatus.OPEN
        assert session.begin_calls == 2

    @pytest.mark.asyncio
    async def test_transition_to_opportunity_requires_dedicated_handoff(self) -> None:
        lead = _FakeLead(
            status=LeadStatus.REPLIED,
            qualification_status=LeadQualificationStatus.QUALIFIED,
        )
        session = FakeSession(execute_results=[_FakeScalarResult(lead)])

        with pytest.raises(ValidationError):
            await transition_lead_status(
                session,
                lead.id,
                LeadStatus.OPPORTUNITY,
                tenant_id=lead.tenant_id,
            )

    @pytest.mark.asyncio
    async def test_opportunity_handoff_updates_status_and_preserves_context(self) -> None:
        lead = _FakeLead(
            status=LeadStatus.REPLIED,
            qualification_status=LeadQualificationStatus.QUALIFIED,
        )
        session = FakeSession(execute_results=[_FakeScalarResult(lead)])

        handoff = await handoff_lead_to_opportunity(session, lead.id, tenant_id=lead.tenant_id)

        assert lead.status == LeadStatus.OPPORTUNITY
        assert handoff.lead_id == lead.id
        assert handoff.company_name == "Prospect Labs"
        assert handoff.territory == "Taipei"
        assert handoff.qualification_status == LeadQualificationStatus.QUALIFIED
        assert handoff.utm_campaign == "spring-launch"
        assert session.begin_calls == 2


class TestCustomerConversion:
    @pytest.mark.asyncio
    async def test_convert_lead_to_customer_marks_lineage(self, monkeypatch: pytest.MonkeyPatch) -> None:
        lead = _FakeLead(
            status=LeadStatus.REPLIED,
            qualification_status=LeadQualificationStatus.QUALIFIED,
        )
        session = FakeSession(execute_results=[_FakeScalarResult(lead)])
        created_customer = _FakeCustomer(uuid.UUID("77777777-8888-9999-aaaa-bbbbbbbbbbbb"))

        async def _fake_create_customer(*_args: object, **_kwargs: object) -> _FakeCustomer:
            return created_customer

        monkeypatch.setattr("domains.crm.service.create_customer", _fake_create_customer)

        result = await convert_lead_to_customer(
            session,
            lead.id,
            CustomerCreate(
                company_name="Prospect Labs",
                business_number="04595257",
                billing_address="Taipei",
                contact_name="Alice Prospect",
                contact_phone="0912-345-678",
                contact_email="alice@prospect.test",
                credit_limit=Decimal("0.00"),
            ),
            tenant_id=lead.tenant_id,
        )

        assert result.customer_id == created_customer.id
        assert lead.status == LeadStatus.CONVERTED
        assert lead.converted_customer_id == created_customer.id
        assert lead.converted_at is not None
        assert session.begin_calls == 2