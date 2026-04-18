"""Tests for supplier order API endpoints — Story 4.5."""

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

# ── Fake objects ──────────────────────────────────────────────


class FakeSupplier:
    def __init__(
        self,
        *,
        name: str = "TestSupplier",
        tenant_id: uuid.UUID = uuid.UUID("00000000-0000-0000-0000-000000000001"),
    ):
        self.id = uuid.uuid4()
        self.tenant_id = tenant_id
        self.name = name
        self.contact_email = "supplier@example.com"
        self.phone = "555-0100"
        self.address = "123 Supply St"
        self.default_lead_time_days = 7
        self.is_active = True
        self.legacy_master_snapshot = {"legacy_code": f"SUP-{name}"}
        self.created_at = datetime.now(tz=UTC)


class FakeSupplierOrderLine:
    def __init__(
        self,
        *,
        order_id: uuid.UUID | None = None,
        product_id: uuid.UUID | None = None,
        warehouse_id: uuid.UUID | None = None,
        quantity_ordered: int = 100,
        unit_price: Decimal | None = None,
        quantity_received: int = 0,
    ):
        self.id = uuid.uuid4()
        self.order_id = order_id or uuid.uuid4()
        self.product_id = product_id or uuid.uuid4()
        self.warehouse_id = warehouse_id or uuid.uuid4()
        self.quantity_ordered = quantity_ordered
        self.unit_price = unit_price
        self.quantity_received = quantity_received
        self.notes = None


class FakeSupplierOrder:
    def __init__(
        self,
        *,
        tenant_id: uuid.UUID = uuid.UUID("00000000-0000-0000-0000-000000000001"),
        supplier_id: uuid.UUID | None = None,
        status_value: str = "pending",
        lines: list[FakeSupplierOrderLine] | None = None,
    ):
        self.id = uuid.uuid4()
        self.tenant_id = tenant_id
        self.supplier_id = supplier_id or uuid.uuid4()
        self.order_number = "PO-20260101-ABCD1234"
        self.status = _FakeEnum(status_value)
        self.order_date = date.today()
        self.expected_arrival_date = None
        self.received_date = None
        self.created_by = "system"
        self.created_at = datetime.now(tz=UTC)
        self.updated_at = datetime.now(tz=UTC)
        self.lines = lines or []


class _FakeEnum:
    """Emulate a SupplierOrderStatus enum value."""

    def __init__(self, val: str):
        self.value = val

    def __eq__(self, other: object) -> bool:
        if hasattr(other, "value"):
            return self.value == other.value
        return self.value == other

    def __hash__(self) -> int:
        return hash(self.value)


class FakeInventoryStock:
    def __init__(
        self,
        *,
        product_id: uuid.UUID | None = None,
        warehouse_id: uuid.UUID | None = None,
        quantity: int = 50,
        reorder_point: int = 10,
    ):
        self.id = uuid.uuid4()
        self.tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        self.product_id = product_id or uuid.uuid4()
        self.warehouse_id = warehouse_id or uuid.uuid4()
        self.quantity = quantity
        self.reorder_point = reorder_point
        self.updated_at = datetime.now(tz=UTC)


class FakeResult:
    def __init__(
        self, obj: object | None = None, *, items: list | None = None, count: int | None = None
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


class FakeScalarsResult:
    """Returned by result.scalars() for list queries."""

    def __init__(self, objs: list[object]):
        self._objs = objs

    def all(self) -> list[object]:
        return list(self._objs)

    def unique(self) -> FakeScalarsResult:
        return self


class FakeAsyncSession:
    def __init__(self) -> None:
        self._execute_results: list[object] = []
        self._idx = 0
        self.added: list[object] = []
        self._objects: dict[type, dict[uuid.UUID, object]] = {}

    def add(self, obj: object) -> None:
        self.added.append(obj)

    def add_all(self, objs: list[object]) -> None:
        self.added.extend(objs)

    async def execute(self, _stmt: object) -> object:
        if self._idx < len(self._execute_results):
            result = self._execute_results[self._idx]
            self._idx += 1
            return result
        return FakeResult()

    def get(self, model: type, ident: uuid.UUID) -> object | None:
        """Return a pre-seeded object by type and id, or None."""
        return self._objects.get(model, {}).get(ident)

    def seed(self, model: type, ident: uuid.UUID, obj: object) -> None:
        """Store a pre-seeded object for retrieval via get()."""
        if model not in self._objects:
            self._objects[model] = {}
        self._objects[model][ident] = obj

    async def flush(self) -> None:
        pass

    async def commit(self) -> None:
        pass

    async def refresh(self, obj: object) -> None:
        pass

    async def close(self) -> None:
        pass

    def queue_scalar(self, obj: object | None) -> None:
        self._execute_results.append(FakeResult(obj=obj))

    def queue_scalars(self, objs: list[object]) -> None:
        self._execute_results.append(FakeResult(items=objs))

    def queue_count(self, value: int) -> None:
        self._execute_results.append(FakeResult(count=value))


# ── Helper ────────────────────────────────────────────────────

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


async def _post(path: str, json: dict) -> Any:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", headers=auth_header()) as c:
        return await c.post(path, json=json)


async def _get(path: str) -> Any:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", headers=auth_header()) as c:
        return await c.get(path)


async def _put(path: str, json: dict | None = None) -> Any:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", headers=auth_header()) as c:
        return await c.put(path, json=json or {})


# ── Supplier list tests ──────────────────────────────────────


async def test_list_suppliers() -> None:
    s1 = FakeSupplier(name="Acme Corp")
    s2 = FakeSupplier(name="Beta Supply")

    session = FakeAsyncSession()
    session.queue_scalars([s1, s2])

    prev = _setup(session)
    try:
        resp = await _get("/api/v1/inventory/suppliers")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
        assert body["items"][0]["name"] == "Acme Corp"
        assert body["items"][1]["name"] == "Beta Supply"
        assert body["items"][0]["legacy_master_snapshot"]["legacy_code"] == "SUP-Acme Corp"
    finally:
        _teardown(prev)


async def test_list_suppliers_empty() -> None:
    session = FakeAsyncSession()
    session.queue_scalars([])

    prev = _setup(session)
    try:
        resp = await _get("/api/v1/inventory/suppliers")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 0
        assert body["items"] == []
    finally:
        _teardown(prev)


# ── Supplier order creation tests ─────────────────────────────


async def test_create_supplier_order_success() -> None:
    supplier_id = uuid.uuid4()
    product_id = uuid.uuid4()
    warehouse_id = uuid.uuid4()
    order_id = uuid.uuid4()

    order_line = FakeSupplierOrderLine(
        order_id=order_id,
        product_id=product_id,
        warehouse_id=warehouse_id,
        quantity_ordered=50,
        unit_price=Decimal("48.50"),
    )
    order = FakeSupplierOrder(
        supplier_id=supplier_id,
        lines=[order_line],
    )
    order.id = order_id

    session = FakeAsyncSession()
    # create_supplier_order calls:
    # 1. flush (order)
    # 2. flush (lines)
    # 3. flush (audit)
    # 4. _serialize_order -> selectinload query + supplier name query
    session.queue_scalar(order)  # _serialize_order fetches order
    session.queue_scalar("TestSupplier")  # _serialize_order fetches supplier name

    prev = _setup(session)
    try:
        resp = await _post(
            "/api/v1/inventory/supplier-orders",
            json={
                "supplier_id": str(supplier_id),
                "order_date": str(date.today()),
                "lines": [
                    {
                        "product_id": str(product_id),
                        "warehouse_id": str(warehouse_id),
                        "quantity_ordered": 50,
                        "unit_price": 48.5,
                    },
                ],
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["supplier_id"] == str(supplier_id)
        assert body["supplier_name"] == "TestSupplier"
        assert body["status"] == "pending"
        assert len(body["lines"]) == 1
        assert body["lines"][0]["quantity_ordered"] == 50
        assert body["lines"][0]["unit_price"] == "48.50"
    finally:
        _teardown(prev)


async def test_create_supplier_order_empty_lines_rejected() -> None:
    resp = await _post(
        "/api/v1/inventory/supplier-orders",
        json={
            "supplier_id": str(uuid.uuid4()),
            "order_date": str(date.today()),
            "lines": [],
        },
    )
    assert resp.status_code == 422


async def test_create_supplier_order_negative_quantity_rejected() -> None:
    resp = await _post(
        "/api/v1/inventory/supplier-orders",
        json={
            "supplier_id": str(uuid.uuid4()),
            "order_date": str(date.today()),
            "lines": [
                {
                    "product_id": str(uuid.uuid4()),
                    "warehouse_id": str(uuid.uuid4()),
                    "quantity_ordered": -5,
                },
            ],
        },
    )
    assert resp.status_code == 422


# ── Supplier order list tests ─────────────────────────────────


async def test_list_supplier_orders() -> None:
    line = FakeSupplierOrderLine()
    order = FakeSupplierOrder(lines=[line])

    session = FakeAsyncSession()
    session.queue_count(1)  # count query
    session.queue_scalars([order])  # list query
    session.queue_scalars([(order.supplier_id, "TestSupplier")])  # batch supplier names

    prev = _setup(session)
    try:
        resp = await _get("/api/v1/inventory/supplier-orders")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["items"][0]["order_number"] == "PO-20260101-ABCD1234"
        assert body["items"][0]["line_count"] == 1
    finally:
        _teardown(prev)


async def test_list_supplier_orders_empty() -> None:
    session = FakeAsyncSession()
    session.queue_count(0)
    session.queue_scalars([])

    prev = _setup(session)
    try:
        resp = await _get("/api/v1/inventory/supplier-orders")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 0
        assert body["items"] == []
    finally:
        _teardown(prev)


# ── Supplier order detail tests ───────────────────────────────


async def test_get_supplier_order_success() -> None:
    line = FakeSupplierOrderLine(quantity_ordered=100, quantity_received=30)
    order = FakeSupplierOrder(lines=[line])

    session = FakeAsyncSession()
    session.queue_scalar(order)  # _serialize_order
    session.queue_scalar("TestSupplier")  # _serialize_order supplier name

    prev = _setup(session)
    try:
        resp = await _get(f"/api/v1/inventory/supplier-orders/{order.id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == str(order.id)
        assert body["lines"][0]["quantity_ordered"] == 100
        assert body["lines"][0]["quantity_received"] == 30
    finally:
        _teardown(prev)


async def test_get_supplier_order_not_found() -> None:
    session = FakeAsyncSession()
    session.queue_scalar(None)  # _serialize_order returns None (no supplier query)

    prev = _setup(session)
    try:
        resp = await _get(f"/api/v1/inventory/supplier-orders/{uuid.uuid4()}")
        assert resp.status_code == 404
    finally:
        _teardown(prev)


# ── Status update tests ──────────────────────────────────────


async def test_update_status_confirmed() -> None:
    order = FakeSupplierOrder(status_value="pending")

    session = FakeAsyncSession()
    session.queue_scalar(order)  # with_for_update select
    # Service modifies order.status in-place, then _serialize_order re-fetches:
    session.queue_scalar(order)
    session.queue_scalar("TestSupplier")  # _serialize_order supplier name

    prev = _setup(session)
    try:
        resp = await _put(
            f"/api/v1/inventory/supplier-orders/{order.id}/status",
            json={"status": "confirmed"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "confirmed"
    finally:
        _teardown(prev)


async def test_update_status_not_found() -> None:
    session = FakeAsyncSession()
    session.queue_scalar(None)

    prev = _setup(session)
    try:
        resp = await _put(
            f"/api/v1/inventory/supplier-orders/{uuid.uuid4()}/status",
            json={"status": "confirmed"},
        )
        assert resp.status_code == 404
    finally:
        _teardown(prev)


async def test_update_status_invalid_value() -> None:
    resp = await _put(
        f"/api/v1/inventory/supplier-orders/{uuid.uuid4()}/status",
        json={"status": "invalid_status"},
    )
    assert resp.status_code == 422


async def test_update_status_invalid_transition() -> None:
    """Cannot transition backwards (e.g., received → pending)."""
    order = FakeSupplierOrder(status_value="received")

    session = FakeAsyncSession()
    session.queue_scalar(order)  # with_for_update select

    prev = _setup(session)
    try:
        resp = await _put(
            f"/api/v1/inventory/supplier-orders/{order.id}/status",
            json={"status": "pending"},
        )
        assert resp.status_code == 422
        body = resp.json()
        assert "cannot transition" in body["detail"].lower()
    finally:
        _teardown(prev)


# ── Receive order tests ──────────────────────────────────────


async def test_receive_order_full() -> None:
    product_id = uuid.uuid4()
    warehouse_id = uuid.uuid4()
    line = FakeSupplierOrderLine(
        product_id=product_id,
        warehouse_id=warehouse_id,
        quantity_ordered=100,
        quantity_received=0,
    )
    order = FakeSupplierOrder(status_value="shipped", lines=[line])
    stock = FakeInventoryStock(
        product_id=product_id,
        warehouse_id=warehouse_id,
        quantity=20,
        reorder_point=10,
    )

    session = FakeAsyncSession()
    # receive_supplier_order makes 2 queries (order, stock).
    # Then _serialize_order makes 2 queries (order, supplier name).
    session.queue_scalar(order)  # 1. receive_supplier_order: lock & fetch order with lines
    session.queue_scalar(stock)  # 2. receive_supplier_order: lock inventory stock
    session.queue_scalar(order)  # 3. _serialize_order: re-fetch order
    session.queue_scalar("TestSupplier")  # 4. _serialize_order: supplier name

    prev = _setup(session)
    try:
        resp = await _put(
            f"/api/v1/inventory/supplier-orders/{order.id}/receive",
            json={},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "received"
        assert body["lines"][0]["quantity_received"] == 100
        # Stock should have been incremented
        assert stock.quantity == 120  # 20 + 100
    finally:
        _teardown(prev)


async def test_receive_order_partial() -> None:
    product_id = uuid.uuid4()
    warehouse_id = uuid.uuid4()
    line = FakeSupplierOrderLine(
        product_id=product_id,
        warehouse_id=warehouse_id,
        quantity_ordered=100,
        quantity_received=0,
    )
    order = FakeSupplierOrder(status_value="shipped", lines=[line])
    stock = FakeInventoryStock(
        product_id=product_id,
        warehouse_id=warehouse_id,
        quantity=10,
    )

    session = FakeAsyncSession()
    session.queue_scalar(order)  # 1. receive_supplier_order: lock & fetch order
    session.queue_scalar(stock)  # 2. receive_supplier_order: lock inventory stock
    session.queue_scalar(order)  # 3. _serialize_order: re-fetch order
    session.queue_scalar("TestSupplier")  # 4. _serialize_order: supplier name

    prev = _setup(session)
    try:
        resp = await _put(
            f"/api/v1/inventory/supplier-orders/{order.id}/receive",
            json={
                "received_quantities": {str(line.id): 40},
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "partially_received"
        assert body["lines"][0]["quantity_received"] == 40
        assert stock.quantity == 50  # 10 + 40
    finally:
        _teardown(prev)


async def test_receive_order_idempotent_already_received() -> None:
    """Receiving an already-received order returns current state without error."""
    order = FakeSupplierOrder(status_value="received")

    session = FakeAsyncSession()
    session.queue_scalar(order)  # Lock & fetch order
    session.queue_scalar(order)  # _serialize_order (idempotent return)
    session.queue_scalar("TestSupplier")  # _serialize_order supplier name

    prev = _setup(session)
    try:
        resp = await _put(
            f"/api/v1/inventory/supplier-orders/{order.id}/receive",
            json={},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "received"
    finally:
        _teardown(prev)


async def test_receive_order_not_found() -> None:
    session = FakeAsyncSession()
    session.queue_scalar(None)

    prev = _setup(session)
    try:
        resp = await _put(
            f"/api/v1/inventory/supplier-orders/{uuid.uuid4()}/receive",
            json={},
        )
        assert resp.status_code == 404
    finally:
        _teardown(prev)


async def test_receive_order_over_quantity_rejected() -> None:
    product_id = uuid.uuid4()
    warehouse_id = uuid.uuid4()
    line = FakeSupplierOrderLine(
        product_id=product_id,
        warehouse_id=warehouse_id,
        quantity_ordered=50,
        quantity_received=40,
    )
    order = FakeSupplierOrder(status_value="shipped", lines=[line])

    session = FakeAsyncSession()
    session.queue_scalar(order)

    prev = _setup(session)
    try:
        resp = await _put(
            f"/api/v1/inventory/supplier-orders/{order.id}/receive",
            json={
                "received_quantities": {str(line.id): 20},
            },
        )
        assert resp.status_code == 422
        body = resp.json()
        assert "remaining" in body["detail"].lower()
    finally:
        _teardown(prev)


async def test_receive_cancelled_order_rejected() -> None:
    order = FakeSupplierOrder(status_value="cancelled")

    session = FakeAsyncSession()
    session.queue_scalar(order)

    prev = _setup(session)
    try:
        resp = await _put(
            f"/api/v1/inventory/supplier-orders/{order.id}/receive",
            json={},
        )
        assert resp.status_code == 422
        body = resp.json()
        assert "cancelled" in body["detail"].lower()
    finally:
        _teardown(prev)
