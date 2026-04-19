from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from common.errors import ValidationError
from domains.inventory.schemas import SupplierCreate, SupplierUpdate
from domains.inventory.services import (
    create_supplier,
    list_suppliers,
    set_supplier_status,
    update_supplier,
)


class FakeSupplier:
    def __init__(
        self,
        *,
        supplier_id: uuid.UUID | None = None,
        name: str = "Acme Supply",
        is_active: bool = True,
    ) -> None:
        self.id = supplier_id or uuid.uuid4()
        self.tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        self.name = name
        self.contact_email = "acme@example.com"
        self.phone = "555-0100"
        self.address = "123 Supply St"
        self.default_lead_time_days = 7
        self.legacy_master_snapshot = {"legacy_code": "SUP-001"}
        self.is_active = is_active
        self.created_at = datetime.now(tz=UTC)


class FakeResult:
    def __init__(self, scalar_value: object | None = None, rows: list[object] | None = None) -> None:
        self._scalar_value = scalar_value
        self._rows = rows or []

    def scalar_one_or_none(self) -> object | None:
        return self._scalar_value

    def scalar(self) -> int:
        return int(self._scalar_value or 0)

    def scalars(self) -> FakeResult:
        return self

    def all(self) -> list[object]:
        return list(self._rows)


class FakeAsyncSession:
    def __init__(self) -> None:
        self._execute_results: list[FakeResult] = []
        self.flush_calls = 0
        self.added: list[object] = []
        self.where_clauses: list[str] = []

    def add(self, obj: object) -> None:
        self.added.append(obj)

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


async def test_create_supplier_trims_and_persists() -> None:
    session = FakeAsyncSession()

    supplier = await create_supplier(
        session,
        uuid.uuid4(),
        SupplierCreate(
            name="  Acme Supply  ",
            contact_email="  acme@example.com  ",
            phone=" 555-0100 ",
            address=" 123 Supply St ",
            default_lead_time_days=5,
        ),
    )

    assert supplier.name == "Acme Supply"
    assert supplier.contact_email == "acme@example.com"
    assert supplier.phone == "555-0100"
    assert supplier.address == "123 Supply St"
    assert supplier.default_lead_time_days == 5
    assert supplier.is_active is True
    assert session.flush_calls == 1


async def test_create_supplier_rejects_blank_name() -> None:
    session = FakeAsyncSession()

    with pytest.raises(ValidationError) as exc_info:
        await create_supplier(
            session,
            uuid.uuid4(),
            SimpleNamespace(
                name="   ",
                contact_email=None,
                phone=None,
                address=None,
                default_lead_time_days=None,
            ),
        )

    assert exc_info.value.errors[0]["loc"] == ("name",)


async def test_update_supplier_returns_none_when_missing() -> None:
    session = FakeAsyncSession()
    session.queue_scalar(None)

    result = await update_supplier(
        session,
        uuid.uuid4(),
        uuid.uuid4(),
        SupplierUpdate(
            name="Acme Supply",
            contact_email=None,
            phone=None,
            address=None,
            default_lead_time_days=5,
        ),
    )

    assert result is None
    assert session.flush_calls == 0


async def test_update_supplier_updates_existing_fields() -> None:
    supplier = FakeSupplier()
    session = FakeAsyncSession()
    session.queue_scalar(supplier)

    result = await update_supplier(
        session,
        supplier.tenant_id,
        supplier.id,
        SupplierUpdate(
            name="  Beta Supply  ",
            contact_email=" beta@example.com ",
            phone=" 555-0199 ",
            address=" 99 Harbor Rd ",
            default_lead_time_days=12,
        ),
    )

    assert result is supplier
    assert supplier.name == "Beta Supply"
    assert supplier.contact_email == "beta@example.com"
    assert supplier.phone == "555-0199"
    assert supplier.address == "99 Harbor Rd"
    assert supplier.default_lead_time_days == 12
    assert session.flush_calls == 1


async def test_set_supplier_status_updates_existing_supplier() -> None:
    supplier = FakeSupplier(is_active=True)
    session = FakeAsyncSession()
    session.queue_scalar(supplier)

    result = await set_supplier_status(session, supplier.tenant_id, supplier.id, is_active=False)

    assert result is supplier
    assert supplier.is_active is False
    assert session.flush_calls == 1


async def test_list_suppliers_filters_active_and_query() -> None:
    session = FakeAsyncSession()
    session.queue_count(0)
    session.queue_rows([])

    await list_suppliers(session, uuid.uuid4(), q="Acme", active_only=True)

    assert any("supplier.is_active" in clause for clause in session.where_clauses)
    assert any("supplier.name" in clause for clause in session.where_clauses)


async def test_list_suppliers_can_include_inactive() -> None:
    session = FakeAsyncSession()
    session.queue_count(0)
    session.queue_rows([])

    await list_suppliers(session, uuid.uuid4(), active_only=False)

    assert all("supplier.is_active" not in clause for clause in session.where_clauses)