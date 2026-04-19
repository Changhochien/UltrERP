from __future__ import annotations

import uuid
from datetime import UTC, datetime

from common.models.unit_of_measure import UnitOfMeasure
from domains.inventory.services import (
    DEFAULT_UNIT_OF_MEASURE_SEEDS,
    list_units,
    seed_default_units,
)


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


class RecordingAsyncSession:
    def __init__(self) -> None:
        self._execute_results: list[FakeScalarResult] = []
        self.executed: list[object] = []
        self.added: list[object] = []

    def add(self, instance: object) -> None:
        self.added.append(instance)

    def add_all(self, instances: list[object]) -> None:
        self.added.extend(instances)

    async def execute(self, statement: object, params: object = None) -> FakeScalarResult:
        self.executed.append(statement)
        if self._execute_results:
            return self._execute_results.pop(0)
        return FakeScalarResult()

    async def flush(self) -> None:
        now = datetime.now(tz=UTC)
        for instance in self.added:
            if getattr(instance, "id", None) is None:
                instance.id = uuid.uuid4()  # type: ignore[attr-defined]
            if getattr(instance, "created_at", None) is None:
                instance.created_at = now  # type: ignore[attr-defined]
            if getattr(instance, "updated_at", None) is None:
                instance.updated_at = now  # type: ignore[attr-defined]

    async def rollback(self) -> None:
        pass

    def queue_scalar(self, value: object | None) -> None:
        self._execute_results.append(FakeScalarResult(scalar_value=value))

    def queue_count(self, value: int) -> None:
        self._execute_results.append(FakeScalarResult(scalar_value=value))

    def queue_scalars(self, items: list[object]) -> None:
        self._execute_results.append(FakeScalarResult(scalar_items=items))


def _where_clause_texts(statements: list[object]) -> list[str]:
    return [" ".join(str(criteria) for criteria in getattr(statement, "_where_criteria", ())) for statement in statements]


async def test_seed_default_units_is_idempotent() -> None:
    tenant_id = uuid.uuid4()
    session = RecordingAsyncSession()
    session.queue_scalars([])

    created = await seed_default_units(session, tenant_id)

    assert [unit.code for unit in created] == [code for code, _, _ in DEFAULT_UNIT_OF_MEASURE_SEEDS]
    added_count = len(session.added)

    session.queue_scalars(created)
    created_again = await seed_default_units(session, tenant_id)

    assert created_again == []
    assert len(session.added) == added_count


async def test_list_units_applies_active_filter_when_requested() -> None:
    tenant_id = uuid.uuid4()
    unit = UnitOfMeasure(
        tenant_id=tenant_id,
        code="pcs",
        name="Pieces",
        decimal_places=0,
        is_active=True,
    )
    session = RecordingAsyncSession()
    session.queue_count(1)
    session.queue_scalars([unit])

    items, total = await list_units(
        session,
        tenant_id,
        active_only=True,
        seed_defaults=False,
    )

    assert total == 1
    assert items == [unit]
    assert all("unit_of_measure.is_active" in text for text in _where_clause_texts(session.executed))


async def test_list_units_omits_active_filter_when_disabled() -> None:
    tenant_id = uuid.uuid4()
    active_unit = UnitOfMeasure(
        tenant_id=tenant_id,
        code="pcs",
        name="Pieces",
        decimal_places=0,
        is_active=True,
    )
    inactive_unit = UnitOfMeasure(
        tenant_id=tenant_id,
        code="box",
        name="Box",
        decimal_places=0,
        is_active=False,
    )
    session = RecordingAsyncSession()
    session.queue_count(2)
    session.queue_scalars([active_unit, inactive_unit])

    items, total = await list_units(
        session,
        tenant_id,
        active_only=False,
        seed_defaults=False,
    )

    assert total == 2
    assert items == [active_unit, inactive_unit]
    assert all("unit_of_measure.is_active" not in text for text in _where_clause_texts(session.executed))