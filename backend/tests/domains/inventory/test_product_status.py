from __future__ import annotations

import uuid

from domains.inventory.services import search_products, set_product_status


class FakeProduct:
    def __init__(
        self,
        *,
        product_id: uuid.UUID | None = None,
        code: str = "SKU-1",
        status: str = "active",
    ) -> None:
        self.id = product_id or uuid.uuid4()
        self.tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        self.code = code
        self.name = "Widget"
        self.category = "Hardware"
        self.description = "Description"
        self.unit = "pcs"
        self.status = status
        self.search_vector = None


class FakeResult:
    def __init__(self, scalar_value: object | None = None, rows: list[object] | None = None) -> None:
        self._scalar_value = scalar_value
        self._rows = rows or []

    def scalar_one_or_none(self) -> object | None:
        return self._scalar_value

    def scalar(self) -> int:
        return int(self._scalar_value or 0)

    def all(self) -> list[object]:
        return self._rows


class FakeAsyncSession:
    def __init__(self) -> None:
        self._execute_results: list[FakeResult] = []
        self.flush_calls = 0
        self.where_clauses: list[str] = []

    async def execute(self, statement: object) -> FakeResult:
        criteria = getattr(statement, "_where_criteria", ())
        self.where_clauses.append(" AND ".join(str(item) for item in criteria))
        if self._execute_results:
            return self._execute_results.pop(0)
        return FakeResult(rows=[])

    async def flush(self) -> None:
        self.flush_calls += 1

    def queue_scalar(self, value: object | None) -> None:
        self._execute_results.append(FakeResult(scalar_value=value))

    def queue_count(self, value: int) -> None:
        self._execute_results.append(FakeResult(scalar_value=value))

    def queue_rows(self, rows: list[object]) -> None:
        self._execute_results.append(FakeResult(rows=rows))


async def test_set_product_status_returns_none_when_missing() -> None:
    session = FakeAsyncSession()
    session.queue_scalar(None)

    result = await set_product_status(session, uuid.uuid4(), uuid.uuid4(), "inactive")

    assert result is None
    assert session.flush_calls == 0


async def test_set_product_status_updates_existing_product() -> None:
    product = FakeProduct(status="active")
    session = FakeAsyncSession()
    session.queue_scalar(product)

    result = await set_product_status(session, product.tenant_id, product.id, "inactive")

    assert result is product
    assert product.status == "inactive"
    assert session.flush_calls == 1


async def test_search_products_filters_inactive_by_default() -> None:
    session = FakeAsyncSession()
    session.queue_count(0)
    session.queue_rows([])

    await search_products(session, uuid.uuid4(), "")

    assert any("product.status" in clause for clause in session.where_clauses)


async def test_search_products_can_include_inactive_rows() -> None:
    session = FakeAsyncSession()
    session.queue_rows([])
    session.queue_rows([])
    session.queue_count(0)

    await search_products(session, uuid.uuid4(), "widget", include_inactive=True)

    assert all("product.status" not in clause for clause in session.where_clauses)


async def test_search_products_applies_category_filter() -> None:
    session = FakeAsyncSession()
    session.queue_count(0)
    session.queue_rows([])

    await search_products(session, uuid.uuid4(), "", category="Hardware")

    assert any("product.category" in clause for clause in session.where_clauses)