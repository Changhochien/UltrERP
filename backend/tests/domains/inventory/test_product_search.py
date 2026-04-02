"""API tests for product search endpoint."""

from __future__ import annotations

import uuid

from httpx import ASGITransport, AsyncClient

from app.main import app
from common.database import get_db

# ── Fake DB layer ──────────────────────────────────────────────

class FakeAsyncSession:
	"""Minimal fake async session for search tests."""

	def __init__(self) -> None:
		self._results: list[object] = []

	def queue_rows(self, rows: list[tuple]) -> None:
		self._results.append(rows)

	async def execute(self, _stmt: object) -> object:  # noqa: ANN401
		data = self._results.pop(0) if self._results else []

		class FakeResult:
			def __init__(self, rows: list[tuple]) -> None:
				self._rows = rows

			def all(self) -> list[tuple]:
				return self._rows

		return FakeResult(data)

	async def commit(self) -> None:
		pass

	async def close(self) -> None:
		pass


_original_dep = None


def _setup(session: FakeAsyncSession) -> None:
	global _original_dep  # noqa: PLW0603
	_original_dep = app.dependency_overrides.get(get_db)

	async def _override() -> FakeAsyncSession:  # type: ignore[misc]
		yield session  # type: ignore[misc]

	app.dependency_overrides[get_db] = _override


def _teardown() -> None:
	if _original_dep is not None:
		app.dependency_overrides[get_db] = _original_dep
	else:
		app.dependency_overrides.pop(get_db, None)


# ── Tests ──────────────────────────────────────────────────────

async def test_search_requires_min_3_chars() -> None:
	session = FakeAsyncSession()
	_setup(session)
	try:
		transport = ASGITransport(app=app)
		async with AsyncClient(
			transport=transport, base_url="http://testserver",
		) as client:
			resp = await client.get(
				"/api/v1/inventory/products/search",
				params={"q": "ab"},
			)
		assert resp.status_code == 422
	finally:
		_teardown()


async def test_search_rejects_blank_query() -> None:
	session = FakeAsyncSession()
	_setup(session)
	try:
		transport = ASGITransport(app=app)
		async with AsyncClient(
			transport=transport, base_url="http://testserver",
		) as client:
			resp = await client.get(
				"/api/v1/inventory/products/search",
				params={"q": "   "},
			)
		# FastAPI validates min_length=3 after stripping? No, it counts
		# spaces. But route strips and checks blank.
		# "   " has length 3, passes min_length, then route returns 400.
		assert resp.status_code == 400
	finally:
		_teardown()


async def test_search_returns_results() -> None:
	pid = uuid.uuid4()
	session = FakeAsyncSession()

	# The search query returns Row-like tuples
	from collections import namedtuple
	SearchRow = namedtuple(
		"SearchRow",
		["id", "code", "name", "category", "status", "current_stock", "relevance"],
	)
	session.queue_rows([
		SearchRow(
			id=pid, code="WIDGET-001", name="Blue Widget",
			category="Widgets", status="active",
			current_stock=42, relevance=10.5,
		),
	])

	_setup(session)
	try:
		transport = ASGITransport(app=app)
		async with AsyncClient(
			transport=transport, base_url="http://testserver",
		) as client:
			resp = await client.get(
				"/api/v1/inventory/products/search",
				params={"q": "widget"},
			)
		assert resp.status_code == 200
		body = resp.json()
		assert body["total"] == 1
		assert body["items"][0]["code"] == "WIDGET-001"
		assert body["items"][0]["current_stock"] == 42
	finally:
		_teardown()


async def test_search_empty_results() -> None:
	session = FakeAsyncSession()
	session.queue_rows([])

	_setup(session)
	try:
		transport = ASGITransport(app=app)
		async with AsyncClient(
			transport=transport, base_url="http://testserver",
		) as client:
			resp = await client.get(
				"/api/v1/inventory/products/search",
				params={"q": "nonexistent"},
			)
		assert resp.status_code == 200
		body = resp.json()
		assert body["total"] == 0
		assert body["items"] == []
	finally:
		_teardown()


async def test_search_limit_parameter() -> None:
	session = FakeAsyncSession()
	session.queue_rows([])

	_setup(session)
	try:
		transport = ASGITransport(app=app)
		async with AsyncClient(
			transport=transport, base_url="http://testserver",
		) as client:
			resp = await client.get(
				"/api/v1/inventory/products/search",
				params={"q": "test", "limit": 5},
			)
		assert resp.status_code == 200
	finally:
		_teardown()


async def test_search_limit_exceeds_max() -> None:
	session = FakeAsyncSession()
	_setup(session)
	try:
		transport = ASGITransport(app=app)
		async with AsyncClient(
			transport=transport, base_url="http://testserver",
		) as client:
			resp = await client.get(
				"/api/v1/inventory/products/search",
				params={"q": "test", "limit": 200},
			)
		assert resp.status_code == 422
	finally:
		_teardown()


async def test_search_strips_whitespace_and_rejects_short() -> None:
	"""A query of spaces-padded short text should be rejected after trimming."""
	session = FakeAsyncSession()
	_setup(session)
	try:
		transport = ASGITransport(app=app)
		async with AsyncClient(
			transport=transport, base_url="http://testserver",
		) as client:
			# " a " has length 3 (passes min_length) but strips to "a" (1 char)
			resp = await client.get(
				"/api/v1/inventory/products/search",
				params={"q": " a "},
			)
		assert resp.status_code == 400
		assert "at least 3" in resp.json()["detail"]
	finally:
		_teardown()


async def test_search_with_warehouse_id() -> None:
	"""warehouse_id parameter should be accepted and passed through."""
	pid = uuid.uuid4()
	wid = uuid.uuid4()
	session = FakeAsyncSession()

	from collections import namedtuple
	SearchRow = namedtuple(
		"SearchRow",
		["id", "code", "name", "category", "status", "current_stock", "relevance"],
	)
	session.queue_rows([
		SearchRow(
			id=pid, code="BOLT-100", name="Hex Bolt M10",
			category="Fasteners", status="active",
			current_stock=500, relevance=8.3,
		),
	])

	_setup(session)
	try:
		transport = ASGITransport(app=app)
		async with AsyncClient(
			transport=transport, base_url="http://testserver",
		) as client:
			resp = await client.get(
				"/api/v1/inventory/products/search",
				params={"q": "bolt", "warehouse_id": str(wid)},
			)
		assert resp.status_code == 200
		body = resp.json()
		assert body["total"] == 1
		assert body["items"][0]["code"] == "BOLT-100"
	finally:
		_teardown()


async def test_search_special_characters_in_query() -> None:
	"""Queries containing LIKE wildcards or SQL-sensitive chars should not cause errors."""
	session = FakeAsyncSession()
	session.queue_rows([])

	_setup(session)
	try:
		transport = ASGITransport(app=app)
		async with AsyncClient(
			transport=transport, base_url="http://testserver",
		) as client:
			for q in ["100%", "foo_bar", "it's", "test; DROP"]:
				resp = await client.get(
					"/api/v1/inventory/products/search",
					params={"q": q},
				)
				assert resp.status_code in (200, 400), f"Unexpected status for q={q!r}"
				session.queue_rows([])  # Replenish for next iteration
	finally:
		_teardown()


async def test_search_multiple_results_returned() -> None:
	"""Multiple rows should all appear in response items."""
	from collections import namedtuple
	SearchRow = namedtuple(
		"SearchRow",
		["id", "code", "name", "category", "status", "current_stock", "relevance"],
	)

	session = FakeAsyncSession()
	session.queue_rows([
		SearchRow(uuid.uuid4(), "WGT-001", "Blue Widget", "Widgets", "active", 10, 10.0),
		SearchRow(uuid.uuid4(), "WGT-002", "Red Widget", "Widgets", "active", 5, 7.5),
		SearchRow(uuid.uuid4(), "WGT-003", "Green Widget", None, "active", 0, 3.2),
	])

	_setup(session)
	try:
		transport = ASGITransport(app=app)
		async with AsyncClient(
			transport=transport, base_url="http://testserver",
		) as client:
			resp = await client.get(
				"/api/v1/inventory/products/search",
				params={"q": "widget"},
			)
		assert resp.status_code == 200
		body = resp.json()
		assert body["total"] == 3
		codes = [item["code"] for item in body["items"]]
		assert codes == ["WGT-001", "WGT-002", "WGT-003"]
	finally:
		_teardown()


async def test_search_result_schema_fields() -> None:
	"""Every result should contain all expected fields with correct types."""
	from collections import namedtuple
	SearchRow = namedtuple(
		"SearchRow",
		["id", "code", "name", "category", "status", "current_stock", "relevance"],
	)
	pid = uuid.uuid4()
	session = FakeAsyncSession()
	session.queue_rows([
		SearchRow(pid, "SCH-001", "Schema Test", None, "active", 99, 5.5),
	])

	_setup(session)
	try:
		transport = ASGITransport(app=app)
		async with AsyncClient(
			transport=transport, base_url="http://testserver",
		) as client:
			resp = await client.get(
				"/api/v1/inventory/products/search",
				params={"q": "schema"},
			)
		assert resp.status_code == 200
		item = resp.json()["items"][0]
		assert item["id"] == str(pid)
		assert item["code"] == "SCH-001"
		assert item["name"] == "Schema Test"
		assert item["category"] is None
		assert item["status"] == "active"
		assert item["current_stock"] == 99
		assert isinstance(item["relevance"], float)
	finally:
		_teardown()
