"""API tests for inventory endpoints — warehouses and transfers."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

from httpx import ASGITransport, AsyncClient

from app.main import app
from common.database import get_db

# ── Fake session for API tests ────────────────────────────────

class FakeAsyncSession:
	def __init__(self) -> None:
		self.added: list[object] = []
		self._execute_results: list[object] = []
		self._idx = 0

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
		now = datetime.now(tz=UTC)
		for obj in self.added:
			if hasattr(obj, "id") and obj.id is None:
				obj.id = uuid.uuid4()
			if hasattr(obj, "created_at") and obj.created_at is None:
				obj.created_at = now

	async def commit(self) -> None:
		await self.flush()

	def queue_result(self, obj: object | None) -> None:
		self._execute_results.append(FakeResult(obj))

	def queue_scalars(self, objs: list[object]) -> None:
		self._execute_results.append(FakeScalarsResult(objs))


class FakeResult:
	def __init__(self, obj: object | None):
		self._obj = obj

	def scalar_one_or_none(self) -> object | None:
		return self._obj

	def scalars(self) -> FakeScalars:
		return FakeScalars([self._obj] if self._obj else [])


class FakeScalarsResult:
	def __init__(self, objs: list[object]):
		self._objs = objs

	def scalar_one_or_none(self) -> object | None:
		return self._objs[0] if self._objs else None

	def scalars(self) -> FakeScalars:
		return FakeScalars(self._objs)


class FakeScalars:
	def __init__(self, objs: list[object]):
		self._objs = objs

	def all(self) -> list:
		return self._objs


def _make_warehouse(
	*,
	wh_id: uuid.UUID | None = None,
	name: str = "Main",
	code: str = "WH-001",
) -> object:

	class FakeWarehouse:
		pass

	w = FakeWarehouse()
	w.id = wh_id or uuid.uuid4()
	w.tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
	w.name = name
	w.code = code
	w.location = "台北"
	w.address = "台北市信義區"
	w.contact_email = "wh@example.com"
	w.is_active = True
	w.created_at = datetime.now(tz=UTC)
	return w


_MISSING_OVERRIDE = object()


def _setup(session: FakeAsyncSession) -> Any:
	async def _override() -> AsyncGenerator[FakeAsyncSession, None]:
		yield session

	previous_override = app.dependency_overrides.get(get_db, _MISSING_OVERRIDE)
	app.dependency_overrides[get_db] = _override
	return previous_override


def _teardown(previous_override: Any) -> None:
	if previous_override is _MISSING_OVERRIDE:
		app.dependency_overrides.pop(get_db, None)
		return

	app.dependency_overrides[get_db] = previous_override


# ── Warehouse list ────────────────────────────────────────────

async def test_list_warehouses_empty() -> None:
	session = FakeAsyncSession()
	session.queue_scalars([])
	previous_override = _setup(session)
	try:
		transport = ASGITransport(app=app)
		async with AsyncClient(
			transport=transport, base_url="http://testserver",
		) as client:
			resp = await client.get("/api/v1/inventory/warehouses")
		assert resp.status_code == 200
		body = resp.json()
		assert body["items"] == []
		assert body["total"] == 0
	finally:
		_teardown(previous_override)


async def test_list_warehouses_returns_items() -> None:
	wh = _make_warehouse(name="Main", code="WH-001")
	session = FakeAsyncSession()
	session.queue_scalars([wh])
	previous_override = _setup(session)
	try:
		transport = ASGITransport(app=app)
		async with AsyncClient(
			transport=transport, base_url="http://testserver",
		) as client:
			resp = await client.get("/api/v1/inventory/warehouses")
		assert resp.status_code == 200
		body = resp.json()
		assert body["total"] == 1
		assert body["items"][0]["name"] == "Main"
		assert body["items"][0]["code"] == "WH-001"
	finally:
		_teardown(previous_override)


# ── Warehouse detail ──────────────────────────────────────────

async def test_get_warehouse_not_found() -> None:
	session = FakeAsyncSession()
	session.queue_result(None)
	previous_override = _setup(session)
	try:
		transport = ASGITransport(app=app)
		async with AsyncClient(
			transport=transport, base_url="http://testserver",
		) as client:
			resp = await client.get(
				f"/api/v1/inventory/warehouses/{uuid.uuid4()}",
			)
		assert resp.status_code == 404
	finally:
		_teardown(previous_override)


async def test_get_warehouse_found() -> None:
	wh_id = uuid.uuid4()
	wh = _make_warehouse(wh_id=wh_id, name="South", code="WH-002")
	session = FakeAsyncSession()
	session.queue_result(wh)
	previous_override = _setup(session)
	try:
		transport = ASGITransport(app=app)
		async with AsyncClient(
			transport=transport, base_url="http://testserver",
		) as client:
			resp = await client.get(
				f"/api/v1/inventory/warehouses/{wh_id}",
			)
		assert resp.status_code == 200
		assert resp.json()["name"] == "South"
	finally:
		_teardown(previous_override)


# ── Transfer validation via API ───────────────────────────────

async def test_transfer_same_warehouse_returns_422() -> None:
	session = FakeAsyncSession()
	previous_override = _setup(session)
	wh = str(uuid.uuid4())
	try:
		transport = ASGITransport(app=app)
		async with AsyncClient(
			transport=transport, base_url="http://testserver",
		) as client:
			resp = await client.post(
				"/api/v1/inventory/transfers",
				json={
					"from_warehouse_id": wh,
					"to_warehouse_id": wh,
					"product_id": str(uuid.uuid4()),
					"quantity": 10,
				},
			)
		assert resp.status_code == 422
		assert "different" in resp.json()["detail"]
	finally:
			_teardown(previous_override)


async def test_transfer_insufficient_stock_returns_409() -> None:
	from tests.domains.inventory.test_transfer_service import (
		FakeInventoryStock,
	)

	source = FakeInventoryStock(quantity=5)
	session = FakeAsyncSession()
	session.queue_result(source)  # source stock
	previous_override = _setup(session)
	try:
		transport = ASGITransport(app=app)
		async with AsyncClient(
			transport=transport, base_url="http://testserver",
		) as client:
			resp = await client.post(
				"/api/v1/inventory/transfers",
				json={
					"from_warehouse_id": str(uuid.uuid4()),
					"to_warehouse_id": str(uuid.uuid4()),
					"product_id": str(uuid.uuid4()),
					"quantity": 10,
				},
			)
		assert resp.status_code == 409
		body = resp.json()
		assert body["detail"]["available"] == 5
		assert body["detail"]["requested"] == 10
	finally:
		_teardown(previous_override)
