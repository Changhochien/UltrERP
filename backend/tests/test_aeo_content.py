"""Tests for AEO content generation — Story 10.3."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from domains.aeo.content import (
	_build_faq,
	_build_summary,
	generate_aeo_content,
)

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
	p = MagicMock()
	p.id = product_id or uuid.uuid4()
	p.name = name
	p.code = code
	p.category = category
	p.description = description
	p.unit = unit
	p.status = status
	p.updated_at = (
		datetime(2026, 4, 1, 12, 0, 0, tzinfo=timezone.utc)
		if updated_at is _UNSET
		else updated_at
	)
	return p


@pytest.fixture
def _override_db():
	from common.database import get_db

	def _set(mock_session):
		async def _fake_db():
			yield mock_session

		app.dependency_overrides[get_db] = _fake_db

	yield _set
	app.dependency_overrides.clear()


# ── generate_aeo_content tests ────────────────────────────────


def test_aeo_content_has_all_sections():
	"""generate_aeo_content returns all required sections."""
	product = _make_product()
	result = generate_aeo_content(product)

	assert "product_summary" in result
	assert "specifications" in result
	assert "faq" in result
	assert "jsonld" in result
	assert "meta" in result


def test_aeo_meta_schema_version():
	"""meta.schema_version is '1.0'."""
	product = _make_product()
	result = generate_aeo_content(product)

	assert result["meta"]["schema_version"] == "1.0"
	assert "generated_at" in result["meta"]


def test_aeo_jsonld_is_valid_schema_org():
	"""jsonld section contains valid schema.org Product."""
	product = _make_product()
	result = generate_aeo_content(product)

	assert result["jsonld"]["@context"] == "https://schema.org"
	assert result["jsonld"]["@type"] == "Product"
	assert result["jsonld"]["name"] == "Widget A"


# ── _build_summary tests ─────────────────────────────────────


def test_summary_with_all_fields():
	"""Summary includes name, category, description, and availability."""
	product = _make_product()
	summary = _build_summary(product)

	assert "Widget A" in summary
	assert "Hardware" in summary
	assert "Industrial grade widget" in summary
	assert "Available" in summary


def test_summary_without_description():
	"""Summary is grammatically correct without description."""
	product = _make_product(description=None)
	summary = _build_summary(product)

	assert "Widget A" in summary
	assert "Available in pcs units" in summary


def test_summary_without_category():
	"""Summary handles missing category."""
	product = _make_product(category=None)
	summary = _build_summary(product)

	assert "Widget A" in summary
	assert "is a product" in summary


def test_summary_inactive_shows_status():
	"""Inactive product shows status label instead of 'Available'."""
	product = _make_product(status="inactive")
	summary = _build_summary(product)

	assert "Out of Stock" in summary


def test_summary_discontinued_shows_status():
	"""Discontinued product shows 'Discontinued'."""
	product = _make_product(status="discontinued")
	summary = _build_summary(product)

	assert "Discontinued" in summary


def test_summary_word_count_cap():
	"""Summary is capped at 100 words."""
	# Create a very long description to trigger the cap
	long_desc = " ".join(["word"] * 200)
	product = _make_product(description=long_desc)
	summary = _build_summary(product)

	word_count = len(summary.split())
	assert word_count <= 101  # 100 words + "..." counts as 1 word


def test_summary_long_description_truncated():
	"""Long first sentence of description is truncated."""
	long_first_sentence = "A" * 100 + ". Second sentence."
	product = _make_product(description=long_first_sentence)
	summary = _build_summary(product)

	assert "..." in summary


def test_summary_minimum_word_count():
	"""Summary generates at least a few words for minimal products."""
	# Minimal product: name only, no category, no description
	product = _make_product(name="X", category=None, description=None)
	summary = _build_summary(product)

	word_count = len(summary.split())
	assert word_count >= 3  # "X is a product. Currently In Stock." = 6 words


# ── specifications tests ──────────────────────────────────────


def test_specs_active_availability():
	"""Active status maps to 'In Stock'."""
	product = _make_product(status="active")
	result = generate_aeo_content(product)

	assert result["specifications"]["availability"] == "In Stock"


def test_specs_discontinued_availability():
	"""Discontinued status maps to 'Discontinued'."""
	product = _make_product(status="discontinued")
	result = generate_aeo_content(product)

	assert result["specifications"]["availability"] == "Discontinued"


def test_specs_inactive_availability():
	"""Inactive status maps to 'Out of Stock'."""
	product = _make_product(status="inactive")
	result = generate_aeo_content(product)

	assert result["specifications"]["availability"] == "Out of Stock"


def test_specs_unknown_availability():
	"""Unknown status maps to 'Unknown'."""
	product = _make_product(status="archived")
	result = generate_aeo_content(product)

	assert result["specifications"]["availability"] == "Unknown"


def test_specs_null_category_defaults():
	"""Null category defaults to 'Uncategorized'."""
	product = _make_product(category=None)
	result = generate_aeo_content(product)

	assert result["specifications"]["category"] == "Uncategorized"


def test_specs_sku_and_unit():
	"""SKU and unit_of_measure are mapped correctly."""
	product = _make_product(code="TEST-99", unit="kg")
	result = generate_aeo_content(product)

	assert result["specifications"]["sku"] == "TEST-99"
	assert result["specifications"]["unit_of_measure"] == "kg"


# ── FAQ tests ─────────────────────────────────────────────────


def test_faq_at_least_two_entries():
	"""FAQ always has at least 2 entries."""
	product = _make_product(category=None)
	faq = _build_faq(product)

	assert len(faq) >= 2
	for entry in faq:
		assert "name" in entry
		assert "acceptedAnswer" in entry
		assert entry["acceptedAnswer"]["@type"] == "Answer"
		assert "text" in entry["acceptedAnswer"]


def test_faq_three_entries_with_category():
	"""FAQ has 3 entries when category is present."""
	product = _make_product(category="Electronics")
	faq = _build_faq(product)

	assert len(faq) == 3


def test_faq_two_entries_without_category():
	"""FAQ has 2 entries when category is absent."""
	product = _make_product(category=None)
	faq = _build_faq(product)

	assert len(faq) == 2


def test_faq_uses_product_name():
	"""FAQ questions use the product name."""
	product = _make_product(name="Super Widget Pro")
	faq = _build_faq(product)

	for entry in faq:
		assert "Super Widget Pro" in entry["name"]


# ── API integration tests ────────────────────────────────────


async def test_api_aeo_returns_200(_override_db):
	"""GET /api/v1/inventory/products/{id}/aeo returns 200."""
	product = _make_product()
	mock_session = AsyncMock()
	mock_session.get = AsyncMock(return_value=product)
	_override_db(mock_session)

	transport = ASGITransport(app=app)
	async with AsyncClient(transport=transport, base_url="http://testserver") as client:
		resp = await client.get(
			f"/api/v1/inventory/products/{product.id}/aeo",
		)

	assert resp.status_code == 200
	body = resp.json()
	assert "product_summary" in body
	assert "specifications" in body
	assert "faq" in body
	assert "jsonld" in body
	assert "meta" in body


async def test_api_aeo_returns_404_for_unknown(_override_db):
	"""GET /api/v1/inventory/products/{id}/aeo returns 404 for unknown product."""
	mock_session = AsyncMock()
	mock_session.get = AsyncMock(return_value=None)
	_override_db(mock_session)

	transport = ASGITransport(app=app)
	async with AsyncClient(transport=transport, base_url="http://testserver") as client:
		resp = await client.get(
			f"/api/v1/inventory/products/{uuid.uuid4()}/aeo",
		)

	assert resp.status_code == 404
