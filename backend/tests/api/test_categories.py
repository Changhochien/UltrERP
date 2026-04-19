from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

from httpx import ASGITransport, AsyncClient

from app.main import app
from common.database import get_db
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


class FakeCategory:
    def __init__(
        self,
        *,
        category_id: uuid.UUID | None = None,
        name: str = "Hardware",
        is_active: bool = True,
        translations: dict[str, str] | None = None,
    ) -> None:
        self.id = category_id or uuid.uuid4()
        self.tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        self.name = name
        self.is_active = is_active
        translation_map = translations or {"en": name}
        self.translations = [
            type("FakeTranslation", (), {"locale": locale, "name": translation_name})()
            for locale, translation_name in translation_map.items()
        ]
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


async def test_create_category_success() -> None:
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
                "/api/v1/inventory/categories",
                json={"name": "Hardware"},
            )

        assert resp.status_code == 201, resp.json()
        body = resp.json()
        assert body["name"] == "Hardware"
        assert body["name_en"] == "Hardware"
        assert body["translations"] == {"en": "Hardware"}
        assert body["is_active"] is True
    finally:
        _teardown(previous)


async def test_create_category_blank_name_returns_422() -> None:
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
                "/api/v1/inventory/categories",
                json={"name": "   "},
            )

        assert resp.status_code == 422
    finally:
        _teardown(previous)


async def test_create_category_duplicate_returns_409() -> None:
    existing = FakeCategory(name="Hardware")
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
                "/api/v1/inventory/categories",
                json={"name": "Hardware"},
            )

        assert resp.status_code == 409
        body = resp.json()
        assert body["error"] == "duplicate_category_name"
        assert body["existing_category_name"] == "Hardware"
    finally:
        _teardown(previous)


async def test_list_categories_returns_items() -> None:
    category = FakeCategory(name="Hardware")
    session = FakeAsyncSession()
    session.queue_scalars([category])
    previous = _setup(session)

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
            headers=auth_header(),
        ) as client:
            resp = await client.get("/api/v1/inventory/categories")

        assert resp.status_code == 200, resp.json()
        body = resp.json()
        assert body["total"] == 1
        assert body["items"][0]["name"] == "Hardware"
        assert body["items"][0]["name_en"] == "Hardware"
    finally:
        _teardown(previous)


async def test_list_categories_localizes_name_from_accept_language() -> None:
    category = FakeCategory(name="Hardware", translations={"en": "Hardware", "zh-Hant": "五金"})
    session = FakeAsyncSession()
    session.queue_scalars([category])
    previous = _setup(session)

    try:
        transport = ASGITransport(app=app)
        headers = {**auth_header(), "Accept-Language": "zh-Hant"}
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
            headers=headers,
        ) as client:
            resp = await client.get("/api/v1/inventory/categories")

        assert resp.status_code == 200, resp.json()
        body = resp.json()
        assert body["items"][0]["name"] == "五金"
        assert body["items"][0]["name_zh_hant"] == "五金"
    finally:
        _teardown(previous)


async def test_update_category_status_success() -> None:
    category = FakeCategory(name="Hardware", is_active=True)
    session = FakeAsyncSession()
    session.queue_scalar(category)
    previous = _setup(session)

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
            headers=auth_header(),
        ) as client:
            resp = await client.patch(
                f"/api/v1/inventory/categories/{category.id}/status",
                json={"is_active": False},
            )

        assert resp.status_code == 200, resp.json()
        body = resp.json()
        assert body["is_active"] is False
    finally:
        _teardown(previous)
