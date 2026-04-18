from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import Any
import uuid

import pytest

from common.model_registry import register_all_models
from common.models.product import Product
from common.models.supplier import Supplier
from domains.inventory import services as inventory_services

register_all_models()


class FakeScalarCollection:
    def __init__(self, items: list[object]) -> None:
        self._items = items

    def all(self) -> list[object]:
        return list(self._items)


class FakeExecuteResult:
    def __init__(
        self,
        *,
        first_value: object | None = None,
        scalar_value: object | None = None,
        scalar_items: list[object] | None = None,
        all_items: list[object] | None = None,
    ) -> None:
        self._first_value = first_value
        self._scalar_value = scalar_value
        self._scalar_items = scalar_items or []
        self._all_items = all_items or []

    def first(self) -> object | None:
        return self._first_value

    def scalar_one_or_none(self) -> object | None:
        return self._scalar_value

    def scalars(self) -> FakeScalarCollection:
        return FakeScalarCollection(self._scalar_items)

    def all(self) -> list[object]:
        return list(self._all_items)


class FakeAsyncSession:
    def __init__(self, *, products: dict[uuid.UUID, object] | None = None, suppliers: dict[uuid.UUID, object] | None = None) -> None:
        self.products = products or {}
        self.suppliers = suppliers or {}
        self.execute_results: list[FakeExecuteResult] = []
        self.added: list[object] = []
        self.deleted: list[object] = []
        self.flush_calls = 0

    async def get(self, model: type[object], obj_id: uuid.UUID) -> object | None:
        if model is Product:
            return self.products.get(obj_id)
        if model is Supplier:
            return self.suppliers.get(obj_id)
        return None

    async def execute(self, _statement: object) -> FakeExecuteResult:
        if not self.execute_results:
            return FakeExecuteResult()
        return self.execute_results.pop(0)

    def add(self, obj: object) -> None:
        self.added.append(obj)

    async def delete(self, obj: object) -> None:
        self.deleted.append(obj)

    async def flush(self) -> None:
        self.flush_calls += 1

    def queue_first(self, value: object | None) -> None:
        self.execute_results.append(FakeExecuteResult(first_value=value))

    def queue_scalar(self, value: object | None) -> None:
        self.execute_results.append(FakeExecuteResult(scalar_value=value))

    def queue_scalar_items(self, values: list[object]) -> None:
        self.execute_results.append(FakeExecuteResult(scalar_items=values))

    def queue_all(self, values: list[object]) -> None:
        self.execute_results.append(FakeExecuteResult(all_items=values))


def _tenant_entity(tenant_id: uuid.UUID, **extra: Any) -> SimpleNamespace:
    return SimpleNamespace(tenant_id=tenant_id, **extra)


@pytest.mark.asyncio
async def test_get_product_supplier_prefers_explicit_default_association() -> None:
    supplier_id = uuid.uuid4()
    session = FakeAsyncSession()
    session.queue_first(
        SimpleNamespace(
            id=supplier_id,
            name="Default Supply",
            unit_cost=Decimal("9.5000"),
            effective_lead_time_days=11,
        )
    )

    result = await inventory_services.get_product_supplier(
        session,
        uuid.uuid4(),
        uuid.uuid4(),
    )

    assert result == {
        "supplier_id": supplier_id,
        "name": "Default Supply",
        "unit_cost": 9.5,
        "default_lead_time_days": 11,
    }


@pytest.mark.asyncio
async def test_get_product_supplier_falls_back_to_heuristic_when_needed() -> None:
    supplier_id = uuid.uuid4()
    session = FakeAsyncSession()
    session.queue_first(None)
    session.queue_first(
        SimpleNamespace(
            id=supplier_id,
            name="Fallback Supply",
            unit_cost=Decimal("5.7500"),
            default_lead_time_days=6,
        )
    )

    result = await inventory_services.get_product_supplier(
        session,
        uuid.uuid4(),
        uuid.uuid4(),
    )

    assert result == {
        "supplier_id": supplier_id,
        "name": "Fallback Supply",
        "unit_cost": 5.75,
        "default_lead_time_days": 6,
    }


@pytest.mark.asyncio
async def test_list_product_suppliers_serializes_associations() -> None:
    association = SimpleNamespace(
        id=uuid.uuid4(),
        product_id=uuid.uuid4(),
        supplier_id=uuid.uuid4(),
        unit_cost=Decimal("4.2000"),
        lead_time_days=3,
        is_default=True,
        created_at=datetime.now(tz=UTC),
        updated_at=datetime.now(tz=UTC),
    )
    session = FakeAsyncSession()
    session.queue_all([(association, "Alpha Supply")])

    result = await inventory_services.list_product_suppliers(
        session,
        uuid.uuid4(),
        association.product_id,
    )

    assert result[0]["supplier_name"] == "Alpha Supply"
    assert result[0]["unit_cost"] == 4.2
    assert result[0]["lead_time_days"] == 3
    assert result[0]["is_default"] is True


@pytest.mark.asyncio
async def test_create_product_supplier_clears_existing_default() -> None:
    tenant_id = uuid.uuid4()
    product_id = uuid.uuid4()
    supplier_id = uuid.uuid4()
    previous_default = SimpleNamespace(is_default=True)
    session = FakeAsyncSession(
        products={product_id: _tenant_entity(tenant_id)},
        suppliers={supplier_id: _tenant_entity(tenant_id, name="Beta Supply")},
    )
    session.queue_scalar(None)
    session.queue_scalar_items([previous_default])

    result = await inventory_services.create_product_supplier(
        session,
        tenant_id,
        product_id,
        supplier_id=supplier_id,
        unit_cost=8.25,
        lead_time_days=5,
        is_default=True,
    )

    created = session.added[0]
    assert previous_default.is_default is False
    assert created.product_id == product_id
    assert created.supplier_id == supplier_id
    assert created.is_default is True
    assert float(created.unit_cost) == 8.25
    assert result["supplier_name"] == "Beta Supply"
    assert session.flush_calls == 1


@pytest.mark.asyncio
async def test_update_and_delete_product_supplier_association() -> None:
    tenant_id = uuid.uuid4()
    product_id = uuid.uuid4()
    supplier_id = uuid.uuid4()
    other_default = SimpleNamespace(is_default=True)
    association = SimpleNamespace(
        id=uuid.uuid4(),
        product_id=product_id,
        supplier_id=supplier_id,
        unit_cost=Decimal("4.2000"),
        lead_time_days=3,
        is_default=False,
        created_at=datetime.now(tz=UTC),
        updated_at=datetime.now(tz=UTC),
    )
    session = FakeAsyncSession()
    session.queue_first((association, "Gamma Supply"))
    session.queue_scalar_items([other_default])

    updated = await inventory_services.update_product_supplier(
        session,
        tenant_id,
        product_id,
        supplier_id,
        unit_cost=6.4,
        lead_time_days=8,
        is_default=True,
    )

    assert updated is not None
    assert updated["supplier_name"] == "Gamma Supply"
    assert updated["unit_cost"] == 6.4
    assert updated["lead_time_days"] == 8
    assert other_default.is_default is False
    assert association.is_default is True

    delete_session = FakeAsyncSession()
    delete_session.queue_scalar(association)
    deleted = await inventory_services.delete_product_supplier(
        delete_session,
        tenant_id,
        product_id,
        supplier_id,
    )

    assert deleted is True
    assert delete_session.deleted == [association]
    assert delete_session.flush_calls == 1