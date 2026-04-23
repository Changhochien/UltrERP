"""Tests for supplier procurement controls (Story 24-5)."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from collections.abc import AsyncGenerator
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from common.database import get_db
from common.models.supplier import Supplier


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------

TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


class FakeAsyncSession:
    def __init__(self) -> None:
        self._execute_results: list[Any] = []
        self.commit_calls = 0
        self.added: list[object] = []
        self._db: dict[str, Any] = {}

    def add(self, instance: object) -> None:
        self.added.append(instance)
        if hasattr(instance, "id") and instance.id is None:
            instance.id = uuid.uuid4()

    async def execute(self, statement: Any, params: Any = None) -> Any:
        if self._execute_results:
            return self._execute_results.pop(0)
        return FakeResult()

    async def flush(self) -> None:
        pass

    async def commit(self) -> None:
        self.commit_calls += 1

    async def rollback(self) -> None:
        pass

    def queue_result(self, result: Any) -> None:
        self._execute_results.append(result)

    def queue_scalar(self, value: Any) -> None:
        self._execute_results.append(FakeScalarResult(value))

    def queue_count(self, value: int) -> None:
        self._execute_results.append(FakeScalarResult(value))


class FakeResult:
    def scalars(self) -> FakeResult:
        return self

    def all(self) -> list[Any]:
        return []

    def scalar_one_or_none(self) -> Any:
        return None


class FakeScalarResult:
    def __init__(self, value: Any) -> None:
        self._value = value

    def scalar_one_or_none(self) -> Any:
        return self._value

    def scalar(self) -> Any:
        return self._value


_MISSING = object()


def _setup(session: FakeAsyncSession) -> Any:
    previous = app.dependency_overrides.get(get_db, _MISSING)

    async def override() -> AsyncGenerator[FakeAsyncSession, None]:
        yield session

    app.dependency_overrides[get_db] = override
    return previous


def _teardown(previous: Any) -> None:
    if previous is _MISSING:
        app.dependency_overrides.pop(get_db, None)
    else:
        app.dependency_overrides[get_db] = previous


def auth_header() -> dict[str, str]:
    return {
        "X-Tenant-Id": str(TENANT_ID),
        "Authorization": "Bearer test-token",
    }


# --------------------------------------------------------------------------
# Supplier Model Tests
# --------------------------------------------------------------------------

class TestSupplierModelControls:
    """Test supplier model procurement control methods."""

    def test_is_effectively_on_hold_when_on_hold_true(self) -> None:
        """Supplier is on hold when on_hold is True."""
        supplier = Supplier(
            id=uuid.uuid4(),
            tenant_id=TENANT_ID,
            name="Test Supplier",
            on_hold=True,
            hold_type="manual",
            release_date=None,
        )
        assert supplier.is_effectively_on_hold() is True

    def test_is_effectively_on_hold_when_on_hold_false_and_no_release_date(self) -> None:
        """Supplier is NOT on hold when on_hold is False and no release_date."""
        supplier = Supplier(
            id=uuid.uuid4(),
            tenant_id=TENANT_ID,
            name="Test Supplier",
            on_hold=False,
            hold_type=None,
            release_date=None,
        )
        assert supplier.is_effectively_on_hold() is False

    def test_is_effectively_on_hold_when_release_date_in_future(self) -> None:
        """Supplier is NOT on hold when release_date is in the future."""
        future_date = date.today() + timedelta(days=7)
        supplier = Supplier(
            id=uuid.uuid4(),
            tenant_id=TENANT_ID,
            name="Test Supplier",
            on_hold=False,
            hold_type=None,
            release_date=future_date,
        )
        assert supplier.is_effectively_on_hold() is False

    def test_is_effectively_on_hold_when_release_date_in_past(self) -> None:
        """Supplier IS on hold when release_date is in the past."""
        past_date = date.today() - timedelta(days=1)
        supplier = Supplier(
            id=uuid.uuid4(),
            tenant_id=TENANT_ID,
            name="Test Supplier",
            on_hold=False,
            hold_type="quality",
            release_date=past_date,
        )
        assert supplier.is_effectively_on_hold() is True

    def test_is_effectively_on_hold_with_custom_check_date(self) -> None:
        """Supplier hold status respects custom check date."""
        release_date = date.today() + timedelta(days=5)
        supplier = Supplier(
            id=uuid.uuid4(),
            tenant_id=TENANT_ID,
            name="Test Supplier",
            on_hold=False,
            hold_type=None,
            release_date=release_date,
        )
        # Check before release date
        check_before = date.today()
        assert supplier.is_effectively_on_hold(check_before) is False
        # Check after release date
        check_after = date.today() + timedelta(days=10)
        assert supplier.is_effectively_on_hold(check_after) is True

    def test_get_rfq_controls_prevent_rfqs(self) -> None:
        """prevent_rfqs blocks RFQ workflow."""
        supplier = Supplier(
            id=uuid.uuid4(),
            tenant_id=TENANT_ID,
            name="Blocked Supplier",
            on_hold=False,
            prevent_rfqs=True,
        )
        blocked, warned, reason = supplier.get_rfq_controls()
        assert blocked is True
        assert warned is False
        assert "blocked from RFQs" in reason

    def test_get_rfq_controls_on_hold(self) -> None:
        """Supplier on hold blocks RFQ workflow."""
        supplier = Supplier(
            id=uuid.uuid4(),
            tenant_id=TENANT_ID,
            name="Held Supplier",
            on_hold=True,
            hold_type="payment",
        )
        blocked, warned, reason = supplier.get_rfq_controls()
        assert blocked is True
        assert warned is False
        assert "on hold" in reason
        assert "payment" in reason

    def test_get_rfq_controls_warn_rfqs(self) -> None:
        """warn_rfqs shows warning but doesn't block."""
        supplier = Supplier(
            id=uuid.uuid4(),
            tenant_id=TENANT_ID,
            name="Warned Supplier",
            on_hold=False,
            warn_rfqs=True,
        )
        blocked, warned, reason = supplier.get_rfq_controls()
        assert blocked is False
        assert warned is True
        assert "warnings" in reason

    def test_get_rfq_controls_no_controls(self) -> None:
        """Supplier with no controls allows RFQ workflow."""
        supplier = Supplier(
            id=uuid.uuid4(),
            tenant_id=TENANT_ID,
            name="Clean Supplier",
            on_hold=False,
            warn_rfqs=False,
            prevent_rfqs=False,
        )
        blocked, warned, reason = supplier.get_rfq_controls()
        assert blocked is False
        assert warned is False
        assert reason == ""

    def test_get_po_controls_prevent_pos(self) -> None:
        """prevent_pos blocks PO workflow."""
        supplier = Supplier(
            id=uuid.uuid4(),
            tenant_id=TENANT_ID,
            name="Blocked Supplier",
            on_hold=False,
            prevent_pos=True,
        )
        blocked, warned, reason = supplier.get_po_controls()
        assert blocked is True
        assert warned is False
        assert "blocked from POs" in reason

    def test_get_po_controls_warn_pos(self) -> None:
        """warn_pos shows warning but doesn't block."""
        supplier = Supplier(
            id=uuid.uuid4(),
            tenant_id=TENANT_ID,
            name="Warned Supplier",
            on_hold=False,
            warn_pos=True,
        )
        blocked, warned, reason = supplier.get_po_controls()
        assert blocked is False
        assert warned is True
        assert "PO warnings" in reason


# --------------------------------------------------------------------------
# Supplier Control Service Tests
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_check_supplier_rfq_controls_no_supplier_id() -> None:
    """Service returns empty result when no supplier_id provided."""
    from domains.procurement.service import check_supplier_rfq_controls

    session = FakeAsyncSession()
    result = await check_supplier_rfq_controls(
        session, TENANT_ID, None, "Test Supplier"
    )
    assert result.is_blocked is False
    assert result.is_warned is False
    assert result.supplier_name == "Test Supplier"


@pytest.mark.asyncio
async def test_check_supplier_po_controls_no_supplier_id() -> None:
    """Service returns empty result when no supplier_id provided."""
    from domains.procurement.service import check_supplier_po_controls

    session = FakeAsyncSession()
    result = await check_supplier_po_controls(
        session, TENANT_ID, None, "Test Supplier"
    )
    assert result.is_blocked is False
    assert result.is_warned is False
    assert result.supplier_name == "Test Supplier"


@pytest.mark.asyncio
async def test_enforce_supplier_controls_blocks_when_blocked() -> None:
    """enforce_supplier_controls raises ValidationError when blocked."""
    from domains.procurement.service import (
        SupplierControlResult,
        enforce_supplier_controls,
    )
    from common.errors import ValidationError

    result = SupplierControlResult(
        is_blocked=True,
        is_warned=False,
        reason="Supplier is on hold",
        supplier_name="Test Supplier",
    )

    with pytest.raises(ValidationError) as exc_info:
        enforce_supplier_controls(result, "RFQ submission")
    errors = exc_info.value.errors
    assert any("on hold" in e.get("message", "") for e in errors)


@pytest.mark.asyncio
async def test_enforce_supplier_controls_allows_when_not_blocked() -> None:
    """enforce_supplier_controls allows operation when not blocked."""
    from domains.procurement.service import (
        SupplierControlResult,
        enforce_supplier_controls,
    )

    result = SupplierControlResult(
        is_blocked=False,
        is_warned=True,
        reason="Warning only",
        supplier_name="Test Supplier",
    )
    # Should not raise
    enforce_supplier_controls(result, "RFQ submission")


# --------------------------------------------------------------------------
# Procurement Reporting Tests
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_procurement_summary_returns_stats() -> None:
    """get_procurement_summary returns expected structure."""
    from domains.procurement.service import get_procurement_summary

    session = FakeAsyncSession()
    # Mock count queries
    session.queue_count(10)  # rfq_count
    session.queue_count(5)   # rfq_submitted
    session.queue_count(20) # sq_count
    session.queue_count(15)  # sq_submitted
    session.queue_count(8)  # award_count
    session.queue_count(12) # po_count
    session.queue_count(10) # po_submitted
    session.queue_count(2)  # blocked_suppliers
    session.queue_count(3)  # warned_suppliers

    result = await get_procurement_summary(session, TENANT_ID)

    assert "period" in result
    assert "rfqs" in result
    assert "supplier_quotations" in result
    assert "awards" in result
    assert "purchase_orders" in result
    assert "supplier_controls" in result
    assert result["rfqs"]["total"] == 10
    assert result["supplier_controls"]["blocked_suppliers"] == 2


@pytest.mark.asyncio
async def test_get_quote_turnaround_stats_empty() -> None:
    """get_quote_turnaround_stats returns empty stats when no data."""
    from domains.procurement.service import get_quote_turnaround_stats

    session = FakeAsyncSession()
    session.queue_result(FakeResult())

    result = await get_quote_turnaround_stats(session, TENANT_ID)

    assert result["total_quotes"] == 0
    assert result["avg_turnaround_days"] is None


@pytest.mark.asyncio
async def test_get_supplier_performance_stats_empty() -> None:
    """get_supplier_performance_stats returns expected structure."""
    from domains.procurement.service import get_supplier_performance_stats

    session = FakeAsyncSession()
    session.queue_result(FakeResult())  # quotations
    session.queue_result(FakeResult())  # suppliers

    result = await get_supplier_performance_stats(session, TENANT_ID)

    assert "overall" in result
    assert "by_supplier" in result
    assert "supplier_controls" in result
    assert result["overall"]["total_quotes"] == 0


@pytest.mark.asyncio
async def test_get_supplier_controls_not_found() -> None:
    """get_supplier_controls raises error when supplier not found."""
    from domains.procurement.service import get_supplier_controls
    from common.errors import ValidationError

    session = FakeAsyncSession()
    session.queue_result(FakeResult())

    with pytest.raises(ValidationError) as exc_info:
        await get_supplier_controls(session, TENANT_ID, uuid.uuid4())
    errors = exc_info.value.errors
    assert any(e.get("field") == "supplier_id" for e in errors)
