from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

from httpx import ASGITransport, AsyncClient

from app.main import app
from common.database import get_db
from domains.inventory.services import DEFAULT_UNIT_OF_MEASURE_SEEDS
from tests.domains.orders._helpers import auth_header


class FakeScalarResult:
    def __init__(
        self,
        *,
        scalar_value: object | None = None,
        scalar_items: list[object] | None = None,
    ) -> None:
        self._scalar_value = scalar_value
        self._scalar_items = scalar_items or []

    def scalar_one_or_none(self) -> object | None:
        return self._scalar_value

    def scalar(self) -> int:
        return int(self._scalar_value or 0)

    def scalars(self) -> FakeScalarResult:
        return self

    def all(self) -> list[object]:
        return list(self._scalar_items)


class FakeUnitOfMeasure:
    def __init__(
        self,
        *,
        unit_id: uuid.UUID | None = None,
        code: str = "pcs",
        name: str = "Pieces",
        decimal_places: int = 0,
        is_active: bool = True,
    ) -> None:
        self.id = unit_id or uuid.uuid4()
        self.tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        self.code = code
        self.name = name
        self.decimal_places = decimal_places
        self.is_active = is_active
        now = datetime.now(tz=UTC)
        self.created_at = now
        self.updated_at = now


class FakeAsyncSession:
    def __init__(self) -> None:
        self._execute_results: list[FakeScalarResult] = []
        self.commit_calls = 0
        self.added: list[object] = []

    def add(self, instance: object) -> None:
        self.added.append(instance)

    def add_all(self, instances: list[object]) -> None:
        self.added.extend(instances)

    async def execute(self, _statement: object, params: object = None) -> FakeScalarResult:
        if self._execute_results:
            return self._execute_results.pop(0)
        return FakeScalarResult()

    async def flush(self) -> None:
        for instance in self.added:
            now = datetime.now(tz=UTC)
            if getattr(instance, "id", None) is None:
                instance.id = uuid.uuid4()  # type: ignore[attr-defined]
            if getattr(instance, "created_at", None) is None:
                instance.created_at = now  # type: ignore[attr-defined]
            if getattr(instance, "updated_at", None) is None:
                instance.updated_at = now  # type: ignore[attr-defined]
            if getattr(instance, "tenant_id", None) is None:
                instance.tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")  # type: ignore[attr-defined]
            if getattr(instance, "is_active", None) is None:
                instance.is_active = True  # type: ignore[attr-defined]

    async def commit(self) -> None:
        self.commit_calls += 1

    async def rollback(self) -> None:
        pass

    def queue_scalar(self, value: object | None) -> None:
        self._execute_results.append(FakeScalarResult(scalar_value=value))

    def queue_count(self, value: int) -> None:
        self._execute_results.append(FakeScalarResult(scalar_value=value))

    def queue_scalars(self, items: list[object]) -> None:
        self._execute_results.append(FakeScalarResult(scalar_items=items))


_MISSING_OVERRIDE = object()


def _setup(session: FakeAsyncSession) -> Any:
    previous = app.dependency_overrides.get(get_db, _MISSING_OVERRIDE)

    async def override() -> AsyncGenerator[FakeAsyncSession, None]:
        yield session

    app.dependency_overrides[get_db] = override
    return previous


def _teardown(previous: Any) -> None:
    if previous is _MISSING_OVERRIDE:
        app.dependency_overrides.pop(get_db, None)
    else:
        app.dependency_overrides[get_db] = previous


async def test_create_unit_success() -> None:
    session = FakeAsyncSession()
    session.queue_scalar(None)
    previous = _setup(session)

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
            headers=auth_header(),
        ) as client:
            resp = await client.post(
                "/api/v1/inventory/units",
                json={"code": "PCS", "name": "Pieces", "decimal_places": 0},
            )

        assert resp.status_code == 201, resp.json()
        body = resp.json()
        assert body["code"] == "pcs"
        assert body["name"] == "Pieces"
        assert body["is_active"] is True
    finally:
        _teardown(previous)


async def test_create_unit_duplicate_returns_409() -> None:
    existing = FakeUnitOfMeasure(code="pcs", name="Pieces")
    session = FakeAsyncSession()
    session.queue_scalar(existing)
    previous = _setup(session)

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
            headers=auth_header(),
        ) as client:
            resp = await client.post(
                "/api/v1/inventory/units",
                json={"code": "pcs", "name": "Pieces", "decimal_places": 0},
            )

        assert resp.status_code == 409
        body = resp.json()
        assert body["error"] == "duplicate_unit_code"
        assert body["existing_unit_code"] == "pcs"
    finally:
        _teardown(previous)


async def test_create_unit_blank_code_returns_422() -> None:
    session = FakeAsyncSession()
    previous = _setup(session)

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
            headers=auth_header(),
        ) as client:
            resp = await client.post(
                "/api/v1/inventory/units",
                json={"code": "   ", "name": "Pieces", "decimal_places": 0},
            )

        assert resp.status_code == 422
        body = resp.json()
        assert body["detail"][0]["loc"] == ["code"]
    finally:
        _teardown(previous)


async def test_list_units_auto_seeds_defaults() -> None:
    seeded_units = [
        FakeUnitOfMeasure(code=code, name=name, decimal_places=decimal_places)
        for code, name, decimal_places in DEFAULT_UNIT_OF_MEASURE_SEEDS
    ]
    session = FakeAsyncSession()
    session.queue_scalars([])
    session.queue_count(len(seeded_units))
    session.queue_scalars(seeded_units)
    previous = _setup(session)

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
            headers=auth_header(),
        ) as client:
            resp = await client.get("/api/v1/inventory/units")

        assert resp.status_code == 200, resp.json()
        body = resp.json()
        assert body["total"] == len(seeded_units)
        assert [item["code"] for item in body["items"]] == [code for code, _, _ in DEFAULT_UNIT_OF_MEASURE_SEEDS]
    finally:
        _teardown(previous)


async def test_update_unit_status_success() -> None:
    unit = FakeUnitOfMeasure(code="pcs", name="Pieces", is_active=True)
    session = FakeAsyncSession()
    session.queue_scalar(unit)
    previous = _setup(session)

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
            headers=auth_header(),
        ) as client:
            resp = await client.patch(
                f"/api/v1/inventory/units/{unit.id}/status",
                json={"is_active": False},
            )

        assert resp.status_code == 200, resp.json()
        body = resp.json()
        assert body["is_active"] is False
    finally:
        _teardown(previous)