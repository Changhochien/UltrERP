from __future__ import annotations

import uuid

import pytest

from common.errors import DuplicateProductCodeError, ValidationError
from domains.inventory.schemas import ProductUpdate
from domains.inventory.services import update_product


class FakeProduct:
    def __init__(
        self,
        *,
        product_id: uuid.UUID | None = None,
        code: str = "SKU-1",
        name: str = "Widget",
        category: str | None = "Hardware",
        description: str | None = "Original description",
        unit: str = "pcs",
        status: str = "active",
    ) -> None:
        self.id = product_id or uuid.uuid4()
        self.tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        self.code = code
        self.name = name
        self.category = category
        self.description = description
        self.unit = unit
        self.status = status
        self.search_vector = None


class FakeScalarResult:
    def __init__(self, value: object | None) -> None:
        self._value = value

    def scalar_one_or_none(self) -> object | None:
        return self._value


class FakeAsyncSession:
    def __init__(self) -> None:
        self._execute_results: list[FakeScalarResult] = []
        self.flush_calls = 0
        self.rollback_calls = 0

    async def execute(self, _statement: object) -> FakeScalarResult:
        if self._execute_results:
            return self._execute_results.pop(0)
        return FakeScalarResult(None)

    async def flush(self) -> None:
        self.flush_calls += 1

    async def rollback(self) -> None:
        self.rollback_calls += 1

    def queue_scalar(self, value: object | None) -> None:
        self._execute_results.append(FakeScalarResult(value))


async def test_update_product_returns_none_when_missing() -> None:
    session = FakeAsyncSession()
    session.queue_scalar(None)

    result = await update_product(
        session,
        uuid.uuid4(),
        uuid.uuid4(),
        ProductUpdate(code="SKU-1", name="Widget", category="Hardware", description="", unit="pcs"),
    )

    assert result is None


async def test_update_product_allows_same_code_and_updates_fields() -> None:
    tenant_id = uuid.uuid4()
    product = FakeProduct(code="SKU-1", name="Widget")
    session = FakeAsyncSession()
    session.queue_scalar(product)
    session.queue_scalar(None)

    result = await update_product(
        session,
        tenant_id,
        product.id,
        ProductUpdate(
            code="SKU-1",
            name="Widget Pro",
            category=" Updated Hardware ",
            description=" Updated description ",
            unit=" box ",
        ),
    )

    assert result is product
    assert product.code == "SKU-1"
    assert product.name == "Widget Pro"
    assert product.category == "Updated Hardware"
    assert product.description == "Updated description"
    assert product.unit == "box"
    assert product.status == "active"
    assert product.search_vector is not None
    assert session.flush_calls == 1


async def test_update_product_updates_to_unique_code() -> None:
    tenant_id = uuid.uuid4()
    product = FakeProduct(code="SKU-1")
    session = FakeAsyncSession()
    session.queue_scalar(product)
    session.queue_scalar(None)

    result = await update_product(
        session,
        tenant_id,
        product.id,
        ProductUpdate(
            code="SKU-2",
            name="Widget",
            category="Hardware",
            description="Updated",
            unit="pcs",
        ),
    )

    assert result is product
    assert product.code == "SKU-2"


async def test_update_product_raises_duplicate_conflict() -> None:
    tenant_id = uuid.uuid4()
    product = FakeProduct(code="SKU-1")
    existing = FakeProduct(code="SKU-2")
    session = FakeAsyncSession()
    session.queue_scalar(product)
    session.queue_scalar(existing)

    with pytest.raises(DuplicateProductCodeError) as exc_info:
        await update_product(
            session,
            tenant_id,
            product.id,
            ProductUpdate(
                code="SKU-2",
                name="Widget",
                category="Hardware",
                description="Updated",
                unit="pcs",
            ),
        )

    assert exc_info.value.existing_code == "SKU-2"


async def test_update_product_rejects_code_reuse_from_inactive_product() -> None:
    tenant_id = uuid.uuid4()
    product = FakeProduct(code="SKU-1")
    existing = FakeProduct(code="SKU-2", status="inactive")
    session = FakeAsyncSession()
    session.queue_scalar(product)
    session.queue_scalar(existing)

    with pytest.raises(DuplicateProductCodeError) as exc_info:
        await update_product(
            session,
            tenant_id,
            product.id,
            ProductUpdate(
                code="SKU-2",
                name="Widget",
                category="Hardware",
                description="Updated",
                unit="pcs",
            ),
        )

    assert exc_info.value.existing_code == "SKU-2"


async def test_update_product_rejects_whitespace_required_fields() -> None:
    session = FakeAsyncSession()

    with pytest.raises(ValidationError) as exc_info:
        await update_product(
            session,
            uuid.uuid4(),
            uuid.uuid4(),
            ProductUpdate(
                code="   ",
                name="\t",
                category="Hardware",
                description="",
                unit=" ",
            ),
        )

    locs = {tuple(error["loc"]) for error in exc_info.value.errors}
    assert ("code",) in locs
    assert ("name",) in locs
    assert ("unit",) in locs