from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import IntegrityError

from app.main import app
from common.database import get_db
from common.models.physical_count_session import PhysicalCountSessionStatus
from domains.inventory.services import (
    PhysicalCountConflictError,
    PhysicalCountNotFoundError,
    approve_physical_count_session,
    create_physical_count_session,
    submit_physical_count_session,
    update_physical_count_line,
)
from tests.domains.orders._helpers import auth_header


class FakeProduct:
    def __init__(self, *, product_id: uuid.UUID | None = None, code: str = "PROD-001", name: str = "Widget"):
        self.id = product_id or uuid.uuid4()
        self.code = code
        self.name = name


class FakeWarehouse:
    def __init__(self, *, warehouse_id: uuid.UUID | None = None, name: str = "Main Warehouse"):
        self.id = warehouse_id or uuid.uuid4()
        self.name = name
        self.tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")


class FakeInventoryStock:
    def __init__(
        self,
        *,
        product_id: uuid.UUID | None = None,
        warehouse_id: uuid.UUID | None = None,
        quantity: int = 10,
        reorder_point: int = 2,
    ):
        self.id = uuid.uuid4()
        self.tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        self.product_id = product_id or uuid.uuid4()
        self.warehouse_id = warehouse_id or uuid.uuid4()
        self.quantity = quantity
        self.reorder_point = reorder_point
        self.updated_at = datetime.now(tz=UTC)


class FakeCountLine:
    def __init__(
        self,
        *,
        line_id: uuid.UUID | None = None,
        product: FakeProduct | None = None,
        system_qty_snapshot: int = 10,
        counted_qty: int | None = None,
        variance_qty: int | None = None,
        notes: str | None = None,
    ):
        self.id = line_id or uuid.uuid4()
        self.product = product or FakeProduct()
        self.product_id = self.product.id
        self.system_qty_snapshot = system_qty_snapshot
        self.counted_qty = counted_qty
        self.variance_qty = variance_qty
        self.notes = notes
        self.created_at = datetime.now(tz=UTC)
        self.updated_at = datetime.now(tz=UTC)


class FakeCountSession:
    def __init__(
        self,
        *,
        session_id: uuid.UUID | None = None,
        tenant_id: uuid.UUID = uuid.UUID("00000000-0000-0000-0000-000000000001"),
        warehouse: FakeWarehouse | None = None,
        lines: list[FakeCountLine] | None = None,
        status: PhysicalCountSessionStatus = PhysicalCountSessionStatus.IN_PROGRESS,
    ):
        self.id = session_id or uuid.uuid4()
        self.tenant_id = tenant_id
        self.warehouse = warehouse or FakeWarehouse()
        self.warehouse_id = self.warehouse.id
        self.lines = lines or []
        self.status = status
        self.created_by = "user-1"
        self.submitted_by = None
        self.submitted_at = None
        self.approved_by = None
        self.approved_at = None
        self.created_at = datetime.now(tz=UTC)
        self.updated_at = datetime.now(tz=UTC)


class FakeResult:
    def __init__(self, obj: object | None = None, *, items: list[object] | None = None, count: int | None = None):
        self._obj = obj
        self._items = items
        self._count = count

    def scalar_one_or_none(self) -> object | None:
        return self._obj

    def scalar(self) -> object | None:
        if self._count is not None:
            return self._count
        return self._obj

    def scalars(self) -> FakeScalars:
        return FakeScalars(self._items if self._items is not None else ([] if self._obj is None else [self._obj]))


class FakeScalars:
    def __init__(self, objs: list[object]):
        self._objs = objs

    def all(self) -> list[object]:
        return list(self._objs)


class FakeAsyncSession:
    def __init__(self) -> None:
        self._execute_results: list[FakeResult] = []
        self._idx = 0
        self.added: list[object] = []
        self.flush_error: Exception | None = None
        self.rollback_calls = 0

    def add(self, obj: object) -> None:
        self.added.append(obj)

    def add_all(self, objs: list[object]) -> None:
        self.added.extend(objs)

    async def execute(self, _stmt: object) -> FakeResult:
        if self._idx < len(self._execute_results):
            result = self._execute_results[self._idx]
            self._idx += 1
            return result
        return FakeResult(None)

    async def flush(self) -> None:
        if self.flush_error is not None:
            error = self.flush_error
            self.flush_error = None
            raise error
        now = datetime.now(tz=UTC)
        for obj in self.added:
            if hasattr(obj, "id") and getattr(obj, "id") is None:
                obj.id = uuid.uuid4()
            if hasattr(obj, "created_at") and getattr(obj, "created_at") is None:
                obj.created_at = now
            if hasattr(obj, "updated_at") and getattr(obj, "updated_at") is None:
                obj.updated_at = now
            if type(obj).__name__ == "PhysicalCountSession" and getattr(obj, "status", None) is None:
                obj.status = PhysicalCountSessionStatus.IN_PROGRESS

    async def commit(self) -> None:
        await self.flush()

    async def rollback(self) -> None:
        self.rollback_calls += 1

    def queue_scalar(self, obj: object | None) -> None:
        self._execute_results.append(FakeResult(obj=obj))

    def queue_scalars(self, objs: list[object]) -> None:
        self._execute_results.append(FakeResult(items=objs))

    def queue_count(self, count: int) -> None:
        self._execute_results.append(FakeResult(count=count))


def _make_detail_session(
    *,
    warehouse_id: uuid.UUID | None = None,
    status: PhysicalCountSessionStatus = PhysicalCountSessionStatus.IN_PROGRESS,
    lines: list[FakeCountLine] | None = None,
) -> FakeCountSession:
    warehouse = FakeWarehouse(warehouse_id=warehouse_id)
    return FakeCountSession(warehouse=warehouse, lines=lines, status=status)


@pytest.mark.asyncio
async def test_create_physical_count_session_prepopulates_snapshot_lines() -> None:
    warehouse_id = uuid.uuid4()
    product_a = FakeProduct(code="P-001", name="Alpha")
    product_b = FakeProduct(code="P-002", name="Beta")
    session = FakeAsyncSession()
    session.queue_scalar(FakeWarehouse(warehouse_id=warehouse_id))
    session.queue_scalar(None)
    session.queue_scalars(
        [
            FakeInventoryStock(product_id=product_a.id, warehouse_id=warehouse_id, quantity=12),
            FakeInventoryStock(product_id=product_b.id, warehouse_id=warehouse_id, quantity=4),
        ]
    )
    session.queue_scalar(
        _make_detail_session(
            warehouse_id=warehouse_id,
            lines=[
                FakeCountLine(product=product_a, system_qty_snapshot=12),
                FakeCountLine(product=product_b, system_qty_snapshot=4),
            ],
        )
    )

    result = await create_physical_count_session(
        session,
        uuid.UUID("00000000-0000-0000-0000-000000000001"),
        warehouse_id=warehouse_id,
        actor_id="user-1",
    )

    assert result["status"] == "in_progress"
    assert result["total_lines"] == 2
    assert [line["system_qty_snapshot"] for line in result["lines"]] == [12, 4]


@pytest.mark.asyncio
async def test_create_physical_count_session_requires_tenant_owned_warehouse() -> None:
    warehouse_id = uuid.uuid4()
    session = FakeAsyncSession()
    session.queue_scalar(None)

    with pytest.raises(PhysicalCountNotFoundError, match="Warehouse not found"):
        await create_physical_count_session(
            session,
            uuid.UUID("00000000-0000-0000-0000-000000000001"),
            warehouse_id=warehouse_id,
            actor_id="user-1",
        )


@pytest.mark.asyncio
async def test_create_physical_count_session_maps_concurrent_open_session_insert_to_conflict() -> None:
    warehouse_id = uuid.uuid4()
    session = FakeAsyncSession()
    session.queue_scalar(FakeWarehouse(warehouse_id=warehouse_id))
    session.queue_scalar(None)
    session.queue_scalars([])
    session.flush_error = IntegrityError("INSERT", {}, Exception("duplicate key"))
    session.queue_scalar(uuid.uuid4())

    with pytest.raises(PhysicalCountConflictError, match="open physical count session"):
        await create_physical_count_session(
            session,
            uuid.UUID("00000000-0000-0000-0000-000000000001"),
            warehouse_id=warehouse_id,
            actor_id="user-1",
        )

    assert session.rollback_calls == 1


@pytest.mark.asyncio
async def test_update_physical_count_line_recomputes_variance() -> None:
    line = FakeCountLine(system_qty_snapshot=10)
    count_session = _make_detail_session(lines=[line])
    session = FakeAsyncSession()
    session.queue_scalar(count_session)

    result = await update_physical_count_line(
        session,
        count_session.tenant_id,
        count_session.id,
        line.id,
        counted_qty=8,
        notes="Shelf recount complete",
    )

    assert line.counted_qty == 8
    assert line.variance_qty == -2
    assert result["lines"][0]["variance_qty"] == -2


@pytest.mark.asyncio
async def test_submit_physical_count_session_locks_editing_and_keeps_variance_summary() -> None:
    line = FakeCountLine(system_qty_snapshot=10, counted_qty=8, variance_qty=-2)
    count_session = _make_detail_session(lines=[line])
    session = FakeAsyncSession()
    session.queue_scalar(count_session)

    result = await submit_physical_count_session(
        session,
        count_session.tenant_id,
        count_session.id,
        actor_id="user-1",
    )

    assert result["status"] == "submitted"
    assert result["variance_total"] == -2
    assert count_session.status == PhysicalCountSessionStatus.SUBMITTED


@pytest.mark.asyncio
async def test_approve_physical_count_session_creates_adjustment_once() -> None:
    warehouse_id = uuid.uuid4()
    product = FakeProduct(code="P-001", name="Alpha")
    line = FakeCountLine(product=product, system_qty_snapshot=10, counted_qty=8, variance_qty=-2)
    count_session = _make_detail_session(
        warehouse_id=warehouse_id,
        status=PhysicalCountSessionStatus.SUBMITTED,
        lines=[line],
    )
    live_stock = FakeInventoryStock(product_id=product.id, warehouse_id=warehouse_id, quantity=10)
    session = FakeAsyncSession()
    session.queue_scalar(count_session)
    session.queue_scalars([live_stock])
    session.queue_scalar(live_stock)
    session.queue_scalar(None)

    result = await approve_physical_count_session(
        session,
        count_session.tenant_id,
        count_session.id,
        actor_id="user-1",
    )

    assert result["status"] == "approved"
    stock_adjustments = [obj for obj in session.added if type(obj).__name__ == "StockAdjustment"]
    assert len(stock_adjustments) == 1
    assert stock_adjustments[0].reason_code.value == "PHYSICAL_COUNT"


@pytest.mark.asyncio
async def test_approve_physical_count_session_is_idempotent_after_approval() -> None:
    line = FakeCountLine(system_qty_snapshot=10, counted_qty=10, variance_qty=0)
    count_session = _make_detail_session(
        status=PhysicalCountSessionStatus.APPROVED,
        lines=[line],
    )
    session = FakeAsyncSession()
    session.queue_scalar(count_session)

    result = await approve_physical_count_session(
        session,
        count_session.tenant_id,
        count_session.id,
        actor_id="user-1",
    )

    assert result["status"] == "approved"
    assert all(type(obj).__name__ != "StockAdjustment" for obj in session.added)


@pytest.mark.asyncio
async def test_approve_physical_count_session_rejects_stale_snapshot() -> None:
    warehouse_id = uuid.uuid4()
    product = FakeProduct(code="P-001", name="Alpha")
    line = FakeCountLine(product=product, system_qty_snapshot=10, counted_qty=8, variance_qty=-2)
    count_session = _make_detail_session(
        warehouse_id=warehouse_id,
        status=PhysicalCountSessionStatus.SUBMITTED,
        lines=[line],
    )
    stale_stock = FakeInventoryStock(product_id=product.id, warehouse_id=warehouse_id, quantity=11)
    session = FakeAsyncSession()
    session.queue_scalar(count_session)
    session.queue_scalars([stale_stock])

    with pytest.raises(PhysicalCountConflictError, match="stale"):
        await approve_physical_count_session(
            session,
            count_session.tenant_id,
            count_session.id,
            actor_id="user-1",
        )


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


@pytest.mark.asyncio
async def test_approve_count_session_endpoint_returns_409_for_stale_snapshot() -> None:
    warehouse_id = uuid.uuid4()
    product = FakeProduct(code="P-001", name="Alpha")
    line = FakeCountLine(product=product, system_qty_snapshot=10, counted_qty=8, variance_qty=-2)
    count_session = _make_detail_session(
        warehouse_id=warehouse_id,
        status=PhysicalCountSessionStatus.SUBMITTED,
        lines=[line],
    )
    stale_stock = FakeInventoryStock(product_id=product.id, warehouse_id=warehouse_id, quantity=11)
    session = FakeAsyncSession()
    session.queue_scalar(count_session)
    session.queue_scalars([stale_stock])

    previous = _setup(session)
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test", headers=auth_header()) as client:
            response = await client.post(f"/api/v1/inventory/count-sessions/{count_session.id}/approve")
        assert response.status_code == 409
        assert "stale" in response.json()["detail"]
    finally:
        _teardown(previous)