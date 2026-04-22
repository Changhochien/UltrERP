"""Focused CRM lead route tests."""

from __future__ import annotations

import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from common.errors import DuplicateLeadConflictError
from domains.crm import routes as crm_routes
from domains.crm.schemas import (
    LeadConversionResult,
    LeadConversionState,
    LeadConversionStepOutcome,
    LeadConversionStepResult,
    LeadCustomerConversionResult,
    LeadOpportunityHandoff,
    LeadQualificationStatus,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tests.domains.orders._helpers import (  # noqa: E402
    FakeAsyncSession,
    auth_header,
    http_get,
    http_post,
    setup_session,
    teardown_session,
)


async def test_list_leads_allows_sales_role(monkeypatch) -> None:
    lead_id = uuid.uuid4()
    updated_at = datetime.now(tz=UTC)

    async def fake_list_leads(_session: FakeAsyncSession, params, tenant_id: uuid.UUID):
        assert params.status.value == "open"
        assert params.q == "rotor"
        assert tenant_id
        return (
            [
                SimpleNamespace(
                    id=lead_id,
                    lead_name="Rotor Works",
                    company_name="Rotor Works",
                    email_id="owner@rotor.example",
                    phone="02-1234-5678",
                    mobile_no="0912-000-111",
                    territory="North",
                    lead_owner="alice",
                    source="expo",
                    status="open",
                    qualification_status="in_process",
                    updated_at=updated_at,
                )
            ],
            1,
        )

    monkeypatch.setattr(crm_routes, "list_leads", fake_list_leads)
    session = FakeAsyncSession()
    prev = setup_session(session)
    try:
        resp = await http_get(
            "/api/v1/crm/leads?q=rotor&status=open",
            headers=auth_header("sales"),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["items"][0]["company_name"] == "Rotor Works"
        assert body["total_count"] == 1
    finally:
        teardown_session(prev)


async def test_list_leads_rejects_warehouse_role() -> None:
    resp = await http_get("/api/v1/crm/leads", headers=auth_header("warehouse"))
    assert resp.status_code == 403


async def test_create_lead_returns_structured_duplicates(monkeypatch) -> None:
    async def fake_create_lead(*_args, **_kwargs):
        raise DuplicateLeadConflictError(
            [
                {
                    "kind": "customer",
                    "id": str(uuid.uuid4()),
                    "label": "Acme Industrial",
                    "matched_on": "company_name",
                }
            ]
        )

    monkeypatch.setattr(crm_routes, "create_lead", fake_create_lead)
    session = FakeAsyncSession()
    prev = setup_session(session)
    try:
        resp = await http_post(
            "/api/v1/crm/leads",
            {
                "lead_name": "Acme Industrial",
                "company_name": "Acme Industrial",
                "email_id": "lead@acme.example",
                "qualification_status": "in_process",
            },
            headers=auth_header("sales"),
        )
        assert resp.status_code == 409
        body = resp.json()
        assert body["error"] == "duplicate_lead"
        assert body["candidates"][0]["matched_on"] == "company_name"
    finally:
        teardown_session(prev)


async def test_handoff_to_opportunity_returns_context(monkeypatch) -> None:
    lead_id = uuid.uuid4()

    async def fake_handoff(_session: FakeAsyncSession, requested_lead_id: uuid.UUID, tenant_id: uuid.UUID):
        assert requested_lead_id == lead_id
        assert tenant_id
        return LeadOpportunityHandoff(
            lead_id=lead_id,
            lead_name="Acme Industrial",
            company_name="Acme Industrial",
            email_id="lead@acme.example",
            phone="02-1234-5678",
            mobile_no="0912-000-111",
            territory="North",
            lead_owner="alice",
            source="expo",
            qualification_status=LeadQualificationStatus.QUALIFIED,
            utm_source="expo",
            utm_medium="field",
            utm_campaign="spring-2026",
            utm_content="booth-a3",
        )

    monkeypatch.setattr(crm_routes, "handoff_lead_to_opportunity", fake_handoff)
    session = FakeAsyncSession()
    prev = setup_session(session)
    try:
        resp = await http_post(
            f"/api/v1/crm/leads/{lead_id}/handoff/opportunity",
            {},
            headers=auth_header("sales"),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["qualification_status"] == "qualified"
        assert body["utm_campaign"] == "spring-2026"
    finally:
        teardown_session(prev)


async def test_convert_to_customer_returns_lineage(monkeypatch) -> None:
    lead_id = uuid.uuid4()
    customer_id = uuid.uuid4()

    async def fake_convert(
        _session: FakeAsyncSession,
        requested_lead_id: uuid.UUID,
        data,
        tenant_id: uuid.UUID,
    ):
        assert requested_lead_id == lead_id
        assert data.company_name == "Acme Industrial"
        assert tenant_id
        return LeadCustomerConversionResult(
            lead_id=lead_id,
            customer_id=customer_id,
            status="converted",
        )

    monkeypatch.setattr(crm_routes, "convert_lead_to_customer", fake_convert)
    session = FakeAsyncSession()
    prev = setup_session(session)
    try:
        resp = await http_post(
            f"/api/v1/crm/leads/{lead_id}/convert/customer",
            {
                "company_name": "Acme Industrial",
                "business_number": "12345675",
                "billing_address": "1 Harbor Rd",
                "contact_name": "Amy Chen",
                "contact_phone": "02-1234-5678",
                "contact_email": "amy@acme.example",
                "credit_limit": "0",
                "default_discount_percent": "0",
            },
            headers=auth_header("sales"),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["lead_id"] == str(lead_id)
        assert body["customer_id"] == str(customer_id)
        assert body["status"] == "converted"
    finally:
        teardown_session(prev)


async def test_convert_lead_route_returns_structured_conversion_result(monkeypatch) -> None:
    lead_id = uuid.uuid4()
    customer_id = uuid.uuid4()

    async def fake_convert(
        _session: FakeAsyncSession,
        requested_lead_id: uuid.UUID,
        data,
        tenant_id: uuid.UUID,
        converted_by: str | None,
    ):
        assert requested_lead_id == lead_id
        assert data.customer is not None
        assert tenant_id
        assert converted_by == "00000000-0000-0000-0000-000000000111"
        return LeadConversionResult(
            lead_id=lead_id,
            status="converted",
            conversion_state=LeadConversionState.CONVERTED,
            conversion_path="customer",
            converted_by="00000000-0000-0000-0000-000000000111",
            converted_customer_id=customer_id,
            steps=[
                LeadConversionStepResult(
                    target="customer",
                    outcome=LeadConversionStepOutcome.CREATED,
                    record_id=customer_id,
                )
            ],
        )

    monkeypatch.setattr(crm_routes, "convert_lead", fake_convert)
    session = FakeAsyncSession()
    prev = setup_session(session)
    try:
        resp = await http_post(
            f"/api/v1/crm/leads/{lead_id}/convert",
            {
                "customer": {
                    "company_name": "Acme Industrial",
                    "business_number": "12345675",
                    "billing_address": "1 Harbor Rd",
                    "contact_name": "Amy Chen",
                    "contact_phone": "02-1234-5678",
                    "contact_email": "amy@acme.example",
                    "credit_limit": "0",
                    "default_discount_percent": "0",
                }
            },
            headers=auth_header("sales"),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["lead_id"] == str(lead_id)
        assert body["conversion_state"] == "converted"
        assert body["converted_customer_id"] == str(customer_id)
        assert body["steps"][0]["outcome"] == "created"
    finally:
        teardown_session(prev)