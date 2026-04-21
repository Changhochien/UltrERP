"""Focused CRM opportunity route tests."""

from __future__ import annotations

import sys
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from domains.crm import routes as crm_routes
from domains.crm.schemas import OpportunityQuotationHandoff

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tests.domains.orders._helpers import (  # noqa: E402
    FakeAsyncSession,
    auth_header,
    http_get,
    http_post,
    setup_session,
    teardown_session,
)


async def test_list_opportunities_allows_sales_role(monkeypatch) -> None:
    opportunity_id = uuid.uuid4()
    updated_at = datetime.now(tz=UTC)

    async def fake_list_opportunities(_session: FakeAsyncSession, params, tenant_id: uuid.UUID):
        assert params.status.value == "open"
        assert params.q == "rotor"
        assert tenant_id
        return (
            [
                SimpleNamespace(
                    id=opportunity_id,
                    opportunity_title="Rotor Works Expansion",
                    opportunity_from="lead",
                    party_name="11111111-2222-3333-4444-555555555555",
                    party_label="Rotor Works",
                    status="open",
                    sales_stage="qualification",
                    probability=55,
                    expected_closing=date(2026, 5, 31),
                    currency="TWD",
                    opportunity_amount=Decimal("25000.00"),
                    opportunity_owner="alice@sales.test",
                    territory="North",
                    updated_at=updated_at,
                )
            ],
            1,
        )

    monkeypatch.setattr(crm_routes, "list_opportunities", fake_list_opportunities)
    session = FakeAsyncSession()
    prev = setup_session(session)
    try:
        resp = await http_get(
            "/api/v1/crm/opportunities?q=rotor&status=open",
            headers=auth_header("sales"),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["items"][0]["party_label"] == "Rotor Works"
        assert body["total_count"] == 1
    finally:
        teardown_session(prev)


async def test_create_opportunity_returns_validation_errors(monkeypatch) -> None:
    async def fake_create_opportunity(*_args, **_kwargs):
        from common.errors import ValidationError

        raise ValidationError([{"field": "party_name", "message": "Customer party not found."}])

    monkeypatch.setattr(crm_routes, "create_opportunity", fake_create_opportunity)
    session = FakeAsyncSession()
    prev = setup_session(session)
    try:
        resp = await http_post(
            "/api/v1/crm/opportunities",
            {
                "opportunity_title": "Rotor Works Expansion",
                "opportunity_from": "customer",
                "party_name": "99999999-8888-7777-6666-555555555555",
                "items": [],
            },
            headers=auth_header("sales"),
        )
        assert resp.status_code == 422
        assert resp.json()["detail"][0]["field"] == "party_name"
    finally:
        teardown_session(prev)


async def test_handoff_to_quotation_returns_context(monkeypatch) -> None:
    opportunity_id = uuid.uuid4()

    async def fake_handoff(_session: FakeAsyncSession, requested_opportunity_id: uuid.UUID, tenant_id: uuid.UUID):
        assert requested_opportunity_id == opportunity_id
        assert tenant_id
        return OpportunityQuotationHandoff(
            opportunity_id=opportunity_id,
            opportunity_title="Rotor Works Expansion",
            opportunity_from="lead",
            party_name="11111111-2222-3333-4444-555555555555",
            party_label="Rotor Works",
            customer_group="Industrial",
            currency="TWD",
            opportunity_amount="25000.00",
            base_opportunity_amount="25000.00",
            territory="North",
            contact_person="Amy Chen",
            contact_email="amy@rotor.example",
            contact_mobile="0912-000-111",
            job_title="Procurement Manager",
            utm_source="expo",
            utm_medium="field",
            utm_campaign="spring-2026",
            utm_content="booth-a3",
            items=[
                {
                    "line_no": 1,
                    "item_name": "Rotor Assembly",
                    "item_code": "",
                    "description": "24V industrial rotor",
                    "quantity": "2.00",
                    "unit_price": "12500.00",
                    "amount": "25000.00",
                }
            ],
        )

    monkeypatch.setattr(crm_routes, "prepare_opportunity_quotation_handoff", fake_handoff)
    session = FakeAsyncSession()
    prev = setup_session(session)
    try:
        resp = await http_post(
            f"/api/v1/crm/opportunities/{opportunity_id}/handoff/quotation",
            {},
            headers=auth_header("sales"),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["currency"] == "TWD"
        assert body["items"][0]["item_name"] == "Rotor Assembly"
    finally:
        teardown_session(prev)