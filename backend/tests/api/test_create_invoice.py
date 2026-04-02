"""API tests for POST /api/v1/invoices."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

from httpx import ASGITransport, AsyncClient

from app.main import app
from common.database import get_db
from domains.customers.models import Customer
from domains.invoices.models import InvoiceNumberRange
from domains.invoices.validators import IMMUTABLE_ERROR


class FakeResult:
    def __init__(self, obj: object | None = None) -> None:
        self._obj = obj

    def scalar_one_or_none(self) -> object | None:
        return self._obj


class FakeAsyncSession:
    def __init__(self) -> None:
        self.added: list[Any] = []
        self._execute_results: list[FakeResult] = []
        self._execute_index = 0

    def add(self, instance: object) -> None:
        self.added.append(instance)

    def add_all(self, instances: list[object]) -> None:
        self.added.extend(instances)

    def queue_result(self, obj: object | None) -> None:
        self._execute_results.append(FakeResult(obj))

    async def execute(self, statement: object, params: object = None) -> FakeResult:
        if type(statement).__name__ == "TextClause":
            return FakeResult(None)
        if self._execute_index < len(self._execute_results):
            result = self._execute_results[self._execute_index]
            self._execute_index += 1
            return result
        return FakeResult(None)

    async def flush(self) -> None:
        for obj in self.added:
            if getattr(obj, "id", None) is None:
                obj.id = uuid.uuid4()  # type: ignore[attr-defined]

    async def refresh(self, instance: object) -> None:
        now = datetime.now(tz=UTC)
        if getattr(instance, "created_at", None) is None:
            instance.created_at = now  # type: ignore[attr-defined]
        if getattr(instance, "updated_at", None) is None:
            instance.updated_at = now  # type: ignore[attr-defined]
        for line in getattr(instance, "lines", []):
            if getattr(line, "id", None) is None:
                line.id = uuid.uuid4()  # type: ignore[attr-defined]
            if getattr(line, "created_at", None) is None:
                line.created_at = now  # type: ignore[attr-defined]

    def begin(self) -> FakeAsyncSession:
        return self

    async def __aenter__(self) -> FakeAsyncSession:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None


def _customer(*, business_number: str = "04595257") -> Customer:
    return Customer(
        id=uuid.uuid4(),
        tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        company_name="台灣好公司有限公司",
        normalized_business_number=business_number,
        billing_address="台北市信義區信義路五段7號",
        contact_name="王大明",
        contact_phone="0912-345-678",
        contact_email="wang@example.com",
        credit_limit=Decimal("100000.00"),
    )


def _range(*, next_number: int = 12345678) -> InvoiceNumberRange:
    return InvoiceNumberRange(
        id=uuid.uuid4(),
        tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        prefix="AZ",
        start_number=12345678,
        end_number=12345699,
        next_number=next_number,
        is_active=True,
    )


def _valid_payload(customer_id: uuid.UUID, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "customer_id": str(customer_id),
        "buyer_type": "b2b",
        "buyer_identifier": "04595257",
        "lines": [
            {
                "product_id": str(uuid.uuid4()),
                "product_code": "P-100",
                "description": "測試商品",
                "quantity": "2",
                "unit_price": "100.00",
                "tax_policy_code": "standard",
            }
        ],
    }
    payload.update(overrides)
    return payload


def _invoice_line() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        product_id=uuid.uuid4(),
        product_code_snapshot="P-100",
        description="測試商品",
        quantity=Decimal("2"),
        unit_price=Decimal("100.00"),
        subtotal_amount=Decimal("200.00"),
        tax_type=1,
        tax_rate=Decimal("0.05"),
        tax_amount=Decimal("10.00"),
        total_amount=Decimal("210.00"),
        zero_tax_rate_reason=None,
    )


def _invoice(
    *,
    invoice_id: uuid.UUID | None = None,
    status: str = "issued",
    invoice_date_value: date | None = None,
    voided_at: datetime | None = None,
    void_reason: str | None = None,
) -> SimpleNamespace:
    now = datetime.now(tz=UTC)
    customer = _customer()
    return SimpleNamespace(
        id=invoice_id or uuid.uuid4(),
        tenant_id=customer.tenant_id,
        invoice_number="AZ12345678",
        invoice_date=invoice_date_value or date.today(),
        customer_id=customer.id,
        buyer_type="b2b",
        buyer_identifier_snapshot=customer.normalized_business_number,
        currency_code="TWD",
        subtotal_amount=Decimal("200.00"),
        tax_amount=Decimal("10.00"),
        total_amount=Decimal("210.00"),
        status=status,
        version=1,
        voided_at=voided_at,
        void_reason=void_reason,
        created_at=now,
        updated_at=now,
        lines=[_invoice_line()],
        domain_events=[],
    )


_MISSING_OVERRIDE = object()


def _setup(session: FakeAsyncSession) -> Any:
    async def _override_get_db() -> AsyncGenerator[FakeAsyncSession, None]:
        yield session

    previous_override = app.dependency_overrides.get(get_db, _MISSING_OVERRIDE)
    app.dependency_overrides[get_db] = _override_get_db
    return previous_override


def _teardown(previous_override: Any) -> None:
    if previous_override is _MISSING_OVERRIDE:
        app.dependency_overrides.pop(get_db, None)
        return

    app.dependency_overrides[get_db] = previous_override


async def test_create_invoice_success() -> None:
    customer = _customer()
    session = FakeAsyncSession()
    session.queue_result(customer)
    session.queue_result(_range())
    previous_override = _setup(session)

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(
                "/api/v1/invoices",
                json=_valid_payload(customer.id),
            )

        assert response.status_code == 201
        body = response.json()
        assert body["invoice_number"] == "AZ12345678"
        assert body["buyer_identifier_snapshot"] == "04595257"
        assert body["subtotal_amount"] == "200.00"
        assert body["tax_amount"] == "10.00"
        assert body["total_amount"] == "210.00"
        assert body["lines"][0]["product_code_snapshot"] == "P-100"
    finally:
        _teardown(previous_override)


async def test_create_invoice_b2c_uses_required_sentinel() -> None:
    customer = _customer()
    session = FakeAsyncSession()
    session.queue_result(customer)
    session.queue_result(_range())
    previous_override = _setup(session)

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(
                "/api/v1/invoices",
                json=_valid_payload(
                    customer.id,
                    buyer_type="b2c",
                    buyer_identifier=None,
                ),
            )

        assert response.status_code == 201
        assert response.json()["buyer_identifier_snapshot"] == "0000000000"
    finally:
        _teardown(previous_override)


async def test_create_invoice_unknown_customer_returns_structured_422() -> None:
    session = FakeAsyncSession()
    session.queue_result(None)
    previous_override = _setup(session)

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(
                "/api/v1/invoices",
                json=_valid_payload(uuid.uuid4()),
            )

        assert response.status_code == 422
        assert response.json() == {
            "detail": [{"field": "customer_id", "message": "Customer does not exist."}]
        }
    finally:
        _teardown(previous_override)


async def test_create_invoice_exhausted_range_returns_structured_422() -> None:
    customer = _customer()
    session = FakeAsyncSession()
    session.queue_result(customer)
    session.queue_result(_range(next_number=12345700))
    previous_override = _setup(session)

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(
                "/api/v1/invoices",
                json=_valid_payload(customer.id),
            )

        assert response.status_code == 422
        assert response.json() == {
            "detail": [
                {
                    "field": "invoice_number",
                    "message": "No invoice numbers remain in the active range.",
                }
            ]
        }
    finally:
        _teardown(previous_override)


async def test_get_invoice_returns_404_when_missing() -> None:
    session = FakeAsyncSession()
    session.queue_result(None)
    previous_override = _setup(session)

    try:
        transport = ASGITransport(app=app)
        invoice_id = uuid.uuid4()
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get(f"/api/v1/invoices/{invoice_id}")

        assert response.status_code == 404
        assert response.json() == {"detail": "Invoice not found"}
    finally:
        _teardown(previous_override)


async def test_get_invoice_returns_serialized_invoice() -> None:
    invoice = _invoice()
    session = FakeAsyncSession()
    session.queue_result(invoice)
    previous_override = _setup(session)

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get(f"/api/v1/invoices/{invoice.id}")

        assert response.status_code == 200
        body = response.json()
        assert body["id"] == str(invoice.id)
        assert body["invoice_number"] == invoice.invoice_number
        assert body["lines"][0]["product_code_snapshot"] == "P-100"
    finally:
        _teardown(previous_override)


async def test_void_invoice_success() -> None:
    invoice = _invoice()
    session = FakeAsyncSession()
    session.queue_result(invoice)
    previous_override = _setup(session)

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(
                f"/api/v1/invoices/{invoice.id}/void",
                json={"reason": "Customer requested cancellation"},
            )

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "voided"
        assert body["void_reason"] == "Customer requested cancellation"
        assert body["voided_at"] is not None
    finally:
        _teardown(previous_override)


async def test_void_invoice_rejects_already_voided_invoice() -> None:
    invoice = _invoice(status="voided", voided_at=datetime.now(tz=UTC), void_reason="done")
    session = FakeAsyncSession()
    session.queue_result(invoice)
    previous_override = _setup(session)

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(
                f"/api/v1/invoices/{invoice.id}/void",
                json={"reason": "Try again"},
            )

        assert response.status_code == 422
        assert response.json() == {
            "detail": [
                {"field": "invoice", "message": "Cannot void invoice in status 'voided'"}
            ]
        }
    finally:
        _teardown(previous_override)


async def test_void_invoice_returns_404_when_missing() -> None:
    session = FakeAsyncSession()
    session.queue_result(None)
    previous_override = _setup(session)

    try:
        transport = ASGITransport(app=app)
        invoice_id = uuid.uuid4()
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(
                f"/api/v1/invoices/{invoice_id}/void",
                json={"reason": "Missing invoice"},
            )

        assert response.status_code == 404
        assert response.json() == {"detail": "Invoice not found"}
    finally:
        _teardown(previous_override)


async def test_put_invoice_returns_405_with_immutable_message() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.put(f"/api/v1/invoices/{uuid.uuid4()}")

    assert response.status_code == 405
    assert response.json() == {"detail": IMMUTABLE_ERROR}


async def test_patch_invoice_returns_405_with_immutable_message() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.patch(f"/api/v1/invoices/{uuid.uuid4()}")

    assert response.status_code == 405
    assert response.json() == {"detail": IMMUTABLE_ERROR}