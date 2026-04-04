"""Tests for JSON-LD structured data generation — Story 10.1."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from domains.aeo.jsonld import generate_product_jsonld

_UNSET = object()

# ── Helpers ───────────────────────────────────────────────────


def _make_product(
	*,
	name: str = "Widget A",
	code: str = "WDG-001",
	category: str | None = "Hardware",
	description: str | None = "Industrial grade widget",
	unit: str = "pcs",
	status: str = "active",
	product_id: uuid.UUID | None = None,
	updated_at: datetime | None | object = _UNSET,
) -> MagicMock:
	"""Create a mock Product with the given attributes."""
	product = MagicMock()
	product.id = product_id or uuid.uuid4()
	product.name = name
	product.code = code
	product.category = category
	product.description = description
	product.unit = unit
	product.status = status
	product.updated_at = (
		datetime(2026, 4, 1, 12, 0, 0, tzinfo=timezone.utc)
		if updated_at is _UNSET
		else updated_at
	)
	return product


# ── Unit tests for generate_product_jsonld ────────────────────


def test_jsonld_all_fields_populated():
	"""JSON-LD includes all fields when product is fully populated."""
	product = _make_product()
	result = generate_product_jsonld(product)

	assert result["@context"] == "https://schema.org"
	assert result["@type"] == "Product"
	assert result["name"] == "Widget A"
	assert result["sku"] == "WDG-001"
	assert result["productID"] == str(product.id)
	assert result["category"] == "Hardware"
	assert result["description"] == "Industrial grade widget"


def test_jsonld_omits_null_category():
	"""JSON-LD omits 'category' when product.category is None."""
	product = _make_product(category=None)
	result = generate_product_jsonld(product)

	assert "category" not in result


def test_jsonld_omits_null_description():
	"""JSON-LD omits 'description' when product.description is None."""
	product = _make_product(description=None)
	result = generate_product_jsonld(product)

	assert "description" not in result


def test_jsonld_omits_both_optional_fields():
	"""JSON-LD omits both optional fields when both are None."""
	product = _make_product(category=None, description=None)
	result = generate_product_jsonld(product)

	assert "category" not in result
	assert "description" not in result
	# Required fields still present
	assert result["name"] == "Widget A"
	assert result["sku"] == "WDG-001"


def test_jsonld_active_status_maps_to_instock():
	"""Active status maps to schema.org InStock availability."""
	product = _make_product(status="active")
	result = generate_product_jsonld(product)

	assert result["offers"]["@type"] == "Offer"
	assert result["offers"]["availability"] == "https://schema.org/InStock"
	assert "price" not in result["offers"]


def test_jsonld_discontinued_status_maps_to_discontinued():
	"""Discontinued status maps to schema.org Discontinued availability."""
	product = _make_product(status="discontinued")
	result = generate_product_jsonld(product)

	assert result["offers"]["availability"] == "https://schema.org/Discontinued"


def test_jsonld_inactive_status_maps_to_outofstock():
	"""Inactive status maps to schema.org OutOfStock availability."""
	product = _make_product(status="inactive")
	result = generate_product_jsonld(product)

	assert result["offers"]["availability"] == "https://schema.org/OutOfStock"


def test_jsonld_unknown_status_omits_offers():
	"""Unknown status does not include offers section."""
	product = _make_product(status="archived")
	result = generate_product_jsonld(product)

	assert "offers" not in result


def test_jsonld_unit_as_additional_property():
	"""Unit of measure is represented as additionalProperty."""
	product = _make_product(unit="kg")
	result = generate_product_jsonld(product)

	prop = result["additionalProperty"]
	assert prop["@type"] == "PropertyValue"
	assert prop["name"] == "unitOfMeasure"
	assert prop["value"] == "kg"


def test_jsonld_unit_none_omits_additional_property():
	"""additionalProperty is omitted when unit is None."""
	product = _make_product(unit=None)
	result = generate_product_jsonld(product)

	assert "additionalProperty" not in result


def test_jsonld_product_id_is_string_uuid():
	"""productID is a string representation of the UUID."""
	pid = uuid.uuid4()
	product = _make_product(product_id=pid)
	result = generate_product_jsonld(product)

	assert result["productID"] == str(pid)
	assert isinstance(result["productID"], str)


def test_jsonld_date_modified_iso_format():
	"""dateModified is in ISO 8601 format."""
	dt = datetime(2026, 4, 1, 12, 30, 45, tzinfo=timezone.utc)
	product = _make_product(updated_at=dt)
	result = generate_product_jsonld(product)

	assert result["dateModified"] == "2026-04-01T12:30:45+00:00"


def test_jsonld_no_date_modified_when_none():
	"""dateModified is omitted when updated_at is None."""
	product = _make_product(updated_at=None)
	result = generate_product_jsonld(product)

	assert "dateModified" not in result


# ── API endpoint integration tests ───────────────────────────


@pytest.fixture
def _override_db():
	"""Yield a helper that overrides get_db, then clears overrides."""
	from common.database import get_db

	def _set(mock_session):
		async def _fake_db():
			yield mock_session

		app.dependency_overrides[get_db] = _fake_db

	yield _set
	app.dependency_overrides.clear()


async def test_api_jsonld_returns_200(_override_db):
	"""GET /api/v1/inventory/products/{id}/jsonld returns 200 with ld+json."""
	product = _make_product()
	mock_session = AsyncMock()
	mock_session.get = AsyncMock(return_value=product)
	_override_db(mock_session)

	transport = ASGITransport(app=app)
	async with AsyncClient(transport=transport, base_url="http://testserver") as client:
		resp = await client.get(
			f"/api/v1/inventory/products/{product.id}/jsonld",
		)

	assert resp.status_code == 200
	assert "application/ld+json" in resp.headers["content-type"]
	body = resp.json()
	assert body["@context"] == "https://schema.org"
	assert body["@type"] == "Product"
	assert body["name"] == "Widget A"


async def test_api_jsonld_returns_404_for_unknown(_override_db):
	"""GET /api/v1/inventory/products/{id}/jsonld returns 404 for unknown product."""
	mock_session = AsyncMock()
	mock_session.get = AsyncMock(return_value=None)
	_override_db(mock_session)

	transport = ASGITransport(app=app)
	async with AsyncClient(transport=transport, base_url="http://testserver") as client:
		resp = await client.get(
			f"/api/v1/inventory/products/{uuid.uuid4()}/jsonld",
		)

	assert resp.status_code == 404
