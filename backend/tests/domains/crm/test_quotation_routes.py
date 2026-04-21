"""Focused CRM quotation route tests."""

from __future__ import annotations

import sys
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from domains.crm import routes as crm_routes
from domains.crm.schemas import QuotationOrderHandoff, QuotationOrderHandoffLine

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tests.domains.orders._helpers import (  # noqa: E402
    FakeAsyncSession,
    auth_header,
    http_get,
    http_post,
    setup_session,
    teardown_session,
)


def _quotation_namespace(
    quotation_id: uuid.UUID,
    *,
    status: str = "open",
    amended_from: uuid.UUID | None = None,
    revision_no: int = 0,
) -> SimpleNamespace:
    now = datetime.now(tz=UTC)
    return SimpleNamespace(
        id=quotation_id,
        tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        quotation_to="lead",
        party_name="11111111-2222-3333-4444-555555555555",
        party_label="Rotor Works",
        status=status,
        transaction_date=date(2026, 4, 21),
        valid_till=date(2026, 5, 21),
        company="UltrERP Taiwan",
        currency="TWD",
        subtotal=Decimal("25000.00"),
        total_taxes=Decimal("1250.00"),
        grand_total=Decimal("26250.00"),
        base_grand_total=Decimal("26250.00"),
        ordered_amount=Decimal("0.00"),
        order_count=0,
        contact_person="Amy Chen",
        contact_email="amy@rotor.example",
        contact_mobile="0912-000-111",
        job_title="Procurement Manager",
        territory="North",
        customer_group="Industrial",
        billing_address="No. 1, Zhongshan Rd, Taipei",
        shipping_address="Warehouse 7, Taoyuan",
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
        taxes=[
            {
                "line_no": 1,
                "description": "VAT",
                "rate": "5.00",
                "tax_amount": "1250.00",
            }
        ],
        terms_template="standard-sales",
        terms_and_conditions="Net 30 days.",
        opportunity_id=uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"),
        amended_from=amended_from,
        revision_no=revision_no,
        lost_reason="",
        competitor_name="",
        loss_notes="",
        auto_repeat_enabled=True,
        auto_repeat_frequency="monthly",
        auto_repeat_until=date(2026, 12, 31),
        notes="Initial commercial offer.",
        version=1,
        created_at=now,
        updated_at=now,
    )


async def test_list_quotations_allows_sales_role(monkeypatch) -> None:
    quotation_id = uuid.uuid4()

    async def fake_list_quotations(_session: FakeAsyncSession, params, tenant_id: uuid.UUID):
        assert params.status.value == "open"
        assert params.q == "rotor"
        assert tenant_id
        return ([_quotation_namespace(quotation_id)], 1)

    monkeypatch.setattr(crm_routes, "list_quotations", fake_list_quotations)
    session = FakeAsyncSession()
    prev = setup_session(session)
    try:
        resp = await http_get(
            "/api/v1/crm/quotations?q=rotor&status=open",
            headers=auth_header("sales"),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["items"][0]["party_label"] == "Rotor Works"
        assert body["items"][0]["grand_total"] == "26250.00"
    finally:
        teardown_session(prev)


async def test_create_quotation_returns_validation_errors(monkeypatch) -> None:
    async def fake_create_quotation(*_args, **_kwargs):
        from common.errors import ValidationError

        raise ValidationError([{"field": "items", "message": "At least one quotation item is required."}])

    monkeypatch.setattr(crm_routes, "create_quotation", fake_create_quotation)
    session = FakeAsyncSession()
    prev = setup_session(session)
    try:
        resp = await http_post(
            "/api/v1/crm/quotations",
            {
                "quotation_to": "lead",
                "party_name": "11111111-2222-3333-4444-555555555555",
                "transaction_date": "2026-04-21",
                "valid_till": "2026-05-21",
                "company": "UltrERP Taiwan",
                "items": [],
            },
            headers=auth_header("sales"),
        )
        assert resp.status_code == 422
        assert resp.json()["detail"][0]["field"] == "items"
    finally:
        teardown_session(prev)


async def test_revise_quotation_returns_revision_lineage(monkeypatch) -> None:
    source_id = uuid.uuid4()
    revised_id = uuid.uuid4()

    async def fake_revise(_session: FakeAsyncSession, requested_id: uuid.UUID, data, tenant_id: uuid.UUID):
        assert requested_id == source_id
        assert data.valid_till == date(2026, 6, 15)
        assert tenant_id
        return _quotation_namespace(revised_id, status="draft", amended_from=source_id, revision_no=1)

    monkeypatch.setattr(crm_routes, "create_quotation_revision", fake_revise)
    session = FakeAsyncSession()
    prev = setup_session(session)
    try:
        resp = await http_post(
            f"/api/v1/crm/quotations/{source_id}/revise",
            {
                "valid_till": "2026-06-15",
                "notes": "Reissued with updated validity.",
            },
            headers=auth_header("sales"),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["status"] == "draft"
        assert body["amended_from"] == str(source_id)
        assert body["revision_no"] == 1
    finally:
        teardown_session(prev)


async def test_handoff_quotation_to_order_returns_prefill_context(monkeypatch) -> None:
    quotation_id = uuid.uuid4()
    customer_id = uuid.uuid4()

    async def fake_handoff(_session: FakeAsyncSession, requested_id: uuid.UUID, tenant_id: uuid.UUID):
        assert requested_id == quotation_id
        assert tenant_id
        return QuotationOrderHandoff(
            quotation_id=quotation_id,
            source_quotation_id=quotation_id,
            customer_id=customer_id,
            crm_context_snapshot={
                "source_document_type": "quotation",
                "party_label": "Rotor Works",
            },
            notes="Initial commercial offer.",
            lines=[
                QuotationOrderHandoffLine(
                    source_quotation_line_no=1,
                    product_id=uuid.uuid4(),
                    description="24V industrial rotor",
                    quantity=Decimal("2.00"),
                    list_unit_price=Decimal("12500.00"),
                    unit_price=Decimal("12500.00"),
                    discount_amount=Decimal("0.00"),
                    tax_policy_code="standard",
                )
            ],
        )

    monkeypatch.setattr(crm_routes, "prepare_quotation_order_handoff", fake_handoff)
    session = FakeAsyncSession()
    prev = setup_session(session)
    try:
        resp = await http_post(
            f"/api/v1/crm/quotations/{quotation_id}/handoff/order",
            {},
            headers=auth_header("sales"),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["source_quotation_id"] == str(quotation_id)
        assert body["customer_id"] == str(customer_id)
        assert body["crm_context_snapshot"]["party_label"] == "Rotor Works"
        assert body["lines"][0]["source_quotation_line_no"] == 1
    finally:
        teardown_session(prev)