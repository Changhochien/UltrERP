"""Tests for purchase supplier-invoice API endpoints."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from httpx import ASGITransport, AsyncClient

from app.main import app
from common.database import get_db
from tests.domains.orders._helpers import auth_header


class _FakeEnum:
    def __init__(self, value: str):
        self.value = value


class FakeSupplierInvoiceLine:
    def __init__(
        self,
        *,
        product_id: uuid.UUID | None = None,
        line_number: int = 1,
    ):
        self.id = uuid.uuid4()
        self.tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        self.supplier_invoice_id = uuid.uuid4()
        self.line_number = line_number
        self.product_id = product_id
        self.product_code_snapshot = "P-100"
        self.description = "Widget"
        self.quantity = Decimal("2.000")
        self.unit_price = Decimal("50.00")
        self.subtotal_amount = Decimal("100.00")
        self.tax_type = 1
        self.tax_rate = Decimal("0.0500")
        self.tax_amount = Decimal("5.00")
        self.total_amount = Decimal("105.00")
        self.created_at = datetime.now(tz=UTC)


class FakeSupplierInvoice:
    def __init__(
        self,
        *,
        supplier_id: uuid.UUID | None = None,
        status: str = "open",
        lines: list[FakeSupplierInvoiceLine] | None = None,
    ):
        self.id = uuid.uuid4()
        self.tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        self.supplier_id = supplier_id or uuid.uuid4()
        self.invoice_number = "PI-2025001"
        self.invoice_date = date(2025, 3, 15)
        self.currency_code = "TWD"
        self.subtotal_amount = Decimal("100.00")
        self.tax_amount = Decimal("5.00")
        self.total_amount = Decimal("105.00")
        self.status = _FakeEnum(status)
        self.notes = "Imported from legacy purchase history"
        self.created_at = datetime.now(tz=UTC)
        self.updated_at = datetime.now(tz=UTC)
        self.lines = lines or []


class FakeResult:
    def __init__(
        self,
        *,
        obj: object | None = None,
        scalars: list[object] | None = None,
        rows: list[tuple[object, ...]] | None = None,
        count: int | None = None,
    ):
        self._obj = obj
        self._scalars = scalars
        self._rows = rows
        self._count = count

    def scalar_one_or_none(self) -> object | None:
        return self._obj

    def scalar(self) -> object | None:
        if self._count is not None:
            return self._count
        return self._obj

    def scalars(self) -> "FakeScalarsResult":
        return FakeScalarsResult(self._scalars or [])

    def all(self) -> list[tuple[object, ...]]:
        return list(self._rows or [])


class FakeScalarsResult:
    def __init__(self, items: list[object]):
        self._items = items

    def unique(self) -> "FakeScalarsResult":
        return self

    def all(self) -> list[object]:
        return list(self._items)


class FakeAsyncSession:
    def __init__(self) -> None:
        self._execute_results: list[FakeResult] = []
        self._execute_index = 0

    def queue_result(self, obj: object | None) -> None:
        self._execute_results.append(FakeResult(obj=obj))

    def queue_scalars(self, items: list[object]) -> None:
        self._execute_results.append(FakeResult(scalars=items))

    def queue_rows(self, rows: list[tuple[object, ...]]) -> None:
        self._execute_results.append(FakeResult(rows=rows))

    def queue_count(self, count: int) -> None:
        self._execute_results.append(FakeResult(count=count))

    async def execute(self, statement: object, params: object = None) -> FakeResult:
        if type(statement).__name__ == "TextClause":
            return FakeResult()
        if self._execute_index < len(self._execute_results):
            result = self._execute_results[self._execute_index]
            self._execute_index += 1
            return result
        return FakeResult()

    def begin(self) -> "FakeAsyncSession":
        return self

    async def __aenter__(self) -> "FakeAsyncSession":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None


_MISSING = object()


def _setup(session: FakeAsyncSession) -> Any:
    async def _override() -> AsyncGenerator[FakeAsyncSession, None]:
        yield session

    previous = app.dependency_overrides.get(get_db, _MISSING)
    app.dependency_overrides[get_db] = _override
    return previous


def _teardown(previous: Any) -> None:
    if previous is _MISSING:
        app.dependency_overrides.pop(get_db, None)
    else:
        app.dependency_overrides[get_db] = previous


async def _get(path: str) -> Any:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", headers=auth_header()) as c:
        return await c.get(path)


async def test_list_supplier_invoices_returns_serialized_items() -> None:
    supplier_id = uuid.uuid4()
    invoice = FakeSupplierInvoice(
        supplier_id=supplier_id,
        lines=[FakeSupplierInvoiceLine(), FakeSupplierInvoiceLine(line_number=2)],
    )
    session = FakeAsyncSession()
    session.queue_count(1)
    session.queue_scalars([invoice])
    session.queue_rows([(supplier_id, "Acme Supply")])
    previous_override = _setup(session)

    try:
        response = await _get("/api/v1/purchases/supplier-invoices?page=1&page_size=20")
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["items"][0]["supplier_name"] == "Acme Supply"
        assert body["items"][0]["line_count"] == 2
        assert body["items"][0]["status"] == "open"
    finally:
        _teardown(previous_override)


async def test_get_supplier_invoice_returns_detail_with_product_names() -> None:
    supplier_id = uuid.uuid4()
    product_id = uuid.uuid4()
    invoice = FakeSupplierInvoice(
        supplier_id=supplier_id,
        lines=[FakeSupplierInvoiceLine(product_id=product_id)],
    )
    session = FakeAsyncSession()
    session.queue_result(invoice)
    session.queue_rows([(supplier_id, "Acme Supply")])
    session.queue_rows([(product_id, "Widget Pro")])
    previous_override = _setup(session)

    try:
        response = await _get(f"/api/v1/purchases/supplier-invoices/{invoice.id}")
        assert response.status_code == 200
        body = response.json()
        assert body["id"] == str(invoice.id)
        assert body["supplier_name"] == "Acme Supply"
        assert body["lines"][0]["product_name"] == "Widget Pro"
        assert body["lines"][0]["product_code_snapshot"] == "P-100"
    finally:
        _teardown(previous_override)


async def test_get_supplier_invoice_returns_404_when_missing() -> None:
    session = FakeAsyncSession()
    session.queue_result(None)
    previous_override = _setup(session)

    try:
        response = await _get(f"/api/v1/purchases/supplier-invoices/{uuid.uuid4()}")
        assert response.status_code == 404
        assert response.json() == {"detail": "Supplier invoice not found"}
    finally:
        _teardown(previous_override)