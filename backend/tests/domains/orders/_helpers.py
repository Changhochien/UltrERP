"""Shared test fakes and utilities for order domain tests."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator, Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import jwt
from httpx import ASGITransport, AsyncClient

from app.main import app
from common.config import settings
from common.database import get_db


def _resolve_test_jwt_secret() -> str:
    try:
        return str(settings.jwt_secret)
    except Exception:
        return "test-secret-at-least-32-characters-long"


TEST_JWT_SECRET = _resolve_test_jwt_secret()


def make_test_token(
    role: str = "owner",
    user_id: str = "00000000-0000-0000-0000-000000000111",
    tenant_id: str = "00000000-0000-0000-0000-000000000001",
) -> str:
    """Create a valid JWT for testing."""
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "role": role,
        "exp": datetime.now(tz=UTC) + timedelta(hours=8),
    }
    return jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")


def auth_header(role: str = "owner") -> dict[str, str]:
    """Return Authorization header dict with a valid Bearer token."""
    return {"Authorization": f"Bearer {make_test_token(role=role)}"}


# ── Fake domain objects ───────────────────────────────────────


class FakeCustomer:
    def __init__(
        self,
        *,
        tenant_id: uuid.UUID = uuid.UUID("00000000-0000-0000-0000-000000000001"),
        default_discount_percent: Decimal = Decimal("0.0000"),
    ):
        self.id = uuid.uuid4()
        self.tenant_id = tenant_id
        self.company_name = "Test Corp"
        self.normalized_business_number = "12345678"
        self.billing_address = "123 Main St"
        self.contact_name = "John Doe"
        self.contact_phone = "0912345678"
        self.contact_email = "john@test.com"
        self.credit_limit = Decimal("100000.00")
        self.default_discount_percent = default_discount_percent
        self.status = "active"
        self.version = 1
        self.created_at = datetime.now(tz=UTC)
        self.updated_at = datetime.now(tz=UTC)


class FakeProduct:
    def __init__(self, *, product_id: uuid.UUID | None = None):
        self.id = product_id or uuid.uuid4()


class FakeOrderLine:
    def __init__(
        self,
        *,
        order_id: uuid.UUID | None = None,
        product_id: uuid.UUID | None = None,
        source_quotation_line_no: int | None = None,
        line_number: int = 1,
        unit_cost: Decimal | None = None,
        available_stock_snapshot: int | None = None,
        backorder_note: str | None = None,
        description: str = "Test product",
        product_name_snapshot: str | None = None,
        product_category_snapshot: str | None = None,
    ):
        self.id = uuid.uuid4()
        self.tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        self.order_id = order_id or uuid.uuid4()
        self.product_id = product_id or uuid.uuid4()
        self.source_quotation_line_no = source_quotation_line_no
        self.line_number = line_number
        self.quantity = Decimal("10.000")
        self.list_unit_price = Decimal("100.00")
        self.unit_price = Decimal("100.00")
        self.unit_cost = unit_cost
        self.discount_amount = Decimal("0.00")
        self.tax_policy_code = "standard"
        self.tax_type = 1
        self.tax_rate = Decimal("0.0500")
        self.tax_amount = Decimal("50.00")
        self.subtotal_amount = Decimal("1000.00")
        self.total_amount = Decimal("1050.00")
        self.description = description
        self.product_name_snapshot = product_name_snapshot
        self.product_category_snapshot = product_category_snapshot
        self.available_stock_snapshot = available_stock_snapshot
        self.backorder_note = backorder_note
        self.created_at = datetime.now(tz=UTC)


class FakeOrder:
    def __init__(
        self,
        *,
        tenant_id: uuid.UUID = uuid.UUID("00000000-0000-0000-0000-000000000001"),
        customer_id: uuid.UUID | None = None,
        source_quotation_id: uuid.UUID | None = None,
        status: str = "pending",
        lines: list[FakeOrderLine] | None = None,
        invoice_id: uuid.UUID | None = None,
        customer: FakeCustomer | None = None,
        sales_team: list[dict[str, str]] | None = None,
        total_commission: Decimal = Decimal("0.00"),
        crm_context_snapshot: dict[str, object] | None = None,
    ):
        self.id = uuid.uuid4()
        self.tenant_id = tenant_id
        self.customer_id = customer_id or uuid.uuid4()
        self.source_quotation_id = source_quotation_id
        self.order_number = "ORD-20260401-ABCD1234"
        self.status = status
        self.payment_terms_code = "NET_30"
        self.payment_terms_days = 30
        self.subtotal_amount = Decimal("1000.00")
        self.discount_amount = Decimal("0.00")
        self.discount_percent = Decimal("0.00")
        self.tax_amount = Decimal("50.00")
        self.total_amount = Decimal("1050.00")
        self.invoice_id = invoice_id
        self.sales_team = sales_team
        self.total_commission = total_commission
        self.notes = None
        self.crm_context_snapshot = crm_context_snapshot
        self.created_by = "00000000-0000-0000-0000-000000000001"
        self.created_at = datetime.now(tz=UTC)
        self.updated_at = datetime.now(tz=UTC)
        self.confirmed_at = datetime.now(tz=UTC) if status != "pending" else None
        self.lines = lines if lines is not None else [FakeOrderLine()]
        self.customer = customer


class FakeInvoiceNumberRange:
    def __init__(self):
        self.id = uuid.uuid4()
        self.tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        self.prefix = "AA"
        self.start_number = 1
        self.end_number = 99999999
        self.next_number = 1
        self.is_active = True
        self.created_at = datetime.now(tz=UTC)
        self.updated_at = datetime.now(tz=UTC)


class FakeWarehouseRow:
    """Represents a joined (InventoryStock + Warehouse) row."""

    def __init__(self, warehouse_id: uuid.UUID, warehouse_name: str, quantity: int):
        self.warehouse_id = warehouse_id
        self.warehouse_name = warehouse_name
        self.quantity = quantity


class FakeInventoryStock:
    """Fake inventory stock row for stock adjustment queries."""

    def __init__(
        self,
        *,
        tenant_id: uuid.UUID = uuid.UUID("00000000-0000-0000-0000-000000000001"),
        product_id: uuid.UUID | None = None,
        warehouse_id: uuid.UUID | None = None,
        quantity: int = 100,
    ):
        self.tenant_id = tenant_id
        self.product_id = product_id or uuid.uuid4()
        self.warehouse_id = warehouse_id or uuid.uuid4()
        self.quantity = quantity
        self.reorder_point = 10


# ── Fake session infrastructure ───────────────────────────────


class FakeResult:
    def __init__(
        self,
        obj: object | None = None,
        *,
        items: list | None = None,
        count: int | None = None,
    ):
        self._obj = obj
        self._items = items
        self._count = count

    def scalar_one_or_none(self) -> object | None:
        return self._obj

    def scalar(self) -> object | None:
        if self._count is not None:
            return self._count
        return self._obj

    def scalars(self) -> FakeScalarsResult:
        return FakeScalarsResult(self._items if self._items is not None else [])

    def all(self) -> list:
        return list(self._items) if self._items is not None else []

    def first(self) -> object | None:
        if self._items is not None:
            return self._items[0] if self._items else None
        return self._obj


class FakeScalarsResult:
    def __init__(self, objs: list[object]):
        self._objs = objs

    def all(self) -> list[object]:
        return list(self._objs)

    def unique(self) -> FakeScalarsResult:
        return self


class _FakeBegin:
    def __init__(self, session: FakeAsyncSession) -> None:
        self._session = session
        self._added_start = 0

    async def __aenter__(self) -> None:
        self._added_start = len(self._session.added)
        self._session._transaction_depth += 1
        return None

    async def __aexit__(self, exc_type: object, *_args: object) -> bool:
        self._session._transaction_depth = max(self._session._transaction_depth - 1, 0)
        if exc_type is not None:
            del self._session.added[self._added_start :]
        return False


class FakeAsyncSession:
    def __init__(self) -> None:
        self._execute_results: list[object] = []
        self._idx = 0
        self._transaction_depth = 0
        self.added: list[object] = []
        self.executed_statements: list[tuple[object, object | None]] = []

    def add(self, obj: object) -> None:
        self.added.append(obj)

    def add_all(self, objs: list[object]) -> None:
        self.added.extend(objs)

    async def execute(self, _stmt: object, _params: object = None) -> object:
        self.executed_statements.append((_stmt, _params))
        if self._idx < len(self._execute_results):
            result = self._execute_results[self._idx]
            self._idx += 1
            return result
        return FakeResult()

    async def flush(self) -> None:
        for obj in self.added:
            if getattr(obj, "id", None) is None:
                setattr(obj, "id", uuid.uuid4())

    async def commit(self) -> None:
        pass

    async def refresh(self, obj: object) -> None:
        pass

    async def delete(self, obj: object) -> None:
        """Fake delete — no-op for test isolation."""
        pass

    def begin(self) -> _FakeBegin:
        return _FakeBegin(self)

    def in_transaction(self) -> bool:
        return self._transaction_depth > 0

    def queue_scalar(self, obj: object | None) -> None:
        self._execute_results.append(FakeResult(obj=obj))

    def queue_scalars(self, objs: Sequence[object]) -> None:
        self._execute_results.append(FakeResult(items=list(objs)))

    def queue_count(self, value: int) -> None:
        self._execute_results.append(FakeResult(count=value))

    def queue_rows(self, rows: Sequence[object]) -> None:
        """Queue result that returns rows via .all()."""
        self._execute_results.append(FakeResult(items=list(rows)))

    def queue_result(self, items: Sequence[object]) -> None:
        """Queue result that returns items via .scalars().all()."""
        self._execute_results.append(FakeResult(items=list(items)))


# ── Setup / teardown ─────────────────────────────────────────

_MISSING = object()


def setup_session(session: FakeAsyncSession) -> Any:
    async def _override() -> AsyncGenerator[FakeAsyncSession, None]:
        yield session

    previous = app.dependency_overrides.get(get_db, _MISSING)
    app.dependency_overrides[get_db] = _override
    return previous


def teardown_session(previous: Any) -> None:
    if previous is _MISSING:
        app.dependency_overrides.pop(get_db, None)
    else:
        app.dependency_overrides[get_db] = previous


# ── HTTP helpers ──────────────────────────────────────────────

_DEFAULT_HEADERS = auth_header("owner")


async def http_get(path: str, *, headers: dict | None = None) -> Any:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        return await c.get(path, headers=headers or _DEFAULT_HEADERS)


async def http_post(path: str, json: dict, *, headers: dict | None = None) -> Any:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        return await c.post(path, json=json, headers=headers or _DEFAULT_HEADERS)


async def http_patch(path: str, json: dict, *, headers: dict | None = None) -> Any:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        return await c.patch(path, json=json, headers=headers or _DEFAULT_HEADERS)


async def http_delete(path: str, *, headers: dict | None = None) -> Any:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        return await c.delete(path, headers=headers or _DEFAULT_HEADERS)
