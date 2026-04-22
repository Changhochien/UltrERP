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
    LeadConversionRequest,
    LeadConversionState,
    LeadCreate,
    LeadQualificationStatus,
    LeadStatus,
    LeadUpdate,
    OpportunityCreate,
    OpportunityPartyKind,
)
from domains.crm.service import (
    convert_lead,
    create_lead,
    create_opportunity,
    convert_lead_to_customer,
    handoff_lead_to_opportunity,
    transition_lead_status,
    update_lead,
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
        self.conversion_state = LeadConversionState.NOT_CONVERTED
        self.conversion_path = ""
        self.converted_by = ""
        self.converted_customer_id = None
        self.converted_opportunity_id = None
        self.converted_quotation_id = None
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
    async def test_create_lead_rejects_unknown_territory(self) -> None:
        session = FakeSession()

        with pytest.raises(ValidationError) as exc_info:
            await create_lead(session, _valid_payload(territory="Unknown Region"))  # type: ignore[arg-type]

        assert exc_info.value.errors == [{"field": "territory", "message": "Select a configured territory."}]

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
    async def test_create_lead_allows_duplicates_when_policy_allows(self) -> None:
        existing_lead = _FakeLead()
        settings = _FakeScalarResult(type("Settings", (), {"lead_duplicate_policy": "allow"})())
        session = FakeSession(
            execute_results=[
                _FakeListResult([existing_lead]),
                _FakeListResult([]),
                settings,
            ]
        )

        lead = await create_lead(session, _valid_payload())  # type: ignore[arg-type]

        assert lead.lead_name == "Alice Prospect"
        assert len(session.added) == 1

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
    async def test_update_lead_checks_duplicates_using_existing_identity_fields(self) -> None:
        lead = _FakeLead()
        existing_customer = _FakeCustomer(uuid.UUID("44444444-5555-6666-7777-888888888888"))
        existing_customer.company_name = lead.company_name
        session = FakeSession(
            execute_results=[
                _FakeScalarResult(lead),
                _FakeListResult([]),
                _FakeListResult([existing_customer]),
            ]
        )

        with pytest.raises(DuplicateLeadConflictError) as exc_info:
            await update_lead(
                session,
                lead.id,
                LeadUpdate(version=lead.version, territory="South"),
                tenant_id=lead.tenant_id,
            )

        assert exc_info.value.candidates == [
            {
                "kind": "customer",
                "id": str(existing_customer.id),
                "label": lead.company_name,
                "matched_on": "company_name",
            }
        ]

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
        session = FakeSession(execute_results=[_FakeScalarResult(lead), _FakeScalarResult(None), _FakeScalarResult(lead)])
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
        assert lead.conversion_state == LeadConversionState.CONVERTED
        assert lead.conversion_path == "customer"
        assert lead.converted_customer_id == created_customer.id
        assert lead.converted_at is not None
        assert session.begin_calls == 4

    @pytest.mark.asyncio
    async def test_convert_lead_marks_partial_state_when_one_target_fails(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        lead = _FakeLead(
            status=LeadStatus.REPLIED,
            qualification_status=LeadQualificationStatus.QUALIFIED,
        )
        session = FakeSession()
        created_customer = _FakeCustomer(uuid.UUID("88888888-9999-aaaa-bbbb-cccccccccccc"))

        async def _fake_get_lead(*_args: object, **_kwargs: object) -> _FakeLead:
            return lead

        async def _fake_lookup_customer(*_args: object, **_kwargs: object) -> None:
            return None

        async def _fake_create_customer(*_args: object, **_kwargs: object) -> _FakeCustomer:
            return created_customer

        async def _fake_create_opportunity(*_args: object, **_kwargs: object):
            raise ValidationError(
                [{"field": "sales_stage", "message": "Select a configured sales stage."}]
            )

        monkeypatch.setattr("domains.crm.service.get_lead", _fake_get_lead)
        monkeypatch.setattr("domains.crm.service.lookup_customer_by_ban", _fake_lookup_customer)
        monkeypatch.setattr("domains.crm.service.create_customer", _fake_create_customer)
        monkeypatch.setattr("domains.crm.service.create_opportunity", _fake_create_opportunity)

        result = await convert_lead(
            session,
            lead.id,
            LeadConversionRequest(
                customer=CustomerCreate(
                    company_name="Prospect Labs",
                    business_number="04595257",
                    billing_address="Taipei",
                    contact_name="Alice Prospect",
                    contact_phone="0912-345-678",
                    contact_email="alice@prospect.test",
                    credit_limit=Decimal("0.00"),
                ),
                opportunity=OpportunityCreate(
                    opportunity_title="Prospect Labs Opportunity",
                    opportunity_from=OpportunityPartyKind.LEAD,
                    party_name=str(lead.id),
                    sales_stage="qualification",
                ),
            ),
            tenant_id=lead.tenant_id,
            converted_by="sales.owner@test",
        )

        assert result.conversion_state == LeadConversionState.PARTIALLY_CONVERTED
        assert result.conversion_path == "customer+opportunity"
        assert result.converted_customer_id == created_customer.id
        assert result.converted_opportunity_id is None
        assert result.converted_by == "sales.owner@test"
        assert [step.outcome for step in result.steps] == ["created", "failed"]
        assert lead.converted_customer_id == created_customer.id
        assert lead.conversion_state == LeadConversionState.PARTIALLY_CONVERTED
        assert lead.status == LeadStatus.CONVERTED


class TestLeadLinkedDownstreamCreation:
    @pytest.mark.asyncio
    async def test_create_opportunity_from_lead_updates_conversion_lineage(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        lead = _FakeLead(
            status=LeadStatus.REPLIED,
            qualification_status=LeadQualificationStatus.QUALIFIED,
        )
        session = FakeSession()

        async def _fake_get_lead(*_args: object, **_kwargs: object) -> _FakeLead:
            return lead

        async def _fake_resolve_party_context(*_args: object, **_kwargs: object):
            return str(lead.id), lead.company_name, {
                "territory": lead.territory,
                "contact_person": lead.lead_name,
                "contact_email": lead.email_id,
                "contact_mobile": lead.mobile_no,
                "utm_source": lead.utm_source,
                "utm_medium": lead.utm_medium,
                "utm_campaign": lead.utm_campaign,
                "utm_content": lead.utm_content,
            }

        async def _fake_sales_stage(*_args: object, **_kwargs: object) -> str:
            return "qualification"

        async def _fake_territory(*_args: object, **_kwargs: object) -> str:
            return lead.territory

        async def _fake_customer_group(*_args: object, **_kwargs: object) -> str:
            return ""

        monkeypatch.setattr("domains.crm.service.get_lead", _fake_get_lead)
        monkeypatch.setattr("domains.crm.service._ensure_sales_stage_supported", _fake_sales_stage)
        monkeypatch.setattr("domains.crm.service._ensure_territory_supported", _fake_territory)
        monkeypatch.setattr("domains.crm.service._ensure_customer_group_supported", _fake_customer_group)
        monkeypatch.setattr("domains.crm.service._resolve_party_context", _fake_resolve_party_context)

        opportunity = await create_opportunity(
            session,
            OpportunityCreate(
                opportunity_title="Prospect Labs Opportunity",
                opportunity_from=OpportunityPartyKind.LEAD,
                party_name=str(lead.id),
                sales_stage="qualification",
            ),
            tenant_id=lead.tenant_id,
        )

        assert opportunity.id is not None
        assert lead.converted_opportunity_id == opportunity.id
        assert lead.conversion_state == LeadConversionState.CONVERTED
        assert lead.conversion_path == "opportunity"
        assert lead.status == LeadStatus.OPPORTUNITY