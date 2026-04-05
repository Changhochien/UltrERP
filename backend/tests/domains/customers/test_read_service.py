"""Tests for customer read service operations."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from domains.customers.models import Customer
from domains.customers.schemas import CustomerListParams
from domains.customers.service import get_customer, list_customers, lookup_customer_by_ban

DEFAULT_TENANT = uuid.UUID("00000000-0000-0000-0000-000000000001")

# Consumed by set_tenant; return value unused.
_TENANT_OK = None


def _make_customer(**overrides: object) -> Customer:
    defaults: dict[str, object] = {
        "id": uuid.uuid4(),
        "tenant_id": DEFAULT_TENANT,
        "company_name": "Test Corp",
        "normalized_business_number": "04595252",
        "billing_address": "Taipei",
        "contact_name": "Alice",
        "contact_phone": "0912-345-678",
        "contact_email": "a@b.com",
        "credit_limit": 1000,
        "status": "active",
        "version": 1,
    }
    defaults.update(overrides)
    return Customer(**defaults)  # type: ignore[arg-type]


class _FakeScalarResult:
    def __init__(self, items: list[Customer]) -> None:
        self._items = items

    def all(self) -> list[Customer]:
        return self._items


class _FakeResult:
    """Mimics SQLAlchemy Result for both scalar() and scalars()."""

    def __init__(self, value: object = None, items: list[Customer] | None = None) -> None:
        self._value = value
        self._items = items or []

    def scalar(self) -> object:
        return self._value

    def scalar_one_or_none(self) -> object:
        return self._value

    def scalars(self) -> _FakeScalarResult:
        return _FakeScalarResult(self._items)


def _mock_session(results: list[_FakeResult]) -> AsyncSession:
    """Return a mock session that yields the given results in order."""
    session = MagicMock(spec=AsyncSession)
    session.execute = AsyncMock(side_effect=results)
    # Support `async with session.begin():`
    begin_ctx = MagicMock()
    begin_ctx.__aenter__ = AsyncMock(return_value=None)
    begin_ctx.__aexit__ = AsyncMock(return_value=False)
    session.begin = MagicMock(return_value=begin_ctx)
    return session


# ---------------------------------------------------------------------------
# list_customers
# ---------------------------------------------------------------------------
class TestListCustomers:
    @pytest.mark.asyncio
    async def test_returns_items_and_count(self) -> None:
        c1 = _make_customer(company_name="Alpha")
        session = _mock_session(
            [
                _FakeResult(value=_TENANT_OK),  # set_tenant
                _FakeResult(value=1),  # count query
                _FakeResult(items=[c1]),  # items query
            ]
        )
        params = CustomerListParams()
        items, total = await list_customers(session, params)
        assert total == 1
        assert len(items) == 1
        assert items[0].company_name == "Alpha"

    @pytest.mark.asyncio
    async def test_empty_result(self) -> None:
        session = _mock_session(
            [
                _FakeResult(value=_TENANT_OK),  # set_tenant
                _FakeResult(value=0),
                _FakeResult(items=[]),
            ]
        )
        params = CustomerListParams()
        items, total = await list_customers(session, params)
        assert total == 0
        assert items == []

    @pytest.mark.asyncio
    async def test_with_search_query(self) -> None:
        session = _mock_session(
            [
                _FakeResult(value=_TENANT_OK),  # set_tenant
                _FakeResult(value=1),
                _FakeResult(items=[_make_customer()]),
            ]
        )
        params = CustomerListParams(q="Test")
        items, total = await list_customers(session, params)
        assert total == 1
        # Verify execute was called three times (set_tenant + count + items)
        assert session.execute.call_count == 3

    @pytest.mark.asyncio
    async def test_with_numeric_search_query(self) -> None:
        session = _mock_session(
            [
                _FakeResult(value=_TENANT_OK),  # set_tenant
                _FakeResult(value=1),
                _FakeResult(items=[_make_customer()]),
            ]
        )
        params = CustomerListParams(q="0459")
        items, total = await list_customers(session, params)
        assert total == 1

    @pytest.mark.asyncio
    async def test_with_status_filter(self) -> None:
        session = _mock_session(
            [
                _FakeResult(value=_TENANT_OK),  # set_tenant
                _FakeResult(value=2),
                _FakeResult(items=[_make_customer(), _make_customer()]),
            ]
        )
        params = CustomerListParams(status="active")
        items, total = await list_customers(session, params)
        assert total == 2
        assert len(items) == 2

    @pytest.mark.asyncio
    async def test_pagination(self) -> None:
        session = _mock_session(
            [
                _FakeResult(value=_TENANT_OK),  # set_tenant
                _FakeResult(value=50),
                _FakeResult(items=[_make_customer()]),
            ]
        )
        params = CustomerListParams(page=3, page_size=10)
        items, total = await list_customers(session, params)
        assert total == 50


# ---------------------------------------------------------------------------
# get_customer
# ---------------------------------------------------------------------------
class TestGetCustomer:
    @pytest.mark.asyncio
    async def test_returns_customer(self) -> None:
        c = _make_customer()
        session = _mock_session([_FakeResult(value=_TENANT_OK), _FakeResult(value=c)])
        result = await get_customer(session, c.id)
        assert result is c

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self) -> None:
        session = _mock_session([_FakeResult(value=_TENANT_OK), _FakeResult(value=None)])
        result = await get_customer(session, uuid.uuid4())
        assert result is None


# ---------------------------------------------------------------------------
# lookup_customer_by_ban
# ---------------------------------------------------------------------------
class TestLookupCustomerByBan:
    @pytest.mark.asyncio
    async def test_returns_customer(self) -> None:
        c = _make_customer(normalized_business_number="04595252")
        session = _mock_session([_FakeResult(value=_TENANT_OK), _FakeResult(value=c)])
        result = await lookup_customer_by_ban(session, "04595252")
        assert result is c

    @pytest.mark.asyncio
    async def test_normalizes_input(self) -> None:
        c = _make_customer(normalized_business_number="04595252")
        session = _mock_session([_FakeResult(value=_TENANT_OK), _FakeResult(value=c)])
        result = await lookup_customer_by_ban(session, "0459-5252")
        assert result is c

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self) -> None:
        session = _mock_session([_FakeResult(value=_TENANT_OK), _FakeResult(value=None)])
        result = await lookup_customer_by_ban(session, "99999999")
        assert result is None
