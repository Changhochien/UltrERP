"""Tests for create_product service function.

These tests exercise the validation and business logic in the service layer
without a real database — the DB interaction is tested in the API tests.
"""

from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError as PydanticValidationError

# The service may raise these; adjust imports once the module is live
try:
    from common.errors import DuplicateProductCodeError, ValidationError
except ImportError:
    DuplicateProductCodeError = None
    ValidationError = None

from domains.inventory.services import create_product


def _make_data(**overrides):
    """Return a mock data object with required create-product fields."""
    defaults = {
        "code": "WIDGET-001",
        "name": "Test Widget",
        "category": None,
        "description": None,
        "unit": "pcs",
    }
    defaults.update(overrides)
    m = type("DataMock", (), defaults)()
    return m


class TestBlankCodeAfterTrim:
    """Code must not be blank after stripping whitespace."""

    def test_whitespace_only_code_raises_validation_error(self) -> None:
        """A code that is only spaces/tabs/newlines must be rejected."""
        if ValidationError is None:
            pytest.skip("ValidationError not yet defined")

        session = _FakeAsyncSession()
        tenant_id = uuid.uuid4()
        data = _make_data(code="   ")

        with pytest.raises(ValidationError) as exc_info:
            # Inline await to keep pytest happy with async service
            import asyncio
            asyncio.get_event_loop().run_until_complete(
                create_product(session, tenant_id, data)
            )

        errors = exc_info.value.errors
        assert any(e.get("loc") == ("code",) for e in errors)

    def test_newline_only_code_raises_validation_error(self) -> None:
        if ValidationError is None:
            pytest.skip("ValidationError not yet defined")

        session = _FakeAsyncSession()
        tenant_id = uuid.uuid4()
        data = _make_data(code="\n\t")

        with pytest.raises(ValidationError):
            import asyncio
            asyncio.get_event_loop().run_until_complete(
                create_product(session, tenant_id, data)
            )


class TestDuplicateCodeDetection:
    """Product code must be unique within a tenant."""

    def test_duplicate_code_raises_DuplicateProductCodeError(self) -> None:
        if DuplicateProductCodeError is None:
            pytest.skip("DuplicateProductCodeError not yet defined")

        session = _FakeAsyncSession()
        tenant_id = uuid.uuid4()

        existing = _FakeProduct(id=uuid.uuid4(), code="WIDGET-001", name="Existing Widget")
        session.queue_result(existing)

        data = _make_data(code="WIDGET-001", name="New Widget")

        with pytest.raises(DuplicateProductCodeError) as exc_info:
            import asyncio
            asyncio.get_event_loop().run_until_complete(
                create_product(session, tenant_id, data)
            )

        assert exc_info.value.existing_code == "WIDGET-001"


class TestSuccessfulCreation:
    """Valid input should create and flush a product record."""

    def test_create_product_success(self) -> None:
        session = _FakeAsyncSession()
        session.queue_result(None)  # no duplicate found
        tenant_id = uuid.uuid4()
        data = _make_data(code="WIDGET-001", name="Test Widget")

        import asyncio
        product = asyncio.get_event_loop().run_until_complete(
            create_product(session, tenant_id, data)
        )

        assert len(session.added) == 1
        assert session.added[0].code == "WIDGET-001"
        assert session.added[0].name == "Test Widget"
        assert session.added[0].status == "active"


# ── Fakes ─────────────────────────────────────────────────────


class _FakeProduct:
    def __init__(self, id, code, name):
        self.id = id
        self.code = code
        self.name = name
        self.tenant_id = uuid.uuid4()
        self.category = None
        self.description = None
        self.unit = "pcs"
        self.status = "active"


class _FakeResult:
    def __init__(self, obj):
        self._obj = obj

    def scalar_one_or_none(self):
        return self._obj


class _FakeAsyncSession:
    """Minimal async session stub for create_product service tests."""

    def __init__(self):
        self.added = []
        self._results = []

    def add(self, instance):
        self.added.append(instance)

    async def execute(self, statement, params=None):
        if self._results:
            return self._results.pop(0)
        return _FakeResult(None)

    async def flush(self):
        for obj in self.added:
            if getattr(obj, "id", None) is None:
                setattr(obj, "id", uuid.uuid4())

    def queue_result(self, obj):
        self._results.append(_FakeResult(obj))
